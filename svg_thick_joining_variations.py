"""
Thick Joining Method - 10 Variations
=====================================
Focus on the promising thick joining approach with parameter variations
and zigzag fill for small closed areas.
"""

import cv2
import numpy as np
from scipy import ndimage
import svgwrite
import os


class ThickJoiningVariations:
    """Generate 10 variations of the thick joining method"""

    def __init__(self):
        self.output_dir = 'svgs'
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_variations(self, image_path, base_filename):
        """
        Generate thick_v1 variation only (conservative joining)

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
        results = {}

        print("\n" + "="*70)
        print("🎨 Generating Thick Joining V1 (Conservative)")
        print("="*70)

        # Only generate V1: Conservative joining
        print("\nV1: Conservative (10px join, light smooth)")
        filename = f"{base_filename}_thick_v1.svg"
        results['v1'] = self._thick_joining_base(
            img, width, height, filename,
            join_threshold=10,
            smooth_sigma=1.0,
            fill_small_areas=False
        )

        print("\n" + "="*70)
        print(f"✅ Generated thick_v1 variation!")
        print("="*70 + "\n")

        return results

    def _thick_joining_base(self, img, width, height, filename,
                            join_threshold=15, smooth_sigma=1.5,
                            fill_small_areas=False, fill_max_area=500):
        """
        Base thick joining method with configurable parameters

        Args:
            join_threshold: Distance threshold for joining segments (pixels)
            smooth_sigma: Gaussian smoothing sigma
            fill_small_areas: Whether to fill small closed areas with zigzag
            fill_max_area: Maximum area (px²) to fill with zigzag
        """
        dwg = svgwrite.Drawing(
            os.path.join(self.output_dir, filename),
            size=(f'{width}px', f'{height}px'),
            viewBox=f'0 0 {width} {height}'
        )

        # 1. Edge detection with bilateral filter
        blurred = cv2.bilateralFilter(img, 9, 75, 75)
        edges = cv2.Canny(blurred, 50, 150)

        # 2. Find contours
        contours, hierarchy = cv2.findContours(
            edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS
        )

        # 3. Process contours
        segments = []
        closed_contours = []  # For zigzag fill

        for idx, contour in enumerate(contours):
            if len(contour) < 5:
                continue

            # Simplify contour
            epsilon = 1.0
            simplified = cv2.approxPolyDP(contour, epsilon, False)

            if len(simplified) > 1:
                points = [tuple(pt[0]) for pt in simplified]

                # Check if contour is closed
                is_closed = cv2.contourArea(contour) > 0

                if is_closed and fill_small_areas:
                    # Calculate area
                    area = cv2.contourArea(contour)

                    # Store for potential zigzag fill
                    if area > 10 and area < fill_max_area:
                        closed_contours.append({
                            'contour': contour,
                            'points': points,
                            'area': area,
                            'simplified': simplified
                        })

                # Add to segments for joining
                segments.append({
                    'points': points,
                    'start': points[0],
                    'end': points[-1],
                    'length': self._polyline_length(points),
                    'is_closed': is_closed
                })

        # 4. Join nearby segments
        joined_paths = self._join_nearby_segments(segments, join_threshold)

        # 5. Smooth the joined paths
        smoothed_paths = []
        for path_points in joined_paths:
            if len(path_points) > 2:
                smoothed = self._smooth_polyline(path_points, sigma=smooth_sigma)
                smoothed_paths.append(smoothed)

        # 6. Optimize drawing order
        if smoothed_paths:
            ordered_paths = self._optimize_path_order(smoothed_paths)

            # Draw smooth paths
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

        # 7. Add zigzag fill for small closed areas (if enabled)
        if fill_small_areas and closed_contours:
            print(f"   Adding zigzag fill to {len(closed_contours)} small areas...")
            zigzag_paths = self._generate_zigzag_fills(closed_contours, spacing=5)

            for points in zigzag_paths:
                if len(points) > 1:
                    dwg.add(dwg.polyline(
                        points=points,
                        stroke='black',
                        fill='none',
                        stroke_width=0.8,
                        stroke_linecap='round',
                        stroke_linejoin='round'
                    ))

        dwg.save()
        print(f"   ✅ Saved: {filename} ({len(smoothed_paths)} paths" +
              (f", {len(closed_contours)} filled)" if fill_small_areas else ")"))
        return os.path.join(self.output_dir, filename)

    def _generate_zigzag_fills(self, closed_contours, spacing=5):
        """
        Generate continuous zigzag fill patterns for small closed areas

        Strategy:
        1. For each closed contour, draw the outline
        2. Generate horizontal zigzag lines inside
        3. Connect zigzag to outline for continuous drawing (no pen lift)

        Args:
            closed_contours: List of closed contour dicts
            spacing: Spacing between zigzag lines (pixels)

        Returns:
            List of polylines (each is a continuous path: outline + zigzag)
        """
        zigzag_paths = []

        for contour_data in closed_contours:
            contour = contour_data['contour']
            points = contour_data['points']

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Generate horizontal zigzag lines
            zigzag_points = []

            # Start from outline's first point
            zigzag_points.append(points[0])

            # Generate zigzag inside the contour
            y_current = y + spacing
            direction = 1  # 1 = left to right, -1 = right to left

            while y_current < y + h:
                # Find intersections with contour at this y level
                intersections = []

                for i in range(len(contour)):
                    pt1 = tuple(contour[i][0])
                    pt2 = tuple(contour[(i + 1) % len(contour)][0])

                    # Check if horizontal line at y_current intersects this edge
                    if (pt1[1] <= y_current <= pt2[1]) or (pt2[1] <= y_current <= pt1[1]):
                        if pt2[1] != pt1[1]:  # Avoid division by zero
                            # Calculate x intersection
                            t = (y_current - pt1[1]) / (pt2[1] - pt1[1])
                            x_intersect = int(pt1[0] + t * (pt2[0] - pt1[0]))
                            intersections.append(x_intersect)

                # Sort intersections
                intersections = sorted(set(intersections))

                # Add zigzag points (alternate direction)
                if len(intersections) >= 2:
                    if direction == 1:
                        # Left to right
                        zigzag_points.append((intersections[0], y_current))
                        zigzag_points.append((intersections[-1], y_current))
                    else:
                        # Right to left
                        zigzag_points.append((intersections[-1], y_current))
                        zigzag_points.append((intersections[0], y_current))

                    direction *= -1  # Flip direction

                y_current += spacing

            # Close by connecting back to start if needed
            if len(zigzag_points) > 1:
                # Add outline points to make it continuous
                # Ensure all points are tuples (x, y)
                validated_points = []
                for pt in points:
                    if isinstance(pt, tuple) and len(pt) == 2:
                        validated_points.append(pt)

                for pt in zigzag_points:
                    if isinstance(pt, tuple) and len(pt) == 2:
                        validated_points.append(pt)

                if len(validated_points) > 1:
                    zigzag_paths.append(validated_points)

        return zigzag_paths

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
                        current_path.extend(candidate['points'][1:])
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
        """Smooth a polyline using Gaussian filter on coordinates."""
        if len(points) < 3:
            return points

        x_coords = np.array([p[0] for p in points], dtype=float)
        y_coords = np.array([p[1] for p in points], dtype=float)

        x_smooth = ndimage.gaussian_filter1d(x_coords, sigma=sigma, mode='nearest')
        y_smooth = ndimage.gaussian_filter1d(y_coords, sigma=sigma, mode='nearest')

        smoothed = [(int(x), int(y)) for x, y in zip(x_smooth, y_smooth)]
        return smoothed

    def _optimize_path_order(self, polylines):
        """
        Optimize drawing order using greedy nearest-neighbor.
        """
        if not polylines:
            return []

        ordered = []
        remaining = polylines.copy()

        current = remaining.pop(0)
        ordered.append(current)
        current_end = current[-1]

        while remaining:
            min_dist = float('inf')
            best_idx = 0
            best_reverse = False

            for idx, poly in enumerate(remaining):
                dist_start = self._point_distance(current_end, poly[0])
                if dist_start < min_dist:
                    min_dist = dist_start
                    best_idx = idx
                    best_reverse = False

                dist_end = self._point_distance(current_end, poly[-1])
                if dist_end < min_dist:
                    min_dist = dist_end
                    best_idx = idx
                    best_reverse = True

            next_poly = remaining.pop(best_idx)
            if best_reverse:
                next_poly = list(reversed(next_poly))

            ordered.append(next_poly)
            current_end = next_poly[-1]

        return ordered

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
thick_joining_variations = ThickJoiningVariations()
