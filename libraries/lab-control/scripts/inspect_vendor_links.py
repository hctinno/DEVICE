"""Read public vendor page/script URLs; no login or credential discovery."""
import argparse
import re
import requests
from urllib.parse import urljoin

p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('--scripts',action='store_true');a=p.parse_args()
r=requests.get(a.url,timeout=(10,30));r.raise_for_status()
urls=re.findall(r'(?:src|href)=["\x27]([^"\x27]+)',r.text)
for url in urls:
    print(urljoin(a.url,url))
    if a.scripts and url.endswith('.js'):
        s=requests.get(urljoin(a.url,url),timeout=(10,30));s.raise_for_status()
        for match in re.finditer(r'.{0,120}(?:\.pdf|user_guide|FBSM|TMX0108|resources|download).{0,160}',s.text,re.I):
            print(match.group())
