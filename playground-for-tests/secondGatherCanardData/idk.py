#!/usr/bin/env python3
# curl_then_node.py
# Fetch a single point with curl (as your browser did) and decode it with Node.

import subprocess
import json
import sys
import shlex
import time

# === CONFIG ===
# Put the cookie header you copy from DevTools here (everything after "Cookie: ")
COOKIE_HEADER = (
    "COOKIE_SUPPORT=true; font1=T; font2=F; font3=F; contrast=F; "
    "GUEST_LANGUAGE_ID=en_US; JSESSIONID=C7AAF907DBF632B9806CDB5012487849; "
    "LFR_SESSION_STATE_20103=1759861420747"
)

# change PID and TYPE as needed
PID = 8552896
TYPE = "PC"  # PP, OPP, PC

# location of your node decoder script (must accept stdin string and print decoded JSON)
NODE_DECODER = "decode_canard.mjs"

# how many attempts before giving up
MAX_RETRIES = 3
RETRY_DELAY = 2.0

# === build curl command ===
def build_curl_command(pid: int, dtype: str, cookie_header: str):
    url = (
        "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
        "?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        "&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
        f"&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={dtype}"
    )

    # Curl command that matches what the browser sends (headers + cookie)
    cmd = [
        "curl",
        "-sS",  # silent but show errors
        "-X", "POST",
        url,
        "-H", "Accept: */*",
        "-H", "Accept-Language: en-GB,en;q=0.7",
        "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
        "-H", "Origin: https://www.canard.gitd.gov.pl",
        "-H", "Referer: https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "-b", cookie_header,
        "--data-raw", f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id={pid}",
    ]
    return cmd

# === helpers ===
def run_curl_and_decode(pid: int, dtype: str, cookie_header: str):
    curl_cmd = build_curl_command(pid, dtype, cookie_header)
    curl_cmd_display = " ".join(shlex.quote(p) for p in curl_cmd)
    print("→ Running curl:", curl_cmd_display)

    # 1) run curl
    try:
        curl_proc = subprocess.run(curl_cmd, capture_output=True)
    except FileNotFoundError:
        print("❌ curl not found. Install curl or adjust the script to use requests/playwright.", file=sys.stderr)
        return None

    if curl_proc.returncode != 0:
        print("❌ curl failed:", curl_proc.stderr.decode("utf-8", "replace"), file=sys.stderr)
        return None

    response_bytes = curl_proc.stdout
    print("HTTP response length:", len(response_bytes))

    # quick textual preview (safe to show first 400 bytes, escaped)
    preview = response_bytes[:400]
    try:
        print("Preview (utf-8):", preview.decode("utf-8"))
    except Exception:
        print("Preview (latin1):", preview.decode("latin1", "replace"))

    # handle obvious empty / short responses
    if not response_bytes or response_bytes.strip() in (b"", b"{}"):
        print("⚠ Empty or placeholder response from server.")
        return None

    # 2) call node decoder, pipe the raw response bytes into stdin
    # Note: we pass bytes directly and set text=False so node receives raw bytes unmodified.
    node_cmd = ["node", NODE_DECODER]
    print("→ Running node decoder:", " ".join(node_cmd))
    node_proc = subprocess.run(node_cmd, input=response_bytes, capture_output=True)

    if node_proc.returncode != 0:
        stderr = node_proc.stderr.decode("utf-8", "replace")
        print("❌ Node decoder failed:", stderr, file=sys.stderr)
        return None

    node_out = node_proc.stdout.decode("utf-8", "replace").strip()
    if not node_out:
        print("⚠ Node produced empty output")
        return None

    # 3) try to parse JSON
    try:
        data = json.loads(node_out)
        return data
    except json.JSONDecodeError:
        print("⚠ JSON decode failed. Node output preview:")
        print(node_out[:800])
        return None

# === main loop with retries ===
def main():
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nAttempt {attempt}/{MAX_RETRIES} for PID={PID} TYPE={TYPE}")
        data = run_curl_and_decode(PID, TYPE, COOKIE_HEADER)
        if data is not None:
            print("✅ Decoded JSON successfully:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
            return 0
        else:
            backoff = RETRY_DELAY * (2 ** (attempt - 1))
            print(f"⏳ Retry after {backoff:.1f}s ...")
            time.sleep(backoff)

    print("❌ All attempts failed.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
