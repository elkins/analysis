"""
"""
from __future__ import annotations


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
__dateModified__ = "$dateModified: 2024-10-02 10:04:24 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import functools
import os
import typing
import operator
from typing import Sequence, Union, Optional, List, Any
from collections import OrderedDict
from datetime import datetime
from collections.abc import Iterable
import pandas as pd
import numpy as np
import re

from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core._implementation.Updater import UPDATE_POST_PROJECT_INITIALISATION
from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC

from ccpn.core.lib import Pid
from ccpn.core.lib import Undo
from ccpn.core.lib.ProjectSaveHistory import getProjectSaveHistory, newProjectSaveHistory
from ccpn.core.lib.ProjectLib import createLogger
from ccpn.core.lib.ContextManagers import notificationBlanking, undoBlock, undoBlockWithoutSideBar, \
    inactivity, logCommandManager, ccpNmrV3CoreUndoBlock

from ccpn.util import Logging
from ccpn.util.ExcelReader import ExcelReader
from ccpn.util.Path import aPath, Path
from ccpn.util.Logging import getLogger, updateLogger
from ccpn.util.decorators import logCommand
from ccpn.ui.gui.guiSettings import consoleStyle

from ccpn.framework.lib.pipeline.PipelineBase import Pipeline
from ccpn.framework.PathsAndUrls import \
    CCPN_ARCHIVES_DIRECTORY, \
    CCPN_STATE_DIRECTORY, \
    CCPN_DATA_DIRECTORY, \
    CCPN_SPECTRA_DIRECTORY, \
    CCPN_PLUGINS_DIRECTORY, \
    CCPN_SCRIPTS_DIRECTORY, \
    CCPN_SUB_DIRECTORIES, \
    CCPN_LOGS_DIRECTORY, \
    CCPN_DIRECTORY_SUFFIX, \
    CCPN_PLOTS_DIRECTORY

from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import NmrProject as ApiNmrProject
from ccpnmodel.ccpncore.memops import Notifiers
from ccpnmodel.ccpncore.memops.ApiError import ApiError
from ccpnmodel.ccpncore.lib.spectrum import NmrExpPrototype
from ccpnmodel.ccpncore.api.ccp.nmr.NmrExpPrototype import RefExperiment
from ccpnmodel.ccpncore.lib.Io import Fasta as fastaIo


# TODO These should be merged with the same constants in CcpnNefIo
# (and likely those in ExportNefPopup) and moved elsewhere
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
COLLECTIONS = 'collections'

# define the default chemical-shift-list name
DEFAULT_CHEMICALSHIFTLIST = 'default'


class Project(AbstractWrapperObject):
    """ The Project is the root object that contains all data objects and serves as the hub for
    navigating between them. All objects are organised in an hiarchical tree-like manner,
    as children, grandchildren, etc.
    """

    #: Short class name, for PID.
    shortClassName = 'PR'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Project'

    #: Name of plural link to instances of class
    _pluralLinkName = 'projects'

    #: List of child classes.
    _childClasses = []

    # All non-abstractWrapperClasses - filled in by
    _allLinkedWrapperClasses = []

    # Utility map - class shortName and longName to class.
    _className2Class = {}

    # 20211113:ED - added extra for searching the Collection objects as these are immutable
    _classNameLower2Class = {}
    _className2ClassList = []
    _classNameLower2ClassList = []

    # List of CCPN pre-registered api notifiers
    # Format is (wrapperFuncName, parameterDict, apiClassName, apiFuncName)
    #
    # The function self.wrapperFuncName(**parameterDict) will be registered in the CCPN api notifier system
    # api notifiers are set automatically, and are cleared by self._clearAllApiNotifiers and by self.delete()
    #
    # RESTRICTED. Direct access in core classes ONLY
    _apiNotifiers = []

    # Actions you can notify
    _notifierActions = ('create', 'delete', 'rename', 'change')

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiNmrProject._metaclass.qualifiedName()

    # Needs to know this for restoring the GuiSpectrum Module. Could be removed after decoupling Gui and Data!
    _isNew = None

    #TODO: do we still have this limitation?
    _MAX_PROJECT_NAME_LENGTH = 32
    _READONLY = 'readOnly'

    #-----------------------------------------------------------------------------------------
    # Property Attributes of the data structure
    #-----------------------------------------------------------------------------------------

    @property
    def _parent(self) -> (AbstractWrapperObject, None):
        """Parent (containing) object. None for Project, as it is the root of the tree
        """
        return None

    @property
    def chemicalShifts(self) -> list:
        """:return: list of chemicalShifts in the project
        """
        _shifts = []
        for shiftList in self.chemicalShiftLists:
            _shifts.extend(shiftList.chemicalShifts)
        return _shifts

    @property
    def collections(self) -> list:
        """:return: list of collections in the project
        """
        return self._collectionList.collections

    @property
    def _collectionData(self):
        return self._wrappedData.collectionData

    @_collectionData.setter
    def _collectionData(self, value):
        self._wrappedData.collectionData = value

    def getBonds(self, bondType: typing.Optional[str] = None):
        """Get the bonds of a specific bondType.
        """
        return tuple(bnd for bnd in self.bonds if bnd.bondType == bondType)

    @property
    def _chemCompsData(self):
        """
        _internal. ChemComps/molecules to be handled in Resources
        Return a Pandas DataFrame with the loaded ChemComps definitions.
        Columns:  'molType', 'ccpCode', 'code3Letter', 'code1Letter', 'obj'.
        """
        from ccpn.core.lib.ChainLib import CODE3LETTER, CODE1LETTER, CCPCODE, MOLTYPE, ISSTANDARD, OBJ

        df = pd.DataFrame()
        attrs = [MOLTYPE, ISSTANDARD, CODE1LETTER, CODE3LETTER, CCPCODE]
        for i, chemComp in enumerate(self._wrappedData.root.chemComps):
            for attr in attrs:
                df.loc[i, attr] = getattr(chemComp, attr, None)
            isStandard = chemComp.stdChemComp == chemComp
            df.loc[i, ISSTANDARD] = isStandard
            df.loc[i, OBJ] = chemComp

        return df

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    # @property
    # def _oldChemicalShifts(self) -> list['_oldChemicalShift']:
    #     """STUB: hot-fixed later
    #     :return: a list of _oldChemicalShifts in the Project
    #     """
    #     return []
    #
    # @property
    # def _peakClusters(self) -> list['_peakCluster']:
    #     """STUB: hot-fixed later
    #     :return: a list of _peakClusters in the Project
    #     """
    #     return []

    @property
    def atoms(self) -> list['Atom']:
        """STUB: hot-fixed later
        :return: a list of atoms in the Project
        """
        return []

    @property
    def axes(self) -> list['Axis']:
        """STUB: hot-fixed later
        :return: a list of axes in the Project
        """
        return []

    @property
    def bonds(self) -> list['Bond']:
        """STUB: hot-fixed later
        :return: a list of bonds in the Project
        """
        return []

    @property
    def calculationSteps(self) -> list['CalculationStep']:
        """STUB: hot-fixed later
        :return: a list of calculationSteps in the Project
        """
        return []

    @property
    def chains(self) -> list['Chain']:
        """STUB: hot-fixed later
        :return: a list of chains in the Project
        """
        return []

    @property
    def chemicalShiftLists(self) -> list['ChemicalShiftList']:
        """STUB: hot-fixed later
        :return: a list of chemicalShiftLists in the Project
        """
        return []

    @property
    def complexes(self) -> list['Complex']:
        """STUB: hot-fixed later
        :return: a list of complexes in the Project
        """
        return []

    @property
    def data(self) -> list['Data']:
        """STUB: hot-fixed later
        :return: a list of data in the Project
        """
        return []

    @property
    def dataTables(self) -> list['DataTable']:
        """STUB: hot-fixed later
        :return: a list of dataTables in the Project
        """
        return []

    @property
    def integralListViews(self) -> list['IntegralListView']:
        """STUB: hot-fixed later
        :return: a list of integralListViews in the Project
        """
        return []

    @property
    def integralLists(self) -> list['IntegralList']:
        """STUB: hot-fixed later
        :return: a list of integralLists in the Project
        """
        return []

    @property
    def integralViews(self) -> list['IntegralView']:
        """STUB: hot-fixed later
        :return: a list of integralViews in the Project
        """
        return []

    @property
    def integrals(self) -> list['Integral']:
        """STUB: hot-fixed later
        :return: a list of integrals in the Project
        """
        return []

    @property
    def marks(self) -> list['Mark']:
        """STUB: hot-fixed later
        :return: a list of marks in the Project
        """
        return []

    @property
    def models(self) -> list['Model']:
        """STUB: hot-fixed later
        :return: a list of models in the Project
        """
        return []

    @property
    def multipletListViews(self) -> list['MultipletListView']:
        """STUB: hot-fixed later
        :return: a list of multipletListViews in the Project
        """
        return []

    @property
    def multipletLists(self) -> list['MultipletList']:
        """STUB: hot-fixed later
        :return: a list of multipletLists in the Project
        """
        return []

    @property
    def multipletViews(self) -> list['MultipletView']:
        """STUB: hot-fixed later
        :return: a list of multipletViews in the Project
        """
        return []

    @property
    def multiplets(self) -> list['Multiplet']:
        """STUB: hot-fixed later
        :return: a list of multiplets in the Project
        """
        return []

    @property
    def nmrAtoms(self) -> list['NmrAtom']:
        """STUB: hot-fixed later
        :return: a list of nmrAtoms in the Project
        """
        return []

    @property
    def nmrChains(self) -> list['NmrChain']:
        """STUB: hot-fixed later
        :return: a list of nmrChains in the Project
        """
        return []

    @property
    def nmrResidues(self) -> list['NmrResidue']:
        """STUB: hot-fixed later
        :return: a list of nmrResidues in the Project
        """
        return []

    @property
    def notes(self) -> list['Note']:
        """STUB: hot-fixed later
        :return: a list of notes in the Project
        """
        return []

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peakListViews in the Project
        """
        return []

    @property
    def peakLists(self) -> list['PeakList']:
        """STUB: hot-fixed later
        :return: a list of peakLists in the Project
        """
        return []

    @property
    def peakViews(self) -> list['PeakView']:
        """STUB: hot-fixed later
        :return: a list of peakViews in the Project
        """
        return []

    @property
    def peaks(self) -> list['Peak']:
        """STUB: hot-fixed later
        :return: a list of peaks in the Project
        """
        return []

    @property
    def pseudoDimensions(self) -> list['PseudoDimension']:
        """STUB: hot-fixed later
        :return: a list of pseudoDimensions in the Project
        """
        return []

    @property
    def residues(self) -> list['Residue']:
        """STUB: hot-fixed later
        :return: a list of residues in the Project
        """
        return []

    @property
    def restraintContributions(self) -> list['RestraintContribution']:
        """STUB: hot-fixed later
        :return: a list of restraintContributions in the Project
        """
        return []

    @property
    def restraintTables(self) -> list['RestraintTable']:
        """STUB: hot-fixed later
        :return: a list of restraintTables in the Project
        """
        return []

    @property
    def restraints(self) -> list['Restraint']:
        """STUB: hot-fixed later
        :return: a list of restraints in the Project
        """
        return []

    @property
    def sampleComponents(self) -> list['SampleComponent']:
        """STUB: hot-fixed later
        :return: a list of sampleComponents in the Project
        """
        return []

    @property
    def samples(self) -> list['Sample']:
        """STUB: hot-fixed later
        :return: a list of samples in the Project
        """
        return []

    @property
    def spectra(self) -> list['Spectrum']:
        """STUB: hot-fixed later
        :return: a list of spectra in the Project
        """
        return []

    @property
    def spectrumDisplays(self) -> list['SpectrumDisplay']:
        """STUB: hot-fixed later
        :return: a list of spectrumDisplays in the Project
        """
        return []

    @property
    def spectrumGroups(self) -> list['SpectrumGroup']:
        """STUB: hot-fixed later
        :return: a list of spectrumGroups in the Project
        """
        return []

    @property
    def spectrumHits(self) -> list['SpectrumHit']:
        """STUB: hot-fixed later
        :return: a list of spectrumHits in the Project
        """
        return []

    @property
    def spectrumReferences(self) -> list['SpectrumReference']:
        """STUB: hot-fixed later
        :return: a list of spectrumReferences in the Project
        """
        return []

    @property
    def spectrumViews(self) -> list['SpectrumView']:
        """STUB: hot-fixed later
        :return: a list of spectrumViews in the Project
        """
        return []

    @property
    def strips(self) -> list['Strip']:
        """STUB: hot-fixed later
        :return: a list of strips in the Project
        """
        return []

    @property
    def structureData(self) -> list['StructureData']:
        """STUB: hot-fixed later
        :return: a list of structureData in the Project
        """
        return []

    @property
    def structureEnsembles(self) -> list['StructureEnsemble']:
        """STUB: hot-fixed later
        :return: a list of structureEnsembles in the Project
        """
        return []

    @property
    def substances(self) -> list['Substance']:
        """STUB: hot-fixed later
        :return: a list of substances in the Project
        """
        return []

    @property
    def violationTables(self) -> list['ViolationTable']:
        """STUB: hot-fixed later
        :return: a list of violationTables in the Project
        """
        return []

    @property
    def windows(self) -> list['Window']:
        """STUB: hot-fixed later
        :return: a list of windows in the Project
        """
        return []

    #-----------------------------------------------------------------------------------------
    # Attribute getters of the data structure
    # getter STUBS: hot-fixed later
    #-----------------------------------------------------------------------------------------

    def getAtom(self, relativeId: str) -> 'Atom | None':
        """STUB: hot-fixed later
        :return: an instance of Atom, or None
        """
        return None

    def getAxis(self, relativeId: str) -> 'Axis | None':
        """STUB: hot-fixed later
        :return: an instance of Axis, or None
        """
        return None

    def getBond(self, relativeId: str) -> 'Bond | None':
        """STUB: hot-fixed later
        :return: an instance of Bond, or None
        """
        return None

    def getCalculationStep(self, relativeId: str) -> 'CalculationStep | None':
        """STUB: hot-fixed later
        :return: an instance of CalculationStep, or None
        """
        return None

    def getChain(self, relativeId: str) -> 'Chain | None':
        """STUB: hot-fixed later
        :return: an instance of Chain, or None
        """
        return None

    # replaced below
    # def getChemicalShiftList(self, relativeId: str) -> 'ChemicalShiftList | None':
    #     """STUB: hot-fixed later
    #     :return: an instance of ChemicalShiftList, or None
    #     """
    #     return None

    def getComplex(self, relativeId: str) -> 'Complex | None':
        """STUB: hot-fixed later
        :return: an instance of Complex, or None
        """
        return None

    def getData(self, relativeId: str) -> 'Data | None':
        """STUB: hot-fixed later
        :return: an instance of Data, or None
        """
        return None

    def getDataTable(self, relativeId: str) -> 'DataTable | None':
        """STUB: hot-fixed later
        :return: an instance of DataTable, or None
        """
        return None

    def getIntegral(self, relativeId: str) -> 'Integral | None':
        """STUB: hot-fixed later
        :return: an instance of Integral, or None
        """
        return None

    def getIntegralList(self, relativeId: str) -> 'IntegralList | None':
        """STUB: hot-fixed later
        :return: an instance of IntegralList, or None
        """
        return None

    def getIntegralListView(self, relativeId: str) -> 'IntegralListView | None':
        """STUB: hot-fixed later
        :return: an instance of IntegralListView, or None
        """
        return None

    def getIntegralView(self, relativeId: str) -> 'IntegralView | None':
        """STUB: hot-fixed later
        :return: an instance of IntegralView, or None
        """
        return None

    def getMark(self, relativeId: str) -> 'Mark | None':
        """STUB: hot-fixed later
        :return: an instance of Mark, or None
        """
        return None

    def getModel(self, relativeId: str) -> 'Model | None':
        """STUB: hot-fixed later
        :return: an instance of Model, or None
        """
        return None

    def getMultiplet(self, relativeId: str) -> 'Multiplet | None':
        """STUB: hot-fixed later
        :return: an instance of Multiplet, or None
        """
        return None

    def getMultipletList(self, relativeId: str) -> 'MultipletList | None':
        """STUB: hot-fixed later
        :return: an instance of MultipletList, or None
        """
        return None

    def getMultipletListView(self, relativeId: str) -> 'MultipletListView | None':
        """STUB: hot-fixed later
        :return: an instance of MultipletListView, or None
        """
        return None

    def getMultipletView(self, relativeId: str) -> 'MultipletView | None':
        """STUB: hot-fixed later
        :return: an instance of MultipletView, or None
        """
        return None

    def getNmrAtom(self, relativeId: str) -> 'NmrAtom | None':
        """STUB: hot-fixed later
        :return: an instance of NmrAtom, or None
        """
        return None

    def getNmrChain(self, relativeId: str) -> 'NmrChain | None':
        """STUB: hot-fixed later
        :return: an instance of NmrChain, or None
        """
        return None

    def getNmrResidue(self, relativeId: str) -> 'NmrResidue | None':
        """STUB: hot-fixed later
        :return: an instance of NmrResidue, or None
        """
        return None

    def getNote(self, relativeId: str) -> 'Note | None':
        """STUB: hot-fixed later
        :return: an instance of Note, or None
        """
        return None

    def getPeak(self, relativeId: str) -> 'Peak | None':
        """STUB: hot-fixed later
        :return: an instance of Peak, or None
        """
        return None

    def getPeakList(self, relativeId: str) -> 'PeakList | None':
        """STUB: hot-fixed later
        :return: an instance of PeakList, or None
        """
        return None

    def getPeakListView(self, relativeId: str) -> 'PeakListView | None':
        """STUB: hot-fixed later
        :return: an instance of PeakListView, or None
        """
        return None

    def getPeakView(self, relativeId: str) -> 'PeakView | None':
        """STUB: hot-fixed later
        :return: an instance of PeakView, or None
        """
        return None

    def getPseudoDimension(self, relativeId: str) -> 'PseudoDimension | None':
        """STUB: hot-fixed later
        :return: an instance of PseudoDimension, or None
        """
        return None

    def getResidue(self, relativeId: str) -> 'Residue | None':
        """STUB: hot-fixed later
        :return: an instance of Residue, or None
        """
        return None

    def getRestraint(self, relativeId: str) -> 'Restraint | None':
        """STUB: hot-fixed later
        :return: an instance of Restraint, or None
        """
        return None

    def getRestraintContribution(self, relativeId: str) -> 'RestraintContribution | None':
        """STUB: hot-fixed later
        :return: an instance of RestraintContribution, or None
        """
        return None

    def getRestraintTable(self, relativeId: str) -> 'RestraintTable | None':
        """STUB: hot-fixed later
        :return: an instance of RestraintTable, or None
        """
        return None

    def getSample(self, relativeId: str) -> 'Sample | None':
        """STUB: hot-fixed later
        :return: an instance of Sample, or None
        """
        return None

    def getSampleComponent(self, relativeId: str) -> 'SampleComponent | None':
        """STUB: hot-fixed later
        :return: an instance of SampleComponent, or None
        """
        return None

    def getSpectrum(self, relativeId: str) -> 'Spectrum | None':
        """STUB: hot-fixed later
        :return: an instance of Spectrum, or None
        """
        return None

    def getSpectrumDisplay(self, relativeId: str) -> 'SpectrumDisplay | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumDisplay, or None
        """
        return None

    def getSpectrumGroup(self, relativeId: str) -> 'SpectrumGroup | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumGroup, or None
        """
        return None

    def getSpectrumHit(self, relativeId: str) -> 'SpectrumHit | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumHit, or None
        """
        return None

    def getSpectrumReference(self, relativeId: str) -> 'SpectrumReference | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumReference, or None
        """
        return None

    def getSpectrumView(self, relativeId: str) -> 'SpectrumView | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumView, or None
        """
        return None

    def getStrip(self, relativeId: str) -> 'Strip | None':
        """STUB: hot-fixed later
        :return: an instance of Strip, or None
        """
        return None

    def getStructureData(self, relativeId: str) -> 'StructureData | None':
        """STUB: hot-fixed later
        :return: an instance of StructureData, or None
        """
        return None

    def getStructureEnsemble(self, relativeId: str) -> 'StructureEnsemble | None':
        """STUB: hot-fixed later
        :return: an instance of StructureEnsemble, or None
        """
        return None

    def getSubstance(self, relativeId: str) -> 'Substance | None':
        """STUB: hot-fixed later
        :return: an instance of Substance, or None
        """
        return None

    def getViolationTable(self, relativeId: str) -> 'ViolationTable | None':
        """STUB: hot-fixed later
        :return: an instance of ViolationTable, or None
        """
        return None

    def getWindow(self, relativeId: str) -> 'Window | None':
        """STUB: hot-fixed later
        :return: an instance of Window, or None
        """
        return None

    # kept for clarity
    # def _getOldChemicalShift(self, relativeId: str) -> '_OldChemicalShift | None':
    #     """STUB: hot-fixed later
    #     :return: an instance of _OldChemicalShift, or None
    #     """
    #     return None
    #
    # def _getPeakCluster(self, relativeId: str) -> '_PeakCluster | None':
    #     """STUB: hot-fixed later
    #     :return: an instance of _PeakCluster, or None
    #     """
    #     return None

    #-----------------------------------------------------------------------------------------
    # (Sub-)directories of the project
    #-----------------------------------------------------------------------------------------

    @property
    def projectPath(self) -> Path:
        """
        Convenience, as project.path (currently) does not yield a Path instance
        :return: the absolute path to the project as a Path instance
        """
        return aPath(self.path)

    @property
    def statePath(self) -> Path:
        """
        :return: the absolute path to the state subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_STATE_DIRECTORY

    @property
    def pipelinePath(self) -> Path:
        """
        :return: the absolute path to the state/pipeline subdirectory of
                 the current project as a Path instance
        """
        return self.statePath.fetchDir(Pipeline.className)

    @property
    def dataPath(self) -> Path:
        """
        :return: the absolute path to the data subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_DATA_DIRECTORY

    @property
    def spectraPath(self) -> Path:
        """
        :return: the absolute path to the data subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_SPECTRA_DIRECTORY

    @property
    def pluginDataPath(self) -> Path:
        """
        :return: the absolute path to the data/plugins subdirectory of the
                 current project as a Path instance
        """
        return self.projectPath / CCPN_PLUGINS_DIRECTORY

    @property
    def scriptsPath(self) -> Path:
        """
        :return: the absolute path to the script subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_SCRIPTS_DIRECTORY

    @property
    def plotsPath(self) -> Path:
        """
        :return: the absolute path to the plots subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_PLOTS_DIRECTORY

    @property
    def archivesPath(self) -> Path:
        """
        :return: the absolute path to the archives subdirectory of the current project
                 as a Path instance
        """
        return self.projectPath / CCPN_ARCHIVES_DIRECTORY

    @property
    def backupPath(self):
        """path to directory containing backup Project
        """
        from ccpn.framework.PathsAndUrls import CCPN_BACKUP_SUFFIX, CCPN_DIRECTORY_SUFFIX

        _dir, _base, _suffix = self.projectPath.parent.split3()
        bPath = _dir / _base + CCPN_BACKUP_SUFFIX + CCPN_DIRECTORY_SUFFIX
        return bPath

    #-----------------------------------------------------------------------------------------
    # Implementation methods
    #-----------------------------------------------------------------------------------------

    def __init__(self, xmlLoader) -> Project:
        """ Init for Project object using data from xmlLoader
        NB Project is NOT complete before the _initProject function is run.
        :param path: Path to the project; name is extracted from it
        """
        from ccpn.core.lib.XmlLoader import XmlLoader

        if not isinstance(xmlLoader, XmlLoader):
            raise ValueError(f'Expected XmlLoader instance, got {xmlLoader}')

        if not xmlLoader.path.exists():
            raise FileNotFoundError(f'Path "{xmlLoader.path}" does not exist')

        if xmlLoader.apiNmrProject is None or not isinstance(xmlLoader.apiNmrProject, ApiNmrProject):
            raise RuntimeError('No valid ApiNmrProject defined')

        # Setup object handling dictionaries
        self._data2Obj = {}
        self._pid2Obj = {}

        #==> AbstractWrapper defines:
        # linkage attributes
        #   self._project = self
        #   self._wrappedData = wrappedData
        # Tuple to hold children that explicitly need finalising after atomic operations
        #   self._finaliseChildren = []
        #   self._childActions = []
        AbstractWrapperObject.__init__(self, project=self, wrappedData=xmlLoader.apiNmrProject)

        self._path = xmlLoader.path.asString()
        # self._checkProjectSubDirectories()  # only do when saving?

        # self._appBase = None (delt with below)
        # Reference to application; defined by Framework
        self._application = None

        self._name = xmlLoader.name
        self._id = self._name
        self._resetIds()

        # reference to XmlLoader instance;
        self._xmlLoader = xmlLoader

        # Set up notification machinery
        # Active notifiers - saved for later cleanup. CORE APPLICATION ONLY
        self._activeNotifiers = []

        # list or None. When set used to accumulate pending notifiers
        # Optional list. Elements are (func, onceOnly, wrapperObject, optional oldPid)
        self._pendingNotifications = []

        # Notification suspension level - to allow for nested notification suspension
        self._notificationSuspension = 0
        self._progressSuspension = 0

        # Notification blanking level - to allow for nested notification disabling
        self._notificationBlanking = 0

        # api 'change' notification blanking level - to allow for api 'change' call to be
        # disabled in the _modifiedApiObject method.
        # To be used with the apiNotificationBlanking context manager; e.g.
        # with apiNotificationBlanking():
        #   do something
        #
        self._apiNotificationBlanking = 0
        self._apiBlocking = 0

        # Wrapper level notifier tracking.  APPLICATION ONLY
        # {(className,action):OrderedDict(notifier:onceOnly)}
        self._context2Notifiers = {}

        # Special attributes:
        self._implExperimentTypeMap = None

        # reference to a ProjectSaveHistory instance;
        # set by _newProject or _loadProject
        self._saveHistory = None

        # reference to the logger; defined in call to _initialiseProject())
        self._logger = None

        # flag to indicate if the project is temporary, i.e., opened as a default project
        # set by _newProject or _loadProject
        self._isTemporary = False

        # reference to special v3 core lists without abstractWrapperObject
        self._collectionList = None
        self._crossReferencing = None

    #-----------------------------------------------------------------------------------------
    # Attributes
    #-----------------------------------------------------------------------------------------

    @property
    def name(self) -> str:
        """name of Project"""
        return self._name

    @property
    def path(self) -> str:
        """return absolute path to directory containing Project
        """
        return self._path

    @property
    def application(self):
        return self._application

    # GWV: 20181102: insert _appBase to retain consistency with current data loading models
    _appBase = application

    @property
    def isNew(self):
        """Return true if the project is new
        """
        # NOTE:ED - based on original check in _initProject
        return self._wrappedData.root.isModified

    @property
    def isTemporary(self):
        """Return true if the project is temporary, i.e., opened as a default project
        """
        return self._isTemporary

    @property
    def isModified(self):
        """Return true if any part of the project has been modified
        """
        return self._wrappedData.root.isProjectModified()

    @property
    def _isUpgradedFromV2(self):
        """Return True if project was upgraded from V2
        """
        return self._apiNmrProject.root._upgradedFromV2

    @staticmethod
    def _needsUpgrading(path) -> bool:
        """
        Check if project defined by path needs upgrading
        :param path: a ccpn project-path
        :return: True/False
        """
        from ccpn.framework.lib.DataLoaders.CcpNmrV2ProjectDataLoader import CcpNmrV2ProjectDataLoader
        from ccpn.framework.lib.DataLoaders.CcpNmrV3ProjectDataLoader import CcpNmrV3ProjectDataLoader

        # Check for V2 project; always needs upgrading
        if (dataloader := CcpNmrV2ProjectDataLoader.checkForValidFormat(path)) is not None:
            return True

        if (dataloader := CcpNmrV3ProjectDataLoader.checkForValidFormat(path)) is None:
            raise ValueError('Path "%s" does not define a valid ccpn project' % path)

        if (projectHistory := getProjectSaveHistory(dataloader.path)):
            # check whether the history exists
            return projectHistory.lastSavedVersion <= '3.0.4'

        return True

    @property
    def _data(self):
        """Get the contents of the data property from the model
        CCPNInternal only
        """
        return self._wrappedData.data

    @_data.setter
    def _data(self, value):
        """Set the contents of the data property from the model
        CCPNInternal only
        """
        if not isinstance(value, dict):
            raise ValueError('value must be a dict')

        self._wrappedData.data = value

    @property
    def pinnedStrips(self):
        """Return the list of pinned strips.
        """
        return list(filter(lambda st: st.pinned, self.strips))

    #-----------------------------------------------------------------------------------------
    # Various, init, restore
    #-----------------------------------------------------------------------------------------

    def _checkProjectSubDirectories(self):
        """if need be, create all project subdirectories
        """
        if not self.readOnly:
            try:
                for dd in CCPN_SUB_DIRECTORIES:
                    self.projectPath.fetchDir(dd)
            except (PermissionError, FileNotFoundError):
                getLogger().info('Folder may be read-only')

    def _initialiseProject(self):
        """Complete initialisation of project,
        set up logger and notifiers, and wrap underlying data
        This routine is called from Framework, as some other machinery first needs to set up
        (linkages, Current, notifiers and such)
        """

        self._logger = createLogger(self, now=self.application._created)

        # Set up notifiers
        self._registerPresetApiNotifiers()

        # initialise, creating the children; pass in self as we are initialising
        with inactivity(project=self):
            self._restoreChildren()
            # perform any required restoration of project not covered by children
            self._restoreObject(self, self._wrappedData)

            # we always have the default chemicalShift list
            if not self.chemicalShiftLists:
                self.newChemicalShiftList(name=DEFAULT_CHEMICALSHIFTLIST)

            # Call any updates
            self._update()

            # finalise restoration of project
            self._postRestore()

    def _setUnmodified(self):
        """Set the status of API-topobject to unmodified.
        """
        self._xmlLoader.setUnmodified()

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Process data that must always be performed after updating all children
        """
        from ccpn.core._implementation.CollectionList import CollectionList
        from ccpn.core._implementation.CrossReferenceHandler import CrossReferenceHandler

        if project.application.hasGui:
            # strange bug that v2 window is missing and needs replacing
            from ccpn.ui.gui.MainWindow import MainWindow

            if not MainWindow._getAllWrappedData(project):
                # NOTE:ED - need to create a mainWindow
                #   there must be a bug in saving that deletes the v2 ccpnmr.gui.Window.Window object :|
                getLogger().debug('>>> Creating new mainWindow')
                project.newWindow(title='default')

        # create new collection table
        project._collectionList = CollectionList(project=project)

        # create new collections from table
        project._collectionList._restoreObject(project, None)

        # create new collection table
        project._crossReferencing = CrossReferenceHandler(project=project)

        # create new collections from table
        project._crossReferencing._restoreObject(project, None)

        # check that strips have been recovered correctly
        try:
            if project.application.hasGui:
                for sd in project.application.mainWindow.spectrumDisplays:
                    for strp in sd.strips:
                        if not strp.axes:
                            # set the border to red
                            sd.mainWidget.setStyleSheet('Frame { border: 3px solid #FF1234; }')
                            sd.mainWidget.setEnabled(False)
                            strp.setEnabled(False)

                            getLogger().error(
                                    f'Strip {strp} contains bad axes - please close SpectrumDisplay {sd} outlined in red.')

        except Exception as es:
            getLogger().warning(f'There was an issue checking the spectrumDisplays {es}')

        # don't need to call super here
        return project

    def _postRestore(self):
        """Finalise restoration of core objects.
        """
        # Clean any deleted/invalid pids from cross-references and enforce consistency
        self._cleanCrossReferences()

        # Clean any inconsistencies in peak-assignments attached to multiplets
        self._cleanMultipletAssignments()

        super()._postRestore()

    def _cleanCrossReferences(self):
        """Clean any deleted/invalid pids from cross-references and enforce consistency
        """
        # clean the cross-references for spectra-substances
        for sp in self.spectra:
            sp._cleanSpectrumReferences()
        for su in self.substances:
            su._cleanSubstanceReferences()

    def _cleanMultipletAssignments(self):
        """Clean any inconsistencies in peak-assignments attached to multiplets.
        """
        for sp in self.spectra:
            dims = sp.dimensionCount

            for mlts in sp.multipletLists:
                for mlt in mlts.multiplets:

                    consistent = True
                    assigns = [None] * dims
                    for pk in mlt.peaks:
                        pAssigns = pk.dimensionNmrAtoms
                        for ind, val in enumerate(pAssigns):

                            # merge all the assignments per dimension
                            val = set(val)
                            try:
                                if assigns[ind] is None:
                                    assigns[ind] = val
                                elif val != assigns[ind]:
                                    assigns[ind] |= val
                                    consistent = False

                            except Exception as es:
                                getLogger().warning(f'There was a problem cleaning {mlt}:{pk} - {es}')

                    if not consistent:
                        getLogger().warning(f'Merging inconsistent peak-assignments for {mlt}')
                        for pk in mlt.peaks:
                            pk.dimensionNmrAtoms = [list(val) or [] for val in assigns]

        for pk in self.peaks:
            if len(pk.multiplets) > 1:
                getLogger().warning(f'Peak {pk} is contained in several multiplets, only one allowed: {pk.multiplets}')

    #-----------------------------------------------------------------------------------------
    # Save, SaveAs, Close
    #-----------------------------------------------------------------------------------------

    def _close(self):
        self.close()

    def _closeApiObjects(self):
        """Close and purge all api-objects
        WARNING: project is irrecoverable after this
        """
        from ccpn.core.lib.ContextManagers import undoStackBlocking, notificationEchoBlocking, apiNotificationBlanking
        from ccpn.core.lib.ContextManagers import progressHandler

        with self._xmlLoader.blockReading():

            status = self._getAPIObjectsStatus(completeScan=True, onlyInvalids=False, checkValidity=False)

            # reverse hierarchy to get lowest-level first, although not always perfect for cross-links
            df = status.data.sort_values('hierarchy', ascending=False)
            getLogger().debug(f'Purging {len(df)} API-items')
            apiHint = 'None'  # for debug message

            # block everything
            with undoStackBlocking() as _:
                with notificationEchoBlocking():
                    with apiNotificationBlanking():

                        # override unnecessary warnings from root
                        root = self._apiNmrProject.root
                        root.override = True

                        with progressHandler(title='busy', maximum=len(df) + 1,
                                             text='Cleaning-up Project',
                                             hideCancelButton=True) as progress:

                            retries = []
                            for cc, (ii, ob) in enumerate(df.iterrows()):
                                # don't need to check cancelled
                                # if 'close' clicked, will pop up again
                                progress.setValue(cc)

                                try:
                                    # errors only come from delete
                                    apiObj = ob['object']

                                    # override API to delete without checking state and notifiers :|
                                    apiObj.__dict__['isLoaded'] = True
                                    apiObj.__dict__['inConstructor'] = True
                                    if not apiObj.isDeleted:
                                        # hierarchy may still delete bottom-level items
                                        apiObj.delete()

                                except Exception:
                                    # there might still be an issue with the removal order
                                    retries.append(apiObj)

                            # perform a second pass to catch all the lowest-level items
                            for apiObj in retries:
                                try:
                                    apiHint = str(apiObj)
                                    # ignore deleted again
                                    if not apiObj.isDeleted:
                                        apiObj.delete()

                                except AttributeError:
                                    # errors shouldn't be an issue here, just NoneType, don't need to log
                                    pass

                                except Exception as es:
                                    # only log anything weird
                                    getLogger().debug2(f'issue purging {apiHint}  -->  {es}')

        getLogger().debug('Done purge')

    def close(self):
        """Clean up the wrapper project previous to deleting or replacing
        Cleanup includes wrapped data graphics objects (e.g. Window, Strip, ...)
        """
        # only update the logger if there have been changes to the project
        self._updateLoggerState(readOnly=self.readOnly or not self.isModified)

        getLogger().info(f"Closing {self.path}")

        # close any spectra
        for sp in self.spectra:
            sp._close()

        # purge all ap-Objects
        self._closeApiObjects()

        # Remove undo stack:
        self._resetUndo(maxWaypoints=0)

        Logging._clearLogHandlers()
        self._clearAllApiNotifiers()
        self.deleteAllNotifiers()
        # clear the lookup dicts
        self._data2Obj.clear()
        self._pid2Obj.clear()
        # self.__dict__.clear()  # GWV: dangerous; why done?

    def saveAs(self, newPath: str, overwrite: bool = False):
        """Save project to newPath (optionally overwrite);
           Derive the new project name from newPath
           :param newPath: new path for storing project files
           :param overwrite: flag to overwrite if path exists
        """
        from ccpn.core.lib.XmlLoader import XmlLoader

        _newPath = aPath(newPath).assureSuffix(CCPN_DIRECTORY_SUFFIX)
        if _newPath.exists() and overwrite:
            parent = _newPath.parent
            _newPath.removeDir()
            parent.fetchDir(_newPath)

        # redirect only if _newXmlLoader is successful?
        for sp in self.spectra:
            # check if any spectra are referenced as ALONGSIDE and update to the new path
            if sp._isAlongside and sp.hasValidPath() and aPath(self.path).parent != _newPath.parent:
                getLogger().debug(f'Redirecting spectrum {aPath(self.path).parent} -> {_newPath.parent}')
                sp._makeAbsolutePath()

        _newXmlLoader = XmlLoader.newFromLoader(self._xmlLoader, path=_newPath, create=True)
        self._xmlLoader = _newXmlLoader
        self._path = _newXmlLoader.path.asString()
        self._name = _newXmlLoader.name
        self._checkProjectSubDirectories()
        self._saveHistory = newProjectSaveHistory(self.path)
        self.save(comment='saveAs')

        # check for application and Gui;
        if self.application and self.application.hasGui:
            self.application.mainWindow.sideBar.setProjectName(self)

    def save(self, comment='regular save', autoBackup: bool = False):
        """Save project; add optional comment to save records
        """
        if self.readOnly:
            getLogger().warning('save skipped: Project is read-only')
            return

        # stop the auto-backups so they don't clash with current save
        with self.application.pauseAutoBackups():

            # Update the spectrum internal settings
            for spectrum in self.spectra:
                spectrum._saveObject()

            try:
                with self._xmlLoader.blockReading():
                    # only need to check what is already there
                    apiStatus = self._getAPIObjectsStatus()
                if apiStatus.invalidObjects:
                    # if deleteInvalidObjects:
                    # delete here ...
                    # run save and apiStatus again. Ensure nothing else has been compromised on the deleting process
                    # else:
                    errorMsg = '\n '.join(apiStatus.invalidObjectsErrors)
                    getLogger().critical(
                            f'Found compromised items. Project might be left in an invalid state. {errorMsg}')
                    raise RuntimeError(errorMsg)

            except Exception as es:
                getLogger().warning(f'Error checking project status: {str(es)}')

            if autoBackup:
                # should be redundant now
                self._xmlLoader.backupUserData(updateIsModified=False)
            else:
                self._xmlLoader.saveUserData(keepFallBack=True)

            self._checkProjectSubDirectories()
            self._saveHistory.addSaveRecord(comment=f'{self.name}: {comment}')
            self._saveHistory.save()
            self._updateLoggerState(readOnly=self.readOnly, flush=True)

            self._isTemporary = False
            self._isNew = False

    def _autoBackup(self):
        """Auto-backup project
        """
        if self.readOnly:
            getLogger().warning('Backup skipped: project is read-only')
            return

        if not self.isModified:
            getLogger().debug('Project is not modified: ignoring backup')
            return

        # # stop the auto-backups, so they don't clash with current save
        # with self.application.pauseAutoBackups():
        # NOTE:ED - this is called inside auto-backup so shouldn't need pausing

        try:
            apiStatus = self._getAPIObjectsStatus()
            if apiStatus.invalidObjects:
                # if deleteInvalidObjects:
                # delete here ...
                # run save and apiStatus again. Ensure nothing else has been compromised on the deleting process
                # else:
                errorMsg = '\n '.join(apiStatus.invalidObjectsErrors)
                getLogger().critical(
                        f'Backup found compromised items. Project might be left in an invalid state. {errorMsg}')
                raise RuntimeError(errorMsg)

        except Exception as es:
            getLogger().warning(f'Error checking project status: {str(es)}')

        self._xmlLoader.backupUserData(updateIsModified=False)
        # there was a valid save
        return True

        # don't touch anything else for the minute

    #-----------------------------------------------------------------------------------------
    # CCPN properties
    #-----------------------------------------------------------------------------------------

    @property
    def _apiNmrProject(self) -> ApiNmrProject:
        """API equivalent to object: NmrProject"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """Project id: Globally unique identifier (guid)"""
        return self._wrappedData.guid.translate(Pid.remapSeparators)

    # _uniqueId: Some classes require a unique identifier per class
    # use _uniqueId property defined in AbstractWrapperObject; values are maintained for project instance
    def _queryNextUniqueIdValue(self, className) -> int:
        """query the next uniqueId for class className; does not increment its value
        CCPNINTERNAL: used in NmrAtom on _uniqueName
        """
        # _nextUniqueIdValues = {}    # a (className, nexIdValue) dictionary
        if not hasattr(self._wrappedData, '_nextUniqueIdValues'):
            setattr(self._wrappedData, '_nextUniqueIdValues', {})
        if self._wrappedData._nextUniqueIdValues is None:
            self._wrappedData._nextUniqueIdValues = {}

        nextUniqueId = self._wrappedData._nextUniqueIdValues.setdefault(className, 0)
        return nextUniqueId

    def _getNextUniqueIdValue(self, className) -> int:
        """Get the next uniqueId for class className; increments its value
        CCPNINTERNAL: used in AbstractWrapper on __init__
        """
        nextUniqueId = self._queryNextUniqueIdValue(className)
        self._wrappedData._nextUniqueIdValues[className] += 1
        return nextUniqueId

    def _setNextUniqueIdValue(self, className, value):
        """Set the next uniqueId for class className
        CCPNINTERNAL: should only be used in _restoreObject or Nef
        """
        self._queryNextUniqueIdValue(className)
        self._wrappedData._nextUniqueIdValues[className] = int(value)

    @logCommand('project.')
    def deleteObjects(self, *objs: typing.Sequence[typing.Union[str, Pid.Pid, AbstractWrapperObject]]):
        """Delete one or more objects, given as either objects or Pids
        """
        getByPid = self.getByPid
        objs = [getByPid(x) if isinstance(x, str) else x for x in objs]

        with undoBlockWithoutSideBar():
            for obj in objs:
                if obj and not obj.isDeleted:
                    obj.delete()

    @property
    def readOnly(self):
        """Return the read-only state of the project.
        """
        # _saveOverride allows the readOnly state to be temporarily set to False during save/saveAs
        # _readOnly sets all projects as read-only from the command-line switch --read-only
        return ((self._getInternalParameter(self._READONLY) or False) or self.application._applicationReadOnlyMode) and \
            not self.application._saveOverride

    @logCommand('project.')
    @ccpNmrV3CoreUndoBlock(readOnlyChanged=True)
    def setReadOnly(self, value):
        """Set the read-only state of the project.
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setReadOnly must be a bool')

        self._setInternalParameter(self._READONLY, value)
        self._updateReadOnlyState()
        self._updateLoggerState(flush=not value)

        # # NOTE:ED - does this need to include override?
        # self._xmlLoader.readOnly = (value and not self.application._saveOverride)
        #
        # updateLogger(self.application.applicationName,
        #              self.projectPath / CCPN_LOGS_DIRECTORY,
        #              level = self.application._debugLevel,
        #              readOnly=value)

    def _updateReadOnlyState(self):
        """Update the state of the xmlLoader from the current read-only state
        CCPN Internal
        """
        # needs to take into account the saveAsOverride state from the application
        self._xmlLoader.setReadOnly(self.readOnly)

    def _updateLoggerState(self, readOnly=True, flush=False):
        """Update the read-only state of the logger
        CCPN Internal
        """
        updateLogger(self.application.applicationName,
                     self.projectPath / CCPN_LOGS_DIRECTORY,
                     level=self.application._debugLevel,
                     readOnly=readOnly,
                     flush=flush,
                     now=self.application._created
                     )

    #-----------------------------------------------------------------------------------------
    # Undo machinery
    #-----------------------------------------------------------------------------------------

    @property
    def _undo(self):
        """undo stack for Project. Implementation attribute"""

        try:
            result = self._wrappedData.root._undo
        except Exception:
            result = None

        return result

    def _resetUndo(self, maxWaypoints: int = Undo.MAXUNDOWAYPOINTS,
                   maxOperations: int = Undo.MAXUNDOOPERATIONS,
                   debug: bool = False, application=None):
        """Reset undo stack, using passed-in parameters.
        NB setting either parameter to 0 removes the undo stack."""
        Undo.resetUndo(self._wrappedData.root, maxWaypoints=maxWaypoints,
                       maxOperations=maxOperations, debug=debug, application=application)

    def newUndoPoint(self):
        """Set a point in the undo stack, you can undo/redo to """
        undo = self._wrappedData.root._undo
        if undo is None:
            self._logger.warning("Trying to add undoPoint but undo is not initialised")
        else:
            undo.newWaypoint()  # DO NOT CHANGE THIS ONE newWaypoint
            self._logger.debug("Added undoPoint")

    def blockWaypoints(self):
        """Block the setting of undo waypoints,
        so that command echoing (_startCommandBLock) does not set waypoints

        NB The programmer must GUARANTEE (try: ... finally) that waypoints are unblocked again"""
        undo = self._wrappedData.root._undo
        if undo is None:
            self._logger.warning("Trying to block waypoints but undo is not initialised")
        else:
            undo.increaseWaypointBlocking()
            self._logger.debug("Waypoint setting blocked")

    def unblockWaypoints(self):
        """Block the setting of undo waypoints,
        so that command echoing (_startCommandBLock) does not set waypoints

        NB The programmer must GUARANTEE (try: ... finally) that waypoints are unblocked again"""
        undo = self._wrappedData.root._undo
        if undo is None:
            self._logger.warning("Trying to unblock waypoints but undo is not initialised")
        else:
            undo.decreaseWaypointBlocking()
            self._logger.debug("Waypoint setting unblocked")

    @property
    def waypointBlocking(self):
        """Return True if the undo-stack is blocked
        """
        return self._undo.waypointBlocking

    #-----------------------------------------------------------------------------------------

    @property
    def _experimentTypeMap(self) -> OrderedDict:
        """{dimensionCount : {sortedNucleusCodeTuple :
                              OrderedDict(experimentTypeSynonym : experimentTypeName)}}
        dictionary

        NB The OrderedDicts are ordered ad-hoc, with the most common experiments (hopefully) first
        """

        # NB This is a hack, in order to rename experiments that we care particularly about
        # This should disappear under refactoring
        from ccpnmodel.ccpncore.lib.spectrum.NmrExpPrototype import priorityNameRemapping

        # NBNB TODO FIXME fetchIsotopeRefExperimentMap should be merged with
        # getExpClassificationDict output - we should NOT have two parallel dictionaries

        result = self._implExperimentTypeMap
        if result is None:
            result = OrderedDict()
            refExperimentMap = NmrExpPrototype.fetchIsotopeRefExperimentMap(self._apiNmrProject.root)

            for nucleusCodes, refExperiments in refExperimentMap.items():

                ndim = len(nucleusCodes)
                dd1 = result.get(ndim, {})
                result[ndim] = dd1

                dd2 = dd1.get(nucleusCodes, OrderedDict())
                dd1[nucleusCodes] = dd2
                for refExperiment in refExperiments:
                    name = refExperiment.name
                    key = refExperiment.synonym or name
                    key = priorityNameRemapping.get(key, key)
                    dd2[key] = name

            self._implExperimentTypeMap = result
        #
        return result

    def _getReferenceExperimentFromType(self, value) -> Optional[RefExperiment]:
        """Search for a reference experiment matching name
        """
        if value is None:
            return

        # nmrExpPrototype = self._wrappedData.root.findFirstNmrExpPrototype(name=value) # Why not findFirst instead of looping all sortedNmrExpPrototypes
        for nmrExpPrototype in self._wrappedData.root.sortedNmrExpPrototypes():
            for refExperiment in nmrExpPrototype.sortedRefExperiments():
                if refExperiment.name == value:
                    return refExperiment

    @property
    def shiftAveraging(self):
        """Return shiftAveraging
        """
        return self._wrappedData.shiftAveraging

    @shiftAveraging.setter
    def shiftAveraging(self, value):
        """Set shiftAveraging
        """
        if not isinstance(value, bool):
            raise TypeError('shiftAveraging must be True/False')

        self._wrappedData.shiftAveraging = value

    #===========================================================================================
    #  Notifiers system
    #
    # Old, API-level functions:
    #
    #===========================================================================================

    @classmethod
    def _setupApiNotifier(cls, func, apiClassOrName, apiFuncName, parameterDict=None):
        """Setting up API notifiers for subsequent registration on each new project
           RESTRICTED. Use in core classes ONLY"""
        tt = cls._apiNotifierParameters(func, apiClassOrName, apiFuncName,
                                        parameterDict=parameterDict)
        cls._apiNotifiers.append(tt)

    @classmethod
    def _apiNotifierParameters(cls, func, apiClassOrName, apiFuncName, parameterDict=None):
        """Define func as method of project and return API parameters for notifier setup
        APPLICATION ONLY"""
        if parameterDict is None:
            parameterDict = {}

        apiClassName = (apiClassOrName if isinstance(apiClassOrName, str)
                        else apiClassOrName._metaclass.qualifiedName())

        dot = '_dot_'
        wrapperFuncName = '_%s%s%s' % (func.__module__.replace('.', dot), dot, func.__name__)
        setattr(Project, wrapperFuncName, func)

        return (wrapperFuncName, parameterDict, apiClassName, apiFuncName)

    def _registerApiNotifier(self, func, apiClassOrName, apiFuncName, parameterDict=None):
        """Register notifier for immediate action on current project (only)

        func must be a function taking two parameters: the ccpn.core.Project and an Api object
        matching apiClassOrName.

        'apiFuncName' is either the name of an API modifier function (a setter, adder, remover),
        in which case the notifier is triggered by this function
        Or it is one of the following tags:
        ('', '__init__', 'postInit', 'preDelete', 'delete', 'startDeleteBlock', 'endDeleteBlock').
        '' registers the notifier to any modifier function call ( setter, adder, remover),
        __init__ and postInit triggers the notifier at the end of object creation, before resp.
        after execution of postConstructorCode, the four delete-related tags
        trigger notifiers at four different points in the deletion process
        (see memops.Implementation.DataObject.delete() code for details).


        ADVANCED, but free to use. Must be unregistered when any object referenced is deleted.
        Use return value as input parameter for _unregisterApiNotifier (if desired)"""
        tt = self.__class__._apiNotifierParameters(func, apiClassOrName, apiFuncName,
                                                   parameterDict=parameterDict)
        return self._activateApiNotifier(*tt)

    def _unregisterApiNotifier(self, notifierTuple):
        """Remove acxtive notifier from project. ADVANVED but free to use.
        Use return value of _registerApiNotifier to identify the relevant notiifier"""
        self._activeNotifiers.remove(notifierTuple)
        Notifiers.unregisterNotify(*notifierTuple)

    def _registerPresetApiNotifiers(self):
        """Register preset API notifiers. APPLCATION ONLY"""

        for tt in self._apiNotifiers:
            self._activateApiNotifier(*tt)

    def _activateApiNotifier(self, wrapperFuncName, parameterDict, apiClassName, apiFuncName):
        """Activate API notifier. APPLICATION ONLY"""

        notify = functools.partial(getattr(self, wrapperFuncName), **parameterDict)
        notifierTuple = (notify, apiClassName, apiFuncName)
        self._activeNotifiers.append(notifierTuple)
        Notifiers.registerNotify(*notifierTuple)
        #
        return notifierTuple

    def _clearAllApiNotifiers(self):
        """CLear all notifiers, previous to closing or deleting Project
        APPLICATION ONLY
        """
        while self._activeNotifiers:
            tt = self._activeNotifiers.pop()
            Notifiers.unregisterNotify(*tt)

    #===========================================================================================
    #  Notifiers system
    #
    # New notifier system (Free for use in application code):
    #
    #===========================================================================================

    def registerNotifier(self, className: str, target: str, func: typing.Callable[..., None],
                         parameterDict: dict = {}, onceOnly: bool = False) -> typing.Callable[..., None]:
        """
        Register notifiers to be triggered when data change

        :param str className: className of wrapper class to monitor (AbstractWrapperObject for 'all')

        :param str target: can have the following values

          *'create'* is called after the creation (or undeletion) of the object and its wrapper.
          Notifier functions are called with the created V3 core object as the only parameter.

          *'delete'* is called before the object is deleted
          Notifier functions are called with the deleted to be deleted V3 core object as the only
          parameter.

          *'rename'* is called after the id and pid of an object has changed
          Notifier functions are called with the renamed V3 core object and the old pid as parameters.

          *'change'* when any object attribute changes value.
          Notifier functions are called with the changed V3 core object as the only parameter.
          rename and crosslink notifiers (see below) may also trigger change notifiers.

          Any other value is interpreted as the name of a V3 core class, and the notifier
          is triggered when a cross link (NOT a parent-child link) between the className and
          the target class is modified

        :param Callable func: The function to call when the notifier is triggered.

          for actions 'create', 'delete' and 'change' the function is called with the object
          created (deleted, undeleted, changed) as the only parameter

          For action 'rename' the function is called with an additional parameter: oldPid,
          the value of the pid before renaming.

          If target is a second className, the function is called with the project as the only
          parameter.

        :param dict parameterDict: Parameters passed to the notifier function before execution.

          This allows you to use the same function with different parameters in different contexts

        :param bool onceOnly: If True, only one of multiple copies is executed

          when notifiers are resumed after a suspension.

        :return The registered notifier (which can be passed to removeNotifier or duplicateNotifier)

        """

        if target in self._notifierActions:
            tt = (className, target)
        else:
            # This is right, it just looks strange. But if target is not an action it is
            # another className, and if so the names must be sorted.
            tt = tuple(sorted([className, target]))

        od = self._context2Notifiers.setdefault(tt, OrderedDict())
        if parameterDict:
            notifier = functools.partial(func, **parameterDict)
        else:
            notifier = func
        if od.get(notifier) is None:
            od[notifier] = onceOnly
        else:
            raise TypeError("Coding error - notifier %s set twice for %s,%s "
                            % (notifier, className, target))
        #
        return notifier

    def unRegisterNotifier(self, className: str, target: str, notifier: typing.Callable[..., None]):
        """Unregister the notifier from this className, and target"""
        if target in self._notifierActions:
            tt = (className, target)
        else:
            # This is right, it just looks strange. But if target is not an action it is
            # another className, and if so the names must be sorted.
            tt = tuple(sorted([className, target]))
        try:
            if hasattr(self, '_context2Notifiers'):
                od = self._context2Notifiers.get((tt), {})
                del od[notifier]
        except KeyError:
            self._logger.warning("Attempt to unregister unknown notifier %s for %s" % (notifier, (className, target)))

    def removeNotifier(self, notifier: typing.Callable[..., None]):
        """Unregister the notifier from all places where it appears."""
        found = False
        for od in self._context2Notifiers.values():
            if notifier in od:
                del od[notifier]
                found = True
        if not found:
            self._logger.warning("Attempt to remove unknown notifier: %s" % notifier)

    def blankNotification(self):
        """Disable notifiers temporarily
        e.g. to disable 'object modified' notifiers during object creation

        Caller is responsible to make sure necessary notifiers are called, and to unblank after use"""
        self._notificationBlanking += 1

    def unblankNotification(self):
        """Resume notifier execution after blanking"""
        self._notificationBlanking -= 1
        if self._notificationBlanking < 0:
            raise TypeError("Code Error: _notificationBlanking below zero!")

    def suspendNotification(self):
        """Suspend notifier execution and accumulate notifiers for later execution"""
        if self.application.hasGui:
            self.application.ui.qtApp.progressAboutToChangeSignal.emit(self._progressSuspension)
        self._progressSuspension += 1

        return
        # # TODO suspension temporarily disabled
        # self._notificationSuspension += 1

    def resumeNotification(self):
        """Execute accumulated notifiers and resume immediate notifier execution"""
        self._progressSuspension -= 1
        if self._progressSuspension < 0:
            raise RuntimeError("Code Error: _progressSuspension below zero")
        if self.application.hasGui:
            self.application.ui.qtApp.progressChangedSignal.emit(self._progressSuspension)

        return

        # TODO suspension temporarily disabled
        # This was broken at one point, and we never found time to fix it
        # It is a time-saving measure, allowing you to e.g. execute a
        # peak-created notifier only once when creating hundreds of peaks in one operation

        # if self._notificationSuspension > 1:
        #     self._notificationSuspension -= 1
        # else:
        #     # Should not be necessary, but in this way we never get below 0 no matter what errors happen
        #     self._notificationSuspension = 0
        #
        #     scheduledNotifiers = set()
        #
        #     executeNotifications = []
        #     pendingNotifications = self._pendingNotifications
        #     while pendingNotifications:
        #         notification = pendingNotifications.pop()
        #         notifier = notification[0]
        #         onceOnly = notification[1]
        #         if onceOnly:
        #
        #             # check whether the match pair, (function, object) is in the found set
        #             matchNotifier = (notifier, notification[2])
        #             if matchNotifier not in scheduledNotifiers:
        #                 scheduledNotifiers.add(matchNotifier)
        #
        #                 # append the function call (function, object, *params)
        #                 executeNotifications.append((notifier, notification[2:]))
        #
        #             # if notifier not in scheduledNotifiers:
        #             #     scheduledNotifiers.add(notifier)
        #             #     executeNotifications.append((notifier, notification[2:]))
        #         else:
        #             executeNotifications.append((notifier, notification[2:]))
        #     #
        #     for notifier, params in reversed(executeNotifications):
        #         notifier(*params)

    # Standard notified functions.
    # RESTRICTED. Use in core classes ONLY

    def _startDeleteCommandBlock(self, *allWrappedData):
        """Call startCommandBlock for wrapper object delete. Implementation only

        If commented: _activateApiNotifier fails

        Used by the preset Api notifiers populated for self._apiNotifiers;
        have _newApiObject, _startDeleteCommandBlock, _finaliseApiDelete, _endDeleteCommandBlock, _finaliseApiUnDelete
        and _modifiedApiObject for each V3 class
        Initialised from _linkWrapperObjects in AbstractWrapperObject.py:954
        """

        undo = self._undo
        if undo is not None:
            # set undo step
            undo.newWaypoint()  # DO NOT CHANGE THIS
            undo.increaseWaypointBlocking()

            # self.suspendNotification()

    def _endDeleteCommandBlock(self, *dummyWrappedData):
        """End block for delete command echoing

        MUST be paired with _startDeleteCommandBlock call - use try ... finally to ensure both are called
        """
        undo = self._undo
        if undo is not None:
            # self.resumeNotification()
            undo.decreaseWaypointBlocking()

    def _newApiObject(self, wrappedData, cls: AbstractWrapperObject):
        """Create new wrapper object of class cls, associated with wrappedData.
        and call creation notifiers.
        This method is called from the api upon creation of a corresponding api object
        """
        if self._apiBlocking != 0:
            getLogger().debug(f'{consoleStyle.fg.red}blocking _newApiObject {self} {wrappedData} {cls}{consoleStyle.reset}')
            return

        # See AbstractWrapperObject:1145
        # factoryFunction = cls._factoryFunction
        # if factoryFunction is None:
        #     result = cls(self, wrappedData)
        # else:
        #     # Necessary for classes where you need to instantiate a subclass instead
        #
        #     result = self._data2Obj.get(wrappedData)
        #     # There are cases where _newApiObject is registered twice,
        #     # when two wrapper classes share the same API class
        #     # (Peak,Integral; PeakList, IntegralList)
        #     # In those cases only the notifiers are done the second time
        #     if result is None:
        #         result = factoryFunction(self, wrappedData)
        #
        if (result := self._data2Obj.get(wrappedData)) is not None:
            raise RuntimeError(
                    f'Project._newApiObject: {result} already exists; Cannot create again and this should not happen!')
        if not cls._ignoreNewApiObjectCallback:
            result = cls._newInstanceFromApiData(project=self, apiObj=wrappedData)

        # GWV: duplicate; done by newObject decorator
        # result._finaliseAction('create')

    def _modifiedApiObject(self, wrappedData):
        """ call object-has-changed notifiers
        """
        if self._apiNotificationBlanking != 0 or self._apiBlocking != 0:
            return
        if not (obj := self._data2Obj.get(wrappedData)):
            # NOTE:GWV - it shouldn't get here but occasionally it does; e.g. when
            # upgrading a V2 project with correctFinalResult() routine
            getLogger().debug(f'_modifiedApiObject: no V3 object for {wrappedData}')
        else:
            obj._finaliseAction('change')

    def _finaliseApiDelete(self, wrappedData):
        """Clean up after object deletion
        """
        if self._apiBlocking != 0:
            return
        if not wrappedData.isDeleted:
            raise ValueError(f"_finaliseApiDelete called before wrapped data are deleted: {wrappedData}")
        # get object
        if not (obj := self._data2Obj.get(wrappedData)):
            # NOTE:ED - it shouldn't get here but occasionally it does :| correctFinalResult() routine?
            getLogger().debug(f'_finaliseApiDelete: no V3 object for {wrappedData}')
        else:
            # obj._finaliseAction('delete')  # GWV: 20181127: now as notify('delete') decorator on delete method
            # remove from wrapped2Obj
            del self._data2Obj[wrappedData]
            # remove from pid2Obj
            del self._pid2Obj[obj.shortClassName][obj._id]
            # Mark the object as obviously deleted, and set up for un-deletion
            obj._id += '-Deleted'
            wrappedData._oldWrapperObject = obj
            obj._wrappedData = None

    def _finaliseApiUnDelete(self, wrappedData):
        """restore undeleted wrapper object, and call creation notifiers,
        same as _newObject.
        """
        if self._apiBlocking != 0:
            return
        if wrappedData.isDeleted:
            raise ValueError(f"_finaliseApiUnDelete called before wrapped data are deleted: {wrappedData}")
        try:
            oldWrapperObject = wrappedData._oldWrapperObject
        except AttributeError as es:
            raise ApiError("Wrapper object to undelete wrongly set up - lacks _oldWrapperObject attribute") from es

        # put back in from wrapped2Obj
        self._data2Obj[wrappedData] = oldWrapperObject
        if oldWrapperObject._id.endswith('-Deleted'):
            oldWrapperObject._id = oldWrapperObject._id[:-8]
        # put back in pid2Obj
        self._pid2Obj[oldWrapperObject.shortClassName][oldWrapperObject._id] = oldWrapperObject
        # Restore object to pre-un-deletion state
        del wrappedData._oldWrapperObject
        oldWrapperObject._wrappedData = wrappedData

    def _notifyRelatedApiObject(self, wrappedData, pathToObject: str, action: str):
        """ call 'action' type notifiers for getattribute(pathToObject)(wrappedData)
        pathToObject is a navigation path (may contain dots) and must yield an API object
        or an iterable of API objects.
        """
        if self._apiNotificationBlanking != 0 or self._apiBlocking != 0:
            return
        if not (target := operator.attrgetter(pathToObject)(wrappedData)):
            return
        elif hasattr(target, '_metaclass'):
            # Hack. This is an API object - only if exists
            targets = [target]
        else:
            # This must be an iterable
            targets = target
        for apiObj in targets:
            if not apiObj.isDeleted:
                if (obj := self._data2Obj.get(apiObj)) is None:
                    # NOTE:GWV - it shouldn't get here but occasionally it does; e.g. when
                    # upgrading a V2 project with correctFinalResult() routine
                    getLogger().debug(f'_notifyRelatedApiObject: no V3 object for {apiObj}')
                else:
                    obj._finaliseAction(action)

    # def _finaliseApiRename(self, wrappedData):
    #     """Reset Finalise rename - called from API object (for API notifiers)
    #     """
    #     # Should be handled by decorators
    #     if self._apiNotificationBlanking == 0 and self._apiBlocking == 0:
    #         getLogger().debug2(f'***   SHOULD THIS BE CALLED? {self._data2Obj.get(wrappedData)}')
    #         # obj = self._data2Obj.get(wrappedData)
    #         # obj._finaliseAction('rename')

    def _finalisePid2Obj(self, obj, action):
        """New/Delete object to the general dict for v3 pids
        """
        # update pid:object mapping dictionary
        dd = self._pid2Obj.setdefault(obj.className, self._pid2Obj.setdefault(obj.shortClassName, {}))
        # set/delete on action
        if action == 'create':
            dd[obj.id] = obj
        elif action == 'delete':
            # should never fail
            del dd[obj.id]

    def _modifiedLink(self, dummy, classNames: typing.Tuple[str, str]):
        """ call link-has-changed notifiers
        The notifier function called must have the signature
        func(project, **parameterDict)

        NB
        1) calls to this function must be set up explicitly in the wrapper for each crosslink
        2) This function is only called when the link is changed explicitly, not when
        a linked object is created or deleted.
        """
        if self._notificationBlanking:
            return
        # get object
        className, target = tuple(sorted(classNames))
        # self._doNotification(classNames[0], classNames[1], self)
        # NB 'AbstractWrapperObject' not currently in use (Sep 2016), but kept for future needs
        iterator = (self._context2Notifiers.setdefault((name, target), OrderedDict())
                    for name in (className, 'AbstractWrapperObject'))
        for dd in iterator:
            for notifier in dd:
                notifier(self)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Library functions
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _getAPIObjectsStatus(self, completeScan=False, onlyInvalids=True,
                             includeDefaultChildren=False, checkValidity=True):
        """
        Scan all API objects and check their validity.

        Parameters:
        completeScan: bool, True to perform a complete validity check of all found API objects
        includeDefaultChildren: bool, False to exclude default objects for inspection such as
                                ChemComps and associated, nmrExpPrototypes etc.See _APIStatus._excludedChildren
                                for the full list of exclusions.
        checkValidity: bool, default True, check the validity of each API object
                       set to False if only the list is required, note that this overrides completeScan
        Return: the API Status object. See _APIStatus for full description

        """
        getLogger().info('Validating Project integrity...')
        from ccpn.core._implementation.APIStatus import APIStatus

        root = self._apiNmrProject.root
        apiStatus = APIStatus(apiObj=root, onlyInvalids=onlyInvalids, completeScan=completeScan,
                              includeDefaultChildren=includeDefaultChildren, checkValidity=checkValidity)
        return apiStatus

    def _update(self):
        """Call the _updateObject method on all objects, including self
        """
        self._updateObject(UPDATE_POST_PROJECT_INITIALISATION)
        objs = self._getAllDecendants()
        for obj in objs:
            obj._updateObject(UPDATE_POST_PROJECT_INITIALISATION)

    @logCommand('project.')
    def exportNef(self, path: str = None,
                  overwriteExisting: bool = False,
                  skipPrefixes: typing.Sequence[str] = (),
                  expandSelection: bool = True,
                  includeOrphans: bool = False,
                  pidList: typing.Sequence[str] = None):
        """
        Export selected contents of the project to a Nef file.

        skipPrefixes: ( 'ccpn', ..., <str> )
        expandSelection: <bool>
        includeOrphans: <bool>

        Include 'ccpn' in the skipPrefixes list will exclude ccpn specific items from the file
        expandSelection = True      will include all data from the project, this may not be data that
                                    is not defined in the Nef standard.
        includeOrphans = True       will include chemicalShifts that have no peak assignments (orphans)

        PidList is a list of <str>, e.g. 'NC:@-', obtained from the objects to be included.
        The Nef file may also contain further dependent items associated with the pidList.

        :param path: output path and filename
        :param skipPrefixes: items to skip
        :param expandSelection: expand the selection
        :param includeOrphans: include chemicalShift orphans
        :param pidList: a list of pids
        """
        from ccpn.framework.lib.ccpnNef import CcpnNefIo

        with undoBlock():
            with notificationBlanking():
                CcpnNefIo.exportNef(self, path,
                                    overwriteExisting=overwriteExisting,
                                    skipPrefixes=skipPrefixes,
                                    expandSelection=expandSelection,
                                    includeOrphans=includeOrphans,
                                    pidList=pidList)

    @staticmethod
    def isCoreObject(obj) -> bool:
        """Return True if obj is a core ccpn object
        """
        return isinstance(obj, (AbstractWrapperObject, V3CoreObjectABC))

    @staticmethod
    def isCoreClass(klass) -> bool:
        """Return True if type(klass) is a core ccpn object type
        """
        return isinstance(klass, type) and issubclass(klass, (AbstractWrapperObject, V3CoreObjectABC))

    #===========================================================================================
    # Data loaders
    #===========================================================================================

    def loadData(self, path: (str, Path)) -> list:
        """Just a stub for backward compatibility
        """
        return self.application.loadData(path)

    def _loadFastaFile(self, path: (str, Path)) -> list:
        """Load Fasta sequence(s) from file into Wrapper project
        CCPNINTERNAL: called from FastDataLoader
        """
        with logCommandManager('application.', 'loadData', path):
            sequences = fastaIo.parseFastaFile(path)
            chains = []
            for sequence in sequences:
                newChain = self.createChain(sequence=sequence[2],
                                            comment=sequence[1],
                                            compoundName=sequence[0],
                                            molType='protein')
                chains.append(newChain)

        return chains

    def _loadPdbFile(self, path: (str, Path)) -> list:
        """Load data from pdb file path into new StructureEnsemble object(s)
        CCPNINTERNAL: called from pdb dataLoader
        """
        from ccpn.util.StructureData import EnsembleData, averageStructure

        with logCommandManager('application.', 'loadData', path):
            path = aPath(path)
            name = path.basename

            ensemble = EnsembleData.from_pdb(str(path))
            se = self.newStructureEnsemble(name=name, data=ensemble)

            # create a new ensemble-average in a dataTable
            dTable = self.newDataTable(name=f'{name}-average', data=averageStructure(ensemble))
            dTable.setMetadata('structureEnsemble', se.pid)

        return [se]

    def _loadMmcifFile(self, path: (str, Path)) -> list:
        """Load data from mmcif file path into new StructureEnsemble object(s)
        CCPNINTERNAL: called from mmcif dataLoader
        """

        from ccpn.util.StructureData import EnsembleData, averageStructure

        with logCommandManager('application.', 'loadData', path):
            path = aPath(path)
            name = path.basename

            ensemble = EnsembleData.from_mmcif(str(path))
            se = self.newStructureEnsemble(name=name, data=ensemble)

            # create a new ensemble-average in a dataTable
            dTable = self.newDataTable(name=f'{name}-average', data=averageStructure(ensemble))
            dTable.setMetadata('structureEnsemble', se.pid)

            def getLoopNames(filename):
                getLogger().info(filename)
                loopNames = []
                loop_ = False
                with open(filename) as f:
                    for l in f:
                        l = l.strip()
                        if len(l) == 0:
                            continue  # Ignore blank lines
                        if l.startswith('#'):
                            loop_ = False
                            continue
                        if l.startswith('loop_'):
                            loop_ = True
                            continue
                        if (loop_ == True) and (l.startswith('_')):
                            loopNames.append(l.split('.')[0])

                return list(set(loopNames))

            loopNames = getLoopNames(path)

            def getLoopData(filename, loopName) -> pd.DataFrame:
                """
                Create a Pandas DataFrame from an mmCIF file.
                """
                columns = []
                atomData = []
                loop_ = False
                _atom_siteLoop = False
                with open(filename) as f:
                    for l in f:
                        l = l.strip()
                        if len(l) == 0:
                            continue  # Ignore blank lines
                        if l.startswith('#'):
                            loop_ = False
                            _atom_siteLoop = False
                            continue
                        if l.startswith('loop_'):
                            loop_ = True
                            _atom_siteLoop = False
                            continue
                        if loop_ and l.startswith(loopName + '.'):
                            _atom_siteLoop = True
                            columns.append(l.replace(loopName + '.', "").strip())
                        if _atom_siteLoop and l.startswith('#'):
                            loop_ = False
                            _atom_siteLoop = False
                        if _atom_siteLoop and not l.startswith(loopName + '.'):
                            split_data = re.findall(r"'[^']*'|\S+", l)
                            split_data = [item.strip("'") for item in split_data]
                            atomData.append(split_data)

                df = pd.DataFrame(atomData, columns=columns)
                # df = df.infer_objects()  # This method returns the DataFrame with inferred data types
                df['idx'] = np.arange(1, df.shape[0] + 1)  # Create an 'idx' column
                df.set_index('idx', inplace=True)  # Set 'idx' as the index

                return df

            try:
                if len(self.chains) == 1:
                    chain = self.chains[0]
                else:
                    getLogger().info(self.chains)
                    return
            except:
                getLogger().info(self.chains)
                return

            if (("_struct_conf" in loopNames) or ("_struct_sheet_range" in loopNames)):
                # generates a Datatable containing secondary structure information from the mmcif file.

                # get chain information
                _struct_confDict = {}

                for residue in chain.residues:
                    _struct_confDict[int(residue.sequenceCode)] = {}
                    _struct_confDict[int(residue.sequenceCode)]['sequenceCode'] = residue.sequenceCode
                    _struct_confDict[int(residue.sequenceCode)]['residueType'] = residue.residueType
                    _struct_confDict[int(residue.sequenceCode)]['residuePID'] = residue.pid
                    _struct_confDict[int(residue.sequenceCode)]['conf_type_id'] = "COIL"

                # try to get secondary structure data from mmcif
                try:
                    dfHelix = getLoopData(path, "_struct_conf")
                except:
                    dfHelix = None

                try:
                    dfSheet = getLoopData(path, "_struct_sheet_range")
                except:
                    dfSheet = None

                # process the helix data - if there is some
                if dfHelix is not None:
                    # Iterate over rows in the DataFrame
                    getLogger().info("dfHelix\n", dfHelix.tail())
                    for index, row in dfHelix.iterrows():
                        # Get the relevant values from the row
                        conf_type_id = row['conf_type_id']
                        startID = row['beg_label_seq_id']
                        endID = row['end_label_seq_id']
                        getLogger().info(conf_type_id, startID, endID)
                        # Iterate over the range between startID and endID
                        for id in range(int(startID), int(endID) + 1):
                            # Set dictionary values for each 'id'
                            try:
                                _struct_confDict[id]['conf_type_id'] = conf_type_id
                            except:
                                getLogger().warning("Not found error. Likely mismatch between Chain and mmcif sequence")

                # process the sheet data if there is some
                if dfSheet is not None:
                    # Iterate over rows in the DataFrame
                    for index, row in dfSheet.iterrows():
                        # Get the relevant values from the row
                        conf_type_id = 'STRN'  # set sheet info to PDB type for Beta Strand
                        startID = row['beg_label_seq_id']
                        endID = row['end_label_seq_id']

                        # Iterate over the range between startID and endID
                        for id in range(int(startID), int(endID) + 1):
                            # Set dictionary values for each 'id'
                            try:
                                _struct_confDict[id]['conf_type_id'] = conf_type_id
                            except:
                                getLogger().warning("Not found error. Likely mismatch between Chain and mmcif sequence")

                # Convert the nested dictionary to a Pandas DataFrame
                df1 = pd.DataFrame.from_dict(_struct_confDict, orient='index')

                # reset the index to have a separate column for the index values
                df1.reset_index(inplace=True)
                df1.rename(columns={'index': 'id'}, inplace=True)

                # save the secondary structure dataframe
                self.newDataTable(name="SecondaryStructure", data=df1,
                                  comment='Secondary Structure Data from MMCIF')

        return [se]

    def _loadTextFile(self, path: (str, Path)) -> list:
        """Load text from file path into new Note object
        CCPNINTERNAL: called from text dataLoader
        """
        with logCommandManager('application.', 'loadData', path):
            path = aPath(path)
            name = path.basename

            with path.open('r') as fp:
                # cannot do read() as we want one string
                text = ''.join(line for line in fp.readlines())
            note = self.newNote(name=name, text=text)
        return [note]

    def _loadLayout(self, path: (str, Path), subType: str):
        # this is a GUI only function call. Please move to the appropriate location on 3.1
        self.application._restoreLayoutFromFile(path)

    def _loadExcelFile(self, path: (str, Path)) -> list:
        """Load data from a Excel file.
        :returns list of loaded objects (awaiting adjust ment of excelReader)
        CCPNINTERNAL: used in Excel data loader
        """

        with logCommandManager('application.', 'loadData', path):
            with undoBlockWithoutSideBar():
                reader = ExcelReader(project=self, excelPath=str(path))
                result = reader.load()
        return result

    def _loadChemCompFile(self, path: (str, Path)) -> list:
        """
        Load a Xml file containing a ChemComp.
        """
        from ccpn.core.Chain import _fetchChemCompFromFile

        with logCommandManager('application.', 'loadData', path):
            with undoBlockWithoutSideBar():
                chemcomp = _fetchChemCompFromFile(project=self, filePath=str(path))
        return chemcomp

    #===========================================================================================
    # End data loaders
    #===========================================================================================

    def getObjectsByPartialId(self, className: str,
                              idStartsWith: str) -> typing.List[AbstractWrapperObject]:
        """get objects from class name / shortName and the start of the ID.

        The function does NOT interrogate the API level, which makes it faster in a
        number fo cases, e.g. for NmrResidues"""

        dd = self._pid2Obj.get(className)
        if dd:
            # NB the _pid2Obj entry is set in the object init.
            # The relevant dictionary may therefore be missing if no object has yet been created
            result = [tt[1] for tt in dd.items() if tt[0].startswith(idStartsWith)]
        else:
            result = None
        #
        return result

    def getObjectsById(self, className: str, id: str) -> typing.List[AbstractWrapperObject]:
        """get objects from class name / shortName and the start of the ID.

        The function does NOT interrogate the API level, which makes it faster in a
        number fo cases, e.g. for NmrResidues"""

        dd = self._pid2Obj.get(className)
        if dd:
            # NB the _pid2Obj entry is set in the object init.
            # The relevant dictionary may therefore be missing if no object has yet been created
            result = [tt[1] for tt in dd.items() if tt[0] == id]
        else:
            result = None
        #
        return result

    def getObjectsByPids(self, pids: Iterable, objectTypes: tuple = None):
        """Optimise method to get all found objects from a list of pids. Remove any None.
        Warning: do not use with zip
        Specify objectTypes to only return objects of the required type, otherwise all objects returned, defaults to None
        """

        if not isinstance(pids, Iterable):
            raise ValueError(f'{self.__class__.__name__}.getObjectsByPids: pids argument must be an iterable')
        if not isinstance(objectTypes, (type, type(None))) and \
                not (isinstance(objectTypes, tuple) and all(
                        isinstance(obj, (type, type(None))) for obj in objectTypes)):
            raise ValueError(
                    f'{self.__class__.__name__}.getObjectsByPids: objectTypes must be a type, tuple of types, or None')

        if objectTypes:
            return list(filter(lambda obj: isinstance(obj, objectTypes),
                               map(lambda x: self.getByPid(x) if isinstance(x, str) else x, pids)))
        else:
            return list(filter(None, map(lambda x: self.getByPid(x) if isinstance(x, str) else x, pids)))

    def getByPids(self, pids: Iterable):
        """Optimise method to get all found objects from a list of pids. Remove any None.
        """
        if not isinstance(pids, Iterable):
            raise ValueError(f'{self.__class__.__name__}.getByPids: pids must be an iterable')

        objs = [self.getByPid(pid) if isinstance(pid, str) else pid for pid in pids]
        return list(filter(lambda obj: self.isCoreObject(obj), objs))

    @staticmethod
    def getPidsByObjects(objs: list):
        """Optimise method to get all found pids from a list of objects. Remove any None.
         Warning: do not use with zip"""
        return list(filter(None, map(lambda x: x.pid if isinstance(x, AbstractWrapperObject) else None, objs)))

    def getCcpCodeData(self, ccpCode, molType=None, atomType=None):
        """Get the CcpCode for molType/AtomType
        """
        from ccpnmodel.ccpncore.lib.assignment.ChemicalShift import getCcpCodeData

        return getCcpCodeData(self._apiNmrProject, ccpCode, molType='protein', atomType=atomType)

    @logCommand('project.')
    def saveToArchive(self) -> Optional[Path]:
        """Make new time-stamped archive of project
        :return path to .tgz archive file as a Path object
        """
        # NOTE:ED - need better gui error-trap
        if self.readOnly:
            getLogger().warning(f'{self.__class__.__name__}.saveToArchive: project is read-only')
            return None

        from ccpn.core.lib.ProjectArchiver import ProjectArchiver

        archiver = ProjectArchiver(projectPath=self.path)
        if archivePath := archiver.makeArchive():
            getLogger().info(f'==> Project archived to {archivePath}')
            return archivePath

    def _getArchivePaths(self) -> List[Path]:
        """:return list of archives from archive directory
        CCPNINTERAL: used in GuiMainWindow
        """
        from ccpn.core.lib.ProjectArchiver import ProjectArchiver

        archiver = ProjectArchiver(projectPath=self.project.path)
        return archiver.archives

    def _getExperimentClassifications(self) -> dict:
        """Get a dictionary of dictionaries of dimensionCount:sortedNuclei:ExperimentClassification named tuples.
        """
        # GWV: 13Jan2023: made into private method; only FrameWork needs this.
        # NOTE:ED - better than being in spectrumLib but still needs moving
        from ccpnmodel.ccpncore.lib.spectrum.NmrExpPrototype import getExpClassificationDict

        return getExpClassificationDict(self._wrappedData)

    @logCommand('project.')
    def copySpectraToProject(self) -> list:
        """ Copy spectra from the original location to the local spectra directory of self;
        e.g. in "myproject.ccpn/data/spectra".
        This is useful when saving the project and want to keep the spectra together with the project.
        :return A list of Path instances of files/directories copied
        """
        result = []
        with undoBlock():
            for sp in self.spectra:
                _files = sp.copyDataToProject()
                result.extend(_files)
        return result

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    @logCommand('project.')
    def newSpectrum(self, path: str, name: str = None):
        """Creation of new Spectrum defined by path; optionally set name.
        """
        from ccpn.core.Spectrum import _newSpectrum

        return _newSpectrum(self, path=path, name=name)

    @logCommand('project.')
    def newEmptySpectrum(self, isotopeCodes: Sequence[str], dimensionCount=None, name='emptySpectrum', path=None,
                         **parameters):
        """
        Make new Empty spectrum from isotopeCodes list - without data and with default parameters.
        default parameters are defined in: SpectrumDataSourceABC.isotopeDefaultDataDict

        :param isotopeCodes: a tuple/list of isotope codes that define the dimensions; e.g. ('1H', '13C')
        :dimensionCount: an optional dimensionCount parameter; default derived from len(isotopeCodes)
        :param name: the name of the resulting spectrum
        :param path: an optional path to be stored with the Spectrum instance
        :param **parameters: optional spectrum (parameter, value) pairs
        :return: a new Spectrum instance.
        """
        from ccpn.core.Spectrum import _newEmptySpectrum

        return _newEmptySpectrum(self, isotopeCodes=isotopeCodes, dimensionCount=dimensionCount,
                                 name=name, path=path, **parameters)

    @logCommand('project.')
    def newHdf5Spectrum(self, isotopeCodes: Sequence[str], name='hdf5Spectrum', path=None, **parameters):
        """
        Make new hdf5 spectrum from isotopeCodes list - without data and with default parameters.

        :param isotopeCodes:
        :param name: name of the spectrum
        :param path: optional path (autogenerated from name when None; resulting file will be in
                     data/spectra folder of the project)
        :param **parameters: optional spectrum (parameter, value) pairs
        :return: a new Spectrum instance.
        """
        from ccpn.core.Spectrum import _newHdf5Spectrum

        return _newHdf5Spectrum(self, isotopeCodes=isotopeCodes, name=name, path=path, **parameters)

    @logCommand('project.')
    def newNmrChain(self, shortName: str = None, isConnected: bool = False, label: str = '?',
                    comment: str = None):
        """Create new NmrChain. Setting isConnected=True produces a connected NmrChain.

        :param str shortName: shortName for new nmrChain (optional, defaults to '@ijk' or '#ijk',  ijk positive integer
        :param bool isConnected: (default to False) If true the NmrChain is a connected stretch. This can NOT be changed later
        :param str label: Modifiable NmrChain identifier that does not change with reassignment. Defaults to '@ijk'/'#ijk'
        :param str comment: comment for new nmrChain (optional)
        :return: a new NmrChain instance.
        """
        from ccpn.core.NmrChain import _newNmrChain

        return _newNmrChain(self, shortName=shortName, isConnected=isConnected,
                            label=label, comment=comment)

    @logCommand('project.')
    def fetchNmrChain(self, shortName: str = None):
        """Fetch chain with given shortName; If none exists call newNmrChain to make one first

        If shortName is None returns a new NmrChain with name starting with '@'

        :param shortName: string name of required nmrAtom
        :return: an NmrChain instance.
        """
        from ccpn.core.NmrChain import _fetchNmrChain

        return _fetchNmrChain(self, shortName=shortName)

    @logCommand('project.')
    def produceNmrAtom(self, atomId: str = None, chainCode: str = None,
                       sequenceCode: Union[int, str] = None,
                       residueType: str = None, name: str = None):
        """Get chainCode, sequenceCode, residueType and atomName from dot-separated atomId or Pid
            or explicit parameters, and find or create an NmrAtom that matches
            Empty chainCode gets NmrChain:@- ; empty sequenceCode get a new NmrResidue

        :param atomId:
        :param chainCode:
        :param sequenceCode:
        :param residueType:
        :param name: new or existing nmrAtom, matching parameters
        :return:
        """
        from ccpn.core.NmrAtom import _produceNmrAtom

        return _produceNmrAtom(self, atomId=atomId, chainCode=chainCode,
                               sequenceCode=sequenceCode, residueType=residueType, name=name)

    @logCommand('project.')
    def newNote(self, name: str = None, text: str = None, comment: str = None, **kwds):
        """Create new Note.

        See the Note class for details.

        Optional keyword arguments can be passed in; see Note._newNote for details.

        :param name: name for the note.
        :param text: contents of the note.
        :return: a new Note instance.
        """
        from ccpn.core.Note import _newNote

        return _newNote(self, name=name, text=text, comment=comment, **kwds)

    @logCommand('project.')
    def newWindow(self, title: str = None, position: tuple = (), size: tuple = (), **kwds):
        """Create new child Window.

        See the Window class for details.

        Optional keyword arguments can be passed in; see Window._newWindow for details.

        :param str title: window  title (optional, defaults to 'W1', 'W2', 'W3', ...
        :param tuple position: x,y position for new window in integer pixels.
        :param tuple size: x,y size for new window in integer pixels.
        :return: a new Window instance.
        """
        from ccpn.ui._implementation.Window import _newWindow

        return _newWindow(self, title=title, position=position, size=size, **kwds)

    @logCommand('project.')
    def newStructureEnsemble(self, name: str = None, data=None, comment: str = None, **kwds):
        """Create new StructureEnsemble.

        See the StructureEnsemble class for details.

        Optional keyword arguments can be passed in; see StructureEnsemble._newStructureEnsemble for details.

        :param name: new name for the StructureEnsemble.
        :param data: Pandas dataframe.
        :param comment: optional comment string
        :return: a new StructureEnsemble instance.
        """
        from ccpn.core.StructureEnsemble import _newStructureEnsemble

        return _newStructureEnsemble(self, name=name, data=data, comment=comment, **kwds)

    def newDataTable(self, name: str = None, data=None, comment: str = None, **kwds):
        """Create new DataTable.

        See the DataTable class for details.

        Optional keyword arguments can be passed in; see DataTable._newDataTable for details.

        :param name: new name for the DataTable.
        :param data: Pandas dataframe.
        :param comment: optional comment string
        :return: a new DataTable instance.
        """
        from ccpn.core.DataTable import _newDataTable

        getLogger().info(
                f'project.newDataTable(name={name})')  # don't log the full dataFrame. is not needed! Add exclusions on Decorator logCommand
        return _newDataTable(self, name=name, data=data, comment=comment, **kwds)

    @logCommand('project.')
    def fetchDataTable(self, name: str):
        """Get or create new DataTable.
        :param name: name for the DataTable.
        """
        from ccpn.core.DataTable import _fetchDataTable

        return _fetchDataTable(self, name=name)

    @logCommand('project.')
    def _newPeakCluster(self, peaks: Sequence[Union['Peak', str]] = None, **kwds) -> Optional['_PeakCluster']:
        """Create new PeakCluster.

        See the PeakCluster class for details.

        Optional keyword arguments can be passed in; see PeakCluster._newPeakCluster for details.

        CCPN Internal - this object is deprecated.

        :param peaks: optional list of peaks as objects or pids.
        :return: a new PeakCluster instance.
        """
        from ccpn.core._implementation._PeakCluster import _newPeakCluster

        return _newPeakCluster(self, peaks=peaks, **kwds)

    @logCommand('project.')
    def newCollection(self, name: str = None, *, items: Sequence[Any] = None, **kwds) -> 'Collection':
        """Create new Collection.

        See the Collection class for details.

        Optional keyword arguments can be passed in; see Collection._newCollection for details.

        :param name: optional name of type str.
        :param items: optional list of core objects as objects or pids.
        :return: a new Collection instance.
        """
        return self._collectionList.newCollection(name=name, items=items, **kwds)

    @logCommand('project.')
    def newSample(self, name: str = None, pH: float = None, ionicStrength: float = None,
                  amount: float = None, amountUnit: str = None, isVirtual: bool = False, isHazardous: bool = None,
                  creationDate: datetime = None, batchIdentifier: str = None, plateIdentifier: str = None,
                  rowNumber: int = None, columnNumber: int = None, comment: str = None, **kwds) -> 'Sample':
        """Create new Sample.

        See the Sample class for details.

        Optional keyword arguments can be passed in; see Sample._newSample for details.

        :param name:
        :param pH:
        :param ionicStrength:
        :param amount:
        :param amountUnit:
        :param isVirtual:
        :param isHazardous:
        :param creationDate:
        :param batchIdentifier:
        :param plateIdentifier:
        :param rowNumber:
        :param columnNumber:
        :param comment:
        :param serial: optional serial number.
        :return: a new Sample instance.
        """
        from ccpn.core.Sample import _newSample

        return _newSample(self, name=name, pH=pH, ionicStrength=ionicStrength,
                          amount=amount, amountUnit=amountUnit, isVirtual=isVirtual, isHazardous=isHazardous,
                          creationDate=creationDate, batchIdentifier=batchIdentifier, plateIdentifier=plateIdentifier,
                          rowNumber=rowNumber, columnNumber=columnNumber, comment=comment, **kwds)

    @logCommand('project.')
    def fetchSample(self, name: str) -> 'Sample':
        """Get or create Sample with given name.
        See the Sample class for details.
        :param self: project
        :param name: sample name
        :return: new or existing Sample instance.
        """
        from ccpn.core.Sample import _fetchSample

        return _fetchSample(self, name)

    @logCommand('project.')
    def newStructureData(self, name: str = None, title: str = None, programName: str = None, programVersion: str = None,
                         dataPath: str = None, creationDate: datetime = None, uuid: str = None,
                         comment: str = None, moleculeFilePath: str = None, **kwds):
        """Create new StructureData

        See the StructureData class for details.

        Optional keyword arguments can be passed in; see StructureData._newStructureData for details.

        :param title: deprecated - original name for StructureData, please use .name
        :param name:
        :param programName:
        :param programVersion:
        :param dataPath:
        :param creationDate:
        :param uuid:
        :param comment:
        :return: a new StructureData instance.
        """
        from ccpn.core.StructureData import _newStructureData

        return _newStructureData(self, name=name, title=title, programName=programName, programVersion=programVersion,
                                 dataPath=dataPath, creationDate=creationDate, uuid=uuid, comment=comment,
                                 moleculeFilePath=moleculeFilePath, **kwds)

    @logCommand('project.')
    def newSpectrumGroup(self, name: str, spectra=(), **kwds):
        """Create new SpectrumGroup

        See the SpectrumGroup class for details.

        Optional keyword arguments can be passed in; see SpectrumGroup._newSpectrumGroup for details.

        :param name: name for the new SpectrumGroup
        :param spectra: optional list of spectra as objects or pids
        :return: a new SpectrumGroup instance.
        """
        from ccpn.core.SpectrumGroup import _newSpectrumGroup

        return _newSpectrumGroup(self, name=name, spectra=spectra, **kwds)

    @logCommand('project.')
    def createChain(self,
                    sequence: Union[str, Sequence[str]] = None,
                    compoundName: str = None,
                    startNumber: int = 1, molType: str = None, isCyclic: bool = False,
                    shortName: str = None, role: str = None, comment: str = None,
                    expandFromAtomSets: bool = True,
                    addPseudoAtoms: bool = True, addNonstereoAtoms: bool = True,
                    **kwds):
        """Create new chain from sequence of residue codes, using default variants.
        Automatically creates the corresponding polymer Substance if the compoundName is not already taken
        See the Chain class for details.
        Optional keyword arguments can be passed in; see Chain._createChain for details.
        :param sequence: str or list of str.
            allowed sequence formats:
                - 1-Letter-Code (only standards)
                    sequence =  'AAAAAA'
                    sequence =  'A A A A A A'
                    sequence =  'A, A, A, A, A, A'
                    sequence =  ['A', 'A', 'A', 'A', 'A']
                - 3-Letter-Code  (standards and non-standards)
                    sequence =  'ALA ALA ALA ALA'
                    sequence =  'ALA, ALA, ALA, ALA'
                    sequence =  ['ALA', 'ALA', 'ALA']
                - ccpCodes:  (standards and non-standards)
                    - sequence containing Standard residue(s) CcpCodes e.g.::
                        sequence = 'Ala Leu Ala'
                        sequence = 'Ala, Leu, Ala'
                        sequence = ['Ala', 'Leu', 'Ala']
                    - sequence containing Non-Standard residue(s) CcpCodes e.g.:
                        sequence = ['Ala', 'Aba', Orn]
                    - sequence of a small-molecule CcpCodes: (Note you need to import the ChemComp first if not available in the Project. see docs)
                        sequence = ['Atp']  # if only one code Must be in a list
                        sequence = ['MySmallMolecule'] # if only one code Must be in a list


        :param str compoundName: name of new Substance (e.g. 'Lysozyme') Defaults to 'Molecule_n
        :param str molType: molType ('protein','DNA', 'RNA'). Needed only if sequence is a string.
        :param int startNumber: number of first residue in sequence
        :param str shortName: shortName for new chain (optional)
        :param str role: role for new chain (optional)
        :param str comment: comment for new chain (optional)
        :param bool expandFromAtomSets: Create new Atoms corresponding to the ChemComp AtomSets definitions.
                Eg. H1, H2, H3 equivalent atoms will add a new H% atom. This will facilitate assignments workflows.
                See ccpn.core.lib.MoleculeLib.expandChainAtoms for details.
        :return: a new Chain instance.
        """
        from ccpn.core.Chain import _createChain

        return _createChain(self,
                            sequence=sequence,
                            compoundName=compoundName,
                            startNumber=startNumber, molType=molType, isCyclic=isCyclic,
                            shortName=shortName, role=role, comment=comment,
                            expandFromAtomSets=expandFromAtomSets, addPseudoAtoms=addPseudoAtoms,
                            addNonstereoAtoms=addNonstereoAtoms, **kwds)

    # GWV: why not newChain to be consistent???
    newChain = createChain

    @logCommand('project.')
    def newSubstance(self, name: str = None, labelling: str = None, substanceType: str = 'Molecule',
                     userCode: str = None, smiles: str = None, inChi: str = None, casNumber: str = None,
                     empiricalFormula: str = None, molecularMass: float = None, comment: str = None,
                     synonyms: typing.Sequence[str] = (), atomCount: int = 0, bondCount: int = 0,
                     ringCount: int = 0, hBondDonorCount: int = 0, hBondAcceptorCount: int = 0,
                     polarSurfaceArea: float = None, logPartitionCoefficient: float = None, **kwds):
        """Create new substance WITHOUT storing the sequence internally
        (and hence not suitable for making chains). SubstanceType defaults to 'Molecule'.

        ADVANCED alternatives are 'Cell' and 'Material'

        See the Substance class for details.

        Optional keyword arguments can be passed in; see Substance._newSubstance for details.

        :param name:
        :param labelling:
        :param substanceType:
        :param userCode:
        :param smiles:
        :param inChi:
        :param casNumber:
        :param empiricalFormula:
        :param molecularMass:
        :param comment:
        :param synonyms:
        :param atomCount:
        :param bondCount:
        :param ringCount:
        :param hBondDonorCount:
        :param hBondAcceptorCount:
        :param polarSurfaceArea:
        :param logPartitionCoefficient:
        :return: a new Substance instance.
        """
        from ccpn.core.Substance import _newSubstance

        return _newSubstance(self, name=name, labelling=labelling, substanceType=substanceType,
                             userCode=userCode, smiles=smiles, inChi=inChi, casNumber=casNumber,
                             empiricalFormula=empiricalFormula, molecularMass=molecularMass, comment=comment,
                             synonyms=synonyms, atomCount=atomCount, bondCount=bondCount,
                             ringCount=ringCount, hBondDonorCount=hBondDonorCount,
                             hBondAcceptorCount=hBondAcceptorCount,
                             polarSurfaceArea=polarSurfaceArea, logPartitionCoefficient=logPartitionCoefficient, **kwds)

    @logCommand('project.')
    def fetchNefSubstance(self, sequence: typing.Sequence[dict], name: str = None, **kwds):
        """Fetch Substance that matches sequence of NEF rows and/or name

        See the Substance class for details.

        Optional keyword arguments can be passed in; see Substance._fetchNefSubstance for details.

        :param self:
        :param sequence:
        :param name:
        :return: a new Nef Substance instance.
        """
        from ccpn.core.Substance import _fetchNefSubstance

        return _fetchNefSubstance(self, sequence=sequence, name=name, **kwds)

    @logCommand('project.')
    def getNefSubstance(self, sequence: typing.Sequence[dict], name: str = None, **kwds):
        """Get existing Substance that matches sequence of NEF rows and/or name

        See the Substance class for details.

        Optional keyword arguments can be passed in; see Substance._fetchNefSubstance for details.

        :param self:
        :param sequence:
        :param name:
        :return: a new Nef Substance instance.
        """
        from ccpn.core.Substance import _getNefSubstance

        return _getNefSubstance(self, sequence=sequence, name=name, **kwds)

    @logCommand('project.')
    def createPolymerSubstance(self, sequence: typing.Sequence[str], name: str,
                               labelling: str = None, userCode: str = None, smiles: str = None,
                               synonyms: typing.Sequence[str] = (), comment: str = None,
                               startNumber: int = 1, molType: str = None, isCyclic: bool = False,
                               **kwds):
        """Make new Substance from sequence of residue codes, using default linking and variants

        NB: For more complex substances, you must use advanced, API-level commands.

        See the Substance class for details.

        Optional keyword arguments can be passed in; see Substance._fetchNefSubstance for details.

        :param Sequence sequence: string of one-letter codes or sequence of residueNames
        :param str name: name of new substance
        :param str labelling: labelling for new substance. Optional - None means 'natural abundance'
        :param str userCode: user code for new substance (optional)
        :param str smiles: smiles string for new substance (optional)
        :param Sequence[str] synonyms: synonyms for Substance name
        :param str comment: comment for new substance (optional)
        :param int startNumber: number of first residue in sequence
        :param str molType: molType ('protein','DNA', 'RNA'). Required only if sequence is a string.
        :param bool isCyclic: Should substance created be cyclic?
        :return: a new Substance instance.
        """
        from ccpn.core.Substance import _createPolymerSubstance

        return _createPolymerSubstance(self, sequence=sequence, name=name,
                                       labelling=labelling, userCode=userCode, smiles=smiles,
                                       synonyms=synonyms, comment=comment,
                                       startNumber=startNumber, molType=molType, isCyclic=isCyclic,
                                       **kwds)

    @logCommand('project.')
    def fetchSubstance(self, name: str, labelling: str = None):
        """Get or create Substance with given name and labelling.
        See the Substance class for details.

        :param self:
        :param name:
        :param labelling:
        :return: new or existing Substance instance.
        """
        from ccpn.core.Substance import _fetchSubstance

        return _fetchSubstance(self, name=name, labelling=labelling)

    @logCommand('project.')
    def newComplex(self, name: str = None, chains=(), **kwds):
        """Create new Complex.
        See the Complex class for details.
        Optional keyword arguments can be passed in; see Complex._newComplex for details.

        :param name:
        :param chains:
        :return: a new Complex instance.
        """
        from ccpn.core.Complex import _newComplex

        return _newComplex(self, name=name, chains=chains, **kwds)

    @logCommand('project.')
    def newChemicalShiftList(self, name: str = None, spectra=(), **kwds):
        """Create new ChemicalShiftList.
        See the ChemicalShiftList class for details.

        :param name:
        :param spectra:
        :return: a new ChemicalShiftList instance.
        """
        from ccpn.core.ChemicalShiftList import _newChemicalShiftList
        from ccpn.core.Spectrum import Spectrum

        if (result := _newChemicalShiftList(self, name=name, **kwds)):
            # needs to be here so that all chemicalShiftTables are notified correctly
            if spectra:
                getByPid = self._project.getByPid
                if (spectra := list(filter(lambda sp: isinstance(sp, Spectrum),
                                           map(lambda sp: getByPid(sp) if isinstance(sp, str) else sp, spectra)))):
                    # add/transfer the spectra
                    result.spectra = spectra

            return result

    @logCommand('project.')
    def getChemicalShiftList(self, name: str = None, **kwds):
        """Get existing ChemicalShiftList.
        See the ChemicalShiftList class for details.

        :param name:
        :return: a new ChemicalShiftList instance.
        """
        from ccpn.core.ChemicalShiftList import _getChemicalShiftList

        return _getChemicalShiftList(self, name=name, **kwds)

    def getCollection(self, name: str) -> Optional['Collection']:
        """Return the collection from the supplied name
        """
        from ccpn.core.Collection import _getCollection

        return _getCollection(self, name=name)

    @logCommand('project.')
    def fetchCollection(self, name: str = None) -> 'Collection':
        """Get or create Collection.
        See the Collection class for details.

        :param name:
        :return: a new Collection instance.
        """
        from ccpn.core.Collection import _fetchCollection

        return _fetchCollection(self, name=name)

    @logCommand('project.')
    def newBond(self, **kwds):
        """Create new Bond.
        See the Bond class for details.
        Optional keyword arguments can be passed in; see Bond._newBond for details.

        :return: a new Bond instance.
        """
        from ccpn.core.Bond import _newBond

        return _newBond(self, **kwds)

    def __repr__(self):
        """String representation"""
        if self.isDeleted:
            return "<Project:-deleted-, isDeleted=True>"
        else:
            return f"<Project:{self.name}>"

    def __str__(self):
        """String representation"""
        if self.isDeleted:
            return "<PR:-deleted-, isDeleted=True>"
        else:
            return f"<PR:{self.name}>"


#End class Project

#=========================================================================================
# Code adapted from prior _implementation/Io.py
#=========================================================================================

def _newProject(application, name: str, path: Path, isTemporary: bool = False) -> Project:
    """Make new project, putting underlying data storage (API project) at path
    :return Project instance
    """
    from ccpn.core.lib.XmlLoader import XmlLoader
    from ccpn.core.lib.ProjectSaveHistory import newProjectSaveHistory

    xmlLoader = XmlLoader(path=path, name=name, create=True)
    xmlLoader.newProject(overwrite=True)

    project = Project(xmlLoader)
    xmlLoader.project = project
    project._isNew = True
    project._isTemporary = isTemporary
    # NB: linkages are set in Framework._initialiseProject()

    project._objectVersion = application.applicationVersion
    project._saveHistory = newProjectSaveHistory(project.path)

    application._saveOverride = False
    project._application = application
    project._updateReadOnlyState()

    # the initialisation is completed by Framework._initialiseProject when it has done its things
    # project._initialiseProject()

    return project


def _loadProject(application, path: str) -> Project:
    """Load the project defined by path
    :return Project instance
    """
    from ccpn.core.lib.XmlLoader import XmlLoader
    from ccpn.core._implementation.updates.update_v2 import updateProject_fromV2

    _path = aPath(path)
    if not _path.exists():
        raise ValueError(f'Path {_path} does not exist')

    xmlLoader = XmlLoader(path=_path, readOnly=True)  # application._readOnly)  always read-only during load
    xmlLoader.loadProject()

    _isV2 = xmlLoader.isV2  # save this, because if V2, we are going to change the xmlLoader
    # If path pointed to a V2 project, we need to do some manipulations
    if _isV2:
        _newPath = _path.withSuffix(CCPN_DIRECTORY_SUFFIX).uniqueVersion()
        # Get a path in the temporary directory - safest for first-save
        _newPath = application._getTemporaryPath(prefix=f'{_path.basename}_', suffix=CCPN_DIRECTORY_SUFFIX)
        _newXmlLoader = XmlLoader.newFromLoader(xmlLoader, path=_newPath, create=True)
        xmlLoader = _newXmlLoader

    project = Project(xmlLoader)
    # back linkage
    xmlLoader.project = project

    if not os.access(_path.parent, os.W_OK) or \
            next((dd for root, dirs, files in os.walk(_path)
                  for dd in dirs if not os.access(aPath(root) / dd, os.W_OK)), False):
        getLogger().warning('Project contains a read-only folder')

    project._application = application  # bit of a hack, isn't set until initialise
    project._updateReadOnlyState()

    project._saveHistory = getProjectSaveHistory(project.path)

    # If path pointed to a V2 project, call the updates, and save the data
    if _isV2:
        try:
            # call the update
            getLogger().info(f'==> Upgrading {project} to version-3')
            updateProject_fromV2(project)
        except Exception as es:
            txt = f'Failed upgrading {project} from version-2: {es}'
            getLogger().warning(txt)
            raise RuntimeError(txt) from es

        # Save using the xmlLoader only as we do not have a complete and valid V3-Project yet
        if not project.readOnly:
            getLogger().debug(f'after update: Saving project to {xmlLoader.path}')
            try:
                # xmlLoader.saveUserData(keepFallBack=False)
                project._saveHistory.addSaveRecord(version=project._objectVersion,
                                                   comment='upgraded from version-2')
                # project._saveHistory.save()
            except (PermissionError, FileNotFoundError):
                getLogger().info('Folder may be read-only')

        project._isNew = True
        project._isTemporary = True

    elif xmlLoader.pathHasChanged or xmlLoader.nameHasChanged:
        # path or name have changed (actually, they are connected)
        # save it, keeping a fallback for if all goes wrong
        # Save using the xmlLoader only as we do not have a complete and valid V3-Project yet
        if not project.readOnly:
            try:
                # NOTE:ED - shouldn't actually be doing any writes now?
                #   in which case remove the error-check

                # xmlLoader.saveUserData(keepFallBack=True)
                project._saveHistory.addSaveRecord(version=project._objectVersion,
                                                   comment='Path/name has changed')
                # project._saveHistory.save()

            except (PermissionError, FileNotFoundError):
                getLogger().info('Folder may be read-only')

        project._isNew = False
        project._isTemporary = False

    else:
        project._isNew = False
        project._isTemporary = False

    # the initialisation is completed by Framework._initialiseProject when it has done its things
    # project._initialiseProject()

    return project
