# AI Sketch Booth

A fun, interactive photobooth web application with camera capture, creative prompt suggestions, and fullscreen kiosk mode.

## Features

- **Live Camera Feed**: Real-time video preview from your device's camera
- **Creative Prompts**: 200+ fun scenario suggestions (e.g., "with a robot dog", "on the beach", "taking a taxi")
- **Photo Capture**: Take photos with a flash effect
- **Fullscreen/Kiosk Mode**: Enter fullscreen mode for a dedicated booth experience
- **Auto-Save**: Photos are automatically saved with timestamps
- **Prompt Metadata**: Each photo's prompt is saved alongside the image

## Quick Start (Windows)

**Easiest method:**
1. Double-click `launch.bat`
2. The script will automatically:
   - Install dependencies if needed
   - Start the Flask server
   - Open Chrome with proper camera permissions
   - Launch the photobooth

## Manual Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Manual Usage

1. Start the server:
```bash
python app.py
```

2. Open Chrome with camera permissions:
```bash
chrome.exe --new-window --app=http://localhost:5000 --use-fake-ui-for-media-stream
```

3. Or open your browser to: `http://localhost:5000` (you'll need to allow camera access)

## How to Use the Photobooth

1. **Allow camera access** when prompted by your browser
2. **Browse suggestions** - 20 random creative scenarios are displayed
3. **Click a suggestion** to fill the prompt textbox, or type your own scenario
4. **Click "Take Photo"** to capture your image with a flash effect
5. **Enter Fullscreen Mode** for a kiosk experience (button hides in fullscreen, press ESC to exit)

## How It Works

- **Flask Server**: Serves the web application and handles photo uploads
- **WebRTC**: Accesses the browser's camera via `getUserMedia`
- **Photos**: Saved to the `photos/` folder with timestamp filenames
- **Prompts**: Each photo's prompt is saved as a `.txt` file alongside the image

## File Structure

```
ai-sketch-booth-claude/
├── app.py                  # Flask server
├── launch.bat              # Windows launcher script
├── suggestions.json        # 200+ creative prompt suggestions
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Main HTML page
├── static/
│   ├── style.css          # Styling
│   └── app.js             # Frontend JavaScript
└── photos/                # Saved photos (created automatically)
```

## Future Enhancements

- AI image generation integration
- Photo filters and effects
- Email/SMS photo delivery
- Social media sharing
- Custom branding options
- Multi-language support

## Browser Compatibility

Requires a modern browser with WebRTC support:
- Chrome 53+
- Firefox 36+
- Safari 11+
- Edge 79+

## Notes

- **Camera access on Chrome**: The `launch.bat` script automatically opens Chrome with flags to bypass camera permission issues on localhost
- **Fullscreen mode**: The fullscreen button automatically hides when in fullscreen - use ESC key to exit
- **Suggestions**: 20 random suggestions are displayed at a time and refresh when you click one
- **Custom prompts**: You can type your own scenario in the textbox instead of using suggestions
- Photos are stored locally in the `photos/` folder with timestamps
