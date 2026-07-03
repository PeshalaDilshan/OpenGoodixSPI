#!/usr/bin/env python3
"""
OpenGoodixSPI Userspace Test Tool
Test driver functionality, send commands, capture data, and simulate fingerprint reads.
"""

import os
import sys
import time
import argparse
import fcntl
import struct
from pathlib import Path

DEVICE_PATH = "/dev/opengoodixspi"
IOCTL_GET_STATE = 0x80044701  # _IOR('G', 1, int)
IOCTL_RESET     = 0x40044702  # _IO('G', 2)

def open_device():
    try:
        return open(DEVICE_PATH, "rb+")
    except FileNotFoundError:
        print(f"❌ Device {DEVICE_PATH} not found. Is the kernel module loaded?")
        sys.exit(1)

def get_state(fd):
    state = struct.pack("I", 0)
    try:
        result = fcntl.ioctl(fd, IOCTL_GET_STATE, state)
        state_val = struct.unpack("I", state)[0]
        states = {0: "UNINITIALIZED", 1: "BOOTLOADER", 2: "READY", 3: "ERROR"}
        print(f"📊 Driver State: {states.get(state_val, state_val)}")
        return state_val
    except Exception as e:
        print(f"❌ IOCTL failed: {e}")
        return None

def reset_device(fd):
    try:
        fcntl.ioctl(fd, IOCTL_RESET)
        print("🔄 Device reset command sent.")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Reset failed: {e}")

def send_raw_command(fd, hex_cmd):
    try:
        cmd_bytes = bytes.fromhex(hex_cmd.replace(" ", ""))
        fd.write(cmd_bytes)
        fd.flush()
        print(f"📤 Sent: {cmd_bytes.hex(' ')}")
        time.sleep(0.1)
        response = fd.read(64)  # Read up to 64 bytes response
        if response:
            print(f"📥 Response: {response.hex(' ')}")
    except Exception as e:
        print(f"❌ Command failed: {e}")

def capture_fingerprint(fd, output="fingerprint.raw"):
    print("👆 Touch the sensor now (timeout 10s)...")
    start = time.time()
    while time.time() - start < 10:
        try:
            data = fd.read(4096)
            if data and len(data) > 32:
                with open(output, "wb") as f:
                    f.write(data)
                print(f"✅ Captured {len(data)} bytes -> {output}")
                return
        except BlockingIOError:
            time.sleep(0.2)
        except Exception as e:
            print(f"Read error: {e}")
            break
    print("⏰ Timeout. No data received.")

def main():
    parser = argparse.ArgumentParser(description="OpenGoodixSPI Test Tool")
    parser.add_argument("--state", action="store_true", help="Get driver state")
    parser.add_argument("--reset", action="store_true", help="Reset device")
    parser.add_argument("--cmd", type=str, help="Send raw hex command (e.g. 'F0')")
    parser.add_argument("--capture", action="store_true", help="Capture fingerprint image")
    parser.add_argument("-o", "--output", default="fingerprint.raw", help="Output file for capture")
    args = parser.parse_args()

    fd = open_device()

    if args.state:
        get_state(fd)
    if args.reset:
        reset_device(fd)
    if args.cmd:
        send_raw_command(fd, args.cmd)
    if args.capture:
        capture_fingerprint(fd, args.output)

    fd.close()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("⚠️  Run with sudo for device access.")
    main()