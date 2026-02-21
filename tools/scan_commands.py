#!/usr/bin/env python3
import os
import sys
import time

DEV_PATH = "/dev/opengoodixspi"
LOG_PATH = "/sys/kernel/debug/opengoodixspi/spi_log"

def main():
    if os.geteuid() != 0:
        print("❌ Please run with sudo")
        sys.exit(1)

    if not os.path.exists(DEV_PATH):
        print(f"❌ Error: {DEV_PATH} not found.")
        sys.exit(1)

    print("🛑 IMPORTANT: Stop live_monitor.py before running this!")
    print("🔍 Scanning commands 0x00 - 0xFF...")
    print("   (Showing only active responses)")

    try:
        dev_fd = os.open(DEV_PATH, os.O_WRONLY)
        log_fd = open(LOG_PATH, "r")
        
        # Consume any existing logs
        log_fd.read()
        
        for cmd in range(256):
            # 1. Wake up the sensor first
            os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
            time.sleep(0.01)

            # Send CMD + 3 dummy bytes (e.g., A0 00 00 00)
            payload = bytes([cmd, 0, 0, 0])
            os.write(dev_fd, payload)
            
            # Small delay to allow driver to log
            time.sleep(0.02)
            
            # Read logs and filter
            logs = log_fd.read()
            for line in logs.splitlines():
                # Filter out "ff" (floating) and "00" (empty) responses
                if "RX:" in line and "ff ff ff ff" not in line and "00 00 00 00" not in line:
                    print(f"CMD {cmd:02X} -> {line.strip()}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()