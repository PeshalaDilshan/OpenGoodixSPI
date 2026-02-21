#!/usr/bin/env python3
import os
import sys
import binascii

DEV_PATH = "/dev/opengoodixspi"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <hex_string>")
        print(f"Example: {sys.argv[0]} AA00F0")
        sys.exit(1)

    hex_str = sys.argv[1]
    try:
        data = binascii.unhexlify(hex_str)
    except binascii.Error:
        print("❌ Error: Invalid hex string")
        sys.exit(1)

    if not os.path.exists(DEV_PATH):
        print(f"❌ Error: {DEV_PATH} not found.")
        sys.exit(1)

    print(f"📤 Sending {len(data)} bytes: {hex_str}")
    
    try:
        fd = os.open(DEV_PATH, os.O_WRONLY)
        os.write(fd, data)
        os.close(fd)
        print("✅ Sent.")
    except OSError as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()