use geo::{
    algorithm::{
        bool_ops::BooleanOps,
        simplify::Simplify,
        contains::Contains,
        area::Area,
    },
    Buffer,
    Coord, LineString, MultiPolygon, Polygon, Point,
};
use anyhow::Result;

/// Clean up a polygon by removing self-intersections and invalid geometry
pub fn clean_polygon(polygon: &Polygon<f64>) -> Result<MultiPolygon<f64>> {
    // Try boolean operations to clean up, but catch panics
    match std::panic::catch_unwind(|| {
        let multi = MultiPolygon::new(vec![polygon.clone()]);
        multi.union(&MultiPolygon::new(vec![]))
    }) {
        Ok(cleaned) => Ok(cleaned),
        Err(_) => {
            // If boolean ops fail, return the original polygon as-is
            Ok(MultiPolygon::new(vec![polygon.clone()]))
        }
    }
}

/// Clean up a multipolygon by removing self-intersections
pub fn clean_multipolygon(multipolygon: &MultiPolygon<f64>) -> Result<MultiPolygon<f64>> {
    // Try boolean operations to clean up, but catch panics
    match std::panic::catch_unwind(|| {
        multipolygon.union(&MultiPolygon::new(vec![]))
    }) {
        Ok(cleaned) => Ok(cleaned),
        Err(_) => {
            // If boolean ops fail, return the original multipolygon as-is
            Ok(multipolygon.clone())
        }
    }
}

/// Check if a point is inside a polygon (considering holes)
pub fn point_in_polygon(point: &Point<f64>, polygon: &Polygon<f64>) -> bool {
    polygon.contains(point)
}

/// Check if a point is inside any polygon in a multipolygon
pub fn point_in_multipolygon(point: &Point<f64>, multipolygon: &MultiPolygon<f64>) -> bool {
    multipolygon.0.iter().any(|polygon| point_in_polygon(point, polygon))
}

/// Create a buffer (offset) around a polygon
pub fn create_polygon_buffer(polygon: &Polygon<f64>, distance: f64) -> Result<MultiPolygon<f64>> {
    // Catch panics in buffer operations
    match std::panic::catch_unwind(|| create_polygon_buffer_impl(polygon, distance)) {
        Ok(result) => result,
        Err(_) => {
            // If buffer operation panics, return empty result for insets or original for outsets
            if distance < 0.0 {
                Ok(MultiPolygon::new(vec![]))
            } else {
                Ok(MultiPolygon::new(vec![polygon.clone()]))
            }
        }
    }
}

fn create_polygon_buffer_impl(polygon: &Polygon<f64>, distance: f64) -> Result<MultiPolygon<f64>> {
    if distance == 0.0 {
        return Ok(MultiPolygon::new(vec![polygon.clone()]));
    }
    
    // Clean and prepare the polygon before buffering to prevent buffer bugs
    let cleaned_polygon = prepare_polygon_for_buffer(polygon)?;
    
    // Use geo::Buffer for proper uniform offsetting
    let buffered = cleaned_polygon.buffer(distance);
    Ok(buffered)
}

/// Prepare polygon for buffer operation by cleaning geometry
fn prepare_polygon_for_buffer(polygon: &Polygon<f64>) -> Result<Polygon<f64>> {
    // First, clean using boolean operations to resolve any issues
    let cleaned = clean_polygon(polygon)?;
    
    // If cleaning resulted in multiple polygons, take the largest one
    let main_polygon = if cleaned.0.is_empty() {
        return Err(anyhow::anyhow!("Polygon cleaning resulted in empty geometry"));
    } else if cleaned.0.len() == 1 {
        cleaned.0.into_iter().next().unwrap()
    } else {
        // Take the largest polygon
        cleaned.0
            .into_iter()
            .max_by(|a, b| a.unsigned_area().partial_cmp(&b.unsigned_area()).unwrap())
            .unwrap()
    };
    
    // Simplify the polygon to remove tiny segments that might cause numerical issues
    let simplified = main_polygon.simplify(1e-6);
    
    // Remove duplicate consecutive points and very close points
    let coords: Vec<Coord<f64>> = simplified.exterior()
        .coords()
        .fold(Vec::new(), |mut acc, coord| {
            if let Some(last) = acc.last() {
                let dist_sq = (coord.x - last.x).powi(2) + (coord.y - last.y).powi(2);
                if dist_sq > 1e-20 {  // Only add if not too close to previous point
                    acc.push(*coord);
                }
            } else {
                acc.push(*coord);
            }
            acc
        });
    
    // Ensure we have enough points and close the polygon
    if coords.len() < 3 {
        return Err(anyhow::anyhow!("Polygon has too few vertices after cleaning"));
    }
    
    let mut final_coords = coords;
    if final_coords.first() != final_coords.last() {
        final_coords.push(final_coords[0]);
    }
    
    let cleaned_exterior = LineString::new(final_coords);
    let final_polygon = Polygon::new(cleaned_exterior, vec![]);
    
    // Final validation
    if final_polygon.unsigned_area() < 1e-2 {
        return Err(anyhow::anyhow!("Polygon area too small after cleaning"));
    }
    
    Ok(final_polygon)
}