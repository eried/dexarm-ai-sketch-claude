"""
DexArm GCode Sender
===================
Send GCode files or commands directly to the DexArm.

This script can:
- Send individual gcode commands interactively
- Execute gcode files
- Monitor execution progress

Usage:
    python 04_gcode_sender.py [PORT] [--file GCODE_FILE]
    python 04_gcode_sender.py [PORT] --interactive

Example:
    python 04_gcode_sender.py COM3 --file drawing.gcode
    python 04_gcode_sender.py COM3 --interactive
"""

import sys
import time
import serial
from pathlib import Path

class GCodeSender:
    def __init__(self, port, baudrate=115200):
        """Initialize GCode sender"""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.line_count = 0

    def connect(self):
        """Connect to DexArm via serial"""
        print(f"🔌 Connecting to {self.port} at {self.baudrate} baud...")

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=5
            )
            time.sleep(2)  # Wait for connection to stabilize

            # Flush any initial data
            self.serial.flushInput()
            self.serial.flushOutput()

            print("✅ Connected!")
            return True

        except serial.SerialException as e:
            print(f"❌ Connection failed: {e}")
            return False

    def send_command(self, command, wait_for_ok=True):
        """Send a single gcode command"""
        if not self.serial or not self.serial.is_open:
            print("❌ Not connected!")
            return False

        # Clean command
        command = command.strip()
        if not command or command.startswith(';'):
            return True  # Skip empty lines and comments

        # Send command
        self.serial.write(f"{command}\n".encode())
        self.line_count += 1

        if wait_for_ok:
            # Wait for 'ok' response
            response = self.serial.readline().decode().strip()
            if 'ok' in response.lower():
                return True
            else:
                print(f"⚠️  Unexpected response: {response}")
                return False

        return True

    def send_file(self, filepath, progress_callback=None):
        """Send a gcode file"""
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            return False

        print(f"\n📄 Loading file: {filepath.name}")

        # Read and filter gcode
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f.readlines()]

        # Remove empty lines and comments
        gcode_lines = [
            line for line in lines
            if line and not line.startswith(';')
        ]

        total_lines = len(gcode_lines)
        print(f"📊 Total commands: {total_lines}")
        print()

        # Send initialization
        print("🏠 Homing...")
        self.send_command("G28")  # Home
        time.sleep(3)

        # Send gcode line by line
        print("✏️  Executing gcode...")
        start_time = time.time()

        for i, line in enumerate(gcode_lines, 1):
            success = self.send_command(line)

            if not success:
                print(f"\n❌ Failed at line {i}: {line}")
                return False

            # Progress update
            if progress_callback:
                progress_callback(i, total_lines)
            elif i % 10 == 0 or i == total_lines:
                percent = (i / total_lines) * 100
                elapsed = time.time() - start_time
                print(f"  Progress: {i}/{total_lines} ({percent:.1f}%) - {elapsed:.1f}s", end='\r')

        elapsed = time.time() - start_time
        print(f"\n✅ Complete! Executed {total_lines} commands in {elapsed:.1f}s")

        # Return to home
        print("🏠 Returning home...")
        self.send_command("G28")

        return True

    def interactive_mode(self):
        """Interactive gcode command entry"""
        print("\n💻 Interactive GCode Mode")
        print("Commands:")
        print("  Enter gcode commands directly (e.g., G1 X100 Y100)")
        print("  'home' - Home the arm (G28)")
        print("  'help' - Show common commands")
        print("  'quit' - Exit")
        print()

        while True:
            try:
                command = input("gcode> ").strip()

                if command.lower() == 'quit':
                    break
                elif command.lower() == 'home':
                    self.send_command("G28")
                    print("Homed")
                elif command.lower() == 'help':
                    self.show_help()
                elif command:
                    success = self.send_command(command)
                    if success:
                        print("ok")
                    else:
                        print("error")

            except KeyboardInterrupt:
                print("\nExiting...")
                break

    def show_help(self):
        """Show common gcode commands"""
        print("\n📖 Common GCode Commands:")
        print("  G28              - Home all axes")
        print("  G1 X100 Y50 Z10  - Move to position")
        print("  G0 X100 Y50 Z10  - Rapid move to position")
        print("  M3               - Pen down (or motor on)")
        print("  M5               - Pen up (or motor off)")
        print("  G4 P500          - Dwell/pause for 500ms")
        print()

    def close(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("🔌 Disconnected")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python 04_gcode_sender.py [PORT] --file [GCODE_FILE]")
        print("  python 04_gcode_sender.py [PORT] --interactive")
        print()
        print("Example:")
        print("  python 04_gcode_sender.py COM3 --file drawing.gcode")
        print("  python 04_gcode_sender.py COM3 --interactive")
        sys.exit(1)

    port = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else None

    print("=" * 50)
    print("DexArm GCode Sender")
    print("=" * 50)

    # Create sender
    sender = GCodeSender(port)

    if not sender.connect():
        sys.exit(1)

    try:
        if mode == '--interactive':
            sender.interactive_mode()
        elif mode == '--file' and len(sys.argv) > 3:
            gcode_file = sys.argv[3]
            sender.send_file(gcode_file)
        else:
            print("❌ Invalid mode. Use --file [path] or --interactive")
            sender.close()
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        sender.close()

if __name__ == "__main__":
    main()
