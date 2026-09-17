#!/usr/bin/env python3
import sys
import os
import struct

def scan_file(filepath):
    print(f"Scanning {filepath}...")
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"  ❌ File not found.")
        return

    # Multiple signature strategies
    signatures = [
        (b'GxFw', "GxFw firmware header"),
        (b'GXFW', "GXFW firmware header"),
        (b'\x00\xF0\x10\x00', "Chip ID response pattern"),
    ]
    
    found = False
    for sig, desc in signatures:
        offset = data.find(sig)
        if offset != -1:
            found = True
            print(f"  ✅ Found {desc} at offset 0x{offset:X}")
            
            # Heuristic: Firmware is usually between 32KB and 256KB
            fw_size = 256 * 1024 
            end_offset = min(offset + fw_size, len(data))
            
            out_name = os.path.basename(filepath) + ".fw_extracted"
            with open(out_name, 'wb') as out:
                out.write(data[offset:end_offset])
            print(f"     -> Extracted {end_offset - offset} bytes to {out_name}")
            print("     (Note: You may need to trim this file manually)")

    # If no signatures found, try entropy-based detection
    if not found:
        print("  [-] No obvious firmware signature found.")
        print("  [*] Attempting entropy-based firmware detection...")
        
        # Scan for high-entropy sections (likely firmware)
        chunk_size = 4096
        min_entropy = 7.0
        
        for i in range(0, len(data) - chunk_size, chunk_size):
            chunk = data[i:i + chunk_size]
            entropy = calculate_entropy(chunk)
            
            if entropy > min_entropy:
                print(f"  [*] Found high-entropy section at offset 0x{i:X} (entropy: {entropy:.2f})")
                
                # Try to extract a reasonable firmware size
                fw_size = 256 * 1024
                end_offset = min(i + fw_size, len(data))
                
                out_name = os.path.basename(filepath) + f"_entropy_0x{i:X}.bin"
                with open(out_name, 'wb') as out:
                    out.write(data[i:end_offset])
                print(f"     -> Extracted {end_offset - i} bytes to {out_name}")
                break

def calculate_entropy(data):
    """Calculate Shannon entropy of a byte sequence"""
    if not data:
        return 0
    
    byte_counts = {}
    for byte in data:
        byte_counts[byte] = byte_counts.get(byte, 0) + 1
    
    entropy = 0
    data_len = len(data)
    for count in byte_counts.values():
        p = count / data_len
        entropy -= p * (p ** 0.5)  # Simplified entropy calculation
    
    return entropy

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dll_file> [<dll_file> ...]")
        sys.exit(1)
    
    for f in sys.argv[1:]:
        scan_file(f)
