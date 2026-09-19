# ECU Family Profiles

This reference provides initial routing for ECU family identification. Each entry is a starting point — the actual ECU profile must be established from hardware/software identifiers, not family assumptions.

## Routing Table

| Target Family | Initial Investigation | Profile Must Establish |
|---|---|---|
| Bosch EDC15 | C167-based variants; external program/calibration storage where present | Exact derivative, addressing model, flash devices, EEPROM, actual read coverage |
| Bosch EDC16 / MED9 | MPC5xx-based variants | Internal/external memory split, boot source, address mappings, relevant debug interface |
| Bosch EDC17 / MED17 | TriCore TC176x/TC179x variants | Program/data flash, aliases, protection configuration, writable regions, integrity chain |
| Continental/Siemens | Identify exact ECU and MCU before choosing architecture | Processor, memory devices, boot configuration, layout and supported protocol |
| Delphi | Identify exact ECU and fuel-system generation | Processor, memory topology, calibration structure and integrity implementation |
| Denso | Identify exact MCU family (Renesas, NEC) | Memory geometry, programming mode, calibration area boundaries |
| Renesas SH705x | Exact SH derivative and operating mode | Flash geometry, vectors, byte order, programming restrictions and recovery interface |

> [!IMPORTANT]
> These are routing hints, not family-wide guarantees. Tool compatibility data identifies specific ECU+tool combinations.

## Known Profile: EDC16U34 (Golf 5 BLS 1.9 TDI)

This is the primary validated profile for this skill.

| Field | Value |
|---|---|
| ECU | Bosch EDC16U34 |
| HW Number | 03G906021QJ |
| SW Number | 391847 |
| MCU | Freescale MPC562 |
| Internal Flash | **None** (MPC562 is flashless, unlike MPC563/564) |
| External Flash | Single chip, holds bootloader + application + calibration |
| Calibration Area | 512 KB |
| EEPROM | Separate, holds immobilizer/adaptations |
| Byte Order | Big-endian (Motorola MSB_FIRST) |
| Checksum | Additive 32-bit BE, K = 0xD01FE500 |
| OBD Tool | MPPS v18 (clone), VID 0x1C43 PID 0x0500, C8051F320 + FT232R |
| Protocol | Proprietary MPPS microcode commands (36/3F), NOT generic KWP2000 K-Line |
| Recovery | Conditional — bootloader on same flash chip. BDM if bootloader corrupt |
| Vehicle | VW Golf 5, 1.9 TDI BLS engine |
| Fuel System | Common-rail (Bosch CP1H pump, piezo injectors) |

### MPPS v18 Protocol Notes
- Communication uses proprietary microcode commands uploaded to C8051F320
- ECU identification via `3F 77` probes (binary responses, NOT ASCII)
- Read/Write via microcode `36/3F` framing
- Generic KWP2000 K-Line (`25 02`) is NOT the correct protocol for this ECU+tool combination
- 2-phase handshake: EEPROM seed read → challenge-response → microcode upload → vehicle protocol init

### Safety Constraints
- MPPS v18 writes ONLY the calibration area (512 KB) — bootloader is NOT at risk
- Always maintain 12.5V+ during programming
- Keep original backup with SHA-256 hash
- NEVER write to bootloader or EEPROM via OBD calibration path

## Profile Template

Use this template when adding new ECU profiles:

```yaml
ecu_profile:
  name: ""
  hw_number: ""
  sw_number: ""
  mcu:
    family: ""
    derivative: ""
    internal_flash: false  # true/false
    internal_flash_size: ""
  external_flash:
    type: ""  # parallel NOR, serial SPI, etc.
    size: ""
    sectors: []
  calibration:
    offset: ""
    size: ""
    byte_order: ""  # big-endian / little-endian
  eeprom:
    type: ""  # discrete / emulated
    size: ""
    contents: ""  # immobilizer, adaptations, etc.
  integrity:
    algorithm: ""  # additive32, crc16, crc32, rsa, etc.
    invariant: ""
    covered_regions: []
    correction_field: ""
    byte_order: ""
  tool:
    name: ""
    connection: ""  # OBD / bench / boot / BDM
    protocol: ""
    supported_operations: []
  recovery:
    method: ""
    prerequisites: []
    limitations: ""
  vehicle:
    make: ""
    model: ""
    engine: ""
    fuel_system: ""
```

## Adding New Profiles

1. Start with physical ECU identification (read HW/SW numbers)
2. Match MCU family from routing table
3. Determine memory architecture from MCU datasheet
4. Identify tool and protocol from compatibility databases
5. Establish integrity algorithm from known-good test vectors
6. Document recovery path and its prerequisites
7. Validate with read-write-readback cycle on a test ECU before production use

## External References
- [AutoTuner compatibility database](https://www.autotuner.com/a/app/compatibility)
- [Alientech connection methods](https://www.alientech-tools.com/en/kess3/connection-methods/)
- [Bosch Motorsport MS 6.x manual](https://www.bosch-motorsport.com/media/downloads/engine_control_unit_ms_6-x_manual.pdf)
