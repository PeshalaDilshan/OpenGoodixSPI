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

Long-term goal: achieve stable upstream Linux support for unsupported Goodix SPI fingerprint devices.
```
