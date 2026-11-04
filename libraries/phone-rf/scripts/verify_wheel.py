"""Import the built wheel in isolation, not the adjacent source package."""
from pathlib import Path
import json
import sys
import zipfile
import tomllib

root=Path(__file__).resolve().parents[1]
version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
wheel=root/f'dist/dgm_rf_command_library-{version}-py3-none-any.whl'
sys.path=[str(wheel)]+[p for p in sys.path if p and Path(p).resolve()!=root]
import dgm_rf
from dgm_rf import Catalog
assert '.whl' in dgm_rf.__file__
catalog=Catalog()
assert len(catalog.entries)==220
from dgm_rf import NfcRequest
assert NfcRequest(31,2,1).nci_payload==bytes([33,1,3,2])
assert catalog.build('s23_uwb_off').wire=='AT+UWBDTEST=0,0,0,0'
assert catalog.build('wifitest_0_0_7',value=9).wire=='AT+WIFITEST=0,0,7,9'
from dgm_rf.chipset import qualcomm_he_fields, wl_tx_packets, catalog as chipset_catalog
assert qualcomm_he_fields(160, 'TCMD_GI_LTF_MODE4_GI_3200', 1)['fields']['rateBw']==16
assert wl_tx_packets('00:11:22:33:44:55',gap_us=40,frame_bytes=1000,frame_count=0).cleanup[0][-1]=='tx'
assert len(chipset_catalog()['commands'])==29
with zipfile.ZipFile(wheel) as archive:
    assert archive.testzip() is None
    assert 'dgm_rf/data/channels-6ghz.csv' in archive.namelist()
    assert 'dgm_rf/data/nfc-prbs.json' in archive.namelist()
    assert 'dgm_rf/data/uwb-rf-arguments.json' in archive.namelist()
    assert 'dgm_rf/data/chipset-commands.json' in archive.namelist()
    assert not any('.manual-cache' in name or '.fcc-cache' in name for name in archive.namelist())
report={'status':'PASS','wheel':wheel.name,'imported_from_wheel':True,'catalog_entries':len(catalog.entries),'package_data_present':True,
        'chipset_records':len(chipset_catalog()['commands']),'chipset_sources':len(chipset_catalog()['sources']),
        'vendor_cache_excluded':True,'phone_tests':0}
(root/'docs/wheel-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
