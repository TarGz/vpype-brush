"""
vpype-brush: Add gradual Z-axis pressure variation for brush plotting

This plugin subdivides line segments and adds Z coordinates to create
natural brush strokes with gradual pressure transitions.
"""

import click
import numpy as np
import vpype as vp
import vpype_cli
import xml.etree.ElementTree as ET
import re
import math
from collections import defaultdict


# =============================================================================
# SVG Color Spatial Index (for --z-from-svg option)
# =============================================================================

class SpatialColorIndex:
    """Grid-based spatial index for fast color lookups from SVG."""

    def __init__(self, cell_size=5.0):
        self.cell_size = cell_size
        self.grid = defaultdict(list)
        self.segments = []  # List of (start_point, end_point, grayscale)
        self.min_x = float('inf')
        self.min_y = float('inf')
        self.max_x = float('-inf')
        self.max_y = float('-inf')

    def _cell_key(self, x, y):
        return (int(x / self.cell_size), int(y / self.cell_size))

    def add_segment(self, p1, p2, grayscale):
        """Add a line segment and update bounds."""
        # Track bounds
        self.min_x = min(self.min_x, p1[0], p2[0])
        self.min_y = min(self.min_y, p1[1], p2[1])
        self.max_x = max(self.max_x, p1[0], p2[0])
        self.max_y = max(self.max_y, p1[1], p2[1])

        segment_id = len(self.segments)
        self.segments.append((p1, p2, grayscale))

        min_x = min(p1[0], p2[0])
        max_x = max(p1[0], p2[0])
        min_y = min(p1[1], p2[1])
        max_y = max(p1[1], p2[1])

        for cx in range(int(min_x / self.cell_size) - 1, int(max_x / self.cell_size) + 2):
            for cy in range(int(min_y / self.cell_size) - 1, int(max_y / self.cell_size) + 2):
                self.grid[(cx, cy)].append(segment_id)

    def find_grayscale_at(self, x, y, search_radius=10.0):
        """Find the grayscale value of the nearest segment to point (x, y)."""
        cell = self._cell_key(x, y)
        search_cells = int(search_radius / self.cell_size) + 1

        min_dist = float('inf')
        nearest_gray = 0.5

        checked = set()

        for dx in range(-search_cells, search_cells + 1):
            for dy in range(-search_cells, search_cells + 1):
                for seg_id in self.grid.get((cell[0] + dx, cell[1] + dy), []):
                    if seg_id in checked:
                        continue
                    checked.add(seg_id)

                    p1, p2, grayscale = self.segments[seg_id]
                    dist = self._point_to_segment_dist(x, y, p1, p2)

                    if dist < min_dist:
                        min_dist = dist
                        nearest_gray = grayscale

        return nearest_gray

    def _point_to_segment_dist(self, px, py, p1, p2):
        """Calculate distance from point to line segment."""
        x1, y1 = p1
        x2, y2 = p2

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)


def parse_svg_color(color_str):
    """Parse a color string and return RGB tuple (0-255)."""
    if color_str is None or color_str == 'none':
        return None

    color_str = color_str.strip().lower()

    # rgb(r,g,b) format
    rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))

    # #RRGGBB format
    hex6_match = re.match(r'#([0-9a-f]{6})', color_str)
    if hex6_match:
        hex_val = hex6_match.group(1)
        return (int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16))

    # #RGB format
    hex3_match = re.match(r'#([0-9a-f]{3})', color_str)
    if hex3_match:
        hex_val = hex3_match.group(1)
        return (int(hex_val[0]*2, 16), int(hex_val[1]*2, 16), int(hex_val[2]*2, 16))

    named_colors = {
        'black': (0, 0, 0), 'white': (255, 255, 255),
        'red': (255, 0, 0), 'green': (0, 128, 0), 'blue': (0, 0, 255),
        'gray': (128, 128, 128), 'grey': (128, 128, 128),
    }
    return named_colors.get(color_str)


def rgb_to_grayscale_value(rgb):
    """Convert RGB tuple to grayscale value (0.0-1.0)."""
    if rgb is None:
        return 0.5
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def get_svg_element_stroke(element, inherited_stroke=None):
    """Get the stroke color of an SVG element."""
    stroke = element.get('stroke')
    if stroke and stroke != 'none':
        return stroke

    style = element.get('style', '')
    style_match = re.search(r'stroke:\s*([^;]+)', style)
    if style_match:
        stroke = style_match.group(1).strip()
        if stroke and stroke != 'none':
            return stroke

    return inherited_stroke


def parse_svg_path_d(d_attr):
    """Parse SVG path 'd' attribute and return list of points."""
    if not d_attr:
        return []

    points = []
    current_x, current_y = 0, 0
    start_x, start_y = 0, 0

    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d_attr)

    i = 0
    current_cmd = None

    while i < len(tokens):
        token = tokens[i]

        if token.isalpha():
            current_cmd = token
            i += 1
            continue

        if current_cmd is None:
            i += 1
            continue

        cmd_upper = current_cmd.upper()
        is_relative = current_cmd.islower()

        try:
            if cmd_upper == 'M':
                x = float(tokens[i])
                y = float(tokens[i + 1]) if i + 1 < len(tokens) else 0
                if is_relative:
                    current_x += x
                    current_y += y
                else:
                    current_x, current_y = x, y
                start_x, start_y = current_x, current_y
                points.append((current_x, current_y))
                i += 2
                current_cmd = 'l' if is_relative else 'L'

            elif cmd_upper == 'L':
                x = float(tokens[i])
                y = float(tokens[i + 1]) if i + 1 < len(tokens) else 0
                if is_relative:
                    current_x += x
                    current_y += y
                else:
                    current_x, current_y = x, y
                points.append((current_x, current_y))
                i += 2

            elif cmd_upper == 'H':
                x = float(tokens[i])
                current_x = current_x + x if is_relative else x
                points.append((current_x, current_y))
                i += 1

            elif cmd_upper == 'V':
                y = float(tokens[i])
                current_y = current_y + y if is_relative else y
                points.append((current_x, current_y))
                i += 1

            elif cmd_upper == 'C':
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                x, y = float(tokens[i + 4]), float(tokens[i + 5])
                if is_relative:
                    x1, y1 = x1 + current_x, y1 + current_y
                    x2, y2 = x2 + current_x, y2 + current_y
                    x, y = x + current_x, y + current_y
                for t in [0.25, 0.5, 0.75, 1.0]:
                    bx = (1-t)**3 * current_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x
                    by = (1-t)**3 * current_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y
                    points.append((bx, by))
                current_x, current_y = x, y
                i += 6

            elif cmd_upper in ['S', 'Q', 'T']:
                params = 4 if cmd_upper in ['S', 'Q'] else 2
                if i + params <= len(tokens):
                    x, y = float(tokens[i + params - 2]), float(tokens[i + params - 1])
                    if is_relative:
                        x, y = x + current_x, y + current_y
                    current_x, current_y = x, y
                    points.append((current_x, current_y))
                i += params

            elif cmd_upper == 'A':
                if i + 7 <= len(tokens):
                    x, y = float(tokens[i + 5]), float(tokens[i + 6])
                    if is_relative:
                        x, y = x + current_x, y + current_y
                    current_x, current_y = x, y
                    points.append((current_x, current_y))
                i += 7

            elif cmd_upper == 'Z':
                current_x, current_y = start_x, start_y
                points.append((current_x, current_y))
                i += 1

            else:
                i += 1
        except (ValueError, IndexError):
            i += 1

    return points


def build_svg_color_index(svg_file):
    """
    Parse SVG file and build spatial index of path segments with colors.
    Returns SpatialColorIndex object.
    """
    with open(svg_file, 'r') as f:
        svg_content = f.read()

    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    root = ET.fromstring(svg_content)

    SVG_NS = 'http://www.w3.org/2000/svg'

    # Get SVG dimensions for coordinate conversion
    viewbox = root.get('viewBox', '')
    width_attr = root.get('width', '')
    height_attr = root.get('height', '')

    vb_width, vb_height = 1, 1
    if viewbox:
        parts = viewbox.split()
        if len(parts) >= 4:
            vb_width, vb_height = float(parts[2]), float(parts[3])

    # Unit conversion factors to mm
    UNIT_TO_MM = {
        'mm': 1.0,
        'cm': 10.0,
        'in': 25.4,
        'pt': 25.4 / 72.0,
        'px': 25.4 / 96.0,
        '': 25.4 / 96.0,  # Default: assume px
    }

    def parse_length_to_mm(length_str):
        """Parse SVG length string to mm."""
        if not length_str:
            return None
        match = re.match(r'([\d.]+)\s*(\w*)', length_str.strip())
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            return value * UNIT_TO_MM.get(unit, 1.0)
        return None

    # Calculate scale factor (viewBox units to mm)
    width_mm = parse_length_to_mm(width_attr)
    height_mm = parse_length_to_mm(height_attr)

    if width_mm and vb_width:
        scale_x = width_mm / vb_width
    else:
        scale_x = UNIT_TO_MM['px']  # Fallback

    if height_mm and vb_height:
        scale_y = height_mm / vb_height
    else:
        scale_y = UNIT_TO_MM['px']  # Fallback

    spatial_index = SpatialColorIndex(cell_size=5.0)
    default_stroke = root.get('stroke', 'black')

    def process_element(element, inherited_stroke=None):
        current_stroke = get_svg_element_stroke(element, inherited_stroke)
        tag_local = element.tag.replace(f'{{{SVG_NS}}}', '')

        if tag_local == 'path':
            d_attr = element.get('d', '')
            points = parse_svg_path_d(d_attr)

            if points and current_stroke:
                points = [(x * scale_x, y * scale_y) for x, y in points]
                rgb = parse_svg_color(current_stroke or default_stroke)
                grayscale = rgb_to_grayscale_value(rgb)

                for i in range(len(points) - 1):
                    spatial_index.add_segment(points[i], points[i + 1], grayscale)

        elif tag_local == 'line':
            x1, y1 = float(element.get('x1', 0)), float(element.get('y1', 0))
            x2, y2 = float(element.get('x2', 0)), float(element.get('y2', 0))
            points = [(x1 * scale_x, y1 * scale_y), (x2 * scale_x, y2 * scale_y)]
            rgb = parse_svg_color(current_stroke or default_stroke)
            grayscale = rgb_to_grayscale_value(rgb)
            spatial_index.add_segment(points[0], points[1], grayscale)

        elif tag_local in ['polyline', 'polygon']:
            points_attr = element.get('points', '')
            coords = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)', points_attr)
            points = [(float(coords[i]) * scale_x, float(coords[i + 1]) * scale_y)
                      for i in range(0, len(coords) - 1, 2)]
            if points:
                rgb = parse_svg_color(current_stroke or default_stroke)
                grayscale = rgb_to_grayscale_value(rgb)
                for i in range(len(points) - 1):
                    spatial_index.add_segment(points[i], points[i + 1], grayscale)
                if tag_local == 'polygon' and len(points) > 2:
                    spatial_index.add_segment(points[-1], points[0], grayscale)

        for child in element:
            process_element(child, current_stroke)

    process_element(root, default_stroke)
    return spatial_index


# =============================================================================
# Original brush functions
# =============================================================================

def color_to_grayscale(color) -> float:
    """
    Convert a vpype Color object to a normalized grayscale value (0.0-1.0).

    0.0 = black, 1.0 = white

    Args:
        color: vpype.metadata.Color object with red, green, blue attributes, or None

    Returns:
        Normalized grayscale value between 0.0 and 1.0
    """
    if color is None:
        return 0.5  # Default to mid-gray

    # vpype Color object has .red, .green, .blue attributes (0-255)
    r = color.red
    g = color.green
    b = color.blue

    # Use standard luminance formula
    grayscale = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return grayscale


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


def merge_connected_lines(lines, tolerance=0.5):
    """
    Merge connected lines on the SAME ROW (similar Y coordinate).

    This fixes the pen-lift bug where SVGs with per-segment colors create
    thousands of tiny separate paths that are actually connected.

    Only merges lines where:
    - X gap is within tolerance (horizontal connection)
    - Y difference is very small (same row, max 1mm)

    Args:
        lines: List of numpy arrays of complex numbers (vpype line format)
        tolerance: Maximum X distance (in vpype units) to consider points connected

    Returns:
        List of merged lines (numpy arrays of complex)
    """
    if not lines:
        return []

    # Convert to list of lists for easier manipulation
    remaining = [list(line) for line in lines if len(line) > 0]

    if not remaining:
        return []

    # Y tolerance: max 3mm difference to be considered same row
    # 3mm = 3 * 96/25.4 ≈ 11.34 vpype units
    y_tolerance = 11.34

    def points_connect(p1, p2):
        """Check if two points connect (same row, X within tolerance)."""
        x_diff = abs(p1.real - p2.real)
        y_diff = abs(p1.imag - p2.imag)
        return x_diff < tolerance and y_diff < y_tolerance

    merged = []

    while remaining:
        # Start a new chain with the first remaining line
        current_chain = remaining.pop(0)

        # Keep trying to extend the chain
        changed = True
        while changed:
            changed = False
            chain_start = current_chain[0]
            chain_end = current_chain[-1]

            i = 0
            while i < len(remaining):
                line = remaining[i]
                line_start = line[0]
                line_end = line[-1]

                # Check if this line connects to end of chain (line_start -> chain_end)
                if points_connect(chain_end, line_start):
                    # Append line to end of chain (skip duplicate point)
                    current_chain.extend(line[1:])
                    remaining.pop(i)
                    changed = True
                    continue

                # Check if this line connects to start of chain (line_end -> chain_start)
                elif points_connect(line_end, chain_start):
                    # Prepend line to start of chain (skip duplicate point)
                    current_chain = line[:-1] + current_chain
                    remaining.pop(i)
                    changed = True
                    continue

                # Check if reversed line connects to end (line_end -> chain_end)
                elif points_connect(chain_end, line_end):
                    # Append reversed line to end
                    current_chain.extend(reversed(line[:-1]))
                    remaining.pop(i)
                    changed = True
                    continue

                # Check if reversed line connects to start (line_start -> chain_start)
                elif points_connect(line_start, chain_start):
                    # Prepend reversed line to start
                    current_chain = list(reversed(line[1:])) + current_chain
                    remaining.pop(i)
                    changed = True
                    continue

                i += 1

        merged.append(np.array(current_chain))

    return merged


def calculate_z(distance_from_start, total_distance, z_up, z_down, press_distance, lift_distance):
    """
    Calculate Z value based on position within stroke.

    For short strokes where total_distance < press_distance + lift_distance,
    the press and lift phases are scaled proportionally to avoid overlap.

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

    # Handle short strokes: scale press/lift distances proportionally
    if total_distance < press_distance + lift_distance:
        # Scale the distances to fit within the stroke length
        total_transition = press_distance + lift_distance
        scale_factor = total_distance / total_transition if total_transition > 0 else 1.0
        actual_press_distance = press_distance * scale_factor
        actual_lift_distance = lift_distance * scale_factor
    else:
        actual_press_distance = press_distance
        actual_lift_distance = lift_distance

    # Phase 1: Pressing down at start
    if distance_from_start <= actual_press_distance:
        progress = distance_from_start / actual_press_distance if actual_press_distance > 0 else 1.0
        return z_up + (z_down - z_up) * progress

    # Phase 3: Lifting up at end
    elif remaining_distance <= actual_lift_distance:
        progress = (actual_lift_distance - remaining_distance) / actual_lift_distance if actual_lift_distance > 0 else 1.0
        return z_down + (z_up - z_down) * progress

    # Phase 2: Constant pressure (middle)
    else:
        return z_down


@click.command()
@click.option('--z-up', default=-3.0, type=float, help='Z height at stroke start/end (mm)')
@click.option('--z-down', default=-20.0, type=float, help='Z height during stroke (full pressure, mm)')
@click.option('--z-from-color', is_flag=True, default=False,
              help='Set Z from line color: black=z-down, white=z-up, grays=progressive')
@click.option('--z-from-svg', type=click.Path(exists=True), default=None,
              help='Set Z from original SVG colors at each point (spatial lookup)')
@click.option('--z-smooth-distance', default=5.0, type=float,
              help='Distance over which to smooth Z transitions when using --z-from-svg (mm)')
@click.option('--press-distance', default=50.0, type=float, help='Distance to press down at start (mm)')
@click.option('--lift-distance', default=50.0, type=float, help='Distance to lift up at end (mm)')
@click.option('--segment-length', default=2.0, type=float, help='Subdivision segment length (mm)')
@click.option('--feed-rate', default=1000.0, type=float, help='Drawing feed rate (mm/min or in/min)')
@click.option('--unit', default='mm', type=str, help='Output units (mm, cm, in, etc.)')
@click.option('--merge-tolerance', default=1.0, type=float,
              help='Distance tolerance (mm) for merging connected lines. Set to 0 to disable merging.')
@click.option('--output', '-o', type=click.Path(), help='Output G-code file path')
@vpype_cli.global_processor
def brush(document, z_up, z_down, z_from_color, z_from_svg, z_smooth_distance, press_distance, lift_distance, segment_length, feed_rate, unit, merge_tolerance, output):
    """
    Add gradual Z-axis pressure variation for brush plotting.

    This command subdivides all line segments and adds Z coordinates to create
    natural brush strokes with gradual pressure transitions at the start and end.

    Examples:
        vpype read input.svg brush --z-up -5 --z-down -20 --output output.gcode

        # Use original SVG colors for Z pressure (spatial lookup):
        vpype read input.svg brush --z-from-svg input.svg --z-up -3 --z-down -20 -o output.gcode
    """

    if output:
        # Direct G-code output mode
        generate_gcode(document, z_up, z_down, z_from_color, z_from_svg, z_smooth_distance,
                       press_distance, lift_distance, segment_length, feed_rate, unit,
                       merge_tolerance, output)
        return document
    else:
        # Process geometry (subdivide lines with Z variations)
        process_geometry(document, z_up, z_down, z_from_color, press_distance, lift_distance, segment_length)
        return document


def process_geometry(document, z_up, z_down, z_from_color, press_distance, lift_distance, segment_length):
    """
    Process all lines in the document and add Z coordinate metadata.
    """
    for layer_id in document.layers:
        lc = document.layers[layer_id]
        new_lines = []

        for line_idx, line in enumerate(lc):
            # Subdivide the line
            points_2d = subdivide_line(line, segment_length)

            if len(points_2d) < 2:
                new_lines.append(line)
                continue

            # Determine effective z_down based on color if z_from_color is enabled
            effective_z_down = z_down
            if z_from_color:
                # Get color for this line
                color = lc.property("vp_color")
                grayscale = color_to_grayscale(color)
                # Map: black (0.0) -> z_down, white (1.0) -> z_up
                effective_z_down = z_down + grayscale * (z_up - z_down)

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
                    effective_z_down,
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


def generate_gcode(document, z_up, z_down, z_from_color, z_from_svg, z_smooth_distance,
                   press_distance, lift_distance, segment_length, feed_rate, unit,
                   merge_tolerance, output_path):
    """
    Generate G-code directly with Z variations.
    Properly scales coordinates from vpype's internal units to the target unit.
    Uses simultaneous XYZ movements for fluid, natural brush strokes.

    If z_from_svg is provided, uses spatial color lookup for smooth Z transitions.
    """
    # Get the unit scale factor (converts from vpype internal units to target unit)
    # vpype uses CSS pixels internally (1px = 1/96 inch = 0.2645833mm)
    unit_scale = vp.convert_length(unit)

    # Build spatial color index if z_from_svg is provided
    svg_color_index = None
    svg_offset_x = 0
    svg_offset_y = 0
    if z_from_svg:
        click.echo(f"Building color index from SVG: {z_from_svg}")
        svg_color_index = build_svg_color_index(z_from_svg)
        click.echo(f"  Indexed {len(svg_color_index.segments)} path segments")
        # vpype normalizes coords to start at 0, but SVG content may have an offset
        svg_offset_x = svg_color_index.min_x
        svg_offset_y = svg_color_index.min_y
        click.echo(f"  SVG bounds: ({svg_color_index.min_x:.1f}, {svg_color_index.min_y:.1f}) to ({svg_color_index.max_x:.1f}, {svg_color_index.max_y:.1f})")

    gcode_lines = []

    # G-code header
    gcode_lines.append("; Generated by vpype-brush")
    if z_from_svg:
        gcode_lines.append(f"; Z from SVG colors: {z_from_svg}")

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

    # Track current Z for smoothing (used with z_from_svg)
    current_z = z_up

    # Process each layer
    for layer_id in sorted(document.layers.keys()):
        lc = document.layers[layer_id]
        gcode_lines.append(f"; Layer {layer_id}")

        # Merge connected lines to reduce pen lifts
        # Convert merge_tolerance from mm to vpype internal units
        # vpype uses CSS pixels (1px = 1/96 inch ≈ 0.2646mm)
        # So 1mm ≈ 3.78 vpype units
        tolerance_vpype_units = merge_tolerance * (96.0 / 25.4) if merge_tolerance > 0 else 0
        original_count = len(lc)

        if tolerance_vpype_units > 0:
            lines_to_process = merge_connected_lines(list(lc), tolerance=tolerance_vpype_units)
        else:
            lines_to_process = list(lc)

        merged_count = len(lines_to_process)

        if original_count != merged_count:
            click.echo(f"  Layer {layer_id}: Merged {original_count} lines → {merged_count} strokes")
            gcode_lines.append(f"; Merged {original_count} lines into {merged_count} strokes")

        for line_idx, line in enumerate(lines_to_process):
            # Subdivide the line
            points_2d = subdivide_line(line, segment_length)

            if len(points_2d) < 2:
                continue

            # Determine effective z_down based on color if z_from_color is enabled
            effective_z_down = z_down
            if z_from_color and not z_from_svg:
                # Get color for this line (layer-level color)
                color = lc.property("vp_color")
                grayscale = color_to_grayscale(color)
                # Map: black (0.0) -> z_down, white (1.0) -> z_up
                effective_z_down = z_down + grayscale * (z_up - z_down)

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

            # Reset current_z at start of new stroke
            current_z = z_up

            # Draw the stroke with Z variation (simultaneous XYZ movement)
            for i, (x, y) in enumerate(points_2d):
                # Convert from vpype internal units to target unit
                x_scaled = x / unit_scale
                y_scaled = y / unit_scale

                if svg_color_index:
                    # Use spatial color lookup for Z (apply SVG offset)
                    grayscale = svg_color_index.find_grayscale_at(
                        x_scaled + svg_offset_x, y_scaled + svg_offset_y)
                    # Map: black (0.0) -> z_down, white (1.0) -> z_up
                    target_z = z_down + grayscale * (z_up - z_down)

                    # Apply press/lift envelope
                    envelope_z = calculate_z(
                        cumulative_distances[i],
                        total_distance,
                        z_up,
                        z_down,  # Use full range for envelope
                        press_distance,
                        lift_distance
                    )
                    # Blend: use envelope to limit how far we can go
                    # At start/end (envelope near z_up), limit Z toward z_up
                    # In middle (envelope at z_down), allow full color-based Z
                    envelope_factor = (envelope_z - z_up) / (z_down - z_up) if z_down != z_up else 1.0
                    target_z = z_up + envelope_factor * (target_z - z_up)

                    # Smooth Z transition using exponential smoothing
                    if z_smooth_distance > 0 and i > 0:
                        x_prev, y_prev = points_2d[i - 1]
                        travel_dist = np.sqrt((x - x_prev)**2 + (y - y_prev)**2) / unit_scale
                        # Exponential smoothing: move fraction of distance to target
                        # Factor of 0.0 = no change, 1.0 = instant change
                        smoothing_factor = min(1.0, travel_dist / z_smooth_distance)
                        z = current_z + smoothing_factor * (target_z - current_z)
                    else:
                        z = target_z

                    current_z = z
                else:
                    # Original behavior: calculate Z from position in stroke
                    z = calculate_z(
                        cumulative_distances[i],
                        total_distance,
                        z_up,
                        effective_z_down,
                        press_distance,
                        lift_distance
                    )

                # Simultaneous XYZ move for fluid brush strokes
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
