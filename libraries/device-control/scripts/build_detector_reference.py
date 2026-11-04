"""Join reviewed detector pages to the already acquired official-source hashes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = {
    'rs-esw': ([473, 474, 478, 484, 485, 557, 558, 561, 562], 'Verified single-bargraph receiver commands and readbacks'),
    'rs-esr': ([607, 608, 609, 610, 612, 615, 637, 638, 639, 640], 'Verified single-bargraph receiver commands and readbacks'),
    'rs-epl': ([407, 408, 464], 'Detector/filter documented; verified receiver-grid workflow NOT integrated'),
    'rs-fsw': ([1097, 1262, 1263], 'QP/CISPR-average requires K54 and CISPR filter; final-measurement workflow NOT integrated'),
    'rs-esu': ([53, 54, 56, 621], 'Receiver/trace detectors documented; verified-grid workflow NOT integrated'),
    'keysight-xsa-b': ([401, 402, 403, 554, 555, 556], 'Scalar voltage averaging differs from RMS; QPE/EAV support/options not integrated')
}


def main():
    sources = json.loads((ROOT.parent/'lab-control/dgm_lab/data/sources.json').read_text(encoding='utf-8'))
    rows = []
    for key, (pages, scope) in REVIEWS.items():
        source = next(s for s in sources if s['id'] == key)
        rows.append(dict(source_id=key, url=source['url'], sha256=source['sha256'],
                         reviewed_pdf_pages=pages, scope=scope, physical_verified=False))
    result = dict(reviewed_date='2026-11-05', manuals=rows,
                  receiver_range_reference='https://www.rohde-schwarz.com/de/produkte/messtechnik/funkstoermessempfaenger/rs-esr-funkstoermessempfaenger_63493-17877.html',
                  note='Page numbers count the PDF cover as page 1; original PDFs are not redistributed')
    (ROOT/'dgm_control/data/detector-sources.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} detector source records with official URL, SHA256 and reviewed pages')


if __name__ == '__main__': main()
