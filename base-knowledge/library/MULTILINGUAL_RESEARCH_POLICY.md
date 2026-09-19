# Multilingual & Alternate Editions Acquisition Protocol

**Canonical Literature Acquisition Policy for Technical ECU Calibration & Engine Management**

---

## 1. Core Principle: Linguistic Agnosticism & OEM-Native Ground Truth

Engineering literature—especially in automotive engine control systems—does not originate exclusively in English. Restricting technical literature research to English creates artificial blind spots, low-quality scanned OCR dependencies, and delays in acquiring authoritative material.

### Hierarchical Language Priority for Bosch & VAG
For all systems engineered by **Robert Bosch GmbH**, **Volkswagen AG**, **Siemens VDO**, or **Continental Automotive**:
$$\textbf{German Original (Born-Digital)} \succ \textbf{English Official Translation} \succ \textbf{Russian / European Professional Edition}$$

1. **German (OEM Native Ground Truth):**
   - Bosch "Gelbe Reihe" (Yellow Series) technical handbooks and VAG SSPs were originally drafted in German by the system design engineers in Stuttgart and Wolfsburg.
   - German editions frequently offer clean born-digital vector typography (no degraded OCR), exact internal German signal nomenclature (e.g. *Mengenkorrektur, Förderbeginn, Ladedruckregelung*), and precede English translations by 2 to 4 years.
2. **English (Global Engineering Standard):**
   - Essential for cross-checking terminology, academic citations, and international calibration protocols.
3. **Russian & Eastern European Translations:**
   - Often provide exceptionally detailed localized technical glossaries, full unabridged chapter translations, and freely accessible complete reference PDFs (e.g. "За рулем" translations of Bosch handbooks).
   - **Mandatory Provenance Check:** Every translated edition must record the exact underlying German/English edition and publication year.

---

## 2. Target Language Matrix & Query Expansion

For every high-priority target work, queries MUST be systematically expanded across 8 core languages:

| Language | Primary Focus / Value | Typical Keywords |
|---|---|---|
| **English (en)** | Global baseline, academic papers, SAE standards | Engine Management, Turbocharging, Volumetric Efficiency, Control |
| **German (de)** | Bosch / VAG OEM primary source, born-digital PDFs | Dieselmotor-Management, Aufladung, Gemischbildung, Ladedruck |
| **Russian (ru)** | Complete translated compendiums, handbook series | Системы управления дизельными двигателями, Автомобильный справочник |
| **Polish (pl)** | Strong VAG TDI and Bosch EDC enthusiast & tuner manuals | Sterowanie silników spalinowych, Doładowanie, Układy wtryskowe |
| **Spanish (es)** | South American & Spanish technical university theses | Gestión de motores diésel, Sobrealimentación, Inyección directa |
| **French (fr)** | PSA / Renault diesel injection and turbo control | Gestion des moteurs diesel, Suralimentation, Turbocompresseur |
| **Italian (it)** | Magneti Marelli / Common Rail birthplace (Fiat/CR) | Gestione motore diesel, Sovralimentazione, Iniezione diretta |
| **Chinese (zh)** | Comprehensive institutional textbook translations | 柴油机管理系统, 内燃机增压, 发动机控制建模 |

---

## 3. Search Dimension Taxonomy

Queries must not rely solely on author and English title. Every search iteration must permute:
1. **Original Native Title:** (e.g. *Dieselmotor-Management: Systeme und Komponenten*)
2. **Translated Title:** (e.g. *Системы управления дизельными двигателями*, *Diesel Engine Management*)
3. **Primary & Volume Authors / Editors:** (e.g. *Konrad Reif*, *Hiereth*, *Prenninger*, *Watson*, *Janota*, *Guzzella*, *Onder*)
4. **ISBN-10 & ISBN-13:** Across all known multilingual translations.
5. **DOI (Digital Object Identifier):** For Springer, SAE, IEEE, ASME, and Elsevier publications.
6. **Publisher Name:** (e.g. *Vieweg+Teubner*, *Springer-Verlag*, *Robert Bosch GmbH*, *За рулем*, *Macmillan*, *Wiley*)
7. **Edition Number & Specific Era Year:** (e.g. 4. Auflage 2004 for EDC16/PD era vs. 5. Auflage 2014 for common-rail Euro 6).

---

## 4. Equivalent & Functional Replacement Hierarchy

If an individual textbook (e.g. *Watson & Janota — Turbocharging*) is unavailable in full born-digital format, **do not stall the pipeline**. Immediately deploy the equivalent textbook heuristic:
- **Watson & Janota (1982)** $\longrightarrow$ **Hiereth & Prenninger — *Aufladung der Verbrennungskraftmaschine* (Springer)**
  - Contains rigorous German engineering derivations of VTG vane kinematics, compressor maps, pulse turbocharging, and transient turbine filling.
- **English Bosch 5th Ed (2014)** $\longrightarrow$ **German Bosch 4. Auflage (2004)**
  - The 2004 edition is functionally superior for EDC16U34 / Pumpe-Düse calibrations because it was written during the active series production of EDC16 and unit injectors.

---

## 5. Provenance & Integrity Verification Checklist

Before cataloging any alternate edition or translation:
- [ ] **Exact Edition & Year:** Documented in metadata.
- [ ] **ISBN / DOI:** Verified against German National Library (DNB), Library of Congress, or Russian Book Chamber.
- [ ] **Page Completeness:** File page count compared against canonical physical edition (ensure no missing chapters or truncated preview).
- [ ] **Translation Fidelity:** Confirm whether mathematical equation numbering, sign conventions, or symbol notations were altered from the original.
- [ ] **Text Layer Quality:** Prioritize born-digital vector PDFs over scanned OCR.
- [ ] **Dual Preservation:** Retain the highest-quality digital text edition for automated searching, while linking the canonical original edition as scientific ground truth.
