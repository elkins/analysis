"""Library functions for (semi)automatic assignment routines

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-10-10 15:45:26 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

# ccp codes sorted by single letter code
CCP_CODES = ('Ala', 'Cys', 'Asp', 'Glu', 'Phe', 'Gly', 'His', 'Ile', 'Lys', 'Leu', 'Met', 'Asn',
             'Pro', 'Gln', 'Arg', 'Ser', 'Thr', 'Val', 'Trp', 'Tyr')

# sorted by 3-letter code
CCP_CODES_SORTED = ('ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 'HIS', 'ILE', 'LEU',
                    'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL')

ATOM_NAMES = {'13C': ['C', 'CA', 'CB', 'CD', 'CD*', 'CD1', 'CD2', 'CE', 'CE*', 'CE1', 'CE2', 'CE3',
                      'CG', 'CG1', 'CG2', 'CH2', 'CZ', 'CZ2', 'CZ3'
                      ],

              '1H' : ['H', 'HA', 'HA2', 'HA3', 'HB',
                      'HB*', 'HB2', 'HB3', 'HD*', 'HD1', 'HD1*', 'HD2', 'HD2*', 'HD3', 'HE', 'HE*', 'HE1',
                      'HE22', 'HE3', 'HG', 'HG1', 'HG1*', 'HG12', 'HG13', 'HG2', 'HG2*', 'HG3', 'HH', 'HH11',
                      'HE2', 'HE21', 'HH12', 'HH2', 'HH21', 'HH22', 'HZ', 'HZ*', 'HZ2', 'HZ3'
                      ],

              '15N': ['N', 'ND1', 'NE', 'NE1', 'NE2', 'NH1', 'NH2', 'NZ']
              }

NEF_ATOM_NAMES = {'13C': ['C', 'CA', 'CB', 'CG', 'CG1', 'CG2', 'CGx', 'CGy', 'CG%',
                          'CD', 'CD1', 'CD2', 'CDx', 'CDy', 'CD%', 'CE', 'CE1', 'CE2', 'CE3',
                          'CEx', 'CEy', 'CE%', 'CZ', 'CZ2', 'CZ3', 'CH2'],
                  '15N': ['N', 'ND1', 'ND2', 'NE', 'NE1', 'NE2', 'NZ', 'NH1', 'NH2', 'NHx', 'NHy'],
                  '1H' : ['H', 'HA', 'HA2', 'HA3', 'HAx', 'HAy', 'HA%', 'HB', 'HB2', 'HB3', 'HBx', 'HBy',
                          'HB%', 'HG', 'HG1', 'HG12', 'HG13', 'HG1x', 'HG1y', 'HG1%', 'HG2', 'HG2%',
                          'HG3', 'HGx', 'HGx%', 'HGy', 'HGy%', 'HG%', 'HD1', 'HD1%', 'HD2', 'HD21', 'HD22',
                          'HD2x', 'HD2y', 'HD2%', 'HD3', 'HDx', 'HDx%', 'HDy', 'HDy%', 'HE', 'HE1', 'HE2',
                          'HE21', 'HE22', 'HE2x', 'HE2y', 'HE3', 'HEx', 'HEy', 'HE%', 'HZ', 'HZ2', 'HZ3', 'HZ%',
                          'HH', 'HH11', 'HH12', 'HH1x', 'HH1y', 'HH2', 'HH21', 'HH22', 'HH2x', 'HH2y',
                          'QA', 'QB', 'QD', 'QE', 'QG', 'QH', 'QH1', 'QH2', 'QR', 'QZ'
                          ]}

NEF_ATOM_NAMES_SORTED = {'alphas'      : ['CA', 'HA', 'HAx', 'HAy', 'HA2', 'HA3', 'HA%'],
                         'betas'       : ['CB', 'HB', 'HBx', 'HBy', 'HB%', 'HB2', 'HB3'],
                         'gammas'      : ['CG', 'CGx', 'CGy', 'CG%', 'CG1', 'CG2', 'HG', 'HGx', 'HGy', 'HG%', 'HG2',
                                          'HG3'],
                         'moreGammas'  : ['HGx%', 'HGy%', 'HG1', 'HG1x', 'HG1y', 'HG1%', 'HG12', 'HG13', 'HG1%',
                                          'HG2%'],
                         'deltas'      : ['CD', 'CDx', 'CDy', 'CD%', 'CD1', 'CD2', 'HDx', 'HDy', 'HD%', 'HD1', 'HD2',
                                          'HD3'],
                         'moreDeltas'  : ['HDx%', 'HDy%', 'ND1', 'ND2', 'HD1%', 'HD2%', 'HD2x', 'HD2y', 'HD21', 'HD22'],
                         'epsilons'    : ['CE', 'CEx', 'CEy', 'CE1', 'CE2', 'HE', 'HEx', 'HEy', 'HE%', 'HE1', 'HE2',
                                          'HE3'],
                         'moreEpsilons': ['CE3', 'NE', 'NE1', 'NE2', 'HE2x', 'HE2y', 'HE21', 'HE22', 'HE%'],
                         'zetas'       : ['CZ', 'CZ2', 'CZ3', 'HZ', 'HZ2', 'HZ3', 'HZ%', 'NZ'],
                         'etas'        : ['CH2', 'HH2', 'HH1x', 'HH1y', 'HH2x', 'HH2y', 'NH1', 'NH2', 'NHx', 'NHy',
                                          'HH21', 'HH22'],
                         'moreEtas'    : ['HH', 'HH11', 'HH12']
                         }

PROTEIN_NEF_ATOM_NAMES = {
    'ALA': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HB%'],
    'ARG': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CD', 'HDx', 'HDy', 'HD2', 'HD3', 'HD%', 'NE', 'HE', 'CZ', 'NHx', 'NHy',
            'NH1', 'NH2', 'HH1x', 'HH1y', 'HH11', 'HH12', 'HH2x', 'HH2y', 'HH21', 'HH22'],
    'ASN': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'ND2',
            'HD2x', 'HD2y', 'HD21', 'HD22'],
    'ASP': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG'],
    'CYS': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'HG'],
    'GLN': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CD', 'NE2', 'HE2x', 'HE2y', 'HE21', 'HE22'],
    'GLU': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CD'],
    'GLY': ['H', 'N', 'C', 'CA', 'HAx', 'HAy', 'HA2', 'HA3', 'HA%'],
    'HIS': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'ND1', 'HD1',
            'CD2', 'HD2', 'CE1', 'HE1', 'NE2', 'HE2'],
    'ILE': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HB', 'CG1', 'HG1x', 'HG1y',
            'HG12', 'HG13', 'HG1%', 'CG2', 'HG2%', 'CD1', 'HD1%'],
    'LEU': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HG', 'CDx',
            'CDy', 'CD%', 'CD1', 'CD2', 'HDx%', 'HDy%', 'HD1%', 'HD2%', 'HD%'],
    'LYS': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CD', 'HDx', 'HDy', 'HD2', 'HD3', 'HD%', 'CE', 'HEx', 'HEy', 'HE2', 'HE3',
            'HE%', 'NZ', 'HZ%'],
    'MET': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CE', 'HE%'],
    'PHE': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'CDx', 'CDy',
            'CD1', 'CD2', 'HDx', 'HDy', 'HD1', 'HD2', 'HD%', 'CEx', 'CEy', 'CE1', 'CE2', 'HEx', 'HEy',
            'HE1', 'HE2', 'HE%', 'CZ', 'HZ'],
    'PRO': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'HGx', 'HGy',
            'HG2', 'HG3', 'HG%', 'CD', 'HDx', 'HDy', 'HD2', 'HD3', 'HD%'],
    'SER': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'HG'],
    'THR': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HB', 'CG2', 'HG1', 'HG2%'],
    'TRP': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'CD1', 'CD2', 'HD1',
            'NE1', 'HE1', 'CE2', 'CE3', 'HE3', 'CZ2', 'CZ3', 'HZ2', 'HZ3', 'CH2', 'HH2'],
    'TYR': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HBx', 'HBy', 'HB2', 'HB3', 'HB%', 'CG', 'CDx', 'CDy', 'CD1',
            'CD2', 'HDx', 'HDy', 'HD1', 'HD2', 'HD%', 'CEx', 'CEy', 'CE1', 'CE2', 'HEx', 'HEy', 'HE1', 'HE2',
            'HE%', 'CZ', 'HH'],
    'VAL': ['H', 'N', 'C', 'CA', 'HA', 'CB', 'HB', 'CGx', 'CGy', 'CG%', 'CG1', 'CG2',
            'HGx%', 'HGy%', 'HG1%', 'HG2%', 'HG%']
    }

# This is a quick and dirty fix in order to enable the creation of synthetic  1H-13C HSQC peak lists.
# This should be overhauled once the new NTdb_jsons have been introduced and updated with NEF atom names.
NEF_ATOM_NAMES_CBONDED = {'CA' : ['HA', 'HA2', 'HA3', 'HAx', 'HAy', 'HA%'],
                          'CB' : ['HB', 'HB2', 'HB3', 'HBx', 'HBy', 'HB%'],
                          'CG' : ['HG', 'HG1', 'HG2', 'HG3', 'HGx', 'HGy', 'HG%'],
                          'CG1': ['HG12', 'HG13', 'HG1x', 'HG1y', 'HG1%', 'HG%'],
                          'CG2': ['HG2%', 'HG%'],
                          'CGx': ['HGx%', 'HG%'],
                          'CGy': ['HGy%', 'HG%'],
                          'CG%': ['HGx%', 'HGy%', 'HG%'],
                          'CD' : ['HD2', 'HD3', 'HDx', 'HDy', 'HD%'],
                          'CD1': ['HD1', 'HD1%'],
                          'CD2': ['HD2', 'HD2%'],
                          'CDx': ['HDx', 'HDx%', 'HD%'],
                          'CDy': ['HDy', 'HDy%', 'HD%'],
                          'CD%': ['HD%'],
                          'CE' : ['HEx%', 'HEy%', 'HE%'],
                          'CE1': ['HE1'],
                          'CE2': ['HE2'],
                          'CE3': ['HE3'],
                          'CEx': ['HEx', 'HE%'],
                          'CEy': ['HEy', 'HE%'],
                          'CE%': ['HE%'],
                          'CZ' : ['HZ'],
                          'CZ2': ['HZ2'],
                          'CZ3': ['HZ3'],
                          'CH2': ['HH2'],
                          }

from itertools import combinations
import typing
import numpy
from typing import Sequence
from collections import defaultdict
from ccpn.core.NmrAtom import NmrAtom, UnknownIsotopeCode
from ccpn.core.Chain import Chain
from ccpn.core.NmrChain import NmrChain
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.Peak import Peak
from ccpn.core.PeakList import PeakList, GAUSSIANMETHOD
from ccpn.core.Project import Project
import ccpn.core.lib.AxisCodeLib as AxisCodeLib
from ccpnmodel.ccpncore.lib.assignment.ChemicalShift import getSpinSystemResidueProbability, getAtomProbability, \
    getResidueAtoms, getCcpCodes, \
    getSpinSystemScore
from ccpn.util import Common as commonUtil
from ccpn.util.Logging import getLogger


defaultAssignmentTolerance = 0.03


def isInterOnlyExpt(experimentType: str) -> bool:
    """
    Determines if the specified experiment is an inter-residual only experiment
    """
    if not experimentType:
        return False
    expList = ('HNCO', 'CONH', 'CONN', 'H[N[CO', 'seq.', 'HCA_NCO.Jmultibond')
    experimentTypeUpper = experimentType.upper()
    if (any(expType in experimentTypeUpper for expType in expList)):
        return True
    return False


def assignAlphas(nmrResidue: NmrResidue, peaks: typing.List[Peak], axisCode='C'):
    """
    Assigns CA and CA-1 NmrAtoms to dimensions of pairs of specified peaks, assuming that one has
    a height greater than the other, e.g. in an HNCA or HNCACB experiment.
    """
    if len(peaks) > 1:
        lowestP = [i for i in peaks if i.height == min([j.height for j in peaks])]
        highestP = [i for i in peaks if i.height == max([j.height for j in peaks])]
        peaks = lowestP + highestP
        chain = nmrResidue.nmrChain
        newNmrResidue = chain.fetchNmrResidue(nmrResidue.sequenceCode + '-1')
        a3 = newNmrResidue.fetchNmrAtom(name='CA')
        a4 = nmrResidue.fetchNmrAtom(name='CA')
        if peaks[0].height > peaks[1].height:
            peaks[0].assignDimension(axisCode=axisCode, value=[a4])
            peaks[1].assignDimension(axisCode=axisCode, value=[a3])
        if peaks[0].height < peaks[1].height:
            peaks[0].assignDimension(axisCode=axisCode, value=[a3])
            peaks[1].assignDimension(axisCode=axisCode, value=[a4])
    elif len(peaks) == 1:
        peaks[0].assignDimension(axisCode=axisCode, value=[nmrResidue.fetchNmrAtom(name='CA')])


def assignBetas(nmrResidue: NmrResidue, peaks: typing.List[Peak], axisCode='C'):
    """
    Assigns CB and CB-1 NmrAtoms to dimensions of specified peaks.
    """
    if len(peaks) > 1:
        lowestP = [i for i in peaks if i.height == min([j.height for j in peaks])]
        highestP = [i for i in peaks if i.height == max([j.height for j in peaks])]
        peaks = lowestP + highestP
        chain = nmrResidue.nmrChain
        newNmrResidue = chain.fetchNmrResidue(nmrResidue.sequenceCode + '-1')
        a3 = newNmrResidue.fetchNmrAtom(name='CB')
        a4 = nmrResidue.fetchNmrAtom(name='CB')
        if abs(peaks[0].height) > abs(peaks[1].height):
            peaks[0].assignDimension(axisCode=axisCode, value=[a4])
            peaks[1].assignDimension(axisCode=axisCode, value=[a3])

        if abs(peaks[0].height) < abs(peaks[1].height):
            peaks[0].assignDimension(axisCode=axisCode, value=[a3])
            peaks[1].assignDimension(axisCode=axisCode, value=[a4])

    elif len(peaks) == 1:
        peaks[0].assignDimension(axisCode=axisCode, value=[nmrResidue.fetchNmrAtom(name='CB')])


def getNmrResiduePrediction(nmrResidue: NmrResidue, chemicalShiftList: ChemicalShiftList, prior: float = 0.05,
                            chemicalShifts=None) -> list:
    """
    Takes an NmrResidue and a ChemicalShiftList and returns a dictionary of the residue type to
    confidence levels for that NmrResidue.
    """

    predictions = {}
    spinSystem = nmrResidue._wrappedData

    if not chemicalShifts:
        # get the non-empty shifts of the nmrAtoms
        chemicalShifts = [(nmrAtom._wrappedData, shift) for nmrAtom in nmrResidue.nmrAtoms
                          for shift in nmrAtom.chemicalShifts if
                          shift.chemicalShiftList == chemicalShiftList and shift.value is not None]

    for code in CCP_CODES:
        predictions[code] = float(getSpinSystemResidueProbability(spinSystem, chemicalShiftList._wrappedData, code,
                                                                  prior=prior, resShifts=chemicalShifts))
    tot = sum(predictions.values())
    refinedPredictions = {}
    for code in CCP_CODES:
        if tot > 0:
            v = int(predictions[code] / tot * 100)
            if v > 0:
                refinedPredictions[code] = v

    finalPredictions = []

    for value in sorted(refinedPredictions.values(), reverse=True)[:5]:
        key = [key for key, val in refinedPredictions.items() if val == value][0]
        finalPredictions.append((key, str(value) + ' %'))

    return finalPredictions


def getNmrAtomPrediction(ccpCode: str, value: float, isotopeCode: str, strict: bool = False) -> list:
    """
    Takes a ccpCode, a chemical shift value and an isotope code and returns a dictionary of
    atom type predictions to confidence values..
    """

    predictions = {}
    for atomName in getResidueAtoms(ccpCode, 'protein'):
        if isotopeCode in ATOM_NAMES and atomName in ATOM_NAMES[isotopeCode]:
            predictions[ccpCode, atomName] = getAtomProbability(ccpCode, atomName, value)
    tot = sum(predictions.values())
    refinedPredictions = {}
    for key, value in predictions.items():
        try:
            if strict:
                if value > 1e-3:
                    v = int(value / tot * 100)
                else:
                    v = 0
            else:
                v = int(value / tot * 100)
        except Exception as es:
            v = 0

        if v > 0:
            refinedPredictions[key] = v

    finalPredictions = []

    for value in sorted(refinedPredictions.values(), reverse=True)[:5]:
        key = [key for key, val in refinedPredictions.items() if val == value][0]
        finalPredictions.append([key, value])

    return finalPredictions


def copyPeakListAssignments(referencePeakList: PeakList, matchPeakList: PeakList):
    """
    Takes a reference peakList and assigns NmrAtoms to dimensions
    of a match peakList based on matching axis codes.
    """

    from sklearn.ensemble import RandomForestClassifier

    project = referencePeakList.project
    refAxisCodes = referencePeakList.spectrum.axisCodes
    matchAxisCodes = matchPeakList.spectrum.axisCodes
    if len(refAxisCodes) < len(matchAxisCodes):
        mappingArray = AxisCodeLib._axisCodeMapIndices(refAxisCodes, matchAxisCodes)
    else:
        mappingArray = AxisCodeLib._axisCodeMapIndices(matchAxisCodes, refAxisCodes)
    refPositions = [numpy.array([peak.position[dim] for dim in mappingArray if dim is not None])
                    for peak in referencePeakList.peaks]
    refLabels = [[peak.pid] for peak in referencePeakList.peaks]
    clf = RandomForestClassifier()
    clf.fit(refPositions, refLabels)

    for peak in matchPeakList.peaks:
        matchArray = []
        for dim in mappingArray:
            if dim is not None:
                matchArray.append(peak.position[dim])

        result = ''.join((clf.predict(numpy.array(matchArray))))

        tolerances = peak.peakList.spectrum.assignmentTolerances
        dimNmrAtoms = project.getByPid(result).dimensionNmrAtoms
        refPositions = project.getByPid(result).position
        if all([abs(refPositions[ii] - peak.position[ii]) < tolerances[ii]
                for ii in mappingArray if ii is not None]):
            [peak.assignDimension(axisCode=refAxisCodes[ii], value=dimNmrAtoms[ii])
             for ii in mappingArray if ii is not None]


def _propagateAssignments(peaks: typing.List[Peak] = None, referencePeak: Peak = None, current: object = None,
                          tolerances: typing.List[float] = None):
    """
    Propagates dimensionNmrAtoms for each dimension of the specified peaks to dimensions of other
    peaks.
    """
    # DEPRECATED in favour of new routine below
    if referencePeak:
        peaksIn = [referencePeak, ]
    elif peaks:
        peaksIn = peaks
    else:
        peaksIn = current.peaks
    if not tolerances:
        tolerances = []

    dimNmrAtoms = {}

    spectra = set()
    for peak in peaksIn:
        spectrum = peak.peakList.spectrum
        spectra.add(spectrum)
        for i, dimensionNmrAtom in enumerate(peak.dimensionNmrAtoms):

            key = spectrum.axisCodes[i]
            if dimNmrAtoms.get(key) is None:
                dimNmrAtoms[key] = []

            if len(peak.dimensionNmrAtoms[i]) > 0:
                for dimensionNmrAtoms in peak.dimensionNmrAtoms[i]:
                    nmrAtom = dimensionNmrAtoms

                    dimNmrAtoms[key].append(nmrAtom)

    # GWV 14/12/21: no longer required as there is always a default value
    # for spectrum in spectra:
    #     if not (all(spectrum.assignmentTolerances)):
    #         # NB Tolerances *should* be non for Fid or sampled dimensions. Even so, for safety:
    #         spectrum.assignmentTolerances = spectrum.defaultAssignmentTolerances

    # spectrum = peak.peakList.spectrum
    # assignmentTolerances = list(spectrum.assignmentTolerances)
    # for tol in assignmentTolerances:
    #   if tol is None:
    #     index = assignmentTolerances.index(tol)
    #     tolerance = spectrum.spectralWidths[index]/spectrum.pointCounts[index]
    #     spectrumTolerances = list(spectrum.assignmentTolerances)
    #     spectrumTolerances[index] =  tolerance
    #     spectrum.assignmentTolerances = spectrumTolerances
    shiftRanges = {}
    for peak in peaksIn:
        for i, axisCode in enumerate(peak.spectrum.axisCodes):

            if axisCode not in shiftRanges:
                shiftMin, shiftMax = sorted(peak.spectrum.spectrumLimits[i])
                shiftRanges[axisCode] = (shiftMin, shiftMax)

            else:
                shiftMin, shiftMax = shiftRanges[axisCode]

            if i < len(tolerances):
                tolerance = tolerances[i]
            else:
                tolerance = peak.spectrum.assignmentTolerances[i]

            pValue = peak.position[i]

            extantNmrAtoms = []

            for dimensionNmrAtom in peak.dimensionNmrAtoms:
                extantNmrAtoms.append(dimensionNmrAtom)

            assignNmrAtoms = []
            closeNmrAtoms = []

            for nmrAtom in dimNmrAtoms[axisCode]:
                if nmrAtom not in extantNmrAtoms:
                    shiftList = peak.chemicalShiftList
                    shift = shiftList.getChemicalShift(nmrAtom)

                    if shift:
                        sValue = shift.value
                        if sValue is not None:
                            if not (shiftMin < sValue < shiftMax):
                                continue

                            assignNmrAtoms.append(nmrAtom)
                            if abs(sValue - pValue) <= tolerance:
                                closeNmrAtoms.append(nmrAtom)

            if closeNmrAtoms:
                for nmrAtom in closeNmrAtoms:
                    peak.assignDimension(axisCode, nmrAtom)

            elif not extantNmrAtoms:
                for nmrAtom in assignNmrAtoms:
                    peak.assignDimension(axisCode, nmrAtom)


from ccpnmodel.ccpncore.lib.assignment.ChemicalShift import _getResidueProbability


def getAllSpinSystems(project: Project, nmrResidues: typing.List[NmrResidue],
                      chains: typing.List[Chain], shiftLists: typing.List[ChemicalShiftList]) -> {}:
    try:
        apiProject = project._wrappedData
        apiSpinSystems = [nmrResidue._wrappedData for nmrResidue in nmrResidues]
        apiChains = [chain._wrappedData for chain in chains]

        shifts = [[(nmrResidue._wrappedData, [(nmrAtom._wrappedData, shift)
                                              for nmrAtom in nmrResidue.nmrAtoms
                                              for shift in nmrAtom.chemicalShifts if
                                              shift.chemicalShiftList == shiftList and shift.value is not None])
                   for nmrResidue in nmrResidues
                   ]
                  for shiftList in shiftLists]

        chainCodes = [[('Cyss' if (residue.ccpCode == 'Cys' and residue.descriptor == 'link:SG') else residue.ccpCode,
                        residue.molType)
                       for residue in apiChain.residues] for apiChain in apiChains]
        setChainCodes = [set(chainCode) for chainCode in chainCodes]

        priorCodes = []
        for chainCode, setChainCode in zip(chainCodes, setChainCodes):
            n = float(len(chainCode))
            priorCodes.append({ccpCode: chainCode.count(ccpCode) / n for ccpCode in setChainCode})

        # now calculate probabilities

        count = 0
        probs = {}
        for ii, (apiChain, setChainCode, priorCode) in enumerate(zip(apiChains, setChainCodes, priorCodes)):

            hsh = ii
            probHash = probs[hsh] = {}

            for jj, _spinSystems in enumerate(shifts):

                spinHash = probHash[jj] = {}

                for _spinSystem in _spinSystems:
                    apiSpinSystem, apiShift = _spinSystem

                    for ccpCode, molType in setChainCode:

                        ppms = []
                        elements = []
                        atomNames = []
                        elementTypes = []
                        ppmsAppend = ppms.append
                        elementsAppend = elements.append
                        atomNamesAppend = atomNames.append
                        elementTypesAppend = elementTypes.append

                        for resonance, shift in apiShift:

                            isotope = resonance.isotope
                            if isotope:
                                ppmsAppend(shift.value)
                                elementsAppend(isotope.chemElement.symbol)
                                atomNamesAppend(resonance.implName)
                                if isotope.chemElement.symbol not in elementTypes:
                                    elementTypesAppend(isotope.chemElement.symbol)

                        prob = _getResidueProbability(ppms, ccpCode, elements, elementTypes,
                                                      atomNames, prior=0.05, molType=molType)

                        if apiSpinSystem not in spinHash:
                            spinHash[apiSpinSystem] = {}
                        if ccpCode not in spinHash[apiSpinSystem]:
                            spinHash[apiSpinSystem][ccpCode] = prob
                        # probHash[apiSpinSystem][ccpCode].append(prob)

                        count += 1

                    # calculate scores from here
                    scores = spinHash[apiSpinSystem]
                    total = sum(scores.values())

                    if total:
                        for ccpCode in scores:
                            scores[ccpCode] *= 100.0 / total

        # print('>>> spinProbability count {}'.format(count))

        assignDict = {}
        for spinSystem in apiProject.resonanceGroups:
            residue = spinSystem.assignedResidue
            if residue:
                assignDict[residue] = spinSystem

        matchesDict = {}

        for ii, (chain, apiChain, probsLists) in enumerate(zip(chains, apiChains, probs.values())):

            matchesChain = matchesDict.setdefault(chain, [])

            for jj, probsList in enumerate(probsLists.values()):
                window = len(nmrResidues)
                textMatrix = []
                objectList = []

                if probsList:
                    matches = []

                    residues = apiChain.sortedResidues()
                    seq = [r.ccpCode for r in residues]

                    seq = [None, None] + seq + [None, None]
                    residues = [None, None] + residues + [None, None]
                    nRes = len(seq)

                    if nRes >= window:
                        scoreDicts = []
                        ccpCodes = getCcpCodes(apiChain)

                        for scores in probsList.values():  # should iterate through residues
                            scoreDict = {}
                            for ccpCode in ccpCodes:
                                scoreDict[ccpCode] = None
                            # scoreDict = {ccpCode: None for ccpCode in ccpCodes}

                            for data in scores.items():
                                if data:
                                    # score, ccpCode = data
                                    ccpCode, score = data
                                    scoreDict[ccpCode] = score

                            scoreDicts.append(scoreDict)
                        sumScore = 0.0
                        for i in range(nRes - window):

                            score = 1.0

                            for j in range(window):
                                ccpCode = seq[i + j]
                                score0 = scoreDicts[j].get(ccpCode)

                                if (ccpCode is None) and (apiSpinSystems[j]):
                                    break
                                if score0:
                                    score *= score0
                                elif score0 == 0.0:
                                    break

                            else:
                                matches.append((score, residues[i:i + window]))
                                sumScore += score

                        matches.sort()
                        matches.reverse()

                        for i, data in enumerate(matches[:10]):
                            score, residues = data
                            if sumScore > 0:
                                score /= sumScore
                            datum = [i + 1, 100.0 * score]

                            for residue in residues:
                                if residue:
                                    datum.append(residue.seqCode)
                                else:
                                    datum.append(None)
                                    # colors.append(None)

                            textMatrix.append(datum)
                            residues2 = [project._data2Obj.get(residue) for residue in residues]
                            objectList.append([100 * score, residues2])

                    if objectList:
                        matchesChain.append(objectList)

        return matchesDict

    except Exception as es:
        getLogger().warning(str(es))
        return {}


def getSpinSystemsLocation(project: Project, nmrResidues: typing.List[NmrResidue],
                           chain: Chain, chemicalShiftList: ChemicalShiftList) -> list:
    """
    Determines location of a set of NmrResidues in the specified chain using residue type
    predictions.
    """

    # TODO NBNB rename variables so api level objects have .api...' names
    # Also consider moving to ccpnmodel, or refactoring. NBNB
    # Also check sorting order for residues

    nmrProject = project._wrappedData
    spinSystems = [nmrResidue._wrappedData for nmrResidue in nmrResidues]
    chain = chain._wrappedData
    shiftList = chemicalShiftList._wrappedData

    scoreMatrix = []
    ccpCodes = getCcpCodes(chain)
    N = len(ccpCodes)

    for nmrResidue in nmrResidues:
        spinSystem0 = nmrResidue._wrappedData

        if spinSystem0:
            shifts = [(nmrAtom._wrappedData, shift)
                      for nmrAtom in nmrResidue.nmrAtoms
                      for shift in nmrAtom.chemicalShifts
                      if shift and shift.chemicalShiftList == shiftList and shift.value is not None]

            scores = getSpinSystemScore(spinSystem0, shifts, chain, shiftList)
            scoreList = [(scores[ccpCode], ccpCode) for ccpCode in ccpCodes]

            scoreList.sort(reverse=True)
        else:
            scoreList = [None] * N

        scoreMatrix.append(scoreList)

    window = len(nmrResidues)
    textMatrix = []
    objectList = []

    if chain and scoreMatrix:
        matches = []

        assignDict = {}
        for spinSystem in nmrProject.resonanceGroups:
            residue = spinSystem.assignedResidue
            if residue:
                assignDict[residue] = spinSystem

        residues = chain.sortedResidues()
        seq = [r.ccpCode for r in residues]

        seq = [None, None] + seq + [None, None]
        residues = [None, None] + residues + [None, None]
        nRes = len(seq)

        if nRes >= window:
            scoreDicts = []
            ccpCodes = getCcpCodes(chain)

            for scores in scoreMatrix:
                scoreDict = {}
                for ccpCode in ccpCodes:
                    scoreDict[ccpCode] = None

                for data in scores:
                    if data:
                        score, ccpCode = data
                        scoreDict[ccpCode] = score

                scoreDicts.append(scoreDict)
            sumScore = 0.0
            for i in range(nRes - window):

                score = 1.0

                for j in range(window):
                    ccpCode = seq[i + j]
                    score0 = scoreDicts[j].get(ccpCode)

                    if (ccpCode is None) and (spinSystems[j]):
                        break
                    elif score0:
                        score *= score0
                    elif score0 == 0.0:
                        break

                else:
                    matches.append((score, residues[i:i + window]))
                    sumScore += score

            matches.sort()
            matches.reverse()

            for i, data in enumerate(matches[:10]):
                score, residues = data
                if sumScore > 0:
                    score /= sumScore
                datum = [i + 1, 100.0 * score]

                for residue in residues:
                    if residue:
                        datum.append(residue.seqCode)
                    else:
                        datum.append(None)
                        # colors.append(None)

                textMatrix.append(datum)
                residues2 = [project._data2Obj.get(residue) for residue in residues]
                objectList.append([100 * score, residues2])

        return objectList


def nmrAtomPairsByDimensionTransfer(peakLists: typing.Sequence[PeakList]) -> dict:
    """From one or more peakLists belonging to the same spectrum,
    get a dictionary of magnetisationTransferTuple (See Spectrum.magnetisationTransfers
    for documentation) to a set of NmrAtom pairs that are coupled by the magnetisation transfer.
    If the two dimensions have the same nucleus, the NmrAtom pairs are sorted, otherwise
    they are in the dimension order.

    Peak.assignedNmrAtoms is used to determine which NmrAtoms are connected"""

    # For subsequent filtering, I recommend:
    # isInterOnlyExpt (this file)
    # NmrAtom.boundNmrAtoms

    result = {}
    if peakLists:

        spectrum = peakLists[0].spectrum
        if any(x for x in peakLists[1:] if x.spectrum is not spectrum):
            raise ValueError("PeakLists do not belong to the same spectrum: %s" % peakLists)

        magnetisationTransfers = spectrum.magnetisationTransfers
        for mt in magnetisationTransfers:
            result[mt] = set()

        # Get sets of NmrAtom pairs
        for peakList in peakLists:
            for peak in peakList.peaks:
                for assignment in peak.assignedNmrAtoms:
                    for mt, aSet in result.items():
                        nmrAtoms = (assignment[mt[0] - 1], assignment[mt[1] - 1], peak)
                        if not None in nmrAtoms:
                            aSet.add(nmrAtoms)

        # Sort NmrAtoms where the nucleus is the same on both sides (or one is undetermined)
        for mt, aSet in result.items():
            tt = spectrum.isotopeCodes
            isotopeCodes = (tt[mt[0] - 1], tt[mt[1] - 1])
            if None in isotopeCodes or isotopeCodes[0] == isotopeCodes[1]:
                newSet = set(tuple(sorted(x for x in nmrAtoms)) for nmrAtoms in aSet)
                result[mt] = newSet

    return result


def getBoundNmrAtomPairs(nmrAtoms, nucleus) -> list:
    """
    Takes a set of NmrAtoms and a nucleus e.g. 'H' or 'C' and returns a list of unique pairs of
    nmrAtoms in the input that are bound to each other.
    """
    result = []
    for na1 in nmrAtoms:
        if na1.name.startswith(nucleus):
            for na2 in na1.boundNmrAtoms:
                if na2 in nmrAtoms:
                    result.append(tuple(sorted([na1, na2])))

    return list(set(result))


def findClosePeaks(peak, matchPeakList, tolerance=0.02):
    """
    Takes an input peak and finds all peaks in the matchPeakList that are close in space to the
    position of the input peak. A close peak is defined as one for which the euclidean distance
    between its position and that of the input peak is less than the specified tolerance. AxisCodes
    are used to match dimensions between peaks to ensure correct distance calculation.
    """
    closePeaks = []
    refAxisCodes = peak.axisCodes
    matchAxisCodes = matchPeakList.spectrum.axisCodes
    mappingArray = [refAxisCodes.index(axisCode) for axisCode in refAxisCodes
                    if axisCode in matchAxisCodes]
    mappingArray2 = [matchAxisCodes.index(axisCode) for axisCode in refAxisCodes
                     if axisCode in matchAxisCodes]
    refPeakPosition = numpy.array([peak.position[dim] for dim in mappingArray if dim is not None])

    for mPeak in matchPeakList.peaks:
        matchArray = []
        for dim in mappingArray2:
            matchArray.append(mPeak.position[dim])

        dist = numpy.linalg.norm(refPeakPosition - numpy.array(matchArray))
        if dist < tolerance:
            closePeaks.append(mPeak)

    return closePeaks


def copyPeakAssignments(refPeak, peaks):
    refAxisCodes = refPeak.axisCodes
    for peak in peaks:
        matchAxisCodes = peak.axisCodes
        mappingArray2 = [matchAxisCodes.index(axisCode) for axisCode in refAxisCodes if axisCode in matchAxisCodes]
        for jj, dim in enumerate(mappingArray2):
            atom = refPeak.dimensionNmrAtoms[jj][0]
            axisCode = peak.axisCodes[dim]
            peak.assignDimension(axisCode, [atom])


def nmrAtomsForPeaks(peaks: typing.List[Peak], nmrAtoms: typing.List[NmrAtom],
                     intraResidual: bool = False, doubleTolerance: bool = False):
    """Get a set of nmrAtoms that fit to the dimensions of the
       peaks.
    """

    selected = matchingNmrAtomsForPeaks(peaks, nmrAtoms, doubleTolerance=doubleTolerance)
    if intraResidual:
        selected = filterIntraResidual(selected)
    return selected


def filterIntraResidual(nmrAtomsForDimensions: typing.List[NmrAtom]):
    """Takes a N-list of lists of nmrAtoms, where N
       is the number of peak dimensions and only returns
       those which belong to residues that show up in
       at least to of the dimensions (This is the behaviour
       in v2, if I am correct).
    """

    nmrResiduesForDimensions = []
    allNmrResidues = set()
    for nmrAtoms in nmrAtomsForDimensions:
        nmrResidues = set([nmrAtom.nmrResidue for nmrAtom in nmrAtoms if nmrAtom.nmrResidue])
        nmrResiduesForDimensions.append(nmrResidues)
        allNmrResidues.update(nmrResidues)

    selectedNmrResidues = set()
    for nmrResidue in allNmrResidues:
        frequency = 0
        for nmrResidues in nmrResiduesForDimensions:
            if nmrResidue in nmrResidues:
                frequency += 1
        if frequency > 1:
            selectedNmrResidues.add(nmrResidue)

    nmrAtomsForDimenionsFiltered = []
    for nmrAtoms in nmrAtomsForDimensions:
        nmrAtoms_filtered = set()
        for nmrAtom in nmrAtoms:
            if nmrAtom.nmrResidue in selectedNmrResidues:
                nmrAtoms_filtered.add(nmrAtom)
        nmrAtomsForDimenionsFiltered.append(nmrAtoms_filtered)

    return nmrAtomsForDimenionsFiltered


def matchingNmrAtomsForPeaks(peaks: typing.List[Peak],
                             nmrAtoms: typing.List[NmrAtom],
                             doubleTolerance: bool = False) -> list:
    """Return the sub-set of nmrAtoms that fit to the dimensions of the peaks.
       All peaks should have the same dimensionality
       This function does the actual calculation and does not involve filtering like
       in nmrAtoms_for_peaks, where more filters can be specified in the future.

       :return a list of the sets matching nmrAtoms per dimension
    """

    dimensionCounts = [peak.spectrum.dimensionCount for peak in peaks]
    # All peaks should have the same number of dimensions.
    if not len(set(dimensionCounts)) == 1:
        return []
    N_dims = dimensionCounts[0]
    matchingNmrAtomsPerDimension = []

    # make dicts from the chemicalShiftLists containing the nmrAtom.pid -> shift value
    #   very quick from the dataFrame
    _shifts = {}
    if (csls := set(pk.peakList.chemicalShiftList for pk in peaks)):
        for csl in csls:
            if shfts := csl.chemicalShifts:
                _shifts[csl] = {sh.nmrAtom.pid: sh.value for sh in shfts if sh.nmrAtom}

    for dim in range(N_dims):
        # Find and add the NmrAtoms that dimension dim in all peaks
        common = set(nmrAtoms)
        for peak in peaks:
            matchingNmrAtoms = matchingNmrAtomsForPeakDimension(peak, dim, nmrAtoms,
                                                                doubleTolerance=doubleTolerance,
                                                                shifts=_shifts)
            # '&=' is set intersection update
            common &= matchingNmrAtoms
        matchingNmrAtomsPerDimension.append(common)

    return matchingNmrAtomsPerDimension


def matchingNmrAtomsForPeakDimension(peak: Peak, dim: int, nmrAtoms: typing.List[NmrAtom],
                                     doubleTolerance: bool = False,
                                     shifts: dict = None) -> typing.Set[NmrAtom]:
    """Find the nmrAtoms that match a dimension of one peak, both with respect to isotopeCode
    and tolerance setting.

    :return A (sub-)set of nmrAtoms that match
    """

    matchingNmrAtoms = set()
    spectrum = peak.peakList.spectrum
    shiftList = peak.peakList.chemicalShiftList
    position = peak.position[dim]

    # isotopeCode = getIsotopeCodeForPeakDimension(peak, dim)
    isotopeCode = spectrum.isotopeCodes[dim]
    if not position or not isotopeCode or not shiftList:
        return matchingNmrAtoms

    tolerance = spectrum.assignmentTolerances[dim]
    if doubleTolerance:
        tolerance *= 2.0

    for nmrAtom in nmrAtoms:
        # find the nmrAtoms with tolerances of the specified position - use the shifts for reference
        if nmrAtom.isotopeCode == isotopeCode and \
                withinTolerance(nmrAtom, position, shiftList, tolerance, shifts):
            matchingNmrAtoms.add(nmrAtom)

    return matchingNmrAtoms


def withinTolerance(nmrAtom: NmrAtom, position: float, shiftList: ChemicalShiftList, tolerance: float,
                    shifts: dict = None):
    """Decides whether the shift of the nmrAtom is
       within the tolerance to be assigned to the
       peak dimension.
    """
    if shifts is not None and shiftList in shifts:
        _value = shifts[shiftList].get(nmrAtom.pid) if nmrAtom else None
        if _value is not None and abs(position - _value) <= tolerance:
            return True

    else:
        # calculate manually, much slower
        shift = shiftList.getChemicalShift(nmrAtom)
        if shift:
            _value = shift.value
            if _value is not None and abs(position - _value) <= tolerance:
                return True
        return False


def peaksAreOnLine(peaks: typing.List[Peak], dimIndex: int):
    """Returns True when multiple peaks are located
       on a line in the dimension defined by dimIndex.
    """
    if not commonUtil.isIterable(peaks):
        raise ValueError('Not iterable peaks argument')

    peaks = list(peaks)
    if len(peaks) == 0:
        raise ValueError('Empty peaks argument')

    if len(peaks) == 1:
        return True

    # Two or more peaks: Take the two furthest peaks (in this dimension) of the selection.
    positions = sorted([peak.position[dimIndex] for peak in peaks])
    max_difference = abs(positions[0] - positions[-1])
    # Use the smallest tolerance of all peaks.
    spectra = set(peak.spectrum for peak in peaks)
    ll = [y for y in (sp.assignmentTolerances[dimIndex] for sp in spectra) if y]
    if ll:
        if len(ll) == 1:
            tolerance = ll[0]
        else:
            tolerance = min(*ll)  # this fails if len(ll) == 1, hence the above
    else:
        tolerance = defaultAssignmentTolerance
    # tolerance = min([getAssignmentToleranceForPeakDimension(peak, dim) for peak in peaks])
    if max_difference < tolerance:
        return True

    return False


def sameAxisCodes(peaks: typing.List[Peak], dim: int):
    """Checks whether all peaks have the same axisCode
       for in the given dimension.
    """

    spectra = set(peak.peakList.spectrum for peak in peaks)
    if len(spectra) > 1:
        spectrum0 = spectra.pop()
        axisCode = spectrum0.axisCodes[dim]
        for spectrum in spectra:
            if not AxisCodeLib.doAxisCodesMatch(spectrum.axisCodes[dim], axisCode):
                return False

    return True


def refitPeaks(peaks: Sequence[Peak], fitMethod: str = GAUSSIANMETHOD, singularMode: bool = False):
    from ccpnmodel.ccpncore.lib.spectrum import Peak as LibPeak

    # LibPeak.fitExistingPeaks([peak._wrappedData for peak in peaks], method)

    if peaks:
        # sort into peakLists for each spectrum, otherwise dataArrays are invalid

        peakLists = {}
        for peak in peaks:
            if peak.peakList in peakLists:
                peakLists[peak.peakList].append(peak)
            else:
                peakLists[peak.peakList] = [peak]

        for peakList, peaks in peakLists.items():
            peakList.fitExistingPeaks(peaks, fitMethod=fitMethod, singularMode=singularMode)


######## CCPN Internal routines used to assign via Drag&Drop from SideBar ###########

def _matchAxesToNmrAtomNames(axisCodes, nmrAtomNames, exactMatch: bool = False, matchingChar: int = 1):
    """
    Make a dict of matching axisCodes, nmrAtomNames.
    Key: the axisCode; value: a list of matching NmrAtom names

    :param axisCodes: list of axis codes
    :param nmrAtomNames: list of nmr atom Names to be matched to the axisCode
    :param exactMatch: Bool. True if needed a 1:1 match. E.g.:  {CA:[CA]};
                             False if only some of the initial characters are required to be matched.
                             Default will do the first character match. E.g.:  {C:[CA, CB]};
    :param matchingChar: int. How many characters of the axis need to be matched to the nmrAtom name.
                              eg. 2: {'HB': ['HBy', 'HBx']}
    :return: dict {axisCode:[nmrAtom names]}
    """
    dd = defaultdict(list)
    for naName in nmrAtomNames:
        for ax in axisCodes:
            if exactMatch:
                if ax == naName:
                    dd[ax].append(naName)
            else:
                if len(ax) >= matchingChar and len(naName) >= matchingChar:
                    if ax[:matchingChar] == naName[:matchingChar]:
                        dd[ax].append(naName)
    return dd


def _matchAxesToNmrAtomIsotopeCode(peak, nmrAtoms):
    """
    Make a dict of matching axisCodes, nmrAtomNames based on common isotopeCodes between nmrAtom-spectrum isotopeCode.
    If nmrAtom.isotopeCode is unknown ('?' or None): it is added to all axisCodes values.
    Key: the axisCode; value: a list of matching NmrAtom names
    :param peak:
    :param nmrAtoms:
    :return:
    """
    dd = defaultdict(list)
    axisCodes = list(peak.axisCodes)

    for axisCode in axisCodes:
        axisCodesDims = peak.peakList.spectrum.getByAxisCodes('dimensions', [axisCode], exactMatch=True)
        if axisCodesDims:
            ic = peak.peakList.spectrum.isotopeCodes[axisCodesDims[0] - 1]
            for nmrAtom in nmrAtoms:
                if nmrAtom.isotopeCode == ic:
                    dd[axisCode].append(nmrAtom.name)
                if not nmrAtom.isotopeCode or nmrAtom.isotopeCode == UnknownIsotopeCode:
                    dd[axisCode].append(nmrAtom.name)
    return dd


def _getNmrAtomForName(nmrAtoms, nmrAtomName) -> NmrAtom | None:
    """
    :return: The NmrAtom object for a given Name or return None. NmrAtoms list should not contain duplicates.
    """
    return ([na for na in nmrAtoms if nmrAtomName == na.name][:1] or [None])[0]


def _assignNmrAtomsToPeaks(peaks, nmrAtoms, exactMatch=False, overwrite=False):
    """
    Called for assigning a selected peak via drag&drop of nmrAtoms from SideBar.
    There are several scenarios divided in ambiguous and unambiguous assignment based on nomenclature and isotopeCode
    matches between nmrAtom-spectrum isotopeCodes or nmrAtom-spectrum axisCodes.
    The top cases are:
    
        unambiguous: exactMatch, an unique axisCode and a single NnmAtom which name matches 1:1 the axisCode name
                     E.g.: axisCode = 'H' -> nmrAtom name = 'H'; {'H': ['H']}
        unambiguous: non exactMatch, an unique axisCode and a single NnmAtom which name partially matches the axisCode name
                     axisCode = 'H' -> nmrAtom name = 'Hn';  {'H': ['Hn']}
                     axisCode = 'Hn' -> nmrAtom name = 'H';  {'Hn': ['H']}
        
        ambiguous:   an unique axisCode and but multiple NmrAtoms matching the axisCode name
                     axisCode = 'H' -> nmrAtom names = 'H1','H2',... ;  {'H': ['H1','H2'...]}
        ambiguous:   two axisCodes and multiple NmrAtoms matching the axisCode names
                     axisCode1 = 'Hn', axisCode2 = 'Hc' -> nmrAtom names = 'H','H1',...; {'Hn': ['H','H1'], 'Hc': ['H','H1']}
        ambiguous:   an unique axisCode and but pseudo NmrAtoms not matching the axisCode name or isotopeCodes of spectrum
                     axisCode = 'H' -> nmrAtom names = 'QA','Jolly',... ;  {'H': ['QA','Jolly',...]}
        ambiguous:   an unique axisCode and but NmrAtoms with name matching axisCode and spectrum isotopeCode
                     axisCode = 'H' -> nmrAtom names = 'M1','Hn',... ;  {'H': ['M1','Hn',...]} nmrAtom m1 has isotopeCode 1H

    Unambiguous nmrAtoms are assigned straight to the peak, if ambiguous nmrAtoms are present a UI will popup.
    Note: If you attempt to assign multiple peaks of different dimensionality at once, it will group based on axisCodes
    and will prompt a popup for each group if ambiguity cannot be resolved.
    :param peaks:
    :param nmrAtoms:
    :param exactMatch:
    :return:
    """
    nmrAtomNames = [na.name for na in nmrAtoms]
    # group peaks with exact axisCodes match so in case of multiple options we don't need a popup for similar peaks.
    peakGroups = defaultdict(list)
    for obj in peaks:
        axs = tuple(sorted(x for x in list(obj.axisCodes)))  # Please don't sort/match simply by first letter code here
        # or it defeat the purpose of all filters done below.
        peakGroups[axs].append(obj)
    # we could add a warning in case many groups.
    for peakGroup in peakGroups.values():
        if not peakGroup:
            break
        peak = peakGroup[-1]
        ambiguousAxisNmrAtomNames = []
        ambiguousNmrAtomsDict = defaultdict(set)
        unambiguousNmrAtomsDict = defaultdict(set)
        nameMatchedNmrAtomsDict = _matchAxesToNmrAtomNames(list(peak.axisCodes), nmrAtomNames, exactMatch=exactMatch)
        isotCodeMatchedNmrAtomsDict = _matchAxesToNmrAtomIsotopeCode(peak, nmrAtoms)
        nameMatchedNmrAtomsDict.update(isotCodeMatchedNmrAtomsDict)

        ## check if same nmrAtoms can be assigned to multiple axisCodes and
        for c in list(combinations(list(nameMatchedNmrAtomsDict.values()), 2)):
            ambiguousAxisNmrAtomNames += list(set(c[0]).intersection(c[1]))

        ## filter the ambiguous and unambiguous nmrAtoms for each axisCodes and fill respective dicts
        for axisCode, matchedNmrAtomNames in nameMatchedNmrAtomsDict.items():
            ## deal with ambiguous nmrAtoms that can be assigned to multiple axisCodes e.g. {'Hn': ['H','H1'], 'Hc': ['H','H1']}
            _unambAxisNmrAtomNames = [name for name in matchedNmrAtomNames if name not in ambiguousAxisNmrAtomNames]
            _ambNmrAtomNames = [name for name in matchedNmrAtomNames if name in ambiguousAxisNmrAtomNames]

            ## fill unambiguousNmrAtomsDict and ambiguousNmrAtomsDict dicts.
            if len(_unambAxisNmrAtomNames) == 1 and len(
                    matchedNmrAtomNames) == 1:  # nothing ambiguous, 1:1 {'H': ['H']}
                na = _getNmrAtomForName(nmrAtoms, _unambAxisNmrAtomNames[0])
                unambiguousNmrAtomsDict[axisCode].add(na)
            if len(matchedNmrAtomNames) > 1:  # make sure nothing appereas as ambiguous and unambiguous. If this happens, keep only as ambiguous {'Hn': ['H', 'M1']} M1 with 1H isotope code
                _nmrAtoms = list(map(lambda x: _getNmrAtomForName(nmrAtoms, x), matchedNmrAtomNames))
                ambiguousNmrAtomsDict[axisCode].update(_nmrAtoms)
            if len(_unambAxisNmrAtomNames) > 1:  # one axis but multiple nmrAtoms. 1:many {'Hn': ['H', 'Hn']}
                _nmrAtoms = list(map(lambda x: _getNmrAtomForName(nmrAtoms, x), _unambAxisNmrAtomNames))
                ambiguousNmrAtomsDict[axisCode].update(_nmrAtoms)
            if len(_ambNmrAtomNames) >= 1:  # multiple axes and multiple nmrAtoms. many:many {'Hn': ['H',...], 'Hc': ['H',...]}
                _nmrAtoms = list(map(lambda x: _getNmrAtomForName(nmrAtoms, x), _ambNmrAtomNames))
                ambiguousNmrAtomsDict[axisCode].update(_nmrAtoms)

        _assignPeakFromNmrAtomDict(peakGroup, unambiguousNmrAtomsDict, ambiguousNmrAtomsDict, overwrite=overwrite)


def _finaliseAssignment(peak, axisCode4NmrAtomsDict, overwrite=False):
    from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar

    with undoBlockWithoutSideBar():
        for _axisCode, _nmrAtoms in axisCode4NmrAtomsDict.items():
            oldNmrAtoms = []
            if not overwrite:  ## Add to existing. We could add a popup to query what to do. "Replace or add" assignment
                axisCodesDims = peak.peakList.spectrum.getByAxisCodes('dimensions', [_axisCode], exactMatch=True)
                if axisCodesDims:
                    dim = axisCodesDims[0] - 1 if axisCodesDims[0] > 0 else axisCodesDims[0]
                    oldNmrAtoms = list(peak.dimensionNmrAtoms[dim])
            newNmrAtoms = list(set(list(_nmrAtoms) + oldNmrAtoms))
            peak.assignDimension(_axisCode, newNmrAtoms)
            ## set the IsotopeCode if was not already set.
            isotopeCode = peak.peakList.spectrum.getByAxisCodes('isotopeCodes', [_axisCode], exactMatch=True)[-1]
            for na in newNmrAtoms:
                if na.isotopeCode in [UnknownIsotopeCode, None]:
                    na._setIsotopeCode(isotopeCode)


def _assignPeakFromNmrAtomDict(peaks, unambiguousNmrAtomsDict, ambiguousNmrAtomsDict,
                               overwrite=False, ):
    """
    assign peaks by axisCode based on unambiguousNmrAtomsDict and ambiguousNmrAtomsDict dictionaries
    Dicts Key: the axisCode; Dicts value: a list of matching NmrAtom assignable for that axisCode
    Dicts should not contains duplicated Values. i.e an NmrAtom or is ambiguous or unambiguous.
    Overwrite to delete existing assignments.
    If ambiguous values, a pop-up will appear otherwise will assign directly.
    """

    # add feedback for un-assignable nmrAtoms

    if not ambiguousNmrAtomsDict and unambiguousNmrAtomsDict:
        for peak in peaks:
            _finaliseAssignment(peak, unambiguousNmrAtomsDict, overwrite=overwrite)
        return
    if ambiguousNmrAtomsDict or unambiguousNmrAtomsDict:
        from ccpn.ui.gui.popups.AssignAmbiguousNmrAtomsPopup import AssignNmrAtoms4AxisCodesPopup

        w = AssignNmrAtoms4AxisCodesPopup(None, axisCode4NmrAtomsDict=ambiguousNmrAtomsDict,
                                          checkedAxisCode4NmrAtomsDict=unambiguousNmrAtomsDict, peaks=peaks)
        result = w.exec_()
        if result:
            axisCode4NmrAtomsDict = w.getSelectedObjects()
            for peak in peaks:
                _finaliseAssignment(peak, axisCode4NmrAtomsDict, overwrite=overwrite)


def _assignNmrResiduesToPeaks(peaks, nmrResidues):
    """
    :param peaks:
    :param nmrResidues:
    :return: assign nmrResidues one at the time based on its nmrAtoms.
    """
    for nmrResidue in nmrResidues:
        _assignNmrAtomsToPeaks(peaks, nmrResidue.nmrAtoms, exactMatch=False)


def _fetchNewPeakAssignments(peakList: PeakList, nmrChain: NmrChain, keepAssignments: bool):
    from ccpn.core.lib.ContextManagers import progressHandler
    from ccpn.core.lib.Notifiers import Notifier
    from functools import partial

    if not (_peaks := list(peakList.peaks)):
        return

    def _updateProgress(pHandler, data):
        # respond to notifier and update the progress-bar
        pHandler.checkCancel()
        indx = _peaks.index(data[Notifier.OBJECT])
        pHandler.setValue(indx)

    # show a progress popup if the operation is taking too long
    with progressHandler(text='Set up NmrResidues...', maximum=len(_peaks) - 1,
                         raiseErrors=False) as progress:
        # add a notifier on a change/create of any peaks in this peakList to update progress-bar
        _notify = Notifier(peakList,
                           [Notifier.CREATE, Notifier.CHANGE],
                           'Peak',
                           partial(_updateProgress, progress))
        peakList.fetchNewAssignments(nmrChain, keepAssignments)

    if progress.error:
        # report any errors
        getLogger().warning(f'fetchNewPeakAssignments: {progress.error}')
    # clean up notifier
    _notify.unRegister()


#=========================================================================================
# _copyPeakAssignments
#=========================================================================================

def _findMatchingDimensions(pk, peaks, tolerancesByIsotope, tolerancesByAxisCode):
    for pk2 in peaks:
        if pk2.pid != pk.pid:
            # Check if the peaks have any isotopeCodes in common
            for ic, axcde in zip(pk.spectrum.isotopeCodes, pk.spectrum.axisCodes):
                for ic2, axcde2 in zip(pk2.spectrum.isotopeCodes, pk2.spectrum.axisCodes):
                    if ic == ic2:
                        _copyPeakAssignments(pk, pk2, axcde, axcde2,
                                             tolerancesByIsotope, tolerancesByAxisCode)


def _copyPeakAssignments(pk, pk2, axcde, axcde2, tolerancesByIsotope, tolerancesByAxisCode):
    # get assigned nmrAtoms from first or reference Peak
    nmrAtoms = _getCleanNmrAtomsList(pk, axcde)
    nmrAtomsToAssign = []
    for nmrAtom in nmrAtoms:
        if tolerancesByIsotope is not None or tolerancesByAxisCode is not None:
            tol = _getTolerance(pk2, axcde2, tolerancesByIsotope, tolerancesByAxisCode)
            shift = pk2.chemicalShiftList.getChemicalShift(nmrAtom)
            if shift and shift.figureOfMerit != 0:
                sValue = shift.value
                # Do Try/Except in case ChemShiftValue is None
                try:
                    diff = abs(sValue - pk2.getByAxisCodes('position', [axcde2], True)[0])
                    if diff <= tol:
                        nmrAtomsToAssign.append(nmrAtom)
                except:
                    print("The ChemicalShift ", shift.pid, " in ChemicalShiftList", pk2.chemicalShiftList.pid,
                          "doesn't have a value. Please correct!")
            # if the NmrAtom doesn't exist in the CSL of the peak it is being copied to, then copy anyway, as there
            # is no tolerance to be violated
            else:
                nmrAtomsToAssign.append(nmrAtom)
        else:
            nmrAtomsToAssign.append(nmrAtom)
    # add assigned nmrAtoms from own peak
    nmrAtomsFromOwnPeak = _getCleanNmrAtomsList(pk2, axcde2)
    nmrAtomsToAssign = nmrAtomsToAssign + nmrAtomsFromOwnPeak
    if nmrAtomsToAssign:
        nmrAtomsToAssign = list(dict.fromkeys(nmrAtomsToAssign))
        pk2.assignDimension(axcde2, nmrAtomsToAssign)


def _getCleanNmrAtomsList(peak, axCde):
    assignedNmrAtoms = [na for i in peak.getByAxisCodes('assignments', [axCde], True) for na in i]
    nmrAtomsList = []
    # remove assignments that are None
    for na in assignedNmrAtoms:
        if na is not None:
            nmrAtomsList.append(na)
    if nmrAtomsList:
        # remove duplicates
        nmrAtomsList = list(dict.fromkeys(nmrAtomsList))
        return nmrAtomsList
    else:
        return []


def _getTolerance(peak, axCde, tolerancesByIsotope, tolerancesByAxisCode):
    """Get the assignments tolerances for the peak.
    Either tolerancesByIsotope, tolerancesByAxisCode, or both can be specified.
    If an isotope-code or axis-code is not found then defaults to the spectrum assignment-tolerances.
    Isotope-codes have priority over axis-codes.
    """
    if tolerancesByIsotope is not None and axCde[0] in tolerancesByIsotope.keys():
        tol = tolerancesByIsotope[axCde[0]]
    elif tolerancesByAxisCode is not None and axCde in tolerancesByAxisCode.keys():
        tol = tolerancesByAxisCode[axCde]
    else:
        tol = peak.spectrum.getByAxisCodes('assignmentTolerances', [axCde], True)[0]
    return tol


def _copyPeakAssignmentsEntry(currentPeaks, referencePeak=None,
                              tolerancesByIsotope=None, tolerancesByAxisCode=None):
    from ccpn.core.lib.ContextManagers import undoBlockWithSideBar as undoBlock

    with undoBlock():
        if referencePeak:
            _findMatchingDimensions(referencePeak, currentPeaks, tolerancesByIsotope, tolerancesByAxisCode)
        else:
            for pk in currentPeaks:
                # only need to copy if peak has assignments
                if pk.assignments != 0:
                    _findMatchingDimensions(pk, currentPeaks, tolerancesByIsotope, tolerancesByAxisCode)


def propagateAssignments(peaks, tolerancesByIsotope=None, tolerancesByAxisCode=None):
    """Propagate assignments - assignments are unified across all selected peaks.
    To match the V2-propagateAssignments, always uses tolerances.

    Specify tolerancesByIsotope, tolerancesByAxisCode, or both.
    If an isotope-code or axis-code is not found then defaults to the spectrum assignment-tolerances for each peak.
    This can be achieved by setting either to an empty dict {}.
    Isotope-codes have priority over axis-codes.
    """
    from ccpn.framework.Application import getCurrent

    if not peaks:
        # do I need to do this?
        peaks = getCurrent().peaks
    if not peaks:
        return
    if not isinstance(tolerancesByIsotope, dict | type(None)):
        raise TypeError('tolerancesByIsotope must be dict|None')
    if not isinstance(tolerancesByAxisCode, dict | type(None)):
        raise TypeError('tolerancesByAxisCode must be dict|None')
    if (tolerancesByIsotope is None and tolerancesByAxisCode is None):
        raise TypeError('Specify tolerancesByIsotope, tolerancesByAxisCode, or both')
    # if ((tolerancesByIsotope is not None and tolerancesByAxisCode is not None) or
    #         (tolerancesByIsotope is None and tolerancesByAxisCode is None)):
    #     raise TypeError('Specify one of tolerancesByIsotope or tolerancesByAxisCode')
    _copyPeakAssignmentsEntry(peaks,
                              tolerancesByIsotope=tolerancesByIsotope,
                              tolerancesByAxisCode=tolerancesByAxisCode)


def copyAssignments(peaks):
    """Propagate assignments - assignments are unified across all selected peaks.
    """
    from ccpn.framework.Application import getCurrent

    if not peaks:
        peaks = getCurrent().peaks
    if not peaks:
        return
    _copyPeakAssignmentsEntry(peaks)


def propagateAssignmentsFromReference(peaks, referencePeak,
                                      tolerancesByIsotope=None, tolerancesByAxisCode=None):
    """Propagate assignments - assignments are propagated from a reference-peak.
    To match the V2-propagateAssignments, always uses tolerances.

    Specify tolerancesByIsotope, tolerancesByAxisCode, or both.
    If an isotope-code or axis-code is not found then defaults to the spectrum assignment-tolerances for each peak.
    This can be achieved by setting either to an empty dict {}.
    Isotope-codes have priority over axis-codes.
    """
    from ccpn.framework.Application import getCurrent

    if not peaks:
        peaks = getCurrent().peaks
    if not peaks:
        return
    if not referencePeak:
        raise TypeError('referencePeak not specified')
    if not isinstance(tolerancesByIsotope, dict | type(None)):
        raise TypeError('tolerancesByIsotope must be dict|None')
    if not isinstance(tolerancesByAxisCode, dict | type(None)):
        raise TypeError('tolerancesByAxisCode must be dict|None')
    if (tolerancesByIsotope is None and tolerancesByAxisCode is None):
        raise TypeError('Specify tolerancesByIsotope, tolerancesByAxisCode, or both')
    # if ((tolerancesByIsotope is not None and tolerancesByAxisCode is not None) or
    #         (tolerancesByIsotope is None and tolerancesByAxisCode is None)):
    #     raise TypeError('Specify one of tolerancesByIsotope or tolerancesByAxisCode')
    _copyPeakAssignmentsEntry(peaks, referencePeak=referencePeak,
                              tolerancesByIsotope=tolerancesByIsotope,
                              tolerancesByAxisCode=tolerancesByAxisCode
                              )


def copyAssignmentsFromReference(peaks, referencePeak):
    """Copy assignments - assignments are copied from a reference-peak.
    """
    from ccpn.framework.Application import getCurrent

    if not peaks:
        peaks = getCurrent().peaks
    if not peaks:
        return
    if not referencePeak:
        raise TypeError('referencePeak not specified')
    _copyPeakAssignmentsEntry(peaks, referencePeak=referencePeak)
