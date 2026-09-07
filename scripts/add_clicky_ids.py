#!/usr/bin/env python3
"""Stamp stable ``data-clicky-id`` attributes onto every editable box in cs198-analogy.html.

Insight cards   (<div class="insight mall|silicon|why">)  ->  ins-001, ins-002, ...
Code panels     (<figure class="code-panel">)             ->  code-001, code-002, ...

Idempotent: boxes that already carry an id are left alone; new boxes get the next
number after the current maximum for their prefix, in document order.

Usage:  python3 scripts/add_clicky_ids.py [path/to/cs198-analogy.html]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cs198-analogy.html"

KINDS = [
    # (prefix, regex matching the opening tag)
    ("ins", re.compile(r'<div class="insight(?: [a-z]+)*"[^>]*>')),
    ("code", re.compile(r'<figure class="code-panel"[^>]*>')),
]


def stamp(html: str) -> tuple[str, dict]:
    stats = {}
    for prefix, tag_re in KINDS:
        existing = [int(n) for n in re.findall(rf'data-clicky-id="{prefix}-(\d+)"', html)]
        counter = max(existing, default=0)
        added = 0

        def repl(m, prefix=prefix):
            nonlocal counter, added
            tag = m.group(0)
            if "data-clicky-id=" in tag:
                return tag
            counter += 1
            added += 1
            return tag[:-1] + f' data-clicky-id="{prefix}-{counter:03d}">'

        html = tag_re.sub(repl, html)
        stats[prefix] = {"existing": len(existing), "added": added, "total": counter}
    return html, stats


def main() -> None:
    original = TARGET.read_text(encoding="utf-8")
    # Only stamp the article body, never script/style text that may mention these tags.
    start = original.index('<main id="content">')
    end = original.index("</main>", start)
    body, stats = stamp(original[start:end])
    updated = original[:start] + body + original[end:]
    if updated != original:
        TARGET.write_text(updated, encoding="utf-8")
    for prefix, s in stats.items():
        print(f"{prefix}: existing={s['existing']} added={s['added']} total={s['total']}")


if __name__ == "__main__":
    main()
