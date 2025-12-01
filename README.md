# vpype-brush

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **BETA VERSION** - This plugin is currently in beta. While functional, it may have bugs or undergo API changes. Please report any issues you encounter.

A [vpype](https://github.com/abey79/vpype) plugin that adds gradual Z-axis pressure variation to brush strokes for natural painting effects with pen plotters and drawing machines.

## Features

- **Distance-based pressure control**: Smoothly press down at stroke start and lift at stroke end
- **Automatic line subdivision**: Converts long straight lines into smooth pressure curves
- **Direct G-code output**: Generates 3D toolpaths (X, Y, Z) directly from vector artwork
- **Customizable parameters**: Full control over Z heights, press/lift distances, and segment length
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
| `--z-up` | -3.0 | Z height when pen is up (start/end of stroke) in mm |
| `--z-down` | -20.0 | Z height at full brush pressure (middle of stroke) in mm |
| `--press-distance` | 50.0 | Distance over which to press down at start in mm |
| `--lift-distance` | 50.0 | Distance over which to lift up at end in mm |
| `--segment-length` | 2.0 | Subdivision segment length for smooth curves in mm |
| `--feed-rate` | 1000.0 | Drawing feed rate in mm/min (or in/min if using inches) |
| `--unit` | mm | Output units (mm, cm, in, etc.) |

## How It Works

The plugin processes your vector artwork in three steps:

1. **Subdivision**: All lines are subdivided into small segments (default 2mm) for smooth Z transitions
2. **Z-axis Calculation**: Each point gets a Z coordinate based on its position in the stroke:
   - **Press phase**: First `press-distance` mm - gradually press from `z-up` → `z-down`
   - **Constant pressure**: Middle section - maintain `z-down` for consistent brush contact
   - **Lift phase**: Last `lift-distance` mm - gradually lift from `z-down` → `z-up`
3. **G-code Generation**: Outputs standard G-code with X, Y, and Z coordinates

### Pressure Curve Example

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

### v0.2.2 (Current - Beta)
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
