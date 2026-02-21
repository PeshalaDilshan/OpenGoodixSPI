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

    print("🔍 Attempting to read Chip ID using F0 command...")
    
    try:
        dev_fd = os.open(DEV_PATH, os.O_WRONLY)
        log_fd = open(LOG_PATH, "r")
        log_fd.read() # Clear logs

        # Sequence: Reset -> Wake -> Read
        cmds = [
            ("Reset (0C)", bytes([0x0C, 0x00, 0x00, 0x00]), 0.1),
            ("Wake (B0)",  bytes([0xB0, 0x00, 0x00, 0x00]), 0.2),
            ("Read (F0)",  bytes([0xF0, 0x00, 0x00, 0x00]), 0.1)
        ]

        for name, payload, delay in cmds:
            print(f"👉 Sending {name}...")
            os.write(dev_fd, payload)
            time.sleep(delay)
            
            # Check response
            logs = log_fd.read()
            for line in logs.splitlines():
                if "RX:" in line:
                    print(f"   Response: {line.strip()}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()