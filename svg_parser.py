"""
SVG Path Parser for DexArm Drawing
===================================
Parses SVG files and converts paths to DexArm drawing commands.
"""

import xml.etree.ElementTree as ET
import re
from svg.path import parse_path
from svg.path.path import Line, Move, Close, CubicBezier, QuadraticBezier, Arc


class SVGPathParser:
    """Parse SVG and convert to DexArm drawing commands"""

    def __init__(self):
        self.paths = []
        self.viewbox = None
        self.width = None
        self.height = None

    def parse_svg_file(self, svg_path):
        """
        Parse an SVG file and extract all paths

        Args:
            svg_path (str): Path to SVG file

        Returns:
            list: List of path segments ready for drawing
        """
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Extract viewBox or width/height
        self._extract_dimensions(root)

        # IMPORTANT: Clear previous paths to avoid caching
        self.paths = []
        self.polyline_count = 0  # Debug counter
        self._extract_paths_recursive(root)

        # Sort paths by length (longest first) for better drawing efficiency
        self.paths.sort(key=lambda p: p.length(), reverse=True)

        print(f"Parsed SVG: {len(self.paths)} paths found (sorted longest first)")
        print(f"  (Parsed {self.polyline_count} polylines)")
        return self.paths

    def _extract_dimensions(self, root):
        """Extract SVG dimensions from viewBox or width/height attributes"""
        # Try viewBox first
        viewbox = root.get('viewBox')
        if viewbox:
            # Handle both comma and space separated viewBox formats
            parts = viewbox.replace(',', ' ').split()
            if len(parts) >= 4:
                self.viewbox = {
                    'x': float(parts[0]),
                    'y': float(parts[1]),
                    'width': float(parts[2]),
                    'height': float(parts[3])
                }
                self.width = self.viewbox['width']
                self.height = self.viewbox['height']
                return

        # Fallback to width/height
        width_str = root.get('width', '100')
        height_str = root.get('height', '100')

        # Strip 'px' or other units
        self.width = float(re.sub(r'[^0-9.]', '', width_str))
        self.height = float(re.sub(r'[^0-9.]', '', height_str))

    def _extract_paths_recursive(self, element):
        """Recursively extract path and line elements from SVG"""
        # Handle namespace for SVG
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        # Check if this element is a path
        if element.tag.endswith('path'):
            d = element.get('d')
            if d:
                try:
                    parsed = parse_path(d)
                    self.paths.append(parsed)
                except Exception as e:
                    print(f"WARNING: Failed to parse path: {e}")

        # Check if this element is a polyline (MUST check BEFORE 'line' since 'polyline' ends with 'line')
        elif element.tag.endswith('polyline'):
            try:
                self.polyline_count += 1
                points_str = element.get('points', '')
                if points_str:
                    # svgwrite outputs points as: "(x1, y1) (x2, y2) (x3, y3)..."
                    # Need to clean up parentheses and commas
                    points_str = points_str.replace('(', '').replace(')', '').replace(',', ' ')
                    coords = points_str.split()

                    if len(coords) >= 4:  # At least 2 points (x,y pairs)
                        # Build path string: M x1,y1 L x2,y2 L x3,y3...
                        path_parts = []
                        for i in range(0, len(coords) - 1, 2):
                            x = coords[i]
                            y = coords[i + 1]
                            if i == 0:
                                path_parts.append(f"M {x},{y}")
                            else:
                                path_parts.append(f"L {x},{y}")

                        path_str = " ".join(path_parts)
                        parsed = parse_path(path_str)
                        self.paths.append(parsed)
            except Exception as e:
                print(f"WARNING: Failed to parse polyline: {e}")

        # Check if this element is a line (from edge detection SVG)
        # NOTE: Must check AFTER polyline since 'polyline' ends with 'line'
        elif element.tag.endswith('line') and not element.tag.endswith('polyline'):
            try:
                x1 = float(element.get('x1', 0))
                y1 = float(element.get('y1', 0))
                x2 = float(element.get('x2', 0))
                y2 = float(element.get('y2', 0))

                # Skip very tiny lines (less than 1 pixel)
                line_length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                if line_length < 1:
                    return

                # Convert line to path format: "M x1,y1 L x2,y2"
                path_str = f"M {x1},{y1} L {x2},{y2}"
                parsed = parse_path(path_str)
                self.paths.append(parsed)
            except Exception as e:
                print(f"WARNING: Failed to parse line: {e}")

        # Check children
        for child in element:
            self._extract_paths_recursive(child)

    def convert_to_drawing_commands(self, drawing_area, z_draw=0, z_up=16, pen_down_feedrate=8000, pen_up_feedrate=8000, max_commands=5000):
        """
        Convert parsed paths to DexArm drawing commands

        Args:
            drawing_area (dict): Drawing area from DexArm controller
                {'width': float, 'height': float, 'x_min': float, 'y_min': float, 'x_max': float, 'y_max': float, 'z_draw': float}
            z_draw (float): Z height for drawing (pen down)
            z_up (float): Z height for moving (pen up)
            pen_down_feedrate (int): Speed when drawing
            pen_up_feedrate (int): Speed when moving
            max_commands (int): Maximum number of commands to generate

        Returns:
            list: List of drawing commands [{'type': 'move'|'draw', 'x': float, 'y': float, 'z': float, 'feedrate': int}, ...]
        """
        if not self.paths:
            print("WARNING: No paths to convert")
            return []

        # Use z_draw from drawing area if available
        if 'z_draw' in drawing_area:
            z_draw = drawing_area['z_draw']

        z_up_actual = z_draw + z_up  # Calculate absolute Z for pen up

        commands = []

        # Calculate scaling factors to fit SVG into drawing area
        svg_width = self.width or 100
        svg_height = self.height or 100

        # Zoom to fill the drawing area (use larger scale to maximize space)
        # This may crop parts of the SVG that don't fit, but fills the space better
        scale_x = drawing_area['width'] / svg_width
        scale_y = drawing_area['height'] / svg_height

        # Use the LARGER scale to fill the area (parts may be cropped)
        scale = max(scale_x, scale_y)

        # Calculate offset to center the drawing
        scaled_width = svg_width * scale
        scaled_height = svg_height * scale
        offset_x = drawing_area['x_min'] + (drawing_area['width'] - scaled_width) / 2
        offset_y = drawing_area['y_min'] + (drawing_area['height'] - scaled_height) / 2

        print(f"📐 SVG dimensions: {svg_width} x {svg_height}")
        print(f"📐 Drawing area: {drawing_area['width']} x {drawing_area['height']}")
        print(f"📐 Scale factor: {scale:.4f}")
        print(f"📐 Offset: ({offset_x:.2f}, {offset_y:.2f})")

        # Process each path (limited by max_commands setting)
        path_count = 0

        for path in self.paths:
            # Stop if we've reached the command limit
            if len(commands) >= max_commands:
                print(f"⚠️  Reached command limit ({max_commands}), skipping remaining {len(self.paths) - path_count} paths")
                break

            path_count += 1

            # Start each path with pen up
            first_point = True

            for segment in path:
                # Sample points from the segment
                if isinstance(segment, Move):
                    # Move command - pen up
                    x, y = self._transform_point(segment.end.real, segment.end.imag, scale, offset_x, offset_y)
                    commands.append({
                        'type': 'move',
                        'x': x,
                        'y': y,
                        'z': z_up_actual,
                        'feedrate': pen_up_feedrate
                    })
                    first_point = False

                elif isinstance(segment, (Line, Close)):
                    # Line segment - pen down
                    x, y = self._transform_point(segment.end.real, segment.end.imag, scale, offset_x, offset_y)

                    # Skip points outside the drawing area (clipping)
                    if not self._is_in_bounds(x, y, drawing_area):
                        continue

                    # If first point of this path, move with pen up first
                    if first_point:
                        commands.append({
                            'type': 'move',
                            'x': x,
                            'y': y,
                            'z': z_up_actual,
                            'feedrate': pen_up_feedrate
                        })
                        # Then pen down
                        commands.append({
                            'type': 'draw',
                            'x': x,
                            'y': y,
                            'z': z_draw,
                            'feedrate': pen_down_feedrate
                        })
                        first_point = False
                    else:
                        commands.append({
                            'type': 'draw',
                            'x': x,
                            'y': y,
                            'z': z_draw,
                            'feedrate': pen_down_feedrate
                        })

                elif isinstance(segment, (CubicBezier, QuadraticBezier, Arc)):
                    # Curve - sample points and draw as line segments
                    num_samples = 20
                    for i in range(num_samples + 1):
                        t = i / num_samples
                        point = segment.point(t)
                        x, y = self._transform_point(point.real, point.imag, scale, offset_x, offset_y)

                        if first_point and i == 0:
                            # Move to start with pen up
                            commands.append({
                                'type': 'move',
                                'x': x,
                                'y': y,
                                'z': z_up_actual,
                                'feedrate': pen_up_feedrate
                            })
                            # Pen down
                            commands.append({
                                'type': 'draw',
                                'x': x,
                                'y': y,
                                'z': z_draw,
                                'feedrate': pen_down_feedrate
                            })
                            first_point = False
                        else:
                            commands.append({
                                'type': 'draw',
                                'x': x,
                                'y': y,
                                'z': z_draw,
                                'feedrate': pen_down_feedrate
                            })

            # Lift pen at end of path
            if commands:
                last_cmd = commands[-1]
                commands.append({
                    'type': 'move',
                    'x': last_cmd['x'],
                    'y': last_cmd['y'],
                    'z': z_up_actual,
                    'feedrate': pen_up_feedrate
                })

        print(f"Generated {len(commands)} drawing commands from {path_count} paths")
        return commands

    def _transform_point(self, svg_x, svg_y, scale, offset_x, offset_y):
        """
        Transform SVG coordinates to DexArm coordinates

        Args:
            svg_x (float): SVG X coordinate
            svg_y (float): SVG Y coordinate
            scale (float): Scale factor
            offset_x (float): X offset
            offset_y (float): Y offset

        Returns:
            tuple: (x, y) in DexArm coordinates
        """
        # Scale and offset
        x = svg_x * scale + offset_x
        y = svg_y * scale + offset_y

        return (x, y)

    def _is_in_bounds(self, x, y, drawing_area):
        """
        Check if a point is within the drawing area bounds

        Args:
            x (float): X coordinate
            y (float): Y coordinate
            drawing_area (dict): Drawing area bounds

        Returns:
            bool: True if point is within bounds
        """
        return (drawing_area['x_min'] <= x <= drawing_area['x_max'] and
                drawing_area['y_min'] <= y <= drawing_area['y_max'])


# Global parser instance
svg_parser = SVGPathParser()
