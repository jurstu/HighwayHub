import os
import re
import json
import time
import requests
import subprocess
from lzstring import LZString

lz = LZString()
SESSION = requests.Session()

URL_BASE = "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
MAIN_PAGE = "https://www.canard.gitd.gov.pl/cms/o-nas/mapa-urzadzen"
DATA_FILE = "canard_detailed_data.json"


def load_progress():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_main_datasets():
    """Download the initial compressed datasets list."""
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


def fetch_point(pid: int):
    """Fetch single point details using Node.js decoder."""
    url = (
        f"{URL_BASE}?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        f"&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        f"&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
        f"&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type=OPP"
    )
    payload = {"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id": pid}

    try:
        r = SESSION.post(url, data=payload, timeout=15)
        if not r.text.strip():
            return None
    except Exception as e:
        print(f"⚠ Error fetching {pid}: {e}")
        return None

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


def main():
    detailed_data = load_progress()
    all_points = fetch_main_datasets()

    for i, point in enumerate(all_points, 1):
        pid = point.get("id")
        if not pid:
            continue

        if str(pid) in detailed_data:
            print(f"⏩ Skipping {pid}, already downloaded")
            continue

        print(f"[{i}/{len(all_points)}] Fetching id={pid} ...")
        data = fetch_point(pid)
        if data:
            detailed_data[str(pid)] = data
            save_progress(detailed_data)
            print(f"✅ Saved {pid}")
        else:
            print(f"❌ Failed {pid}")

        time.sleep(0.5)  # be polite to the server

    print("🎉 Done! All data saved in", DATA_FILE)


if __name__ == "__main__":
    main()
