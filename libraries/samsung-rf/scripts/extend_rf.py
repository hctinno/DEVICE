"""Build-scoped RF definitions. Never derive hardware ranges from parser types."""
import hashlib
import json
import shutil


def extend(commands, sources, analysis, evidence, data):
    if analysis is not None:
        src = analysis / 'uwbuci13-jadx/sources/com/samsung/android/uwb_extension'
        for name in ['UwbFactoryCommand', 'UwbFactoryManager', 'UwbFactoryIntentManager', 'UwbFactoryConstant']:
            shutil.copy2(src / 'factory' / (name+'.java'), evidence / (name+'.java'))
        shutil.copy2(src/'rfTest/SamsungUwbTestManager.java', evidence/'SamsungUwbTestManager.java')
        shutil.copy2(src/'UciBuilder.java', evidence/'UwbUciBuilder.java')
        shutil.copy2(analysis/'AtUwbdtest-S23.java', evidence/'AtUwbdtest-S23.java')
        shutil.copy2(analysis/'EgisFingerprint-S23.java', evidence/'EgisFingerprint-S23.java')
    assert 'MAJOR_VERSION = "1"' in (evidence/'EgisFingerprint-S23.java').read_text(encoding='utf-8')
    if analysis is not None:
        nfc = analysis/'samsungnfc16-jadx/sources/com/samsung/android/nfc'
        for part in ['testapp/NfcTestManager.java', 'nci/cmd/factory/PrbsCommand.java', 'nci/SamsungNciPacket.java']:
            shutil.copy2(nfc/part, evidence/part.split('/')[-1])
    additions = [
        dict(file='UwbUci-S918NKSU1AWC8.apk', sha256='3ecf5ac64dbda502b8b7808dcead766cde1bfee3898dfb4733bc3d958bc496d0',
             build='S918NKSU1AWC8', url='https://github.com/RandomPush/samsung_dm3q_dump/blob/081499d451cb31058152c8efda2db51ffe449133/system/system/app/UwbUci/UwbUci.apk'),
        dict(file='FacAtFunction-S918NKSU1AWC8.apk', sha256='079b2c2392b69beb89c8053e0090f65ef10eb0357016a6eab84eb5f1395eaccd',
             build='S918NKSU1AWC8', url='https://github.com/RandomPush/samsung_dm3q_dump/blob/081499d451cb31058152c8efda2db51ffe449133/system/system/priv-app/FacAtFunction/FacAtFunction.apk'),
        dict(file='SamsungNfc16-20251119.apk', sha256='f764238466a817a5984f33eb204d543f3b36deca86e553078562eb44869f60c2',
             api=36, upload_date='2025-11-19', url='https://www.apkmirror.com/apk/samsung-electronics-co-ltd/nfc-3/nfc-16-release/nfc-16-5-android-apk-download/')]
    for item in additions:
        if analysis is not None:
            assert hashlib.sha256((analysis/item['file']).read_bytes()).hexdigest() == item['sha256']
    sources.extend(additions)

    def loc(file, needle):
        text = (evidence/file).read_text(encoding='utf-8')
        assert needle in text, (file, needle)
        return dict(file='evidence/'+file, line=text[:text.index(needle)].count('\n')+1)

    def spec(domain=None, kind='int', minimum=None, maximum=None):
        return dict(type=kind, domain=None if domain is None else list(map(str,domain)), minimum=minimum, maximum=maximum)

    def add(id, suffix, name, params, effect, target, branch):
        commands.append(dict(id='s23_uwb_'+id, family='UWBDTEST', radio='uwb',
            template='AT+UWBDTEST='+suffix, fixed_args=['0'], arg_count=4, parameters=params,
            name=name, evidence='same_build_parser_to_service', status='needs_profile' if any(p['domain'] is None for p in params.values()) else 'static_ready',
            effect=effect, response='status', device_verified=False,
            device_scope=dict(model='SM-S918N', build='S918NKSU1AWC8'),
            source=loc('AtUwbdtest-S23.java',branch), downstream_sources=[loc('UwbFactoryManager.java',target)],
            stop_ids=['s23_uwb_off'] if effect in ('tx','open') else [],
            notes=['Android 13 S918NKSU1AWC8 전용. 최신 기종 호환 미검증.',
                   'OFF는 어댑터 disable 경로입니다. RF 소멸 실측 필요. 출력 코드를 dBm으로 환산하지 않습니다.']))

    add('off','0,0,0,0','UWB 어댑터 비활성화 / TX 종료',{},'stop','MSG_TEST_UWB_OFF','sendUwbTestCommand(0, 0, 0, 0)')
    add('on','0,0,0,1','UWB 시험 세션 열기',{},'open','MSG_TEST_UWB_ON','sendUwbTestCommand(0, 0, 0, 1)')
    add('channel','0,0,3,{value}','UWB 채널 번호',{'value':spec([5,9])},'configure','MSG_TEST_SET_CHANNEL:','sendUwbTestCommand(0, 0, 3, argu[3])')
    add('antenna','0,0,1,{value}','TX_ANT_0 → 내부 1 / TX_ANT_1 → 내부 2',{'value':spec(['TX_ANT_0','TX_ANT_1'],'token')},'configure','MSG_TEST_SET_TX_ANTENNA:','sendUwbTestCommand(0, 0, 1, argu[3])')
    add('timing','0,0,4,{gap}_{window}_{packets}','TGap_TWin_NumOfPkts: 세 정수, 밑줄 구분',
        {k:spec(minimum=1,maximum=2147483647) for k in ['gap','window','packets']},'configure','MSG_TEST_CHANGE_GAP_AND_PACKET:','sendUwbTestCommand(0, 0, 4, argu[3])')
    add('preamble','0,0,6,{value}','Preamble code index',{'value':spec(minimum=0,maximum=127)},'configure','MSG_TEST_SET_PREAMBLE_INDEX:','sendUwbTestCommand(0, 0, 6, argu[3])')
    add('sts','0,0,8,{value}','RFRAME_CONFIG 값 (STS packet type)',{'value':spec(minimum=0,maximum=127)},'configure','MSG_TEST_SET_STS_PACKET_TYPE:','sendUwbTestCommand(0, 0, 8, argu[3])')
    add('tx','0,1,1,{value}','출력 코드 설정 후 periodic TX 시작',{'value':spec(minimum=-128,maximum=127)},'tx','MSG_TEST_SET_TX_POWER: TX powerId=','sendUwbTestCommand(0, 1, 1, argu[3])')
    add('tx_calibrated','0,1,2,0','EFS 보정 출력 읽기 후 periodic TX 시작',{},'tx','MSG_TEST_SET_TX_CALIBRATED_POWER: startTestModeSession','sendUwbTestCommand(0, 1, 2, 0)')
    for c in commands:
        if c['id'].startswith('s23_uwb_tx'):
            c['notes'] += ['setCalibration 호출 뒤 startTestModeSession(0, ABCDABCD). 별도 EFS 쓰기 명령과 구분됩니다.',
                           'periodic TX이며 무한 CW가 아닙니다. 패킷 수 설정에 따라 종료될 수 있습니다.']
            c['downstream_sources'].append(loc('SamsungUwbTestManager.java','public int startTestModeSession'))

    service = dict(schema_version=1, service='com.samsung.android.nfc', apk_sha256=additions[2]['sha256'],
        protocol='android_protected_broadcast', action='com.samsung.android.nfc.test.action.REQUEST',
        permission='com.samsung.permission.NFC_SYSTEM_PROTECTION',
        extra_prefix='com.samsung.android.nfc.test.extra.', device_verified=False,
        commands=[dict(id='nfc_prbs_start',request_id=31,effect='tx',parameters={'TECH':[0,1,2],'RATE':[0,1,2]},
                       nci_payload='21 01 (TECH+1) (RATE+1)',stop_id='nfc_prbs_stop',
                       source=loc('NfcTestManager.java','case 31:')),
                  dict(id='nfc_prbs_stop',request_id=32,effect='stop',parameters={},nci_payload='21 00',
                       source=loc('NfcTestManager.java','case 32:'))],
        numeric_mapping={'TECH':{'0':1,'1':2,'2':3},'RATE':{'0':1,'1':2,'2':3}},
        notes=['TECH와 RATE의 숫자 변환만 확인. A/B/F 및 kbps 이름의 대응은 미확인.',
               '서비스 코드에 PRBS 동작 완료 응답 방송이 없습니다. Broadcast completed를 RF 성공으로 판정하면 안 됩니다.',
               '일반 ADB shell 권한으로 보호된 수신기에 전달된다고 보장하지 않습니다.',
               '시작 시 NFC가 켜져 있으면 disable(false) 후 always-on mode 2를 사용합니다. 종료는 PRBS 정지와 mode 0입니다.'])
    (data/'nfc-prbs.json').write_text(json.dumps(service,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    numeric=[]
    for c in commands:
        if c['id'].startswith('s23_uwb_'):
            numeric.append({k:c[k] for k in ['id','template','parameters','source','downstream_sources','stop_ids','device_scope']})
    (data/'uwb-rf-arguments.json').write_text(json.dumps(numeric,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
