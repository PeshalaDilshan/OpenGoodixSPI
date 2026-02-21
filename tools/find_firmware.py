#!/usr/bin/env python3
import sys
import os

def scan_file(filepath):
    print(f"Scanning {filepath}...")
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"  ❌ File not found.")
        return

    # Heuristic: Look for "GxFw" ASCII signature (Common in Goodix firmware headers)
    # This signature often appears at the start of the firmware blob.
    signatures = [b'GxFw', b'GXFW']
    
    found = False
    for sig in signatures:
        offset = data.find(sig)
        if offset != -1:
            found = True
            print(f"  ✅ Found '{sig.decode()}' signature at offset 0x{offset:X}")
            
            # Heuristic: Firmware is usually between 32KB and 128KB. 
            # Let's extract 128KB to be safe.
            fw_size = 128 * 1024 
            end_offset = min(offset + fw_size, len(data))
            
            out_name = os.path.basename(filepath) + ".fw_extracted"
            with open(out_name, 'wb') as out:
                out.write(data[offset:end_offset])
            print(f"     -> Extracted {end_offset - offset} bytes to {out_name}")
            print("     (Note: You may need to trim this file manually)")

    if not found:
        print("  [-] No obvious firmware signature found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dll_file>")
        sys.exit(1)
    
    for f in sys.argv[1:]:
        scan_file(f)