// Color Wheel Component with Live Preview

class ColorWheel {
    constructor(canvas, hueSlider, previewElement, saturationSlider = null, lightnessSlider = null) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.hueSlider = hueSlider;
        this.previewElement = previewElement;
        this.saturationSlider = saturationSlider;
        this.lightnessSlider = lightnessSlider;
        
        this.currentHue = 0;
        this.currentSaturation = 100;
        this.currentLightness = 50;
        
        this.init();
    }
    
    init() {
        this.drawColorWheel();
        this.setupEventListeners();
        this.updatePreview();
    }
    
    drawColorWheel() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 10;
        
        this.ctx.clearRect(0, 0, width, height);
        
        // Draw color wheel
        for (let angle = 0; angle < 360; angle++) {
            const startAngle = (angle - 2) * Math.PI / 180;
            const endAngle = (angle + 2) * Math.PI / 180;
            
            this.ctx.beginPath();
            this.ctx.moveTo(centerX, centerY);
            this.ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            this.ctx.closePath();
            
            this.ctx.fillStyle = `hsl(${angle}, 100%, 50%)`;
            this.ctx.fill();
        }
        
        // Draw center circle (white to show selected color)
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius * 0.4, 0, 2 * Math.PI);
        this.ctx.fillStyle = `hsl(${this.currentHue}, ${this.currentSaturation}%, ${this.currentLightness}%)`;
        this.ctx.fill();
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // Draw selection indicator
        const indicatorAngle = (this.currentHue - 90) * Math.PI / 180;
        const indicatorRadius = radius * 0.7;
        const indicatorX = centerX + Math.cos(indicatorAngle) * indicatorRadius;
        const indicatorY = centerY + Math.sin(indicatorAngle) * indicatorRadius;
        
        this.ctx.beginPath();
        this.ctx.arc(indicatorX, indicatorY, 8, 0, 2 * Math.PI);
        this.ctx.fillStyle = 'white';
        this.ctx.fill();
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }
    
    setupEventListeners() {
        // Canvas click to select hue
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = this.canvas.width / 2;
            const centerY = this.canvas.height / 2;
            
            const angle = Math.atan2(y - centerY, x - centerX);
            let hue = (angle * 180 / Math.PI) + 90;
            if (hue < 0) hue += 360;
            
            this.currentHue = Math.round(hue);
            this.hueSlider.value = this.currentHue;
            
            // Update display
            const valueDisplay = this.hueSlider.parentElement.querySelector('.value-display');
            if (valueDisplay) {
                valueDisplay.textContent = this.currentHue + '°';
            }
            
            this.drawColorWheel();
            this.updatePreview();
        });
        
        // Hue slider
        this.hueSlider.addEventListener('input', (e) => {
            this.currentHue = parseInt(e.target.value);
            const valueDisplay = e.target.parentElement.querySelector('.value-display');
            if (valueDisplay) {
                valueDisplay.textContent = this.currentHue + '°';
            }
            this.drawColorWheel();
            this.updatePreview();
        });
        
        // Saturation slider
        if (this.saturationSlider) {
            this.saturationSlider.addEventListener('input', (e) => {
                this.currentSaturation = parseInt(e.target.value);
                this.drawColorWheel();
                this.updatePreview();
            });
        }
        
        // Lightness slider
        if (this.lightnessSlider) {
            this.lightnessSlider.addEventListener('input', (e) => {
                this.currentLightness = parseInt(e.target.value);
                this.drawColorWheel();
                this.updatePreview();
            });
        }
    }
    
    updatePreview() {
        const color = `hsl(${this.currentHue}, ${this.currentSaturation}%, ${this.currentLightness}%)`;
        this.previewElement.style.backgroundColor = color;
    }
    
    setColor(hue, saturation = 100, lightness = 50) {
        this.currentHue = hue;
        this.currentSaturation = saturation;
        this.currentLightness = lightness;
        
        this.hueSlider.value = hue;
        if (this.saturationSlider) this.saturationSlider.value = saturation;
        if (this.lightnessSlider) this.lightnessSlider.value = lightness;
        
        const valueDisplay = this.hueSlider.parentElement.querySelector('.value-display');
        if (valueDisplay) {
            valueDisplay.textContent = hue + '°';
        }
        
        this.drawColorWheel();
        this.updatePreview();
    }
    
    getHue() {
        return this.currentHue;
    }
    
    getSaturation() {
        return this.currentSaturation;
    }
    
    getLightness() {
        return this.currentLightness;
    }
}

// Initialize color wheels when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Main lighting color wheel
    const lightingCanvas = document.getElementById('lighting-color-wheel');
    const lightingHueSlider = document.getElementById('lighting-hue');
    const lightingPreview = document.getElementById('lighting-color-preview');
    const lightingSatSlider = document.getElementById('lighting-saturation');
    const lightingLightSlider = document.getElementById('lighting-lightness');
    
    if (lightingCanvas && lightingHueSlider && lightingPreview) {
        window.lightingColorWheel = new ColorWheel(lightingCanvas, lightingHueSlider, lightingPreview, lightingSatSlider, lightingLightSlider);
    }
    
    // Face button color wheels
    const faceCanvases = document.querySelectorAll('.face-color-wheel');
    faceCanvases.forEach(canvas => {
        const button = canvas.getAttribute('data-button');
        const hueSlider = document.querySelector(`.face-hue[data-button="${button}"]`);
        const satSlider = document.querySelector(`.face-sat[data-button="${button}"]`);
        const lightSlider = document.querySelector(`.face-light[data-button="${button}"]`);
        const preview = document.getElementById(`face-${button}-preview`);
        
        if (hueSlider && preview) {
            const colorWheel = new ColorWheel(canvas, hueSlider, preview, satSlider, lightSlider);
            
            // Store reference for later access
            if (!window.faceColorWheels) window.faceColorWheels = {};
            window.faceColorWheels[button] = colorWheel;
        }
    });
});
