use pyo3::prelude::*;
use geo::{Coord, LineString, MultiLineString, MultiPolygon, Polygon};
use crate::fill_patterns::generate_concentric_fill_concurrent;
use anyhow::Result;

/// Convert Python coordinates to geo types
fn coords_to_polygon(coords: Vec<Vec<f64>>) -> Result<Polygon<f64>, anyhow::Error> {
    if coords.is_empty() {
        return Err(anyhow::anyhow!("Empty coordinates"));
    }
    
    let exterior_coords: Vec<Coord<f64>> = coords[0]
        .chunks(2)
        .map(|chunk| Coord {
            x: chunk[0],
            y: chunk[1],
        })
        .collect();
    
    let exterior = LineString::new(exterior_coords);
    
    // Handle holes if present
    let mut holes = Vec::new();
    for hole_coords in coords.iter().skip(1) {
        let hole_coord_vec: Vec<Coord<f64>> = hole_coords
            .chunks(2)
            .map(|chunk| Coord {
                x: chunk[0],
                y: chunk[1],
            })
            .collect();
        holes.push(LineString::new(hole_coord_vec));
    }
    
    Ok(Polygon::new(exterior, holes))
}

/// Convert MultiLineString back to Python format
fn multilinestring_to_python(py: Python, lines: &MultiLineString<f64>) -> PyResult<Py<PyAny>> {
    let mut result = Vec::new();
    
    for line in &lines.0 {
        let mut line_coords = Vec::new();
        for coord in line.coords() {
            line_coords.push(coord.x);
            line_coords.push(coord.y);
        }
        result.push(line_coords);
    }
    
    Ok(result.into_pyobject(py)?.unbind())
}

/// Main function to generate fill patterns - exposed to Python
#[pyfunction]
pub fn generate_fill_patterns(
    py: Python,
    polygons: Vec<Vec<Vec<f64>>>,
    pen_width: f64,
    _threads: Option<usize>, // Keep for backward compatibility but ignore
    fill_holes: Option<bool>,
    discard_hole_borders: Option<bool>,
    discard_exterior: Option<bool>,
    reverse_ring_draw_order: Option<bool>,
) -> PyResult<Py<PyAny>> {
    let mut all_polygons = Vec::new();
    
    // Convert all input polygons
    for poly_coords in polygons {
        match coords_to_polygon(poly_coords) {
            Ok(polygon) => all_polygons.push(polygon),
            Err(e) => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Failed to parse polygon: {}", e
                )));
            }
        }
    }
    
    if all_polygons.is_empty() {
        return Ok(Vec::<Vec<f64>>::new().into_pyobject(py)?.unbind());
    }
    
    // Create multipolygon
    let multipolygon = MultiPolygon::new(all_polygons);
    
    // Generate fill patterns using concurrent processing with default thread count
    let result = generate_concentric_fill_concurrent(
        &multipolygon, 
        pen_width, 
        None, // Always use default parallel behavior
        fill_holes.unwrap_or(false), 
        discard_hole_borders.unwrap_or(false),
        discard_exterior.unwrap_or(false),
        reverse_ring_draw_order.unwrap_or(false)
    );
    
    match result {
        Ok(lines) => multilinestring_to_python(py, &lines),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
            "Failed to generate fill patterns: {}", e
        ))),
    }
}

/// Create the main vpype extension
#[pyfunction]
pub fn create_vpype_extension(_py: Python) -> PyResult<String> {
    // Simple function that returns info about the extension
    Ok("vpype-cfill extension loaded successfully".to_string())
}
