import re, json, requests
from lzstring import LZString
from time import sleep

lz = LZString()
URL = "https://www.canard.gitd.gov.pl/cms/o-nas/mapa-urzadzen"
session = requests.Session()
html = session.get(URL).text

# Extract namespace and URLs
ns_match = re.search(r'm\.namespace\s*=\s*"([^"]+)"', html)
namespace = ns_match.group(1) if ns_match else ""
urls = {k: re.search(rf'm\.obj{k}DataURL\s*=\s*"([^"]+)"', html)
        for k in ["PP", "OPP", "RL", "PK"]}
urls = {k: v.group(1) for k, v in urls.items() if v}
print("Namespace:", namespace)
print("URLs:", urls)

# Find compressed datasets
candidates = re.findall(r'"([A-Za-z0-9+/=]{200,})"', html)
datasets = {}
for idx, c in enumerate(candidates):
    try:
        d = lz.decompressFromBase64(c)
        if d and d.strip().startswith("["):
            datasets[f"dataset_{idx}"] = json.loads(d)
    except Exception:
        pass

# Pick one dataset (PP for example)
points = list(datasets.values())[0]
print(f"Loaded {len(points)} points")

enriched = []
for i, item in enumerate(points[:20]):  # test 20
    obj_id = item["id"]
    try:
        payload = {f"{namespace}id": obj_id}
        r = session.post(urls["PP"], data=payload)
        detail_raw = lz.decompressFromUTF16(r.text)
        if not detail_raw or detail_raw.strip() in ("{}", ""):
            print(f"#{i}: id={obj_id} empty")
            continue
        detail = json.loads(detail_raw)
        detail = json.loads(detail_raw)
        print(json.dumps(detail, indent=2, ensure_ascii=False))
        limits = []
        if "limity" in detail:
            for lim in detail["limity"]:
                val = lim.get("wartosc") or lim.get("limit")
                if val: limits.append(val)
        item["details"] = detail
        item["speed_limits"] = limits
        print(f"#{i}: id={obj_id}, limits={limits}")
        enriched.append(item)
        sleep(0.4)
    except Exception as e:
        print(f"#{i}: id={obj_id} failed ({e})")

with open("points_with_limits.json", "w", encoding="utf-8") as f:
    json.dump(enriched, f, indent=2, ensure_ascii=False)
print("✅ Done")

