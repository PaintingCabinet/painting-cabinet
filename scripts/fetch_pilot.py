import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

LIMIT_EACH = 15
CONTEXT = ssl._create_unverified_context()

ARTISTS = [
    ("Q102272", "Jan van Eyck", "flemish"),
    ("Q68631", "Rogier van der Weyden", "flemish"),
    ("Q106851", "Hans Memling", "flemish"),
    ("Q43270", "Pieter Bruegel the Elder", "flemish"),
    ("Q5599", "Peter Paul Rubens", "flemish"),
    ("Q150679", "Anthony van Dyck", "flemish"),
    ("Q676163", "Clara Peeters", "flemish"),
    ("Q167654", "Frans Hals", "dutch"),
    ("Q5598", "Rembrandt", "dutch"),
    ("Q41264", "Johannes Vermeer", "dutch"),
    ("Q213612", "Jacob van Ruisdael", "dutch"),
    ("Q205863", "Jan Steen", "dutch"),
    ("Q166898", "Rachel Ruysch", "dutch"),
    ("Q233265", "Nicolas Poussin", "french"),
    ("Q214074", "Claude Lorrain", "french"),
    ("Q183221", "Jean-Antoine Watteau", "french"),
    ("Q83155", "Jacques-Louis David", "french"),
    ("Q33477", "Eugène Delacroix", "french"),
    ("Q23380", "Jean-Auguste-Dominique Ingres", "french"),
    ("Q296", "Claude Monet", "french"),
]

def map_genre(label):
    text = (label or "").lower()
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

def fetch_artist(artist_id, name, school):
    query = f"""
    SELECT ?work ?workLabel ?image ?date ?genreLabel WHERE {{
      ?work wdt:P170 wd:{artist_id}.
      ?work wdt:P18 ?image.
      ?work wdt:P31/wdt:P279* wd:Q3305213.
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
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PaintingCabinet/0.1 (educational project)"},
    )
    with urllib.request.urlopen(request, timeout=90, context=CONTEXT) as response:
        data = json.load(response)

    works = []
    seen = set()
    for row in data["results"]["bindings"]:
        work_id = row["work"]["value"]
        if work_id in seen:
            continue
        seen.add(work_id)
        image = row["image"]["value"]
        if "Special:FilePath/" in image:
            image = image + ("&" if "?" in image else "?") + "width=1600"
        date = row["date"]["value"][:4] if "date" in row else ""
        genre_label = row["genreLabel"]["value"] if "genreLabel" in row else ""
        works.append({
            "title": row["workLabel"]["value"],
            "artist_name": name,
            "school": school,
            "date": date,
            "genre": map_genre(genre_label),
            "image": image,
            "wiki": work_id,
        })
    return works

all_works = []
for artist_id, name, school in ARTISTS:
    print(f"Fetching {name}...")
    try:
        found = fetch_artist(artist_id, name, school)
        print(f"  {len(found)} works")
        all_works.extend(found)
    except Exception as error:
        print(f"  skipped: {error}")
    time.sleep(1)

out_path = Path(__file__).resolve().parents[1] / "data" / "works.json"
out_path.write_text(json.dumps({"works": all_works}, indent=2), encoding="utf-8")
print(f"Saved {len(all_works)} works to {out_path}")