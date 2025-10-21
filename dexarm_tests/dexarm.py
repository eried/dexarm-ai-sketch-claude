"""
Simple DexArm Control Wrapper
==============================
Direct serial communication with Rotrics DexArm using pyserial.
DexArm uses Marlin firmware and responds to standard G-code commands.
"""

import serial
import time

class Dexarm:
    """Simple wrapper for DexArm control via serial port"""

    def __init__(self, port, baudrate=115200, timeout=10):
        """
        Initialize DexArm connection

        Args:
            port (str): Serial port (e.g., 'COM3', '/dev/ttyUSB0')
            baudrate (int): Baud rate (default: 115200)
            timeout (int): Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

        # Connect
        self._connect()

    def _connect(self):
        """Establish serial connection"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=10  # 10 second write timeout
            )
            time.sleep(2)  # Wait for connection to stabilize

            # Flush buffers
            self.serial.flushInput()
            self.serial.flushOutput()

            # Wait for startup messages
            time.sleep(1)
            while self.serial.in_waiting:
                self.serial.readline()

        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to DexArm on {self.port}: {e}")

    def send_gcode(self, command, wait_ok=True, timeout=10):
        """
        Send a G-code command

        Args:
            command (str): G-code command
            wait_ok (bool): Wait for 'ok' response
            timeout (float): Timeout in seconds for waiting response

        Returns:
            str: Response from DexArm
        """
        if not self.serial or not self.serial.is_open:
            raise ConnectionError("Not connected to DexArm")

        # Clean command
        command = command.strip()
        if not command:
            return ""

        try:
            # Send command with explicit encoding
            self.serial.write(f"{command}\n".encode('utf-8'))
            self.serial.flush()  # Ensure data is sent
            
            if wait_ok:
                # Wait for response with timeout
                start_time = time.time()
                response_lines = []
                
                while (time.time() - start_time) < timeout:
                    if self.serial.in_waiting > 0:
                        try:
                            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                response_lines.append(line)
                                # If we got 'ok', we're done
                                if line == 'ok':
                                    return '\n'.join(response_lines)
                        except:
                            pass
                    else:
                        time.sleep(0.01)  # Small delay to avoid busy-waiting
                
                # Return what we got even if no 'ok'
                return '\n'.join(response_lines) if response_lines else ""
            
            return ""
            
        except serial.SerialTimeoutException:
            raise TimeoutError(f"Write timeout sending command: {command}")
        except Exception as e:
            raise RuntimeError(f"Error sending command '{command}': {e}")

    def go_home(self, timeout=30):
        """
        Home all axes (G28) with timeout protection

        Args:
            timeout (int): Maximum time to wait for homing in seconds

        Raises:
            TimeoutError: If homing takes longer than timeout
        """
        print("Starting homing sequence...")
        self.send_gcode("G28", wait_ok=True, timeout=timeout)

        # Wait a bit for homing to complete and verify position
        time.sleep(2)

        # Verify we're at home position
        pos = self.get_position()
        if pos:
            print(f"Homing complete. Position: X={pos['x']:.2f}, Y={pos['y']:.2f}, Z={pos['z']:.2f}")
        else:
            print("WARNING: Could not verify home position")

    def move_to(self, x, y, z, feedrate=2000):
        """
        Move to absolute position

        Args:
            x, y, z: Coordinates in mm
            feedrate: Movement speed in mm/min
        """
        self.send_gcode(f"G1 X{x} Y{y} Z{z} F{feedrate}")

    def fast_move_to(self, x, y, z, feedrate=3000):
        """
        Rapid move to absolute position

        Args:
            x, y, z: Coordinates in mm
            feedrate: Movement speed in mm/min
        """
        self.send_gcode(f"G0 X{x} Y{y} Z{z} F{feedrate}")

    def set_absolute_positioning(self):
        """Set to absolute positioning mode (G90)"""
        self.send_gcode("G90")

    def set_relative_positioning(self):
        """Set to relative positioning mode (G91)"""
        self.send_gcode("G91")

    def get_position(self):
        """
        Get current position (M114)

        Returns:
            dict: Current position {'x': float, 'y': float, 'z': float}
                  Returns None if position cannot be read
        """
        try:
            # Flush any pending data first to avoid reading stale responses
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # Send M114 and wait for response
            self.serial.write(b"M114\n")
            self.serial.flush()  # Ensure command is sent
            time.sleep(0.3)  # Increased wait time for full multi-line response

            # Read all available lines with timeout
            lines = []
            timeout = time.time() + 1.0  # 1 second timeout
            while time.time() < timeout:
                if self.serial.in_waiting > 0:
                    try:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            lines.append(line)
                            # If we got 'ok', we're done
                            if line == 'ok':
                                break
                    except:
                        pass
                else:
                    time.sleep(0.05)  # Small delay before checking again

            # Find the line starting with "X:" (the main position line)
            for line in lines:
                if line.startswith('X:'):
                    # Parse response: "X:200.00 Y:0.00 Z:0.00 E:0.00 ..."
                    position = {}
                    parts = line.split()
                    for part in parts:
                        if ':' in part:
                            axis, value = part.split(':', 1)
                            axis = axis.upper()
                            if axis in ['X', 'Y', 'Z']:
                                try:
                                    position[axis.lower()] = float(value)
                                except ValueError:
                                    pass

                    # Return position if we got all three axes
                    if 'x' in position and 'y' in position and 'z' in position:
                        return position

            # If we didn't find valid position, return None to indicate failure
            return None

        except Exception as e:
            print(f"Error getting position: {e}")
            return None

    def delay(self, milliseconds):
        """
        Dwell/pause (G4)

        Args:
            milliseconds (int): Pause duration in milliseconds
        """
        self.send_gcode(f"G4 P{milliseconds}")

    def unlock_motors(self):
        """
        Unlock motors (M84) - allows manual positioning
        Motors can be moved freely by hand
        """
        # M84 may not return OK, send without waiting
        self.send_gcode("M84", wait_ok=False)
        # Small delay to ensure command is processed
        time.sleep(0.1)

    def lock_motors(self):
        """
        Lock motors (M17) - enables holding torque
        Motors hold their position
        """
        # M17 may not return OK, send without waiting
        self.send_gcode("M17", wait_ok=False)
        # Small delay to ensure command is processed
        time.sleep(0.1)

    def close(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __del__(self):
        """Destructor"""
        self.close()


# Helper functions
def find_dexarm_port():
    """
    Try to auto-detect DexArm port

    Returns:
        str: Port name or None if not found
    """
    import serial.tools.list_ports

    ports = serial.tools.list_ports.comports()

    for port in ports:
        # DexArm typically shows up as USB Serial Device
        if 'USB' in port.description or 'Serial' in port.description:
            return port.device

    return None
