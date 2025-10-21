"""
Alternative SVG Generation Methods for Plotter Drawing
========================================================
Three different approaches optimized for continuous, smooth pen plotting.
"""

import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import distance_matrix
import svgwrite
from skimage.morphology import skeletonize, medial_axis
from skimage import img_as_ubyte
import os


class PlotterSVGGenerator:
    """Generate plotter-optimized SVG files using different methods"""

    def __init__(self):
        self.output_dir = 'svgs'
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_methods(self, image_path, base_filename):
        """
        Generate 3 SVG files using different plotter-optimized methods

        Args:
            image_path: Path to input JPG image
            base_filename: Base name for output SVG files

        Returns:
            dict: Paths to generated SVG files
        """
        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        height, width = img.shape

        # Generate all 3 methods
        results = {}

        print("🎨 Generating Method 1: Centerline Tracing (Plotter-optimized)...")
        results['method1'] = self._method1_centerline_tracing(
            img, width, height, f"{base_filename}_method1_centerline.svg"
        )

        print("🎨 Generating Method 2: Thick Line Detection with Joining...")
        results['method2'] = self._method2_thick_line_joining(
            img, width, height, f"{base_filename}_method2_thick_joining.svg"
        )

        print("🎨 Generating Method 3: CNC V-Carving Style (Variable Width)...")
        results['method3'] = self._method3_cnc_vcarving_style(
            img, width, height, f"{base_filename}_method3_cnc_style.svg"
        )

        return results

    def _method1_centerline_tracing(self, img, width, height, filename):
        """
        Method 1: Centerline Tracing (Plotter-Recommended)

        Uses morphological skeletonization to find centerlines of thick strokes,
        then optimizes path order for continuous drawing with minimal pen-ups.

        This is the industry-standard approach for pen plotters.
        """
        dwg = svgwrite.Drawing(
            os.path.join(self.output_dir, filename),
            size=(f'{width}px', f'{height}px'),
            viewBox=f'0 0 {width} {height}'
        )

        # 1. Edge detection with multiple thresholds to capture all details
        edges = cv2.Canny(img, 30, 100)

        # 2. Dilate edges to create thick strokes (simulate pen width)
        kernel = np.ones((3, 3), np.uint8)
        thick_edges = cv2.dilate(edges, kernel, iterations=2)

        # 3. Invert for skeletonization (need white on black)
        inverted = cv2.bitwise_not(thick_edges)

        # 4. Skeletonize to find centerlines
        # This creates single-pixel-wide paths along the center of thick strokes
        skeleton = skeletonize(inverted > 128)
        skeleton = img_as_ubyte(skeleton)

        # 5. Find contours in the skeleton
        skeleton_contours, _ = cv2.findContours(
            skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1
        )

        # 6. Convert contours to polylines and optimize order
        polylines = []
        for contour in skeleton_contours:
            if len(contour) > 3:  # Skip very short segments
                # Simplify path using Douglas-Peucker
                epsilon = 0.5  # Lower = more detail
                simplified = cv2.approxPolyDP(contour, epsilon, False)

                if len(simplified) > 1:
                    points = [(int(pt[0][0]), int(pt[0][1])) for pt in simplified]
                    polylines.append(points)

        # 7. Optimize drawing order using greedy nearest-neighbor
        # This minimizes pen-up travel distance
        if polylines:
            ordered_polylines = self._optimize_path_order(polylines)

            # 8. Draw optimized polylines
            for points in ordered_polylines:
                if len(points) > 1:
                    dwg.add(dwg.polyline(
                        points=points,
                        stroke='black',
                        fill='none',
                        stroke_width=1.0,
                        stroke_linecap='round',
                        stroke_linejoin='round'
                    ))

        dwg.save()
        print(f"✅ Method 1 saved: {filename} ({len(polylines)} paths)")
        return os.path.join(self.output_dir, filename)

    def _method2_thick_line_joining(self, img, width, height, filename):
        """
        Method 2: Custom Thick Line Detection with Intelligent Joining

        Detects thick contours, finds their centerlines, and intelligently
        joins nearby line segments to create long, smooth, continuous strokes
        like an artist would draw.
        """
        dwg = svgwrite.Drawing(
            os.path.join(self.output_dir, filename),
            size=(f'{width}px', f'{height}px'),
            viewBox=f'0 0 {width} {height}'
        )

        # 1. Edge detection with bilateral filter to preserve edges
        blurred = cv2.bilateralFilter(img, 9, 75, 75)
        edges = cv2.Canny(blurred, 50, 150)

        # 2. Find contours
        contours, hierarchy = cv2.findContours(
            edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS
        )

        # 3. Process each contour to find centerlines
        segments = []

        for contour in contours:
            if len(contour) < 5:
                continue

            # Simplify contour
            epsilon = 1.0
            simplified = cv2.approxPolyDP(contour, epsilon, False)

            if len(simplified) > 1:
                # Extract endpoints
                points = [tuple(pt[0]) for pt in simplified]
                segments.append({
                    'points': points,
                    'start': points[0],
                    'end': points[-1],
                    'length': self._polyline_length(points)
                })

        # 4. Join nearby segments (within threshold distance)
        join_threshold = 15  # pixels
        joined_paths = self._join_nearby_segments(segments, join_threshold)

        # 5. Smooth the joined paths using Bezier approximation
        smoothed_paths = []
        for path_points in joined_paths:
            if len(path_points) > 2:
                # Apply Gaussian smoothing to coordinates
                smoothed = self._smooth_polyline(path_points)
                smoothed_paths.append(smoothed)

        # 6. Optimize drawing order
        if smoothed_paths:
            ordered_paths = self._optimize_path_order(smoothed_paths)

            # 7. Draw smooth paths
            for points in ordered_paths:
                if len(points) > 1:
                    dwg.add(dwg.polyline(
                        points=points,
                        stroke='black',
                        fill='none',
                        stroke_width=1.2,
                        stroke_linecap='round',
                        stroke_linejoin='round'
                    ))

        dwg.save()
        print(f"✅ Method 2 saved: {filename} ({len(smoothed_paths)} joined paths)")
        return os.path.join(self.output_dir, filename)

    def _method3_cnc_vcarving_style(self, img, width, height, filename):
        """
        Method 3: CNC V-Carving Style (Adapted for Drawing)

        Uses techniques from CNC V-carving: creates variable-width strokes
        by drawing parallel offset paths at different depths/widths.
        Simulates varying pen pressure or multiple passes.
        """
        dwg = svgwrite.Drawing(
            os.path.join(self.output_dir, filename),
            size=(f'{width}px', f'{height}px'),
            viewBox=f'0 0 {width} {height}'
        )

        # 1. Multi-threshold edge detection for depth layers
        # Lighter threshold = outer edges (wide strokes)
        # Darker threshold = inner edges (narrow strokes)

        # Layer 1: Outer contours (light edges)
        edges_light = cv2.Canny(img, 20, 60)

        # Layer 2: Medium contours
        edges_medium = cv2.Canny(img, 40, 120)

        # Layer 3: Inner contours (dark edges)
        edges_dark = cv2.Canny(img, 80, 200)

        # 2. Process each layer with different stroke widths
        layers = [
            (edges_light, 2.0, 'light'),
            (edges_medium, 1.2, 'medium'),
            (edges_dark, 0.8, 'dark')
        ]

        all_paths = []

        for edge_img, stroke_width, layer_name in layers:
            # Find contours
            contours, _ = cv2.findContours(
                edge_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1
            )

            # Simplify and collect paths
            for contour in contours:
                if len(contour) > 4:
                    epsilon = 0.8
                    simplified = cv2.approxPolyDP(contour, epsilon, False)

                    if len(simplified) > 1:
                        points = [(int(pt[0][0]), int(pt[0][1])) for pt in simplified]
                        all_paths.append((points, stroke_width))

        # 3. Optimize drawing order (draw from outside to inside)
        # Sort by average distance from center (outer first)
        center_x, center_y = width / 2, height / 2

        def path_distance_from_center(path_data):
            points, _ = path_data
            avg_dist = np.mean([
                np.sqrt((x - center_x)**2 + (y - center_y)**2)
                for x, y in points
            ])
            return -avg_dist  # Negative for reverse sort (outer first)

        all_paths.sort(key=path_distance_from_center)

        # 4. Draw layered paths
        for points, stroke_width in all_paths:
            if len(points) > 1:
                dwg.add(dwg.polyline(
                    points=points,
                    stroke='black',
                    fill='none',
                    stroke_width=stroke_width,
                    stroke_linecap='round',
                    stroke_linejoin='round'
                ))

        dwg.save()
        print(f"✅ Method 3 saved: {filename} ({len(all_paths)} layered paths)")
        return os.path.join(self.output_dir, filename)

    # --- Helper Methods ---

    def _optimize_path_order(self, polylines):
        """
        Optimize drawing order using greedy nearest-neighbor TSP approximation.
        Minimizes pen-up travel distance.
        """
        if not polylines:
            return []

        ordered = []
        remaining = polylines.copy()

        # Start with first polyline
        current = remaining.pop(0)
        ordered.append(current)
        current_end = current[-1]

        # Greedy nearest-neighbor
        while remaining:
            # Find nearest polyline (by start or end point)
            min_dist = float('inf')
            best_idx = 0
            best_reverse = False

            for idx, poly in enumerate(remaining):
                # Distance to start
                dist_start = self._point_distance(current_end, poly[0])
                if dist_start < min_dist:
                    min_dist = dist_start
                    best_idx = idx
                    best_reverse = False

                # Distance to end (would need to reverse)
                dist_end = self._point_distance(current_end, poly[-1])
                if dist_end < min_dist:
                    min_dist = dist_end
                    best_idx = idx
                    best_reverse = True

            # Add best match
            next_poly = remaining.pop(best_idx)
            if best_reverse:
                next_poly = list(reversed(next_poly))

            ordered.append(next_poly)
            current_end = next_poly[-1]

        return ordered

    def _join_nearby_segments(self, segments, threshold):
        """
        Join line segments that are close together into continuous paths.
        """
        if not segments:
            return []

        # Sort by length (longest first)
        segments.sort(key=lambda s: s['length'], reverse=True)

        joined_paths = []
        used = set()

        for i, seg in enumerate(segments):
            if i in used:
                continue

            # Start new path
            current_path = list(seg['points'])
            used.add(i)
            current_end = seg['end']

            # Try to extend this path by finding nearby segments
            changed = True
            while changed:
                changed = False

                for j, candidate in enumerate(segments):
                    if j in used:
                        continue

                    # Check if candidate start is near current end
                    dist = self._point_distance(current_end, candidate['start'])

                    if dist < threshold:
                        # Extend path
                        current_path.extend(candidate['points'][1:])  # Skip duplicate point
                        current_end = candidate['end']
                        used.add(j)
                        changed = True
                        break

                    # Check if candidate end is near current end (reverse it)
                    dist_reverse = self._point_distance(current_end, candidate['end'])

                    if dist_reverse < threshold:
                        # Extend path with reversed candidate
                        reversed_points = list(reversed(candidate['points']))
                        current_path.extend(reversed_points[1:])
                        current_end = candidate['start']
                        used.add(j)
                        changed = True
                        break

            joined_paths.append(current_path)

        return joined_paths

    def _smooth_polyline(self, points, sigma=1.5):
        """
        Smooth a polyline using Gaussian filter on coordinates.
        """
        if len(points) < 3:
            return points

        # Extract x and y coordinates
        x_coords = np.array([p[0] for p in points], dtype=float)
        y_coords = np.array([p[1] for p in points], dtype=float)

        # Apply Gaussian smoothing
        x_smooth = ndimage.gaussian_filter1d(x_coords, sigma=sigma, mode='nearest')
        y_smooth = ndimage.gaussian_filter1d(y_coords, sigma=sigma, mode='nearest')

        # Reconstruct points
        smoothed = [(int(x), int(y)) for x, y in zip(x_smooth, y_smooth)]

        return smoothed

    def _point_distance(self, p1, p2):
        """Calculate Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _polyline_length(self, points):
        """Calculate total length of a polyline."""
        if len(points) < 2:
            return 0

        total = 0
        for i in range(len(points) - 1):
            total += self._point_distance(points[i], points[i + 1])

        return total


# Global instance
plotter_svg_generator = PlotterSVGGenerator()
