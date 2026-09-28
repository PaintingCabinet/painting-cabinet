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
NAMES = ROOT / "data" / "popular_names.txt"
MAIN = ROOT / "data" / "artists.json"

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                time.sleep(15 * (attempt + 1))
                continue
            raise

def lookup(title):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": title,
        "format": "json",
    })
    data = request_json(url)
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        name = page.get("title")
        if qid and name:
            return name, qid
    return None, None

main = json.loads(MAIN.read_text(encoding="utf-8"))
artists = main["artists"]
have_ids = {a["id"] for a in artists}
have_names = {a["name"].lower() for a in artists}

added = 0
for raw in NAMES.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if "|" in line:
        name, school = [part.strip() for part in line.split("|", 1)]
    else:
        name, school = line, "other"
    school = school.lower()
    if name.lower() in have_names:
        print("already listed", name)
        continue
    title, qid = lookup(name)
    time.sleep(0.8)
    if not qid:
        print("not found", name)
        continue
    if qid in have_ids:
        print("already id", name, qid)
        continue
    artists.append({
        "id": qid,
        "name": title,
        "school": school,
        "wiki": "https://www.wikidata.org/wiki/" + qid,
    })
    have_ids.add(qid)
    have_names.add(title.lower())
    have_names.add(name.lower())
    added += 1
    print("added", title, qid, school)

main["artists"] = artists
MAIN.write_text(json.dumps(main, indent=2), encoding="utf-8")
print("Added", added)
print("Total artists", len(artists))