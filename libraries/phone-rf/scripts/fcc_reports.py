"""Acquire public FCC PDFs, hash bytes, and extract page-addressable local evidence."""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone
import requests
import fitz

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "fcc-2026"
CACHE = ROOT / ".fcc-cache"

def acquire(row):
    row = dict(row)
    target = CACHE / (row["id"] + ".pdf")
    try:
        if not target.exists():
            response = requests.get(row["pdf_url"], timeout=(10, 45))
            response.raise_for_status()
            if not response.content.startswith(b"%PDF-"):
                raise ValueError("Response is not a PDF")
            target.write_bytes(response.content)
        raw = target.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if row.get("sha256") and row["sha256"] != digest:
            raise ValueError("Pinned PDF SHA-256 mismatch")
        with fitz.open(target) as doc:
            pages = [p.get_text(sort=True) for p in doc]
        normalized = re.sub(r"[^A-Z0-9]", "", "".join(pages[:8]).upper())
        expected = re.sub(r"[^A-Z0-9]", "", row["fcc_id"])
        identity_check = 'fcc_id_in_first_8_pages'
        if expected not in normalized:
            parent_id = row.get('identity_parent')
            report = row.get('report_number')
            if not parent_id or not report or not row.get('identity_parent_sha256'):
                raise ValueError("FCC ID absent from first 8 pages; review identity manually")
            parent = CACHE / (parent_id + '.pdf')
            if hashlib.sha256(parent.read_bytes()).hexdigest() != row['identity_parent_sha256']:
                raise ValueError('Identity parent hash mismatch')
            with fitz.open(parent) as doc:
                parent_text = ''.join(p.get_text() for p in list(doc)[:8])
            if expected not in re.sub(r'[^A-Z0-9]', '', parent_text.upper()) or report not in parent_text:
                raise ValueError('Identity parent does not establish FCC ID/report number')
            if not all(report in p for p in pages):
                raise ValueError('Report number missing from continuation page')
            identity_check = 'report_number_every_page_and_hash_pinned_identity_parent'
        (CACHE / (row["id"] + ".pages.json")).write_text(
            json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (CACHE / (row["id"] + ".txt")).write_text(
            "\n".join(f"=== PDF PAGE {i} ===\n{p}" for i, p in enumerate(pages, 1)),
            encoding="utf-8")
        row.update(status="acquired", sha256=digest, bytes=len(raw), pages=len(pages),
                   identity_check=identity_check, retrieved_date=datetime.now(timezone.utc).date().isoformat(),
                   host_kind="third_party_mirror_of_fcc_submission",
                   official_url=f"https://apps.fcc.gov/eas/GetApplicationAttachment.html?id={row['id']}")
    except Exception as error:
        row.update(status="failed", error=str(error))
    return row

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--ids", nargs="*")
    args = parser.parse_args()
    rows = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    if args.ids:
        unknown = set(args.ids) - {r['id'] for r in rows}
        if unknown:
            raise SystemExit(f"Unknown exhibit IDs: {sorted(unknown)}")
        rows = [r for r in rows if r["id"] in args.ids]
    CACHE.mkdir(exist_ok=True)
    if not args.download:
        raise SystemExit("Pass --download to acquire public files; no device I/O is performed.")
    old = {}
    manifest = DATA / "manifest.json"
    if manifest.exists():
        old = {r["id"]: r for r in json.loads(manifest.read_text(encoding="utf-8"))}
    for r in rows:
        if old.get(r["id"], {}).get("sha256"):
            r["sha256"] = old[r["id"]]["sha256"]
    # Acquire identity-bearing reports before their dependent continuation files.
    for dependent in (False, True):
        batch = [r for r in rows if bool(r.get('identity_parent')) == dependent]
        for r in batch:
            if dependent:
                parent = old.get(r['identity_parent'], {})
                if parent.get('status') == 'acquired':
                    r['identity_parent_sha256'] = parent['sha256']
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for row in pool.map(acquire, batch):
                old[row["id"]] = row
                print(row["id"], row["status"], row.get("pages", row.get("error")), flush=True)
    result = sorted(old.values(), key=lambda r: (r["fcc_id"], r["id"]))
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Acquired", sum(r["status"] == "acquired" for r in result), "/", len(result))
    if any(old[r['id']]['status'] != 'acquired' for r in rows):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
