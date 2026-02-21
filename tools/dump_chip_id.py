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

    print("🔍 Dumping Chip ID (F0) with extended buffer...")
    
    try:
        dev_fd = os.open(DEV_PATH, os.O_WRONLY)
        log_fd = open(LOG_PATH, "r")
        log_fd.read() # Clear logs

        # 1. Reset & Wake
        print("⚡ Sending Reset (0C) & Wake (B0)...")
        os.write(dev_fd, bytes([0x0C, 0x00, 0x00, 0x00]))
        time.sleep(0.1)
        os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
        time.sleep(0.1)

        # 2. Read F0 with 16 bytes
        print("👉 Sending F0 + 15 dummy bytes...")
        payload = bytes([0xF0] + [0x00]*15)
        os.write(dev_fd, payload)
        time.sleep(0.1)
        
        # Check response
        logs = log_fd.read()
        for line in logs.splitlines():
            if "RX:" in line:
                print(f"   {line.strip()}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()