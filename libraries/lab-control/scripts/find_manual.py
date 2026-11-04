"""Locate a literal command in locally acquired manufacturer PDF text."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('source')
p.add_argument('terms', nargs='+')
p.add_argument('--limit', type=int, default=8)
p.add_argument('--context', type=int, default=250)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
pages = json.loads((root/'.manual-cache'/f'{a.source}.pages.json').read_text(encoding='utf-8'))
for term in a.terms:
    print(f'--- {term} ---')
    matches = 0
    for i, page in enumerate(pages, 1):
        pos = page.casefold().find(term.casefold())
        if pos >= 0:
            print(f'PDF p.{i}: {page[max(0,pos-a.context):pos+len(term)+a.context]}')
            matches += 1
            if matches >= a.limit:
                break
