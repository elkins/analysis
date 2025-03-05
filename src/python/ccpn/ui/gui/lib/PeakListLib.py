"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2025-03-05 15:51:45 +0000 (Wed, March 05, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: rhfogh $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.isotopes import name2IsotopeCode
from collections import defaultdict
from itertools import product
from ccpn.util.Logging import getLogger


def restrictedPick(peakListView, axisCodes, peak=None, nmrResidue=None):
    """
    Takes a Peak or an NmrResidue, not both, a set of axisCodes, and a PeakListView.
    Derives positions for picking and feeds them into a PeakList wrapper function that
    performs the picking.
    """

    spectrum = peakListView.spectrumView.spectrum
    peakList = spectrum.peakLists[0]
    doPos = spectrum.includePositiveContours
    doNeg = spectrum.includeNegativeContours

    if peak and nmrResidue:
        # cannot do both at the same time
        return

    if not peak and not nmrResidue:
        # nothing selected
        return

    if peak:
        # DT: causes attribute error PeakList has no axisCodes attribute.
        # if (positionCodeDict := {peak.peakList.axisCodes[ii]: peak.position[ii] for ii in range(len(peak.position))}):
        if positionCodeDict := dict(zip(peak.axisCodes, peak.position)):
            peaks = peakList.restrictedPick(positionCodeDict, doPos, doNeg)
            return peakList, peaks

    allPeaks = []
    if nmrResidue:
        # make sure it is the main-nmrResidue with all the nmrAtoms
        nmrResidue = nmrResidue.mainNmrResidue

        allShifts = defaultdict(list, {})
        shiftList = spectrum.chemicalShiftList

        _mapping = [(atm.isotopeCode, shiftList.getChemicalShift(atm).value) for atm in nmrResidue.nmrAtoms if shiftList.getChemicalShift(atm)]
        for isoCode, shift in _mapping:
            allShifts[isoCode].append(shift)

        # shiftIsotopeCodes = [name2IsotopeCode(code) for code in axisCodes]
        shiftIsotopeCodes = list(map(name2IsotopeCode, axisCodes))

        # make all combinations of position dicts for the shift found for each shift
        _combis = [{axisCodes[shiftIsotopeCodes.index(iso)]: sh for ii, (iso, sh) in enumerate(zip(allShifts.keys(), val)) if iso in shiftIsotopeCodes}
                   for val in product(*allShifts.values())]

        for _posCodeDict in _combis:
            if not _posCodeDict:
                raise ValueError(f'There are no restricted axes associated with {spectrum.id}')

            peaks = peakList.restrictedPick(_posCodeDict, doPos, doNeg)
            allPeaks += peaks

    return peakList, allPeaks


def line_rectangle_intersection(line_start, line_end, rect_top_left, rect_bottom_right, firstIntersect=True):
    """
    Calculate the intersection points between a line and a rectangle.
    """
    x1, y1 = line_start
    x2, y2 = line_end
    rect_x1, rect_y1 = rect_top_left
    rect_x2, rect_y2 = rect_bottom_right

    # Ensure rectangle coordinates are in the correct order
    rect_left = min(rect_x1, rect_x2)
    rect_right = max(rect_x1, rect_x2)
    rect_top = min(rect_y1, rect_y2)
    rect_bottom = max(rect_y1, rect_y2)

    # Calculate line slope and y-intercept
    if x1 != x2:
        m = (y2 - y1) / (x2 - x1)
        b = y1 - m * x1
    else:
        m = None
        b = None

    intersections = []

    # Check for intersection with left or right sides of the rectangle
    if x1 <= rect_left <= x2 or x1 >= rect_left >= x2:
        y = m * rect_left + b if m is not None else y1
        if rect_top <= y <= rect_bottom:
            if firstIntersect:
                return (rect_left, y)
            intersections.append((rect_left, y))

    if x1 <= rect_right <= x2 or x1 >= rect_right >= x2:
        y = m * rect_right + b if m is not None else y1
        if rect_top <= y <= rect_bottom:
            if firstIntersect:
                return (rect_right, y)
            intersections.append((rect_right, y))

    # Check for intersection with top or bottom sides of the rectangle
    if y1 <= rect_top <= y2 or y1 >= rect_top >= y2:
        x = (rect_top - b) / m if m != 0 else x1
        if rect_left <= x <= rect_right:
            if firstIntersect:
                return (x, rect_top)
            intersections.append((x, rect_top))

    if y1 <= rect_bottom <= y2 or y1 >= rect_bottom >= y2:
        x = (rect_bottom - b) / m if m != 0 else x1
        if rect_left <= x <= rect_right:
            if firstIntersect:
                return (x, rect_bottom)
            intersections.append((x, rect_bottom))

    return intersections
