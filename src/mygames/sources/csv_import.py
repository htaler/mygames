"""Manual lists for stores without a usable API (EA app, Ubisoft Connect, Amazon, itch.io...).

CSV needs a `title` column; an `id` column is optional. One title per line with no
header also works. Importing replaces everything previously imported for that platform.
"""

import csv
from pathlib import Path

from ..matching import Ownership


def read(path: Path, platform: str) -> list[Ownership]:
    text = path.read_text(encoding="utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = [h.strip().lower() for h in next(csv.reader([lines[0]]))]
    if "title" in header:
        rows = [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(lines)]
        titles = [(r.get("id") or r["title"], r["title"]) for r in rows if r.get("title")]
    else:
        titles = [(line.strip(), line.strip()) for line in lines]
    return [Ownership(platform, store_id, title) for store_id, title in titles]
