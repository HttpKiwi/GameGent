// Controller SVG Interaction for Remapping

document.addEventListener('DOMContentLoaded', function() {
    const controllerSvg = document.getElementById('controller-svg');
    const remapSourceSelect = document.getElementById('remap-source');
    
    if (controllerSvg) {
        // Load SVG and make it interactive
        controllerSvg.addEventListener('load', function() {
            const svgDoc = controllerSvg.contentDocument;
            if (svgDoc) {
                setupControllerInteractions(svgDoc);
            }
        });
        
        // If SVG is already loaded
        if (controllerSvg.complete) {
            const svgDoc = controllerSvg.contentDocument;
            if (svgDoc) {
                setupControllerInteractions(svgDoc);
            }
        }
    }
    
    function setupControllerInteractions(svgDoc) {
        // Define button mappings based on SVG elements
        // This will need to be adjusted based on the actual SVG structure
        const buttonMappings = {
            'l4': ['l4', 'L4', 'button-l4'],
            'r4': ['r4', 'R4', 'button-r4'],
            't1': ['t1', 'T1', 'button-t1'],
            't2': ['t2', 'T2', 'button-t2'],
            't3': ['t3', 'T3', 'button-t3'],
            'c1': ['c1', 'C1', 'button-c1'],
            'c2': ['c2', 'C2', 'button-c2'],
            'c3': ['c3', 'C3', 'button-c3'],
            'c4': ['c4', 'C4', 'button-c4'],
            'a': ['a', 'A', 'button-a'],
            'b': ['b', 'B', 'button-b'],
            'x': ['x', 'X', 'button-x'],
            'y': ['y', 'Y', 'button-y'],
            'lb': ['lb', 'LB', 'button-lb'],
            'rb': ['rb', 'RB', 'button-rb'],
            'lt': ['lt', 'LT', 'button-lt'],
            'rt': ['rt', 'RT', 'button-rt'],
            'l3': ['l3', 'L3', 'button-l3'],
            'r3': ['r3', 'R3', 'button-r3'],
            'back': ['back', 'Back', 'button-back'],
            'start': ['start', 'Start', 'button-start'],
            'dpad_up': ['dpad_up', 'dpad-up', 'dpadUp', 'button-dpad-up'],
            'dpad_down': ['dpad_down', 'dpad-down', 'dpadDown', 'button-dpad-down'],
            'dpad_left': ['dpad_left', 'dpad-left', 'dpadLeft', 'button-dpad-left'],
            'dpad_right': ['dpad_right', 'dpad-right', 'dpadRight', 'button-dpad-right'],
            'screenshot': ['screenshot', 'Screenshot', 'button-screenshot']
        };
        
        // Find and make buttons clickable
        for (const [buttonId, possibleIds] of Object.entries(buttonMappings)) {
            for (const id of possibleIds) {
                const element = svgDoc.getElementById(id) || svgDoc.querySelector(`[id*="${id}"]`) || svgDoc.querySelector(`[class*="${id}"]`);
                if (element) {
                    element.style.cursor = 'pointer';
                    element.addEventListener('click', function(e) {
                        e.preventDefault();
                        selectButtonForRemap(buttonId);
                        highlightButton(element);
                    });
                    
                    // Add hover effect
                    element.addEventListener('mouseenter', function() {
                        element.style.opacity = '0.7';
                    });
                    
                    element.addEventListener('mouseleave', function() {
                        element.style.opacity = '1';
                    });
                    
                    break; // Found the element, move to next button
                }
            }
        }
    }
    
    function selectButtonForRemap(buttonId) {
        if (remapSourceSelect) {
            remapSourceSelect.value = buttonId;
            // Trigger change event
            const event = new Event('change');
            remapSourceSelect.dispatchEvent(event);
        }
    }
    
    function highlightButton(element) {
        // Remove highlight from all buttons
        const svgDoc = controllerSvg.contentDocument;
        if (svgDoc) {
            const allElements = svgDoc.querySelectorAll('*');
            allElements.forEach(el => {
                el.style.filter = 'none';
            });
        }
        
        // Add highlight to selected button
        element.style.filter = 'brightness(1.5) drop-shadow(0 0 5px #00a4ef)';
        
        // Remove highlight after 1 second
        setTimeout(() => {
            element.style.filter = 'none';
        }, 1000);
    }
    
    // Visual feedback for remapped buttons
    function updateRemappedButtons() {
        const svgDoc = controllerSvg.contentDocument;
        if (!svgDoc || !currentConfig.key_mappings) return;
        
        const buttonMappings = {
            'l4': ['l4', 'L4', 'button-l4'],
            'r4': ['r4', 'R4', 'button-r4'],
            't1': ['t1', 'T1', 'button-t1'],
            't2': ['t2', 'T2', 'button-t2'],
            't3': ['t3', 'T3', 'button-t3'],
            'c1': ['c1', 'C1', 'button-c1'],
            'c2': ['c2', 'C2', 'button-c2'],
            'c3': ['c3', 'C3', 'button-c3'],
            'c4': ['c4', 'C4', 'button-c4'],
            'a': ['a', 'A', 'button-a'],
            'b': ['b', 'B', 'button-b'],
            'x': ['x', 'X', 'button-x'],
            'y': ['y', 'Y', 'button-y'],
            'lb': ['lb', 'LB', 'button-lb'],
            'rb': ['rb', 'RB', 'button-rb'],
            'lt': ['lt', 'LT', 'button-lt'],
            'rt': ['rt', 'RT', 'button-rt'],
            'l3': ['l3', 'L3', 'button-l3'],
            'r3': ['r3', 'R3', 'button-r3'],
            'back': ['back', 'Back', 'button-back'],
            'start': ['start', 'Start', 'button-start'],
            'dpad_up': ['dpad_up', 'dpad-up', 'dpadUp', 'button-dpad-up'],
            'dpad_down': ['dpad_down', 'dpad-down', 'dpadDown', 'button-dpad-down'],
            'dpad_left': ['dpad_left', 'dpad-left', 'dpadLeft', 'button-dpad-left'],
            'dpad_right': ['dpad_right', 'dpad-right', 'dpadRight', 'button-dpad-right'],
            'screenshot': ['screenshot', 'Screenshot', 'button-screenshot']
        };
        
        for (const [button, target] of Object.entries(currentConfig.key_mappings)) {
            const possibleIds = buttonMappings[button];
            if (possibleIds) {
                for (const id of possibleIds) {
                    const element = svgDoc.getElementById(id) || svgDoc.querySelector(`[id*="${id}"]`);
                    if (element) {
                        // Add visual indicator that button is remapped
                        element.style.filter = 'brightness(1.2) saturate(1.2)';
                    }
                }
            }
        }
    }
    
    // Update button highlights when config changes
    const originalSaveConfigToServer = window.saveConfigToServer;
    if (originalSaveConfigToServer) {
        window.saveConfigToServer = async function(config) {
            const result = await originalSaveConfigToServer(config);
            if (result) {
                updateRemappedButtons();
            }
            return result;
        };
    }
});
