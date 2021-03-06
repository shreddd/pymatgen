#!/usr/bin/env python

"""
This module provides input and output from the CSSR file format.
"""

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__date__ = "Jan 24, 2012"

import re

from pymatgen.util.io_utils import zopen
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure


class Cssr(object):
    """
    Basic object for working with Cssr file. Right now, only conversion from
    a Structure to a Cssr file is supported.
    """

    def __init__(self, structure):
        """
        Args:
            structure:
                A structure to create the Cssr object.
        """
        if not structure.is_ordered:
            raise ValueError("Cssr file can only be constructed from ordered "
                             "structure")
        self.structure = structure

    def __str__(self):
        output = ["{:.4f} {:.4f} {:.4f}"
                  .format(*self.structure.lattice.abc),
                  "{:.2f} {:.2f} {:.2f} SPGR =  1 P 1    OPT = 1"
                  .format(*self.structure.lattice.angles),
                  "{} 0".format(len(self.structure)),
                  "0 {}".format(self.structure.formula)]
        for i, site in enumerate(self.structure.sites):
            output.append("{} {} {:.4f} {:.4f} {:.4f}"
                          .format(i + 1, site.specie, site.a, site.b, site.c))
        return "\n".join(output)

    def write_file(self, filename):
        """
        Write out a CSSR file.

        Args:
            filename:
                Filename to write to.
        """
        with open(filename, 'w') as f:
            f.write(str(self) + "\n")

    @staticmethod
    def from_string(string):
        """
        Reads a string representation to a Cssr object.

        Args:
            string:
                A string representation of a CSSR.

        Returns:
            Cssr object.
        """
        lines = string.split("\n")
        toks = lines[0].split()
        lengths = map(float, toks)
        toks = lines[1].split()
        angles = map(float, toks[0:3])
        latt = Lattice.from_lengths_and_angles(lengths, angles)
        sp = []
        coords = []
        for l in lines[4:]:
            m = re.match("\d+\s+(\w+)\s+([0-9\-\.]+)\s+([0-9\-\.]+)\s+" +
                         "([0-9\-\.]+)", l.strip())
            if m:
                sp.append(m.group(1))
                coords.append([float(m.group(i)) for i in xrange(2, 5)])
        return Cssr(Structure(latt, sp, coords))

    @staticmethod
    def from_file(filename):
        """
        Reads a CSSR file to a Cssr object.

        Args:
            filename:
                Filename to read from.

        Returns:
            Cssr object.
        """
        with zopen(filename, "r") as f:
            return Cssr.from_string(f.read())
