import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "data" / "artists.json"
BATTLE = ROOT / "data" / "battle_artists.json"

main = json.loads(MAIN.read_text(encoding="utf-8"))
artists = main["artists"]
have = {a["id"] for a in artists}

added = 0
for artist in json.loads(BATTLE.read_text(encoding="utf-8"))["artists"]:
    if artist["id"] in have:
        continue
    artists.append({
        "id": artist["id"],
        "name": artist["name"],
        "school": "french",
        "wiki": artist.get("wiki", "https://www.wikidata.org/wiki/" + artist["id"]),
    })
    have.add(artist["id"])
    added += 1
    print("added", artist["name"])

main["artists"] = artists
MAIN.write_text(json.dumps(main, indent=2), encoding="utf-8")
print(f"Added {added} new artists. Total now {len(artists)}")