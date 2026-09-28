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
NAMES = ROOT / "data" / "american_category_names.json"
OUT = ROOT / "data" / "american_artists.json"

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                wait = 20 * (attempt + 1)
                print(f"  waiting {wait}s after HTTP 429")
                time.sleep(wait)
                continue
            raise

titles = json.loads(NAMES.read_text(encoding="utf-8"))["titles"]
artists = []
seen_ids = set()
done_names = set()
if OUT.exists():
    artists = json.loads(OUT.read_text(encoding="utf-8")).get("artists", [])
    for artist in artists:
        seen_ids.add(artist["id"])
        done_names.add(artist["name"])
    print("resuming with", len(artists), "artists")

def save():
    OUT.write_text(json.dumps({"artists": artists}, indent=2), encoding="utf-8")

pending = [title for title in titles if title not in done_names]
print("still to resolve", len(pending))

for i in range(0, len(pending), 40):
    chunk = pending[i:i + 40]
    params = {
        "action": "query",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": "|".join(chunk),
        "format": "json",
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url)
    except Exception as error:
        print("  chunk failed:", error)
        save()
        time.sleep(30)
        continue
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        title = page.get("title")
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if not title or not qid or qid in seen_ids:
            continue
        seen_ids.add(qid)
        artists.append({
            "id": qid,
            "name": title,
            "school": "american",
            "wiki": "https://www.wikidata.org/wiki/" + qid,
        })
        print("ok", title, qid)
    save()
    print("  saved", len(artists), "artists")
    time.sleep(1.5)

print("Saved", len(artists), "American artists")