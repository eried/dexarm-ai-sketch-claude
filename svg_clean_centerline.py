"""
Clean Centerline SVG Generator
===============================
Extracts clean centerlines from images using morphological skeletonization.
Avoids double lines on thick strokes by finding the medial axis.

Key Features:
- Single clean lines for thick strokes (no double outlines)
- Connected fill patterns for very thick areas
- Multiple parameter variations for testing
"""

import cv2
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize, medial_axis
import svgwrite
import os


class CleanCenterlineGenerator:
    """Generate clean SVG using centerline extraction"""

    def __init__(self):
        self.output_dir = 'svgs'
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_variations(self, image_path, base_filename):
        """
        Generate clean centerline variations

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
        print("Generating Clean Centerline Variations")
        print("="*70)

        # V1: Basic skeletonization with light smoothing
        print("\nV1: Basic skeleton (light smooth, clean lines)")
        filename = f"{base_filename}_clean_v1.svg"
        results['clean_v1'] = self._centerline_base(
            img, width, height, filename,
            threshold_method='adaptive',
            smooth_sigma=0.5,
            min_segment_length=3,
            add_fill=False
        )

        # V2: Moderate smoothing with longer segments
        print("\nV2: Moderate smooth (balanced detail/cleanup)")
        filename = f"{base_filename}_clean_v2.svg"
        results['clean_v2'] = self._centerline_base(
            img, width, height, filename,
            threshold_method='adaptive',
            smooth_sigma=0.8,
            min_segment_length=6,
            add_fill=False
        )

        # V3: Skeleton with connected fill for thick areas
        print("\nV3: Skeleton + connected fill (thick areas hatched)")
        filename = f"{base_filename}_clean_v3.svg"
        results['clean_v3'] = self._centerline_base(
            img, width, height, filename,
            threshold_method='adaptive',
            smooth_sigma=0.8,
            min_segment_length=3,
            add_fill=True,
            fill_threshold=15  # Thick areas > 15px get fill
        )

        print("\n" + "="*70)
        print(f"Generated {len(results)} clean centerline variations!")
        print("="*70 + "\n")

        return results

    def _centerline_base(self, img, width, height, filename,
                        threshold_method='adaptive',
                        smooth_sigma=1.0,
                        min_segment_length=3,
                        add_fill=False,
                        fill_threshold=15):
        """
        Base centerline extraction method

        Args:
            threshold_method: 'adaptive' or 'otsu'
            smooth_sigma: Gaussian smoothing for skeleton
            min_segment_length: Minimum pixels to keep a segment
            add_fill: Whether to add fill patterns for thick areas
            fill_threshold: Minimum thickness (px) to add fill pattern
        """
        dwg = svgwrite.Drawing(
            os.path.join(self.output_dir, filename),
            size=(f'{width}px', f'{height}px'),
            viewBox=f'0 0 {width} {height}'
        )

        # 1. Threshold the image to get binary mask
        if threshold_method == 'adaptive':
            # Adaptive threshold - good for varying lighting
            blurred = cv2.GaussianBlur(img, (5, 5), 1.0)
            binary = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                21, 5
            )
        else:
            # Otsu's method - automatic global threshold
            blurred = cv2.GaussianBlur(img, (5, 5), 1.0)
            _, binary = cv2.threshold(
                blurred, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

        # 2. Clean up binary image
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 3. Get distance transform for thickness-aware processing
        binary_bool = binary > 0
        distance = ndimage.distance_transform_edt(binary_bool)

        # 4. Extract skeleton using medial axis
        skeleton, dist_on_skel = medial_axis(binary_bool, return_distance=True)

        # Smooth the skeleton slightly
        if smooth_sigma > 0:
            skeleton_float = skeleton.astype(float)
            skeleton_smooth = ndimage.gaussian_filter(skeleton_float, sigma=smooth_sigma)
            skeleton = skeleton_smooth > 0.5

        # 5. Convert skeleton to polylines
        skeleton_uint8 = (skeleton * 255).astype(np.uint8)
        contours, hierarchy = cv2.findContours(
            skeleton_uint8, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS
        )

        # 6. Process contours into polylines
        polylines = []
        thick_areas = []  # Areas that need fill patterns

        for contour in contours:
            if len(contour) < min_segment_length:
                continue

            # Simplify slightly
            epsilon = 0.5
            simplified = cv2.approxPolyDP(contour, epsilon, False)

            if len(simplified) > 1:
                # Convert to plain Python ints to avoid svgwrite type errors
                points = [(int(pt[0][0]), int(pt[0][1])) for pt in simplified]

                # Check if this is a thick area (average distance > threshold)
                if add_fill and len(contour) > 0:
                    # Sample thickness along this contour
                    thicknesses = []
                    for pt in contour[::max(1, len(contour)//10)]:  # Sample 10 points
                        y, x = pt[0][1], pt[0][0]
                        if 0 <= y < distance.shape[0] and 0 <= x < distance.shape[1]:
                            thicknesses.append(distance[y, x])

                    avg_thickness = np.mean(thicknesses) if thicknesses else 0

                    if avg_thickness > fill_threshold:
                        # Mark as thick area for fill pattern
                        thick_areas.append({
                            'contour': contour,
                            'thickness': avg_thickness,
                            'points': points
                        })
                        continue  # Don't draw outline, just fill

                polylines.append(points)

        # 7. Optimize drawing order
        if polylines:
            ordered_polylines = self._optimize_path_order(polylines)

            # Draw polylines
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

        # 8. Add fill patterns for thick areas
        if add_fill and thick_areas:
            print(f"   Adding fill to {len(thick_areas)} thick areas...")
            fill_polylines = self._generate_connected_fill(thick_areas, distance, spacing=4)

            for points in fill_polylines:
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
        print(f"   Saved: {filename} ({len(polylines)} lines" +
              (f", {len(thick_areas)} filled)" if add_fill else ")"))
        return os.path.join(self.output_dir, filename)

    def _generate_connected_fill(self, thick_areas, distance_map, spacing=4):
        """
        Generate connected fill patterns for thick areas

        Strategy:
        - Use the distance transform to find the "thick" regions
        - Generate hatching lines that follow the shape
        - Connect hatching to make continuous paths (reduce pen lifts)

        Args:
            thick_areas: List of thick area dicts
            distance_map: Distance transform of binary image
            spacing: Spacing between hatch lines (pixels)

        Returns:
            List of polylines for fill patterns
        """
        fill_polylines = []

        for area in thick_areas:
            contour = area['contour']
            thickness = area['thickness']

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Create mask for this area
            mask = np.zeros(distance_map.shape, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)

            # Generate diagonal hatching
            hatch_points = []

            # Diagonal lines from top-left to bottom-right
            for offset in range(-max(w, h), max(w, h), spacing):
                line_points = []

                for i in range(max(w, h)):
                    px = x + i
                    py = y + i + offset

                    if (0 <= px < mask.shape[1] and
                        0 <= py < mask.shape[0] and
                        mask[py, px] > 0):
                        line_points.append((int(px), int(py)))

                if len(line_points) > 3:  # Only keep substantial lines
                    hatch_points.extend(line_points)
                    # Add separator to break between lines
                    hatch_points.append(None)

            # Convert to polylines (continuous where possible)
            current_poly = []
            for pt in hatch_points:
                if pt is None:
                    if len(current_poly) > 1:
                        fill_polylines.append(current_poly)
                    current_poly = []
                else:
                    current_poly.append(pt)

            if len(current_poly) > 1:
                fill_polylines.append(current_poly)

        return fill_polylines

    def _optimize_path_order(self, polylines):
        """
        Optimize drawing order using greedy nearest-neighbor
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
        """Calculate Euclidean distance between two points"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


# Global instance
clean_centerline_generator = CleanCenterlineGenerator()
