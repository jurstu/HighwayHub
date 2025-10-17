import json
import glob
from pathlib import Path

MAIN_DATA_GLOB = "../0-get-datasets/dataset_*.json"      # source datasets
DETAILED_FILE = "../canard_detailed_data.json"
OUTPUT_FILE = "../id_point_types.csv"

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
    # --- Load base datasets ---
    all_points = []
    for path in sorted(glob.glob(MAIN_DATA_GLOB)):
        points = load_json(path)
        print(f"✅ Loaded {len(points)} from {path}")
        all_points.extend(points)

    # Create mapping ID → type
    id_to_type = {}
    for p in all_points:
        pid = p.get("id")
        if not pid:
            continue
        ptype = p.get("rodzajPomiaru") or p.get("rodzaj") or "UNKNOWN"
        id_to_type[int(pid)] = ptype

    base_ids = set(id_to_type.keys())
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
    empties = [int(k) for k, v in detailed.items() if is_empty_record(v)]

    print(f"🧮 In detailed JSON: {len(detailed_ids)} records")
    print(f"🚫 Missing: {len(missing)}")
    print(f"➕ Extra: {len(extra)}")
    print(f"⚪ Empty/placeholder: {len(empties)}")

    # --- Save lists ---
    if missing:
        with open("../missing_ids.txt", "w", encoding="utf-8") as f:
            for mid in sorted(missing):
                f.write(f"{mid}\n")
        print("📄 Missing IDs saved to missing_ids.txt")

    if empties:
        with open("empty_ids.txt", "w", encoding="utf-8") as f:
            for eid in sorted(empties):
                f.write(f"{eid}\n")
        print("📄 Empty IDs saved to empty_ids.txt")

    # --- Save ID + type CSV ---
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("id,point_type\n")
        for pid, ptype in sorted(id_to_type.items()):
            f.write(f"{pid},{ptype}\n")

    print(f"✅ Saved ID/type mapping to {OUTPUT_FILE}")
    print("🏁 Verification complete.")

if __name__ == "__main__":
    main()
