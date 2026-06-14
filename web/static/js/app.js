// GameGent Web Interface - Main Application JavaScript

let currentConfig = {};
let lastConfigHash = '';

// Tab switching
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Initialize range sliders with value displays
    initializeRangeSliders();
    
    // Load config on startup
    loadConfig();
    
    // Start periodic config check
    setInterval(checkConfigChanges, 2000); // Check every 2 seconds
});

function initializeRangeSliders() {
    const sliders = document.querySelectorAll('input[type="range"]');
    sliders.forEach(slider => {
        const valueDisplay = slider.parentElement.querySelector('.value-display');
        if (valueDisplay) {
            slider.addEventListener('input', function() {
                valueDisplay.textContent = this.value + '%';
            });
        }
    });
}

// API communication
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) {
            console.error('API Error:', result.error);
            alert('Error: ' + (result.error || 'Unknown error'));
            return null;
        }
        
        return result;
    } catch (error) {
        console.error('Fetch Error:', error);
        alert('Network error: ' + error.message);
        return null;
    }
}

// Load config from server
async function loadConfig() {
    const config = await apiCall('/config', 'GET');
    if (config) {
        currentConfig = config;
        lastConfigHash = generateConfigHash(config);
        populateUIFromConfig(config);
    }
}

// Generate simple hash of config object
function generateConfigHash(config) {
    return JSON.stringify(config);
}

// Check for config changes periodically
async function checkConfigChanges() {
    const config = await apiCall('/config', 'GET');
    if (config) {
        const newHash = generateConfigHash(config);
        if (newHash !== lastConfigHash) {
            currentConfig = config;
            lastConfigHash = newHash;
            populateUIFromConfig(config);
            console.log('Config updated from server');
        }
    }
}

// Save config to server
async function saveConfigToServer(config) {
    const result = await apiCall('/config', 'POST', config);
    if (result) {
        currentConfig = config;
        lastConfigHash = generateConfigHash(config);
        alert('Configuration saved successfully!');
    }
}

// Populate UI from config
function populateUIFromConfig(config) {
    // Dashboard
    if (config.lighting_mode) document.getElementById('dash-lighting-mode').value = config.lighting_mode;
    if (config.brightness !== undefined) {
        document.getElementById('dash-brightness').value = config.brightness;
        document.getElementById('dash-brightness').parentElement.querySelector('.value-display').textContent = config.brightness + '%';
    }
    if (config.layout) document.getElementById('dash-layout').value = config.layout;
    if (config.stick_left?.mode) document.getElementById('dash-left-stick-mode').value = config.stick_left.mode;
    if (config.stick_right?.mode) document.getElementById('dash-right-stick-mode').value = config.stick_right.mode;
    
    // Lighting
    if (config.lighting_mode) document.getElementById('lighting-mode').value = config.lighting_mode;
    if (config.brightness !== undefined) {
        document.getElementById('lighting-brightness').value = config.brightness;
        document.getElementById('lighting-brightness').parentElement.querySelector('.value-display').textContent = config.brightness + '%';
    }
    if (config.lighting_speed !== undefined) {
        document.getElementById('lighting-speed').value = config.lighting_speed;
        document.getElementById('lighting-speed').parentElement.querySelector('.value-display').textContent = config.lighting_speed + '%';
    }
    if (config.color_hue !== undefined) {
        document.getElementById('lighting-hue').value = config.color_hue;
        document.getElementById('lighting-hue').parentElement.querySelector('.value-display').textContent = config.color_hue + '°';
    }
    if (config.color_saturation !== undefined) {
        document.getElementById('lighting-saturation').value = config.color_saturation;
        document.getElementById('lighting-saturation').parentElement.querySelector('.value-display').textContent = config.color_saturation + '%';
    }
    if (config.color_lightness !== undefined) {
        document.getElementById('lighting-lightness').value = config.color_lightness;
        document.getElementById('lighting-lightness').parentElement.querySelector('.value-display').textContent = config.color_lightness + '%';
    }
    if (config.lighting_zone !== undefined) {
        document.getElementById('lighting-led-target').value = config.lighting_zone === 1 ? 'panel' : 'home';
    }
    
    // Update lighting color wheel if it exists
    if (window.lightingColorWheel && config.color_hue !== undefined) {
        window.lightingColorWheel.setColor(
            config.color_hue,
            config.color_saturation || 100,
            config.color_lightness || 50
        );
    }
    
    // Face LEDs
    if (config.face_leds) {
        ['a', 'b', 'x', 'y'].forEach((btn, idx) => {
            const color = config.face_leds[idx] || [0, 100, 50];
            const hue = Math.round((color[0] / 255) * 360);
            document.querySelector(`.face-hue[data-button="${btn}"]`).value = hue;
            document.querySelector(`.face-sat[data-button="${btn}"]`).value = color[1];
            document.querySelector(`.face-light[data-button="${btn}"]`).value = color[2];

            // Update color wheel visual representation
            if (window.faceColorWheels && window.faceColorWheels[btn]) {
                window.faceColorWheels[btn].setColor(hue, color[1], color[2]);
            }
        });
    }
    
    // Home button LED (stored separately in config)
    if (config.home_led) {
        const hue = Math.round((config.home_led[0] / 255) * 360);
        document.querySelector(`.face-hue[data-button="home"]`).value = hue;
        document.querySelector(`.face-sat[data-button="home"]`).value = config.home_led[1];
        document.querySelector(`.face-light[data-button="home"]`).value = config.home_led[2];
        
        if (window.faceColorWheels && window.faceColorWheels['home']) {
            window.faceColorWheels['home'].setColor(hue, config.home_led[1], config.home_led[2]);
        }
    }
    
    // Triggers
    populateTriggerUI('left', config.trigger_left);
    populateTriggerUI('right', config.trigger_right);
    
    // Sticks
    populateStickUI('left', config.stick_left);
    populateStickUI('right', config.stick_right);
    
    // Gyro
    populateGyroUI(config.gyro);
}

function populateTriggerUI(side, triggerConfig) {
    if (!triggerConfig) return;
    
    const prefix = side === 'left' ? 'left' : 'right';
    
    if (triggerConfig.hair_mode) document.getElementById(`${prefix}-hair-mode`).value = triggerConfig.hair_mode;
    if (triggerConfig.hair_trigger_begin !== undefined) {
        document.getElementById(`${prefix}-hair-begin`).value = triggerConfig.hair_trigger_begin;
        document.getElementById(`${prefix}-hair-begin`).parentElement.querySelector('.value-display').textContent = triggerConfig.hair_trigger_begin + '%';
    }
    if (triggerConfig.hair_trigger_end !== undefined) {
        document.getElementById(`${prefix}-hair-end`).value = triggerConfig.hair_trigger_end;
        document.getElementById(`${prefix}-hair-end`).parentElement.querySelector('.value-display').textContent = triggerConfig.hair_trigger_end + '%';
    }
    if (triggerConfig.deadzone_begin !== undefined) {
        document.getElementById(`${prefix}-dz-begin`).value = triggerConfig.deadzone_begin;
        document.getElementById(`${prefix}-dz-begin`).parentElement.querySelector('.value-display').textContent = triggerConfig.deadzone_begin + '%';
    }
    if (triggerConfig.deadzone_end !== undefined) {
        document.getElementById(`${prefix}-dz-end`).value = triggerConfig.deadzone_end;
        document.getElementById(`${prefix}-dz-end`).parentElement.querySelector('.value-display').textContent = triggerConfig.deadzone_end + '%';
    }
    if (triggerConfig.antideadzone_begin !== undefined) {
        document.getElementById(`${prefix}-anti-begin`).value = triggerConfig.antideadzone_begin;
        document.getElementById(`${prefix}-anti-begin`).parentElement.querySelector('.value-display').textContent = triggerConfig.antideadzone_begin + '%';
    }
    if (triggerConfig.antideadzone_end !== undefined) {
        document.getElementById(`${prefix}-anti-end`).value = triggerConfig.antideadzone_end;
        document.getElementById(`${prefix}-anti-end`).parentElement.querySelector('.value-display').textContent = triggerConfig.antideadzone_end + '%';
    }
    if (triggerConfig.curve_preset) document.getElementById(`${prefix}-curve`).value = triggerConfig.curve_preset;
    if (triggerConfig.curve_intensity !== undefined) {
        document.getElementById(`${prefix}-curve-intensity`).value = triggerConfig.curve_intensity;
        document.getElementById(`${prefix}-curve-intensity`).parentElement.querySelector('.value-display').textContent = triggerConfig.curve_intensity + '%';
    }
}

function populateStickUI(side, stickConfig) {
    if (!stickConfig) return;
    
    const prefix = side === 'left' ? 'left' : 'right';
    
    if (stickConfig.mode) document.getElementById(`${prefix}-stick-mode`).value = stickConfig.mode;
    if (stickConfig.x_sensitivity !== undefined) {
        document.getElementById(`${prefix}-x-sens`).value = stickConfig.x_sensitivity;
        document.getElementById(`${prefix}-x-sens`).parentElement.querySelector('.value-display').textContent = stickConfig.x_sensitivity + '%';
    }
    if (stickConfig.y_sensitivity !== undefined) {
        document.getElementById(`${prefix}-y-sens`).value = stickConfig.y_sensitivity;
        document.getElementById(`${prefix}-y-sens`).parentElement.querySelector('.value-display').textContent = stickConfig.y_sensitivity + '%';
    }
    if (stickConfig.overlap_percent !== undefined) {
        document.getElementById(`${prefix}-overlap`).value = stickConfig.overlap_percent;
        document.getElementById(`${prefix}-overlap`).parentElement.querySelector('.value-display').textContent = stickConfig.overlap_percent + '%';
    }
    if (stickConfig.mouse_x_dpi !== undefined) {
        document.getElementById(`${prefix}-mouse-dpi`).value = stickConfig.mouse_x_dpi;
        document.getElementById(`${prefix}-mouse-dpi`).parentElement.querySelector('.value-display').textContent = stickConfig.mouse_x_dpi + '%';
    }
    if (stickConfig.mouse_y_dpi !== undefined) {
        document.getElementById(`${prefix}-mouse-ydpi`).value = stickConfig.mouse_y_dpi;
        document.getElementById(`${prefix}-mouse-ydpi`).parentElement.querySelector('.value-display').textContent = stickConfig.mouse_y_dpi + '%';
    }
    if (stickConfig.is_circle !== undefined) document.getElementById(`${prefix}-shape`).value = stickConfig.is_circle ? 'circle' : 'square';
    if (stickConfig.deadzone_min !== undefined) {
        document.getElementById(`${prefix}-deadzone-min`).value = stickConfig.deadzone_min;
        document.getElementById(`${prefix}-deadzone-min`).parentElement.querySelector('.value-display').textContent = stickConfig.deadzone_min + '%';
    }
    if (stickConfig.antideadzone_min !== undefined) {
        document.getElementById(`${prefix}-antideadzone-min`).value = stickConfig.antideadzone_min;
        document.getElementById(`${prefix}-antideadzone-min`).parentElement.querySelector('.value-display').textContent = stickConfig.antideadzone_min + '%';
    }
    if (stickConfig.deadzone_max !== undefined) {
        document.getElementById(`${prefix}-deadzone-max`).value = stickConfig.deadzone_max;
        document.getElementById(`${prefix}-deadzone-max`).parentElement.querySelector('.value-display').textContent = stickConfig.deadzone_max + '%';
    }
    if (stickConfig.antideadzone_max !== undefined) {
        document.getElementById(`${prefix}-antideadzone-max`).value = stickConfig.antideadzone_max;
        document.getElementById(`${prefix}-antideadzone-max`).parentElement.querySelector('.value-display').textContent = stickConfig.antideadzone_max + '%';
    }
    if (stickConfig.curve_preset) document.getElementById(`${prefix}-stick-curve`).value = stickConfig.curve_preset;
    if (stickConfig.curve_intensity !== undefined) {
        document.getElementById(`${prefix}-stick-curve-intensity`).value = stickConfig.curve_intensity;
        document.getElementById(`${prefix}-stick-curve-intensity`).parentElement.querySelector('.value-display').textContent = stickConfig.curve_intensity + '%';
    }
}

function populateGyroUI(gyroConfig) {
    if (!gyroConfig) return;

    if (gyroConfig.output_mode) document.getElementById('gyro-output-mode').value = gyroConfig.output_mode;
    if (gyroConfig.motion_mode) document.getElementById('gyro-motion-mode').value = gyroConfig.motion_mode;
    if (gyroConfig.activate_method) document.getElementById('gyro-method').value = gyroConfig.activate_method;
    if (gyroConfig.axis_mode) document.getElementById('gyro-axis').value = gyroConfig.axis_mode;
    if (gyroConfig.activate_button) document.getElementById('gyro-button').value = gyroConfig.activate_button;
    if (gyroConfig.x_sensitivity !== undefined) {
        document.getElementById('gyro-x-sens').value = gyroConfig.x_sensitivity;
        document.getElementById('gyro-x-sens').parentElement.querySelector('.value-display').textContent = gyroConfig.x_sensitivity + '%';
    }
    if (gyroConfig.y_sensitivity !== undefined) {
        document.getElementById('gyro-y-sens').value = gyroConfig.y_sensitivity;
        document.getElementById('gyro-y-sens').parentElement.querySelector('.value-display').textContent = gyroConfig.y_sensitivity + '%';
    }
    if (gyroConfig.overlap_percent !== undefined) {
        document.getElementById('gyro-overlap').value = gyroConfig.overlap_percent;
        document.getElementById('gyro-overlap').parentElement.querySelector('.value-display').textContent = gyroConfig.overlap_percent + '%';
    }
    if (gyroConfig.deadzone_min !== undefined) {
        document.getElementById('gyro-deadzone-min').value = gyroConfig.deadzone_min;
        document.getElementById('gyro-deadzone-min').parentElement.querySelector('.value-display').textContent = gyroConfig.deadzone_min + '%';
    }
    if (gyroConfig.deadzone_max !== undefined) {
        document.getElementById('gyro-deadzone-max').value = gyroConfig.deadzone_max;
        document.getElementById('gyro-deadzone-max').parentElement.querySelector('.value-display').textContent = gyroConfig.deadzone_max + '%';
    }
    if (gyroConfig.antideadzone_min !== undefined) {
        document.getElementById('gyro-antideadzone-min').value = gyroConfig.antideadzone_min;
        document.getElementById('gyro-antideadzone-min').parentElement.querySelector('.value-display').textContent = gyroConfig.antideadzone_min + '%';
    }
    if (gyroConfig.antideadzone_max !== undefined) {
        document.getElementById('gyro-antideadzone-max').value = gyroConfig.antideadzone_max;
        document.getElementById('gyro-antideadzone-max').parentElement.querySelector('.value-display').textContent = gyroConfig.antideadzone_max + '%';
    }
    if (gyroConfig.invert_x !== undefined) document.getElementById('gyro-invert-x').checked = gyroConfig.invert_x;
    if (gyroConfig.invert_y !== undefined) document.getElementById('gyro-invert-y').checked = gyroConfig.invert_y;
    if (gyroConfig.curve_preset) document.getElementById('gyro-curve').value = gyroConfig.curve_preset;
    if (gyroConfig.curve_intensity !== undefined) {
        document.getElementById('gyro-curve-intensity').value = gyroConfig.curve_intensity;
        document.getElementById('gyro-curve-intensity').parentElement.querySelector('.value-display').textContent = gyroConfig.curve_intensity + '%';
    }
    if (gyroConfig.kb_up) document.getElementById('gyro-kb-up').value = gyroConfig.kb_up;
    if (gyroConfig.kb_down) document.getElementById('gyro-kb-down').value = gyroConfig.kb_down;
    if (gyroConfig.kb_left) document.getElementById('gyro-kb-left').value = gyroConfig.kb_left;
    if (gyroConfig.kb_right) document.getElementById('gyro-kb-right').value = gyroConfig.kb_right;
}

// Save functions
async function saveDashboard() {
    const data = {
        lighting_mode: document.getElementById('dash-lighting-mode').value,
        brightness: parseInt(document.getElementById('dash-brightness').value),
        layout: document.getElementById('dash-layout').value,
        stick_left: { mode: document.getElementById('dash-left-stick-mode').value },
        stick_right: { mode: document.getElementById('dash-right-stick-mode').value }
    };
    
    // Apply settings via API
    await apiCall('/lighting', 'POST', {
        mode: data.lighting_mode,
        brightness: data.brightness,
        speed: 100
    });
    
    await apiCall('/layout', 'POST', { layout: data.layout });
    
    await apiCall('/stick', 'POST', {
        stick: 'left',
        mode: data.stick_left.mode
    });
    
    await apiCall('/stick', 'POST', {
        stick: 'right',
        mode: data.stick_right.mode
    });
    
    // Update config
    currentConfig.lighting_mode = data.lighting_mode;
    currentConfig.brightness = data.brightness;
    currentConfig.layout = data.layout;
    currentConfig.stick_left.mode = data.stick_left.mode;
    currentConfig.stick_right.mode = data.stick_right.mode;
    
    await saveConfigToServer(currentConfig);
}

async function saveLighting() {
    const data = {
        mode: document.getElementById('lighting-mode').value,
        brightness: parseInt(document.getElementById('lighting-brightness').value),
        speed: parseInt(document.getElementById('lighting-speed').value),
        target: document.getElementById('lighting-led-target').value,
        hue: parseInt(document.getElementById('lighting-hue').value),
        saturation: parseInt(document.getElementById('lighting-saturation').value),
        lightness: parseInt(document.getElementById('lighting-lightness').value)
    };
    
    await apiCall('/lighting', 'POST', {
        mode: data.mode,
        brightness: data.brightness,
        speed: data.speed
    });
    
    await apiCall('/led', 'POST', {
        target: data.target,
        hue: data.hue,
        saturation: data.saturation,
        lightness: data.lightness
    });
    
    currentConfig.lighting_mode = data.mode;
    currentConfig.brightness = data.brightness;
    currentConfig.lighting_speed = data.speed;
    currentConfig.color_hue = data.hue;
    currentConfig.color_saturation = data.saturation;
    currentConfig.color_lightness = data.lightness;
    currentConfig.lighting_zone = data.target === 'panel' ? 1 : 0;
    
    await saveConfigToServer(currentConfig);
}

async function saveFaceLEDs() {
    const buttons = ['a', 'b', 'x', 'y'];
    const colors = {};
    
    buttons.forEach(btn => {
        const hue = parseInt(document.querySelector(`.face-hue[data-button="${btn}"]`).value);
        const sat = parseInt(document.querySelector(`.face-sat[data-button="${btn}"]`).value);
        const light = parseInt(document.querySelector(`.face-light[data-button="${btn}"]`).value);
        colors[btn] = { hue, sat, light };
    });
    
    await apiCall('/face', 'POST', {
        button: 'all',
        a_hue: colors.a.hue,
        a_sat: colors.a.sat,
        a_light: colors.a.light,
        b_hue: colors.b.hue,
        b_sat: colors.b.sat,
        b_light: colors.b.light,
        x_hue: colors.x.hue,
        x_sat: colors.x.sat,
        x_light: colors.x.light,
        y_hue: colors.y.hue,
        y_sat: colors.y.sat,
        y_light: colors.y.light
    });
    
    // Convert to compressed format for config
    const face_leds = buttons.map(btn => {
        const hue = Math.round((colors[btn].hue / 360) * 255);
        return [hue, colors[btn].sat, colors[btn].light];
    });
    
    currentConfig.face_leds = face_leds;
    
    // Handle home button separately (uses /api/led endpoint)
    const homeHue = parseInt(document.querySelector(`.face-hue[data-button="home"]`).value);
    const homeSat = parseInt(document.querySelector(`.face-sat[data-button="home"]`).value);
    const homeLight = parseInt(document.querySelector(`.face-light[data-button="home"]`).value);
    
    await apiCall('/led', 'POST', {
        target: 'home',
        hue: homeHue,
        saturation: homeSat,
        lightness: homeLight
    });
    
    // Store home LED in config
    const homeHueCompressed = Math.round((homeHue / 360) * 255);
    currentConfig.home_led = [homeHueCompressed, homeSat, homeLight];
    
    await saveConfigToServer(currentConfig);
}

async function saveTriggers() {
    const data = {
        hair: document.getElementById('left-hair-mode').value,
        hair_begin: parseInt(document.getElementById('left-hair-begin').value),
        hair_end: parseInt(document.getElementById('left-hair-end').value),
        dz_begin: parseInt(document.getElementById('left-dz-begin').value),
        dz_end: parseInt(document.getElementById('left-dz-end').value),
        anti_begin: parseInt(document.getElementById('left-anti-begin').value),
        anti_end: parseInt(document.getElementById('left-anti-end').value),
        curve: document.getElementById('left-curve').value,
        curve_intensity: parseInt(document.getElementById('left-curve-intensity').value),
        left_hair: document.getElementById('right-hair-mode').value,
        left_hair_begin: parseInt(document.getElementById('right-hair-begin').value),
        left_hair_end: parseInt(document.getElementById('right-hair-end').value),
        left_dz_begin: parseInt(document.getElementById('right-dz-begin').value),
        left_dz_end: parseInt(document.getElementById('right-dz-end').value),
        left_anti_begin: parseInt(document.getElementById('right-anti-begin').value),
        left_anti_end: parseInt(document.getElementById('right-anti-end').value),
        left_curve: document.getElementById('right-curve').value,
        left_intensity: parseInt(document.getElementById('right-curve-intensity').value)
    };
    
    await apiCall('/trigger', 'POST', data);
    
    currentConfig.trigger_left = {
        hair_mode: document.getElementById('left-hair-mode').value,
        hair_trigger_begin: parseInt(document.getElementById('left-hair-begin').value),
        hair_trigger_end: parseInt(document.getElementById('left-hair-end').value),
        deadzone_begin: parseInt(document.getElementById('left-dz-begin').value),
        deadzone_end: parseInt(document.getElementById('left-dz-end').value),
        antideadzone_begin: parseInt(document.getElementById('left-anti-begin').value),
        antideadzone_end: parseInt(document.getElementById('left-anti-end').value),
        curve_preset: document.getElementById('left-curve').value,
        curve_intensity: parseInt(document.getElementById('left-curve-intensity').value)
    };
    
    currentConfig.trigger_right = {
        hair_mode: document.getElementById('right-hair-mode').value,
        hair_trigger_begin: parseInt(document.getElementById('right-hair-begin').value),
        hair_trigger_end: parseInt(document.getElementById('right-hair-end').value),
        deadzone_begin: parseInt(document.getElementById('right-dz-begin').value),
        deadzone_end: parseInt(document.getElementById('right-dz-end').value),
        antideadzone_begin: parseInt(document.getElementById('right-anti-begin').value),
        antideadzone_end: parseInt(document.getElementById('right-anti-end').value),
        curve_preset: document.getElementById('right-curve').value,
        curve_intensity: parseInt(document.getElementById('right-curve-intensity').value)
    };
    
    await saveConfigToServer(currentConfig);
}

async function saveSticks() {
    const sides = ['left', 'right'];
    const data = {
        left: {},
        right: {}
    };
    
    for (const side of sides) {
        const prefix = side === 'left' ? 'left' : 'right';
        data[side] = {
            mode: document.getElementById(`${prefix}-stick-mode`).value,
            x_sens: parseInt(document.getElementById(`${prefix}-x-sens`).value),
            y_sens: parseInt(document.getElementById(`${prefix}-y-sens`).value),
            overlap: parseInt(document.getElementById(`${prefix}-overlap`).value),
            mouse_dpi: parseInt(document.getElementById(`${prefix}-mouse-dpi`).value),
            mouse_ydpi: parseInt(document.getElementById(`${prefix}-mouse-ydpi`).value),
            square: document.getElementById(`${prefix}-shape`).value === 'square',
            deadzone_min: parseInt(document.getElementById(`${prefix}-deadzone-min`).value),
            antideadzone_min: parseInt(document.getElementById(`${prefix}-antideadzone-min`).value),
            deadzone_max: parseInt(document.getElementById(`${prefix}-deadzone-max`).value),
            antideadzone_max: parseInt(document.getElementById(`${prefix}-antideadzone-max`).value),
            curve: document.getElementById(`${prefix}-stick-curve`).value,
            curve_intensity: parseInt(document.getElementById(`${prefix}-stick-curve-intensity`).value)
        };
        
        currentConfig[`stick_${side}`] = {
            mode: data[side].mode,
            x_sensitivity: data[side].x_sens,
            y_sensitivity: data[side].y_sens,
            overlap_percent: data[side].overlap,
            mouse_x_dpi: data[side].mouse_dpi,
            mouse_y_dpi: data[side].mouse_ydpi,
            is_circle: !data[side].square,
            deadzone_min: data[side].deadzone_min,
            antideadzone_min: data[side].antideadzone_min,
            deadzone_max: data[side].deadzone_max,
            antideadzone_max: data[side].antideadzone_max,
            curve_preset: data[side].curve,
            curve_intensity: data[side].curve_intensity
        };
    }
    
    await apiCall('/stick', 'POST', data);
    await saveConfigToServer(currentConfig);
}

async function saveGyro() {
    const data = {
        mode: document.getElementById('gyro-output-mode').value,
        motion: document.getElementById('gyro-motion-mode').value,
        method: document.getElementById('gyro-method').value,
        axis: document.getElementById('gyro-axis').value,
        button: document.getElementById('gyro-button').value,
        x_sens: parseInt(document.getElementById('gyro-x-sens').value),
        y_sens: parseInt(document.getElementById('gyro-y-sens').value),
        overlap: parseInt(document.getElementById('gyro-overlap').value),
        deadzone_min: parseInt(document.getElementById('gyro-deadzone-min').value),
        deadzone_max: parseInt(document.getElementById('gyro-deadzone-max').value),
        antideadzone_min: parseInt(document.getElementById('gyro-antideadzone-min').value),
        antideadzone_max: parseInt(document.getElementById('gyro-antideadzone-max').value),
        invert_x: document.getElementById('gyro-invert-x').checked,
        invert_y: document.getElementById('gyro-invert-y').checked,
        curve: document.getElementById('gyro-curve').value,
        curve_intensity: parseInt(document.getElementById('gyro-curve-intensity').value),
        kb_up: document.getElementById('gyro-kb-up').value,
        kb_down: document.getElementById('gyro-kb-down').value,
        kb_left: document.getElementById('gyro-kb-left').value,
        kb_right: document.getElementById('gyro-kb-right').value
    };
    
    await apiCall('/gyro', 'POST', data);
    
    currentConfig.gyro = {
        output_mode: data.mode,
        motion_mode: data.motion,
        activate_method: data.method,
        axis_mode: data.axis,
        activate_button: data.button,
        x_sensitivity: data.x_sens,
        y_sensitivity: data.y_sens,
        overlap_percent: data.overlap,
        deadzone_min: data.deadzone_min,
        deadzone_max: data.deadzone_max,
        antideadzone_min: data.antideadzone_min,
        antideadzone_max: data.antideadzone_max,
        invert_x: data.invert_x,
        invert_y: data.invert_y,
        curve_preset: data.curve,
        curve_intensity: data.curve_intensity,
        kb_up: data.kb_up,
        kb_down: data.kb_down,
        kb_left: data.kb_left,
        kb_right: data.kb_right
    };
    
    await saveConfigToServer(currentConfig);
}

async function applyRemap() {
    const button = document.getElementById('remap-source').value;
    const target = document.getElementById('remap-target').value;
    
    await apiCall('/map', 'POST', { button, target });
    
    if (!currentConfig.key_mappings) currentConfig.key_mappings = {};
    currentConfig.key_mappings[button] = target;
    
    await saveConfigToServer(currentConfig);
}

async function saveTurbo() {
    const data = {
        button: document.getElementById('turbo-button').value,
        target: document.getElementById('turbo-target').value,
        rate: parseInt(document.getElementById('turbo-rate').value),
        continuous: document.getElementById('turbo-continuous').checked
    };
    
    await apiCall('/turbo', 'POST', data);
    alert('Turbo applied successfully!');
}

async function saveRumble() {
    const left = parseInt(document.getElementById('rumble-left').value);
    const right = parseInt(document.getElementById('rumble-right').value);
    
    await apiCall('/rumble', 'POST', { pct: left, right });
    alert('Rumble level set!');
}

async function fireRumble() {
    const left = parseInt(document.getElementById('rumble-fire-left').value);
    const right = parseInt(document.getElementById('rumble-fire-right').value);
    const duration = parseInt(document.getElementById('rumble-duration').value);
    
    await apiCall('/rumble', 'POST', { fire: left, fire_right: right, duration });
    alert('Rumble fired!');
}

async function saveCombo() {
    const button = document.getElementById('combo-button').value;
    const keysText = document.getElementById('combo-keys').value;
    const keys = keysText.split(' ').filter(k => k);
    
    if (keys.length < 2 || keys.length > 3) {
        alert('Combo requires 2 or 3 keys');
        return;
    }
    
    await apiCall('/combo', 'POST', { button, keys });
    alert('Combo applied successfully!');
}

async function saveMacro() {
    const button = document.getElementById('macro-button').value;
    const stepsText = document.getElementById('macro-steps').value;
    const steps = stepsText.split('\n').filter(s => s.trim());
    
    await apiCall('/macro', 'POST', {
        button,
        steps,
        hold: document.getElementById('macro-hold').checked,
        loop: document.getElementById('macro-loop').checked
    });
    alert('Macro applied successfully!');
}

async function saveAllConfig() {
    await saveConfigToServer(currentConfig);
}
