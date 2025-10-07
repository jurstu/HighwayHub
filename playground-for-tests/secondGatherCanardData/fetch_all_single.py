import os
import re
import json
import time
import requests
import subprocess
from lzstring import LZString

# ---------- CONFIG ----------

lz = LZString()
SESSION = requests.Session()

URL_BASE = "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
MAIN_PAGE = "https://www.canard.gitd.gov.pl/cms/o-nas/mapa-urzadzen"
DATA_FILE = "canard_detailed_data.json"

# copy these from your own curl/devtools
COOKIES = {
    "COOKIE_SUPPORT": "true",
    "font1": "T",
    "font2": "F",
    "font3": "F",
    "contrast": "F",
    "GUEST_LANGUAGE_ID": "en_US",
    "JSESSIONID": "C7AAF907DBF632B9806CDB5012487849",
    "LFR_SESSION_STATE_20103": "1759861420747",
}

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-GB,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.canard.gitd.gov.pl",
    "Referer": "https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}

SESSION.cookies.update(COOKIES)
SESSION.headers.update(HEADERS)

# ---------- UTILITIES ----------

def load_progress():
    """Load previous progress (already-downloaded points)."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_progress(data):
    """Atomically save progress to disk."""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def fetch_main_datasets():
    """Download the compressed list of all measurement points."""
    html = SESSION.get(MAIN_PAGE).text
    compressed = re.findall(r'"([A-Za-z0-9+/=]{200,})"', html)
    datasets = []
    for comp in compressed:
        try:
            dec = lz.decompressFromBase64(comp)
            if dec and dec.strip().startswith("["):
                datasets.extend(json.loads(dec))
        except Exception:
            pass
    print(f"✅ Loaded {len(datasets)} points from main map")
    return datasets

def build_canard_url(data_type: str) -> str:
    """Build the correct URL for PP / OPP / PC request type."""
    return (
        f"{URL_BASE}"
        "?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        "&p_p_lifecycle=2"
        "&p_p_state=normal"
        "&p_p_mode=view"
        "&p_p_resource_id=%2Fobjdata"
        "&p_p_cacheability=cacheLevelPage"
        f"&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={data_type}"
    )

def fetch_point(pid: int, data_type="PP"):
    """Fetch a single point using the same cookies + Node decoder."""
    url = build_canard_url(data_type)
    payload = {"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id": pid}

    try:
        r = SESSION.post(url, data=payload, timeout=15)
        if not r.text.strip():
            print(f"⚠ {pid} empty HTTP body")
            return None
    except Exception as e:
        print(f"⚠ Error fetching {pid}: {e}")
        return None

    # run Node.js decoder
    proc = subprocess.run(
        ["node", "decode_canard.mjs"],
        input=r.text,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(f"⚠ Decoder error for {pid}: {proc.stderr.strip()}")
        return None

    try:
        return json.loads(proc.stdout.strip())
    except Exception:
        print(f"⚠ JSON parse failed for {pid}")
        return None

# ---------- MAIN LOGIC ----------

def main():
    detailed_data = load_progress()
    all_points = fetch_main_datasets()

    for i, point in enumerate(all_points, 1):
        pid = point.get("id")
        data_type = point.get("rodzajPomiaru", "PP")  # PP / OPP / PC

        if not pid:
            continue
        if str(pid) in detailed_data:
            print(f"⏩ Skipping {pid}, already downloaded")
            continue

        print(f"[{i}/{len(all_points)}] Fetching id={pid} ({data_type}) ...")
        data = fetch_point(pid, data_type)
        if data:
            detailed_data[str(pid)] = data
            save_progress(detailed_data)
            print(f"✅ Saved {pid}")
        else:
            print(f"❌ Failed {pid}")

        time.sleep(0.5)  # polite delay

    print(f"🎉 Done. Saved {len(detailed_data)} records to {DATA_FILE}")

if __name__ == "__main__":
    main()
