#!/usr/bin/env python

"""
Utilities for generating nicer plots.
"""

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__date__ = "Mar 13, 2012"

import math


def get_publication_quality_plot(width=8, height=None):
    """
    Provides a publication quality plot, with nice defaults for font sizes etc.

    Args:
        width:
            Width of plot in inches. Defaults to 8in.
        height.
            Height of plot in inches. Defaults to width * golden ratio.

    Returns:
        Matplotlib plot object with properly sized fonts.
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    mpl.rcParams["font.serif"] = "Times New Roman"
    mpl.rcParams["font.sans-serif"] = "Arial"
    golden_ratio = (math.sqrt(5) - 1.0) / 2.0
    if not height:
        height = int(width * golden_ratio)
    plt.figure(figsize=(width, height), facecolor="w")
    plt.ylabel("Y-axis", fontsize=width * 3)
    plt.xlabel("X-axis", fontsize=width * 3)
    plt.xticks(fontsize=width * 3)
    plt.yticks(fontsize=width * 3)
    plt.title("", fontsize=width * 4)
    return plt
