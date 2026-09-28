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
OUT = ROOT / "data" / "german_category_names.json"

CATEGORIES = [
    "Category:14th-century_German_painters",
    "Category:15th-century_German_painters",
    "Category:16th-century_German_painters",
    "Category:17th-century_German_painters",
    "Category:18th-century_German_painters",
    "Category:19th-century_German_painters",
]

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 7:
                wait = 20 * (attempt + 1)
                print(f"  waiting {wait}s after HTTP 429")
                time.sleep(wait)
                continue
            raise

titles = []
seen = set()
if OUT.exists():
    titles = json.loads(OUT.read_text(encoding="utf-8")).get("titles", [])
    seen = set(titles)
    print("resuming with", len(titles), "titles")

def save():
    OUT.write_text(json.dumps({"titles": titles}, indent=2), encoding="utf-8")

for category in CATEGORIES:
    print("category", category)
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "100",
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        try:
            data = request_json(url)
        except Exception as error:
            print("  skipped page:", error)
            save()
            break
        for row in data.get("query", {}).get("categorymembers", []):
            title = row.get("title", "")
            if title.startswith("Category:") or title.startswith("List of"):
                continue
            if title not in seen:
                seen.add(title)
                titles.append(title)
        save()
        print("  have", len(titles), "titles")
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(1.2)

print("Saved", len(titles), "unique titles")