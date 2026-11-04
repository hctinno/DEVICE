"""Reproducible extraction from the APK evidence collected in this conversation."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil
import argparse
from extend_rf import extend

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--analysis', type=Path, help='Optional original APK/JADX analysis directory')
ANALYSIS = parser.parse_args().analysis
EVIDENCE = ROOT / 'evidence'
DATA = ROOT / 'dgm_rf/data'
DOCS = ROOT / 'docs'
for directory in (EVIDENCE, DATA, DOCS):
    directory.mkdir(parents=True, exist_ok=True)
if ANALYSIS is not None:
    fac = ANALYSIS / 'fac16-jadx/sources/com/sec/facatfunction/aporiented'
    for name in ['AtWifitest', 'AtFcbttest', 'AtBtletest', 'AtNfcmtest', 'AtUwbdtest', 'AtCommandHandler']:
        shutil.copy2(fac / 'athandler' / (name + '.java'), EVIDENCE / (name + '.java'))
    shutil.copy2(fac / 'AtParser.java', EVIDENCE / 'AtParser.java')
    shutil.copy2(ANALYSIS / 'fac16-jadx/sources/com/sec/factorymodule/modules/ModuleCommunication.java', EVIDENCE / 'ModuleCommunication.java')
    shutil.copy2(ANALYSIS / 'uwb16-jadx/sources/com/sec/android/app/uwbtest/UwbCsTest.java', EVIDENCE / 'UwbCsTest.java')
    for filename in ['numeric-arguments.json', 'channels-6ghz.csv', 'numeric-arguments.csv', 'NUMERIC_ARGUMENTS.md']:
        shutil.copy2(ANALYSIS / filename, DATA / filename)
    shutil.copy2(ANALYSIS/'wlan17-jadx/sources/com/sec/android/app/wlantest/WlanTest.java', EVIDENCE/'WlanTest.java')
    shutil.copy2(ANALYSIS/'wlan17-jadx/resources/res/values/arrays.xml', EVIDENCE/'WlanArrays.xml')
    numeric_doc=DATA/'NUMERIC_ARGUMENTS.md'
    content=numeric_doc.read_text(encoding='utf-8')
    for old,new in {
        'fac16-jadx/sources/com/sec/facatfunction/aporiented/AtParser.java':'../../evidence/AtParser.java',
        'fac16-jadx/sources/com/sec/facatfunction/aporiented/athandler/AtWifitest.java':'../../evidence/AtWifitest.java',
        'wlan17-jadx/sources/com/sec/android/app/wlantest/WlanTest.java':'../../evidence/WlanTest.java',
        'wlan17-jadx/resources/res/values/arrays.xml':'../../evidence/WlanArrays.xml',
    }.items():
        content=content.replace(old,new)
    numeric_doc.write_text(content,encoding='utf-8')
    # The imported prose is a derived public note; retain the original analysis separately.
    (EVIDENCE/'numeric-arguments-original.txt').write_text(content,encoding='utf-8')
    content=re.sub(r'\bSamsung\b', 'OEM', content)
    content=content.replace('삼성전자','단말 OEM').replace('삼성','단말 OEM')
    numeric_doc.write_text(content,encoding='utf-8')
else:
    from verify_sources import verify
    verify()

numeric = json.loads((DATA / 'numeric-arguments.json').read_text(encoding='utf-8'))
commands = []
by_id = {}
families = [('AtWifitest', 'WIFITEST', 'wlan', 4), ('AtFcbttest', 'FCBTTEST', 'bluetooth', 3),
            ('AtBtletest', 'BTLETEST', 'bluetooth', 4), ('AtNfcmtest', 'NFCMTEST', 'nfc', 2),
            ('AtUwbdtest', 'UWBDTEST', 'uwb', 4)]
for classname, family, radio, nargs in families:
    text = (EVIDENCE / (classname + '.java')).read_text(encoding='utf-8')
    matches = list(re.finditer(r'checkArgu\(strArr, new String\[\]\{([^}]+)\}\)', text))
    seen = set()
    for index, match in enumerate(matches):
        args = re.findall(r'"([^"]+)"', match[1])
        key = family.lower() + '_' + '_'.join(args)
        if key in seen:
            continue
        seen.add(key)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end]
        targets = re.findall(r'\.instance\(this\.context\)\.([A-Za-z0-9_]+)\(', body)
        target = targets[0] if targets else ''
        action = re.search(r'requestActionToBTService\((\d+)', body)
        labels = re.findall(r'log_[di]\([^\n]+?CLASS_NAME, "([^"]+)"', body)
        if not target and labels:
            target = next((x for x in labels if x not in ['handleCommand']), '')
        row = dict(id=key, family=family, radio=radio, template='AT+' + family + '=' + ','.join(args + ['{value}'] * (nargs - len(args))),
                   fixed_args=args, arg_count=nargs, parameters={'value': {'type': 'token', 'domain': None}} if len(args) < nargs else {},
                   name=target or '기능 의미 미확인: ' + ','.join(args), evidence='parser_branch',
                   status='reference_only', effect='unknown', response='status',
                   source={'file': 'evidence/' + classname + '.java', 'line': text.count('\n', 0, match.start()) + 1},
                   downstream_action=int(action[1]) if action else None, stop_ids=[], device_verified=False,
                   notes=['동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요'])
        commands.append(row)
        by_id[key] = row

def configure(key, name, *, enum=None, kind='int', status='static_ready', effect='configure', response='status', stops=(), notes=()):
    row = by_id[key]
    row.update(name=name, status=status, effect=effect, response=response, stop_ids=list(stops), notes=list(notes))
    if row['parameters']:
        row['parameters']['value'] = {'type': kind, 'domain': enum}
    return row

wlan = {
    '0_1_1': ('DUT 열기 / 시험 FW', ['0'], 'open'), '0_1_0': ('DUT 닫기', ['0'], 'stop'),
    '0_0_6': ('Band 선택', ['1','2','3'], 'configure'), '0_0_7': ('대역폭/PHY', [str(x) for x in range(1,26)], 'configure'),
    '0_0_1': ('Data rate / MCS 코드', [str(x) for x in range(1,31)], 'configure'),
    '0_0_2': ('Preamble / GI', [str(x) for x in range(1,8)], 'configure'),
    '0_7_0': ('안테나', ['0','1','2'], 'configure'), '0_1_5': ('Channel Encoding', ['0','1'], 'configure'),
    '0_0_0': ('채널 전달값', None, 'configure'), '0_0_3': ('출력 설정값', None, 'configure'),
    '0_0_4': ('Payload length', None, 'configure'), '0_0_5': ('Burst interval', None, 'configure'),
    '0_2_1': ('TX 시작: 1 변조 / 2 무변조', ['1','2'], 'tx'),
    '0_2_0': ('TX 정지', ['0'], 'stop'), '0_3_0': ('RX 정지', ['0'], 'stop'),
    '0_3_1': ('RX 시작', None, 'rx'),
}
for suffix, (name, enum, effect) in wlan.items():
    configure('wifitest_' + suffix, name, enum=enum, kind='number' if suffix=='0_0_3' else 'int',
              status='needs_profile' if enum is None else 'static_ready', effect=effect,
              stops=['wifitest_0_2_0', 'wifitest_0_1_0'] if effect=='tx' else ['wifitest_0_3_0','wifitest_0_1_0'] if effect=='rx' else [])
for row in numeric['prefixes']:
    key = 'wifitest_' + row['at_prefix'].split('=')[1].replace(',', '_')
    if key in by_id:
        by_id[key]['dut_id'] = row['dut_id']
        by_id[key]['dut_name'] = row['dut_name']
        by_id[key]['evidence'] = row['evidence']
for suffix, name in [('0_4_0','RX 오류 프레임'),('0_4_1','RX 정상 프레임'),('0_4_2','RSSI'),('0_4_5','11ax TX 오류'),('1_0_0','모듈 벤더')]:
    configure('wifitest_'+suffix, name, status='needs_profile', response='data', effect='read')

# Fixed Bluetooth presets have complete parser syntax; exact RF settings still require a device profile.
for row in commands:
    if row['family']=='FCBTTEST' and not row['parameters'] and row['name'].startswith(('bt','ble')):
        row.update(status='static_ready', effect='configure', notes=['Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.'])
        if 'Tx' in row['name'] or 'Rx' in row['name']:
            row['effect'] = 'tx' if 'Tx' in row['name'] else 'rx'
            row['stop_ids'] = ['fcbttest_0_6_9'] if 'Le' in row['name'] else ['fcbttest_0_8_3']
        if row['name'].endswith('Read'):
            row.update(effect='read', response='data', stop_ids=[])
        elif row['name'].endswith('Stop'):
            row.update(effect='stop', stop_ids=[])
for suffix, name, effect in [('0_0_0','Bluetooth 활성화','open'),('0_2_0','Bluetooth 비활성화','stop'),('0_2_1','BT RF 시험 종료','stop'),('0_6_9','BLE 시험 종료','stop'),('0_8_3','BR/EDR 시험 종료','stop'),('3_1_3','BR/EDR 시험 종료','stop'),('3_4_0','BLE PHY 1M','configure'),('3_4_1','BLE PHY 2M','configure')]:
    configure('fcbttest_'+suffix,name,effect=effect)
configure('fcbttest_0_3_0','BT RF 시험 앱 시작: 연속 TX 명령으로 간주하지 않음',status='reference_only',effect='menu')
for row in commands:
    if row['family']=='BTLETEST':
        row.update(status='needs_profile', effect='configure', notes=['정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.'])
        if row['parameters']:
            row['parameters']['value']['type']='int'
        if row['id']=='btletest_1_0_0':
            row.update(response='data',effect='read')
ble_names = ['TX output channel','TX modulation 0F channel','TX modulation AA channel','TX carrier channel',
             'TX in-band channel','RX channel','RX PHY code','RX modulation-index code',
             'TX modulation PHY code','TX modulation channel','BLE channel start','BLE stop action 84',
             'BLE stop action 85','BLE TX power code','BLE TX payload length']
for index,name in enumerate(ble_names):
    key='btletest_0_0_'+str(index)+('_0' if index in (11,12) else '')
    by_id[key]['name']=name
    by_id[key]['downstream_action']=60+index if index<10 else {10:83,11:84,12:85,13:86,14:87}[index]
    if index==10:
        by_id[key]['effect']='unknown_start'
        by_id[key]['notes'].append('TX/RX 구분과 종료 경로를 하위 서비스에서 검증해야 합니다.')
for suffix in ['0_0_11_0','0_0_12_0']:
    configure('btletest_'+suffix,'BLE stop 경로 ('+suffix+')',effect='stop',notes=['두 stop 경로의 차이는 미확인.'])

configure('nfcmtest_0_0','NFC 종료/비활성화 경로',effect='stop',notes=['Factory binary와 일반 binary의 경로가 다릅니다. RF field-off 실측 필요.'])
configure('nfcmtest_0_3','NFC 활성화 경로',effect='open')
for suffix,name in [('1_1','NFC Tag ID 읽기'),('1_2','NFC 검출 로그 읽기'),('1_6','Secure Element 식별'),('1_7','NFC 부트로더 버전'),('1_8','NFC 칩 이름')]:
    configure('nfcmtest_'+suffix,name,effect='read',response='data')
for row in commands:
    if row['family']=='NFCMTEST' and (row['fixed_args'][0] in ['2','3','4','5','6','9'] or row['fixed_args']==['0','9']):
        row.update(effect='persistent_write',status='blocked',notes=['저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.'])

uwb = dict(by_id['uwbdtest_0_0_9'])
uwb.update(id='uwb_loopback', template='AT+UWBDTEST=0,0,9,5', fixed_args=['0','0','9','5'], parameters={},
           name='UWB RF loopback 자체 시험', evidence='parser_and_ui_constant', status='static_ready', effect='self_test',
           source={'file':'evidence/UwbCsTest.java','line':19}, notes=['연속 TX 또는 FCC 측정 모드가 아닙니다.'])
commands.append(uwb)

# Policy registration proves names only, never arguments or RF behavior.
policy = (EVIDENCE / 'UserOpenCommand.java').read_text(encoding='utf-8')
cell_names = {'MITSRFTS','RFEVTAIT','PRXDRXCK','SVCBANDB','RFBKOFFC','SECNRSSI','RFNVCHKS','RFBYCODE','RFMIPITT','RFSARONOFF'}
for family in sorted(cell_names):
    hits=list(re.finditer(r'putAtCommands\("(AT\+'+family+r'=[^"]+)"',policy))
    if not hits:
        continue
    commands.append(dict(id='cellular_'+family.lower(), family=family, radio='cellular', template=None,
                         registered_patterns=list(dict.fromkeys(x[1] for x in hits)), parameters={}, fixed_args=[],arg_count=None,
                         name=family+' 정책 등록만 확인',evidence='policy_name_only',status='blocked',effect='unknown',response='unknown',
                         source={'file':'evidence/UserOpenCommand.java','line':policy.count('\n',0,hits[0].start())+1},
                         stop_ids=[],device_verified=False,notes=['LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.']))

sources=numeric['sources']+[dict(file='UwbTest-API36-20250920.apk',sha256='300ce18a1300b1b4d4f2a6e8554225c9bac1751f0732269a92ef257c1f59fff4',upload_date='2025-09-20',api=36,url='https://www.apkmirror.com/apk/samsung-electronics-co-ltd/uwbtest/uwbtest-1-0-0-release/uwbtest-1-0-0-8-android-apk-download/')]
for source in sources:
    if ANALYSIS is not None:
        assert hashlib.sha256((ANALYSIS/source['file']).read_bytes()).hexdigest()==source['sha256']
sources.append(dict(file='UserOpenCommand.java',url='https://github.com/488315/android_samsung_frameworks_base/blob/d7c13fe69a1ad46f8dff0254f1abd32596fef5cd/src/com/samsung/android/service/ProtectedATCommand/list/UserOpenCommand.java',build='S936USQU5ZYHB',kind='policy_registration'))
extend(commands, sources, ANALYSIS, EVIDENCE, DATA)
assert len({c['id'] for c in commands})==len(commands)
catalog=dict(schema_version=1,product='DGM RF Command Library',checked_date='2026-11-04',complete_for_all_devices=False,device_verified=False,sources=sources,commands=commands)
(DATA/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (DOCS/'commands.csv').open('w',encoding='utf-8-sig',newline='') as fp:
    keys=['id','radio','family','name','template','status','effect','response','parameters','source','notes']
    out=csv.DictWriter(fp,fieldnames=keys);out.writeheader()
    for c in commands:
        out.writerow({k:json.dumps(c[k],ensure_ascii=False) if isinstance(c[k],(dict,list)) else c[k] for k in keys})
for radio in ['wlan','bluetooth','cellular','nfc','uwb']:
    subset=[c for c in commands if c['radio']==radio]
    lines=['# '+radio+' 명령 카탈로그','', '정적 분석 결과입니다. static_ready는 문법 생성 가능, needs_profile은 인수 범위 지정 필요, reference_only/blocked는 실행 불가입니다. 실기기 검증 명령은 0개입니다.','',
           '| ID | 기능 | 명령 | 상태 | 근거 |','| --- | --- | --- | --- | --- |']
    for c in subset:
        src=c['source']
        link='../'+src['file']
        lines.append('| '+ ' | '.join([c['id'], c['name'], '`'+(c['template'] or '인수 미확인')+'`',c['status'],f"[{Path(src['file']).name}:{src['line']}]({link})"])+' |')
    lines+=['','## 인수·전제조건·종료','']
    for c in subset:
        lines += ['### '+c['id'],'',json.dumps(c['parameters'],ensure_ascii=False),'','종료 후보: '+(', '.join(c['stop_ids']) or '미확인 또는 해당 없음'),'',' / '.join(c['notes']),'']
    (DOCS/(radio+'.md')).write_text('\n'.join(lines),encoding='utf-8')
summary={r:sum(c['radio']==r for c in commands) for r in ['wlan','bluetooth','cellular','nfc','uwb']}
(DOCS/'catalog-validation.json').write_text(json.dumps(dict(total=len(commands),by_radio=summary,device_verified=0,
    apk_hashes='PASS' if ANALYSIS is not None else 'NOT_CHECKED_SNAPSHOT_MODE',
    snapshot_hashes='PASS' if ANALYSIS is None else 'NOT_CHECKED_APK_MODE'),indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary))
