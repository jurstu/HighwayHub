import subprocess
import json
from pathlib import Path

# --- CONFIGURATION ---
output_dir = Path("../3-outputs-that-were-missing/datablobs/")
output_json = Path("../canard_detailed_data.json")

# --- LOAD EXISTING ---
if output_json.exists():
    with open(output_json, "r", encoding="utf-8") as f:
        detailed_data = json.load(f)
else:
    detailed_data = {}

print(f"📂 Loaded {len(detailed_data)} existing entries.")

# --- FIND NEW FILES ---
files = sorted(output_dir.glob("*.lzutf16"))
new_files = [f for f in files if f.stem not in detailed_data]

print(f"🧩 {len(new_files)} new raw files to decode.")

# --- MAIN LOOP ---
for i, file_path in enumerate(new_files, 1):
    mid = file_path.stem
    print(f"[{i}/{len(new_files)}] Decoding {mid} ...", end=" ")

    try:
        # Run Node decoder
        with open(file_path, "rb") as f:
            raw_data = f.read()

        # Call your Node decoder script
        proc = subprocess.run(
            ["node", "decode_canard.mjs"],
            input=raw_data.decode(),  # pass as text to Node
            capture_output=True,
            text=True,
            timeout=20,
        )

        if proc.returncode != 0 or not proc.stdout.strip():
            print(f"⚠️ failed (code {proc.returncode})")
            if proc.stderr:
                print("   stderr:", proc.stderr.strip())
            continue

        # Try parsing Node output
        try:
            print(proc.stdout)
            decoded = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print("⚠️ invalid JSON output")
            continue

        # Store under ID
        detailed_data[mid] = decoded
        print("✅ saved")

        # Save incrementally every file
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(detailed_data, f, ensure_ascii=False, indent=2)

    except subprocess.TimeoutExpired:
        print("⏱️ timeout")
    except Exception as e:
        print(f"❌ error: {e}")

print("\n🎯 Done — all decoded entries merged into canard_detailed_data.json.")
