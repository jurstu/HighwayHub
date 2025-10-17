import os
import re
import json
import time
import random
import requests
import subprocess
from lzstring import LZString
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

lz = LZString()
SESSION = requests.Session()
LOCK = Lock()

URL_BASE = "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
MAIN_PAGE = "https://www.canard.gitd.gov.pl/cms/o-nas/mapa-urzadzen"
DATA_FILE = "canard_detailed_data.json"

MAX_WORKERS = 3           # tweak for rate-limit tolerance
RETRY_DELAY = 3.0         # seconds before retry on error


def load_progress():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


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


def worker(point, shared_data, index, total):
    pid = point.get("id")
    if not pid:
        return

    print(f"[{index}/{total}] Fetching id={pid} ...")

    data = fetch_point(pid)
    if not data or (isinstance(data, dict) and not data):
        data = {"id": pid, "status": "empty"}

    with LOCK:
        shared_data[str(pid)] = data
        save_progress(shared_data)

    if data.get("status") == "empty":
        print(f"⚪ {pid} → EMPTY")
    else:
        print(f"✅ Saved {pid}")


def main():
    detailed_data = load_progress()
    all_points = fetch_main_datasets()

    todo = [p for p in all_points if str(p.get("id")) not in detailed_data]
    total = len(todo)
    print(f"🔹 Need to fetch {total} new points")

    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(worker, p, detailed_data, i + 1, total): p for i, p in enumerate(todo)
        }
        for f in as_completed(futures):
            time.sleep(random.uniform(0.2, 0.8))  # gentle rate control

    print(f"🏁 Completed in {time.time() - start:.1f}s")
    print(f"💾 Total entries: {len(detailed_data)}")


if __name__ == "__main__":
    main()
