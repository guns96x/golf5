#!/usr/bin/env python3
"""
kb — локальна база знань ECU calibration.

Принцип: система не «знає» відповідь. Вона знає, де шукати, що вважати доказом,
і коли доказів недостатньо. Цитата, якої немає в інгестованому документі,
не проходить — це перевіряє `kb check`, а не совість моделі.

Команди:
    kb init                       створити/оновити базу
    kb ingest <тека> [--drafts]   інгест PDF/MD/TXT
    kb search "<запит>"           гібридний пошук: точні ідентифікатори + FTS5
    kb status                     що в базі
    kb check                      перевірка цілісності (головний запобіжник)
    kb gaps                       відкриті прогалини
"""
import argparse, hashlib, json, os, re, sqlite3, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB   = ROOT / "knowledge" / "kb.sqlite3"

# Наші власні чернетки, які Gemini позначив Tier A. Вони корисні як гіпотези,
# але джерелом бути не можуть — інакше база підтверджує сама себе.
DRAFT_PUBLISHERS = {"Autonomous Engineering Corpus"}

CHUNK_CHARS, CHUNK_OVERLAP = 1800, 200

# A2L-символи (FlMng_qPresSmoke_MAP), адреси (0x1D6632), парт-номери (03G906021QJ)
RE_A2L   = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}_[A-Za-z0-9_]{3,}\b")
RE_ADDR  = re.compile(r"\b0x[0-9A-Fa-f]{4,8}\b")
RE_PART  = re.compile(r"\b0[0-9A-Z]{2}\s?[0-9]{3}\s?[0-9]{3}\s?[A-Z]{0,2}\b")
RE_SW    = re.compile(r"\b10\d{8}\b|\b39\d{4}\b")


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def cmd_init(a):
    c = connect()
    c.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    c.commit()
    print(f"База готова: {DB}")


# ── читання документів ─────────────────────────────────────────────────────
def read_pdf(path):
    """Повертає (сторінки:list[str], метрика тексту). Не довіряємо чужим звітам."""
    import logging, warnings
    logging.disable(logging.CRITICAL); warnings.filterwarnings("ignore")
    from pypdf import PdfReader
    r = PdfReader(str(path))
    pages = []
    for p in r.pages:
        try:    pages.append(p.extract_text() or "")
        except Exception: pages.append("")
    nonempty = [p for p in pages if p.strip()]
    cpp = int(sum(len(p) for p in nonempty) / max(1, len(pages)))
    layer = "GOOD" if cpp >= 300 else ("THIN" if cpp >= 50 else "NONE")
    return pages, layer, cpp


def read_text(path):
    t = path.read_text(encoding="utf-8", errors="replace")
    return [t], ("GOOD" if len(t) > 300 else "THIN"), len(t)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[ \t ]+", " ", s).strip()


def chunk_pages(pages):
    """Чанкуємо, зберігаючи номери сторінок — без локатора цитата непридатна."""
    out, buf, first = [], "", 1
    for i, raw in enumerate(pages, 1):
        t = norm(raw)
        if not t:
            continue
        if not buf:
            first = i
        buf += ("\n" if buf else "") + t
        while len(buf) >= CHUNK_CHARS:
            cut = buf.rfind(". ", 0, CHUNK_CHARS)
            cut = cut + 1 if cut > CHUNK_CHARS // 2 else CHUNK_CHARS
            out.append((first, i, buf[:cut].strip()))
            buf  = buf[max(0, cut - CHUNK_OVERLAP):].strip()
            first = i
    if buf.strip():
        out.append((first, len(pages), buf.strip()))
    return out


def extract_identifiers(text):
    found = set()
    for rx, kind in ((RE_A2L, "a2l_symbol"), (RE_ADDR, "address"),
                     (RE_PART, "part_number"), (RE_SW, "sw_number")):
        for m in rx.findall(text):
            tok = m.replace(" ", "")
            if len(tok) >= 4:
                found.add((tok, kind))
    return found



# Правила застосовності до ЦІЄЇ машини: Golf 5 / BLS / EDC16U34 / SW 1037391847 / BV39.
# 5 = точний SW або заміряне з цієї машини; 4 = EDC16U34 або BLS;
# 3 = EDC16 загальний чи PD загальний; 2 = дизель загалом; 1 = інша система.
APPLICABILITY_RULES = [
    # (підрядок у назві, applicability, система, примітка)
    ("distributor",   1, "VP37",   "розподільчий ТНВД VP37 — не Pumpe-Duse"),
    ("common rail",   1, "CR",     "Common Rail — не Pumpe-Duse"),
    ("cp1",           1, "CR",     "Common Rail — не Pumpe-Duse"),
    ("einspritzpump", 1, "INLINE", "рядний ТНВД PE/PF — не Pumpe-Duse"),
    ("garrett",       2, "N-A",    "загальна теорія турбін; турбіна тут BorgWarner BV39"),
    ("edc 16",        3, "N-A",    "EDC16 загальний — перевіряй, чи розділ не про R5/V10"),
    ("edc16",         3, "N-A",    "EDC16 загальний"),
    ("edc 17",        1, "CR",     "EDC17/Common Rail — інше покоління"),
    ("edc 15",        2, "VP37",   "EDC15 — попереднє покоління"),
    ("pumpe",         4, "PD",     "Pumpe-Duse — та сама система"),
    ("pump injection",4, "PD",     "Pumpe-Duse — та сама система"),
    ("unit injector", 4, "PD",     "UIS = Pumpe-Duse"),
    ("bls",           5, "PD",     "той самий двигун"),
]


def classify(title):
    """Повертає (applicability, system_match, note) за назвою документа."""
    t = (title or "").lower()
    best = (3, "N-A", "")
    for kw, ap, sysm, note in APPLICABILITY_RULES:
        if kw in t:
            if ap > best[0] or best[2] == "":
                best = (ap, sysm, note)
    return best


def load_registry(lib):
    """Метадані з library_registry.json, якщо він є поруч."""
    reg = {}
    for cand in (lib / "library_registry.json", lib / "knowledge" / "library" / "library_registry.json"):
        if cand.exists():
            d = json.loads(cand.read_text(encoding="utf-8"))
            items = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
            for i in items:
                if isinstance(i, dict) and i.get("filename"):
                    reg[i["filename"]] = i
            break
    return reg


def cmd_ingest(a):
    c   = connect()
    lib = Path(a.path).resolve()
    reg = load_registry(lib)
    files = [p for p in sorted(lib.rglob("*"))
             if p.suffix.lower() in {".pdf", ".md", ".txt"} and p.is_file()]
    print(f"Знайдено файлів: {len(files)}   реєстр: {len(reg)} записів")

    added = skipped = 0
    for p in files:
        digest = sha256(p)
        if c.execute("SELECT 1 FROM documents WHERE sha256=?", (digest,)).fetchone():
            skipped += 1
            continue

        meta      = reg.get(p.name, {})
        publisher = str(meta.get("publisher") or "")
        # Чернетки не стають джерелами. Порядок перевірок важливий:
        # спершу явне поле реєстру, і лише потім евристики — інакше зміна
        # назви видавця мовчки вимикає захист (саме так і сталося одного разу).
        is_draft = (a.drafts
                    or str(meta.get("obtainability", "")).upper() == "PROJECT_DRAFT"
                    or str(meta.get("authority_tier", "")).upper() == "DRAFT"
                    or publisher in DRAFT_PUBLISHERS
                    or "drafts" in p.parts)
        if is_draft:
            obtain, tier, auth = "PROJECT_DRAFT", "DRAFT", 1
        else:
            obtain = "HAVE_LOCAL"
            tier   = (meta.get("authority_tier") or "Tier C").replace("Tier ", "").strip() or "C"
            auth   = {"A": 5, "B": 4, "C": 3, "D": 2}.get(tier, 3)
            applic, sysm, note = classify(meta.get("title") or p.stem)

        try:
            pages, layer, cpp = read_pdf(p) if p.suffix.lower() == ".pdf" else read_text(p)
        except Exception as e:
            print(f"  ! не читається: {p.name} — {str(e)[:60]}")
            continue
        if layer == "NONE":
            print(f"  ~ пропущено (скан без тексту): {p.name}")
            continue

        sid = c.execute(
            """INSERT INTO sources(title,authors,publisher,year,obtainability,tier,
                                   authority,applicability,url,license_note)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (meta.get("title") or p.stem, str(meta.get("authors") or ""), publisher,
             meta.get("year"), obtain, tier, auth,
             1 if is_draft else applic,
             str(meta.get("source_url") or ""),
             "ВЛАСНА ЧЕРНЕТКА — не є зовнішнім джерелом" if is_draft
             else (f"[{sysm}] {note}" if note else ""))).lastrowid

        did = c.execute(
            """INSERT INTO documents(source_id,rel_path,sha256,bytes,pages,text_layer,chars_per_page)
               VALUES(?,?,?,?,?,?,?)""",
            (sid, str(p.relative_to(lib)), digest, p.stat().st_size,
             len(pages), layer, cpp)).lastrowid

        title = meta.get("title") or p.stem
        for n, (pf, pt, body) in enumerate(chunk_pages(pages)):
            prefix = (f"Уривок з «{title}»"
                      + (f" ({publisher}" + (f", {meta['year']}" if meta.get("year") else "") + ")" if publisher else "")
                      + (f", стор. {pf}" + (f"–{pt}" if pt != pf else "") if p.suffix.lower() == ".pdf" else "")
                      + (". УВАГА: власна робоча чернетка, не зовнішнє джерело." if is_draft else "."))
            cid = c.execute(
                """INSERT INTO chunks(document_id,ordinal,page_from,page_to,section,
                                      context_prefix,content,n_chars)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (did, n, pf, pt, None, prefix, body, len(body))).lastrowid
            for tok, kind in extract_identifiers(body):
                c.execute("INSERT OR IGNORE INTO identifiers(token,kind,chunk_id) VALUES(?,?,?)",
                          (tok, kind, cid))
        added += 1
        if added % 10 == 0:
            c.commit(); print(f"  … {added}")

    c.commit()
    n_chunks = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"\nДодано документів: {added}   пропущено (дублікат): {skipped}   чанків усього: {n_chunks}")


# ── пошук ──────────────────────────────────────────────────────────────────
def cmd_search(a):
    c, q = connect(), a.query
    print(f"\n── Точні збіги ідентифікаторів ──")
    rows = c.execute(
        """SELECT DISTINCT i.token, i.kind, d.rel_path, ch.page_from, s.tier, s.obtainability,
                  substr(ch.content,1,180) AS snip
           FROM identifiers i
           JOIN chunks ch    ON ch.id = i.chunk_id
           JOIN documents d  ON d.id  = ch.document_id
           JOIN sources s    ON s.id  = d.source_id
           WHERE i.token = ? COLLATE NOCASE LIMIT ?""", (q.strip(), a.limit)).fetchall()
    if rows:
        for r in rows:
            mark = "ЧЕРНЕТКА" if r["obtainability"] == "PROJECT_DRAFT" else f"Tier {r['tier']}"
            print(f"  [{mark}] {r['rel_path']} стор.{r['page_from']}\n      {r['snip']}…")
    else:
        print("  —")

    print(f"\n── Повнотекстовий пошук ──")
    try:
        fts = c.execute(
            """SELECT ch.id, d.rel_path, ch.page_from, s.tier, s.obtainability, s.title, s.applicability,
                      snippet(chunks_fts,0,'»','«','…',18) AS snip, bm25(chunks_fts) AS score
               FROM chunks_fts
               JOIN chunks ch   ON ch.id = chunks_fts.rowid
               JOIN documents d ON d.id  = ch.document_id
               JOIN sources s   ON s.id  = d.source_id
               WHERE chunks_fts MATCH ?
               ORDER BY (bm25(chunks_fts) + CASE s.obtainability
                            WHEN 'PROJECT_DRAFT' THEN 5.0 ELSE 0 END)
               LIMIT ?""", (q, a.limit)).fetchall()
    except sqlite3.OperationalError as e:
        print(f"  помилка запиту FTS: {e}"); return
    if not fts:
        print("  —\n\n  Доказів у локальній базі недостатньо → це привід створити gap, а не здогадку.")
        return
    for r in fts:
        mark = "ЧЕРНЕТКА" if r["obtainability"] == "PROJECT_DRAFT" else f"Tier {r['tier']}/ap{r['applicability']}"
        print(f"  [{mark}] {str(r['title'])[:58]}  стор.{r['page_from']}")
        print(f"      {r['snip']}")



# ── A2L ────────────────────────────────────────────────────────────────────
RE_CHAR = re.compile(
    r'/begin\s+(CHARACTERISTIC|MEASUREMENT)\s*\n\s*\n?\s*'
    r'([A-Za-z0-9_.]+)\s*\n\s*"([^"]*)"\s*\n\s*(\w+)\s*\n\s*(0x[0-9A-Fa-f]+)?')


def cmd_ingest_a2l(a):
    """A2L — не література, а первинна істина про конкретний SW."""
    c    = connect()
    path = Path(a.path).resolve()
    sw   = a.sw
    # Файл у latin-1. Перекодовувати далі не треба — саме це ламало німецькі описи.
    txt  = path.read_bytes().decode("latin-1")

    n = 0
    for kind, name, desc, otype, addr in RE_CHAR.findall(txt):
        grp = name.split("_")[0] if "_" in name else None
        try:
            c.execute("""INSERT OR IGNORE INTO a2l_objects
                         (sw_number,name,description,obj_type,address,func_group)
                         VALUES(?,?,?,?,?,?)""",
                      (sw, name, desc.strip(), otype, addr or None, grp))
            n += 1
        except sqlite3.Error:
            pass
    c.commit()

    total = c.execute("SELECT COUNT(*) FROM a2l_objects WHERE sw_number=?", (sw,)).fetchone()[0]
    print(f"A2L {path.name}\n  SW {sw}: об'єктів у базі {total}")
    print("\n  найбільші функціональні групи:")
    for r in c.execute("""SELECT func_group g, COUNT(*) n FROM a2l_objects
                          WHERE sw_number=? AND func_group IS NOT NULL
                          GROUP BY g ORDER BY n DESC LIMIT 8""", (sw,)):
        print(f"    {r['g']:12} {r['n']}")


def cmd_a2l(a):
    """Показати об'єкти прошивки за іменем, групою або адресою."""
    c = connect()
    rows = c.execute("""SELECT name,description,obj_type,address,func_group,sw_number
                        FROM a2l_objects
                        WHERE name LIKE ? OR func_group = ? OR address = ?
                        ORDER BY name LIMIT ?""",
                     (f"%{a.query}%", a.query, a.query, a.limit)).fetchall()
    if not rows:
        print("Не знайдено в A2L."); return
    for r in rows:
        print(f"  {r['address'] or '—':10} {r['obj_type']:6} {r['name']}")
        if r["description"]:
            print(f"             {r['description'][:88]}")


def cmd_status(a):
    c = connect()
    def one(q, d=0):
        r = c.execute(q).fetchone()
        return r[0] if r and r[0] is not None else d
    print("── Джерела ──")
    for r in c.execute("""SELECT obtainability, COUNT(*) n FROM sources
                          GROUP BY obtainability ORDER BY n DESC"""):
        print(f"  {r['obtainability']:16} {r['n']}")
    print("\n── Документи ──")
    for r in c.execute("SELECT text_layer, COUNT(*) n FROM documents GROUP BY text_layer"):
        print(f"  текстовий шар {r['text_layer']:5} {r['n']}")
    print(f"\n  чанків       : {one('SELECT COUNT(*) FROM chunks')}")
    print(f"  ідентифікаторів: {one('SELECT COUNT(DISTINCT token) FROM identifiers')}")
    print(f"  тверджень    : {one('SELECT COUNT(*) FROM claims')}")
    print(f"  цитат        : {one('SELECT COUNT(*) FROM citations')}")
    print(f"  конфліктів   : {one('SELECT COUNT(*) FROM conflicts')}")
    n_gaps = one("SELECT COUNT(*) FROM gaps WHERE status='OPEN'")
    print(f"  прогалин OPEN: {n_gaps}")


def cmd_check(a):
    """Головний запобіжник. Детермінований, без моделі."""
    c, fail = connect(), 0
    print("── Перевірка цілісності ──\n")

    bad = c.execute("""
        SELECT cl.id, substr(cl.statement,1,70) s, cl.evidence_kind
        FROM claims cl LEFT JOIN citations ci ON ci.claim_id = cl.id
        WHERE cl.evidence_kind IN ('OEM_DOCUMENTED','STANDARD','TEXTBOOK')
          AND ci.id IS NULL""").fetchall()
    print(f"1. Документовані твердження без цитати: {len(bad)}")
    for r in bad[:10]:
        print(f"   ✗ #{r['id']} [{r['evidence_kind']}] {r['s']}…")
    fail += len(bad)

    # Порівнюємо з нормалізованими пробілами — інакше перенос рядка в PDF
    # дає хибне спрацювання. Перевірка все одно детермінована, без моделі.
    ws = lambda t: " ".join((t or "").split())
    ghost = []
    for r in c.execute("""SELECT ci.id, ci.claim_id, ci.quote, ch.content
                          FROM citations ci JOIN chunks ch ON ch.id = ci.chunk_id"""):
        if ws(r["quote"]) not in ws(r["content"]):
            ghost.append(r)
    print(f"\n2. Цитати, яких НЕМАЄ в тексті чанка: {len(ghost)}")
    for r in ghost[:10]:
        print(f"   ✗ цитата #{r['id']} (claim #{r['claim_id']}): «{ws(r['quote'])[:60]}…»")
    fail += len(ghost)

    selfref = c.execute("""
        SELECT cl.id, substr(cl.statement,1,70) s
        FROM claims cl
        JOIN citations ci ON ci.claim_id = cl.id
        JOIN chunks ch    ON ch.id = ci.chunk_id
        JOIN documents d  ON d.id  = ch.document_id
        JOIN sources sr   ON sr.id = d.source_id
        WHERE sr.obtainability = 'PROJECT_DRAFT'
          AND cl.evidence_kind IN ('OEM_DOCUMENTED','STANDARD','TEXTBOOK')""").fetchall()
    print(f"\n3. Твердження, що цитують ВЛАСНУ чернетку як джерело: {len(selfref)}")
    for r in selfref[:10]:
        print(f"   ✗ #{r['id']} {r['s']}…")
    fail += len(selfref)

    scope = c.execute("""
        SELECT id, substr(statement,1,70) s FROM claims
        WHERE ecu_variant IS NOT NULL AND (sw_number IS NULL OR sw_number='')""").fetchall()
    print(f"\n4. Твердження про конкретний ECU без номера SW: {len(scope)}")
    fail += len(scope)

    print("\n" + ("✓ ПРОЙДЕНО — порушень немає" if fail == 0
                  else f"✗ ПРОВАЛЕНО — {fail} порушень"))
    return 1 if fail else 0


def cmd_gaps(a):
    c = connect()
    rows = c.execute("""SELECT id,priority,status,question,needed_source FROM gaps
                        WHERE status!='RESOLVED' ORDER BY priority, id""").fetchall()
    if not rows:
        print("Відкритих прогалин немає."); return
    for r in rows:
        print(f"[P{r['priority']}] {r['status']:11} {r['question']}")
        if r["needed_source"]:
            print(f"            потрібно: {r['needed_source']}")


def main():
    ap = argparse.ArgumentParser(prog="kb", description="Локальна база знань ECU calibration")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init").set_defaults(fn=cmd_init)
    p = sp.add_parser("ingest"); p.add_argument("path")
    p.add_argument("--drafts", action="store_true", help="все як власні чернетки")
    p.set_defaults(fn=cmd_ingest)
    p = sp.add_parser("search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_search)
    p = sp.add_parser("ingest-a2l"); p.add_argument("path")
    p.add_argument("--sw", required=True, help="номер SW, напр. 1037391847")
    p.set_defaults(fn=cmd_ingest_a2l)
    p = sp.add_parser("a2l"); p.add_argument("query")
    p.add_argument("--limit", type=int, default=20); p.set_defaults(fn=cmd_a2l)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    sp.add_parser("check").set_defaults(fn=cmd_check)
    sp.add_parser("gaps").set_defaults(fn=cmd_gaps)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:      # `| head` / `| more` — не помилка
        os._exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
