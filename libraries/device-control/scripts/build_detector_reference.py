"""Join reviewed detector pages to the already acquired official-source hashes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = {
    'rs-esw': ([473, 474, 478, 484, 485, 557, 558, 561, 562], 'Verified single-bargraph receiver commands and readbacks'),
    'rs-esr': ([607, 608, 609, 610, 612, 615, 637, 638, 639, 640], 'Verified single-bargraph receiver commands and readbacks'),
    'rs-epl': ([387, 388, 395, 396, 397, 398, 401, 404, 407, 408, 459, 460, 464], 'Single bargraph, standard EMI functionality, EPL1000 <=30 MHz'),
    'rs-fsw': ([339, 340, 344, 348, 618, 905, 906, 1096, 1097, 1098, 1100, 1101, 1102, 1103, 1216, 1289, 1290, 1291], 'K54-gated final marker; not ordinary spectrum trace'),
    'rs-esu': ([53, 54, 55, 56, 557, 578, 579, 580, 581, 590, 610, 611, 622, 698, 699, 702], 'Single receiver bargraph; AVER voltage envelope (not spectrum mode average power)'),
    'keysight-xsa-a': ([414, 638, 709, 710, 711, 712, 713, 714, 715, 716, 717, 754], 'EMC-gated Measure-at-Marker A.02.00+; scalar voltage average'),
    'keysight-xsa-b': ([378, 379, 380, 384, 385, 386, 401, 402, 403, 452, 523, 524, 2942], 'EMC-gated Measure-at-Marker; zero span avoids zoom; QPE/EAV/AVER+SCAL')
}


def main():
    sources = json.loads((ROOT.parent/'lab-control/dgm_lab/data/sources.json').read_text(encoding='utf-8'))
    rows = []
    for key, (pages, scope) in REVIEWS.items():
        source = next(s for s in sources if s['id'] == key)
        rows.append(dict(source_id=key, url=source['url'], sha256=source['sha256'],
                         reviewed_pdf_pages=pages, scope=scope, physical_verified=False))
    result = dict(reviewed_date='2026-11-05', manuals=rows,
                  epl_range_reference='https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_brochures_and_datasheets/specifications/3683_7819_22/EPL_specs_en_3683-7819-22_v0800.pdf',
                  receiver_range_reference='https://www.rohde-schwarz.com/de/produkte/messtechnik/funkstoermessempfaenger/rs-esr-funkstoermessempfaenger_63493-17877.html',
                  note='Page numbers count the PDF cover as page 1; original PDFs are not redistributed')
    (ROOT/'dgm_control/data/detector-sources.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} detector source records with official URL, SHA256 and reviewed pages')


if __name__ == '__main__': main()
