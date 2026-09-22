import json
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "PaintingCabinet/0.1 (educational project)"}

PAGES = [
    ("List_of_Flemish_painters", "flemish"),
    ("List_of_Dutch_painters", "dutch"),
    ("List_of_French_painters", "french"),
]

SKIP = (
    "list of ",
    "category:",
    "file:",
    "template:",
    "wikipedia:",
    "help:",
    "portal:",
    "talk:",
)

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")

def get_wikitext(title):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
    })
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60, context=CONTEXT) as response:
        data = json.load(response)
    return data["parse"]["wikitext"]["*"]

def names_from_page(title, school):
    text = get_wikitext(title)
    found = []
    seen = set()
    for line in text.splitlines():
        if not line.lstrip().startswith("*"):
            continue
        for match in LINK_RE.findall(line):
            name = match.strip()
            key = name.lower()
            if key in seen:
                continue
            if key.startswith(SKIP):
                continue
            if len(name) < 3:
                continue
            seen.add(key)
            found.append({
                "name": name,
                "school": school,
                "wiki": "https://en.wikipedia.org/wiki/" + name.replace(" ", "_"),
            })
    return found

all_artists = []
for title, school in PAGES:
    print(f"Reading {title}...")
    artists = names_from_page(title, school)
    print(f"  {len(artists)} names")
    all_artists.extend(artists)

out_path = Path(__file__).resolve().parents[1] / "data" / "artists.json"
out_path.write_text(json.dumps({"artists": all_artists}, indent=2), encoding="utf-8")
print(f"Saved {len(all_artists)} artists to {out_path}")