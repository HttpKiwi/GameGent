# core/transport.py
import os
import glob

# The hardware IDs we are hunting for (lowercase for safe matching)
VENDOR_ID = "3537"
PRODUCT_ID = "103e"

def find_dongle_path():
    """Scans sysfs directory topology to locate the correct hidraw node"""
    # Look at every registered hidraw device
    for sysfs_path in glob.glob("/sys/class/hidraw/hidraw*"):
        try:
            # Resolving the symlink takes us to the true device boundary
            real_path = os.path.realpath(sysfs_path)
            
            # The path will look something like: 
            # /sys/devices/pci0000:00/.../0003:3537:103E.000A/hidraw/hidraw9
            # We just need to check if our target VID and PID are anywhere in that path string
            if f"{VENDOR_ID}:{PRODUCT_ID}" in real_path.lower():
                dev_name = os.path.basename(sysfs_path) # Extracts 'hidraw9'
                return f"/dev/{dev_name}"
        except Exception:
            continue
    return None

def send_raw_bytes(payload):
    """Injects a 32-byte payload straight into the kernel"""
    device_path = find_dongle_path()
    if not device_path:
        raise FileNotFoundError("GameSir Dongle not found in system topologies.")

    if isinstance(payload, (bytes, bytearray)):
        payload = list(payload)

    # Ensure absolute 32-byte alignment
    padded_payload = payload + [0x00] * (32 - len(payload))
    
    # Standard Linux primitive write
    fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
    try:
        os.write(fd, bytes(padded_payload))
    finally:
        os.close(fd)
