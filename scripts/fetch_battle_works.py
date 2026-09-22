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
ARTISTS_PATH = ROOT / "data" / "battle_artists.json"
WORKS_PATH = ROOT / "data" / "works.json"
REJECTED_PATH = ROOT / "data" / "rejected.json"

OFFSET = 0
BATCH_SIZE = 50
LIMIT_EACH = 25
MIN_SIDE = 800

SKIP_WORDS = (
    "black and white", "black-and-white", "b&w", "b-w",
    "engraving", "etching", "woodcut", "lithograph",
    "mezzotint", "aquatint", "drypoint", "photogravure",
    "print of", "after a painting",
)

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 5:
                wait = 12 * (attempt + 1)
                print(f"  waiting {wait}s after HTTP {error.code}")
                time.sleep(wait)
                continue
            raise

def map_genre(label, title=""):
    text = " ".join([label or "", title or ""]).lower()
    if any(word in text for word in (
        "battle", "battles", "war", "wars", "combat", "assault",
        "siege", "skirmish", "massacre", "bombardment",
        "naval battle", "fight", "fighting",
    )):
        return "battle"
    if "portrait" in text:
        return "portrait"
    if "landscape" in text or "cityscape" in text:
        return "landscape"
    if "still" in text:
        return "still-life"
    if "history" in text:
        return "history"
    if "religious" in text or "altar" in text:
        return "religious"
    if "myth" in text:
        return "mythological"
    if "genre" in text:
        return "genre-scene"
    if "marine" in text or "sea" in text:
        return "landscape"
    return "other"

def file_from_image(url):
    if "Special:FilePath/" not in (url or ""):
        return ""
    name = url.split("Special:FilePath/", 1)[1].split("?", 1)[0]
    return urllib.parse.unquote(name)

def looks_bw(title, filename):
    text = " ".join([title or "", filename.replace("_", " ")]).lower()
    return any(word in text for word in SKIP_WORDS)

def too_small(filename):
    if not filename:
        return False
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "titles": "File:" + filename,
        "prop": "imageinfo",
        "iiprop": "size",
        "format": "json",
    })
    try:
        data = request_json(url)
    except Exception:
        return False
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        width = info.get("width") or 0
        height = info.get("height") or 0
        return min(width, height) < MIN_SIDE and max(width, height) > 0
    return False

def fetch_artist(artist):
    artist_id = artist["id"]
    query = f"""
    SELECT ?work ?workLabel ?image ?date ?genreLabel WHERE {{
      ?work wdt:P170 wd:{artist_id}.
      ?work wdt:P18 ?image.
      OPTIONAL {{ ?work wdt:P571 ?date. }}
      OPTIONAL {{ ?work wdt:P136 ?genre. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {LIMIT_EACH}
    """
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
    })
    data = request_json(url)
    works = []
    seen = set()
    for row in data["results"]["bindings"]:
        work_id = row["work"]["value"]
        qid = work_id.rsplit("/", 1)[-1]
        if work_id in seen or work_id in rejected or qid in rejected:
            continue
        seen.add(work_id)
        image = row["image"]["value"]
        if "Special:FilePath/" in image:
            image = image + ("&" if "?" in image else "?") + "width=1600"
        date = row["date"]["value"][:4] if "date" in row else ""
        title = row["workLabel"]["value"]
        genre_label = row["genreLabel"]["value"] if "genreLabel" in row else ""
        filename = file_from_image(image)
        if looks_bw(title, filename) or too_small(filename):
            continue
        works.append({
            "title": title,
            "artist_name": artist["name"],
            "artist_id": artist_id,
            "school": artist["school"],
            "date": date,
            "genre": map_genre(genre_label, title),
            "image": image,
            "wiki": work_id,
        })
    return works

artists = json.loads(ARTISTS_PATH.read_text(encoding="utf-8"))["artists"]
batch = artists[OFFSET:OFFSET + BATCH_SIZE]
print(f"Fetching battle works for artists {OFFSET + 1} to {OFFSET + len(batch)}")

if WORKS_PATH.exists():
    existing = json.loads(WORKS_PATH.read_text(encoding="utf-8")).get("works", [])
else:
    existing = []

rejected = set()
if REJECTED_PATH.exists():
    rejected = set(json.loads(REJECTED_PATH.read_text(encoding="utf-8")).get("rejected", []))

by_id = {}
for work in existing:
    wiki = work.get("wiki", "")
    qid = wiki.rsplit("/", 1)[-1]
    if wiki in rejected or qid in rejected:
        continue
    by_id[wiki] = work

for artist in batch:
    print(f"  {artist['name']}")
    try:
        found = fetch_artist(artist)
        print(f"    {len(found)} works")
        for work in found:
            by_id[work["wiki"]] = work
    except Exception as error:
        print(f"    skipped: {error}")
    time.sleep(4)

works = list(by_id.values())
WORKS_PATH.write_text(json.dumps({"works": works}, indent=2), encoding="utf-8")
print(f"Saved {len(works)} total works to {WORKS_PATH}")