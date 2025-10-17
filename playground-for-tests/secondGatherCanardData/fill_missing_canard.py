#!/usr/bin/env python3
import os
import json
import time
import subprocess
from lzstring import LZString

lz = LZString()

# --- CONFIG ---
DATA_FILE = "canard_detailed_data.json"
DATASETS = ["dataset_0.json", "dataset_1.json", "dataset_2.json", "dataset_3.json"]

# You can paste the cookie string directly from your browser here (refresh often)
COOKIE_HEADER = (
    "COOKIE_SUPPORT=true; font1=T; font2=F; font3=F; contrast=F; "
    "GUEST_LANGUAGE_ID=en_US; JSESSIONID=YOUR_SESSION_ID_HERE; "
    "LFR_SESSION_STATE_20103=YOUR_STATE_ID_HERE"
)

# --- UTILS ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def build_curl_command(pid: int, data_type: str):
    """Builds a curl command matching what your browser sends."""
    url = (
        f"https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen?"
        f"p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd&"
        f"p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&"
        f"p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage&"
        f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={data_type}"
    )

    data = f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id={pid}"

    cmd = [
        "curl", "-s", url,
        "-H", "Accept: */*",
        "-H", "Accept-Language: en-GB,en;q=0.7",
        "-H", "Connection: keep-alive",
        "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
        "-H", f"Cookie: {COOKIE_HEADER}",
        "-H", "Origin: https://www.canard.gitd.gov.pl",
        "-H", "Referer: https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "-H", "X-Requested-With: XMLHttpRequest",
        "--data-raw", data,
    ]
    return cmd

def fetch_point(pid: int, data_type="PP"):
    """Run curl + node decoder pipeline."""
    cmd = build_curl_command(pid, data_type)
    try:
        curl_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if curl_proc.returncode != 0:
            print(f"⚠ Curl error for {pid}: {curl_proc.stderr.strip()}")
            return None

        raw = curl_proc.stdout.strip()
        if not raw:
            print(f"⚠ Empty response for {pid}")
            return None

        decode_proc = subprocess.run(
            ["node", "decode_canard.mjs"],
            input=raw,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if decode_proc.returncode != 0:
            print(f"⚠ Decode error for {pid}: {decode_proc.stderr.strip()}")
            return None

        out = decode_proc.stdout.strip()
        return json.loads(out)

    except Exception as e:
        print(f"⚠ Exception for {pid}: {e}")
        return None


def main():
    # Load main data
    detailed_data = load_json(DATA_FILE)
    all_points = []
    for ds in DATASETS:
        data = load_json(ds)
        print(f"✅ Loaded {len(data)} points from {ds}")
        all_points.extend(data)

    unique_points = {str(p["id"]): p for p in all_points}
    empty_ids = [k for k, v in detailed_data.items() if not v or v == {} or v.get("status") == "empty"]
    missing_ids = list(set(unique_points.keys()) - set(detailed_data.keys())) + empty_ids

    print(f"🧩 Missing or empty entries: {len(missing_ids)}")
    if not missing_ids:
        print("✅ Everything already filled.")
        return

    for i, pid in enumerate(missing_ids, 1):
        meta = unique_points.get(pid, {})
        dtype = meta.get("rodzajPomiaru", "PP")

        print(f"[{i}/{len(missing_ids)}] Fetching {pid} ({dtype}) ...")
        data = fetch_point(int(pid), dtype)

        if data:
            detailed_data[pid] = data
            save_json(DATA_FILE, detailed_data)
            print(f"💾 Saved {pid}")
        else:
            print(f"❌ Failed {pid}")

        time.sleep(1.0)  # polite delay

    print("🏁 Done — missing entries fetched.")


if __name__ == "__main__":
    main()
