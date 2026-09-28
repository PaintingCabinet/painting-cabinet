import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "data" / "works.json"

RULES = [
    ("battle", r"\b(battle|combat|war|siege|assault|cavalry charge|skirmish|massacre|naval battle)\b"),
    ("animal", r"\b(horse|horses|dog|dogs|cattle|cow|bull|lion|lions|sheep|hunt|hunting|spaniel|stallion)\b"),
    ("marine", r"\b(seascape|marine|man-of-war|men-o['’]?war|harbour|harbor|fleet|shipping|calm sea|rough sea)\b"),
    ("still-life", r"\b(still[- ]life|bodegon|breakfast piece|vanitas|flower piece|fruit piece)\b"),
    ("cityscape", r"\b(view of|cityscape|townscape|piazza|veduta|street in|market square)\b"),
    ("interior", r"\b(interior|in the studio|church interior)\b"),
    ("allegory", r"\b(allegory|allegorical)\b"),
    ("landscape", r"\b(landscape|valley|forest|woodland|river scene|winter scene|coast)\b"),
    ("portrait", r"\b(portrait|self[- ]portrait|head of|bust of)\b"),
    ("religious", r"\b(madonna|virgin|annunciation|adoration|crucifixion|nativity|saint\b|st\.|christ\b|last supper|piet|trinity|assumption)\b"),
    ("mythological", r"\b(venus|apollo|diana|bacchus|hercules|mars\b|minerva|neptune|cupid|nymph)\b"),
    ("history", r"\b(history painting|coronation|abdication|triumph of)\b"),
    ("genre-scene", r"\b(tavern|peasant|card players|merry company)\b"),
]

data = json.loads(WORKS.read_text(encoding="utf-8"))
works = data.get("works", [])
counts = {key: 0 for key, _ in RULES}
untouched = 0

for work in works:
    current = (work.get("genre") or "other").lower()
    if current not in ("", "other", "unknown"):
        continue
    blob = " ".join([
        str(work.get("title") or ""),
        str(work.get("artist_name") or ""),
    ]).lower()
    matched = None
    for key, pattern in RULES:
        if re.search(pattern, blob, re.I):
            matched = key
            break
    if matched:
        work["genre"] = matched
        counts[matched] += 1
    else:
        work["genre"] = "other"
        untouched += 1

data["works"] = works
WORKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("Moved from other:")
for key, n in counts.items():
    print(" ", key, n)
print("Still other:", untouched)