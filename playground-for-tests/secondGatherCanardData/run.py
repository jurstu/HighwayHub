import requests
import subprocess
import json

def fetch_point(pid: int):
    url = (
        "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen"
        "?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd"
        "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        "&p_p_resource_id=%2Fobjdata&p_p_cacheability=cacheLevelPage"
        "&_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type=PP"
    )

    payload = {"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id": pid}
    r = requests.post(url, data=payload)
    print("HTTP", r.status_code, "len=", len(r.text))
    if not r.text.strip():
        print("⚠ Empty response")
        return None

    # Run Node.js decoder
    proc = subprocess.run(
        ["node", "decode_canard.mjs"],
        input=r.text,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print("Decoder error:", proc.stderr.strip())
        return None

    decoded = proc.stdout.strip()
    try:
        return json.loads(decoded)
    except Exception:
        print("⚠ JSON parse failed, preview:")
        print(decoded[:500])
        return None


if __name__ == "__main__":
    data = fetch_point(87764188)
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))
