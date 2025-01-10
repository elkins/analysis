"""
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
__dateModified__ = "$dateModified: 2025-01-10 18:01:46 +0000 (Fri, January 10, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from typing import Tuple, Sequence, List, Union, Optional
from functools import partial
from collections.abc import Iterable

from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core._implementation.DataFrameABC import DataFrameABC
from ccpn.core.PeakList import PeakList
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.lib.Pid import Pid, remapSeparators
from ccpn.core.lib.ContextManagers import newObject, newV3Object, renameObject, \
    undoStackBlocking, undoBlock, ccpNmrV3CoreSetter
from ccpn.util.decorators import logCommand
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.DataEnum import DataEnum


CS_UNIQUEID = 'uniqueId'
CS_PID = 'pid'
CS_VALUE = 'value'
CS_VALUEERROR = 'valueError'
CS_FIGUREOFMERIT = 'figureOfMerit'
CS_NMRATOM = 'nmrAtom'
CS_NMRRESIDUE = 'nmrResidue'
CS_CHAINCODE = 'chainCode'
CS_SEQUENCECODE = 'sequenceCode'
CS_RESIDUETYPE = 'residueType'
CS_ATOMNAME = 'atomName'
CS_STATE = 'state'
CS_STATIC = 'static'
CS_DYNAMIC = 'dynamic'
CS_ORPHAN = 'orphan'
CS_SHIFTLISTPEAKS = 'shiftListPeaks'
CS_ALLPEAKS = 'allPeaks'
CS_SHIFTLISTPEAKSCOUNT = 'shiftListPeaksCount'
CS_ALLPEAKSCOUNT = 'allPeaksCount'
CS_COMMENT = 'comment'
CS_ISDELETED = 'isDeleted'
CS_OBJECT = '_object'  # this must match the object search for guiTable

CS_COLUMNS = (CS_UNIQUEID, CS_ISDELETED,
              CS_STATIC,
              CS_VALUE, CS_VALUEERROR, CS_FIGUREOFMERIT,
              CS_NMRATOM, CS_CHAINCODE, CS_SEQUENCECODE, CS_RESIDUETYPE, CS_ATOMNAME,
              CS_COMMENT)
CS_TABLECOLUMNS = (CS_UNIQUEID, CS_ISDELETED, CS_PID,
                   # CS_STATIC,
                   CS_VALUE, CS_VALUEERROR, CS_FIGUREOFMERIT,
                   CS_NMRATOM, CS_CHAINCODE, CS_SEQUENCECODE, CS_RESIDUETYPE, CS_ATOMNAME,
                   CS_STATE, CS_ORPHAN,
                   CS_ALLPEAKS, CS_SHIFTLISTPEAKSCOUNT, CS_ALLPEAKSCOUNT,
                   CS_COMMENT, CS_OBJECT)

# NOTE:ED - these currently match the original V3 classNames - not ChemShift
#   it is the name used in the dataframe and in project._getNextUniqueIdValue
CS_CLASSNAME = 'ChemicalShift'
CS_PLURALNAME = 'chemicalShifts'


class ChemicalShiftState(DataEnum):
    STATIC = 0, CS_STATIC
    DYNAMIC = 1, CS_DYNAMIC
    ORPHAN = 2, CS_ORPHAN


class _ChemicalShiftListFrame(DataFrameABC):
    """
    ChemicalShiftList data - as a Pandas DataFrame.
    CCPNInternal - only for access from ChemicalShiftList
    """
    # NOT USED YET
    # Class added to wrap the model data in a core class
    # functionality can be moved from main class below to here at some point as required
    # - currently not using undo/redo ability of superclass
    pass


# register the class with DataFrameABC for json loading/saving
_ChemicalShiftListFrame.register()

from ccpn.core._implementation.Updater import updateObject, UPDATE_POST_OBJECT_INITIALISATION
from ccpn.core._implementation.updates.update_3_0_4 import _updateChemicalShiftList_3_0_4_to_3_1_0


@updateObject('3.0.4', '3.1.0', _updateChemicalShiftList_3_0_4_to_3_1_0, UPDATE_POST_OBJECT_INITIALISATION)
class ChemicalShiftList(AbstractWrapperObject):
    """An object containing Chemical Shifts. Note: the object is not a (subtype of a) Python list.
    To access all ChemicalShift objects, use chemicalShiftList.chemicalShifts.

    A chemical shift list named 'default' is used by default for new experiments,
    and is created if necessary."""

    #: Short class name, for PID.
    shortClassName = 'CL'
    # Attribute it necessary as subclasses must use superclass className
    className = 'ChemicalShiftList'

    _parentClass = Project

    #: Name of plural link to instances of class
    _pluralLinkName = 'chemicalShiftLists'

    # the attribute name used by current
    _currentAttributeName = 'chemicalShiftLists'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = Nmr.ShiftList._metaclass.qualifiedName()
    _wrappedData: Nmr.ShiftList

    def __init__(self, project: Project, wrappedData: Nmr.ShiftList):
        self._wrappedData = wrappedData
        self._project = project
        defaultName = f'Shifts{wrappedData.serial}'
        self._setUniqueStringKey(defaultName)

        # internal lists to hold the current chemicalShifts and deletedChemicalShift
        self._shifts = []
        self._deletedShifts = []

        super().__init__(project, wrappedData)

    #-----------------------------------------------------------------------------------------
    # CCPN Properties
    #-----------------------------------------------------------------------------------------

    @property
    def _apiShiftList(self) -> Nmr.ShiftList:
        """ CCPN ShiftList matching ChemicalShiftList"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """name, regularised as used for id"""
        return self._wrappedData.name.translate(remapSeparators)

    @property
    def serial(self) -> int:
        """Shift list serial number"""
        return self._wrappedData.serial

    @property
    def _parent(self) -> Project:
        """Parent (containing) object."""
        return self._project

    @property
    def name(self) -> str:
        """name of ChemicalShiftList. """
        return self._wrappedData.name

    @name.setter
    def name(self, value: str):
        """set name of ChemicalShiftList."""
        self.rename(value)

    @property
    def unit(self) -> str:
        """Measurement unit of ChemicalShiftList. Should always be 'ppm'"""
        return self._wrappedData.unit

    @unit.setter
    def unit(self, value: str):
        self._wrappedData.unit = value

    @property
    def autoUpdate(self) -> bool:
        """Automatically update Chemical Shifts from assigned peaks - True/False"""
        return self._wrappedData.autoUpdate

    @autoUpdate.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def autoUpdate(self, value: bool):
        self._wrappedData.autoUpdate = value

    @property
    def isSimulated(self) -> bool:
        """True if the ChemicalShiftList is simulated."""
        return self._wrappedData.isSimulated

    @isSimulated.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def isSimulated(self, value: bool):
        self._wrappedData.isSimulated = value

    @property
    def static(self) -> bool:
        """True if the ChemicalShiftList is static.
        Overrides chemicalShift.static"""
        return self._wrappedData.static

    @static.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def static(self, value: bool):
        self._wrappedData.static = value

    @property
    def autoChangeStatic(self) -> bool:
        """Prevent further queries"""
        return self._wrappedData.autoChangeStatic

    @autoChangeStatic.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def autoChangeStatic(self, value: bool):
        self._wrappedData.autoChangeStatic = value

    @staticmethod
    def _recalculatePeakShifts(nmrResidues, shifts):
        # update the assigned nmrAtom chemical shift values - notify the nmrResidues and chemicalShifts
        for sh in shifts:
            sh._static = not sh.chemicalShiftList.spectra
            sh._recalculateShiftValue()
        for nmr in nmrResidues:
            nmr._finaliseAction('change')
        for sh in shifts:
            sh._finaliseAction('change')

    @property
    def spectra(self) -> Tuple[Spectrum, ...]:
        """ccpn.Spectra that use ChemicalShiftList to store chemical shifts"""
        ff = self._project._data2Obj.get
        return tuple(sorted(ff(y) for x in self._wrappedData.experiments
                            for y in x.dataSources))

    @spectra.setter
    @logCommand(get='self', isProperty=True)
    def spectra(self, _spectra: Optional[Sequence[Union[Spectrum, str]]]):
        """Set the list of spectra attached to the chemicalShiftList
        List must be iterable and of type Spectrum or str
        :param _spectra: Iterable or None
        """
        if _spectra:
            if not isinstance(_spectra, Iterable):
                raise ValueError(f'{self.className}.spectra must be an iterable of items of type Spectrum or str')
            getByPid = self._project.getByPid
            _spectra = [getByPid(x) if isinstance(x, str) else x for x in _spectra]
            if not all(isinstance(val, Spectrum) for val in _spectra):
                raise ValueError(f'{self.className}.spectra must be an iterable of items of type Spectrum or str')
        else:
            _spectra = []

        # add a spectrum/remove a spectrum
        _createSpectra = set(_spectra) - set(self.spectra)
        _createCSL = {spec.chemicalShiftList for spec in _createSpectra} - {None}
        _deleteSpectra = set(self.spectra) - set(_spectra)
        _createNmrAtoms = self._getNmrAtomsFromSpectra(_createSpectra)  # new nmrAtoms to add
        _deleteNmrAtoms = self._getNmrAtomsFromSpectra(_deleteSpectra)  # old nmrAtoms to update

        _thisNmrAtoms = self._getNmrAtoms()  # current nmrAtoms referenced in shiftLift

        # nmrAtoms with peakCount = 0 -> these are okay
        _oldNmrAtoms = {nmr for nmr in _thisNmrAtoms if self not in [pk.chemicalShiftList for pk in nmr.assignedPeaks]}
        _newNmrAtoms = _createNmrAtoms - _thisNmrAtoms  # _oldNmrAtoms <- this skips unassigned :|

        _nmrAtoms = _createNmrAtoms | _deleteNmrAtoms | _oldNmrAtoms  # do I need to do all these?
        nmrResidues = {nmr.nmrResidue for nmr in _nmrAtoms}
        shifts = {cs for nmrAt in _nmrAtoms for cs in nmrAt.chemicalShifts if cs and not cs.isDeleted}

        with undoBlock():
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=partial(self._recalculatePeakShifts, nmrResidues, shifts))

            self._wrappedData.experiments = {x._wrappedData.experiment for x in _spectra}

            # set the removed spectra to the default (first shiftList) in the project
            firstCSL = self.project.chemicalShiftLists[0]
            for spec in _deleteSpectra:
                spec.chemicalShiftList = firstCSL

            # update the chemicalShiftLists that are now empty
            self.static = not self.spectra
            for csl in _createCSL:
                csl.static = not csl.spectra
                if not csl.spectra:
                    for sh in csl.chemicalShifts:
                        sh._static = True

            for nmrAtom in _newNmrAtoms:
                self.newChemicalShift(nmrAtom=nmrAtom)

            self._recalculatePeakShifts(nmrResidues, shifts)
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=partial(self._recalculatePeakShifts, nmrResidues, shifts))

    def recalculatePeakShifts(self):
        """Recalculate the chemical shifts from any updated peak positions
        """
        self._recalculatePeakShifts(self._getNmrAtoms(), self.chemicalShifts)

    @staticmethod
    def _getNmrAtomsFromSpectra(spectra):
        """Get the list of nmrAtoms in the supplied spectra
        """
        return {nmrAtom
                for spec in spectra
                for pList in spec.peakLists if not pList.isSynthetic
                for pk in pList.peaks
                for aNmrAtoms in pk.assignedNmrAtoms
                for nmrAtom in aNmrAtoms
                } - {None}

    def _getNmrAtoms(self):
        """Get the list of nmrAtoms
        """
        try:
            _data = self._wrappedData.data
            _oldNmrAtoms = _data[_data[CS_ISDELETED] == False][CS_NMRATOM]
            _oldNmr = {self.project.getByPid(nmr) for nmr in _oldNmrAtoms} - {None}
        except Exception:
            # dataframe may not have been created yet
            _oldNmr = set()
        return _oldNmr

    def _getNmrAtomPids(self):
        """Get the list of nmrAtom pids
        """
        try:
            _data = self._wrappedData.data
            _oldNmrAtoms = _data[_data[CS_ISDELETED] == False][CS_NMRATOM]
            _oldNmr = set(_oldNmrAtoms) - {None}  # remove any Nones
        except Exception:
            # dataframe may not have been created yet
            _oldNmr = set()
        return _oldNmr

    @property
    def chemicalShifts(self):
        """Return the shifts belonging to ChemicalShiftList
        """
        return self._shifts

    def getChemicalShift(self, nmrAtom: Union[NmrAtom, str, None] = None, uniqueId: Union[int, None] = None,
                         _includeDeleted: bool = False):
        """Return a chemicalShift by nmrAtom or uniqueId
        Shift is returned as a namedTuple
        """
        if nmrAtom and uniqueId:
            raise ValueError(f'{self.className}.getChemicalShift: use either nmrAtom or uniqueId')

        _data = self._wrappedData.data
        if _data is None:
            return

        rows = None
        if nmrAtom:
            # get shift by nmrAtom
            nmrAtom = self.project.getByPid(nmrAtom) if isinstance(nmrAtom, str) else nmrAtom
            if not isinstance(nmrAtom, (NmrAtom, type(None))):
                raise ValueError(f'{self.className}.getChemicalShift: nmrAtom must be of type NmrAtom or str')
            if nmrAtom:
                # search dataframe
                rows = _data[_data[CS_NMRATOM] == nmrAtom.pid]

        elif uniqueId is not None:
            # get shift by uniqueId
            if not isinstance(uniqueId, int):
                raise ValueError(f'{self.className}.getChemicalShift: uniqueId must be an int')

            # search dataframe
            rows = _data[_data[CS_UNIQUEID] == uniqueId]

        if rows is not None:
            if len(rows) > 1:
                raise RuntimeError(f'{self.className}.getChemicalShift: bad number of shifts in list')
            if len(rows) == 1:
                uniqueId = rows.iloc[0].uniqueId
                _shs = [sh for sh in self._shifts if sh._uniqueId == uniqueId]
                if _shs and len(_shs) == 1:
                    return _shs[0]

                if _includeDeleted:
                    _shs = [sh for sh in self._deletedShifts if sh._uniqueId == uniqueId]
                    if _shs and len(_shs) == 1:
                        return _shs[0]

                raise ValueError(f'{self.className}.getChemicalShift: shift not found')

                # # this is marginally quicker
                # _s, _e = 0, len(self._shifts) - 1
                # _sh = None
                # while _s <= _e:
                #     _m = (_s + _e) // 2
                #     _sh = self._shifts[_m]
                #     if _sh._uniqueId == uniqueId:
                #         return _sh
                #     if _sh._uniqueId > uniqueId:
                #         _e = _m - 1
                #     else:
                #         _s = _m + 1
                #
                # raise ValueError(f'{self.className}.getChemicalShift: shift not found')

    #-----------------------------------------------------------------------------------------
    # property STUBS: hot-fixed later
    #-----------------------------------------------------------------------------------------

    @property
    def _oldChemicalShifts(self) -> list['_oldChemicalShift']:
        """STUB: hot-fixed later
        :return: a list of _oldChemicalShifts in the ChemicalShiftList
        """
        return []

    #-----------------------------------------------------------------------------------------
    # getter STUBS: hot-fixed later
    #-----------------------------------------------------------------------------------------

    def _getOldChemicalShift(self, relativeId: str) -> '_OldChemicalShift | None':
        """STUB: hot-fixed later
        :return: an instance of _OldChemicalShift, or None
        """
        return None

    # def get_OldChemicalShift(self, relativeId: str) -> '_OldChemicalShift | None':
    #     """STUB: hot-fixed later
    #     :return: an instance of _OldChemicalShift, or None
    #     """
    #     return None

    #-----------------------------------------------------------------------------------------
    # Core methods
    #-----------------------------------------------------------------------------------------

    @logCommand(get='self')
    def duplicate(self, includeSpectra=False, autoUpdate=False):
        """
        :param includeSpectra: move the spectra to the newly created ChemicalShiftList
        :param autoUpdate: automatically update according to the project changes.
        :return: a duplicated copy of itself containing all chemicalShifts.
        """
        from ccpn.core.ChemicalShift import _newChemicalShift as _newShift

        # name = _incrementObjectName(self.project, self._pluralLinkName, self.name)
        ncsl = self.project.newChemicalShiftList()

        # duplicate the chemicalShiftList dataframe - remove the deleted shifts (not required)
        # will copy the correct type if changed to _ChemicalShiftListFrame
        df = self._wrappedData.data.copy()
        df = df[df[CS_ISDELETED] == False]
        ncsl._wrappedData.data = df
        ncsl.static = True

        # make a new list of uniqueIds
        _newIds = [self.project._getNextUniqueIdValue(CS_CLASSNAME) for _ in range(len(df))]
        df[CS_UNIQUEID] = _newIds
        df.set_index(df[CS_UNIQUEID], inplace=True, )

        # create the new shift objects
        for ii in range(len(df)):
            _row = df.iloc[ii]

            # create a new shift with the uniqueId from the dataframe
            shift = _newShift(self.project, ncsl, _uniqueId=int(_row[CS_UNIQUEID]))
            shift._static = True
            ncsl._shifts.append(shift)

            # add the new object to the _pid2Obj dict
            self.project._finalisePid2Obj(shift, 'create')

            # add the shift to the nmrAtom
            shift._updateNmrAtomShifts()

        ncsl.autoUpdate = autoUpdate
        for att in ['unit', 'isSimulated', 'comment']:
            setattr(ncsl, att, getattr(self, att, None))

        # setting the spectra will autoUpdate as required
        ncsl.spectra = self.spectra if includeSpectra else ()
        # # old chemicalShifts
        # list(map(lambda cs: cs.copyTo(ncsl), self.chemicalShifts))

    @classmethod
    def _getAllWrappedData(cls, parent: Project) -> List[Nmr.ShiftList]:
        """get wrappedData (ShiftLists) for all ShiftList children of parent Project
        """
        return [x for x in parent._apiNmrProject.sortedMeasurementLists() if x.className == 'ShiftList']

    @renameObject()
    @logCommand(get='self')
    def rename(self, value: str):
        """Rename ChemicalShiftList, changing its name and Pid.
        """
        return self._rename(value)

    def _getByUniqueId(self, uniqueId):
        """Get the shift data from the dataFrame by the uniqueId
        """
        try:
            return self._data.loc[uniqueId]
        except Exception as es:
            raise ValueError(
                f'{self.className}._getByUniqueId: error getting row, uniqueId {uniqueId} in {self}  -  {es}') from None

    def _getAttribute(self, uniqueId, name, attribType):
        """Get the named attribute from the chemicalShift with supplied uniqueId

        Check the attribute for None, nan, inf, etc., and cast to attribType
        CCPN Internal - Pandas dataframe changes values after saving through api
        """
        try:
            _val = self._data.at[uniqueId, name]
            return None if (_val is None or (_val != _val)) else attribType(_val)
        except Exception as es:
            raise ValueError(
                f'{self.className}._getAttribute: error getting attribute {name} in {self}  -  {es}') from None

    def _setAttribute(self, uniqueId, name, value):
        """Set the attribute of the chemicalShift with the supplied uniqueId
        """
        try:
            self._data.at[uniqueId, name] = value
        except Exception as es:
            raise ValueError(
                f'{self.className}._setAttribute: error setting attribute {name} in {self}  -  {es}') from None

    def _getAttributes(self, uniqueId, startName, endName, attribTypes):
        """Get the named attributes from the chemicalShift with supplied uniqueId

        Check the attributes for None, nan, inf, etc., and cast to attribType
        CCPN Internal - Pandas dataframe changes values after saving through api
        """
        try:
            _val = self._data.loc[uniqueId, startName:endName]
            return tuple(None if (val is None or (val != val)) else attribType(val) for val, attribType in
                         zip(_val, attribTypes))

        except Exception as es:
            raise ValueError(
                f'{self.className}._getAttributes: error getting attributes {startName}|{endName} in {self}  -  {es}') from None

    def _setAttributes(self, uniqueId, startName, endName, value):
        """Set the attributes of the chemicalShift with the supplied uniqueId
        """
        try:
            self._data.loc[uniqueId, startName:endName] = value
        except Exception as es:
            raise ValueError(
                f'{self.className}._setAttributes: error setting attributes {startName}|{endName} in {self}  -  {es}') from None

    def _undoRedoShifts(self, shifts):
        """update the shifts after undo/redo
        shifts should be a simple, non-nested dict of int:<shift> pairs
        """
        # keep the same shift list
        self._shifts[:] = shifts

    def _undoRedoDeletedShifts(self, deletedShifts):
        """update to deleted shifts after undo/redo
        deletedShifts should be a simple, non-nested dict of int:<deletedShift> pairs
        """
        # keep the same deleted shift list
        self._deletedShifts[:] = deletedShifts

    @staticmethod
    def _setDeleted(shift, state):
        """Set the deleted state of the shift
        """
        shift._deleted = state

    @property
    def _data(self):
        """Helper method to get the stored dataframe
        CCPN Internal
        """
        return self._wrappedData.data

    def getAsDataFrame(self) -> pd.DataFrame:
        return self._data.copy(deep=True) if self._data is not None else None

    def _searchChemicalShifts(self, nmrAtom=None, uniqueId=None):
        """Return True if the nmrAtom/uniqueId already exists in the chemicalShifts dataframe
        """
        if nmrAtom and uniqueId:
            raise ValueError(f'{self.className}._searchChemicalShifts: use either nmrAtom or uniqueId')

        if (_data := self._wrappedData.data) is None:
            return

        if nmrAtom:
            # get shift by nmrAtom
            nmrAtom = self.project.getByPid(nmrAtom) if isinstance(nmrAtom, str) else nmrAtom
            if not isinstance(nmrAtom, NmrAtom):
                raise ValueError(f'{self.className}._searchChemicalShifts: nmrAtom must be of type NmrAtom, str')

            # search dataframe for single element
            return nmrAtom.pid in set(_data[CS_NMRATOM])

        elif uniqueId is not None:
            # get shift by uniqueId
            if not isinstance(uniqueId, int):
                raise ValueError(f'{self.className}._searchChemicalShifts: uniqueId must be an int - {uniqueId}')

            # search dataframe for single element
            return uniqueId in set(_data[CS_UNIQUEID])

    def delete(self):
        """Delete the chemicalShiftList and associated chemicalShifts
        """
        shifts = list(self._shifts)
        if len(self.project.chemicalShiftLists) < 2:
            raise RuntimeError(f'{self.className}.delete: cannot delete the last chemicalShiftList')

        with undoBlock():
            for sh in shifts:
                _oldShifts = self._shifts[:]
                _oldDeletedShifts = self._deletedShifts[:]

                self._shifts.remove(sh)
                self._deletedShifts.append(sh)  # not sorted - sort?

                _newShifts = self._shifts[:]
                _newDeletedShifts = self._deletedShifts[:]

                sh._deleteWrapper(self, _newDeletedShifts, _newShifts, _oldDeletedShifts, _oldShifts)

            # remember the old spectra for after the actual delete
            _deleteSpectra = self.spectra

            # delete the chemicalShiftList
            self._delete()

            # set the removed spectra to the default (first shiftList) in the project
            firstCSL = self.project.chemicalShiftLists[0]
            for spec in _deleteSpectra:
                spec.chemicalShiftList = firstCSL

    def _getDirectChildren(self):
        """Get list of all objects that have self as a parent
        Special case here, as children are V3-core objects
        """
        return self._shifts  # ignore deleted

    #-----------------------------------------------------------------------------------------
    # CCPN functions
    #-----------------------------------------------------------------------------------------

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Subclassed to allow for initialisations on restore, not on creation via newChemicalShiftList
        """
        from ccpn.util.Logging import getLogger
        from ccpn.core.ChemicalShift import _newChemicalShift as _newShift

        chemicalShiftList = super()._restoreObject(project, apiObj)

        # create a set of new shift objects linked to the pandas rows - discard deleted
        _data = chemicalShiftList._wrappedData.data

        if _data is not None:
            # check that is the new DataFrameABC class, update as required - for later use
            # if not isinstance(_data, DataFrameABC):
            #     getLogger().debug(f'updating classType {chemicalShiftList} -> _ChemicalShiftListFrame')
            #     _data = _ChemicalShiftListFrame(_data)

            # remove the deleted shifts, not needed after restore
            _data = _data[_data[CS_ISDELETED] == False]
            oldLen = len(_data)

            # drop any duplicates and merge back in the Nones which must be kept
            _data.reset_index(drop=True, inplace=True)
            _noDupes = _data.drop_duplicates(CS_NMRATOM).merge(_data[_data[CS_NMRATOM].isnull()], how='outer')
            _noDupes.sort_values(CS_UNIQUEID, inplace=True, )
            if len(_noDupes) != oldLen:
                # log a warning and update the dataFrame
                getLogger().warning(f'Duplicate nmrAtoms have been removed from {chemicalShiftList}')
                getLogger().debug(f'>>> Dropped rows\n{list(_data.drop(_noDupes.index)[CS_UNIQUEID])}')
                _data = _noDupes

            if CS_STATIC not in _data.columns:
                # add new static column if not defined
                _data.insert(CS_COLUMNS.index(CS_STATIC), CS_STATIC, False)
            _data.set_index(_data[CS_UNIQUEID], inplace=True, )  # drop=False)

            chemicalShiftList._wrappedData.data = _data

            for ii in range(len(_data)):
                _row = _data.iloc[ii]

                # create a new shift with the uniqueId from the old shift
                shift = _newShift(project, chemicalShiftList, _uniqueId=int(_row[CS_UNIQUEID]))
                chemicalShiftList._shifts.append(shift)

                # add the new object to the _pid2Obj dict
                project._finalisePid2Obj(shift, 'create')

                # restore the nmrAtom, etc., for the new shift
                shift._updateNmrAtomShifts()

            for sh in chemicalShiftList._shifts:
                # ensure that all shifts have the correct value/valueError when first loaded
                if sh.value is None:
                    sh._recalculateShiftValue()

        return chemicalShiftList

    #-----------------------------------------------------------------------------------------==
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #-----------------------------------------------------------------------------------------==

    @logCommand(get='self')
    def newChemicalShift(self,
                         value: float = None, valueError: float = None, figureOfMerit: float = 1.0,
                         static: bool = False,
                         nmrAtom: Union[NmrAtom, str, Pid, None] = None,
                         chainCode: str = None, sequenceCode: str = None, residueType: str = None, atomName: str = None,
                         comment: str = None
                         ):
        """Create new ChemicalShift within ChemicalShiftList.

        An nmrAtom can be attached to the shift as required.
        nmrAtom can be core object, Pid or pid string
        If attached (chainCode, sequenceCode, residueType, atomName) will be derived from the nmrAtom.pid
        If nmrAtom is not specified, (chainCode, sequenceCode, residueType, atomName) can be set as string values.
        A chemicalShift is not static by default (dynamic), i.e., its value will update when there are changes to the assigned peaks.

        See the ChemicalShift class for details.

        :param value: float shift value
        :param valueError: float
        :param figureOfMerit: float, default = 1.0
        :param static: bool, default = False
        :param nmrAtom: nmrAtom as object or pid, or None if not required
        :param chainCode:
        :param sequenceCode:
        :param residueType:
        :param atomName:
        :param comment: optional comment string
        :return: a new ChemicalShift tuple.
        """

        data = self._wrappedData.data
        if nmrAtom is not None:
            _nmrAtom = self.project.getByPid(nmrAtom) if isinstance(nmrAtom, str) else nmrAtom
            if _nmrAtom is None:
                raise ValueError(f'{self.className}.newChemicalShift: nmrAtom {_nmrAtom} not found')
            nmrAtom = _nmrAtom

        if data is not None and nmrAtom and nmrAtom.pid in list(data[CS_NMRATOM]):
            raise ValueError(f'{self.className}.newChemicalShift: nmrAtom {nmrAtom} already exists')

        return self._newChemicalShiftObject(data=data,
                                            value=value, valueError=valueError, figureOfMerit=figureOfMerit,
                                            static=static,
                                            nmrAtom=nmrAtom,
                                            chainCode=chainCode, sequenceCode=sequenceCode, residueType=residueType,
                                            atomName=atomName,
                                            comment=comment)

    @newV3Object()
    def _newChemicalShiftObject(self, data, value, valueError, figureOfMerit, static,
                                nmrAtom, chainCode, sequenceCode, residueType, atomName, comment):
        """Create a new pure V3 ChemicalShift object
        Method is wrapped with create/delete notifier
        """
        from ccpn.core.ChemicalShift import _getByTuple, _newChemicalShift as _newShift

        # make new tuple - verifies contents
        _nextUniqueId = self.project._getNextUniqueIdValue(CS_CLASSNAME)
        _row = _getByTuple(chemicalShiftList=self,
                           uniqueId=_nextUniqueId,
                           isDeleted=False,
                           static=static,
                           value=value, valueError=valueError, figureOfMerit=figureOfMerit,
                           nmrAtom=None,  # MUST be None here and set later
                           chainCode=chainCode, sequenceCode=sequenceCode,
                           residueType=residueType, atomName=atomName,
                           comment=comment)
        # add to dataframe - this is in undo stack and marked as modified
        # Note the "additional" tuple around _row; needed to match the shape as one row, 12 columns
        _dfRow = pd.DataFrame(data=(_row,), columns=list(CS_COLUMNS))

        if data is None or data.empty:
            # set as the new subclassed DataFrameABC
            _data = self._wrappedData.data = _dfRow  # _ChemicalShiftListFrame(_dfRow)
        else:
            # not particularly fast, but no alternative for now
            # _data = self._wrappedData.data = self._wrappedData.data.append(_dfRow)  # deprecated
            _data = self._wrappedData.data = pd.concat([self._wrappedData.data, _dfRow], axis=0, ignore_index=True)
        _data.set_index(_data[CS_UNIQUEID], inplace=True, )

        # create new shift object
        # new Shift only needs chemicalShiftList and uniqueId - properties are linked to dataframe
        shift = _newShift(self.project, self, _uniqueId=int(_nextUniqueId))
        if nmrAtom:
            # None above should ensure recalculation of shift values from assignments
            shift.nmrAtom = nmrAtom

        _oldShifts = self._shifts[:]
        self._shifts.append(shift)
        _newShifts = self._shifts[:]

        # add an undo/redo item to recover shifts
        with undoStackBlocking() as addUndoItem:
            addUndoItem(undo=partial(self._undoRedoShifts, _oldShifts),
                        redo=partial(self._undoRedoShifts, _newShifts))

        return shift

    @logCommand(get='self')
    def deleteChemicalShift(self, nmrAtom: Union[None, NmrAtom, str] = None, uniqueId: int = None):
        """Delete a chemicalShift by nmrAtom or uniqueId
        """
        if nmrAtom and uniqueId:
            raise ValueError(f'{self.className}.deleteChemicalShift: use either nmrAtom or uniqueId')

        if self._wrappedData.data is None:
            return

        if nmrAtom:
            # get shift by nmrAtom
            nmrAtom = self.project.getByPid(nmrAtom) if isinstance(nmrAtom, str) else nmrAtom
            if not isinstance(nmrAtom, NmrAtom):
                raise ValueError(f'{self.className}.deleteChemicalShift: nmrAtom must be of type NmrAtom, str')

            # search dataframe for single element
            _data = self._wrappedData.data
            rows = _data[_data[CS_NMRATOM] == nmrAtom.pid]
            if len(rows) > 1:
                raise RuntimeError(f'{self.className}.deleteChemicalShift: bad number of shifts in list')
            elif len(rows) == 0:
                raise ValueError(f'{self.className}.deleteChemicalShift: nmrAtom {nmrAtom.pid} not found')

        elif uniqueId is not None:
            # get shift by uniqueId
            if not isinstance(uniqueId, int):
                raise ValueError(f'{self.className}.deleteChemicalShift: uniqueId must be an int')

            # search dataframe for single element
            _data = self._wrappedData.data
            rows = _data[_data[CS_UNIQUEID] == uniqueId]
            if len(rows) > 1:
                raise RuntimeError(f'{self.className}.deleteChemicalShift: bad number of shifts in list')
            elif len(rows) == 0:
                raise ValueError(f'{self.className}.deleteChemicalShift: uniqueId {uniqueId} not found')

        else:
            return

        uniqueId = rows.iloc[0].uniqueId
        if (_shs := [sh for sh in self._shifts if sh._uniqueId == uniqueId]):
            # raise an error if there are any assigned peaks
            _val = _shs[0]
            if _val.assignedPeaks:
                raise ValueError(
                    f'{self.className}.deleteChemicalShift: cannot delete chemicalShift with assigned peaks')

            self._deleteChemicalShiftObject(rows)

    def _deleteChemicalShiftObject(self, rows):
        """Update the dataframe and handle notifiers
        """
        _oldShifts = self._shifts[:]
        _oldDeletedShifts = self._deletedShifts[:]

        uniqueId = rows.iloc[0].uniqueId
        _shs = [sh for sh in self._shifts if sh._uniqueId == uniqueId]
        _val = _shs[0]

        self._shifts.remove(_val)
        self._deletedShifts.append(_val)  # not sorted - sort?

        _newShifts = self._shifts[:]
        _newDeletedShifts = self._deletedShifts[:]

        _val._deleteWrapper(self, _newDeletedShifts, _newShifts, _oldDeletedShifts, _oldShifts)


#=========================================================================================
# Connections to parents:
#=========================================================================================

def getter(self: Spectrum) -> ChemicalShiftList:
    """Return the chemicalShiftList for the spectrum
    """
    return self._project._data2Obj.get(self._apiDataSource.experiment.shiftList)


@logCommand(get='self', isProperty=True)
def chemicalShiftList(self: Spectrum, chemicalShiftList: ChemicalShiftList):
    """Set the chemicalShiftList for the spectrum
    """
    _shiftList = self.getByPid(chemicalShiftList) if isinstance(chemicalShiftList, str) else chemicalShiftList
    if isinstance(_shiftList, ChemicalShiftList):
        # add the spectrum to the chemicalShiftList - undo handled in .spectra setter
        _shiftList.spectra = set(_shiftList.spectra) | {self}

    elif _shiftList is None:
        # # set the chemicalShiftList to None - undo handled in .spectra setter
        # _shiftList = self.chemicalShiftList
        # if _shiftList:
        #     _shiftList.spectra = set(_shiftList.spectra) - {self}
        raise ValueError(f'{self.__class__.__name__}.chemicalShiftList: cannot set to None')

    else:
        # Don't raise errors here or you crash-out a perfectly valid project/Nef from loading
        from ccpn.util.Logging import getLogger

        getLogger().warning(f'Could not set chemicalShiftList for Spectrum {self}. Invalid ChemicalShiftList.')


Spectrum.chemicalShiftList = property(getter, chemicalShiftList, None,
                                      "ccpn.ChemicalShiftList used for ccpn.Spectrum")
del chemicalShiftList


def getter(self: PeakList) -> ChemicalShiftList:
    """Return the chemicalShiftList for the peak
    """
    return self._project._data2Obj.get(self._wrappedData.shiftList)


@logCommand(get='self', isProperty=True)
def chemicalShiftList(self: PeakList, value: ChemicalShiftList):
    """Set the chemicalShiftList for the peak
    """
    value = self.getByPid(value) if isinstance(value, str) else value
    self._apiPeakList.shiftList = None if value is None else value._apiShiftList


PeakList.chemicalShiftList = property(getter, chemicalShiftList, None,
                                      "ChemicalShiftList associated with PeakList.")
del getter
del chemicalShiftList


#=========================================================================================

@newObject(ChemicalShiftList)
def _newChemicalShiftList(self: Project, name: str = None, unit: str = 'ppm', autoUpdate: bool = True,
                          isSimulated: bool = False, comment: str = None,
                          spectra=()) -> ChemicalShiftList:
    """Create new ChemicalShiftList.

    See the ChemicalShiftList class for details.

    :param name: name for the new chemicalShiftList
    :param unit: unit type as str, e.g. 'ppm'
    :param autoUpdate: True/False - automatically update chemicalShifts when assignments change
    :param isSimulated: True/False
    :param comment: optional user comment
    :return: a new ChemicalShiftList instance.
    """

    name = ChemicalShiftList._uniqueName(parent=self, name=name)

    # set up call parameters for new api-object
    dd = {'name'   : name, 'unit': unit, 'autoUpdate': autoUpdate, 'isSimulated': isSimulated,
          'details': comment}

    apiChemicalShiftList = self._wrappedData.newShiftList(**dd)
    result = self._data2Obj.get(apiChemicalShiftList)
    if result is None:
        raise RuntimeError('Unable to generate new ChemicalShiftList item')

    # instantiate a new empty dataframe
    df = pd.DataFrame(columns=list(CS_COLUMNS))
    df.set_index(df[CS_UNIQUEID], inplace=True, )

    # set as the new subclassed DataFrameABC
    apiChemicalShiftList.data = df  # _ChemicalShiftListFrame(df)

    # if spectra:
    #     # add the spectra to the new chemicalShiftList - moved outside newObject for now
    #     getByPid = self._project.getByPid
    #     if (spectra := list(filter(lambda sp: isinstance(sp, Spectrum),
    #                                map(lambda sp: getByPid(sp) if isinstance(sp, str) else sp, spectra)))):
    #         # add/transfer the spectra
    #         result.spectra = spectra
    #         # dd.update({'experiments': OrderedSet([spec._wrappedData.experiment for spec in spectra])})

    return result


def _getChemicalShiftList(self: Project, name: str = None, unit: str = 'ppm', autoUpdate: bool = True,
                          isSimulated: bool = False, comment: str = None,
                          spectra=()) -> ChemicalShiftList:
    """Create new ChemicalShiftList.

    See the ChemicalShiftList class for details.

    :param name:
    :param unit:
    :param autoUpdate:
    :param isSimulated:
    :param comment:
    :return: a new ChemicalShiftList instance.
    """

    if spectra:
        getByPid = self._project.getByPid
        spectra = [getByPid(x) if isinstance(x, str) else x for x in spectra]

    dd = {'name'   : name, 'unit': unit, 'autoUpdate': autoUpdate, 'isSimulated': isSimulated,
          'details': comment}
    if spectra:
        dd['experiments'] = OrderedSet([spec._wrappedData.experiment for spec in spectra])

    apiChemicalShiftList = self._wrappedData.getShiftList(**dd)
    return self._data2Obj.get(apiChemicalShiftList)


# Notifiers
className = Nmr.ShiftList._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (  # ('_finaliseApiRename', {}, className, 'setName'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'Spectrum')}, className, 'addExperiment'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'Spectrum')}, className,
             'removeExperiment'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'Spectrum')}, className, 'setExperiments'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'PeakList')}, className, 'addPeakList'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'PeakList')}, className, 'removePeakList'),
            ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'PeakList')}, className, 'setPeakLists'),
            )
        )
Project._apiNotifiers.append(('_modifiedLink', {'classNames': ('ChemicalShiftList', 'PeakList')},
                              Nmr.PeakList._metaclass.qualifiedName(), 'setSpecificShiftList')
                             )
className = Nmr.Experiment._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('ChemicalShiftList', 'Spectrum')}, className, 'setShiftList'),
         ('_modifiedLink', {'classNames': ('ChemicalShiftList', 'PeakList')}, className, 'setShiftList'),
         )
        )
