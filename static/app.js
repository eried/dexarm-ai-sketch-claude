// Global variables
let video = null;
let canvas = null;
let suggestions = [];
let currentSVG = null;
let isFullscreenMode = false;
let paintbrushLoader = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    video = document.getElementById('video');
    canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const drawBtn = document.getElementById('drawBtn');
    const retakeBtn = document.getElementById('retakeBtn');
    const closeGalleryBtn = document.getElementById('closeGalleryBtn');

    // Auto-connect to DexArm if previously configured
    tryAutoConnectDexArm();

    // Load suggestions from server
    await loadSuggestions();

    // Initialize camera
    await initCamera();

    // Display random suggestions
    displayRandomSuggestions();

    // Event listeners
    captureBtn.addEventListener('click', capturePhoto);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    uploadBtn.addEventListener('click', openPhotoGallery);
    drawBtn.addEventListener('click', drawCurrentImage);
    retakeBtn.addEventListener('click', closePreview);
    closeGalleryBtn.addEventListener('click', closeGallery);

    // Monitor fullscreen state
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
});

// Load suggestions from JSON file via API
async function loadSuggestions() {
    try {
        const response = await fetch('/api/suggestions');
        const data = await response.json();
        suggestions = data.suggestions || [];
        console.log(`Loaded ${suggestions.length} suggestions`);
    } catch (error) {
        console.error('Error loading suggestions:', error);
        suggestions = ['with a funny hat', 'on the moon', 'in a disco'];
    }
}

// Initialize camera
async function initCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1920 },
                height: { ideal: 1080 },
                facingMode: 'user'
            },
            audio: false
        });
        video.srcObject = stream;
        showStatus('Camera ready!', 'success');
    } catch (error) {
        console.error('Error accessing camera:', error);
        showStatus('Error: Could not access camera', 'error');
    }
}

// Display random suggestions as clickable items
function displayRandomSuggestions(count = 9) {
    if (suggestions.length === 0) return;

    const suggestionsGrid = document.getElementById('suggestionsGrid');
    suggestionsGrid.innerHTML = '';

    // Get random suggestions
    const shuffled = [...suggestions].sort(() => Math.random() - 0.5);
    const displayedSuggestions = shuffled.slice(0, count);

    // Create clickable items
    displayedSuggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = suggestion;
        item.addEventListener('click', () => {
            document.getElementById('promptInput').value = suggestion;
            // Refresh suggestions after clicking one
            displayRandomSuggestions();
        });
        suggestionsGrid.appendChild(item);
    });
}

// Handle fullscreen state changes
function handleFullscreenChange() {
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const adminButtons = document.querySelectorAll('.admin-only');
    isFullscreenMode = document.fullscreenElement ||
                       document.webkitFullscreenElement ||
                       document.mozFullScreenElement;

    if (isFullscreenMode) {
        fullscreenBtn.classList.add('hidden');
        // Hide admin buttons in fullscreen/kiosk mode
        adminButtons.forEach(btn => btn.classList.add('hidden'));
    } else {
        fullscreenBtn.classList.remove('hidden');
        // Show admin buttons when not in fullscreen
        adminButtons.forEach(btn => btn.classList.remove('hidden'));
    }
}

// Capture photo from video stream
async function capturePhoto() {
    const promptInput = document.getElementById('promptInput');
    const flash = document.getElementById('flash');
    const captureBtn = document.getElementById('captureBtn');

    captureBtn.disabled = true;
    captureBtn.textContent = '⏳ Get Ready...';

    // Create countdown overlays - one darkens page, one on camera
    const pageDarkOverlay = document.createElement('div');
    pageDarkOverlay.className = 'countdown-page-dark';
    document.body.appendChild(pageDarkOverlay);

    const cameraCountdown = document.createElement('div');
    cameraCountdown.className = 'countdown-camera-overlay';
    cameraCountdown.innerHTML = `<div class="countdown-number">3</div>`;

    const cameraSection = document.querySelector('.camera-section');
    cameraSection.appendChild(cameraCountdown);

    // Show countdown overlays
    setTimeout(() => {
        pageDarkOverlay.classList.add('show');
        cameraCountdown.classList.add('show');
    }, 10);

    // Countdown sequence
    const countdownEl = cameraCountdown.querySelector('.countdown-number');
    await new Promise(resolve => setTimeout(resolve, 1000));
    countdownEl.textContent = '2';
    await new Promise(resolve => setTimeout(resolve, 1000));
    countdownEl.textContent = '1';
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Remove countdown
    pageDarkOverlay.classList.remove('show');
    cameraCountdown.classList.remove('show');
    setTimeout(() => {
        pageDarkOverlay.remove();
        cameraCountdown.remove();
    }, 300);

    // Set canvas size to match video dimensions
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw video frame to canvas BEFORE flash (freeze frame)
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Freeze the video by hiding it and showing the canvas
    video.style.opacity = '0';
    canvas.style.display = 'block';
    canvas.style.opacity = '1';

    // Show flash effect (white screen for 400ms)
    flash.classList.add('active');
    await new Promise(resolve => setTimeout(resolve, 400));
    flash.classList.remove('active');

    captureBtn.textContent = '⏳ Processing...';

    // Keep frozen frame visible for another moment
    await new Promise(resolve => setTimeout(resolve, 100));

    // Get image data as base64
    const imageData = canvas.toDataURL('image/png');

    // Save photo to server
    try {
        console.log('Sending photo to server with prompt:', promptInput.value);

        // Check if ComfyUI is available before showing loading
        const statusCheck = await fetch('/api/comfyui/status');
        const statusData = await statusCheck.json();
        
        if (statusData.available) {
            // Show loading overlay only if ComfyUI is available
            showLoading('🎨 Creating Your Caricature...', 'Analyzing your photo and generating artwork...');
            // Small delay to ensure loading overlay renders before blocking fetch
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        const response = await fetch('/api/save-photo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageData,
                prompt: promptInput.value
            })
        });

        const result = await response.json();
        console.log('Server response:', result);

        if (statusData.available) {
            hideLoading();
        }

        if (result.success) {
            showStatus('Photo saved!', 'success');

            // Show caricature if available
            if (result.caricature) {
                showResultPreview(result);
            } else if (!result.comfyui_available) {
                showStatus('Photo saved (ComfyUI not available)', 'info');
            }

            // Clear prompt and refresh suggestions for next photo
            setTimeout(() => {
                promptInput.value = '';
                displayRandomSuggestions();
            }, 1000);
        } else {
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error saving photo:', error);
        hideLoading();
        showStatus('Error saving photo', 'error');
    } finally {
        captureBtn.disabled = false;
        captureBtn.textContent = '📸 Take Photo';

        // Restore camera video visibility
        video.style.opacity = '1';
        canvas.style.display = 'none';
    }
}

// Open photo gallery modal
async function openPhotoGallery() {
    const modal = document.getElementById('galleryModal');
    const grid = document.getElementById('galleryGrid');

    // Show modal
    modal.style.display = 'flex';

    // Load photos
    grid.innerHTML = '<div class="gallery-loading">Loading photos...</div>';

    try {
        const response = await fetch('/api/photos/list');
        const data = await response.json();

        if (data.success && data.photos.length > 0) {
            grid.innerHTML = '';

            data.photos.forEach(photo => {
                const item = document.createElement('div');
                item.className = 'gallery-item';

                // Create image container for fade animation
                if (photo.caricature_exists) {
                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'gallery-img-container';

                    const originalImg = document.createElement('img');
                    originalImg.src = `/photos/${photo.filename}`;
                    originalImg.className = 'gallery-img-original';

                    const caricatureImg = document.createElement('img');
                    caricatureImg.src = `/caricatures/${photo.caricature_filename}`;
                    caricatureImg.className = 'gallery-img-caricature';

                    imgContainer.appendChild(originalImg);
                    imgContainer.appendChild(caricatureImg);
                    item.appendChild(imgContainer);

                    // Start fade animation
                    startFadeAnimation(imgContainer);
                } else {
                    const img = document.createElement('img');
                    img.src = `/photos/${photo.filename}`;
                    img.alt = photo.prompt || 'Photo';
                    item.appendChild(img);
                }

                const info = document.createElement('div');
                info.className = 'gallery-item-info';

                // Prompt row with reuse icon
                const promptRow = document.createElement('div');
                promptRow.className = 'gallery-item-prompt-row';

                const promptText = document.createElement('span');
                promptText.className = 'gallery-item-prompt';
                promptText.textContent = photo.prompt || '(no prompt)';

                const reuseIcon = document.createElement('button');
                reuseIcon.className = 'prompt-reuse-icon';
                reuseIcon.innerHTML = '🔄';
                reuseIcon.title = 'Use this prompt';
                reuseIcon.onclick = (e) => {
                    e.stopPropagation();
                    reusePrompt(photo.prompt);
                };

                promptRow.appendChild(promptText);
                promptRow.appendChild(reuseIcon);
                info.appendChild(promptRow);

                // Actions row with buttons and delete icon
                const actions = document.createElement('div');
                actions.className = 'gallery-item-actions';

                if (photo.caricature_exists) {
                    const viewBtn = document.createElement('button');
                    viewBtn.textContent = '👁️ Preview';  // Changed from "View" to "Preview"
                    viewBtn.className = 'gallery-btn';
                    viewBtn.onclick = () => {
                        closeGallery();
                        showResultPreview({
                            caricature: photo.caricature_filename,
                            svg: photo.svg_filename,
                            can_draw: photo.svg_exists
                        });
                    };
                    actions.appendChild(viewBtn);
                } else {
                    const generateBtn = document.createElement('button');
                    generateBtn.textContent = '🎨 Generate';
                    generateBtn.className = 'gallery-btn';
                    generateBtn.onclick = () => processExistingPhoto(photo.filename, photo.prompt);
                    actions.appendChild(generateBtn);
                }

                // Delete icon
                const deleteIcon = document.createElement('button');
                deleteIcon.className = 'gallery-delete-icon';
                deleteIcon.innerHTML = '🗑️';
                deleteIcon.title = 'Delete';
                deleteIcon.onclick = (e) => {
                    e.stopPropagation();
                    deletePhoto(photo.filename);
                };
                actions.appendChild(deleteIcon);

                info.appendChild(actions);
                item.appendChild(info);
                grid.appendChild(item);
            });
        } else {
            grid.innerHTML = '<div class="gallery-empty">No photos found. Take some photos first!</div>';
        }
    } catch (error) {
        console.error('Error loading photos:', error);
        grid.innerHTML = '<div class="gallery-error">Error loading photos</div>';
    }
}

// Close gallery modal
function closeGallery() {
    const modal = document.getElementById('galleryModal');
    modal.style.display = 'none';
}

// Process an existing photo
async function processExistingPhoto(filename, prompt) {
    closeGallery();

    // Show prompt in input field
    const promptInput = document.getElementById('promptInput');
    promptInput.value = prompt;

    try {
        showLoading('🎨 Creating Your Caricature...', 'Processing saved photo...');

        const response = await fetch('/api/photos/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                prompt: prompt
            })
        });

        const result = await response.json();

        hideLoading();

        if (result.success) {
            if (result.caricature) {
                showResultPreview(result);
                showStatus('Caricature generated!', 'success');
            } else if (!result.comfyui_available) {
                showStatus('ComfyUI not available', 'error');
            } else {
                showStatus('Generation failed', 'error');
            }
        } else {
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error processing photo:', error);
        hideLoading();
        showStatus('Error processing photo', 'error');
    }
}

// Show result preview overlay
function showResultPreview(result) {
    const preview = document.getElementById('resultPreview');
    const img = document.getElementById('caricatureImg');
    const drawBtn = document.getElementById('drawBtn');

    // Set caricature image
    img.src = `/caricatures/${result.caricature}`;

    // Show draw button if arm is calibrated
    if (result.can_draw && result.svg) {
        currentSVG = result.svg;
        drawBtn.style.display = 'block';
    } else {
        drawBtn.style.display = 'none';
    }

    // Show preview
    preview.style.display = 'flex';
}

// Close result preview
function closePreview() {
    const preview = document.getElementById('resultPreview');
    preview.style.display = 'none';
    currentSVG = null;

    // Ensure camera and photobooth are visible and reset
    const video = document.getElementById('video');
    const cameraSection = document.querySelector('.camera-section');
    const photoboothContainer = document.querySelector('.photobooth-container');

    if (video) video.style.display = 'block';
    if (cameraSection) cameraSection.style.display = 'block';
    if (photoboothContainer) photoboothContainer.style.display = 'grid';
}

// Draw current image with DexArm
async function drawCurrentImage() {
    if (!currentSVG) {
        showStatus('No drawing available', 'error');
        return;
    }

    const drawBtn = document.getElementById('drawBtn');
    drawBtn.disabled = true;
    drawBtn.textContent = '⏳ Drawing...';

    // Create and show robot arm loader
    const robotLoader = new RobotArmLoader();
    robotLoader.show();

    try {
        showStatus('Starting drawing...', 'info');

        const response = await fetch('/api/draw-svg', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                svg: currentSVG
            })
        });

        const result = await response.json();

        if (result.success) {
            showStatus('Drawing complete!', 'success');
            robotLoader.complete();

            // Hide loader after a delay
            setTimeout(() => {
                robotLoader.hide();
                closePreview();
            }, 2000);
        } else {
            showStatus(`Error: ${result.error}`, 'error');
            robotLoader.hide();
        }
    } catch (error) {
        console.error('Error drawing:', error);
        showStatus('Error drawing', 'error');
        robotLoader.hide();
    } finally {
        drawBtn.disabled = false;
        drawBtn.textContent = '🖊️ Draw It!';
    }
}

// Paintbrush Loader Class
class PaintbrushLoader {
    constructor() {
        this.progressBar = document.getElementById('progressBar');
        this.percentage = document.getElementById('percentage');
        this.statusText = document.getElementById('statusText');
        this.currentProgress = 0;
        this.targetProgress = 0;
        this.duration = 50000; // 50 seconds

        // Each stage has multiple random message options
        this.messageStages = [
            // Stage 1: Initialization
            [
                'Connecting to AI brain...',
                'Initializing AI engine...',
                'Waking up the AI...',
                'Booting up neural networks...',
                'Starting the magic...'
            ],
            // Stage 2: Photo analysis
            [
                'Analyzing your stunning face...',
                'Studying your photo...',
                'Reading your features...',
                'Examining every pixel...',
                'Getting to know you...'
            ],
            // Stage 3: Background removal
            [
                'Removing background...',
                'Cutting you out...',
                'Erasing the boring parts...',
                'Making background disappear...',
                'Isolating the star of the show...'
            ],
            // Stage 4: Depth mapping
            [
                'Creating depth map...',
                'Calculating 3D information...',
                'Measuring dimensions...',
                'Mapping your contours...',
                'Understanding your shape...'
            ],
            // Stage 5: Line art generation
            [
                'Generating line art...',
                'Drawing the outlines...',
                'Sketching your features...',
                'Creating clean lines...',
                'Tracing your silhouette...'
            ],
            // Stage 6: Style application
            [
                'Applying artistic style...',
                'Adding caricature magic...',
                'Making it artistic...',
                'Transforming to cartoon...',
                'Sprinkling creativity...'
            ],
            // Stage 7: Enhancement
            [
                'Enhancing details...',
                'Perfecting the lines...',
                'Polishing the artwork...',
                'Making it pop...',
                'Adding final touches...'
            ],
            // Stage 8: Upscaling
            [
                'Upscaling image...',
                'Making it bigger and better...',
                'Enhancing resolution...',
                'Increasing quality...',
                'Supersizing the art...'
            ],
            // Stage 9: Finalization
            [
                'Finalizing masterpiece...',
                'Adding the finishing touches...',
                'Completing the artwork...',
                'Wrapping it up...',
                'Making it perfect...'
            ],
            // Stage 10: Almost done
            [
                'Almost almost complete...',
                'We are almost ready...',
                'Paint is almost dry...',
                'Just a few more seconds...',
                'Getting ready to reveal...',
                'Preparing your masterpiece...',
                'Nearly there...'
            ]
        ];

        // Pick random messages for this session
        this.statusMessages = this.messageStages.map(stage =>
            stage[Math.floor(Math.random() * stage.length)]
        );

        this.animationId = null;
        this.intervalId = null;
    }

    // Custom easing function: very slow start, fast middle, VERY slow end (stay at 99% longer)
    customEasing(t) {
        // Random values set once at the start
        if (!this.phase1End) {
            this.phase1End = 0.04 + Math.random() * 0.16; // 4-20%
            this.phase2End = 0.85 + Math.random() * 0.10; // 85-95%
        }

        if (t < 0.25) {
            // First 12.5 seconds: 0% to 4-20%
            const localT = t / 0.25;
            const eased = Math.pow(localT, 2.5);
            return eased * this.phase1End;
        } else if (t < 0.60) {
            // Next 17.5 seconds: 4-20% to 85-95%
            const localT = (t - 0.25) / 0.35;
            return this.phase1End + (localT * (this.phase2End - this.phase1End));
        } else {
            // Last 20 seconds: 85-95% to 99% (stay at 99% for a long time)
            const localT = (t - 0.60) / 0.40;
            const eased = 1 - Math.pow(1 - localT, 4); // Very slow easing
            const targetProgress = this.phase2End + (eased * (0.99 - this.phase2End));
            return Math.min(targetProgress, 0.99); // Cap at 99%
        }
    }

    start() {
        this.currentProgress = 0;
        this.phase1End = null;
        this.phase2End = null;
        this.progressBar.style.width = '0%';
        this.percentage.textContent = '0%';

        // Pick new random messages for each generation
        this.statusMessages = this.messageStages.map(stage =>
            stage[Math.floor(Math.random() * stage.length)]
        );
        this.statusText.textContent = this.statusMessages[0];

        const startTime = Date.now();
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const normalizedTime = Math.min(elapsed / this.duration, 1);

            const targetProgress = this.customEasing(normalizedTime) * 100;
            this.currentProgress += (targetProgress - this.currentProgress) * 0.15;

            this.progressBar.style.width = `${this.currentProgress}%`;
            this.percentage.textContent = `${Math.round(this.currentProgress)}%`;

            if (normalizedTime < 1 || this.currentProgress < 99.9) {
                this.animationId = requestAnimationFrame(animate);
            } else {
                this.onComplete();
            }
        };

        this.animationId = requestAnimationFrame(animate);
        this.updateStatus();
    }

    updateStatus() {
        let messageIndex = 0;
        const interval = this.duration / this.statusMessages.length;

        const updateMessage = () => {
            if (messageIndex < this.statusMessages.length) {
                this.statusText.style.opacity = '0';
                setTimeout(() => {
                    this.statusText.textContent = this.statusMessages[messageIndex];
                    this.statusText.style.opacity = '1';
                    messageIndex++;
                }, 300);
            }
        };

        updateMessage();
        this.intervalId = setInterval(() => {
            if (messageIndex < this.statusMessages.length) {
                updateMessage();
            } else {
                clearInterval(this.intervalId);
            }
        }, interval);
    }

    onComplete() {
        this.progressBar.style.width = '100%';
        this.percentage.textContent = '100%';
        // Use the last status message (already randomized)
        this.statusText.textContent = this.statusMessages[this.statusMessages.length - 1];
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

// Show loading overlay
function showLoading(title, message) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';

    // Initialize and start paintbrush loader
    if (!paintbrushLoader) {
        paintbrushLoader = new PaintbrushLoader();
    }
    paintbrushLoader.start();
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'none';

    // Stop paintbrush loader
    if (paintbrushLoader) {
        paintbrushLoader.stop();
    }
}

// Toggle fullscreen mode
function toggleFullscreen() {
    const elem = document.documentElement;
    const btn = document.getElementById('fullscreenBtn');

    if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.mozFullScreenElement) {
        // Enter fullscreen
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.mozRequestFullScreen) {
            elem.mozRequestFullScreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
        btn.textContent = 'Fullscreen Mode Active';
    }
}

// Show status message
function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;

    // Clear status after 3 seconds
    setTimeout(() => {
        status.textContent = '';
        status.className = 'status';
    }, 3000);
}

// Reuse prompt function
function reusePrompt(prompt) {
    closeGallery();
    document.getElementById('promptInput').value = prompt || '';
    // Scroll to camera view
    document.getElementById('video').scrollIntoView({ behavior: 'smooth' });
    showStatus('Prompt copied!', 'success');
}

// Delete photo function
async function deletePhoto(filename) {
    if (!confirm('Delete this photo and its results?')) return;

    try {
        const response = await fetch('/api/photos/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });

        const result = await response.json();
        if (result.success) {
            showStatus('Photo deleted', 'success');
            // Refresh gallery
            openPhotoGallery();
        } else {
            showStatus('Error deleting photo', 'error');
        }
    } catch (error) {
        console.error('Error deleting photo:', error);
        showStatus('Error deleting photo', 'error');
    }
}

// Start fade animation for gallery items
function startFadeAnimation(container) {
    let isShowingOriginal = true;

    // Initial state: show original for 2 seconds
    setTimeout(() => {
        // Fade to result
        container.classList.add('fade-to-result');
        isShowingOriginal = false;

        // Then alternate every 4 seconds
        setInterval(() => {
            if (isShowingOriginal) {
                container.classList.add('fade-to-result');
                container.classList.remove('fade-to-original');
            } else {
                container.classList.remove('fade-to-result');
                container.classList.add('fade-to-original');
            }
            isShowingOriginal = !isShowingOriginal;
        }, 4000);
    }, 2000);
}

// Robot Arm Loader Class - for drawing animations
class RobotArmLoader {
    constructor() {
        this.overlay = null;
        this.statusText = null;
        this.currentMessageIndex = 0;

        // Funny robot messages for drawing
        this.messages = [
            '🤖 The robot is working...',
            '🎨 The artist is drawing...',
            '✏️ Beep boop, creating art...',
            '🖊️ This human looks interesting...',
            '🎭 Drawing your magnificent features...',
            '✨ Making you even more beautiful...',
            '🤖 My servos are dancing with joy...',
            '🎨 Picasso? Never heard of him...',
            '✏️ This is my masterpiece!',
            '🖊️ Almost there, just a few more lines...',
            '⚡ My circuits are tingling...',
            '🤖 Calculating the perfect stroke...',
            '🎨 The machine spirit is pleased...',
            '✏️ Drawing at 1000% efficiency...',
            '🖊️ One line closer to perfection...',
            '🎭 Your portrait deserves a museum...',
            '✨ Making Da Vinci jealous...',
            '🤖 Robots do it with precision...',
            '🎨 Engaging artistic subroutines...',
            '✏️ Error 404: Ugly not found...'
        ];

        // Time-based messages (shown after 20 seconds)
        this.timeMessages = [
            '{time} remaining, almost there!',
            'Just {time} more, patience young grasshopper...',
            'The artist needs {time} to finish this beauty...',
            'A little more than {time} left...',
            'Less than {time} to go!',
            '{time} until your masterpiece is complete!',
            'Estimated {time} remaining, worth the wait!',
            'Give me {time} and I\'ll give you art!',
            'Only {time} left, stay with me!',
            '{time} more for perfection...',
            'About {time} to go, hang tight!',
            'The robot needs {time} more, beep boop!',
            '{time} remaining, then we\'re done!',
            'Almost finished, just {time} left!',
            'Your portrait will be ready in {time}!',
            '{time} more and this masterpiece is yours!',
            'Patience! {time} remaining...',
            'The countdown is on: {time} left!',
            '{time} until glory!',
            'Hold on, {time} more to go!'
        ];

        this.messageInterval = null;
        this.startTime = null;
    }

    show() {
        // Create overlay if it doesn't exist
        if (!this.overlay) {
            this.overlay = document.createElement('div');
            this.overlay.id = 'robotArmOverlay';
            this.overlay.className = 'robot-arm-overlay';
            this.overlay.innerHTML = `
                <div class="robot-arm-container">
                    <h1 class="robot-arm-title">🤖 Drawing Your Masterpiece</h1>

                    <div class="robot-arm-animation">
                        <div class="robot-base"></div>
                        <div class="robot-segment robot-segment-1">
                            <div class="robot-joint"></div>
                            <div class="robot-segment robot-segment-2">
                                <div class="robot-joint"></div>
                                <div class="robot-pen">
                                    <div class="brush-tip"></div>
                                    <div class="brush-bristles"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="robot-status-text" id="robotStatusText">🤖 The robot is working...</div>
                    <div class="robot-progress-container">
                        <div class="robot-progress-bar" id="robotProgressBar"></div>
                        <div class="robot-progress-text" id="robotProgressText">0%</div>
                    </div>
                </div>
            `;
            document.body.appendChild(this.overlay);
            this.statusText = document.getElementById('robotStatusText');
        }

        // Show overlay with fade-in
        setTimeout(() => {
            this.overlay.style.display = 'flex';
            setTimeout(() => {
                this.overlay.classList.add('show');
            }, 10);
        }, 10);

        // Start cycling through messages
        this.startMessageCycle();

        // Connect to SSE for real-time progress
        this.connectProgressStream();
    }

    connectProgressStream() {
        // Close existing connection if any
        if (this.eventSource) {
            this.eventSource.close();
        }

        // Connect to SSE endpoint
        this.eventSource = new EventSource('/api/drawing-progress');

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.progress !== undefined) {
                    this.updateProgress(data.progress);
                }
                // Show completion message when present
                if (data.message && this.statusText) {
                    this.statusText.textContent = data.message;
                    this.statusText.style.opacity = '1';
                }
            } catch (error) {
                console.error('Error parsing progress data:', error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            // Don't close on error, let it reconnect automatically
        };
    }

    startMessageCycle() {
        // Record start time
        this.startTime = Date.now();

        // Show initial message
        this.currentMessageIndex = 0;
        if (this.statusText) {
            this.statusText.textContent = this.messages[0];
        }

        // Change message every 3 seconds
        this.messageInterval = setInterval(() => {
            if (!this.statusText) return;

            const elapsedSeconds = (Date.now() - this.startTime) / 1000;
            const progressBar = document.getElementById('robotProgressBar');
            const currentProgress = progressBar ? parseFloat(progressBar.style.width) || 0 : 0;

            // After 20 seconds, start showing time-based messages randomly
            const useTimeMessage = elapsedSeconds > 20 && Math.random() < 0.4; // 40% chance

            // Fade out
            this.statusText.style.opacity = '0';

            setTimeout(() => {
                if (useTimeMessage && currentProgress > 0 && currentProgress < 95) {
                    // Calculate estimated remaining time
                    const estimatedTotalSeconds = (elapsedSeconds / currentProgress) * 100;
                    const remainingSeconds = estimatedTotalSeconds - elapsedSeconds;
                    const timeStr = this.formatTime(remainingSeconds);

                    // Pick random time message
                    const randomTimeMsg = this.timeMessages[Math.floor(Math.random() * this.timeMessages.length)];
                    this.statusText.textContent = randomTimeMsg.replace('{time}', timeStr);
                } else {
                    // Show regular message
                    this.currentMessageIndex = (this.currentMessageIndex + 1) % this.messages.length;
                    this.statusText.textContent = this.messages[this.currentMessageIndex];
                }

                // Fade in
                this.statusText.style.opacity = '1';
            }, 300);
        }, 3000);
    }

    formatTime(seconds) {
        if (seconds < 60) {
            return `${Math.ceil(seconds)} seconds`;
        } else if (seconds < 120) {
            return 'about a minute';
        } else if (seconds < 180) {
            return 'less than 3 minutes';
        } else if (seconds < 240) {
            return 'about 3 minutes';
        } else if (seconds < 300) {
            return 'less than 5 minutes';
        } else {
            const minutes = Math.ceil(seconds / 60);
            return `about ${minutes} minutes`;
        }
    }

    updateProgress(percent) {
        const progressBar = document.getElementById('robotProgressBar');
        const progressText = document.getElementById('robotProgressText');

        if (progressBar && progressText) {
            progressBar.style.width = percent + '%';
            progressText.textContent = Math.floor(percent) + '%';
        }
    }

    complete() {
        // Stop message cycling and close SSE connection
        if (this.messageInterval) {
            clearInterval(this.messageInterval);
            this.messageInterval = null;
        }
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        // Set progress to 100%
        this.updateProgress(100);

        // Show completion message
        if (this.statusText) {
            this.statusText.textContent = '✅ Drawing complete! Masterpiece created!';
        }
    }

    hide() {
        // Stop message cycling and close SSE connection
        if (this.messageInterval) {
            clearInterval(this.messageInterval);
            this.messageInterval = null;
        }
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        if (this.overlay) {
            this.overlay.classList.remove('show');
            setTimeout(() => {
                this.overlay.style.display = 'none';
            }, 300);
        }
    }
}

// Auto-connect to DexArm on photobooth startup
async function tryAutoConnectDexArm() {
    try {
        console.log('Attempting auto-connect to DexArm...');

        const response = await fetch('/api/dexarm/auto-connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            console.log(`Auto-connected to DexArm on ${result.port}`);
            if (result.moved_to_rest) {
                console.log('Moved to resting position');
            }
            if (result.is_calibrated) {
                console.log('DexArm is calibrated and ready for drawing');
            }
        } else {
            if (result.needs_setup) {
                console.log('DexArm needs setup - user should visit /setup');
            } else {
                console.warn(`Auto-connect failed: ${result.error}`);
            }
        }
    } catch (error) {
        console.error('Auto-connect error:', error);
    }
}
