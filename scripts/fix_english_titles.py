import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "PaintingCabinet/0.1 (educational; local build)"}
ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "data" / "works.json"
QID = re.compile(r"^Q\d+$")

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                wait = 15 * (attempt + 1)
                print("  waiting", wait, "s after 429")
                time.sleep(wait)
                continue
            raise

def qid_of(work):
    wiki = str(work.get("wiki") or "")
    tail = wiki.rsplit("/", 1)[-1]
    return tail if QID.match(tail) else None

data = json.loads(WORKS.read_text(encoding="utf-8"))
works = data.get("works", [])
need = [w for w in works if qid_of(w)]
print("checking", len(need), "works")

changed = 0
for i in range(0, len(need), 40):
    chunk = need[i:i + 40]
    ids = "|".join(qid_of(w) for w in chunk)
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": ids,
        "props": "labels|sitelinks",
        "languages": "en",
        "sitefilter": "enwiki",
        "format": "json",
    })
    try:
        payload = request_json(url)
    except Exception as error:
        print("  chunk failed:", error)
        time.sleep(20)
        continue
    entities = payload.get("entities", {})
    for work in chunk:
        qid = qid_of(work)
        ent = entities.get(qid) or {}
        english = None
        labels = ent.get("labels") or {}
        if "en" in labels and labels["en"].get("value"):
            english = labels["en"]["value"]
        else:
            sitelinks = ent.get("sitelinks") or {}
            enwiki = sitelinks.get("enwiki") or {}
            if enwiki.get("title"):
                english = enwiki["title"].replace("_", " ")
        if not english:
            continue
        if work.get("title") != english:
            print(work.get("title"), "->", english)
            work["title"] = english
            changed += 1
    data["works"] = works
    WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  saved, english titles set", changed)
    time.sleep(1.2)

print("Done. Updated", changed)