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
ARTISTS_PATH = ROOT / "data" / "artists.json"
WORKS_PATH = ROOT / "data" / "works.json"
REJECTED_PATH = ROOT / "data" / "rejected.json"
NAMES_PATH = ROOT / "data" / "popular_names.txt"

LIMIT_EACH = 250

SKIP_WORDS = (
    "black and white", "black-and-white", "b&w", "b-w",
    "engraving", "etching", "woodcut", "lithograph",
    "mezzotint", "aquatint", "drypoint", "photogravure",
    "print of", "after a painting",
)

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 3:
                wait = 15 * (attempt + 1)
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
    if "animal" in text or "horse" in text:
        return "animal"
    if "marine" in text or "seascape" in text:
        return "marine"
    return "other"

def file_from_image(url):
    if "Special:FilePath/" not in (url or ""):
        return ""
    name = url.split("Special:FilePath/", 1)[1].split("?", 1)[0]
    return urllib.parse.unquote(name)

def looks_bw(title, filename):
    text = " ".join([title or "", filename.replace("_", " ")]).lower()
    return any(word in text for word in SKIP_WORDS)

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
        if looks_bw(title, filename):
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

def save(by_id):
    tmp = WORKS_PATH.with_name("works.tmp.json")
    tmp.write_text(json.dumps({"works": list(by_id.values())}, indent=2), encoding="utf-8")
    tmp.replace(WORKS_PATH)

def parse_wanted():
    wanted = []
    for raw in NAMES_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        wanted.append(line.split("|", 1)[0].strip().lower())
    return wanted

artists = json.loads(ARTISTS_PATH.read_text(encoding="utf-8"))["artists"]
wanted = parse_wanted()
chosen = []
for artist in artists:
    name = artist["name"].lower()
    if any(key in name or name in key for key in wanted):
        chosen.append(artist)

print("Popular artists matched:", len(chosen))
for artist in chosen:
    print(" ", artist["name"])

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

for artist in chosen:
    print(f"  {artist['name']}")
    try:
        found = fetch_artist(artist)
        added = 0
        for work in found:
            if work["wiki"] not in by_id:
                by_id[work["wiki"]] = work
                added += 1
        save(by_id)
        print(f"    +{added} new, saved {len(by_id)} total")
    except Exception as error:
        print(f"    skipped: {error}")
        save(by_id)
    time.sleep(2)

print(f"Saved {len(by_id)} total works to {WORKS_PATH}")