#!/usr/bin/env python

"""
This module provides classes that define a chemical reaction.
"""

from __future__ import division

__author__ = "Shyue Ping Ong, Anubhav Jain"
__copyright__ = "Copyright 2011, The Materials Project"
__version__ = "2.0"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__status__ = "Production"
__date__ = "Jul 11 2012"

import logging
import itertools
import numpy as np
import re
from collections import defaultdict

from pymatgen.serializers.json_coders import MSONable
from pymatgen.core.composition import Composition

logger = logging.getLogger(__name__)


class Reaction(MSONable):
    """
    A class representing a Reaction.
    """

    # Tolerance for determining if a particular component fraction is > 0.
    TOLERANCE = 1e-6

    def __init__(self, reactants, products):
        """
        Reactants and products to be specified as list of
        pymatgen.core.structure.Composition.  e.g., [comp1, comp2]

        Args:
            reactants:
                List of reactants.
            products:
                List of products.
        """
        self._input_reactants = reactants
        self._input_products = products
        all_comp = reactants[:]
        all_comp.extend(products[:])
        els = set()
        for c in all_comp:
            els.update(c.elements)
        els = tuple(els)

        nconstraints = len(all_comp)
        num_els = len(els)
        dim = max(num_els, nconstraints)
        logger.debug("num_els = {}".format(num_els))
        logger.debug("nconstraints = {}".format(nconstraints))
        logger.debug("dim = {}".format(dim))

        if nconstraints < 2:
            raise ReactionError("A reaction cannot be formed with just one "
                                "composition.")
        elif nconstraints == 2:
            if all_comp[0].reduced_formula != all_comp[1].reduced_formula:
                raise ReactionError("Reaction cannot be balanced.")
            else:
                coeffs = [-all_comp[1][els[0]] / all_comp[0][els[0]], 1]
        else:
            comp_matrix = np.zeros((dim, dim))
            count = 0
            if nconstraints < num_els:
                for i in range(nconstraints, num_els):
                    all_comp.append(Composition({els[i]: 1}))
            for c in all_comp:
                for i in range(num_els):
                    comp_matrix[i][count] = c[els[i]]
                count += 1

            if nconstraints > num_els:
                #Try two schemes for making the comp matrix non-singular.
                for i in range(num_els, nconstraints):
                    for j in range(num_els):
                        comp_matrix[i][j] = 0
                    comp_matrix[i][i] = 1
                count = 0
                if abs(np.linalg.det(comp_matrix)) < self.TOLERANCE:
                    for i in range(num_els, nconstraints):
                        for j in range(num_els):
                            comp_matrix[i][j] = count
                            count += 1
                        comp_matrix[i][i] = count
                ans_matrix = np.zeros(nconstraints)
                ans_matrix[num_els:nconstraints] = 1
                coeffs = np.linalg.solve(comp_matrix, ans_matrix)
            else:
                if abs(np.linalg.det(comp_matrix)) < self.TOLERANCE:
                    logger.debug("Linear solution possible. Trying various "
                                 "permutations.")
                    comp_matrix = comp_matrix[0:num_els][:, 0:nconstraints]
                    logger.debug("comp_matrix = {}".format(comp_matrix))
                    ans_found = False
                    for perm_matrix in itertools.permutations(comp_matrix):
                        logger.debug("Testing permuted matrix = {}"
                                     .format(perm_matrix))
                        for m in xrange(nconstraints):
                            submatrix = [[perm_matrix[i][j]
                                          for j in xrange(nconstraints)
                                          if j != m]
                                         for i in xrange(nconstraints)
                                         if i != m]
                            logger.debug("Testing submatrix = {}"
                                         .format(submatrix))
                            if abs(np.linalg.det(submatrix)) > self.TOLERANCE:
                                logger.debug("Possible sol")
                                ansmatrix = [perm_matrix[i][m]
                                             for i in xrange(nconstraints)
                                             if i != m]
                                coeffs = -np.linalg.solve(submatrix, ansmatrix)
                                coeffs = [c for c in coeffs]
                                coeffs.insert(m, 1)
                                #Check if final coeffs are valid
                                overall_mat = np.dot(perm_matrix, coeffs)
                                if (abs(overall_mat) < 1e-8).all():
                                    ans_found = True
                                    break
                    if not ans_found:
                        raise ReactionError("Reaction is ill-formed and cannot"
                                            " be balanced.")
                else:
                    raise ReactionError("Reaction is ill-formed and cannot be"
                                        " balanced.")

        for i in xrange(len(coeffs) - 1, -1, -1):
            if coeffs[i] != 0:
                normfactor = coeffs[i]
                break
        #Invert negative solutions and scale to final product
        coeffs = [c / normfactor for c in coeffs]
        self._els = els
        self._all_comp = all_comp[0:nconstraints]
        self._coeffs = coeffs[0:nconstraints]
        self._num_comp = nconstraints

    def copy(self):
        """
        Returns a copy of the Reaction object.
        """
        return Reaction(self.reactants, self.products)

    def calculate_energy(self, energies):
        """
        Calculates the energy of the reaction.

        Args:
            energies:
                dict of {comp:energy}. E.g., {comp1: energy1, comp2: energy2}.

        Returns:
            reaction energy as a float.
        """
        return sum([self._coeffs[i] * energies[self._all_comp[i]]
                    for i in range(self._num_comp)])

    def normalize_to(self, comp, factor=1):
        """
        Normalizes the reaction to one of the compositions.
        By default, normalizes such that the composition given has a
        coefficient of 1. Another factor can be specified.

        Args:
            comp:
                Composition to normalize to
            factor:
                Factor to normalize to. Defaults to 1.
        """
        scale_factor = abs(1 / self._coeffs[self._all_comp.index(comp)]
                           * factor)
        self._coeffs = [c * scale_factor for c in self._coeffs]

    def normalize_to_element(self, element, factor=1):
        """
        Normalizes the reaction to one of the elements.
        By default, normalizes such that the amount of the element is 1.
        Another factor can be specified.

        Args:
            element:
                Element to normalize to.
            factor:
                Factor to normalize to. Defaults to 1.
        """
        all_comp = self._all_comp
        coeffs = self._coeffs
        current_el_amount = sum([all_comp[i][element] * abs(coeffs[i])
                                 for i in xrange(len(all_comp))]) / 2
        scale_factor = factor / current_el_amount
        self._coeffs = [c * scale_factor for c in coeffs]

    def get_el_amount(self, element):
        """
        Returns the amount of the element in the reaction.

        Args:
            element:
                Element in the reaction

        Returns:
            Amount of that element in the reaction.
        """
        return sum([self._all_comp[i][element] * abs(self._coeffs[i])
                    for i in xrange(len(self._all_comp))]) / 2

    @property
    def elements(self):
        """
        List of elements in the reaction
        """
        return self._els[:]

    @property
    def coeffs(self):
        """
        Final coefficients of the calculated reaction
        """
        return self._coeffs[:]

    @property
    def all_comp(self):
        """
        List of all compositions in the reaction.
        """
        return self._all_comp

    @property
    def reactants(self):
        """
        List of reactants
        """
        return [self._all_comp[i] for i in xrange(len(self._all_comp))
                if self._coeffs[i] < 0]

    @property
    def products(self):
        """
        List of products
        """
        return [self._all_comp[i] for i in xrange(len(self._all_comp))
                if self._coeffs[i] > 0]

    def get_coeff(self, comp):
        """
        Returns coefficient for a particular composition
        """
        return self._coeffs[self._all_comp.index(comp)]

    def normalized_repr_and_factor(self):
        """
        Normalized representation for a reaction
        For example, ``4 Li + 2 O -> 2Li2O`` becomes ``2 Li + O -> Li2O``
        """
        reactant_str = []
        product_str = []
        scaled_coeffs = []
        reduced_formulas = []
        for i in range(self._num_comp):
            comp = self._all_comp[i]
            coeff = self._coeffs[i]
            (reduced_formula,
             scale_factor) = comp.get_reduced_formula_and_factor()
            scaled_coeffs.append(coeff * scale_factor)
            reduced_formulas.append(reduced_formula)

        count = 0
        while sum([abs(coeff) % 1 for coeff in scaled_coeffs]) > 1e-8:
            norm_factor = 1 / smart_float_gcd(scaled_coeffs)
            scaled_coeffs = [c / norm_factor for c in scaled_coeffs]
            count += 1
            # Prevent an infinite loop
            if count > 10:
                break

        for i in range(self._num_comp):
            if scaled_coeffs[i] == -1:
                reactant_str.append(reduced_formulas[i])
            elif scaled_coeffs[i] == 1:
                product_str.append(reduced_formulas[i])
            elif scaled_coeffs[i] < 0:
                reactant_str.append("{:.0f} {}".format(-scaled_coeffs[i],
                                                       reduced_formulas[i]))
            elif scaled_coeffs[i] > 0:
                product_str.append("{:.0f} {}".format(scaled_coeffs[i],
                                                      reduced_formulas[i]))
        factor = scaled_coeffs[0] / self._coeffs[0]

        return " + ".join(reactant_str) + " -> " + " + ".join(product_str), \
               factor

    @property
    def normalized_repr(self):
        """
        A normalized representation of the reaction. All factors are converted
        to lowest common factors.
        """
        return self.normalized_repr_and_factor()[0]

    def __eq__(self, other):
        if other is None:
            return False
        for comp in self._all_comp:
            if self.get_coeff(comp) != other.get_coeff(comp):
                return False
        return True

    def __hash__(self):
        return 7

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        reactant_str = []
        product_str = []
        for i in range(self._num_comp):
            comp = self._all_comp[i]
            coeff = self._coeffs[i]
            red_comp = Composition.from_formula(comp.reduced_formula)
            scale_factor = comp.num_atoms / red_comp.num_atoms
            scaled_coeff = coeff * scale_factor
            if scaled_coeff < 0:
                reactant_str.append("{:.3f} {}".format(-scaled_coeff,
                                                       comp.reduced_formula))
            elif scaled_coeff > 0:
                product_str.append("{:.3f} {}".format(scaled_coeff,
                                                      comp.reduced_formula))
        return " + ".join(reactant_str) + " -> " + " + ".join(product_str)

    @property
    def to_dict(self):
        return {"@module": self.__class__.__module__,
                "@class": self.__class__.__name__,
                "reactants": [comp.to_dict for comp in self._input_reactants],
                "products": [comp.to_dict for comp in self._input_products]}

    @staticmethod
    def from_dict(d):
        reactants = [Composition(sym_amt) for sym_amt in d["reactants"]]
        products = [Composition(sym_amt) for sym_amt in d["products"]]
        return Reaction(reactants, products)


def smart_float_gcd(list_of_floats):
    """
    Determines the great common denominator (gcd).  Works on floats as well as
    integers.

    Args:
        list_of_floats: List of floats to determine gcd.
    """
    mult_factor = 1.0
    all_remainders = sorted([abs(f - int(f)) for f in list_of_floats])
    for i in range(len(all_remainders)):
        if all_remainders[i] > 1e-5:
            mult_factor *= all_remainders[i]
            all_remainders = [f2 / all_remainders[i]
                              - int(f2 / all_remainders[i])
                              for f2 in all_remainders]
    return 1 / mult_factor


class ReactionError(Exception):
    """
    Exception class for Reactions. Allows more information in exception
    messages to cover situations not covered by standard exception classes.
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class BalancedReaction(Reaction):
    """
    An extended version of Reaction to allow coefficients to be specified.
    """

    def __init__(self, reactants_coeffs, products_coeffs):
        """
        Reactants and products to be specified as dict of {Composition: coeff}.

        Args:
            reactants:
                Reactants as dict of {Composition: amt}.
            products:
                Products as dict of {Composition: amt}.
        """

        coeffs = []
        all_comp = []
        for comp, c in reactants_coeffs.items():
            if comp not in all_comp:
                all_comp.append(comp)
                coeffs.append(-c)
            else:
                ind = all_comp.index(comp)
                coeffs[ind] += -c

        for comp, c in products_coeffs.items():
            if comp not in all_comp:
                all_comp.append(comp)
                coeffs.append(c)
            else:
                ind = all_comp.index(comp)
                coeffs[ind] += c
        els = set()
        for c in all_comp:
            els.update(c.elements)
        els = tuple(els)

        sum_comp = defaultdict(int)

        for i in xrange(len(all_comp)):
            for el in els:
                sum_comp[el] += coeffs[i] * all_comp[i][el]

        for v in sum_comp.values():
            if abs(v) > Reaction.TOLERANCE:
                raise ReactionError("Reaction is unbalanced!")

        self._input_rct = reactants_coeffs
        self._input_prd = products_coeffs

        self._els = els
        self._all_comp = all_comp
        self._coeffs = coeffs
        self._num_comp = len(self._all_comp)

    @property
    def to_dict(self):
        return {"@module": self.__class__.__module__,
                "@class": self.__class__.__name__,
                "reactants": {str(comp): coeff
                              for comp, coeff in self._input_rct.items()},
                "products": {str(comp): coeff
                             for comp, coeff in self._input_prd.items()}}

    @staticmethod
    def from_dict(d):
        reactants = {Composition(comp): coeff
                     for comp, coeff in d["reactants"].items()}
        products = {Composition(comp): coeff
                    for comp, coeff in d["products"].items()}
        return BalancedReaction(reactants, products)

    @staticmethod
    def from_string(rxn_string):
        """
        Generates a balanced reaction from a string. The reaciton must
        already be balanced.

        Args:
            rxn_string:
                The reaction string. For example, "4 Li + O2-> 2Li2O"

        Returns:
            BalancedReaction
        """
        rct_str, prod_str = rxn_string.split("->")

        def get_comp_amt(comp_str):
            return {Composition(m.group(2)): float(m.group(1) or 1)
                    for m in re.finditer("([\d\.]*)\s*([A-Z][\w\.]*)",
                                         comp_str)}
        return BalancedReaction(get_comp_amt(rct_str), get_comp_amt(prod_str))


class ComputedReaction(Reaction):
    """
    Convenience class to generate a reaction from ComputedEntry objects, with
    some additional attributes, such as a reaction energy based on computed
    energies.
    """

    def __init__(self, reactant_entries, product_entries):
        """
        Args:
            reactant_entries:
                List of reactant_entries.
            products:
                List of product_entries.
        """
        self._reactant_entries = reactant_entries
        self._product_entries = product_entries
        reactant_comp = set([e.composition
                             .get_reduced_composition_and_factor()[0]
                             for e in reactant_entries])
        product_comp = set([e.composition
                            .get_reduced_composition_and_factor()[0]
                            for e in product_entries])
        super(ComputedReaction, self).__init__(list(reactant_comp),
                                               list(product_comp))

    @property
    def calculated_reaction_energy(self):
        calc_energies = {}

        def update_calc_energies(entry):
            (comp, factor) = \
                entry.composition.get_reduced_composition_and_factor()
            calc_energies[comp] = min(calc_energies.get(comp, float('inf')),
                                      entry.energy / factor)
        map(update_calc_energies, self._reactant_entries)
        map(update_calc_energies, self._product_entries)
        return self.calculate_energy(calc_energies)

    @property
    def to_dict(self):
        return {"@module": self.__class__.__module__,
                "@class": self.__class__.__name__,
                "reactants": [e.to_dict for e in self._reactant_entries],
                "products": [e.to_dict for e in self._product_entries]}

    @staticmethod
    def from_dict(d):
        from pymatgen.serializers.json_coders import PMGJSONDecoder
        dec = PMGJSONDecoder()
        reactants = [dec.process_decoded(e) for e in d["reactants"]]
        products = [dec.process_decoded(e) for e in d["products"]]
        return ComputedReaction(reactants, products)
