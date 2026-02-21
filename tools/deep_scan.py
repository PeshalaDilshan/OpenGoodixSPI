#!/usr/bin/env python3
import os
import sys
import time
import struct

DEV_PATH = "/dev/opengoodixspi"
LOG_PATH = "/sys/kernel/debug/opengoodixspi/spi_log"

def main():
    if os.geteuid() != 0:
        print("❌ Please run with sudo")
        sys.exit(1)

    print("🔍 Deep Scan: Searching for Control Registers...")
    print("   Strategy: Write 0x01 to address, check for response.")

    try:
        dev_fd = os.open(DEV_PATH, os.O_RDWR)
        log_fd = open(LOG_PATH, "r")
        log_fd.read() # Clear logs

        # 1. Reset & Wake
        print("⚡ Sending Reset (0C) & Wake (B0)...")
        os.write(dev_fd, bytes([0x0C, 0x00, 0x00, 0x00]))
        time.sleep(0.1)
        os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
        time.sleep(0.1)

        # 2. Scan Addresses 0x0000 - 0x0100
        # We suspect the control register is in this range.
        # Common Goodix Write Opcode is often 0xF0 + 1 (0xF1) or 0x80 + 1 (0x81)
        # But let's try the standard "Write" opcode if we can guess it.
        # If Read is 0xF0, Write might be 0xF1.
        
        WRITE_CMD = 0xF1 

        for addr in range(0x00, 0x100):
            # Construct: CMD | ADDR_H | ADDR_L | DATA
            # Try to write 0x01 to this address
            payload = bytes([WRITE_CMD, 0x00, addr, 0x01])
            
            os.write(dev_fd, payload)
            time.sleep(0.01)

            # Immediately try to read back using F0 (Chip ID read) to see if device is still alive
            # or if the write caused a state change.
            os.write(dev_fd, bytes([0xF0, 0x00, 0x00, 0x00]))
            time.sleep(0.01)

            logs = log_fd.read()
            if "RX: 00 f0 10 00" not in logs.lower():
                # If we don't see the Chip ID, maybe we crashed it or found a special register
                print(f"⚠️  Anomaly at Address 0x{addr:02X} (Device state changed?)")
                print(f"    Logs: {logs.strip()}")
                
                # Re-wake
                os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
                time.sleep(0.05)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()