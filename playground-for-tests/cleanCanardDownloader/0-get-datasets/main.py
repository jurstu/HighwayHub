import re
import json
import requests
from lzstring import LZString

lz = LZString()
URL = "https://www.canard.gitd.gov.pl/cms/o-nas/mapa-urzadzen"

session = requests.Session()
resp = session.get(URL)
resp.raise_for_status()
html = resp.text

# Step 1: Find all Base64 strings in the HTML that look like LZString payloads
# They are usually very long and wrapped in quotes
candidates = re.findall(r'"([A-Za-z0-9+/=]{200,})"', html)

if not candidates:
    raise RuntimeError("No Base64 payloads found in page")

print(f"Found {len(candidates)} compressed datasets")

datasets = {}
for idx, compressed in enumerate(candidates):
    try:
        decoded = lz.decompressFromBase64(compressed)
        if decoded and decoded.strip().startswith("["):
            data = json.loads(decoded)
            datasets[f"dataset_{idx}"] = data
            print(f"Decoded dataset_{idx}: {len(data)} features")
    except Exception as e:
        print(f"Candidate {idx} failed: {e}")

# Save each dataset to file
for name, data in datasets.items():
    with open(f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Done. Decoded datasets saved as dataset_X.json")