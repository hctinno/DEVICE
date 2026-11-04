"""No device I/O: inspect report conditions and compile an LTE signaling plan."""
from dgm_rf.fcc import FccResearch
from dgm_rf.cmw_lte import LteRmcConfig,lte_rmc_plan

db=FccResearch()
print(f'FCC: {len(db.groups())} groups; Fold8 UWB: {len(db.cases("fold8-uwb"))} cases')
plan=lte_rmc_plan(LteRmcConfig(25,26140,10,1))
print('OFFLINE SCPI ONLY; not commissioned for DUT/hardware')
for stage in ('configure','start','cleanup'):
    print(stage.upper())
    for command in plan[stage]: print(command)
print('State checkpoints, RF verification and site commissioning are required; nothing was transmitted.')
