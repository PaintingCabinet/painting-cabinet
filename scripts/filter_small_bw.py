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
WORKS = ROOT / "data" / "works.json"
MIN_SIDE = 800

SKIP_WORDS = (
    "black and white", "black-and-white", "b&w", "b-w",
    "engraving", "etching", "woodcut", "lithograph",
    "mezzotint", "aquatint", "drypoint", "photogravure",
    "print of", "after a painting",
)

def request_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as response:
        return json.load(response)

def file_from_image(url):
    if "Special:FilePath/" not in url:
        return ""
    name = url.split("Special:FilePath/", 1)[1].split("?", 1)[0]
    return urllib.parse.unquote(name)

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

def looks_bw(work, filename):
    text = " ".join([
        work.get("title") or "",
        filename.replace("_", " "),
    ]).lower()
    return any(word in text for word in SKIP_WORDS)

data = json.loads(WORKS.read_text(encoding="utf-8"))
kept = []
removed = {"small": 0, "bw": 0}

for i, work in enumerate(data["works"], start=1):
    filename = file_from_image(work.get("image", ""))
    reason = None
    if looks_bw(work, filename):
        reason = "bw"
    elif too_small(filename):
        reason = "small"
    if reason:
        removed[reason] += 1
        print(f"drop {reason}: {work.get('title')}")
    else:
        kept.append(work)
    if i % 20 == 0:
        print(f"  checked {i}")
        time.sleep(0.4)

data["works"] = kept
WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Kept {len(kept)}")
print(f"Removed small={removed['small']} bw/print={removed['bw']}")