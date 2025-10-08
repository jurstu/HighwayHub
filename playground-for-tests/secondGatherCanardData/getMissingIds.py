import json
from pathlib import Path

# Paths
datasets = [f"dataset_{i}.json" for i in range(4)]
detailed_path = Path("canard_detailed_data.json")

# Load all expected IDs from dataset files
all_ids = set()
for ds_path in datasets:
    with open(ds_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for entry in data:
            all_ids.add(str(entry["id"]))

print(f"📦 Total IDs found in datasets: {len(all_ids)}")

# Load existing data file
if detailed_path.exists():
    with open(detailed_path, "r", encoding="utf-8") as f:
        detailed_data = json.load(f)
    existing_ids = set(detailed_data.keys())
else:
    print("⚠ No canard_detailed_data.json found — treating as empty.")
    existing_ids = set()

# Determine which IDs are missing
missing_ids = sorted(all_ids - existing_ids, key=int)

print(f"🧩 Missing entries: {len(missing_ids)}")
if missing_ids:
    print("\n".join(missing_ids))

# Optionally, write them to a file for later use
Path("missing_ids.txt").write_text("\n".join(missing_ids), encoding="utf-8")
print("\n📝 Saved list to missing_ids.txt")
