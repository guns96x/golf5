# Research Changelog & Bootstrap History

## Version 1.0.0 — 2026-09-16
- **Bootstrap Initialization**: Implemented the complete Project Knowledge Bootstrap Pack specification from `docs/knowledge/EDC16U34_KNOWLEDGE_BOOTSTRAP_PACK.md`.
- **Database Engine**: Deployed `knowledge/edc16_knowledge.db` with SQLite relational schema and FTS5 virtual tables (`claims_fts`, `maps_fts`).
- **A2L Ingestion**: Parsed and indexed 11,537 characteristics from OEM A2L dataset `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`.
- **Active Maps**: Tagged and correlated 29 verified active maps from `active-map-verification.json`.
- **Telemetry Ingestion**: Ingested VCDS and Turbo Fast logs into relational tables with quantitative overshoot calculations.
- **Documentation**: Generated all 20 technical knowledge documents in `docs/knowledge/` adhering to the Master Research Policy.
