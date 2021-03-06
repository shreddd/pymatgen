#!/usr/bin/env python

"""
This module provides classes for plotting PhaseDiagram objects.
"""

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2011, The Materials Project"
__version__ = "1.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__status__ = "Production"
__date__ = "Jun 15, 2012"

import math
import numpy as np
import itertools

from pymatgen.phasediagram.pdanalyzer import PDAnalyzer
from pymatgen.util.string_utils import latexify
from pymatgen.util.plotting_utils import get_publication_quality_plot
from pymatgen.util.coord_utils import in_coord_list


class PDPlotter(object):
    """
    A plotter class for phase diagrams.
    """

    def __init__(self, phasediagram, show_unstable=False):
        """
        Args:
            phasediagram:
                A PhaseDiagram object.
            show_unstable:
                Whether unstable phases will be plotted as well as red crosses.
                Defaults to False.
        """
        self._pd = phasediagram
        self._dim = len(self._pd.elements)
        self.lines = uniquelines(self._pd.facets)
        self.show_unstable = show_unstable
        if self._dim < 2 or self._dim > 4:
            raise ValueError("Only 2-4 components supported!")

    @property
    def pd_plot_data(self):
        """
        Plot data for phase diagram.
        2-comp - Full hull with energies
        3/4-comp - Projection into 2D or 3D Gibbs triangle.

        Returns:
            (lines, stable_entries, unstable_entries):
                - lines is a list of list of coordinates for lines in the PD.
                - stable_entries is a {coordinate : entry} for each stable node
                  in the phase diagram. (Each coordinate can only have one
                  stable phase)
                - unstable_entries is a {entry: coordinates} for all unstable
                  nodes in the phase diagram.
        """
        pd = self._pd
        entries = pd.qhull_entries
        data = np.array(pd.qhull_data)
        lines = []
        stable_entries = {}
        for line in self.lines:
            entry1 = entries[line[0]]
            entry2 = entries[line[1]]
            if self._dim == 2:
                x = [data[line[0]][0], data[line[1]][0]]
                y = [pd.get_form_energy_per_atom(entry1),
                     pd.get_form_energy_per_atom(entry2)]
                coord = [x, y]
            elif self._dim == 3:
                coord = triangular_coord(data[line, 0:2])
            else:
                coord = tet_coord(data[line, 0:3])
            lines.append(coord)
            labelcoord = list(zip(*coord))
            stable_entries[labelcoord[0]] = entry1
            stable_entries[labelcoord[1]] = entry2

        all_entries = pd.all_entries
        all_data = np.array(pd.all_entries_hulldata)
        unstable_entries = dict()
        stable = pd.stable_entries
        for i in xrange(0, len(all_entries)):
            entry = all_entries[i]
            if entry not in stable:
                if self._dim == 2:
                    x = [all_data[i][0], all_data[i][0]]
                    y = [pd.get_form_energy_per_atom(entry),
                         pd.get_form_energy_per_atom(entry)]
                    coord = [x, y]
                elif self._dim == 3:
                    coord = triangular_coord([all_data[i, 0:2],
                                              all_data[i, 0:2]])
                else:
                    coord = tet_coord([all_data[i, 0:3], all_data[i, 0:3],
                                       all_data[i, 0:3]])
                labelcoord = list(zip(*coord))
                unstable_entries[entry] = labelcoord[0]

        return lines, stable_entries, unstable_entries

    def show(self, label_stable=True, label_unstable=True):
        """
        Draws the phase diagram using Matplotlib and show it.
        """
        if self._dim < 4:
            plt = self._get_2d_plot(label_stable, label_unstable)
        elif self._dim == 4:
            plt = self._get_3d_plot(label_stable)
        plt.show()

    def _get_2d_plot(self, label_stable=True, label_unstable=True):
        """
        Shows the plot using pylab.  Usually I won"t do imports in methods,
        but since plotting is a fairly expensive library to load and not all
        machines have matplotlib installed, I have done it this way.
        """

        plt = get_publication_quality_plot(8, 6)
        from matplotlib.font_manager import FontProperties
        (lines, labels, unstable) = self.pd_plot_data
        for x, y in lines:
            plt.plot(x, y, "ko-", linewidth=3, markeredgecolor="k",
                     markerfacecolor="b", markersize=15)
        font = FontProperties()
        font.set_weight("bold")
        font.set_size(24)

        # Sets a nice layout depending on the type of PD. Also defines a
        # "center" for the PD, which then allows the annotations to be spread
        # out in a nice manner.
        if len(self._pd.elements) == 3:
            plt.axis("equal")
            plt.xlim((-0.1, 1.2))
            plt.ylim((-0.1, 1.0))
            plt.axis("off")
            center = (0.5, math.sqrt(3) / 6)
        else:
            all_coords = labels.keys()
            miny = min([c[1] for c in all_coords])
            ybuffer = max(abs(miny) * 0.1, 0.1)
            plt.xlim((-0.1, 1.1))
            plt.ylim((miny - ybuffer, ybuffer))
            center = (0.5, miny / 2)
            plt.xlabel("Fraction", fontsize=28, fontweight='bold')
            plt.ylabel("Formation energy (eV/fu)", fontsize=28,
                       fontweight='bold')

        for coords in sorted(labels.keys(), key=lambda x: -x[1]):
            entry = labels[coords]
            label = entry.name

            # The follow defines an offset for the annotation text emanating
            # from the center of the PD. Results in fairly nice layouts for the
            # most part.
            vec = (np.array(coords) - center)
            vec = vec / np.linalg.norm(vec) * 10 if np.linalg.norm(vec) != 0 \
                else vec
            valign = "bottom" if vec[1] > 0 else "top"
            if vec[0] < -0.01:
                halign = "right"
            elif vec[0] > 0.01:
                halign = "left"
            else:
                halign = "center"
            if label_stable:
                plt.annotate(latexify(label), coords, xytext=vec,
                             textcoords="offset points",
                             horizontalalignment=halign,
                             verticalalignment=valign,
                             fontproperties=font)

        if self.show_unstable:
            font = FontProperties()
            font.set_size(16)
            for entry, coords in unstable.items():
                vec = (np.array(coords) - center)
                vec = vec / np.linalg.norm(vec) * 10
                label = entry.name
                plt.plot(coords[0], coords[1], "ks", linewidth=3,
                         markeredgecolor="k", markerfacecolor="r",
                         markersize=8)
                if label_unstable:
                    plt.annotate(latexify(label), coords, xytext=vec,
                                 textcoords="offset points",
                                 horizontalalignment=halign, color="b",
                                 verticalalignment=valign,
                                 fontproperties=font)
        F = plt.gcf()
        F.set_size_inches((8, 6))
        plt.subplots_adjust(left=0.09, right=0.98, top=0.98, bottom=0.07)
        return plt

    def _get_3d_plot(self, label_stable=True):
        """
        Shows the plot using pylab.  Usually I won"t do imports in methods,
        but since plotting is a fairly expensive library to load and not all
        machines have matplotlib installed, I have done it this way.
        """
        import matplotlib.pyplot as plt
        import mpl_toolkits.mplot3d.axes3d as p3
        from matplotlib.font_manager import FontProperties
        fig = plt.figure()
        ax = p3.Axes3D(fig)
        font = FontProperties()
        font.set_weight("bold")
        font.set_size(20)
        (lines, labels, unstable) = self.pd_plot_data
        count = 1
        newlabels = list()
        for x, y, z in lines:
            ax.plot(x, y, z, "bo-", linewidth=3, markeredgecolor="b",
                    markerfacecolor="r", markersize=10)
        for coords in sorted(labels.keys()):
            entry = labels[coords]
            label = entry.name
            if label_stable:
                if len(entry.composition.elements) == 1:
                    ax.text(coords[0], coords[1], coords[2], label)
                else:
                    ax.text(coords[0], coords[1], coords[2], str(count))
                    newlabels.append("{} : {}".format(count, latexify(label)))
                    count += 1
        plt.figtext(0.01, 0.01, "\n".join(newlabels))
        ax.axis("off")
        return plt

    def write_image(self, stream, image_format="svg"):
        """
        Writes the phase diagram to an image in a stream.

        Args:
            stream:
                stream to write to. Can be a file stream or a StringIO stream.
            image_format
                format for image. Can be any of matplotlib supported formats.
                Defaults to svg for best results for vector graphics.
        """
        if self._dim < 4:
            plt = self._get_2d_plot()
        elif self._dim == 4:
            plt = self._get_3d_plot()

        f = plt.gcf()
        f.set_size_inches((12, 10))

        plt.savefig(stream, format=image_format)

    def plot_chempot_range_map(self, elements):
        """
        Plot the chemical potential range map. Currently works only for
        3-component PDs.

        Args:
            elements:
                Sequence of elements to be considered as independent variables.
                E.g., if you want to show the stability ranges of all Li-Co-O
                phases wrt to uLi and uO, you will supply
                [Element("Li"), Element("O")]
        """
        self.get_chempot_range_map_plot(elements).show()

    def get_chempot_range_map_plot(self, elements):
        """
        Returns a plot of the chemical potential range map. Currently works
        only for 3-component PDs.

        Args:
            elements:
                Sequence of elements to be considered as independent variables.
                E.g., if you want to show the stability ranges of all Li-Co-O
                phases wrt to uLi and uO, you will supply
                [Element("Li"), Element("O")]
        Returns:
            A matplotlib plot object.
        """

        plt = get_publication_quality_plot(12, 8)
        analyzer = PDAnalyzer(self._pd)
        chempot_ranges = analyzer.get_chempot_range_map(elements)
        missing_lines = {}
        excluded_region = []
        for entry, lines in chempot_ranges.items():
            comp = entry.composition
            center_x = 0
            center_y = 0
            coords = []
            contain_zero = any([comp.get_atomic_fraction(el) == 0
                                for el in elements])
            is_boundary = (not contain_zero) and \
                sum([comp.get_atomic_fraction(el) for el in elements]) == 1
            for line in lines:
                (x, y) = line.coords.transpose()
                plt.plot(x, y, "k-")

                for coord in line.coords:
                    if not in_coord_list(coords, coord):
                        coords.append(coord.tolist())
                        center_x += coord[0]
                        center_y += coord[1]
                if is_boundary:
                    excluded_region.extend(line.coords)

            if coords and contain_zero:
                missing_lines[entry] = coords
            else:
                xy = (center_x / len(coords), center_y / len(coords))
                plt.annotate(latexify(entry.name), xy, fontsize=22)

        ax = plt.gca()
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        #Shade the forbidden chemical potential regions.
        excluded_region.append([xlim[1], ylim[1]])
        excluded_region = sorted(excluded_region, key=lambda c: c[0])
        (x, y) = np.transpose(excluded_region)
        plt.fill(x, y, "0.80")

        #The hull does not generate the missing horizontal and vertical lines.
        #The following code fixes this.
        el0 = elements[0]
        el1 = elements[1]
        for entry, coords in missing_lines.items():
            center_x = sum([c[0] for c in coords])
            center_y = sum([c[1] for c in coords])
            comp = entry.composition
            is_x = comp.get_atomic_fraction(el0) < 0.01
            is_y = comp.get_atomic_fraction(el1) < 0.01
            n = len(coords)
            if not (is_x and is_y):
                if is_x:
                    coords = sorted(coords, key=lambda c: c[1])
                    for i in [0, -1]:
                        x = [min(xlim), coords[i][0]]
                        y = [coords[i][1], coords[i][1]]
                        plt.plot(x, y, "k")
                        center_x += min(xlim)
                        center_y += coords[i][1]
                elif is_y:
                    coords = sorted(coords, key=lambda c: c[0])
                    for i in [0, -1]:
                        x = [coords[i][0], coords[i][0]]
                        y = [coords[i][1], min(ylim)]
                        plt.plot(x, y, "k")
                        center_x += coords[i][0]
                        center_y += min(ylim)
                xy = (center_x / (n + 2), center_y / (n + 2))
            else:
                center_x = sum(coord[0] for coord in coords) + xlim[0]
                center_y = sum(coord[1] for coord in coords) + ylim[0]
                xy = (center_x / (n + 1), center_y / (n + 1))

            plt.annotate(latexify(entry.name), xy,
                         horizontalalignment="center",
                         verticalalignment="center", fontsize=22)

        plt.xlabel("$\mu_{{{0}}} - \mu_{{{0}}}^0$ (eV)"
                   .format(el0.symbol))
        plt.ylabel("$\mu_{{{0}}} - \mu_{{{0}}}^0$ (eV)"
                   .format(el1.symbol))
        plt.tight_layout()
        return plt

    def get_contour_pd_plot(self):
        """
        Plot a contour phase diagram plot, where phase triangles are colored
        according to degree of instability by interpolation. Currently only
        works for 3-component phase diagrams.

        Returns:
            A matplotlib plot object.
        """
        from scipy import interpolate
        from matplotlib import cm

        pd = self._pd
        entries = pd.qhull_entries
        data = np.array(pd.qhull_data)

        plt = self._get_2d_plot()
        analyzer = PDAnalyzer(pd)
        data[:, 0:2] = triangular_coord(data[:, 0:2]).transpose()
        for i, e in enumerate(entries):
            data[i, 2] = analyzer.get_e_above_hull(e)

        gridsize = 0.005
        xnew = np.arange(0, 1., gridsize)
        ynew = np.arange(0, 1, gridsize)

        f = interpolate.LinearNDInterpolator(data[:, 0:2], data[:, 2])
        znew = np.zeros((len(ynew), len(xnew)))
        for (i, xval) in enumerate(xnew):
            for (j, yval) in enumerate(ynew):
                znew[j, i] = f(xval, yval)

        plt.contourf(xnew, ynew, znew, 1000, cmap=cm.autumn_r)

        plt.colorbar()
        return plt


def uniquelines(q):
    """
    Given all the facets, convert it into a set of unique lines.  Specifically
    used for converting convex hull facets into line pairs of coordinates.

    Args:
        q:
            A 2-dim sequence, where each row represents a facet. E.g.,
            [[1,2,3],[3,6,7],...]

    Returns:
        setoflines:
            A set of tuple of lines.  E.g., ((1,2), (1,3), (2,3), ....)
    """
    setoflines = set()
    for facets in q:
        for line in itertools.combinations(facets, 2):
            setoflines.add(tuple(sorted(line)))
    return setoflines


def triangular_coord(coord):
    """
    Convert a 2D coordinate into a triangle-based coordinate system for a
    prettier phase diagram.

    Args:
        coordinate:
            coordinate used in the convex hull computation.

    Returns:
        coordinates in a triangular-based coordinate system.
    """
    unitvec = np.array([[1, 0], [0.5, math.sqrt(3) / 2]])
    result = np.dot(np.array(coord), unitvec)
    return result.transpose()


def tet_coord(coord):
    """
    Convert a 3D coordinate into a tetrahedron based coordinate system for a
    prettier phase diagram.

    Args:
        coordinate:
            coordinate used in the convex hull computation.

    Returns:
        coordinates in a tetrahedron-based coordinate system.
    """
    unitvec = np.array([[1, 0, 0], [0.5, math.sqrt(3) / 2, 0],
                        [0.5, 1.0 / 3.0 * math.sqrt(3) / 2, math.sqrt(6) / 3]])
    result = np.dot(np.array(coord), unitvec)
    return result.transpose()
