#!/usr/bin/env python3
"""
bench-retrieval — базова лінія якості пошуку.

Без цього будь-яке «стало краще» лишається на віру. Міряє, а не здогадується.

Випадки живуть у bench/retrieval.jsonl і навмисно НЕ прив'язані до chunk_id:
id змінюються на кожному переінгесті, а очікування має пережити перебудову бази.
Тому перевіряється властивість результату (який документ, який текст, яка адреса),
а не його номер.

    python bench_retrieval.py            прогін, підсумок
    python bench_retrieval.py -v         показати кожен випадок
    python bench_retrieval.py --save     записати базову лінію у bench/baseline.json
    python bench_retrieval.py --compare  порівняти з базовою лінією
"""
import argparse, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB   = ROOT / "knowledge" / "kb.sqlite3"
CASES = ROOT / "bench" / "retrieval.jsonl"
BASE  = ROOT / "bench" / "baseline.json"


def connect():
    if not DB.exists():
        sys.exit(f"Бази немає: {DB}\nСпершу: python kb.py init && python kb.py ingest …")
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    return c


def fts_rows(c, query, k):
    """Той самий шлях, яким шукає kb search — інакше бенчмарк міряв би не те."""
    try:
        return c.execute("""
            SELECT s.title, s.obtainability, ch.content, ch.page_from
            FROM chunks_fts
            JOIN chunks ch   ON ch.id = chunks_fts.rowid
            JOIN documents d ON d.id  = ch.document_id
            JOIN sources s   ON s.id  = d.source_id
            WHERE chunks_fts MATCH ?
              AND s.obtainability != 'PROJECT_DRAFT'
            ORDER BY bm25(chunks_fts) LIMIT ?""", (query, k)).fetchall()
    except sqlite3.OperationalError:
        return []


def like(value, pattern):
    """SQL-подібний LIKE у Python, щоб не ганяти зайвий запит."""
    import re
    rx = "^" + re.escape(pattern).replace("%", ".*").replace("\\%", ".*") + "$"
    return re.search(rx, value or "", re.I | re.S) is not None


def run_case(c, case):
    kind = case.get("kind", "fts")
    k    = case.get("k", 5)

    if kind == "a2l":
        rows = c.execute("SELECT name,address,obj_type FROM a2l_objects WHERE name=?",
                         (case["query"],)).fetchall()
        if not rows:
            return False, "символ не знайдено"
        r = rows[0]
        if "expect_address" in case and (r["address"] or "").lower() != case["expect_address"].lower():
            return False, f"адреса {r['address']} ≠ {case['expect_address']}"
        return True, r["address"] or r["obj_type"]

    if kind == "a2l_group":
        n = c.execute("SELECT COUNT(*) FROM a2l_objects WHERE func_group=?",
                      (case["query"],)).fetchone()[0]
        ok = n >= case.get("expect_min_count", 1)
        return ok, f"{n} об'єктів"

    rows = fts_rows(c, case["query"], k)
    if kind == "negative":
        # Не провал сам по собі: фіксуємо, ЩО саме видається на питання без відповіді.
        top = rows[0]["title"][:40] if rows else "—"
        return True, f"{len(rows)} рез., топ: {top}"

    if not rows:
        return False, "нічого не знайдено"

    if "forbid_top1_doc_like" in case:
        if like(rows[0]["title"], case["forbid_top1_doc_like"]):
            return False, f"заборонене перше: {rows[0]['title'][:44]}"
        return True, rows[0]["title"][:44]

    if "forbid_doc_like" in case:
        bad = [r["title"] for r in rows if like(r["title"], case["forbid_doc_like"])]
        if bad:
            return False, f"у видачі: {bad[0][:44]}"
        return True, f"{len(rows)} рез., забороненого немає"

    if "expect_doc_like" in case:
        for i, r in enumerate(rows, 1):
            if like(r["title"], case["expect_doc_like"]):
                return True, f"позиція {i}: {r['title'][:44]}"
        return False, f"немає в топ-{k}; перший: {rows[0]['title'][:40]}"

    if "expect_text_like" in case:
        for i, r in enumerate(rows, 1):
            if like(r["content"], case["expect_text_like"]):
                return True, f"позиція {i}: {r['title'][:44]}"
        return False, f"тексту немає в топ-{k}"

    return True, f"{len(rows)} рез."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--save", action="store_true", help="записати як базову лінію")
    ap.add_argument("--compare", action="store_true", help="порівняти з базовою лінією")
    a = ap.parse_args()

    c = connect()
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]

    results, by_kind = {}, {}
    for case in cases:
        ok, detail = run_case(c, case)
        results[case["id"]] = ok
        kind = case.get("kind", "fts")
        by_kind.setdefault(kind, [0, 0])
        by_kind[kind][1] += 1
        if ok: by_kind[kind][0] += 1
        if a.verbose or not ok:
            mark = "✓" if ok else "✗"
            print(f"  {mark} {case['id']:5} {case['query'][:38]:40} {detail}")

    print("\n── за типами ──")
    for kind, (ok, total) in sorted(by_kind.items()):
        label = {"a2l":"точні символи A2L","a2l_group":"групи A2L","fts":"повнотекстовий",
                 "scope":"область дії","negative":"питання без відповіді"}.get(kind, kind)
        bar = "" if kind == "negative" else f"  {100*ok/total:.0f}%"
        print(f"  {label:24} {ok}/{total}{bar}")

    scored = {k: v for k, v in results.items() if not k.startswith("N")}
    total_ok = sum(scored.values())
    recall = 100 * total_ok / len(scored)
    print(f"\nRECALL: {total_ok}/{len(scored)} = {recall:.1f}%")

    if a.save:
        BASE.write_text(json.dumps({"recall": recall, "results": results},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Базову лінію записано: {BASE.name}")

    if a.compare and BASE.exists():
        old = json.loads(BASE.read_text(encoding="utf-8"))
        delta = recall - old["recall"]
        print(f"\nПроти базової лінії: {old['recall']:.1f}% → {recall:.1f}%  ({delta:+.1f})")
        regressed = [k for k, v in old["results"].items() if v and not results.get(k)]
        fixed     = [k for k, v in old["results"].items() if not v and results.get(k)]
        if regressed: print(f"  ✗ зламалось: {', '.join(regressed)}")
        if fixed:     print(f"  ✓ полагодилось: {', '.join(fixed)}")
        if not regressed and not fixed: print("  без змін")

    return 0


if __name__ == "__main__":
    sys.exit(main())
