import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# --- CONFIG ---
THREADS = 12  # 🚀 adjust for your CPU/network
datasets = [f"../0-get-datasets/dataset_{i}.json" for i in range(4)]
detailed_path = Path("../canard_detailed_data.json")
output_dir = Path("../3-outputs-that-were-missing/datablobs")
output_dir.mkdir(exist_ok=True)
missing_file = Path("../missing_ids.txt")
log_file = Path("download_log.txt")

# --- MAP rodzajPomiaru → endpoint type ---
TYPE_MAP = {
    "PK": "PK",
    "PP": "PP",
    "PR": "RL",
    "RL": "RL",
    "OP": "OPP",
    "ODCINKOWY": "OPP",
}
def guess_endpoint(rodzaj: str) -> str:
    rodzaj = (rodzaj or "").upper().strip()
    return TYPE_MAP.get(rodzaj, "RL")

# --- LOAD IDS ---
id_type_map = {}
for ds_path in datasets:
    with open(ds_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for entry in data:
            rid = str(entry["id"])
            rodzaj = entry.get("rodzajPomiaru", "")
            id_type_map[rid] = guess_endpoint(rodzaj)

all_ids = set(id_type_map.keys())

if detailed_path.exists():
    with open(detailed_path, "r", encoding="utf-8") as f:
        done_ids = set(json.load(f).keys())
else:
    done_ids = set()

if missing_file.exists():
    missing_ids = [x.strip() for x in missing_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    missing_ids = [m for m in missing_ids if m in all_ids]
else:
    missing_ids = sorted(all_ids - done_ids, key=int)
    missing_file.write_text("\n".join(missing_ids), encoding="utf-8")

print(f"🧩 {len(missing_ids)} IDs to process with {THREADS} threads.")

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
          "JSESSIONID=F5D532B83CB663AF603614DA62CCD058; LFR_SESSION_STATE_20103=1759918642522",
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

# --- SAFE LOGGER ---
log_lock = Lock()
def log(msg):
    with log_lock:
        print(msg, flush=True)
        log_file.open("a", encoding="utf-8").write(msg + "\n")

# --- DOWNLOADER ---
def curl_download(mid: str, type_param: str, out_file: Path) -> bool:
    """Run curl, validate result."""
    url = f"{BASE_URL}&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={type_param}"
    data_arg = f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id={mid}"
    cmd = ["curl", "-sS", url, *COMMON_HEADERS, "--data-raw", data_arg]

    try:
        with open(out_file, "wb") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=20)
        if result.returncode != 0:
            return False
        size = out_file.stat().st_size
        if size < 40:
            return False
        with open(out_file, "rb") as f:
            chunk = f.read(64)
        txt = chunk.decode("utf-8", errors="ignore")
        if "ᯢ" in txt or txt.strip() == "":
            return False
        return True
    except Exception:
        out_file.unlink(missing_ok=True)
        return False

def process_id(mid: str):
    outfile = output_dir / f"{mid}.lzutf16"
    if outfile.exists() and outfile.stat().st_size > 0:
        return f"{mid}: already exists"

    preferred_type = id_type_map.get(mid, "RL")
    if curl_download(mid, preferred_type, outfile):
        return f"{mid}: ✅ OK ({preferred_type})"
    for alt in ["PK", "PP", "RL", "OPP"]:
        if alt == preferred_type:
            continue
        if curl_download(mid, alt, outfile):
            return f"{mid}: ✅ OK (alt={alt})"
    outfile.unlink(missing_ok=True)
    return f"{mid}: ❌ failed all types"

# --- MAIN PARALLEL LOOP ---
start = time.time()
with ThreadPoolExecutor(max_workers=THREADS) as ex:
    futures = {ex.submit(process_id, mid): mid for mid in missing_ids}
    for i, fut in enumerate(as_completed(futures), 1):
        mid = futures[fut]
        try:
            msg = fut.result()
        except Exception as e:
            msg = f"{mid}: ❌ exception {e}"
        log(f"[{i}/{len(futures)}] {msg}")

elapsed = time.time() - start
log(f"\n🎯 Done in {elapsed:.1f}s — processed {len(missing_ids)} entries with {THREADS} threads.")
