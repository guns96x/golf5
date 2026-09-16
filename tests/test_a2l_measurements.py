import os
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath import a2l


class A2LMeasurementParsing(unittest.TestCase):
    def test_parse_measurement_metadata(self):
        src = textwrap.dedent(r'''
            /begin COMPU_METHOD Trq "torque" RAT_FUNC "%6.1" "Nm"
                COEFFS 0 10 0 0 0 1
            /end COMPU_METHOD
            /begin MEASUREMENT
                ASDdc_trq
                "Momentforderung Aktiver Ruckeldämpfer"
                SWORD
                Trq
                1
                100
                -3276.8
                3276.7
                ECU_ADDRESS 0x123456
            /end MEASUREMENT
        ''')
        with tempfile.NamedTemporaryFile('w', encoding='cp1252', delete=False) as f:
            f.write(src)
            path = f.name
        try:
            db = a2l.parse_a2l(path)
        finally:
            os.unlink(path)
        m = db['measurements']['ASDdc_trq']
        self.assertEqual(m['desc'], 'Momentforderung Aktiver Ruckeldämpfer')
        self.assertEqual(m['dtype'], 'SWORD')
        self.assertEqual(m['conversion'], 'Trq')
        self.assertEqual(m['lower'], -3276.8)
        self.assertEqual(m['upper'], 3276.7)
        self.assertEqual(m['address'], 0x123456)

    def test_measurement_address_is_optional(self):
        src = textwrap.dedent(r'''
            /begin COMPU_METHOD InjMass "inj" RAT_FUNC "%6.2" "mg/stroke"
                COEFFS 0 100 0 0 0 1
            /end COMPU_METHOD
            /begin MEASUREMENT
                FMTC_qAct
                "IQ setpoint"
                SWORD
                InjMass
                1
                100
                -327.68
                327.67
            /end MEASUREMENT
        ''')
        with tempfile.NamedTemporaryFile('w', encoding='cp1252', delete=False) as f:
            f.write(src)
            path = f.name
        try:
            db = a2l.parse_a2l(path)
        finally:
            os.unlink(path)
        self.assertIsNone(db['measurements']['FMTC_qAct']['address'])


if __name__ == '__main__':
    unittest.main()
