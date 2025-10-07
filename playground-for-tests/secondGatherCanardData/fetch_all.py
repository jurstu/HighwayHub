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

MAX_WORKERS = 4           # lower concurrency helps survive throttling
MAX_RETRIES = 5
BASE_DELAY = 2.0          # seconds before first retry
FAIL_SLEEP = 15           # cool-down if many recent failures


def load_progress():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        #print(f"data added: {json.dumps(data, indent=4)}")
    os.replace(tmp, DATA_FILE)


def fetch_main_datasets():
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


def fetch_point(pid: int, meta: dict):
    url = (
        f"{URL_BASE}?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        f"&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        f"&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
        f"&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type=PP"
    )
    payload = {"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id": pid}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # small random jitter between threads
            time.sleep(random.uniform(0.5, 1.8))
            r = SESSION.post(url, data=payload, timeout=15)
            if not r.text.strip():
                raise ValueError("empty response")

            proc = subprocess.run(
                ["node", "decode_canard.mjs"],
                input=r.text,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"decoder: {proc.stderr.strip()}")

            result = proc.stdout.strip()
            data = json.loads(result)
            kind = data.get("urzadzenie", {}).get("rodzajPomiaru") or meta.get("rodzajPomiaru", "???")
            print(f"✅ {pid} [{kind}] OK,            {""}")
            return data

        except Exception as e:
            delay = BASE_DELAY * (2 ** (attempt - 1)) + random.random()
            print(f"⚠ {pid} ({meta.get('rodzajPomiaru','?')}) fail #{attempt}: {e} → retry in {delay:.1f}s")
            time.sleep(delay)

    print(f"❌ {pid} permanently failed after {MAX_RETRIES} attempts")
    return None


def worker(point, shared_data):
    pid = point["id"]
    meta = point
    print(f"➡ Fetching {pid}: {meta.get('rodzajPomiaru','unknown')} ({meta.get('nazwa','no name')})")

    data = fetch_point(pid, meta)
    if not data or (isinstance(data, dict) and not data):
        # mark explicitly as empty
        empty_info = {
            "id": pid,
            "status": "empty",
            "rodzajPomiaru": meta.get("rodzajPomiaru", "unknown"),
            "nazwa": meta.get("nazwa", "no name"),
        }
        with LOCK:
            shared_data[str(pid)] = empty_info
            save_progress(shared_data)
        print(f"⚪ {pid} → EMPTY")
    else:
        with LOCK:
            shared_data[str(pid)] = data
            save_progress(shared_data)
        print(f"💾 Saved {pid} OK")


def main():
    detailed_data = load_progress()
    all_points = fetch_main_datasets()
    todo = [p for p in all_points if str(p["id"]) not in detailed_data]
    print(f"🔹 Need to fetch {len(todo)} new points")

    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(worker, p, detailed_data): p for p in todo}
        for i, f in enumerate(as_completed(futures), 1):
            pid = futures[f]["id"]
            print(f"[{i}/{len(todo)}] finished {pid}")

    print(f"🏁 Completed in {time.time() - start:.1f}s")
    print(f"💾 Total entries: {len(detailed_data)}")


if __name__ == "__main__":
    main()
