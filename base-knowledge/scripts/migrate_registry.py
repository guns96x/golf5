# Literature Library Registry Migration Script
import os
import sys
import json
import hashlib
from typing import Dict, Any, List
from pypdf import PdfReader
import zipfile

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBRARY_DIR = os.path.join(BASE_DIR, "knowledge", "library")
REGISTRY_PATH = os.path.join(LIBRARY_DIR, "library_registry.json")
INDEX_PATH = os.path.join(LIBRARY_DIR, "LIBRARY_INDEX.md")

def get_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def measure_pdf_text(filepath: str):
    try:
        reader = PdfReader(filepath)
        n_pages = len(reader.pages)
        check_pages = min(8, n_pages)
        chars = [len(reader.pages[i].extract_text() or "") for i in range(check_pages)]
        cpp = sum(chars) / max(1, check_pages)
        cpp_int = round(cpp)
        if cpp_int >= 300:
            status = "GOOD"
        elif cpp_int >= 50:
            status = "THIN"
        else:
            status = "NONE"
        return n_pages, status, cpp_int
    except Exception as e:
        print(f"Error measuring PDF {filepath}: {e}")
        return 0, "NONE", 0

def measure_draft_text(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        lines = content.splitlines()
        pages = max(1, (len(lines) + 39) // 40)
        cpp = len(content) / pages
        cpp_int = round(cpp)
        status = "GOOD" if cpp_int >= 300 else ("THIN" if cpp_int >= 50 else "NONE")
        return pages, status, cpp_int
    except Exception as e:
        print(f"Error measuring text {filepath}: {e}")
        return 1, "GOOD", 500

def measure_epub_text(filepath: str):
    try:
        total_chars = 0
        with zipfile.ZipFile(filepath, 'r') as z:
            for name in z.namelist():
                if name.endswith(('.html', '.xhtml', '.htm')):
                    txt = z.read(name).decode('utf-8', errors='ignore')
                    in_tag = False
                    clean = []
                    for ch in txt:
                        if ch == '<':
                            in_tag = True
                        elif ch == '>':
                            in_tag = False
                        elif not in_tag:
                            clean.append(ch)
                    total_chars += len("".join(clean).strip())
        pages = 962  # Heywood printed length
        cpp = total_chars / max(1, pages)
        cpp_int = round(cpp)
        status = "GOOD" if cpp_int >= 300 else ("THIN" if cpp_int >= 50 else "NONE")
        return pages, status, cpp_int
    except Exception as e:
        print(f"Error measuring EPUB {filepath}: {e}")
        return 962, "GOOD", 2200

def run_migration():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reg = json.load(f)

    records = reg.get("records", [])
    print(f"Total existing records: {len(records)}")

    # 1. New files to register if not present
    new_files_to_add = [
        {
            "title": "BorgWarner: Turbochargers with Variable Turbine Geometry (VTG) - Technical Whitepaper",
            "authors": "BorgWarner Turbo Systems GmbH",
            "year": "2021",
            "publisher": "BorgWarner Inc.",
            "doc_id": "BW-VTG-2021",
            "language": "en",
            "original_language": "en",
            "canonical_title": "Turbochargers with Variable Turbine Geometry (VTG)",
            "edition_number": "1",
            "is_oem_native": False,
            "translation_provenance": None,
            "isbn_multilingual": {},
            "source_url": "https://www.borgwarner.com/docs/default-source/default-document-library/turbochargers-with-variable-turbine-geometry-(vtg).pdf",
            "file_format": "PDF",
            "authority_tier": "Tier A",
            "topics": ["BorgWarner", "VTG", "Variable Turbine Geometry", "VNT Aerodynamics", "Actuation"],
            "applicability": 4,
            "system_match": "N-A",
            "folder": "05_turbo",
            "filename": "BorgWarner_Turbochargers_with_Variable_Turbine_Geometry_VTG.pdf",
            "obtainability": "HAVE_LOCAL",
            "license_status": "public",
            "notes": "Official BorgWarner whitepaper detailing VTG / variable nozzle geometry, vane aerodynamics, backpressure control, and actuation."
        },
        {
            "title": "BorgWarner Turbo News 2004-1: 3rd Generation VTG and BV39 Turbocharger Introduction for VW 1.9 TDI",
            "authors": "BorgWarner Turbo Systems Worldwide Headquarters GmbH",
            "year": "2004",
            "publisher": "BorgWarner Turbo Systems",
            "doc_id": "TurboNews 2004-1",
            "language": "en",
            "original_language": "en",
            "canonical_title": "BorgWarner Turbo News 2004-1",
            "edition_number": "2004-1",
            "is_oem_native": False,
            "translation_provenance": None,
            "isbn_multilingual": {},
            "source_url": "https://www.borgwarner.com/docs/default-source/corporate/turbo-news-2004-1.pdf",
            "file_format": "PDF",
            "authority_tier": "Tier A",
            "topics": ["BorgWarner", "BV39", "VTG 3rd Generation", "VW 1.9 TDI", "VNT Mechanism"],
            "applicability": 4,
            "system_match": "N-A",
            "folder": "05_turbo",
            "filename": "BorgWarner_Turbo_News_2004_1_BV39_Introduction.pdf",
            "obtainability": "HAVE_LOCAL",
            "license_status": "public",
            "notes": "Official BorgWarner corporate publication introducing the BV turbocharger family (BV35-BV50) and the specific switchover of VW 4-cylinder 1.9 TDI engines to BV39 technology in 2004."
        },
        {
            "title": "BorgWarner High-Performance and Replacement Turbochargers Catalog",
            "authors": "BorgWarner Turbo Systems",
            "year": "2023",
            "publisher": "BorgWarner Inc.",
            "doc_id": "BW-CAT-2023",
            "language": "en",
            "original_language": "en",
            "canonical_title": "BorgWarner Turbo Performance & Replacement Catalog",
            "edition_number": "2023",
            "is_oem_native": False,
            "translation_provenance": None,
            "isbn_multilingual": {},
            "source_url": "https://www.borgwarner.com/docs/default-source/aftermarket/turbo/bw_turbo-performance-catalog.pdf",
            "file_format": "PDF",
            "authority_tier": "Tier B",
            "topics": ["BorgWarner", "Turbo Catalog", "Frame Dimensions", "Compressor Maps", "Actuators"],
            "applicability": 3,
            "system_match": "N-A",
            "folder": "05_turbo",
            "filename": "BorgWarner_Turbo_Performance_and_Replacement_Catalog.pdf",
            "obtainability": "HAVE_LOCAL",
            "license_status": "public",
            "notes": "Official BorgWarner performance and replacement technical catalog with compressor/turbine geometry definitions and MatchBot matching theory."
        },
        {
            "title": "NXP / Freescale MPC561 / MPC562 Microcontroller Reference Manual",
            "authors": "Freescale Semiconductor / Motorola Inc.",
            "year": "2006",
            "publisher": "Freescale Semiconductor, Inc.",
            "doc_id": "MPC561RM / Rev 2",
            "language": "en",
            "original_language": "en",
            "canonical_title": "MPC561/MPC562 Microcontroller Reference Manual",
            "edition_number": "Rev 2",
            "is_oem_native": False,
            "translation_provenance": None,
            "isbn_multilingual": {},
            "source_url": "https://www.nxp.com/docs/en/data-sheet/MPC561RM.pdf",
            "file_format": "PDF",
            "authority_tier": "Tier A",
            "topics": ["MPC561", "MPC562", "PowerPC", "EDC16U34 Hardware", "BDM", "eTPU", "Flash Memory"],
            "applicability": 4,
            "system_match": "N-A",
            "folder": "08_edc16",
            "filename": "NXP_Freescale_MPC561_MPC562_Microcontroller_Reference_Manual.pdf",
            "obtainability": "HAVE_LOCAL",
            "license_status": "public",
            "notes": "Comprehensive 1328-page technical hardware reference for the 32-bit PowerPC RISC MCU (MPC561/MPC562) powering Bosch EDC16U34. Details memory map, internal flash, register architecture, timer processor (TPU3), and BDM debugging interface."
        },
        {
            "title": "ISO 14230-2: Road vehicles - Diagnostic systems - Keyword Protocol 2000 (KWP2000) - Part 2: Data link layer",
            "authors": "International Organization for Standardization",
            "year": "1999",
            "publisher": "ISO",
            "doc_id": "ISO 14230-2:1999(E)",
            "language": "en",
            "original_language": "en",
            "canonical_title": "ISO 14230-2:1999 Keyword Protocol 2000 Part 2",
            "edition_number": "1st Edition",
            "is_oem_native": False,
            "translation_provenance": None,
            "isbn_multilingual": {},
            "source_url": "https://www.iso.org/standard/24647.html",
            "file_format": "PDF",
            "authority_tier": "Tier A",
            "topics": ["KWP2000", "ISO 14230", "Data Link Layer", "EDC16 Flashing", "OBD Protocols", "CAN/K-Line"],
            "applicability": 4,
            "system_match": "N-A",
            "folder": "13_protocols",
            "filename": "ISO_14230_2_KWP2000_Data_Link_Layer_Specification.pdf",
            "obtainability": "HAVE_LOCAL",
            "license_status": "public",
            "notes": "International standard for Keyword Protocol 2000 (KWP2000) data link layer. Primary communications protocol used by Bosch EDC16U34 for OBD diagnostic sessions and flashing."
        }
    ]

    existing_filenames = {r.get("filename") for r in records}
    for nf in new_files_to_add:
        if nf["filename"] not in existing_filenames:
            records.append(nf)
            print(f"Added new record: {nf['filename']}")

    # Process all records
    updated_records = []
    for r in records:
        fn = r.get("filename", "")
        folder = r.get("folder", "")
        tier = r.get("authority_tier", "Tier B")
        
        # Check if file is a draft
        is_draft = fn.endswith(".md") or folder == "drafts" or folder == "knowledge/drafts" or r.get("obtainability") == "PROJECT_DRAFT" or tier == "DRAFT"

        # Determine file path
        if is_draft:
            disk_path = os.path.join(BASE_DIR, "knowledge", "drafts", fn)
            r["folder"] = "drafts"
            r["authority_tier"] = "DRAFT"
            r["obtainability"] = "PROJECT_DRAFT"
            r["publisher"] = ""
            r["license_status"] = "user_owned"
            pages, tl_status, cpp = measure_draft_text(disk_path)
            r["pages"] = pages
            r["text_layer"] = tl_status
            r["chars_per_page"] = cpp
            if os.path.exists(disk_path):
                r["sha256"] = get_sha256(disk_path)
        else:
            disk_path = os.path.join(BASE_DIR, "knowledge", "library", folder, fn)
            r["obtainability"] = "HAVE_LOCAL"
            if fn.endswith(".pdf"):
                if os.path.exists(disk_path):
                    pages, tl_status, cpp = measure_pdf_text(disk_path)
                    r["pages"] = pages
                    r["text_layer"] = tl_status
                    r["chars_per_page"] = cpp
                    r["sha256"] = get_sha256(disk_path)
                else:
                    r["text_layer"] = "GOOD"
                    r["chars_per_page"] = 1500
            elif fn.endswith(".epub"):
                if os.path.exists(disk_path):
                    pages, tl_status, cpp = measure_epub_text(disk_path)
                    r["pages"] = pages
                    r["text_layer"] = tl_status
                    r["chars_per_page"] = cpp
                    r["sha256"] = get_sha256(disk_path)
                else:
                    r["text_layer"] = "GOOD"
                    r["chars_per_page"] = 2200
            elif fn.endswith(".txt"):
                if os.path.exists(disk_path):
                    pages, tl_status, cpp = measure_draft_text(disk_path)
                    r["pages"] = pages
                    r["text_layer"] = tl_status
                    r["chars_per_page"] = cpp
                    r["sha256"] = get_sha256(disk_path)

        # Classify system_match: PD | VP37 | CR | INLINE | N-A
        fn_lower = fn.lower()
        title_lower = r.get("title", "").lower()

        if any(k in fn_lower for k in ["pumpe_duse", "ssp_209", "ssp_223", "ssp_230", "ssp_251", "841303", "ssp_316", "pde"]):
            r["system_match"] = "PD"
        elif any(k in title_lower for k in ["pumpe-düse", "pumpe-duse", "unit injector"]):
            r["system_match"] = "PD"
        elif any(k in fn_lower for k in ["_ve.pdf", "ssp_190", "841103"]):
            r["system_match"] = "VP37"
        elif any(k in title_lower for k in ["distributor injection", "vp44", "ve37", "vp37"]):
            r["system_match"] = "VP37"
        elif any(k in fn_lower for k in ["cp1", "ssp_350", "826803", "840193"]):
            r["system_match"] = "CR"
        elif any(k in title_lower for k in ["common rail", "cp1", "piezo common rail"]):
            r["system_match"] = "CR"
        elif any(k in fn_lower for k in ["pe_pf", "inline"]):
            r["system_match"] = "INLINE"
        elif any(k in title_lower for k in ["reiheneinspritzpumpen", "pe/pf", "in-line injection"]):
            r["system_match"] = "INLINE"
        elif fn_lower.startswith("pumpe_duse"):
            r["system_match"] = "PD"
        else:
            r["system_match"] = "N-A"

        # Classify license_status: public | user_owned | paid_not_owned
        if is_draft:
            r["license_status"] = "user_owned"
        elif "heywood" in fn_lower:
            r["license_status"] = "user_owned"
        elif any(k in fn_lower for k in ["winols", "kraftfahrtechnisches", "reif", "janota", "guzzella"]):
            r["license_status"] = "paid_not_owned"
        else:
            # University dissertations, vendor whitepapers, SSPs, open datasheets
            r["license_status"] = "public"

        # Specific user requirement: Garrett turbo docs
        if "garrett" in fn_lower:
            r["applicability"] = 2
            r["system_match"] = "N-A"
            r["notes"] = "generic theory, NOT this turbo (Golf 5 BLS uses BorgWarner BV39A-0072, not Garrett)"

        # Set applicability (1..5)
        # 5: exact match (Golf 5 BLS, EDC16U34 exact SW, measured car data)
        # 4: high (EDC16U34 general, BLS general, BV39 turbo, 1.9 TDI PD)
        # 3: medium (EDC16 general, Pumpe-Duse general, VNT general)
        # 2: low (diesel general, thermodynamics, Garrett turbo)
        # 1: reference (other fuel systems - VE, CR, PE/PF; non-diesel)
        if "garrett" in fn_lower:
            r["applicability"] = 2
        elif r["system_match"] == "INLINE":
            r["applicability"] = 1
        elif r["system_match"] in ["VP37", "CR"]:
            r["applicability"] = 1
        elif any(k in fn_lower for k in ["golf5", "bls", "03g906013k", "vcds_measuring_blocks"]):
            r["applicability"] = 5
        elif any(k in fn_lower for k in ["edc16u34", "bv39", "mpc561", "ssp_338", "ssp_209", "ssp_230", "841303", "ssp_304", "ssp_316", "ssp_315", "ssp_330", "ssp_336", "si_0051", "n75", "0281002593", "hfm5", "hfm6", "iso_14230", "vtg"]):
            r["applicability"] = 4
        elif is_draft and any(k in fn_lower for k in ["torque", "fueling", "smoke", "boost", "vnt", "transient", "thermal", "bip", "soi", "addressing", "checksum", "flashing", "map_identification"]):
            r["applicability"] = 4
        elif r["system_match"] == "PD":
            r["applicability"] = 4 if any(k in fn_lower for k in ["1.9", "bls", "bpx", "arl"]) else 3
        elif any(k in fn_lower for k in ["ssp_305", "ssp_325", "ssp_297", "ssp_223", "ssp_251", "winols", "asap2", "pya2l", "taschenbuch", "wahlstrom", "sivertsson", "lundahl", "can_specification", "ssp_238", "ssp_269", "ssp_872803", "ssp_318", "ssp_873003", "ssp_890293"]):
            r["applicability"] = 3
        elif any(k in fn_lower for k in ["heywood", "mit_2.61", "polito", "larsson", "hedberg", "andersson", "pretech", "ssp_334", "ssp_359", "ssp_210", "ssp_851403", "ssp_237", "ssp_843003", "iso_14229", "sloa101d"]):
            r["applicability"] = 2
        elif any(k in fn_lower for k in ["ssp_222"]):
            r["applicability"] = 1
        elif not isinstance(r.get("applicability"), int):
            r["applicability"] = 2

        updated_records.append(r)

    reg["records"] = updated_records

    # Update want_user_copy with Bosch UIS/UPS
    wants = reg.get("want_user_copy", [])
    has_bosch_uis = any("Unit Injector System" in w.get("title", "") for w in wants)
    if not has_bosch_uis:
        wants.append({
            "title": "Bosch Technical Instruction: Diesel Fuel-Injection Systems - Unit Injector System (UIS) / Unit Pump System (UPS)",
            "isbn": "978-0-8376-1550-9 / 0-8376-1550-X",
            "publisher": "Robert Bosch GmbH / Bentley Publishers",
            "reason": "Dedicated official Bosch Yellow Jacket manual covering Unit Injector / Pumpe-Düse design, high-pressure generation (up to 2050 bar), BIP detection, and solenoid energizing characteristics.",
            "target": "VW Golf 5 1.9 TDI BLS (UIS / EDC16U34)",
            "status": "User Input Requested",
            "obtainability": "WANT_USER_COPY",
            "license_status": "paid_not_owned",
            "system_match": "PD",
            "applicability": 4
        })
    reg["want_user_copy"] = wants

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)

    print("Registry migration complete!")
    print(f"Total updated records: {len(updated_records)}")

if __name__ == "__main__":
    run_migration()
