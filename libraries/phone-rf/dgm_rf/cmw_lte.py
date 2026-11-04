"""Offline CMW LTE signaling SCPI plan builder, NOT a commissioned RF executor.

Sources: Rohde & Schwarz RsCmwLteSig 4.0.20.28 reference pages in SOURCES.
This is LTE RMC signaling, not OEM FTM, Apple diagnostics, or a 5G NR API.
"""
from dataclasses import dataclass

BASE='https://rscmwltesig.readthedocs.io/en/latest/'
SOURCES={k:BASE+v+'.html' for k,v in {
    'band':'Configure_Pcc', 'duplex':'Configure_Pcc_Dmode',
    'bandwidth':'Configure_Cell_Bandwidth_Pcc', 'channel':'Configure_RfSettings_Pcc_Channel',
    'schedule':'Configure_Connection_Pcc_Stype', 'rmc':'Configure_Connection_Pcc_Rmc_Uplink',
    'rb_position':'Configure_Connection_Pcc_Rmc_RbPosition',
    'power':'Configure_Uplink_Pcc_Pusch_Tpc', 'cell':'Source_Cell_State',
    'connection':'Call_Pswitched','state':'Pswitched_State'}.items()}
BW={1.4:'B014',3:'B030',5:'B050',10:'B100',15:'B150',20:'B200'}
RB_CAPACITY={1.4:6,3:15,5:25,10:50,15:75,20:100}
RB_ALLOWED={1,2,3,4,5,6,7,8,9,10,12,15,16,17,18,20,21,24,25,27,30,32,36,40,42,45,48,50,54,60,64,72,75,80,81,83,90,92,96,100}
# Restrict to ordinary FDD PCC bands; do not silently generate TDD/SCC-only plans.
FDD_BANDS={1,2,3,4,5,7,8,12,13,14,17,18,19,20,21,24,25,26,28,30,31,65,66,68,70,71,72,73,74,85,87,88}


@dataclass(frozen=True)
class LteRmcConfig:
    band: int
    uplink_channel: int
    bandwidth_mhz: float
    rb_count: int
    modulation: str = 'QPSK'
    rb_position: str = 'LOW'
    instance: int = 1


def lte_rmc_plan(c: LteRmcConfig):
    for name in ['band','uplink_channel','rb_count','instance']:
        if type(getattr(c,name)) is not int:
            raise ValueError(f'{name} must be an integer, not bool/string')
    if c.band not in FDD_BANDS:
        raise ValueError('Only listed FDD PCC bands are supported by this builder')
    if not 0 <= c.uplink_channel <= 262143 or not 1 <= c.instance <= 4:
        raise ValueError('Invalid channel or signaling instance')
    if type(c.bandwidth_mhz) not in (int,float) or c.bandwidth_mhz not in BW:
        raise ValueError('Bandwidth must be 1.4, 3, 5, 10, 15 or 20 MHz')
    if c.rb_count not in RB_ALLOWED or c.rb_count>RB_CAPACITY[c.bandwidth_mhz]:
        raise ValueError('RB allocation is not supported or exceeds cell bandwidth')
    if c.modulation not in {'QPSK','Q16','Q64','Q256'}:
        raise ValueError('Unknown LTE modulation')
    if c.rb_position not in {'LOW','MID','HIGH'}:
        raise ValueError('This builder supports LOW/MID/HIGH positions only')
    root=f'LTE:SIGNaling{c.instance}'
    conf=f'CONFigure:{root}'
    return dict(kind='offline_scpi_plan',hardware_ready=False,
        prerequisites=[
            'Confirm instrument model/options/firmware and this command set.',
            'Validate band/channel/bandwidth and modulation/TBS combination on the configured CMW.',
            'Load verified RF routing, path loss, PLMN/authentication, test SIM/eSIM and DUT attachment setup.',
            'Confirm DUT antenna/fold state and actual uplink waveform/power/duty with instruments.',
            'Implement bounded waits, instrument error-queue checks, cancellation and independent RF-off verification.'
        ],
        configure=[
            f'SOURce:{root}:CELL:STATe OFF',
            f'{conf}:PCC:DMODe FDD',
            f'{conf}:PCC:BAND OB{c.band}',
            f'{conf}:CELL:BANDwidth:PCC:DL {BW[c.bandwidth_mhz]}',
            f'{conf}:RFSettings:PCC:CHANnel:UL {c.uplink_channel}',
            f'{conf}:CONNection:PCC:STYPe RMC',
            f'{conf}:CONNection:PCC:RMC:UL N{c.rb_count},{c.modulation},KEEP',
            f'{conf}:CONNection:PCC:RMC:RBPosition:UL {c.rb_position}',
            f'{conf}:UL:PCC:PUSCh:TPC:SET MAXPower'],
        start=[f'SOURce:{root}:CELL:STATe ON',f'CALL:{root}:PSWitched:ACTion CONNect'],
        checkpoints=[
            dict(after='CELL ON',query=f'SOURce:{root}:CELL:STATe:ALL?',expect='ON,ADJ'),
            dict(before='CONNect',query=f'FETCh:{root}:PSWitched:STATe?',expect='ATT'),
            dict(after='CONNect',query=f'FETCh:{root}:PSWitched:STATe?',expect='CEST')],
        cleanup=[f'CALL:{root}:PSWitched:ACTion DISConnect',f'SOURce:{root}:CELL:STATe OFF'],
        off_query=f'SOURce:{root}:CELL:STATe:ALL?',
        off_expect='OFF,ADJ',
        stop_caveat='Cell OFF confirms callbox output only; confirm DUT RF cessation independently. MINPower is not TX OFF.',
        sources=SOURCES)
