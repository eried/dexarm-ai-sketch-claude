# DexArm Testing Scripts

This folder contains test scripts for getting your Rotrics DexArm working with the AI Sketch Booth.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Hardware Setup**
   - Connect DexArm via USB
   - Power on the DexArm
   - Close Rotrics Studio if running (only one program can access the port at a time)
   - Attach pen/marker to the drawing module

3. **Find Your COM Port**
   - Windows: Check Device Manager → Ports (COM & LPT)
   - Common ports: COM3, COM4, COM5
   - Or let the scripts auto-detect

## Testing Workflow

Follow these scripts in order:

### 1. Connection Test
**Script**: `01_connection_test.py`

Tests basic connection and homing.

```bash
# Auto-detect port
python 01_connection_test.py

# Or specify port
python 01_connection_test.py COM3
```

**Expected Result**: DexArm homes successfully and shows "All tests passed!"

---

### 2. Pen Calibration
**Script**: `02_pen_test.py`

**IMPORTANT**: This step calibrates the Z-height for drawing!

```bash
# Interactive calibration
python 02_pen_test.py COM3 --calibrate
```

**Instructions**:
1. Place paper on the work surface
2. Use `w/s` keys to move pen up/down by 1mm
3. Use `a/d` keys for fine adjustment (0.1mm)
4. Lower the pen until it JUST touches the paper
5. Press `q` when done
6. **Write down the Z-height value!**
7. Update `Z_DOWN` in `03_shape_drawing.py` with this value

After calibration, test pen control:
```bash
python 02_pen_test.py COM3
```

This will draw a dot and a short line to verify settings.

---

### 3. Shape Drawing Test
**Script**: `03_shape_drawing.py`

Tests drawing basic shapes.

```bash
# Draw all shapes
python 03_shape_drawing.py COM3 all

# Draw specific shape
python 03_shape_drawing.py COM3 square
python 03_shape_drawing.py COM3 circle
python 03_shape_drawing.py COM3 star
```

**Before running**:
- Update `Z_UP` and `Z_DOWN` with your calibrated values
- Place fresh paper on work surface

**Expected Result**: DexArm draws the requested shapes on paper

---

### 4. GCode Sender
**Script**: `04_gcode_sender.py`

Send custom gcode files or commands.

```bash
# Send a gcode file
python 04_gcode_sender.py COM3 --file sample_drawing.gcode

# Interactive mode (type commands manually)
python 04_gcode_sender.py COM3 --interactive
```

**Interactive Mode Commands**:
- `G1 X100 Y50 Z10` - Move to position
- `home` - Home the arm
- `help` - Show common commands
- `quit` - Exit

**Sample File**: `sample_drawing.gcode` draws a simple smiley face

---

## Important Z-Height Values

After calibration, you'll have these values:

- **Z_UP**: Height when pen is lifted (default: 10mm)
  - High enough that pen doesn't touch paper during travel moves

- **Z_DOWN**: Height when drawing (calibrated, typically -3 to -5mm)
  - Just touching paper with light pressure
  - Too low = too much pressure, pen damage
  - Too high = pen doesn't touch, no lines drawn

**Update these values in all scripts before running!**

---

## Troubleshooting

### "Port not found" or "Access denied"
- Check USB connection
- Close Rotrics Studio
- Try different USB port
- Restart DexArm

### "Pen doesn't touch paper"
- Decrease Z_DOWN value (e.g., -3 → -4)
- Run calibration again

### "Pen presses too hard"
- Increase Z_DOWN value (e.g., -5 → -3)
- Check pen attachment

### "Unexpected movements"
- Stop immediately (power off if needed)
- Verify coordinate system
- Check that workspace is clear
- Re-run homing

### "Lines are shaky or uneven"
- Reduce DRAW_SPEED
- Check that paper is flat and secured
- Ensure DexArm base is stable
- Verify pen is secured properly

---

## Coordinate System

DexArm workspace (approximate):
- **X**: -300 to +300mm (left to right)
- **Y**: -300 to +300mm (front to back)
- **Z**: -150 to +150mm (down to up)

**Safe drawing area** (with pen module):
- X: 100 to 300mm
- Y: -100 to 100mm
- Z: -10 to 20mm

**Home Position**: X=200, Y=0, Z=0 (approximately)

---

## Next Steps

Once all tests pass:

1. ✅ Connection works
2. ✅ Pen up/down calibrated
3. ✅ Shapes draw correctly
4. ✅ GCode execution works

You're ready to integrate with the image processing pipeline! The next phase will:
- Generate line art from photos
- Vectorize images
- Create gcode from vectors
- Send to DexArm for drawing

---

## File Reference

- `01_connection_test.py` - Basic connection and homing
- `02_pen_test.py` - Pen control and Z-calibration
- `03_shape_drawing.py` - Draw test shapes
- `04_gcode_sender.py` - Send gcode files/commands
- `sample_drawing.gcode` - Test gcode file (smiley face)

---

## Safety Notes

⚠️ **Always**:
- Keep workspace clear of obstacles
- Monitor the first run of any new script
- Have power switch accessible
- Start with pen raised (Z_UP)
- Test movements slowly first

⚠️ **Never**:
- Leave DexArm unattended during operation
- Use excessive pen pressure
- Exceed workspace limits
- Run untested gcode files at full speed
