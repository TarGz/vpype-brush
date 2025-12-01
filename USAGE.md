# vpype-brush Usage Guide

## Installation

The plugin is already installed in the virtual environment. To use it:

```bash
cd /Users/jterraz/Documents/GIT/vpype-brush
source vpype_brush/bin/activate
```

## Basic Usage

```bash
vpype read input.svg brush -o output.gcode
```

## With Custom Parameters

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

## Parameters Explained

- `--z-up` (default: -3.0): Z height when pen is up (start/end of stroke)
- `--z-down` (default: -20.0): Z height at full brush pressure (middle of stroke)
- `--press-distance` (default: 50.0): Distance (mm) over which to press down at start
- `--lift-distance` (default: 50.0): Distance (mm) over which to lift up at end
- `--segment-length` (default: 2.0): How finely to subdivide lines (smaller = smoother but larger files)

## How It Works

1. **Subdivides all lines** into small segments (~2mm by default)
2. **Calculates Z for each point** based on position in stroke:
   - **Phase 1** (first 50mm): Gradually press from z_up → z_down
   - **Phase 2** (middle): Stay at constant z_down pressure
   - **Phase 3** (last 50mm): Gradually lift from z_down → z_up
3. **Outputs G-code** directly with X, Y, and Z coordinates

## Advantages Over Post-Processing

✅ Works with single straight lines (subdivides them automatically)
✅ Reaches full depth properly on all strokes
✅ Distance-based (not time-based) for consistent behavior
✅ No fragile regex parsing
✅ Integrates directly into vpype pipeline

## Tips

- **Shorter strokes**: If stroke is shorter than press_distance + lift_distance, it will smoothly transition from up to down to up with no constant pressure phase
- **Finer control**: Reduce `--segment-length` to 1.0 for ultra-smooth transitions (but larger files)
- **Adjust pressure curve**: Change press_distance and lift_distance independently for asymmetric pressure curves

## Comparison with Old Script

| Feature | Old Script | vpype-brush Plugin |
|---------|-----------|-------------------|
| Single straight lines | ❌ Only middle Z | ✅ Full transition |
| Long strokes | ⚠️ Incomplete Z | ✅ Complete Z transition |
| Architecture | Post-process G-code | Geometry-level |
| Parameter model | Time-based | Distance-based |
| Integration | Separate script | vpype pipeline |

## Examples

### Natural brush stroke (slow press, quick lift):
```bash
vpype read art.svg \
  brush --press-distance 60 --lift-distance 30 \
  -o output.gcode
```

### Light touch (small Z range):
```bash
vpype read sketch.svg \
  brush --z-up -3 --z-down -10 \
  -o output.gcode
```

### Heavy pressure (large Z range):
```bash
vpype read bold.svg \
  brush --z-up -5 --z-down -25 --press-distance 80 \
  -o output.gcode
```

## Deactivating Virtual Environment

When done:
```bash
deactivate
```
