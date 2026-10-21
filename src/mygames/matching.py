"""Cross-store title matching: the same game is titled differently per store.

normalize() is deliberately conservative. It drops edition and branding noise
but keeps years and numerals, because "DOOM" and "DOOM (1993)" really are
different games. Anything it gets wrong is fixed in aliases.toml.
"""

import re
import unicodedata
from dataclasses import dataclass, field

_SYMBOLS = re.compile(r"[™®©]")
# Stripped only when followed by "Edition": bare "Gold" or "Royal" can be part of a real title.
_EDITION_WORDS = (
    r"definitive|enhanced|ultimate|deluxe|digital deluxe|gold|premium|special"
    r"|anniversary|standard|collector'?s|legendary|royal|complete|extended|game of the year"
)
# Only trailing suffixes, e.g. "X: Game of the Year Edition", "X - Director's Cut", "X GOTY".
_EDITION_SUFFIX = re.compile(
    rf"[\s:\-–—]*\(?\b(?:(?:{_EDITION_WORDS})\s+edition|edition|goty|game of the year|complete"
    rf"|(?:director'?s|(?:the )?final) cut)\)?\s*$"
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(title: str) -> str:
    # Strip symbols before NFKD, which would otherwise expand ™ into "TM".
    t = unicodedata.normalize("NFKD", _SYMBOLS.sub("", title))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.casefold().replace("&", " and ").replace("’", "'")
    # Strip stacked suffixes like "Enhanced Edition Director's Cut".
    while True:
        stripped = _EDITION_SUFFIX.sub("", t).strip()
        if stripped == t or not stripped:
            break
        t = stripped
    t = _NON_ALNUM.sub(" ", t.replace("'", "")).strip()
    if t.startswith("the "):
        t = t[4:]
    return t


@dataclass
class Ownership:
    platform: str
    store_id: str
    title: str
    playtime_min: int | None = None


@dataclass
class Game:
    key: str
    title: str
    owned: list[Ownership] = field(default_factory=list)

    @property
    def platforms(self) -> list[str]:
        return sorted({o.platform for o in self.owned})

    @property
    def is_duplicate(self) -> bool:
        return len(self.platforms) > 1


def rank(platform: str, priority: list[str]) -> tuple[int, str]:
    return (priority.index(platform) if platform in priority else len(priority), platform)


def play_on(game: Game, priority: list[str]) -> str:
    return min(game.platforms, key=lambda p: rank(p, priority))


def group(
    rows: list[Ownership],
    priority: list[str],
    aliases: dict[str, str] | None = None,
    ignore: list[str] | None = None,
) -> list[Game]:
    """Group store rows into games. Display title comes from the preferred platform."""
    alias_keys = {normalize(k): normalize(v) for k, v in (aliases or {}).items()}
    alias_titles = {normalize(v): v for v in (aliases or {}).values()}
    ignored = {normalize(t) for t in (ignore or [])}

    games: dict[str, Game] = {}
    for row in rows:
        key = normalize(row.title)
        if key in ignored:
            continue
        key = alias_keys.get(key, key)
        games.setdefault(key, Game(key=key, title=row.title)).owned.append(row)

    for game in games.values():
        game.owned.sort(key=lambda o: rank(o.platform, priority))
        game.title = alias_titles.get(game.key, game.owned[0].title)
    return sorted(games.values(), key=lambda g: g.key)
