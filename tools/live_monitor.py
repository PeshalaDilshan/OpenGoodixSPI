#!/usr/bin/env python3
import time
import os

LOG_PATH = "/sys/kernel/debug/opengoodixspi/spi_log"

def main():
    print(f"📡 Monitoring Goodix SPI Traffic at {LOG_PATH}...")
    print("Press Ctrl+C to stop.")
    
    if not os.path.exists(LOG_PATH):
        print("❌ Error: Debugfs file not found. Is the driver loaded?")
        return

    try:
        while True:
            # The driver returns 0 (EOF) when buffer is empty, so we must reopen
            with open(LOG_PATH, "r") as f:
                data = f.read()
                if data:
                    # Print each line with a timestamp
                    for line in data.strip().split('\n'):
                        print(f"[{time.strftime('%H:%M:%S')}] {line}")
            
            # Prevent CPU spinning
            time.sleep(0.1)
            
    except PermissionError:
        print("❌ Error: Permission denied. Run with sudo.")
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
