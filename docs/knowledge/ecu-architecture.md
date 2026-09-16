# Bosch EDC16U34 ECU Architecture

## Hardware Overview

The engine management computer installed in this vehicle is the **Bosch EDC16U34-3.42** electronic diesel control unit.

- **VAG Part Number**: `03G 906 021 QJ`
- **Bosch Hardware Number**: `0 281 014 065`
- **Bosch Software Version**: `1037391847` (Family `391847`, Project code `P447_HAXN`)
- **Engine Application**: 1.9 TDI 8V Pumpe-Düse (Engine code `BLS`, 77 kW / 105 HP, with factory DPF)

### Microcontroller & Memory Architecture

```
+-------------------------------------------------------------+
|                 Bosch EDC16U34 ECU Core                     |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Microcontroller: Motorola/Freescale MPC562 (PowerPC)   |  |
|  | - 32-bit RISC core, 56/66 MHz                          |  |
|  | - Internal SRAM: 32 KB CALRAM (per NXP MPC562 spec)   |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | External Flash Memory (2,097,152 bytes / 2 MB)        |  |
|  | Typical parts: AMD AM29BL802CB / ST M58BW016DB family  |  |
|  |                                                       |  |
|  | 0x000000 - 0x03FFFF: Bootloader & Microcode           |  |
|  | 0x040000 - 0x1BFFFF: Operating System & Engine Code   |  |
|  | 0x1C0000 - 0x1FFFFF: Calibration Block (Maps & Axes)  |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | Serial EEPROM: ST95320 / ST95640 (4 KB / 8 KB)        |  |
|  | - Immobilizer data, coding, mileage, injector trims   |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

### Memory Map Layout in Flash

In SW `1037391847`, all calibration parameters and maps reside in the upper **256 KB** of the flash image (offset range `0x1C0000` to `0x1FFFFF`).

- **Flash Base Address**: `0x000000`
- **Calibration Area Base**: `0x1C0000`
- **N75 Pre-Control Map (`PCR_rBPCtlBas_MAP`)**: `0x1E9FD0` (16×13)
- **Base Boost Target Map (`PCR_pBDesBas_MAP`)**: `0x1EB0B2` (16×10)
- **Smoke Limiter (`FlMng_qPresSmoke_MAP`)**: `0x1D6490` (16×12)
- **Hot-Start Base Torque (`StSys_trqStrtBas_MAP`)**: `0x1F070C` (9×9)
- **Hot-Start Term 50 Torque (`StSys_trqStrt_MAP`)**: `0x1F07EA` (9×9)
- **Cruise SOI 5-6 Gear (`InjCrv_phiBasGear56_MAP`)**: `0x1DACF8` (16×14)

---

## Operating System & Execution Tasks

> [!NOTE]
> Bosch EDC16 systems typically execute multi-rate time-triggered tasks (e.g., 10 ms boost regulation, 20 ms torque coordination, 100 ms thermal monitoring) alongside angle-synchronous injection tasks (every 180° crank angle). Exact task raster scheduling in SW 1037391847 remains a typical Bosch reference model until disassembler verification is completed.
