# EDC16U34 Project Knowledge Base — Golf 5 1.9 TDI BLS

Welcome to the **Engineering Knowledge Base** for the 2008 Volkswagen Golf 5 1.9 TDI BLS running Bosch EDC16U34.

This repository structure is built strictly according to the **[Project Knowledge Bootstrap Pack Specification](EDC16U34_KNOWLEDGE_BOOTSTRAP_PACK.md)** and governed by **[RESEARCH_POLICY.md](RESEARCH_POLICY.md)**.

> [!IMPORTANT]
> **Source of Truth Hierarchy**:
> - **Primary Ground Truth**: `diagnostic-review/*` + raw matching A2L (`03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`) + exact reference/active BINs + real telemetry logs.
> - **Draft Knowledge Layer**: `docs/knowledge/*` represents the synthesized working model subject to continuous verification and sign-test logging.

---

## Target Vehicle & ECU Profile

- **Vehicle**: Volkswagen Golf 5 (1K1), 2008
- **Engine**: 1.9 TDI 8V Pumpe-Düse (Engine Code: `BLS`, 77 kW / 105 HP)
- **Engine Control Unit**: Bosch EDC16U34-3.42
- **VAG Hardware Part Number**: `03G 906 021 QJ`
- **Bosch Software Version**: `1037391847` (Family `391847`, Calibration project: `P447_HAXN`)
- **Turbocharger**: BorgWarner / KKK BV39 (`5439 988 0072` / `03G 253 014 M`)

---

## Core Knowledge Architecture

Every engineering claim is rated along two independent axes:
1. **Authority Score (1–5)**: Credibility and rigor of the source.
2. **Applicability Score (1–5)**: Direct physical relevance to SW `1037391847` and BLS hardware.

Claims follow a strict epistemic lifecycle:
$$\text{raw} \longrightarrow \text{corroborated} \longrightarrow \text{project\_matched} \longrightarrow \text{experiment\_supported} \longrightarrow \text{verified}$$

---

## Knowledge Documentation Index

| Category | Document | Description |
|---|---|---|
| **Governance & Sources** | [RESEARCH_POLICY.md](RESEARCH_POLICY.md) | Master research prompt, epistemic rules & priority hierarchy |
| | [source-index.md](source-index.md) | 21+ Tier A/B/C sources with authority & applicability ratings |
| | [research-changelog.md](research-changelog.md) | Ingestion changelog and ground-truth alignment history |
| **ECU & Engine Architecture** | [ecu-architecture.md](ecu-architecture.md) | MPC562 MCU, 2MB Flash, calibration partitioning, raster tasks |
| | [edc16-torque-model.md](edc16-torque-model.md) | Torque coordinator, indicated torque, losses, conversion to IQ |
| | [hardware-limits.md](hardware-limits.md) | Safe limits for BV39 turbo, BLS conrods, and DMF |
| **Air Path & Boost Control** | [boost-control.md](boost-control.md) | Stage 1 target (2214 mbar abs), atmospheric/temp derating |
| | [vnt-n75-control.md](vnt-n75-control.md) | N75 pre-control (`PCR_rBPCtlBas_MAP` 16×13), unproven polarity |
| **Fueling & Combustion** | [fueling-and-limiters.md](fueling-and-limiters.md) | Limiter cascade (Driver Wish, Torque Limit, Smoke Limit) |
| | [smoke-limiter.md](smoke-limiter.md) | MAP-based (`FlMng_qPresSmoke_MAP` @ 0x1D6490, 16×12) |
| | [injection-duration.md](injection-duration.md) | PD unit injector duration maps (`InjCrv_phiDur_MAP`) |
| | [injection-timing.md](injection-timing.md) | Start of Injection (`InjCrv_phiMI1Des_MAP`), cruise eco-timing |
| | [hot-start.md](hot-start.md) | Cranking torque (`StSys_trqStrtBas_MAP` @ 0x1F070C) & HS-250 fix |
| | [thermal-protection.md](thermal-protection.md) | Modeled EGT, thermal derating & component protection (805°C) |
| **Calibration & Lineage** | [a2l-map-index.md](a2l-map-index.md) | Catalog of verified active maps with addresses in SW `1037391847` |
| | [firmware-lineage.md](firmware-lineage.md) | Stock (2050 mbar) vs Active Stage 1 (2214 mbar) vs Refined (HS-250) |
| **Telemetry & Investigation** | [log-index.md](log-index.md) | Inventory of VCDS WOT and Turbo Fast road test logs |
| | [experiment-results.md](experiment-results.md) | Analysis of 2310–2320 mbar boost peak vs 2214 mbar target |
| | [conflicting-evidence.md](conflicting-evidence.md) | Resolution of conflicting claims (N75 polarity, smoke limiter) |
| | [open-questions.md](open-questions.md) | Core project questions & competing boost hypotheses (A–G) |
| | [recommended-tests.md](recommended-tests.md) | Standardized VCDS logging protocols (Group 011 single-group run) |

---

## SQLite Database & CLI Querying Engine

The relational database (`knowledge/edc16_knowledge.db`) contains **11,537 indexed A2L characteristics**, active map offsets, firmware metadata, and VCDS log runs with SQLite **FTS5 full-text search**.

### Query Commands

```bash
# Print knowledge base statistics
python tools/knowledge_manager.py stats

# Search for any map, symbol, or hex address using FTS5
python tools/knowledge_manager.py search PCR_rBPCtlBas_MAP
python tools/knowledge_manager.py search "0x1E9FD0"
python tools/knowledge_manager.py search "smoke limiter"
```
