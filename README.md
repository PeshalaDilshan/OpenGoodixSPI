# OpenGoodixSPI

Open-source experimental Linux kernel driver for Goodix SPI fingerprint sensors.

## 🎯 Mission

Many Huawei laptops ship with Goodix SPI fingerprint sensors that work on Windows but lack proper Linux support. OpenGoodixSPI aims to:

- Develop a clean SPI-based Linux kernel driver
- Reverse engineer protocol communication safely
- Enable future integration with libfprint
- Create a structured path toward upstream support

This is a research-driven engineering project.

---

## 🧩 Current Status

- [x] **Device detection**: ACPI IDs `GXFP5187`, `GXFP3287`, `GXFP51A0` registered.
- [x] **SPI probe**: Driver loads, allocates resources, and communicates.
- [x] **Interrupt handling**: IRQ detected and handler registered.
- [x] **Debug Interface**: `debugfs` logging of raw SPI packets.
- [x] **User Space**: Character device `/dev/opengoodixspi` for read/write.
- [x] **Protocol Discovery**: Identified Wake (`0xB0`) and Chip ID (`0xF0`) commands.
- [x] **Driver Engine**: State machine implemented (Bootloader/Ready/Error).
- [x] **IOCTL Interface**: User-space control for state queries and resets.
- [ ] **Firmware Loading**: Driver requests `goodix_fp.bin`, upload logic is WIP.
- [ ] libfprint integration layer

---

## 🛠 Technical Stack

- Linux Kernel 6.x+
- SPI subsystem
- Character device interface
- ACPI / Device Tree matching
- C (kernel-space)

---

## 📦 Repository Structure

```

driver/                  # Kernel module source
docs/                    # Technical documentation
reverse-engineering/     # Protocol analysis notes
tools/                   # Debugging and logging tools
tests/                   # Experimental validation code

```

---

## 🕵️ Reverse Engineering Findings

### Protocol Basics
- **SPI Mode**: 0 (CPOL=0, CPHA=0)
- **Packet Structure**: Likely `CMD (1 byte) + ADDR/DATA...`

### Known Commands
| Command | Name | Description |
| :--- | :--- | :--- |
| `0xB0` | **Wake / CS** | Pulls MISO low (Active). Must be sent before other commands. |
| `0xF0` | **Chip ID** | Returns `00 F0 10 00` on some devices. |
| `0x0C` | **Soft Reset** | Resets the internal state machine. |

### Windows Driver Analysis
- **Driver Version**: `1.1.124.12` (Huawei / Goodix SPI)
- **Key DLLs**: `gfspi.dll`, `AlgoMilan.dll`
- **Firmware**: Likely embedded in `AlgoMilan.dll` or `.data` section of `gfspi.dll`.
- **Status**: The sensor appears to be in a bootloader state waiting for a firmware blob upload.

---

## 📦 Firmware Installation

The driver now expects a firmware file to be present.

1. **Extract**: Use `tools/find_firmware.py` on the Windows driver DLLs.
2. **Install**: Copy the extracted blob to the system firmware directory:
   ```bash
   sudo cp <extracted_firmware> /lib/firmware/goodix_fp.bin
   ```
3. **Reload**: `make load` (or `modprobe opengoodixspi`).

---

## 🔬 Next Steps for Contributors

1. **Extract Firmware**: Use `tools/find_firmware.py` on the Windows driver DLLs to locate the firmware blob.
2. **Implement Upload**: Reverse engineer the upload protocol (likely chunked writes to a specific address).
3. **Analyze Handshake**: Once firmware is loaded, the device should respond to more commands.

### Phase 4 – User Space Interface
- Expose character device
- Implement ioctl controls
- Prepare abstraction layer for libfprint

### Phase 5 – Upstream Strategy
- Code cleanup
- Locking and concurrency audit
- Prepare for kernel submission review

---

## 🧪 Testing & Debugging

To capture live traffic from the sensor, you need two terminal windows.

**Terminal 1: The Monitor** (Watches SPI traffic)
```bash
sudo python3 tools/live_monitor.py
```

**Terminal 2: The Trigger** (Waits for interrupts and reads data)
```bash
sudo python3 tools/trigger_read.py
```

Once both are running, touch the fingerprint sensor. You should see "Touch detected" in Terminal 2 and hex dumps in Terminal 1.

---

## 🛠 Reverse Engineering Tools

- `tools/live_monitor.py`: Real-time SPI traffic viewer (reads from debugfs).
- `tools/send_command.py`: Send raw hex bytes to the sensor.
- `tools/scan_commands.py`: Brute-force scan for valid command opcodes.
- `tools/scan_addresses.py`: Scan memory addresses for data.
- `tools/dump_chip_id.py`: Targeted script to read Chip ID (0xF0).
- `tools/deep_scan.py`: Fuzzing tool to find control registers.
- `tools/get_state.py`: Query driver state and force reset via IOCTL.
- `tools/find_firmware.py`: Scans Windows DLLs for embedded firmware blobs.

---

## ⚠️ Disclaimer

This project is not affiliated with Goodix or Huawei.

Fingerprint sensors may use encrypted communication or secure enclaves. Some devices may not be fully implementable without vendor cooperation.

---

## 🤝 Contributing

We welcome:

- Kernel developers
- Reverse engineers
- Embedded systems engineers
- Security researchers
- Testers with compatible hardware

Please read CONTRIBUTING.md before submitting pull requests.

---

## 📜 License

GPL-2.0 (required for kernel module compatibility)

---

## 📌 Target Hardware

Primarily Huawei MateBook series with Goodix SPI fingerprint sensors.

If you have compatible hardware, please open an issue and include:

- Laptop model
- Kernel version
- `dmesg` output
- SPI device ID

---

## 🔥 Vision

“A structured effort to bridge unsupported biometric hardware into the Linux ecosystem through open, maintainable kernel engineering.”
