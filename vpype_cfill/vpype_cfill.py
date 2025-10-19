import click
import numpy as np
from typing import Iterable, List, Tuple, Optional
import vpype as vp
from vpype import LineCollection
import vpype_cli

try:
    from . import vpype_cfill_rust
except ImportError:
    # Fallback if Rust extension is not available
    vpype_cfill_rust = None


def polygon_to_coords(polygon) -> List[List[float]]:
    """Convert a shapely polygon to coordinate list format."""
    coords = []

    # Exterior ring
    if hasattr(polygon, "exterior"):
        ext_coords = list(polygon.exterior.coords)
        flat_coords = []
        for x, y in ext_coords:
            flat_coords.extend([x, y])
        coords.append(flat_coords)

        # Interior rings (holes)
        for interior in polygon.interiors:
            int_coords = list(interior.coords)
            flat_coords = []
            for x, y in int_coords:
                flat_coords.extend([x, y])
            coords.append(flat_coords)

    return coords


def coords_to_line_collection(coords_list) -> LineCollection:
    """Convert coordinate list back to vpype LineCollection."""
    lc = LineCollection()

    for line_coords in coords_list:
        if len(line_coords) >= 4:  # At least 2 points (x,y pairs)
            # Convert flat list to numpy array of points
            points = np.array(line_coords).reshape(-1, 2)
            # Convert to complex numbers (vpype format)
            complex_line = points[:, 0] + 1j * points[:, 1]
            lc.append(complex_line)

    return lc


@click.command()
@click.option(
    "-pw",
    "--pen-width",
    type=vpype_cli.LengthType(),
    default="1.0",
    help="Width of pen/spacing between concentric lines (default: 1.0)",
)
@click.option(
    "-fh",
    "--fill-holes",
    is_flag=True,
    default=False,
    help="Fill holes in polygons instead of preserving them",
)
@click.option(
    "-dh",
    "--discard-hole-borders",
    is_flag=True,
    default=False,
    help="Discard original hole border geometry (independent of --fill-holes)",
)
@click.option(
    "-de",
    "--discard-exterior",
    is_flag=True,
    default=False,
    help="Discard original exterior geometry. Combine with --discard-hole-borders to generate only fill.",
)
@click.option(
    "-r",
    "--reverse-ring-draw-order",
    is_flag=True,
    default=False,
    help="Draw inner-most ring first, then move outwards to edges. (avoid ink pools)",
)
@vpype_cli.layer_processor
def cfill(
    lines: LineCollection,
    pen_width: float,
    fill_holes: bool,
    discard_hole_borders: bool,
    discard_exterior: bool,
    reverse_ring_draw_order: bool,
) -> LineCollection:
    """
    Generate concentric fill patterns inside polygons.

    Examples:
        vpype read input.svg cfill --pen-width 2.0 write output.svg
        vpype rect 0 0 100 100 cfill -pw 1.5 show
    """

    if len(lines) == 0:
        return LineCollection()

    # Convert lines to polygons
    polygons = []
    for line in lines:
        if len(line) > 2:
            # Check if the line is closed (or close it)
            if abs(line[0] - line[-1]) > 1e-6:
                line = np.append(line, line[0])

            # Convert complex line to real coordinates
            coords = []
            for point in line:
                coords.extend([point.real, point.imag])

            if len(coords) >= 6:  # At least 3 points for a polygon
                polygons.append([coords])

    if not polygons:
        click.echo("Warning: No valid polygons found in input")
        return LineCollection()

    if vpype_cfill_rust is not None:
        try:
            result_coords = vpype_cfill_rust.generate_fill_patterns(
                polygons,
                pen_width,
                None,
                fill_holes,
                discard_hole_borders,
                discard_exterior,
                reverse_ring_draw_order,
            )
            return coords_to_line_collection(result_coords)
        except Exception as e:
            click.echo(f"Rust implementation failed: {type(e).__name__}: {e}")
            return LineCollection()

    # If Rust extension not available
    click.echo("Rust extension not available")
    return LineCollection()
