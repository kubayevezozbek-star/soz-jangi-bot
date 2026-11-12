import re
import json
from pathlib import Path

raw_file = Path(__file__).parent / "data" / "raw_vocab.txt"
json_file = Path(__file__).parent / "data" / "words.json"

with open(raw_file, "r", encoding="utf-8") as f:
    text = f.read()

days_data = {}
current_day = 1
word_id = 1

# Patterns
# Day header: "1-kun (10 ta so'z)"
# Line: "1. Read (rid) – o'qimoq" or "1. Read (rid) - o'qimoq" or "1. Read - o'qimoq"

lines = text.split("\n")
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    day_match = re.match(r"^(\d+)-kun", line, re.IGNORECASE)
    if day_match:
        current_day = int(day_match.group(1))
        if current_day not in days_data:
            days_data[current_day] = []
        continue
    
    # Check for word line e.g. "1. Word (pron) – meaning"
    item_match = re.match(r"^\d+\.\s*(.+)$", line)
    if item_match:
        content = item_match.group(1).strip()
        # Find divider: '–' or '-' or '—'
        # Be careful: English phrase or pronunciation might have hyphen e.g. "Ice-cream (ayskrim) – muzqaymoq"
        parts = re.split(r"\s+[–—]\s+|\s+-\s+(?=[^)]*(?:\(|$))", content, maxsplit=1)
        if len(parts) == 2:
            left, uz = parts[0].strip(), parts[1].strip()
        else:
            # Try splitting on last dash
            if "–" in content:
                p = content.split("–", 1)
                left, uz = p[0].strip(), p[1].strip()
            elif "—" in content:
                p = content.split("—", 1)
                left, uz = p[0].strip(), p[1].strip()
            elif " - " in content:
                p = content.split(" - ", 1)
                left, uz = p[0].strip(), p[1].strip()
            else:
                continue

        # Extract pronunciation from left if present: "Read (rid)"
        pron = ""
        en = left
        pron_match = re.search(r"\(([^)]+)\)", left)
        if pron_match:
            pron = pron_match.group(1).strip()
            en = re.sub(r"\([^)]+\)", "", left).strip()
        
        # Clean extra characters from en
        en = re.sub(r"^[^\w]+|[^\w\s\-\'/]+$", "", en).strip()
        
        # Clean uz
        uz = re.sub(r"^\s*[-–—]\s*", "", uz).strip()
        
        # Primary uz: first clean term before commas or semicolons
        primary_uz = re.split(r"[,;]|\s+2\)", uz)[0].strip()
        primary_uz = re.sub(r"^\d+[\).]\s*", "", primary_uz).strip()

        if en and uz:
            word_obj = {
                "id": word_id,
                "day": current_day,
                "en": en,
                "pron": pron,
                "uz": uz,
                "primary_uz": primary_uz or uz
            }
            if current_day not in days_data:
                days_data[current_day] = []
            days_data[current_day].append(word_obj)
            word_id += 1

total_words = sum(len(w) for w in days_data.values())
output = {
    "total_days": len(days_data),
    "total_words": total_words,
    "days": days_data
}

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Parsed {len(days_data)} days, {total_words} words. Saved to {json_file}")
