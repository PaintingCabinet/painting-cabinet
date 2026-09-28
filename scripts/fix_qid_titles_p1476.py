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
    if QID.match(title):
        return title
    return tail if QID.match(title) else None

def from_claims(ent):
    claims = (ent.get("claims") or {}).get("P1476") or []
    for claim in claims:
        value = (((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
        text = value.get("text") if isinstance(value, dict) else None
        if text and not QID.match(text):
            return text
    labels = ent.get("labels") or {}
    for lang in ("en", "fr", "nl", "de", "es", "it", "pt", "pl", "ru"):
        if lang in labels and labels[lang].get("value"):
            val = labels[lang]["value"]
            if not QID.match(val):
                return val
    return None

data = json.loads(WORKS.read_text(encoding="utf-8"))
works = data.get("works", [])
need = [w for w in works if QID.match(str(w.get("title") or ""))]
print("Q-id titles left:", len(need))

fixed = 0
for i in range(0, len(need), 40):
    chunk = need[i:i + 40]
    ids = []
    for work in chunk:
        tail = str(work.get("wiki") or "").rsplit("/", 1)[-1]
        ids.append(tail if QID.match(tail) else str(work.get("title")))
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "labels|claims",
        "format": "json",
    })
    try:
        payload = request_json(url)
    except Exception as error:
        print("  chunk failed:", error)
        time.sleep(20)
        continue
    entities = payload.get("entities", {})
    for work, qid in zip(chunk, ids):
        label = from_claims(entities.get(qid) or {})
        if not label:
            continue
        work["title"] = label
        fixed += 1
        print("ok", qid, "->", label)
    data["works"] = works
    WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  saved, fixed so far", fixed)
    time.sleep(1.2)

print("Done. Renamed", fixed, "of", len(need))