"""Builds data/featured.json (the home-page slideshow) from data/works.json.
Put this file next to fetch_works_batch.py, edit PICKS if you like, then run:  python make_featured.py
"""
import json
import random
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKS_PATH = ROOT / "data" / "works.json"
OUT_PATH = ROOT / "data" / "featured.json"
MIN_SLIDES = 8

# (artist names to look for, painting titles to prefer - first match wins, else a random work)
PICKS = [
    (["Johannes Vermeer"], ["Girl with a Pearl Earring", "The Milkmaid", "View of Delft"]),
    (["Rembrandt", "Rembrandt van Rijn"], ["The Night Watch", "Anatomy Lesson"]),
    (["Jan van Eyck"], ["Arnolfini"]),
    (["Pieter Bruegel the Elder"], ["Hunters in the Snow", "Tower of Babel"]),
    (["Peter Paul Rubens"], ["Descent from the Cross"]),
    (["Frans Hals"], ["Laughing Cavalier"]),
    (["Vincent van Gogh"], ["Starry Night", "Sunflowers"]),
    (["Claude Monet"], ["Impression, Sunrise", "Water Lilies"]),
    (["Diego Velázquez"], ["Las Meninas"]),
    (["Jan Brueghel the Elder"], ["Assault on a Convoy"]),
    (["Sandro Botticelli"], ["Birth of Venus", "Primavera"]),
    (["J. M. W. Turner"], ["Fighting Temeraire"]),
]


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


works = [w for w in json.loads(WORKS_PATH.read_text(encoding="utf-8")).get("works", []) if w.get("image")]
by_artist = {}
for w in works:
    by_artist.setdefault(norm(w.get("artist_name")), []).append(w)

chosen, used = [], set()


def add(w):
    key = w.get("wiki") or w["image"]
    if key in used:
        return False
    used.add(key)
    chosen.append({k: w.get(k, "") for k in ("title", "artist_name", "school", "date", "image", "wiki")})
    print("  added:", w.get("artist_name"), "-", w.get("title"))
    return True


for names, titles in PICKS:
    pool = [w for n in names for w in by_artist.get(norm(n), [])]
    if not pool:
        print("  not found:", names[0])
        continue
    pick = None
    for t in titles:
        pick = next((w for w in pool if norm(t) in norm(w.get("title"))), None)
        if pick:
            break
    if not pick:
        known = [w for w in pool if w.get("genre") not in (None, "", "other")]
        pick = random.choice(known or pool)
    add(pick)

if len(chosen) < MIN_SLIDES:
    top = [name for name, _ in Counter({k: len(v) for k, v in by_artist.items()}).most_common(40)]
    random.shuffle(top)
    for name in top:
        if len(chosen) >= MIN_SLIDES:
            break
        pool = [w for w in by_artist[name] if w.get("genre") not in (None, "", "other")]
        if pool:
            add(random.choice(pool))

OUT_PATH.write_text(json.dumps({"featured": chosen}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(chosen)} works to {OUT_PATH}")
