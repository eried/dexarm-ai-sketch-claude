// Setup Wizard State
let currentStep = 1;
let currentPosition = { x: 0, y: 0, z: 0 };
let isUnlocked = false;
let positionPollInterval = null;
let countdownInterval = null;
let lastSaveTimestamp = 0;  // Prevent accidental rapid saves

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Check if already connected
    await checkStatus();

    // Set up event listeners
    document.getElementById('connectBtn').addEventListener('click', connectDexArm);
    document.getElementById('homeBtn').addEventListener('click', homeDexArm);
    document.getElementById('saveCorner1Btn').addEventListener('click', () => saveCorner('corner1', 1));
    document.getElementById('saveCorner2Btn').addEventListener('click', () => saveCorner('corner2', 2));
    document.getElementById('saveRestingBtn').addEventListener('click', saveRestingPosition);
    document.getElementById('testDrawBtn').addEventListener('click', testDraw);
    document.getElementById('resetBtn').addEventListener('click', resetCalibration);
});

// Check DexArm status
async function checkStatus() {
    try {
        const response = await fetch('/api/dexarm/status');
        const data = await response.json();

        if (data.connected) {
            showStatus('DexArm connected', 'success');
            updateConnectionUI(true);

            if (data.calibrated) {
                // Already calibrated, skip to complete step
                goToStep(6);
                displayCalibrationSummary(data.drawing_area);
            } else {
                // Connected but not calibrated, go to homing
                goToStep(2);
            }
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Connect to DexArm
async function connectDexArm() {
    const port = document.getElementById('portInput').value.trim() || null;
    const connectBtn = document.getElementById('connectBtn');

    connectBtn.disabled = true;
    connectBtn.textContent = 'Connecting...';

    try {
        const response = await fetch('/api/dexarm/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Connected successfully!', 'success');
            updateConnectionUI(true);
            goToStep(2);
        } else {
            showStatus(`Connection failed: ${data.error}`, 'error');
            connectBtn.disabled = false;
            connectBtn.textContent = 'Connect';
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect';
    }
}

// Update connection UI
function updateConnectionUI(connected) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');

    if (connected) {
        indicator.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        indicator.classList.remove('connected');
        statusText.textContent = 'Not connected';
    }
}

// Home DexArm
async function homeDexArm() {
    const homeBtn = document.getElementById('homeBtn');
    homeBtn.disabled = true;
    homeBtn.textContent = 'Homing...';

    try {
        showStatus('Homing DexArm...', 'info');

        const response = await fetch('/api/dexarm/home', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Homing complete! Ready to calibrate.', 'success');
            homeBtn.disabled = false;
            homeBtn.textContent = 'Home Again';
            // Don't auto-advance, let user proceed manually
            goToStep(3);
            // Start corner 1 calibration with countdown after a short delay
            setTimeout(() => startCornerCalibration(1), 500);
        } else {
            showStatus(`Homing failed: ${data.error}`, 'error');
            homeBtn.disabled = false;
            homeBtn.textContent = 'Home DexArm';
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        homeBtn.disabled = false;
        homeBtn.textContent = 'Home DexArm';
    }
}

// Start corner calibration with automatic countdown and unlock
async function startCornerCalibration(cornerNum) {
    const stepId = cornerNum === 1 ? 'step-corner1' : cornerNum === 2 ? 'step-corner2' : 'step-resting';
    const statusId = `positionStatus${cornerNum}`;
    const cornerName = cornerNum === 1 ? 'Corner 1' : cornerNum === 2 ? 'Corner 2' : 'Resting Position';
    
    console.log(`Starting calibration for ${cornerName}`);
    
    try {
        // Lock motors first
        showStatus(`Preparing ${cornerName} - locking motors...`, 'info');
        const lockResponse = await fetch('/api/dexarm/lock', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!lockResponse.ok) {
            throw new Error('Failed to lock motors');
        }
        
        const lockData = await lockResponse.json();
        if (!lockData.success) {
            throw new Error('Motor lock failed');
        }
        
        isUnlocked = false;
        
        showStatus(`Setting ${cornerName} - Motors locked`, 'info');
        
        // Update status to show countdown
        const statusEl = document.getElementById(statusId);
        if (statusEl) {
            statusEl.style.display = 'flex';
            const statusSpan = statusEl.querySelector('span:last-child');
            
            let countdown = 2;  // 2 seconds countdown
            statusSpan.textContent = `Motors will unlock in ${countdown} seconds...`;
            statusSpan.style.color = '#ff9800';
            
            // Clear any existing countdown
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            
            countdownInterval = setInterval(async () => {
                countdown--;
                if (countdown > 0) {
                    statusSpan.textContent = `Motors will unlock in ${countdown} seconds...`;
                } else {
                    clearInterval(countdownInterval);
                    countdownInterval = null;
                    
                    // Try to unlock motors with retries
                    let unlockSuccess = false;
                    const maxRetries = 3;

                    for (let attempt = 1; attempt <= maxRetries; attempt++) {
                        try {
                            statusSpan.textContent = attempt === 1
                                ? 'Unlocking motors...'
                                : `Trying to unlock motors (attempt ${attempt}/${maxRetries})...`;

                            const unlockResponse = await fetch('/api/dexarm/unlock', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' }
                            });

                            if (!unlockResponse.ok) {
                                const errorData = await unlockResponse.json().catch(() => ({}));
                                throw new Error(errorData.error || 'HTTP error');
                            }

                            const unlockData = await unlockResponse.json();

                            if (unlockData.success) {
                                unlockSuccess = true;
                                isUnlocked = true;
                                statusSpan.textContent = 'Motors unlocked - move arm to position';
                                statusSpan.style.color = '#4CAF50';
                                showStatus(`${cornerName}: Motors unlocked! Move the arm by hand`, 'success');

                                // Start position polling
                                startPositionPolling();
                                break;
                            } else {
                                throw new Error(unlockData.error || 'Unlock returned false');
                            }
                        } catch (error) {
                            console.warn(`Unlock attempt ${attempt} failed:`, error);

                            if (attempt === maxRetries) {
                                // Final attempt failed
                                statusSpan.textContent = 'Failed to unlock motors after 3 attempts';
                                statusSpan.style.color = '#f44336';
                                showStatus('Could not unlock motors. Please restart the app and try again.', 'error');
                            } else {
                                // Wait before retry
                                await new Promise(resolve => setTimeout(resolve, 500));
                            }
                        }
                    }
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Error in startCornerCalibration:', error);
        showStatus(`Calibration setup failed: ${error.message}`, 'error');
    }
}

// Toggle motor lock/unlock
async function toggleUnlock(btnNum) {
    // This function is now deprecated - keeping for compatibility
    // The new flow uses automatic unlock with countdown
}

// Start polling position
function startPositionPolling() {
    // Stop any existing polling
    stopPositionPolling();
    
    // Update immediately
    updatePosition();

    // Then poll every 300ms for more responsive updates
    positionPollInterval = setInterval(updatePosition, 300);
}

// Stop polling position
function stopPositionPolling() {
    if (positionPollInterval) {
        clearInterval(positionPollInterval);
        positionPollInterval = null;
    }
    
    // Clear countdown too
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
}

// Update position display
async function updatePosition() {
    try {
        const response = await fetch('/api/dexarm/position');
        const data = await response.json();

        console.log('Position response:', data); // DEBUG

        if (data.success && data.position) {
            const oldPosition = { ...currentPosition };
            currentPosition = data.position;

            console.log('Updating to position:', currentPosition); // DEBUG

            // Update all position displays and add flash effect if value changed
            const updateElement = (id, value) => {
                const element = document.getElementById(id);
                if (element) {
                    const oldValue = element.textContent;
                    const newValue = value.toFixed(2);
                    element.textContent = newValue;

                    console.log(`Updated ${id}: ${oldValue} -> ${newValue}`); // DEBUG

                    // Flash effect if value changed
                    if (oldValue !== newValue && oldValue !== '--') {
                        element.classList.add('value-flash');
                        setTimeout(() => element.classList.remove('value-flash'), 300);
                    }
                }
            };

            // Update displays on all steps
            updateElement('posX', currentPosition.x);
            updateElement('posY', currentPosition.y);
            updateElement('posZ', currentPosition.z);

            updateElement('posX2', currentPosition.x);
            updateElement('posY2', currentPosition.y);
            updateElement('posZ2', currentPosition.z);

            updateElement('posX3', currentPosition.x);
            updateElement('posY3', currentPosition.y);
            updateElement('posZ3', currentPosition.z);

            // Update status indicators when position is successfully read
            if (positionPollInterval) {
                const statuses = ['positionStatus1', 'positionStatus2', 'positionStatus3'];
                statuses.forEach(id => {
                    const statusEl = document.getElementById(id);
                    if (statusEl) {
                        statusEl.style.display = 'flex';
                        const statusSpan = statusEl.querySelector('span:last-child');
                        if (statusSpan && isUnlocked) {
                            statusSpan.textContent = 'Position updated - move arm to adjust';
                            statusSpan.style.color = '#4CAF50';
                        }
                    }
                });
            }
        } else {
            // Position read failed - show error in status
            console.warn('Position read failed:', data.error);
            if (positionPollInterval) {
                const statuses = ['positionStatus1', 'positionStatus2', 'positionStatus3'];
                statuses.forEach(id => {
                    const statusEl = document.getElementById(id);
                    if (statusEl) {
                        const statusSpan = statusEl.querySelector('span:last-child');
                        if (statusSpan) {
                            statusSpan.textContent = 'Waiting for position...';
                            statusSpan.style.color = '#ff9800';
                        }
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error updating position:', error);
        // Show network error in status
        if (positionPollInterval) {
            const statuses = ['positionStatus1', 'positionStatus2', 'positionStatus3'];
            statuses.forEach(id => {
                const statusEl = document.getElementById(id);
                if (statusEl) {
                    const statusSpan = statusEl.querySelector('span:last-child');
                    if (statusSpan) {
                        statusSpan.textContent = 'Connection error';
                        statusSpan.style.color = '#f44336';
                    }
                }
            });
        }
    }
}

// Save corner
async function saveCorner(corner, cornerNum) {
    const buttonId = corner === 'corner1' ? 'saveCorner1Btn' : 'saveCorner2Btn';
    const button = document.getElementById(buttonId);

    console.log(`saveCorner called for ${corner}, button disabled: ${button.disabled}`);

    // Prevent accidental rapid saves (debounce)
    const now = Date.now();
    if (now - lastSaveTimestamp < 2000) {  // Minimum 2 seconds between saves
        console.warn('Save attempted too quickly after previous save, ignoring');
        return;
    }

    // Prevent double-clicks - strict check
    if (button.disabled) {
        console.warn('Button already disabled, ignoring duplicate click');
        return;
    }

    // Immediately disable to prevent any race conditions
    button.disabled = true;
    button.textContent = 'Saving...';
    lastSaveTimestamp = now;

    try {
        // Stop position polling first
        stopPositionPolling();
        
        // Lock motors if unlocked
        if (isUnlocked) {
            showStatus('Locking motors...', 'info');
            const lockResponse = await fetch('/api/dexarm/lock', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!lockResponse.ok) {
                throw new Error('Failed to lock motors');
            }
            
            const lockData = await lockResponse.json();
            if (!lockData.success) {
                throw new Error('Motor lock failed');
            }
            
            isUnlocked = false;
            // Wait a bit for motors to stabilize
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        showStatus(`Saving ${corner === 'corner1' ? 'first' : 'second'} corner...`, 'info');

        // Save the corner position with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        const response = await fetch('/api/dexarm/save-corner', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ corner }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showStatus(`${corner === 'corner1' ? 'First' : 'Second'} corner saved!`, 'success');

            // Keep button disabled with success message
            button.textContent = `✓ ${corner === 'corner1' ? 'Corner 1' : 'Corner 2'} Saved`;

            // IMPORTANT: Don't re-enable button, it stays disabled to prevent double-clicks
            // Wait before proceeding to next step
            await new Promise(resolve => setTimeout(resolve, 1000));

            if (data.is_calibrated) {
                // Both corners saved, go to resting position step
                console.log('Both corners saved, moving to resting position step');
                goToStep(5);
                setTimeout(() => startCornerCalibration(3), 500);
            } else {
                // First corner saved, go to second corner
                console.log('Corner 1 saved, moving to corner 2 step');
                goToStep(4);
                setTimeout(() => startCornerCalibration(2), 500);
            }
        } else {
            throw new Error(data.error || 'Failed to save corner');
        }
    } catch (error) {
        console.error('Error saving corner:', error);
        
        if (error.name === 'AbortError') {
            showStatus('Save timeout - please try again', 'error');
        } else {
            showStatus(`Failed to save corner: ${error.message}`, 'error');
        }
        
        button.disabled = false;
        button.textContent = corner === 'corner1' ? '✓ Save Corner 1' : '✓ Save Corner 2';
    }
}

// Save resting position
async function saveRestingPosition() {
    const button = document.getElementById('saveRestingBtn');

    // Prevent double-clicks
    if (button.disabled) {
        console.log('Button already disabled, ignoring click');
        return;
    }

    button.disabled = true;
    button.textContent = 'Saving...';

    try {
        // Stop position polling first
        stopPositionPolling();
        
        // Lock motors if unlocked
        if (isUnlocked) {
            showStatus('Locking motors...', 'info');
            const lockResponse = await fetch('/api/dexarm/lock', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!lockResponse.ok) {
                throw new Error('Failed to lock motors');
            }
            
            const lockData = await lockResponse.json();
            if (!lockData.success) {
                throw new Error('Motor lock failed');
            }
            
            isUnlocked = false;
            // Wait a bit for motors to stabilize
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        showStatus('Saving resting position...', 'info');

        // Save resting position with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        const response = await fetch('/api/dexarm/save-resting', {
            method: 'POST',
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showStatus('Resting position saved!', 'success');

            // Keep button disabled with success message
            button.textContent = '✓ Resting Position Saved';

            // Wait before proceeding to complete step (keep button disabled)
            await new Promise(resolve => setTimeout(resolve, 1500));

            // Move to rest position automatically
            showStatus('Moving to rest position...', 'info');
            try {
                const restResponse = await fetch('/api/dexarm/go-resting', {
                    method: 'POST'
                });
                const restData = await restResponse.json();
                if (restData.success) {
                    showStatus('Arm moved to rest position', 'success');
                }
            } catch (error) {
                console.warn('Could not move to rest position:', error);
            }

            // Wait a bit for movement to complete
            await new Promise(resolve => setTimeout(resolve, 500));

            // Go to complete step and show calibration summary
            goToStep(6);
            const statusResponse = await fetch('/api/dexarm/status');
            const statusData = await statusResponse.json();
            displayCalibrationSummary(statusData.drawing_area);
        } else {
            throw new Error(data.error || 'Failed to save resting position');
        }
    } catch (error) {
        console.error('Error saving resting position:', error);
        
        if (error.name === 'AbortError') {
            showStatus('Save timeout - please try again', 'error');
        } else {
            showStatus(`Failed to save resting position: ${error.message}`, 'error');
        }
        
        button.disabled = false;
        button.textContent = '✓ Save Resting Position';
    }
}

// Test draw frame and X
async function testDraw() {
    const button = document.getElementById('testDrawBtn');
    const testStatus = document.getElementById('testStatus');

    button.disabled = true;
    button.textContent = 'Drawing...';
    testStatus.className = 'test-status show running';
    testStatus.textContent = 'Starting test draw...';

    try {
        const response = await fetch('/api/dexarm/test-draw', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            // Show all progress messages
            const messages = data.messages.join('\n');
            testStatus.className = 'test-status show success';
            testStatus.textContent = '✅ ' + messages;
            showStatus('Test draw complete! Arm returned to rest position.', 'success');
        } else {
            testStatus.className = 'test-status show error';
            testStatus.textContent = '❌ Test draw failed: ' + data.error;
            showStatus('Test draw failed', 'error');
        }

        button.disabled = false;
        button.textContent = '▶️ Test Draw Frame + X';

    } catch (error) {
        testStatus.className = 'test-status show error';
        testStatus.textContent = '❌ Error: ' + error.message;
        showStatus(`Error: ${error.message}`, 'error');
        button.disabled = false;
        button.textContent = '▶️ Test Draw Frame + X';
    }
}

// Display calibration summary
function displayCalibrationSummary(area) {
    if (!area) return;

    const summary = document.getElementById('areaSummary');
    summary.innerHTML = `
        <p><strong>Width:</strong> ${area.width.toFixed(1)} mm</p>
        <p><strong>Height:</strong> ${area.height.toFixed(1)} mm</p>
        <p><strong>X Range:</strong> ${area.x_min.toFixed(1)} to ${area.x_max.toFixed(1)} mm</p>
        <p><strong>Y Range:</strong> ${area.y_min.toFixed(1)} to ${area.y_max.toFixed(1)} mm</p>
        <p><strong>Drawing Z-Height:</strong> ${area.z_draw.toFixed(1)} mm</p>
    `;
}


// Reset calibration
async function resetCalibration() {
    if (!confirm('Are you sure you want to reset the calibration? You will need to set the corners again.')) {
        return;
    }

    // Stop position polling if active
    stopPositionPolling();

    try {
        showStatus('Resetting calibration...', 'info');

        const response = await fetch('/api/dexarm/reset-calibration', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Calibration reset - starting over...', 'success');
            goToStep(2);

            // Automatically start homing after 1 second
            setTimeout(async () => {
                await homeDexArm();
            }, 1000);
        } else {
            showStatus(`Reset failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

// Navigate to step
function goToStep(step) {
    // Stop position polling when changing steps
    stopPositionPolling();
    if (isUnlocked) {
        isUnlocked = false;
    }

    // Hide all steps
    document.querySelectorAll('.setup-step').forEach(el => {
        el.style.display = 'none';
    });

    // Show target step
    const targetStep = document.querySelector(`[data-step="${step}"]`);
    if (targetStep) {
        targetStep.style.display = 'block';
        currentStep = step;
    }
}

// Show status message
function showStatus(message, type) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = 'status-message show ' + type;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusEl.classList.remove('show');
    }, 5000);
}
