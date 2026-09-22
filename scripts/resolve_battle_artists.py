import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "PaintingCabinet/0.1 (educational; local build)"}
ROOT = Path(__file__).resolve().parents[1]
NAMES = ROOT / "data" / "battle_artist_names.json"
OUT = ROOT / "data" / "battle_artists.json"

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                wait = 15 * (attempt + 1)
                print(f"  waiting {wait}s after HTTP 429")
                time.sleep(wait)
                continue
            raise

already = {}
if OUT.exists():
    for artist in json.loads(OUT.read_text(encoding="utf-8")).get("artists", []):
        already[artist["id"]] = artist
        already[artist["name"].lower()] = artist

names = json.loads(NAMES.read_text(encoding="utf-8"))["artists"]
found = []
seen_ids = set()
missing = []

for row in names:
    cached = already.get(row["name"].lower())
    if cached:
        if cached["id"] not in seen_ids:
            found.append(cached)
            seen_ids.add(cached["id"])
            print("have", row["name"], "->", cached["id"])
        continue

    query = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "search": row["name"],
        "language": "en",
        "type": "item",
        "limit": 5,
        "format": "json",
    })
    url = "https://www.wikidata.org/w/api.php?" + query
    try:
        data = request_json(url)
        hit = None
        for item in data.get("search", []):
            desc = (item.get("description") or "").lower()
            if "painter" in desc or "artist" in desc or "peintre" in desc:
                hit = item
                break
        if not hit and data.get("search"):
            hit = data["search"][0]
        if hit and hit["id"] not in seen_ids:
            artist = {
                "id": hit["id"],
                "name": hit.get("label") or row["name"],
                "school": "french",
                "focus": row["focus"],
                "wiki": "https://www.wikidata.org/wiki/" + hit["id"],
            }
            found.append(artist)
            seen_ids.add(hit["id"])
            print("ok", row["name"], "->", hit["id"])
        else:
            missing.append(row["name"])
            print("miss", row["name"])
    except Exception as error:
        missing.append(row["name"])
        print("error", row["name"], error)
    time.sleep(1.5)

OUT.write_text(json.dumps({"artists": found}, indent=2), encoding="utf-8")
print("Saved", len(found), "artists")
print("Missing:", missing)