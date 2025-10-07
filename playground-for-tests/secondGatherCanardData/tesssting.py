import requests

session = requests.Session()

# Example: paste cookies copied from browser "Cookie: a=1; b=2" string
cookie_header = "COOKIE_SUPPORT=true; font1=T; font2=F; contrast=F; JSESSIONID=ABC...; GUEST_LANGUAGE_ID=en_US"
cookies = {}
for kv in cookie_header.split(";"):
    if "=" in kv:
        k, v = kv.split("=", 1)
        cookies[k.strip()] = v.strip()

print(cookies)

# Use same headers the browser sent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Accept": "*/*",
    "Accept-Language": "en-GB,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.canard.gitd.gov.pl",
    "Referer": "https://www.canard.gitd.gov.pl/cms/en/mapa-urzadzen",
    "X-Requested-With": "XMLHttpRequest",
}

url = "https://www.canard.gitd.gov.pl/cms/en/web/guest/mapa-urzadzen?p_p_id=pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd&p_p_resource_id=%2Fobjdata"
payload = {"_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_id": 87764188, "_pl_canard_cms_portlet_mapa_INSTANCE_URMGfsNrnTYd_type":"PP"}

r = session.post(url, headers=headers, data=payload, timeout=10)
print(r.status_code, r.headers.get("content-type"))
print("len:", len(r.content))
print("body preview:", r.text[:])
