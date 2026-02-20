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
