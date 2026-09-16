Objective: independently investigate the MPPS V18 clone USB transport issue and return a concise Markdown research note with primary-source citations and explicitly labeled inference.

Absolute working directory: C:\Users\pavlo\golf5

Facts: USB device VID 1C43 PID 0500 product Amt Flash bcdDevice 4.00; endpoints bulk OUT 0x02, IN 0x81 MPS 64. Control request 0x90/0xC0 reads addresses: 0x3000 voltage, 0x1000 => 55 00 unlocked, 0x2000 dynamic TX/RX masks. Android sends XOR-masked commands, OUT succeeds, every IN returns exactly FTDI status bytes 01 10 and no payload. Board reportedly contains FTDI bridge, C8051F340, SJA1000, L9637D.

Research questions: exact meaning of FTDI two-byte status prefix; all FTDI control transfers used to configure UART and their USB encoding; likely or verified baud/data/parity/flow/bitmode/latency sequence used by genuine MPPS V18 Windows software; whether unlock=0x55 still needs rearm; concrete minimal diagnostic and init sequence. Search official FTDI docs/libftdi/Linux driver/source and inspect local files/binaries/source if useful. Do not modify any files. Do not delegate further.

Acceptance: distinguish confirmed facts from unverified MPPS-specific claims; do not invent baud or unlock behavior; identify what evidence is required (USBPcap, logic analyzer, or disassembly) to settle unknowns.

Response contract: ready-to-save Markdown with source URLs and a short prioritized answer.
