"""Code for CCPN-specific NEF I/O
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2025-04-16 12:49:01 +0100 (Wed, April 16, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

# from copy import deepcopy
import random
import os
import sys
import time
import typing
import re
import pandas as pd
import json
from functools import partial
from collections import OrderedDict as OD, namedtuple
from collections.abc import MutableMapping

# from collections import Counter
from operator import attrgetter, itemgetter
from typing import List, Union, Optional, Sequence, Tuple
from ast import literal_eval

from ccpn.core.lib import Pid
from ccpn.core import _coreImportOrder

from ccpn.framework.lib.ccpnNef.CcpnNefCommon import nef2CcpnMap, saveFrameReadingOrder, _isALoop, \
    saveFrameWritingOrder, _parametersFromLoopRow, _traverse, _stripSpectrumName, _stripSpectrumSerial
from ccpn.core.lib.CcpnSorting import universalSortKey
from ccpn.util import Common as commonUtil
from ccpn.util import jsonIo
from ccpn.util.nef import Specification
from ccpn.util.nef import StarIo
from ccpn.util.isotopes import isotopeCode2Nucleus

from ccpnmodel.ccpncore.lib import Constants as coreConstants
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum, MAXALIASINGRANGE
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Complex import Complex
from ccpn.core.PeakList import PeakList
from ccpn.core.IntegralList import IntegralList
from ccpn.core.Integral import Integral
from ccpn.core.MultipletList import MultipletList
from ccpn.core.Multiplet import Multiplet
# from ccpn.core._PeakCluster import _PeakCluster
from ccpn.core.Peak import Peak
from ccpn.core.Sample import Sample
# from ccpn.core.SampleComponent import SampleComponent
from ccpn.core.Substance import Substance
from ccpn.core.Chain import Chain
from ccpn.core.Residue import Residue
from ccpn.core.Atom import Atom
from ccpn.core.NmrChain import NmrChain
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.ChemicalShiftList import ChemicalShiftList
# from ccpn.core.ChemicalShift import ChemicalShift
from ccpn.core.StructureData import StructureData
from ccpn.core.Data import Data
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.Note import Note
from ccpn.core.ViolationTable import ViolationTable
from ccpn.core.DataTable import DataTable
from ccpn.core.Collection import Collection
from ccpn.core.lib import SpectrumLib
from ccpn.core.lib.MoleculeLib import extraBoundAtomPairs
from ccpn.core.lib import RestraintLib
from ccpn.core.lib.ContextManagers import notificationEchoBlocking, apiNotificationBlanking

from ccpn.util.Logging import getLogger
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.AttrDict import AttrDict
from ccpn.util.nef.GenericStarParser import PARSER_MODE_STANDARD

from ccpn.framework.lib.ccpnNef.CcpnNefContent import CcpnNefContent


# Max value used for random integer. Set to be expressible as a signed 32-bit integer.
maxRandomInt = 2000000000

# Current NEF version (as float)
currentNefVersion = 1.1
# Lowest version that this reader can read (may not be the same), as float:
minimumNefVersion = 0.9

# TODO These should be consolidated with the same constants in NefIo
# (and likely those in ExportNefPopup) and likely replaced with a list of classes
CHAINS = 'chains'
CHEMICALSHIFTLISTS = 'chemicalShiftLists'
RESTRAINTTABLES = 'restraintTables'
PEAKLISTS = 'peakLists'
INTEGRALLISTS = 'integralLists'
MULTIPLETLISTS = 'multipletLists'
SAMPLES = 'samples'
SUBSTANCES = 'substances'
NMRCHAINS = 'nmrChains'
# DATASETS = 'dataSets'
STRUCTUREDATA = 'structureData'
COMPLEXES = 'complexes'
SPECTRUMGROUPS = 'spectrumGroups'
NOTES = 'notes'
# _PEAKCLUSTERS = '_peakClusters'
VIOLATIONTABLES = 'violationTables'
DATATABLES = 'dataTables'
COLLECTIONS = 'collections'

POSITIONCERTAINTY = 'position_uncertainty_'
POSITIONCERTAINTYLEN = len(POSITIONCERTAINTY)

DEFAULTRESTRAINTLINKLOAD = False

REGEXREMOVEENDQUOTES = r'\`\d*`+?'
REGEXPREFIXQUOTEDNUMBER = r'^\`(\d+)\`'
REGEXPOSTFIXQUOTEDNUMBER = r'\`(\d+)\`$'
# REGEXCHECKNMRATOM = r'^\?\@\d+$|^\w+\@\d+$'
REGEXCHECKNMRATOM = r'^\?\@\d+$|^\w+\%?\*?\%?\@\d+$'

NEFEXTENSION = '.nef'

DEFAULTUPDATEPARAMETERS = ('comment',)

# NAMETOOBJECTMAPPING = {obj.className.lower(): obj for obj in (Project, Spectrum, SpectrumGroup, Complex, PeakList,
#                                                               IntegralList, MultipletList, _PeakCluster, Sample,
#                                                               Substance, Chain, NmrChain, ChemicalShiftList, StructureData,
#                                                               RestraintTable, Note)}

NAMETOOBJECTMAPPING = {'nef_chemical_shift_list'               : ChemicalShiftList,
                       'ccpn_spectrum_group'                   : SpectrumGroup,
                       'nef_nmr_spectrum'                      : PeakList,
                       'integral'                              : IntegralList,
                       'multiplet'                             : MultipletList,
                       # 'ccpn_peak_cluster_list'                : _PeakCluster,
                       'ccpn_sample'                           : Sample,
                       'ccpn_complex'                          : Complex,
                       'ccpn_substance'                        : Substance,
                       'nef_molecular_system'                  : Chain,
                       'ccpn_assignment'                       : NmrChain,
                       'nef_distance_restraint_list'           : RestraintTable,
                       'nef_dihedral_restraint_list'           : RestraintTable,
                       'nef_rdc_restraint_list'                : RestraintTable,
                       'ccpn_restraint_list'                   : RestraintTable,
                       'ccpn_distance_restraint_violation_list': ViolationTable,
                       'ccpn_dihedral_restraint_violation_list': ViolationTable,
                       'ccpn_rdc_restraint_violation_list'     : ViolationTable,
                       'ccpn_datatable'                        : DataTable,
                       'ccpn_dataset'                          : StructureData,
                       'ccpn_collections'                      : Collection,
                       'ccpn_notes'                            : Note,
                       '_nef_spectrum'                         : Spectrum,
                       }

DATANAME = 'ccpn_structuredata_name'
DATANAME_DEFAULT = 'structureFromNef'
DATANAME_DEPRECATED = 'ccpn_dataset_id'
SHIFTNAME = 'chemical_shift_list'

deferredItem = namedtuple('deferredItem', 'func spectrum loop saveFrame peakListId')

CONTENTATTR = '_content'
ROWERRORATTR = '_rowErrors'


def mergeDict(dict1: MutableMapping, dict2: MutableMapping):
    """Merge right-hand dict into the left-hand dict (dict2 into dict1).
    Merge is performed inplace.
     - Keep unique keys from left-hand dict.
     - Overwrite existing keys with value from right-hand dict.
     - Adds new keys from right-hand dict.

    :param dict1: original dict
    :param dict2: new dict to merge
    :return: updated dict
    """
    if not isinstance(dict1, MutableMapping):
        raise TypeError('mergeDict: dict1 must be compatible with collections.abc.MutableMapping, e.g., a dict')
    if not isinstance(dict2, MutableMapping):
        raise TypeError('mergeDict: dict2 must be compatible with collections.abc.MutableMapping, e.g., a dict')

    def _merge(d1: MutableMapping, d2: MutableMapping):
        """Perform recursive merge of the dicts
        """
        if not isinstance(d1, MutableMapping):
            return d2

        for k, val in d2.items():
            d1[k] = _merge(d1.get(k, {}), val) if isinstance(val, MutableMapping) else val

        return d1

    return _merge(dict1, dict2)


# NEf to CCPN tag mapping (and tag order)
#
# Contents are:
# Nef2CcpnMap = {saveframe_or_loop_category:contents}
# contents = {tag:ccpn_tag_or_None}
# loopMap = {tag:ccpn_tag}
#
# Loops are entered as saveFrame contents with their category as tag and 'ccpn_tag' None
# and at the top level under their category name
# This relies on loop categories being unique, both at the top level, and among the item
# names within a saveframe

# Sentinel value - MUST evaluate as False

# This dictionary is used directly to control what is read from and written to
# NEF. The top level keys are the tags for saveframes and loops, which must
# either have their own entries in the Reader 'imprters' dictionary, of (if loops)
# be read directly by the parent samveframe).
# The next level down desceibes saveframe attributes or loop elements.
#
# Each saveframe or loop row matches a wrapper object, and the nef2CcpnMap map
# is used to read and write starting at that object.
# There are several variants. Using nef_sequence as an example:
#
# ('residue_name','residueType') means that the NEF value is read AND written
#  to residue.residueType.
#
# ('chain_code','chain.shortName') means that the NEF value is set (for writing) automatically,
# but the code for reading from NEF and passing it into the project must be done by hand
#
# ('cis_peptide',None), means that the tag exists, but that both on reading and writing it
# must be handled  explicitly.
#
# values _isALoop have an obvious meaning
#
# Note the _parametersFromSaveFrame and _parametersFromLoopRow functions
# that make a parameters dictionary (for use in object creation), using these mappings


def saveNefProject(project: Project,
                   path: str,
                   overwriteExisting: bool = False,
                   skipPrefixes: typing.Sequence = (),
                   expandSelection: bool = True,
                   includeOrphans: bool = False):
    """Save project NEF file to path"""

    dirPath, fileName = os.path.split(path)
    if not fileName:
        # we got a directory - derive filename from project
        fileName = project.name + '.nef'

    filePath = os.path.join(dirPath, fileName)

    if os.path.exists(filePath) and not overwriteExisting:
        raise IOError("%s already exists" % filePath)

    text = convert2NefString(project, skipPrefixes=skipPrefixes,
                             expandSelection=expandSelection,
                             includeOrphans=includeOrphans)

    if dirPath and not os.path.isdir(dirPath):
        os.makedirs(dirPath)

    open(filePath, 'w').write(text)


def exportNef(project: Project,
              path: str,
              overwriteExisting: bool = False,
              skipPrefixes: typing.Sequence = (),
              expandSelection: bool = True,
              includeOrphans: bool = False,
              # exclusionDict={},
              pidList: typing.Sequence = None):
    """export NEF file to path"""

    path = str(path)

    if path[-4:] != '.nef':
        path = path + '.nef'
        getLogger().debug('Adding .nef extension to filename %s' % path)

    if os.path.exists(path) and not overwriteExisting:
        raise IOError("%s already exists" % path)

    text = convert2NefString(project, skipPrefixes=skipPrefixes,
                             expandSelection=expandSelection,
                             includeOrphans=includeOrphans,
                             pidList=pidList)  #, exclusionDict=exclusionDict)

    dirPath, fileName = os.path.split(path)
    if dirPath and not os.path.isdir(dirPath):
        os.makedirs(dirPath)

    with open(path, 'w') as f:  # save write
        f.write(text)


def convertToDataBlock(project: Project,
                       # path:str,
                       # overwriteExisting:bool=False,
                       skipPrefixes: typing.Sequence = (),
                       expandSelection: bool = True,
                       includeOrphans: bool = False,
                       # exclusionDict={},
                       pidList: typing.Sequence = None):
    """export NEF file to path"""
    # ejb - dialog added to allow the changing of the name from the current project name.

    dataBlock = convertToCcpnDataBlock(project, skipPrefixes=skipPrefixes,
                                       expandSelection=expandSelection,
                                       includeOrphans=includeOrphans,
                                       pidList=pidList)  #, exclusionDict=exclusionDict)

    return dataBlock


def writeDataBlock(dataBlock, path: str, overwriteExisting: bool = False):
    if path[-4:] != '.nef':
        path = path + '.nef'
        getLogger().debug('Adding .nef extension to filename %s' % path)

    if os.path.exists(path) and not overwriteExisting:
        raise IOError("%s already exists" % path)

    dirPath, fileName = os.path.split(path)
    if dirPath and not os.path.isdir(dirPath):
        os.makedirs(dirPath)

    with open(path, 'w') as f:  # save write
        f.write(dataBlock.toString())


def convert2NefString(project: Project, skipPrefixes: typing.Sequence = (), expandSelection: bool = True, includeOrphans: bool = False,
                      pidList: list = None):  #, exclusionDict:dict={}):
    """Convert project to NEF string"""

    converter = CcpnNefWriter(project)

    dataBlock = converter.exportProject(expandSelection=expandSelection, includeOrphans=includeOrphans, pidList=pidList)  #, exclusionDict=exclusionDict)

    # Delete tags starting with certain prefixes.
    # NB designed to strip out 'ccpn' tags to make output comparison easier
    for prefix in skipPrefixes:
        # Could be done faster, but this is a rare operation
        for sftag in list(dataBlock.keys()):
            if sftag.startswith(prefix):
                del dataBlock[sftag]
            else:
                sf = dataBlock[sftag]
                for tag in list(sf.keys()):
                    if tag.startswith(prefix):
                        del sf[tag]
                    else:
                        val = sf[tag]
                        if isinstance(val, StarIo.NmrLoop):
                            # This is a loop:
                            for looptag in val.columns:
                                # NB val.columns is a tuple (encapsulation) and will not change during the loop
                                if looptag.startswith(prefix):
                                    val.removeColumn(looptag, removeData=True)

    return dataBlock.toString()


def convertToCcpnDataBlock(project: Project, skipPrefixes: typing.Sequence = (), expandSelection: bool = True, includeOrphans: bool = False,
                           pidList: list = None):  #, exclusionDict:dict={}):
    """Convert project to NEF string"""

    converter = CcpnNefWriter(project)

    dataBlock = converter.exportProject(expandSelection=expandSelection, includeOrphans=includeOrphans, pidList=pidList)  #, exclusionDict=exclusionDict)

    # Delete tags starting with certain prefixes.
    # NB designed to strip out 'ccpn' tags to make output comparison easier
    for prefix in skipPrefixes:
        # Could be done faster, but this is a rare operation
        for sftag in list(dataBlock.keys()):
            if sftag.startswith(prefix):
                del dataBlock[sftag]
            else:
                sf = dataBlock[sftag]
                for tag in list(sf.keys()):
                    if tag.startswith(prefix):
                        del sf[tag]
                    else:
                        val = sf[tag]
                        if isinstance(val, StarIo.NmrLoop):
                            # This is a loop:
                            for looptag in val.columns:
                                # NB val.columns is a tuple (encapsulation) and will not change during the loop
                                if looptag.startswith(prefix):
                                    val.removeColumn(looptag, removeData=True)

    return dataBlock


def _tryNumber(value):
    if isinstance(value, str):
        ll = value.rsplit('`', 2)
        if len(ll) == 3:
            # name is of form abc`xyz`
            try:
                return int(ll[1])
            except ValueError:
                pass


_nameFromCategory = namedtuple('_nameFromCategory', ('framecode', 'frameName', 'subname', 'prefix', 'postfix', 'precode', 'postcode', 'category'))


def _saveFrameNameFromCategory(saveFrame: StarIo.NmrSaveFrame):
    """Parse the saveframe name to extract pre- and post- numbering
    necessary for restraint and spectrum saveframe names
    """
    category = saveFrame['sf_category']
    framecode = saveFrame['sf_framecode']
    # frameName = framecode[len(category) + 1:]
    return _getNameFromCategory(category, framecode)


def _getNameFromCategory(category, framecode):
    # check for any occurrences of `n` in the saveframe name and keep for later reference
    frameName = framecode[len(category) + 1:]

    names = re.split(REGEXREMOVEENDQUOTES, frameName)
    if 0 <= len(names) > 3:
        raise TypeError('bad splitting of saveframe name {}'.format(framecode))
    subName = re.sub(REGEXREMOVEENDQUOTES, '', frameName)
    matches = [mm for mm in re.finditer(REGEXREMOVEENDQUOTES, frameName)]
    prefix = matches[0].group() if matches and matches[0] and matches[0].span()[0] == 0 else ''
    preSerial = _tryNumber(prefix)
    postfix = matches[-1].group() if matches and matches[-1] and matches[-1].span()[1] == len(frameName) else ''
    postSerial = _tryNumber(postfix)

    return _nameFromCategory(framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category)


class CcpnNefWriter:
    """CCPN NEF reader/writer"""

    def __init__(self, project: Project, specificationFile: str = None, mode: str = 'strict',
                 programName: str = None, programVersion: str = None):
        self.project = project
        self.mode = mode
        if specificationFile is None:
            self.specification = None
        else:
            # NBNB TBD reconsider whether we want the spec summary or something else
            self.specification = Specification.getCcpnSpecification(specificationFile)

        if hasattr(project, 'application'):
            programName = programName or project.application.applicationName
            programVersion = programVersion or project.application.applicationVersion
        self.programName = programName or 'CcpnNefWriter'
        self.programVersion = programVersion
        self.ccpn2SaveFrameName = {}

    def exportObjects(self,
                      expandSelection: bool = True,
                      includeOrphans: bool = False,
                      chains: typing.Sequence[Chain] = (),
                      chemicalShiftLists: typing.Sequence[ChemicalShiftList] = (),
                      restraintTables: typing.Sequence[RestraintTable] = (),
                      peakLists: typing.Sequence[PeakList] = (),
                      integralLists: typing.Sequence[IntegralList] = (),
                      multipletLists: typing.Sequence[MultipletList] = (),
                      samples: typing.Sequence[Sample] = (),
                      substances: typing.Sequence[Substance] = (),
                      nmrChains: typing.Sequence[NmrChain] = (),
                      structureData: typing.Sequence[StructureData] = (),
                      complexes: typing.Sequence[Complex] = (),
                      spectrumGroups: typing.Sequence[SpectrumGroup] = (),
                      notes: typing.Sequence[Note] = (),
                      # peakClusters: typing.Sequence[_PeakCluster] = (),
                      violationTables: typing.Sequence[ViolationTable] = (),
                      dataTables: typing.Sequence[DataTable] = (),
                      collections: typing.Sequence[Collection] = (),
                      ):
        """Export objects passed in and objects they are linked to.

            if expandSelection is True (strongly recommended):
            Will add PeakLists (Spectra) from SpectrumGroups (first peakList only),
            Samples and ChemicalShiftLists from peakLists (Spectra)
            Samples from SpectrumHits,
            Substances from Samples
            RestraintTables from StructureData
            NmrChains from ChemicalShifts
            and Chains from Substances, SampleComponents, NmrChains, and Complexes"""

        # set-up
        self.ccpn2SaveFrameName = {}
        saveFrames = []
        project = self.project

        if expandSelection:
            # Add linked-to objects - we can not skip these without altering the data:

            # SpectrumGroups and PeakLists
            peakLists = list(peakLists)
            integralLists = list(integralLists)
            multipletLists = list(multipletLists)

            spectrumSet = set(x.spectrum for x in peakLists)
            for spectrumGroup in spectrumGroups:
                for spectrum in spectrumGroup.spectra:
                    if spectrum not in spectrumSet:
                        spectrumSet.add(spectrum)

                        pl = spectrum.peakLists
                        if pl:
                            # Add one of the peakLists
                            peakLists.append(pl[0])
                        else:
                            peakLists.append(spectrum.newPeakList())

                        il = spectrum.integralLists
                        if il:
                            # Add one of the peakLists
                            integralLists.append(il[0])
                        else:
                            integralLists.append(spectrum.newIntegralList())

                        ml = spectrum.multipletLists
                        if ml:
                            # Add one of the peakLists
                            multipletLists.append(ml[0])
                        else:
                            multipletLists.append(spectrum.newMultipletList())
            peakLists = sorted(peakLists)
            integralLists = sorted(integralLists)
            multipletLists = sorted(multipletLists)

            # # PeakClusters
            # peakClusterLists = set(peakClusters)
            # for peakCluster in peakClusterLists:
            #     peakClusterLists.add(peakCluster)
            # peakClusterLists = sorted(peakClusters)

            # ChemicalShiftLists
            chemicalShiftListSet = set(chemicalShiftLists)
            for peakList in peakLists:
                xx = peakList.chemicalShiftList
                if xx is None:
                    raise ValueError(
                            "PeakList %s has no ChemicalShiftList attached and cannot be exported to NEF")
                else:
                    chemicalShiftListSet.add(xx)
            chemicalShiftLists = sorted(chemicalShiftListSet)

            # Samples
            sampleSet = set(samples)
            for spectrum in spectrumSet:
                sample = spectrum.sample
                if sample is not None:
                    sampleSet.add(sample)
                for spectrumHit in spectrum.spectrumHits:
                    sample = spectrumHit.sample
                    if sample is not None:
                        sampleSet.add(sample)
            samples = sorted(sampleSet)

            # restraintLists
            restraintListSet = set(restraintTables)
            for dSet in structureData:
                restraintListSet.update(dSet.restraintTables)
            restraintTables = sorted(restraintListSet)

            # ChemicalShiftLists and NmrChains
            nmrChainSet = set(nmrChains)
            for chemicalShiftList in chemicalShiftLists:
                for chemicalShift in chemicalShiftList.chemicalShifts:
                    if chemicalShift.nmrAtom:
                        nmrChainSet.add(chemicalShift.nmrAtom.nmrResidue.nmrChain)
            nmrChains = sorted(nmrChainSet)

            # NmrChains and Chains
            chainSet = set(chains)
            for nmrChain in nmrChains:
                chain = nmrChain.chain
                if chain is not None:
                    chainSet.add(chain)

            # Complexes and Chains
            for cmplx in complexes:
                chainSet.update(cmplx.chains)

            # Samples, Substances and Chains
            substanceSet = set(substances)
            for sample in samples:
                for sampleComponent in sample.sampleComponents:
                    substance = sampleComponent.substance
                    if substance is not None:
                        substanceSet.add(substance)
                    # chain = sampleComponent.chain
                    # if chain is not None:
                    #     chainSet.add(chain)
            substances = sorted(substanceSet)

            # Substances and Chains
            for substance in substances:
                for chain in substance.chains:  # ejb - modified
                    if chain is not None:
                        chainSet.add(chain)
            chains = sorted(chainSet)

        # MetaData
        saveFrames.append(self.makeNefMetaData(project))

        # ccpnLogging
        saveFrameList = self.ccpnLogging2Nef(project)
        if saveFrameList:
            saveFrames.extend(saveFrameList)

        # Chains
        saveFrames.append(self.chains2Nef(sorted(chains)))

        # CCPN assignment
        saveFrames.append(self.ccpnAssignentToNef(nmrChains))

        # ChemicalShiftLists
        for obj in sorted(chemicalShiftLists):
            saveFrames.append(self.chemicalShiftList2Nef(obj, includeOrphans))

        # Create Samples - create first otherwise ccpn2SaveFrameName not populated correctly :|
        sampleFrames = [self.sample2Nef(obj) for obj in sorted(samples)]

        # RestraintLists and
        restraintTables = sorted(restraintTables, key=attrgetter('restraintType', 'serial'))
        singleStructureTable = bool(restraintTables) and len(set(x.structureData for x in restraintTables)) == 1
        for obj in restraintTables:
            saveFrames.append(self.restraintTable2Nef(obj, singleStructureTable=singleStructureTable))

        # NOTE:ED - need to make an active list of spectra and export from there with the required
        #           PeakLists/IntegralLists/MultipletLists

        # Spectra/PeakLists/IntegralLists/MultipletLists
        _exportedSpectra = OrderedSet()
        for obj in sorted(peakLists + integralLists + multipletLists):
            _exportedSpectra.add(obj.spectrum)

        # for spectrum in _exportedSpectra:
        #     saveFrames.append(self.peakList2Nef(spectrum, peakLists, integralLists, multipletLists, True))

        spectrumList = OD()
        for obj in sorted(peakLists):
            if obj.spectrum not in spectrumList:
                spectrumList[obj.spectrum] = {'peakLists'     : OrderedSet([obj]),
                                              'integralLists' : OrderedSet(),
                                              'multipletLists': OrderedSet()
                                              }
            else:
                spectrumList[obj.spectrum]['peakLists'].add(obj)
        for obj in sorted(integralLists):
            if obj.spectrum not in spectrumList:
                spectrumList[obj.spectrum] = {'peakLists'     : OrderedSet(),
                                              'integralLists' : OrderedSet([obj]),
                                              'multipletLists': OrderedSet()
                                              }
            else:
                spectrumList[obj.spectrum]['integralLists'].add(obj)
        for obj in sorted(multipletLists):
            if obj.spectrum not in spectrumList:
                spectrumList[obj.spectrum] = {'peakLists'     : OrderedSet(),
                                              'integralLists' : OrderedSet(),
                                              'multipletLists': OrderedSet([obj])
                                              }
            else:
                spectrumList[obj.spectrum]['multipletLists'].add(obj)

        for spectrum, listObjs in spectrumList.items():
            peakLists, integralLists, multipletLists = listObjs['peakLists'], listObjs['integralLists'], listObjs['multipletLists']
            if len(peakLists) > 0:
                for peaklistNum, peakList in enumerate(peakLists):
                    saveFrames.append(self.peakList2Nef(spectrum, peakList, peakLists, integralLists, multipletLists, exportCompleteSpectrum=(peaklistNum == 0),
                                                        peakListSerial=peakList.serial))
            else:
                saveFrames.append(self.peakList2Nef(spectrum, None, peakLists, integralLists, multipletLists, exportCompleteSpectrum=True, peakListSerial=1))

        # # Spectra/PeakLists/IntegralLists/MultipletLists
        # for obj in sorted(peakLists + integralLists + multipletLists):
        #     saveFrames.append(self.peakList2Nef(obj.spectrum, peakList, peakLists, integralLists, multipletLists, obj.spectrum not in _exportedSpectra))
        #     _exportedSpectra.add(obj.spectrum)

        # restraint-peak links
        saveFrame = self.peakRestraintLinks2Nef(restraintTables)
        if saveFrame:
            saveFrames.append(saveFrame)

        # Now add CCPN-specific data:

        # TODO temporarily blanked out, pending bug fixes
        # # NmrChains
        # saveFrames.append(self.assignments2Nef(project))

        # SpectrumGroups
        for obj in project.spectrumGroups:
            saveFrames.append(self.spectrumGroup2Nef(obj))

        # # PeakClusters
        # saveFrame = self.peakClusters2Nef(sorted(peakClusters))
        # if saveFrame:
        #     saveFrames.append(saveFrame)

        # Samples
        saveFrames.extend(sampleFrames)

        # Substances
        for obj in sorted(substances):
            saveFrames.append(self.substance2Nef(obj))

        # Complexes
        for obj in project.complexes:
            saveFrames.append(self.complex2Nef(obj))

        # structureData
        if structureData:
            saveFrames.extend(self.structureData2Nef(sorted(structureData)))

        # Notes
        saveFrame = self.notes2Nef(project, sorted(notes))
        if saveFrame:
            saveFrames.append(saveFrame)

        # # violation tables
        # if project.violationTables:
        #     if (found := self.violationTables2Nef(project)):
        #         saveFrames.extend(found)

        # RestraintLists and
        violationTables = sorted(violationTables)
        singleStructureTable = bool(violationTables) and len(set(x.structureData for x in violationTables)) == 1
        for obj in violationTables:
            saveFrames.append(self.violationTable2Nef(obj, singleStructureTable=singleStructureTable))

        # data tables
        for dataTable in sorted(dataTables):
            if (found := self.dataTable2Nef(project, dataTable)):
                saveFrames.append(found)

        # collections
        if (found := self.collections2Nef(project, sorted(collections))):
            saveFrames.append(found)

        # Additional data
        saveFrame = self.additionalData2Nef(project)
        if saveFrame:
            saveFrames.append(saveFrame)

        # make and return dataBlock with saveframes in export order
        result = StarIo.NmrDataBlock(name=self.project.name)
        for saveFrame in self._saveFrameNefOrder(saveFrames):
            result.addItem(saveFrame['sf_framecode'], saveFrame)
        #
        return result

    def exportDataSet(self, dataSet: StructureData) -> StarIo.NmrDataBlock:
        """Get dataSet and all objects linked to therein as NEF object tree for export"""

        saveFrames = list()

        saveFrames.append(self.makeNefMetaData(dataSet))

        # etc.

        # make and return dataBlock with saveframes in export order
        result = StarIo.NmrDataBlock(name=dataSet.name)
        for saveFrame in self._saveFrameNefOrder(saveFrames):
            result.addItem(saveFrame['sf_framecode'], saveFrame)
        #
        return result

    # def exportProject(self, expandSelection:bool=False,
    #                   pidList:list=None,
    #                   exclusionDict:dict=None) -> typing.Optional[StarIo.NmrDataBlock]:
    def exportProject(self, expandSelection: bool = False, includeOrphans: bool = False,
                      pidList: list = None) -> typing.Optional[StarIo.NmrDataBlock]:
        """
        Get project and all contents as NEF object tree for export
        """
        project = self.project

        # ejb - added items to be removed from the list
        # gets a copy of all the lists in the project that are relevant to Nef files

        # assume that a list of pids to include is being passed in
        # if there is none

        if pidList is None:
            # use as a flag to export everything

            return self.exportObjects(expandSelection=expandSelection,
                                      includeOrphans=includeOrphans,
                                      chains=project.chains, chemicalShiftLists=project.chemicalShiftLists,
                                      restraintTables=project.restraintTables, peakLists=project.peakLists,
                                      integralLists=project.integralLists, multipletLists=project.multipletLists,
                                      samples=project.samples, substances=project.substances,
                                      nmrChains=project.nmrChains, structureData=project.structureData,
                                      complexes=project.complexes, spectrumGroups=project.spectrumGroups,
                                      notes=project.notes,
                                      # peakClusters=project.peakClusters,
                                      violationTables=project.violationTables, dataTables=project.dataTables,
                                      collections=project.collections)
        else:
            # export selection of objects
            # either everything minus the exclusionDict or the list of pids
            # if pidList is not None and exclusionDict is not None:
            #   lists must be mutually exclusive
            # return None

            self.chains = []
            self.chemicalShiftLists = []
            self.restraintTables = []
            self.peakLists = []
            self.integralLists = []
            self.multipletLists = []
            self.samples = []
            self.substances = []
            self.nmrChains = []
            self.structureData = []
            self.complexes = []
            self.spectrumGroups = []
            self.notes = []
            # self._peakClusters = []
            self.violationTables = []
            self.dataTables = []
            self.collections = []

            checkList = [CHAINS, CHEMICALSHIFTLISTS, RESTRAINTTABLES, PEAKLISTS,
                         INTEGRALLISTS, MULTIPLETLISTS,
                         SAMPLES, SUBSTANCES, NMRCHAINS,
                         STRUCTUREDATA, COMPLEXES, SPECTRUMGROUPS, NOTES,
                         # _PEAKCLUSTERS,
                         VIOLATIONTABLES, DATATABLES, COLLECTIONS]

            # put the pids in the correct lists
            for name in checkList:
                attrib = getattr(self, name)
                for aPid in pidList:
                    pidObj = project.getByPid(aPid)
                    if pidObj is not None and pidObj._pluralLinkName == name:  # need to check this
                        attrib.append(pidObj)

                # if name in exclusionDict:        # if not in list then still write all values
                #   # setattr(self, name, [])           # make it an empty list
                #   attrib = getattr(self, name)
                #   for obj in getattr(project, name):
                #     if obj.pid in exclusionDict[name]:
                #       # attrib.append(obj)              # append the found items to the list
                #       attrib.remove(obj)            # treat as exclusion list

            return self.exportObjects(expandSelection=expandSelection,
                                      includeOrphans=includeOrphans,
                                      chains=self.chains, chemicalShiftLists=self.chemicalShiftLists,
                                      restraintTables=self.restraintTables, peakLists=self.peakLists,
                                      integralLists=self.integralLists, multipletLists=self.multipletLists,
                                      samples=self.samples, substances=self.substances,
                                      nmrChains=self.nmrChains, structureData=self.structureData,
                                      complexes=self.complexes, spectrumGroups=self.spectrumGroups,
                                      notes=self.notes,
                                      # peakClusters=self.peakClusters,
                                      violationTables=self.violationTables, dataTables=self.dataTables,
                                      collections=self.collections
                                      )

        # self.ccpn2SaveFrameName = {}
        # saveFrames = []
        #
        # project = self.project
        #
        # # MetaData
        # saveFrames.append(self.makeNefMetaData(project))
        #
        # # Chains
        # saveFrames.append(self.chains2Nef(sorted(project.chains)))
        #
        # # ChemicalShiftLists
        # for obj in sorted(project.chemicalShiftLists):
        #     saveFrames.append(self.chemicalShiftList2Nef(obj))
        #
        # # RestraintLists and
        # restraintLists = sorted(project.restraintTables,
        #                         key=attrgetter('restraintType', 'serial'))
        # singleStructureData = bool(restraintLists) and len(set(x.structureData for x in restraintLists)) == 1
        # for obj in restraintLists:
        #     saveFrames.append(self.restraintTable2Nef(obj, singleStructureData=singleStructureData))
        #
        # # Spectra
        # for obj in sorted(project.spectra):
        #     # NB we get multiple saveframes, one per peakList
        #     saveFrames.extend(self.spectrum2Nef(obj))
        #
        # # restraint-peak links
        # saveFrame = self.peakRestraintLinks2Nef(restraintLists)
        # if saveFrame:
        #     saveFrames.append(saveFrame)
        #
        # # Now add CCPN-specific data:
        #
        # # PeakClusters
        # saveFrames.append(self.peakClusters2Nef(project))
        #
        # # NmrChains
        # saveFrames.append(self.assignments2Nef(project))
        #
        # # SpectrumGroups
        # for obj in project.spectrumGroups:
        #     saveFrames.append(self.spectrumGroup2Nef(obj))
        #
        # # Samples
        # for obj in sorted(project.samples):
        #     saveFrames.append(self.sample2Nef(obj))
        #
        # # Substances
        # for obj in sorted(project.substances):
        #     saveFrames.append(self.substance2Nef(obj))
        #
        # # # StructureData - NB does not include RestraintLists, which are given above
        # # for obj in project.structureData:
        # #   saveFrames.append(self.structureData2Nef(obj))
        #
        # # Notes
        # saveFrame = self.notes2Nef(sorted(project.notes))
        # if saveFrame:
        #     saveFrames.append(saveFrame)
        #
        # # Additional data
        # saveFrame = self.additionalData2Nef(project)
        # if saveFrame:
        #     saveFrames.append(saveFrame)
        #
        # # make and return dataBlock with saveframes in export order
        # result = StarIo.NmrDataBlock(name=self.project.name)
        # for saveFrame in self._saveFrameNefOrder(saveFrames):
        #     result.addItem(saveFrame['sf_framecode'], saveFrame)
        # #
        # return result

    def makeNefMetaData(self, headObject: Union[Project, StructureData],
                        coordinateFileName: str = None) -> StarIo.NmrSaveFrame:
        """make NEF metadata saveframe from Project"""

        # NB No attributes can be set from map here, so we do not try

        category = 'nef_nmr_meta_data'
        result = self._newNefSaveFrame(headObject, category, category)

        # NBNB TBD FIXME add proper values for format version from specification file
        result['format_name'] = 'nmr_exchange_format'
        result['format_version'] = currentNefVersion
        # format_version=None
        result['coordinate_file_name'] = coordinateFileName
        if headObject.className == 'Project':
            result['program_name'] = self.programName
            result['program_version'] = self.programVersion
            result['creation_date'] = timeStamp = commonUtil.getTimeStamp()
            result['uuid'] = '%s-%s-%s' % (self.programName, timeStamp, random.randint(0, maxRandomInt))

            # This loop is only set when exporting StructureData
            del result['nef_related_entries']
            # This loop is only set when exporting StructureData
            del result['nef_run_history']

            loop = result['nef_program_script']
            loop.newRow(dict(program_name='CcpNmr', script_name='exportProject'))

        else:
            assert headObject.className == 'DataSet', "Parameter must be a Project or DataSet"
            result['program_name'] = headObject.programName
            result['program_version'] = headObject.programVersion
            result['creation_date'] = headObject.creationDate
            result['uuid'] = headObject.uuid

            # NBNB TBD FIXME nef_related_entries is still to be implemented
            del result['nef_related_entries']

            loop = result['nef_run_history']
            # NBNB TBD FIXME nef_run_history is still to be wrapped
            del result['nef_run_history']
        #
        return result

    def chains2Nef(self, chains: List[Chain]) -> StarIo.NmrSaveFrame:
        """Convert selected Chains to CCPN NEF saveframe"""

        category = 'nef_molecular_system'
        if chains:
            project = chains[0].project
            result = self._newNefSaveFrame(project, category, category)

            loopName = 'nef_sequence'
            loop = result[loopName]

            index = 0
            for chain in chains:
                for residue in sorted(chain.residues):
                    index += 1
                    rowdata = self._loopRowData(loopName, residue)
                    rowdata['index'] = index
                    loop.newRow(rowdata)

            loop = result['nef_covalent_links']
            columns = ('chain_code_1', 'sequence_code_1', 'residue_name_1', 'atom_name_1',
                       'chain_code_2', 'sequence_code_2', 'residue_name_2', 'atom_name_2'
                       )

            boundAtomPairs = extraBoundAtomPairs(project, selectSequential=False)

            if boundAtomPairs:
                for atom1, atom2 in boundAtomPairs:
                    if atom1.residue.chain in chains and atom2.residue.chain:
                        loop.newRow(dict(zip(columns, (atom1._idTuple + atom2._idTuple))))
            else:
                del result['nef_covalent_links']
            #
            return result

        else:
            return self._newNefSaveFrame(None, category, category)

    # def peakClusters2Nef(self, peakClusters) -> StarIo.NmrSaveFrame:
    #     """Convert PeakClusters to saveframe"""
    #
    #     category = 'ccpn_peak_cluster_list'
    #     if peakClusters:
    #         result = self._newNefSaveFrame(peakClusters[0].project, category, category)
    #
    #         loopName = 'ccpn_peak_cluster'
    #         loop = result[loopName]
    #         for peakCluster in sorted(peakClusters[0].project.peakClusters):
    #             row = loop.newRow(self._loopRowData(loopName, peakCluster))
    #             row['serial'] = peakCluster.serial
    #
    #         loopName = 'ccpn_peak_cluster_peaks'
    #         loop = result[loopName]
    #         for peakCluster in sorted(peakClusters[0].project.peakClusters):
    #
    #             for peak in peakCluster.peaks:
    #                 row = loop.newRow(self._loopRowData(loopName, peak))
    #                 row['peak_cluster_serial'] = peakCluster.serial
    #                 row['peak_spectrum'] = peak.peakList.spectrum.name
    #                 row['peak_list_serial'] = peak.peakList.serial
    #                 row['peak_serial'] = peak.serial
    #                 # row['peak_pid'] = peak.pid
    #         return result

    def assignments2Nef(self, project: Project) -> StarIo.NmrSaveFrame:
        """Convert NmrChains, NmrResidues and NmrAtoms to saveframe"""

        category = 'ccpn_assignment'
        result = self._newNefSaveFrame(project, category, category)

        nmrChainLoopName = 'nmr_chain'
        nmrChainLoop = result[nmrChainLoopName]
        nmrResidueLoopName = 'nmr_residue'
        nmrResidueLoop = result[nmrResidueLoopName]
        nmrAtomLoopName = 'nmr_atom'
        nmrAtomLoop = result[nmrAtomLoopName]

        for nmrChain in sorted(project.nmrChains):
            rowdata = self._loopRowData(nmrChainLoopName, nmrChain)
            rowdata['serial'] = nmrChain.serial
            nmrChainLoop.newRow(rowdata)

            # Use sorting - should give correct results
            for nmrResidue in sorted(nmrChain.nmrResidues):
                rowdata = self._loopRowData(nmrResidueLoopName, nmrResidue)
                rowdata['serial'] = nmrResidue.serial
                rowdata['residue_name'] = nmrResidue.residueType or None
                nmrResidueLoop.newRow(rowdata)

                for nmrAtom in sorted(nmrResidue.nmrAtoms):
                    rowdata = self._loopRowData(nmrAtomLoopName, nmrAtom)
                    rowdata['serial'] = nmrAtom.serial
                    nmrAtomLoop.newRow(rowdata)
        #
        return result

    def _sortingShifts(self, shift, order=True):
        """Sort the shifts according to nmrAtom.id or own pid if all Nones

        :param shift: chemical shift to be sorted
        :param order: True/False, if True undefined will always be at the bottom of the list
        :return:
        """
        # ChainCodes may be before/after 'CS' in list
        # Prefixed bool forces undefined to bottom of list by pid
        # For the purposes of sorting, pads all numbers to an 8-chr fixed-width field, if prefix is the same, should then sort numerically
        val = tuple(re.sub(r'(\d+)', lambda gr: str(gr.group()).zfill(8), str(vv)) for vv in (shift.chainCode, shift.sequenceCode, shift.residueType, shift.atomName))
        if all(vv is None for vv in val):
            val = (order,) + tuple(re.sub(r'(\d+)', lambda gr: str(gr.group()).zfill(8), str(vv)) for vv in shift.pid._split())
        else:
            val = (not order,) + val

        return val

    def chemicalShiftList2Nef(self, chemicalShiftList: ChemicalShiftList, includeOrphans: bool = False) -> StarIo.NmrSaveFrame:
        """Convert ChemicalShiftList to CCPN NEF saveframe"""

        from ccpn.core.ChemicalShiftList import CS_CHAINCODE, CS_SEQUENCECODE, CS_RESIDUETYPE, CS_ATOMNAME

        # Set up frame
        category = 'nef_chemical_shift_list'
        result = self._newNefSaveFrame(chemicalShiftList, category, chemicalShiftList.name)

        self.ccpn2SaveFrameName[chemicalShiftList] = result['sf_framecode']

        # Fill in loop - use dictionary rather than list as this is more robust against reorderings
        loopName = 'nef_chemical_shift'
        loop = result[loopName]
        atomCols = ['chain_code', 'sequence_code', 'residue_name', 'atom_name', ]
        # NB We cannot use nmrAtom.id.split('.'), since the id has reserved characters remapped
        shifts = sorted(chemicalShiftList.chemicalShifts, key=lambda sh: self._sortingShifts(sh))
        if shifts:
            for shift in shifts:
                if shift.orphan and not includeOrphans:
                    # skip orphans if not required
                    continue

                rowdata = self._loopRowData(loopName, shift)
                _row = shift._getAsTuple()
                rowdata.update(zip(atomCols, (getattr(_row, CS_CHAINCODE, None),
                                              getattr(_row, CS_SEQUENCECODE, None),
                                              getattr(_row, CS_RESIDUETYPE, None),
                                              getattr(_row, CS_ATOMNAME, None))
                                   )
                               )
                # rowdata.update(zip(atomCols, nmrAtom._idTuple))
                rowdata['element'] = None
                rowdata['isotope_number'] = None
                rowdata['ccpn_static'] = shift.getStatic()  # get the local static state

                name = rowdata['atom_name']
                nmrAtom = shift.nmrAtom
                if nmrAtom:
                    if nmrAtom.isotopeCode is not None:
                        isotopeCode = nmrAtom.isotopeCode.upper()
                        isotope, element = commonUtil.splitIntFromChars(isotopeCode)
                        if isotope is not None:
                            rowdata['element'] = element
                            rowdata['isotope_number'] = isotope

                        # Correct for atom names starting with the isotopeCode (e.g. 2HA, 111CD)
                        if name.startswith(isotopeCode):
                            plainName = name[len(str(isotope)):]
                            if chemicalShiftList.getChemicalShift(nmrAtom.nmrResidue.pid + Pid.IDSEP + plainName) is None:
                                # There is no shift in this list that has the corresponding name without the
                                # isotope number prefix. Remove the prefix for writing
                                rowdata['atom_name'] = plainName

                loop.newRow(rowdata)
        else:
            del result[loopName]
        #
        return result

    def structureData2Nef(self, structureData: Sequence[StructureData]) -> StarIo.NmrSaveFrame:
        """Convert StructureData to CCPN NEF saveframes"""

        results = []
        for sData in structureData:

            # # skip the ccpnLogging
            # if dataSet.id == CCPNLOGGING:
            #     continue

            # Set up frame
            category = 'ccpn_dataset'
            result = self._newNefSaveFrame(sData, category, str(sData.id))

            self.ccpn2SaveFrameName[sData] = result['sf_framecode']

            # Fill in loops
            loopName = 'ccpn_calculation_step'
            loop = result[loopName]
            calculationSteps = sData.calculationSteps
            if calculationSteps:
                for calculationStep in calculationSteps:
                    loop.newRow(self._loopRowData(loopName, calculationStep))
            else:
                del result[loopName]

            loopName = 'ccpn_calculation_data'
            loop = result[loopName]
            calculationData = sData.data
            if calculationData:
                for obj in calculationData:
                    loop.newRow(self._loopRowData(loopName, obj))
            else:
                del result[loopName]

            results.append(result)

        paramNum = 1
        category = 'ccpn_parameter'
        for sData in structureData:

            calculationData = sData.data
            if calculationData:
                for obj in calculationData:
                    for k, val in obj.dataParameters.items():

                        # Set up frame - this is too hard-coded here
                        result = self._newNefSaveFrame(None, category, str(paramNum))
                        result.addItem(DATANAME, str(sData.id))
                        # result.addItem('ccpn_dataset_serial', sData.serial)
                        result.addItem('ccpn_data_id', obj.name)
                        result.addItem('ccpn_parameter_name', k)

                        if isinstance(val, pd.DataFrame):
                            # create a loop from a pd.dataFrame - needs improvement
                            loopName = f'ccpn_dataframe'
                            cols = list(val.columns)

                            # NOTE:ED - need to modify the headers somewhere more sensible
                            from ccpn.ui.gui.modules.lib.RestraintAITableCommon import Headers, nefHeaders

                            # list of header types that need swapping - need the opposite to load
                            _headers = [(nefHeaders, Headers),
                                        ]

                            for oldHeaders, newHeaders in _headers:
                                if all(hh in newHeaders for hh in cols) and len(cols) == len(newHeaders):
                                    # rename all the column headers to the correct names
                                    cols = [oldHeaders[newHeaders.index(cc)] if cc in newHeaders else cc for cc in cols]

                            loop = result.newLoop(loopName, list(cols))
                            for _row in val.itertuples(index=False):
                                loop.newRow(_row)

                        # elif isinstance(val, np.ndarray):
                        #     with np.printoptions(threshold=sys.maxsize):
                        #     # opt = np.get_printoptions()
                        #     # np.set_printoptions(threshold=sys.maxsize)
                        #         result.addItem('ccpn_value', val)
                        #     # np.set_printoptions(**opt)

                        else:
                            # or just write the value - handled by valueToStarString
                            result.addItem('ccpn_value', val)

                        results.append(result)
                        paramNum += 1

        return results

    def ccpnLogging2Nef(self, project: Project):
        """Convert ccpn logging dataSet to CCPN NEF saveframe"""

        from ccpn.framework.lib.ccpnNef.CcpnNefLogging import CCPNDEFAULT, getCcpnNefLogNames, getCcpnNefLog

        results = []
        category = 'ccpn_logging'

        _logs = getCcpnNefLogNames(project)
        if _logs is not None:
            result = self._newNefSaveFrame(project, category, CCPNDEFAULT)

            for logName in _logs:
                value = getCcpnNefLog(project, logName)
                if isinstance(value, pd.DataFrame):
                    # Fill in loops
                    loop = result[logName]
                    for obj in value.itertuples():
                        loop.newRow(self._loopRowData(logName, obj))

            results.append(result)

        return results

    def restraintTable2Nef(self, restraintTable: RestraintTable, singleStructureTable: bool = False
                           ) -> StarIo.NmrSaveFrame:
        """Convert RestraintTable to CCPN NEF restraint_list saveframe"""

        project = restraintTable._project

        # Set up frame
        restraintType = restraintTable.restraintType
        itemLength = restraintTable.restraintItemLength

        if restraintType == 'Distance':
            category = 'nef_distance_restraint_list'
            loopName = 'nef_distance_restraint'
        elif restraintType == 'Dihedral':
            category = 'nef_dihedral_restraint_list'
            loopName = 'nef_dihedral_restraint'
        elif restraintType == 'Rdc':
            category = 'nef_rdc_restraint_list'
            loopName = 'nef_rdc_restraint'
        else:
            category = 'ccpn_restraint_list'
            loopName = 'ccpn_restraint'

        max = itemLength + 1
        multipleAttributes = OD((
            ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
            ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
            ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
            ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
            ))

        name = restraintTable.name
        if not singleStructureTable:
            # If there are multiple StructureData, add the structureData serial for disambiguation
            ss = '`%s`' % restraintTable.structureData.serial
            if not name.startswith(ss):
                name = ss + name

        result = self._newNefSaveFrame(restraintTable, category, name)

        self.ccpn2SaveFrameName[restraintTable] = result['sf_framecode']

        # for tag in ('tensor_magnitude', 'tensor_rhombicity', 'tensor_isotropic_value',
        #             'ccpn_tensor_magnitude', 'ccpn_tensor_rhombicity', 'ccpn_tensor_isotropic_value'):
        #   if result.get(tag) == 0:
        #     # Tensor components default to 0
        #     result[tag] = None
        #
        # tensor = restraintTable.tensor
        # if tensor is not None:
        #   result['tensor_magnitude'] = tensor.axial or None
        #   result['tensor_rhombicity'] = tensor.rhombic or None
        #   if category == 'ccpn_restraint_list':
        #     result['tensor_isotropic_value'] = tensor.isotropic or None
        #   else:
        #     result['ccpn_tensor_isotropic_value'] = tensor.isotropic or None

        loop = result[loopName]

        if itemLength < 4:
            # Remove unnecessary columns
            removeNameEndings = ('_1', '_2', '_3', '_4')[itemLength:]
            for tag in loop.columns:
                if tag[-2:] in removeNameEndings:
                    loop.removeColumn(tag, removeData=True)

        index = 0
        for contribution in sorted(restraintTable.restraintContributions):
            rowdata = self._loopRowData(loopName, contribution)
            for item in contribution.restraintItems:
                row = loop.newRow(rowdata)
                index += 1
                row['index'] = index

                # NBNB TBD FIXME Using the PID, as we do here, you are remapping '.' to '^'
                # NBNB reconsider!!!

                # Set individual parts of assignment one by one.
                # NB _set command takes care of varying number of items
                assignments = list(x.split('.') for x in item)
                for ii, attrName in enumerate(('chainCodes', 'sequenceCodes', 'residueTypes', 'atomNames',)):
                    for jj, tag in enumerate(multipleAttributes[attrName]):
                        row[tag] = assignments[jj][ii] or None
                if category == 'nef_dihedral_restraint_list':
                    row['name'] = RestraintLib.dihedralName(project, item)
        #
        return result

    # def spectrum2Nef(self, spectrum: Spectrum) -> StarIo.NmrSaveFrame:
    #     """Convert spectrum to NEF saveframes - one per peaklist
    #
    #     Will create a peakList if none are present"""
    #
    #     result = []
    #
    #     peakLists = sorted(spectrum.peakLists)
    #     if not peakLists:
    #         peakLists = [spectrum.newPeakList()]
    #
    #     # NOTE:ED - this is a stupid hack for more than one peakList per spectrum
    #     first = True
    #     for peakList in peakLists:
    #         result.append(self.peakList2Nef(peakList, exportCompleteSpectrum=first))
    #         first = False
    #     #
    #     return result

    # def peakList2Nef(self, spectrum: Spectrum, peakLists, integralLists, multipletLists,
    def peakList2Nef(self, spectrum: Spectrum, peakList: PeakList | None,
                     peakLists, integralLists, multipletLists,
                     exportCompleteSpectrum: bool = True,
                     # spectrumCount=None,
                     peakListSerial=1,
                     ) -> StarIo.NmrSaveFrame:
        """Convert PeakList to CCPN NEF saveframe.
        Used for all spectrum export, as there is one frame per PeakList
        """

        # spectrum = peakList.spectrum

        # framecode for saveFrame that holds spectrum and first peaklist.
        # If not None, the peakList will be read into that spectrum
        # spectrumAlreadySaved = bool(self.ccpn2SaveFrameName.get(spectrum))

        # We do not support sampled or unprocessed dimensions yet. NBNB TBD.
        if any(x != 'Frequency' for x in spectrum.dimensionTypes):
            raise NotImplementedError(
                    "NEF only implemented for processed frequency spectra, dimension types were: %s"
                    % (spectrum.dimensionTypes,)
                    )

        # Get unique frame name
        obj = spectrum
        name = spectrum.name
        # always append the peaklist number to the end of the name
        name = '%s`%s`' % (name, peakListSerial)  # NOTE:ED - was peakList, then obj.serial - make sure >= 1
        _foundSpectrum = spectrum.project.getSpectrum(name)
        if _foundSpectrum:
            # check that existing spectra don't have this type of postfix
            raise TypeError('Spectrum {} has illegal name'.format(_foundSpectrum.name))

        # Set up frame
        category = 'nef_nmr_spectrum'
        result = self._newNefSaveFrame(obj, category, name, includeLoops=False)  # NOTE:ED - was peakList

        path = spectrum.path  # .filePath gives the path containing $DATA, etc.
        if path:
            result['ccpn_spectrum_file_path'] = path

        self.ccpn2SaveFrameName[obj] = result['sf_framecode']  # NOTE:ED - was peakList
        if peakListSerial > 1:  # add a new saveframe only for the additional peakLists
            self.ccpn2SaveFrameName[spectrum] = result['sf_framecode']

        self.ccpn2SaveFrameName[peakList] = result['sf_framecode']  # also keep the peak-list

        result['chemical_shift_list'] = self.ccpn2SaveFrameName.get(obj.chemicalShiftList)  # NOTE:ED - was peakList
        result['ccpn_sample'] = self.ccpn2SaveFrameName.get(obj.sample)

        # NOTE:ED - add extra saveFrame information for the peakList frame
        appendCategory = 'ccpn_no_peak_list'
        if peakList:
            self._appendCategory(peakList, appendCategory, result)

        # NOTE:ED - add the dataSource values that are required for v2io
        appendCategory = 'nef_ccpn_spectrum_datastore'
        self._appendCategory(obj.dataSource, appendCategory, result)
        try:
            result['ccpn_file_number_type'] = obj.dataSource.isFloatData and 'float' or 'int'

            # still missing complexStoredBy, hasBlockPadding

            # import numpy as np
            #
            # result['ccpn_file_number_type'] = str(_val.dtype)
            # _val = np.finfo(result['ccpn_file_number_type'])
            # result['ccpn_file_byte_number'] = _val.bits // 8
            # if 'ccpn_file_complex_stored_by' not in result:
            #     # set a default for the minute, not sure where this comes from
            #     result['ccpn_file_complex_stored_by'] = 'dimension'

        except:
            self.project._logger.debug("Could not get %s from Spectrum.dataSource %s\n" % ('ccpn_file_number_type', spectrum))

        # NOTE:ED - added to match the spectrum saveFrame above - need to add loops after the peak_list info
        self._appendCategoryLoops(obj, category, result)

        # Will give wrong values for Hz or pointNumber units, and
        # Will fill in all None for non-Frequency dimensions
        loopName = 'nef_spectrum_dimension'
        loop = result[loopName]
        data = OD()
        _mapping = nef2CcpnMap.get(loopName) or {}
        for neftag, attrstring in _mapping.items():
            if attrstring is None:
                # to fill in later
                data[neftag] = [None] * spectrum.dimensionCount
            else:
                data[neftag] = attrgetter(attrstring)(spectrum)

        data['folding'] = ['none' if x is None else x for x in spectrum.foldingModes]
        data['value_first_point'] = [tt[0] for tt in spectrum.spectrumLimits]
        # NBNB All CCPN peaks are in principle at the correct unaliased positions
        # Whether they are set correctly is another matter.
        data['absolute_peak_positions'] = spectrum.dimensionCount * [True]
        acquisitionAxisCode = spectrum.acquisitionAxisCode
        if acquisitionAxisCode is None:
            data['is_acquisition'] = spectrum.dimensionCount * [None]
        else:
            data['is_acquisition'] = [(x == acquisitionAxisCode) for x in spectrum.axisCodes]

        for ii in range(spectrum.dimensionCount):
            rowdata = dict((tt[0], tt[1][ii]) for tt in data.items())
            row = loop.newRow(rowdata)
            row['dimension_id'] = ii + 1

        loopName = 'ccpn_spectrum_dimension'
        loop = result[loopName]
        data = OD()
        _mapping = nef2CcpnMap.get(loopName) or {}
        for neftag, attrstring in _mapping.items():
            if attrstring is None:
                # to fill in later
                data[neftag] = [None] * spectrum.dimensionCount
            else:
                try:
                    data[neftag] = attrgetter(attrstring)(spectrum)
                except AttributeError:
                    self.project._logger.debug("Could not get %s from Spectrum %s\n" % (attrstring, spectrum))

        aliasingLimits = spectrum.aliasingLimits
        for ii in range(spectrum.dimensionCount):
            rowdata = dict((tt[0], tt[1][ii]) for tt in data.items())
            rowdata['lower_aliasing_limit'], rowdata['higher_aliasing_limit'] = aliasingLimits[ii]
            row = loop.newRow(rowdata)
            row['dimension_id'] = ii + 1

        loopName = 'nef_spectrum_dimension_transfer'
        loop = result[loopName]
        transfers = spectrum.magnetisationTransfers
        if transfers:
            for tt in transfers:
                loop.newRow(dict(zip(['dimension_1', 'dimension_2', 'transfer_type', 'is_indirect'], tt)))
        # else:
        #     del result[loopName]

        # Remove superfluous tags
        removeNameEndings = ('_1', '_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9',
                             '_10', '_11', '_12', '_13', '_14', '_15',)[spectrum.dimensionCount:]

        # # NOTE:ED - new for ccpn_peak_lists
        # spectrumPeakLists = set(spectrum.peakLists) & set(peakLists)

        # peakList = AttrDict()  # NOTE:ED - make a temporary peak object
        # peakList.peaks = [pk for pkList in spectrumPeakLists for pk in pkList.peaks]
        # if peakList.peaks:

        loopName = 'nef_peak'
        loop = result[loopName]

        # # Remove superfluous tags
        # removeNameEndings = ('_1', '_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9',
        #                      '_10', '_11', '_12', '_13', '_14', '_15',)[spectrum.dimensionCount:]

        for tag in loop.columns:
            if any(tag.endswith(x) for x in removeNameEndings):
                loop.removeColumn(tag)

        # Get name map for per-dimension attributes
        _max = spectrum.dimensionCount + 1
        multipleAttributes = {
            'position'     : tuple('position_%s' % ii for ii in range(1, _max)),
            'positionError': tuple('position_uncertainty_%s' % ii for ii in range(1, _max)),
            'chainCodes'   : tuple('chain_code_%s' % ii for ii in range(1, _max)),
            'sequenceCodes': tuple('sequence_code_%s' % ii for ii in range(1, _max)),
            'residueTypes' : tuple('residue_name_%s' % ii for ii in range(1, _max)),
            'atomNames'    : tuple('atom_name_%s' % ii for ii in range(1, _max)),
            'slopes'       : tuple('slopes_%s' % ii for ii in range(1, _max)),
            'lowerLimits'  : tuple('lower_limits_%s' % ii for ii in range(1, _max)),
            'upperLimits'  : tuple('upper_limits_%s' % ii for ii in range(1, _max)),
            }

        index = 0

        # export the nef_peak frame even if empty
        for peak in sorted(peakList.peaks if peakList else []):
            rowdata = self._loopRowData(loopName, peak)

            assignments = peak.assignedNmrAtoms
            if assignments:
                for tt in sorted(assignments):
                    # Make one row per assignment
                    row = loop.newRow(rowdata)
                    index += 1
                    row['index'] = index
                    values = peak.position
                    for ii, tag in enumerate(multipleAttributes['position']):
                        row[tag] = values[ii]
                    values = peak.positionError
                    for ii, tag in enumerate(multipleAttributes['positionError']):
                        row[tag] = values[ii]
                    # NB the row._set function will set position_1, position_2 etc.
                    # row._set('position', peak.position)
                    # row._set('position_uncertainty', peak.positionError)

                    # Add the assignments
                    ll = list(x if x is None else x._idTuple for x in tt)
                    for ii, attrName in enumerate(
                            ('chainCodes', 'sequenceCodes', 'residueTypes', 'atomNames')
                            ):
                        tags = multipleAttributes[attrName]
                        for jj, val in enumerate(ll):
                            row[tags[jj]] = None if val is None else val[ii]
                    # # Add the assignments
                    # ll =list(zip(*(x._idTuple if x else (None, None, None, None) for x in tt)))
                    # row._set('chain_code', ll[0])
                    # row._set('sequence_code', ll[1])
                    # row._set('residue_name', ll[2])
                    # row._set('atom_name', ll[3])

            else:
                # No assignments - just make one unassigned row
                row = loop.newRow(rowdata)
                index += 1
                row['index'] = index
                values = peak.position
                for ii, tag in enumerate(multipleAttributes['position']):
                    row[tag] = values[ii]
                values = peak.positionError
                for ii, tag in enumerate(multipleAttributes['positionError']):
                    row[tag] = values[ii]
                # # NB the row._set function will set position_1, position_2 etc.
                # row._set('position', peak.position)
                # row._set('position_uncertainty', peak.positionError)
            row['ccpn_linked_integral'] = None if peak.integral is None else peak.integral.pid

        # else:
        #     del result['nef_peak']

        if exportCompleteSpectrum and spectrum.spectrumHits:
            loopName = 'ccpn_spectrum_hit'
            loop = result[loopName]
            for spectrumHit in spectrum.spectrumHits:
                loop.newRow(self._loopRowData(loopName, spectrumHit))
        else:
            del result['ccpn_spectrum_hit']

        if exportCompleteSpectrum and spectrum.referenceSubstances:
            loopName = 'ccpn_spectrum_reference_substances'
            loop = result[loopName]
            referenceSubstances = spectrum.referenceSubstances
            if len(referenceSubstances) > 0:
                for substance in referenceSubstances:
                    loop.newRow(self._loopRowData(loopName, substance))
            else:
                del result[loopName]

        # NOTE:ED - new for ccpn_peak_lists
        spectrumPeakLists = set(spectrum.peakLists) & set(peakLists)
        if exportCompleteSpectrum and spectrumPeakLists:
            loopName = 'ccpn_peak_list'

            if loopName in result:
                loop = result[loopName]
                for tag in loop.columns:
                    if any(tag.endswith(x) for x in removeNameEndings):
                        loop.removeColumn(tag)
                for pkList in sorted(spectrumPeakLists):
                    row = loop.newRow(self._loopRowData(loopName, pkList))
                    row['peak_list_serial'] = pkList.serial
        else:
            if 'ccpn_peak_list' in result:
                del result['ccpn_peak_list']
            # del result['ccpn_peak']

        spectrumIntegralLists = set(spectrum.integralLists) & set(integralLists)
        if exportCompleteSpectrum and spectrumIntegralLists:
            loopName = 'ccpn_integral_list'

            loop = result[loopName]
            for tag in loop.columns:
                if any(tag.endswith(x) for x in removeNameEndings):
                    loop.removeColumn(tag)
            for integralList in sorted(spectrumIntegralLists):
                row = loop.newRow(self._loopRowData(loopName, integralList))
                row['serial'] = integralList.serial

            loopName = 'ccpn_integral'
            loop = result[loopName]
            for tag in loop.columns:
                if any(tag.endswith(x) for x in removeNameEndings):
                    loop.removeColumn(tag)

            intgrls = sorted([intgrl for intgrl in spectrum.integrals if intgrl.integralList in spectrumIntegralLists])
            if intgrls:
                for integral in intgrls:
                    row = loop.newRow(self._loopRowData(loopName, integral))
                    row['integral_serial'] = integral.serial
                    # values = integral.slopes
                    # for ii, tag in enumerate(multipleAttributes['slopes']):
                    #   row[tag] = None if values is None else values[ii]
                    # # lowerlimits,upperLimits = zip(integral.limits)
                    # lowerlimits = integral.limits
                    # upperLimits = integral.limits
                    # for ii, tag in enumerate(multipleAttributes['lowerLimits']):
                    #   row[tag] = None if lowerlimits is None else lowerlimits[ii]
                    # for ii, tag in enumerate(multipleAttributes['upperLimits']):
                    #   row[tag] = None if upperLimits is None else upperLimits[ii]
                    row['ccpn_linked_peak'] = None if integral.peak is None else integral.peak.pid
            else:
                del result['ccpn_integral']
        else:
            del result['ccpn_integral_list']
            del result['ccpn_integral']

        spectrumMultipletLists = set(spectrum.multipletLists) & set(multipletLists)
        if exportCompleteSpectrum and spectrumMultipletLists:
            loopName = 'ccpn_multiplet_list'

            loop = result[loopName]
            for tag in loop.columns:
                if any(tag.endswith(x) for x in removeNameEndings):
                    loop.removeColumn(tag)
            for multipletList in sorted(spectrumMultipletLists):
                row = loop.newRow(self._loopRowData(loopName, multipletList))
                row['serial'] = multipletList.serial

            loopName = 'ccpn_multiplet'
            loop = result[loopName]
            for tag in loop.columns:
                if any(tag.endswith(x) for x in removeNameEndings):
                    loop.removeColumn(tag)

            mltplts = sorted([mltplt for mltplt in spectrum.multiplets if mltplt.multipletList in spectrumMultipletLists])
            if mltplts:
                for multiplet in mltplts:
                    row = loop.newRow(self._loopRowData(loopName, multiplet))
                    row['multiplet_serial'] = multiplet.serial
                    # values = multiplet.slopes
                    # for ii, tag in enumerate(multipleAttributes['slopes']):
                    #   row[tag] = None if values is None else values[ii]
                    # # lowerlimits,upperLimits = zip(multiplet.limits)
                    # lowerlimits = multiplet.limits
                    # upperLimits = multiplet.limits
                    # for ii, tag in enumerate(multipleAttributes['lowerLimits']):
                    #   row[tag] = None if lowerlimits is None else lowerlimits[ii]
                    # for ii, tag in enumerate(multipleAttributes['upperLimits']):
                    #   row[tag] = None if upperLimits is None else upperLimits[ii]
            else:
                del result['ccpn_multiplet']

            # loopName = 'ccpn_multiplet_peaks'
            # loop = result[loopName]
            # for tag in loop.columns:
            #     if any(tag.endswith(x) for x in removeNameEndings):
            #         loop.removeColumn(tag)
            # for multiplet in sorted(spectrum.multiplets):
            #     for peak in multiplet.peaks:
            #         row = loop.newRow(self._loopRowData(loopName, peak))
            #         row['multiplet_list_serial'] = multiplet.multipletList.serial
            #         row['multiplet_serial'] = multiplet.serial
            #         row['peak_id'] = peak.pid

        else:
            del result['ccpn_multiplet_list']
            del result['ccpn_multiplet']
            # del result['ccpn_multiplet_peaks']

            # NB do more later (e.g. SpectrumReference)

        # NOTE:ED - needs to be in all spectra to deal with cross-spectrum multiplets
        if spectrumMultipletLists:
            loopName = 'ccpn_multiplet_peaks'
            loop = result[loopName]
            for tag in loop.columns:
                if any(tag.endswith(x) for x in removeNameEndings):
                    loop.removeColumn(tag)

            # mltplts = sorted([mltplt for mltplt in spectrum.multiplets if mltplt.multipletList in spectrumMultipletLists])
            # for multiplet in mltplts:
            #     for peak in multiplet.peaks:
            #         row = loop.newRow(self._loopRowData(loopName, peak))
            #         row['multiplet_list_serial'] = multiplet.multipletList.serial
            #         row['multiplet_serial'] = multiplet.serial
            #         row['peak_id'] = peak.pid

            mltpks = sorted([(mltplt, pk) for mltplt in spectrum.multiplets if mltplt.multipletList in spectrumMultipletLists for pk in mltplt.peaks])
            if mltpks:
                for multiplet, peak in mltpks:
                    row = loop.newRow(self._loopRowData(loopName, peak))
                    row['multiplet_list_serial'] = multiplet.multipletList.serial
                    row['multiplet_serial'] = multiplet.serial
                    # row['peak_pid'] = peak.pid
            else:
                del result['ccpn_multiplet_peaks']
        else:
            del result['ccpn_multiplet_peaks']

        return result

    def peakRestraintLinks2Nef(self, restraintTables: Sequence[RestraintTable]) -> StarIo.NmrSaveFrame:

        data = []
        for restraintList in sorted(restraintTables):
            restraintListFrame = self.ccpn2SaveFrameName.get(restraintList)
            if restraintListFrame is not None:
                for restraint in sorted(restraintList.restraints):
                    for peak in sorted(restraint.peaks):
                        peakListFrame = self.ccpn2SaveFrameName.get(peak.peakList)  # .spectrum)
                        if peakListFrame is not None:
                            data.append((peakListFrame, peak.serial, restraintListFrame, restraint.serial))

        if data:
            category = 'nef_peak_restraint_links'
            columns = ('nmr_spectrum_id', 'peak_id', 'restraint_list_id', 'restraint_id',)
            # Set up frame
            result = self._newNefSaveFrame(restraintTables[0].project, category, category)
            loopName = 'nef_peak_restraint_link'
            loop = result[loopName]
            for rowdata in sorted(data):
                loop.newRow(dict(zip(columns, rowdata)))
        else:
            result = None
        #
        return result

    def spectrumGroup2Nef(self, spectrumGroup: SpectrumGroup) -> StarIo.NmrSaveFrame:
        """Convert SpectrumGroup to CCPN NEF saveframe"""

        # Set up frame
        category = 'ccpn_spectrum_group'
        result = self._newNefSaveFrame(spectrumGroup, category, spectrumGroup.name)

        self.ccpn2SaveFrameName[spectrumGroup] = result['sf_framecode']

        # Fill in loop
        loopName = 'ccpn_group_spectrum'
        loop = result[loopName]
        spectra = spectrumGroup.spectra
        if spectra:
            for spectrum in spectra:
                loop.newRow((spectrum.name,))
        else:
            del result[loopName]
        #
        return result

    def complex2Nef(self, complex: Complex) -> StarIo.NmrSaveFrame:
        """Convert Complex to CCPN NEF saveframe"""

        # Set up frame
        category = 'ccpn_complex'
        result = self._newNefSaveFrame(complex, category, complex.name)

        self.ccpn2SaveFrameName[complex] = result['sf_framecode']

        # Fill in loop
        loopName = 'ccpn_complex_chain'
        loop = result[loopName]
        chains = sorted(complex.chains)
        if chains:
            for chain in chains:
                loop.newRow((chain.shortName,))
        else:
            del result[loopName]
        #
        return result

    # TODO:ED add the correct function for converting structureEnsemble to Nef
    # def structureEnsemble2Nef(self, ensemble:StructureEnsemble) -> StarIo.NmrSaveFrame:
    #   """Convert StructureEnsemble to CCPN NEF saveframe"""
    #
    #   # Set up frame
    #   category = 'ccpn_structure_ensemble'
    #   result = self._newNefSaveFrame(ensemble, category, ensemble.name)
    #
    #   return result

    def sample2Nef(self, sample: Sample) -> StarIo.NmrSaveFrame:
        """Convert Sample to CCPN NEF saveframe"""

        # Set up frame
        category = 'ccpn_sample'
        result = self._newNefSaveFrame(sample, category, sample.name)

        self.ccpn2SaveFrameName[sample] = result['sf_framecode']

        # Fill in loop
        loopName = 'ccpn_sample_component'
        loop = result[loopName]
        components = sorted(sample.sampleComponents)
        if components:
            for sampleComponent in components:
                loop.newRow(self._loopRowData(loopName, sampleComponent))
        else:
            del result[loopName]
        #
        return result

    def substance2Nef(self, substance: Substance) -> StarIo.NmrSaveFrame:
        """Convert Substance to CCPN NEF saveframe"""

        # Set up frame
        category = 'ccpn_substance'
        name = '%s.%s' % (substance.name, substance.labelling)
        result = self._newNefSaveFrame(substance, category, name)

        substanceType = substance.substanceType
        result['substance_type'] = substanceType
        if substanceType == 'Molecule':
            apiMolecule = substance._molecule
            if apiMolecule is not None:
                result['sequence_string'] = substance.sequenceString
                result['start_number'] = apiMolecule.sortedMolResidues()[0].seqCode
                result['is_cyclic'] = apiMolecule.isStdCyclic
                molType = apiMolecule.molType
                if molType and not '/' in molType:
                    # 'protein', 'DNA', or 'RNA'. Excludes 'DNA/RNA'
                    result['mol_type'] = molType

        self.ccpn2SaveFrameName[substance] = result['sf_framecode']

        loopName = 'ccpn_substance_synonym'
        loop = result[loopName]
        synonyms = substance.synonyms
        if synonyms:
            for synonym in synonyms:
                loop.newRow((synonym,))
        else:
            del result[loopName]

        loopName = 'ccpn_substance_reference_spectra'
        loop = result[loopName]
        referenceSpectra = substance.referenceSpectra
        if len(referenceSpectra) > 0:
            for spectrum in referenceSpectra:
                loop.newRow((spectrum.name,))
        else:
            del result[loopName]

        return result

    def ccpnAssignentToNef(self, nmrChains: List[NmrChain]):
        """Write CCPN assignment data, to preserve serials etc."""
        category = 'ccpn_assignment'
        if nmrChains:
            project = nmrChains[0].project
            result = self._newNefSaveFrame(project, category, category)

            loopName = 'nmr_chain'
            loop = result[loopName]
            for nmrChain in nmrChains:
                row = loop.newRow(self._loopRowData(loopName, nmrChain))
                row['serial'] = nmrChain.serial

            loopName = 'nmr_residue'
            loop = result[loopName]
            for nmrResidue in project.nmrResidues:
                row = loop.newRow(self._loopRowData(loopName, nmrResidue))
                row['serial'] = nmrResidue.serial

            loopName = 'nmr_atom'
            loop = result[loopName]
            for nmrAtom in project.nmrAtoms:
                row = loop.newRow(self._loopRowData(loopName, nmrAtom))
                row['serial'] = nmrAtom.serial

        else:
            result = None
        #
        return result

    def notes2Nef(self, project: Project, notes: List[Note]) -> StarIo.NmrSaveFrame:
        """Convert Notes to CCPN NEF saveframe"""

        # Set up frame
        category = 'ccpn_notes'
        if notes:
            result = self._newNefSaveFrame(project, category, category)
            loopName = 'ccpn_note'
            loop = result[loopName]
            for note in sorted(notes):
                row = loop.newRow(self._loopRowData(loopName, note))
                row['serial'] = note.serial
                row['created'] = note.created
                row['last_modified'] = note.lastModified
        else:
            result = None
        #
        return result

    def additionalData2Nef(self, project: Project) -> StarIo.NmrSaveFrame:
        """Make singleton saveFrame for additional data (ccpnInternalData)"""

        # Set up frame
        category = 'ccpn_additional_data'
        pid2Obj = project._pid2Obj
        data = {}
        for className in _coreImportOrder:
            # Use importOrder to get all classNames. The actual order does not matter here.
            dd = pid2Obj.get(className)
            if dd:
                for obj in dd.values():
                    if hasattr(obj, '_ccpnInternalData'):
                        internalData = obj._ccpnInternalData
                        if internalData:
                            data[obj.longPid] = internalData

        if data:
            result = self._newNefSaveFrame(project, category, category)
            loopName = 'ccpn_internal_data'
            loop = result[loopName]
            for key, val in sorted(data.items()):
                row = loop.newRow((key, jsonIo.dumps(val)))
        else:
            result = None
        #
        return result

    def violationTable2Nef(self, violationTable: ViolationTable, singleStructureTable: bool = False
                           ) -> Optional[StarIo.NmrSaveFrame]:
        """Make a saveFrame for a violationTable"""

        project = violationTable._project

        # Set up frame
        # if violationTable.restraintTable:
        #     restraintType = violationTable.restraintType
        # else:
        #     return

        restraintType = 'Distance'

        if restraintType == 'Distance':
            category = 'ccpn_distance_restraint_violation_list'
            loopName = 'ccpn_distance_restraint_violation'
            itemLength = 2
        elif restraintType == 'Dihedral':
            category = 'ccpn_dihedral_restraint_violation_list'
            loopName = 'ccpn_dihedral_restraint_violation'
            itemLength = 4
        elif restraintType == 'Rdc':
            category = 'ccpn_rdc_restraint_violation_list'
            loopName = 'ccpn_rdc_restraint_violation'
            itemLength = 2
        else:
            return

        name = violationTable.name
        if not singleStructureTable:
            # If there are multiple StructureData, add the structureData serial for disambiguation
            ss = '`%s`' % violationTable.structureData.serial
            if not name.startswith(ss):
                name = ss + name

        result = self._newNefSaveFrame(violationTable, category, name)
        self.ccpn2SaveFrameName[violationTable] = result['sf_framecode']
        result['ccpn_restraint_violation_list_columns'] = json.dumps(list(violationTable.columns))

        metaloopName = 'ccpn_restraint_violation_list_metadata'
        loop = result[metaloopName]

        # add the metadata loop to the saveframe
        if violationTable.metadata.items():
            for k, val in violationTable.metadata.items():
                row = loop.newRow(self._loopRowData(metaloopName, {}))
                row['name'] = k
                row['parameter'] = json.dumps(val)
        else:
            del loop

        # add the dataFrame to the saveframe
        _data = violationTable.data

        if isinstance(_data, pd.DataFrame) and not _data.empty:
            # create a loop from a pd.dataFrame

            # delete the old list - easier to create a new one
            del result[loopName]

            cols = list(_data.nefCompatibleColumns)
            loop = result.newLoop(loopName, list(cols))
            for _row in _data.itertuples(index=False):
                loop.newRow(_row)

        else:
            del result[loopName]

        return result

        # # Set up frame
        # category = 'ccpn_datatable'
        # name = '%s.%s' % (category, violationTable.name)
        # result = self._newNefSaveFrame(violationTable, category, name)
        #
        # loopName = 'ccpn_datatable_metadata'
        # loop = result[loopName]
        #
        # # add the metadata loop to the saveframe
        # if violationTable.metadata.items():
        #     for k, val in violationTable.metadata.items():
        #         row = loop.newRow(self._loopRowData(loopName, {}))
        #         row['name'] = k
        #         row['parameter'] = val
        # else:
        #     del loop
        #
        # # add the dataFrame to the saveframe
        # _data = violationTable.data
        # loopName = 'ccpn_datatable_data'
        # if isinstance(_data, pd.DataFrame) and not _data.empty:
        #     # create a loop from a pd.dataFrame - needs improvement
        #
        #     del result[loopName]
        #
        #     cols = list(_data.columns)
        #     loop = result.newLoop(loopName, list(cols))
        #     for _row in _data.itertuples(index=False):
        #         loop.newRow(_row)
        #
        # else:
        #     del result[loopName]
        #
        # return result

    def dataTable2Nef(self, project: Project, dataTable: DataTable) -> StarIo.NmrSaveFrame:
        """Make a saveFrame for a datatable"""

        # Set up frame
        category = 'ccpn_datatable'
        result = self._newNefSaveFrame(dataTable, category, dataTable.name)
        result['ccpn_datatable_columns'] = json.dumps(list(dataTable.columns))

        loopName = 'ccpn_datatable_metadata'
        loop = result[loopName]

        # add the metadata loop to the saveframe
        if dataTable.metadata.items():
            for k, val in dataTable.metadata.items():
                row = loop.newRow(self._loopRowData(loopName, {}))
                row['name'] = k
                row['parameter'] = json.dumps(val)
        else:
            del loop

        # add the dataFrame to the saveframe
        _data = dataTable.data
        loopName = 'ccpn_datatable_data'
        if isinstance(_data, pd.DataFrame) and not _data.empty:
            # create a loop from a pd.dataFrame - needs improvement

            del result[loopName]

            # get the nef compatible columns from the dataTable
            cols = list(_data.nefCompatibleColumns)
            loop = result.newLoop(loopName, list(cols))
            for _row in _data.itertuples(index=False):
                loop.newRow(_row)

        else:
            del result[loopName]

        return result

        # if isinstance(val, pd.DataFrame):
        #     # create a loop from a pd.dataFrame - needs improvement
        #     loopName = f'ccpn_dataframe'
        #     cols = list(val.columns)
        #
        #     # NOTE:ED - need to modify the headers somewhere more sensible
        #     from ccpn.ui.gui.modules.RestraintAnalysisTable import nefHeaders, Headers
        #
        #     # list of header types that need swapping - need the opposite to load
        #     _headers = [(nefHeaders, Headers),
        #                 ]
        #
        #     for oldHeaders, newHeaders in _headers:
        #         if all(hh in newHeaders for hh in cols) and len(cols) == len(newHeaders):
        #             # rename all the column headers to the correct names
        #             cols = [oldHeaders[newHeaders.index(cc)] if cc in newHeaders else cc for cc in cols]
        #
        #     loop = result.newLoop(loopName, list(cols))
        #     for _row in val.itertuples(index=False):
        #         loop.newRow(_row)

    def collections2Nef(self, project: Project, collections) -> StarIo.NmrSaveFrame:
        """Make singleton saveFrame for collections"""

        # Set up frame
        category = 'ccpn_collections'
        if collections:
            result = self._newNefSaveFrame(project, category, category)
            loopName = 'ccpn_collection'
            loop = result[loopName]
            for collection in collections:
                row = loop.newRow(self._loopRowData(loopName, collection))
                row['items'] = json.dumps([itm.pid for itm in collection.items])
        else:
            result = None

        return result

    def _saveFrameNefOrder(self, saveframes: List[Optional[StarIo.NmrSaveFrame]]
                           ) -> List[StarIo.NmrSaveFrame]:
        """Reorder saveframes in NEF export order, and filter out Nones"""
        dd = {}
        for saveframe in saveframes:
            if saveframe is not None:
                try:
                    ll = dd.setdefault(saveframe['sf_category'], [])
                    ll.append(saveframe)
                except Exception as es:
                    pass
        #
        result = []
        for tag in saveFrameWritingOrder:
            if tag in dd:
                ll = dd.pop(tag)
                result.extend(ll)
        if dd:
            raise ValueError("Unknown saveframe types in export: %s" % list(dd.keys()))
        #
        return result

    def _loopRowData(self, loopName: str, wrapperObj: AbstractWrapperObject) -> dict:
        """Fill in a loop row data dictionary from master mapping and wrapperObj.
        Unmapped data to be added afterwards"""

        rowdata = {}
        _mapping = nef2CcpnMap.get(loopName) or {}
        for neftag, attrstring in _mapping.items():
            if attrstring is not None:

                val = attrgetter(attrstring)(wrapperObj)
                if val != '':
                    rowdata[neftag] = val
                else:
                    rowdata[neftag] = None
        return rowdata

    def _newNefSaveFrame(self, wrapperObj: Optional[AbstractWrapperObject],
                         category: str, name: str,
                         includeLoops=True) -> StarIo.NmrSaveFrame:
        """Create new NEF saveframe of category for wrapperObj using data from self.Nef2CcpnMap
        The functions will fill in top level items and make loops, but not
        fill in loop data
        """

        name = StarIo.string2FramecodeString(name)
        if name != category:
            name = '%s_%s' % (category, name)

        # Set up frame
        result = StarIo.NmrSaveFrame(name=name, category=category)
        result.addItem('sf_category', category)
        result.addItem('sf_framecode', name)

        if wrapperObj is not None:
            # Add data
            frameMap = nef2CcpnMap.get(category) or {}
            for tag, itemvalue in frameMap.items():
                if itemvalue is None:
                    result.addItem(tag, None)
                elif isinstance(itemvalue, str):
                    try:
                        result.addItem(tag, attrgetter(itemvalue)(wrapperObj))
                    except AttributeError:
                        # You can get this error if a) the mapping is incorrect
                        # The dotted navigation expression can not always be followed
                        # as is the case e.g. for (PeakList.)spectrum dataStore headerSize'
                        # where the dataStore is sometimes None
                        self.project._logger.debug("Could not get %s from %s\n" % (itemvalue, wrapperObj))
                else:
                    # This is a loop
                    assert itemvalue == _isALoop, "Invalid item specifier in Nef2CcpnMap: %s" % (itemvalue,)
                    if includeLoops:
                        result.newLoop(tag, nef2CcpnMap.get(tag) or {})
        #
        return result

    def _appendCategory(self, wrapperObj: Optional[AbstractWrapperObject],
                        category: str, saveFrame: StarIo.NmrSaveFrame,
                        includeLoops=True):
        """Append values to a saveFrame from another saveFrame definition
        """
        if wrapperObj is not None:
            # Add data
            frameMap = nef2CcpnMap.get(category) or {}
            for tag, itemvalue in frameMap.items():
                if itemvalue is None:
                    saveFrame.addItem(tag, None)
                elif isinstance(itemvalue, str):
                    try:
                        saveFrame.addItem(tag, attrgetter(itemvalue)(wrapperObj))
                    except AttributeError:
                        # You can get this error if a) the mapping is incorrect
                        # The dotted navigation expression can not always be followed
                        # as is the case e.g. for (PeakList.)spectrum dataStore headerSize'
                        # where the dataStore is sometimes None
                        self.project._logger.debug("Could not get %s from %s\n" % (itemvalue, wrapperObj))
                else:
                    # This is a loop
                    assert itemvalue == _isALoop, "Invalid item specifier in Nef2CcpnMap: %s" % (itemvalue,)
                    if includeLoops:
                        saveFrame.newLoop(tag, nef2CcpnMap.get(tag) or {})

    def _appendCategoryLoops(self, wrapperObj: Optional[AbstractWrapperObject],
                             category: str, saveFrame: StarIo.NmrSaveFrame):
        """Append values to a saveFrame from another saveFrame definition
        """
        if wrapperObj is not None:
            # Add data
            frameMap = nef2CcpnMap.get(category) or {}
            for tag, itemvalue in frameMap.items():
                if itemvalue is None:
                    pass
                elif isinstance(itemvalue, str):
                    pass
                else:
                    # This is a loop
                    assert itemvalue == _isALoop, "Invalid item specifier in Nef2CcpnMap: %s" % (itemvalue,)
                    saveFrame.newLoop(tag, nef2CcpnMap.get(tag) or {})

    ####################################################################################
    #
    #       NEF reader code:
    #
    ####################################################################################


class CcpnNefReader(CcpnNefContent):
    # Importer functions - used for converting saveframes and loops
    importers = {}
    verifiers = {}
    renames = {}

    def __init__(self, application, specificationFile: str = None, mode: str = PARSER_MODE_STANDARD,
                 testing: bool = False):

        self.application = application
        self.mode = mode
        self._saveFrameName = None
        self.warnings = []
        self.errors = []
        self.setImportAll(True)
        self.testing = testing

        # Map for resolving cross-links in NEF file
        self.frameCode2Object = {}
        self._frameCodeToSpectra = {}

        # Map for speeding up restraint reading
        self._dataSet2ItemMap = {}
        self._nmrResidueMap = None

        self.defaultDataSetSerial = None
        self.defaultNmrChain = None
        self.mainDataSetSerial = None
        self.defaultChemicalShiftList = None

    def setImportAll(self, value):
        """Set/clear the importAll status - used for importing subset of nef file
        Must be done prior to any content/verify/import
        """
        if not isinstance(value, bool):
            raise TypeError('{} must be a bool'.format(value))

        self._importAll = value
        self._importDict = {}

    def getNefData(self, path: str):
        """Get NEF data structure from file"""
        nmrDataExtent = StarIo.parseNefFile(path)
        dataBlocks = list(nmrDataExtent.values())
        if len(dataBlocks) > 1:
            getLogger().warning('More than one datablock in a NEF file is not allowed.  Using the first and discarding the rest.')
        dataBlock = dataBlocks[0]

        # Initialise afresh for every file read
        self._dataSet2ItemMap = {}
        self._nmrResidueMap = {}
        #
        return dataBlock

    def getNMRStarData(self, path: str):
        """Get NEF data structure from file"""
        nmrDataExtent = StarIo.parseNmrStarFile(path)
        dataBlocks = list(nmrDataExtent.values())
        dataBlock = dataBlocks[0]

        # Initialise afresh for every file read
        self._dataSet2ItemMap = {}
        self._nmrResidueMap = {}
        #
        return dataBlock

    def _getSaveFramesInOrder(self, dataBlock: StarIo.NmrDataBlock) -> OD:
        """Get saveframes in fixed reading order as Ordereddict(category:[saveframe,])"""
        result = OD(((x, []) for x in saveFrameReadingOrder))
        result['other'] = otherFrames = []
        for saveFrameName, saveFrame in dataBlock.items():
            sf_category = saveFrame.get('sf_category')
            ll = result.get(sf_category)
            if ll is None:
                ll = otherFrames
            ll.append(saveFrame)
        #
        return result

        # these should be mandatory
        # save_nef_nmr_meta_data
        # save_nef_molecular_system
        # save_nef_sequence
        # save_nef_chemical_shift_list

    def _mergeSaveFramesInOrder(self, od1: OD, od2: OD) -> OD:
        result = OD(((x, []) for x in saveFrameReadingOrder))
        for k in result:
            ll1 = od1.get(k, [])
            ll2 = od2.get(k, [])

            ll2 = [val for val in ll2 if val not in ll1]
            result[k] = ll1 + ll2

        # result = OD((k1, list(set(val1) | set(val2))) for k1, val1 in od1.items() for k2, val2 in od2.items() if k1 == k2)
        return result

    # def verifyProject(self, project: Project, dataBlock: StarIo.NmrDataBlock,
    #                   projectIsEmpty: bool = True,
    #                   selection: typing.Optional[dict] = None):
    #     """Verify import of selection from dataBlock into existing/empty Project
    #     """
    #     # Initialise mapping dicts
    #     if not hasattr(self, '_dataSet2ItemMap') or projectIsEmpty:
    #         self._dataSet2ItemMap = {}
    #     if not hasattr(self, '_nmrResidueMap') or projectIsEmpty:
    #         self._nmrResidueMap = {}
    #
    #     self.warnings = []
    #     self.project = project
    #     self.defaultChainCode = None
    #
    #     saveframeOrderedDict = self._getSaveFramesInOrder(dataBlock)
    #
    #     # Load metadata and molecular system first
    #     metaDataFrame = dataBlock['nef_nmr_meta_data']
    #     self._saveFrameName = 'nef_nmr_meta_data'
    #     self.verifiers['nef_nmr_meta_data'](self, project, metaDataFrame)
    #     del saveframeOrderedDict['nef_nmr_meta_data']
    #
    #     saveFrame = dataBlock.get('nef_molecular_system')
    #     if saveFrame:
    #         self._saveFrameName = 'nef_molecular_system'
    #         self.verifiers['nef_molecular_system'](self, project, saveFrame)
    #     del saveframeOrderedDict['nef_molecular_system']
    #
    #     # Load assignments, or preload from shiftlists
    #     # to make sure '@' and '#' identifiers match the right serials
    #     saveFrame = dataBlock.get('ccpn_assignment')
    #     if saveFrame:
    #         self._saveFrameName = 'ccpn_assignment'
    #         self.verify_ccpn_assignment(project, saveFrame)
    #         del saveframeOrderedDict['ccpn_assignment']
    #     # else:
    #     #     self.verify_preloadAssignmentData(dataBlock)
    #
    #     for sf_category, saveFrames in saveframeOrderedDict.items():
    #         for saveFrame in saveFrames:
    #             saveFrameName = self._saveFrameName = saveFrame.name
    #             saveFrame._rowErrors = {}
    #
    #             if selection and saveFrameName not in selection:
    #                 getLogger().debug2('>>>   -- skip saveframe {}'.format(saveFrameName))
    #                 continue
    #             getLogger().debug2('>>> verifying saveframe {}'.format(saveFrameName))
    #
    #             verifier = self.verifiers.get(sf_category)
    #             if verifier is None:
    #                 getLogger().warning('    Unknown saveframe category {sf_category} {saveFrameName}')
    #             else:
    #                 result = verifier(self, project, saveFrame)
    #
    #     return (tuple(self.warnings or ()), tuple(self.errors or ()))

    def _verifySaveFrame(self, project, saveFrame: StarIo.NmrSaveFrame,
                         projectIsEmpty: bool = True,
                         selection: typing.Optional[dict] = None):
        """Verify a saveFrame (if in selection, or always if selection is empty)
        """
        saveFrameName = saveFrame.name
        sf_category = saveFrame['sf_category']
        saveFrame._rowErrors = AttrDict()

        verifier = self.verifiers.get(sf_category)
        if verifier is None:
            getLogger().debug("verify - unknown saveframe category {} {}".format(sf_category, saveFrameName))
        else:
            return verifier(self, project, saveFrame)

    def verifyProject(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                      projectIsEmpty: bool = True,
                      selection: typing.Optional[dict] = None):
        """Verify import of selection from dataBlock into existing/empty Project
        """
        # Initialise mapping dicts
        if not hasattr(self, '_dataSet2ItemMap') or projectIsEmpty:
            self._dataSet2ItemMap = {}
        if not hasattr(self, '_nmrResidueMap') or projectIsEmpty:
            self._nmrResidueMap = {}

        self.warnings = []
        self.errors = []
        self.project = project
        self.defaultChainCode = None
        dataBlock._rowErrors = AttrDict()

        with notificationEchoBlocking():
            self.traverseDataBlock(project, dataBlock, traverseFunc=partial(self._verifySaveFrame,
                                                                            projectIsEmpty=projectIsEmpty,
                                                                            selection=selection))

        return (tuple(self.warnings or ()), tuple(self.errors or ()))

    @staticmethod
    def _getErrors(project, item: StarIo.NmrDataBlock | StarIo.NmrSaveFrame | StarIo.NmrLoop):
        """Print the errors in a saveFrame/dataBlock - results generated with _verifyNef
        Loops are included in the saveFrame
        """
        if getattr(item, ROWERRORATTR, None):
            leader = item.name + ':' + item.category + ' - '
            leaderSpace = ' ' * len(leader)
            for name, thisSet in item._rowErrors.items():
                leaderName = name + ' - '
                leaderNameSpace = ' ' * len(leaderName)
                viewList = list(thisSet or ['empty'])
                print('{}{}{}'.format(leader, leaderName, [ss for ss in thisSet]))

                # CMAX = 7
                # for cCount, v in enumerate(viewList[:CMAX+1]):
                #     print('{}{}{}'.format(leader, leaderName,
                #                           v if cCount < CMAX else
                #                           '... {} more'.format(len(viewList) - CMAX)))
                #     leader = leaderSpace
                #     leaderName = leaderNameSpace

    def testErrors(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                   projectIsEmpty: bool = True,
                   selection: typing.Optional[dict] = None):
        """Print the errors in the nef dict - results generated with _contentNef
        """
        return self.traverseDataBlock(project, dataBlock, traverseFunc=self._getErrors)

    def _searchReplaceLoop(self, project, loop: StarIo.NmrLoop,
                           searchFrameCode=None, replaceFrameCode=None, replace=False,
                           rowSearchList=None):
        """Search the loop for occurrences of searchFrameCode and replace if required
        """
        if not loop:
            return

        for row in loop.data:
            for rowNum, (k, val) in enumerate(row.items()):
                if rowSearchList and k not in rowSearchList:
                    continue

                # search for any matching value
                if val == (searchFrameCode if searchFrameCode != '.' else None):
                    getLogger().debug('found {} {} --> {}'.format(rowNum, k, val))
                    if replace:
                        row[k] = replaceFrameCode

    def _searchReplaceFrame(self, project, saveFrame: StarIo.NmrSaveFrame,
                            searchFrameCode=None, replaceFrameCode=None,
                            replace=False, validFramesOnly=False,
                            frameSearchList=None, attributeSearchList=None,
                            loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of searchFrameCode and replace if required
        """
        if not saveFrame:
            return

        # category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        if not frameSearchList or framecode in frameSearchList:
            for k, val in saveFrame.items():
                if attributeSearchList and k not in attributeSearchList:
                    continue

                if val == (searchFrameCode if searchFrameCode != '.' else None):
                    getLogger().debug('found {} {} --> {}'.format(saveFrame, k, val))
                    if replace:
                        saveFrame[k] = replaceFrameCode

        elif validFramesOnly:
            return

        # search loops as well - will still search for all loops even in ignored saveFrames
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._searchReplaceLoop(project, loop, searchFrameCode=searchFrameCode,
                                            replaceFrameCode=replaceFrameCode, replace=replace,
                                            rowSearchList=rowSearchList)

    @staticmethod
    def _searchReplaceDictLoop(project, loop: StarIo.NmrLoop,
                               searchFrameCode=None, replaceFrameCode=None, replace=False,
                               rowSearchList=None):
        """Search the loop for occurrences of item in dict and replace if required
        """
        import re

        if not loop:
            return

        for row in loop.data:
            for rowNum, (k, val) in enumerate(row.items()):
                if rowSearchList and k not in rowSearchList:
                    continue

                # val is a string so can replace easily
                if isinstance(val, str):
                    for _old, _new in zip(searchFrameCode, replaceFrameCode):
                        # add double-quotes around the string - catches case of contains only the pid
                        # NOTE:ED - not very generic, should write better regex search, but requires doubling up all searches
                        val = re.sub(_old, _new, '"' + val + '"')
                        val = val[1:-1]

                    if row[k] != val:
                        getLogger().debug(f'{"_searchReplaceDictLoop":25} found     {row[k]}')
                        row[k] = val

    def _searchReplaceDict(self, project, saveFrame: StarIo.NmrSaveFrame,
                           searchFrameCode=None, replaceFrameCode=None,
                           replace=False, validFramesOnly=False,
                           frameSearchList=None, attributeSearchList=None,
                           loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of item in dict and replace if required
        """
        if not saveFrame:
            return

        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._searchReplaceDictLoop(project, loop, searchFrameCode=searchFrameCode,
                                                replaceFrameCode=replaceFrameCode, replace=replace,
                                                rowSearchList=rowSearchList)

    def searchReplace(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                      projectIsEmpty: bool = True,
                      selection: typing.Optional[dict] = None,
                      searchFrameCode=None, replaceFrameCode=None,
                      replace=False, validFramesOnly=False,
                      frameSearchList=None, attributeSearchList=None,
                      loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        if searchFrameCode is not None:
            return self.traverseDataBlock(project, dataBlock,
                                          traverseFunc=partial(self._searchReplaceFrame,
                                                               searchFrameCode=searchFrameCode, replaceFrameCode=replaceFrameCode,
                                                               replace=replace, validFramesOnly=validFramesOnly,
                                                               frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                                                               loopSearchList=loopSearchList, rowSearchList=rowSearchList))

    @staticmethod
    def _searchReplaceListLoop(project, loop: StarIo.NmrLoop,
                               searchFrameCode=None, replaceFrameCode=None, replace=False,
                               rowSearchList=None):
        """Search the loop for occurrences of searchFrameCode and replace if required
        """
        if not loop:
            return

        for rowNum, row in enumerate(loop.data):
            found = OD()
            for k, oldVal, newVal in zip(rowSearchList, searchFrameCode, replaceFrameCode):
                if k in row:
                    val = row.get(k)
                    if val == oldVal:
                        found[k] = (val, newVal)

            # must have found ALL matching in the list
            if len(found) == len(rowSearchList):
                for k, (val, newVal) in found.items():
                    getLogger().debug('found {} {} --> {}'.format(rowNum, k, val))
                    if replace:
                        row[k] = newVal

    @staticmethod
    def _searchReplaceNumberListLoop(project, loop: StarIo.NmrLoop,
                                     searchFrameCode=None, replaceFrameCode=None, replace=False,
                                     rowSearchList=None):
        """Search the loop for occurrences of searchFrameCode and replace if required
        """
        # NOTE:ED - special for nef_peaks
        if not loop:
            return

        maxPos = positions = 0
        for rowNum, row in enumerate(loop.data):
            positions = [int(_val[POSITIONCERTAINTYLEN:]) for _val in row.keys() if isinstance(_val, str) and _val.startswith(POSITIONCERTAINTY)]
            maxPos = max(positions)
            break

        for rowNum, row in enumerate(loop.data):
            for posNum in range(1, maxPos + 1):
                found = OD()
                for k, oldVal, newVal in zip(rowSearchList, searchFrameCode, replaceFrameCode):
                    kNum = '{}_{}'.format(k, posNum)

                    if kNum in row:
                        val = row.get(kNum)
                        if val == oldVal:
                            found[kNum] = (val, newVal)

                # must have found ALL matching in the list
                if len(found) == len(rowSearchList):
                    for kNum, (val, newVal) in found.items():
                        getLogger().debug('found {} {} --> {}'.format(rowNum, kNum, val))
                        if replace:
                            row[kNum] = newVal

    def _searchReplaceListFrame(self, project, saveFrame: StarIo.NmrSaveFrame,
                                searchFrameCode=None, replaceFrameCode=None,
                                replace=False, validFramesOnly=False,
                                frameSearchList=None, attributeSearchList=None,
                                loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of searchFrameCode and replace if required
        MUST BE LIST BASED
        """
        if not saveFrame:
            return

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        if not frameSearchList or framecode in frameSearchList:
            found = OD()
            for k, oldVal, newVal in zip(attributeSearchList, searchFrameCode, replaceFrameCode):
                if k in saveFrame:
                    val = saveFrame.get(k)
                    if val == oldVal:
                        found[k] = (val, newVal)

            # must have found ALL matching in the list
            if len(found) == len(attributeSearchList):
                for k, (val, newVal) in found.items():
                    getLogger().debug('found {} {} --> {}'.format(saveFrame, k, val))
                    if replace:
                        saveFrame[k] = newVal

        elif validFramesOnly:
            return

        # search loops as well - will still search for all loops even in ignored saveFrames
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._searchReplaceListLoop(project, loop, searchFrameCode=searchFrameCode,
                                                replaceFrameCode=replaceFrameCode, replace=replace,
                                                rowSearchList=rowSearchList)

    def _searchReplaceNumberListLoops(self, project, saveFrame: StarIo.NmrSaveFrame,
                                      searchFrameCode=None, replaceFrameCode=None,
                                      replace=False, validFramesOnly=False,
                                      frameSearchList=None, attributeSearchList=None,
                                      loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of searchFrameCode and replace if required
        MUST BE LIST BASED
        """
        if not saveFrame:
            return

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # search loops as well - will still search for all loops even in ignored saveFrames
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._searchReplaceNumberListLoop(project, loop, searchFrameCode=searchFrameCode,
                                                      replaceFrameCode=replaceFrameCode, replace=replace,
                                                      rowSearchList=rowSearchList)

    def searchReplaceList(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                          projectIsEmpty: bool = True,
                          selection: typing.Optional[dict] = None,
                          searchFrameCode=None, replaceFrameCode=None,
                          replace=False, validFramesOnly=False,
                          frameSearchList=None, attributeSearchList=None,
                          loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to attribute list and row list
        All saveframes are traversed, attributes are processed for saveFrames in categorySearch list (if exists, or all of empty)
        All searchframeCodes must match for replace to occur

        e.g. searchFrameCode = ('exampleName', 'exampleLabel')
            replaceFrameCode = ('newName', 'newLabel')

            attributes to search for are defined in attributeSearchList and rowSearchList
             ('name', 'labelling')

             Replace will occur if name == exampleName & labelling == exampleLabel
             in saveFrame attributes and in row of a loop with columns 'name' and 'labelling'
        """
        if searchFrameCode is not None:
            return self.traverseDataBlock(project, dataBlock,
                                          traverseFunc=partial(self._searchReplaceListFrame,
                                                               searchFrameCode=searchFrameCode, replaceFrameCode=replaceFrameCode,
                                                               replace=replace, validFramesOnly=validFramesOnly,
                                                               frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                                                               loopSearchList=loopSearchList, rowSearchList=rowSearchList))

    def searchReplaceLoopListNumbered(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                                      projectIsEmpty: bool = True,
                                      selection: typing.Optional[dict] = None,
                                      searchFrameCode=None, replaceFrameCode=None,
                                      replace=False, validFramesOnly=False,
                                      frameSearchList=None, attributeSearchList=None,
                                      loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to attribute list and row list
        All saveframes are traversed, attributes are processed for saveFrames in categorySearch list (if exists, or all of empty)
        All searchframeCodes must match for replace to occur

        e.g. searchFrameCode = ('exampleName', 'exampleLabel')
            replaceFrameCode = ('newName', 'newLabel')

            attributes to search for are defined in attributeSearchList and rowSearchList
             ('name', 'labelling')

             Replace will occur if name == exampleName & labelling == exampleLabel
             in saveFrame attributes and in row of a loop with columns 'name' and 'labelling'
        """
        if searchFrameCode is not None:
            return self.traverseDataBlock(project, dataBlock,
                                          traverseFunc=partial(self._searchReplaceNumberListLoops,
                                                               searchFrameCode=searchFrameCode, replaceFrameCode=replaceFrameCode,
                                                               replace=replace, validFramesOnly=validFramesOnly,
                                                               frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                                                               loopSearchList=loopSearchList, rowSearchList=rowSearchList))

    def searchReplaceDict(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                          projectIsEmpty: bool = True,
                          selection: typing.Optional[dict] = None,
                          searchFrameCode=None, replaceFrameCode=None,
                          replace=False, validFramesOnly=False,
                          frameSearchList=None, attributeSearchList=None,
                          loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        if searchFrameCode is not None:
            return self.traverseDataBlock(project, dataBlock,
                                          traverseFunc=partial(self._searchReplaceDict,
                                                               searchFrameCode=searchFrameCode, replaceFrameCode=replaceFrameCode,
                                                               replace=replace, validFramesOnly=validFramesOnly,
                                                               frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                                                               loopSearchList=loopSearchList, rowSearchList=rowSearchList))

    @staticmethod
    def _searchReplaceChainLoop(project, loop: StarIo.NmrLoop,
                                searchFrameCode=None, replaceFrameCode=None, replace=False,
                                rowSearchList=None):
        """Search the loop for occurrences of searchFrameCode and replace if required
        """
        if not loop:
            return

        for rowNum, row in enumerate(loop.data):
            for postFix in range(16):
                k = 'chain_code' + (f'_{postFix}' if postFix else '')
                if k in row:
                    val = row[k]

                    # search for any matching value
                    if val == (searchFrameCode if searchFrameCode != '.' else None):
                        if any(row.get(col + (f'_{postFix}' if postFix else ''))
                               for col in ('sequence_code', 'residue_name', 'atom_name')):
                            getLogger().debug('found {} {} --> {}'.format(rowNum, k, val))
                            if replace:
                                row[k] = replaceFrameCode

    def _searchReplaceChainFrame(self, project, saveFrame: StarIo.NmrSaveFrame,
                                 searchFrameCode=None, replaceFrameCode=None,
                                 replace=False, validFramesOnly=False,
                                 frameSearchList=None, attributeSearchList=None,
                                 loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of searchFrameCode and replace if required
        """
        if not saveFrame:
            return

        # category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        if not frameSearchList or framecode in frameSearchList:
            for k, val in saveFrame.items():
                if attributeSearchList and k not in attributeSearchList:
                    continue

                if val == (searchFrameCode if searchFrameCode != '.' else None):
                    getLogger().debug('found {} {} --> {}'.format(saveFrame, k, val))
                    if replace:
                        saveFrame[k] = replaceFrameCode

        elif validFramesOnly:
            return

        # search loops as well - will still search for all loops even in ignored saveFrames
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._searchReplaceChainLoop(project, loop, searchFrameCode=searchFrameCode,
                                                 replaceFrameCode=replaceFrameCode, replace=replace,
                                                 rowSearchList=rowSearchList)

    def searchReplaceChain(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                           projectIsEmpty: bool = True,
                           selection: typing.Optional[dict] = None,
                           searchFrameCode=None, replaceFrameCode=None,
                           replace=False, validFramesOnly=False,
                           frameSearchList=None, attributeSearchList=None,
                           loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        if searchFrameCode is not None:
            return self.traverseDataBlock(project, dataBlock,
                                          traverseFunc=partial(self._searchReplaceChainFrame,
                                                               searchFrameCode=searchFrameCode, replaceFrameCode=replaceFrameCode,
                                                               replace=replace, validFramesOnly=validFramesOnly,
                                                               frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                                                               loopSearchList=loopSearchList, rowSearchList=rowSearchList))

    @staticmethod
    def _printFunc(project, item: StarIo.NmrDataBlock | StarIo.NmrSaveFrame | StarIo.NmrLoop):
        """Print the contents of a saveFrame/dataBlock - results generated from _contentNef
        Loops are included in the saveFrame
        """
        if getattr(item, CONTENTATTR, None):  # may occasionally be a dataBlock
            leader = item.name + ':' + item.category + ' - '
            leaderSpace = ' ' * len(leader)
            for name, thisSet in item._content.items():
                leaderName = name + ' - '
                leaderNameSpace = ' ' * len(leaderName)
                viewList = list(thisSet or ['empty'])
                CMAX = 7
                for cCount, v in enumerate(viewList[:CMAX + 1]):
                    print('{}{}{}'.format(leader, leaderName,
                                          v if cCount < CMAX else
                                          '... {} more'.format(len(viewList) - CMAX)))
                    leader = leaderSpace
                    leaderName = leaderNameSpace

    def testPrint(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                  traverseFunc=None,
                  *, selection: dict | None = None):
        """Print the contents of the nef dict
        """
        return self.traverseDataBlock(project, dataBlock, traverseFunc=self._printFunc)

    @staticmethod
    def _clearSaveFrame(project, saveFrame):
        """Clear the contents of a saveFrame/dataBlock - results generated with _contentNef
        """
        setattr(saveFrame, CONTENTATTR, None)
        setattr(saveFrame, ROWERRORATTR, None)

    def clearSaveFrames(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                        traverseFunc=None,
                        *, selection: dict | None = None,
                        ):
        """Clear the contents and rowErrors of the nef dict
        """
        setattr(dataBlock, CONTENTATTR, None)
        setattr(dataBlock, ROWERRORATTR, None)
        return self.traverseDataBlock(project, dataBlock, traverseFunc=self._clearSaveFrame, selection=None)

    def traverseDataBlock(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                          traverseFunc: typing.Callable,
                          *, selection: dict | None = None,
                          ):
        """Traverse the saveFrames in the correct order
        """
        # NOTE:ED - keep a record of the current datablock
        self._dataBlock = dataBlock

        result = _traverse(self, project, dataBlock, traverseFunc, selection=selection)

        self._dataBlock = None
        return result

    def importExistingProject(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                              projectIsEmpty: bool = True,
                              selection: typing.Optional[dict] = None):
        """Import selection from dataBlock into existing/empty Project
        """
        # Initialise mapping dicts
        if not hasattr(self, '_dataSet2ItemMap') or projectIsEmpty:
            self._dataSet2ItemMap = {}
        if not hasattr(self, '_nmrResidueMap') or projectIsEmpty:
            self._nmrResidueMap = {}

        self.importNewProject(project, dataBlock=dataBlock, projectIsEmpty=projectIsEmpty, )  #selection=selection)

    def importNewProject(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                         projectIsEmpty: bool = True,
                         # selection: typing.Optional[dict] = None
                         ):
        """Import entire project from dataBlock into empty Project"""

        t0 = time.time()

        self.warnings = []
        self.project = project
        self.defaultChainCode = None
        self._deferredItems = []

        # temporarily store the new/overwrite existing state for load methods
        self._projectIsEmpty = projectIsEmpty

        saveframeOrderedDict = self._getSaveFramesInOrder(dataBlock)

        # Load metadata and molecular system first
        metaDataFrame = dataBlock.get('nef_nmr_meta_data')
        if metaDataFrame:
            self._saveFrameName = 'nef_nmr_meta_data'
            self.load_nef_nmr_meta_data(project, metaDataFrame)
            del saveframeOrderedDict['nef_nmr_meta_data']

        saveFrame = dataBlock.get('nef_molecular_system')
        if saveFrame and (self._importAll or self._importDict.get(saveFrame.name)):
            self._saveFrameName = 'nef_molecular_system'

            # NOTE:ED - caution here - this creates a substance called Molecule_1
            self.load_nef_molecular_system(project, saveFrame)
            del saveframeOrderedDict['nef_molecular_system']

        # Load assignments, or preload from shiftlists
        # to make sure '@' and '#' identifiers match the right serials
        saveFrame = dataBlock.get('ccpn_assignment')
        if saveFrame and (self._importAll or self._importDict.get(saveFrame.name)):
            self._saveFrameName = 'ccpn_assignment'
            self.load_ccpn_assignment(project, saveFrame)
            del saveframeOrderedDict['ccpn_assignment']
        else:
            self.preloadAssignmentData(dataBlock)

        # t1 = time.time()
        # print ('@~@~ NEF load starting frames', t1-t0)

        for sf_category, saveFrames in saveframeOrderedDict.items():
            for saveFrame in saveFrames:
                saveFrameName = self._saveFrameName = saveFrame.name

                # NOTE:ED - need spectrum saveFrames here for restraint Links
                if sf_category == 'nef_nmr_spectrum':
                    getLogger().debug2('>>>  -- SPECTRUM {}'.format(saveFrameName))

                    peakListSerial = _stripSpectrumSerial(saveFrameName) or saveFrame.get('ccpn_peaklist_serial') or 1
                    self._frameCodeToSpectra[saveFrameName] = peakListSerial

                elif sf_category in ['nef_distance_restraint_list',
                                     'nef_dihedral_restraint_list',
                                     'nef_rdc_restraint_list',
                                     'ccpn_restraint_list',
                                     'ccpn_distance_restraint_violation_list',
                                     'ccpn_dihedral_restraint_violation_list',
                                     'ccpn_rdc_restraint_violation_list',
                                     ]:
                    # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
                    name = saveFrameName[len(sf_category) + 1:]
                    sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT
                    # dataSetSerial = saveFrame.get('ccpn_dataset_serial')
                    # if dataSetSerial is not None:
                    #     ss = '`%s`' % dataSetSerial
                    #     if name.startswith(ss):
                    #         name = name[len(ss):]
                    # else:
                    #     dataSetSerial = 1
                    name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''
                    self._frameCodeToSpectra[saveFrameName] = sDataName  # or dataSetSerial or 1

                elif sf_category == 'nef_chemical_shift_list':
                    # needs to be more generic
                    if '.' in str(saveFrameName):
                        # make sure the chemicalShiftList name does not contain a '.'
                        saveFrameName = saveFrameName.replace('.', '_')

                # if selection and str(saveFrameName) not in selection:
                #     getLogger().debug2('>>>  -- skip saveframe {}'.format(saveFrameName))
                #     continue
                # getLogger().debug2('>>> loading saveframe {}'.format(saveFrameName))

                importer = self.importers.get(sf_category)
                if importer is None:
                    getLogger().warning(f'Unknown saveframe category {sf_category}: {saveFrameName}')
                else:
                    # NB - newObject may be project, for some saveframes.

                    if not (self._importAll or self._importDict.get(saveFrame.name)):
                        # skip items not in the selection list
                        continue

                    result = importer(self, project, saveFrame)
                    if isinstance(result, AbstractWrapperObject):
                        self.frameCode2Object[saveFrameName] = result
                    # elif not isinstance(result, list):
                    #   self.warning("Unexpected return %s while reading %s" %
                    #                (result, saveFrameName))

                    # Handle unmapped elements
                    extraTags = [x for x in saveFrame
                                 if x not in (nef2CcpnMap.get(sf_category) or {})
                                 and x not in ('sf_category', 'sf_framecode')]
                    if extraTags:
                        pass
                        # getLogger().warning(f'Unused tags in saveframe {saveFrameName}: {extraTags}')
                        # TODO put here function that stashes data in object, or something

        # process deferred loops
        for defer in self._deferredItems:
            if not defer.func:
                raise RuntimeError('deferred item has no function')

            # call the deferred function
            defer.func(defer.spectrum, defer.loop, defer.saveFrame, defer.peakListId)

        # Put metadata in main dataset
        self.updateMetaData(metaDataFrame)

        t2 = time.time()
        getLogger().debug('Loaded NEF file, time = %.2fs' % (t2 - t0))

        for msg in self.warnings:
            getLogger().warning(f'{msg}')
        self.project = None

    def importNewNMRStarProject(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                                projectIsEmpty: bool = True):
        """Import entire project from dataBlock into empty Project"""

        t0 = time.time()

        self.warnings = []
        self.project = project
        self.defaultChainCode = None

        saveframeOrderedDict = self._getSaveFramesInOrder(dataBlock)

        # these sections below check each of the saveframes, extract the relevant information
        # and then discard if they are no longer required
        # the following saveframes can then be checked to find the corrct one holding the
        # chemical shift list information

        # # Load metadata and molecular system first
        # metaDataFrame = dataBlock['nef_nmr_meta_data']
        # self._saveFrameName = 'nef_nmr_meta_data'
        # self.load_nef_nmr_meta_data(project, metaDataFrame)
        # del saveframeOrderedDict['nef_nmr_meta_data']
        #
        # saveFrame = dataBlock.get('nef_molecular_system')
        # if saveFrame:
        #   self._saveFrameName = 'nef_molecular_system'
        #   self.load_nef_molecular_system(project, saveFrame)
        # del saveframeOrderedDict['nef_molecular_system']
        #
        # # Load assignments, or preload from shiftlists
        # # to make sure '@' and '#' identifiers match the right serials
        # saveFrame = dataBlock.get('ccpn_assignment')
        # if saveFrame:
        #   self._saveFrameName = 'ccpn_assignment'
        #   self.load_ccpn_assignment(project, saveFrame)
        #   del saveframeOrderedDict['ccpn_assignment']
        # else:
        #   self.preloadAssignmentData(dataBlock)

        # t1 = time.time()
        # print ('@~@~ NEF load starting frames', t1-t0)

        for sf_category, saveFrames in saveframeOrderedDict.items():
            for saveFrame in saveFrames:
                saveFrameName = self._saveFrameName = saveFrame.name

                importer = self.importers.get(sf_category)
                if importer is None:
                    getLogger().warning(f'Unknown saveframe category {sf_category}: {saveFrameName}')
                else:
                    # NB - newObject may be project, for some saveframes.

                    if not (self._importAll or self._importDict.get(saveFrame.name)):
                        # skip items not in the selection list
                        continue

                    result = importer(self, project, saveFrame)
                    if isinstance(result, AbstractWrapperObject):
                        self.frameCode2Object[saveFrameName] = result
                    # elif not isinstance(result, list):
                    #   self.warning("Unexpected return %s while reading %s" %
                    #                (result, saveFrameName))

                    # Handle unmapped elements
                    extraTags = [x for x in saveFrame
                                 if x not in (nef2CcpnMap.get(sf_category) or {})
                                 and x not in ('sf_category', 'sf_framecode')]
                    if extraTags:
                        pass
                        # getLogger().warning(f'Unused tags in saveframe {saveFrameName}: {extraTags}')
                        # TODO put here function that stashes data in object, or something

        # Put metadata in main dataset
        # self.updateMetaData(metaDataFrame)

        t2 = time.time()
        getLogger().debug('Loaded NEF file, time = %.2fs' % (t2 - t0))

        for msg in self.warnings:
            getLogger().warning(f'{msg}')
        self.project = None

    def _verifyLoops(self, project: Project, saveFrame: StarIo.NmrSaveFrame, addLoopAttribs=None,
                     excludeList=(), **kwds):
        """Iterate over the loops in a saveFrame, and verify contents
        """
        mapping = nef2CcpnMap.get(saveFrame.category) or {}

        if getattr(saveFrame, ROWERRORATTR, None) is None:
            # reset the errors for the loop/saveframe/datablock
            print(f'==> _verifyLoops  {saveFrame}')
            saveFrame._rowErrors = AttrDict()
        for tag, ccpnTag in mapping.items():
            if tag not in excludeList and ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop:
                    saveFrame._rowErrors[loop.name] = OrderedSet()
                    verify = self.verifiers.get(tag)
                    if verify:
                        if addLoopAttribs:
                            dd = []
                            for name in addLoopAttribs:
                                dd.append(saveFrame.get(name))
                            verify(self, project, loop, saveFrame, *dd, **kwds)
                        else:
                            verify(self, project, loop, saveFrame, **kwds)

    def _noLoopVerify(self, project: Project, loop: StarIo.NmrLoop, *arg, **kwds):
        """Verify the contents of the loop
        This is a loop that requires no verification
        """
        pass

    def _getLoops(self, project: Project, saveFrame: StarIo.NmrSaveFrame, excludeList=(), **kwds):
        """Iterate over the loops in a saveFrame, and add to a list"""
        result = ()
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if tag not in excludeList and ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop:
                    content = self.contentFuncs[tag]
                    result += (loop,)

        return result

    def _updateStringParameters(self, params, attribs=DEFAULTUPDATEPARAMETERS):
        """Update the values in the parameters that should be None|str
        """
        for attrib in attribs:
            val = params.get(attrib, None)
            if val is not None:
                params[attrib] = str(val)

    def load_nef_nmr_meta_data(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load nef_nmr_meta_data saveFrame"""

        # Other data are read in here at the end of the load
        self.mainDataSetSerial = saveFrame.get('ccpn_dataset_serial')

        formatName = saveFrame.get('format_name')
        formatVersion = saveFrame.get('format_version')
        if formatName == 'nmr_exchange_format':
            if formatVersion:
                try:
                    version = float(formatVersion)
                except ValueError:
                    raise ValueError("Illegal version string %s for nmr_exchange_format"
                                     % formatVersion)
                else:
                    if version < minimumNefVersion:
                        raise ValueError("Unsupported nef file version %s; minimum version is %s"
                                         % (formatVersion, minimumNefVersion))
            else:
                project._logger.warning("NEF file format version missing: Reading may fail.")

        else:
            project._logger.warning("NEF file format name '%s', not recognised. Reading may fail."
                                    % formatName)

        return None

        # TODO - store data in this saveframe
        # for now we store none of this, as the storage slots are in DataSet, not Project
        # Maybe for another load function?

    #
    importers['nef_nmr_meta_data'] = load_nef_nmr_meta_data

    def verify_nef_nmr_meta_data(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify nef_nmr_meta_data saveFrame"""
        self.mainDataSetSerial = saveFrame.get('ccpn_dataset_serial')

        formatName = saveFrame.get('format_name')
        formatVersion = saveFrame.get('format_version')
        if formatName == 'nmr_exchange_format':
            if formatVersion:
                try:
                    version = float(formatVersion)
                except ValueError:
                    self.error('Illegal version string {} for nmr_exchange_format'.format(formatVersion), saveFrame, None)
                else:
                    if version < minimumNefVersion:
                        self.error('Unsupported nef file version {}; minimum version is {}'.format(formatVersion, minimumNefVersion), saveFrame, None)
            else:
                self.warning('file format version missing: Reading may fail', saveFrame)
        else:
            self.warning("NEF file format name '{}', not recognised. Reading may fail.".format(formatName), saveFrame)

    verifiers['nef_nmr_meta_data'] = verify_nef_nmr_meta_data
    # not strictly needed
    verifiers['nef_related_entries'] = _noLoopVerify
    verifiers['nef_program_script'] = _noLoopVerify
    verifiers['nef_run_history'] = _noLoopVerify

    def load_ccpn_logging(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_logging saveFrame"""

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        name = framecode[len(category) + 1:]
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                # special case, uses the loopName for the storage name
                importer(self, project, loop, saveFrame, loopName)

    importers['ccpn_logging'] = load_ccpn_logging

    def verify_ccpn_logging(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify ccpn_logging saveFrame"""
        from ccpn.framework.lib.ccpnNef.CcpnNefLogging import CCPNLOGGING

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        # name = framecode[len(category) + 1:]

        # Verify main object
        # result = project.getCcpnNefLogging(name)
        data = project._data or {}
        result = data.get(CCPNLOGGING)
        if result is not None:
            self.error('ccpn_logging - ccpnLogging {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (CCPNLOGGING,)

    verifiers['ccpn_logging'] = verify_ccpn_logging
    verifiers['ccpn_history'] = _noLoopVerify

    def load_ccpn_history(self, project: Project, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                          name: str):
        """Serves to load ccpn_history loops"""
        from ccpn.framework.lib.ccpnNef.CcpnNefLogging import setCcpnNefLog

        if loop and loop.data:
            # if loop.data exists then load as a pandas dataFrame
            _df = pd.DataFrame(loop.data)

            # store in the project
            setCcpnNefLog(project, name, _df, overwrite=True)

    importers['ccpn_history'] = load_ccpn_history

    def load_nef_molecular_system(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load nef_molecular_system saveFrame"""

        mapping = nef2CcpnMap.get('nef_molecular_system') or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop:
                    importer = self.importers[tag]
                    importer(self, project, loop, saveFrame)
        #
        return None

    #
    importers['nef_molecular_system'] = load_nef_molecular_system
    verifiers['nef_molecular_system'] = _verifyLoops

    def _checkImport(self, saveFrame, checkItem, checkID='_importRows'):
        if not self._importAll:

            # ejb - need to remove the rogue `n` at the beginning of the name if it exists
            #       as it is passed into the namespace and gets added iteratively every save
            #       next three lines remove all occurrences of `n` from name
            name = saveFrame.name
            name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''

            _importList = self._importDict.get(name)  # need to remove any trailing `<n>`
            if _importList:
                _importRows = _importList.get(checkID) or []
                if checkItem not in _importRows:
                    return False
        return True

    def load_nef_sequence(self, project: Project, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """Load nef_sequence loop"""

        result = []

        chainData = {}
        for row in loop.data:
            chainCode = row['chain_code']
            ll = chainData.get(chainCode)
            if ll is None:
                chainData[chainCode] = [row]
            else:
                ll.append(row)

        defaultChainCode = None
        if None in chainData:
            defaultChainCode = 'A'
            # Replace chainCode None with default chainCode
            # Selecting the first value that is not already taken.
            while defaultChainCode in chainData:
                defaultChainCode = commonUtil.incrementName(defaultChainCode)
            chainData[defaultChainCode] = chainData.pop(None)
            for row in chainData[defaultChainCode]:
                row['chain_code'] = defaultChainCode
            # NOTE:ED - need to rename option in _importList - affects flag below

        self.defaultChainCode = defaultChainCode

        sequence2Chain = {}
        tags = ('residue_name', 'linking', 'residue_variant')
        for chainCode, rows in sorted(chainData.items()):

            # NOTE:ED - adding flags to restrict importing to the selection
            if not self._checkImport(saveFrame, chainCode):
                continue

            self._updateStringParameters(rows[0], attribs=('ccpn_chain_comment',))
            compoundName = rows[0].get('ccpn_compound_name')
            role = rows[0].get('ccpn_chain_role')
            comment = rows[0].get('ccpn_chain_comment')

            for row in rows:
                if row.get('linking') == 'dummy':
                    row['residue_name'] = 'dummy.' + row['residue_name']
            sequence = tuple(tuple(row.get(tag) for tag in tags) for row in rows)

            lastChain = sequence2Chain.get(sequence)
            if lastChain is None:
                newSubstance = project.fetchNefSubstance(sequence=rows, name=compoundName)
                newChain = newSubstance.createChain(shortName=chainCode, role=role,
                                                    comment=comment)
                sequence2Chain[sequence] = newChain

                # Set variant codes:
                for ii, residue in enumerate(newChain.residues):
                    variantCode = sequence[ii][2]

                    if variantCode:

                        # keep so I can find the place again
                        # atomNamesRemoved, atomNamesAdded = residue._wrappedData.getAtomNameDifferences()

                        for code in variantCode.split(','):
                            code = code.strip()  # Should not be necessary but costs nothing to catch those errors
                            atom = residue.getAtom(code[1:])
                            if code[0] == '-':
                                if atom is None:
                                    self.error("Incorrect variantCode %s: No atom named %s found in %s. Skipping ..."
                                               % (variantCode, code, residue), loop)
                                else:
                                    atom.delete()

                            elif code[0] == '+':
                                if atom is None:
                                    residue.newAtom(name=code[1:])
                                else:
                                    self.warning("Incorrect variantCode %s: Atom named %s already present in %s. Skipping ..."
                                                 % (variantCode, code, residue), loop)

                            else:
                                self.error("Incorrect variantCode %s: must start with '+' or '-'. Skipping ..."
                                           % variantCode, loop)

            else:
                newChain = lastChain.clone(shortName=chainCode)
                newChain.role = role
                newChain.comment = comment

            for apiResidue in newChain._wrappedData.sortedResidues():
                # Necessary to guarantee against name clashes
                # Direct access to avoid unnecessary notifiers
                apiResidue.__dict__['seqInsertCode'] = '__@~@~__'
            for ii, apiResidue in enumerate(newChain._wrappedData.sortedResidues()):
                # NB we have to loop over API residues to be sure we get the residues
                # in creation order rather than sorted order
                residue = project._data2Obj[apiResidue]
                residue.rename(rows[ii].get('sequence_code'))
                residue._resetIds()

            # Necessary as notification is blanked here:
            newChain._resetIds()

            #
            result.append(newChain)

            # Add Residue comments
            for ii, residue in enumerate(newChain.residues):
                comment = rows[ii].get('ccpn_comment')
                if comment is not None:
                    residue.comment = str(comment)
        #
        return result

    #
    importers['nef_sequence'] = load_nef_sequence

    def verify_nef_sequence(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
        """verify nef_sequence loop"""
        chainData = OD()
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
        _chainErrors = parentFrame._rowErrors[loop.name + '_chain_code'] = OrderedSet()

        for row in loop.data:
            chainCode = row['chain_code']
            ll = chainData.get(chainCode)
            if ll is None:
                chainData[chainCode] = [row]
            else:
                ll.append(row)

        defaultChainCode = None
        if None in chainData:
            defaultChainCode = 'A'
            # Replace chainCode None with default chainCode
            # Selecting the first value that is not already taken.
            while defaultChainCode in chainData:
                defaultChainCode = commonUtil.incrementName(defaultChainCode)
            chainData[defaultChainCode] = chainData.pop(None)
        self.defaultChainCode = defaultChainCode

        sequence2Chain = {}
        tags = ('residue_name', 'linking', 'residue_variant')
        for chainCode, rows in sorted(chainData.items()):
            compoundName = rows[0].get('ccpn_compound_name')
            # role = rows[0].get('ccpn_chain_role')
            # comment = rows[0].get('ccpn_chain_comment')
            for row in rows:
                if row.get('linking') == 'dummy':
                    row['residue_name'] = 'dummy.' + row['residue_name']
            sequence = tuple(tuple(row.get(tag) for tag in tags) for row in rows)

            lastChain = sequence2Chain.get(sequence)
            if lastChain is None:
                # newSubstance = project.fetchNefSubstance(sequence=rows, name=compoundName)
                newSubstance = project.getNefSubstance(sequence=rows, name=compoundName)
                if newSubstance is not None:
                    self.error('nef_sequence - Substance {} already exists'.format(newSubstance), loop, (newSubstance,))

                    # # add the row to all errors, and add to specific chain error
                    # for code, sRows in chainData.items():
                    #     if row in sRows:
                    #         for thisRow in sRows:
                    #             _rowErrors.add(loop.data.index(thisRow))
                    #         # add to errors for this chain
                    #         parentFrame._rowErrors['_'.join([loop.name, chainCode])] = OrderedSet([loop.data.index(tRow) for tRow in sRows])

                result = project.getChain(chainCode)
                if result is not None:
                    self.error('nef_sequence - Chain {} already exists'.format(result), loop, (result,))
                    _chainErrors.add(chainCode)

                    # add the row to all errors, and add to specific chain error
                    for thisRow in rows:
                        _rowErrors.add(loop.data.index(thisRow))
                    # add to errors for this chain
                    parentFrame._rowErrors['_'.join([loop.name, chainCode])] = OrderedSet([loop.data.index(tRow) for tRow in rows])

    verifiers['nef_sequence'] = verify_nef_sequence

    def load_nef_covalent_links(self, project: Project, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """Load nef_sequence loop"""

        result = []

        for row in loop.data:
            id1 = Pid.createId(*(row[x] for x in ('chain_code_1', 'sequence_code_1',
                                                  'residue_name_1', 'atom_name_1',)))
            id2 = Pid.createId(*(row[x] for x in ('chain_code_2', 'sequence_code_2',
                                                  'residue_name_2', 'atom_name_2',)))
            atom1 = project.getAtom(id1)
            atom2 = project.getAtom(id2)
            if atom1 is None:
                self.warning("Unknown atom %s for bond to %s. Skipping..." % (id1, id2), loop)
            elif atom2 is None:
                self.warning("Unknown atom %s for bond to %s. Skipping..." % (id2, id1), loop)
            else:
                result.append((atom1, atom2))
                atom1.addInterAtomBond(atom2, 'disulfide')
        #
        return result

    #
    importers['nef_covalent_links'] = load_nef_covalent_links
    verifiers['nef_covalent_links'] = _noLoopVerify

    def preloadAssignmentData(self, dataBlock: StarIo.NmrDataBlock):
        """Set up NmrChains and NmrResidues with reserved names to ensure the serials are OK
    and create NmrResidues in connected nmrChains in order

    NB later we can store serials in CCPN projects, but something is needed that works anyway

    NB, without CCPN-specific tags you can NOT guarantee that connected stretches are stable,
    and that serials are put back where they came from.
    This heuristic creates NmrResidues in connected stretches in the order they are found,
    but this will break if connected stretches appear in multiple shiftlists and some are partial."""

        project = self.project

        assignmentData = {}
        for saveFrameName, saveFrame in dataBlock.items():

            # get all NmrResidue data in chemicalshift lists
            if saveFrameName.startswith('nef_chemical_shift_list'):
                loop = saveFrame.get('nef_chemical_shift')
                if loop:
                    for row in loop.data:
                        # NB the self.defaultChainCode guards against chainCode being None
                        chainCode = row['chain_code'] or self.defaultChainCode

                        nmrResidues = assignmentData.get(chainCode, OD())
                        assignmentData[chainCode] = nmrResidues
                        nmrResidues[(row['sequence_code'], row['residue_name'])] = None

        # Create objects with reserved names
        for chainCode in sorted(assignmentData):

            if chainCode[0] in '@#' and chainCode[1:].isdigit():
                # reserved name - make chain
                try:
                    project.fetchNmrChain(chainCode)
                except ValueError:
                    # Could not be done, probably because we have NmrChain '@1'. Leave for later
                    pass

        assignmentData2 = {}
        for chainCode, nmrResidues in sorted(assignmentData.items()):

            # Create NmrChain
            try:
                nmrChain = project.fetchNmrChain(chainCode)
            except ValueError:
                nmrChain = project.fetchNmrChain('`%s`' % chainCode)

            if nmrChain.isConnected:
                # Save data for later processing
                assignmentData2[nmrChain] = nmrResidues
            else:
                # Create non-assigned NmrResidues to reserve the serials. The rest can wait
                for sequenceCode, residueType in list(nmrResidues.keys()):
                    if sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
                        nmrChain.fetchNmrResidue(sequenceCode=sequenceCode, residueType=residueType)

        for nmrChain, nmrResidues in sorted(assignmentData2.items()):
            # Create NmrResidues in order, to preserve connection order
            for sequenceCode, residueType in list(nmrResidues.keys()):
                # This time we want all non-offset, regardless of type - as we must get them in order
                if (len(sequenceCode) < 2 or sequenceCode[-2] not in '+-'
                        or not sequenceCode[-1].isdigit()):
                    # I.e. for sequenceCodes that do not include an offset
                    nmrChain.fetchNmrResidue(sequenceCode=sequenceCode, residueType=residueType)

    def verify_preloadAssignmentData(self, dataBlock: StarIo.NmrDataBlock):
        """Set up NmrChains and NmrResidues with reserved names to ensure the serials are OK
        and create NmrResidues in connected nmrChains in order"""

        # NOTE:ED - need to check and validate this bit

        project = self.project

        for saveFrameName, saveFrame in dataBlock.items():

            # get all NmrResidue data in chemicalshift lists
            assignmentData = {}
            if saveFrameName.startswith('nef_chemical_shift_list'):
                loop = saveFrame.get('nef_chemical_shift')
                if loop:
                    for row in loop.data:
                        # NB the self.defaultChainCode guards against chainCode being None
                        chainCode = row['chain_code'] or self.defaultChainCode

                        nmrResidues = assignmentData.get(chainCode, OD())
                        assignmentData[chainCode] = nmrResidues
                        nmrResidues[(row['sequence_code'], row['residue_name'])] = None

        # Create objects with reserved names
        for chainCode in sorted(assignmentData):

            if chainCode[0] in '@#' and chainCode[1:].isdigit():
                # reserved name - make chain
                nmrChain = project.getNmrChain(chainCode)
                if nmrChain:
                    self.warning('nmrChain {} already exists'.format(nmrChain), dataBlock)

    def load_nef_chemical_shift_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load nef_chemical_shift_list saveFrame"""

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        name = str(framecode[len(category) + 1:])
        if '.' in name:
            name = name.replace('.', '_')
            self.warning(f'chemicalShiftList name contains "." replacing with {name}')

        # parameters['name'] = framecode[len(category) + 1:]
        parameters['name'] = name
        parameters.pop('serial', 1)  # not required

        # Make main object
        result = project.getChemicalShiftList(name) or project.newChemicalShiftList(**parameters)
        if self.defaultChemicalShiftList is None:
            # ChemicalShiftList should default to the unique ChemicalShIftList in the file
            # A file with multiple ChemicalShiftLists MUST have explicit chemical shift lists
            # given for all spectra- but this is not the place for validity checking
            self.defaultChemicalShiftList = result

        if self.testing:
            # When testing you want the values to remain as read
            result.autoUpdate = False
            # NB The above is how it ought to work.
            # The below is how it is working as of July 2016
            result._wrappedData.topObject.shiftAveraging = False

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)

        return result

    importers['nef_chemical_shift_list'] = load_nef_chemical_shift_list

    def verify_nef_chemical_shift_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify nef_chemical_shift_list saveFrame"""

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        name = str(framecode[len(category) + 1:])
        if '.' in name:
            # flag that chemicalShiftList contains bad characters - need ability to store errors
            self.error(f'nef_chemical_shift_list - ChemicalShiftList {name} contains bad character "."', saveFrame)
            saveFrame._rowErrors[category] = (name,)

        # Verify main object
        result = project.getChemicalShiftList(name)
        if result is not None:
            self.error('nef_chemical_shift_list - ChemicalShiftList {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (name,)

        self._verifyLoops(project, saveFrame, name=name)

    verifiers['nef_chemical_shift_list'] = verify_nef_chemical_shift_list

    def load_ccpn_datatable(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_datatable saveFrame"""

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        parameters['name'] = framecode[len(category) + 1:]
        parameters.pop('serial', 1)  # not required
        columns = saveFrame.get('ccpn_datatable_columns')
        if columns:
            columns = json.loads(columns)

        # Make main object
        result = project.newDataTable(**parameters)
        # try:
        #     result._resetSerial(serial)
        # except Exception as es:
        #     self.warning('Could not set serial for {} to {}'.format(result, serial), saveFrame)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)

        # set columns back to the correct non-nef values
        if columns:
            result.data.columns = columns

        return result

    importers['ccpn_datatable'] = load_ccpn_datatable

    def verify_ccpn_datatable(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify ccpn_datatable saveFrame"""

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        name = framecode[len(category) + 1:]

        # Verify main object
        result = project.getDataTable(name)
        if result is not None:
            self.error('ccpn_datatable - DataTable {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (name,)

        self._verifyLoops(project, saveFrame, name=name)

    verifiers['ccpn_datatable'] = verify_ccpn_datatable

    def load_ccpn_datatable_metadata(self, data: Data, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                     run_id: str = '', itemLength: int = None):
        """Serves to load ccpn_<type>_datatable_metadata loops"""

        if loop and loop.data:
            for row in loop.data:
                name = row.get('name')
                parameter = row.get('parameter')

                data.setMetadata(name, json.loads(parameter))

    importers['ccpn_datatable_metadata'] = load_ccpn_datatable_metadata

    def load_ccpn_datatable_data(self, data: Data, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                 run_id: str = '', itemLength: int = None):
        """Serves to load ccpn_<type>_datatable_data loop"""

        if loop and loop.data:
            _df = pd.DataFrame(loop.data)
            data.data = _df

    importers['ccpn_datatable_data'] = load_ccpn_datatable_data

    def _ordered_dict_prepend(self, dct, key, value, dict_setitem=dict.__setitem__):
        """Prepend an item to an OrderedDict
        """
        # NOTE:ED - this may be needed if the ordering of datablock is important
        #           may be okay as use _getSaveFramesInOrder...
        root = dct._OrderedDict__root
        first = root[1]

        if key in dct:
            link = dct._OrderedDict__map[key]
            link_prev, link_next, _ = link
            link_prev[1] = link_next
            link_next[0] = link_prev
            link[0] = root
            link[1] = first
            root[1] = first[0] = link
        else:
            root[1] = first[0] = dct._OrderedDict__map[key] = [root, first, key]
            dict_setitem(dct, key, value)

    def _getNewName(self, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...], saveFrame, itemName, newName, contentItem, descriptor):

        currentItems = set()
        for dataBlock in contentDataBlocks:
            _contentFrame = dataBlock.get(saveFrame.name)
            _content = getattr(_contentFrame, CONTENTATTR, {}) if _contentFrame else {}
            # itemName is the current item
            currentItems |= (_content.get(contentItem) or set())

        if newName:
            # check not in the current list
            if newName in currentItems:
                raise ValueError("{} {} already exists".format(descriptor, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            newName = itemName if itemName not in ['.', None] else '1'
            while newName in currentItems:
                newName = commonUtil.incrementName(newName)

        return newName

    def _getNewSequence(self, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...], saveFrame, itemName, newName, contentItem, prefix, _highCount):

        currentItems = set()
        for dataBlock in contentDataBlocks:
            _contentFrame = dataBlock.get(saveFrame.name)
            _content = getattr(_contentFrame, CONTENTATTR, {}) if _contentFrame else {}
            # itemName is the current item
            currentItems |= (_content.get(contentItem) or set())

        # iterate through the names to find the first that is not taken yet
        newName = int(itemName[len(prefix):])
        _newHighCount = max(_highCount, max(*currentItems) if currentItems else 1) + 1
        newName = '{}{}'.format(prefix, _newHighCount)

        return newName, _newHighCount

    def _getNewNameDataBlock(self, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...], saveFrame: StarIo.NmrSaveFrame,
                             itemName, newName, contentItem, descriptor):

        def incrementName(name):
            """Add '.1' to name or change suffix '.n' to '.(n+1)
            Assume that the current Pid.IDSEP is '.'
            """
            ll = name.rsplit(Pid.IDSEP, 1)
            if len(ll) == 2:
                try:
                    ll[1] = str(int(ll[1]) + 1)
                    return Pid.IDSEP.join(ll)

                except ValueError:
                    pass

            return name + Pid.IDSEP + '1'

        # if dataBlock:
        #     _content = getattr(dataBlock, CONTENTATTR, {})
        #     # itemName is the current item name
        #     currentItems = getattr(_content, 'loopSet', [])
        # else:
        #     raise RuntimeError('dataBlock not defined')

        currentItems = set()
        for dataBlock in contentDataBlocks:
            _content = getattr(dataBlock, CONTENTATTR, {})
            # itemName is the current item
            currentItems |= set(getattr(_content, 'loopSet', []))

        if newName:
            # check not in the current list
            if newName in currentItems:
                raise ValueError("{} {} already exists".format(descriptor, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            newName = itemName
            while newName in currentItems:
                newName = incrementName(newName)

        return newName

    def _renameDataBlock(self, project, dataBlock, saveFrame, newSaveFrameName):
        """Rename the key of a datBlock because the saveFrame.name has changed in the connected saveFrame
        """
        oldName = saveFrame.name
        saveFrame.name = newSaveFrameName

        # replace all occurrences of the saveframe name in the datablock
        self.searchReplace(project, dataBlock, True, None, oldName, newSaveFrameName, replace=True)
        saveFrame['sf_framecode'] = newSaveFrameName

        data = [(k, val) for k, val in dataBlock.items()]
        for ii, (k, val) in enumerate(data):
            if val == saveFrame:
                getLogger().debug('found {} {} --> {}'.format(saveFrame, k, val))
                data[ii] = (newSaveFrameName, val)
                # should only be one
                break
        newData = OD((k, val) for k, val in data)
        dataBlock.clear()
        dataBlock.update(newData)

    def _renameDataBlockSpectra(self, project, dataBlock, category, oldSpectrum, spectrum, oldSerial, newSerial):
        """Rename all saveFrames matching the spectrum_name
        """
        # filter data to spectra
        def getSpectra(dbItem):
            key, sFrame = dbItem
            frameId = _saveFrameNameFromCategory(sFrame)
            if frameId.subname == oldSpectrum and frameId.category == 'nef_nmr_spectrum':
                return (key, sFrame, frameId)
        # get the spectrum save-frames with the same name
        spectrumData = sorted(filter(None, map(lambda dd: getSpectra(dd), dataBlock.items())))

        for ii, (k, sFrame, _frameID) in enumerate(spectrumData):
            # _frameID = _saveFrameNameFromCategory(sFrame)
            _framecode, _frameName, subName, prefix, postfix, _preSerial, _postSerial, _category = _frameID

            if _postSerial is not None and _postSerial == oldSerial and _postSerial != newSerial:
                postfix = f'`{newSerial}`'
            lSerial = _stripSpectrumSerial(_frameID) or sFrame.get('ccpn_peaklist_serial') or 1
            newName = '_'.join([category, prefix + spectrum + postfix])

            # NOTE:ED - search for any multiplet/integral-lists that reference this save-frame
            #       for future, if only renaming specific
            if True:  # lSerial == oldSerial:
                # this is the save-frame to change
                # newFrame = deepcopy(sFrame)  # reserved for changing specific peak-lists

                self._renameDataBlock(project, dataBlock, sFrame, newName)
                if sFrame.get('ccpn_peaklist_serial') is not None and lSerial == oldSerial:
                    # if None, is extracted from the save-frame name (or 1)
                    sFrame['ccpn_peaklist_serial'] = newSerial

                # rename the spectra in the spectrum-groups
                loopList = ('ccpn_group_spectrum', 'ccpn_multiplet_peaks')
                replaceList = ('nmr_spectrum_id', 'peak_spectrum')
                self.searchReplace(project, dataBlock, True, None, oldSpectrum, spectrum, replace=True,
                                   loopSearchList=loopList, rowSearchList=replaceList, attributeSearchList=(None,))

                # # rename the spectra in the multiplet_peaks
                # loopList = ('ccpn_multiplet_peaks',)
                # replaceList = ('peak_spectrum',)
                # self.searchReplace(project, dataBlock, True, None, oldSpectrum, spectrum, replace=True,
                #                    loopSearchList=loopList, rowSearchList=replaceList, attributeSearchList=(None,))

                # dataBlock.addItem(newFrame['sf_framecode'], newFrame)  # reserved for changing specific peak-lists

    def rename_saveframe(self, project: Project,
                         dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                         saveFrame: StarIo.NmrSaveFrame,
                         itemName=None, newName=None):
        """Rename a saveFrame
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        # category = saveFrame['sf_category']
        # framecode = saveFrame['sf_framecode']
        # if not itemName or newName == itemName:
        #     return

        if newName == itemName:
            return

        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        frameList = frames.get(category) or []
        frameNames = [_saveFrameNameFromCategory(frame).framecode for frame in frameList]

        if newName:
            newSaveFrameName = '_'.join([category, prefix + newName + postfix])
            if newSaveFrameName in frameNames:
                raise ValueError("{} name '{}' already exists".format(category, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            newSaveFrameName = '_'.join([category, prefix + itemName + postfix])
            newName = itemName
            while newSaveFrameName in frameNames:
                # newSaveFrameName = commonUtil.incrementName(newSaveFrameName)
                newName = commonUtil.incrementName(newName)
                newSaveFrameName = '_'.join([category, prefix + newName + postfix])
                # newName = _getNameFromCategory(category, newSaveFrameName).frameName

        if newName is not None:
            # oldName = framecode
            # saveFrame.name = newSaveFrameName
            #
            # # replace all occurrences of the saveframe name in the datablock
            # self.searchReplace(project, dataBlock, True, None, oldName, newSaveFrameName, replace=True)

            # # remove the old saveFrame in the dataBlock and replace with the new
            # # NOTE:ED - may need to check dict ordering here
            # del dataBlock[oldName]
            # dataBlock[newSaveFrameName] = saveFrame
            self._renameDataBlock(project, dataBlock, saveFrame, newSaveFrameName)

            # search in additionalData for the pid and change
            self._checkAdditionalDataCollections(category, dataBlock, frames, itemName, newName, project)

        return newName

    def rename_ccpn_table(self, project: Project,
                          dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                          saveFrame: StarIo.NmrSaveFrame,
                          itemName=None, newName=None):
        """Rename a saveFrame
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        
        requires ccpn_structuredata_name
        """
        # category = saveFrame['sf_category']
        # framecode = saveFrame['sf_framecode']
        # if not itemName or newName == itemName:
        #     return

        if newName == itemName:
            return

        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        # frameList = frames.get(category) or []

        frameList = []
        # HACK to get the full list of restraint/violation_lists
        if category.endswith('restraint_list'):
            for k, v in frames.items():
                if k.endswith('restraint_list'):
                    frameList += (frames.get(k) or [])

        elif category.endswith('violation_list'):
            for k, v in frames.items():
                if k.endswith('violation_list'):
                    frameList += (frames.get(k) or [])

        else:
            return

        # restrict the search to the names in the current structureData
        frameList = [fr for fr in frameList if fr.get('ccpn_structuredata_name') == saveFrame.get('ccpn_structuredata_name')]

        frameNames = [_saveFrameNameFromCategory(frame).framecode for frame in frameList]
        # get the list of just the subName from the saveFrame
        _shortNames = [_saveFrameNameFromCategory(frame).subname for frame in frameList]
        if newName:
            newSaveFrameName = '_'.join([category, prefix + newName + postfix])
            # if newSaveFrameName in frameNames:
            if newName in _shortNames:
                raise ValueError("{} name '{}' already exists".format(category, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            newSaveFrameName = '_'.join([category, prefix + itemName + postfix])
            newName = itemName
            while newName in _shortNames:
                # while newSaveFrameName in frameNames:
                # newSaveFrameName = commonUtil.incrementName(newSaveFrameName)
                newName = commonUtil.incrementName(newName)
                newSaveFrameName = '_'.join([category, prefix + newName + postfix])
                # newName = _getNameFromCategory(category, newSaveFrameName).frameName

        if newName is not None:
            # oldName = framecode
            # saveFrame.name = newSaveFrameName
            #
            # # replace all occurrences of the saveframe name in the datablock
            # self.searchReplace(project, dataBlock, True, None, oldName, newSaveFrameName, replace=True)

            # # remove the old saveFrame in the dataBlock and replace with the new
            # # NOTE:ED - may need to check dict ordering here
            # del dataBlock[oldName]
            # dataBlock[newSaveFrameName] = saveFrame
            self._renameDataBlock(project, dataBlock, saveFrame, newSaveFrameName)

            # search in additionalData for the pid and change
            if category in NAMETOOBJECTMAPPING:
                obj = NAMETOOBJECTMAPPING[category]

                frameCats = frames.get('ccpn_additional_data') or []
                frameList = [frame.name for frame in frameCats]
                attList = ('None',)
                loopList = ('ccpn_internal_data',)
                replaceList = ('ccpn_object_pid', 'internal_data_string',)

                sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT

                # rename the items in the additionalData saveFrame
                _oldPid = Pid.Pid._join(obj.shortClassName, sDataName, itemName)
                _newPid = Pid.Pid._join(obj.shortClassName, sDataName, newName)
                # rename the items in the additionalData saveFrame
                _oldLongPid = Pid.Pid._join(obj.className, sDataName, itemName)
                _newLongPid = Pid.Pid._join(obj.className, sDataName, newName)

                # need different search
                self.searchReplaceDict(project, dataBlock, True, None,
                                       (f'(\"{_oldPid}\")', f'(\"{_oldLongPid}\")'),
                                       (f'\"{_newPid}\"', f'\"{_newLongPid}\"'),
                                       replace=True, validFramesOnly=True,
                                       frameSearchList=frameList, attributeSearchList=attList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

                self._replaceInCollections(dataBlock, _oldPid, _newPid, _oldLongPid, _newLongPid)

        return newName

    def rename_nef_molecular_system(self, project: Project,
                                    dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                                    saveFrame: StarIo.NmrSaveFrame,
                                    itemName=None, newName=None):
        """Rename a chain in a nef_sequence
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        # category = saveFrame['sf_category']
        # framecode = saveFrame['sf_framecode']
        if itemName is None or newName == itemName:
            return

        newName = self._getNewName(contentDataBlocks, saveFrame, itemName, newName, 'nef_sequence_chain_code', 'Chain')

        # NOTE:ED - check which are chains and which are nmr_chains
        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID
        frames = self._getSaveFramesInOrder(dataBlock)
        # frameCats = frames.get(category) or []

        frameList = ['None']  #_saveFrameNameFromCategory(frame).framecode for frame in frameCats if _saveFrameNameFromCategory(frame).fr]
        loopList = ('nef_sequence', 'nef_chemical_shift_list')
        replaceList = ('chain_code', 'complex_chain_code',
                       'chain_code_1', 'chain_code_2', 'chain_code_3', 'chain_code_4', 'chain_code_5',
                       'chain_code_6', 'chain_code_7', 'chain_code_8', 'chain_code_9', 'chain_code_10',
                       'chain_code_11', 'chain_code_12', 'chain_code_13', 'chain_code_14', 'chain_code_15',
                       'ccpn_tensor_chain_code', 'tensor_chain_code')
        self.searchReplace(project, dataBlock, True, None, itemName, newName, replace=True,
                           frameSearchList=frameList, rowSearchList=replaceList, loopSearchList=loopList)

        loopList = ('nef_peak', 'nef_covalent_links', 'nef_chemical_shift',
                    'nef_distance_restraint', 'nef_dihedral_restraint', 'nef_rdc_restraint', 'ccpn_restraint',
                    'ccpn_distance_restraint_violation', 'ccpn_dihedral_restraint_violation', 'ccpn_rdc_restraint_violation')
        replaceList = ()
        self.searchReplaceChain(project, dataBlock, True, None, itemName, newName, replace=True,
                                frameSearchList=frameList, rowSearchList=replaceList, loopSearchList=loopList)

        # update in the additionalData saveFrames
        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        # search in additionalData for the pid and change
        if category in NAMETOOBJECTMAPPING:
            frameCats = frames.get('ccpn_additional_data') or []
            frameList = [frame.name for frame in frameCats]
            attList = ('None',)
            loopList = ('ccpn_internal_data',)
            replaceList = ('ccpn_object_pid', 'internal_data_string',)

            for (obj, _pre, _post) in ((Chain, '(\"{}\")', '\"{}\"'),
                                       (Residue, r'(?:\"{}\.)(.*?)\"', '\"{}.\\1\"'),
                                       (Atom, r'(?:\"{}\.)(.*?)\"', '\"{}.\\1\"'),
                                       ):
                # rename the items in the additionalData saveFrame
                _oldPid = Pid.Pid._join(obj.shortClassName, itemName)
                _newPid = Pid.Pid._join(obj.shortClassName, newName)
                # rename the items in the additionalData saveFrame
                _oldLongPid = Pid.Pid._join(obj.className, itemName)
                _newLongPid = Pid.Pid._join(obj.className, newName)

                # need different search
                self.searchReplaceDict(project, dataBlock, True, None,
                                       (_pre.format(_oldPid), _pre.format(_oldLongPid)),
                                       (_post.format(_newPid), _post.format(_newLongPid)),
                                       replace=True, validFramesOnly=True,
                                       frameSearchList=frameList, attributeSearchList=attList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

                self._replaceInCollections(dataBlock, _oldPid, _newPid, _oldLongPid, _newLongPid)

        return newName

    def rename_ccpn_assignment(self, project: Project,
                               dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                               saveFrame: StarIo.NmrSaveFrame,
                               itemName=None, newName=None):
        """Rename an nmr_chain in a ccpn_assignment
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        if itemName is None or newName == itemName:
            return

        newName = self._getNewName(contentDataBlocks, saveFrame, itemName, newName, 'nmr_chain', 'NmrChain')

        # NOTE:ED - check which are chains and which are nmr_chains
        loopList = ('nmr_chain', 'nmr_residue', 'nmr_atom', 'nef_peak')
        replaceList = ('chain_code', 'complex_chain_code',
                       'chain_code_1', 'chain_code_2', 'chain_code_3', 'chain_code_4', 'chain_code_5',
                       'chain_code_6', 'chain_code_7', 'chain_code_8', 'chain_code_9', 'chain_code_10',
                       'chain_code_11', 'chain_code_12', 'chain_code_13', 'chain_code_14', 'chain_code_15',
                       'ccpn_tensor_chain_code', 'tensor_chain_code', 'short_name')
        self.searchReplace(project, dataBlock, True, None, itemName, newName, replace=True,
                           loopSearchList=loopList, rowSearchList=replaceList, attributeSearchList=(None,))

        loopList = ('nef_chemical_shift')
        replaceList = ('chain_code',)
        self.searchReplace(project, dataBlock, True, None, itemName, newName, replace=True,
                           loopSearchList=loopList, rowSearchList=replaceList, attributeSearchList=(None,))

        # update in the additionalData saveFrames
        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        # search in additionalData for the pid and change
        if category in NAMETOOBJECTMAPPING:
            frameCats = frames.get('ccpn_additional_data') or []
            frameList = [frame.name for frame in frameCats]
            attList = ('None',)
            loopList = ('ccpn_internal_data',)
            replaceList = ('ccpn_object_pid', 'internal_data_string',)

            for (obj, _pre, _post) in ((NmrChain, '(\"{}\")', '\"{}\"'),
                                       (NmrResidue, r'(?:\"{}\.)(.*?)\"', '\"{}.\\1\"'),
                                       (NmrAtom, r'(?:\"{}\.)(.*?)\"', '\"{}.\\1\"'),
                                       ):
                # rename the items in the additionalData saveFrame
                _oldPid = Pid.Pid._join(obj.shortClassName, itemName)
                _newPid = Pid.Pid._join(obj.shortClassName, newName)
                # rename the items in the additionalData saveFrame
                _oldLongPid = Pid.Pid._join(obj.className, itemName)
                _newLongPid = Pid.Pid._join(obj.className, newName)

                # need different search
                self.searchReplaceDict(project, dataBlock, True, None,
                                       (_pre.format(_oldPid), _pre.format(_oldLongPid)),
                                       (_post.format(_newPid), _post.format(_newLongPid)),
                                       replace=True, validFramesOnly=True,
                                       frameSearchList=frameList, attributeSearchList=attList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

                self._replaceInCollections(dataBlock, _oldPid, _newPid, _oldLongPid, _newLongPid)

        return newName

    def rename_ccpn_assignment_sequence_code(self, project: Project,
                                             dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                                             saveFrame: StarIo.NmrSaveFrame,
                                             itemName=None, newName=None):
        """Rename sequenceCode/serial number for @<n> nmrResidues
        """
        nmrChainLoopName = 'nmr_chain'
        nmrResidueLoopName = 'nmr_residue'
        nmrAtomLoopName = 'nmr_atom'
        nmrSequenceCodeName = 'nmr_sequence_codes'
        nmrAtomCodeName = 'nmr_atom_names'

        nmrChains = OrderedSet()
        nmrResidues = OrderedSet()
        nmrAtoms = OrderedSet()
        nmrSequenceCodes = OrderedSet()

        # read nmr_residue loop - add the details to nmrChain/nmrResidue/nmrAtom lists
        tempResidueDict = {}
        _highestSequenceCount = 0

        mapping = nef2CcpnMap.get(nmrResidueLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrResidueLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['chain_code']
            sequenceCode = row['sequence_code']

            # NOTE:ED - change sequenceCode
            if chainCode == itemName and sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
                newSequence, _highestSequenceCount = self._getNewSequence(contentDataBlocks, saveFrame, sequenceCode, None, 'nmr_sequence_codes', '@',
                                                                          _highestSequenceCount)

                # replace sequenceCode/serial
                loopList = ('nmr_residue', 'nmr_atom', 'nef_chemical_shift')
                replaceList = ('chain_code', 'sequence_code')
                self.searchReplaceList(project, dataBlock, True, None, (chainCode, sequenceCode), (chainCode, newSequence), replace=True,
                                       attributeSearchList=replaceList,
                                       loopSearchList=loopList, rowSearchList=replaceList)
                loopList = ('nmr_residue',)
                replaceList = ('chain_code', 'serial')
                self.searchReplaceList(project, dataBlock, True, None, (chainCode, int(sequenceCode[1:])), (chainCode, int(newSequence[1:])), replace=True,
                                       attributeSearchList=replaceList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

                # special replace sequenceCode/serial in nef_peak
                loopList = ('nef_peak',)
                replaceList = ('chain_code', 'sequence_code')
                self.searchReplaceLoopListNumbered(project, dataBlock, True, None, (chainCode, sequenceCode), (chainCode, newSequence), replace=True,
                                                   attributeSearchList=replaceList,
                                                   loopSearchList=loopList, rowSearchList=replaceList)

        mapping = nef2CcpnMap.get(nmrAtomLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrAtomLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['chain_code']
            sequenceCode = row['sequence_code']
            name = row['name']

            # NOTE:ED - change name
            if chainCode == itemName and name[0:2] == '?@' and name[2:].isdigit():
                newName, _highestSequenceCount = self._getNewSequence(contentDataBlocks, saveFrame, name, None, 'nmr_atom_names', '?@', _highestSequenceCount)

                # replace sequenceCode/serial
                loopList = ('nmr_atom',)
                replaceList = ('chain_code', 'name')
                self.searchReplaceList(project, dataBlock, True, None, (chainCode, name), (chainCode, newName), replace=True,
                                       attributeSearchList=replaceList,
                                       loopSearchList=loopList, rowSearchList=replaceList)
                loopList = ('nmr_atom',)
                replaceList = ('chain_code', 'serial')
                self.searchReplaceList(project, dataBlock, True, None, (chainCode, int(name[2:])), (chainCode, int(newName[2:])), replace=True,
                                       attributeSearchList=replaceList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

    def rename_ccpn_note(self, project: Project,
                         dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                         saveFrame: StarIo.NmrSaveFrame,
                         itemName=None, newName=None):
        """Rename a ccpn_note in ccpn_notes
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        if itemName is None or newName == itemName:
            return

        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        newName = self._getNewName(contentDataBlocks, saveFrame, itemName, newName, 'ccpn_notes', 'Note')

        loopList = ('ccpn_note')
        replaceList = ('name')
        self.searchReplace(project, dataBlock, True, None, itemName, newName, replace=True,
                           loopSearchList=loopList, rowSearchList=replaceList)

        # search in additionalData for the pid and change
        self._checkAdditionalDataCollections(category, dataBlock, frames, itemName, newName, project)

        return newName

    def _replaceInCollections(self, dataBlock: StarIo.NmrDataBlock, oldPid, newPid, oldLongPid, newLongPid):
        """Replace the pids of the object type in collections
        """

        saveframeOrderedDict = self._getSaveFramesInOrder(dataBlock)
        for sf_category, saveFrames in saveframeOrderedDict.items():
            for saveFrame in saveFrames:

                if sf_category == 'ccpn_collections':
                    _renames = ((f'"{oldPid}"', f'"{newPid}"'),
                                (f'"{oldLongPid}"', f'"{newLongPid}"'),
                                (f"'{oldPid}'", f"'{newPid}'"),
                                (f"'{oldLongPid}'", f"'{newLongPid}'"),
                                )

                    # replace the names in the collection.items
                    if (loop := saveFrame.get('ccpn_collection')):
                        for row in loop.data:
                            if (_items := row.get('items')):
                                # must be wrapped in quotes to exclude subsets
                                for _old, _new in _renames:
                                    _items = _items.replace(_old, _new)
                                row['items'] = _items

    def rename_ccpn_collection(self, project: Project,
                               dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                               saveFrame: StarIo.NmrSaveFrame,
                               itemName=None, newName=None):
        """Rename a ccpn_collection in ccpn_collections
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        if itemName is None or newName == itemName:
            return

        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        newName = self._getNewName(contentDataBlocks, saveFrame, itemName, newName, 'ccpn_collections', 'Collection')

        loopList = ('ccpn_collection')
        replaceList = ('name')
        self.searchReplace(project, dataBlock, True, None, itemName, newName, replace=True,
                           loopSearchList=loopList, rowSearchList=replaceList)

        # search in additionalData for the pid and change
        self._checkAdditionalDataCollections(category, dataBlock, frames, itemName, newName, project)

        return newName

    def _getNewListName(self, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...], saveFrame, itemName, newName, contentItem, descriptor):

        def incrementName(name):
            """Add '.1' to name or change suffix '.n' to '.(n+1) 
            Assume that the current Pid.IDSEP is '.'
            """
            ll = name.rsplit(Pid.IDSEP, 1)
            if len(ll) == 2:
                try:
                    ll[1] = str(int(ll[1]) + 1)
                    return Pid.IDSEP.join(ll)

                except ValueError:
                    pass

            return name + Pid.IDSEP + '1'

        currentItems = set()
        for dataBlock in contentDataBlocks:
            _contentFrame = dataBlock.get(saveFrame.name)
            _content = getattr(_contentFrame, CONTENTATTR, {}) if _contentFrame else {}
            # itemName is the current item
            currentItems |= (_content.get(contentItem) or set())

        if newName:
            # check not in the current list
            if newName in currentItems:
                raise ValueError("{} {} already exists".format(descriptor, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            newName = itemName
            while newName in currentItems:
                newName = incrementName(newName)

        return newName

    def _getNewSerial(self, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...], saveFrame, itemSerial, newSerial, contentItem, descriptor):

        def incrementSerial(serial):
            """Add '.1' to serial or change suffix '.n' to '.(n+1) 
            Assume that the current Pid.IDSEP is '.'
            """
            try:
                ll = str(int(serial) + 1)
                return ll

            except ValueError:
                pass
            return '1'

        currentItems = set()
        for dataBlock in contentDataBlocks:
            _contentFrame = dataBlock.get(saveFrame.name)
            _content = getattr(_contentFrame, CONTENTATTR, {}) if _contentFrame else {}
            # itemName is the current item
            currentItems |= (_content.get(contentItem) or set())

        if newSerial:
            # check not in the current list
            if newSerial in currentItems:
                raise ValueError("{} {} already exists".format(descriptor, newSerial))
        else:
            # iterate through the serials to find the first that is not taken yet
            newSerial = itemSerial
            while newSerial in currentItems:
                newSerial = incrementSerial(newSerial)

        return newSerial

    def rename_ccpn_list(self, project: Project,
                         dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                         saveFrame: StarIo.NmrSaveFrame,
                         itemName=None, newName=None, _lowerCaseName='none'):
        """Rename a ccpn_list in a ccpn_assignment
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        category = saveFrame['sf_category']
        if itemName is None or newName == itemName:
            return

        _upperCaseName = _lowerCaseName.capitalize()
        newName = self._getNewListName(contentDataBlocks, saveFrame, itemName, newName,
                                       'ccpn_{}_list'.format(_lowerCaseName),
                                       '{}List'.format(_upperCaseName))
        try:
            # split name into spectrum.serial
            oldSpectrum, oldSerial = itemName.split(Pid.IDSEP)
            if not (oldSpectrum or oldSerial):
                raise
            oldSerial = int(oldSerial)
            spectrum, newSerial = newName.split(Pid.IDSEP)
            if not (spectrum or newSerial):
                raise
            newSerial = int(newSerial)
        except Exception as es:
            raise TypeError('Incorrect {}List definition; must be <spectrum>.<serial>'.format(_upperCaseName))

        _frameID = _saveFrameNameFromCategory(saveFrame)
        # if spectrum != _frameID.subname:
        #     raise ValueError('{}List prefix cannot be changed; must be <spectrum>.<serial>'.format(_upperCaseName))

        if True:  #oldSerial != newSerial:
            frames = self._getSaveFramesInOrder(dataBlock)
            frameCats = frames.get(category) or []
            # get all saveframes attached to this spectrum - for ccpn
            # frameList = ['None']
            frameList = [frame.name for frame in frameCats if _saveFrameNameFromCategory(frame).subname == _frameID.subname]
            attList = ('None',)
            loopList = [loopName.format(_lowerCaseName)
                        for loopName in ('ccpn_{}_list', 'ccpn_{}', 'ccpn_{}_peaks')]
            replaceList = ('serial', '{}_list_serial'.format(_lowerCaseName))
            self.searchReplace(project, dataBlock, True, None, oldSerial, newSerial, replace=True, validFramesOnly=True,
                               frameSearchList=frameList, attributeSearchList=attList,
                               loopSearchList=loopList, rowSearchList=replaceList)

        # need to rename the matching-key in dataBlock
        self._renameDataBlockSpectra(project, dataBlock, category, oldSpectrum, spectrum, oldSerial, newSerial)
        self._checkAllSpectrumRename(dataBlock, oldSpectrum, spectrum, category, project)

        return newName

        # # rename the items in the additionalData saveFrame
        # _oldLongPid = Pid.Pid._join(f'{_upperCaseName}List', itemName)
        # _newLongPid = Pid.Pid._join(f'{_upperCaseName}List', newName)
        #
        # frameCats = frames.get('ccpn_additional_data') or []
        # frameList = [frame.name for frame in frameCats]
        # attList = ('None',)
        # loopList = [loopName.format(_lowerCaseName) for loopName in ('ccpn_internal_data',)]
        # replaceList = ('ccpn_object_pid',)
        # self.searchReplace(project, dataBlock, True, None, _oldLongPid, _newLongPid, replace=True, validFramesOnly=True,
        #                    frameSearchList=frameList, attributeSearchList=attList,
        #                    loopSearchList=loopList, rowSearchList=replaceList)
        #
        # # search in additionalData for the pid and change
        # self._checkAdditionalDataCollections(_lowerCaseName, dataBlock, frames, itemName, newName, project)
        #
        # return newName

    # def rename_ccpn_peak_cluster_list(self, project: Project,
    #                                   dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
    #                                   saveFrame: StarIo.NmrSaveFrame,
    #                                   itemName=None, newName=None):
    #     """Rename a ccpn_peak_cluster in ccpn_peak_cluster_list
    #     :param itemName: name of the item to rename - dependent on saveFrame type
    #     :param newName: new item name or None to autorename to next available name
    #     """
    #     if not itemName or newName == itemName:
    #         return
    #
    #     newName = self._getNewSerial(contentDataBlocks, saveFrame, itemName, newName, 'ccpn_peak_cluster', 'PeakCluster')
    #
    #     try:
    #         oldSerial = int(itemName)
    #         newSerial = int(newName)
    #     except Exception as es:
    #         raise TypeError('Incorrect PeakCluster definition; must be <int>')
    #
    #     frameList = ('None',)
    #     loopList = ('ccpn_peak_cluster', 'ccpn_peak_cluster_peaks')
    #     replaceList = ('serial', 'peak_cluster_serial')
    #     self.searchReplace(project, dataBlock, True, None, oldSerial, newSerial, replace=True,
    #                        frameSearchList=frameList, loopSearchList=loopList, rowSearchList=replaceList)
    #
    #     return newName

    def rename_ccpn_substance(self, project: Project,
                              dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                              saveFrame: StarIo.NmrSaveFrame,
                              itemName=None, newName=None):
        """Rename a ccpn_substance
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """

        def incrementName(name):
            """Add '_1' to name or change suffix '_n' to '_(n+1)
            Assume that the current Pid.IDSEP is '.'
            """
            ll = name.rsplit(Pid.IDSEP, 1)
            if len(ll) == 2:
                try:
                    ll[0] = str(int(ll[0]) + 1)
                    return Pid.IDSEP.join(ll)

                except ValueError:
                    pass

            return Pid.IDSEP.join([name + '_1', 'None'])

        category = saveFrame['sf_category']
        if itemName is None or newName == itemName:
            return

        _lowerCaseName = 'substance'
        _upperCaseName = _lowerCaseName.capitalize()

        _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        frames = None
        for contentBlock in contentDataBlocks:
            framesBlock = self._getSaveFramesInOrder(contentBlock)
            if not frames:
                frames = framesBlock
            else:
                # merge the frames dict
                frames = self._mergeSaveFramesInOrder(frames, framesBlock)

        frameCats = frames.get(category) or []
        frameList = [_saveFrameNameFromCategory(frame).framecode for frame in frameCats]

        try:
            # split name into spectrum.serial
            oldName, oldLabelling = itemName.split(Pid.IDSEP)
            if not (oldName or oldLabelling):
                raise
        except Exception as es:
            raise TypeError('Incorrect {} definition; must be <name>.<labelling>'.format(_upperCaseName))

        if newName:
            try:
                name, newLabelling = newName.split(Pid.IDSEP)
                if not (name or newLabelling):
                    raise
            except Exception as es:
                raise TypeError('Incorrect {} definition; must be <name>.<labelling>'.format(_upperCaseName))

            _framename = Pid.IDSEP.join([name, newLabelling or 'None'])
            newSaveFrameName = '_'.join([category, prefix + _framename + postfix])
            if newSaveFrameName in frameList:
                raise ValueError("{} name '{}' already exists".format(category, newName))
        else:
            # iterate through the names to find the first that is not taken yet
            name, newLabelling = oldName, oldLabelling
            _framename = Pid.IDSEP.join([name, newLabelling or 'None'])
            newSaveFrameName = '_'.join([category, prefix + _framename + postfix])
            newName = itemName
            while newSaveFrameName in frameList:
                name = commonUtil.incrementName(name)
                _framename = Pid.IDSEP.join([name, newLabelling or 'None'])
                newSaveFrameName = '_'.join([category, prefix + _framename + postfix])

        if newName is not None:
            # oldFramecode = framecode
            # saveFrame.name = newSaveFrameName
            saveFrame['name'] = name
            saveFrame['labelling'] = newLabelling

            # # replace all occurrences of the saveframe name in the datablock
            # self.searchReplace(project, dataBlock, True, None, oldFramecode, newSaveFrameName, replace=True)

            # replace name
            frameList = [frame.name for frame in frameCats if _saveFrameNameFromCategory(frame).category == 'ccpn_sample']
            loopList = ('ccpn_sample_component',)
            replaceList = ('name', 'labelling')
            self.searchReplaceList(project, dataBlock, True, None, (oldName, oldLabelling or None), (name, newLabelling or None), replace=True,
                                   frameSearchList=frameList, attributeSearchList=replaceList,
                                   loopSearchList=loopList, rowSearchList=replaceList)

            # remove the old saveFrame in the dataBlock and replace with the new
            self._renameDataBlock(project, dataBlock, saveFrame, newSaveFrameName)

            if category in NAMETOOBJECTMAPPING:
                obj = NAMETOOBJECTMAPPING[category]

                frameCats = frames.get('ccpn_additional_data') or []
                frameList = [frame.name for frame in frameCats]
                attList = ('None',)
                loopList = ('ccpn_internal_data',)
                replaceList = ('ccpn_object_pid', 'internal_data_string',)

                # rename the items in the additionalData saveFrame
                _oldPid = Pid.Pid._join(obj.shortClassName, itemName)
                _newPid = Pid.Pid._join(obj.shortClassName, name, newLabelling or '')
                # rename the items in the additionalData saveFrame
                _oldLongPid = Pid.Pid._join(obj.className, itemName)
                _newLongPid = Pid.Pid._join(obj.className, name, newLabelling or '')

                # need different search
                self.searchReplaceDict(project, dataBlock, True, None,
                                       (f'(\"{_oldPid}\")', f'(\"{_oldLongPid}\")'),
                                       (f'\"{_newPid}\"', f'\"{_newLongPid}\"'),
                                       replace=True, validFramesOnly=True,
                                       frameSearchList=frameList, attributeSearchList=attList,
                                       loopSearchList=loopList, rowSearchList=replaceList)

                self._replaceInCollections(dataBlock, _oldPid, _newPid, _oldLongPid, _newLongPid)

            return Pid.IDSEP.join([name, newLabelling])

        # if name != _frameID.subname:
        #     raise ValueError('{} prefix cannot be changed; must be <name>.<labelling>'.format(_upperCaseName))
        #
        # frames = self._getSaveFramesInOrder(dataBlock)
        # frameCats = frames.get(category) or []
        # # get all saveframes attached to this spectrum - for ccpn
        # frameList = ['None']  # [frame.name for frame in frameCats if _saveFrameNameFromCategory(frame).subname == _frameID.subname]
        #
        # loopList = [loopName.format(_lowerCaseName) for loopName in ('ccpn_{}_list', 'ccpn_{}', 'ccpn_{}_peaks')]
        # replaceList = ('serial', '{}_list_serial'.format(_lowerCaseName))
        # self.searchReplace(project, dataBlock, True, None, oldSerial, newSerial, replace=True,
        #                    frameSearchList=frameList, loopSearchList=loopList, rowSearchList=replaceList)

        return newName

    def rename_ccpn_peak_list(self, project: Project,
                              dataBlock: StarIo.NmrDataBlock, contentDataBlocks: Tuple[StarIo.NmrDataBlock, ...],
                              saveFrame: StarIo.NmrSaveFrame,
                              itemName=None, newName=None, _lowerCaseName='none'):
        """Rename a ccpn_list in a ccpn_assignment
        :param itemName: name of the item to rename - dependent on saveFrame type
        :param newName: new item name or None to autorename to next available name
        """
        category = saveFrame['sf_category']
        if itemName is None or newName == itemName:
            return

        _upperCaseName = _lowerCaseName.capitalize()
        newName = self._getNewNameDataBlock(contentDataBlocks, saveFrame, itemName, newName,
                                            'ccpn_{}_list'.format(_lowerCaseName),
                                            '{}List'.format(_upperCaseName))
        try:
            # split name into spectrum.serial
            oldSpectrum, oldSerial = itemName.split(Pid.IDSEP)
            if not (oldSpectrum or oldSerial):
                raise
            oldSerial = int(oldSerial)
            spectrum, newSerial = newName.split(Pid.IDSEP)
            if not (spectrum or newSerial):
                raise
            newSerial = int(newSerial)
        except Exception as es:
            raise TypeError('Incorrect {}List definition; must be <spectrum>.<serial>'.format(_upperCaseName))

        _frameID = _saveFrameNameFromCategory(saveFrame)
        # if spectrum != _frameID.subname:
        #     raise ValueError('{}List prefix cannot be changed; must be <spectrum>.<serial>'.format(_upperCaseName))

        frames = self._getSaveFramesInOrder(dataBlock)
        frameCats = frames.get(category) or []
        # get all saveframes attached to this spectrum - for ccpn
        frameList = ['None']  # [frame.name for frame in frameCats if _saveFrameNameFromCategory(frame).subname == _frameID.subname]

        # now need to update the serial number in the relevant saveFrames

        # _frameID = _saveFrameNameFromCategory(saveFrame)
        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

        # if postSerial is not None:
        # may not be necessary
        newFrameCode = '_'.join([category, prefix + spectrum + '`{}`'.format(newSerial)])
        # saveFrame.name = newFrameCode
        # saveFrame['sf_framecode'] = newFrameCode

        # CHECK:ED
        #   nef_peak                    ccpn_peak_list_serial
        #   ccpn_multiplet_peaks        peak_list_serial
        #   ccpn_integral_list
        #   ccpn_integral
        #   ccpn_integral_peaks         serial
        #                               integral_list_serial
        #   ccpn_multiplet_list
        #   ccpn_multiplet
        #   ccpn_multiplet_peaks        serial
        #                               multiplet_list_serial
        #   nef_nmr_spectrum
        #   ccpn_additional_data

        if oldSerial != newSerial:
            # if saveFrame.get('ccpn_peaklist_serial') is not None:
            #     saveFrame['ccpn_peaklist_serial'] = newSerial

            # replace the serial number in the nef_peak loop
            frameList = (newFrameCode,)
            loopList = ('nef_peak',)
            replaceList = ('ccpn_peak_list_serial',)
            self.searchReplace(project, dataBlock, True, None, oldSerial, newSerial, replace=True,
                               frameSearchList=frameList, loopSearchList=loopList, rowSearchList=replaceList)
            loopList = ('ccpn_multiplet_peaks',)
            replaceList = ('peak_list_serial',)
            self.searchReplace(project, dataBlock, True, None, oldSerial, newSerial, replace=True,
                               frameSearchList=frameList, loopSearchList=loopList, rowSearchList=replaceList)

        # # replace the spectrum/serial in the peak clusters
        # frameList = ('None',)
        # loopList = ('ccpn_peak_cluster_peaks', 'ccpn_multiplet_peaks')
        # replaceList = ('peak_spectrum', 'peak_list_serial')
        # self.searchReplaceList(project, dataBlock, True, None, (subName, oldSerial), (subName, newSerial), replace=True,
        #                        frameSearchList=frameList, loopSearchList=loopList, rowSearchList=replaceList)

        # need to rename the matching-key in dataBlock
        self._renameDataBlockSpectra(project, dataBlock, category, oldSpectrum, spectrum, oldSerial, newSerial)
        self._checkAllSpectrumRename(dataBlock, oldSpectrum, spectrum, category, project)

        # # rename the items in the additionalData saveFrame
        # _oldLongPid = Pid.Pid._join(f'{_upperCaseName}List', itemName)
        # _newLongPid = Pid.Pid._join(f'{_upperCaseName}List', newName)
        #
        # frameCats = frames.get('ccpn_additional_data') or []
        # frameList = [frame.name for frame in frameCats]
        # attList = ('None',)
        # loopList = [loopName.format(_lowerCaseName) for loopName in ('ccpn_internal_data',)]
        # replaceList = ('ccpn_object_pid',)
        # self.searchReplace(project, dataBlock, True, None, _oldLongPid, _newLongPid, replace=True, validFramesOnly=True,
        #                    frameSearchList=frameList, attributeSearchList=attList,
        #                    loopSearchList=loopList, rowSearchList=replaceList)
        #
        # # search in additionalData for the pid and change
        # self._checkAdditionalDataCollections(category, dataBlock, frames, itemName, newName, project)

        return newName

    def _checkAllSpectrumRename(self, dataBlock, oldSpectrum, spectrum, category, project):
        """Rename everything that could be a spectrumName
        """
        from ccpn.framework.lib.ccpnNef.CcpnNefSearch import SearchBasic, SearchDeep

        frames = self._getSaveFramesInOrder(dataBlock)

        for pidPrefix, _lowerCaseName, category in (('SP', 'spectrum', '_nef_spectrum'),
                                                    ('PL', 'peak_list', 'nef_nmr_spectrum'),
                                                    ('IL', 'integral_list', 'integral'),
                                                    ('ML', 'multiplet_list', 'multiplet'),
                                                    ('Spectrum', 'spectrum', '_nef_spectrum'),
                                                    ('PeakList', 'peak_list', 'nef_nmr_spectrum'),
                                                    ('IntegralList', 'integral_list', 'integral'),
                                                    ('MultipletList', 'multiplet_list', 'multiplet')):
            # rename the items in the additionalData saveFrame
            _oldPid = Pid.Pid._join(pidPrefix, oldSpectrum)
            _newPid = Pid.Pid._join(pidPrefix, spectrum)

            frameCats = frames.get('ccpn_additional_data') or []
            frameList = [frame.name for frame in frameCats]
            attList = ('None',)
            loopList = [loopName.format(_lowerCaseName) for loopName in ('ccpn_internal_data',)]
            replaceList = ('ccpn_object_pid',)
            # self.searchReplace(project, dataBlock, True, None, _oldLongPid, _newLongPid, replace=True, validFramesOnly=True,
            #                    frameSearchList=frameList, attributeSearchList=attList,
            #                    loopSearchList=loopList, rowSearchList=replaceList)

            search = SearchBasic(self.project, dataBlock, replace=True)
            search.replace(_oldPid, _newPid,
                           frameSearchList=frameList, attributeSearchList=attList,
                           loopSearchList=loopList, rowSearchList=replaceList)

            search = SearchDeep(self.project, dataBlock, replace=True)
            search.replace(_oldPid, _newPid, )

            # search in additionalData for the pid and change
            # self._checkAdditionalDataCollections(category, dataBlock, frames, oldSpectrum, spectrum, project)

    def _checkAdditionalDataCollections(self, category, dataBlock, frames, itemName, newName, project):
        if category in NAMETOOBJECTMAPPING:
            obj = NAMETOOBJECTMAPPING[category]

            frameCats = frames.get('ccpn_additional_data') or []
            frameList = [frame.name for frame in frameCats]
            attList = ('None',)
            loopList = ('ccpn_internal_data',)
            replaceList = ('ccpn_object_pid', 'internal_data_string',)

            # rename the items in the additionalData saveFrame
            _oldPid = Pid.Pid._join(obj.shortClassName, itemName)
            _newPid = Pid.Pid._join(obj.shortClassName, newName)
            # rename the items in the additionalData saveFrame
            _oldLongPid = Pid.Pid._join(obj.className, itemName)
            _newLongPid = Pid.Pid._join(obj.className, newName)

            # need different search
            self.searchReplaceDict(project, dataBlock, True, None,
                                   (f'(\"{_oldPid}\")', f'(\"{_oldLongPid}\")'),
                                   (f'\"{_newPid}\"', f'\"{_newLongPid}\"'),
                                   replace=True, validFramesOnly=True,
                                   frameSearchList=frameList, attributeSearchList=attList,
                                   loopSearchList=loopList, rowSearchList=replaceList)

            self._replaceInCollections(dataBlock, _oldPid, _newPid, _oldLongPid, _newLongPid)

    renames['nef_chemical_shift_list'] = rename_saveframe
    renames['nef_distance_restraint_list'] = rename_ccpn_table
    renames['nef_dihedral_restraint_list'] = rename_ccpn_table
    renames['nef_rdc_restraint_list'] = rename_ccpn_table
    renames['ccpn_restraint_list'] = rename_saveframe
    # renames['nef_peak_restraint_links'] = rename_saveframe
    renames['ccpn_sample'] = rename_saveframe
    renames['ccpn_complex'] = rename_saveframe
    renames['ccpn_spectrum_group'] = rename_saveframe
    renames['nef_sequence'] = rename_nef_molecular_system
    renames['nmr_chain'] = rename_ccpn_assignment
    renames['nmr_sequence_code'] = rename_ccpn_assignment_sequence_code
    renames['ccpn_integral_list'] = partial(rename_ccpn_list, _lowerCaseName='integral')
    renames['ccpn_multiplet_list'] = partial(rename_ccpn_list, _lowerCaseName='multiplet')
    renames['ccpn_peak_list'] = partial(rename_ccpn_peak_list, _lowerCaseName='peak')
    renames['ccpn_note'] = rename_ccpn_note
    # renames['ccpn_peak_cluster_list'] = rename_ccpn_peak_cluster_list
    renames['ccpn_substance'] = rename_ccpn_substance
    renames['ccpn_distance_restraint_violation_list'] = rename_ccpn_table
    renames['ccpn_dihedral_restraint_violation_list'] = rename_ccpn_table
    renames['ccpn_rdc_restraint_violation_list'] = rename_ccpn_table
    renames['ccpn_collection'] = rename_ccpn_collection
    renames['ccpn_datatable'] = rename_saveframe
    renames['ccpn_logging'] = rename_saveframe
    renames['ccpn_dataset'] = rename_saveframe

    # renames['ccpn_parameter'] = rename_saveframe

    def load_nef_chemical_shift(self, parent: ChemicalShiftList, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """load nef_chemical_shift loop
        """
        from ccpn.util.isotopes import name2ElementSymbol, DEFAULT_ISOTOPE_DICT

        result = []

        creatorFunc = parent.newChemicalShift

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            tt = tuple(row.get(tag) for tag in ('chain_code', 'sequence_code', 'residue_name',
                                                'atom_name'))
            element = row.get('element')
            isotope = row.get('isotope_number')
            if element not in DEFAULT_ISOTOPE_DICT:
                # Unknown / wrong element definition (Q instead of H is not valid)
                isotopeCode = None
            else:
                if element is not None:
                    if isotope:
                        isotopeCode = '%s%s' % (isotope, element.title())
                    else:
                        isotopeCode = DEFAULT_ISOTOPE_DICT.get(element.upper())
                elif isotope:
                    element = name2ElementSymbol(tt[3])
                    isotopeCode = '%s%s' % (isotope, element.title())
                else:
                    isotopeCode = None

            try:
                if (nmrResidue := self.produceNmrResidue(*tt[:3])) and \
                        (nmrAtom := self.produceNmrAtom(nmrResidue, tt[3], isotopeCode=isotopeCode)):
                    parameters['nmrAtom'] = nmrAtom
                parameters['static'] = row.get('ccpn_static') or False  # may be undefined for older nef files

                shift = creatorFunc(**parameters)
                shift._static = False if shift.chemicalShiftList.spectra else True

                result.append(shift)

            except ValueError as es:
                self.warning("Cannot produce NmrAtom for assignment %s. Skipping ChemicalShift" % (tt,), loop)
                # Should eventually be removed - raise while still testing
                # raise
        #
        return result

    #
    importers['nef_chemical_shift'] = load_nef_chemical_shift

    def verify_nef_chemical_shift(self, parent: ChemicalShiftList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, name=None):
        """verify nef_chemical_shift loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        if name is None:
            self.error('Undefined chemicalShiftList', loop, None)
            return

        # Verify main object
        shiftList = parent.getChemicalShiftList(name)
        if shiftList is None:
            return

        for row in loop.data:
            tt = tuple(row.get(tag) for tag in ('chain_code', 'sequence_code', 'residue_name',
                                                'atom_name'))
            shiftId = Pid.IDSEP.join(('' if x is None else str(x)) for x in tt)

            # find the chemicalShift
            shift = shiftList.getChemicalShift(shiftId)
            if shift is not None:
                self.error('nef_chemical_shift - ChemicalShift {} already exists'.format(shift), loop, (shift,))
                _rowErrors.add(loop.data.index(row))

    verifiers['nef_chemical_shift'] = verify_nef_chemical_shift

    def load_nef_restraint_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Serves to load nef_distance_restraint_list, nef_dihedral_restraint_list,
        nef_rdc_restraint_list and ccpn_restraint_list"""

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        if category == 'nef_distance_restraint_list':
            restraintType = 'Distance'
        elif category == 'nef_dihedral_restraint_list':
            restraintType = 'Dihedral'
        elif category == 'nef_rdc_restraint_list':
            restraintType = 'Rdc'
        else:
            restraintType = saveFrame.get('restraint_type')
            if not restraintType:
                self.warning("Missing restraint_type for saveFrame %s - value was %s" %
                             (framecode, restraintType),
                             saveFrame)
                return
        parameters['restraintType'] = restraintType
        namePrefix = restraintType[:3].capitalize() + '-'

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]

        # # replace the deprecated tag with the new tag
        # if DATANAME_DEPRECATED in saveFrame:
        #     if DATANAME not in saveFrame:
        #         saveFrame[DATANAME] = saveFrame.get(DATANAME_DEPRECATED) or DATANAME_DEFAULT  # cannot be empty
        #     del saveFrame[DATANAME_DEPRECATED]  # remove as new tag takes priority
        #
        sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''

        # Make main object
        sData = self.fetchStructureData(sDataName)

        # # need to fix the names here... cannot contain '.'
        # previous = sData.getRestraintTable(name)
        # if previous is not None:
        #     # NEF but NOT CCPN has separate namespaces for different restraint types,
        #     # so we may get name clashes
        #     # We should preserve NEF names, but it cannot be helped.
        #     if not name.startswith(namePrefix):
        #         # Add prefix for disambiguation since NEF but NOT CCPN has separate namespaces
        #         # for different constraint types
        #         name = namePrefix + name
        #         while sData.getRestraintTable(name) is not None:
        #             # This way we get a unique name even in the most bizarre cases
        #             name = '`%s`' % name

        # create a new restraintTable
        parameters['name'] = name
        parameters.pop('serial', 1)  # not required
        result = sData.newRestraintTable(**parameters)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                if loopName.endswith('_restraint'):
                    # There are no other loops currently, but if there ever is they will not need this
                    itemLength = saveFrame.get('restraint_item_length')

                    importer(self, result, loop, saveFrame, itemLength)
                else:
                    importer(self, result, loop, saveFrame)

        return result

    importers['nef_distance_restraint_list'] = load_nef_restraint_list
    importers['nef_dihedral_restraint_list'] = load_nef_restraint_list
    importers['nef_rdc_restraint_list'] = load_nef_restraint_list
    importers['ccpn_restraint_list'] = load_nef_restraint_list

    # from ccpn.util.decorators import profile
    #
    # @profile()
    def verify_nef_restraint_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Serves to verify nef_distance_restraint_list, nef_dihedral_restraint_list,
        nef_rdc_restraint_list and ccpn_restraint_list"""
        # Get ccpn-to-nef mapping for saveframe
        # _rowErrors = saveFrame._rowErrors[saveFrame.name] = OrderedSet()

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        if category == 'nef_distance_restraint_list':
            restraintType = 'Distance'
        elif category == 'nef_dihedral_restraint_list':
            restraintType = 'Dihedral'
        elif category == 'nef_rdc_restraint_list':
            restraintType = 'Rdc'
        else:
            restraintType = saveFrame.get('restraint_type')
            if not restraintType:
                self.warning("Missing restraint_type for saveFrame %s - value was %s" %
                             (framecode, restraintType), saveFrame)
                return
        parameters['restraintType'] = restraintType

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]

        # # replace the deprecated tag with the new tag
        # if DATANAME_DEPRECATED in saveFrame:
        #     if DATANAME not in saveFrame:
        #         saveFrame[DATANAME] = saveFrame.get(DATANAME_DEPRECATED) or DATANAME_DEFAULT  # cannot be empty
        #     del saveFrame[DATANAME_DEPRECATED]  # remove as new tag takes priority

        sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''

        sData = self.project.getStructureData(sDataName) if sDataName else None
        # Make main object
        if sData is not None:
            # find the restraintList
            restraintList = sData.getRestraintTable(name)
            if restraintList is not None:
                self.error('nef_restraint_list - RestraintTable {} already exists'.format(restraintList), saveFrame, (restraintList,))
                saveFrame._rowErrors[category] = (name,)

                self._verifyLoops(restraintList, saveFrame, name=name)

    verifiers['nef_distance_restraint_list'] = verify_nef_restraint_list
    verifiers['nef_dihedral_restraint_list'] = verify_nef_restraint_list
    verifiers['nef_rdc_restraint_list'] = verify_nef_restraint_list
    verifiers['ccpn_restraint_list'] = verify_nef_restraint_list

    def load_nef_restraint(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                           itemLength: int = None):
        """Serves to load nef_distance_restraint, nef_dihedral_restraint,
        nef_rdc_restraint and ccpn_restraint loops"""

        # NB Restraint.name - written out for dihedral restraints - is not read.
        # Which is probably OK, it is derived from the atoms.

        result = []

        string2ItemMap = self._dataSet2ItemMap[restraintTable.structureData]

        # set itemLength if not passed in:
        if not itemLength:
            itemLength = coreConstants.constraintListType2ItemLength.get(restraintTable.restraintType)

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        contributionTags = sorted(map2.values())
        restraints = {}
        # assignTags = ('chain_code', 'sequence_code', 'residue_name', 'atom_name')

        max = itemLength + 1
        multipleAttributes = OD((
            ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
            ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
            ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
            ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
            ))

        parametersFromLoopRow = _parametersFromLoopRow
        defaultChainCode = self.defaultChainCode
        for row in loop.data:

            # get or make restraint
            serial = row.get('restraint_id')
            restraint = restraints.get(serial)
            if restraint is None:
                valuesToContribution = {}
                dd = {}  # {'serial': serial}
                val = row.get('ccpn_vector_length')
                if val is not None:
                    dd['vectorLength'] = val
                val = row.get('ccpn_figure_of_Merit')
                if val is not None:
                    dd['figureOfMerit'] = val
                val = row.get('ccpn_comment')
                if val is not None:
                    dd['comment'] = str(val)
                restraint = restraintTable.newRestraint(**dd)
                try:
                    restraint._resetSerial(serial)
                except Exception as es:
                    self.warning('Could not set serial for {} to {}'.format(restraint, serial), loop)
                restraints[serial] = restraint
                result.append(restraint)

            # Get or make restraintContribution
            parameters = parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            combinationId = parameters.get('combinationId')
            nonAssignmentValues = tuple(parameters.get(tag) for tag in contributionTags)
            if combinationId:
                # Items in a combination are ANDed, so each line has one contribution
                contribution = restraint.newRestraintContribution(**parameters)
            else:
                contribution = valuesToContribution.get(nonAssignmentValues)
                if contribution is None:
                    contribution = restraint.newRestraintContribution(**parameters)
                    valuesToContribution[nonAssignmentValues] = contribution

            # Add item
            # ll = [row._get(tag)[:itemLength] for tag in assignTags]
            ll = [list(row.get(x) for x in y) for y in multipleAttributes.values()]
            # Reset missing chain codes to default
            # ll[0] = [x or defaultChainCode for x in ll[0]]

            idStrings = []
            for item in zip(*ll):
                if defaultChainCode is not None and item[0] is None:
                    # ChainCode missing - replace with default chain code
                    item = (defaultChainCode,) + item[1:]
                idStrings.append(Pid.IDSEP.join(('' if x is None else str(x)) for x in item))
            try:
                # create the contribution
                contribution.addRestraintItem(idStrings, string2ItemMap)

                # NOTE:ED - check with Eliza - create the required nmrAtoms/atoms
                for atm in idStrings:
                    if atm:
                        chn, seq, res, atmType = atm.split(Pid.IDSEP)
                        nmrChain = self.project.fetchNmrChain(chn)
                        if res:
                            nmrResidue = nmrChain.fetchNmrResidue(seq, res)
                        else:
                            nmrResidue = nmrChain.fetchNmrResidue(seq)
                        nmrResidue.fetchNmrAtom(atmType)

            except ValueError:
                self.warning("Cannot Add restraintItem %s. Identical to previous. Skipping" % idStrings, loop)

        #
        return result

    #
    importers['nef_distance_restraint'] = load_nef_restraint
    importers['nef_dihedral_restraint'] = load_nef_restraint
    importers['nef_rdc_restraint'] = load_nef_restraint
    importers['ccpn_restraint'] = load_nef_restraint

    def verify_nef_restraint(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                             name=None, itemLength: int = None):
        """Verify the contents of nef_distance_restraint, nef_dihedral_restraint,
        nef_rdc_restraint and ccpn_restraint loops"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        # string2ItemMap = self._dataSet2ItemMap[restraintTable.structureData]
        #
        # # set itemLength if not passed in:
        # if not itemLength:
        #     itemLength = coreConstants.constraintListType2ItemLength.get(restraintTable.restraintType)
        #
        # mapping = nef2CcpnMap.get(loop.name) or {}
        # map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        # contributionTags = sorted(map2.values())
        # restraints = {}
        # # assignTags = ('chain_code', 'sequence_code', 'residue_name', 'atom_name')
        #
        # max = itemLength + 1
        # multipleAttributes = OD((
        #     ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
        #     ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
        #     ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
        #     ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
        #     ))
        #
        # parametersFromLoopRow = self._parametersFromLoopRow
        # defaultChainCode = self.defaultChainCode
        for row in loop.data:
            # get restraint
            serial = row.get('restraint_id')
            restraint = restraintTable.getRestraint(serial)
            if restraint is not None:
                self.error('nef_restraint - Restraint {} already exists'.format(restraint), loop, (restraint,))
                _rowErrors.add(loop.data.index(row))

    verifiers['nef_distance_restraint'] = verify_nef_restraint
    verifiers['nef_dihedral_restraint'] = verify_nef_restraint
    verifiers['nef_rdc_restraint'] = verify_nef_restraint
    verifiers['ccpn_restraint'] = verify_nef_restraint

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def load_ccpn_restraint_violation_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Serves to load ccpn_restraint_violation_list"""

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        if category == 'ccpn_distance_restraint_violation_list':
            restraintType = 'Distance'
            itemLength = 2
        elif category == 'ccpn_dihedral_restraint_violation_list':
            restraintType = 'Dihedral'
            itemLength = 4
        elif category == 'ccpn_rdc_restraint_violation_list':
            restraintType = 'Rdc'
            itemLength = 2
        else:
            return
        #     restraintType = saveFrame.get('restraint_type')
        #     if not restraintType:
        #         self.warning("Missing restraint_type for saveFrame %s - value was %s" %
        #                      (framecode, restraintType),
        #                      saveFrame)
        #         return

        parameters['restraintType'] = restraintType
        namePrefix = restraintType[:3].capitalize() + '-'

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]

        # # replace the deprecated tag with the new tag
        # if DATANAME_DEPRECATED in saveFrame:
        #     if DATANAME not in saveFrame:
        #         saveFrame[DATANAME] = saveFrame.get(DATANAME_DEPRECATED) or DATANAME_DEFAULT  # cannot be empty
        #     del saveFrame[DATANAME_DEPRECATED]  # remove as new tag takes priority

        sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT
        columns = saveFrame.get('ccpn_restraint_violation_list_columns')
        if columns:
            columns = json.loads(columns)

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''

        run_id = parameters.get('runId')

        restraintId = Pid.IDSEP.join(('' if x is None else str(x)) for x in (sDataName, name))
        previous = project.getObjectsByPartialId(className='RestraintTable', idStartsWith=restraintId)

        # need to fix the names here... cannot contain '.'

        if previous and len(previous) == 1 and not sDataName:
            dataSet = previous[0].structureData
        else:
            # dataSet = project.newDataSet()
            dataSet = self.fetchStructureData(sDataName)

        # create a new violationTable
        parameters['name'] = name
        parameters.pop('serial', 1)  # not required
        result = dataSet.newViolationTable(name)
        # # create a new violationTable
        # result = dataSet.getViolationTable(name) or dataSet.newViolationTable(name)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                if loopName.endswith('_restraint_violation'):
                    # There are no other loops currently, but if there ever is they will not need this
                    # itemLength = saveFrame.get('restraint_item_length')

                    importer(self, result, loop, saveFrame, run_id, itemLength)
                else:
                    importer(self, result, loop, saveFrame)

        # set columns back to the correct non-nef values
        if columns:
            result.data.columns = columns

        return result

    importers['ccpn_distance_restraint_violation_list'] = load_ccpn_restraint_violation_list
    importers['ccpn_dihedral_restraint_violation_list'] = load_ccpn_restraint_violation_list
    importers['ccpn_rdc_restraint_violation_list'] = load_ccpn_restraint_violation_list

    def verify_ccpn_restraint_violation_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Serves to verify ccpn_<type>_restraint_violation_list"""

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        if category == 'ccpn_distance_restraint_violation_list':
            restraintType = 'Distance'
        elif category == 'ccpn_dihedral_restraint_violation_list':
            restraintType = 'Dihedral'
        elif category == 'ccpn_rdc_restraint_violation_list':
            restraintType = 'Rdc'
        else:
            return

        parameters['restraintType'] = restraintType

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]

        # # replace the deprecated tag with the new tag
        # if DATANAME_DEPRECATED in saveFrame:
        #     if DATANAME not in saveFrame:
        #         saveFrame[DATANAME] = saveFrame.get(DATANAME_DEPRECATED) or DATANAME_DEFAULT  # cannot be empty
        #     del saveFrame[DATANAME_DEPRECATED]  # remove as new tag takes priority

        sDataName = saveFrame.get(DATANAME) or DATANAME_DEFAULT

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        name = re.sub(REGEXREMOVEENDQUOTES, '', name)  # substitute with ''

        dataSet = self.project.getStructureData(sDataName) if sDataName else None
        # Make main object
        if dataSet is not None:
            # find the restraintList
            violationTable = dataSet.getViolationTable(name)
            if violationTable is not None:
                self.error(f'{category} - violationTable {violationTable} already exists', saveFrame, (violationTable,))

                # NOTE:ED - this causes an issue with same name violation tables in different structureData
                saveFrame._rowErrors[category] = (name,)

                self._verifyLoops(violationTable, saveFrame, name=name)

    verifiers['ccpn_distance_restraint_violation_list'] = verify_ccpn_restraint_violation_list
    verifiers['ccpn_dihedral_restraint_violation_list'] = verify_ccpn_restraint_violation_list
    verifiers['ccpn_rdc_restraint_violation_list'] = verify_ccpn_restraint_violation_list

    def load_ccpn_restraint_violation_list_metadata(self, data: Data, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                                    run_id: str = '', itemLength: int = None):
        """Serves to load ccpn_<type>_restraint_violation loops"""

        if loop and loop.data:
            for row in loop.data:
                name = row.get('name')
                parameter = row.get('parameter')

                data.setMetadata(name, json.loads(parameter))

    importers['ccpn_restraint_violation_list_metadata'] = load_ccpn_restraint_violation_list_metadata

    def _uniqueParameterName(self, data, name):
        """Return a unique name based on name (set to defaultName if None)
        """
        if name is None:
            name = 'default'
        name = name.strip()
        names = [dd.name for dd in data.dataParameters]
        while name in names:
            name = commonUtil.incrementName(name)
        return name

    def load_ccpn_restraint_violation(self, data: Data, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                      run_id: str = '', itemLength: int = None):
        """Serves to load ccpn_<type>_restraint_violation loops"""

        # if not run_id:
        #     raise RuntimeError('run_id is not defined')

        if loop and loop.data:
            # if loop.data exists then load as a pandas dataFrame
            _df = pd.DataFrame(loop.data)

            atomCols = None
            for ii in range(itemLength):

                # skip if there are no atoms defined in the columns - it is a results violationTable
                if not f'chain_code_{ii + 1}' in _df:
                    break

                # add new columns - concatenate to give atom IDs to compare with restraintItems
                atomCol = _df[f'chain_code_{ii + 1}'].map(str) + '.' + \
                          _df[f'sequence_code_{ii + 1}'].map(str) + '.' + \
                          _df[f'residue_name_{ii + 1}'].map(str) + '.' + \
                          _df[f'atom_name_{ii + 1}'].map(str)

                # insert into the dataFrame
                _df[f'atom{ii + 1}'] = atomCol

                # build a set of pd.Series to add to the dataFrame
                if atomCols is None:
                    atomCols = atomCol
                else:
                    atomCols = atomCols + ' - ' + atomCol

            if atomCols is not None:
                _df[f'atoms'] = [' - '.join(sorted(st.split(' - '), key=universalSortKey)) if st else None for st in atomCols]

            # vset3 = [v for k, v in p1.groupby(['model_id'])]
            # pd.concat([v.reset_index()['violation'] for v in vset3], axis=1).agg(['sum', 'mean', 'min', 'max', lambda x : sum(x > 0.3), lambda x : sum(x > 0.3)], axis=1)
            # data.setDataParameter(run_id, _df)

            data.data = _df

    importers['ccpn_distance_restraint_violation'] = load_ccpn_restraint_violation
    importers['ccpn_dihedral_restraint_violation'] = load_ccpn_restraint_violation
    importers['ccpn_rdc_restraint_violation'] = load_ccpn_restraint_violation

    def verify_ccpn_restraint_violation(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                        name=None, itemLength: int = None):
        """Verify the contents of ccpn_<type>_restraint_violation loops"""
        result = []

    verifiers['ccpn_distance_restraint_violation'] = verify_ccpn_restraint_violation
    verifiers['ccpn_dihedral_restraint_violation'] = verify_ccpn_restraint_violation
    verifiers['ccpn_rcd_restraint_violation'] = verify_ccpn_restraint_violation

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _parametersFromSpectrumDimensionLoop(self, loop: StarIo.NmrLoop, mapping) -> dict:
        """Parse a spectrum dimension loop (either nef or ccpn) and convert data to a dictionary
        """
        if mapping is None:
            raise ValueError('Undefined spectrum dimension mapping dict')

        result = {}

        # sort the rows on dimension_id; (just to be sure they are in order??)
        rows = sorted(loop.data, key=itemgetter('dimension_id'))
        if not rows:
            raise RuntimeError("Spectrum dimension loop data is missing or empty")

        # Get dimension attributes
        for nefTag, ccpnTag in mapping.items():
            if nefTag in rows[0] and ccpnTag is not None:
                result[ccpnTag] = list(row.get(nefTag) for row in rows)
        #
        return result

    def _load_spectrum(self, saveFrame: StarIo.NmrSaveFrame, project: Project) -> Spectrum:
        """Create or get a spectrum corresponding to the saveFrame data
        :return: the Spectrum instance
        """
        from ccpn.core.Spectrum import _newEmptySpectrum
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import _getPotentialDataLoaders

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # Get name from the framecode
        _name = framecode[len(category) + 1:]
        spectrumName = _stripSpectrumName(_name)

        # see if the spectrum is already in the project
        _pid = Pid.Pid.new(Spectrum.shortClassName, spectrumName)
        if (spectrum := project.getByPid(_pid)) is None:
            # Spectrum did not exist, create a new one

            _params = dict()

            # Get nef- and ccpn-defined spectrum parameters
            spectrumParams, _tmp = self._parametersFromSaveFrame(saveFrame,
                                                                 mapping=nef2CcpnMap.get(category, {}),
                                                                 ccpnPrefix=None)
            self._updateStringParameters(spectrumParams)

            dimensionCount = spectrumParams['dimensionCount']  # we need this later
            _params.update(spectrumParams)

            # get dimension parameters
            if (_loop := saveFrame.get('nef_spectrum_dimension')) is not None:
                nefDimensionParameters = self._parametersFromSpectrumDimensionLoop(_loop,
                                                                                   mapping=nef2CcpnMap.get('nef_spectrum_dimension')
                                                                                   )
                _params.update(nefDimensionParameters)

            # nef dimension parameters do not have the reference point as a parameter
            # assume 1.0 as default; maybe overridden later by the ccpn dimension parameters
            _params['referencePoints'] = [1.0] * dimensionCount

            if (_loop := saveFrame.get('ccpn_spectrum_dimension')) is not None:
                ccpnDimensionParameters = self._parametersFromSpectrumDimensionLoop(_loop,
                                                                                    mapping=nef2CcpnMap.get('ccpn_spectrum_dimension')
                                                                                    )
                _params.update(ccpnDimensionParameters)

            expName = _params.pop('experimentName', None)
            expType = _params.pop('experimentType', None)
            refExpDims = _params.pop('referenceExperimentDimensions', None)

            # create a new spectrum; first empty but change dataFormat if known
            filePath = _params.pop('filePath', None)
            dataFormat = _params.pop('dataFormat', None)
            if filePath is not None and dataFormat is None:
                # see if we can derive a dataFormat from the filePath
                _loaders = _getPotentialDataLoaders(filePath)
                if len(_loaders) == 1 and _loaders[0].isSpectrumLoader:
                    dataFormat = _loaders[0].spectumDataSourceClass.dataFormat

            spectrum = _newEmptySpectrum(project, name=spectrumName, path=filePath, **_params)
            # Optionally change the dataFormat
            if filePath is not None and dataFormat is not None:
                try:
                    spectrum._close()
                    spectrum._setdataFormat(dataFormat)  # specially override the dataFormat setting
                    spectrum.filePath = filePath  # This will also try to reopen the file
                except (RuntimeError, ValueError) as es:
                    getLogger().warning(f'{es}')

            framecode = saveFrame.get('chemical_shift_list')
            cslName = framecode[len('nef_chemical_shift_list_'):]
            # Defaults to the specified shiftList or the first shiftList (there should be only one, but we want the read to work)
            # if (csl := (self.frameCode2Object.get(framecode) or project.fetchChemicalShiftList(cslName))):
            #         # self.defaultChemicalShiftList)):
            #     spectrum.chemicalShiftList = csl

            if csl := (self.frameCode2Object.get(framecode) or
                    project.getChemicalShiftList(cslName) or
                    project.newChemicalShiftList(cslName) or
                    self.defaultChemicalShiftList):
                spectrum.chemicalShiftList = csl
            print(f'==> chemicalshiftlist {framecode}     {cslName}     {csl}')

            framecode = saveFrame.get('ccpn_sample')
            if (sample := self.frameCode2Object.get(framecode)):
                spectrum.sample = sample

            # set the experimentName and -Type if available - not mandatory
            if expName:
                spectrum.experimentName = expName
            if expType:
                spectrum.experimentType = expType

            dimensionTransferTags = ('dimension_1', 'dimension_2', 'transfer_type', 'is_indirect')

            transferData = None
            # read dimension transfer data
            loopName = 'nef_spectrum_dimension_transfer'
            # Those are treated elsewhere
            loop = saveFrame.get(loopName)
            if loop:
                data = loop.data
                transferData = [
                    SpectrumLib.MagnetisationTransferTuple(*(row.get(tag) for tag in dimensionTransferTags))
                    for row in data
                    ]
                # if name is available, use it to set the experimentType (if not set)
                if expName and not expType:  # (expName := spectrum.experimentName):
                    spectrum.experimentType = expName  # name or type can be used here

                # will be set if the type is valid
                if not spectrum.experimentType and transferData:
                    spectrum._setMagnetisationTransfers(transferData)
            else:
                raise ValueError("nef_spectrum_dimension_transfer is missing or empty")

            if refExpDims:
                try:
                    # set the reference dimensions - may be a bad string
                    spectrum.referenceExperimentDimensions = literal_eval(refExpDims)
                except Exception as es:
                    getLogger().warning(f'could not evaluate referenceExperimentDimensions - {es}')

            else:
                # set the default
                if (newRefs := spectrum.getAvailableReferenceExperimentDimensions(spectrum.experimentType)):
                    spectrum.referenceExperimentDimensions = newRefs[0]
                elif transferData:
                    spectrum.referenceExperimentDimensions = spectrum.axisCodes

            # to still implement
            #             framecode = saveFrame.get('chemical_shift_list')
            #             # Defaults to first (there should be only one, but we want the read to work) ShiftList
            #             spectrumParameters['chemicalShiftList'] = self.frameCode2Object.get(framecode) or self.defaultChemicalShiftList
            #
            #             framecode = saveFrame.get('ccpn_sample')
            #             if framecode and framecode in self.frameCode2Object:
            #                 spectrumParameters['sample'] = self.frameCode2Object[framecode]
            # # read dimension transfer data
            # loopName = 'nef_spectrum_dimension_transfer'
            # # Those are treated elsewhere
            # loop = saveFrame.get(loopName)
            # if loop:
            #     data = loop.data
            #     transferData = [
            #         SpectrumLib.MagnetisationTransferTuple(*(row.get(tag) for tag in dimensionTransferTags))
            #         for row in data
            #         ]
            # else:
            #     # transferData = []
            #     raise ValueError("nef_spectrum_dimension_transfer is missing or empty")
            #
            # if not self.defaultChemicalShiftList:
            #     # no chemicalShiftLists have been loaded yet, so need to fetch/create one
            #     if not project.chemicalShiftLists:
            #         project.newChemicalShiftList()
            #     self.defaultChemicalShiftList = project.chemicalShiftLists[0]

        return spectrum

    def _load_peaks(self, saveFrame: StarIo.NmrSaveFrame, spectrum: Spectrum):
        """Load the peaks defined in saveframe; add to a peaklist of spectrum
        :return a PeakList instance with the peaks
        """
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # Get name from the framecode
        _name = framecode[len(category) + 1:]

        # Get peakList parameters
        peakListParameters, dummy = self._parametersFromSaveFrame(saveFrame,
                                                                  mapping=nef2CcpnMap.get('ccpn_no_peak_list', {})
                                                                  )
        # self._updateStringParameters(peakListParameters)
        peakListId = _stripSpectrumSerial(_name) or peakListParameters.get('serial') or 1
        peakListParameters.pop('serial', None)

        peakList = None
        if (_loop := saveFrame.get('nef_peak')) is not None:
            peakList = self.load_nef_peak(spectrum=spectrum,
                                          loop=_loop,
                                          saveFrame=saveFrame,
                                          peakListId=peakListId,
                                          peakListParameters=peakListParameters)
        return peakList

    def load_nef_nmr_spectrum(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Load an nmr spectrum, peaks and all associated things from the saveframe
        :return a PeakList instance
        """
        spectrum = self._load_spectrum(saveFrame, project)
        peakList = self._load_peaks(saveFrame, spectrum)

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        # Load remaining loops, with spectrum as parent - ccpn multiplets/integrals
        for loopName in loopNames:
            if loopName not in ('nef_spectrum_dimension', 'ccpn_spectrum_dimension', 'nef_peak',
                                'nef_spectrum_dimension_transfer',
                                ):
                # Those are treated elsewhere
                loop = saveFrame.get(loopName)
                if loop:
                    importer = self.importers[loopName]
                    importer(self, spectrum, loop, saveFrame)

        return peakList

    #
    importers['nef_nmr_spectrum'] = load_nef_nmr_spectrum

    def load_ccpn_spectrum_reference_substances(self, parent: Spectrum, loop: StarIo.NmrLoop,
                                                saveFrame: StarIo.NmrSaveFrame, **kwargs):
        """load reference_substances loop"""

        referenceSubstances = []
        for row in loop.data:
            name = row.get('name')
            labelling = row.get('labelling')
            nameLabelling = '.'.join([str(name), str(labelling or '')])
            substance = self.project.getSubstance(nameLabelling)
            if substance is None:
                self.warning(
                        "No substance found with framecode %s. Skipping substance from referenceSubstances"
                        % nameLabelling, loop)
            else:
                referenceSubstances.append(substance)
        #
        parent.referenceSubstances = referenceSubstances

    #
    importers['ccpn_spectrum_reference_substances'] = load_ccpn_spectrum_reference_substances

    def verify_nef_nmr_spectrum(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        _rowSpectrumErrors = saveFrame._rowErrors[saveFrame.name] = OrderedSet()
        # _rowPeakErrors = saveFrame._rowErrors['nef_peak_list'] = OrderedSet()

        dimensionTransferTags = ('dimension_1', 'dimension_2', 'transfer_type', 'is_indirect')

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        mappingNoPeakList = nef2CcpnMap.get('ccpn_no_peak_list') or {}

        # Get peakList parameters and make peakList
        # peakListParameters, dummy = self._parametersFromSaveFrame(saveFrame, mapping)
        peakListParameters, dummy = self._parametersFromSaveFrame(saveFrame, mappingNoPeakList)

        # Get spectrum parameters
        spectrumParameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping,
                                                                      ccpnPrefix=None)
        # ccpnPrefix = 'spectrum')

        # Get name from spectrum parameters, or from the framecode
        spectrumName = framecode[len(category) + 1:]
        _spectrumNameNoPostfix = spectrumName

        # get the serial number become stripping name
        peakListSerial = _stripSpectrumSerial(spectrumName) or peakListParameters.get('serial') or 1
        spectrumName = _stripSpectrumName(spectrumName)

        spectrum = project.getSpectrum(spectrumName)
        if spectrum is not None:
            # search
            peakListId = Pid.IDSEP.join(('' if x is None else str(x)) for x in (spectrumName, peakListSerial))
            peakList = project.getObjectsByPartialId(className='PeakList', idStartsWith=peakListId)

            if peakList:
                self.error('nef_nmr_spectrum - Peaklist {} already exists'.format(peakListId), saveFrame, (spectrum,))
                _rowSpectrumErrors.add((spectrumName, peakListSerial))

            # peakList = spectrum.getPeakList(peakListParameters['serial'])
            # if peakList is not None:
            #     self.error('nef_nmr_spectrum - PeakList {} already exists'.format(peakList), saveFrame, (peakList,))
            #     _rowPeakErrors.add(peakList.serial)

            # loop = saveFrame.get('nef_peak')
            # if loop:
            #     self.verify_nef_peak(peakList, loop, saveFrame)

            self._verifyLoops(spectrum, saveFrame, dimensionCount=saveFrame['num_dimensions'],
                              excludeList=('nef_spectrum_dimension', 'ccpn_spectrum_dimension',  #'nef_peak',
                                           'nef_spectrum_dimension_transfer',
                                           ),
                              spectrumListSerial=peakListSerial)

    verifiers['nef_nmr_spectrum'] = verify_nef_nmr_spectrum

    def read_nef_spectrum_dimension_transfer(self, loop: StarIo.NmrLoop):

        transferTypes = ('onebond', 'Jcoupling', 'Jmultibond', 'relayed', 'through-space',
                         'relayed-alternate')

        result = []

        if loop:
            data = loop.data
            for row in data:
                ll = [row.get(tag) for tag in ('dimension_1', 'dimension_2', 'transfer_type',
                                               'is_indirect')]
                result.append(SpectrumLib.MagnetisationTransferTuple(*ll))
        #
        return result

    def load_nef_spectrum_dimension_transfer(self, spectrum: Spectrum, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):

        transferTypes = ('onebond', 'Jcoupling', 'Jmultibond', 'relayed', 'through-space',
                         'relayed-alternate')

        result = []

        if loop:
            apiExperiment = spectrum.experiment

            data = loop.data
            # Remove invalid data rows
            for row in data:
                ll = [row.get(tag) for tag in ('dimension_1', 'dimension_2', 'transfer_type',
                                               'is_indirect')]
                if (apiExperiment.findFirstExpDim(dim=row['dimension_1']) is None or
                        apiExperiment.findFirstExpDim(dim=row['dimension_2']) is None or
                        row['transfer_type'] not in transferTypes):
                    self.warning("Illegal values in nef_spectrum_dimension_transfer: %s"
                                 % list(row.values()),
                                 loop)
                else:
                    result.append(SpectrumLib.MagnetisationTransferTuple(*ll))
        #
        return result

    # importers['nef_spectrum_dimension_transfer'] = load_nef_spectrum_dimension_transfer

    def process_nef_spectrum_dimension_transfer(self, spectrum: Spectrum,
                                                dataLists: Sequence[Sequence]):
        # Store expTransfers in API as we can not be sure we will get a refExperiment

        apiExperiment = spectrum.experiment

        for ll in dataLists:
            expDimRefs = []
            for dim in ll[:2]:
                expDim = apiExperiment.findFirstExpDim(dim=dim)
                # After spectrum creation there will be one :
                expDimRefs.append(expDim.sortedExpDimRefs()[0])
            if apiExperiment.findFirstExpTransfer(expDimRefs=expDimRefs) is None:
                apiExperiment.newExpTransfer(expDimRefs=expDimRefs, transferType=ll[2],
                                             isDirect=not ll[3])
            else:
                self.warning("Duplicate nef_spectrum_dimension_transfer: %s" % (ll,))

    verifiers['nef_spectrum_dimension_transfer'] = _noLoopVerify

    def load_ccpn_spectrum_dimension(self, spectrum: Spectrum, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame) -> dict:
        """Read ccpn_spectrum_dimension loop, set the relevant values,
        and return the spectrum and other parameters for further processing"""

        params = {}
        extras = {}
        nefTag2ccpnTag = nef2CcpnMap.get('ccpn_spectrum_dimension') or {}

        if not loop.data:
            raise ValueError("ccpn_spectrum_dimension is empty")

        rows = sorted(loop.data, key=itemgetter('dimension_id'))

        # Get spectrum attributes
        for nefTag, ccpnTag in nefTag2ccpnTag.items():
            if nefTag in rows[0]:
                ll = list(row.get(nefTag) for row in rows)
                if any(x is not None for x in ll):
                    if ccpnTag and not '.' in ccpnTag:
                        params[ccpnTag] = ll
                    else:
                        extras[nefTag] = ll

        # Set main values
        for tag, value in params.items():
            if tag != 'referencePoints':
                setattr(spectrum, tag, value)

        referencePoints = params.get('referencePoints')
        points = []
        values = []
        if referencePoints is not None:
            spectrumReferences = spectrum.spectrumReferences
            for ii, spectrumReference in enumerate(spectrumReferences):
                if spectrumReference is None:
                    points.append(None)
                    values.append(None)
                else:
                    point = referencePoints[ii]
                    points.append(point)
                    values.append(spectrumReference.pointToValue(point))
        spectrum.referencePoints = points
        spectrum.referenceValues = values

        # set storage attributes
        value = extras.get('dimension_is_complex')
        if value:
            spectrum.isComplex = value

        # set aliasingLimits
        defaultLimits = spectrum.dimensionCount * [None]
        lowerLimits = extras.get('lower_aliasing_limit', defaultLimits)
        higherLimits = extras.get('higher_aliasing_limit', defaultLimits)
        try:
            spectrum.aliasingLimits = list(zip(lowerLimits, higherLimits))
        except:
            # foldingLimits extend 0.5points beyond spectrumLimits
            spectrum.aliasingLimits = tuple(sorted(lim) for lim in spectrum.foldingLimits)
            self.warning(f'Cannot set aliasingLimits {list(zip(lowerLimits, higherLimits))} for {spectrum}, setting to spectrumLimits',
                         saveFrame)
        else:
            # check that the read values of aliasingLimits are with the allowed range (-3, +3)
            # and round to the nearest limit
            inds = spectrum.aliasingIndexes
            clippedInds = tuple(tuple(max(min(ind, MAXALIASINGRANGE), -MAXALIASINGRANGE) for ind in anInd) for anInd in inds)

            if inds != clippedInds:
                self.warning(f'AliasingLimits {list(zip(lowerLimits, higherLimits))} out-of-range for {spectrum}, clipping to ±{MAXALIASINGRANGE} spectrum widths',
                             saveFrame)
            # foldingLimits extend 0.5points beyond spectrumLimits
            lims = spectrum.foldingLimits
            wids = spectrum.spectralWidths
            # deltaLims = tuple(abs(lim[1] - lim[0]) for lim in lims) # +ve
            newLims = tuple((min(sp) + min(cl) * wid, max(sp) + max(cl) * wid) for sp, cl, wid in zip(lims, clippedInds, wids))
            # set the new aliasing limits
            spectrum.aliasingLimits = newLims

    importers['ccpn_spectrum_dimension'] = load_ccpn_spectrum_dimension
    verifiers['ccpn_spectrum_dimension'] = _noLoopVerify

    # def adjustAxisCodes(self, spectrum, dimensionData):
    #   # Use data to rename axisCodes
    #   axisCodes = spectrum.axisCodes
    #   newCodes = list(axisCodes)
    #   atomTypes = [commonUtil.splitIntFromChars(x)[1] for x in spectrum.isotopeCodes]
    #   acquisitionAxisCode = spectrum.acquisitionAxisCode
    #   if acquisitionAxisCode is not None:
    #     acquisitionDim = axisCodes.index(acquisitionAxisCode) + 1
    #     if acquisitionAxisCode == atomTypes[acquisitionDim - 1]:
    #       # this axisCode needs improvement
    #       for pair in oneBondPairs:
    #         # First do acquisition dimension
    #         if acquisitionDim in pair:
    #           ll = pair.copy()
    #           ll.remove(acquisitionDim)
    #           otherDim = ll[0]
    #           otherCode = axisCodes[otherDim - 1]
    #           if otherCode == atomTypes[otherDim - 1]:

    def read_nef_spectrum_dimension(self, project: Project, loop: StarIo.NmrLoop):
        """Read nef_spectrum_dimension loop and convert data to a dictionary
        of ccpnTag:[per-dimension-value]"""

        # NB we are not using absolute_peak_positions - if false what could we do?

        result = {}
        nefTag2ccpnTag = nef2CcpnMap.get('nef_spectrum_dimension') or {}

        rows = sorted(loop.data, key=itemgetter('dimension_id'))
        # rows = [(row['dimension_id'], row) for row in loop.data]
        # rows = [tt[1] for tt in sorted(rows)]

        if not rows:
            raise ValueError("nef_spectrum_dimension is missing or empty")

        # Get spectrum attributes
        for nefTag, ccpnTag in nefTag2ccpnTag.items():
            if nefTag in rows[0]:
                if ccpnTag:
                    result[ccpnTag] = list(row.get(nefTag) for row in rows)
                else:
                    # Unmapped attributes are passed with the original tag for later processing
                    result[nefTag] = list(row.get(nefTag) for row in rows)
        #
        return result

    verifiers['nef_spectrum_dimension'] = _noLoopVerify

    def load_ccpn_peak_list(self, spectrum: Spectrum,
                            loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame, peakListId=None) -> List[PeakList]:

        result = []

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        creatorFunc = spectrum.newPeakList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            # NOTE:ED - adding flags to restrict importing to the selection
            serial = parameters.get('serial')
            if not self._checkImport(saveFrame, serial):
                continue

            peakList = creatorFunc(**parameters)
            # peakList.resetSerial(row['serial'])
            # NB former call was BROKEN!
            # modelUtil.resetSerial(peakList, row['serial'], 'peakLists')
            result.append(peakList)
        #
        return result

    importers['ccpn_peak_list'] = load_ccpn_peak_list

    def verify_ccpn_peak_list(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        """Verify the peakLists"""
        _ID = 'ccpn_peak_list'
        _serialName = '{}_serial'.format(_ID)
        _serialErrors = parentFrame._rowErrors[_serialName] = OrderedSet()
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        verifyFunc = spectrum.getPeakList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            peakList = verifyFunc(parameters['serial'])
            if peakList is not None:
                self.error('{} - PeakList {} already exists'.format(_ID, peakList), loop, (peakList,))
                _rowErrors.add(loop.data.index(row))
                listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, parameters['serial']])
                _serialErrors.add(listName)
                parentFrame._rowErrors['_'.join([_ID, listName])] = OrderedSet([loop.data.index(row)])

    verifiers['ccpn_peak_list'] = verify_ccpn_peak_list

    def load_ccpn_integral_list(self, spectrum: Spectrum,
                                loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame, peakListId=None) -> List[IntegralList]:

        result = []

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        creatorFunc = spectrum.newIntegralList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, parameters['serial']])
            if not self._checkImport(saveFrame, listName, checkID='_importIntegrals'):
                continue

            parameters.pop('serial', None)  # remove from parameters
            integralList = creatorFunc(**parameters)
            integralList._resetSerial(row['serial'])

            result.append(integralList)
        #
        return result

    importers['ccpn_integral_list'] = load_ccpn_integral_list

    def verify_ccpn_integral_list(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        """Verify the integralLists"""
        _ID = 'ccpn_integral_list'
        _serialName = '{}_serial'.format(_ID)
        _serialErrors = parentFrame._rowErrors[_serialName] = OrderedSet()
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        verifyFunc = spectrum.getIntegralList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            integralList = verifyFunc(parameters['serial'])
            if integralList is not None:
                self.error('{} - IntegralList {} already exists'.format(_ID, integralList), loop, (integralList,))
                _rowErrors.add(loop.data.index(row))
                listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, parameters['serial']])
                _serialErrors.add(listName)
                parentFrame._rowErrors['_'.join([_ID, listName])] = OrderedSet([loop.data.index(row)])

    verifiers['ccpn_integral_list'] = verify_ccpn_integral_list

    def load_ccpn_multiplet_list(self, spectrum: Spectrum,
                                 loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame, peakListId=None) -> List[MultipletList]:

        result = []

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        creatorFunc = spectrum.newMultipletList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, parameters['serial']])
            if not self._checkImport(saveFrame, listName, checkID='_importMultiplets'):
                continue

            parameters.pop('serial', None)  # remove from parameters
            multipletList = creatorFunc(**parameters)
            multipletList._resetSerial(row['serial'])

            result.append(multipletList)

        return result

    importers['ccpn_multiplet_list'] = load_ccpn_multiplet_list

    def verify_ccpn_multiplet_list(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        """Verify the multipletLists"""
        _ID = 'ccpn_multiplet_list'
        _serialName = '{}_serial'.format(_ID)
        _serialErrors = parentFrame._rowErrors[_serialName] = OrderedSet()
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        verifyFunc = spectrum.getMultipletList
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            multipletList = verifyFunc(parameters['serial'])
            if multipletList is not None:
                self.error('{} - MultipletList {} already exists'.format(_ID, multipletList), loop, (multipletList,))
                _rowErrors.add(loop.data.index(row))
                listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, parameters['serial']])
                _serialErrors.add(listName)
                parentFrame._rowErrors['_'.join([_ID, listName])] = OrderedSet([loop.data.index(row)])

    verifiers['ccpn_multiplet_list'] = verify_ccpn_multiplet_list

    def load_ccpn_integral(self, spectrum: Spectrum,
                           loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame, peakListId=None) -> List[Integral]:

        result = []

        # Get name map for per-dimension attributes
        max = spectrum.dimensionCount + 1
        multipleAttributes = {
            'slopes'     : tuple('slopes_%s' % ii for ii in range(1, max)),
            'lowerLimits': tuple('lower_limits_%s' % ii for ii in range(1, max)),
            'upperLimits': tuple('upper_limits_%s' % ii for ii in range(1, max)),
            }

        serial2creatorFunc = dict((x.serial, x.newIntegral) for x in spectrum.integralLists)

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters, attribs=('comment', 'annotation'))

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, row['integral_list_serial']])
            if not self._checkImport(saveFrame, listName, checkID='_importIntegrals'):
                continue

            serial = parameters.pop('serial', 1)
            integral = serial2creatorFunc[row['integral_list_serial']](**parameters)

            # integral.slopes = tuple(row.get(x) for x in multipleAttributes['slopes'])
            # lowerLimits = tuple(row.get(x) for x in multipleAttributes['lowerLimits'])
            # upperLimits = tuple(row.get(x) for x in multipleAttributes['upperLimits'])
            # # integral.slopes = row._get('slopes')
            # # lowerLimits = row._get('lower_limits')
            # # upperLimits = row._get('upper_limits')
            # integral.limits = zip((lowerLimits, upperLimits))

            if row['slopes']:
                integral.slopes = eval(row['slopes'])
            if row['limits']:
                integral.limits = eval(row['limits'])
            if row['point_limits']:
                integral.pointLimits = eval(row['point_limits'])
            integral._resetSerial(serial)

            mPeak = row['ccpn_linked_peak']
            peak = spectrum.project.getByPid(mPeak)
            if peak:
                integral.peak = peak

            result.append(integral)

        return result

    importers['ccpn_integral'] = load_ccpn_integral

    def verify_ccpn_integral(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        _ID = 'ccpn_integral'
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        serial2verifyFunc = dict((x.serial, x.getIntegral) for x in spectrum.integralLists)

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, row['integral_list_serial']])
            integralID = '_'.join([_ID, listName])

            integralFunc = serial2verifyFunc.get(row['integral_list_serial'])
            if integralFunc:
                integral = integralFunc(parameters['serial'])
                if integral is not None:
                    self.error('{} - Integral {} already exists'.format(_ID, integral), loop, (integral,))
                    _rowErrors.add(loop.data.index(row))

                    if integralID not in parentFrame._rowErrors:
                        parentFrame._rowErrors[integralID] = OrderedSet([loop.data.index(row)])
                    else:
                        parentFrame._rowErrors[integralID].add(loop.data.index(row))

    verifiers['ccpn_integral'] = verify_ccpn_integral

    def load_ccpn_multiplet(self, spectrum: Spectrum,
                            loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame, peakListId=None) -> List[Multiplet]:

        result = []

        # Get name map for per-dimension attributes
        max = spectrum.dimensionCount + 1
        serial2creatorFunc = dict((x.serial, x.newMultiplet) for x in spectrum.multipletLists)

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters, attribs=('comment', 'annotation'))

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, row['multiplet_list_serial']])
            if not self._checkImport(saveFrame, listName, checkID='_importMultiplets'):
                continue

            # these are now derived
            if parameters.get('position'):
                del parameters['position']
            if parameters.get('positionError'):
                del parameters['positionError']
            parameters.pop('serial', None)  # remove from parameters
            multiplet = serial2creatorFunc[row['multiplet_list_serial']](**parameters)

            if row['slopes']:
                multiplet.slopes = eval(row['slopes'])
            if row['limits']:
                multiplet.limits = eval(row['limits'])
            if row['point_limits']:
                multiplet.pointLimits = eval(row['point_limits'])

            multiplet._resetSerial(row['multiplet_serial'])
            result.append(multiplet)

        return result

    importers['ccpn_multiplet'] = load_ccpn_multiplet

    def verify_ccpn_multiplet(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        _ID = 'ccpn_multiplet'
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        serial2verifyFunc = dict((x.serial, x.getMultiplet) for x in spectrum.multipletLists)

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, row['multiplet_list_serial']])
            multipletID = '_'.join([_ID, listName])

            multFunc = serial2verifyFunc.get(row['multiplet_list_serial'])
            if multFunc:
                multiplet = multFunc(parameters['serial'])
                if multiplet is not None:
                    self.error('ccpn_multiplet - Multiplet {} already exists'.format(multiplet), loop, (multiplet,))
                    _rowErrors.add(loop.data.index(row))

                    if multipletID not in parentFrame._rowErrors:
                        parentFrame._rowErrors[multipletID] = OrderedSet([loop.data.index(row)])
                    else:
                        parentFrame._rowErrors[multipletID].add(loop.data.index(row))

    verifiers['ccpn_multiplet'] = verify_ccpn_multiplet

    def load_ccpn_multiplet_peaks(self, spectrum: Spectrum,
                                  loop: StarIo.NmrLoop,
                                  saveFrame: StarIo.NmrSaveFrame,
                                  peakListId=None) -> list[Multiplet] | None:

        # NOTE:ED - SHOULD defer this so that only needs to be defined in one nef_nmr_spectrum
        #   and check duplicates are actually the same, and only use first one?

        if not saveFrame:
            raise RuntimeError(f'saveFrame not specified')

        self._deferredItems.append(deferredItem(func=self.deferred_load_ccpn_multiplet_peaks,
                                                spectrum=spectrum,
                                                loop=loop,
                                                saveFrame=saveFrame,
                                                peakListId=peakListId))

    importers['ccpn_multiplet_peaks'] = load_ccpn_multiplet_peaks

    def deferred_load_ccpn_multiplet_peaks(self, spectrum: Spectrum,
                                           loop: StarIo.NmrLoop,
                                           saveFrame: StarIo.NmrSaveFrame,
                                           peakListId=None) -> list[Multiplet] | None:

        # Get name map for per-dimension attributes
        # max = spectrum.dimensionCount + 1
        # serial2creatorFunc = dict((x.serial, x.newMultiplet) for x in spectrum.multipletLists)

        # mapping = nef2CcpnMap.get(loop.name) or {}
        # map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:

            mList = row['multiplet_list_serial']
            mSerial = row['multiplet_serial']
            pSpectrum = row['peak_spectrum']
            pList = row['peak_list_serial']
            pSerial = row['peak_serial']
            mPeak = Pid.IDSEP.join(('' if x is None else str(x)) for x in ['PK:' + pSpectrum, pList, pSerial])
            # mPeak = row['peak_pid']

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [pSpectrum, mList])
            if not self._checkImport(saveFrame, listName, checkID='_importMultiplets'):
                continue

            mlList = [ml for ml in spectrum.multipletLists if ml.serial == mList]
            mlts = [mt for ml in mlList for mt in ml.multiplets if mt.serial == mSerial]
            peak = spectrum.project.getByPid(mPeak)

            # NOTE:ED - there is a problem with cross-spectra peaks
            if mlts and peak and peak not in mlts[0].peaks:
                mlts[0]._forcePeaks(peak)

    def verify_ccpn_multiplet_peaks(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
        """verify ccpn_multiplet_peaks loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            parameters['peak_list_serial'] = row.get('peak_list_serial')
            # parameters['peak_spectrum'] = row.get('peak_spectrum')

            tt = [parameters[col] for col in ('peak_list_serial', 'serial')]
            peakName = Pid.IDSEP.join(('' if x is None else str(x)) for x in tt)

            peak = spectrum.getPeak(peakName)
            if peak is not None:
                self.error('ccpn_multiplet_peaks - MultipletPeaks contains {}'.format(peak), loop, (peak,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_multiplet_peaks'] = verify_ccpn_multiplet_peaks

    # def load_ccpn_peak_cluster_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
    #
    #     # load ccpn_peak_cluster
    #     loopName = 'ccpn_peak_cluster'
    #     loop = saveFrame[loopName]
    #     creatorFunc = project.newPeakCluster
    #
    #     result = []
    #     mapping = nef2CcpnMap.get(loopName) or {}
    #     map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
    #     for row in loop.data:
    #         parameters = _parametersFromLoopRow(row, map2)
    #         self._updateStringParameters(parameters, attribs=('comment', 'annotation'))
    #
    #         # NOTE:ED - adding flags to restrict importing to the selection
    #         serial = parameters.pop('serial', 1)
    #         if not self._checkImport(saveFrame, str(serial)):
    #             continue
    #
    #         obj = creatorFunc(**parameters)
    #         obj._resetSerial(serial)
    #         result.append(obj)
    #
    #     # load ccpn_peak_cluster
    #     loopName = 'ccpn_peak_cluster_peaks'
    #     loop = saveFrame[loopName]
    #
    #     for row in loop.data:
    #         pClSerial = row['peak_cluster_serial']
    #         pSpectrum = row['peak_spectrum']
    #         pList = row['peak_list_serial']
    #         pSerial = row['peak_serial']
    #
    #         # NOTE:ED - adding flags to restrict importing to the selection
    #         if not self._checkImport(saveFrame, str(pClSerial)):
    #             continue
    #
    #         pPeak = Pid.IDSEP.join(('' if x is None else str(x)) for x in ['PK:' + pSpectrum, pList, pSerial])
    #         # pPeak = row['peak_pid']
    #
    #         pcs = [pc for pc in project.peakClusters if pc.serial == pClSerial]
    #         peak = project.getByPid(pPeak)
    #         if pcs and peak:
    #             pcs[0].addPeaks(peak)
    #
    #     return result
    #
    # importers['ccpn_peak_cluster_list'] = load_ccpn_peak_cluster_list
    #
    # def verify_ccpn_peak_cluster_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
    #     """Verify the peakClusters"""
    #     self._verifyLoops(project, saveFrame)
    #
    #     # TODO:ED - get serials from peak_cluster, put into ccpn_peak_cluster_list error
    #
    # verifiers['ccpn_peak_cluster_list'] = verify_ccpn_peak_cluster_list
    #
    # def verify_ccpn_peak_cluster(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, **kwds):
    #     """Verify the peakClusters"""
    #     _ID = 'ccpn_peak_cluster'
    #     _serialName = 'ccpn_peak_cluster_serial'
    #     _serialErrors = parentFrame._rowErrors[_serialName] = OrderedSet()
    #     _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
    #
    #     mapping = nef2CcpnMap.get(loop.name) or {}
    #     map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
    #
    #     verifyFunc = project.getPeakCluster
    #     for row in loop.data:
    #         parameters = _parametersFromLoopRow(row, map2)
    #         peakCluster = verifyFunc(parameters['serial'])
    #         if peakCluster is not None:
    #             self.error('{} - PeakCluster {} already exists'.format(_ID, peakCluster), loop, (peakCluster,))
    #             _rowErrors.add(loop.data.index(row))
    #             listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [parameters['serial']])
    #             _serialErrors.add(listName)
    #             parentFrame._rowErrors['_'.join([_ID, listName])] = OrderedSet([loop.data.index(row)])
    #
    # verifiers['ccpn_peak_cluster'] = verify_ccpn_peak_cluster
    #
    # def verify_ccpn_peak_cluster_peaks(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
    #     """verify ccpn_peak_cluster_peaks loop"""
    #     _ID = 'ccpn_peak_cluster_peaks'
    #     _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
    #
    #     mapping = nef2CcpnMap.get(loop.name) or {}
    #     map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
    #     for row in loop.data:
    #         parameters = _parametersFromLoopRow(row, map2)
    #         parameters['peak_list_serial'] = row.get('peak_list_serial')
    #         parameters['peak_spectrum'] = row.get('peak_spectrum')
    #         listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [row['peak_cluster_serial']])
    #         clusterID = '_'.join([_ID, listName])
    #
    #         tt = [parameters[col] for col in ('peak_spectrum', 'peak_list_serial', 'serial')]
    #         peakName = Pid.IDSEP.join(('' if x is None else str(x)) for x in tt)
    #
    #         peak = project.getPeak(peakName)
    #         if peak is not None:
    #             self.error('ccpn_peak_cluster_peaks - PeakCluster contains {}'.format(peak), loop, (peak,))
    #             _rowErrors.add(loop.data.index(row))
    #
    #             if clusterID not in parentFrame._rowErrors:
    #                 parentFrame._rowErrors[clusterID] = OrderedSet([loop.data.index(row)])
    #             else:
    #                 parentFrame._rowErrors[clusterID].add(loop.data.index(row))
    #
    # verifiers['ccpn_peak_cluster_peaks'] = verify_ccpn_peak_cluster_peaks

    # def load_nef_peak(self, peakList: PeakList, loop: StarIo.NmrLoop) -> List[Peak]:
    def load_nef_peak(self, spectrum: Spectrum, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                      peakListId=None, peakListParameters=None) -> List[Peak]:
        """Serves to load nef_peak loop
        """
        # NOTE:ED - new calling parameter

        result = []

        # dimensionCount = peakList.spectrum.dimensionCount
        dimensionCount = spectrum.dimensionCount

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        # Get name map for per-dimension attributes
        multipleAttributes = {
            'position'     : tuple('position_%s' % ii for ii in range(1, dimensionCount + 1)),
            'positionError': tuple('position_uncertainty_%s' % ii for ii in range(1, dimensionCount + 1)),
            'chainCodes'   : tuple('chain_code_%s' % ii for ii in range(1, dimensionCount + 1)),
            'sequenceCodes': tuple('sequence_code_%s' % ii for ii in range(1, dimensionCount + 1)),
            'residueTypes' : tuple('residue_name_%s' % ii for ii in range(1, dimensionCount + 1)),
            'atomNames'    : tuple('atom_name_%s' % ii for ii in range(1, dimensionCount + 1)),
            }

        # Peaks assignment can extend over multiple rows (?)
        # keep a dict of the peaks (by peakListSerial.peakSerial)
        # create and build the assignment(s) by row
        peaks = {}
        assignedNmrAtoms = []

        # _parentName = saveFrame['sf_framecode']
        # _parentSerial = self._stripSpectrumSerial(_parentName)

        peakLabel = ''
        for row in loop.data:

            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters, attribs=('comment', 'annotation'))

            # get or make peak
            serial = parameters.pop('serial')  # parameters['serial']
            peakListSerial = peakListId or row.get('ccpn_peak_list_serial') or 1
            peakLabel = Pid.IDSEP.join(('' if x is None else str(x)) for x in (peakListSerial, serial))
            peak = peaks.get(peakLabel)

            # TODO check if peak parameters are the same for all rows, and do something about it
            # For now we simply use the first row that appears
            if peak is None:
                # start of a new peak

                # finalise last peak
                if result and assignedNmrAtoms:
                    try:
                        # set the isotopeCodes to match the peak
                        ics = result[-1].spectrum.isotopeCodes
                        for asgns in assignedNmrAtoms:
                            for ic, na in zip(ics, asgns):
                                if not na.isotopeCode:
                                    na._setIsotopeCode(ic)
                        # There is a peak in result, and the peak has assignments to set
                        result[-1].assignedNmrAtoms = assignedNmrAtoms
                    except Exception as es:
                        # error settings assignments - maybe badly defined
                        self.warning("Error setting Peak assignment for peak %s: %s."
                                     % (peakLabel, assignedNmrAtoms),
                                     loop)
                    assignedNmrAtoms.clear()

                # make new peak  multipleAttributes
                # parameters['position'] = row._get('position')[:dimensionCount]
                parameters['ppmPositions'] = tuple(row.get(x) for x in multipleAttributes['position'])
                parameters['positionError'] = tuple(row.get(x) for x in multipleAttributes['positionError'])
                # parameters['positionError'] = row._get('position_uncertainty')[:dimensionCount]

                peakList = spectrum.getPeakList(str(peakListSerial))
                if not peakList:
                    with apiNotificationBlanking():
                        # must block the creation of peakListViews here until the serial has been defined
                        #   otherwise creates a badly numbered peakListView :|
                        peakList = spectrum.newPeakList(str(peakListSerial))

                        if peakListParameters:
                            # if a new peakList, need to set the parameters from the saveFrame
                            for att, val in peakListParameters.items():
                                setattr(peakList, att, val)
                    try:
                        # change the serial number to match the new name
                        peakList._resetSerial(peakListSerial)

                        from ccpn.ui._implementation.PeakListView import _peakListAddPeakListViews

                        # create new peakListviews here
                        _peakListAddPeakListViews(self.project, peakList._wrappedData)

                    except:
                        self.warning(f'Error setting PeakList Serial to {peakListSerial}', loop)

                try:
                    peak = peakList.newPeak(**parameters)
                    peak._resetSerial(serial)
                    peaks[peakLabel] = peak
                    result.append(peak)

                    if peakListParameters:
                        # spectrum always has a peakList, so need to set the parameters from the saveFrame if (the first peakList)
                        # may be a little slow if lots of peaks
                        for att, val in peakListParameters.items():
                            setattr(peakList, att, val)

                except Exception as es:
                    self.warning(f'Error creating new peak - {es}', loop)

            # Add assignment
            # NB the self.defaultChainCode or converts code None to the default chain code
            chainCodes = tuple(row.get(x) or self.defaultChainCode for x in multipleAttributes['chainCodes'])
            sequenceCodes = tuple(row.get(x) for x in multipleAttributes['sequenceCodes'])
            residueTypes = tuple(row.get(x) for x in multipleAttributes['residueTypes'])
            atomNames = tuple(row.get(x) for x in multipleAttributes['atomNames'])
            # chainCodes = row._get('chain_code')[:dimensionCount]
            # sequenceCodes = row._get('sequence_code')[:dimensionCount]
            # residueTypes = row._get('residue_name')[:dimensionCount]
            # atomNames = row._get('atom_name')[:dimensionCount]
            assignments = zip(chainCodes, sequenceCodes, residueTypes, atomNames)
            nmrAtoms = []
            foundAssignment = False
            for tt in assignments:
                if all(x is None for x in tt):
                    # No assignment
                    nmrAtoms.append(None)
                elif tt[1] and tt[3]:
                    # Enough for an assignment - make it
                    foundAssignment = True
                    nmrResidue = self.produceNmrResidue(*tt[:3])
                    nmrAtom = self.produceNmrAtom(nmrResidue, tt[3])
                    nmrAtoms.append(nmrAtom)
                else:
                    # partial and unusable assignment
                    self.warning("Uninterpretable Peak assignment for peak %s: %s. Set to None"
                                 # % (peak.serial, tt))
                                 % (peakLabel, tt),
                                 loop)
                    nmrAtoms.append(None)
            if foundAssignment:
                assignedNmrAtoms.append(nmrAtoms)

        # finalise last peak
        if result and assignedNmrAtoms:
            try:
                # set the isotopeCodes to match the peak
                #   not sure why duplicated here, and not sure if executes this loop
                ics = result[-1].spectrum.isotopeCodes
                for asgns in assignedNmrAtoms:
                    for ic, na in zip(ics, asgns):
                        if not na.isotopeCode:
                            na._setIsotopeCode(ic)
                # There is a peak in result, and the peak has assignments to set
                result[-1].assignedNmrAtoms = assignedNmrAtoms
            except Exception:
                # error settings assignments - maybe badly defined
                self.warning("Error setting Peak assignment for peak %s: %s."
                             % (peakLabel, assignedNmrAtoms),
                             loop)
            assignedNmrAtoms.clear()
        #
        return result

    #
    # importers['nef_peak'] = load_nef_peak

    # def verify_nef_peak(self, peakList: PeakList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, dimensionCount: int = None):
    def verify_nef_peak(self, spectrum: Spectrum, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame, dimensionCount: int = None,
                        spectrumListSerial=None):
        """Serves to verify nef_peak loop"""
        _ID = 'nef_peak'
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)

            serial = parameters['serial']
            peakListSerial = spectrumListSerial or row.get('ccpn_peak_list_serial') or 1
            # peakLabel = Pid.IDSEP.join(('' if x is None else str(x)) for x in (peakListSerial, serial))

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [spectrum.name, peakListSerial])
            peakID = '_'.join([_ID, listName])

            peakList = spectrum.getPeakList(peakListSerial)
            # peakList = self.project.getObjectsByPartialId(className='PeakList', idStartsWith=listName)
            if peakList is not None:
                peak = peakList.getPeak(serial)

                if peak is not None:
                    self.error('nef_peak - Peak {} already exists'.format(peak), loop, (peak,))
                    _rowErrors.add(loop.data.index(row))

                    if peakID not in parentFrame._rowErrors:
                        parentFrame._rowErrors[peakID] = OrderedSet([loop.data.index(row)])
                    else:
                        parentFrame._rowErrors[peakID].add(loop.data.index(row))

                # NOTE:ED - needed because don't have a ccpn_peak_list loop at the moment
                #           when we do, this will get overwritten - need to check later
                _peaklist_errors = parentFrame._rowErrors.get('ccpn_peak_list_serial')
                if not _peaklist_errors:
                    parentFrame._rowErrors['ccpn_peak_list_serial'] = OrderedSet((listName,))
                else:
                    _peaklist_errors.add(listName)

                if (attrib := getattr(self._dataBlock, ROWERRORATTR, None)) is None:
                    # create a new temporary saveFrame
                    attrib = AttrDict()
                    setattr(self._dataBlock, ROWERRORATTR, attrib)

                if not attrib.get('loop'):
                    attrib.loop = StarIo.NmrLoop(name='_ccpn_peak_list', columns=('pid',))
                    attrib.loopSet = OrderedSet()
                if listName not in attrib.loopSet:
                    attrib.loopSet.add(listName)
                    attrib.loop.newRow((listName,))

    verifiers['nef_peak'] = verify_nef_peak

    def load_nef_peak_restraint_links(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load nef_peak_restraint_links saveFrame"""

        mapping = nef2CcpnMap.get('nef_peak_restraint_links') or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop:
                    importer = self.importers[tag]
                    importer(self, project, loop, saveFrame)
        #
        return project

    #
    importers['nef_peak_restraint_links'] = load_nef_peak_restraint_links
    verifiers['nef_peak_restraint_links'] = _verifyLoops

    def load_nef_peak_restraint_link(self, project: Project, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """Load nef_peak_restraint_link loop"""

        links = {}

        # NBNB TODO:RASMUS There was a very strange bug in this function
        # When I was using PeakList.getPeak(str(serial))
        # and RestraintTable.getRestraint(str(serial), peaks and restraints were
        # sometimes missed even though the data were present.
        # Doing the test at the API level (as now) fixed the problem
        # THIS SHOULD BE IMPOSSIBLE
        # At some point we ought to go back, reproduce the bug, and remove the reason for it.

        for row in loop.data:
            if DEFAULTRESTRAINTLINKLOAD:
                peakList = self.frameCode2Object.get(row.get('nmr_spectrum_id'))
                if peakList is None:
                    self.warning(
                            "No Spectrum saveframe found with framecode %s. Skipping peak_restraint_link"
                            % row.get('nmr_spectrum_id'),
                            loop
                            )
                    continue
                restraintList = self.frameCode2Object.get(row.get('restraint_list_id'))
                if restraintList is None:
                    self.warning(
                            "No restraint_list saveframe found with framecode %s. Skipping peak_restraint_link"
                            % row.get('restraint_list_id'),
                            loop
                            )
                    continue
            else:
                _spectrumPidFrame = row.get('nmr_spectrum_id')
                # _spectrumPid = re.sub(REGEXREMOVEENDQUOTES, '', _spectrumPidFrame)  # substitute with ''
                # _spectrum = project.getByPid('SP:' + _spectrumPid[len('nef_nmr_spectrum_'):])

                # matches = [mm for mm in re.finditer(REGEXREMOVEENDQUOTES, _spectrumPidFrame)]
                # postfix = matches[-1].group() if matches and matches[-1] and matches[-1].span()[1] == len(_spectrumPidFrame) else ''
                # postSerial = _tryNumber(postfix)

                peakListObject = self.frameCode2Object.get(_spectrumPidFrame)
                peakListSerial = peakListObject.serial if peakListObject else None
                _spectrum = peakListObject.spectrum if peakListObject else None
                if not _spectrum:
                    # spectrum not found in a saveframe so try and load from project
                    _frameID = _getNameFromCategory('nef_nmr_spectrum', _spectrumPidFrame)
                    if _frameID:
                        framecode, frameName, subName, prefix, postfix, preSerial, postSerial, category = _frameID

                        _spectrum = project.getSpectrum(subName)
                        if _spectrum is not None:
                            # find the peakList in the project
                            _serial = postSerial or 1
                            peakListId = Pid.IDSEP.join(('' if x is None else str(x)) for x in (subName, _serial))
                            peakList = project.getObjectsByPartialId(className='PeakList', idStartsWith=peakListId)
                            if peakList:
                                peakListSerial = _serial

                if not _spectrum:
                    continue

                _lastPeakListNum = _spectrum.peakLists[-1].serial if _spectrum.peakLists else None

                peakListNum = peakListSerial or _lastPeakListNum or 1
                if not (_spectrum and peakListNum):
                    continue

                _restraintId = row.get('restraint_list_id')
                restraintList = self.frameCode2Object.get(_restraintId)
                if not restraintList:
                    # restraintList not found in a saveframe so try and load from project
                    dataSetCode = self._frameCodeToSpectra.get(_restraintId)
                    _dataSet = project.getStructureData(dataSetCode)  # could be the name
                    _dataSet = _dataSet or project.getStructureData('myStructureData_{}'.format(dataSetCode))
                    _dataSet = _dataSet or self.getStructureData(dataSetCode)
                    if _dataSet is not None:
                        for prefix in ['nef_distance_restraint_list',
                                       'nef_dihedral_restraint_list',
                                       'nef_rdc_restraint_list',
                                       'ccpn_restraint_list']:
                            if _restraintId.startswith(prefix):
                                _name = _restraintId[len(prefix) + 1:]
                                restraintList = _dataSet.getRestraintTable(_name)
                                if restraintList:
                                    break
                if not restraintList:
                    continue

                peakList = _spectrum.getPeakList(peakListNum)
                if not peakList:
                    continue

            peak = peakList._wrappedData.findFirstPeak(serial=row.get('peak_id'))
            if peak is None:
                self.warning(
                        "No peak %s found in %s Skipping peak_restraint_link"
                        % (row.get('peak_id'), row.get('nmr_spectrum_id')),
                        loop
                        )
                continue
            restraint = restraintList._wrappedData.findFirstConstraint(serial=row.get('restraint_id'))
            if restraint is None:
                self.warning(
                        "No restraint %s found in %s Skipping peak_restraint_link"
                        % (row.get('restraint_id'), row.get('restraint_list_id')),
                        loop
                        )
                continue

            # Is all worked, now accumulate the links
            ll = links.get(restraint, set())
            ll.add(peak)
            links[restraint] = ll

        # Set the actual links
        for restraint, peaks in links.items():
            try:
                restraint.peaks = list(peaks)
            except Exception as es:
                self.warning(
                        "Error setting restraint.peaks: %s - %s"
                        % (peaks, str(es)),
                        loop
                        )
        #
        return None

    #
    importers['nef_peak_restraint_link'] = load_nef_peak_restraint_link
    verifiers['nef_peak_restraint_link'] = _noLoopVerify

    def load_ccpn_spectrum_group(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        # framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        if not self._checkImport(saveFrame, parameters['name']):
            # skip if not in the import list
            return

        # Make main object
        result = project.newSpectrumGroup(**parameters)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)
        #
        return result

    #
    importers['ccpn_spectrum_group'] = load_ccpn_spectrum_group

    def verify_ccpn_spectrum_group(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        name = framecode[len(category) + 1:]  #parameters['name']

        # Get main object
        result = project.getSpectrumGroup(name)
        if result is not None:
            self.error('ccpn_spectrum_group - SpectrumGroup {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (name,)

            self._verifyLoops(result, saveFrame)

    verifiers['ccpn_spectrum_group'] = verify_ccpn_spectrum_group

    def load_ccpn_group_spectrum(self, parent: SpectrumGroup, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_group_spectrum loop"""

        spectra = []
        for row in loop.data:
            spectrum = self.project.getSpectrum(row.get('nmr_spectrum_id'))
            if spectrum is None:
                self.warning(
                        "No Spectrum saveframe found with framecode %s. Skipping Spectrum from SpectrumGroup"
                        % row.get('nmr_spectrum_id'),
                        loop
                        )
            else:
                spectra.append(spectrum)
        #
        parent.spectra = spectra

    #
    importers['ccpn_group_spectrum'] = load_ccpn_group_spectrum

    def verify_ccpn_group_spectrum(self, parent: SpectrumGroup, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
        """verify ccpn_group_spectrum loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        for row in loop.data:
            spectrum = self.project.getSpectrum(row.get('nmr_spectrum_id'))
            if spectrum is not None:
                self.error('ccpn_group_spectrum - SpectrumGroup contains {}'.format(spectrum), loop, (spectrum,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_group_spectrum'] = verify_ccpn_group_spectrum

    def load_ccpn_complex(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        # Make main object
        result = project.newComplex(**parameters)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)
        #
        return result

    #
    importers['ccpn_complex'] = load_ccpn_complex

    def verify_ccpn_complex(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        name = framecode[len(category) + 1:]  #parameters['name']

        # Get main object
        result = project.getComplex(name)
        if result is not None:
            self.error('ccpn_complex - Complex {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (name,)

            self._verifyLoops(result, saveFrame)

    verifiers['ccpn_complex'] = verify_ccpn_complex

    def load_ccpn_complex_chain(self, parent: Complex, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_complex_chain loop"""

        chains = []
        for row in loop.data:
            chain = self.project.getChain(row.get('complex_chain_code'))
            if chain is None:
                self.warning(
                        "No Chain found with code %s. Skipping Chain from Complex"
                        % row.get('complex_chain_code'),
                        loop
                        )
            else:
                chains.append(chain)
        #
        parent.chains = chains

    #
    importers['ccpn_complex_chain'] = load_ccpn_complex_chain

    def verify_ccpn_complex_chain(self, parent: Complex, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
        """verify ccpn_complex_chain loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()

        for row in loop.data:
            chain = self.project.getChain(row.get('complex_chain_code'))
            if chain is not None:
                self.error('ccpn_complex_chain - Complex contains {}'.format(chain), loop, (chain,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_complex_chain'] = verify_ccpn_complex_chain

    def load_ccpn_sample(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        from ccpn.core.Sample import _newSample

        # NBNB TODO add crosslinks to spectrum (also for components)

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        self._updateStringParameters(parameters)

        # Make main object
        result = _newSample(project, **parameters)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)
        #
        return result

    #
    importers['ccpn_sample'] = load_ccpn_sample

    def verify_ccpn_sample(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        # mapping = nef2CcpnMap.get(category) or {}
        name = framecode[len(category) + 1:]

        # parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        # Verify main object
        result = project.getSample(name)
        if result is not None:
            self.error('ccpn_sample - Sample {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (name,)

        self._verifyLoops(project, saveFrame, addLoopAttribs=['name'])

    verifiers['ccpn_sample'] = verify_ccpn_sample

    def load_ccpn_sample_component(self, parent: Sample, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_sample_component loop"""
        from ccpn.core.SampleComponent import _newSampleComponent

        result = []

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)
            sc = _newSampleComponent(parent, **parameters)
            result.append(sc)

        return result

    importers['ccpn_sample_component'] = load_ccpn_sample_component

    def verify_ccpn_sample_component(self, parent: Sample, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                     sampleName: str = None):
        """verify ccpn_sample_component loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
        verifyFunc = parent.getSampleComponent

        if sampleName is None:
            self.error('Undefined sampleName', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)

            result = verifyFunc('.'.join([sampleName, parameters.get('name') or '', parameters.get('labelling') or '']))
            if result is not None:
                self.error('ccpn_sample_component - SampleComponent {} already exists'.format(result), loop, (result,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_sample_component'] = verify_ccpn_sample_component

    def load_ccpn_substance(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        from ccpn.core.Substance import _getSubstanceByName

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        name = parameters.pop('name')
        if 'labelling' in parameters:
            labelling = parameters.pop('labelling')
        else:
            labelling = None
        previous = [_getSubstanceByName(project, name)]  #get directly from API and avoid loops.
        sequence = saveFrame.get('sequence_string')
        if sequence and not previous:
            # We have a 'Molecule' type substance with a sequence and no previous occurrence
            # Create it as new polymer
            if ',' in sequence:
                sequence = list(sequence.split(','))
            params = {'molType': saveFrame.get('mol_type')}
            startNumber = saveFrame.get('start_number')
            if startNumber is not None:
                params['startNumber'] = startNumber
            isCyclic = saveFrame.get('is_cyclic')
            if isCyclic is not None:
                params['isCyclic'] = isCyclic
            #
            result = project.createPolymerSubstance(sequence, name, labelling, **params)

        else:
            # find or create substance
            # NB substance could legitimately be existing already, since substances are created
            # when a chain is created.
            result = project.fetchSubstance(name, labelling)
            if previous and previous[0]:
                # In case this is a new Substance, (known name, different labelling)
                # set the sequenceString, if any, to the same as previous
                if previous[0] is not None:
                    sequenceString = previous[0].sequenceString
                    if sequenceString is not None:
                        result.sequenceString = sequenceString

        # Whether substance was pre-existing or not
        # overwrite the missing substance-specific parameters
        for tag, val in parameters.items():
            setattr(result, tag, val)

        # Load loops, with object as parent
        for loopName in loopNames:
            loop = saveFrame.get(loopName)
            if loop:
                importer = self.importers[loopName]
                importer(self, result, loop, saveFrame)
        return result

    #
    importers['ccpn_substance'] = load_ccpn_substance

    def verify_ccpn_substance(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        name = parameters.pop('name')
        if 'labelling' in parameters:
            labelling = parameters.pop('labelling')
        else:
            labelling = None

        # previous = [x for x in project.substances if x.name == name]
        # sequence = saveFrame.get('sequence_string')
        # if sequence and not previous:
        #     pass
        #
        # else:

        # find existing substance
        substanceId = Pid.IDSEP.join(('' if x is None else str(x)) for x in (name, labelling))
        result = project.getSubstance(substanceId)
        if result is not None:
            self.error('ccpn_substance - Substance {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (substanceId,)

        # shouldn't need to verify loopNames

    verifiers['ccpn_substance'] = verify_ccpn_substance

    def load_ccpn_substance_synonym(self, parent: Substance, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame):
        """load ccpn_substance_synonym loop"""

        result = [row['synonym'] for row in loop.data]
        parent.synonyms = result
        #
        return result

    #
    importers['ccpn_substance_synonym'] = load_ccpn_substance_synonym
    verifiers['ccpn_substance_synonym'] = _noLoopVerify

    def load_ccpn_substance_reference_spectra(self, parent: Substance, loop: StarIo.NmrLoop,
                                              saveFrame: StarIo.NmrSaveFrame, **kwargs):
        """load  reference_spectra loop"""

        referenceSpectra = []
        for row in loop.data:
            name = row.get('nmr_spectrum_id')
            spectrum = self.project.getObjectsByPartialId(className='Spectrum', idStartsWith=name)
            # spectrum = self.project.getSpectrum(name)
            if not spectrum:
                self.warning(
                        "No spectrum found with framecode %s. Skipping substance from referenceSubstances"
                        % name, loop)
            else:
                referenceSpectra.append(spectrum)

        parent.referenceSpectra = referenceSpectra

    #
    importers['ccpn_substance_reference_spectra'] = load_ccpn_substance_reference_spectra

    def load_ccpn_assignment(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # the saveframe contains nothing but three loops:
        nmrChainLoopName = 'nmr_chain'
        nmrResidueLoopName = 'nmr_residue'
        nmrAtomLoopName = 'nmr_atom'

        nmrChains = {}
        nmrResidues = {}

        # # ejb - stop notifiers from generating spurious items in the sidebar
        # project.blankNotification()

        # read nmr_chain loop
        mapping = nef2CcpnMap.get(nmrChainLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        creatorFunc = project.newNmrChain
        for row in saveFrame[nmrChainLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            # NOTE:ED - adding flags to restrict importing to the selection
            if not self._checkImport(saveFrame, parameters.get('shortName')):
                continue

            if parameters['shortName'] == coreConstants.defaultNmrChainCode:
                nmrChain = project.getNmrChain(coreConstants.defaultNmrChainCode)
            else:
                nmrChain = creatorFunc(**parameters)
            try:
                nmrChain._resetSerial(row['serial'])
            except Exception as es:
                pass
            nmrChains[parameters['shortName']] = nmrChain

        # # resume notifiers again
        # project.unblankNotification()

        # read nmr_residue loop
        mapping = nef2CcpnMap.get(nmrResidueLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        # reorder the residues so that i-1 residues are after the corresponding i residue
        nmrResidueLoopData = []
        for row in saveFrame[nmrResidueLoopName].data:

            # can't test with an empty list
            if nmrResidueLoopData:

                # check adjacent items have same chain_code and matching sequence_code
                # split should give [', '-...', ] if correct i-1 residue
                # maxsplit required for special fix - sequence code is -1-1
                residueTest = nmrResidueLoopData[-1]['sequence_code'].split(row['sequence_code'], maxsplit=1)
                if row['chain_code'] == nmrResidueLoopData[-1]['chain_code'] \
                        and len(residueTest) > 1 \
                        and residueTest[0] == '' \
                        and residueTest[1].startswith('-'):
                    # if row['chain_code'] == nmrResidueLoopData[-1]['chain_code'] \
                    #     and row['sequence_code'] in nmrResidueLoopData[-1]['sequence_code']:

                    nmrResidueLoopData.insert(-1, row)  # insert 1 from the end

                else:
                    nmrResidueLoopData.append(row)  # else append

            else:  # add the first element
                nmrResidueLoopData.append(row)

        # for row in saveFrame[nmrResidueLoopName].data:
        for row in nmrResidueLoopData:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            parameters['residueType'] = row.get('residue_name')
            # NB chainCode None is not possible here (for ccpn data)
            chainCode = row['chain_code']

            # NOTE:ED - adding flags to restrict importing to the selection
            if not self._checkImport(saveFrame, chainCode):
                continue

            # nmrChain = nmrChains[chainCode]
            nmrChain = project.fetchNmrChain(chainCode)
            nmrResidue = nmrChain.newNmrResidue(**parameters)
            try:
                nmrResidue._resetSerial(row['serial'])
            except Exception as es:
                pass
            # NB former call was BROKEN!
            # modelUtil.resetSerial(nmrResidue, row['serial'], 'nmrResidues')
            nmrResidues[(chainCode, parameters['sequenceCode'])] = nmrResidue

        # read nmr_atom loop
        mapping = nef2CcpnMap.get(nmrAtomLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrAtomLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            chainCode = row['chain_code']

            # NOTE:ED - adding flags to restrict importing to the selection
            if not self._checkImport(saveFrame, chainCode):
                continue

            sequenceCode = row['sequence_code']
            nmrResidue = nmrResidues[(chainCode, sequenceCode)]

            _name = parameters.get('name') or ''
            _match = re.match(REGEXCHECKNMRATOM, _name)
            if _match:
                # remove name if of the form '?@<n>'
                parameters.pop('name', None)

            nmrAtom = nmrResidue.newNmrAtom(**parameters)
            try:
                nmrAtom._resetSerial(row['serial'])
                if _match:
                    # reset name based on the serial number of the nmrAtom
                    # as newNmrAtom creates with name 'nmrAtom@<n>'
                    # can reset the name and _id as serial number is valid
                    nmrAtom._setApiName(None)

            except Exception as es:
                self.warning("Could not set serial of nmrAtom %s" % nmrAtom,
                             saveFrame[nmrAtomLoopName]
                             )

    importers['ccpn_assignment'] = load_ccpn_assignment

    def verify_ccpn_assignment(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # the saveframe contains nothing but three loops:
        _ID = 'ccpn_assignment'
        nmrChainLoopName = 'nmr_chain'
        nmrResidueLoopName = 'nmr_residue'
        nmrAtomLoopName = 'nmr_atom'

        nmrChainLoopSerial = 'nmr_chain_serial'
        saveFrame._rowErrors = AttrDict()
        _nmrChainErrors = saveFrame._rowErrors[nmrChainLoopName] = OrderedSet()
        _nmrChainSerial = saveFrame._rowErrors[nmrChainLoopSerial] = OrderedSet()
        _nmrResidueErrors = saveFrame._rowErrors[nmrResidueLoopName] = OrderedSet()
        _nmrAtomErrors = saveFrame._rowErrors[nmrAtomLoopName] = OrderedSet()

        # read nmr_chain loop
        mapping = nef2CcpnMap.get(nmrChainLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        verifyFunc = project.getNmrChain
        loop = saveFrame[nmrChainLoopName]
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            if parameters['shortName'] == coreConstants.defaultNmrChainCode:
                result = verifyFunc(coreConstants.defaultNmrChainCode)
            else:
                name = parameters['shortName']
                result = verifyFunc(name)
                # shortName.translate(Pid.remapSeparators))
            if result:
                # warning as already exists
                self.error('{} - NmrChain {} already exists'.format(_ID, result), saveFrame, (result,))
                _nmrChainErrors.add(loop.data.index(row))
                _nmrChainSerial.add(result.name)

                itemID = '_'.join([nmrChainLoopName, result.name])
                if itemID not in saveFrame._rowErrors:
                    saveFrame._rowErrors[itemID] = OrderedSet([loop.data.index(row)])
                else:
                    saveFrame._rowErrors[itemID].add(loop.data.index(row))

        nmrResidues = {}
        loop = saveFrame[nmrResidueLoopName]
        for row in loop.data:
            # parameters = self._parametersFromLoopRow(row, map2)
            # parameters['residueType'] = row.get('residue_name')
            # NB chainCode None is not possible here (for ccpn data)
            chainCode = row['chain_code']
            nmrChain = verifyFunc(chainCode)
            if nmrChain is not None:
                name = Pid.IDSEP.join(('' if x is None else str(x)) for x in (row.get('sequence_code'), row.get('residue_name')))
                result = nmrChain.getNmrResidue(name)
                if result is not None:
                    self.error('{} - NmrResidue {} already exists'.format(_ID, result), saveFrame, (result,))
                    nmrResidues[(chainCode, row.get('sequence_code'))] = result
                    _nmrResidueErrors.add(loop.data.index(row))

                    itemID = '_'.join([nmrResidueLoopName, chainCode])
                    if itemID not in saveFrame._rowErrors:
                        saveFrame._rowErrors[itemID] = OrderedSet([loop.data.index(row)])
                    else:
                        saveFrame._rowErrors[itemID].add(loop.data.index(row))

            sequenceCode = row['sequence_code']
            if sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
                # this is a reserved name
                serial = int(sequenceCode[1:])
                obj = project._wrappedData.findFirstResonanceGroup(serial=serial)
                if obj is not None:
                    self.error('{} - NmrResidue sequenceCode @{} already exists'.format(_ID, serial), saveFrame, (None,))
                    _nmrResidueErrors.add(loop.data.index(row))
                    itemID = '_'.join([nmrResidueLoopName, chainCode])
                    if itemID not in saveFrame._rowErrors:
                        saveFrame._rowErrors[itemID] = OrderedSet([loop.data.index(row)])
                    else:
                        saveFrame._rowErrors[itemID].add(loop.data.index(row))

                    # add the error to the chain loop
                    _chainLoop = saveFrame[nmrChainLoopName]
                    for _chainRow in _chainLoop.data:
                        _name = _chainRow.get('short_name')
                        if _name == chainCode:
                            _nmrChainErrors.add(_chainLoop.data.index(_chainRow))
                            _nmrChainSerial.add(chainCode)
                            itemID = '_'.join([nmrChainLoopName, chainCode])
                            if itemID not in saveFrame._rowErrors:
                                saveFrame._rowErrors[itemID] = OrderedSet([_chainLoop.data.index(_chainRow)])
                            else:
                                saveFrame._rowErrors[itemID].add(_chainLoop.data.index(_chainRow))
                            break

        # read nmr_atom loop
        mapping = nef2CcpnMap.get(nmrAtomLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        loop = saveFrame[nmrAtomLoopName]
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['chain_code']
            sequenceCode = row['sequence_code']
            nmrResidue = nmrResidues.get((chainCode, sequenceCode))
            if nmrResidue:
                nmrAtom = nmrResidue.getNmrAtom(row.get('name'))
                if nmrAtom is not None:
                    self.error('{} - NmrAtom {} already exists'.format(_ID, nmrAtom), saveFrame, (nmrAtom,))
                    _nmrAtomErrors.add(loop.data.index(row))

                    itemID = '_'.join([nmrAtomLoopName, chainCode])
                    if itemID not in saveFrame._rowErrors:
                        saveFrame._rowErrors[itemID] = OrderedSet([loop.data.index(row)])
                    else:
                        saveFrame._rowErrors[itemID].add(loop.data.index(row))

            # add the error to the atom loop
            if sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
                # this is a reserved name
                serial = int(sequenceCode[1:])
                obj = project._wrappedData.findFirstResonanceGroup(serial=serial)
                if obj is not None:
                    self.error('{} - NmrAtom sequenceCode @{} already exists'.format(_ID, serial), saveFrame, (None,))
                    _nmrAtomErrors.add(loop.data.index(row))
                    itemID = '_'.join([nmrAtomLoopName, chainCode])
                    if itemID not in saveFrame._rowErrors:
                        saveFrame._rowErrors[itemID] = OrderedSet([loop.data.index(row)])
                    else:
                        saveFrame._rowErrors[itemID].add(loop.data.index(row))

    verifiers['ccpn_assignment'] = verify_ccpn_assignment
    verifiers['nmr_chain'] = _noLoopVerify
    verifiers['nmr_residue'] = _noLoopVerify
    verifiers['nmr_atom'] = _noLoopVerify

    def load_ccpn_notes(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # ccpn_notes contains nothing except for the ccpn_note loop
        loopName = 'ccpn_note'
        loop = saveFrame[loopName]
        creatorFunc = project.newNote

        result = []
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            if not self._checkImport(saveFrame, parameters['name']):
                # skip if not in the import list
                continue

            parameters.pop('serial', None)  # remove from parameters, not required
            obj = creatorFunc(**parameters)
            result.append(obj)

            # load time stamps and serial
            created = row.get('created')
            if created:
                obj.created = created
            lastModified = row.get('last_modified')
            if lastModified:
                obj.lastModified = lastModified

        return result

    importers['ccpn_notes'] = load_ccpn_notes

    def load_ccpn_collections(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # ccpn_collections contains nothing except for the ccpn_collection loop
        loopName = 'ccpn_collection'
        loop = saveFrame[loopName]
        creatorFunc = project.fetchCollection

        result = []
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            self._updateStringParameters(parameters)

            if not self._checkImport(saveFrame, parameters['name']):
                # skip if not in the import list
                continue

            if (name := parameters.pop('name', None)):
                comment = parameters.pop('comment', None)
                parameters.pop('uniqueId', None)  # remove from parameters, although it shouldn't be there
                obj = creatorFunc(name=name)
                result.append(obj)

                if comment:
                    obj.comment = comment
                if (itms := row.get('items')):
                    itms = json.loads(itms)
                    _itms = [project.getByPid(itm) for itm in itms]
                    obj.items = list(set(obj.items) | set(filter(None, _itms)))

        return result

    importers['ccpn_collections'] = load_ccpn_collections

    def verify_ccpn_notes(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        loopName = 'ccpn_note'
        loop = saveFrame[loopName]
        _rowErrors = saveFrame._rowErrors[loopName] = OrderedSet()
        saveFrame._rowErrors['ccpn_notes'] = OrderedSet()
        verifyFunc = project.getNote

        result = []
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            name = parameters['name']
            result = verifyFunc(name)
            if result:
                self.error('ccpn_notes - Note {} already exists'.format(result), saveFrame, (result,))
                _rowErrors.add(loop.data.index(row))
                saveFrame._rowErrors['ccpn_notes'].add(name)
                saveFrame._rowErrors['ccpn_note_' + name] = (loop.data.index(row),)

    verifiers['ccpn_notes'] = verify_ccpn_notes
    verifiers['ccpn_note'] = _noLoopVerify

    def verify_ccpn_collections(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        loopName = 'ccpn_collection'
        loop = saveFrame[loopName]
        _rowErrors = saveFrame._rowErrors[loopName] = OrderedSet()
        saveFrame._rowErrors['ccpn_collections'] = OrderedSet()
        verifyFunc = project.getCollection

        result = []
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            name = parameters['name']
            result = verifyFunc(name)
            if result:
                self.error('ccpn_collections - Collection {} already exists'.format(result), saveFrame, (result,))
                _rowErrors.add(loop.data.index(row))
                saveFrame._rowErrors['ccpn_collections'].add(name)
                saveFrame._rowErrors['ccpn_collection_' + name] = (loop.data.index(row),)

    verifiers['ccpn_collections'] = verify_ccpn_collections
    verifiers['ccpn_collection'] = _noLoopVerify

    def load_ccpn_additional_data(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        # ccpn_additional_data contains nothing except for the ccpn_internal_data loop
        loopName = 'ccpn_internal_data'
        loop = saveFrame[loopName]

        for row in loop.data:
            pid, data = row.values()

            if not self._checkImport(saveFrame, pid):
                # skip if not in the import list
                continue

            obj = project.getByPid(pid)
            if obj is None:
                getLogger().debug2('Loading NEF additional data: unable to find object "%s"' % pid)
            else:
                # read in the new _ccpnInternal and write the existing over the top
                if (dataIn := jsonIo.loads(data)) and isinstance(dataIn, dict):
                    try:
                        if existingInternal := obj._ccpnInternalData:
                            if self._projectIsEmpty:
                                # recursively update the dict replacing the original values
                                dataIn = mergeDict(existingInternal, dataIn)
                            else:
                                # recursively update the dict adding new keys, but keep the original values
                                dataIn = mergeDict(dataIn, existingInternal)
                        obj._ccpnInternalData = dataIn
                    except:
                        self.warning(f'Could not load additional data for {obj}', loop)

    importers['ccpn_additional_data'] = load_ccpn_additional_data

    def verify_ccpn_additional_data(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        loopName = 'ccpn_internal_data'
        loop = saveFrame[loopName]
        _rowErrors = saveFrame._rowErrors[loopName] = OrderedSet()
        saveFrame._rowErrors['ccpn_additional_data'] = OrderedSet()
        verifyFunc = project.getByPid

        for row in loop.data:
            pid, data = row.values()
            result = verifyFunc(pid)

            if result:
                data = result._ccpnInternalData
                if data:
                    self.error('ccpn_additional_data - Object {} contains internal data'.format(result), saveFrame, (result,))
                    _rowErrors.add(loop.data.index(row))
                    saveFrame._rowErrors['ccpn_additional_data'].add(pid)
                    saveFrame._rowErrors['ccpn_internal_data_' + pid] = (loop.data.index(row),)

    verifiers['ccpn_additional_data'] = verify_ccpn_additional_data
    verifiers['ccpn_internal_data'] = _noLoopVerify

    def load_ccpn_dataset(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """load dataSet savefame"""
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        creatorFunc = project.newStructureData
        mapping = nef2CcpnMap.get(category) or {}

        name = framecode[len(category) + 1:]
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        # Make main object - remove blank parameters
        parameters.pop('serial', None)  # serial not needed
        for k, v in list(parameters.items()):
            if not v:
                parameters.pop(k, None)
        result = creatorFunc(**parameters)
        if result:
            # Load loops, with object as parent
            for loopName in loopNames:
                loop = saveFrame.get(loopName)
                if loop:
                    importer = self.importers[loopName]
                    importer(self, result, loop, saveFrame, name)

        return result

    importers['ccpn_dataset'] = load_ccpn_dataset

    def verify_ccpn_dataset(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify contents of dataSet saveFrame"""
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        name = framecode[len(category) + 1:]

        # Verify main object
        dataSet = project.getStructureData(name)
        if dataSet is not None:
            self.error('ccpn_dataset - dataSet {} already exists'.format(dataSet), saveFrame, (dataSet,))
            saveFrame._rowErrors[category] = (name,)

            self._verifyLoops(dataSet, saveFrame, name=name)

    verifiers['ccpn_dataset'] = verify_ccpn_dataset

    def load_ccpn_calculation_step(self, parent: StructureData, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                   name: str):
        """load dataSet.calculation_step loop"""
        # NOTE:ED - not checked yet
        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            calc = parent.getCalculationStep(parameters.get('name'))
            if not calc:
                parent.newCalculationStep(**parameters)

    importers['ccpn_calculation_step'] = load_ccpn_calculation_step

    def verify_ccpn_calculation_step(self, parent: StructureData, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                     name: str):
        """verify dataSet.calculation_step loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
        for row in loop.data:
            # get calculation step
            serial = row.get('serial')
            calc = parent.getCalculationStep(serial)
            if calc is not None:
                self.error('ccpn_dataset - CalculationStep {} already exists'.format(calc), loop, (calc,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_calculation_step'] = verify_ccpn_calculation_step

    def load_ccpn_calculation_data(self, parent: StructureData, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                                   name: str):
        """load dataSet.calculation_step loop"""
        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])

        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            data = parent.getData(parameters.get('name'))
            if not data:
                parent.newData(**parameters)

    importers['ccpn_calculation_data'] = load_ccpn_calculation_data

    def verify_ccpn_calculation_data(self, parent: StructureData, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                     name: str):
        """verify dataSet.calculation_step loop"""
        _rowErrors = parentFrame._rowErrors[loop.name] = OrderedSet()
        for row in loop.data:
            # get calculation data
            name = row.get('data_name')
            data = parent.getData(name)
            if data is not None:
                self.error('ccpn_dataset - Data {} already exists'.format(data), loop, (data,))
                _rowErrors.add(loop.data.index(row))

    verifiers['ccpn_calculation_data'] = verify_ccpn_calculation_data

    def load_ccpn_parameter(self, project: Project, saveFrame: StarIo.NmrSaveFrame):

        from ccpn.core.lib.CcpnDataSetParameters import setCcpnNefParameter

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        name = framecode[len(category) + 1:]
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        if not loopNames:
            result = setCcpnNefParameter(project, **parameters)
        else:
            # Load loops, with object as parent
            for loopName in loopNames:
                loop = saveFrame.get(loopName)
                if loop:
                    importer = self.importers[loopName]
                    importer(self, project, loop, saveFrame, **parameters)

    importers['ccpn_parameter'] = load_ccpn_parameter

    def verify_ccpn_parameter(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """verify ccpn_parameter saveFrame"""
        from ccpn.core.lib.CcpnDataSetParameters import getCcpnNefParameter

        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        name = framecode[len(category) + 1:]

        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        _name = f"{parameters.get('dataSet')}.{parameters.get('name')}:{parameters.get('parameterName')}"

        # verify parameter
        parameters.pop('value', None)
        result = getCcpnNefParameter(project, **parameters)
        if result is not None:
            self.error('ccpn_parameter - ccpnParameter {} already exists'.format(result), saveFrame, (result,))
            saveFrame._rowErrors[category] = (_name,)

    verifiers['ccpn_parameter'] = verify_ccpn_parameter
    verifiers['ccpn_dataframe'] = _noLoopVerify

    def load_ccpn_dataframe(self, project: Project, loop: StarIo.NmrLoop, saveFrame: StarIo.NmrSaveFrame,
                            **parameters):
        """Serves to load ccpn_distance_restraint_violation loops"""
        from ccpn.core.lib.CcpnDataSetParameters import setCcpnNefParameter

        if loop and loop.data:
            # if loop.data exists then load as a pandas dataFrame
            _df = pd.DataFrame(loop.data)

            if _df is not None:

                # NOTE:ED - need to modify the headers somewhere more sensible
                from ccpn.ui.gui.modules.lib.RestraintAITableCommon import Headers, nefHeaders

                # list of header types that need swapping - need the opposite to save
                _headers = [(nefHeaders, Headers),
                            ]

                dfHeaders = list(_df.columns)
                for oldHeaders, newHeaders in _headers:
                    if all(hh in oldHeaders for hh in dfHeaders):
                        # rename all the column headers to the correct names
                        _df.rename(columns={old: new for old, new in zip(oldHeaders, newHeaders)}, inplace=True)

                parameters['value'] = _df

                # store in the project
                try:
                    setCcpnNefParameter(project, **parameters)
                except Exception as es:
                    raise

    importers['ccpn_dataframe'] = load_ccpn_dataframe

    def _parametersFromSaveFrame(self, saveFrame: StarIo.NmrSaveFrame, mapping: OD,
                                 ccpnPrefix: str = None):
        """Extract {parameter:value} dictionary and list of loop names from saveFrame

    The mapping gives the map from NEF tags to ccpn tags.
    If the ccpn tag is of the form <ccpnPrefix.tag> it is ignored unless
    the first part of the tag matches the passed-in ccpnPrefix
    (NB the ccpnPrefix may contain '.').
    """

        # Get attributes that have a simple tag mapping, and make a separate loop list
        parameters = {}
        loopNames = []
        if ccpnPrefix is None:
            # Normal extraction from saveframe map
            for tag, ccpnTag in mapping.items():
                if ccpnTag == _isALoop:
                    loopNames.append(tag)
                elif ccpnTag and '.' not in ccpnTag:
                    val = saveFrame.get(tag)
                    if val is not None:
                        # necessary as tags like ccpn_serial should NOT be set if absent of None
                        parameters[ccpnTag] = val
        else:
            # extracting tags of the form `ccpnPrefix`.tag
            for tag, ccpnTag in mapping.items():
                if ccpnTag == _isALoop:
                    loopNames.append(tag)
                elif ccpnTag:
                    parts = ccpnTag.rsplit('.', 1)
                    if parts[0] == ccpnPrefix:
                        val = saveFrame.get(tag)
                        if val is not None:
                            # necessary as tags like ccpn_serial should NOT be set if absent of None
                            parameters[parts[1]] = val

        #
        return parameters, loopNames

    def error(self, message: str, source, objects: Optional[tuple] = None):
        """Update the error log with the message
        """
        # # MUST BE SUBCLASSED
        # raise NotImplementedError("Code error: function not implemented")
        template = "Error in saveFrame {}: {}"
        self.errors.append((template.format(self._saveFrameName, message), source, objects))

    def warning(self, message: str, loopName=None):
        template = "in saveFrame %s:\n%s"
        self.warnings.append(template % (self._saveFrameName, message))

    def produceNmrChain(self, chainCode: str = None):
        """Get NmrChain, correcting for possible errors"""

        if chainCode is None:
            chainCode = coreConstants.defaultNmrChainCode
        newChainCode = chainCode
        while True:
            try:
                nmrChain = self.project.fetchNmrChain(newChainCode)
                return nmrChain
            except ValueError:
                newChainCode = '`%s`' % newChainCode
                self.warning("New NmrChain:%s name caused an error.  Renamed %s"
                             % (chainCode, newChainCode))

    def produceNmrResidue(self, chainCode: str = None, sequenceCode: str = None, residueType: str = None):
        """Get NmrResidue, correcting for possible errors"""

        chainCode = chainCode or self.defaultChainCode

        inputTuple = (chainCode, sequenceCode, residueType)
        result = self._nmrResidueMap.get(inputTuple)
        if result is not None:
            return result

        if not sequenceCode:
            return
            # raise ValueError("Cannot produce NmrResidue for sequenceCode: %s" % repr(sequenceCode))

        if isinstance(sequenceCode, int):
            sequenceCode = str(sequenceCode)

        nmrChain = self.produceNmrChain(chainCode)

        rt = residueType or ''
        cc = nmrChain.shortName

        try:
            result = nmrChain.fetchNmrResidue(sequenceCode, residueType)
            # return result
        except ValueError:
            # This can happen legitimately, e.g. for offset residues
            # Further processing needed.

            # Parse values from sequenceCode
            seqNo, insertCode, offset = commonUtil.parseSequenceCode(sequenceCode)

            if offset is None:
                if residueType:
                    # This could be a case where the NmrResidue had been created from an offset NmrResidue
                    # with the residueType therefore missing.
                    # If so, set the residueType
                    # NBNB this also has the effect of having real entries with empty residueType
                    # overridden by clashing entries with residueType set,
                    # but that does make some sense and anyway cannot be helped.

                    # NB this must be a pre-existing residue or it would have been created above.
                    try:
                        previous = nmrChain.fetchNmrResidue(sequenceCode)
                        if not previous.residueType:
                            result = previous
                            result.residueType = residueType
                            # return result
                    except ValueError:
                        # Deal with it below
                        pass

            else:
                # Offset NmrResidue - get mainNmrResidue
                ss = '%+d' % offset
                try:
                    # Fetch the mainNmrResidue. This will create it if it is missing (if possible)
                    mainNmrResidue = nmrChain.fetchNmrResidue(sequenceCode[:-len(ss)])
                except ValueError:
                    # No go
                    mainNmrResidue = None

                if mainNmrResidue is not None:
                    try:
                        result = nmrChain.fetchNmrResidue(sequenceCode, residueType)
                        # return result
                    except ValueError:
                        # Handle lower down
                        pass

        # If e get here, we could not make an NmrResidue that matched the input
        # Make with modified sequenceCode
        if result is None:
            newSequenceCode = sequenceCode
            while True:
                try:
                    result = nmrChain.fetchNmrResidue(newSequenceCode, residueType)
                    return result
                except ValueError:
                    newSequenceCode = '`%s`' % newSequenceCode
                    self.warning("New NmrResidue:%s.%s.%s name caused an error.  Renamed %s.%s.%s"
                                 % (cc, sequenceCode, rt, cc, newSequenceCode, rt))
        #
        # Result cannot have been in map, so put it there
        self._nmrResidueMap[inputTuple] = result
        return result

    def produceNmrAtom(self, nmrResidue: NmrResidue, name: str, isotopeCode=None):
        """Get NmrAtom from NmrResidue and name, correcting for possible errors"""

        if not name:
            raise ValueError("Cannot produce NmrAtom for atom name: %s" % repr(name))

        # this needs addressing and probably requires Q-atoms to be added to resources
        if isotopeCode and not (isotopeCode == '1H' and name.startswith('Q')):
            prefix = isotopeCode.upper()
            if not name.startswith(prefix):
                prefix = isotopeCode2Nucleus(isotopeCode)
                if prefix is None:
                    self.warning("Ignoring unsupported isotopeCode: %s for NmrAtom:%s.%s"
                                 % (isotopeCode, nmrResidue._id, name))
                elif not name.startswith(prefix):
                    newName = '%s@%s' % (prefix, name)
                    self.warning("NmrAtom name %s does not match isotopeCode %s - renamed to %s"
                                 % (isotopeCode, name, newName))
                    name = newName

        newName = name
        while True:
            nmrAtom = nmrResidue.getNmrAtom(newName.translate(Pid.remapSeparators))
            if nmrAtom is None:
                try:
                    nmrAtom = nmrResidue.newNmrAtom(newName, isotopeCode)
                    return nmrAtom
                except ValueError:
                    pass
            elif isotopeCode in (None, nmrAtom.isotopeCode):
                # We must ensure that the isotopeCodes match
                return nmrAtom
            else:
                # IsotopeCode mismatch. Try to
                if prefix == isotopeCode.upper():
                    # Something wrong here.
                    raise ValueError("Clash between NmrAtom %s (%s) and %s (%s) in %s"
                                     % (nmrAtom.name, nmrAtom.isotopeCode, newName, isotopeCode, nmrResidue))
                else:
                    newName = isotopeCode.upper() + newName[len(prefix):]
                    continue

            # If we get here there was an error. Change name and try again
            tt = newName.rsplit('_', 1)
            if len(tt) == 2 and tt[1].isdigit():
                newName = '%s_%s' % (tt[0], int(tt[1]) + 1)
            else:
                newName += '_1'
            self.warning("New NmrAtom:%s.%s name caused an error.  Renamed %s.%s"
                         % (nmrResidue._id, name, nmrResidue._id, newName))

    def updateMetaData(self, metaDataFrame: StarIo.NmrSaveFrame):
        """Add meta information to main data set. Must be done at end of read"""

        # NBNB NOT WORKING YET!

        # dataSet = self.fetchStructureData(self.mainDataSetSerial)
        self.mainDataSetSerial = None

    def _defaultName(self, cls, serial):
        # Get the next class name using serial, this may already exist
        return '%s_%s' % (cls._defaultName(), serial)

    def fetchStructureData(self, sDataName: str = None, serial: int = None):
        """Fetch StructureData with given serial.
        If input is None, use self.defaultDataSetSerial
        If that too is None, create a new DataSet and use its serial as the default

        NB when reading, all StructureData with known serials should be instantiated BEFORE calling
        with input None"""

        # if serial is None and sDataName is None:
        #     serial = self.defaultDataSetSerial

        sData = self.project.getStructureData(sDataName)  # if sDataName else None
        sData = sData or self.project.newStructureData(sDataName)

        # if serial is None:
        #     # default not set - create one
        #     dataSet = dataSet or self.project.newStructureData(sDataName)
        #     self.defaultDataSetSerial = dataSet.serial
        # else:
        #     dataSet = dataSet or self.getStructureData(serial)
        #     if dataSet is None:
        #         _name = sDataName or self._defaultName(StructureData, serial)
        #         _name = StructureData._uniqueName(parent=self.project, name=_name)
        #         dataSet = self.project.newStructureData(name=_name, )

        # # # take or create dataSet matching serial
        # # dataSet = dataSet or self.getStructureData(serial)
        # if dataSet is None:
        #     _name = sDataName or self._defaultName(DataSet, serial)
        #     dataSet = self.project.newDataSet(name=_name, )  #serial=serial)

        # try:
        #     dataSet._resetSerial(serial)
        # except Exception as es:
        #     self.warning(f'Cannot reset serial of dataSet {dataSet}')
        #
        self._dataSet2ItemMap[sData] = sData._getTempItemMap()

        return sData

    def getStructureData(self, serial: int = None):
        """Get the required DataSet with given serial.
        If input is None, use self.defaultDataSetSerial
        If that too is None, create a new DataSet and use its serial as the default

        NB when reading, all StructureData with known serials should be instantiated BEFORE calling
        with input None"""

        if serial is None:
            serial = self.defaultDataSetSerial or 1
        # _name = self._defaultName(DataSet, serial)
        # return self.project.getStructureData(_name)
        dataSets = [ds for ds in self.project.structureData if ds.serial == serial]
        if dataSets:
            if len(dataSets) > 1:
                raise RuntimeError('CcpnNefReader.getStructureData: too many structureData with the same serial')
            return dataSets[0]


def _printOutMappingDict(mappingDict: dict):
    """Utility - print out mapping dict for editing and copying"""
    saveframeOrder = []
    print("# NEf to CCPN tag mapping (and tag order)")
    print("{\n")
    for category, od in mappingDict.items():
        saveframeOrder.append(category)
        print("  %s:OD((" % repr(category))
        for tag, val in od.items():
            if isinstance(val, str) or val is None:
                print("    (%s,%s)," % (repr(tag), repr(val)))
            else:
                # This must be a loop OD
                print("    (%s,OD((" % repr(tag))
                for tag2, val2 in val.items():
                    print("      (%s,%s)," % (repr(tag2), repr(val2)))
                print("    ))),")
        print("  )),\n")
    print("}\n")

    print("#SaveFrameOrder\n[")
    for tag in saveframeOrder:
        print("  %s," % repr(tag))
    print("]\n")


def _exportToNef(path: str, skipPrefixes: Sequence[str] = ()):
    if path.endswith('.ccpn'):
        outPath = path[:-4] + 'nef'
    elif path.endswith('.ccpn/'):
        outPath = path[:-5] + 'nef'
    elif path.endswith('/'):
        outPath = path[:-1] + '.nef'
    else:
        outPath = path + '.nef'

    from ccpn.framework.Framework import createFramework

    path = os.path.normpath(os.path.abspath(path))
    time1 = time.time()
    application = createFramework(_skipUpdates=True)
    application.loadProject(path)
    project = application.project
    time2 = time.time()
    print("====> Loaded %s from file in seconds %s" % (project.name, time2 - time1))
    saveNefProject(project, outPath, overwriteExisting=True, skipPrefixes=skipPrefixes)
    time3 = time.time()
    print("====> Saved  %s  to  NEF file in seconds %s" % (project.name, time3 - time2))

    # Needed to clean up notifiers - not any more
    # project.delete()
    #
    return outPath


# from ccpn.util.nef.GenericStarParser import DataBlock
# from collections import OrderedDict
#
#
# def _convertToDataBlock(self: Project, skipPrefixes: typing.Sequence = (),
#                         expandSelection: bool = True,
#                         includeOrphans: bool = False,
#                         pidList: list = None):
#     """
#   Export selected contents of the project to a Nef file.
#
#     skipPrefixes: ( 'ccpn', ..., <str> )
#     expandSelection: <bool>
#     includeOrphans: <bool>
#
#     Include 'ccpn' in the skipPrefixes list will exclude ccpn specific items from the file
#     expandSelection = True  will include all data from the project, this may not be data that
#                             is not defined in the Nef standard.
#     includeOrphans = True   will include chemicalShifts that have no peak assignments(orphans)
#
#   PidList is a list of <str>, e.g. 'NC:@-', obtained from the objects to be included.
#   The Nef file may also contain further dependent items associated with the pidList.
#
#   :param skipPrefixes: items to skip
#   :param expandSelection: expand the selection
#   :param includeOrphans: include chemicalShift orphans
#   :param pidList: a list of pids
#   """
#     from ccpn.core.lib.ContextManagers import undoBlockManager
#
#     with undoBlockManager():
#         dataBlock = convertToDataBlock(self, skipPrefixes=skipPrefixes,
#                                        expandSelection=expandSelection,
#                                        pidList=pidList)
#
#     return dataBlock
#
#
# def _writeDataBlockToFile(self: Project, dataBlock: DataBlock = None, path: str = None,
#                           overwriteExisting: bool = False):
#     # Export the modified dataBlock to file
#     from ccpn.core.lib.ContextManagers import undoBlockManager
#
#     with undoBlockManager():
#         writeDataBlock(dataBlock, path=path, overwriteExisting=overwriteExisting)


def _testNefIo(path: str, skipPrefixes: Sequence[str] = ()):
    from ccpn.framework.Framework import createFramework

    path = os.path.normpath(os.path.abspath(path))

    if path.endswith('.nef'):
        outPath = path[:-4] + '.out.nef'
    else:
        raise ValueError("File name does not end in '.nef': %s" % path)

    time1 = time.time()
    application = createFramework(_skipUpdates=True)
    application.nefReader.testing = True
    application.loadProject(path)

    project = application.project
    # spectrum = project.spectra[0]
    time2 = time.time()
    print("====> Loaded %s from NEF file in seconds %s" % (project.name, time2 - time1))
    saveNefProject(project, outPath, overwriteExisting=True, skipPrefixes=skipPrefixes)
    time3 = time.time()
    print("====> Saved  %s  to  NEF file in seconds %s" % (project.name, time3 - time2))
    # Needed to clean up notifiers
    project.delete()

    return outPath


# def _extractVariantsTable(aa_variants_cif:str)-> str:
#   """Read aa-variants.cif file contents and return variants mapping table string"""
#
#   lineformat = "%-15s    %-12s    %-7s    %-15s"
#   lines =[lineformat % ('MMCIF_code', "residue_name", "linking", "residue_variant")]
#
#   #
#   # 'LL'
#   # linkingMap = {
#   #   'LL':'middle',
#   #   'LEO2':'end', # deprotonated
#   #   'LEO2H':'end', # deprotonated
#   #   'LFOH':'single', # neutral
#   #   'LFZW':'single', # zwitter
#   #   'LSN3':'start', # protonated
#   #
#   # }
#
#   names = []
#
#   for line in open(aa_variants_cif):
#
#     hxt = False
#
#     if 'data_' in line:
#       ll = line.strip().split('_')
#       if len(ll) == 2:
#         pass
#       else:
#         name = ll[1]
#         names.append(name)
#         ll2 = []
#         lnk = ll[2]
#         linking = '.'
#         if lnk == 'LL':
#           linking = 'middle'
#         elif lnk == 'LEO2':
#           linking = 'end'
#         elif lnk == 'LEO2H':
#           linking = 'end'
#           hxt = True
#         elif lnk == 'LFZW':
#           linking = 'single'
#         elif lnk == 'LFOH':
#           linking = 'single'
#           ll2.append('-H3')
#           hxt = True
#         elif lnk == 'LSN3':
#           linking = 'start'
#         else:
#           print('WARNING, not recognised', ll)
#
#         if len(ll) > 3:
#           var = ll[3]
#           if var[0] == 'D':
#             ll2.append('-'+var[1:])
#           else:
#             print ("NB Ignoring MMcif variant %s" % var)
#
#         # Sort before further treatment, to make sure '+' markers come at the end
#         ll2.sort()
#
#         # Special handling for ASP and GLU - where default is side chain deprotonated
#         if name == 'ASP':
#           if '-HD2' in ll2:
#             ll2.remove('-HD2')
#           else:
#             ll2.append('+HD2')
#         elif name == 'GLU':
#           if '-HE2' in ll2:
#             ll2.remove('-HE2')
#           else:
#             ll2.append('+HE2')
#         elif name == 'HIS':
#           if '-HE2' in ll2:
#             ll2.remove('-HE2')
#           else:
#             ll2.append('+HE2')
#
#         # NBNB
#
#         if hxt:
#           ll2.append('+HXT')
#         if ll2:
#           variant = ','.join(ll2)
#         else:
#           variant = '.'
#         ss = lineformat % ('_'.join(ll[1:]), name, linking, variant)
#
#         lines.append(ss)
#
#   #
#   print (Counter(names))
#
#   #
#   return '\n'.join(lines)

def main():
    # Explanation:
    # _exportToNef will read a project from path and export the corresponding NEF file
    # skipPrefixes=('ccpn', ) means 'remove all ccpn-specific tags from the output';
    # default is to leave them in. Note that path may also be a NEF file,
    # which will then be imported and re-exported
    #
    # testNefIo will read a NEF file and re-export it (with a .out.nef suffix),
    # producing a V3 project on disk as a byproduct if the original is a V2 project.

    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("CcpnNefIo exports a project as a NEF file. Usage:"
              "\n\n One mandatory argument - the project directory to export")
    else:
        path = sys.argv[1]
        nefpath = _exportToNef(path)

    # _testNefIo(path, skipPrefixes=('ccpn', ))
    # _testNefIo(path)
    # _testNefIo(nefpath)
    # nefpath = _exportToNef(path, skipPrefixes=('ccpn', ))
    # _testNefIo(nefpath, skipPrefixes=('ccpn', ))
    # print(_extractVariantsTable(path))


import unittest


class testMergeDict(unittest.TestCase):

    def test_merge_d1d2(self):
        """Merge d2 into d1
        """
        d1 = {
            "Boolean1"  : (True, None, False),
            "Boolean2"  : True,
            "DictOuter" : {"String1"    : 'string1',
                           "nestedLists": [0],
                           "MuteL"      : {},
                           },
            "nestedDict": [],
            }

        d2 = {
            "Boolean2"  : False,
            "Boolean3"  : (True,),
            "DictOuter" : {"String2"    : 'string2',
                           "nestedLists": [99],
                           "MuteL"      : 1.0,
                           },
            "nestedDict": {"Boolean1": {"NewItem": 'New',
                                        }
                           },
            }

        result = {
            "Boolean1"  : (True, None, False),
            "Boolean2"  : False,  # from d2
            "DictOuter" : {"String1"    : 'string1',
                           "nestedLists": [99],  # from d2
                           "MuteL"      : 1.0,
                           "String2"    : 'string2',  # from d2
                           },
            "nestedDict": {"Boolean1": {"NewItem": 'New',  # from d2
                                        }
                           },
            "Boolean3"  : (True,),  # from d2
            }

        # inplace merge
        out = mergeDict(d1, d2)

        self.assertEqual(out, result)

    def test_merge_d2d1(self):
        """Merge d1 into d2
        """
        d1 = {
            "Boolean1"  : (True, None, False),
            "Boolean2"  : True,
            "DictOuter" : {"String1"    : 'string1',
                           "nestedLists": [0],
                           "MuteL"      : {},
                           },
            "nestedDict": [],
            }

        d2 = {
            "Boolean2"  : False,
            "Boolean3"  : (True,),
            "DictOuter" : {"String2"    : 'string2',
                           "nestedLists": [99],
                           "MuteL"      : 1.0,
                           },
            "nestedDict": {"Boolean1": {"NewItem": 'New',
                                        }
                           },
            }

        result = {
            "Boolean2"  : True,  # from d1
            "Boolean3"  : (True,),
            "DictOuter" : {"String2"    : 'string2',
                           "nestedLists": [0],  # from d1
                           "MuteL"      : {},
                           "String1"    : 'string1',  # from d1
                           },
            "nestedDict": [],  # from d1
            "Boolean1"  : (True, None, False),  # from d1
            }

        # inplace merge
        out = mergeDict(d2, d1)

        self.assertEqual(out, result)

    def test_merge_bad(self):
        d1 = {'a': 'b'}

        self.assertRaises(TypeError, mergeDict, d1, [])
        self.assertRaises(TypeError, mergeDict, [], d1)


if __name__ == '__main__':
    testMergeDict()
