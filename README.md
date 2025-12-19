# vpype-brush

A [vpype](https://github.com/abey79/vpype) plugin that adds Z-axis pressure control for brush plotting.

> **BETA** - May have bugs. Please report issues.

## Installation

```bash
git clone https://github.com/TarGz/vpype-brush.git
cd vpype-brush
pip install -e .
```

## Quick Start

```bash
# Basic usage
vpype read input.svg brush -o output.gcode

# With SVG color-based pressure
vpype read input.svg brush --z-from-svg input.svg --z-up -8 --z-down -20 -o output.gcode
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--z-up` | -3.0 | Z for light pressure (mm) |
| `--z-down` | -20.0 | Z for full pressure (mm) |
| `--z-travel` | (z-up) | Z for travel moves (mm) |
| `--z-from-svg` | none | SVG file for spatial color lookup |
| `--z-from-color` | false | Use layer color for Z |
| `--z-smooth-distance` | 5.0 | Gaussian smoothing radius (mm) |
| `--press-distance` | 50.0 | Press-down distance at stroke start (mm) |
| `--lift-distance` | 50.0 | Lift-up distance at stroke end (mm) |
| `--merge-tolerance` | 1.0 | Merge lines within this distance (mm, 0=disable) |
| `--segment-length` | 2.0 | Subdivision length (mm) |
| `--feed-rate` | 1000.0 | Drawing speed (mm/min) |
| `--unit` | mm | Output units |

## Z Pressure Modes

### Position-based (default)
Press down at start, lift at end:
```bash
vpype read input.svg brush --z-up -3 --z-down -20 -o output.gcode
```

### SVG Spatial
Z varies along stroke based on SVG colors (black=down, white=up):
```bash
vpype read input.svg brush --z-from-svg input.svg --z-travel -3 --z-up -8 --z-down -20 -o output.gcode
```

### Layer Color
Uniform Z per layer based on layer color:
```bash
vpype read input.svg brush --z-from-color --z-up -3 --z-down -20 -o output.gcode
```

## Requirements

- Python 3.9+
- vpype 1.9+

## License

MIT

## Changelog

### v0.4.4
- Simplified README documentation

### v0.4.3
- Fixed diagonal lines with spiral patterns in `--z-from-svg` mode
- Line merge now uses Euclidean distance

### v0.4.2
- Added CSS class stroke color support (Adobe Illustrator SVGs)
- Fixed coordinate offset bug in merged strokes

### v0.4.1
- Added progress indicators for long operations

### v0.4.0
- Added `--z-travel` option for separate travel height

### v0.3.1
- Added `--z-from-svg` spatial mode
- Added `--z-smooth-distance` and `--merge-tolerance`
- Removed press/lift envelope in SVG spatial mode

### v0.2.3
- Added `--z-from-color` option

### v0.2.2
- Fixed short stroke behavior (proportional scaling)

### v0.2.1
- Added `--feed-rate` option

### v0.2.0
- Fixed coordinate scaling
- Added `--unit` option

### v0.1.2
- Initial public beta release

### v0.1.1
- Removed gwrite references

### v0.1.0
- Initial release
