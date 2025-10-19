use geo::{
    algorithm::{
        area::Area,
    },
    LineString, MultiLineString, MultiPolygon, Polygon, Point,
};
use crate::polygon_utils::{
    clean_multipolygon,
     point_in_multipolygon, create_polygon_buffer,
};
use anyhow::Result;
use rayon::prelude::*;

/// Generate concentric fill patterns for a multipolygon with parallel processing
pub fn generate_concentric_fill_concurrent(
    multipolygon: &MultiPolygon<f64>,
    pen_width: f64,
    _num_threads: Option<usize>,
    fill_holes: bool,
    discard_hole_borders: bool,
    discard_exterior: bool,
    reverse_ring_draw_order: bool,
) -> Result<MultiLineString<f64>> {
    // Note: We use the default Rayon thread pool instead of trying to create a global one
    // The global thread pool may already be initialized by the parent application
    
    // Clean the multipolygon first
    let cleaned_multi = clean_multipolygon(multipolygon)?;
    println!("Finished cleaning geometry, processing {} polygons", cleaned_multi.0.len());
    
    let results: Result<Vec<_>, _> =
        cleaned_multi.0
            .par_iter()
            .map(|polygon| generate_concentric_lines_for_polygon(polygon, pen_width, fill_holes, discard_hole_borders, discard_exterior, reverse_ring_draw_order))
            .collect();
    
    let polygon_lines = results?;
    
    // Collect all lines
    let mut all_lines = Vec::new();
    for lines in polygon_lines {
        all_lines.extend(lines.0);
    }
    
    Ok(MultiLineString::new(all_lines))
}

fn generate_concentric_lines_for_polygon(
    polygon: &Polygon<f64>,
    pen_width: f64,
    fill_holes: bool,
    discard_hole_borders: bool,
    discard_exterior: bool,
    reverse_ring_draw_order: bool,
) -> Result<MultiLineString<f64>> {
    let mut all_lines = Vec::new();
    
    // preserve the original exterior boundary (unless discard_exterior is true)
    if !discard_exterior {
        all_lines.push(polygon.exterior().clone());
    }
    
    // preserve original hole geometry (unless discard_hole_borders is true)
    if !polygon.interiors().is_empty() && !discard_hole_borders {
        for hole in polygon.interiors() {
            all_lines.push(hole.clone());
        }
    }
    
    if polygon.signed_area() > pen_width {
        let mut polygons_to_process = vec![polygon.clone()];
        
        // Convert original polygon to multipolygon for clipping operations
        // If fill_holes is true, use a polygon without holes for clipping
        let clipping_polygon = if fill_holes {
            Polygon::new(polygon.exterior().clone(), vec![])
        } else {
            polygon.clone()
        };
        let original_multipolygon = MultiPolygon::new(vec![clipping_polygon]);
        
        // Collect all fill lines first if we need to reverse the order
        let mut fill_lines = Vec::new();
        
        loop {
            if polygons_to_process.is_empty() {
                break;
            }
            
            let mut next_polygons = Vec::new();
            
            for current_polygon in polygons_to_process {
                // Check if polygon is too small to continue
                let area = current_polygon.unsigned_area();
                if area < (pen_width * pen_width * 0.25) || !area.is_finite() {
                    continue;
                }
                
                let inset_result = std::panic::catch_unwind(|| {
                    create_inset(&current_polygon, pen_width)
                });
                
                match inset_result {
                    Ok(Ok(inset_multi)) => {
                        if !inset_multi.0.is_empty() {
                            for inset_polygon in inset_multi.0 {
                                let inset_area = inset_polygon.unsigned_area();
                                if inset_area >= (pen_width * pen_width * 0.05) && inset_area.is_finite() {
                                    // Add boundary lines for this polygon (only exterior)
                                    let boundary_lines = polygon_to_lines(&inset_polygon);
                                    
                                    // Hole mask
                                    let boundary_multilinestring = MultiLineString::new(boundary_lines);
                                    let clipped_lines = clip_lines_to_multipolygon(&boundary_multilinestring, &original_multipolygon)?;
                                    
                                    // Store lines for potential reversal
                                    fill_lines.extend(clipped_lines.0);
                                    
                                    // Add to next iteration for further processing
                                    next_polygons.push(inset_polygon);
                                }
                            }
                        }
                    }
                    Ok(Err(_)) => {
                        eprintln!("Inset creation failed for polygon with area: {}", area);
                        continue;
                    }
                    Err(_) => {
                        eprintln!("Panic during inset creation for polygon with area: {}", area);
                        continue;
                    }
                }
            }
            
            polygons_to_process = next_polygons;
        }
        
        if reverse_ring_draw_order {
            // Reverse the order of the fill lines (innermost first)
            all_lines.extend(fill_lines.into_iter().rev());
        } else {
            // Normal order (outermost first)
            all_lines.extend(fill_lines);
        }

        Ok(MultiLineString::new(all_lines))
    }
    else 
    {
        Ok(MultiLineString::empty())
    }
}

fn create_inset(polygon: &Polygon<f64>, inset_distance: f64) -> Result<MultiPolygon<f64>> {
    let buffer_result = create_polygon_buffer(polygon, -inset_distance);
    
    match buffer_result {
        Ok(multi) => {
            let valid_polygons: Vec<_> = multi.0
                .into_iter()
                .filter(|p| {
                    let area = p.unsigned_area();
                    // filter suspicious polygons out
                    area > 1e-6 && area.is_finite() && p.exterior().coords().count() >= 4
                })
                .collect();
            
            Ok(MultiPolygon::new(valid_polygons))
        }
        Err(e) => Err(e),
    }
}

/// Convert a polygon's exterior to line strings (holes are handled separately)
fn polygon_to_lines(polygon: &Polygon<f64>) -> Vec<LineString<f64>> {
    let mut lines = Vec::new();
    lines.push(polygon.exterior().clone());
    lines
}

/// Clip lines to polygon boundaries (remove parts outside polygons)
pub fn clip_lines_to_multipolygon(
    lines: &MultiLineString<f64>,
    multipolygon: &MultiPolygon<f64>,
) -> Result<MultiLineString<f64>> {
    let mut clipped_lines = Vec::new();
    
    for line in &lines.0 {
        let clipped = clip_line_to_multipolygon(line, multipolygon);
        clipped_lines.extend(clipped);
    }
    
    Ok(MultiLineString::new(clipped_lines))
}

/// Clip a single line to multipolygon boundaries
fn clip_line_to_multipolygon(
    line: &LineString<f64>,
    multipolygon: &MultiPolygon<f64>,
) -> Vec<LineString<f64>> {
    let mut result = Vec::new();
    let mut current_line = Vec::new();
    
    for coord in line.coords() {
        let point = Point::new(coord.x, coord.y);
        let is_inside = point_in_multipolygon(&point, multipolygon);
        
        if is_inside {
            current_line.push(*coord);
        } else {
            if current_line.len() > 1 {
                result.push(LineString::new(current_line.clone()));
            }
            current_line.clear();
        }
    }
    
    // Add the final line segment if it exists
    if current_line.len() > 1 {
        result.push(LineString::new(current_line));
    }
    
    result
}
