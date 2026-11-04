"""Rebuild and verify the OEM RF library without opening device transports."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
LIBRARY=ROOT/'libraries/phone-rf'
for script in ['scripts/verify_sources.py','scripts/build_catalog.py','scripts/render_rf_update.py',
               'scripts/build_fcc_matrix.py','scripts/check_fcc_evidence.py',
               'scripts/render_fcc_report.py','scripts/build_chipset_catalog.py','scripts/verify.py']:
    subprocess.run([sys.executable,script],cwd=LIBRARY,check=True)
print('PASS: OEM RF research/software checks; hardware and RF measurements NOT RUN')
