"""All declared model extensions through native drivers and durable runner evidence."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from dgm_control import equipment_template, check_equipment, run_equipment, probe_equipment, open_device
from dgm_lab.model_scope import model_rows
from dgm_control.equipment import _plain


class EquipmentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_every_extension_model_uses_native_driver_and_saves_proof(self):
        rows=model_rows()
        self.assertGreaterEqual(len({r['model'] for r in rows}),30)
        with patch('socket.create_connection',side_effect=AssertionError('No network allowed')):
            for index,row in enumerate(rows):
                with self.subTest(driver=row['driver'],model=row['model']):
                    job=equipment_template(row['driver'],row['model'])
                    self.assertTrue(check_equipment(job)['valid'])
                    dest=self.root/str(index)
                    result=run_equipment(job,dest)
                    self.assertEqual(result['status'],'completed',result)
                    self.assertTrue(result['simulated']); self.assertFalse(result['physical_verified'])
                    self.assertIsNone(result['fcc_verdict']); self.assertTrue(result['cleanup_scope_succeeded'])
                    self.assertEqual(json.loads((dest/'identity.json').read_text())['identity']['model'],row['model'])
                    traffic=[json.loads(s) for s in (dest/'traffic.jsonl').read_text().splitlines()]
                    tx=[r['payload'] for r in traffic if r['direction']=='tx']
                    self.assertNotIn('*RST',tx)
                    if row['driver'] in {'SignalGenerator','PowerSupply'}:
                        self.assertLess(tx.index('OUTP OFF'),tx.index('OUTP ON'))
                        self.assertIn('OUTP OFF',tx[tx.index('OUTP ON')+1:])
                    else: self.assertIn('ABOR',tx)
                    self.assertEqual(len((dest/'operations.jsonl').read_text().splitlines()),result['operations_completed'])

    def test_all_new_receiver_models_all_final_detectors(self):
        for row in [r for r in model_rows() if r['driver']=='EmiReceiver']:
            for detector in ('POS','QP','LINEAR_AVER','CISPR_AVER'):
                job=equipment_template('EmiReceiver',row['model'])
                job['steps'][0]['arguments']['detector']=detector
                result=run_equipment(job,self.root/(row['model']+detector))
                self.assertEqual(result['status'],'completed',result)

    def test_identity_probe_only_issues_documented_read_queries(self):
        for model in ('FSW8','ESU26','ESW26','N9000A','N9042B'):
            job=equipment_template('EmiReceiver',model)
            dest=self.root/model
            result=probe_equipment(job['profile'],dest)
            self.assertEqual(result['status'],'identified',result)
            self.assertFalse(result['commissioned'])
            tx=[json.loads(s)['payload'] for s in (dest/'traffic.jsonl').read_text().splitlines() if json.loads(s)['direction']=='tx']
            self.assertTrue(set(tx)<={'*IDN?','*OPT?'},tx)

    def test_recipe_rejects_unknown_models_raw_commands_start_and_bad_binding(self):
        from dgm_control import equipment_catalog
        extensions=equipment_catalog()['extensions']
        for row in extensions:
            if row['driver']=='UsbPowerSensor' and row['model'].startswith(('NRP40','NRP50','NRP67','NRP90')):
                self.assertIn('50 MHz',row['scope'])
                self.assertEqual(row['range_source_id'],'rs-nrp-range')
        with self.assertRaises(ValueError): equipment_template('DigitalMultimeter','DMM-UNKNOWN')
        for operation,args in [('start',{}),('raw',{'command':'*RST'}),('read',{'bad':1})]:
            job=equipment_template('DigitalMultimeter')
            job['steps']=[dict(operation=operation,arguments=args)]
            with self.assertRaises((ValueError,TypeError)): check_equipment(job)
        job=equipment_template('DigitalMultimeter');job['settle_seconds']=float('nan')
        with self.assertRaises(ValueError): check_equipment(job)

    def test_pre_cancel_never_connects_and_preserves_inputs(self):
        event=threading.Event();event.set()
        with patch('dgm_control.equipment.open_device',side_effect=AssertionError('No connection')):
            result=run_equipment(equipment_template('DigitalMultimeter'),self.root/'cancel',cancelled=event)
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual(result['operations_completed'],0)
        self.assertTrue((self.root/'cancel/inputs.json').exists())
        self.assertFalse((self.root/'cancel/result.json').exists())

    def test_mid_operation_cancel_stops_output_and_keeps_partial_results(self):
        event=threading.Event(); opened=[]
        @contextmanager
        def connect(profile,**kwargs):
            with open_device(profile,**kwargs) as session:
                opened.append(session._driver.io)
                original=session.call
                def call(op,**args):
                    value=original(op,**args)
                    if op=='read_voltage': event.set()
                    return value
                session.call=call
                yield session
        with patch('dgm_control.equipment.open_device',connect):
            result=run_equipment(equipment_template('PowerSupply','E3641A'),self.root/'mid',cancelled=event)
        self.assertEqual(result['status'],'cancelled',result)
        self.assertFalse(opened[0].output)
        self.assertEqual(result['operations_completed'],2)
        self.assertTrue((self.root/'mid/operations.jsonl').exists())

    def test_bad_measurement_and_cleanup_failure_both_retained(self):
        @contextmanager
        def connect(profile,**kwargs):
            with open_device(profile,**kwargs) as session:
                def fail_read(): raise ValueError('bad DMM data')
                def fail_stop(): raise RuntimeError('abort rejected')
                session._driver.read=fail_read;session._driver.stop=fail_stop
                # Configuration also calls stop; fail only after setup completed.
                original=session.call
                def call(op,**args):
                    if op=='configure':
                        stop=session._driver.stop;session._driver.stop=lambda:None
                        try: return original(op,**args)
                        finally: session._driver.stop=stop
                    return original(op,**args)
                session.call=call
                yield session
        with patch('dgm_control.equipment.open_device',connect):
            result=run_equipment(equipment_template('DigitalMultimeter'),self.root/'bad')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error']['code'],'MULTIPLE_FAILURES')
        self.assertIn('bad DMM data',json.dumps(result))
        self.assertIn('abort rejected',json.dumps(result))
        self.assertFalse(result['cleanup_scope_succeeded'])

    def test_logging_failure_does_not_prevent_output_off(self):
        opened=[]
        @contextmanager
        def connect(profile,**kwargs):
            with open_device(profile,**kwargs) as session:
                opened.append(session._driver.io)
                original=session.call
                def call(op,**args):
                    value=original(op,**args)
                    if op=='configure': session._driver.io.log({'force':True})
                    return value
                session.call=call
                yield session
        from dgm_lab.transport import JsonlLog
        original_log=JsonlLog.__call__
        def fail(log,record):
            if record.get('force'): raise OSError('disk log failure')
            return original_log(log,record)
        with patch('dgm_control.equipment.open_device',connect),patch.object(JsonlLog,'__call__',fail):
            result=run_equipment(equipment_template('PowerSupply'),self.root/'logfail')
        self.assertEqual(result['status'],'failed')
        self.assertFalse(opened[0].output)
        self.assertTrue(result['cleanup_scope_succeeded'])
        self.assertIn('traffic_log_errors',result)

    def test_existing_destination_and_preflight_errors_never_connect(self):
        self.root.joinpath('existing').mkdir()
        with patch('dgm_control.equipment.open_device',side_effect=AssertionError('No connection')):
            with self.assertRaises(FileExistsError): run_equipment(equipment_template('DigitalMultimeter'),self.root/'existing')
            job=equipment_template('DigitalMultimeter'); job['setup'][0]['operation']='start'
            with self.assertRaises(ValueError): run_equipment(job,self.root/'invalid')

    def test_complex_measurements_have_explicit_json_real_imag(self):
        self.assertEqual(_plain(dict(s11=(1+2j,))),dict(s11=[dict(real=1,imag=2)]))
