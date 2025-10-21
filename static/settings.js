/**
 * General Settings Page
 */

class SettingsManager {
    constructor() {
        this.initializeElements();
        this.loadSettings();
        this.attachEventListeners();
    }

    initializeElements() {
        this.comfyuiUrl = document.getElementById('comfyuiUrl');
        this.penLiftHeight = document.getElementById('penLiftHeight');
        this.svgMethod = document.getElementById('svgMethod');
        this.maxCommands = document.getElementById('maxCommands');
        this.saveBtn = document.getElementById('saveSettingsBtn');
        this.resetBtn = document.getElementById('resetDefaultsBtn');
        this.statusMessage = document.getElementById('statusMessage');
    }

    attachEventListeners() {
        this.saveBtn.addEventListener('click', () => this.saveSettings());
        this.resetBtn.addEventListener('click', () => this.resetToDefaults());
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            if (!response.ok) {
                throw new Error('Failed to load settings');
            }

            const settings = await response.json();

            // Populate form fields
            this.comfyuiUrl.value = settings.comfyui_url || 'http://127.0.0.1:8188';
            this.penLiftHeight.value = settings.pen_lift_height || 16;
            this.svgMethod.value = settings.svg_method || 'clean_v1';
            this.maxCommands.value = settings.max_commands || 5000;

        } catch (error) {
            console.error('Error loading settings:', error);
            this.showStatus('Failed to load settings', 'error');
        }
    }

    async saveSettings() {
        try {
            const settings = {
                comfyui_url: this.comfyuiUrl.value,
                pen_lift_height: parseInt(this.penLiftHeight.value),
                svg_method: this.svgMethod.value,
                max_commands: parseInt(this.maxCommands.value)
            };

            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                throw new Error('Failed to save settings');
            }

            const result = await response.json();
            this.showStatus('Settings saved successfully!', 'success');

        } catch (error) {
            console.error('Error saving settings:', error);
            this.showStatus('Failed to save settings: ' + error.message, 'error');
        }
    }

    async resetToDefaults() {
        if (!confirm('Reset all settings to defaults?')) {
            return;
        }

        // Default values
        this.comfyuiUrl.value = 'http://127.0.0.1:8188';
        this.penLiftHeight.value = 16;
        this.svgMethod.value = 'clean_v1';
        this.maxCommands.value = 5000;

        await this.saveSettings();
    }

    showStatus(message, type = 'info') {
        this.statusMessage.textContent = message;
        this.statusMessage.className = 'status-message ' + type;
        this.statusMessage.style.display = 'block';

        setTimeout(() => {
            this.statusMessage.style.display = 'none';
        }, 3000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new SettingsManager();
});
