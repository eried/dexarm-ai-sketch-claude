"""
ComfyUI API Client
==================
Handles communication with ComfyUI for generating caricature images.
"""

import json
import requests
import websocket
import uuid
import time
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import cv2
import numpy as np

# Create debug folder
DEBUG_DIR = "debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


class ComfyUIClient:
    """Client for interacting with ComfyUI API"""

    def __init__(self, server_address="127.0.0.1:8000"):
        """
        Initialize ComfyUI client

        Args:
            server_address (str): ComfyUI server address (default: 127.0.0.1:8000)
        """
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.is_available = False
        self._check_availability()

    def _check_availability(self):
        """Check if ComfyUI server is running"""
        try:
            response = requests.get(f"http://{self.server_address}/system_stats", timeout=2)
            self.is_available = response.status_code == 200
        except:
            self.is_available = False

    def queue_prompt(self, prompt):
        """
        Queue a prompt for generation

        Args:
            prompt (dict): ComfyUI workflow prompt

        Returns:
            dict: Response with prompt_id
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        response = requests.post(
            f"http://{self.server_address}/prompt",
            data=data
        )
        return response.json()

    def get_image(self, filename, subfolder, folder_type):
        """
        Retrieve generated image from ComfyUI

        Args:
            filename (str): Image filename
            subfolder (str): Subfolder path
            folder_type (str): Folder type

        Returns:
            PIL.Image: Generated image
        """
        # Build the URL parameters
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }

        # Try the /view endpoint
        response = requests.get(
            f"http://{self.server_address}/view",
            params=params
        )

        print(f"Getting image: {filename}, subfolder: {subfolder}, type: {folder_type}")
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers.get('content-type')}")

        if response.status_code != 200:
            print(f"Error response: {response.text[:200]}")
            raise Exception(f"Failed to get image: {response.status_code}")

        # Check if response is actually an image
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            print(f"Response is not an image. Content: {response.text[:200]}")
            raise Exception(f"Response is not an image: {content_type}")

        return Image.open(BytesIO(response.content))

    def get_history(self, prompt_id):
        """
        Get prompt history

        Args:
            prompt_id (str): Prompt ID

        Returns:
            dict: History data
        """
        response = requests.get(
            f"http://{self.server_address}/history/{prompt_id}"
        )
        return response.json()

    def upload_image(self, image_path):
        """
        Upload an image to ComfyUI

        Args:
            image_path (str): Path to image file

        Returns:
            dict: Upload response with filename
        """
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(
                f"http://{self.server_address}/upload/image",
                files=files
            )
        return response.json()

    def wait_for_completion(self, prompt_id, timeout=300):
        """
        Wait for prompt completion via polling (more reliable than WebSocket)

        Args:
            prompt_id (str): Prompt ID to wait for
            timeout (int): Timeout in seconds

        Returns:
            bool: True if completed successfully
        """
        start_time = time.time()

        print(f"Waiting for completion of prompt: {prompt_id}")

        while True:
            if time.time() - start_time > timeout:
                print("Timeout waiting for completion")
                return False

            try:
                # Poll the history endpoint to check if generation is complete
                history = self.get_history(prompt_id)

                # If prompt_id exists in history, it's done
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    if outputs:
                        print(f"Generation complete! Found outputs: {list(outputs.keys())}")
                        return True

                # Wait a bit before polling again
                time.sleep(2)

            except Exception as e:
                print(f"Error checking completion: {e}")
                time.sleep(2)

    def _cutout_person(self, image_path):
        """
        Detect and cutout the person from the image
        If detection fails, just use the whole image

        Args:
            image_path (str): Path to input image

        Returns:
            str: Path to processed image (cropped or original)
        """
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                print("⚠️  Could not load image, using original")
                return image_path

            debug_log = []
            debug_log.append("=== PERSON DETECTION DEBUG ===\n\n")

            # Just try face detection - it's the most reliable
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) == 0:
                # No face detected - use full image
                debug_log.append("ℹ️  No face detected\n")
                debug_log.append("✅ Using full image\n\n")
                debug_path = os.path.join(DEBUG_DIR, "step1_detection.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write("".join(debug_log))
                    f.flush()
                print(f"✅ Debug saved: {debug_path}")
                print("ℹ️  Using full image (no face detected)")
                return image_path

            # Face detected - use it with generous expansion
            debug_log.append(f"✅ Found {len(faces)} face(s)\n")
            x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
            debug_log.append(f"✅ Face location: x={x}, y={y}, w={w}, h={h}\n\n")

            # VERY GENEROUS EXPANSION - ensure we get full head and body
            # Expand to get full body based on face
            expand_w = int(w * 1.5)  # 150% wider on each side
            expand_h_top = int(h * 0.5)  # 50% more space above for hair/head
            expand_h_bottom = int(h * 4)  # 4x face height below for body

            original_x, original_y, original_w, original_h = x, y, w, h
            x = max(0, x - expand_w)
            y = max(0, y - expand_h_top)
            w = min((original_w + expand_w * 2), img.shape[1] - x)
            h = min((original_h + expand_h_top + expand_h_bottom), img.shape[0] - y)

            # Check if expansion is too small or weird - if so, use full image
            img_area = img.shape[0] * img.shape[1]
            crop_area = w * h
            if crop_area < (img_area * 0.1) or crop_area > (img_area * 0.95):
                debug_log.append("⚠️  Crop area suspicious, using full image instead\n")
                debug_path = os.path.join(DEBUG_DIR, "step1_detection.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write("".join(debug_log))
                    f.flush()
                print("ℹ️  Using full image (crop size suspicious)")
                return image_path

            debug_log.append(f"🔄 Expanding to include body:\n")
            debug_log.append(f"   Face: x={original_x}, y={original_y}, w={original_w}, h={original_h}\n")
            debug_log.append(f"   Expanded: x={x}, y={y}, w={w}, h={h}\n\n")

            # Draw debug visualization
            img_debug = img.copy()
            cv2.rectangle(img_debug, (original_x, original_y), (original_x+original_w, original_y+original_h), (0, 0, 255), 2)
            cv2.rectangle(img_debug, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(img_debug, f"Face detected, expanded for body",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(img_debug, f"Red=Face, Green=Final crop",
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imwrite(os.path.join(DEBUG_DIR, "step1_detection.jpg"), img_debug)
            debug_log.append(f"📸 Saved: step1_detection.jpg\n\n")

            # Crop
            person_crop = img[y:y+h, x:x+w]
            cv2.imwrite(os.path.join(DEBUG_DIR, "step2_final_crop.jpg"), person_crop)
            debug_log.append(f"📸 Saved: step2_final_crop.jpg (sent to ComfyUI)\n\n")

            # Save as cutout
            cutout_path = image_path.replace('.jpg', '_cutout.png').replace('.png', '_cutout.png')
            cv2.imwrite(cutout_path, person_crop)

            # Save debug log
            debug_path = os.path.join(DEBUG_DIR, "step1_detection.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write("".join(debug_log))
                f.flush()

            print(f"✅ Debug saved: {debug_path}")
            print(f"✅ Person crop created: {cutout_path}")
            return cutout_path

        except Exception as e:
            print(f"⚠️  Error in person detection: {e}")
            import traceback
            traceback.print_exc()
            print("ℹ️  Using full image as fallback")
            return image_path

    def generate_caricature(self, image_path, prompt_text, workflow_json_path="workflow.json"):
        """
        Generate a big-head caricature from an image and prompt

        Args:
            image_path (str): Path to input photo
            prompt_text (str): User's scenario prompt (e.g., "on a bike")
            workflow_json_path (str): Path to ComfyUI workflow JSON (default: workflow.json)

        Returns:
            PIL.Image: Generated caricature image, or None if failed
        """
        try:
            print(f"\n🎨 === STARTING CARICATURE GENERATION ===")
            print(f"📷 Input image: {image_path}")
            print(f"💬 Prompt: '{prompt_text}'")
            print(f"🔌 ComfyUI available: {self.is_available}")

            if not self.is_available:
                print(f"❌ ComfyUI not available! Check if it's running on {self.server_address}")
                return None

            # Step 1: Cutout the person from background
            print(f"\n🔍 Step 1: Detecting person...")
            cutout_path = self._cutout_person(image_path)
            print(f"✅ Cutout created: {cutout_path}")

            # Upload the cutout image
            print(f"\n📤 Step 2: Uploading to ComfyUI...")
            upload_result = self.upload_image(cutout_path)

            if 'name' not in upload_result:
                print(f"❌ Upload failed: {upload_result}")
                return None

            uploaded_filename = upload_result['name']
            print(f"✅ Uploaded as: {uploaded_filename}")

            # Use the SDXL LineArt workflow
            workflow_path = "workflow_lineart.json"
            if os.path.exists(workflow_path):
                print(f"\n📋 Loading LineArt workflow from: {workflow_path}")
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                workflow = self._replace_workflow_placeholders(workflow, uploaded_filename, prompt_text)
                print(f"✅ LineArt workflow loaded and placeholders replaced")
            else:
                print(f"⚠️ LineArt workflow not found, using default DreamShaper")
                workflow = self._get_default_caricature_workflow(uploaded_filename, prompt_text)

            # DEBUG: Save workflow and prompts
            debug_info = []
            debug_info.append("=== COMFYUI WORKFLOW DEBUG ===\n\n")
            debug_info.append(f"📝 User prompt: '{prompt_text}'\n\n")
            
            # Log the custom prompt that was inserted
            if '15' in workflow and 'inputs' in workflow['15']:
                debug_info.append(f"📝 Node 15 (Text String) - Custom prompt:\n")
                debug_info.append(f"   text: {workflow['15']['inputs'].get('text', '')}\n")
                debug_info.append(f"   text_b: {workflow['15']['inputs'].get('text_b', '')}\n")
                debug_info.append(f"   text_c: {workflow['15']['inputs'].get('text_c', '')}\n\n")
            
            # Log the SDXL Prompt Styler settings
            if '29' in workflow and 'inputs' in workflow['29']:
                debug_info.append(f"📝 Node 29 (SDXL Prompt Styler):\n")
                debug_info.append(f"   style: {workflow['29']['inputs'].get('style', '')}\n")
                debug_info.append(f"   text_negative: {workflow['29']['inputs'].get('text_negative', '')}\n\n")
            
            # Try to find and log CLIP text encoders
            for node_id, node_data in workflow.items():
                if isinstance(node_data, dict) and 'class_type' in node_data:
                    if node_data['class_type'] == 'CLIPTextEncode':
                        text = node_data.get('inputs', {}).get('text', '')
                        if text:
                            debug_info.append(f"📝 CLIP Text Encode (Node {node_id}):\n{text}\n\n")
            
            debug_info.append(f"⚙️  Workflow nodes: {len(workflow)}\n\n")

            debug_path = os.path.join(DEBUG_DIR, "step4_comfyui_workflow.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write("".join(debug_info))
                f.flush()

            with open(os.path.join(DEBUG_DIR, "step4_workflow.json"), "w", encoding="utf-8") as f:
                json.dump(workflow, f, indent=2)
                f.flush()

            print(f"✅ Debug saved: {debug_path}")
            print(f"✅ Custom prompt inserted: '{prompt_text}'")

            # Queue the prompt
            print(f"\n🚀 Step 3: Queuing generation in ComfyUI...")
            queue_result = self.queue_prompt(workflow)
            print(f"Queue result: {queue_result}")

            # ComfyUI returns prompt_id in different ways depending on version
            prompt_id = queue_result.get('prompt_id') or queue_result.get('id')

            if not prompt_id:
                print(f"No prompt_id in response: {queue_result}")
                return None

            # Wait for completion
            if not self.wait_for_completion(prompt_id):
                print("ComfyUI generation timed out")
                return None

            # Get the output image
            history = self.get_history(prompt_id)
            if prompt_id not in history:
                print("Prompt ID not found in history")
                return None

            # Extract output image info (adjust based on your workflow)
            outputs = history[prompt_id]['outputs']

            # Get the generated image from "Final Upscale BW Level" node (node 64)
            generated_img = None
            
            # First, try to get from node 64 (Final Upscale BW Level)
            if '64' in outputs and 'images' in outputs['64']:
                for image_info in outputs['64']['images']:
                    print(f"Getting image from node 64 (Final Upscale BW Level): {image_info['filename']}")
                    generated_img = self.get_image(
                        image_info['filename'],
                        image_info['subfolder'],
                        image_info['type']
                    )
                    break
            
            # Fallback: try any node with images
            if generated_img is None:
                print("Node 64 not found, trying other output nodes...")
                for node_id in outputs:
                    node_output = outputs[node_id]
                    if 'images' in node_output:
                        for image_info in node_output['images']:
                            print(f"Getting image from node {node_id}: {image_info['filename']}")
                            generated_img = self.get_image(
                                image_info['filename'],
                                image_info['subfolder'],
                                image_info['type']
                            )
                            break
                    if generated_img:
                        break

            if generated_img is None:
                print("ERROR: No generated image found in any output node!")
                return None

            # DEBUG: Save ComfyUI output
            generated_img.save(os.path.join(DEBUG_DIR, "step5_comfyui_output.jpg"))
            debug_final = []
            debug_final.append("=== COMFYUI OUTPUT DEBUG ===\n\n")
            debug_final.append(f"✅ ComfyUI generated image successfully\n")
            debug_final.append(f"📸 Saved: step5_comfyui_output.jpg\n\n")
            debug_final.append(f"✅ Using ComfyUI output directly (no B&W conversion)\n")

            debug_path = os.path.join(DEBUG_DIR, "step5_output.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write("".join(debug_final))
                f.flush()

            print(f"✅ Debug saved: {debug_path}")
            print(f"✅ Returning ComfyUI generated image directly")
            return generated_img

        except Exception as e:
            print(f"Error in generate_caricature: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _replace_workflow_placeholders(self, workflow, image_filename, prompt_text):
        """
        Replace placeholders in workflow with actual values

        Args:
            workflow (dict): Workflow template
            image_filename (str): Uploaded image filename
            prompt_text (str): User's custom prompt

        Returns:
            dict: Workflow with placeholders replaced
        """
        # Convert workflow to JSON string for easy replacement
        workflow_str = json.dumps(workflow)

        # Build custom prompt with STRONG caricature emphasis + background + dynamic action
        # Key improvements:
        # 1. Multiple head/body size keywords to override BLIP and emphasize proportions
        # 2. Dynamic action words to prevent stiff poses
        # 3. Background/environment keywords to prevent empty backgrounds
        # 4. Put action/background FIRST to override BLIP caption
        if prompt_text:
            custom_prompt = f"dynamic action pose, full scene illustration, {prompt_text}, detailed background environment, bobblehead caricature character, huge oversized exaggerated head, massive giant head, tiny miniature small body, exaggerated proportions, fun energetic pose, dynamic movement, cartoon caricature art style, illustration, "
        else:
            custom_prompt = "dynamic action pose, full scene illustration, detailed background environment, bobblehead caricature character, huge oversized exaggerated head, massive giant head, tiny miniature small body, exaggerated proportions, fun energetic pose, dynamic movement, cartoon caricature art style, illustration, "

        # Replace placeholders
        workflow_str = workflow_str.replace("{{INPUT_IMAGE}}", image_filename)
        workflow_str = workflow_str.replace("{{CUSTOM_PROMPT}}", custom_prompt)

        # Convert back to dict
        workflow = json.loads(workflow_str)
        
        # IMPORTANT: Modify node 14 (Text Concatenate) to use ONLY the custom prompt
        # SKIP BLIP CAPTION because it describes "isolated/empty background" from the cutout image
        # Originally workflow has: text_a=BLIP + text_b=custom + text_c=style1 + text_d=style2
        # We change to: text_a=custom + text_b=style1 + text_c=style2 + text_d=empty
        # This prevents BLIP from adding "empty background" descriptions
        if '14' in workflow and 'inputs' in workflow['14']:
            workflow['14']['inputs']['text_a'] = ["15", 0]  # Custom prompt (with background/action keywords!)
            workflow['14']['inputs']['text_b'] = ["15", 1]  # "black and white, colorless"
            workflow['14']['inputs']['text_c'] = ["15", 2]  # "lineart, linework"
            workflow['14']['inputs']['text_d'] = ""  # Empty (skip BLIP entirely)

            print(f"✅ Modified node 14: Using custom prompt ONLY, skipping BLIP caption to prevent empty backgrounds")
        
        # Clear hardcoded example prompts in ShowText nodes (227 and 58)
        # These are just for display and shouldn't interfere, but let's clear them anyway
        if '227' in workflow and 'inputs' in workflow['227']:
            if 'text_0' in workflow['227']['inputs']:
                workflow['227']['inputs']['text_0'] = ""
            if 'text_1' in workflow['227']['inputs']:
                workflow['227']['inputs']['text_1'] = ""
        
        if '58' in workflow and 'inputs' in workflow['58']:
            if 'text_0' in workflow['58']['inputs']:
                workflow['58']['inputs']['text_0'] = ""
            if 'text_1' in workflow['58']['inputs']:
                workflow['58']['inputs']['text_1'] = ""
        
        return workflow

    def _get_default_caricature_workflow(self, image_filename, prompt_text):
        """
        Image-to-image workflow for creating caricatures

        Args:
            image_filename (str): Uploaded image filename
            prompt_text (str): User's prompt

        Returns:
            dict: ComfyUI workflow
        """
        # Build the caricature prompt - line art style (video tutorial approach)
        full_prompt = f"black and white line art, ink drawing, clean lines, no shading, no colors, bobblehead caricature, huge oversized head, tiny body, person {prompt_text}, simple line drawing, outline only, coloring book style"

        # Real workflow exported from ComfyUI (based on line art tutorial)
        workflow = {
            "3": {
                "inputs": {
                    "seed": int(time.time()),  # Random seed each time
                    "steps": 20,  # Tutorial uses 20 steps
                    "cfg": 8,  # Tutorial uses 8-10 CFG
                    "sampler_name": "euler_ancestral",  # Best for line art per tutorial
                    "scheduler": "karras",  # Karras for better quality
                    "denoise": 0.30,  # VERY LOW = stay very close to input (tutorial value)
                    "model": ["14", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["12", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "6": {
                "inputs": {
                    "text": full_prompt,
                    "clip": ["14", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "7": {
                "inputs": {
                    "text": "photograph, realistic, photorealistic, colored, color, shading, shadows, gradient, gray tones, 3d render, blurry, watermark, text, dark background, thick fill, complex details",
                    "clip": ["14", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["14", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "9": {
                "inputs": {
                    "filename_prefix": "caricature",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            },
            "10": {
                "inputs": {
                    "image": image_filename
                },
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"}
            },
            "12": {
                "inputs": {
                    "pixels": ["18", 0],
                    "vae": ["14", 2]
                },
                "class_type": "VAEEncode",
                "_meta": {"title": "VAE Encode"}
            },
            "14": {
                "inputs": {
                    # DreamShaper 8 - excellent for cartoons and line art
                    "ckpt_name": "dreamshaper_8.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "18": {
                "inputs": {
                    "upscale_method": "nearest-exact",
                    "megapixels": 0.25,
                    "image": ["10", 0]
                },
                "class_type": "ImageScaleToTotalPixels",
                "_meta": {"title": "Scale Image to Total Pixels"}
            }
        }

        return workflow


# Global client instance
comfyui_client = ComfyUIClient()
