#!/usr/bin/env python3
import os
import sys
import fcntl
import struct

DEV_PATH = "/dev/opengoodixspi"

# IOCTL Macros (replicated from kernel headers)
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

def _IOC(dir, type, nr, size):
    return (dir << _IOC_DIRSHIFT) | \
           (size << _IOC_SIZESHIFT) | \
           (type << _IOC_TYPESHIFT) | \
           (nr << _IOC_NRSHIFT)

def _IOR(type, nr, size):
    return _IOC(_IOC_READ, type, nr, size)

def _IO(type, nr):
    return _IOC(_IOC_NONE, type, nr, 0)

# OpenGoodix Definitions
GOODIX_IOC_MAGIC = ord('G')
GOODIX_IOC_GET_STATE = _IOR(GOODIX_IOC_MAGIC, 1, 4) # sizeof(int)
GOODIX_IOC_RESET     = _IO(GOODIX_IOC_MAGIC, 2)

STATE_MAP = {
    0: "UNINITIALIZED",
    1: "BOOTLOADER",
    2: "READY",
    3: "ERROR"
}

def main():
    if not os.path.exists(DEV_PATH):
        print(f"❌ Error: {DEV_PATH} not found. Is the driver loaded?")
        sys.exit(1)

    try:
        fd = os.open(DEV_PATH, os.O_RDWR)
        
        # 1. Get State
        # Create a 4-byte buffer for the integer result
        buf = struct.pack('I', 0)
        res = fcntl.ioctl(fd, GOODIX_IOC_GET_STATE, buf)
        state_val = struct.unpack('I', res)[0]
        
        state_str = STATE_MAP.get(state_val, f"UNKNOWN ({state_val})")
        print(f"Current Driver State: {state_str}")

        # 2. Optional: Reset
        if len(sys.argv) > 1 and sys.argv[1] == "--reset":
            print("Sending Reset Command...")
            fcntl.ioctl(fd, GOODIX_IOC_RESET)
            print("Reset complete. Re-checking state...")
            
            res = fcntl.ioctl(fd, GOODIX_IOC_GET_STATE, buf)
            state_val = struct.unpack('I', res)[0]
            print(f"New Driver State: {STATE_MAP.get(state_val, 'UNKNOWN')}")

        os.close(fd)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()