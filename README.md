# OpenGoodixSPI

This project is an experimental, open-source Linux kernel driver for Goodix fingerprint sensors found in many Huawei MateBooks and other laptops.

**⚠️ IMPORTANT HARDWARE COMPATIBILITY NOTICE (July 2026)**

Recent reverse engineering has revealed **critical hardware differences** between Goodix sensor variants:

### 🔴 GXFP51B7 (MateBook X Pro 2020) - NOT SUPPORTED
- **This is NOT an SPI device** - it's an ACPI platform device with EC-bridged MMIO mailbox
- Requires a **platform driver**, not `spi_driver`
- Uses TLS-PSK encryption with SGX-sealed keys (per-device, CPU-bound)
- Full authentication is **not achievable on Linux** without vendor cooperation
- See Issue #16 for complete protocol analysis and why this hardware is blocked

### 🟢 Supported Devices (SPI-based)
- GXFP5187, GXFP3287, GXFP51A0 and similar SPI variants
- These devices use direct SPI communication (Mode 0)
- This driver targets these SPI-based sensors only

**The original author has postponed development. The codebase is stable, compiles, and loads, but requires specific protocol reverse-engineering to become functional. We welcome any contributors to pick up the torch!**

## 🎯 Mission

Many Huawei laptops ship with Goodix fingerprint sensors that work on Windows but lack proper Linux support. OpenGoodixSPI aims to:

- Develop a clean Linux kernel driver for **SPI-based** Goodix sensors
- Reverse engineer protocol communication safely
- Enable future integration with libfprint
- Create a structured path toward upstream support

This is a research-driven engineering project.

---

## 🧩 Current Technical Status

### ✅ What Works
- [x] **Device Detection**: ACPI IDs `GXFP5187`, `GXFP3287`, `GXFP51A0` are registered.
- [x] **SPI Subsystem**: Driver loads, probes, and establishes SPI communication (Mode 0).
- [x] **Interrupt handling**: IRQ handler is registered and fires on sensor touch.
- [x] **Debug Interface**: `/sys/kernel/debug/opengoodixspi/spi_log` provides real-time traffic logging.
- [x] **Character Device**: `/dev/opengoodixspi` exists for user-space interaction.
- [x] **Protocol Discovery**: Identified Wake (`0xB0`) and Chip ID (`0xF0`) commands.
- [x] **Driver Engine**: State machine implemented (Bootloader/Ready/Error).
- [x] **IOCTL Interface**: Custom IOCTLs implemented to query driver state and force resets.
- [x] **Firmware Request**: The driver requests `goodix_fp.bin` from `/lib/firmware`.

### ❌ What is Missing
- [ ] **libfprint integration layer**
- [ ] **Image Capture**: Once initialized, logic to read the fingerprint image is needed.
- [ ] **Firmware Loading**: Skeleton implemented. Needs protocol headers from `analyze_log.py`.
- [ ] **Firmware Upload Logic**: The driver loads the binary into memory but does not know *how* to send it to the chip (chunk headers, commands, checksums).

### ⚠️ Known Hardware Limitations

| Device | Laptop Model | Bus Type | Status |
| :--- | :--- | :--- | :--- |
| GXFP5187/3287/51A0 | Various MateBooks | SPI | ✅ Supported (this driver) |
| **GXFP51B7** | **MateBook X Pro 2020** | **EC Mailbox (MMIO)** | ❌ **Not supported - different hardware architecture** |
| 27c6:51x7/5503 | MateBook 13 2021+ | USB | ✅ Works via existing USB drivers |

**Why GXFP51B7 cannot use this driver:**
- No `SpiSerialBus` resource in ACPI - uses Memory32Fixed + GpioInt instead
- Communicates through EC shared memory mailbox at 0x40200000
- Requires platform driver binding, not spi_driver
- Even with correct driver, TLS-PSK authentication is blocked by SGX sealing

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

---

## 📚 References & Research

### GXFP51B7 Protocol Analysis (Issue #16)

Complete reverse engineering of the GXFP51B7 sensor in MateBook X Pro 2020:

- **Hardware Architecture**: EC-bridged MMIO mailbox at 0x40200000 (32KB window)
- **Transport Layer**: Host → EC shared memory → EC → SPI → Goodix MCU
- **Command Protocol**: Fully documented packet format with checksums
- **Security Blocker**: TLS-PSK with SGX-sealed keys (per-device, CPU-bound)
- **Authentication**: Requires RSA-2048 signed provisioning blobs from Goodix

**Key Findings:**
1. The sensor is **not an SPI slave** - it's a platform device requiring ACPI binding
2. Layer A (mailbox transport) works - CHIP-ID command returns 0xE1E0
3. Layer B (TLS-PSK) is blocked - PSK sealed to Intel SGX enclave
4. No trust-on-first-use hole (unlike USB Goodix parts)
5. Provisioning requires Goodix factory RSA private key

See [Issue #16](https://github.com/PeshalaDilshan/OpenGoodixSPI/issues/16) for complete technical analysis.

### Related Projects

- **libfprint #112**: SPI Goodix protocol discussion (2020)
- **libfprint-goodixtls**: Working driver for USB Goodix sensors
- **goodix-fp-linux-dev**: USB Goodix reverse engineering tools

---
