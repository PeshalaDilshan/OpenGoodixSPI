#!/usr/bin/env python3
import os
import sys

DEV_PATH = "/dev/opengoodixspi"

def main():
    if not os.path.exists(DEV_PATH):
        print(f"❌ Error: {DEV_PATH} not found. Is the driver loaded?")
        sys.exit(1)

    print(f"👆 Trigger active. Reading from {DEV_PATH}...")
    print("   (This process will block until you touch the sensor)")
    
    try:
        fd = os.open(DEV_PATH, os.O_RDONLY)
        while True:
            # This read blocks until the driver receives an interrupt from the hardware
            data = os.read(fd, 128)
            if data:
                print(f"✅ Touch detected! (Triggered SPI transfer of {len(data)} bytes)")
            else:
                # If driver returns 0 bytes, something might be wrong with the xfer
                pass
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
