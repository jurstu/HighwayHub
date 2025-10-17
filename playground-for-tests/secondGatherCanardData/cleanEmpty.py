import json
from pathlib import Path

DATA_FILE = "canard_detailed_data.json"
BACKUP_FILE = "canard_detailed_data_backup.json"

def is_empty_record(rec):
    """Return True if record is empty, placeholder, or just status=empty."""
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
    path = Path(DATA_FILE)
    if not path.exists():
        print(f"❌ {DATA_FILE} not found.")
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"📦 Loaded {len(data)} records from {DATA_FILE}")

    # Backup before cleaning
    path.rename(BACKUP_FILE)
    print(f"💾 Backup created → {BACKUP_FILE}")

    # Filter out empty records
    cleaned = {k: v for k, v in data.items() if not is_empty_record(v)}
    removed = len(data) - len(cleaned)
    print(f"🧹 Removed {removed} empty entries, kept {len(cleaned)} valid ones")

    # Overwrite original file with cleaned data
    with path.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"✅ Overwritten {DATA_FILE} with cleaned data")

    print("\n💡 You can now run:")
    print("   python3 verify_canard_data.py")
    print("to verify that all empty entries are gone.\n")

if __name__ == "__main__":
    main()
