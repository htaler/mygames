"""Self-contained HTML report: one file, no network, searchable, duplicates highlighted."""

import json
from datetime import date
from html import escape

from .matching import Game, play_on, rank

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>My Games</title>
<style>
:root {
  --bg: #f7f7f5; --fg: #1c1c1a; --muted: #6b6b66; --line: #e2e2dd; --card: #ffffff;
  --accent: #1a6fd1; --dup: #fff4d6; --dup-fg: #7a5200;
  --steam: #1b2838; --gog: #7b2fbe; --epic: #2a2a2a; --other: #5d6b5d;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #151514; --fg: #ececea; --muted: #9a9a94; --line: #2c2c2a; --card: #1d1d1c;
    --accent: #6aa8ff; --dup: #3a2f12; --dup-fg: #ffd47a;
    --steam: #66c0f4; --gog: #c58cff; --epic: #d8d8d8; --other: #a8b8a8;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { margin: 0 0 4px; font-size: 24px; }
.meta { color: var(--muted); margin: 0 0 20px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px 20px; margin-bottom: 16px; color: var(--muted); }
.stats b { color: var(--fg); font-variant-numeric: tabular-nums; }
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 12px;
  position: sticky; top: 0; background: var(--bg); padding: 8px 0; }
input[type=search] { flex: 1 1 240px; padding: 10px 12px; font: inherit; color: var(--fg);
  background: var(--card); border: 1px solid var(--line); border-radius: 8px; }
label { color: var(--muted); user-select: none; }
.services { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; flex-basis: 100%; }
.services label { color: var(--fg); white-space: nowrap; }
.services button { font: inherit; font-size: 13px; color: var(--accent); background: none;
  border: 0; padding: 0; cursor: pointer; }
.shown { color: var(--muted); margin-left: auto; font-variant-numeric: tabular-nums; }
table { width: 100%; border-collapse: collapse; background: var(--card);
  border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
tr.dup td { background: var(--dup); }
tr.dup td:first-child::after { content: " owned twice+"; color: var(--dup-fg); font-size: 12px; }
.badge { display: inline-block; margin: 0 4px 2px 0; padding: 1px 8px; border-radius: 999px;
  font-size: 12px; border: 1px solid currentColor; color: var(--other); }
.badge.steam { color: var(--steam); } .badge.gog { color: var(--gog); } .badge.epic { color: var(--epic); }
.badge.best { font-weight: 700; }
.play { font-weight: 600; white-space: nowrap; }
.empty { padding: 24px; text-align: center; color: var(--muted); }
@media (max-width: 560px) { th:nth-child(3), td:nth-child(3) { display: none; } }
</style>
</head>
<body>
<main>
  <h1>My Games</h1>
  <p class="meta">Generated __DATE__ · __PRIORITY__</p>
  <div class="stats" id="stats"></div>
  <div class="controls">
    <input type="search" id="q" placeholder="Search titles…" autofocus>
    <label><input type="checkbox" id="dups"> Only owned on 2+ platforms</label>
    <div class="services" id="services"></div>
  </div>
  <table>
    <thead><tr><th>Title</th><th>Owned on</th><th>Play on</th></tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No matches.</div>
</main>
<script>
const GAMES = __DATA__;
const norm = s => s.normalize("NFKD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
for (const g of GAMES) g.search = norm(g.title + " " + g.titles.join(" "));

const counts = {};
for (const g of GAMES) for (const p of g.platforms) counts[p] = (counts[p] || 0) + 1;
document.getElementById("stats").innerHTML =
  `<span><b>${GAMES.length}</b> games</span>` +
  `<span><b>${GAMES.filter(g => g.dup).length}</b> owned on 2+ platforms</span>` +
  Object.entries(counts).map(([p, n]) => `<span>${esc(p)} <b>${n}</b></span>`).join("");

// One checkbox per store, in preference order; a game shows if owned on any ticked store.
const PLATFORMS = __PLATFORMS__;
const services = document.getElementById("services");
services.innerHTML =
  PLATFORMS.map(p => `<label><input type="checkbox" value="${esc(p)}" checked> ` +
    `<span class="badge ${esc(p)}">${esc(p)}</span> ${counts[p]}</label>`).join("") +
  `<button type="button" data-all="1">all</button><button type="button" data-all="">none</button>` +
  `<span class="shown" id="shown"></span>`;
const boxes = [...services.querySelectorAll("input")];
services.addEventListener("change", render);
services.addEventListener("click", e => {
  if (!("all" in (e.target.dataset || {}))) return;
  for (const b of boxes) b.checked = !!e.target.dataset.all;
  render();
});

const q = document.getElementById("q"), dups = document.getElementById("dups");
function render() {
  const terms = norm(q.value).split(/\\s+/).filter(Boolean);
  const on = new Set(boxes.filter(b => b.checked).map(b => b.value));
  const shown = GAMES.filter(g => (!dups.checked || g.dup) && g.platforms.some(p => on.has(p)) &&
    terms.every(t => g.search.includes(t)));
  document.getElementById("shown").textContent = `showing ${shown.length} of ${GAMES.length}`;
  document.getElementById("rows").innerHTML = shown.map(g =>
    `<tr class="${g.dup ? "dup" : ""}"><td>${esc(g.title)}</td><td>` +
    g.platforms.map(p => `<span class="badge ${esc(p)}${p === g.play ? " best" : ""}">${esc(p)}</span>`).join("") +
    `</td><td class="play">${esc(g.play)}</td></tr>`).join("");
  document.getElementById("empty").hidden = shown.length > 0;
}
q.addEventListener("input", render);
dups.addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def render(games: list[Game], priority: list[str]) -> str:
    data = [
        {
            "title": g.title,
            "titles": sorted({o.title for o in g.owned}),
            # Preferred platform first, so badges read in priority order.
            "platforms": list(dict.fromkeys(o.platform for o in g.owned)),
            "play": play_on(g, priority),
            "dup": g.is_duplicate,
        }
        for g in sorted(games, key=lambda g: g.title.casefold())
    ]
    owned_on = {p for g in data for p in g["platforms"]}
    platforms = sorted(owned_on, key=lambda p: rank(p, priority))
    # "</" inside the inline JSON would close the <script> tag early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__DATE__", date.today().isoformat())
        .replace("__PRIORITY__", escape("Preference: " + " > ".join(priority) + " > others"))
        .replace("__PLATFORMS__", json.dumps(platforms))
        .replace("__DATA__", payload)
    )
