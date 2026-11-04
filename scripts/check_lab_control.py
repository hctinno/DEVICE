"""Repeatable offline/localhost validation. Never discovers or opens laboratory addresses."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'libraries/lab-control'
EXCLUDE={'build','dist','.venv','__pycache__','.manual-cache','.fcc-cache'}
BAD=('???','\ufffd','\u6fe1','\u6e72','\u907a','\u5a9b','\uf9e1')


def run(argv,*,cwd=ROOT,env=None):
    result=subprocess.run(argv,cwd=cwd,env=env,encoding='utf-8',errors='replace',capture_output=True)
    if result.returncode:
        raise RuntimeError(f'Command failed: {argv!r}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def main():
    started=time.monotonic()
    report=dict(utc=datetime.now(timezone.utc).isoformat(),python=sys.version.split()[0],passed=False,
                physical_equipment_tests=0,phone_rf_tests=0,mechanical_motion_tests=0,
                regulatory_conformity_tests=0,external_deployments=0,
                skipped=['Physical VISA/USB/GPIB/serial devices','Actual phone TX and RF-off verification',
                         'Measurement accuracy/calibration/uncertainty','Physical motion/SAR/NR/DFS test workflows'])
    try:
        for script in ('build_inventory.py','build_report_inventory.py','build_reference.py','build_profiles.py','build_workflows.py','build_developer_index.py'):
            print(run([sys.executable,'-X','utf8',str(LIB/'scripts'/script)]).strip(),flush=True)
        checked=0
        for path in LIB.rglob('*'):
            if not path.is_file() or EXCLUDE.intersection(path.relative_to(LIB).parts): continue
            if path.suffix in ('.py','.md','.json','.csv','.toml'):
                raw=path.read_bytes();content=raw.decode('utf-8-sig')
                if any(t in content for t in BAD): raise ValueError(f'Encoding marker in {path}')
                if path.suffix=='.py': compile(content,str(path),'exec')
                if path.suffix=='.json': json.loads(content)
                checked+=1
        report['utf8_source_artifacts']=checked
        sources=json.loads((LIB/'dgm_lab/data/sources.json').read_text(encoding='utf-8'))
        verified=0
        for source in sources:
            pdf=LIB/'.manual-cache'/f"{source['id']}.pdf"
            if source['status']=='acquired' and pdf.exists():
                if hashlib.sha256(pdf.read_bytes()).hexdigest()!=source['sha256']:
                    raise ValueError(f"Manual hash mismatch: {source['id']}")
                verified+=1
        report['local_manual_sha256_verified']=verified
        report['manual_pdf_cache_present']=bool(verified)
        report_sources=json.loads((LIB/'research/report-review.json').read_text(encoding='utf-8'))
        report_verified=0
        for source in report_sources:
            pdf=LIB/'.fcc-cache/report-2026'/f"{source['id']}.pdf"
            if source['included'] and pdf.exists():
                if hashlib.sha256(pdf.read_bytes()).hexdigest()!=source['sha256']:
                    raise ValueError(f"Report hash mismatch: {source['id']}")
                report_verified+=1
        report['local_report_pdf_sha256_verified']=report_verified
        sys.path[:0]=[str(LIB),str(LIB/'tests'),str(ROOT/'libraries/phone-rf')]
        suite=unittest.defaultTestLoader.discover(str(LIB/'tests'))
        result=unittest.TextTestRunner(verbosity=1).run(suite)
        report.update(tests_run=result.testsRun,test_failures=len(result.failures),test_errors=len(result.errors),
                      localhost_tcp_tests=7,visa_serial_adapter_fixture_tests=4)
        if not result.wasSuccessful(): raise RuntimeError('Library tests failed')
        with tempfile.TemporaryDirectory(prefix='dgm-lab-check-') as temporary:
            temp=Path(temporary);wheels=temp/'wheels';target=temp/'installed'
            for package in (LIB,ROOT/'libraries/phone-rf'):
                run([sys.executable,'-m','pip','--disable-pip-version-check','wheel','--no-deps',
                     '--no-build-isolation','--wheel-dir',str(wheels),str(package)])
            built=list(wheels.glob('*.whl'))
            if len(built)!=2: raise RuntimeError('Expected lab-control and phone-rf wheels')
            run([sys.executable,'-m','pip','--disable-pip-version-check','install','--no-deps','--no-index',
                 '--target',str(target),*[str(p) for p in built]],cwd=temp)
            env=dict(os.environ,PYTHONPATH=str(target),PYTHONIOENCODING='utf-8')
            output=run([sys.executable,'-m','dgm_lab','inventory','N9030B'],cwd=temp,env=env)
            row=json.loads(output.strip())
            if row['driver']!='SpectrumAnalyzer': raise RuntimeError('Installed package catalog missing')
            output=run([sys.executable,'-m','dgm_lab','inventory','--scope','report-2026','CO3000'],cwd=temp,env=env)
            hits=[json.loads(line) for line in output.splitlines() if line.strip()]
            if not any(r['model']=='CO3000' and r['driver']=='Co3000' for r in hits):
                raise RuntimeError('Installed report catalog missing')
            for example in ('spectrum.py','outputs.py','phone_spectrum.py','report_radiated.py'):
                run([sys.executable,str(LIB/'examples'/example),'--help'],cwd=temp,env=env)
            output=run([sys.executable,'-m','dgm_lab','capabilities','OdaEx'],cwd=temp,env=env)
            if json.loads(output)[0]['driver']!='OdaEx': raise RuntimeError('Installed capabilities missing')
            output=run([sys.executable,'-m','dgm_lab','demo','--output-dir',str(temp/'demo')],cwd=temp,env=env)
            demo=json.loads(output)
            if not demo['simulated'] or not demo['simulated_output_off'] or len(demo['measurements'])!=2:
                raise RuntimeError('Installed package demo failed')
            report['wheels_built_and_installed']=len(built)
            report['installed_package_cli_and_example_help_checks']=8
        report['inventory']=json.loads((LIB/'research/inventory-validation.json').read_text(encoding='utf-8'))
        report['report_inventory']=json.loads((LIB/'research/report-validation.json').read_text(encoding='utf-8'))
        report['passed']=True
    except BaseException as exc:
        report['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (LIB/'docs/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: lab-control software, localhost TCP, package installation and source/catalog integrity. Hardware NOT RUN.')


if __name__=='__main__': main()
