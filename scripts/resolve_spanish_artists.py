import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "PaintingCabinet/0.1 (educational; local build)"}
ROOT = Path(__file__).resolve().parents[1]
NAMES = ROOT / "data" / "spanish_category_names.json"
OUT = ROOT / "data" / "spanish_artists.json"

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
        return json.load(response)

titles = json.loads(NAMES.read_text(encoding="utf-8"))["titles"]
artists = []
seen = set()

for i in range(0, len(titles), 40):
    chunk = titles[i:i + 40]
    params = {
        "action": "query",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": "|".join(chunk),
        "format": "json",
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = request_json(url)
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        title = page.get("title")
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if not title or not qid or qid in seen:
            continue
        seen.add(qid)
        artists.append({
            "id": qid,
            "name": title,
            "school": "spanish",
            "wiki": "https://www.wikidata.org/wiki/" + qid,
        })
        print("ok", title, qid)
    print("  chunk", i + 1, "to", i + len(chunk))
    time.sleep(0.8)

OUT.write_text(json.dumps({"artists": artists}, indent=2), encoding="utf-8")
print("Saved", len(artists), "Spanish artists")