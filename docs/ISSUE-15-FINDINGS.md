# Issue #15 — GXFP51A0 findings update

This document records the September 2026 findings from Windows-side reverse engineering of the `GXFP51A0` integration, especially the MateBook 13 2020/2021 reports in Issue #15.

## Confirmed integration details

- The ACPI `_CRS` resource order observed on the affected machines is **GpioInt at index 0, GpioIo/reset at index 1**.
- The reset GPIO therefore needs an ACPI driver mapping before the kernel GPIO consumer API can acquire it by name.
- A reset pulse of **LOW for 10 ms, then HIGH for 100 ms** was observed to make the reset line/IRQ path behave differently, but this does **not** by itself establish that the sensor is fully initialized.
- After reset acquisition, the remaining failure is **MISO = `0xff`**; the wake/bootloader handshake is still unresolved.
- The Windows-side investigation identifies `0x2504` as the chip identifier and sensor type 12 (`ChicagoHS`), with 80x64 geometry. The reported firmware is `GF_ST411SEC_APP_14115` on the STM32 path.

## Important protocol correction

The old driver documentation treated `0xF0` as a chip-ID command. The newer Windows reverse-engineering results indicate that command byte `0xF` is associated with firmware upgrade operations, while chip/register identification is reached through the `0x8` register-read path (`0x82` in the observed command form).

Until the complete transaction framing/checksum/response semantics are independently verified, this repository should **not** treat the old `0xF0` probe as a reliable chip-ID transaction.

## Firmware handling

The Windows driver was observed to report that the installed firmware is already the same version and does not need an update on the affected `GXFP51A0` hardware. The firmware images are embedded in the Windows driver, but their presence does not prove that Linux should automatically upload them.

The current Linux driver contains a speculative firmware-upload path. That path is not considered validated by these findings and must not be treated as a confirmed initialization sequence.

## What remains unresolved

The critical blocker is still the **wake/bootloader sequence** after reset. The fact that the IRQ fires after the reset GPIO is correctly acquired is useful evidence, but it is not evidence that the sensor has entered the application protocol.

Do not infer that `0xff` means "waiting for firmware" solely from the response. The Windows evidence indicates that the affected sensor can already contain the expected firmware image.

## Cross-project references

The Issue #15 discussion references independent Windows/Linux reverse-engineering work and a working Linux implementation for the same `0x2504`/sensor-type-12 silicon. Those external projects should be treated as evidence to compare against, not as proof that every board-level ACPI integration is identical.

## Testing direction

The next useful experiments should focus on reproducing the Windows initialization transaction after the GPIO reset has been asserted, rather than repeating generic SPI clock/mode/CS experiments that have already produced `0xff`.

No claim of a fully working Linux driver is made by this document.