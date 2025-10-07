import json
import glob
from pathlib import Path

MAIN_DATA_GLOB = "dataset_*.json"      # the 4 source datasets
DETAILED_FILE = "canard_detailed_data.json"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_empty_record(rec):
    """Decide if a record is effectively empty."""
    if not rec:
        return True
    if isinstance(rec, dict):
        if rec.get("status") == "empty":
            return True
        if len(rec.keys()) == 1 and "id" in rec:
            return True
        if not rec.get("urzadzenie") and not rec.get("rodzaj"):
            return True
    return False

def main():
    # --- Load all base datasets ---
    all_points = []
    for path in sorted(glob.glob(MAIN_DATA_GLOB)):
        points = load_json(path)
        print(f"✅ Loaded {len(points)} from {path}")
        all_points.extend(points)
    base_ids = {int(p["id"]) for p in all_points if "id" in p}
    print(f"🔹 Total unique IDs in source datasets: {len(base_ids)}")

    # --- Load detailed data ---
    if not Path(DETAILED_FILE).exists():
        print(f"❌ Missing {DETAILED_FILE}")
        return
    detailed = load_json(DETAILED_FILE)
    detailed_ids = {int(k) for k in detailed.keys()}

    # --- Compare ---
    missing = base_ids - detailed_ids
    extra = detailed_ids - base_ids

    print(f"🧮 In detailed JSON: {len(detailed_ids)} records")
    print(f"🚫 Missing {len(missing)} IDs")
    print(f"➕ Extra {len(extra)} IDs")

    # --- Empty content check ---
    empties = [int(k) for k, v in detailed.items() if is_empty_record(v)]
    print(f"⚪ Empty/placeholder records: {len(empties)}")

    # --- Optional outputs ---
    if missing:
        with open("missing_ids.txt", "w") as f:
            for mid in sorted(missing):
                f.write(f"{mid}\n")
        print("📄 Missing IDs saved to missing_ids.txt")

    if empties:
        with open("empty_ids.txt", "w") as f:
            for eid in sorted(empties):
                f.write(f"{eid}\n")
        print("📄 Empty IDs saved to empty_ids.txt")

    print("✅ Verification complete.")

if __name__ == "__main__":
    main()
