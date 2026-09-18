# Literature Curator & Registry Manager
# Multilingual & Alternate Editions Acquisition Protocol
import os
import sys
import json
import hashlib
import requests
from typing import Dict, Any, Optional, List
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
DRAFTS_DIR = os.path.join(BASE_DIR, "knowledge", "drafts")
REGISTRY_PATH = os.path.join(LIBRARY_DIR, "library_registry.json")
INDEX_PATH = os.path.join(LIBRARY_DIR, "LIBRARY_INDEX.md")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

LANG_BADGES = {
    "en": "🇬🇧 EN",
    "de": "🇩🇪 DE",
    "ru": "🇷🇺 RU",
    "pl": "🇵🇱 PL",
    "it": "🇮🇹 IT",
    "fr": "🇫🇷 FR",
    "es": "🇪🇸 ES",
    "zh": "🇨🇳 ZH",
    "ja": "🇯🇵 JA",
    "multilingual": "🌐 Multi"
}

MULTILINGUAL_DOMAIN_TERMS = {
    "turbocharging_vtg": {
        "en": ["turbocharging internal combustion engines", "variable turbine geometry VTG", "VNT boost control", "wastegate dynamics", "Watson Janota turbocharging", "Hiereth Prenninger charging"],
        "de": ["Aufladung der Verbrennungskraftmaschine", "Abgasturbolader VTG", "variable Turbinengeometrie", "Ladedruckregelung", "Hiereth Prenninger Aufladung"],
        "ru": ["турбонаддув двигателей внутреннего сгорания", "турбокомпрессор с изменяемой геометрией", "регулирование давления наддува", "турбина с изменяемой геометрией VNT"],
        "pl": ["doładowanie silników spalinowych", "turbosprężarka zmienna geometria VNT", "sterowanie ciśnieniem doładowania"],
        "fr": ["suralimentation des moteurs thermiques", "turbocompresseur à géométrie variable", "régulation pression suralimentation"],
        "es": ["sobrealimentación de motores de combustión interna", "turbocompresor geometría variable", "control de sobrealimentación"],
        "it": ["sovralimentazione motori combustione interna", "turbocompressore a geometria variabile", "controllo sovralimentazione"],
        "zh": ["内燃机增压", "可变截面涡轮增压器 VTG", "废气涡轮增压控制"]
    },
    "diesel_engine_management_edc": {
        "en": ["Diesel Engine Management Systems and Components", "Electronic Diesel Control EDC16", "Unit Injector System UIS Pumpe Duse", "Bosch diesel handbook"],
        "de": ["Dieselmotor-Management Systeme und Komponenten", "Elektronische Dieselregelung EDC16", "Pumpe-Düse-System UIS PDE", "Konrad Reif Bosch Diesel"],
        "ru": ["Системы управления дизельными двигателями", "электронное управление дизелями EDC16", "насос-форсунка UIS", "справочник Bosch дизель"],
        "pl": ["sterowanie silników z zapłonem samoczynnym", "elektroniczne sterowanie EDC", "pompowtryskiwacze UIS Bosch"],
        "fr": ["gestion des moteurs diesel", "commande électronique diesel EDC", "injecteur-pompe UIS"],
        "es": ["gestión del motor diésel", "control electrónico diésel EDC", "sistema inyector bomba UIS"],
        "it": ["gestione motore diesel", "controllo elettronico diesel EDC", "iniettore pompa UIS"],
        "zh": ["柴油机管理系统", "柴油机电子控制系统 EDC", "泵喷嘴系统 UIS"]
    },
    "automotive_handbook": {
        "en": ["Bosch Automotive Handbook", "Robert Bosch Automotive Handbook 6th 7th 8th 9th 10th", "Bentley Bosch Handbook"],
        "de": ["Kraftfahrtechnisches Taschenbuch Bosch", "Bosch Fachinformation Automobil", "Vieweg Teubner Kraftfahrtechnisches"],
        "ru": ["Автомобильный справочник Bosch", "За рулем автомобильный справочник Бош", "Бош справочник автомобилей"],
        "pl": ["Poradnik techniczny Bosch", "Samochodowy poradnik techniczny Bosch"],
        "fr": ["Mémento de technologie automobile Bosch", "Cahier technique automobile Bosch"],
        "es": ["Manual de la técnica del automóvil Bosch"],
        "it": ["Manuale dell'automobile Bosch", "Manuale della tecnica automobilistica Bosch"],
        "zh": ["博世汽车工程手册", "汽车工程手册 博世"]
    },
    "engine_control_modeling": {
        "en": ["Introduction to Modeling and Control of Internal Combustion Engine Systems", "Guzzella Onder engine control", "mean value engine model MVEM"],
        "de": ["Modellierung und Regelung von Verbrennungsmotoren", "Guzzella Onder Motorsteuerung", "Regelungstechnik Verbrennungskraftmaschinen"],
        "ru": ["моделирование и управление двигателями внутреннего сгорания", "математические модели ДВС Гуццелла"],
        "zh": ["内燃机系统建模与控制导论", "内燃机控制建模"]
    }
}

def get_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inspect_pdf(filepath: str) -> Dict[str, Any]:
    try:
        reader = PdfReader(filepath)
        num_pages = len(reader.pages)
        check_pages = min(8, num_pages)
        chars = [len(reader.pages[i].extract_text() or "") for i in range(check_pages)]
        cpp = sum(chars) / max(1, check_pages)
        cpp_int = round(cpp)
        
        if cpp_int >= 300:
            status = "GOOD"
        elif cpp_int >= 50:
            status = "THIN"
        else:
            status = "NONE"

        return {
            "valid_pdf": True,
            "num_pages": num_pages,
            "text_layer": status,
            "chars_per_page": cpp_int,
            "pages_checked": check_pages
        }
    except Exception as e:
        return {
            "valid_pdf": False,
            "error": str(e),
            "num_pages": 0,
            "text_layer": "NONE",
            "chars_per_page": 0
        }

def expand_multilingual_queries(topic_key: str, target_langs: Optional[List[str]] = None) -> Dict[str, List[str]]:
    terms = MULTILINGUAL_DOMAIN_TERMS.get(topic_key, {})
    if not terms:
        return {}
    if target_langs is None:
        target_langs = ["de", "en", "ru", "pl", "es", "fr", "it", "zh"]
    return {lang: terms[lang] for lang in target_langs if lang in terms}

def load_registry() -> Dict[str, Any]:
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"records": [], "gaps": [], "want_user_copy": []}

def save_registry(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_index_markdown():
    data = load_registry()
    all_records = data.get("records", [])
    gaps = data.get("gaps", [])
    wants = data.get("want_user_copy", [])

    primary_records = [r for r in all_records if r.get("obtainability") != "PROJECT_DRAFT"]
    draft_records = [r for r in all_records if r.get("obtainability") == "PROJECT_DRAFT"]

    good_text_count = sum(1 for r in primary_records if r.get("text_layer") == "GOOD")
    thin_text_count = sum(1 for r in primary_records if r.get("text_layer") == "THIN")
    none_text_count = sum(1 for r in primary_records if r.get("text_layer") == "NONE")
    
    tier_counts: Dict[str, int] = {}
    lang_counts: Dict[str, int] = {}
    sys_counts: Dict[str, int] = {}
    appl_counts: Dict[int, int] = {}
    oem_native_count = 0

    for r in primary_records:
        t = r.get("authority_tier", "Tier C")
        tier_counts[t] = tier_counts.get(t, 0) + 1
        
        lang = r.get("original_language") or r.get("language", "en")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        s = r.get("system_match", "N-A")
        sys_counts[s] = sys_counts.get(s, 0) + 1

        ap = r.get("applicability", 2)
        appl_counts[ap] = appl_counts.get(ap, 0) + 1
        
        is_oem = r.get("is_oem_native", False)
        pub_lower = str(r.get("publisher", "")).lower()
        if not is_oem and lang == "de" and any(k in pub_lower for k in ["bosch", "volkswagen", "audi", "vag"]):
            is_oem = True
        if is_oem:
            oem_native_count += 1

    domains = [
        ("01_engine_physics", "1. Engine fundamentals"),
        ("02_diesel_combustion", "2. Diesel combustion"),
        ("03_injection", "3. Diesel injection"),
        ("04_pumpe_duse", "4. Pumpe-Düse / UIS"),
        ("05_turbo", "5. Turbocharging & VNT"),
        ("06_control_systems", "6. ECU architecture & Control Theory"),
        ("07_edc15", "7. Bosch EDC15"),
        ("08_edc16", "8. Bosch EDC16 & EDC16U34"),
        ("09_edc17", "9. Bosch EDC17"),
        ("10_winols_a2l", "10. WinOLS, A2L & ASAM MCD-2 MC"),
        ("11_diagnostics", "11. Diagnostics & Sensors"),
        ("12_vcds", "12. VCDS & Logging"),
        ("13_protocols", "13. Flashing & Protocols (CAN/KWP/UDS)"),
        ("14_calibration_methodology", "14. Calibration methodology & Limits"),
        ("15_scientific_papers", "15. Scientific papers & Theses"),
        ("16_vw_ssp", "16. VW Self-Study Programs (SSP)"),
        ("17_vehicle_specific_bls", "17. Vehicle specific: VW Golf 5 BLS")
    ]

    domain_counts = {d_folder: 0 for d_folder, _ in domains}
    for r in primary_records:
        folder = r.get("folder", "")
        if folder in domain_counts:
            domain_counts[folder] += 1

    md = []
    md.append("# Technical Research Library: ECU Calibration & Diesel Engine Management")
    md.append("")
    md.append("Autonomous corpus of professional literature, textbooks, OEM manuals, SSPs, patents, and doctoral dissertations.")
    md.append("> **CRITICAL REPOSITORY INVARIANT**: Large binary files (`*.pdf`, `*.epub`) are strictly **gitignored** (`.gitignore`) to avoid bloating the git history and comply with licensing terms. All files remain intact locally on disk. Internal project drafts are stored exclusively in `knowledge/drafts/` with `authority_tier=\"DRAFT\"`.")
    md.append("")
    md.append("## Executive Corpus Summary")
    md.append("")
    md.append(f"- **Total Primary External Documents**: {len(primary_records)}")
    md.append(f"- **Internal Working Drafts (`knowledge/drafts/`)**: {len(draft_records)}")
    md.append(f"- **Text Layer Quality**: Born-Digital / High OCR (`GOOD` >=300 cpp): **{good_text_count}** | Thin (`THIN` 50-299 cpp): **{thin_text_count}** | Scanned / No OCR (`NONE` <50 cpp): **{none_text_count}**")
    md.append(f"- **Fuel System Alignment**: Pumpe-Düse (`PD`): **{sys_counts.get('PD', 0)}** | Common Rail (`CR`): **{sys_counts.get('CR', 0)}** | Distributor (`VP37`): **{sys_counts.get('VP37', 0)}** | In-Line (`INLINE`): **{sys_counts.get('INLINE', 0)}** | General (`N-A`): **{sys_counts.get('N-A', 0)}**")
    md.append(f"- **Target Applicability**: Level 5 (Exact Vehicle/Dump): **{appl_counts.get(5, 0)}** | Level 4 (EDC16U34/BLS/BV39): **{appl_counts.get(4, 0)}** | Level 3 (Generic EDC16/PD): **{appl_counts.get(3, 0)}** | Level 2 (Generic Diesel/Garrett): **{appl_counts.get(2, 0)}** | Level 1 (Other Fuel Systems): **{appl_counts.get(1, 0)}**")
    
    tier_str = ", ".join([f"{k}: {v}" for k, v in sorted(tier_counts.items())])
    md.append(f"- **Tier Breakdown**: {tier_str if tier_str else 'None'}")
    
    lang_str_items = []
    for l_code, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        badge = LANG_BADGES.get(l_code, l_code.upper())
        lang_str_items.append(f"{badge}: {count}")
    md.append(f"- **Linguistic Corpus Distribution**: {', '.join(lang_str_items)}")
    md.append(f"- **German OEM Native Ground Truth (Bosch / VAG)**: {oem_native_count} verified documents")
    md.append(f"- **WANT_USER_COPY (Proprietary / Closed Literature)**: {len(wants)}")
    md.append(f"- **Identified Open Gaps**: {len(gaps)}")
    md.append("")
    md.append("## Domain Coverage Matrix")
    md.append("")
    md.append("| Domain Directory | Topic Name | Verified Docs | Coverage Status |")
    md.append("|---|---|---|---|")
    for d_folder, d_name in domains:
        c = domain_counts.get(d_folder, 0)
        status = "🟢 Strong" if c >= 3 else ("🟡 Covered" if c >= 1 else "🔴 Missing")
        md.append(f"| `{d_folder}` | {d_name} | {c} | {status} |")

    md.append("")
    md.append("## Catalog of Verified Primary Technical Documents")
    md.append("")
    md.append("| # | Title | Author(s) | Year | Sys | Appl | Tier | Lang | Text Layer (cpp) | License | Folder / File |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for idx, r in enumerate(primary_records, 1):
        rel_path = os.path.join(r.get("folder", ""), r.get("filename", "")).replace("\\", "/")
        title = r.get("title", "Unknown").replace("|", "-")
        authors = r.get("authors", "Unknown").replace("|", "-")
        year = r.get("year", "N/A")
        sys_m = r.get("system_match", "N-A")
        appl = r.get("applicability", 2)
        tier = r.get("authority_tier", "Tier B")
        tl = r.get("text_layer", "GOOD")
        cpp = r.get("chars_per_page", 0)
        lic = r.get("license_status", "public")
        
        lang_code = r.get("original_language") or r.get("language", "en")
        is_oem = r.get("is_oem_native", False)
        pub_lower = str(r.get("publisher", "")).lower()
        if not is_oem and lang_code == "de" and any(k in pub_lower for k in ["bosch", "volkswagen", "audi", "vag"]):
            is_oem = True
            
        badge = LANG_BADGES.get(lang_code, lang_code.upper())
        if is_oem:
            lang_display = f"{badge} **[OEM]**"
        else:
            lang_display = badge

        prov = r.get("translation_provenance")
        if prov and isinstance(prov, dict):
            src_ed = prov.get("source_edition", "")
            if src_ed:
                title = f"{title} *(Trans. of {src_ed})*"

        tl_display = f"{tl} ({cpp})"
        if tl == "NONE":
            tl_display = f"⚠️ **NONE ({cpp})**"
        elif tl == "THIN":
            tl_display = f"🟡 THIN ({cpp})"

        appl_display = f"**{appl}**" if appl >= 4 else str(appl)

        md.append(f"| {idx} | **{title}** | {authors} | {year} | `{sys_m}` | {appl_display} | {tier} | {lang_display} | {tl_display} | `{lic}` | [`{rel_path}`]({rel_path}) |")

    if draft_records:
        md.append("")
        md.append("## Internal Project Engineering Drafts (`knowledge/drafts/`)")
        md.append("")
        md.append("> [!NOTE]")
        md.append("> These files represent project syntheses, working hypotheses, and mathematical derivations created internally. They carry `authority_tier=\"DRAFT\"` and `obtainability=\"PROJECT_DRAFT\"` and are NOT external primary evidence.")
        md.append("")
        md.append("| # | Draft Title | Topics | Appl | Path |")
        md.append("|---|---|---|---|---|")
        for idx, r in enumerate(draft_records, 1):
            t = r.get("title", "").replace("|", "-")
            topics = ", ".join(r.get("topics", []))
            ap = r.get("applicability", 4)
            fn = r.get("filename", "")
            md.append(f"| {idx} | **{t}** | {topics} | {ap} | [`knowledge/drafts/{fn}`](../drafts/{fn}) |")

    if wants:
        md.append("")
        md.append("## WANT_USER_COPY (Proprietary / Closed Literature)")
        md.append("")
        md.append("| Item | System | Appl | Reason / Required Material | Target Vehicle / ECU | Status |")
        md.append("|---|---|---|---|---|---|")
        for w in wants:
            item_title = w.get("title", "").replace("|", "-")
            sys_m = w.get("system_match", "N-A")
            ap = w.get("applicability", 3)
            reason = w.get("reason", "").replace("|", "-")
            target = w.get("target", "").replace("|", "-")
            status = w.get("status", "User Input Requested").replace("|", "-")
            md.append(f"| **{item_title}** | `{sys_m}` | {ap} | {reason} | {target} | {status} |")

    if gaps:
        md.append("")
        md.append("## Open Literature Gaps")
        md.append("")
        md.append("| Topic | Targeted Document | Status |")
        md.append("|---|---|---|")
        for g in gaps:
            t = g.get("topic", "").replace("|", "-")
            d = g.get("document", "").replace("|", "-")
            md.append(f"| {t} | {d} | Searching / Investigating |")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("Generated LIBRARY_INDEX.md successfully")

def download_document(
    url: str,
    folder: str,
    filename: str,
    title: str,
    authors: str,
    year: str,
    publisher: str,
    authority_tier: str,
    topics: List[str],
    doc_id: str = "",
    language: str = "en",
    notes: str = "",
    applicability: int = 3,
    system_match: str = "N-A",
    license_status: str = "public",
    obtainability: str = "HAVE_LOCAL",
    timeout: int = 50,
    original_language: str = "en",
    canonical_title: str = "",
    translation_provenance: Optional[Dict[str, Any]] = None,
    is_oem_native: bool = False,
    isbn_multilingual: Optional[Dict[str, str]] = None,
    edition_number: str = ""
) -> Optional[Dict[str, Any]]:
    target_dir = os.path.join(LIBRARY_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8"
    }

    print(f"Downloading: {title} -> {folder}/{filename}")
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
        except requests.exceptions.SSLError:
            print("SSL verification failed, retrying with verify=False...")
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True, verify=False)
        if resp.status_code != 200:
            print(f"Failed HTTP {resp.status_code} for {url}")
            return None

        content_length = resp.headers.get("content-length")
        if content_length and int(content_length) > 95 * 1024 * 1024:
            print(f"Warning: File exceeds 95MB ({content_length} bytes)")

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"Download error: {e}")
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
        return None

    # Verify content
    fmt = "PDF"
    num_pages = 0
    tl_status = "NONE"
    cpp = 0
    with open(target_path, "rb") as f:
        head = f.read(1024)
        if not head.startswith(b"%PDF-"):
            if b"<html" in head.lower() or b"<!doctype html" in head.lower():
                fmt = "HTML"
                num_pages = 1
                tl_status = "GOOD"
                cpp = 1000
            else:
                print(f"File is not valid PDF or HTML: {head[:64]}")
                try:
                    os.remove(target_path)
                except Exception:
                    pass
                return None
        else:
            info = inspect_pdf(target_path)
            if not info["valid_pdf"]:
                print(f"Corrupted PDF: {info.get('error')}")
                try:
                    os.remove(target_path)
                except Exception:
                    pass
                return None
            num_pages = info["num_pages"]
            tl_status = info["text_layer"]
            cpp = info["chars_per_page"]

    sha256 = get_sha256(target_path)
    reg = load_registry()

    for existing in reg.get("records", []):
        if existing.get("sha256") == sha256:
            print(f"Duplicate SHA256 with {existing.get('filename')}. Skipping.")
            os.remove(target_path)
            return existing

    record = {
        "title": title,
        "authors": authors,
        "year": str(year),
        "publisher": publisher,
        "doc_id": doc_id,
        "language": language,
        "original_language": original_language or language,
        "canonical_title": canonical_title or title,
        "edition_number": edition_number,
        "is_oem_native": is_oem_native,
        "translation_provenance": translation_provenance,
        "isbn_multilingual": isbn_multilingual or {},
        "pages": num_pages,
        "source_url": url,
        "file_format": fmt,
        "text_layer": tl_status,
        "chars_per_page": cpp,
        "full_document": "YES",
        "authority_tier": authority_tier,
        "topics": topics,
        "applicability": applicability,
        "system_match": system_match,
        "license_status": license_status,
        "obtainability": obtainability,
        "folder": folder,
        "filename": filename,
        "sha256": sha256,
        "notes": notes
    }

    reg["records"].append(record)
    save_registry(reg)
    generate_index_markdown()
    print(f"Successfully saved: {filename} ({num_pages} pages, text_layer={record['text_layer']})")
    return record

def add_gap(topic: str, document: str):
    reg = load_registry()
    for g in reg.get("gaps", []):
        if g.get("topic") == topic and g.get("document") == document:
            return
    reg["gaps"].append({"topic": topic, "document": document})
    save_registry(reg)
    generate_index_markdown()

def add_want_user_copy(
    title: str,
    reason: str,
    target: str,
    system_match: str = "N-A",
    applicability: int = 3,
    isbn: str = "",
    publisher: str = "",
    status: str = "User Input Requested"
):
    reg = load_registry()
    for w in reg.get("want_user_copy", []):
        if w.get("title") == title:
            w["status"] = status
            w["system_match"] = system_match
            w["applicability"] = applicability
            save_registry(reg)
            generate_index_markdown()
            return
    reg["want_user_copy"].append({
        "title": title,
        "isbn": isbn,
        "publisher": publisher,
        "reason": reason,
        "target": target,
        "status": status,
        "obtainability": "WANT_USER_COPY",
        "license_status": "paid_not_owned",
        "system_match": system_match,
        "applicability": applicability
    })
    save_registry(reg)
    generate_index_markdown()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "index":
            generate_index_markdown()
        elif cmd == "query" and len(sys.argv) > 2:
            q_res = expand_multilingual_queries(sys.argv[2])
            print(json.dumps(q_res, ensure_ascii=False, indent=2))
        elif cmd == "stats":
            data = load_registry()
            print(f"Total Records: {len(data.get('records', []))}")
            print(f"Gaps: {len(data.get('gaps', []))}")
            print(f"Wants: {len(data.get('want_user_copy', []))}")
        else:
            print("Usage: python curator.py [index|stats|query <topic_key>]")
    else:
        generate_index_markdown()
