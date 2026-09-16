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
|  | - 32-bit RISC core, 56 MHz or 66 MHz                  |  |
|  | - Internal SRAM: 512 KB                               |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | External Flash Memory (2,097,152 bytes / 2 MB)        |  |
|  | Part: AMD AM29BL802CB / ST M58BW016DB                |  |
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
- **Base Boost Target Map (`PCR_pBDesBas_MAP`)**: `0x1EB0B2` / `0x1E9A40` (16×10 / 16×16 depending on variant bank)
- **Smoke Limiter (`FlMng_qPresSmoke_MAP`)**: `0x1D6490` (16×12)
- **Hot-Start Base Torque (`StSys_trqStrtBas_MAP`)**: `0x1F070C` (9×9)
- **Hot-Start Term 50 Torque (`StSys_trqStrt_MAP`)**: `0x1F07EA` (9×9)
- **Cruise SOI 5-6 Gear (`InjCrv_phiBasGear56_MAP`)**: `0x1DACF8` (16×14)

---

## Operating System & Execution Tasks

EDC16 operates on a deterministic real-time OSEK-compliant operating system with two execution domains:
1. **Time-triggered tasks**:
   - `10 ms raster`: Fast PID controllers (boost pressure closed-loop, rail pressure, air control).
   - `20 ms raster`: Smoke limitation, driver wish calculation, torque coordinator.
   - `100 ms raster`: Thermal modeling (modeled EGT, oil temp derating, ambient compensation).
2. **Angle-triggered tasks (Synchronous with Crankshaft Rotation)**:
   - Fired at defined crank angle intervals (every 180° crank angle for a 4-cylinder engine).
   - Computes exact Start of Injection (SOI), BIP (Beginning of Injection Period), and Unit Injector solenoid energization duration.
