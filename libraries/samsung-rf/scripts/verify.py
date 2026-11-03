"""Focused acceptance harness, including generated artifact encoding."""
from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
checks=[]
for command in [
    [sys.executable,'-m','dgm_rf','demo','--log','docs/demo-log.json'],
    [sys.executable,'-m','examples.bluetooth'],
    [sys.executable,'-m','examples.uwb_nfc'],
    [sys.executable,'-m','examples.fcc_plan'],
    [sys.executable,'-m','dgm_rf','render','wifitest_0_0_7','--value','9']
]:
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    checks.append({'command':command[1:],'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
bad=['???','\ufffd','\u6fe1','\u6e72','\u907a','\u5a9b','\uf9e1']
encoding_errors=[]
checked=0
for path in ROOT.rglob('*'):
    if path.suffix not in {'.md','.json','.csv','.py','.toml'} or any(x in path.parts for x in ['build','dist','.venv','__pycache__','.fcc-cache']):
        continue
    text=path.read_text(encoding='utf-8-sig')
    checked+=1
    # The detector necessarily contains the patterns it detects.
    if path.name not in {'verify.py','render_numeric.py'} and any(x in text for x in bad):
        encoding_errors.append(str(path.relative_to(ROOT)))
catalog=json.loads((ROOT/'dgm_rf/data/catalog.json').read_text(encoding='utf-8'))
states={}
for command in catalog['commands']:
    states[command['status']]=states.get(command['status'],0)+1
report={'unit_tests_run':result.testsRun,'unit_failures':len(result.failures),'unit_errors':len(result.errors),
        'cli_checks':checks,'utf8_files_checked':checked,'encoding_errors':encoding_errors,
        'catalog_count':len(catalog['commands']),'catalog_states':states,'physical_phone_test':'NOT_RUN',
        'serial_hardware_test':'NOT_RUN','instrument_measurement':'NOT_RUN','fcc_compliance_validation':'NOT_IMPLEMENTED'}
report['status']='PASS_SOFTWARE_ONLY' if result.wasSuccessful() and not encoding_errors and all(x['returncode']==0 for x in checks) else 'FAIL'
(ROOT/'docs/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
sys.exit(0 if report['status']=='PASS_SOFTWARE_ONLY' else 1)
