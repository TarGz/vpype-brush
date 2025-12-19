# vpype-brush

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **BETA VERSION** - This plugin is currently in beta. While functional, it may have bugs or undergo API changes. Please report any issues you encounter.

A [vpype](https://github.com/abey79/vpype) plugin that adds gradual Z-axis pressure variation to brush strokes for natural painting effects with pen plotters and drawing machines.

## Features

- **Three Z pressure modes**:
  - **Position-based**: Classic brush stroke with press-down at start, lift at end
  - **Layer color**: Uniform Z pressure per layer based on layer color
  - **SVG spatial**: Varying pressure within strokes based on original SVG colors at each point
- **Gaussian smoothing**: Smooth Z transitions for natural brush strokes
- **Automatic line merging**: Reduces pen lifts by merging connected path segments
- **Automatic line subdivision**: Converts long straight lines into smooth pressure curves
- **Direct G-code output**: Generates 3D toolpaths (X, Y, Z) directly from vector artwork
- **Customizable parameters**: Full control over Z heights, smoothing, and segment length
- **Pipeline integration**: Works seamlessly within vpype's processing pipeline

## Installation

### From Source (Current)

```bash
git clone https://github.com/TarGz/vpype-brush.git
cd vpype-brush
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install vpype-brush
```

## Quick Start

Basic usage with default parameters:

```bash
vpype read input.svg brush -o output.gcode
```

With custom parameters:

```bash
vpype read input.svg \
  brush \
    --z-up -5 \
    --z-down -18 \
    --press-distance 50 \
    --lift-distance 50 \
    --segment-length 2 \
  -o output.gcode
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--z-up` | -3.0 | Z height for light pressure (white colors) in mm |
| `--z-down` | -20.0 | Z height for full pressure (black colors) in mm |
| `--z-travel` | (z-up) | Z height for traveling between strokes in mm (defaults to z-up) |
| `--z-from-color` | false | Set Z from layer color (uniform per layer) |
| `--z-from-svg` | none | Path to SVG for spatial color lookup at each point |
| `--z-smooth-distance` | 5.0 | Gaussian smoothing radius for Z transitions in mm |
| `--press-distance` | 50.0 | Distance to press down at start (position-based mode) in mm |
| `--lift-distance` | 50.0 | Distance to lift up at end (position-based mode) in mm |
| `--merge-tolerance` | 1.0 | Distance tolerance for merging connected lines in mm (0 to disable) |
| `--segment-length` | 2.0 | Subdivision segment length for smooth curves in mm |
| `--feed-rate` | 1000.0 | Drawing feed rate in mm/min (or in/min if using inches) |
| `--unit` | mm | Output units (mm, cm, in, etc.) |

## Z Pressure Modes

### 1. Position-based Mode (default)

Classic brush stroke behavior. Z starts at `z-up`, presses down to `z-down` over the `press-distance`, stays at `z-down` during the stroke, then lifts back to `z-up` over the `lift-distance`.

```bash
vpype read input.svg brush --z-up -3 --z-down -20 --press-distance 50 --lift-distance 50 -o output.gcode
```

```
        Travel   Downward   Constant   Upward   Travel
         (up)     Phase      height    Phase     (up)
           |        |           |         |         |
           v        v           v         v         v

Z-up   -------------+                             +-----
                    \                            /
                     \                          /
                      \                        /
                       \                      /
                        \                    /
Z-down                   \__________________/
```

### 2. Layer Color Mode

Uses the color assigned to each vpype layer to determine Z pressure. Black layers get full pressure (`z-down`), white layers get light pressure (`z-up`), gray layers get intermediate values. Still uses press/lift envelope at stroke boundaries.

```bash
vpype read grayscale.svg brush --z-from-color --z-up -3 --z-down -20 -o output.gcode
```

### 3. SVG Spatial Mode

Looks up the color from the original SVG file at each point along the stroke. This allows varying pressure *within* a single stroke based on the color at each position. Uses Gaussian smoothing for smooth transitions. No press/lift envelope - the SVG encodes the full pressure curve.

```bash
vpype read artwork.svg brush --z-from-svg artwork.svg --z-travel -3 --z-up -8 --z-down -20 --z-smooth-distance 5 -o output.gcode
```

Note: `--z-travel` sets a safe height for moving between strokes (pen fully lifted), while `--z-up` defines the lightest drawing pressure (for white colors). If not specified, `--z-travel` defaults to `--z-up`.

This mode is ideal for:
- Grayscale artwork where color represents pressure/shading
- Images with gradients converted to vector paths
- Pre-processed SVGs with color-encoded pressure information

## How It Works

The plugin processes your vector artwork in these steps:

1. **Line Merging**: Connected path segments are merged to reduce pen lifts (configurable via `--merge-tolerance`)
2. **Subdivision**: All lines are subdivided into small segments (default 2mm) for smooth Z transitions
3. **Z-axis Calculation**: Each point gets a Z coordinate based on the selected mode
4. **Smoothing**: For SVG spatial mode, Gaussian smoothing creates natural pressure transitions
5. **G-code Generation**: Outputs standard G-code with simultaneous X, Y, and Z coordinates

## Usage Tips

### Short Strokes
If a stroke is shorter than `press-distance + lift-distance`, the press and lift distances are automatically scaled proportionally to fit within the stroke length. This ensures smooth pressure transitions without the pen lifting prematurely.

### Fluid 3D Movement
The plugin uses simultaneous XYZ movements for natural, fluid brush strokes. The feed rate applies to the 3D path, creating smooth transitions as the brush presses down and lifts up while drawing.

### Fine Control
Reduce `--segment-length` to 1.0 for ultra-smooth transitions (creates larger G-code files):

```bash
vpype read input.svg brush --segment-length 1.0 -o output.gcode
```

### Asymmetric Pressure Curves
Adjust press and lift distances independently for different start/end behaviors:

```bash
vpype read input.svg brush --press-distance 30 --lift-distance 70 -o output.gcode
```

### Integration with vpype Pipeline

Combine with other vpype commands:

```bash
vpype read input.svg \
  linemerge --tolerance 0.1mm \
  linesort \
  brush --z-up -5 --z-down -20 \
  -o output.gcode
```

## Requirements

- Python 3.9 or higher
- [vpype](https://github.com/abey79/vpype) 1.9 or higher
- click
- numpy
- shapely

## Compatibility

This plugin generates standard G-code with Z-axis control. It should work with most CNC controllers and drawing machines that support 3-axis motion (Grbl, Marlin, etc.).

## Examples

### Light Watercolor Effect
```bash
vpype read artwork.svg brush --z-up -2 --z-down -8 --press-distance 30 -o light.gcode
```

### Heavy Brush Pressure
```bash
vpype read artwork.svg brush --z-up -5 --z-down -25 --press-distance 80 -o heavy.gcode
```

### Quick Sketch Style
```bash
vpype read sketch.svg brush --z-up -3 --z-down -12 --press-distance 20 --lift-distance 20 -o quick.gcode
```

### Layer Color Pressure
Use `--z-from-color` to derive pressure from layer colors. Black layers get full pressure, white layers get light pressure:
```bash
vpype read grayscale-artwork.svg brush --z-from-color --z-up -3 --z-down -20 -o shaded.gcode
```

### SVG Spatial Pressure (Varying Within Strokes)
Use `--z-from-svg` for pressure that varies at each point based on the original SVG colors:
```bash
vpype read gradient-artwork.svg brush --z-from-svg gradient-artwork.svg --z-travel -3 --z-up -8 --z-down -20 --z-smooth-distance 5 -o variable.gcode
```

### Reduce Pen Lifts
Use `--merge-tolerance` to merge connected path segments (reduces pen up/down movements):
```bash
vpype read segmented.svg brush --merge-tolerance 1.0 --z-from-svg segmented.svg -o merged.gcode
```

## Known Issues

- Beta software: May contain bugs or unexpected behavior
- G-code output only (no SVG passthrough yet)
- Assumes Z-axis control is available on your machine

Please report issues at: [GitHub Issues](https://github.com/TarGz/vpype-brush/issues)

## Contributing

Contributions are welcome! This is a beta project and can benefit from:
- Bug reports and fixes
- Documentation improvements
- Feature suggestions
- Code optimizations
- More examples and use cases

## License

MIT License - See LICENSE file for details

## Credits

Created by targz

Built for the [vpype](https://github.com/abey79/vpype) ecosystem by [Abey79](https://github.com/abey79)

## Changelog

### v0.4.0 (Current - Beta)
- **ADDED**: `--z-travel` option for separate travel height between strokes (defaults to z-up for backward compatibility)

### v0.3.1 (Beta)
- **ADDED**: `--z-from-svg` option for spatial color lookup - Z pressure varies within strokes based on original SVG colors
- **ADDED**: `--z-smooth-distance` option for Gaussian smoothing of Z transitions
- **ADDED**: `--merge-tolerance` option to merge connected path segments and reduce pen lifts
- **IMPROVED**: Three distinct Z pressure modes: position-based, layer color, and SVG spatial
- **IMPROVED**: Linear Z transitions instead of exponential smoothing
- **FIXED**: Removed press/lift envelope when using SVG spatial mode (SVG encodes full pressure curve)

### v0.2.3 (Beta)
- **ADDED**: `--z-from-color` option to derive Z pressure from line colors (black=full pressure, white=light, grays=progressive)
- New `color_to_grayscale()` function using standard luminance formula

### v0.2.2 (Beta)
- **FIXED**: Short stroke behavior - press/lift distances now scale proportionally for strokes shorter than press+lift distance
- Improved fluid 3D movement with simultaneous XYZ motion

### v0.2.1 (Beta)
- **FIXED**: Added missing feed rate parameter (fixes Grbl error 22)
- **ADDED**: `--feed-rate` option for drawing speed control (default: 1000 mm/min)

### v0.2.0 (Beta)
- **FIXED**: Coordinate scaling issue - outputs now respect actual document dimensions
- **ADDED**: `--unit` option for output unit control (mm, cm, in, etc.)
- Proper unit conversion from vpype's internal units to target units
- G-code header now adapts based on output unit (G20/G21)

### v0.1.2 (Beta)
- Updated documentation with comprehensive README
- Added MIT License
- Cleaned up repository structure
- Removed deprecated documentation files
- Ready for public beta release

### v0.1.1 (Beta)
- Removed gwrite references to avoid conflict with vpype-gcode plugin
- Beta release for testing and feedback

### v0.1.0 (Beta)
- Initial beta release
- Core brush pressure functionality
- Configurable Z-axis parameters
- Distance-based press/lift curves
