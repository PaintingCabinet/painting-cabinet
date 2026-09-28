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

GENRE_MAP = {
    "Q134307": "portrait",
    "Q191163": "landscape",
    "Q170571": "still-life",
    "Q14085": "still-life",
    "Q1047337": "genre-scene",
    "Q742333": "history",
    "Q2864737": "religious",
    "Q3374376": "mythological",
    "Q158607": "marine",
    "Q21627748": "battle",
    "Q16875712": "animal",
    "Q2839016": "allegory",
    "Q1935974": "cityscape",
    "Q331116": "interior",
    "Q185166": "interior",
}

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                wait = 15 * (attempt + 1)
                print("  waiting", wait, "s")
                time.sleep(wait)
                continue
            raise

def item_id(work):
    tail = str(work.get("wiki") or "").rsplit("/", 1)[-1]
    return tail if QID.match(tail) else None

data = json.loads(WORKS.read_text(encoding="utf-8"))
works = data.get("works", [])
need = [w for w in works if (w.get("genre") or "other") in ("other", "unknown", "")]
print("other to check:", len(need))

mapped = 0
for i in range(0, len(need), 40):
    chunk = need[i:i + 40]
    ids = [item_id(w) for w in chunk if item_id(w)]
    if not ids:
        continue
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "claims",
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
        qid = item_id(work)
        claims = ((entities.get(qid) or {}).get("claims") or {}).get("P136") or []
        for claim in claims:
            dv = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
            gid = dv.get("id")
            if gid in GENRE_MAP:
                work["genre"] = GENRE_MAP[gid]
                mapped += 1
                print(qid, "->", GENRE_MAP[gid])
                break
    data["works"] = works
    WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("  saved, mapped", mapped)
    time.sleep(1.2)

print("Done. Mapped", mapped, "of", len(need))