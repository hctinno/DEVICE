"""Reviewed family extensions. Limits below are wrapper scope, not product ratings.

PDF page numbers count the cover. Original report inventories remain immutable.
"""
GROUPS = [
    ('SpectrumAnalyzer', 'rs-fsw', 'rs', ['FSW8','FSW13','FSW26','FSW43','FSW85'], [2], '6.40'),
    ('SpectrumAnalyzer', 'rs-esu', 'legacy-rs', ['ESU26'], [2], '5.74'),
    ('SpectrumAnalyzer', 'rs-fsv', 'legacy-rs', ['FSV3','FSV4','FSV7','FSV13','FSV30','FSVA4','FSVA7','FSVA13','FSVA30','FSVA40'], [2], '3.30'),
    ('SpectrumAnalyzer', 'keysight-xsa-a', 'keysight', ['N9000A'], [1], None),
    ('SpectrumAnalyzer', 'keysight-xsa-b', 'keysight', ['N9000B','N9010B','N9020B','N9021B','N9032B','N9041B','N9042B','N9048B'], [1], None),
    ('EmiReceiver', 'rs-fsw', None, ['FSW8','FSW13','FSW26','FSW43','FSW85'], [2,1096,1097,1098,1100,1101,1102,1103], '6.40'),
    ('EmiReceiver', 'rs-esu', None, ['ESU26'], [2,54,55,56,610,611,622,698,702], '5.74'),
    ('EmiReceiver', 'rs-esw', None, ['ESW26'], [2,473,478,484,485,557,562], '3.20'),
    ('EmiReceiver', 'keysight-xsa-a', None, ['N9000A'], [1,709,710,714,718,754], 'A.02.00'),
    ('EmiReceiver', 'keysight-xsa-b', None, ['N9000B','N9010B','N9020B','N9021B','N9032B','N9041B','N9042B','N9048B'], [1,378,379,384,385,386,401,402,403], None),
    ('SignalGenerator', 'keysight-mxg-a', None, ['N5161A','N5162A','N5182A','N5183A'], [1], None),
    ('SignalGenerator', 'keysight-mxg-b', None, ['N5166B','N5171B','N5172B','N5173B','N5181B','N5183B'], [1], None),
    ('SignalGenerator', 'keysight-psg', None, ['E8257D','E8663D'], [1], None),
    ('UsbPowerSensor', 'rs-nrps', None, ['NRP8SN','NRP18SN','NRP33S','NRP33SN','NRP40S','NRP40SN','NRP50S','NRP50SN','NRP67S','NRP67SN','NRP90S','NRP90SN','NRP33SN-V','NRP67SN-V'], [2], '03.40'),
    ('UsbPowerSensor', 'keysight-u2000', None, ['U2001A','U2002A','U2004A','U2000H','U2001H','U2002H','U2000B','U2001B','U2002B'], [259], None),
    ('PowerSupply', 'keysight-e3640', None, ['E3641A','E3642A','E3643A','E3644A','E3645A'], [24,102,103], None),
    ('DigitalMultimeter', 'keysight-truevolt', None, ['34460A','34461A','34465A','34470A'], [1], None),
]


def extra_models(driver, *, dialect=False):
    return {m: (source, mode) if dialect else source
            for name, source, mode, models, _, _ in GROUPS if name == driver for m in models}


def model_rows():
    return [dict(driver=name, model=m, source_id=source, reviewed_pdf_pages=pages,
                 documented_firmware=firmware, firmware_status='site-validation-required',
                 manufacturer='Keysight/Agilent' if source.startswith('keysight') else 'Rohde & Schwarz',
                 status='implemented-uncommissioned', physical_verified=False,
                 scope='9 kHz..1 GHz final detector; QP <=1 GHz' if name == 'EmiReceiver' else
                       '50 MHz..1 GHz reviewed wrapper' if name=='UsbPowerSensor' and m.startswith(('NRP40','NRP50','NRP67','NRP90')) else
                       '10 MHz..1 GHz reviewed wrapper' if name in {'SpectrumAnalyzer','SignalGenerator','UsbPowerSensor'} else
                       'Explicit model/range and site voltage/current limits' if name == 'PowerSupply' else
                       'DC/AC voltage <=10 V; 2-wire resistance <=1 Mohm')
            for name, source, _, models, pages, firmware in GROUPS for m in models]


def is_extension(driver, model):
    return model in extra_models(driver)


def frequency_scope(driver, model, frequency):
    low = 50e6 if driver=='UsbPowerSensor' and model.startswith(('NRP40','NRP50','NRP67','NRP90')) else 10e6
    if is_extension(driver, model) and not low <= frequency <= 1e9:
        raise ValueError(f'Expanded model wrapper scope is {low:g}..1e9 Hz; commissioned installed options still required')


SUPPLY_RANGES = {
    'E3640A': {'P8V': (8,3), 'P20V': (20,1.5)},
    'E3641A': {'P35V': (35,.8), 'P60V': (60,.5)},
    'E3642A': {'P8V': (8,5), 'P20V': (20,2.5)},
    'E3643A': {'P35V': (35,1.4), 'P60V': (60,.8)},
    'E3644A': {'P8V': (8,8), 'P20V': (20,4)},
    'E3645A': {'P35V': (35,2.2), 'P60V': (60,1.3)},
}
