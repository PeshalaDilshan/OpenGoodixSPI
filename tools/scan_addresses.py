#!/usr/bin/env python3
import os
import sys
import time

DEV_PATH = "/dev/opengoodixspi"
LOG_PATH = "/sys/kernel/debug/opengoodixspi/spi_log"

# Common Read Commands for Goodix Sensors
READ_CMDS = [0xF0, 0x84, 0x80, 0x03]

def main():
    if os.geteuid() != 0:
        print("❌ Please run with sudo")
        sys.exit(1)

    if not os.path.exists(DEV_PATH):
        print(f"❌ Error: {DEV_PATH} not found.")
        sys.exit(1)

    print("🛑 IMPORTANT: Stop live_monitor.py before running this!")
    print("🔍 Scanning memory addresses for Chip ID...")

    try:
        dev_fd = os.open(DEV_PATH, os.O_WRONLY)
        log_fd = open(LOG_PATH, "r")
        log_fd.read() # Clear existing logs

        # 1. Reset and Wake up the sensor
        print("⚡ Sending Reset (0x0C)...")
        os.write(dev_fd, bytes([0x0C, 0x00, 0x00, 0x00]))
        time.sleep(0.1)

        print("⚡ Sending Wake (0xB0)...")
        os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
        time.sleep(0.2)

        for cmd in READ_CMDS:
            print(f"👉 Testing Read Opcode: 0x{cmd:02X} on addresses 0x00-0xFF...")
            
            # Scan low range (0x00XX) and high range (0x80XX)
            for high_byte in [0x00, 0x80]:
                print(f"   Scanning 0x{high_byte:02X}00 - 0x{high_byte:02X}FF...")
                
                for low_byte in range(0x100):
                    # Re-wake every 16 addresses to keep sensor active
                    if low_byte % 16 == 0:
                        os.write(dev_fd, bytes([0xB0, 0x00, 0x00, 0x00]))
                        time.sleep(0.005)

                    # Construct: CMD | ADDR_H | ADDR_L | DUMMY
                    payload = bytes([cmd, high_byte, low_byte, 0x00])
                    os.write(dev_fd, payload)
                    
                    # Small delay for log propagation
                    time.sleep(0.02)
                    
                    logs = log_fd.read()
                    for line in logs.splitlines():
                        if "RX:" in line and "00 00 00 00" not in line and "ff ff ff ff" not in line:
                            print(f"   MATCH! [CMD {cmd:02X} ADDR {high_byte:02X}{low_byte:02X}] -> {line.strip()}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()