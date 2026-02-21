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

- [ ] Device detection
- [ ] SPI probe implementation
- [ ] Interrupt handling
- [ ] SPI transaction logging
- [ ] Protocol reverse engineering
- [ ] Character device interface
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

## 🔬 Development Roadmap

### Phase 1 – Hardware Detection
- Register SPI driver
- Confirm probe and remove functions
- Validate hardware communication

### Phase 2 – Communication Layer
- Implement spi_sync transactions
- Log raw SPI packets
- Identify handshake patterns

### Phase 3 – Protocol Analysis
- Map packet structure
- Identify command types
- Reverse engineer authentication flow

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

- `tools/live_monitor.py`: Real-time SPI traffic viewer.
- `tools/send_command.py`: Send raw hex bytes to the sensor.
- `tools/scan_commands.py`: Brute-force scan for valid command opcodes.
- `tools/scan_addresses.py`: Scan memory addresses for data.
- `tools/dump_chip_id.py`: Targeted script to read Chip ID (0xF0).
- `tools/deep_scan.py`: Fuzzing tool to find control registers.
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

Primarily Huawei laptops with Goodix SPI fingerprint sensors.

If you have compatible hardware, please open an issue and include:

- Laptop model
- Kernel version
- `dmesg` output
- SPI device ID

---

## 🔥 Vision

“A structured effort to bridge unsupported biometric hardware into the Linux ecosystem through open, maintainable kernel engineering.”
