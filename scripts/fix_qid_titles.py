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
    title = str(work.get("title") or "")
    if QID.match(title):
        return title
    wiki = str(work.get("wiki") or "")
    tail = wiki.rsplit("/", 1)[-1]
    if QID.match(title) is None and QID.match(tail) and QID.match(title or ""):
        return title
    return title if QID.match(title) else None

data = json.loads(WORKS.read_text(encoding="utf-8"))
works = data.get("works", [])
need = []
for work in works:
    qid = qid_of(work)
    if qid:
        need.append((work, qid))

print("titles that look like Q-ids:", len(need))

fixed = 0
for i in range(0, len(need), 40):
    chunk = need[i:i + 40]
    ids = "|".join(item[1] for item in chunk)
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": ids,
        "props": "labels",
        "languages": "en|fr|nl|de|es|it",
        "format": "json",
    })
    try:
        payload = request_json(url)
    except Exception as error:
        print("  chunk failed:", error)
        time.sleep(20)
        continue
    entities = payload.get("entities", {})
    for work, qid in chunk:
        ent = entities.get(qid) or {}
        labels = ent.get("labels") or {}
        label = None
        for lang in ("en", "fr", "nl", "de", "es", "it"):
            if lang in labels and labels[lang].get("value"):
                label = labels[lang]["value"]
                break
        if label and not QID.match(label):
            work["title"] = label
            fixed += 1
            print("ok", qid, "->", label)
    data["works"] = works
    WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  saved, fixed so far", fixed)
    time.sleep(1.2)

print("Done. Renamed", fixed, "of", len(need))