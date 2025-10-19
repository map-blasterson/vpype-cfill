# vpype-cfill

A [vpype](https://github.com/abey79/vpype) extension for generating concentric fill patterns inside polygons.

![Screenshot comparing input solid fill and resulting concentric fill](https://raw.githubusercontent.com/map-blasterson/vpype-cfill/main/doc/demo.png)

## Installation

```bash
python -m venv env
. env/bin/activate
./build.sh
```

## Usage

### Basic Usage

```bash
# Generate concentric fill for a rectangle with 2.0 unit spacing
vpype rect 0 0 100 100 cfill --pen-width 2.0mm show

# Process an SVG file
vpype read input.svg cfill -pw 0.125in write output.svg
```

### Command Line Arguments

- `-pw, --pen-width FLOAT`: Width of pen/spacing between concentric lines (default: 1.0)
- `'-fh', '--fill-holes'`: Fill holes in polygons instead of preserving them
- `'-dh', '--discard-hole-borders'`: Discard original hole border geometry (independent of --fill-holes)
- `'-de', '--discard-exterior'`: Discard original exterior geometry. Combine with --discard-hole-borders to generate only fill.
- `'-r', '--reverse-ring-draw-order'`: Draw inner-most ring first, then move outwards to edges. (avoid ink pools)

### Examples

```bash
# Concentric fill
vpype rect 0 0 50 50 cfill --pen-width 0.5mm show


# Process complex shapes from SVG
vpype read complex_shape.svg linesort cfill -pw 1.2mm linesimplify --tolerance 0.05mmlinesimplify --tolerance 0.05mm  write filled_output.svg
```

## License

MIT License - see LICENSE file for details.
