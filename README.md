# OpenGoodixSPI

This project is an experimental, open-source Linux kernel driver for Goodix SPI fingerprint sensors found in many Huawei MateBooks and other laptops.

**The original author has postponed development. The codebase is stable, compiles, and loads, but requires specific protocol reverse-engineering to become functional. We welcome any contributors to pick up the torch!**

## 🎯 Mission

Many Huawei laptops ship with Goodix SPI fingerprint sensors that work on Windows but lack proper Linux support. OpenGoodixSPI aims to:

- Develop a clean SPI-based Linux kernel driver
- Reverse engineer protocol communication safely
- Enable future integration with libfprint
- Create a structured path toward upstream support

This is a research-driven engineering project.

---

## 🧩 Current Technical Status

- [x] **Device detection**: ACPI IDs `GXFP5187`, `GXFP3287`, `GXFP51A0` registered.
- [x] **SPI probe**: Driver loads, allocates resources, and communicates.
- [x] **Interrupt handling**: IRQ detected and handler registered.
- [x] **Debug Interface**: `debugfs` logging of raw SPI packets.
- [x] **User Space**: Character device `/dev/opengoodixspi` for read/write.
- [x] **Protocol Discovery**: Identified Wake (`0xB0`) and Chip ID (`0xF0`) commands.
- [x] **Driver Engine**: State machine implemented (Bootloader/Ready/Error).
- [x] **IOCTL Interface**: User-space control for state queries and resets.
- [ ] **Firmware Loading**: Skeleton implemented. Needs protocol headers from `analyze_log.py`.
- [ ] libfprint integration layer

### ✅ What Works
- **Device Detection**: ACPI IDs `GXFP5187`, `GXFP3287`, `GXFP51A0` are registered.
- **SPI Subsystem**: Driver loads, probes, and establishes SPI communication (Mode 0).
- **Interrupts**: IRQ handler is registered and fires on sensor touch.
- **Character Device**: `/dev/opengoodixspi` exists for user-space interaction.
- **Debug Interface**: `/sys/kernel/debug/opengoodixspi/spi_log` provides real-time traffic logging.
- **IOCTLs**: Custom IOCTLs implemented to query driver state and force resets.
- **Firmware Request**: The driver requests `goodix_fp.bin` from `/lib/firmware`.

### ❌ What is Missing
- **Firmware Upload Logic**: The driver loads the binary into memory but does not know *how* to send it to the chip (chunk headers, commands, checksums).
- **Image Capture**: Once initialized, logic to read the fingerprint image is needed.

---

## 🛠️ Getting Started

### 1. Prerequisites
- Linux Kernel 6.x+
- GCC and Make
- Secure Boot disabled (or you must sign the module manually)

### 2. Build and Load
```bash
cd driver
make
# If you have your own signing keys setup:
# make sign
sudo make load
```

### 3. Install Firmware
The driver requires the proprietary firmware from the Windows driver.
1.  Locate the Windows driver files (usually `C:\Windows\System32\DriverStore\FileRepository\...\gfspi.dll` or `AlgoMilan.dll`).
2.  Use the extraction tool:
    ```bash
    python3 tools/find_firmware.py <path_to_dll>
    ```
3.  Copy the extracted file (usually ~128KB) to the system path:
    ```bash
    sudo cp <extracted_file> /lib/firmware/goodix_fp.bin
    ```
4.  Reload the driver:
    ```bash
    sudo rmmod opengoodixspi
    sudo insmod opengoodixspi.ko
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

## 🕵️ How to Contribute (The "Missing Link")

The immediate goal is to implement the **Firmware Upload Protocol**.

### Step 1: Capture Windows Traffic
You need a traffic log of the sensor initializing on Windows.
- **Option A**: Use a hardware logic analyzer on the SPI lines (Best).
- **Option B**: Use Wireshark with USBPcap if the SPI controller is USB-attached (Rare for these sensors).
- **Option C**: Use a software filter driver on Windows (Advanced).

---

## 🕵️ Protocol Analysis Workflow

To implement the firmware upload, we need to find the specific command headers used by the Windows driver.

1. **Capture**: Obtain a traffic log from Windows (Wireshark USB capture or Logic Analyzer).
2. **Analyze**: Run the analyzer tool:
   ```bash
   python3 tools/analyze_log.py <path_to_log.txt> <path_to_firmware.bin>
   ```
3. **Implement**: The tool will identify the header bytes (e.g., `F1 00 ...`). Use these to fill the `TODO` section in `driver/opengoodixspi.c`.

## 🔬 Next Steps for Contributors

1. **Extract Firmware**: Use `tools/find_firmware.py` on the Windows driver DLLs to locate the firmware blob.
2. **Analyze Protocol**: Use `tools/analyze_log.py` with a Windows traffic log to identify the firmware upload headers.
3. **Implement Upload**: Update `opengoodix_load_firmware` in the driver to send the firmware in chunks.
4. **Analyze Handshake**: Once firmware is loaded, the device should respond to more commands.

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
python3 tools/analyze_log.py <windows_log.txt> <extracted_firmware.bin>
```
*Output Example:*
```text
✅ Match at FW Offset 0x0000
   Log Offset: 0x001040
   Header: F1 00 00 00  <-- THIS IS WHAT WE NEED
```

### Step 3: Update the Driver
Open `driver/opengoodixspi.c` and find `opengoodix_load_firmware`.
Update the `TODO` section with the header format you found.

```c
/* Example: If header is F1 <AddrH> <AddrL> 00 */
tx[0] = 0xF1;
tx[1] = (offset >> 8) & 0xFF;
tx[2] = offset & 0xFF;
tx[3] = 0x00;
memcpy(&tx[4], fw->data + offset, payload_len);
```

Once both are running, touch the fingerprint sensor. You should see "Touch detected" in Terminal 2 and hex dumps in Terminal 1.

---

## 🛠 Reverse Engineering Tools

The `tools/` directory contains Python scripts to aid reverse engineering:

| Tool | Description |
| :--- | :--- |
| `live_monitor.py` | Reads `/sys/kernel/debug/.../spi_log` to show live traffic. |
| `get_state.py` | Uses IOCTL to check if driver is in `BOOTLOADER` or `READY` state. |
| `find_firmware.py` | Scans Windows DLLs for "GxFw" signatures. |
| `analyze_log.py` | Finds firmware chunks in traffic logs to deduce protocol. |
| `send_command.py` | Sends raw hex bytes to the device via `/dev/opengoodixspi`. |
| `scan_addresses.py` | Brute-forces read commands to find valid registers. |

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
