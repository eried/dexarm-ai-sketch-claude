"""
DexArm Pen Up/Down Test
========================
This script tests pen/marker control (Z-axis movement).

IMPORTANT: Make sure you have:
- Pen/marker attachment installed
- Paper positioned on the work surface
- Appropriate Z-height calibrated

Usage:
    python 02_pen_test.py [PORT]
"""

import sys
import time
from dexarm import Dexarm

# Z-axis heights (adjust these based on your setup)
PEN_UP_HEIGHT = 10      # Z height when pen is up (mm above paper)
PEN_DOWN_HEIGHT = -5    # Z height when pen touches paper (adjust carefully!)
DRAWING_HEIGHT = -3     # Z height for actual drawing (light pressure)

def test_pen_control(port):
    """Test pen up/down movements"""

    print(f"\n🔌 Connecting to DexArm on {port}...")

    try:
        dexarm = Dexarm(port=port)
        print("✅ Connected!")

        # Home first
        print("\n🏠 Homing...")
        dexarm.go_home()
        time.sleep(2)

        # Move to a safe starting position
        print("\n📍 Moving to starting position...")
        start_x, start_y = 200, 0  # Center front of workspace
        dexarm.fast_move_to(start_x, start_y, PEN_UP_HEIGHT)
        time.sleep(1)

        print("\n✏️  Testing pen control...")
        print("Watch the pen/marker attachment carefully!")
        print()

        # Test 1: Pen down and up
        print("Test 1: Pen Down")
        print(f"  Lowering to Z={DRAWING_HEIGHT}mm...")
        dexarm.fast_move_to(start_x, start_y, DRAWING_HEIGHT)
        time.sleep(2)

        print("  Pen Up")
        print(f"  Raising to Z={PEN_UP_HEIGHT}mm...")
        dexarm.fast_move_to(start_x, start_y, PEN_UP_HEIGHT)
        time.sleep(2)

        # Test 2: Draw a small dot
        print("\nTest 2: Drawing a small dot")
        print("  Moving pen down...")
        dexarm.fast_move_to(start_x, start_y, DRAWING_HEIGHT)
        time.sleep(1)
        print("  Pen up...")
        dexarm.fast_move_to(start_x, start_y, PEN_UP_HEIGHT)
        time.sleep(1)

        # Test 3: Draw a short line
        print("\nTest 3: Drawing a short line")
        print("  Pen down...")
        dexarm.fast_move_to(start_x - 20, start_y, DRAWING_HEIGHT)
        time.sleep(0.5)
        print("  Drawing line...")
        dexarm.fast_move_to(start_x + 20, start_y, DRAWING_HEIGHT)
        time.sleep(1)
        print("  Pen up...")
        dexarm.fast_move_to(start_x + 20, start_y, PEN_UP_HEIGHT)
        time.sleep(1)

        # Return to home
        print("\n🏠 Returning to home position...")
        dexarm.go_home()

        print("\n✅ Pen control test complete!")
        print("\n📝 Notes:")
        print("   - If pen didn't touch paper, decrease DRAWING_HEIGHT")
        print("   - If pen pressed too hard, increase DRAWING_HEIGHT")
        print(f"   - Current settings: UP={PEN_UP_HEIGHT}mm, DOWN={DRAWING_HEIGHT}mm")

        dexarm.close()
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def calibrate_z_height(port):
    """Interactive Z-height calibration"""

    print(f"\n🔌 Connecting to DexArm on {port}...")

    try:
        dexarm = Dexarm(port=port)
        print("✅ Connected!")

        dexarm.go_home()
        time.sleep(2)

        # Move to calibration position
        x, y = 200, 0
        z = 0
        dexarm.fast_move_to(x, y, z)

        print("\n🎯 Z-Height Calibration Mode")
        print("Commands:")
        print("  w/s - Move Z up/down by 1mm")
        print("  a/d - Move Z up/down by 0.1mm")
        print("  q   - Quit and show current Z")
        print()
        print("Lower the pen until it just touches the paper.")

        while True:
            command = input(f"Z={z:.1f}mm > ").strip().lower()

            if command == 'w':
                z += 1
            elif command == 's':
                z -= 1
            elif command == 'a':
                z += 0.1
            elif command == 'd':
                z -= 0.1
            elif command == 'q':
                break
            else:
                print("Invalid command")
                continue

            dexarm.fast_move_to(x, y, z)
            print(f"Moved to Z={z:.1f}mm")

        print(f"\n📋 Calibrated Z-height: {z:.1f}mm")
        print(f"Update DRAWING_HEIGHT = {z:.1f} in this script")

        dexarm.go_home()
        dexarm.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 02_pen_test.py [PORT] [--calibrate]")
        print("Example: python 02_pen_test.py COM3")
        print("         python 02_pen_test.py COM3 --calibrate")
        sys.exit(1)

    port = sys.argv[1]
    calibrate_mode = len(sys.argv) > 2 and sys.argv[2] == '--calibrate'

    print("=" * 50)
    if calibrate_mode:
        print("DexArm Z-Height Calibration")
        print("=" * 50)
        calibrate_z_height(port)
    else:
        print("DexArm Pen Control Test")
        print("=" * 50)
        success = test_pen_control(port)
        sys.exit(0 if success else 1)
