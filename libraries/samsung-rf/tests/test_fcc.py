import unittest
from dgm_rf.fcc import FccResearch
from dgm_rf.cmw_lte import LteRmcConfig,lte_rmc_plan

class ReportPlans(unittest.TestCase):
    def setUp(self): self.db=FccResearch()

    def test_uwb_profiles_do_not_invent_sp2_or_hprf_short_packet(self):
        cases=self.db.cases('fold8-uwb')
        self.assertEqual(len(cases),18)
        for c in cases:
            v=c['values']
            self.assertIn(v['config'],['SP0','SP1','SP3'])
            if v['prf']=='HPRF': self.assertEqual((v['preamble_id'],v['packet_length']),(25,127))

    def test_model_and_firmware_required(self):
        with self.assertRaises(ValueError): self.db.prepare('fold8-uwb',model='SM-S918N',firmware='test')
        with self.assertRaises(ValueError): self.db.prepare('duo-nfc',model='A3447',firmware='')

    def test_matching_report_firmware_is_not_hardware_authorization(self):
        result=self.db.prepare('duo-nfc',model='A3447',firmware='24A343')
        self.assertFalse(result['ready'])
        self.assertIsNone(result['start_command'])
        with self.assertRaises(RuntimeError): self.db.wire_commands('duo-nfc')

    def test_returned_data_cannot_enable_library(self):
        self.db.group('fold8-uwb')['start_command']='invented'
        self.assertIsNone(self.db.group('fold8-uwb')['start_command'])

    def test_ntn_scs_allocations_and_nfc_states(self):
        self.assertEqual(len(self.db.cases('fold8-ntn')),54)
        for c in self.db.cases('fold8-ntn'):
            v=c['values']
            if v['scs_khz']==3.75:
                self.assertEqual(v['subcarriers'],1)
                self.assertIn(v['offset'],[0,24,47])
        self.assertEqual({(c['values']['state'],c['values']['type'],c['values']['rate_kbps'])
                          for c in self.db.cases('duo-nfc')},{('A','F',212),('B','A',106)})

    def test_unknown_group_or_device_fails(self):
        with self.assertRaises(KeyError): self.db.cases('fake')
        with self.assertRaises(ValueError): self.db.groups('iphone_unknown')

class CmwPlan(unittest.TestCase):
    def config(self,**kw):
        return LteRmcConfig(**dict(dict(band=25,uplink_channel=26140,bandwidth_mhz=10,rb_count=1),**kw))

    def test_lte_start_stop_is_not_generic_phone_at(self):
        p=lte_rmc_plan(self.config())
        self.assertFalse(p['hardware_ready'])
        self.assertTrue(p['start'][1].endswith('CONNect'))
        self.assertTrue(p['cleanup'][0].endswith('DISConnect'))
        self.assertTrue(p['cleanup'][1].endswith('OFF'))
        self.assertEqual(len(p['checkpoints']),3)
        self.assertIn('N1,QPSK,KEEP',p['configure'][6])

    def test_reject_injection_bool_and_invalid_allocations(self):
        for kw in [dict(band=True),dict(rb_count=100,bandwidth_mhz=1.4),dict(modulation='QPSK;*RST'),
                   dict(uplink_channel='26140'),dict(band=48),dict(rb_position='P999'),dict(instance=0)]:
            with self.subTest(kw=kw),self.assertRaises(ValueError): lte_rmc_plan(self.config(**kw))

if __name__=='__main__': unittest.main()
