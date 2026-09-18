# Memory Architecture and Addressing

## Memory Types

### Internal vs External Flash
- **Internal flash**: Integrated in MCU die (MPC563/564, TC1797, SH7058). Faster access, separate from external storage.
- **External flash**: Separate parallel NOR chip (AM29F400, MX29F800). MPC562 (EDC16U34) is flashless — ALL code and data on external flash.
- **EEPROM**: Discrete I²C/SPI EEPROM or data-flash emulation. Holds immobilizer, adaptations, learned values.
- **EEPROM emulation**: Some MCUs (TriCore) use data flash sectors to emulate EEPROM with wear leveling.

### Memory Segments
- **Code/Application**: Compiled ECU firmware, interrupt vectors, startup code
- **Calibration**: Tunable parameters, maps, curves, scalars
- **Bootloader**: Programming loader, recovery routines
- **RAM overlays**: Runtime copies of calibration pages for hot-calibration
- **Mirrors/Aliases**: TriCore maps same physical memory at multiple address ranges

## Addressing Models

### C167 (EDC15 family)
Segmented addressing with Data Page Pointers (DPP0–DPP3):
- 24-bit physical address = 10-bit segment + 14-bit offset
- Each DPP register maps a 16 KB page
- Code and data may reference different segments simultaneously
- Segment boundaries affect map pointer resolution

### PowerPC MPC5xx (EDC16 family)
- 32-bit flat address space
- MMU may remap regions; check BAT/TLB configuration
- MPC562: no internal flash; external bus interface (EBI) maps external flash
- MPC563/564: internal flash at fixed addresses + optional external
- Instruction and data caches affect observable behavior during debugging

### TriCore TC17xx (EDC17/MED17 family)
- Multiple address aliases for same physical memory:
  - Cached segment: `0x8xxxxxxx`
  - Non-cached segment: `0xAxxxxxxx`
  - Physical: `0x0xxxxxxx`
- Program Flash (PF): code and bootloader
- Data Flash (DF): EEPROM emulation, adaptations
- Flash sector protection: password-controlled + permanently lockable (OTP)
- TPROT (Tuning Protection): hardware-enforced read/write restrictions

### Renesas SH705x
- Fixed flash geometry with specific sector sizes
- Big-endian instruction encoding
- Programming mode via specific pin configuration
- Memory-emulation mode for development

## Address Translation

For a contiguous byte-addressed segment:

$$fileOffset = segmentFileOffset + (ecuAddress - segmentBase)$$

Apply this **only after resolving** the segment, bank, and alias. A guessed global base subtraction is insufficient.

### Common Pitfalls
- Assuming a single flat base address for all segments
- Ignoring banked/aliased regions that map to the same physical memory
- Confusing cached vs non-cached addresses on TriCore
- DPP-relative addresses on C167 without knowing the DPP register values

## Byte Order

Decode byte order explicitly:

Big-endian (Motorola MSB_FIRST):
$$u_{BE} = \sum_{i=0}^{k-1} b_i \cdot 256^{k-1-i}$$

Little-endian (Intel LSB_FIRST):
$$u_{LE} = \sum_{i=0}^{k-1} b_i \cdot 256^{i}$$

- `MSB_FIRST` = big-endian
- `MSB_LAST` / `LSB_FIRST` = little-endian
- Distinguish from CAN signal bit numbering
- Processor defaults do NOT establish the encoding of every stored object — A2L byte-order overrides exist

## File Formats

| Format | Characteristics |
|---|---|
| Raw binary | Flat memory image, position = address offset from base |
| Intel HEX | ASCII, address records, supports extended linear/segment addressing |
| Motorola S-record | ASCII, S0 header, S1/S2/S3 data records with addresses |
| Tool-specific | MPPS .bin, Galletto, BDM100 — may include headers, metadata, or reordered regions |

### Handling
- Address gaps in HEX/S-record may indicate unmapped regions or separate segments
- Padding bytes (0xFF or 0x00) fill erased flash areas
- Tool headers: strip before checksum calculation, restore before programming
- Image size must match expected segment size exactly

## TriCore TC1797 Specifics

Program flash, sector protection, password-controlled access, and permanently lockable sectors require derivative-specific handling.

Key features:
- Flash configuration via UCB (User Configuration Block)
- Read/write protection per sector group
- OTP (One-Time Programmable) lock — irreversible
- Debug interface (DAP) protection separate from flash protection

Reference: [Infineon TC1797 datasheet](https://www.infineon.com/assets/row/public/documents/10/49/tc1797-ds-v1-3.pdf)

## SH7058 Specifics

SH7058 has its own programming and memory-emulation behavior:
- Fixed flash sectors with specific erase/program granularity
- Boot mode for external programming
- On-chip programming routines
- Memory-emulation mode maps external RAM over flash for development

Reference: [Renesas SH7058 hardware manual](https://www.renesas.com/en/document/mah/sh-2e-sh7058-f-ztat-tm-hardware-manual?r=1054746)

## MPC562 Specifics (Golf 5 EDC16U34)

> [!CAUTION]
> MPC562 has **NO internal flash** (unlike MPC563/564). All code — including the bootloader — resides on the same external flash chip. Corrupting the bootloader sector makes the ECU unrecoverable via OBD. BDM/JTAG is the only recovery path.

- External bus interface (EBI) maps external NOR flash
- Calibration area: 512 KB within the flash image
- MPPS v18 writes only the calibration area — bootloader sectors are NOT touched
- Recovery via AMT (Automatic Memory Test) is conditional, not guaranteed
- COP (Common On-chip Processor) debug port provides BDM access for emergency recovery
