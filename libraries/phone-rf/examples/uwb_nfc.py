"""Software-only example: python -m examples.uwb_nfc. Never connects a device."""
from dgm_rf import (Profile, Controller, ScriptedTransport, UwbTxConfig, uwb_tx,
                    NfcRequest, NfcPrbsController, SimulatedNfcTransport)

profile=Profile('SIM','fixture',argument_domains={
    's23_uwb_timing':{'gap':['2000'],'window':['750'],'packets':['1000']},
    's23_uwb_tx':{'value':['0']}})
phone=Controller(ScriptedTransport(),profile)
with uwb_tx(phone,UwbTxConfig(9,0,2000,750,1000,power_code=0)):
    pass
for event in phone.log:
    print('SIM:',event['command'])
nfc=NfcPrbsController(SimulatedNfcTransport())
with nfc.session(0,0,verify_started=lambda budget:True,verify_stopped=lambda budget:True):
    pass
print('NFC simulated IDs:',[event['request_id'] for event in nfc.log])
print('NFC payloads:',NfcRequest(31,0,0).nci_payload.hex(),NfcRequest(32).nci_payload.hex())
