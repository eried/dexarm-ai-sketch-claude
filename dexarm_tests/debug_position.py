"""
Debug Position Reading
======================
This script tests position reading in unlocked mode and shows raw responses.
"""

import sys
import time
import os
import subprocess
sys.path.append('.')

from dexarm import Dexarm, find_dexarm_port

def kill_other_python_instances():
    """Kill other Python processes to free up COM port"""
    current_pid = os.getpid()

    print("Killing other Python instances...")

    try:
        # Windows taskkill approach
        if sys.platform == 'win32':
            # Get list of Python processes
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True
            )

            lines = result.stdout.strip().split('\n')
            killed_count = 0

            for line in lines:
                if line and 'python.exe' in line.lower():
                    parts = line.replace('"', '').split(',')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            if pid != current_pid:
                                subprocess.run(['taskkill', '/PID', str(pid), '/F'],
                                             capture_output=True)
                                killed_count += 1
                                print(f"  Killed Python process PID {pid}")
                        except (ValueError, subprocess.SubprocessError):
                            pass

            if killed_count > 0:
                print(f"  Total killed: {killed_count}")
                print("  Waiting 2 seconds for ports to be released...")
                time.sleep(2)
            else:
                print("  No other Python instances found")
        else:
            # Unix/Linux approach
            subprocess.run(['pkill', '-f', 'python'], capture_output=True)
            print("  Sent kill signal to other Python processes")
            time.sleep(2)

    except Exception as e:
        print(f"  Warning: Could not kill other instances: {e}")
        print("  Continuing anyway...")

def debug_position_reading():
    """Test position reading and show raw responses"""

    # Kill other Python instances first
    kill_other_python_instances()

    # Find and connect
    print("\nFinding DexArm...")
    port = find_dexarm_port()

    if not port:
        print("ERROR: Could not find DexArm")
        return

    print(f"Connecting to {port}...")
    arm = Dexarm(port)

    print("\n=== Testing Position Reading ===\n")

    # Test 1: Position with motors locked
    print("TEST 1: Position reading with motors LOCKED")
    print("-" * 50)
    arm.lock_motors()
    time.sleep(0.5)

    for i in range(3):
        print(f"\nAttempt {i+1}:")
        arm.serial.write(b"M114\n")
        time.sleep(0.2)

        # Read all available lines
        lines = []
        while arm.serial.in_waiting > 0:
            line = arm.serial.readline().decode().strip()
            if line:
                lines.append(line)

        print(f"  Raw response ({len(lines)} lines):")
        for line in lines:
            print(f"    '{line}'")

        # Try parsing
        position = arm.get_position()
        print(f"  Parsed position: {position}")
        time.sleep(0.5)

    # Test 2: Position with motors unlocked
    print("\n\nTEST 2: Position reading with motors UNLOCKED")
    print("-" * 50)
    arm.unlock_motors()
    time.sleep(0.5)

    for i in range(5):
        print(f"\nAttempt {i+1}:")
        arm.serial.write(b"M114\n")
        time.sleep(0.2)

        # Read all available lines
        lines = []
        while arm.serial.in_waiting > 0:
            line = arm.serial.readline().decode().strip()
            if line:
                lines.append(line)

        print(f"  Raw response ({len(lines)} lines):")
        for line in lines:
            print(f"    '{line}'")

        # Try parsing
        position = arm.get_position()
        print(f"  Parsed position: {position}")
        time.sleep(1)

    # Test 3: Try different command variations
    print("\n\nTEST 3: Testing different position commands")
    print("-" * 50)

    commands = [
        "M114",
        "M114 R",
        "M114 D",
        "P2220"  # DexArm specific position command
    ]

    for cmd in commands:
        print(f"\nCommand: {cmd}")
        arm.serial.write(f"{cmd}\n".encode())
        time.sleep(0.3)

        lines = []
        while arm.serial.in_waiting > 0:
            line = arm.serial.readline().decode().strip()
            if line:
                lines.append(line)

        print(f"  Response ({len(lines)} lines):")
        for line in lines:
            print(f"    '{line}'")

    # Clean up
    print("\n\nClosing connection...")
    arm.close()
    print("Done!")

if __name__ == "__main__":
    try:
        debug_position_reading()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
