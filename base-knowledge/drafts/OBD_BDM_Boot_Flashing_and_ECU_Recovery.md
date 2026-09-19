# Flashing Safety and Recovery

## Pre-Flash Evidence Gates

Every flash operation must pass ALL gates before proceeding:

| Gate | Required Evidence |
|---|---|
| Identity | Physical target and diagnostic IDs match the selected profile and artifact |
| Backup | Available memories preserved; missing coverage and virtual-read limitations documented |
| Artifact | Final hash, reviewed byte diff, protected-region checks, integrity results |
| Tool | Exact hardware, software version, license/protocol, supported operation |
| Power | OEM/tool voltage range, current capacity, stable supply mode, monitored connection |
| Connection | Exact pinout, adapter, grounding; appropriate board handling where required |
| Recovery | Documented failure route, usable backup coverage, required access, available equipment |
| Execution | Authorization covers this ECU, image, and operation |
| Acceptance | Post-write verification and controlled engine-validation plan established |

## Access Methods

| Method | Description | Physical Access |
|---|---|---|
| OBD | Via diagnostic connector, ECU on-vehicle | OBD-II port under dashboard |
| Bench | ECU removed, powered on bench supply | ECU connector + external PSU |
| Boot | MCU forced into boot/programming mode via pins | Board-level, specific pin strapping |
| BDM/JTAG | Debug interface, processor-level access | Board-level, debug header/pads |

> [!IMPORTANT]
> - Bench does **NOT** automatically mean BDM/JTAG
> - Boot mode does **NOT** guarantee unrestricted memory access
> - Use the exact tool's supported connection procedure

Reference: [Alientech connection methods](https://www.alientech-tools.com/en/kess3/connection-methods/)

## Recovery Procedures

Recovery follows the observed failure:

### 1. Responsive Programming Loader
- ECU still enters programming mode via diagnostic request
- Use the tool's documented recovery procedure
- Re-flash with verified backup image
- Verify readback matches expected content

### 2. Unresponsive Application
- ECU does not respond to normal diagnostic communication
- Determine whether bench/boot/debug access remains available
- Attempt forced programming mode (tool-specific procedure)
- If boot mode available: use boot-mode flash procedure

### 3. Protected or Unreadable Memory
- Document the limitation before assuming restoration is possible
- Check if protection can be removed via debug interface
- OTP (one-time programmable) protections are irreversible
- Password-protected regions require the correct credentials

### 4. Interrupted Programming
- Preserve ALL logs from the interrupted session
- Follow the tool's recovery instructions
- Avoid speculative resets or repeated writes
- If bootloader is intact: use normal recovery
- If bootloader is corrupted: BDM/JTAG is the only path

> [!CAUTION]
> If a tool changes checksums during programming, retain the exported programmed artifact where available or document the transformation. Compare like-for-like memory coverage during readback.

## MPC562/EDC16U34 Recovery (Golf 5 BLS)

### Architecture Risk
- MPC562 has **NO internal flash** — bootloader lives on same external chip
- If bootloader sector is corrupted → BDM/JTAG is the only recovery path
- AMT (Automatic Memory Test) recovery is **conditional**, not guaranteed

### Normal Calibration Write (MPPS v18)
- Writes ONLY the 512 KB calibration area
- Bootloader sectors are **NOT touched**
- Risk of bootloader corruption: **minimal** during normal calibration writes
- Interrupted calibration write → bootloader intact → OBD recovery possible

### Emergency Recovery
1. **OBD Recovery** (if bootloader intact):
   - ECU enters programming mode on power-up
   - Use MPPS or compatible tool to re-flash calibration
   - Verify with readback

2. **BDM Recovery** (if bootloader corrupted):
   - Requires physical access to ECU board
   - Connect BDM/COP debugger to MPC562 debug port
   - Flash complete image including bootloader
   - Equipment: BDM100, Motorola/NXP debugger, or compatible BDM probe

## Power Requirements

| Parameter | Requirement |
|---|---|
| Minimum voltage | 12.5V continuous, monitored |
| Recommended supply | Battery charger in maintenance mode or regulated bench PSU |
| Current capacity | ≥5A (ECU + adapter + relay coils during programming) |
| Monitoring | Continuous voltage monitoring during entire programming sequence |

> [!WARNING]
> **Never** rely on battery alone for extended programming operations. Voltage drop during cranking or accessory load can corrupt a write in progress.

### Voltage Monitoring Protocol
1. Measure voltage before starting programming
2. Abort if voltage drops below 12.0V during write
3. Use stable power source: bench PSU or battery charger in float/maintenance mode
4. Ensure all vehicle accessories are off during programming
5. Do not start engine during programming

## Tool Compatibility

Tool compatibility data identifies specific ECU+connection+operation combinations. Never assume one tool's procedures apply to another.

| Tool | Type | Typical Use |
|---|---|---|
| MPPS v18 | OBD reader/writer | Calibration read/write via K-Line/CAN |
| KESS v2/v3 | OBD reader/writer | Professional calibration access |
| KTag | Bench/Boot | ECU on bench, direct flash access |
| BDM100 | BDM debugger | Emergency recovery, full flash access |
| AutoTuner | OBD/Bench/Boot | Multi-protocol, newer ECU support |
| Alientech KESS3 | OBD/Bench/Boot | Professional, wide ECU coverage |

Reference: [AutoTuner compatibility database](https://www.autotuner.com/a/app/compatibility)

## Post-Write Verification

### Readback Verification
1. Read back the written area immediately after programming
2. Compare SHA-256 hash with the intended artifact
3. Document any tool-modified regions (checksums corrected by tool)
4. Compare like-for-like memory coverage

### Engine Validation Plan
1. **Initial start**: Verify engine starts and idles normally
2. **Idle quality**: Check for rough idle, misfires, unusual noise
3. **Basic driving**: Low-load acceleration, deceleration, cruise
4. **Full-load test**: Controlled acceleration to verify torque delivery
5. **Thermal test**: Extended driving to verify no overheating
6. **Diagnostic scan**: Check for new DTCs after test drive
7. **Data logging**: Log key parameters (boost, EGT, rail pressure, lambda) under load

> [!IMPORTANT]
> A successful write and checksum pass does **NOT** equal a validated calibration. Engine testing is a separate, required validation step.
