#!/usr/bin/env python

"""
Created on Jan 25, 2012
"""

__author__ = "Anubhav Jain, Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Anubhav Jain"
__email__ = "ajain@lbl.gov"
__date__ = "Jan 25, 2012"

import unittest
import os
import json

from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.apps.battery.insertion_battery import InsertionElectrode
from pymatgen import PMGJSONEncoder, PMGJSONDecoder

test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                        'test_files')


class InsertionElectrodeTest(unittest.TestCase):

    def setUp(self):
        self.entry_Li = ComputedEntry("Li", -1.90753119)

        with open(os.path.join(test_dir, "LiTiO2_batt.json"), "r") as f:
            self.entries_LTO = json.load(f, cls=PMGJSONDecoder)

        self.ie_LTO = InsertionElectrode(self.entries_LTO, self.entry_Li)

    def test_voltage(self):
        #test basic voltage
        self.assertAlmostEqual(self.ie_LTO.max_voltage, 2.78583901, 3)
        self.assertAlmostEqual(self.ie_LTO.min_voltage, 0.89702381, 3)
        self.assertAlmostEqual(self.ie_LTO.get_average_voltage(), 1.84143141,
                               3)
        #test voltage range selectors
        self.assertAlmostEqual(self.ie_LTO.get_average_voltage(0, 1),
                               0.89702381, 3)
        self.assertAlmostEqual(self.ie_LTO.get_average_voltage(2, 3),
                               2.78583901, 3)
        #test non-existing voltage range
        self.assertAlmostEqual(self.ie_LTO.get_average_voltage(0, 0.1), 0, 3)
        self.assertAlmostEqual(self.ie_LTO.get_average_voltage(4, 5), 0, 3)

    def test_capacities(self):
        #test basic capacity
        self.assertAlmostEqual(self.ie_LTO.get_capacity_grav(), 308.74865045,
                               3)
        self.assertAlmostEqual(self.ie_LTO.get_capacity_vol(), 1205.99391136,
                               3)

        #test capacity selector
        self.assertAlmostEqual(self.ie_LTO.get_capacity_grav(1, 3),
                               154.374325225, 3)

        #test alternate normalization option
        self.assertAlmostEqual(self.ie_LTO.get_capacity_grav(1, 3, False),
                               160.803169506, 3)
        self.assertIsNotNone(self.ie_LTO.to_dict_summary(True))

    def test_get_muO2(self):
        self.assertIsNone(self.ie_LTO.get_max_muO2())

    def test_entries(self):
        #test that the proper number of sub-electrodes are returned
        self.assertEqual(len(self.ie_LTO.get_sub_electrodes(False, True)), 3)
        self.assertEqual(len(self.ie_LTO.get_sub_electrodes(True, True)), 2)

    def test_get_all_entries(self):
        self.ie_LTO.get_all_entries()

    def test_to_from_dict(self):
        d = self.ie_LTO.to_dict
        ie = InsertionElectrode.from_dict(d)
        self.assertAlmostEqual(ie.max_voltage, 2.78583901, 3)
        self.assertAlmostEqual(ie.min_voltage, 0.89702381, 3)
        self.assertAlmostEqual(ie.get_average_voltage(), 1.84143141, 3)

        #Just to make sure json string works.
        json_str = json.dumps(self.ie_LTO, cls=PMGJSONEncoder)
        ie = json.loads(json_str, cls=PMGJSONDecoder)
        self.assertAlmostEqual(ie.max_voltage, 2.78583901, 3)
        self.assertAlmostEqual(ie.min_voltage, 0.89702381, 3)
        self.assertAlmostEqual(ie.get_average_voltage(), 1.84143141, 3)

    def test_voltage_pair(self):
        vpair = self.ie_LTO[0]
        self.assertAlmostEqual(vpair.voltage, 2.78583901)
        self.assertAlmostEqual(vpair.mAh, 13400.7411749)
        self.assertAlmostEqual(vpair.mass_charge, 79.8658)
        self.assertAlmostEqual(vpair.mass_discharge, 83.3363)
        self.assertAlmostEqual(vpair.vol_charge, 37.553684467)
        self.assertAlmostEqual(vpair.vol_discharge, 37.917719932)
        self.assertAlmostEqual(vpair.frac_charge, 0.0)
        self.assertAlmostEqual(vpair.frac_discharge, 0.14285714285714285)

if __name__ == '__main__':
    unittest.main()
