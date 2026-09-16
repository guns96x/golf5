import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.transient_inventory import inventory_transient_objects


class TransientInventory(unittest.TestCase):
    def test_reports_required_measurements_and_missing_items(self):
        db = {
            'measurements': {
                'ASDdc_trq': {'desc': 'active damper torque'},
                'FMTC_qAct': {'desc': 'IQ before damper'},
                'FlMng_pIATCorr_mp': {'desc': 'corrected smoke pressure'},
            },
            'characteristics': {},
        }
        result = inventory_transient_objects(db)
        self.assertTrue(result['measurements']['ASDdc_trq']['found'])
        self.assertEqual(result['measurements']['ASDdc_trq']['role'], 'active_damper_torque')
        self.assertTrue(result['measurements']['ASDdc_trq']['runtime_required'])
        self.assertEqual(result['measurements']['ASDdc_trq']['evidence_level'], 'runtime')
        self.assertIn('CoEng_trqInrLtdDrv', result['missing_required'])
        self.assertNotIn('ASDdc_trq', result['missing_required'])

    def test_selects_asddc_asdrf_and_dynamic_smoke_characteristics(self):
        db = {
            'measurements': {},
            'characteristics': {
                'ASDdc_trqLimHi_CUR': {'address': 1},
                'ASDrf_dtrqPos_MAP': {'address': 2},
                'FlMng_qDynSmoke_MAP': {'address': 3},
                'FlMng_facDynSmkAP_CUR': {'address': 4},
                'PCR_pBDesBas_MAP': {'address': 5},
            },
        }
        result = inventory_transient_objects(db)
        selected = result['characteristics']
        self.assertIn('ASDdc_trqLimHi_CUR', selected)
        self.assertIn('ASDrf_dtrqPos_MAP', selected)
        self.assertIn('FlMng_qDynSmoke_MAP', selected)
        self.assertIn('FlMng_facDynSmkAP_CUR', selected)
        self.assertNotIn('PCR_pBDesBas_MAP', selected)
        self.assertIn('FlMng_facDynSmoke_CUR', result['missing_dynamic_characteristics'])


if __name__ == '__main__':
    unittest.main()
