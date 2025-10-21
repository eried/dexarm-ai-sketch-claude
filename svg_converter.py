"""
Image to SVG Converter
======================
Converts raster images to SVG line drawings for robot arm drawing.
"""

import os
import subprocess
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import svgwrite


class SVGConverter:
    """Converts images to SVG line drawings"""

    def __init__(self):
        pass

    def image_to_svg(self, image_path, output_path=None, method='potrace', generate_all_versions=False):
        """
        Convert image to SVG line drawing

        Args:
            image_path (str): Path to input image
            output_path (str): Path for output SVG (optional)
            method (str): Conversion method ('potrace' or 'edges')
            generate_all_versions (bool): If True, generate all 10 versions for comparison

        Returns:
            str: Path to generated SVG file (main version)
        """
        if output_path is None:
            base = os.path.splitext(image_path)[0]
            output_path = f"{base}_lineart.svg"

        # Generate all 10 versions if requested
        if generate_all_versions:
            print("\n🎨 Generating 10 different SVG versions for comparison...")
            base = os.path.splitext(output_path)[0]

            for version in range(10):
                version_output = f"{base}_version{version}.svg"
                try:
                    self._generate_version(image_path, version_output, version)
                    print(f"✅ Version {version} complete: {version_output}")
                except Exception as e:
                    print(f"❌ Version {version} failed: {e}")

            print(f"\n✅ All versions generated! Main file: {output_path}")
            # Return version 8 as default (contour-following hatching with long lines)
            return f"{base}_version8.svg"

        # Single version generation - always use version 8
        print(f"Generating Version 8 (contour-following hatching)...")
        self._generate_version(image_path, output_path, version=8)
        print(f"✅ Version 8 generated: {output_path}")
        return output_path

    def _generate_version(self, image_path, output_path, version):
        """
        Generate specific version of SVG

        Args:
            image_path (str): Input image path
            output_path (str): Output SVG path
            version (int): Version number (0-9)
        """
        import cv2
        import numpy as np
        import svgwrite

        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        img = cv2.equalizeHist(img)  # Enhance contrast

        # Create SVG
        height, width = img.shape
        dwg = svgwrite.Drawing(output_path, size=(f'{width}px', f'{height}px'))
        dwg.viewbox(width=width, height=height)

        if version == 0:
            # Version 0: Contours with horizontal hatching in dark areas
            edges = cv2.Canny(img, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add horizontal hatching in dark areas
            self._add_hatching(dwg, img, 'horizontal', spacing=8)

        elif version == 1:
            # Version 1: Sobel edge detection (user's favorite from old v7)
            sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.uint8(np.sqrt(sobelx**2 + sobely**2))
            _, edges = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)

        elif version == 2:
            # Version 2: Edges with cross-hatching in shadows
            edges = cv2.Canny(img, 40, 120)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.5)
            # Add cross-hatching
            self._add_hatching(dwg, img, 'cross', spacing=10)

        elif version == 3:
            # Version 3: Edges with diagonal scribbles in dark areas
            edges = cv2.Canny(img, 45, 135)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add diagonal scribbles
            self._add_scribbles(dwg, img, angle=45, density=15)

        elif version == 4:
            # Version 4: Edges with stippling/dots in shadows
            edges = cv2.Canny(img, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add stippling
            self._add_stippling(dwg, img, density=0.3)

        elif version == 5:
            # Version 5: Edges with concentric circles in dark areas
            edges = cv2.Canny(img, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add circular scribbles
            self._add_circular_scribbles(dwg, img, radius=8, spacing=20)

        elif version == 6:
            # Version 6: Edges with wavy horizontal lines in shadows
            edges = cv2.Canny(img, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add wavy lines
            self._add_wavy_hatching(dwg, img, spacing=10, amplitude=3)

        elif version == 7:
            # Version 7: Laplacian edges with random scribbles
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            edges = np.uint8(np.absolute(laplacian))
            _, edges = cv2.threshold(edges, 30, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add random scribbles
            self._add_scribbles(dwg, img, angle='random', density=20)

        elif version == 8:
            # Version 8: Edges with contour following hatching
            edges = cv2.Canny(img, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.0)
            # Add contour-following lines
            self._add_contour_hatching(dwg, img, contours, spacing=8)

        elif version == 9:
            # Version 9: Thick edges with dense diagonal hatching
            img_blur = cv2.GaussianBlur(img, (3, 3), 0)
            edges = cv2.Canny(img_blur, 40, 120)
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            self._add_contours_to_svg(dwg, contours, 2.5)
            # Add dense hatching
            self._add_hatching(dwg, img, 'diagonal', spacing=6)

        dwg.save()
        return output_path

    def _add_contours_to_svg(self, dwg, contours, epsilon):
        """Add contour paths to SVG"""
        import cv2
        min_length = 20
        contours = [c for c in contours if cv2.arcLength(c, False) > min_length]

        for contour in contours:
            approx = cv2.approxPolyDP(contour, epsilon, False)
            if len(approx) < 2:
                continue

            path_data = []
            for i, point in enumerate(approx):
                x, y = point[0]
                if i == 0:
                    path_data.append(f'M {x},{y}')
                else:
                    path_data.append(f'L {x},{y}')

            if path_data:
                path_str = ' '.join(path_data)
                dwg.add(dwg.path(
                    d=path_str,
                    stroke='black',
                    fill='none',
                    stroke_width=1.0,
                    stroke_linecap='round',
                    stroke_linejoin='round'
                ))

    def _add_hatching(self, dwg, img, direction='horizontal', spacing=10):
        """Add hatching lines in dark areas"""
        import numpy as np
        height, width = img.shape

        for y in range(0, height, spacing):
            for x in range(0, width, spacing):
                if img[y, x] < 100:  # Dark area
                    if direction == 'horizontal':
                        x2 = min(x + spacing - 2, width - 1)
                        dwg.add(dwg.line((x, y), (x2, y), stroke='black', stroke_width=0.5))
                    elif direction == 'diagonal':
                        x2 = min(x + spacing - 2, width - 1)
                        y2 = min(y + spacing - 2, height - 1)
                        dwg.add(dwg.line((x, y), (x2, y2), stroke='black', stroke_width=0.5))
                    elif direction == 'cross':
                        x2 = min(x + spacing - 2, width - 1)
                        y2 = min(y + spacing - 2, height - 1)
                        dwg.add(dwg.line((x, y), (x2, y), stroke='black', stroke_width=0.5))
                        dwg.add(dwg.line((x, y), (x, y2), stroke='black', stroke_width=0.5))

    def _add_scribbles(self, dwg, img, angle=45, density=15):
        """Add scribble lines in dark areas"""
        import numpy as np
        height, width = img.shape

        for y in range(0, height, density):
            for x in range(0, width, density):
                if img[y, x] < 100:  # Dark area
                    if angle == 'random':
                        import random
                        a = random.randint(0, 360)
                    else:
                        a = angle

                    length = density - 2
                    rad = np.radians(a)
                    x2 = int(x + length * np.cos(rad))
                    y2 = int(y + length * np.sin(rad))

                    if 0 <= x2 < width and 0 <= y2 < height:
                        dwg.add(dwg.line((x, y), (x2, y2), stroke='black', stroke_width=0.5))

    def _add_stippling(self, dwg, img, density=0.3):
        """Add dots in dark areas"""
        import numpy as np
        height, width = img.shape

        for y in range(0, height, 3):
            for x in range(0, width, 3):
                if img[y, x] < 100:  # Dark area
                    import random
                    if random.random() < density:
                        dwg.add(dwg.circle((x, y), r=0.5, fill='black'))

    def _add_circular_scribbles(self, dwg, img, radius=8, spacing=20):
        """Add small circular scribbles in dark areas"""
        import numpy as np
        height, width = img.shape

        for y in range(0, height, spacing):
            for x in range(0, width, spacing):
                if img[y, x] < 100:  # Dark area
                    dwg.add(dwg.circle((x, y), r=radius * 0.5,
                                     stroke='black', fill='none', stroke_width=0.5))

    def _add_wavy_hatching(self, dwg, img, spacing=10, amplitude=3):
        """Add wavy horizontal lines in dark areas"""
        import numpy as np
        height, width = img.shape

        for y in range(0, height, spacing):
            path_data = []
            in_dark_region = False

            for x in range(0, width, 2):
                if img[y, x] < 100:  # Dark area
                    wave_y = y + amplitude * np.sin(x * 0.1)
                    if not in_dark_region:
                        path_data.append(f'M {x},{wave_y}')
                        in_dark_region = True
                    else:
                        path_data.append(f'L {x},{wave_y}')
                else:
                    in_dark_region = False

            if path_data:
                path_str = ' '.join(path_data)
                dwg.add(dwg.path(d=path_str, stroke='black', fill='none', stroke_width=0.5))

    def _add_contour_hatching(self, dwg, img, contours, spacing=8):
        """Add hatching that follows contours in dark areas"""
        import cv2
        import numpy as np

        # Create a distance transform from edges
        edge_img = np.zeros_like(img)
        cv2.drawContours(edge_img, contours, -1, 255, 1)
        dist_transform = cv2.distanceTransform(cv2.bitwise_not(edge_img), cv2.DIST_L2, 3)

        height, width = img.shape

        for y in range(0, height, spacing):
            for x in range(0, width, spacing):
                if img[y, x] < 100:  # Dark area
                    # Calculate gradient direction from distance transform
                    if x > 0 and x < width-1 and y > 0 and y < height-1:
                        dx = dist_transform[y, x+1] - dist_transform[y, x-1]
                        dy = dist_transform[y+1, x] - dist_transform[y-1, x]
                        angle = np.arctan2(dy, dx)

                        # 3x longer lines for better shading effect
                        length = (spacing - 2) * 3
                        x2 = int(x + length * np.cos(angle))
                        y2 = int(y + length * np.sin(angle))

                        if 0 <= x2 < width and 0 <= y2 < height:
                            dwg.add(dwg.line((x, y), (x2, y2), stroke='black', stroke_width=0.5))

    def _convert_with_potrace(self, image_path, output_path):
        """
        Convert using potrace (produces smoother curves)

        Requires potrace to be installed:
        - Windows: Download from http://potrace.sourceforge.net
        - Linux: apt-get install potrace
        - Mac: brew install potrace

        Args:
            image_path (str): Input image path
            output_path (str): Output SVG path

        Returns:
            str: Output SVG path
        """
        # Preprocess image to black and white
        img = Image.open(image_path)
        img = img.convert('L')  # Convert to grayscale

        # Enhance contrast and detect edges
        img = ImageOps.autocontrast(img, cutoff=2)
        img = img.filter(ImageFilter.FIND_EDGES)
        img = ImageOps.invert(img)

        # Threshold to pure black and white
        threshold = 128
        img = img.point(lambda p: 255 if p > threshold else 0, mode='1')

        # Save as PBM for potrace
        pbm_path = output_path.replace('.svg', '.pbm')
        img.save(pbm_path)

        try:
            # Run potrace
            subprocess.run([
                'potrace',
                pbm_path,
                '-s',  # SVG output
                '-o', output_path,
                '--tight',  # Tight bounding box
                '--blacklevel', '0.5'
            ], check=True)

            # Clean up temporary file
            os.remove(pbm_path)

            return output_path

        except FileNotFoundError:
            print("Potrace not found. Falling back to edge detection method.")
            return self._convert_with_edges(image_path, output_path)

        except Exception as e:
            print(f"Potrace conversion failed: {e}")
            if os.path.exists(pbm_path):
                os.remove(pbm_path)
            return self._convert_with_edges(image_path, output_path)

    def _convert_with_edges(self, image_path, output_path):
        """
        Convert using skeletonization for cleaner strokes
        This creates drawing-like centerline paths instead of edge detection.

        Args:
            image_path (str): Input image path
            output_path (str): Output SVG path

        Returns:
            str: Output SVG path
        """
        import cv2
        import numpy as np
        from skimage.morphology import skeletonize
        from skimage import img_as_ubyte

        print(f"Converting {image_path} to SVG using skeletonization...")

        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        # Enhance contrast
        img = cv2.equalizeHist(img)

        # Detect edges using Canny
        edges = cv2.Canny(img, 50, 150)

        # Invert (skeletonize works on white areas)
        edges_inv = cv2.bitwise_not(edges)

        # Apply morphological closing to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        edges_inv = cv2.morphologyEx(edges_inv, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Convert to binary (0 or 1)
        binary = edges_inv > 128

        # Skeletonize to get centerlines (this creates clean single-pixel strokes)
        skeleton = skeletonize(binary)

        # Convert back to uint8
        skeleton_img = img_as_ubyte(skeleton)

        # Find contours on the skeleton
        contours, _ = cv2.findContours(skeleton_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        print(f"Found {len(contours)} skeleton paths")

        # Filter out very small contours (noise)
        min_contour_length = 30
        contours = [c for c in contours if cv2.arcLength(c, False) > min_contour_length]

        print(f"After filtering: {len(contours)} paths")

        # Create SVG
        height, width = img.shape
        dwg = svgwrite.Drawing(output_path, size=(f'{width}px', f'{height}px'))
        dwg.viewbox(width=width, height=height)

        # Convert contours to SVG paths with aggressive simplification
        for contour in contours:
            # Aggressive simplification for smoother, cleaner strokes
            epsilon = 5.0  # Higher value = smoother, fewer points
            approx = cv2.approxPolyDP(contour, epsilon, False)

            # Skip very small contours
            if len(approx) < 2:
                continue

            # Build path data
            path_data = []
            for i, point in enumerate(approx):
                x, y = point[0]
                if i == 0:
                    path_data.append(f'M {x},{y}')  # Move to start
                else:
                    path_data.append(f'L {x},{y}')  # Line to point

            # Create path element
            if path_data:
                path_str = ' '.join(path_data)
                dwg.add(dwg.path(
                    d=path_str,
                    stroke='black',
                    fill='none',
                    stroke_width=1.5,
                    stroke_linecap='round',
                    stroke_linejoin='round'
                ))

        dwg.save()
        print(f"SVG saved with {len(contours)} clean stroke paths")
        return output_path

    def optimize_for_drawing(self, svg_path, output_path=None, drawing_area=None):
        """
        Optimize SVG for robot arm drawing
        - Join nearby path segments into continuous lines
        - Auto-rotate if SVG orientation doesn't match drawing area
        - Simplify and clean up paths

        Args:
            svg_path (str): Input SVG path
            output_path (str): Output SVG path (optional)
            drawing_area (dict): Drawing area dimensions {'width': float, 'height': float}

        Returns:
            str: Optimized SVG path
        """
        if output_path is None:
            output_path = svg_path.replace('.svg', '_optimized.svg')

        import xml.etree.ElementTree as ET
        import math

        # Parse the SVG
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Get SVG dimensions
        viewbox = root.get('viewBox')
        if viewbox:
            # Handle both comma and space separated viewBox formats
            parts = viewbox.replace(',', ' ').split()
            if len(parts) >= 4:
                svg_width = float(parts[2])
                svg_height = float(parts[3])
            else:
                # Fallback to width/height attributes
                svg_width = float(root.get('width', '100').replace('px', ''))
                svg_height = float(root.get('height', '100').replace('px', ''))
        else:
            svg_width = float(root.get('width', '100').replace('px', ''))
            svg_height = float(root.get('height', '100').replace('px', ''))

        print(f"📐 Original SVG: {svg_width} x {svg_height}")

        # Auto-rotate if needed to fit drawing area better
        if drawing_area:
            area_width = drawing_area['width']
            area_height = drawing_area['height']

            svg_is_portrait = svg_height > svg_width
            area_is_portrait = area_height > area_width

            # Rotate 90 degrees only if orientations don't match (portrait vs landscape)
            should_rotate = svg_is_portrait != area_is_portrait

            if should_rotate:
                orientation = "portrait" if svg_is_portrait else "landscape"
                area_orientation = "portrait" if area_is_portrait else "landscape"
                print(f"🔄 Rotating {orientation} SVG 90° to fit {area_orientation} drawing area")
                self._rotate_svg_90(root, svg_width, svg_height)
                # Swap dimensions after rotation
                svg_width, svg_height = svg_height, svg_width

                # Update viewBox
                if viewbox:
                    parts = viewbox.replace(',', ' ').split()
                    if len(parts) >= 4:
                        root.set('viewBox', f"{parts[0]},{parts[1]},{svg_width},{svg_height}")
                root.set('width', f"{svg_width}px")
                root.set('height', f"{svg_height}px")
            else:
                print(f"✅ SVG orientation matches drawing area - no rotation needed")

        # Join nearby paths into continuous lines
        print("🔗 Joining nearby path segments...")
        self._join_nearby_paths(root)

        # Save optimized SVG
        tree.write(output_path, encoding='unicode', xml_declaration=True)
        print(f"✅ Optimized SVG saved: {output_path}")

        return output_path

    def _rotate_svg_90(self, root, width, height):
        """
        Rotate all paths in SVG by 90 degrees clockwise

        Args:
            root: SVG root element
            width: Original SVG width
            height: Original SVG height
        """
        # Rotation matrix for 90° clockwise: (x, y) -> (y, width - x)
        # We use a transform attribute for simplicity

        # Find all path elements
        for elem in root.iter():
            if elem.tag.endswith('path'):
                # Add transform to rotate 90° clockwise around center
                # rotate(90, cx, cy) where cx, cy is the center
                transform = f"rotate(90 {width/2} {height/2})"
                existing_transform = elem.get('transform', '')
                if existing_transform:
                    elem.set('transform', f"{existing_transform} {transform}")
                else:
                    elem.set('transform', transform)

    def _join_nearby_paths(self, root):
        """
        Join path segments that have endpoints close to each other

        Args:
            root: SVG root element
        """
        import re

        # Extract all path elements
        paths = []
        for elem in root.iter():
            if elem.tag.endswith('path'):
                d = elem.get('d')
                if d:
                    paths.append({'elem': elem, 'd': d})

        if len(paths) < 2:
            return

        # Parse path data to get endpoints
        path_data = []
        for p in paths:
            coords = self._extract_path_endpoints(p['d'])
            if coords:
                path_data.append({
                    'elem': p['elem'],
                    'd': p['d'],
                    'start': coords['start'],
                    'end': coords['end']
                })

        # Join nearby paths (within 5 pixel threshold)
        threshold = 5.0
        joined_count = 0

        i = 0
        while i < len(path_data):
            j = i + 1
            while j < len(path_data):
                # Check if end of path i is near start of path j
                dist = self._distance(path_data[i]['end'], path_data[j]['start'])
                if dist < threshold:
                    # Join path j to path i
                    path_data[i]['d'] = self._join_path_strings(path_data[i]['d'], path_data[j]['d'])
                    path_data[i]['end'] = path_data[j]['end']

                    # Remove path j from SVG
                    root.remove(path_data[j]['elem'])

                    # Update path i in SVG
                    path_data[i]['elem'].set('d', path_data[i]['d'])

                    # Remove path j from our list
                    path_data.pop(j)
                    joined_count += 1
                    continue  # Don't increment j, check the next path

                j += 1
            i += 1

        if joined_count > 0:
            print(f"✅ Joined {joined_count} path segments")

    def _extract_path_endpoints(self, d):
        """Extract start and end coordinates from path data"""
        import re

        # Find all coordinates in the path
        # Match M, L commands and their coordinates
        coords = []
        parts = d.split()

        i = 0
        while i < len(parts):
            part = parts[i]
            if part in ['M', 'L', 'm', 'l']:
                # Next part should be coordinates
                if i + 1 < len(parts):
                    coord_str = parts[i + 1]
                    if ',' in coord_str:
                        x, y = coord_str.split(',')
                        coords.append((float(x), float(y)))
                i += 2
            else:
                i += 1

        if len(coords) >= 2:
            return {'start': coords[0], 'end': coords[-1]}
        return None

    def _distance(self, p1, p2):
        """Calculate Euclidean distance between two points"""
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

    def _join_path_strings(self, d1, d2):
        """
        Join two path strings by connecting the end of d1 to the start of d2

        Args:
            d1: First path data string
            d2: Second path data string

        Returns:
            str: Combined path string
        """
        # Remove the M (move) command from the start of d2
        # since we're continuing from d1
        d2_parts = d2.split()

        # Skip the first M command and its coordinates
        if d2_parts[0] in ['M', 'm']:
            d2_parts = d2_parts[2:]  # Skip M and coordinates

        # Join with a line command
        return f"{d1} L {' '.join(d2_parts)}"


# Global converter instance
svg_converter = SVGConverter()
