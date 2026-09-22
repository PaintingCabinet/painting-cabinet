import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

ARTIST_ID = "Q5598"
ARTIST_NAME = "Rembrandt"
LIMIT = 40

QUERY = f"""
SELECT ?work ?workLabel ?image ?date WHERE {{
  ?work wdt:P170 wd:{ARTIST_ID}.
  ?work wdt:P18 ?image.
  ?work wdt:P31/wdt:P279* wd:Q3305213.
  OPTIONAL {{ ?work wdt:P571 ?date. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT {LIMIT}
"""

url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({
    "query": QUERY,
    "format": "json",
})

request = urllib.request.Request(
    url,
    headers={"User-Agent": "PaintingCabinet/0.1 (educational project)"},
)

context = ssl._create_unverified_context()

print("Asking Wikidata for Rembrandt paintings...")
with urllib.request.urlopen(request, timeout=60, context=context) as response:
    data = json.load(response)

works = []
for row in data["results"]["bindings"]:
    image = row["image"]["value"]
    if "Special:FilePath/" in image:
        image = image + ("&" if "?" in image else "?") + "width=1600"

    date = ""
    if "date" in row:
        date = row["date"]["value"][:4]

    works.append({
        "title": row["workLabel"]["value"],
        "artist_name": ARTIST_NAME,
        "school": "dutch",
        "date": date,
        "image": image,
        "wiki": row["work"]["value"],
    })

out_path = Path(__file__).resolve().parents[1] / "data" / "works_rembrandt.json"
out_path.write_text(json.dumps({"works": works}, indent=2), encoding="utf-8")
print(f"Saved {len(works)} works to {out_path}")