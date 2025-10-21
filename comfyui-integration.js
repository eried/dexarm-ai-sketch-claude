/**
 * ComfyUI Integration Module
 * Handles workflow execution and loading animation
 */

class ComfyUIIntegration {
    constructor(config = {}) {
        this.comfyUIUrl = config.comfyUIUrl || 'http://127.0.0.1:8188';
        this.workflowPath = config.workflowPath || './workflow.json';
        this.outputFolder = config.outputFolder || './caricatures';
        this.loadingContainer = config.loadingContainer || document.body;
        this.workflow = null;
    }

    /**
     * Load the workflow template
     */
    async loadWorkflow() {
        try {
            const response = await fetch(this.workflowPath);
            this.workflow = await response.json();
            console.log('Workflow loaded successfully');
            return this.workflow;
        } catch (error) {
            console.error('Error loading workflow:', error);
            throw error;
        }
    }

    /**
     * Replace placeholders in the workflow
     * @param {string} inputImagePath - Path to the input image
     * @param {string} customPrompt - Custom prompt for the caricature
     */
    prepareWorkflow(inputImagePath, customPrompt) {
        if (!this.workflow) {
            throw new Error('Workflow not loaded. Call loadWorkflow() first.');
        }

        // Clone the workflow to avoid modifying the original
        const workflowCopy = JSON.parse(JSON.stringify(this.workflow));

        // Replace input image placeholder (node 5)
        if (workflowCopy['5'] && workflowCopy['5'].inputs) {
            workflowCopy['5'].inputs.image = inputImagePath;
        }

        // Replace custom prompt placeholder (node 15)
        if (workflowCopy['15'] && workflowCopy['15'].inputs) {
            workflowCopy['15'].inputs.text = customPrompt;
        }

        return workflowCopy;
    }

    /**
     * Show loading animation
     */
    showLoadingAnimation() {
        // Create iframe to show loading animation
        const iframe = document.createElement('iframe');
        iframe.id = 'paintbrush-loading';
        iframe.src = 'paintbrush-loading.html';
        iframe.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            z-index: 9999;
            background: rgba(0, 0, 0, 0.8);
        `;
        this.loadingContainer.appendChild(iframe);
        return iframe;
    }

    /**
     * Hide loading animation
     */
    hideLoadingAnimation() {
        const iframe = document.getElementById('paintbrush-loading');
        if (iframe) {
            iframe.remove();
        }
    }

    /**
     * Upload image to ComfyUI
     * @param {File|Blob} imageFile - Image file to upload
     */
    async uploadImage(imageFile) {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('overwrite', 'true');

        try {
            const response = await fetch(`${this.comfyUIUrl}/upload/image`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Image uploaded:', result.name);
            return result.name;
        } catch (error) {
            console.error('Error uploading image:', error);
            throw error;
        }
    }

    /**
     * Queue a workflow for execution
     * @param {Object} workflow - Prepared workflow object
     */
    async queueWorkflow(workflow) {
        try {
            const response = await fetch(`${this.comfyUIUrl}/prompt`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: workflow,
                    client_id: this.getClientId()
                })
            });

            const result = await response.json();
            console.log('Workflow queued:', result.prompt_id);
            return result.prompt_id;
        } catch (error) {
            console.error('Error queueing workflow:', error);
            throw error;
        }
    }

    /**
     * Monitor workflow progress via WebSocket
     * @param {string} promptId - The prompt ID to monitor
     */
    async monitorProgress(promptId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(`ws://${this.comfyUIUrl.replace('http://', '')}/ws?clientId=${this.getClientId()}`);

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'progress') {
                    const progress = (data.data.value / data.data.max) * 100;
                    console.log(`Progress: ${progress}%`);

                    // Update loading animation if needed
                    const iframe = document.getElementById('paintbrush-loading');
                    if (iframe && iframe.contentWindow) {
                        iframe.contentWindow.postMessage({
                            type: 'progress-update',
                            progress: progress
                        }, '*');
                    }
                }

                if (data.type === 'executing' && data.data.node === null) {
                    console.log('Workflow execution complete');
                    ws.close();
                    resolve();
                }

                if (data.type === 'execution_error') {
                    console.error('Execution error:', data.data);
                    ws.close();
                    reject(new Error('Workflow execution failed'));
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };
        });
    }

    /**
     * Get the latest generated image from the output folder
     */
    async getLatestOutput() {
        try {
            // This would need to be implemented based on your server setup
            // For now, we'll just return the expected path
            const timestamp = Date.now();
            return `${this.outputFolder}/sketch_final_${timestamp}.png`;
        } catch (error) {
            console.error('Error getting output:', error);
            throw error;
        }
    }

    /**
     * Main function to process an image
     * @param {File|Blob} imageFile - Input image
     * @param {string} customPrompt - Custom prompt for the caricature
     */
    async processImage(imageFile, customPrompt = ' is in a beautiful location with scenic background, bobblehead caricature style, ') {
        try {
            // Show loading animation
            const loadingIframe = this.showLoadingAnimation();

            // Load workflow if not already loaded
            if (!this.workflow) {
                await this.loadWorkflow();
            }

            // Upload image to ComfyUI
            const uploadedImageName = await this.uploadImage(imageFile);

            // Prepare workflow with the uploaded image and custom prompt
            const preparedWorkflow = this.prepareWorkflow(uploadedImageName, customPrompt);

            // Queue the workflow
            const promptId = await this.queueWorkflow(preparedWorkflow);

            // Monitor progress
            await this.monitorProgress(promptId);

            // Get the output image path
            const outputPath = await this.getLatestOutput();

            // Hide loading animation
            this.hideLoadingAnimation();

            console.log('Processing complete!', outputPath);
            return outputPath;

        } catch (error) {
            console.error('Error processing image:', error);
            this.hideLoadingAnimation();
            throw error;
        }
    }

    /**
     * Generate a unique client ID
     */
    getClientId() {
        if (!this.clientId) {
            this.clientId = `photobooth_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }
        return this.clientId;
    }
}

// Example usage:
/*
const comfyUI = new ComfyUIIntegration({
    comfyUIUrl: 'http://127.0.0.1:8188',
    workflowPath: './workflow.json',
    outputFolder: './caricatures'
});

// Process an image from a file input
document.getElementById('photoInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const customPrompt = ' is at the Eiffel Tower in Paris, bobblehead caricature style, ';

    try {
        const outputPath = await comfyUI.processImage(file, customPrompt);
        console.log('Generated image:', outputPath);
        // Display the result
        document.getElementById('result').src = outputPath;
    } catch (error) {
        console.error('Failed to process image:', error);
        alert('Failed to generate caricature. Please try again.');
    }
});
*/

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComfyUIIntegration;
}
