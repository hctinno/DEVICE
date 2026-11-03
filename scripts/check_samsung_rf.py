"""Rebuild and verify the Samsung RF library without opening device transports."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
LIBRARY=ROOT/'libraries/samsung-rf'
for script in ['scripts/verify_sources.py','scripts/build_catalog.py','scripts/render_rf_update.py','scripts/verify.py']:
    subprocess.run([sys.executable,script],cwd=LIBRARY,check=True)
print('PASS: Samsung RF research/software checks; hardware and RF measurements NOT RUN')
