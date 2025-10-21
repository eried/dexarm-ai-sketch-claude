# Installing Potrace for Better SVG Quality

## What is Potrace?

Potrace is a tool for tracing bitmaps into smooth, scalable vector graphics (SVG). It produces **much better quality** SVG files than the fallback edge detection method.

**Without Potrace:** Generates SVG with polylines from contour detection
**With Potrace:** Generates SVG with smooth bezier curves

## Installation

### Windows

1. **Download Potrace:**
   - Visit: http://potrace.sourceforge.net/#downloading
   - Download the Windows version (potrace-1.16.win64.zip or similar)

2. **Extract and Install:**
   ```bash
   # Extract to a folder, e.g., C:\Program Files\Potrace
   # Add the folder to your system PATH
   ```

3. **Add to PATH:**
   - Right-click "This PC" → Properties
   - Advanced System Settings → Environment Variables
   - Under "System Variables", find "Path" and click "Edit"
   - Click "New" and add: `C:\Program Files\Potrace`
   - Click OK on all dialogs

4. **Verify Installation:**
   ```bash
   potrace --version
   ```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install potrace

# Fedora/RHEL
sudo dnf install potrace

# Arch
sudo pacman -S potrace
```

### macOS

```bash
# Using Homebrew
brew install potrace

# Using MacPorts
sudo port install potrace
```

## Testing

After installation, restart your application and generate a new caricature. You should see:

```
Using Potrace for SVG conversion...
Potrace conversion successful
```

Instead of:

```
Potrace not found. Falling back to edge detection method.
```

## Fallback Method

If you can't install Potrace, the application will automatically use OpenCV contour detection as a fallback. This produces decent quality SVG files with polylines, but Potrace's bezier curves are smoother and better for drawing.

## Quality Comparison

| Method | Smoothness | File Size | Drawing Time |
|--------|------------|-----------|--------------|
| **Potrace** | ★★★★★ Bezier curves | Small | Faster |
| **Contour Detection** | ★★★☆☆ Polylines | Medium | Medium |
| **Edge Detection (old)** | ★☆☆☆☆ Scan lines | Large | Slow |
