#!/usr/bin/env python3
# main.py
import sys
import core
from core.protocol import LIGHTING_MODES

def print_usage():
    print("GameGent Controller Tool")
    print("Usage:")
    print("  ./main.py                       - Show current local profile state")
    print("  sudo ./main.py sync             - Push saved state down to hardware")
    print("  sudo ./main.py mode <name>      - Set lighting mode (static, rainbow, etc.)")
    print("  sudo ./main.py brightness <0-100> - Set illumination value")
    print("  sudo ./main.py speed <0-100>    - Set animation velocity")
    print("  sudo ./main.py color <0-360>    - Set custom color hue angle (for breathing, radar, static)")
    print("  ./main.py remap <btn> <target>  - Map controller button to key or mouse action")
    print("  ./main.py remap <btn> clear     - Clear mapping for a button")
    print("  ./main.py joystick [<left|right> [<attr> <val>]] - View/configure joystick curves and zones")
    print("\nValid buttons: c1-c4, t1-t3, l4, r4")
    print("Valid targets: keyboard keys, mouse clicks/scrolls, controller buttons, or 'unbind'")
    print("               (e.g., 'enter', 'left_click', 'controller:a' to avoid keyboard conflict)")
    print("\nJoystick configurations:")
    print("  Attributes: circle (true/false), deadzone_min (0-100), antideadzone_min (0-100)")
    print("              deadzone_max (0-100), antideadzone_max (0-100)")
    print("              curve (linear, expo, s-curve), intensity (0-100)")

def main():
    state = core.load_config()

    if len(sys.argv) == 1:
        print("--- CURRENT LOCAL PROFILE STATE ---")
        for k, v in state.items():
            print(f"  {k.replace('_', ' ').title()}: {v}")
        return

    command = sys.argv[1].lower()

    if command == "sync":
        print(f"Enforcing profile target ({state['lighting_mode']}) down the wire...")
        core.set_hardware_state(
            mode=state["lighting_mode"],
            brightness=state["brightness"],
            speed=state["lighting_speed"]
        )
        
        # Sync color if configured and lighting mode supports custom colors (static, breathing, radar)
        if state.get("lighting_mode") in ["static", "breathing", "radar"] and "color_hue" in state:
            hue = state["color_hue"]
            print(f"Enforcing custom color hue ({hue}°) down the wire...")
            core.set_color(hue)
            
        # Sync key mappings if defined
        mappings = state.get("key_mappings", {})
        if mappings:
            print("Enforcing key/mouse mappings down the wire...")
            for btn, target in mappings.items():
                core.apply_mapping(btn, target)
                
        # Sync joystick configurations
        print("Enforcing joystick configurations down the wire...")
        from core.config import DEFAULT_CONFIG
        left_data = state.get("joystick_left", DEFAULT_CONFIG["joystick_left"])
        right_data = state.get("joystick_right", DEFAULT_CONFIG["joystick_right"])
        left_config = core.JoystickConfig(
            is_circle=left_data.get("is_circle", True),
            deadzone_min=left_data.get("deadzone_min", 5),
            antideadzone_min=left_data.get("antideadzone_min", 0),
            deadzone_max=left_data.get("deadzone_max", 100),
            antideadzone_max=left_data.get("antideadzone_max", 100),
            curve_preset=left_data.get("curve_preset", "linear"),
            curve_intensity=left_data.get("curve_intensity", 50)
        )
        right_config = core.JoystickConfig(
            is_circle=right_data.get("is_circle", True),
            deadzone_min=right_data.get("deadzone_min", 5),
            antideadzone_min=right_data.get("antideadzone_min", 0),
            deadzone_max=right_data.get("deadzone_max", 100),
            antideadzone_max=right_data.get("antideadzone_max", 100),
            curve_preset=right_data.get("curve_preset", "linear"),
            curve_intensity=right_data.get("curve_intensity", 50)
        )
        core.set_joystick_state(left_config, right_config)
                
        print("Hardware sync complete.")

    elif command == "mode":
        if len(sys.argv) < 3:
            print("Error: Missing mode name.")
            return
        mode_val = sys.argv[2].lower()
        if mode_val not in LIGHTING_MODES:
            print(f"Invalid mode. Choose from: {list(LIGHTING_MODES.keys())}")
            return
            
        state["lighting_mode"] = mode_val
        core.set_hardware_state(mode_val, state["brightness"], state["lighting_speed"])
        core.save_config(state)
        print(f"Mode updated to {mode_val} and committed to config.")

    elif command == "brightness":
        if len(sys.argv) < 3:
            print("Error: Missing percentage.")
            return
        val = int(sys.argv[2])
        state["brightness"] = val
        core.set_hardware_state(state["lighting_mode"], val, state["lighting_speed"])
        core.save_config(state)
        print(f"Brightness updated to {val}% and committed to config.")

    elif command == "speed":
        if len(sys.argv) < 3:
            print("Error: Missing speed setting.")
            return
        val = int(sys.argv[2])
        state["lighting_speed"] = val
        core.set_hardware_state(state["lighting_mode"], state["brightness"], val)
        core.save_config(state)
        print(f"Animation speed updated to {val}% and committed to config.")

    elif command == "color":
        if len(sys.argv) < 3:
            print("Error: Missing hue value (0-360).")
            return
        try:
            hue = int(sys.argv[2])
            if not (0 <= hue <= 360):
                raise ValueError("Hue must be between 0 and 360.")
        except ValueError as e:
            print(f"Error: {e}")
            return
            
        state["color_hue"] = hue
        # If currently not in a mode that supports custom colors, default to static
        if state.get("lighting_mode") not in ["static", "breathing", "radar"]:
            state["lighting_mode"] = "static"
            print("Lighting mode updated to 'static' to support custom color.")
            
        core.save_config(state)
        print(f"Custom color hue updated to {hue}° and committed to config.")
        
        try:
            # Set mode/speed/brightness first
            core.set_hardware_state(state["lighting_mode"], state["brightness"], state["lighting_speed"])
            # Then apply the custom color packet
            core.set_color(hue)
            print("Successfully pushed color to hardware.")
        except Exception as e:
            print(f"[!] Warning: Could not push color to hardware: {e}")

    elif command == "remap":
        if len(sys.argv) < 4:
            print("Error: Missing button name or target mapping.")
            print("Usage: ./main.py remap <button> <target>")
            print("Example: ./main.py remap c1 left_click")
            return
        btn = sys.argv[2].lower()
        target = sys.argv[3].lower()
        
        # Validate button
        try:
            core.resolve_button_index(btn)
        except ValueError as e:
            print(f"Error: {e}")
            print(f"Valid buttons are: {', '.join(core.CONTROLLER_SOURCE.keys())}")
            return
            
        # Validate target
        if target != "clear":
            try:
                core.resolve_target_packet(0, target)
            except ValueError as e:
                print(f"Error: {e}")
                print("Valid targets include:")
                print("  - Keyboard keys (e.g., 'a', 'escape', 'enter')")
                print("  - Mouse clicks (e.g., 'left_click', 'right_click', 'button_4')")
                print("  - Mouse scrolls (e.g., 'scroll_up', 'scroll_down')")
                print("  - Controller buttons (e.g., 'a', 'lb', 'dpad_up') - use 'controller:a' to resolve ambiguity")
                print("  - 'unbind' to disable the button")
                print("  - 'clear' to remove mapping from configuration")
                return

        if "key_mappings" not in state:
            state["key_mappings"] = {}
        
        if target == "clear":
            if btn in state["key_mappings"]:
                del state["key_mappings"][btn]
            core.save_config(state)
            print(f"Removed {btn} mapping from local config.")
            
            # Send unbind packet to hardware
            try:
                core.apply_mapping(btn, "unbind")
                print("Successfully cleared mapping on hardware.")
            except Exception as e:
                print(f"[!] Warning: Could not clear mapping on hardware: {e}")
                print("Run 'sudo ./main.py sync' to apply updates.")
        else:
            state["key_mappings"][btn] = target
            core.save_config(state)
            print(f"Mapped {btn} to {target} in local config.")
            
            # Send to hardware
            try:
                core.apply_mapping(btn, target)
                print("Successfully pushed mapping to hardware.")
            except Exception as e:
                print(f"[!] Warning: Could not push mapping to hardware: {e}")
                print("Run 'sudo ./main.py sync' to apply updates.")

    elif command == "joystick":
        from core.config import DEFAULT_CONFIG
        left_data = state.get("joystick_left", DEFAULT_CONFIG["joystick_left"])
        right_data = state.get("joystick_right", DEFAULT_CONFIG["joystick_right"])
        
        if len(sys.argv) == 2:
            print("--- JOYSTICK CONFIGURATION ---")
            print("Left Stick:")
            for k, v in left_data.items():
                print(f"  {k}: {v}")
            print("\nRight Stick:")
            for k, v in right_data.items():
                print(f"  {k}: {v}")
            return
            
        stick = sys.argv[2].lower()
        if stick not in ["left", "right"]:
            print("Error: Stick must be 'left' or 'right'.")
            return
            
        stick_data = left_data if stick == "left" else right_data
        
        if len(sys.argv) == 3:
            print(f"--- {stick.upper()} STICK CONFIGURATION ---")
            for k, v in stick_data.items():
                print(f"  {k}: {v}")
            return
            
        if len(sys.argv) < 5:
            print("Error: Missing attribute or value.")
            print("Usage: ./main.py joystick <left|right> <attribute> <value>")
            return
            
        attr = sys.argv[3].lower()
        val_str = sys.argv[4].lower()
        
        attr_map = {
            "is_circle": "is_circle",
            "circle": "is_circle",
            "deadzone_min": "deadzone_min",
            "deadzone-min": "deadzone_min",
            "dz_min": "deadzone_min",
            "dz-min": "deadzone_min",
            "antideadzone_min": "antideadzone_min",
            "antideadzone-min": "antideadzone_min",
            "adz_min": "antideadzone_min",
            "adz-min": "antideadzone_min",
            "deadzone_max": "deadzone_max",
            "deadzone-max": "deadzone_max",
            "dz_max": "deadzone_max",
            "dz-max": "deadzone_max",
            "antideadzone_max": "antideadzone_max",
            "antideadzone-max": "antideadzone_max",
            "adz_max": "antideadzone_max",
            "adz-max": "antideadzone_max",
            "curve_preset": "curve_preset",
            "curve-preset": "curve_preset",
            "curve": "curve_preset",
            "preset": "curve_preset",
            "curve_intensity": "curve_intensity",
            "curve-intensity": "curve_intensity",
            "intensity": "curve_intensity"
        }
        
        if attr not in attr_map:
            print(f"Error: Unknown joystick attribute '{attr}'.")
            print("Valid attributes: circle, deadzone_min, antideadzone_min, deadzone_max, antideadzone_max, curve, intensity")
            return
            
        canonical_attr = attr_map[attr]
        
        if canonical_attr == "is_circle":
            if val_str in ["true", "1", "yes", "on", "circle"]:
                val = True
            elif val_str in ["false", "0", "no", "off", "square", "raw"]:
                val = False
            else:
                print("Error: is_circle value must be true/false.")
                return
        elif canonical_attr in ["deadzone_min", "antideadzone_min", "deadzone_max", "antideadzone_max", "curve_intensity"]:
            try:
                val = int(val_str)
                if not (0 <= val <= 100):
                    raise ValueError()
            except ValueError:
                print(f"Error: {canonical_attr} must be an integer between 0 and 100.")
                return
        elif canonical_attr == "curve_preset":
            if val_str in ["linear", "expo", "s-curve", "s_curve", "scurve"]:
                if val_str in ["s_curve", "scurve"]:
                    val = "s-curve"
                else:
                    val = val_str
            else:
                print("Error: curve_preset must be one of: linear, expo, s-curve")
                return
                
        stick_data[canonical_attr] = val
        state[f"joystick_{stick}"] = stick_data
        core.save_config(state)
        print(f"Updated {stick} stick {canonical_attr} to {val} in local config.")
        
        try:
            left_inst = core.JoystickConfig(
                is_circle=left_data.get("is_circle", True),
                deadzone_min=left_data.get("deadzone_min", 5),
                antideadzone_min=left_data.get("antideadzone_min", 0),
                deadzone_max=left_data.get("deadzone_max", 100),
                antideadzone_max=left_data.get("antideadzone_max", 100),
                curve_preset=left_data.get("curve_preset", "linear"),
                curve_intensity=left_data.get("curve_intensity", 50)
            )
            right_inst = core.JoystickConfig(
                is_circle=right_data.get("is_circle", True),
                deadzone_min=right_data.get("deadzone_min", 5),
                antideadzone_min=right_data.get("antideadzone_min", 0),
                deadzone_max=right_data.get("deadzone_max", 100),
                antideadzone_max=right_data.get("antideadzone_max", 100),
                curve_preset=right_data.get("curve_preset", "linear"),
                curve_intensity=right_data.get("curve_intensity", 50)
            )
            core.set_joystick_state(left_inst, right_inst)
            print("Successfully pushed joystick configuration to hardware.")
        except Exception as e:
            print(f"[!] Warning: Could not push joystick configuration to hardware: {e}")
            print("Run 'sudo ./main.py sync' to apply updates.")

    else:
        print_usage()

if __name__ == "__main__":
    try:
        main()
    except PermissionError:
        print("[!] Error: Accessing /dev/hidraw nodes requires higher privileges. Run with sudo.")
    except Exception as e:
        print(f"[!] Operation Failed: {e}")
