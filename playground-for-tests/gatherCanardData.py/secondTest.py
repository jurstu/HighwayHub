import requests
import json
import struct
from lzstring2 import LZString

lz = LZString()

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
    print("HTTP", r.status_code, "len=", len(r.content))
    raw = r.content

    # Interpret bytes as UTF-16 little endian 16-bit code units (JS uses 16-bit UCS-2)
    # If length is odd, pad with a zero byte.
    if len(raw) % 2:
        raw = raw[:-1]
    code_units = struct.unpack("<" + "H" * (len(raw) // 2), raw)
    print(code_units)

    decompressed = lz.decompressFromUTF16(str(r.content))
    print(len(decompressed))
    if not decompressed:
        raise RuntimeError("LZString failed to decompress")

    try:
        data = json.loads(decompressed)
    except Exception:
        print("Decompressed text preview:", f"'{decompressed}'")
        raise

    return data

data = fetch_point(87764188)
print(json.dumps(data, indent=2, ensure_ascii=False))
