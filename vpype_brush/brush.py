"""
vpype-brush: Add gradual Z-axis pressure variation for brush plotting

This plugin subdivides line segments and adds Z coordinates to create
natural brush strokes with gradual pressure transitions.
"""

import copy
import click
import numpy as np
import vpype as vp
import vpype_cli
from shapely.geometry import LineString


def subdivide_line(line, segment_length):
    """
    Subdivide a vpype line (numpy array of complex numbers) into smaller segments.

    Args:
        line: A numpy array of complex numbers (vpype format: real=x, imag=y)
        segment_length: Target length for each segment (mm)

    Returns:
        List of (x, y) tuples including all original and interpolated points
    """
    if len(line) < 2:
        return [(z.real, z.imag) for z in line]

    result_points = [(line[0].real, line[0].imag)]

    for i in range(len(line) - 1):
        x1, y1 = line[i].real, line[i].imag
        x2, y2 = line[i + 1].real, line[i + 1].imag

        # Calculate distance between consecutive points
        dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # Calculate number of segments needed
        num_segments = max(1, int(np.ceil(dist / segment_length)))

        # Add intermediate points (skip the first point as it's already added)
        for j in range(1, num_segments + 1):
            t = j / num_segments
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            result_points.append((x, y))

    return result_points


def calculate_z(distance_from_start, total_distance, z_up, z_down, press_distance, lift_distance):
    """
    Calculate Z value based on position within stroke.

    Args:
        distance_from_start: Cumulative distance from start of stroke
        total_distance: Total stroke length
        z_up: Z height at start/end
        z_down: Z height at full pressure
        press_distance: Distance over which to press down
        lift_distance: Distance over which to lift up

    Returns:
        Z value for this point
    """
    remaining_distance = total_distance - distance_from_start

    # Phase 1: Pressing down at start
    if distance_from_start <= press_distance:
        progress = distance_from_start / press_distance if press_distance > 0 else 1.0
        return z_up + (z_down - z_up) * progress

    # Phase 3: Lifting up at end
    elif remaining_distance <= lift_distance:
        progress = (lift_distance - remaining_distance) / lift_distance if lift_distance > 0 else 1.0
        return z_down + (z_up - z_down) * progress

    # Phase 2: Constant pressure (middle)
    else:
        return z_down


@click.command()
@click.option('--z-up', default=-3.0, type=float, help='Z height at stroke start/end (mm)')
@click.option('--z-down', default=-20.0, type=float, help='Z height during stroke (full pressure, mm)')
@click.option('--press-distance', default=50.0, type=float, help='Distance to press down at start (mm)')
@click.option('--lift-distance', default=50.0, type=float, help='Distance to lift up at end (mm)')
@click.option('--segment-length', default=2.0, type=float, help='Subdivision segment length (mm)')
@click.option('--feed-rate', default=1000.0, type=float, help='Drawing feed rate (mm/min or in/min)')
@click.option('--unit', default='mm', type=str, help='Output units (mm, cm, in, etc.)')
@click.option('--output', '-o', type=click.Path(), help='Output G-code file path')
@vpype_cli.global_processor
def brush(document, z_up, z_down, press_distance, lift_distance, segment_length, feed_rate, unit, output):
    """
    Add gradual Z-axis pressure variation for brush plotting.

    This command subdivides all line segments and adds Z coordinates to create
    natural brush strokes with gradual pressure transitions at the start and end.

    Example:
        vpype read input.svg brush --z-up -5 --z-down -20 --output output.gcode
    """

    if output:
        # Direct G-code output mode
        generate_gcode(document, z_up, z_down, press_distance, lift_distance, segment_length, feed_rate, unit, output)
        return document
    else:
        # Process geometry (subdivide lines with Z variations)
        process_geometry(document, z_up, z_down, press_distance, lift_distance, segment_length)
        return document


def process_geometry(document, z_up, z_down, press_distance, lift_distance, segment_length):
    """
    Process all lines in the document and add Z coordinate metadata.
    """
    for layer_id in document.layers:
        lc = document.layers[layer_id]
        new_lines = []

        for line in lc:
            # Subdivide the line
            points_2d = subdivide_line(line, segment_length)

            if len(points_2d) < 2:
                new_lines.append(line)
                continue

            # Calculate cumulative distances
            cumulative_distances = [0.0]
            for i in range(1, len(points_2d)):
                x1, y1 = points_2d[i-1]
                x2, y2 = points_2d[i]
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                cumulative_distances.append(cumulative_distances[-1] + dist)

            total_distance = cumulative_distances[-1]

            # Calculate Z values for each point
            points_3d = []
            for i, (x, y) in enumerate(points_2d):
                z = calculate_z(
                    cumulative_distances[i],
                    total_distance,
                    z_up,
                    z_down,
                    press_distance,
                    lift_distance
                )
                # Store as complex number: real=x, imag=y
                # We'll store Z in metadata
                points_3d.append(complex(x, y))

            # Create new line with subdivided points
            new_line = np.array(points_3d)

            # Note: Z values are calculated but not stored in vpype line metadata.
            # Use --output flag for direct G-code generation with Z variations.
            new_lines.append(new_line)

        document.layers[layer_id] = vp.LineCollection(new_lines)


def generate_gcode(document, z_up, z_down, press_distance, lift_distance, segment_length, feed_rate, unit, output_path):
    """
    Generate G-code directly with Z variations.
    Properly scales coordinates from vpype's internal units to the target unit.
    """
    # Get the unit scale factor (converts from vpype internal units to target unit)
    # vpype uses CSS pixels internally (1px = 1/96 inch = 0.2645833mm)
    unit_scale = vp.convert_length(unit)

    gcode_lines = []

    # G-code header
    gcode_lines.append("; Generated by vpype-brush")

    # Set G-code unit command based on target unit
    if unit == "mm":
        gcode_lines.append("G21 ; Set units to millimeters")
    elif unit == "in":
        gcode_lines.append("G20 ; Set units to inches")
    else:
        # For other units (cm, etc.), default to mm with a note
        gcode_lines.append(f"G21 ; Set units to millimeters (output in {unit})")

    gcode_lines.append("G90 ; Use absolute coordinates")
    gcode_lines.append(f"G0 Z{z_up:.4f} ; Pen up")
    gcode_lines.append(f"F{feed_rate:.1f} ; Set feed rate")
    gcode_lines.append("")

    # Process each layer
    for layer_id in sorted(document.layers.keys()):
        lc = document.layers[layer_id]
        gcode_lines.append(f"; Layer {layer_id}")

        for line in lc:
            # Subdivide the line
            points_2d = subdivide_line(line, segment_length)

            if len(points_2d) < 2:
                continue

            # Calculate cumulative distances
            cumulative_distances = [0.0]
            for i in range(1, len(points_2d)):
                x1, y1 = points_2d[i-1]
                x2, y2 = points_2d[i]
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                cumulative_distances.append(cumulative_distances[-1] + dist)

            total_distance = cumulative_distances[-1]

            # Move to start position (pen up)
            x_start, y_start = points_2d[0]
            # Convert from vpype internal units to target unit
            x_start_scaled = x_start / unit_scale
            y_start_scaled = y_start / unit_scale
            gcode_lines.append(f"G0 X{x_start_scaled:.4f} Y{y_start_scaled:.4f}")

            # Draw the stroke with Z variation
            for i, (x, y) in enumerate(points_2d):
                z = calculate_z(
                    cumulative_distances[i],
                    total_distance,
                    z_up,
                    z_down,
                    press_distance,
                    lift_distance
                )
                # Convert from vpype internal units to target unit
                x_scaled = x / unit_scale
                y_scaled = y / unit_scale
                gcode_lines.append(f"G1 X{x_scaled:.4f} Y{y_scaled:.4f} Z{z:.4f}")

            # Pen up
            gcode_lines.append(f"G0 Z{z_up:.4f}")
            gcode_lines.append("")

    # G-code footer
    gcode_lines.append("; End of program")
    gcode_lines.append("M2")

    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(gcode_lines))

    click.echo(f"G-code written to: {output_path}")
