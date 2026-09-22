import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "PaintingCabinet/0.1 (educational; local build)"}
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "spanish_category_names.json"

CATEGORIES = [
    "Category:14th-century_Spanish_painters",
    "Category:15th-century_Spanish_painters",
    "Category:16th-century_Spanish_painters",
    "Category:17th-century_Spanish_painters",
    "Category:18th-century_Spanish_painters",
    "Category:19th-century_Spanish_painters",
]

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
        return json.load(response)

titles = []
seen = set()

for category in CATEGORIES:
    print("category", category)
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "500",
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        data = request_json(url)
        for row in data.get("query", {}).get("categorymembers", []):
            title = row.get("title", "")
            if title.startswith("Category:") or title.startswith("List of"):
                continue
            if title not in seen:
                seen.add(title)
                titles.append(title)
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.4)

OUT.write_text(json.dumps({"titles": titles}, indent=2), encoding="utf-8")
print("Saved", len(titles), "unique titles")