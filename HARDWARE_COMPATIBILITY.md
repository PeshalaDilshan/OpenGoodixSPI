# Hardware Compatibility Guide

## ⚠️ Critical Hardware Differences

Not all Goodix fingerprint sensors use the same communication protocol. This document explains the different hardware architectures and their Linux support status.

---

## 🔴 GXFP51B7 (MateBook X Pro 2020) - NOT SUPPORTED

### Hardware Architecture

The GXFP51B7 sensor found in Huawei MateBook X Pro 2020 (MACHC-*) is **NOT an SPI device**. It uses a completely different architecture:

```
Host CPU ←→ EC Shared Memory (MMIO @0x40200000) ←→ EC MCU ←→ SPI ←→ Goodix Sensor
           ↑                                        ↑
           └──────── ACPI Platform Device ──────────┘
```

### ACPI Configuration

From SSDT11:
```asl
Device (SPBA)  // GXFP51B7
{
    Name (_HID, "GXFP51B7")
    Name (_CRS, ResourceTemplate () {
        Memory32Fixed (ReadWrite, 0x00000000, 0x00008000)  // Patched to 0x40200000
        GpioInt (Level, ActiveLow, ExclusiveAndWake, "\\_SB.PCI0.GPI0") { ... }
        GpioIo  (Exclusive, PullUp, IoRestrictionOutputOnly, "\\_SB.PCI0.GPI0") { ... }
    })
    // NO SpiSerialBus resource!
}
```

**Key observations:**
- Uses `Memory32Fixed` (32KB MMIO window) instead of `SpiSerialBus`
- Has GpioInt for interrupts and GpioIo for reset/attn lines
- Requires **platform driver**, not `spi_driver`
- Linux binds it as `GXFP51B7:00` platform device

### Communication Protocol

#### Layer A: EC Mailbox Transport ✅ WORKING

The host communicates with the Embedded Controller (EC) through a shared memory mailbox:

- **Base Address**: 0x40200000 (32KB window)
- **Host→EC Ring**: Offset 0x0000
- **EC→Host Ring**: Offset 0x001000
- **Doorbell**: `_DSM` function 2 → `HWEC.ECMD(0xF0)`
- **Interrupt**: GpioInt signals response availability

**Packet Format** (verified on real hardware):
```
Offset  Field
[0]     0xA0                          // Frame marker (high nibble 0xA)
[1..2]  total_len - 4 (LE16)          // Prefix length
[3]     [0] + hi([1..2]) + lo([1..2]) // Header checksum
[4]     (cmd0 << 4) | (cmd1 << 1)     // PACKED command byte
[5..6]  payload_len + 1 (LE16)
[7..]   payload
[plen+7] 0xAA - (packed + Σpayload)   // Data checksum (or 0x88 = no checksum)
```

**Command Table** (cmd0):
- `0x0` NOP
- `0x2` Ima (image capture)
- `0x3` FDT (firmware download/upload) ⚠️ DANGER - can brick device
- `0x9` CHIP (chip ID)
- `0xD` TLSCONN (TLS tunnel)
- `0xE` PROD (production/provisioning)
- `0xF` UPFW (firmware update) ⚠️ DANGER - can brick device

**Verified Transaction**:
```
Request  @0x0000: a0 04 00 a4 90 01 00 19  // CHIP-ID command
Response @0x1000: a0 07 00 a7 b0 04 00 90 e0 e1 a5  // Chip ID = 0xE1E0
```

#### Layer B: TLS-PSK Encryption ❌ BLOCKED

After establishing mailbox communication, all further communication is tunneled through TLS-PSK:

- **Protocol**: TLS 1.2 PSK (`TLS-PSK-WITH-AES-128-CBC-SHA256`)
- **Host Role**: TLS server
- **MCU Role**: TLS client with identity `"Client_identity"`
- **Transport**: Mailbox command `0xD TLSCONN`

**The Blocker**: The PSK (Pre-Shared Key) is protected by multiple layers:

1. **SGX Sealing**: PSK stored as `sgx_sealed_data_t` blob
   - `key_name = SGX_KEYSELECT_SEAL` (CPU-bound seal key)
   - `key_policy = MRSIGNER` (enclave-specific)
   - 32-byte per-device `key_id`
   - Cannot be extracted without running Goodix-signed enclave on same CPU

2. **RSA-Signed Provisioning**: Setting/changing PSK requires:
   - AES-encrypted blob
   - RSA-2048 signature from Goodix factory private key
   - No trust-on-first-use window

3. **Enclave Dependency**: Windows driver uses `WBDI_Enclave.signed.dll`
   - Windows PE format (not compatible with Linux SGX)
   - Signed with Goodix MRSIGNER key (cannot reproduce)

### Why Linux Support Is Not Feasible

| Goal | Blocked By | Missing Secret |
| :--- | :--- | :--- |
| Read existing PSK | SGX sealing | CPU seal key + Goodix enclave |
| Set/clear PSK | AES + RSA-2048 signing | Goodix factory RSA private key |
| Set trust anchor | RSA-2048 signing | Goodix factory RSA private key |

**Comparison with USB Goodix sensors**:
- USB parts (27c6:51x7/5503) have trust-on-first-use hole
- They accept hardcoded all-zeros PSK via `preset_psk_write()`
- Milan GXFP51B7 has **no TOFU path** - all security parameters are signature-gated

### Conclusion

A full libfprint backend for GXFP51B7 is **not achievable** without secrets held only by Intel (SGX seal keys) and Goodix (RSA signing keys). The only theoretical path would require:

1. Proving the MCU doesn't enforce RSA checks (high risk of permanent bricking)
2. Defeating the AES/white-box encryption layer
3. Re-pairing with custom keys

This is documented but **not recommended**.

---

## 🟢 Supported SPI Devices

### Compatible ACPI IDs

The OpenGoodixSPI driver supports these SPI-based Goodix sensors:

- `GXFP5187`
- `GXFP3287`
- `GXFP51A0`
- Similar SPI variants

### Hardware Characteristics

These devices use direct SPI communication:

```
Host CPU ←→ SPI Controller ←→ Goodix Sensor (SPI slave)
            ↑
            └── ACPI SPI SerialBus Resource
```

**ACPI Configuration**:
```asl
Device (FPSI)
{
    Name (_HID, "GXFP5187")  // or similar
    Name (_CRS, ResourceTemplate () {
        SpiSerialBus (0, PolarityLow, FirstEdge, 8-bit, 10MHz, ...)
        GpioInt (...)
    })
}
```

**Key differences from GXFP51B7**:
- Uses `SpiSerialBus` resource (binds to `spi_driver`)
- Direct SPI communication (no EC mailbox)
- No SGX-sealed keys (may have simpler security model)
- Protocol reverse engineering in progress

---

## 📋 How to Identify Your Device

### Step 1: Check ACPI Devices

```bash
cat /sys/bus/acpi/devices/*/modalias | grep GXFP
```

Expected output examples:
- `acpi:GXFP51B7` → **NOT SUPPORTED** (EC mailbox)
- `acpi:GXFP5187` → May be supported (SPI)
- `acpi:GXFP3287` → May be supported (SPI)

### Step 2: Check Device Resources

```bash
# Find your device
ls /sys/bus/acpi/devices/ | grep GXFP

# Check resources (replace with your device path)
cat /sys/bus/acpi/devices/GXFP51B7:00/resources
```

Look for:
- `Memory32Fixed` → EC mailbox (NOT SUPPORTED)
- `SpiSerialBus` → SPI device (MAY BE SUPPORTED)

### Step 3: Check dmesg

```bash
dmesg | grep -i goodix
dmesg | grep -i gxfp
```

### Step 4: Check lsusb

If you see a Goodix USB device:
```bash
lsusb | grep -i goodix
# Example: 27c6:5117 Goodix Fingerprint Sensor
```

USB devices are handled by separate drivers (libfprint-goodixtls), not this SPI driver.

---

## 🎯 Summary Table

| Device ID | Laptop Model | Bus Type | Driver | Status |
| :--- | :--- | :--- | :--- | :--- |
| GXFP51B7 | MateBook X Pro 2020 | EC Mailbox (MMIO) | None | ❌ Blocked (SGX + RSA) |
| GXFP5187 | Various MateBooks | SPI | OpenGoodixSPI | 🟡 In Development |
| GXFP3287 | Various MateBooks | SPI | OpenGoodixSPI | 🟡 In Development |
| GXFP51A0 | Various MateBooks | SPI | OpenGoodixSPI | 🟡 In Development |
| 27c6:5117 | MateBook 13 2021+ | USB | libfprint-goodixtls | ✅ Working |
| 27c6:5503 | Various | USB | libfprint-goodixtls | ✅ Working |

---

## 📚 References

- [Issue #16](https://github.com/PeshalaDilshan/OpenGoodixSPI/issues/16) - Complete GXFP51B7 protocol analysis
- [libfprint #112](https://gitlab.freedesktop.org/libfprint/libfprint/-/issues/112) - SPI Goodix discussion (2020)
- [libfprint-goodixtls](https://github.com/goodix-fp-linux-dev/libfprint-goodixtls) - USB Goodix driver

---

*Last updated: July 2026*
