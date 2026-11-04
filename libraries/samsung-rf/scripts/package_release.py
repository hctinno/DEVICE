from pathlib import Path
import hashlib
import json
import zipfile
import tomllib

root=Path(__file__).resolve().parents[1]
validation=json.loads((root/'docs/validation.json').read_text(encoding='utf-8'))
assert validation['status']=='PASS_SOFTWARE_ONLY'
target=root/'dist'
target.mkdir(exist_ok=True)
version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
archive=target/f'dgm-rf-command-library-{version}.zip'
excluded={'dist','build','__pycache__','.venv','.git','.manual-cache','.fcc-cache'}
bad=[chr(63)*3,chr(0xfffd),chr(0x6fe1),chr(0x6e72),chr(0x907a),chr(0x5a9b),chr(0xf9e1)]
checked=0
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if path.is_file() and not any(part in excluded or part.endswith('.egg-info') for part in relative.parts):
            if path.suffix in {'.md','.json','.csv','.toml','.py'} and path.name!='verify.py':
                text=path.read_text(encoding='utf-8-sig')
                assert not any(token in text for token in bad), str(relative)
                checked+=1
            output.write(path,Path('dgm-rf-command-library')/relative)
with zipfile.ZipFile(archive) as check:
    assert check.testzip() is None
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'utf8_checked':checked}))
