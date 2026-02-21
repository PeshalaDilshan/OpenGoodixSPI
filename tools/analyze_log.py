#!/usr/bin/env python3
import sys
import os
import re

def clean_hex(text):
    """
    Removes timestamps, ASCII, and other noise, returning a pure bytes object.
    Assumes the log contains hex strings like 'AA BB CC' or '0xAA, 0xBB'.
    """
    # Find all hex-like patterns (2 chars 0-9, a-f)
    hex_chars = re.findall(r'[0-9a-fA-F]{2}', text)
    return bytes.fromhex(''.join(hex_chars))

def analyze(log_path, fw_path):
    print(f"🔹 Loading Firmware: {fw_path}")
    with open(fw_path, 'rb') as f:
        fw_data = f.read()

    print(f"🔹 Loading Log: {log_path}")
    # Read log as text, then convert to binary stream
    try:
        with open(log_path, 'r', errors='ignore') as f:
            log_text = f.read()
            log_data = clean_hex(log_text)
    except Exception as e:
        print(f"❌ Failed to read log: {e}")
        return

    print(f"   Log size (parsed bytes): {len(log_data)}")
    print(f"   Firmware size: {len(fw_data)}")
    print("-" * 60)

    # Strategy: Take chunks of firmware and find them in the log
    chunk_size = 32  # Bytes to match to be sure
    search_step = 128 # How often to check (guess common packet sizes: 64, 128, 256, 4096)
    
    found_packets = []

    for fw_offset in range(0, len(fw_data) - chunk_size, search_step):
        # Get a snippet of firmware
        snippet = fw_data[fw_offset : fw_offset + chunk_size]
        
        # Find it in the log
        log_offset = log_data.find(snippet)
        
        if log_offset != -1:
            # Look at bytes BEFORE the data (The Header)
            header_len = 8
            start = max(0, log_offset - header_len)
            header = log_data[start : log_offset]
            
            found_packets.append({
                'fw_offset': fw_offset,
                'log_offset': log_offset,
                'header': header
            })
            
            # Print the first few matches to help the user spot the pattern
            if len(found_packets) <= 5:
                print(f"✅ Match at FW Offset 0x{fw_offset:04X}")
                print(f"   Log Offset: 0x{log_offset:06X}")
                print(f"   Header (Preceding bytes): {header.hex(' ')}")
                print(f"   Data Start: {snippet[:8].hex(' ')} ...")
                print("")

    if not found_packets:
        print("❌ No firmware chunks found in the log.")
        print("   - Check if the log is decrypted (if USB).")
        print("   - Check if the firmware file is correct.")
        return

    # Analyze the pattern
    print("-" * 60)
    print("📊 Analysis Results")
    
    if len(found_packets) > 1:
        # Calculate distance between log matches vs firmware offsets
        fw_diff = found_packets[1]['fw_offset'] - found_packets[0]['fw_offset']
        log_diff = found_packets[1]['log_offset'] - found_packets[0]['log_offset']
        overhead = log_diff - fw_diff
        
        print(f"   Detected Chunk Size: {fw_diff} bytes (Estimated)")
        print(f"   Detected Packet Overhead: {overhead} bytes (Header + Checksum?)")
        print(f"   Likely Header: {found_packets[0]['header'][-overhead:].hex(' ')} (Last {overhead} bytes)")
    else:
        print("   Not enough matches to calculate packet structure.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <log_file.txt> <firmware.bin>")
        sys.exit(1)
    analyze(sys.argv[1], sys.argv[2])