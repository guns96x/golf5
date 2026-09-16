# MPPS V18 clone USB transport analysis

Date: 2026-09-11

Scope: VID `1C43`, PID `0500`, product `Amt Flash`, bulk OUT `0x02`, bulk IN `0x81`, 64-byte max packet, C8051F320-based clone. This establishes the adapter handshake and the boundary before ECU-specific flashing. It does **not** certify a write procedure or the supplied calibration.

## Conclusions

1. A two-byte bulk-IN transfer such as `01 10` or `01 60` is a valid FTDI-compatible **status-only packet**. It proves that endpoint `0x81` is alive but that the device queued no data payload. FTDI-compatible IN packets reserve the first two bytes for modem and line status; in the absence of data, the device may return only those bytes. [Linux FTDI protocol definitions](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/ftdi_sio.h#L2254-L2341)
2. There is no evidenced fixed "FTDI-to-C8051 UART baud." The C8051F320 itself contains a full-speed USB function controller/transceiver and can implement endpoints `0x81` and `0x02` directly. [Silicon Labs C8051F32x data sheet, USB0](https://www.silabs.com/documents/public/data-sheets/C8051F32x.pdf) The local `AmtFlash.sys` also contains the original build path `...FTDIBUS.pdb`, consistent with a host-side FTDI-compatible driver, not proof of a separate FTDI IC.
3. The open-source `amtflash` reference performs only USB reset and latency configuration before its proprietary handshake. It does not call SetBaudRate before that handshake. [ftdibus.py lines 39-62](https://github.com/endes0/amtflash/blob/main/src/amtflash/ftdibus.py#L39-L62) Baud request `0x03` is exposed later through the KWP interface and is therefore vehicle-side serial configuration, not an adapter-link baud. [ftdibus.py lines 169-182](https://github.com/endes0/amtflash/blob/main/src/amtflash/ftdibus.py#L169-L182)
4. The published reference accepts `read(0x1000)[0] == 0x33` only. It does **not** document `0x55` as "already unlocked" and does not contain a branch that skips authentication for `0x55`. [amt.py lines 15-45](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L15-L45)
5. Request `0x91`, `wIndex=0x5001`, zero data length is part of the demonstrated post-challenge sequence. Request `0x92` is the conventional FTDI EEPROM-erase request, not a wake command, and must not be tried on a working adapter. [OpenOCD FT232R request definitions](https://github.com/openocd-org/openocd/blob/master/src/jtag/drivers/ft232r.c)
6. The custom Windows driver GUID and IOCTLs are host APIs which ultimately construct USB URBs. Android talking directly to the USB device does not need the Windows GUID or a Windows IOCTL. The local driver's signed binary is a customized FTDIBUS-derived WDM driver; no evidence was found for a separate MPPS-specific wake IOCTL.
7. `amtflash.read(2)` does **not** submit a two-byte USB IN request. Its low-level implementation always requests 4096 bytes and then removes the two FTDI status bytes before counting logical payload. An Android `bulkTransfer()` whose receive buffer is only two bytes cannot faithfully receive a packet containing the two-byte status header plus challenge payload; status-only or overflow/truncation behavior is not a valid challenge test. [ftdibus.py lines 91-130](https://github.com/endes0/amtflash/blob/main/src/amtflash/ftdibus.py#L91-L130)
8. The reference `_purge()` is a drain loop made from bulk IN reads. It is **not** another vendor reset/purge control request after reading `0x2000`. Resetting the SIO/parser after obtaining session masks is an unverified ordering change and may invalidate the masks/state just obtained. [amt.py lines 47-50](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L47-L50)

## Why the commands are silent

First distinguish a host receive-length bug from a silent parser. If the Android IN request length is `2`, it has not actually tested for the two-byte challenge: request at least one complete 64-byte endpoint packet. Only if `actualLength == 2` with a receive buffer of at least 64 bytes is the result genuinely status-only.

After that distinction, the strongest supported diagnosis is that the bulk command parser has not reached the authenticated/armed state expected by the reference protocol. `0x22`, `0x25`, and `0x30` are post-handshake commands. Skipping the complete `0x21` challenge/response and `0x26` final phase leaves no published path under which they should answer.

Calling SetBaudRate before authentication is unnecessary and should be removed from the minimal reproduction, but it does not explain why the USB command parser itself cannot answer `0x22`: the reference initializes and authenticates before configuring KWP baud.

`0x55 00` at pseudo-register `0x1000` is the unresolved discriminator. For this exact V18 clone it could mean a different firmware generation, a locked/failed clone state, or some state not covered by the V13-oriented open-source code. Calling it "unlocked" is not supported by the available source. Likewise, replacing the challenge transform constant `0x33` with `0x55` is only a guess. That transform is used *after* the first challenge is received, so it cannot explain why the initial logical `21 55` produces no payload. A USB power cycle followed by a clean trace is needed to distinguish those cases.

The same caution applies to `0x6000 = 00 01`. The published `get_usages()` returns byte 0 only, so that implementation would report `0`, not big-endian `1`. The V18 meaning of the second byte is undocumented. [amt.py lines 61-63](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L61-L63)

## Demonstrated adapter initialization (only when `0x1000` starts with `0x33`)

All control requests use recipient `DEVICE`, vendor type. All bulk command bytes are XORed with the TX mask; all bulk payload bytes, after status removal, are XORed with the RX mask.

1. Select configuration 1, claim interface 0, alternate setting 0. Locate endpoints by direction/type rather than descriptor array order.
2. `40 00`, `wValue=0000`, `wIndex=0000`, zero length: FTDI-compatible SIO reset.
3. `40 09`, `wValue=0001`, `wIndex=0000`, zero length: latency timer 1 ms.
4. `C0 90`, `wValue=0000`, `wIndex=1000`, `wLength=2`. Require first byte `33` for the published protocol.
5. `C0 90`, `wValue=0000`, `wIndex=2000`, `wLength=2`. Assign `txMask = byte[0]`, `rxMask = byte[1]`.
6. Drain only stale payload by submitting 64-byte (or larger) bulk IN reads. Do not send another SIO reset/purge control request here. For every USB packet, discard its two status bytes. Do not mistake a status-only packet for one byte of payload.
7. Send logical `21 55`; on this observed unit with `txMask=8D`, wire bytes are `AC D8`.
8. Read exactly two logical challenge bytes: strip status bytes first, then XOR each payload byte with `rxMask` (`36` on this unit). Let the result be `c0 c1`.
9. Compute `r0 = c0 XOR FF XOR 33 = c0 XOR CC`, `r1 = c1 XOR CC`.
10. Send logical `21 56 r0 r1`, with the TX mask applied to every byte. Read one logical byte and require `33`.
11. Send `40 91`, `wValue=0000`, `wIndex=5001`, zero length.
12. Drain stale payload again.
13. Send logical `26 00 01 00 00`, TX-masked. Read one logical byte and require `55` (`'U'`).
14. Only now send logical `22` (wire `AF` for TX mask `8D`). The first logical response byte is a string length, followed by that many logical bytes.

The source for masking, status stripping, and the handshake is [ftdibus.py lines 64-148](https://github.com/endes0/amtflash/blob/main/src/amtflash/ftdibus.py#L64-L148) and [amt.py lines 15-45](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L15-L45).

### Android receive rule

For a full-speed 64-byte endpoint, strip bytes 0 and 1 from **each USB packet**, not merely once from an arbitrarily large Java buffer. For short replies a transfer of length 64 is simplest. Never size the physical USB request to the expected logical payload length. Treat `actualLength == 2` as zero payload and continue until the command timeout. Check line errors in status byte 1 separately; the reference treats bits selected by mask `0x8E` as errors.

`01 10` also does not mean CTS high. In the documented IN header, byte 0 is modem status: `01` has only the mandatory reserved bit and CTS (`0x10`) is clear. Byte 1 is line status: `10` means Break Interrupt. [Linux FTDI IN format](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/ftdi_sio.h#L2254-L2341)

## What to do with `0x55 00`

Do not skip directly to version/KWP/CAN commands and do not issue `0x92`.

1. Physically power-cycle the adapter (disconnect USB and OBD power), wait several seconds, reconnect with no MPPS PC process attached.
2. Perform only reset `0x00`, latency `0x09`, then read `0x1000` and `0x2000`. Do not set baud, DTR, RTS, bit mode, or send bulk data before recording those reads.
   Read both `0x2000` bytes in one control transfer; byte 0 is the OUT/TX XOR mask and byte 1 is the IN/RX XOR mask in the published implementation. Do not reuse one byte for both directions.
3. If `0x1000` is `33 xx`, run the demonstrated handshake above exactly.
4. If it is still `55 00`, stop treating the V13 reference as exact for this firmware. Capture a successful V18 Windows session from USB enumeration through the first version response with USBPcap/Wireshark, or obtain the C8051 firmware and reverse the state machine. The decisive trace must include control setup packets, raw OUT bytes, raw IN bytes, timestamps, and 64-byte boundaries.

Trying the `0x21` exchange anyway while the discriminator is `0x55` is an experiment, not a known reset/re-arm procedure. It is safe only as a read-only transport probe if no ECU write session is active, but its outcome cannot be predicted from the available source.

## Vehicle-side communication after adapter handshake

### K-line fast-init path

1. Configure 10400 baud with vendor request `0x03` using the FTDI divisor encoding used by the reference. With its 3 MHz base, 10400 calculates to `wValue=0x4120`, `wIndex=0` (about 10398.6 baud).
2. Configure 8 data bits, no parity, one stop bit, break off: request `0x04`, `wValue=0x0008`, `wIndex=0`.
3. Send logical adapter command `25 01 05 00 19 81 01 F1 81 F4`, TX-masked. Its format is command/subcommand, one-byte data length, inter-byte delay, init-pulse delay, then KWP bytes. The open-source source labels this function untested. [amt.py lines 197-207](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L197-L207)
4. Read and unmask the resulting KWP traffic. Do not attempt this before the adapter handshake returns `U`.

### CAN/TP2.0 path

The demonstrated adapter command order is:

1. logical `30 01` (reset SJA1000), expect logical `55`;
2. logical `30 10 ...setup fields...`, expect `55`;
3. logical `30 09` (enable controller), expect `55`;
4. logical `30 03 len data[0..7]` to send one raw CAN frame;
5. logical `30 08` to request the last eight received bytes.

The setup payload is: bus-timing mode; optional BTR0/BTR1 for custom mode; acceptance code LE32; acceptance mask LE32; TX CAN identifier LE32; RX-filter identifier LE32; extended-frame flag; transmission mode; encapsulation. [amt.py lines 243-323](https://github.com/endes0/amtflash/blob/main/src/amtflash/amt.py#L243-L323)

EDC16U34 is listed by MPPS-era coverage material as `K-Line/CAN TP2.0`, so an exact car/session route cannot be inferred from the ECU family name alone. The open-source `amtflash` package does not implement VW TP2.0, KWP programming-session security, erase, transfer-data, or checksum routines; its CAN receive code is explicitly marked unfinished/untested. Therefore no evidence-backed byte-perfect EDC16U34 flashing sequence can be supplied from this package alone.

The safe next acceptance gate is: adapter handshake PASS, version probe PASS, then ECU identification PASS in read-only mode using a USB capture of the genuine V18 drive. Flash erase/write must remain disabled until that trace identifies the exact TP2.0/KWP services, security algorithm, memory layout, checksum handling, and recovery behavior for the selected `03G906021QJ` software.

## Safety boundary

- `12.58 V` is adequate evidence for a powered adapter, not a safe programming supply. Use a regulated battery support supply appropriate for vehicle programming and verify voltage under load.
- Never send `0x92`; it is conventionally EEPROM erase.
- Do not experiment with erase/write services on the ECU while diagnosing USB authentication.
- Before any ECU write: obtain and independently verify the full original read, ECU identifiers, target compatibility, checksums, stable power, and a tested recovery path.

## Evidence limitations

- The open-source project describes itself as an MPPS **v13** driver, while the subject is a V18 clone. Its adapter sequence is strong evidence for the protocol family, not proof that every V18 clone uses the same `0x1000` state semantics.
- No successful Windows USB capture for this exact serial/hardware revision was available.
- No protected C8051 firmware image was available, so the meaning of `0x55 00` cannot be established from firmware code.
