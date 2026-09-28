import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "data" / "artists.json"
EXTRA = ROOT / "data" / "australian_artists.json"

main = json.loads(MAIN.read_text(encoding="utf-8"))
artists = main["artists"]
have = {a["id"] for a in artists}
start = len(artists)

added = 0
for artist in json.loads(EXTRA.read_text(encoding="utf-8"))["artists"]:
    if artist["id"] in have:
        continue
    artists.append(artist)
    have.add(artist["id"])
    added += 1
    print("added", artist["name"])

main["artists"] = artists
MAIN.write_text(json.dumps(main, indent=2), encoding="utf-8")
print("Added", added)
print("Total artists", len(artists))
print("Australian fetch OFFSET should be", start)