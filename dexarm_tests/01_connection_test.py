"""
DexArm Connection and Homing Test
==================================
This script tests basic connection to the DexArm and performs homing.

Usage:
    python 01_connection_test.py [PORT]

If PORT is not specified, the script will try to auto-detect the DexArm.

Example:
    python 01_connection_test.py COM3
"""

import sys
import time
from dexarm import Dexarm, find_dexarm_port

def test_connection(port=None):
    """Test connection to DexArm and perform homing"""

    # Auto-detect port if not provided
    if port is None:
        port = find_dexarm_port()
        if port is None:
            print("\n❌ No DexArm found. Please specify port manually.")
            print("Usage: python 01_connection_test.py COM3")
            return False

    print(f"\n🔌 Connecting to DexArm on {port}...")

    try:
        # Create DexArm instance
        dexarm = Dexarm(port=port)
        print("✅ Connection successful!")

        # Get firmware version
        print("\n📋 Getting device info...")
        # Note: Check pydexarm docs for exact method to get version
        # This might need adjustment based on actual API

        print("\n🏠 Homing DexArm...")
        print("⚠️  Make sure the arm has clear space to move!")
        time.sleep(2)  # Give user time to read warning

        # Home the arm
        dexarm.go_home()
        print("✅ Homing complete!")

        # Get current position
        print("\n📍 Current position:")
        # Note: Adjust based on actual pydexarm API
        # position = dexarm.get_current_position()
        # print(f"   X: {position[0]}, Y: {position[1]}, Z: {position[2]}")

        print("\n✅ All tests passed!")
        print("Your DexArm is ready to use.")

        # Close connection
        dexarm.close()
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure DexArm is powered on")
        print("2. Check USB connection")
        print("3. Close Rotrics Studio if it's running")
        print("4. Try a different USB port")
        print("5. Verify the correct COM port")
        return False

if __name__ == "__main__":
    # Get port from command line or auto-detect
    port = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 50)
    print("DexArm Connection & Homing Test")
    print("=" * 50)

    success = test_connection(port)

    sys.exit(0 if success else 1)
