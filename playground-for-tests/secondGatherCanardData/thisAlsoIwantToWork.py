#!/usr/bin/env python3
"""
fetch_point_rl.py

Fetch a single RL point using curl (to mimic the browser exactly),
decode the LZString/UTF-16 payload via a Node decoder, and save JSON.

Edit COOKIE_HEADER and (optionally) NODE_DECODER before running.
"""

import subprocess
import shlex
import json
import sys
import time
from pathlib import Path

# --- CONFIG: paste fresh cookie header from DevTools here (value after "Cookie: ") ---
COOKIE_HEADER = (
    "COOKIE_SUPPORT=true; font1=T; font2=F; font3=F; contrast=F; "
    "GUEST_LANGUAGE_ID=en_US; JSESSIONID=6DACDA935FB5DBB8A94822981198D868; "
    "LFR_SESSION_STATE_20103=1759865672914"
)

# Point to fetch (from your curl example)
PID = 6506621
TYPE = "RL"   # as in your curl

# Path to the Node decoder script that accepts raw bytes on stdin and prints JSON
NODE_DECODER = "decode_canard.mjs"   # adjust if necessary

# Output file
OUT_JSON = f"point_{PID}_{TYPE}.json"

# curl binary and basic options
CURL_BIN = "curl"


def build_curl_command(pid: int, dtype: str, cookie_header: str):
    url = (
        "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
        "?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        "&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
        f"&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type={dtype}"
    )

    cmd = [
        CURL_BIN,
        "-sS",               # silent but show errors
        "-X", "POST",
        url,
        "-H", "Accept: */*",
        "-H", "Accept-Language: en-GB,en;q=0.7",
        "-H", "Connection: keep-alive",
        "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
        "-H", "Origin: https://www.canard.gitd.gov.pl",
        "-H", "Referer: https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
        "-H", "X-Requested-With: XMLHttpRequest",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "-b", cookie_header,
        "--data-raw", f"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id={pid}",
    ]
    return cmd


def run_curl(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        print("❌ curl not found on PATH. Install curl or use a different method.", file=sys.stderr)
        return None, proc if 'proc' in locals() else None

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace")
        print("❌ curl failed:", stderr, file=sys.stderr)
        return None, proc

    return proc.stdout, proc


def run_node_decoder(decoder_path, input_bytes):
    # run node decoder; pass bytes on stdin
    proc = subprocess.run(["node", decoder_path], input=input_bytes, capture_output=True)
    if proc.returncode != 0:
        print("❌ Node decoder failed:", proc.stderr.decode("utf-8", "replace"), file=sys.stderr)
        return None, proc
    return proc.stdout.decode("utf-8", "replace"), proc


def main():
    # sanity checks
    if not Path(NODE_DECODER).exists():
        print(f"❗ Node decoder '{NODE_DECODER}' not found. Make sure it exists and is executable.")
        return 2

    curl_cmd = build_curl_command(PID, TYPE, COOKIE_HEADER)
    print("→ Running curl:")
    print("  ", " ".join(shlex.quote(p) for p in curl_cmd))

    raw, curl_proc = run_curl(curl_cmd)
    if raw is None:
        return 3

    print("HTTP response length:", len(raw))
    # quick preview
    preview = raw[:400]
    try:
        print("Preview (utf-8):", preview.decode("utf-8"))
    except Exception:
        print("Preview (latin1):", preview.decode("latin1", "replace"))

    # quick empty checks
    if not raw.strip():
        print("⚠ Empty response body.")
        return 4
    if raw.strip() in (b"{}"):
        print("⚠ Server returned placeholder/empty content:", raw.strip()[:200])
        return 5

    # pass raw bytes to node decoder
    print("→ Running Node decoder:", NODE_DECODER)
    node_out, node_proc = run_node_decoder(NODE_DECODER, raw)
    if node_out is None:
        return 6

    node_out = node_out.strip()
    if not node_out:
        print("⚠ Node produced empty output.")
        return 7

    # attempt JSON parse
    try:
        data = json.loads(node_out)
    except json.JSONDecodeError:
        print("⚠ JSON decoding of node output failed. Node output (first 2000 chars):")
        print(node_out[:2000])
        return 8

    # Save to file
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Decoded JSON saved to {OUT_JSON}")
    print("Preview of top-level keys / sample:")
    if isinstance(data, dict):
        for k in list(data.keys())[:20]:
            print("  ", k)
    else:
        print("  (non-dict JSON root)")

    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
