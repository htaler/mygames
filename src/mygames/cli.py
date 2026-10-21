import argparse
import difflib
import importlib
from pathlib import Path

from . import config, db
from .matching import Game, group, normalize, play_on
from .report import render
from .sources import csv_import

API_SOURCES = ["steam", "gog", "epic", "amazon", "itch"]


def _source(name: str):
    return importlib.import_module(f".sources.{name}", __package__)


def _games(conn) -> list[Game]:
    aliases, ignore = config.aliases()
    return group(db.all_rows(conn), config.priority(), aliases, ignore)


def _print_game(game: Game, priority: list[str]) -> None:
    best = play_on(game, priority)
    # Show the store's own title only where it differs, so merges are visible.
    owned = ", ".join(o.platform if o.title == game.title else f"{o.platform} ({o.title})" for o in game.owned)
    print(f"{game.title}\n  owned on: {owned}\n  play on:  {best.upper()}")


def cmd_login(args) -> None:
    _source(args.platform).login()


def cmd_sync(args) -> None:
    conn = db.connect()
    failed = []
    for name in args.platforms or API_SOURCES:
        if not args.platforms and not _source(name).is_configured():
            print(f"{name}: skipped (not logged in; run `mygames login {name}`)")
            continue
        try:
            games = _source(name).fetch()
        except (SystemExit, Exception) as e:
            print(f"{name}: FAILED: {e}")
            failed.append(name)
            continue
        db.replace_platform(conn, name, games)
        print(f"{name}: {len(games)} games")
    if failed:
        raise SystemExit(1)


def cmd_import(args) -> None:
    platform = args.platform.lower()
    if platform in API_SOURCES:
        raise SystemExit(f"{platform} syncs from its API; use `mygames sync {platform}`.")
    games = csv_import.read(Path(args.file), platform)
    db.replace_platform(db.connect(), platform, games)
    print(f"{platform}: imported {len(games)} games")


def cmd_find(args) -> None:
    games = _games(db.connect())
    priority = config.priority()
    terms = normalize(" ".join(args.query)).split()
    hits = [g for g in games if all(t in g.key for t in terms)]
    if not hits:
        by_key = {g.key: g for g in games}
        close = difflib.get_close_matches(" ".join(terms), by_key, n=5, cutoff=0.6)
        if not close:
            print("Not owned anywhere (as far as the database knows).")
            return
        print("No exact match. Did you mean:\n")
        hits = [by_key[k] for k in close]
    for game in hits:
        _print_game(game, priority)
        print()


def cmd_dupes(args) -> None:
    priority = config.priority()
    dupes = [g for g in _games(db.connect()) if g.is_duplicate]
    for game in dupes:
        _print_game(game, priority)
        print()
    print(f"{len(dupes)} games owned on more than one platform.")


def cmd_status(args) -> None:
    conn = db.connect()
    print(f"data dir: {config.HOME}")
    for platform, count, synced in db.platform_summary(conn):
        print(f"  {platform:<10} {count:>5} games   synced {synced}")
    games = _games(conn)
    print(f"  {'total':<10} {len(games):>5} unique, {sum(g.is_duplicate for g in games)} owned twice+")


def cmd_report(args) -> None:
    out = Path(args.out)
    out.write_text(render(_games(db.connect()), config.priority()), encoding="utf-8")
    print(f"Wrote {out.resolve()}")


def main() -> None:
    p = argparse.ArgumentParser(prog="mygames", description="Where do I own this game, and where should I play it?")
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("login", help="one-time setup for a store")
    s.add_argument("platform", choices=API_SOURCES)
    s.set_defaults(func=cmd_login)

    s = sub.add_parser("sync", help="refresh libraries from store APIs (default: all logged-in)")
    s.add_argument("platforms", nargs="*", choices=API_SOURCES, metavar="platform")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("import", help="import a CSV / title list for a store without an API")
    s.add_argument("platform", help="e.g. ea, ubisoft, amazon, itch")
    s.add_argument("file")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("find", help="search your library")
    s.add_argument("query", nargs="+")
    s.set_defaults(func=cmd_find)

    sub.add_parser("dupes", help="games owned on 2+ platforms").set_defaults(func=cmd_dupes)
    sub.add_parser("status", help="what is in the database").set_defaults(func=cmd_status)

    s = sub.add_parser("report", help="write a searchable HTML report")
    s.add_argument("--out", default="mygames-report.html")
    s.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
