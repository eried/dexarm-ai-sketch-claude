from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import os
import base64
from datetime import datetime
import json
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance
from dexarm_controller import controller as dexarm_controller
from comfyui_client import comfyui_client
from svg_converter import svg_converter
from svg_parser import svg_parser
from svg_plotter_methods import plotter_svg_generator
from svg_thick_joining_variations import thick_joining_variations
from svg_clean_centerline import clean_centerline_generator
import time
import threading

app = Flask(__name__)
app.jinja_env.autoescape = True

# Global progress tracking for drawing
drawing_progress = {'current': 0, 'total': 0, 'active': False, 'message': ''}
progress_lock = threading.Lock()

# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================
class AppSettings:
    """Manage application settings"""

    def __init__(self, config_file='app_settings.json'):
        self.config_file = config_file
        self.settings = self.load()

    def load(self):
        """Load settings from file or return defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")

        # Return defaults
        return {
            'comfyui_url': 'http://127.0.0.1:8000',  # ComfyUI default port
            'pen_lift_height': 16,
            'svg_method': 'clean_v1',
            'max_commands': 5000
        }

    def save(self, settings):
        """Save settings to file"""
        self.settings = settings
        with open(self.config_file, 'w') as f:
            json.dump(settings, f, indent=2)

    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

# Initialize settings
app_settings = AppSettings()

# Apply ComfyUI URL from settings (strip http:// prefix if present)
comfyui_url = app_settings.get('comfyui_url', 'http://127.0.0.1:8188')
comfyui_client.server_address = comfyui_url.replace('http://', '').replace('https://', '')
print(f"\nComfyUI Server: {comfyui_client.server_address}")

# Create directories if they don't exist
PHOTOS_DIR = 'photos'
CARICATURES_DIR = 'caricatures'
SVGS_DIR = 'svgs'

for directory in [PHOTOS_DIR, CARICATURES_DIR, SVGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# SVG drawing variant is now configured in General Settings (/settings)
# ============================================================================

# Check ComfyUI availability on startup
print("\n" + "="*60)
print("AI Sketch Booth - Startup Check")
print("="*60)

if not comfyui_client.is_available:
    print("⚠️  WARNING: ComfyUI is not running!")
    print("   The app will work, but caricature generation will be disabled.")
    print("\n   To enable caricature generation:")
    print("   1. Start ComfyUI server")
    print("   2. Make sure it's running on http://127.0.0.1:8000")
    print("   3. Restart this application")
    print("\n" + "="*60)
else:
    print("✓ ComfyUI is running and available")
    print("="*60)

# Show current settings
print(f"\nCurrent Settings:")
print(f"  SVG Method: {app_settings.get('svg_method')}")
print(f"  Max Commands: {app_settings.get('max_commands')}")
print(f"  Pen Lift Height: {app_settings.get('pen_lift_height')}mm")
print(f"  ComfyUI URL: {app_settings.get('comfyui_url')}")
print("  To change: Visit /settings")
print()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify(app_settings.settings)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save settings"""
    try:
        settings = request.get_json()
        app_settings.save(settings)

        # Update ComfyUI client URL if changed (strip http:// prefix)
        if 'comfyui_url' in settings:
            url = settings['comfyui_url'].replace('http://', '').replace('https://', '')
            comfyui_client.server_address = url

        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    """Serve photos from photos directory"""
    return send_from_directory(PHOTOS_DIR, filename)

@app.route('/caricatures/<path:filename>')
def serve_caricature(filename):
    """Serve caricatures from caricatures directory"""
    return send_from_directory(CARICATURES_DIR, filename)

@app.route('/api/suggestions')
def get_suggestions():
    """Load and return prompt suggestions from JSON file"""
    with open('suggestions.json', 'r') as f:
        suggestions = json.load(f)
    return jsonify(suggestions)

@app.route('/api/save-photo', methods=['POST'])
def save_photo():
    """Save photo, generate caricature, convert to SVG, and optionally draw"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        prompt = data.get('prompt', '')

        # Remove the data URL prefix
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Load image with PIL
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if necessary (JPG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        
        # Apply sharpening
        img = img.filter(ImageFilter.SHARPEN)
        
        # Optional: Enhance sharpness further
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)  # 1.5x sharpness boost

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        photo_filename = f'photo_{timestamp}.jpg'
        photo_filepath = os.path.join(PHOTOS_DIR, photo_filename)

        # Save as JPG with good quality
        img.save(photo_filepath, 'JPEG', quality=85, optimize=True)

        # Save prompt as metadata
        if prompt:
            metadata_file = photo_filepath.replace('.jpg', '.txt')
            with open(metadata_file, 'w') as f:
                f.write(prompt)

        result = {
            'success': True,
            'filename': photo_filename,
            'timestamp': timestamp,
            'comfyui_available': comfyui_client.is_available,
            'dexarm_calibrated': dexarm_controller.is_calibrated()
        }

        # Generate caricature if ComfyUI is available
        if comfyui_client.is_available:
            try:
                print(f"Generating caricature for: {prompt}")
                caricature_img = comfyui_client.generate_caricature(photo_filepath, prompt)

                if caricature_img:
                    # Save caricature
                    caricature_filename = f'caricature_{timestamp}.png'
                    caricature_filepath = os.path.join(CARICATURES_DIR, caricature_filename)
                    caricature_img.save(caricature_filepath)

                    result['caricature'] = caricature_filename
                    print(f"Caricature saved: {caricature_filename}")

                    # Convert to SVG
                    svg_filename = f'drawing_{timestamp}.svg'
                    svg_filepath = os.path.join(SVGS_DIR, svg_filename)
                    svg_converter.image_to_svg(caricature_filepath, svg_filepath)

                    result['svg'] = svg_filename
                    print(f"SVG generated: {svg_filename}")

                    # Generate 3 alternative plotter-optimized SVG methods for evaluation
                    try:
                        print("\n" + "="*60)
                        print("🎨 Generating Alternative Plotter Methods...")
                        print("="*60)
                        base_name = f'drawing_{timestamp}'
                        plotter_methods = plotter_svg_generator.generate_all_methods(
                            caricature_filepath, base_name
                        )
                        print(f"✅ Generated {len(plotter_methods)} alternative SVG methods")
                        print("="*60 + "\n")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate alternative methods: {e}")

                    # Generate thick joining v1 (conservative)
                    try:
                        base_name = f'drawing_{timestamp}'
                        thick_variations = thick_joining_variations.generate_all_variations(
                            caricature_filepath, base_name
                        )
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate thick joining variations: {e}")

                    # Generate clean centerline variations (no double lines)
                    try:
                        base_name = f'drawing_{timestamp}'
                        clean_variations = clean_centerline_generator.generate_all_variations(
                            caricature_filepath, base_name
                        )
                        print(f"Generated {len(clean_variations)} clean centerline variations")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate clean centerline variations: {e}")

                    # If DexArm is calibrated, offer to draw
                    if dexarm_controller.is_calibrated():
                        result['can_draw'] = True
                        result['svg_path'] = svg_filepath
                else:
                    result['caricature_error'] = 'ComfyUI generation failed'

            except Exception as e:
                print(f"Caricature generation error: {e}")
                result['caricature_error'] = str(e)

        # Move DexArm to resting position if connected
        try:
            if dexarm_controller.is_connected:
                dexarm_controller.go_to_resting_position()
        except:
            pass  # Don't fail photo save if arm movement fails

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# DexArm Setup Routes
# ============================================================================

@app.route('/setup')
def setup():
    """DexArm setup wizard page"""
    return render_template('setup.html')

@app.route('/api/dexarm/connect', methods=['POST'])
def dexarm_connect():
    """Connect to DexArm"""
    try:
        data = request.get_json() or {}
        port = data.get('port')
        move_to_rest = data.get('move_to_rest', False)

        success = dexarm_controller.connect(port, move_to_rest=move_to_rest)

        if success:
            return jsonify({
                'success': True,
                'port': dexarm_controller.config.get('port'),
                'is_calibrated': dexarm_controller.is_calibrated(),
                'has_resting_position': dexarm_controller.get_resting_position() is not None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to DexArm'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/disconnect', methods=['POST'])
def dexarm_disconnect():
    """Disconnect from DexArm"""
    try:
        dexarm_controller.disconnect()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/status')
def dexarm_status():
    """Get DexArm status"""
    try:
        return jsonify({
            'connected': dexarm_controller.is_connected,
            'calibrated': dexarm_controller.is_calibrated(),
            'corners': dexarm_controller.get_corners(),
            'drawing_area': dexarm_controller.get_drawing_area(),
            'port': dexarm_controller.config.get('port'),
            'has_resting_position': dexarm_controller.get_resting_position() is not None
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'error': str(e)
        })

@app.route('/api/dexarm/auto-connect', methods=['POST'])
def dexarm_auto_connect():
    """
    Auto-connect to DexArm using saved config
    If calibrated, moves to resting position after connecting
    """
    try:
        # Get saved port and calibration status
        saved_port = dexarm_controller.config.get('port')
        is_calibrated = dexarm_controller.is_calibrated()
        has_rest = dexarm_controller.get_resting_position() is not None

        if not saved_port:
            return jsonify({
                'success': False,
                'error': 'No saved port configuration',
                'needs_setup': True
            })

        print(f"\n=== AUTO-CONNECT ===")
        print(f"Saved port: {saved_port}")
        print(f"Calibrated: {is_calibrated}")
        print(f"Has rest position: {has_rest}")

        # Connect (and move to rest if calibrated)
        move_to_rest = is_calibrated and has_rest
        success = dexarm_controller.connect(saved_port, move_to_rest=move_to_rest)

        if success:
            print("Auto-connect successful!")
            return jsonify({
                'success': True,
                'port': saved_port,
                'is_calibrated': is_calibrated,
                'moved_to_rest': move_to_rest
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to {saved_port}',
                'needs_setup': True
            })

    except Exception as e:
        print(f"Auto-connect error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/home', methods=['POST'])
def dexarm_home():
    """Home the DexArm"""
    try:
        dexarm_controller.home(timeout=30)
        return jsonify({'success': True})
    except TimeoutError as e:
        print(f"Homing timeout: {e}")
        return jsonify({
            'success': False,
            'error': 'Homing timed out. Please check if the arm is powered and not blocked.',
            'timeout': True
        }), 500
    except Exception as e:
        print(f"Homing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/move', methods=['POST'])
def dexarm_move():
    """Move DexArm to position"""
    try:
        data = request.get_json()
        x = data.get('x')
        y = data.get('y')
        z = data.get('z')
        feedrate = data.get('feedrate', 2000)

        dexarm_controller.move_to(x, y, z, feedrate)

        # Get position after move
        position = dexarm_controller.get_position()

        return jsonify({
            'success': True,
            'position': position
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/position')
def dexarm_get_position():
    """Get current DexArm position"""
    try:
        position = dexarm_controller.get_position()
        if position is None:
            return jsonify({
                'success': False,
                'error': 'Could not read position from DexArm'
            }), 500
        return jsonify({
            'success': True,
            'position': position
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/unlock', methods=['POST'])
def dexarm_unlock():
    """Unlock motors for manual positioning"""
    try:
        dexarm_controller.unlock_motors()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error unlocking motors: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/lock', methods=['POST'])
def dexarm_lock():
    """Lock motors"""
    try:
        dexarm_controller.lock_motors()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error locking motors: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/save-corner', methods=['POST'])
def dexarm_save_corner():
    """Save current position as a corner"""
    try:
        data = request.get_json()
        corner_name = data.get('corner')  # 'corner1' or 'corner2'

        if corner_name not in ['corner1', 'corner2']:
            return jsonify({
                'success': False,
                'error': 'Invalid corner name'
            }), 400

        # Ensure motors are locked before saving
        try:
            dexarm_controller.lock_motors()
        except Exception as e:
            print(f"Warning: Could not lock motors: {e}")
        
        # Small delay to ensure motors are stable
        import time
        time.sleep(0.1)

        position = dexarm_controller.save_corner(corner_name)

        # If this was corner2, calibration is complete - go to rest position
        if corner_name == 'corner2' and dexarm_controller.is_calibrated():
            print("📍 Calibration complete! Moving to resting position...")
            try:
                dexarm_controller.go_to_resting_position()
            except Exception as e:
                print(f"Warning: Could not move to rest: {e}")

        return jsonify({
            'success': True,
            'corner': corner_name,
            'position': position,
            'is_calibrated': dexarm_controller.is_calibrated()
        })

    except Exception as e:
        print(f"Error saving corner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/reset-calibration', methods=['POST'])
def dexarm_reset_calibration():
    """Reset calibration (clear corners)"""
    try:
        dexarm_controller.reset_calibration()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/save-resting', methods=['POST'])
def dexarm_save_resting():
    """Save current position as resting position"""
    try:
        # Ensure motors are locked before saving
        try:
            dexarm_controller.lock_motors()
        except Exception as e:
            print(f"Warning: Could not lock motors: {e}")
        
        # Small delay to ensure motors are stable
        import time
        time.sleep(0.1)

        position = dexarm_controller.save_resting_position()
        return jsonify({
            'success': True,
            'position': position
        })
    except Exception as e:
        print(f"Error saving resting position: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/go-resting', methods=['POST'])
def dexarm_go_resting():
    """Move to resting position"""
    try:
        dexarm_controller.go_to_resting_position()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dexarm/test-draw', methods=['POST'])
def dexarm_test_draw():
    """Draw test frame and X"""
    try:
        # Execute test draw and collect all messages
        messages = []
        for message in dexarm_controller.test_draw_frame():
            messages.append(message)

        return jsonify({
            'success': True,
            'messages': messages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/drawing-progress')
def drawing_progress_stream():
    """Server-Sent Events endpoint for real-time drawing progress"""
    def generate():
        """Generate SSE messages with drawing progress"""
        while True:
            with progress_lock:
                if drawing_progress['active']:
                    percentage = 0
                    if drawing_progress['total'] > 0:
                        percentage = int((drawing_progress['current'] / drawing_progress['total']) * 100)

                    yield f"data: {json.dumps({'progress': percentage, 'current': drawing_progress['current'], 'total': drawing_progress['total'], 'message': drawing_progress.get('message', '')})}\n\n"
                else:
                    yield f"data: {json.dumps({'progress': 0, 'current': 0, 'total': 0, 'active': False, 'message': ''})}\n\n"

            time.sleep(0.1)  # Update every 100ms

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/draw-svg', methods=['POST'])
def draw_svg():
    """Draw an SVG file with the DexArm"""
    try:
        data = request.get_json()
        svg_filename = data.get('svg')

        if not svg_filename:
            return jsonify({
                'success': False,
                'error': 'No SVG filename provided'
            }), 400

        # Use configured SVG method from settings
        svg_method = app_settings.get('svg_method', 'original')
        if svg_method != 'original':
            # Replace .svg with _METHOD.svg (e.g., drawing_123.svg → drawing_123_clean_v1.svg)
            base_name = svg_filename.replace('.svg', '')
            variant_filename = f"{base_name}_{svg_method}.svg"
            variant_path = os.path.join(SVGS_DIR, variant_filename)

            if os.path.exists(variant_path):
                print(f"Using SVG method: {svg_method}")
                svg_path = variant_path
                svg_filename = variant_filename
            else:
                print(f"Warning: Method {svg_method} not found, using original")
                svg_path = os.path.join(SVGS_DIR, svg_filename)
        else:
            svg_path = os.path.join(SVGS_DIR, svg_filename)

        if not os.path.exists(svg_path):
            return jsonify({
                'success': False,
                'error': 'SVG file not found'
            }), 404

        # Check connection status
        if not dexarm_controller.is_connected:
            return jsonify({
                'success': False,
                'error': 'DexArm not connected. Please visit /setup to connect and calibrate.'
            }), 400

        if not dexarm_controller.is_calibrated():
            return jsonify({
                'success': False,
                'error': 'DexArm not calibrated. Please visit /setup to calibrate.'
            }), 400

        print(f"\n🤖 === STARTING DRAWING ===")
        print(f"📄 SVG file: {svg_filename}")

        # Get drawing area from calibration
        drawing_area = dexarm_controller.get_drawing_area()

        # Auto-rotate SVG if orientation doesn't match drawing area
        import xml.etree.ElementTree as ET
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Get SVG dimensions
        viewbox = root.get('viewBox')
        if viewbox:
            parts = viewbox.replace(',', ' ').split()
            if len(parts) >= 4:
                svg_width = float(parts[2])
                svg_height = float(parts[3])
            else:
                svg_width = float(root.get('width', '100').replace('px', ''))
                svg_height = float(root.get('height', '100').replace('px', ''))
        else:
            svg_width = float(root.get('width', '100').replace('px', ''))
            svg_height = float(root.get('height', '100').replace('px', ''))

        # Check if rotation needed
        svg_is_portrait = svg_height > svg_width
        area_is_portrait = drawing_area['height'] > drawing_area['width']

        if svg_is_portrait != area_is_portrait:
            print(f"🔄 Rotating SVG to match drawing area orientation")
            # Add rotation transform to all paths, lines, and circles
            for elem in root.iter():
                if elem.tag.endswith('path') or elem.tag.endswith('line') or elem.tag.endswith('circle'):
                    transform = f"rotate(90 {svg_width/2} {svg_height/2})"
                    existing = elem.get('transform', '')
                    elem.set('transform', f"{existing} {transform}" if existing else transform)

            # Save rotated version
            rotated_path = svg_path.replace('.svg', '_rotated.svg')
            tree.write(rotated_path, encoding='unicode', xml_declaration=True)
            svg_path = rotated_path

        # Parse SVG file
        svg_parser.parse_svg_file(svg_path)

        # Convert paths to drawing commands using settings
        pen_lift_height = app_settings.get('pen_lift_height', 16)
        max_commands = app_settings.get('max_commands', 5000)
        commands = svg_parser.convert_to_drawing_commands(
            drawing_area,
            z_up=pen_lift_height,
            max_commands=max_commands
        )

        if not commands:
            return jsonify({
                'success': False,
                'error': 'No drawing commands generated from SVG'
            }), 400

        print(f"🎨 Executing {len(commands)} drawing commands...")

        # Initialize progress tracking
        with progress_lock:
            drawing_progress['current'] = 0
            drawing_progress['total'] = len(commands)
            drawing_progress['active'] = True

        # Track current Z position for safe movements
        current_z = None
        pos = dexarm_controller.get_position()
        if pos:
            current_z = pos['z']

        # Execute drawing commands with safe movement
        for i, cmd in enumerate(commands):
            if cmd['type'] == 'move':
                # Pen up movement (fast) - safe move lifts Z first
                current_z = dexarm_controller.move_to_safe(
                    cmd['x'], cmd['y'], cmd['z'], cmd['feedrate'], current_z
                )
            elif cmd['type'] == 'draw':
                # Pen down drawing - safe move moves XY first, then lowers Z
                current_z = dexarm_controller.move_to_safe(
                    cmd['x'], cmd['y'], cmd['z'], cmd['feedrate'], current_z
                )

            # Update progress
            with progress_lock:
                drawing_progress['current'] = i + 1

            # Progress feedback every 50 commands
            if i % 50 == 0:
                progress = int((i / len(commands)) * 100)
                print(f"  Progress: {progress}%")

        # Keep progress at 100% while returning to rest (5-second pause)
        print(f"🏁 Drawing complete! Returning to rest...")
        with progress_lock:
            drawing_progress['current'] = len(commands)
            drawing_progress['message'] = 'Your drawing is ready!'

        # Return to resting position (takes ~2-3 seconds)
        dexarm_controller.go_to_resting_position()

        # Hold at 100% for 5 seconds total
        import time
        time.sleep(5)

        # Mark drawing as complete
        with progress_lock:
            drawing_progress['active'] = False
            drawing_progress['current'] = 0
            drawing_progress['total'] = 0
            drawing_progress['message'] = ''

        return jsonify({
            'success': True,
            'message': f'Drawing completed! {len(commands)} commands executed.',
            'commands_executed': len(commands)
        })

    except Exception as e:
        print(f"❌ Drawing error: {e}")
        import traceback
        traceback.print_exc()

        # Reset progress on error
        with progress_lock:
            drawing_progress['active'] = False
            drawing_progress['current'] = 0
            drawing_progress['total'] = 0

        # Try to return to resting position even on error
        try:
            if dexarm_controller.is_connected:
                dexarm_controller.go_to_resting_position()
        except:
            pass

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Upload an image and prompt for processing"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400

        file = request.files['image']
        prompt = request.form.get('prompt', '')

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Load and process uploaded file
        img = Image.open(file.stream)
        
        # Convert to RGB if necessary (JPG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        
        # Apply sharpening
        img = img.filter(ImageFilter.SHARPEN)
        
        # Optional: Enhance sharpness further
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)  # 1.5x sharpness boost
        
        # Save processed file as JPG
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        photo_filename = f'uploaded_{timestamp}.jpg'
        photo_filepath = os.path.join(PHOTOS_DIR, photo_filename)
        img.save(photo_filepath, 'JPEG', quality=85, optimize=True)

        # Save prompt
        if prompt:
            metadata_file = photo_filepath.replace('.jpg', '.txt')
            with open(metadata_file, 'w') as f:
                f.write(prompt)

        result = {
            'success': True,
            'filename': photo_filename,
            'prompt': prompt,
            'comfyui_available': comfyui_client.is_available,
            'dexarm_calibrated': dexarm_controller.is_calibrated()
        }

        # Generate caricature if ComfyUI is available
        if comfyui_client.is_available:
            try:
                print(f"Generating caricature for uploaded image: {prompt}")
                caricature_img = comfyui_client.generate_caricature(photo_filepath, prompt)

                if caricature_img:
                    caricature_filename = f'caricature_{timestamp}.png'
                    caricature_filepath = os.path.join(CARICATURES_DIR, caricature_filename)
                    caricature_img.save(caricature_filepath)

                    result['caricature'] = caricature_filename

                    # Convert to SVG
                    svg_filename = f'drawing_{timestamp}.svg'
                    svg_filepath = os.path.join(SVGS_DIR, svg_filename)
                    svg_converter.image_to_svg(caricature_filepath, svg_filepath)

                    result['svg'] = svg_filename

                    # Generate 3 alternative plotter-optimized SVG methods for evaluation
                    try:
                        print("\n" + "="*60)
                        print("🎨 Generating Alternative Plotter Methods...")
                        print("="*60)
                        base_name = f'drawing_{timestamp}'
                        plotter_methods = plotter_svg_generator.generate_all_methods(
                            caricature_filepath, base_name
                        )
                        print(f"✅ Generated {len(plotter_methods)} alternative SVG methods")
                        print("="*60 + "\n")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate alternative methods: {e}")

                    # Generate thick joining v1 (conservative)
                    try:
                        base_name = f'drawing_{timestamp}'
                        thick_variations = thick_joining_variations.generate_all_variations(
                            caricature_filepath, base_name
                        )
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate thick joining variations: {e}")

                    # Generate clean centerline variations (no double lines)
                    try:
                        base_name = f'drawing_{timestamp}'
                        clean_variations = clean_centerline_generator.generate_all_variations(
                            caricature_filepath, base_name
                        )
                        print(f"Generated {len(clean_variations)} clean centerline variations")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate clean centerline variations: {e}")

                    if dexarm_controller.is_calibrated():
                        result['can_draw'] = True
                        result['svg_path'] = svg_filepath

            except Exception as e:
                print(f"Caricature generation error: {e}")
                result['caricature_error'] = str(e)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/comfyui/status')
def comfyui_status():
    """Check ComfyUI availability"""
    comfyui_client._check_availability()
    return jsonify({
        'available': comfyui_client.is_available
    })

@app.route('/api/photos/list')
def list_photos():
    """List all saved photos with their prompts"""
    try:
        photos = []

        # Get all photos in the photos directory
        for filename in os.listdir(PHOTOS_DIR):
            if (filename.endswith('.jpg') or filename.endswith('.png')) and not filename.startswith('.'):
                filepath = os.path.join(PHOTOS_DIR, filename)

                # Get file timestamp
                timestamp = os.path.getmtime(filepath)

                # Determine file extension
                file_ext = '.jpg' if filename.endswith('.jpg') else '.png'

                # Try to load prompt from metadata file
                prompt = ''
                metadata_file = filepath.replace(file_ext, '.txt')
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        prompt = f.read().strip()

                # Check if caricature exists
                caricature_filename = filename.replace('photo_', 'caricature_').replace('uploaded_', 'caricature_')
                caricature_exists = os.path.exists(os.path.join(CARICATURES_DIR, caricature_filename))

                # Check if SVG exists
                svg_filename = filename.replace('photo_', 'drawing_').replace('uploaded_', 'drawing_').replace(file_ext, '.svg')
                svg_exists = os.path.exists(os.path.join(SVGS_DIR, svg_filename))

                photos.append({
                    'filename': filename,
                    'prompt': prompt,
                    'timestamp': timestamp,
                    'caricature_exists': caricature_exists,
                    'svg_exists': svg_exists,
                    'caricature_filename': caricature_filename if caricature_exists else None,
                    'svg_filename': svg_filename if svg_exists else None
                })

        # Sort by timestamp, newest first
        photos.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({
            'success': True,
            'photos': photos
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/photos/process', methods=['POST'])
def process_saved_photo():
    """Process a saved photo (generate caricature from existing photo)"""
    try:
        data = request.get_json()
        photo_filename = data.get('filename')
        prompt = data.get('prompt', '')

        if not photo_filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400

        photo_filepath = os.path.join(PHOTOS_DIR, photo_filename)

        if not os.path.exists(photo_filepath):
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404

        # Determine file extension and extract timestamp
        file_ext = '.jpg' if photo_filename.endswith('.jpg') else '.png'
        timestamp = photo_filename.replace('photo_', '').replace('uploaded_', '').replace(file_ext, '')

        result = {
            'success': True,
            'filename': photo_filename,
            'prompt': prompt,
            'comfyui_available': comfyui_client.is_available,
            'dexarm_calibrated': dexarm_controller.is_calibrated()
        }

        # Generate caricature if ComfyUI is available
        if comfyui_client.is_available:
            try:
                print(f"Processing saved photo: {photo_filename} with prompt: {prompt}")
                caricature_img = comfyui_client.generate_caricature(photo_filepath, prompt)

                if caricature_img:
                    caricature_filename = f'caricature_{timestamp}.png'
                    caricature_filepath = os.path.join(CARICATURES_DIR, caricature_filename)
                    caricature_img.save(caricature_filepath)

                    result['caricature'] = caricature_filename
                    print(f"Caricature saved: {caricature_filename}")

                    # Convert to SVG
                    svg_filename = f'drawing_{timestamp}.svg'
                    svg_filepath = os.path.join(SVGS_DIR, svg_filename)
                    svg_converter.image_to_svg(caricature_filepath, svg_filepath)

                    result['svg'] = svg_filename
                    print(f"SVG generated: {svg_filename}")

                    # Generate 3 alternative plotter-optimized SVG methods for evaluation
                    try:
                        print("\n" + "="*60)
                        print("🎨 Generating Alternative Plotter Methods...")
                        print("="*60)
                        base_name = f'drawing_{timestamp}'
                        plotter_methods = plotter_svg_generator.generate_all_methods(
                            caricature_filepath, base_name
                        )
                        print(f"✅ Generated {len(plotter_methods)} alternative SVG methods")
                        print("="*60 + "\n")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate alternative methods: {e}")

                    # Generate thick joining v1 (conservative)
                    try:
                        base_name = f'drawing_{timestamp}'
                        thick_variations = thick_joining_variations.generate_all_variations(
                            caricature_filepath, base_name
                        )
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate thick joining variations: {e}")

                    # Generate clean centerline variations (no double lines)
                    try:
                        base_name = f'drawing_{timestamp}'
                        clean_variations = clean_centerline_generator.generate_all_variations(
                            caricature_filepath, base_name
                        )
                        print(f"Generated {len(clean_variations)} clean centerline variations")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not generate clean centerline variations: {e}")

                    if dexarm_controller.is_calibrated():
                        result['can_draw'] = True
                        result['svg_path'] = svg_filepath
                else:
                    result['caricature_error'] = 'ComfyUI generation failed'

            except Exception as e:
                print(f"Caricature generation error: {e}")
                result['caricature_error'] = str(e)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/photos/delete', methods=['POST'])
def delete_photo():
    """Delete a photo and its associated files"""
    try:
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            }), 400

        # Determine file extension
        file_ext = '.jpg' if filename.endswith('.jpg') else '.png'

        # Extract timestamp from filename
        timestamp = filename.replace('photo_', '').replace('uploaded_', '').replace(file_ext, '')

        # Delete photo
        photo_path = os.path.join(PHOTOS_DIR, filename)
        if os.path.exists(photo_path):
            os.remove(photo_path)
            print(f"Deleted photo: {filename}")

        # Delete metadata file
        metadata_path = photo_path.replace(file_ext, '.txt')
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        # Delete caricature if exists
        caricature_filename = f"caricature_{timestamp}.png"
        caricature_path = os.path.join(CARICATURES_DIR, caricature_filename)
        if os.path.exists(caricature_path):
            os.remove(caricature_path)
            print(f"Deleted caricature: {caricature_filename}")

        # Delete SVG if exists
        svg_filename = f"drawing_{timestamp}.svg"
        svg_path = os.path.join(SVGS_DIR, svg_filename)
        if os.path.exists(svg_path):
            os.remove(svg_path)
            print(f"Deleted SVG: {svg_filename}")

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error deleting photo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting AI Sketch Booth...")
    print("Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
