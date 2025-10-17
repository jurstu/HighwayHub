import json
import subprocess
import time
from pathlib import Path

# --- CONFIGURATION ---
datasets = [f"dataset_{i}.json" for i in range(4)]
detailed_path = Path("canard_detailed_data.json")
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)
missing_file = Path("missing_ids.txt")

# --- LOAD IDS AND TYPES ---
id_type_map = {}
for ds_path in datasets:
    with open(ds_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for entry in data:
            id_type_map[str(entry["id"])] = entry.get("rodzajPomiaru", "").upper() or "RL"

# collect all IDs
all_ids = set(id_type_map.keys())

# load already completed
if detailed_path.exists():
    with open(detailed_path, "r", encoding="utf-8") as f:
        done_ids = set(json.load(f).keys())
else:
    done_ids = set()

# if user provided a missing_ids.txt, prefer that list
if missing_file.exists():
    missing_ids = [line.strip() for line in missing_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    missing_ids = [mid for mid in missing_ids if mid in all_ids]
else:
    missing_ids = sorted(all_ids - done_ids, key=int)
    missing_file.write_text("\n".join(missing_ids), encoding="utf-8")

print(f"🧩 {len(missing_ids)} IDs to process.")

# --- CURL TEMPLATE ---
BASE_URL = (
    "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen?"
    "p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
    "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
    "&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
)
COMMON_HEADERS = [
    "-H", "Accept: */*",
    "-H", "Accept-Language: en-GB,en;q=0.7",
    "-H", "Connection: keep-alive",
    "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
    "-b", "COOKIE_SUPPORT=true; font1=T; font2=F; font3=F; contrast=F; GUEST_LANGUAGE_ID=en_US; "
          "JSESSIONID=6DACDA935FB5DBB8A94822981198D868; LFR_SESSION_STATE_20103=1759865672914",
    "-H", "Origin: https://www.canard.gitd.gov.pl",
    "-H", "Referer: https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
    "-H", "Sec-Fetch-Dest: empty",
    "-H", "Sec-Fetch-Mode: cors",
    "-H", "Sec-Fetch-Site: same-origin",
    "-H", "Sec-GPC: 1",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "-H", "X-Requested-With: XMLHttpRequest",
    "-H", 'sec-ch-ua: "Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "-H", "sec-ch-ua-mobile: ?0",
    "-H", 'sec-ch-ua-platform: "Windows"',
]

# --- HELPER ---
def curl_download(mid: str, type_param: str, out_file: Path) -> bool:
    """Return True if successful and file is valid."""
    url = f"{BASE_URL}&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={type_param}"
    data_arg = f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id={mid}"
    cmd = ["curl", url, *COMMON_HEADERS, "--data-raw", data_arg]

    try:
        with open(out_file, "wb") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=20)
        if result.returncode != 0:
            print(f"⚠ {mid}: curl exit {result.returncode}")
            return False
        if out_file.stat().st_size < 40:  # small → usually gibberish header
            return False
        # quick heuristic check: first 4 bytes often non-UTF8 binary for good data
        with open(out_file, "rb") as f:
            first_bytes = f.read(16)
        if first_bytes.decode("utf-8", errors="ignore").strip() == "":
            # looks empty textwise, still OK
            return True
        if "ᯢ" in first_bytes.decode("utf-8", errors="ignore"):
            # known stub signature
            return False
        return True
    except Exception as e:
        print(f"❌ {mid}: {e}")
        out_file.unlink(missing_ok=True)
        return False

# --- MAIN LOOP ---
for i, mid in enumerate(missing_ids, 1):
    outfile = output_dir / f"{mid}.lzutf16"
    if outfile.exists() and outfile.stat().st_size > 0:
        print(f"[{i}/{len(missing_ids)}] {mid} already downloaded.")
        continue

    preferred_type = "PK" if id_type_map.get(mid, "RL") == "PK" else "RL"

    print(f"[{i}/{len(missing_ids)}] Fetching {mid} ({preferred_type}) ...", end=" ")

    # Try preferred type first
    if curl_download(mid, preferred_type, outfile):
        print("✅ OK")
    else:
        # Retry with the opposite type
        alt_type = "PK" if preferred_type == "RL" else "RL"
        print(f"↩ retrying as {alt_type} ...", end=" ")
        if curl_download(mid, alt_type, outfile):
            print("✅ OK (alt)")
        else:
            print("❌ failed both")
            outfile.unlink(missing_ok=True)
    time.sleep(0.4)

print("\n🎯 Done — all missing entries processed safely.")
