# vpype-brush

A vpype plugin that adds gradual Z-axis pressure variation to brush strokes for natural painting effects.

## Installation

```bash
pip install -e .
```

## Usage

```bash
vpype read input.svg brush --z-up -5 --z-down -20 --press-distance 50 --lift-distance 50 --output output.gcode
```

## Parameters

- `--z-up`: Z height at stroke start/end (default: -3.0 mm)
- `--z-down`: Z height during stroke at full pressure (default: -20.0 mm)
- `--press-distance`: Distance to press down at start (default: 50.0 mm)
- `--lift-distance`: Distance to lift up at end (default: 50.0 mm)
- `--segment-length`: Subdivision segment length (default: 2.0 mm)
