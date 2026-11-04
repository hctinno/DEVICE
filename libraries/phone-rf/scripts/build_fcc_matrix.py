"""Curated report facts -> portable plans. Never infer an OEM wire encoding."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'dgm_rf/data/fcc-2026.json'
groups = []
cases = []

def group(key, device, radio, exhibit, pages, items, conditions, route, missing):
    groups.append(dict(id=key, device=device, radio=radio,
        evidence=[dict(exhibit_id=exhibit, pdf_pages=pages)] if exhibit else [],
        test_items=items.split('|'), conditions=conditions, control_route=route,
        missing=missing.split('|'), hardware_verified=False,
        start_command=None, stop_command=None, status='blocked_for_hardware'))

def case(group_id, values):
    n = sum(c['group_id'] == group_id for c in cases) + 1
    cases.append(dict(id=f'{group_id}-{n:03d}', group_id=group_id,
                      values=values, value_kind='reported_physical_condition_not_wire_arguments'))

OEM = '모델·빌드가 일치하는 제조사 시험 앱/프로토콜|설정 인코딩·시작·종료·응답|실측 ON/OFF 검증'
group('fold8-6g', 'fold8', 'wlan', '9312879', [8,15,16,17,18,22,24,52],
      '26dB 대역폭|전도출력|EIRP/PSD|대역내 방출|대역경계/불요방사|CBP|AC 전도',
      dict(phy_tested='802.11be', covered_phy=['802.11ax'], bandwidth_mhz=[20,40,80,160,320],
           mcs=0, tx_chains=2, power_classes=['SP','LPI','VLP'],
           sp_bands=['UNII-5','UNII-7'], lpi_vlp_bands=['UNII-5','UNII-6','UNII-7','UNII-8'],
           eht160_example=dict(channel=15,frequency_mhz=6025),
           measured_duty=dict(eht160_su_percent=99.25,eht320_su_percent=99.18),
           note='ax와 be의 동일성 설명으로 be 시험. 측정 듀티는 burst 명령 인수가 아닙니다.'),
      'OEM hidden menu; 기존 WIFITEST는 타 빌드 후보', OEM+'|RU/MRU·전력등급·체인·출력 단위 매핑')
for power, ru in [('SP',52),('LPI',242),('VLP',484)]:
    case('fold8-6g',dict(phy='EHT',bandwidth_mhz=160,channel=15,frequency_mhz=6025,
                        mcs=0,power_class=power,allocation='RU',ru_tones=ru,tx_chains=2))

group('duo-6g','duo','wlan','9564181',[11,12,13,14,15,22,23,27],
      '99%/26dB 대역폭|전도출력|EIRP/PSD|대역내 방출|대역경계/불요방사|TPC|AC 전도',
      dict(software='24A343',phy_tested='802.11be',covered_phy=['802.11ax'],bandwidth_mhz=[20,40,80,160],
           states={'A':'fully_closed','B':'fully_open'},conducted_mcs=0,radiated_bandedge_mcs=11,
           radiated_spurious_mcs=0,power_classes=['SP','LP','VLP'],
           eht160_selected_frequency_mhz=[6025,6345,6505,6665,6825,6985],
           exception=dict(channel=233,frequency_mhz=7115,phy='802.11a'),
           note='안테나 표의 ANT6/ANT16과 다른 표의 표기 불일치 검토 필요. TPC는 동일 모델 동반기 P2P 필요.'),
      'Apple 시험 소프트웨어 / TPC companion link',OEM+'|안테나 포트 표기 대조|TPC 동반기·가변감쇠기')
# Only explicitly documented endpoints, not a claimed exhaustive channel sweep.
for frequency in [6025,6345,6505,6665,6825,6985]:
    case('duo-6g',dict(phy='EHT',bandwidth_mhz=160,frequency_mhz=frequency,mcs=0,test_item='conducted'))

group('fold8-uwb','fold8','uwb','9268526',[7,8,9,11],
      '10dB 대역폭|평균/피크 EIRP|송신중단|불요방사|AC 전도',
      dict(channels=[5,9],antenna='Ant 1',configs=['SP0','SP1','SP3'],unsupported=['SP2'],
           tested_preamble_ids={'BPRF':9,'HPRF':25},fold_state='half_folded',axis='Z',
           packet_length_unit='not_stated_in_table'),
      'OEM hidden menu; S23 UWBDTEST 호환성 미확인',OEM+'|HPRF·packet length·SP 설정 매핑')
for ch in [5,9]:
    for sp in ['SP0','SP1','SP3']:
        for prf, preamble, length in [('BPRF',9,4),('BPRF',9,127),('HPRF',25,127)]:
            case('fold8-uwb',dict(channel=ch,config=sp,prf=prf,preamble_id=preamble,
                                 packet_length=length,antenna='Ant 1'))
group('duo-uwb','duo','uwb',None,[], 'UWB RF 세부 시험 원문 추가 확보',
      dict(note='인증 대장 주파수만으로 RF 성적서 조건 또는 명령을 생성하지 않습니다.'),
      'Apple 제조사 인터페이스 필요',OEM+'|해당 모델 UWB RF 성적서')

group('fold8-nfc','fold8','nfc','9269168',[8,9,11],
      '20dB 대역폭|기본파/불요방사|주파수 안정도|AC 전도',
      dict(frequency_mhz=13.56,type='A',rate_kbps=106,fold_state='full_folded',axis='Y',
           measured_20db_bw_khz=440,note='NFC PRBS 서비스 TECH/RATE 번호를 Type A 106으로 단정하지 않습니다.'),
      '제조사 NFC 시험 모드; 기존 NFC PRBS는 동등성 미확인',OEM+'|태그 유무 지그')
for tag in [False,True]:
    case('fold8-nfc',dict(frequency_mhz=13.56,type='A',rate_kbps=106,reading_passive_tag=tag,
                        fold_state='full_folded',axis='Y'))
group('duo-nfc','duo','nfc','9559817',[8,9,10,124,125],
      '점유대역폭|기본파/불요방사|주파수 안정도|AC 전도',
      dict(software='24A343',frequency_mhz=13.56,states={'A':'fully_closed','B':'fully_open'},
           evaluated_modes=['Reader','CE','Tag'],note='모든 Type/속도/안테나/모드의 직교 조합을 지원한다고 가정하지 않습니다.',
           document_discrepancy='exhibit title E18V2R; PDF body E18V1'),
      'Apple USB 시험 소프트웨어',OEM)
for state, typ, rate, primary_axis, secondary_axis in [('A','F',212,'Z','Z'),('B','A',106,'Y','X')]:
    for antenna, axis in [('primary',primary_axis),('secondary',secondary_axis)]:
        case('duo-nfc',dict(frequency_mhz=13.56,state=state,type=typ,rate_kbps=rate,
                           antenna=antenna,axis=axis))

group('fold8-ble','fold8','bluetooth','9299650',[8],
      '출력|PSD|6dB 대역폭|대역경계/불요방사',
      dict(phy_mbps=[1,2],packet_length_by_phy={'1':37,'2':255},
           frequency_limits_mhz={'1':[2402,2480],'2':[2404,2478]},
           additional_mode='CS_SYNC_1M',antennas=['ANT1','ANT2','dual']),
      'OEM hidden menu; BTTEST 후보',OEM+'|CS_SYNC 전용 인수')
group('fold8-cs','fold8','bluetooth','9299612',[8,10],
      'Channel Sounding ASK 출력/대역폭/불요방사',
      dict(mode='CS_TONE_ASK',frequency_limits_mhz=[2404,2478],antennas=['ANT1','ANT2']),
      'OEM BLE Channel Sounding 시험 소프트웨어',OEM+'|tone/ASK 시작·종료 프로토콜')
group('fold8-bt','fold8','bluetooth','9299613',[11],
      'BR/EDR 출력|호핑/대역폭|대역경계/불요방사',dict(mode='continuous communication with Bluetooth tester'),
      'Bluetooth tester signaling + DUT 시험 소프트웨어',OEM+'|BT tester 설정·응답')
group('duo-bt','duo','bluetooth','9588682',[8,10],
      'HDR RF 시험',dict(software='24A343',modes=['HDR4','HDR8'],frequency_limits_mhz=[2404,2476],
                       antennas=['ANT4','ANT3','ANT4+ANT3 BF'],scope='HDR report only; classic BR/EDR report not acquired'),
      'Apple 시험 소프트웨어',OEM+'|BR/EDR/BLE별 성적서·조건 추가 추출')

for key, radio, exhibit, pages, items, cond in [
    ('fold8-wlan24','wlan','9299648',[1],'2.4GHz DTS 출력·PSD·대역폭·방사',dict(scope='part1 only; b/g/n/be report')),
    ('fold8-wlan5','wlan','9299684',[1],'5GHz UNII 출력·PSD·대역폭·방사',dict(scope='report acquired; detailed conditions pending')),
    ('duo-wlan24','wlan','9588701',[1],'2.4GHz DTS RF',dict(scope='part1 only; detailed conditions pending')),
    ('duo-wlan5','wlan','9563436',[1],'5GHz UNII conducted RF',dict(scope='conducted report; radiated report separately required')),
    ('fold8-wwan','cellular','9299749',[40,41,43,45],'출력|점유대역폭|불요방사|대역경계',
     dict(mode='callbox continuous communication',antenna='factory forced',callboxes=['CMW500','E7515B'],
          note='대역별 상세 부속 파일 일부 미확보. CMW500 단독 NR 지원으로 해석하지 않습니다.')),
    ('fold8-cbrs','cellular','9268870',[13,14],'B48/n48 출력·방사',dict(bands=['B48','n48'])),
    ('fold8-mmw','cellular','9269056',[9,15],'Part30 mmWave 출력·방사',dict(mode='FTM',tx_duty_percent=100)),
    ('fold8-scs','cellular','9268953',[1],'Part25 SCS',dict(scope='report acquired; detailed controls pending')),
    ('fold8-wpt','wpt','9269173',[7,8],'무선전력전송 방사|AC 전도',
     dict(frequency_limits_khz=[110,148],mode='power sharing',fold_state='open',axis='Y',
          worst_case=2,dut_battery='fully charged',client_battery_percent=[1,20],
          document_discrepancy='exhibit E15V1; PDF body E14V1')),
    ('fold8-emc','emc','9269163',[1],'Part15B 비의도성 방사',dict(scope='TX 단일 모드 시험과 별도')),
    ('duo-dfs','wlan','9563437',[1],'DFS',dict(note='radar waveform generator + AP/client link; continuous TX alone insufficient')),
    ('duo-cbp','wlan','9564211',[1],'Contention Based Protocol',dict(note='간섭 신호·점유 감지·송신 억제 관측 필요')),
    ('duo-154','ieee802154','9588704',[8],'802.15.4 RF',
     dict(software='24A343',frequency_limits_mhz=[2405,2475],antennas=['ANT4','ANT3'],power_modes=['high','low'])),
    ('duo-154ab','ieee802154','9563438',[9],'802.15.4ab UNII-3',
     dict(frequency_limits_mhz=[5728.75,5846.25],bandwidth_mhz=2.5,antennas=['ANT6','ANT5'],power_modes=['high','low'])),
    ('duo-nb','narrowband','9563439',[9],'Narrowband UNII-1/3',
     dict(unii1_frequency_limits_mhz=[5162,5245],selected_modes=['BDR','HDT2','LE1M','LE2M','XHDRPS2'],
          antennas=['ANT6','ANT5','ANT6+ANT5 BF'],note='일반 2.4GHz Bluetooth 채널 코드와 동일시하지 않습니다.')),
    ('duo-nb6','narrowband','9564212',[9],'Narrowband UNII-5',dict(frequency_limits_mhz=[6106,6420],power_class='VLP')),
    ('duo-mss','cellular','9590464',[9],'Part25 MSS L-band',
     dict(software='24A343',frequency_limits_mhz=[1610.17,1626.03],antenna_by_state={'A':'ANT2','B':'ANT4'})),
    ('duo-b53','cellular','9590465',[12],'Part25 band53 2.4GHz',
     dict(bands=['LTE B53','NR n53'],frequency_limits_mhz=[2483.5,2495],antenna='ANT2',
          worst_waveform='DFT-s-OFDM',worst_modulation={'LTE':'QPSK','NR':'BPSK'})),
    ('duo-sar-pd','exposure','9563684',[1],'SAR|PD|동시송신 RF 노출',dict(scope='part 1/2 only',note='DASY/PD probe·phantom·공간 위치·출력 정규화 필요')),
    ('duo-tas','exposure','9563707',[19,22,23,62,63],'시간평균 출력/SAR 알고리즘 검증',
     dict(sampling_interval_ms=10,software_by_radio='24A build varies by report',
          callboxes=['CMW500 for GSM/WCDMA/LTE','UXM5G/CMX500 for NR'],
          note='USB beam/FTM toggle mentioned; command bytes not disclosed')),
]:
    group(key,'fold8' if key.startswith('fold8') else 'duo',radio,exhibit,pages,items,cond,
          '성적서별 제조사/계측기 연동',OEM+'|해당 시험법 계측기·옵션·SOP')
for n, client, ac, cross in [(1,'phone',False,False),(2,'phone',True,False),
                           (3,'phone',False,True),(4,'phone',True,True),
                           (5,'wearable',False,False),(6,'wearable',True,False)]:
    case('fold8-wpt',dict(report_test_case=n,client=client,dut_ac_charging=ac,cross_position=cross,
                         client_battery_percent=[1,20]))

group('fold8-ntn','fold8','cellular','9269019',[8,10,14,15],
      'NB-NTN 출력|점유대역폭|불요방사',
      dict(band=255,antenna='F',mode='FTM',tx_duty_percent=100,
           channel_frequency_mhz=[[261505,1626.60],[261674,1643.50],[261843,1660.40]]),
      'OEM NB-NTN FTM',OEM+'|subcarrier offset·SCS 명령 인코딩')
for channel, frequency in [(261505,1626.60),(261674,1643.50),(261843,1660.40)]:
    for scs, modulation, allocations in [
        (3.75,'BPSK',[(1,0),(1,24),(1,47)]),(3.75,'QPSK',[(1,0),(1,24),(1,47)]),
        (15,'BPSK',[(1,0),(1,6),(1,11)]),
        (15,'QPSK',[(1,0),(1,6),(1,11),(3,0),(3,6),(3,9),(6,0),(6,6),(12,0)])]:
        for count, offset in allocations:
            case('fold8-ntn',dict(band=255,channel=channel,frequency_mhz=frequency,
                                 scs_khz=scs,modulation=modulation,subcarriers=count,offset=offset))
group('duo-n77','duo','cellular','9563482',[14,16,21],
      'NR n77 출력|점유대역폭|대역경계|불요방사',
      dict(software='24A388',band='n77',example_bandwidth_mhz=10,scs_khz=None,
           antennas=['ANT2','ANT7','ANT4','ANT3'],note='10MHz 표의 SCS를 RB 수로 역추정하지 않습니다.'),
      'NR callbox + Apple antenna/FTM software',OEM+'|NR 계측기 드라이버·SCS 확인')
for channel, frequency in [(630334,3455.01),(633332,3499.98),(636332,3544.98)]:
    for modulation in ['BPSK','QPSK','16QAM','64QAM','256QAM']:
        for rb, offset in [(1,0),(1,1),(1,22),(1,23),(12,6),(24,0)]:
            case('duo-n77',dict(band='n77',bandwidth_mhz=10,nrarfcn=channel,frequency_mhz=frequency,
                              modulation=modulation,rb_count=rb,rb_offset=offset))

def main():
    manifest = json.loads((ROOT/'research/fcc-2026/manifest.json').read_text(encoding='utf-8'))
    sources = {r['id']:r for r in manifest if r['status']=='acquired'}
    for g in groups:
        for e in g['evidence']:
            r = sources[e['exhibit_id']]
            assert all(1 <= p <= r['pages'] for p in e['pdf_pages'])
            e.update(sha256=r['sha256'],pdf_url=r['pdf_url'],official_url=r['official_url'])
    payload=dict(schema_version=1,as_of='2026-11-04',scope='selected_report_conditions_not_exhaustive_certification_suite',
        devices={
            'fold8':dict(name='OEM Galaxy Z Fold8',model='SM-F971U',fcc_id='A3LSMF971U',
                        identity_url='https://www.verizon.com/about/privacy/accessibility/hearing'),
            'duo':dict(name='Apple iPhone Duo',model='A3447',fcc_id='BCG-E9188A',
                      identity_url='https://support.apple.com/en-us/106349')},
        groups=groups,cases=cases)
    DEST.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'docs/fcc-test-cases.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['case_id','device','radio','group_id','conditions_json','exhibit_id','pdf_pages','hardware_status'])
        by_id={g['id']:g for g in groups}
        for c in cases:
            g=by_id[c['group_id']];e=g['evidence'][0]
            w.writerow([c['id'],g['device'],g['radio'],g['id'],json.dumps(c['values'],ensure_ascii=False),
                        e['exhibit_id'],','.join(map(str,e['pdf_pages'])),g['status']])
    print(f'FCC matrix: {len(groups)} groups, {len(cases)} reported-condition cases; hardware ready: 0')

if __name__=='__main__': main()
