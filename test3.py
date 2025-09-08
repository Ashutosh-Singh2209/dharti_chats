from datetime import datetime, timezone
from pathlib import Path
import json

SRC_DIR = Path("transliterated_non_retrieval")
OUT_PATH = Path("conversations_sorted_by_date.json")

def parse_mongo_date(zstr):
    if zstr.endswith("Z"):
        return datetime.fromisoformat(zstr[:-1]).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(zstr)

def extract_tag(path):
    name = path.name
    if name.startswith("transliterated_"):
        name = name[len("transliterated_"):]
    suffix = "_messages.modified_2.json"
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    return name

records = []
for file_path in SRC_DIR.glob("*.json"):
    tag = extract_tag(file_path)
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for conv in data:
        messages = conv.get("messages", [])
        if not messages:
            continue
        ts_raw = messages[0].get("timestamp", {}).get("$date")
        dt = parse_mongo_date(ts_raw)
        
        conv_copy = dict(conv)
        conv_copy["tag"] = tag
        conv_copy["conv_date"] = dt.isoformat()
        records.append((dt, conv_copy))

records.sort(key=lambda x: (-x[0].timestamp(), x[1]["tag"]))
sorted_convs = [conv for _, conv in records]
with OUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(sorted_convs, f, ensure_ascii=False, indent=2)
print(f"Saved {len(sorted_convs)} conversations to {OUT_PATH}")
