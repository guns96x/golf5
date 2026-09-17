#!/usr/bin/env python3
"""
tidy — прибирає корінь проєкту, щоб агент не витрачав токени на шум.

Нічого НЕ видаляє: переносить у archive/ через `git mv`, тож усе зворотно
і історія зберігається.

    python scripts/tidy.py            показати план (нічого не робить)
    python scripts/tidy.py --apply    виконати
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Лишається в корені — решта їде в archive/
KEEP = {
    "CLAUDE.md", "README.md", "START-HERE.md", ".gitignore", ".gitattributes",
    "requirements.txt", "pyproject.toml", "kb.py", "schema.sql",
}
KEEP_DIRS = {
    ".git", ".claude", "tools", "tests", "scripts", "docs", "knowledge",
    "logs", "diagnostic-review", "archive", "ecu-kb", ".venv", "__pycache__",
}
# Розширення, що в корені є сміттям за визначенням
JUNK_EXT = {".png", ".jpg", ".ps1", ".pcap", ".txt", ".whl", ".cer"}


def plan():
    moves = []
    for p in sorted(ROOT.iterdir()):
        if p.name in KEEP or p.name in KEEP_DIRS:
            continue
        if p.is_dir():
            continue                      # теки не чіпаємо
        if p.suffix.lower() in JUNK_EXT:
            moves.append((p, "archive/scratch"))
        elif p.suffix == ".py":
            moves.append((p, "archive/oneoff-scripts"))
        elif p.suffix == ".bin":
            moves.append((p, "firmware"))  # BIN — не сміття, але й не корінь
        elif p.suffix in {".md"}:
            moves.append((p, "docs/notes"))
    return moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    moves = plan()
    if not moves:
        print("Корінь уже чистий.")
        return

    by_dest = {}
    for src, dest in moves:
        by_dest.setdefault(dest, []).append(src.name)
    for dest, names in sorted(by_dest.items()):
        print(f"\n{dest}/  ({len(names)} файлів)")
        for n in names[:6]:
            print(f"    {n}")
        if len(names) > 6:
            print(f"    … ще {len(names)-6}")

    rest = len([p for p in ROOT.iterdir()]) - len(moves)
    print(f"\nУ корені залишиться: {rest} елементів (було {len(list(ROOT.iterdir()))})")

    if not a.apply:
        print("\nЦе лише план. Запусти з --apply, щоб виконати.")
        return

    tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.split("\n"))
    for src, dest in moves:
        d = ROOT / dest
        d.mkdir(parents=True, exist_ok=True)
        if src.name in tracked:
            subprocess.run(["git", "mv", src.name, f"{dest}/{src.name}"], cwd=ROOT, check=False)
        else:
            src.rename(d / src.name)
    print(f"\nПеренесено: {len(moves)}. Нічого не видалено — усе в archive/, firmware/, docs/notes/.")
    print("Перевір `git status`, потім комітни.")


if __name__ == "__main__":
    main()
