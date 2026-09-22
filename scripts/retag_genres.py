import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "data" / "works.json"
data = json.loads(path.read_text(encoding="utf-8"))

BATTLE = re.compile(
    r"\b(battle|battles|war|wars|combat|assault|siege|skirmish|"
    r"massacre|bombardment|cavalry charge|naval battle|"
    r"fight|fighting|conflict|storming|raid)\b",
    re.I,
)

def map_genre(work):
    text = " ".join([
        work.get("title") or "",
        work.get("genre") or "",
    ]).lower()

    if BATTLE.search(text):
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
    if "marine" in text or "seascape" in text:
        return "landscape"
    if work.get("genre") in {
        "portrait", "landscape", "still-life", "history",
        "religious", "mythological", "genre-scene", "battle",
    }:
        return work["genre"]
    return "other"

counts = {}
for work in data["works"]:
    work["genre"] = map_genre(work)
    counts[work["genre"]] = counts.get(work["genre"], 0) + 1

path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("Retagged", len(data["works"]), "works")
for key, value in sorted(counts.items()):
    print(f"  {key}: {value}")