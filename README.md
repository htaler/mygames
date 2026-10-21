# mygames

**Where do I own this game, and where should I play it?**

`mygames` builds a local database of every game you own across PC stores. When you
own the same game on several stores, it tells you which one to play it on.

It solves two everyday problems:

- **Buying a game twice.** Before buying, run `mygames find <title>` to see if you
  already own it on another store.
- **Playing on the wrong store.** If you own a game on Steam and on GOG, it tells
  you to play it on Steam, or on whichever store you rank first.

```
$ mygames find witcher 3
The Witcher 3: Wild Hunt
  owned on: steam, gog (The Witcher 3: Wild Hunt - Game of the Year Edition), epic
  play on:  STEAM
```

## Supported stores

| Store | How it syncs | Login |
|---|---|---|
| **Steam** | Official Steam Web API | API key + your profile |
| **GOG** | GOG Galaxy's OAuth login and the gog.com library endpoint | Browser login |
| **Epic Games** | [legendary](https://github.com/derrod/legendary) | Browser login |
| **Amazon Games / Prime Gaming** | [nile](https://github.com/imLinguin/nile) | Browser login |
| **itch.io** | Official itch.io server-side API | API key |
| **EA app (Origin), Ubisoft Connect, anything else** | Manual list import | — |

Only Steam and itch.io have official APIs. GOG, Epic and Amazon use the same
unofficial logins as the open-source launchers Heroic, legendary and nile. They can
break if a store changes something on its side.

## Requirements

- macOS (the Amazon login reads from the clipboard with `pbpaste`; everything else is
  plain Python and should work elsewhere, but is only tested on macOS)
- [uv](https://docs.astral.sh/uv/) (it installs Python 3.11+ for you if needed)
- `git` (only for Amazon)

`mygames` has no Python dependencies outside the standard library. legendary (Epic)
and nile (Amazon) are downloaded and run by uv on first use; you don't install them.

## Installation

```sh
git clone <this repo> mygames
cd mygames
uv tool install -e .     # puts `mygames` on your PATH
```

Or skip the install and run everything from the project folder with
`uv run mygames …`.

## Setup: log in to your stores (once)

Run these in your own terminal. Some of them ask you to type or paste something.
Skip any store you don't use.

### Steam

```sh
mygames login steam
```

1. Get a Web API key at <https://steamcommunity.com/dev/apikey>. For the domain
   field, any name works, e.g. `localhost`.
2. Paste the key, then your profile URL, custom profile name, or 17-digit SteamID64.

> **Your Steam profile's game details must be public.** Go to Steam → Profile →
> Edit Profile → Privacy Settings → **Game details: Public**. If they're private,
> Steam returns an empty library and the sync fails with a hint about this.

### GOG

```sh
mygames login gog
```

A browser window opens with the GOG login. After you log in you land on a mostly
blank page. Copy its full URL (it contains `?code=…`) and paste it into the terminal.

### Epic Games

```sh
mygames login epic
```

This runs `legendary auth`, which walks you through the Epic login in your browser.

### Amazon Games / Prime Gaming

```sh
mygames login amazon
```

1. A browser window opens. Log in to Amazon.
2. When you end up on amazon.com, **copy** the full URL from the address bar
   (<kbd>Cmd</kbd>+<kbd>L</kbd>, <kbd>Cmd</kbd>+<kbd>C</kbd>). **Don't paste it** into the terminal.
3. Switch back to the terminal and press <kbd>Enter</kbd>. `mygames` reads the URL from your clipboard.

The URL comes from the clipboard because macOS terminals drop pasted lines longer
than 1024 characters, and Amazon's redirect URL is longer than that.

On first use, `mygames` downloads nile into `~/.config/mygames/tools/`. It is pinned
to a fixed release, because nile can't be installed as a regular Python package.

### itch.io

```sh
mygames login itch
```

Create an API key at <https://itch.io/user/settings/api-keys> and paste it in. The
key is checked against your profile before it's saved.

## Everyday use

```sh
mygames sync              # refresh every store you're logged in to
mygames sync steam gog    # refresh only some stores
mygames find hollow knight
mygames dupes             # every game you own on 2+ stores
mygames status            # game count and last sync time per store
mygames report            # write the HTML report (see below)
```

### `sync`

Downloads each store's current library and replaces that store's games in the
database:

- **Removed games disappear.** A refunded game won't linger.
- **A failed sync changes nothing.** The store keeps its previous list.
- **One store failing doesn't stop the rest.** It's reported as `FAILED` and the
  other stores still sync.

`mygames sync` with no arguments skips stores you haven't logged in to.

### `find`

Every word you type has to appear in the title; case, accents and punctuation don't
matter. If nothing matches, it suggests close matches, so a typo like
`mass efect` still finds *Mass Effect*.

### `dupes`

Lists every game you own on more than one store, each with the store to play it on.

### `report`

```sh
mygames report                      # writes ./mygames-report.html
mygames report --out ~/games.html
```

This writes a single HTML file that works offline. Open it in any browser.
It has:

- a search box
- a checkbox per store (plus *all* / *none*). A game shows if you own it on any
  ticked store.
- an **Only owned on 2+ platforms** filter, with duplicates highlighted
- a "play on" column and store badges, with the preferred store in bold

The report contains your full library. It's ignored by git (`*-report.html`), so it
won't be pushed by accident.

## Stores without an API (EA app / Origin, Ubisoft Connect, …)

Keep a plain list per store and import it. Use either one title per line:

```text
Mass Effect Legendary Edition
Dragon Age: Inquisition
```

or a CSV with a `title` column and an optional `id` column:

```csv
title,id
Mass Effect Legendary Edition,me-le
Anno 1800,anno1800
```

```sh
mygames import ea ea-games.txt
mygames import ubisoft ubisoft.csv
```

The store name is up to you (`ea`, `ubisoft`, `battlenet`, `humble`, …).
Re-importing replaces everything previously imported for that store, so keep the
file as your master list and add to it. Stores that sync automatically (steam, gog,
epic, amazon, itch) can't be imported.

## Choosing the preferred store

The ranking lives in `~/.config/mygames/config.toml`:

```toml
priority = ["steam", "gog", "epic"]
```

Stores not in the list rank after the listed ones, alphabetically. Change the order
and every command and report uses it right away.

## How games are matched across stores

The same game often has a different name on each store, e.g.
*The Witcher 3: Wild Hunt* vs *The Witcher 3: Wild Hunt – Game of the Year Edition*.
Before comparing titles, `mygames` normalizes them:

- ignores case, accents, ™ ® © and punctuation (`&` counts as *and*, apostrophes are dropped)
- drops a leading *The*
- drops trailing edition markers: *GOTY*, *Game of the Year*, *Complete*,
  *Definitive / Enhanced / Deluxe / Gold / Extended / … Edition*, *Director's Cut*,
  *The Final Cut*

It deliberately **keeps** numbers, years and subtitles, because *DOOM* and
*DOOM (1993)* really are different games. Words like *Gold* or *Royal* are only
dropped when followed by *Edition*, so *Fool's Gold* keeps its name.

### Fixing mismatches: `aliases.toml`

No automatic matching is perfect. Fix the exceptions in
`~/.config/mygames/aliases.toml`. Changes apply on the next command, with no re-sync:

```toml
# Hide titles entirely (soundtracks, tools, demos you don't care about)
ignore = ["Some Game Soundtrack", "Some Engine Tool"]

# Group a store's title under another title (the right-hand side is shown)
[alias]
"Final Fantasy 7" = "FINAL FANTASY VII"
"Witcher 3 Wild Hunt GOTY" = "The Witcher 3: Wild Hunt"
```

Both sides are normalized, so you don't need exact capitalization or punctuation.

To review matches, open the report and tick **Only owned on 2+ platforms**.

## Where your data lives

Everything is stored in `~/.config/mygames/`. Set `MYGAMES_HOME` to use another folder.

| File | Contents |
|---|---|
| `mygames.db` | SQLite database, one row per game per store |
| `credentials.json` | Steam / GOG / itch.io keys and tokens (readable only by you, `chmod 600`) |
| `config.toml` | Store preference order |
| `aliases.toml` | Your matching fixes |
| `tools/` | Downloaded copy of nile (Amazon) |

legendary and nile keep their own logins in their usual folders
(`~/.config/legendary/` and `~/Library/Application Support/nile/`).

Nothing in the project folder contains your credentials or library.

The database is plain SQLite, so you can query it directly:

```sh
sqlite3 ~/.config/mygames/mygames.db \
  "SELECT platform, title, playtime_min FROM ownership WHERE platform = 'steam' ORDER BY playtime_min DESC LIMIT 10"
```

(`playtime_min` is only filled in for Steam.)

## Troubleshooting

| Problem | Fix |
|---|---|
| `steam: FAILED: Steam returned no games` | Set Steam **Game details** to **Public** (see [Steam](#steam)). |
| `steam: FAILED: HTTP Error 401/403` | Wrong or revoked API key. Run `mygames login steam` again. |
| `gog: FAILED: …` after a long break | The saved GOG login expired. Run `mygames login gog` again. |
| Amazon login hangs after pasting the URL | Don't paste. Copy the URL and press Enter (see [Amazon](#amazon-games--prime-gaming)). |
| `The clipboard doesn't hold the redirect URL` | You copied the wrong page. Copy the amazon.com URL you were redirected to after logging in, then run `mygames login amazon` again. |
| `<store>: skipped (not logged in …)` | Run `mygames login <store>`. |
| The same game shows up twice | Add an `[alias]` entry (see [Fixing mismatches](#fixing-mismatches-aliasestoml)). |
| A game from an itch.io bundle is missing | See [Known limitations](#known-limitations). |

## Known limitations

- **itch.io bundles:** the API only lists games you have *claimed*. Buying a bundle
  doesn't claim its games; each one is claimed when you open it from the bundle's
  download page. Unclaimed bundle games won't appear until you do that. itch.io's
  API has no way to list a bundle's contents or claim games in it.
- **EA app (Origin) and Ubisoft Connect** have no automatic sync yet; use
  [manual import](#stores-without-an-api-ea-app--origin-ubisoft-connect-).
- **GOG, Epic and Amazon** use unofficial logins borrowed from other launchers. If a
  store changes its login or API, that store's sync may break until the code is updated.
- **Epic** lists both Windows and Mac games. Legendary defaults to Mac-only on macOS,
  and `mygames` overrides that.

## Development

```sh
uv run pytest
```

The tests run offline: store APIs, legendary, nile and the clipboard are all faked.

```
src/mygames/
  cli.py          commands
  matching.py     title normalization and cross-store grouping
  db.py           SQLite storage (one row per game per store; grouping happens on read)
  report.py       HTML report
  config.py       data folder, config, credentials, aliases
  sources/        one module per store: is_configured(), login(), fetch()
tests/
```

### Adding a store

Create `src/mygames/sources/<store>.py` with three functions:

- `is_configured() -> bool`
- `login() -> None`
- `fetch() -> list[Ownership]`

Then add the store's name to `API_SOURCES` in `cli.py`. `fetch()` should raise
`SystemExit("…")` with a helpful message when something is wrong. Any other exception
is also caught and reported as `FAILED` without stopping other stores.

## Credits

- [legendary](https://github.com/derrod/legendary): Epic Games
- [nile](https://github.com/imLinguin/nile): Amazon Games
- [heroic-gogdl](https://github.com/Heroic-Games-Launcher/heroic-gogdl) and
  [Minigalaxy](https://github.com/sharkwouter/minigalaxy): reference for the GOG login and library endpoints

`mygames` is an unofficial personal tool. It is not affiliated with Valve, GOG, Epic
Games, Amazon, itch.io, EA or Ubisoft.
