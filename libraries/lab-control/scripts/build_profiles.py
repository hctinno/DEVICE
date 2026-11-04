"""Create non-operational templates; never fill in unprovided site addresses/limits."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
visa=dict(kind='visa',resource='REPLACE_WITH_INSTALLED_VISA_RESOURCE',timeout=30)
templates={
    'dmm':('DigitalMultimeter',dict(model='34461A',max_voltage=0),visa),
    'oda-ex':('OdaEx',dict(model='EX60-40',expected_serial='',expected_firmware='',max_voltage=0,max_current=0,installed_model_confirmed=False),dict(kind='serial',port='',baudrate=9600,parity='N',bytesize=8,stopbits=1,timeout=5,termination='\n')),
    'cmu200-cw':('Cmu200Cw',dict(secondary_address=0,output_port=0,max_frequency_hz=0,max_power_dbm=None,expected_firmware='',site_profile_confirmed=False),visa),
    'co3000':('Co3000',dict(axes={},motion_enabled=False),dict(kind='tcp',host='',port=5025,timeout=5,termination='\n')),
    'osp':('OspSwitch',dict(model='OSP120',modules={},paths={},safe_path='safe',switching_enabled=False),visa),
    'epm':('EpmPowerMeter',dict(model='E4419B'),visa),
    'spectrum':('SpectrumAnalyzer',dict(model='N9030B',max_frequency_hz=0),visa),
    'receiver':('EmiReceiver',dict(model='ESW44',max_frequency_hz=0),visa),
    'rf-source':('SignalGenerator',dict(model='N5182B',max_frequency_hz=0,max_power_dbm=None),visa),
    'power-supply':('PowerSupply',dict(model='E3640A',max_voltage=0,max_current=0),visa),
    'power-meter':('PSeriesPowerMeter',dict(model='N1912A'),visa),
    'usb-sensor':('UsbPowerSensor',dict(model='NRP18S'),visa),
    'hp437b':('Hp437B',{},visa),
    'vna':('VectorNetworkAnalyzer',dict(model='ZNLE6',max_frequency_hz=0,max_power_dbm=None),visa),
    'cmw-lte':('CmwLte',dict(site_profile_confirmed=False),visa),
    'thermotron':('Thermotron8800',dict(channel=1,minimum=None,maximum=None,acknowledgement=False,installed_controller_confirmed=False),
                  dict(kind='tcp',host='',port=8888,timeout=10,termination='\r')),
    'espec':('EspecController',dict(expected_rom='',minimum_c=None,maximum_c=None,installed_controller_confirmed=False),
             dict(kind='tcp',host='',port=10001,timeout=10,termination='\r\n')),
}
for name,(driver,parameters,transport) in templates.items():
    value=dict(driver=driver,parameters=parameters,transport=transport,
               notes='Template only. Confirm installed model/controller, limits, options, address and termination before use.')
    (ROOT/'profiles'/f'{name}.template.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(f'{len(templates)} blocked site templates generated')
