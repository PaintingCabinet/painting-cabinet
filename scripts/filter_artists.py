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
IN_PATH = ROOT / "data" / "artists.json"
OUT_PATH = ROOT / "data" / "artists.json"

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503) and attempt < 5:
                wait = 8 * (attempt + 1)
                print(f"  waiting {wait}s after HTTP {error.code}")
                time.sleep(wait)
                continue
            raise

def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def wiki_title(artist):
    return artist["wiki"].split("/wiki/")[-1]

print("Loading artists...")
artists = json.loads(IN_PATH.read_text(encoding="utf-8"))["artists"]

qid_by_title = {}
titles = [wiki_title(a) for a in artists]
print(f"Resolving {len(titles)} Wikipedia pages...")
for group in chunks(titles, 8):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "titles": "|".join(group),
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "format": "json",
        "redirects": 1,
    })
    data = request_json(url)
    pages = data.get("query", {}).get("pages", {})
    redirects = {
        r["from"].replace(" ", "_"): r["to"].replace(" ", "_")
        for r in data.get("query", {}).get("redirects", [])
    }
    normalized = {
        n["from"].replace(" ", "_"): n["to"].replace(" ", "_")
        for n in data.get("query", {}).get("normalized", [])
    }
    title_to_qid = {}
    for page in pages.values():
        title = page.get("title", "").replace(" ", "_")
        qid = page.get("pageprops", {}).get("wikibase_item")
        if qid:
            title_to_qid[title] = qid
    for title in group:
        lookup = redirects.get(title, title)
        lookup = normalized.get(lookup, lookup)
        if lookup in title_to_qid:
            qid_by_title[title] = title_to_qid[lookup]
    print(f"  resolved {len(qid_by_title)} so far")
    time.sleep(1.2)

qids = sorted(set(qid_by_title.values()))
print(f"Checking {len(qids)} Wikidata items...")

painter_qids = set()
for group in chunks(qids, 20):
    values = " ".join(f"wd:{qid}" for qid in group)
    query = f"""
    SELECT DISTINCT ?person WHERE {{
      VALUES ?person {{ {values} }}
      ?person wdt:P31 wd:Q5.
      ?person wdt:P106/wdt:P279* ?occ.
      FILTER(?occ IN (wd:Q1028181, wd:Q3391743, wd:Q483501))
    }}
    """
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
    })
    data = request_json(url)
    for row in data["results"]["bindings"]:
        painter_qids.add(row["person"]["value"].rsplit("/", 1)[-1])
    print(f"  painters found {len(painter_qids)}")
    time.sleep(1.0)

cleaned = []
seen = set()
for artist in artists:
    title = wiki_title(artist)
    qid = qid_by_title.get(title)
    if not qid or qid not in painter_qids:
        continue
    if qid in seen:
        continue
    seen.add(qid)
    artist["id"] = qid
    cleaned.append(artist)

OUT_PATH.write_text(json.dumps({"artists": cleaned}, indent=2), encoding="utf-8")
print(f"Kept {len(cleaned)} painters out of {len(artists)}")