"""
OCR Ingestion Pipeline for Scanned Technical PDFs.
Uses native Windows OCR (winocr) + PyMuPDF.
Strictly operates on Drive D: without polluting Drive C:.
"""

import asyncio
import hashlib
import io
import os
import re
import sqlite3
import sys
from pathlib import Path
from PIL import Image
import pymupdf
import winocr

REPO_ROOT = Path("D:/golf5-ecu-system")
DB_PATH = REPO_ROOT / "ecu-kb" / "knowledge" / "kb.sqlite3"
SCRATCH_DIR = REPO_ROOT / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Set environment variables to keep all temp operations on Drive D:
os.environ["TMP"] = str(SCRATCH_DIR)
os.environ["TEMP"] = str(SCRATCH_DIR)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


async def ocr_page_if_needed(page, page_num: int) -> str:
    # 1. Try digital text extraction first
    text = page.get_text().strip()
    if len(text) >= 50:
        return text

    # 2. If no text or very short, use hardware-accelerated Windows OCR
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    try:
        res = await winocr.recognize_pil(img, lang="en-US")
        extracted = (res.text or "").strip()
        return extracted
    except Exception as e:
        print(f"    [Warning] OCR error on page {page_num}: {e}")
        return ""


def split_into_chunks(pages_text: list[tuple[int, str]], target_size=800) -> list[dict]:
    """Splits extracted page texts into clean semantic chunks."""
    chunks = []
    current_text = []
    current_chars = 0
    start_page = 1

    for page_num, text in pages_text:
        if not text:
            continue
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for p in paragraphs:
            # Clean up hyphenation and excessive spaces
            clean_p = re.sub(r"(\w+)-\s*\n(\w+)", r"\1\2", p)
            clean_p = re.sub(r"\s+", " ", clean_p)
            if not clean_p:
                continue

            if not current_text:
                start_page = page_num

            current_text.append(clean_p)
            current_chars += len(clean_p) + 1

            if current_chars >= target_size:
                chunk_body = "\n\n".join(current_text)
                chunks.append({
                    "page_from": start_page,
                    "page_to": page_num,
                    "content": chunk_body,
                    "n_chars": len(chunk_body)
                })
                current_text = []
                current_chars = 0

    # Remaining text
    if current_text:
        chunk_body = "\n\n".join(current_text)
        chunks.append({
            "page_from": start_page,
            "page_to": pages_text[-1][0] if pages_text else start_page,
            "content": chunk_body,
            "n_chars": len(chunk_body)
        })

    return chunks


async def process_pdf(pdf_path: Path, title: str, tier: str = "A", publisher: str = "Bosch"):
    print(f"\n=======================================================")
    print(f" Processing: {pdf_path.name}")
    print(f" Size: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"=======================================================")

    file_hash = sha256_file(pdf_path)
    file_bytes = pdf_path.stat().st_size

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Check if document already exists
    existing = conn.execute("SELECT id FROM documents WHERE sha256 = ?", (file_hash,)).fetchone()
    if existing:
        print(f"Document already ingested with ID {existing['id']}! Skipping.")
        conn.close()
        return

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    print(f"Total pages to process: {total_pages}")

    pages_text = []
    total_chars = 0

    for i in range(total_pages):
        page = doc[i]
        page_num = i + 1
        t = await ocr_page_if_needed(page, page_num)
        pages_text.append((page_num, t))
        total_chars += len(t)
        if page_num % 10 == 0 or page_num == total_pages:
            print(f"  Processed {page_num}/{total_pages} pages ({total_chars} total chars)...")

    avg_chars = total_chars // total_pages if total_pages > 0 else 0
    text_layer = "GOOD" if avg_chars > 150 else ("THIN" if avg_chars > 30 else "NONE")

    print(f"Extraction complete: {total_chars} chars, avg {avg_chars} chars/page, layer: {text_layer}")

    chunks = split_into_chunks(pages_text, target_size=800)
    print(f"Generated {len(chunks)} text chunks.")

    # Insert source if not present
    source_row = conn.execute("SELECT id FROM sources WHERE title = ?", (title,)).fetchone()
    if source_row:
        source_id = source_row["id"]
    else:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sources(title, publisher, obtainability, tier, authority, applicability)
            VALUES (?, ?, 'HAVE_LOCAL', ?, 5, 4)
        """, (title, publisher, tier))
        source_id = cur.lastrowid

    # Insert document
    cur = conn.cursor()
    rel_path = str(pdf_path.relative_to(REPO_ROOT / "base-knowledge" / "library")).replace("\\", "/")
    cur.execute("""
        INSERT INTO documents(source_id, rel_path, sha256, bytes, pages, text_layer, chars_per_page)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (source_id, rel_path, file_hash, file_bytes, total_pages, text_layer, avg_chars))
    doc_id = cur.lastrowid

    # Insert chunks
    context_prefix = f"{title} [{publisher}]"
    for idx, ch in enumerate(chunks):
        cur.execute("""
            INSERT INTO chunks(document_id, ordinal, page_from, page_to, context_prefix, content, n_chars)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, idx, ch["page_from"], ch["page_to"], context_prefix, ch["content"], ch["n_chars"]))

    conn.commit()
    conn.close()
    print(f"Successfully ingested {len(chunks)} chunks into kb.sqlite3 for document ID {doc_id}!")


async def main():
    library_dir = REPO_ROOT / "base-knowledge" / "library"

    # 2. Heywood 1988 Fundamentals
    heywood_pdf = library_dir / "01_engine_physics" / "Heywood_1988_Internal_Combustion_Engine_Fundamentals_Complete.pdf"
    if heywood_pdf.exists():
        await process_pdf(
            heywood_pdf,
            title="Internal Combustion Engine Fundamentals",
            tier="A",
            publisher="McGraw-Hill (John B. Heywood)"
        )
    else:
        print(f"Not found: {heywood_pdf}")


if __name__ == "__main__":
    asyncio.run(main())
