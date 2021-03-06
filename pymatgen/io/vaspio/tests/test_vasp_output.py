#!/usr/bin/env python

"""
Created on Jul 16, 2012
"""

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__date__ = "Jul 16, 2012"

import unittest
import os
import json
import numpy as np

from pymatgen.io.vaspio.vasp_output import Chgcar, Locpot, Oszicar, Outcar, \
    Vasprun
from pymatgen import Spin, Orbital

test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                        'test_files')


class VasprunTest(unittest.TestCase):

    def test_properties(self):
        filepath = os.path.join(test_dir, 'vasprun.xml')
        vasprun = Vasprun(filepath)
        filepath2 = os.path.join(test_dir, 'lifepo4.xml')
        vasprun_ggau = Vasprun(filepath2, parse_projected_eigen=True)
        totalscsteps = sum([len(i['electronic_steps'])
                            for i in vasprun.ionic_steps])
        self.assertEquals(29, len(vasprun.ionic_steps))
        self.assertEquals(308, totalscsteps,
                          "Incorrect number of energies read from vasprun.xml")
        self.assertEquals([u'Li', u'Fe', u'Fe', u'Fe', u'Fe', u'P', u'P', u'P',
                           u'P', u'O', u'O', u'O', u'O', u'O', u'O', u'O',
                           u'O', u'O', u'O', u'O', u'O', u'O', u'O', u'O',
                           u'O'],
                          vasprun.atomic_symbols,
                          "Incorrect symbols read from vasprun.xml")
        self.assertEquals(vasprun.final_structure.composition.reduced_formula,
                          "LiFe4(PO4)4",
                          "Wrong formula for final structure read.")
        self.assertIsNotNone(vasprun.incar, "Incar cannot be read")
        self.assertIsNotNone(vasprun.kpoints, "Kpoints cannot be read")
        self.assertIsNotNone(vasprun.eigenvalues,
                             "Eigenvalues cannot be read")
        self.assertAlmostEqual(vasprun.final_energy, -269.38319884, 7,
                               "Wrong final energy")
        self.assertAlmostEqual(vasprun.tdos.get_gap(), 2.0589, 4,
                               "Wrong gap from dos!")

        expectedans = (2.539, 4.0906, 1.5516, False)
        (gap, cbm, vbm, direct) = vasprun.eigenvalue_band_properties
        self.assertAlmostEqual(gap, expectedans[0])
        self.assertAlmostEqual(cbm, expectedans[1])
        self.assertAlmostEqual(vbm, expectedans[2])
        self.assertEqual(direct, expectedans[3])
        self.assertFalse(vasprun.is_hubbard)
        self.assertEqual(vasprun.potcar_symbols, [u'PAW_PBE Li 17Jan2003',
                                                  u'PAW_PBE Fe 06Sep2000',
                                                  u'PAW_PBE Fe 06Sep2000',
                                                  u'PAW_PBE P 17Jan2003',
                                                  u'PAW_PBE O 08Apr2002'])
        self.assertIsNotNone(vasprun.kpoints, "Kpoints cannot be read")
        self.assertIsNotNone(vasprun.actual_kpoints,
                             "Actual kpoints cannot be read")
        self.assertIsNotNone(vasprun.actual_kpoints_weights,
                             "Actual kpoints weights cannot be read")
        for atomdoses in vasprun.pdos:
            for orbitaldos in atomdoses:
                self.assertIsNotNone(orbitaldos, "Partial Dos cannot be read")

        #test skipping ionic steps.
        vasprun_skip = Vasprun(filepath, 3)
        self.assertEqual(vasprun_skip.final_energy, vasprun.final_energy)
        self.assertEqual(len(vasprun_skip.ionic_steps),
                         int(len(vasprun.ionic_steps) / 3) + 1)
        self.assertEqual(len(vasprun_skip.ionic_steps),
                         len(vasprun_skip.structures) - 2)

        self.assertTrue(vasprun_ggau.is_hubbard)
        self.assertEqual(vasprun_ggau.hubbards["Fe"], 4.3)
        self.assertAlmostEqual(vasprun_ggau.projected_eigenvalues[(Spin.up, 0,
                                                                   0, 96,
                                                                   Orbital.s)],
                               0.0032)
        d = vasprun_ggau.to_dict
        self.assertEqual(d["elements"], ["Fe", "Li", "O", "P"])
        self.assertEqual(d["nelements"], 4)

        filepath = os.path.join(test_dir, 'vasprun.xml.unconverged')
        vasprun_unconverged = Vasprun(filepath)
        self.assertFalse(vasprun_unconverged.converged)

    def test_to_dict(self):
        filepath = os.path.join(test_dir, 'vasprun.xml')
        vasprun = Vasprun(filepath)
        #Test that to_dict is json-serializable
        self.assertIsNotNone(json.dumps(vasprun.to_dict))

    def test_get_band_structure(self):
        filepath = os.path.join(test_dir, 'vasprun_Si_bands.xml')
        vasprun = Vasprun(filepath)
        bs = vasprun.get_band_structure(kpoints_filename=
                                        os.path.join(test_dir,
                                                     'KPOINTS_Si_bands'))
        cbm = bs.get_cbm()
        vbm = bs.get_vbm()
        self.assertEqual(cbm['kpoint_index'], [13], "wrong cbm kpoint index")
        self.assertAlmostEqual(cbm['energy'], 6.2301, "wrong cbm energy")
        self.assertEqual(cbm['band_index'], {Spin.up: [4], Spin.down: [4]},
                         "wrong cbm bands")
        self.assertEqual(vbm['kpoint_index'], [0, 63, 64],
                         "wrong vbm kpoint index")
        self.assertAlmostEqual(vbm['energy'], 5.6158, "wrong vbm energy")
        self.assertEqual(vbm['band_index'], {Spin.up: [1, 2, 3],
                                             Spin.down: [1, 2, 3]},
                         "wrong vbm bands")
        self.assertEqual(vbm['kpoint'].label, "\Gamma", "wrong vbm label")
        self.assertEqual(cbm['kpoint'].label, None, "wrong cbm label")


class OutcarTest(unittest.TestCase):

    def test_init(self):
        filepath = os.path.join(test_dir, 'OUTCAR')
        outcar = Outcar(filepath)
        expected_mag = ({'d': 0.0, 'p': 0.003, 's': 0.002, 'tot': 0.005},
                         {'d': 0.798, 'p': 0.008, 's': 0.007, 'tot': 0.813},
                         {'d': 0.798, 'p': 0.008, 's': 0.007, 'tot': 0.813},
                         {'d': 0.0, 'p':-0.117, 's': 0.005, 'tot':-0.112},
                         {'d': 0.0, 'p':-0.165, 's': 0.004, 'tot':-0.162},
                         {'d': 0.0, 'p':-0.117, 's': 0.005, 'tot':-0.112},
                         {'d': 0.0, 'p':-0.165, 's': 0.004, 'tot':-0.162})
        expected_chg = ({'p': 0.154, 's': 0.078, 'd': 0.0, 'tot': 0.232},
                        {'p': 0.707, 's': 0.463, 'd': 8.316, 'tot': 9.486},
                        {'p': 0.707, 's': 0.463, 'd': 8.316, 'tot': 9.486},
                        {'p': 3.388, 's': 1.576, 'd': 0.0, 'tot': 4.964},
                        {'p': 3.365, 's': 1.582, 'd': 0.0, 'tot': 4.947},
                        {'p': 3.388, 's': 1.576, 'd': 0.0, 'tot': 4.964},
                        {'p': 3.365, 's': 1.582, 'd': 0.0, 'tot': 4.947})

        self.assertAlmostEqual(outcar.magnetization, expected_mag, 5,
                               "Wrong magnetization read from Outcar")
        self.assertAlmostEqual(outcar.charge, expected_chg, 5,
                               "Wrong charge read from Outcar")
        self.assertFalse(outcar.is_stopped)
        self.assertEqual(outcar.run_stats, {'System time (sec)': 0.938,
                                            'Total CPU time used (sec)': 545.142,
                                            'Elapsed time (sec)': 546.709,
                                            'Maximum memory used (kb)': 0.0,
                                            'Average memory used (kb)': 0.0,
                                            'User time (sec)': 544.204})
        self.assertAlmostEqual(outcar.efermi, 2.0112)
        self.assertAlmostEqual(outcar.nelect, 44.9999991)
        self.assertAlmostEqual(outcar.total_mag, 0.9999998)

        self.assertIsNotNone(outcar.to_dict)
        filepath = os.path.join(test_dir, 'OUTCAR.stopped')
        outcar = Outcar(filepath)
        self.assertTrue(outcar.is_stopped)


class OszicarTest(unittest.TestCase):

    def test_init(self):
        filepath = os.path.join(test_dir, 'OSZICAR')
        oszicar = Oszicar(filepath)
        self.assertEqual(len(oszicar.electronic_steps),
                         len(oszicar.ionic_steps))
        self.assertEqual(len(oszicar.all_energies), 60)
        self.assertAlmostEqual(oszicar.final_energy, -526.63928)


class LocpotTest(unittest.TestCase):

    def test_init(self):
        filepath = os.path.join(test_dir, 'LOCPOT')
        locpot = Locpot.from_file(filepath)
        self.assertAlmostEqual(-217.05226954,
                               sum(locpot.get_average_along_axis(0)))
        self.assertAlmostEqual(locpot.get_axis_grid(0)[-1], 2.87629, 2)
        self.assertAlmostEqual(locpot.get_axis_grid(1)[-1], 2.87629, 2)
        self.assertAlmostEqual(locpot.get_axis_grid(2)[-1], 2.87629, 2)


class ChgcarTest(unittest.TestCase):

    def test_init(self):
        filepath = os.path.join(test_dir, 'CHGCAR.nospin')
        chg = Chgcar.from_file(filepath)
        self.assertAlmostEqual(chg.get_integrated_diff(0, 2)[0, 1], 0)
        filepath = os.path.join(test_dir, 'CHGCAR.spin')
        chg = Chgcar.from_file(filepath)
        self.assertAlmostEqual(chg.get_integrated_diff(0, 1)[0, 1],
                               -0.0043896932237534022)
        #test sum
        chg += chg
        self.assertAlmostEqual(chg.get_integrated_diff(0, 1)[0, 1],
                               -0.0043896932237534022 * 2)

        filepath = os.path.join(test_dir, 'CHGCAR.noncubic')
        chg = Chgcar.from_file(filepath)
        ans = [0.221423, 0.462059, 0.470549, 0.434775, 0.860738, 2.1717482]
        myans = chg.get_integrated_diff(0, 3, 6)
        self.assertTrue(np.allclose(myans[:, 1], ans))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
