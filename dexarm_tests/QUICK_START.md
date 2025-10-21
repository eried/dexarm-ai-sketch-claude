# DexArm Quick Start Guide

## Installation

```bash
cd ai-sketch-booth-claude
pip install -r requirements.txt
```

## Testing Steps (In Order)

### Step 1: Connect & Home
```bash
cd dexarm_tests
python 01_connection_test.py
```
✅ Should show "All tests passed!"

---

### Step 2: Calibrate Pen Height
```bash
python 02_pen_test.py COM3 --calibrate
```

**Instructions:**
1. Place paper on work surface
2. Use `w/s` to adjust height (1mm steps)
3. Use `a/d` for fine tuning (0.1mm steps)
4. Lower pen until it JUST touches paper
5. Press `q` to finish
6. **Note the Z-height value shown**

**Update Scripts:**
Open `02_pen_test.py` and `03_shape_drawing.py`:
- Set `Z_DOWN = [your calibrated value]` (e.g., -3.5)

---

### Step 3: Test Pen Control
```bash
python 02_pen_test.py COM3
```
✅ Should draw a dot and a line

---

### Step 4: Draw Shapes
```bash
python 03_shape_drawing.py COM3 all
```
✅ Should draw square, circle, and star

---

### Step 5: Test GCode
```bash
python 04_gcode_sender.py COM3 --file sample_drawing.gcode
```
✅ Should draw a smiley face

---

## Common Issues

**"Port not found"**
- Replace `COM3` with your actual port
- Check Device Manager (Windows)
- Close Rotrics Studio

**"Pen doesn't touch paper"**
- Lower Z_DOWN (e.g., -3 → -4)

**"Pen presses too hard"**
- Raise Z_DOWN (e.g., -5 → -3)

---

## Ready for Next Phase?

Once all tests pass, you're ready for Phase A (Image Pipeline):
- Background removal
- ComfyUI integration
- Vectorization
- GCode generation

See main README.md for next steps!
