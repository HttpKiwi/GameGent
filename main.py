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
    print("  sudo ./main.py remap <btn> <target> - Map controller button to key or mouse action")

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
        
        # Sync key mappings if defined
        mappings = state.get("key_mappings", {})
        if mappings:
            print("Enforcing key/mouse mappings down the wire...")
            for btn, target in mappings.items():
                core.apply_mapping(btn, target)
                
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

    elif command == "remap":
        if len(sys.argv) < 4:
            print("Error: Missing button name or target mapping.")
            print("Usage: sudo ./main.py remap <button> <target>")
            print("Example: sudo ./main.py remap c1 left_click")
            return
        btn = sys.argv[2]
        target = sys.argv[3]
        
        if "key_mappings" not in state:
            state["key_mappings"] = {}
        
        state["key_mappings"][btn.lower()] = target.lower()
        core.apply_mapping(btn, target)
        core.save_config(state)
        print(f"Mapped {btn} to {target} and committed to config.")

    else:
        print_usage()

if __name__ == "__main__":
    try:
        main()
    except PermissionError:
        print("[!] Error: Accessing /dev/hidraw nodes requires higher privileges. Run with sudo.")
    except Exception as e:
        print(f"[!] Operation Failed: {e}")
