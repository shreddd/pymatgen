#!/usr/bin/env python

'''
Created on Jun 27, 2012
'''

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__date__ = "Jun 27, 2012"

import unittest
import os
import json

from pymatgen.entries.exp_entries import ExpEntry
from pymatgen import PMGJSONDecoder

test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        'test_files')


class ExpEntryTest(unittest.TestCase):

    def setUp(self):
        thermodata = json.load(open(os.path.join(test_dir, "Fe2O3_exp.json"),
                                    "r"), cls=PMGJSONDecoder)
        self.entry = ExpEntry("Fe2O3", thermodata)

    def test_energy(self):
        self.assertAlmostEqual(self.entry.energy, -825.5)

    def test_to_from_dict(self):
        d = self.entry.to_dict
        e = ExpEntry.from_dict(d)
        self.assertAlmostEqual(e.energy, -825.5)

    def test_str(self):
        self.assertIsNotNone(str(self.entry))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
