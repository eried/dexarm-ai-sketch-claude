"""
DexArm Shape Drawing Test
==========================
This script tests drawing basic shapes: square, circle, and star.

SETUP REQUIRED:
- Run 02_pen_test.py first to calibrate Z-heights
- Update Z_UP and Z_DOWN constants below with calibrated values
- Place paper on work surface

Usage:
    python 03_shape_drawing.py [PORT] [shape]

Shapes: square, circle, star, all (default)

Example:
    python 03_shape_drawing.py COM3 square
    python 03_shape_drawing.py COM3 all
"""

import sys
import time
import math
from dexarm import Dexarm

# Z-axis heights (UPDATE THESE after running 02_pen_test.py --calibrate)
Z_UP = 10        # Pen up height (mm)
Z_DOWN = -3      # Pen down height for drawing (mm)

# Drawing parameters
DRAW_SPEED = 2000   # Speed for drawing movements (mm/min)
MOVE_SPEED = 3000   # Speed for non-drawing movements (mm/min)

def pen_up(dexarm, x, y):
    """Lift pen up"""
    dexarm.fast_move_to(x, y, Z_UP)
    time.sleep(0.3)

def pen_down(dexarm, x, y):
    """Put pen down"""
    dexarm.fast_move_to(x, y, Z_DOWN)
    time.sleep(0.3)

def draw_square(dexarm, center_x, center_y, size=40):
    """Draw a square"""
    print(f"  Drawing square at ({center_x}, {center_y}), size={size}mm")

    half = size / 2

    # Calculate corners
    corners = [
        (center_x - half, center_y - half),  # Bottom-left
        (center_x + half, center_y - half),  # Bottom-right
        (center_x + half, center_y + half),  # Top-right
        (center_x - half, center_y + half),  # Top-left
        (center_x - half, center_y - half),  # Back to start
    ]

    # Move to start position (pen up)
    pen_up(dexarm, corners[0][0], corners[0][1])

    # Put pen down
    pen_down(dexarm, corners[0][0], corners[0][1])

    # Draw the square
    for x, y in corners[1:]:
        dexarm.fast_move_to(x, y, Z_DOWN)
        time.sleep(0.2)

    # Pen up
    pen_up(dexarm, corners[0][0], corners[0][1])

def draw_circle(dexarm, center_x, center_y, radius=20, segments=36):
    """Draw a circle"""
    print(f"  Drawing circle at ({center_x}, {center_y}), radius={radius}mm")

    # Generate circle points
    points = []
    for i in range(segments + 1):
        angle = (2 * math.pi * i) / segments
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Move to start position (pen up)
    pen_up(dexarm, points[0][0], points[0][1])

    # Put pen down
    pen_down(dexarm, points[0][0], points[0][1])

    # Draw the circle
    for x, y in points[1:]:
        dexarm.fast_move_to(x, y, Z_DOWN)
        time.sleep(0.05)

    # Pen up
    pen_up(dexarm, points[0][0], points[0][1])

def draw_star(dexarm, center_x, center_y, outer_radius=30, inner_radius=12):
    """Draw a 5-pointed star"""
    print(f"  Drawing star at ({center_x}, {center_y})")

    points = []
    for i in range(10):
        angle = (2 * math.pi * i) / 10 - math.pi / 2  # Start at top
        radius = outer_radius if i % 2 == 0 else inner_radius
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Close the star
    points.append(points[0])

    # Move to start position (pen up)
    pen_up(dexarm, points[0][0], points[0][1])

    # Put pen down
    pen_down(dexarm, points[0][0], points[0][1])

    # Draw the star
    for x, y in points[1:]:
        dexarm.fast_move_to(x, y, Z_DOWN)
        time.sleep(0.1)

    # Pen up
    pen_up(dexarm, points[0][0], points[0][1])

def test_shapes(port, shape='all'):
    """Test drawing shapes"""

    print(f"\n🔌 Connecting to DexArm on {port}...")

    try:
        dexarm = Dexarm(port=port)
        print("✅ Connected!")

        # Home first
        print("\n🏠 Homing...")
        dexarm.go_home()
        time.sleep(2)

        print(f"\n✏️  Drawing shapes (Z_UP={Z_UP}, Z_DOWN={Z_DOWN})...")

        # Define positions for different shapes
        # Adjust these based on your paper placement
        positions = {
            'square': (150, -50),
            'circle': (200, 0),
            'star': (250, 50),
        }

        if shape == 'all' or shape == 'square':
            print("\n📦 Drawing Square...")
            draw_square(dexarm, positions['square'][0], positions['square'][1])

        if shape == 'all' or shape == 'circle':
            print("\n⭕ Drawing Circle...")
            draw_circle(dexarm, positions['circle'][0], positions['circle'][1])

        if shape == 'all' or shape == 'star':
            print("\n⭐ Drawing Star...")
            draw_star(dexarm, positions['star'][0], positions['star'][1])

        # Return to home
        print("\n🏠 Returning to home...")
        dexarm.go_home()
        time.sleep(1)

        print("\n✅ Drawing complete!")
        print("\n📸 Check your paper for the drawn shapes!")

        dexarm.close()
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 03_shape_drawing.py [PORT] [shape]")
        print("Shapes: square, circle, star, all (default)")
        print("Example: python 03_shape_drawing.py COM3 all")
        sys.exit(1)

    port = sys.argv[1]
    shape = sys.argv[2] if len(sys.argv) > 2 else 'all'

    if shape not in ['square', 'circle', 'star', 'all']:
        print(f"Invalid shape: {shape}")
        print("Valid shapes: square, circle, star, all")
        sys.exit(1)

    print("=" * 50)
    print("DexArm Shape Drawing Test")
    print("=" * 50)
    print(f"⚠️  Make sure paper is placed on the work surface!")
    print(f"⚠️  Z-heights: UP={Z_UP}mm, DOWN={Z_DOWN}mm")
    print()
    input("Press Enter to continue...")

    success = test_shapes(port, shape)
    sys.exit(0 if success else 1)
