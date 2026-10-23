"""Reversible source-label grouping and provisional equipment classification.

No manufacturer website, programming manual, or physical unit was consulted.
These rules never establish support for a protocol or enable device commands.
"""
import html
import re
import unicodedata

MISSING = {'', '-', '--', '---', 'n/a', 'na', 'n.a', 'n.a.', 'none', 'null', '없음', '미상'}


def clean(value):
    if value is None:
        return None
    text = str(value)
    for _ in range(5):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    text = unicodedata.normalize('NFKC', text).strip()
    return re.sub(r'\s+', ' ', text)


def optional(value):
    value = clean(value)
    return None if value is None or value.casefold() in MISSING else value


def brand_key(value):
    value = clean(value) or ''
    value = value.replace('(주)', '').replace('주식회사', '')
    # Preserve &, +, / and other meaningful characters; no fuzzy auto-merge.
    return re.sub(r'[\s.,\-]', '', value).casefold()


# Explicit, inspectable spelling/abbreviation groups. Legacy brands are kept
# separate: HP, Agilent and Keysight; EMCO and ETS-Lindgren; TDK and TDK-Lambda.
BRAND_GROUPS = {
    'Rohde & Schwarz': ['ROHDE&SCHWARZ','ROHDE SCHWARZ','R&S','R/S','ROHDE AND SCHWARZ'],
    'Keysight': ['KEYSIGHT','Keysight Technologies','KEYSIGHT Tech.'],
    'Agilent': ['AGILENT','Agilent Technologies'],
    'HP': ['HP','H.P','Hewlett Packard','HP HEWLETT PACKARD'],
    'Tektronix': ['TEKTRONIX'],
    'SCHWARZBECK': ['Schwarzbeck','Schwarzbeck Mess-Elektronik OHG','SCHWARZBECK MESS-ELEKTRONIK'],
    'Wainwright Instruments': ['Wainwright','Wainwright Instrument','Wainwright Instruments','Wainwright Instruments GmbH'],
    'INNCO Systems': ['Innco system','Innco systems','Innco systems GmbH'],
    'EM TEST': ['EMTEST','EM TEST'],
    'EMC PARTNER': ['EMC Partner','EMCPARTNER'],
    'AR / Amplifier Research': ['AR','A/R','AMPLIFIER RESEARCH','AMPLIFIERRESEARCH'],
    'Anritsu': ['ANRITSU','ANRITSU CORP','ANRITSU CORPORATION'],
    'SPEAG': ['Speag','SCHMID & PARTNER'],
    'National Instruments': ['NI','National Instruments'],
    'BIRD': ['Bird','BIRD ELEC','BIRD ELEC.'],
    'Solar Electronics': ['Solar','SOLAR Electronics'],
    'HUBER+SUHNER': ['HUBER+SUHNER','H+S'],
    'Mini-Circuits': ['MINI-CIRCUITS','minicircuits'],
    'A.H. Systems': ['A.H.Systems','A.H. SYSTEMS'],
    'ETS-Lindgren': ['ETS-LINDGREN','ETS LINDGREN'],
    'Fairview Microwave': ['Fairview Microwave','FairviewMicrowave','FAIRVIEW MICROWAVE INC.'],
    'OML': ['OML INC.','OML INC'],
    'CERNEX': ['CERNEX','Cernex Inc.','CERNEX, Inc'],
    'Pearson Electronics': ['Pearson','PEARSON ELECTRONICS'],
    'COM-POWER': ['COM-POWER','Com Power','COM-POWER CORPORATION'],
    'AE Techron': ['AE TECHRON','AETECHRON'],
    'KEITHLEY': ['KEITHLEY','KEITHLEY Instruments'],
    'LUMILOOP': ['LUMI LOOP','LUMILOOP'],
    'RF-LAMBDA': ['RF-LAMBDA','RF- Lambda'],
    'LOTUS Communication Systems': ['LOTUS COMMUNICATION SYSTEMS, INC.','LOTUS COMMUNICATION SYSTEMS, INC..'],
    'SONOMA Instrument': ['SONOMA INSTRUMENT','SONOMA'],
    'SCM Technology': ['SCM TECHNOLOGY','SCM TECH'],
    'DIGITEK POWER': ['DIGITEK POWER','DIGITEK POWER Co., Ltd.','디지텍파워'],
    'Elex Polytech': ['ELEX POLYTECH','엘렉스폴리텍'],
    'ENEX SCIENCE': ['ENEX SCIENCE','에넥스과학'],
    'ODA': ['ODA','ODA TECHNOLOGY'],
    'Newtons4th': ['Newtons4th','Newtons4th Ltd','N4L'],
    'Xantrex': ['XANTREX','Xantrex Technology'],
    'B&K Precision': ['BKPRECISION','BK Precision'],
    'ZES ZIMMER': ['ZESZIMMER','ZES ZIMMER'],
    'GRAS': ['G.R.A.S'],
    'ED&D': ['ED & D','ED&D'],
    'Total Phase': ['Total Phase, Inc.','TOTAL PHASE, Inc'],
    'L.A.B. Equipment': ['L.A.B','L.A.B. Equipment, Inc.'],
    'UCS': ['UCS','UCS Co., Ltd'],
    'Guangzhou Zhilitong Electromechanical': ['Guangzhou Zhilitong Electromechanical Co., Ltd','Guangzhou Zhilitong Electromechanical CO.,Ltd'],
    'TDK RF Solutions': ['TDK RF SOLUTIONS','TDK RF Solutions lnc.'],
    'Ergonomics': ['Ergonomics','Ergonomics, Inc'],
    'DWYER': ['Dwyer','DWYER INSTRUMENT'],
    'SPIRENT': ['SPIRENT','SPIRENTCOMMUNICATION'],
    'Wandel & Goltermann': ['Wandel & Goltermann','W&G'],
}

# Suspected errors are NOT merged. Store a suggestion and a review task instead.
TYPO_SUGGESTIONS = {
    'RODHE&SCHWARZ':'Rohde & Schwarz', 'RODHE & SCHWARZ':'Rohde & Schwarz',
    'RODEH&SCHWARZ':'Rohde & Schwarz','Rhode&Schwarz':'Rohde & Schwarz',
    'ROHDE':'Rohde & Schwarz','Rodhe & Schwarz':'Rohde & Schwarz',
    'Keysght':'Keysight','KETSIGHT':'Keysight',
    'TECKTRONIX':'Tektronix','Tektronics':'Tektronix','TEKPRONIX':'Tektronix',
    'Schwarzneck':'SCHWARZBECK','WEINWRIGHT INSTRUMENTS GMBH':'Wainwright Instruments',
    'INCCO SYSTEMS GmbH':'INNCO Systems','Hwelett Packard':'HP',
    'Amplifer Research':'AR / Amplifier Research','KIKUSI':'KIKUSUI',
    'HUBER+SUNNER':'HUBER+SUHNER','Heafely':'HAEFELY',
    'WEISSTECKNIK':'Weiss Technik','GRAPHTECH':'GRAPHTEC',
    'Anritsu Cooperation':'Anritsu','KOREA SIMULARTOR':'KOREA SIMULATOR',
    'SY Coporation':'SY Corporation','SY corportation':'SY Corporation',
    'TESEO':'TESEQ','EGALE':'EAGLE',
    'CERNEX&apos;- Inc. USA':'CERNEX','CERNEX&apos;- Inc':'CERNEX','CERNEX&apos;- Inc.미국':'CERNEX',
}
INVALID_MANUFACTURERS = {
    'any vendor':'제조사 미지정', 'germany':'국가명이 제조사로 기재됨',
    '한국':'국가명이 제조사로 기재됨', '주문제작':'제조 주체가 특정되지 않음',
    '자체제작':'제조 주체가 특정되지 않음', '조립pc':'제조 주체가 특정되지 않음',
    'thermo hygrometer':'장비명이 제조사로 기재된 것으로 보임',
}
COMPOSITE_MANUFACTURERS = {
    'Indoor RU: Wave Electronics , USLP: SUPER MICRO COMPUTER.INC',
    'Aegis, Cybellum', 'Agilent/HP',
}

BRAND_LOOKUP = {}
for canonical, aliases in BRAND_GROUPS.items():
    for alias in [canonical, *aliases]:
        key = brand_key(alias)
        assert key not in BRAND_LOOKUP or BRAND_LOOKUP[key] == canonical
        BRAND_LOOKUP[key] = canonical
TYPO_LOOKUP = {brand_key(k): v for k,v in TYPO_SUGGESTIONS.items()}


def manufacturer_info(raw):
    value = optional(raw)
    if value is None:
        return None, 'missing', True, None, '원본 제조사가 공란 또는 결측 표기'
    if value.casefold() in INVALID_MANUFACTURERS:
        return None, 'non_manufacturer', True, None, INVALID_MANUFACTURERS[value.casefold()]
    if value in COMPOSITE_MANUFACTURERS:
        return None, 'multiple_manufacturers', True, None, '복수 제조사 원문 유지; 구성품별 확인 필요'
    key = brand_key(value)
    if key in TYPO_LOOKUP:
        return value, 'suspected_typo_unmerged', True, TYPO_LOOKUP[key], '유사 표기 후보만 제안; 제조사 병합하지 않음'
    if key in BRAND_LOOKUP:
        return BRAND_LOOKUP[key], 'explicit_alias', False, None, 'rules.py의 명시적 표기/약칭 매핑; 외부 확인 전'
    return value, 'format_only', False, None, '대소문자·공백·일부 구두점·법인 표기만 통일; 외부 확인 전'


# First matching expression wins. Classification uses equipment NAME only.
# Hints are research routes, never a claim that remote control is supported.
# (id, domain, Korean label, research route, regex)
CATEGORIES = [
 ('motion_controller','위치·로봇','로봇·마스트·턴테이블 제어기','전용 컨트롤러·SDK 조사',r'(?:mast|table|robot|ant\.? mast).*control|teach pendant|joystick'),
 ('motion','위치·로봇','로봇·마스트·턴테이블','전용 컨트롤러·SDK 조사',r'robot|antenna mast|antenna master|turn\s*table|positioner|로봇|턴테이블|마스트'),
 ('switch_system','신호 경로','스위칭·경로 제어 장치','스위치 제어 API·명령 조사',r'switch|\bosp\b|rf switch|스위칭|스위치'),
 ('software_computer','전산·소프트웨어','컴퓨터·소프트웨어·라이선스','소프트웨어 API·라이선스 조사',r'\bpc\b|computer|software|license|licence|dongle|데스크탑|컴퓨터|소프트웨어|노트북|laptop|workstation|server|burp suite|fuzz|cybellum|펌웨어 분석'),
 ('interface','통신 인터페이스','버스·광통신·제어 인터페이스','인터페이스·SDK 조사',r'gpib|interface|pcan|canoe|coupler for|lin convert|usb isolator|ethernet|hub\b|\brouter\b|gateway|버스|광컨버터'),
 ('rf_analyzer','RF·무선 측정','스펙트럼·신호·EMI 분석기','프로그래밍 매뉴얼·드라이버 조사',r'spectrum analy|signal analy|emi.*receiv|test receiver|emi analyzer|스펙트럼|스펙트럼분석기'),
 ('network_analyzer','RF·무선 측정','네트워크·임피던스 분석기','프로그래밍 매뉴얼·드라이버 조사',r'network analy|reflectometer|impedance analy|네트워크.*분석'),
 ('communication_tester','RF·무선 측정','무선통신·프로토콜 시험기','프로그래밍 매뉴얼·SDK 조사',r'communication.*(?:analy|test|set)|wireless.*(?:test|set|platform)|bluetooth|protocol analy|sniffer|dab/dmb|통신.*시험|무선.*시험'),
 ('signal_generator','신호 발생','신호·파형·GNSS 발생기','프로그래밍 매뉴얼·드라이버 조사',r'signal generat|function generat|arbitrary.*generat|gnss|gps.*simulat|multi carrier generat|mpeg generator|pattern generat|파형발생|신호발생'),
 ('power_supply','전력·전기','전원공급기·전력 시뮬레이터','전원 제어·한계값·인터록 조사',r'power suppl|power source|power system|grid simulat|\bcvcf\b|전원공급|직류전원|교류전원|battery simulat|bipolar power'),
 ('electronic_load','전력·전기','전자부하·배터리 사이클러','부하·충방전 제어·인터록 조사',r'electronic load|battery cycl|pack cycl|charge/disch|충방전|전자부하|e-load'),
 ('power_sensor','RF·무선 측정','전력 센서','연결 계측기·센서 인터페이스 조사',r'power sensor|전력센서|파워센서'),
 ('power_meter','전력·전기','전력계·전력 분석기','프로그래밍 매뉴얼·드라이버 조사',r'power meter|power analy|wattmeter|watt meter|power indicator|전력계|전력분석'),
 ('oscilloscope','전력·전기','오실로스코프','프로그래밍 매뉴얼·드라이버 조사',r'oscilloscope|오실로스코프'),
 ('electrical_meter','전력·전기','멀티미터·저항·LCR 계측기','프로그래밍 매뉴얼·드라이버 조사',r'multimeter|resistance.*(?:meter|tester)|ohm.*meter|lcr.*(?:meter|tester)|clamp meter|ammeter|volt.?meter|mΩ.*hitester|저항.*측정|멀티미터|전압계|전류계'),
 ('daq','데이터 수집','데이터 로거·수집 장치','프로그래밍 매뉴얼·데이터 형식 조사',r'logger|hilogger|recorder|data acquis|mobile corder|data recorder|데이터.*로거|기록계'),
 ('emc_transient','EMC 내성','ESD·서지·과도현상 시험기','시퀀스 제어·인터록 조사',r'esd.*simulat|electrostatic discharge|surge|burst|transient|load dump|pulse generat|impulse test|power fail|voltage drop|compact simulat|서지|정전기.*시험|전원시험기'),
 ('emc_network','EMC 결합망','LISN·CDN·결합망','배선·경로·교정값 조사',r'\blisn\b|\bcdn\b|\bisn\b|v-network|coupling.*(?:network|clamp)|absorption device|stabilization network|인공.*회로망'),
 ('chamber','환경·신뢰성','환경·열·진공·차폐 챔버','챔버 제어기·PLC·인터록 조사',r'chamber|항온|항습|챔버|shield.*enclosure|차폐.*실|thermal shock|열충격|진공.*시험'),
 ('cooling_heating','환경·신뢰성','냉각·가열·공조 장치','제어기·PLC·인터록 조사',r'chiller|냉각|냉동|냉장|오븐|\boven\b|furnace|항온조|water bath|건조기|heater|heating'),
 ('mechanical_test','환경·신뢰성','진동·충격·기계적 시험기','제어기·PLC·인터록 조사',r'vibration|shaker|drop test|impact test|shock test|crush|tensile|진동|낙하|충격|압축|인장|torsion|굽힘'),
 ('electrical_safety','안전 시험','전기안전·절연·내전압 시험기','프로그래밍 매뉴얼·인터록 조사',r'electrical safety|withstand voltage|hipot|leakage current|touch current|insulation|earth.*(?:bond|resist)|내전압|누설전류|절연|접지저항'),
 ('fire_ip_test','안전 시험','방수·방진·화염·재료 시험 장치','장치 구성·제어기·작업 절차 조사',r'ipx|ip\s*x[0-9]|flame|glow.*wire|bunsen|ball pressure|needle|tracking test|rain|dust|방수|방진|화염|연소|내열|분진|nozzle'),
 ('attenuator','RF 수동부품','감쇠기','수동/가변 여부·경로·교정값 조사',r'attenuat|감쇠기'),
 ('filter','RF 수동부품','필터·듀플렉서','수동/가변 여부·경로·교정값 조사',r'filter|duplexer|필터'),
 ('rf_coupler','RF 수동부품','커플러·분배기·정합 부품','경로·연결 규격·교정값 조사',r'coupler|divider|splitter|balun|matching.*pad|directional bridge|circulator|isolator|coupling.*(?:box|unit)|분배기'),
 ('termination','RF 수동부품','종단기·수동 부하','수동/가변 여부·경로·교정값 조사',r'termination|resistive load|resistor load|verification load|dummy load|종단|터미네이션'),
 ('antenna','RF 안테나','안테나·방사 루프','경로·위치·교정값 조사',r'antenna|radiating loop|dipole|공중선|안테나|elements for sba|imda elements'),
 ('rf_amplifier','RF·신호 증폭','증폭기·프리앰프','제어 가능 여부·상태 감시 조사',r'amplifier|\bamp\b|\blna\b|증폭기|앰프'),
 ('rf_conversion','RF·무선 측정','주파수 변환·믹서·확장 모듈','연결 계측기·프로그래밍 매뉴얼 조사',r'mixer|frequency convert|down convert|up convert|rf convert|transceiver|mill?imeter.*(?:source|module)|frequency extender|demodulat|modulat.*analy'),
 ('sar','SAR·전자기장','SAR·팬텀·전자기장 시험 부속','시스템 연동·SDK·교정값 조사',r'phantom|팬텀|speag|c(?:sar|dasy)|\bsar\b|\bdae\b|dielectric|field.*(?:analy|meter|generator|monitor)|field.*coil|circular coil|자기장|전자기장'),
 ('probe_sensor','센서·프로브','전압·전류·장·가속도 센서','연결 계측기·센서 인터페이스 조사',r'probe|sensor|acceleromet|transducer|thermocouple|프로브|센서|가속도계|열전대'),
 ('temperature_humidity','환경 계측','온도·습도 계측기','디지털 출력·데이터 수집 가능 여부 조사',r'hygromet|thermomet|온습도|온도계|습도계'),
 ('pressure_flow','환경 계측','압력·진공·유량·환경 계측기','센서 출력·프로그래밍 매뉴얼 조사',r'pressure|vacuum gauge|manometer|barometer|flow.*meter|anemometer|particle counter|압력|진공계|유량|풍속|유속|가스.*측정'),
 ('optical','광학·방사선','광학·색·조도·방사선 계측기','프로그래밍 매뉴얼·SDK 조사',r'color analy|optical|photomet|photo.?detec|illumin|lux|laser|spectrophotom|x-ray|xrf|레이저|조도|광도|포토디텍터|microscope|현미경'),
 ('audio','음향','음향 계측·발생 장치','프로그래밍 매뉴얼·SDK 조사',r'audio|sound|acoustic|microphone|piston.*phone|ear simulat|coupler.*ear|octave|음향|소음|마이크'),
 ('calibration','교정·표준','교정기·교정 표준·치구','교정 절차·유효성·연결 계측기 조사',r'calibrat|calibrator|교정|standard.*(?:resist|capac|volt)|standard test hob'),
 ('passive_electrical','전기 수동부품','저항·션트·커패시터·변압기','수동/가변 여부·연결 규격 조사',r'resistor|shunt|capacitor|transformer|저항|커패시터|변압기|capacitan.*box'),
 ('dimension_mass_time','치수·질량·시간','치수·질량·시간·토크 계측기','디지털 출력 또는 수작업 절차 조사',r'caliper|measuring tape|stop\s*watch|timer|torque|balance|\bweight\b|\bscale\b|micrometer|dial gauge|곧은자|줄자|스톱워치|저울|추\b|두께|각도계|길이|회전계'),
 ('fixture_accessory','치구·부속품','시험 치구·케이블·부속품','작업 절차·배선·기구 자동화 검토',r'fixture|\bjig\b|holder|mount|bracket|stand\b|adapter|adaptor|cable|connector|beaker|cylinder|vessel|test rod|metal bar|foil|test arch|test finger|test pin|치구|케이블|거치대|시험봉|비커|실린더|플러그|플러그|지그|테이블|rack|랙|렌치|wrench|cart|카트'),
 ('unclassified','확인 필요','미분류·추가 확인','장비명·용도·제조사 확인',r'.*'),
]
# Additional literal vocabulary observed in this register. Unknown product codes
# (AMMI, AMCC, FBSR-04C, QMS-00100, etc.) deliberately stay unclassified.
EXTRA_PATTERNS = {
 'motion_controller': r'positioning controller|slide bar controller',
 'motion': r'^slide bar$',
 'software_computer': r'notebook|probook|sparrow enterprise|led monitor',
 'interface': r'optocan|optolan|usb can|high speed can|plin-lwl|analog optic convert|network tap|bus converter|^pxi$',
 'rf_analyzer': r'spectrum\s*analy|emi.*reciever|signal alalyzer|emc analyzer|noise figure meter|click (?:meter|analyzer)|wide band receiver',
 'communication_tester': r'wlan.*test|lte.*test|signalling tester|radio.*test|wireless communication|radio communication|wireless.*emulator|network emulator|protocol tester|fira.*test|mobile device tester|multi ue tester|telecom.*analy|telephone.*(?:analy|test)|telephone test head|isdn.*(?:analy|simulat|bridge)|sonet/|pcm channel|cell site test|cdma.*test|bt call simulator|subscriber loop|loop simulator|tel\. line|dual terminal emulator',
 'signal_generator': r'signal gen\.|signal generaotr|signal source|comb generator|noise source|noise emitter|pulse/function genrator',
 'power_supply': r'^psu$|^avr$|ac source|dc source|voltage.*frequency simulator|自動電圧|자동전압조정기|line power conditioner',
 'electronic_load': r'electric load|^dc load$|cell cycler|charge.*discharge.*(?:cycle|cycl)|charger/discharger|charge / discharger|battery.*(?:test|hitester|hi tester)|power battery test',
 'power_meter': r'power quality an|power analayzer|clamp on power',
 'oscilloscope': r'osilloscope',
 'electrical_meter': r'multi-meter|voltage meter|current meter|source meter|source/measure|low ohm|mΩ tester|clamp on ac/dc|av multitester|conductance meter|universal counter|electronic counter',
 'daq': r'scope corder|mobilecorder|hiligger|signal cond(?:ition|igion)ing',
 'emc_transient': r'impulse noise|emc immunity|compact immunity|esd tester|multifunction test generator',
 'emc_network': r'artifi(?:cial|cal) network|em injection clamp|absorbing clamp|capacitive coupling device|phase shift network|compensation network|reference impedance|reference impedence|flicker impedance|전자기 클램프',
 'chamber': r'shield.*(?:room|box)|faraday cage|ems room|ce test room|esd room|high accelerated stress|glove box|주변기기실',
 'cooling_heating': r'water chilling|고압증기멸균|constant temprature',
 'mechanical_test': r'tumbling barrel|push[ -]pull|force tester|compression test|universal testing|endurance test|rollover|projectile|spring impact|impact hammer|impact ball|fall tester|scratch|swivel test|flexing tester|flexibility tester|continuously operation|연속동작시험|air cooled vibrator|sharp.*(?:edge|tester)|edge sharpness|hydraulic tester|locked-rotor',
 'electrical_safety': r'withstand(?:ing)? voltage|withsranding voltage|ground bond|earth contin|short circuit|corona discharge|partial discharge|impulse winding|measuring circuit|voltage test box',
 'fire_ip_test': r'corrosion|염수분무|sprinkler|splash test|spillage|spiliage|immersion tester|oscillating tube|flammability|external icing',
 'attenuator': r'^att \d',
 'filter': r'diplexer',
 'rf_coupler': r'spliter|directional couper|loss pad|matching network|macthing network|impedence matching|return loss bridge|dirextional bridge|rf combiner|dc block',
 'termination': r'^load bank$|^test load$',
 'antenna': r'\bhorn ant\b|bi-log ant|corner reflector',
 'rf_conversion': r'up/down-converter|up/down.convert|주파수변환|range extender|waveguide detector|diode detector|pulse limiter|power limiter',
 'sar': r'^dae\d|dasy\d|(?:wpt|5g) verification|gauss meter|tesla meter|exposure level|field (?:tester|simulator)|em filed meter|gtem|tem\s*cell|strip line|(?:left|right) hand|simulated hand',
 'temperature_humidity': r'^temperture$|temperature & humidity|dewpoint|hygrograph|temperature indicator|thermal imaging',
 'pressure_flow': r'대기압|gas.*(?:monitor|measur|analy)|냉매누설|air (?:velocity|quality) meter|leak tester',
 'optical': r'light meter|파장측정|refract|otdr|^camera$|서베이미터|survey meter|dosimeter|selective radiation|reference radiation',
 'audio': r'mouth simulator|head and torso|hearing aid|speaker|distortion.*(?:analy|measur)|초음파|하이드로폰|acqua',
 'calibration': r'black body source|ac voltage current standard|표준시편|esd target',
 'passive_electrical': r'decade resistance|variable resistance|platinum resistance|power registor|variac|xfmr|배선용 차단기',
 'dimension_mass_time': r'ruler|\brule\b|tapeline|철자|tachimeter|rpm meter|angle meter|protractor|goniometer|distance gauge|dimension gauge|radius gauge|rod gauge|ball gauge|feeler gauge|hardness gauge|\bmass\b|speed indicator|counter for|coating thickness',
 'fixture_accessory': r'\bdia bar\b|test sphere|steel disc|steel disk|alumini?um ring|wooden|wire frame|\btray\b|mask|metallic supports|insulating material|test (?:threshold|surface|hook|corner|carpet|box|pan)|taper bowl|test sieve|\bsteel\b|\bsphere\b|plastic cylindrical|glass plate|shelf|capillary tube|funnel|kettles horizontal|^iron bar|inclined|hardwood|human body test|drop surface|\bcylindrical\b|test tool|test plug|^clamp$|centre punch|^brake$|width strap|spacer|metal plate|\bstep$|black walls|compact table|modular rf platform|수조|시험 용기|원판|인체 외피|water supply|water evaporation',
}
CATEGORIES = [(*c[:-1], c[-1] + ('|' + EXTRA_PATTERNS[c[0]] if c[0] in EXTRA_PATTERNS else '')) for c in CATEGORIES]
CATEGORIES[-1:-1] = [
 ('medical_test','의료기기 시험','생체신호·의료기기 시험기','시험기 매뉴얼·SDK·시험 절차 조사',r'ecg|eeg|defibrillat|esu ne|vital sign|전기수술기|cmrr test|pro-mam|mammography|내시경'),
 ('chemical_lab','이화학·실험실','수질·이화학·실험실 장비','장비 출력·작업 절차 조사',r'ph meter|ec meter|ec/tds|do meter|증류수제조'),
 ('broadcast_network','방송·통신 시스템','방송·통신 시스템 장치','시스템 매뉴얼·SDK 조사',r'base station|radio head|small cell|cmts|modulator|broadcast|video.*(?:measur|noise)|tv analy|drm test|8vsb|p5g solution|multimedia display|tone pulse'),
 ('system_controller','시스템 제어','범용 제어기·시스템 제어 장치','연결 시스템·제어기·SDK 조사',r'controller|control equipment|auto wave control|control module|test configuration unit|voltage multiplex'),
]
COMPILED_CATEGORIES = [(c, re.compile(c[-1], re.I)) for c in CATEGORIES]


def classify(name):
    name = clean(name) or ''
    for category, pattern in COMPILED_CATEGORIES:
        if pattern.search(name):
            return category[0], 'unclassified' if category[0] == 'unclassified' else 'suggested', category[-1]
    raise AssertionError('unclassified fallback missing')
