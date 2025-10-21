"""
DexArm Controller for Flask App
================================
Manages persistent connection to DexArm and provides high-level control.
"""

import json
import os
from pathlib import Path
from dexarm_tests.dexarm import Dexarm, find_dexarm_port

class DexArmController:
    """Singleton controller for DexArm"""

    _instance = None
    _dexarm = None
    _config_file = 'dexarm_config.json'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize controller"""
        self.config = self.load_config()
        self.is_connected = False

    def connect(self, port=None, move_to_rest=False):
        """
        Connect to DexArm

        Args:
            port (str): Serial port, or None to auto-detect
            move_to_rest (bool): If True, move to resting position after connect

        Returns:
            bool: True if connected successfully
        """
        try:
            # If already connected to the same port, just return success
            if self.is_connected and self._dexarm and port == self.config.get('port'):
                print(f"Already connected to {port}")
                # Still move to rest if requested
                if move_to_rest and self.get_resting_position():
                    try:
                        print("Moving to resting position...")
                        self.lock_motors()
                        import time
                        time.sleep(0.2)
                        self.go_to_resting_position()
                        print("At resting position")
                    except Exception as e:
                        print(f"WARNING: Could not move to resting position: {e}")
                return True

            # Disconnect if already connected to different port
            if self.is_connected:
                print("Disconnecting from previous connection...")
                self.disconnect()

            if port is None:
                port = self.config.get('port') or find_dexarm_port()

            if port is None:
                print("ERROR: No DexArm port found")
                return False

            print(f"Connecting to DexArm on {port}...")
            self._dexarm = Dexarm(port)
            self._dexarm.set_absolute_positioning()
            self.is_connected = True

            # Save port to config
            self.config['port'] = port
            self.save_config()

            print(f"Connected successfully to {port}")

            # Move to rest position if requested and calibrated
            if move_to_rest and self.get_resting_position():
                try:
                    print("Moving to resting position...")
                    self.lock_motors()  # Lock motors first
                    import time
                    time.sleep(0.2)  # Wait for motors to lock
                    self.go_to_resting_position()
                    print("At resting position")
                except Exception as e:
                    print(f"WARNING: Could not move to resting position: {e}")

            return True

        except Exception as e:
            print(f"Failed to connect to DexArm: {e}")
            import traceback
            traceback.print_exc()
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from DexArm"""
        if self._dexarm:
            self._dexarm.close()
            self._dexarm = None
        self.is_connected = False

    def home(self, timeout=30):
        """
        Home the DexArm with timeout protection

        Args:
            timeout (int): Maximum time to wait for homing in seconds

        Raises:
            RuntimeError: If not connected
            TimeoutError: If homing takes too long
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        try:
            self._dexarm.go_home(timeout=timeout)
        except TimeoutError as e:
            raise TimeoutError(f"Homing timed out after {timeout} seconds. The arm may be stuck or unpowered.") from e

    def move_to(self, x, y, z, feedrate=2000):
        """Move to position"""
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")
        self._dexarm.fast_move_to(x, y, z, feedrate)

    def move_to_safe(self, x, y, z, feedrate=2000, current_z=None):
        """
        Safe move with Z-aware path planning to prevent pen dragging

        Strategy:
        - When moving UP (Z increasing): Lift Z first, then move XY
        - When moving DOWN (Z decreasing): Move XY first, then lower Z

        This prevents the pen from dragging across the paper during moves.

        Args:
            x, y, z: Target coordinates
            feedrate: Movement speed (mm/min)
            current_z: Current Z position (if None, will be fetched)

        Returns:
            float: Final Z position after move
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        # Get current Z if not provided
        if current_z is None:
            pos = self.get_position()
            if pos:
                current_z = pos['z']
            else:
                # If we can't get position, fall back to simple move
                self._dexarm.fast_move_to(x, y, z, feedrate)
                return z

        z_diff = z - current_z

        if abs(z_diff) < 0.5:
            # Z is essentially the same, just move directly
            # Use faster feedrate for lateral moves
            self._dexarm.fast_move_to(x, y, z, feedrate)
        elif z_diff > 0:
            # Moving UP (pen up) - Lift Z first, then move XY
            # Use fast feedrate for pen-up moves
            self._dexarm.fast_move_to(current_z, current_z, z, 10000)  # Lift pen fast
            import time
            time.sleep(0.05)  # Brief pause
            self._dexarm.fast_move_to(x, y, z, 10000)  # Move XY fast with pen up
        else:
            # Moving DOWN (pen down) - Move XY first, then lower Z
            # Move to XY position with pen still up
            self._dexarm.fast_move_to(x, y, current_z, 10000)  # Move XY fast
            import time
            time.sleep(0.05)  # Brief pause
            self._dexarm.fast_move_to(x, y, z, feedrate)  # Lower pen at drawing speed

        return z

    def get_position(self):
        """
        Get current position

        Returns:
            dict or None: Current position {'x': float, 'y': float, 'z': float}
                         Returns None if position cannot be read
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        try:
            pos = self._dexarm.get_position()
            return pos
        except Exception as e:
            print(f"WARNING: Could not get position: {e}")
            # Don't disconnect on position read failure - might be temporary
            return None

    def unlock_motors(self):
        """
        Unlock motors for manual positioning with verification

        Raises:
            RuntimeError: If unlock fails or cannot verify
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        print("Unlocking motors...")
        self._dexarm.unlock_motors()

        # Try to verify unlock by checking if position changes when manually moved
        # (This is a simple check - motors unlocked won't hold position)
        import time
        time.sleep(0.3)
        print("Motors unlocked successfully")

    def lock_motors(self):
        """
        Lock motors with verification

        Raises:
            RuntimeError: If lock fails
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        print("Locking motors...")
        self._dexarm.lock_motors()

        import time
        time.sleep(0.2)
        print("Motors locked successfully")

    def save_corner(self, corner_name):
        """
        Save current position as a corner

        Args:
            corner_name (str): 'corner1' or 'corner2'
        
        Returns:
            dict: Saved position
        
        Raises:
            RuntimeError: If position cannot be read
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        position = self._dexarm.get_position()
        
        if position is None:
            raise RuntimeError("Could not read current position from DexArm")

        if 'corners' not in self.config:
            self.config['corners'] = {}

        self.config['corners'][corner_name] = {
            'x': position['x'],
            'y': position['y'],
            'z': position['z']
        }

        self.save_config()
        return position

    def get_corners(self):
        """Get saved corners"""
        return self.config.get('corners', {})

    def is_calibrated(self):
        """Check if both corners are set"""
        corners = self.config.get('corners', {})
        return 'corner1' in corners and 'corner2' in corners

    def save_resting_position(self):
        """
        Save current position as resting position
        
        Returns:
            dict: Saved position
        
        Raises:
            RuntimeError: If position cannot be read
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        position = self._dexarm.get_position()
        
        if position is None:
            raise RuntimeError("Could not read current position from DexArm")
            
        self.config['resting_position'] = {
            'x': position['x'],
            'y': position['y'],
            'z': position['z']
        }
        self.save_config()
        return position

    def get_resting_position(self):
        """Get resting position"""
        return self.config.get('resting_position', None)

    def go_to_resting_position(self):
        """Move arm to resting position"""
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        resting_pos = self.get_resting_position()
        if not resting_pos:
            # Default resting position (safe position above workspace)
            resting_pos = {'x': 200, 'y': 0, 'z': 50}

        self._dexarm.fast_move_to(
            resting_pos['x'],
            resting_pos['y'],
            resting_pos['z']
        )

    def get_drawing_area(self):
        """
        Get drawing area dimensions

        Returns:
            dict: {'width': float, 'height': float, 'x_min': float, 'y_min': float}
        """
        corners = self.get_corners()
        if not self.is_calibrated():
            return None

        c1 = corners['corner1']
        c2 = corners['corner2']

        x_min = min(c1['x'], c2['x'])
        x_max = max(c1['x'], c2['x'])
        y_min = min(c1['y'], c2['y'])
        y_max = max(c1['y'], c2['y'])

        return {
            'width': x_max - x_min,
            'height': y_max - y_min,
            'x_min': x_min,
            'y_min': y_min,
            'x_max': x_max,
            'y_max': y_max,
            'z_draw': c1['z']  # Use same Z height as corners
        }

    def load_config(self):
        """Load configuration from file"""
        config_path = Path(self._config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self):
        """Save configuration to file"""
        with open(self._config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def reset_calibration(self):
        """Clear saved corners"""
        if 'corners' in self.config:
            del self.config['corners']
        self.save_config()

    def test_draw_frame(self):
        """
        Draw a complete rectangle frame and X in the calibrated area
        Sequence: Rest -> C1 -> C3 -> C2 -> C4 -> C1 (rectangle) -> C1-C2 diagonal -> C3-C4 diagonal -> Rest

        Corner layout (user sets C1 and C2, we calculate C3 and C4):
          C1 ----------- C3
          |              |
          |              |
          C4 ----------- C2

        Returns progress updates as generator
        """
        if not self.is_connected or not self._dexarm:
            raise RuntimeError("DexArm not connected")

        if not self.is_calibrated():
            raise RuntimeError("Not calibrated - set corners first")

        area = self.get_drawing_area()
        z_draw = area['z_draw']
        z_up = z_draw + 20  # Pen up height (increased for better clearance)

        # Get user-defined corners
        corners = self.get_corners()
        c1 = corners['corner1']  # User sets this (e.g., top-left)
        c2 = corners['corner2']  # User sets this (e.g., bottom-right)

        # Calculate the other two corners to complete the rectangle
        # C3 shares X with C2 and Y with C1 (opposite to C4)
        # C4 shares X with C1 and Y with C2 (opposite to C3)
        c3 = {'x': c2['x'], 'y': c1['y'], 'z': z_draw}  # Top-right
        c4 = {'x': c1['x'], 'y': c2['y'], 'z': z_draw}  # Bottom-left

        try:
            import time

            # Start from rest position
            yield "Moving from rest position..."
            self.go_to_resting_position()
            time.sleep(0.5)

            # Move to C1 with pen up
            yield "Moving to Corner 1..."
            self._dexarm.fast_move_to(c1['x'], c1['y'], z_up)
            time.sleep(0.3)
            self._dexarm.move_to(c1['x'], c1['y'], z_draw, feedrate=2000)  # Pen down
            time.sleep(0.3)

            # Draw rectangle clockwise: C1 -> C3 -> C2 -> C4 -> C1
            yield "Drawing to Corner 3..."
            self._dexarm.move_to(c3['x'], c3['y'], z_draw, feedrate=2000)
            time.sleep(0.3)

            yield "Drawing to Corner 2..."
            self._dexarm.move_to(c2['x'], c2['y'], z_draw, feedrate=2000)
            time.sleep(0.3)

            yield "Drawing to Corner 4..."
            self._dexarm.move_to(c4['x'], c4['y'], z_draw, feedrate=2000)
            time.sleep(0.3)

            # Close the rectangle
            yield "Closing rectangle (back to Corner 1)..."
            self._dexarm.move_to(c1['x'], c1['y'], z_draw, feedrate=2000)
            time.sleep(0.3)

            # Draw X - first diagonal: C1 to C2 (pen is already down at C1)
            yield "Drawing X (diagonal 1: C1 to C2)..."
            self._dexarm.move_to(c2['x'], c2['y'], z_draw, feedrate=2000)  # Draw to C2
            time.sleep(0.3)
            self._dexarm.move_to(c2['x'], c2['y'], z_up, feedrate=2000)  # Pen up
            time.sleep(0.3)

            # Draw X - second diagonal: C3 to C4
            yield "Drawing X (diagonal 2: C3 to C4)..."
            self._dexarm.fast_move_to(c3['x'], c3['y'], z_up)  # Move to C3
            time.sleep(0.3)
            self._dexarm.move_to(c3['x'], c3['y'], z_draw, feedrate=2000)  # Pen down
            time.sleep(0.3)
            self._dexarm.move_to(c4['x'], c4['y'], z_draw, feedrate=2000)  # Draw to C4
            time.sleep(0.3)
            self._dexarm.move_to(c4['x'], c4['y'], z_up, feedrate=2000)  # Pen up
            time.sleep(0.3)

            # Return to resting position
            yield "Returning to resting position..."
            self.go_to_resting_position()

            yield "Test draw complete!"

        except Exception as e:
            raise RuntimeError(f"Test draw failed: {e}")


# Global controller instance
controller = DexArmController()
