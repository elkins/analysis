"""
Module documentation here
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
__dateModified__ = "$dateModified: 2024-05-22 14:42:25 +0100 (Wed, May 22, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing

from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import ResonanceGroup as ApiResonanceGroup
from ccpnmodel.ccpncore.lib.Constants import defaultNmrChainCode
from ccpn.core.NmrChain import NmrChain
from ccpn.core.Project import Project
from ccpn.core.Residue import Residue
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core._implementation.AbsorbResonance import absorbResonance
from ccpn.core.lib import Pid
from ccpn.core.lib.ContextManagers import newObject, ccpNmrV3CoreSetter, \
    renameObject, undoBlock
from ccpn.util.Common import makeIterableList
from ccpn.util.decorators import logCommand
from ccpn.util.Logging import getLogger
from ccpn.util.DataEnum import DataEnum


# Value used for sorting with no offset - puts no_offset just before offset +0
SORT_NO_OFFSET = -0.1


class MoveToEnd(DataEnum):
    HEAD = 0, 'head'
    TAIL = 1, 'tail'


# ASSIGNEDPEAKSCHANGED = '_assignedPeaksChanged'


class NmrResidue(AbstractWrapperObject):
    """Nmr Residues are used for assignment. An NmrResidue within an assigned NmrChain is
    by definition assigned to the Residue with the same sequenceCode
    (if any). An NmrResidue is defined by its containing chain and sequenceCode, so you cannot have
    two NmrResidues with the same NmrChain and sequenceCode but different residueType.

    An NmrResidue created without a name will be given the name
    '@ij', where ij is the serial number of the NmrResidue. Names of this form are reserved.
    Setting the NmrResidue sequenceCode to None will revert to this default name.

    An NmrResidue can be defined by a sequential offset relative to another NmrResidue. E.g. the
    NmrResidue i-1 relative to NmrResidue @5.@185.ALA would be named @5.@185-1.VAL. Reassigning
    NR:@5.@185.ALA to NR:B.do1.ALA or NR:B.125.THR, would cause the offset NmrResidue
    to be reassigned to NR:B.do1-1.VAL or NR:B.125-1.VAL, respectively. Offsets can be any integer
    (including '+0').

    NmrResidues that are not offset can be linked into consecutive stretches by putting them
    into connected NmrChains (see NmrChain).


    NmrResidue objects behave in there different ways when sorted:

      - If they are assigned to a Residue they sort like the Residue, in sequential order
      - If they belong to a connected NmrChain, they sort by the order they appear in the NmrChain.
      - In other 4cases they sort by creation order.
      - Offset NmrResidues in all cases sort alongside their main NmrResidue, by offset.

    """

    #: Short class name, for PID.
    shortClassName = 'NR'
    # Attribute it necessary as subclasses must use superclass className
    className = 'NmrResidue'

    _parentClass = NmrChain

    #: Name of plural link to instances of class
    _pluralLinkName = 'nmrResidues'

    # the attribute name used by current
    _currentAttributeName = 'nmrResidues'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiResonanceGroup._metaclass.qualifiedName()

    # used in chemical shift mapping
    _delta = None
    _includeInDeltaShift = True  # default included in the calculation
    _estimatedKd = None
    _colour = None

    # Number of fields that comprise the object's pid; Used to get parent id's
    _numberOfIdFields = 2

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _apiResonanceGroup(self) -> ApiResonanceGroup:
        """ CCPN resonanceGroup matching Residue"""
        return self._wrappedData

    @property
    def sequenceCode(self) -> str:
        """Residue sequence code and id (e.g. '1', '127B', '\@157+1)
        Names of the form '\@ijk', '\@ijk+n', and '\@ijk-n' (where ijk and n are integers)
        are reserved and cannot be set. They are obtained by the deassign command."""
        return self._wrappedData.sequenceCode

    @sequenceCode.setter
    @logCommand(get='self', isProperty=True)
    def sequenceCode(self, value: str | None):
        """Sequence Code Setter.

            Note: This heavily relies on the rename function, changes to that function will
            need to be reflected here and in NmrResiduePopup.py
        """
        if self.residue:
            raise RuntimeError('Cannot change the sequenceCode of an assigned NmrResidue.')

        if self.sequenceCode != value:
            try:
                self.rename(sequenceCode=value, residueType=self.residueType)
            except ValueError as es:
                raise ValueError(es)
            except Exception as es:
                raise RuntimeError(f'Error changing the sequenceCode to {value}') from es

    @property
    def serial(self) -> int:
        """NmrResidue serial number - set at creation and unchangeable"""
        return self._wrappedData.serial

    @property
    def _key(self) -> str:
        """Residue local ID"""
        return Pid.createId(self.sequenceCode, self.residueType)

    @classmethod
    def _nextKey(cls):
        """Get the next available key from _serialDict
        Limited functionality but helps to get potential Pid of the next _wrapped object
        In this case Pid element is of the form '@<num>.<residueType>' but subject to change
        residueType will default to ''
        """
        from ccpn.framework.Application import getApplication

        _project = getApplication().project

        _metaName = cls._apiClassQualifiedName.split('.')[-1]
        _metaName = _metaName[0].lower() + _metaName[1:] + 's'
        _name = f'@{_project._wrappedData.topObject._serialDict[_metaName] + 1}'

        return Pid.createId(_name, '')

    @property
    def _ccpnSortKey(self) -> tuple:
        """Attibute used to sort objects.

        Normally this is set on __init__  (for speed) and reset by self._resetIds
        (which is called by the rename finaliser and by resetSerial).
         But NmrResidue sorting order changes cynamically depending on
         what other NmrResidues are iN the same NmrChain. So for this class
         we need to set it dynamically, as a property"""

        sortKey = self.nmrChain._ccpnSortKey[2:] + self._localCcpnSortKey
        idx = self._getClassIndex(self.className)
        result = (id(self._project), idx) + sortKey
        #
        return result

    @property
    def _localCcpnSortKey(self) -> typing.Tuple:
        """Local sorting key, in context of parent."""

        unassignedOffset = 1000000000

        obj = self._wrappedData
        offset = obj.relativeOffset

        if offset is None:
            # this is a main NmrResidue
            offset = SORT_NO_OFFSET
        else:
            # Offset NmrResidue - get sort key from main Nmr Residue
            # NBNB We can NOT rely on the main NmrResidue to be already initialised
            obj = obj.mainResonanceGroup

        apiNmrChain = obj.nmrChain
        if apiNmrChain.isConnected:
            result = (apiNmrChain.mainResonanceGroups.index(obj), '', offset)
        else:
            seqCode = obj.seqCode
            if seqCode is None:
                result = (unassignedOffset + obj.serial, obj.seqInsertCode or '', offset)
            else:
                result = (seqCode, obj.seqInsertCode or '', offset)

        # if offset is None:
        #   apiNmrChain = obj.nmrChain
        #   if apiNmrChain.isConnected:
        #     result = (apiNmrChain.mainResonanceGroups.index(obj), '', SORT_NO_OFFSET)
        #   else:
        #     # this is a main NmrResidue
        #     seqCode = obj.seqCode
        #     if seqCode is None:
        #       result = (Constants.POSINFINITY, '@%s' % obj.serial, SORT_NO_OFFSET)
        #     else:
        #       result = (seqCode, obj.seqInsertCode or '', SORT_NO_OFFSET)
        # else:
        #   result = self.mainNmrResidue._localCcpnSortKey[:-1]  + (offset,)
        #
        return result

    @property
    def _parent(self) -> NmrChain:
        """NmrChain containing NmrResidue. Use self.assignTo to reset the NmrChain"""
        return self._project._data2Obj[self._wrappedData.nmrChain]

    nmrChain = _parent

    @property
    def residueType(self) -> str:
        """Residue type string (e.g. 'ALA'). Part of id.
        """
        return self._wrappedData.residueType or ''

    @residueType.setter
    @logCommand(get='self', isProperty=True)
    def residueType(self, value: typing.Optional[str]):
        """residueType setter.

            Note: This heavily relies on the rename function, changes to that function will
            need to be reflected here and in NmrResiduePopup.py
        """
        if self.residue:
            raise RuntimeError('Cannot change the residueType of an assigned NmrResidue.')

        if self.residueType != value:
            try:
                self.rename(sequenceCode=self.sequenceCode, residueType=value)
            except ValueError as es:
                raise ValueError(es)
            except Exception as es:
                raise RuntimeError(f'Error changing the sequenceCode to {value}') from es

    @property
    def relativeOffset(self) -> typing.Optional[int]:
        """Sequential offset of NmrResidue relative to mainNmrResidue
        May be 0. Is None for residues that are not offset."""
        return self._wrappedData.relativeOffset

    @property
    def residue(self) -> Residue:
        """Residue to which NmrResidue is assigned"""
        return self._project.getResidue(self._id)

    # GWV 20181122: removed setters between Chain/NmrChain, Residue/NmrResidue, Atom/NmrAtom
    # @residue.setter
    # def residue(self, value:Residue):
    #   if value:
    #     tt = tuple((x or None) for x in value._id.split('.'))
    #     self.assignTo(chainCode=tt[0], sequenceCode=tt[1], residueType=tt[2])
    #   else:
    #     residueType = self.residueType
    #     if residueType:
    #       self.rename('.' + residueType)
    #     else:
    #       self.rename(None)

    @property
    def offsetNmrResidues(self) -> typing.Tuple['NmrResidue', ...]:
        """"All other NmrResidues with the same sequenceCode sorted by offSet suffix '-1', '+1', etc."""
        getDataObj = self._project._data2Obj.get
        return tuple(getDataObj(x) for x in self._wrappedData.offsetResonanceGroups)

    def getOffsetNmrResidue(self, offset: int) -> typing.Optional['NmrResidue']:
        """Get offset NmrResidue with indicated offset
        (or None, if no such offset NmrResidue exists"""
        for result in self.offsetNmrResidues:
            if result.relativeOffset == offset:
                return result
        #
        return None

    @property
    def mainNmrResidue(self) -> typing.Optional['NmrResidue']:
        """Main NmrResidue (self, or the residue that self is offset relative to"""
        return self._project._data2Obj.get(self._wrappedData.mainResonanceGroup)

    @property
    def nextNmrResidue(self) -> typing.Optional['NmrResidue']:
        """Next sequentially connected NmrResidue (or None, as appropriate).
        Either from a connected NmrChain,
        or the NmrResidue assigned to the next Residue in the same Chain"""

        apiResonanceGroup = self._wrappedData
        apiNmrChain = apiResonanceGroup.directNmrChain
        residue = self.residue

        result = None

        if apiNmrChain and apiNmrChain.isConnected:
            # Connected stretch
            stretch = apiNmrChain.mainResonanceGroups
            if apiResonanceGroup is stretch[-1]:
                result = None
            else:
                result = self._project._data2Obj.get(stretch[stretch.index(apiResonanceGroup) + 1])

        elif residue:
            # Assigned to residue
            nextResidue = residue.nextResidue
            if nextResidue:
                result = nextResidue.nmrResidue
        #
        return result

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def nmrAtoms(self) -> list['NmrAtom']:
        """STUB: hot-fixed later
        :return: a list of nmrAtoms in the NmrResidue
        """
        return []

    #=========================================================================================
    # getter STUBS: hot-fixed later
    #=========================================================================================

    def getNmrAtom(self, relativeId: str) -> 'NmrAtom | None':
        """STUB: hot-fixed later
        :return: an instance of NmrAtom, or None
        """
        return None

    #=========================================================================================
    # Core methods
    #=========================================================================================

    @logCommand(get='self')
    def connectNext(self, nmrResidue: typing.Union['NmrResidue', str]) -> NmrChain:
        """Connect free end of self to free end of next residue in sequence,
        and return resulting connected NmrChain

        Raises error if self is assigned, or if either self or value is offset.

        NB Undoing a connection between two connected stretches
        will get back a 'value' stretch with a new shortName"""
        apiResonanceGroup = self._wrappedData
        # apiResidue = apiResonanceGroup.assignedResidue
        apiNmrChain = apiResonanceGroup.directNmrChain

        project = self._project

        if nmrResidue is None:
            raise ValueError("Cannot connect to value: None")
        elif isinstance(nmrResidue, str):
            xx = project.getByPid(nmrResidue)
            if xx is None:
                raise ValueError("No object found matching Pid %s" % nmrResidue)
            else:
                nmrResidue = xx

        apiValueNmrChain = nmrResidue._wrappedData.nmrChain

        if self.relativeOffset is not None:
            raise ValueError("Cannot connect from offset residue")

        elif nmrResidue.relativeOffset is not None:
            raise ValueError("Cannot connect to offset NmrResidue")

        elif self.residue is not None:
            raise ValueError("Cannot connect assigned NmrResidue - assign the value instead")

        elif nmrResidue.residue is not None:
            raise ValueError("Cannot connect to assigned NmrResidue - assign the NmrResidue instead")

        elif self.nextNmrResidue is not None:
            raise ValueError("Cannot connect next NmrResidue - it is already connected")

        elif nmrResidue.previousNmrResidue is not None:
            raise ValueError("Cannot connect to next NmrResidue - it is already connected")

        elif apiNmrChain.isConnected and apiValueNmrChain is apiNmrChain:
            raise ValueError("Cannot make cyclical connected NmrChain")

        with undoBlock():
            if apiNmrChain.isConnected:

                # At this point, self must be the last NmrResidue in a connected chain
                if apiValueNmrChain.isConnected:
                    for rg in apiValueNmrChain.mainResonanceGroups:
                        rg.moveDirectNmrChain(apiNmrChain, 'tail')

                    # apiValueNmrChain.delete()

                    # need the V3 operator here for the undo/redo to fire correctly
                    V3nmrChain = self.project._data2Obj[apiValueNmrChain]
                    V3nmrChain.delete()

                else:
                    # [connected:NmrChain] -> [Value]
                    nmrResidue._wrappedData.moveDirectNmrChain(apiNmrChain, 'tail')
                result = self.nmrChain

            else:
                # self is unassigned, unconnected NmrResidue
                if apiValueNmrChain.isConnected:
                    # At this point value must be the first NmrResidue in a connected NmrChain

                    apiResonanceGroup.moveDirectNmrChain(apiValueNmrChain, 'head')

                else:
                    # [NmrChain] -> [Value]

                    # newApiNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)

                    # need the V3 operator here for the undo/redo to fire correctly
                    newV3nmrChain = self.project.newNmrChain(isConnected=True)
                    newApiNmrChain = newV3nmrChain._apiNmrChain

                    apiResonanceGroup.directNmrChain = newApiNmrChain
                    nmrResidue._wrappedData.directNmrChain = newApiNmrChain

                result = nmrResidue.nmrChain

        return result

    @logCommand(get='self')
    def deassignNmrChain(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._deassignNmrChain()
            else:
                getLogger().warning('Cannot deassign an unassigned chain')

    def _deassignNmrChain(self):
        # nmrList = self._getAllConnectedList()
        # if nmrList:
        #   if len(nmrList) > 1:
        #
        #     apiNmrChain = self._wrappedData.directNmrChain
        #     newNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)
        #
        #     for nmr in nmrList:
        #       nmr._wrappedData.directNmrChain = newNmrChain
        #       nmr.deassign()
        #   else:
        #     nmrList[0]._deassignSingle()

        nmrList = self._getAllConnectedList()

        if nmrList:
            if len(nmrList) > 1:
                # need the V3 operator here for the undo/redo to fire correctly
                newV3nmrChain = self.project.newNmrChain(isConnected=True)
                nmrList[0].moveToNmrChain(newV3nmrChain)

                for nmr in nmrList:
                    nmr.deassign()
                for i in range(len(nmrList) - 1):
                    nmrList[i].connectNext(nmrList[i + 1])
            else:
                nmrList[0]._deassignSingle()

        if not self.mainNmrResidue.previousNmrResidue:
            # a single residue so return to the default
            self._deassignSingle()
        return None

    @logCommand(get='self')
    def disconnectAll(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._disconnectAssignedAll(assigned=True)
            else:
                self._disconnectAssignedAll(assigned=False)

    def _disconnectAssignedAll(self, assigned=False):
        # disconnect all and return to the @- chain
        for nmr in self._getAllConnectedList():
            nmr._deassignSingle()

    @logCommand(get='self')
    def disconnectNext(self) -> typing.Optional['NmrChain']:
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                newNmrChain = self._disconnectAssignedNext()
            else:
                newNmrChain = self._disconnectNext()
            return newNmrChain

    def _disconnectAssignedNext(self) -> typing.Optional['NmrChain']:
        """Cut connected NmrChain after NmrResidue, creating new connected NmrChain if necessary"""
        nmrList = self._getNextConnectedList()

        if nmrList:
            if len(nmrList) > 1:
                for nmr in nmrList:
                    nmr.deassign()
                for i in range(len(nmrList) - 1):
                    nmrList[i].connectNext(nmrList[i + 1])
            else:
                nmrList[0]._deassignSingle()

        if not self.mainNmrResidue.previousNmrResidue:
            # a single residue so return to the default
            self._deassignSingle()
        return None

    def _disconnectNext(self) -> typing.Optional['NmrChain']:
        """Cut connected NmrChain after NmrResidue, creating new connected NmrChain if necessary
        Does nothing if nextNmrResidue is empty;
        Raises ValueError for assigned NmrResidues"""

        apiResonanceGroup = self._wrappedData
        apiNmrChain = apiResonanceGroup.directNmrChain
        defaultChain = apiNmrChain.nmrProject.findFirstNmrChain(code=defaultNmrChainCode)

        if apiNmrChain is None:
            # offset residue: no-op
            return

        elif self.residue is not None:
            # Assigned residue with successor residue - error
            raise ValueError("Assigned NmrResidue %s cannot be disconnected" % self)

        data2Obj = self._project._data2Obj
        if apiNmrChain.isConnected:
            # Connected stretch - break stretch, keeping first half in the NmrChain
            stretch = apiNmrChain.mainResonanceGroups

            if apiResonanceGroup is stretch[-1]:  # nothing to disconnect on the right
                return

            if apiResonanceGroup is stretch[0]:  # first in the chain
                # chop off end ResonanceGroup
                if len(stretch) <= 2:
                    # Chain gets removed

                    for resonanceGroup in reversed(stretch):
                        resonanceGroup.directNmrChain = defaultChain
                    # delete empty chain

                    # apiNmrChain.delete()

                    # need the V3 operator here for the undo/redo to fire correctly
                    V3nmrChain = self.project._data2Obj[apiNmrChain]
                    V3nmrChain.delete()

                else:

                    apiResonanceGroup.moveDirectNmrChain(defaultChain, 'head')

                    # newNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)
                    # for rg in reversed(stretch):
                    #   if rg is apiResonanceGroup:
                    #     break
                    #   else:
                    #     rg.moveDirectNmrChain(newNmrChain, 'head')
                    # apiResonanceGroup.directNmrChain = defaultChain
                    # apiNmrChain.delete()

            elif apiResonanceGroup is stretch[-2]:
                # chop off end ResonanceGroup
                stretch[-1].directNmrChain = defaultChain

            else:
                # make new connected NmrChain with rightmost ResonanceGroups
                # newNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)

                # need the V3 operator here for the undo/redo to fire correctly
                newV3nmrChain = self.project.newNmrChain(isConnected=True)
                newNmrChain = newV3nmrChain._apiNmrChain

                for rg in reversed(stretch):
                    if rg is apiResonanceGroup:
                        break
                    else:
                        rg.moveDirectNmrChain(newNmrChain, 'head')

                return newNmrChain  # need this when using disconnectPrevious

    @property
    def previousNmrResidue(self) -> typing.Optional['NmrResidue']:
        """Previous sequentially connected NmrResidue (or None, as appropriate).
        Either from a connected NmrChain,
        or the NmrResidue assigned to the previous Residue in the same Chain"""
        apiResonanceGroup = self._wrappedData
        apiNmrChain = apiResonanceGroup.directNmrChain
        residue = self.residue

        result = None

        if apiNmrChain and apiNmrChain.isConnected:
            # Connected stretch
            stretch = apiNmrChain.mainResonanceGroups
            if apiResonanceGroup is stretch[0]:
                result = None
            else:
                result = self._project._data2Obj.get(stretch[stretch.index(apiResonanceGroup) - 1])

        elif residue:
            # Assigned to residue
            previousResidue = residue.previousResidue
            if previousResidue:
                result = previousResidue.nmrResidue

        return result

    @logCommand(get='self')
    def connectPrevious(self, nmrResidue=None) -> NmrChain:
        """Connect free end of self to free end of previous residue in sequence,
        and return resulting connected NmrChain

        Raises error if self is assigned, or if either self or value is offset.

        NB Undoing a connection between two connected stretches
        will get back a 'value' stretch with a new shortName"""

        apiResonanceGroup = self._wrappedData
        # apiResidue = apiResonanceGroup.assignedResidue
        apiNmrChain = apiResonanceGroup.directNmrChain

        project = self._project

        if nmrResidue is None:
            raise ValueError("Cannot connect to value: None")

        elif isinstance(nmrResidue, str):
            xx = project.getByPid(nmrResidue)
            if xx is None:
                raise ValueError("No object found matching Pid %s" % nmrResidue)
            else:
                nmrResidue = xx

        apiValueNmrChain = nmrResidue._wrappedData.nmrChain

        if self.relativeOffset is not None:
            raise ValueError("Cannot connect from offset residue")

        elif nmrResidue.relativeOffset is not None:
            raise ValueError("Cannot connect to offset NmrResidue")

        elif self.residue is not None:
            raise ValueError("Cannot connect assigned NmrResidue - assign the value instead")

        elif nmrResidue.residue is not None:
            raise ValueError("Cannot connect to assigned NmrResidue - assign the NmrResidue instead")

        elif self.previousNmrResidue is not None:
            raise ValueError("Cannot connect previous NmrResidue - it is already connected")

        elif nmrResidue.nextNmrResidue is not None:
            raise ValueError("Cannot connect to previous NmrResidue - it is already connected")

        elif apiNmrChain.isConnected and apiValueNmrChain is apiNmrChain:
            raise ValueError("Cannot make cyclical connected NmrChain")

        with undoBlock():
            if apiNmrChain.isConnected:
                # At this point, self must be the first NmrResidue in a connected chain
                undo = apiValueNmrChain.root._undo
                try:

                    ll = apiNmrChain.__dict__['mainResonanceGroups']
                    if apiValueNmrChain.isConnected:
                        for rg in reversed(apiValueNmrChain.mainResonanceGroups):
                            rg.moveDirectNmrChain(apiNmrChain, 'head')

                        # apiValueNmrChain.delete()

                        # need the V3 operator here for the undo/redo to fire correctly
                        V3nmrChain = self.project._data2Obj[apiValueNmrChain]
                        V3nmrChain.delete()

                    else:
                        nmrResidue._wrappedData.moveDirectNmrChain(apiNmrChain, 'head')

                finally:
                    result = self.nmrChain

            else:
                # self is unassigned, unconnected NmrResidue
                if apiValueNmrChain.isConnected:
                    # At this point value must be the last NmrResidue in a connected NmrChain

                    # [connected:Value] <- [NmrChain]
                    apiResonanceGroup.moveDirectNmrChain(apiValueNmrChain, 'tail')
                else:

                    # [Value] <- [NmrChain]
                    # newApiNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)

                    # need the V3 operator here for the undo/redo to fire correctly
                    newV3nmrChain = self.project.newNmrChain(isConnected=True)
                    newApiNmrChain = newV3nmrChain._apiNmrChain

                    nmrResidue._wrappedData.directNmrChain = newApiNmrChain
                    # newApiNmrChain.__dict__['mainResonanceGroups'].reverse()
                    apiResonanceGroup.directNmrChain = newApiNmrChain
                    # apiResonanceGroup.moveToNmrChain(newApiNmrChain)

                result = nmrResidue.nmrChain

        return result

    # def _bubbleHead(self, ll):
    #     ll.insert(0, ll.pop())

    # def _bubbleTail(self, ll):
    #     ll.append(ll.pop(0))

    @logCommand(get='self')
    def unlinkPreviousNmrResidue(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._disconnectAssignedPrevious()

    @logCommand(get='self')
    def unlinkNextNmrResidue(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._disconnectAssignedNext()

    @logCommand(get='self')
    def disconnectPrevious(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._disconnectAssignedPrevious()
            else:
                self._disconnectPrevious()

    def _disconnectAssignedPrevious(self) -> typing.Optional['NmrChain']:
        """Cut connected NmrChain after NmrResidue, creating new connected NmrChain if necessary"""
        nmrList = self._getPreviousConnectedList()

        if nmrList:
            if len(nmrList) > 1:
                for nmr in nmrList:
                    nmr.deassign()
                for i in range(len(nmrList) - 1):
                    nmrList[i].connectNext(nmrList[i + 1])
            else:
                nmrList[0]._deassignSingle()

        if not self.mainNmrResidue.nextNmrResidue:
            # a single residue so return to the default
            self._deassignSingle()

        return None

    def _disconnectPrevious(self):
        """Cut connected NmrChain before NmrResidue, creating new connected NmrChain if necessary
        Does nothing if previousNmrResidue is empty;
        Raises ValueError for assigned NmrResidues
        """

        apiResonanceGroup = self._wrappedData
        apiNmrChain = apiResonanceGroup.directNmrChain
        defaultChain = apiNmrChain.nmrProject.findFirstNmrChain(code=defaultNmrChainCode)

        if apiNmrChain is None:
            # offset residue: no-op
            return

        elif self.residue is not None:
            # Assigned residue with successor residue - error
            raise ValueError("Assigned NmrResidue %s cannot be disconnected" % self)

        elif apiNmrChain.isConnected:
            # Connected stretch - break stretch, keeping first half in the NmrChain
            stretch = apiNmrChain.mainResonanceGroups

            if apiResonanceGroup is stretch[0]:  # first in the chain
                return

            if apiResonanceGroup is stretch[-1]:  # last in the chain
                # chop off end ResonanceGroup
                if len(stretch) <= 2:
                    # Chain gets removed

                    for resonanceGroup in reversed(stretch):
                        resonanceGroup.directNmrChain = defaultChain

                    # delete empty chain
                    # apiNmrChain.delete()

                    # need the V3 operator here for the undo/redo to fire correctly
                    V3nmrChain = self.project._data2Obj[apiNmrChain]
                    V3nmrChain.delete()

                else:

                    apiResonanceGroup.moveDirectNmrChain(defaultChain, 'tail')

                    # newNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)
                    # for rg in stretch:
                    #   if rg is apiResonanceGroup:
                    #     break
                    #   else:
                    #     rg.moveDirectNmrChain(newNmrChain, 'tail')
                    # apiResonanceGroup.directNmrChain = defaultChain
                    # apiNmrChain.delete()

            elif apiResonanceGroup is stretch[1]:
                # chop off end ResonanceGroup
                stretch[0].moveDirectNmrChain(defaultChain, 'head')

            else:
                # make new connected NmrChain with rightmost ResonanceGroups
                # newNmrChain = apiNmrChain.nmrProject.newNmrChain(isConnected=True)

                # need the V3 operator here for the undo/redo to fire correctly
                newV3nmrChain = self.project.newNmrChain(isConnected=True)
                newNmrChain = newV3nmrChain._apiNmrChain

                for rg in stretch:
                    if rg is apiResonanceGroup:
                        break
                    else:
                        rg.moveDirectNmrChain(newNmrChain, 'tail')

                return newNmrChain

    @logCommand(get='self')
    def disconnect(self):
        with undoBlock():
            if self.residue is not None:  # assigned to chain
                self._disconnectAssigned()
            else:
                self._disconnect()

    def _deassignSingle(self):
        # disconnect a single residue - return to @- chain
        # apiResonanceGroup = nmrResidue._wrappedData
        # apiNmrChain = apiResonanceGroup.directNmrChain
        # defaultChain = apiNmrChain.nmrProject.findFirstNmrChain(code=defaultNmrChainCode)
        #
        # if apiNmrChain:
        #   apiResonanceGroup.directNmrChain = defaultChain
        #   nmrResidue.deassign()
        self.moveToNmrChain()
        self.deassign()

    def _getPreviousConnectedList(self):
        # generate a list of the previous connected nmrResidues
        nmrListPrevious = []
        nmr = self.mainNmrResidue
        while nmr.previousNmrResidue:
            nmr = nmr.previousNmrResidue
            nmrListPrevious.insert(0, nmr)
        return nmrListPrevious

    def _getNextConnectedList(self):
        # generate a list of the next connected nmrResidues
        nmrListNext = []
        nmr = self.mainNmrResidue
        while nmr.nextNmrResidue:
            nmr = nmr.nextNmrResidue
            nmrListNext.append(nmr)
        return nmrListNext

    def _getAllConnectedList(self):
        # generate a list of all the connected nmrResidues
        nmrList = []
        nmr = self.mainNmrResidue
        while nmr.previousNmrResidue:
            nmr = nmr.previousNmrResidue
        while nmr:
            nmrList.append(nmr)
            nmr = nmr.nextNmrResidue
        return nmrList

    def _disconnectAssigned(self):
        nmrListPrev = self._getPreviousConnectedList()
        nmrListNext = self._getNextConnectedList()
        self._deassignSingle()
        if len(nmrListPrev) == 1:
            nmrListPrev[0]._deassignSingle()
        if len(nmrListNext) == 1:
            nmrListNext[0]._deassignSingle()

    def _disconnect(self):
        """Move NmrResidue from connected NmrChain to default chain,
        creating new connected NmrChains as necessary"""
        apiResonanceGroup = self._wrappedData
        apiNmrChain = apiResonanceGroup.directNmrChain
        if not apiNmrChain:
            raise ValueError("Offset NmrResidue %s cannot be disconnected" % self)

        defaultChain = apiNmrChain.nmrProject.findFirstNmrChain(code=defaultNmrChainCode)

        if apiNmrChain is None:
            # offset residue: no-op
            return

        elif self.residue is not None:
            # Assigned residue with successor residue - error
            raise ValueError("Assigned NmrResidue %s cannot be disconnected" % self)

        elif apiNmrChain.isConnected:
            # Connected stretch - break stretch, keeping first half in the NmrChain
            stretch = apiNmrChain.mainResonanceGroups

            if len(stretch) < 3 or (len(stretch) == 3 and apiResonanceGroup is stretch[1]):
                for rg in reversed(stretch):
                    # reversed to add residues back in proper order (they are added to end)
                    rg.directNmrChain = defaultChain

                # apiNmrChain.delete()

                # need the V3 operator here for the undo/redo to fire correctly
                V3nmrChain = self.project._data2Obj[apiNmrChain]
                V3nmrChain.delete()

            else:
                index = stretch.index(apiResonanceGroup)
                data2Obj = self._project._data2Obj

                # NB operations are carefully selected to make sure they undo correctly
                if apiResonanceGroup is stretch[-1]:
                    apiResonanceGroup.directNmrChain = defaultChain

                elif apiResonanceGroup is stretch[-2]:
                    stretch[-1].directNmrChain = defaultChain
                    apiResonanceGroup.directNmrChain = defaultChain

                elif index == 0:
                    data2Obj[stretch[1]]._disconnectPrevious()

                elif index == 1:
                    nmrChain = self.nmrChain
                    nr1 = data2Obj[stretch[1]]
                    nr2 = data2Obj[stretch[2]]

                    nr1._disconnectPrevious()
                    nr2._disconnectPrevious()

                else:
                    self._disconnectNext()
                    apiResonanceGroup.directNmrChain = defaultChain

    @property
    def probableResidues(self) -> typing.Tuple[typing.Tuple[Residue, float], ...]:
        """tuple of (residue, probability) tuples for probable residue assignments
        sorted by decreasing probability. Probabilities are normalised to 1"""
        getDataObj = self._project._data2Obj.get
        ll = sorted((x.weight, x.possibility) for x in self._wrappedData.residueProbs)
        totalWeight = sum(tt[0] for tt in ll) or 1.0  # If sum is zero give raw weights
        return tuple((getDataObj(tt[1]), tt[0] / totalWeight) for tt in reversed(ll))

    @probableResidues.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def probableResidues(self, value):
        apiResonanceGroup = self._wrappedData
        for residueProb in apiResonanceGroup.residueProbs:
            residueProb.delete()
        for residue, weight in value:
            apiResonanceGroup.newResidueProb(possibility=residue._wrappedData, weight=weight)

    @property
    def probableResidueTypes(self) -> typing.Tuple[typing.Tuple[str, float]]:
        """tuple of (residueType, probability) tuples for probable residue types
        sorted by decreasing probability"""
        ll = sorted((x.weight, x.possibility) for x in self._wrappedData.residueTypeProbs)
        totalWeight = sum(tt[0] for tt in ll) or 1.0  # If sum is zero give raw weights
        return tuple((tt[1].code3Letter, tt[0] / totalWeight) for tt in reversed(ll))

    @probableResidueTypes.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def probableResidueTypes(self, value):
        apiResonanceGroup = self._wrappedData
        root = apiResonanceGroup.root
        for residueTypeProb in apiResonanceGroup.residueTypeProbs:
            residueTypeProb.delete()
        for weight, residueType in value:
            chemComp = root.findFirstChemComp(code3Letter=residueType)
            if chemComp is None:
                # print("Residue type %s not recognised - skipping" % residueType)
                getLogger().warning("Residue type %s not recognised - skipping" % residueType)
            else:
                apiResonanceGroup.newResidueTypeProb(chemComp=chemComp, weight=weight)

    @logCommand(get='self')
    def deassign(self):
        """Reset sequenceCode and residueType assignment to default values"""
        # with undoBlock():
        #     apiResonanceGroup = self._apiResonanceGroup
        #     apiResonanceGroup.sequenceCode = None
        #     apiResonanceGroup.resetResidueType(None)
        self.rename()

    def moveToEnd(self, end: typing.Union[int, MoveToEnd] = MoveToEnd.TAIL):
        """Move an nmrResidue from one end of a connected chain to the other.
        """
        if not self.nmrChain.isConnected:
            raise RuntimeError(f'{self} does not belong to a connected nmrChain.')
        if not isinstance(end, (int, MoveToEnd)):
            raise TypeError(f'end must be of type {MoveToEnd.__class__.__name__} or int {list(MoveToEnd.values())}')
        if isinstance(end, int):
            if end not in MoveToEnd.values():
                raise TypeError(f'end must be of type {MoveToEnd.__class__.__name__} or int {list(MoveToEnd.values())}')

            # change to the enum-type for later
            end = MoveToEnd(end)

        nmrs = self.nmrChain.mainNmrResidues
        ind = nmrs.index(self.mainNmrResidue)

        if end == MoveToEnd.HEAD and ind != len(nmrs) - 1:
            raise RuntimeError(f'{self} is not at the end of a connected nmrChain.')
        elif end == MoveToEnd.TAIL and ind != 0:
            raise RuntimeError(f'{self} is not at the head of a connected nmrChain.')

        with undoBlock():
            self._wrappedData.moveDirectNmrChain(self.nmrChain._wrappedData, end.description)

    @logCommand(get='self')
    def moveToNmrChain(self, newNmrChain: typing.Union['NmrChain', str] = 'NC:@-', sequenceCode: str = None,
                       residueType: str = None):
        """Move residue to newNmrChain, breaking connected NmrChain if necessary.
        Optionally rename residue using sequenceCode and residueType

        newNmrChain default resets to NmrChain '@-'
        Routine is illegal for offset NmrResidues, use the main nmrResidue instead

        Routine will fail if current sequenceCode,residueType already exists in newNmrChain, as the nmrResidue is first moved
        then renamed; consider moving to temporary chain first.
        """

        apiResonanceGroup = self._apiResonanceGroup
        if apiResonanceGroup.relativeOffset is not None:
            raise ValueError("Cannot reset NmrChain for offset NmrResidue %s" % self.id)

        # optionally get newNmrChain from str object
        if isinstance(newNmrChain, str):
            nChain = self._project.getByPid(newNmrChain)
            if nChain is None:
                raise ValueError('Invalid newNmrChain "%s"' % newNmrChain)
            newNmrChain = nChain

        nmrChain = self.nmrChain

        with undoBlock():
            try:
                # if needed: move self to newNmrChain
                movedChain = False
                if newNmrChain != nmrChain:
                    apiResonanceGroup.moveToNmrChain(newNmrChain._wrappedData)
                    movedChain = True

                # optionally rename
                if self.sequenceCode != sequenceCode or self.residueType != residueType:
                    if sequenceCode is None:
                        sequenceCode = self.sequenceCode
                    if residueType is None:
                        residueType = self.residueType
                    self.rename(sequenceCode, residueType)

            except Exception as es:
                getLogger().warning(str(es))
                if movedChain:
                    # Need to undo this
                    apiResonanceGroup.moveToNmrChain(nmrChain._wrappedData)
                raise es

    @logCommand(get='self')
    def assignTo(self, chainCode: str = None, sequenceCode: typing.Union[int, str] = None,
                 residueType: str = None, mergeToExisting: bool = False) -> 'NmrResidue':

        """Assign NmrResidue to new assignment, as defined by the naming parameters
        and return the result.

        Empty parameters (e.g. chainCode=None) retain the previous value. E.g.:
        for NmrResidue NR:A.121.ALA
        calling with sequenceCode=123 will reassign to 'A.123.ALA'.

        If no assignment with the same chainCode and sequenceCode exists, the current NmrResidue
        will be reassigned.
        If an NmrResidue with the same chainCode and sequenceCode already exists, the function
        will either raise ValueError. If mergeToExisting is set to True, it will instead merge the
        two NmrResidues, delete the current one, and return the new one .
        NB Merging is NOT undoable.
        WARNING: When calling with mergeToExisting=True, always use in the form "x = x.assignTo(...)",
        as the call 'x.assignTo(...) may cause the source x object to become deleted.

        NB resetting the NmrChain for an NmrResidue in the middle of a connected NmrChain
        will cause an error. Use moveToNmrChain(newNmrChainOrPid) instead
        """

        # oldPid = self.longPid
        # clearUndo = False
        # undo = apiResonanceGroup.root._undo

        # check parameters
        sequenceCode = str(sequenceCode) if sequenceCode else None
        # apiResonanceGroup = self._apiResonanceGroup

        # oldNmrChain =  apiResonanceGroup.nmrChain
        # oldSequenceCode = apiResonanceGroup.sequenceCode
        # oldResidueType = apiResonanceGroup.residueType

        # Check for illegal separators in input values
        for ss in (chainCode, sequenceCode, residueType):
            if ss and Pid.altCharacter in ss:
                raise ValueError("Character %s not allowed in ccpn.NmrResidue id: %s.%s.%s" %
                                 (Pid.altCharacter, chainCode, sequenceCode, residueType))

        # Keep old values to go back to previous state
        oldChainCode, oldSequenceCode, oldResidueType = self._id.split('.')
        oldResidueType = oldResidueType or None

        # set missing parameters to existing or default values
        chainCode = chainCode or oldChainCode
        sequenceCode = sequenceCode or oldSequenceCode
        residueType = residueType or oldResidueType

        with undoBlock():
            apiResonanceGroup = self._wrappedData

            partialId = '%s.%s.' % (chainCode, sequenceCode)
            ll = self._project.getObjectsByPartialId(className='NmrResidue', idStartsWith=partialId)
            if ll:
                # There can only ever be one match
                result = ll[0]
            else:
                result = None

            if result is self:
                # We are reassigning to self - either a no-op or resetting the residueType
                result = self
                if residueType and self.residueType != residueType:
                    apiResonanceGroup.resetResidueType(residueType)

            elif result is None:
                # we are moving to new, free assignment
                result = self
                newNmrChain = self._project.fetchNmrChain(chainCode)

                try:
                    # NB Complex resetting sequence necessary
                    # in case we are setting an offset and illegal sequenceCode
                    # apiResonanceGroup.sequenceCode = None  # To guarantee against clashes
                    self.rename(None, residueType)
                    apiResonanceGroup.directNmrChain = newNmrChain._apiNmrChain  # Only directNmrChain is settable
                    # # Now we can (re)set - will throw error for e.g. illegal offset values
                    # apiResonanceGroup.sequenceCode = sequenceCode
                    # if residueType:
                    #     apiResonanceGroup.resetResidueType(residueType)
                    self.rename(sequenceCode, residueType)

                except:
                    # apiResonanceGroup.resetResidueType(oldResidueType)
                    # apiResonanceGroup.sequenceCode = None
                    self.rename(None, oldResidueType)
                    apiResonanceGroup.directNmrChain = apiResonanceGroup.nmrProject.findFirstNmrChain(
                            code=oldChainCode
                            )
                    # apiResonanceGroup.sequenceCode = oldSequenceCode
                    self.rename(oldSequenceCode, oldResidueType)
                    self._project._logger.error("Attempt to set illegal or inconsistent assignment: %s.%s.%s"
                                                % (chainCode, sequenceCode, residueType) + "\n  Reset to original state"
                                                )
                    raise

            else:
                #We are assigning to an existing NmrResidue
                if not mergeToExisting:
                    raise ValueError("New assignment clash with existing assignment,"
                                     " and merging is disallowed")

                newApiResonanceGroup = result._wrappedData

                if not residueType or result.residueType == residueType:

                    # Move or merge the NmrAtoms across and delete the current NmrResidue
                    for resonance in apiResonanceGroup.resonances:
                        newResonance = newApiResonanceGroup.findFirstResonance(implName=resonance.name)
                        if newResonance is None:
                            resonance.resonanceGroup = newApiResonanceGroup
                        else:
                            _res = self._project._data2Obj.get(resonance)
                            _newRes = self._project._data2Obj.get(newResonance)
                            if not (_res and _newRes):
                                raise RuntimeError('Cannot find associated v3 resonances')
                            absorbResonance(_newRes, _res)

                    apiResonanceGroup.delete()

                else:
                    # We cannot reassign if it involves changing residueType on an existing NmrResidue
                    raise ValueError("Cannot assign to %s.%s.%s: NR:%s.%s.%s already exists"
                                     % (chainCode, sequenceCode, residueType,
                                        chainCode, sequenceCode, result.residueType))

        return result

    @logCommand(get='self')
    def mergeNmrResidues(self, nmrResidues: typing.Sequence['NmrResidue']):
        nmrResidues = makeIterableList(nmrResidues)
        nmrResidues = [self.project.getByPid(nmrResidue) if isinstance(nmrResidue, str) else nmrResidue
                       for nmrResidue in nmrResidues]
        if not all(isinstance(nmrResidue, NmrResidue) for nmrResidue in nmrResidues):
            raise TypeError('nmrResidues can only contain items of type NmrResidue')
        if self in nmrResidues:
            raise TypeError('nmrResidue cannot be merged with itself')

        with undoBlock():
            apiResonanceGroup = self._wrappedData

            for nmrResidue in nmrResidues:
                for nmrAtom in nmrResidue.nmrAtoms:
                    existingNmrAtom = self.getNmrAtom(nmrAtom.name)
                    if existingNmrAtom is None:
                        # move resonance
                        resonance = nmrAtom._wrappedData
                        resonance.resonanceGroup = apiResonanceGroup
                    else:
                        absorbResonance(existingNmrAtom, nmrAtom)

                nmrResidue.delete()

    # def _rebuildAssignedChains(self):
    #   self._startCommandEchoBlock('_rebuildAssignedChains')
    #   try:
    #     assignedChain = self._project.fetchNmrChain('A')
    #     while assignedChain.nmrResidues:
    #       startNmrResidue = assignedChain.nmrResidues[0].mainNmrResidue
    #       startNmrResidue._deassignNmrChain()
    #       startNmrResidue.nmrChain.reverse()
    #
    #   except Exception as es:
    #     getLogger().warning(str(es))
    #   finally:
    #     self._endCommandEchoBlock()

    def delete(self):
        """Delete routine to check whether the item can be deleted otherwise raise api error.
        """
        try:
            # fetching the api tree will raise api errors for those objects that cannot be deleted/modified
            # and skip the actual delete
            self._getApiObjectTree()

            # need to do a special delete here as the api always reinserts the nmrResidue at the end of the chain
            self._delete()

        except Exception as es:
            raise es

    @renameObject()
    @logCommand(get='self')
    def rename(self, sequenceCode: str = None, residueType: str = None):
        """Rename NmrResidue. changing its sequenceCode and residueType.

        Specifying None for the sequenceCode will reset the nmrResidue to its canonical form, '@<serial>."""

        apiResonanceGroup = self._apiResonanceGroup
        self._validateStringValue('sequenceCode', sequenceCode, allowNone=True)
        self._validateStringValue('residueType', residueType, allowNone=True, allowEmpty=True)
        sequenceCode = sequenceCode or None
        residueType = residueType or None

        if sequenceCode:
            # Check if name is not already used
            partialId = '%s.%s.' % (self._parent._id, sequenceCode.translate(Pid.remapSeparators))
            ll = self._project.getObjectsByPartialId(className=self.className, idStartsWith=partialId)
            if ll and ll != [self]:
                raise ValueError(
                    f'Cannot rename {self} to {self.nmrChain.id}.{sequenceCode}.{residueType or ""} - assignment already exists')

        oldSequenceCode = apiResonanceGroup.sequenceCode
        oldResidueType = apiResonanceGroup.residueType
        # self._oldPid = self.pid

        # rename functions from here - both values are always changed
        apiResonanceGroup.sequenceCode = sequenceCode
        apiResonanceGroup.resetResidueType(residueType)

        # now handled by _finaliseAction
        # self._renameChildren()

        return (oldSequenceCode, oldResidueType)

    #=========================================================================================
    # Implementation methods
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: NmrChain) -> list:
        """get wrappedData (MolSystem.Residues) for all Residue children of parent Chain"""
        return parent._wrappedData.sortedResonanceGroups() if parent._wrappedData else ()

    @staticmethod
    def _reverseChainForDelete(apiNmrChain):
        """Reverse the chain.
        """
        apiNmrChain.__dict__['mainResonanceGroups'].reverse()

    def _finaliseAction(self, action: str, **actionKwds):
        """Subclassed to handle associated offsetNMrResidues
        """
        if action == 'delete':
            # store the old parent information - may be required for some modules
            self._oldNmrChain = self.nmrChain
            self._oldNmrAtoms = tuple(self.nmrAtoms)
            for nmrAt in self.nmrAtoms:
                nmrAt._oldNmrResidue = self
                nmrAt._oldAssignedPeaks = tuple(nmrAt.assignedPeaks)
        elif action == 'create':
            self._oldNmrChain = None
            self._oldNmrAtoms = ()
            # this might be empty
            for nmrAt in self.nmrAtoms:
                nmrAt._oldNmrResidue = None
                nmrAt._oldAssignedPeaks = ()

        if not super()._finaliseAction(action):
            return

        if action in ['rename']:
            for offNmrRes in self.offsetNmrResidues:
                offNmrRes._finaliseAction('rename')

        if action in ['delete', 'create']:
            # notify any offset-nmrResidues
            for offNmrRes in self.offsetNmrResidues:
                offNmrRes._finaliseAction(action)
            # notify that the peak labels need to be updated
            _peaks = set(pk for nmrAtom in self.nmrAtoms for pk in nmrAtom.assignedPeaks)
            for pk in _peaks:
                pk._finaliseAction('change')

    def _delete(self):
        """Delete object, with all contained objects and underlying data.
        """
        atHeadOfChain = False
        apiNmrChain = self._wrappedData.directNmrChain
        if apiNmrChain and apiNmrChain.isConnected:
            stretch = tuple(apiNmrChain.mainResonanceGroups)
            atHeadOfChain = True if len(stretch) > 1 and stretch[0].mainResonanceGroup is self._wrappedData else False

        with undoBlock():
            if atHeadOfChain:
                # can be deleted from the end
                self.moveToEnd()

            # remove all the mmrAtoms from their associated chemicalShifts
            # - clearing before the delete handles the notifiers nicely
            _shs = {sh for nmrRes in (self,) + self.offsetNmrResidues
                    for nmrAt in nmrRes.nmrAtoms
                    for sh in nmrAt.chemicalShifts}
            for sh in _shs:
                sh.nmrAtom = None
            super().delete()
            # clean-up/delete the chemical-shifts
            for sh in _shs:
                sh.delete()

    def _renameChildren(self):
        """Update the chemicalShifts to the rename
        """
        for nmrAt in self.nmrAtoms:
            # actions to be called outside of rename - must be last thing to set?
            nmrAt._childActions.append(nmrAt._renameChemicalShifts)
            nmrAt._finaliseChildren.extend((sh, 'change') for sh in nmrAt.chemicalShifts)

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    @logCommand(get='self')
    def newNmrAtom(self, name: str = None, isotopeCode: str = None, comment: str = None, **kwds):
        """Create new NmrAtom within NmrResidue. If name is None, use default name
            (of form e.g. '@_123, @H_211', '@N_45', ...)

        See the NmrAtom class for details

        :param name: string name of the new nmrAtom
        :param isotopeCode: isotope code
        :param comment: optional string comment
        :return: a new NmrAtom instance.
        """
        from ccpn.core.NmrAtom import _newNmrAtom  # imported here to avoid circular imports

        return _newNmrAtom(self, name=name, isotopeCode=isotopeCode, comment=comment, **kwds)

    def fetchNmrAtom(self, name: str, isotopeCode: str = None):
        """Fetch NmrAtom with name=name, creating it if necessary

        :param name: string name for new nmrAtom if created
        :param isotopeCode: optional isotope code only used for a new nmrAtom.
        :return: new or existing nmrAtom
        """
        from ccpn.core.NmrAtom import _fetchNmrAtom  # imported here to avoid circular imports

        return _fetchNmrAtom(self, name=name, isotopeCode=isotopeCode)


#=========================================================================================
# Connections to parents:
#=========================================================================================

# GWV 20181122: Moved to Residue class
# def getter(self:Residue) -> typing.Optional[NmrResidue]:
#   try:
#     return self._project.getNmrResidue(self._id)
#   except:
#     return None
#
# def setter(self:Residue, value:NmrResidue):
#   oldValue = self.nmrResidue
#   if oldValue is value:
#     return
#   elif oldValue is not None:
#     oldValue.assignTo()
#   #
#   if value is not None:
#     value.residue = self
#
# Residue.nmrResidue = property(getter, setter, None, "NmrResidue to which Residue is assigned")

# GWV 20181122: Mover to Residue class
# def getter(self:Residue) -> typing.Tuple[NmrResidue]:
#   result = []
#
#   nmrChain = self.chain.nmrChain
#   if nmrChain is not None:
#     nmrResidue = self.nmrResidue
#     if nmrResidue is not None:
#       result = [nmrResidue]
#
#     for offset in set(x.relativeOffset for x in nmrChain.nmrResidues):
#       if offset is not None:
#         residue = self
#         if offset > 0:
#           for ii in range(offset):
#             residue = residue.previousResidue
#             if residue is None:
#               break
#         elif offset < 0:
#           for ii in range(-offset):
#             residue = residue.nextResidue
#             if residue is None:
#               break
#         #
#         if residue is not None:
#           sequenceCode = '%s%+d' % (residue.sequenceCode, offset)
#           ll = [x for x in nmrChain.nmrResidues if x.sequenceCode == sequenceCode]
#           if ll:
#             result.extend(ll)
#
#   #
#   return tuple(sorted(result))
# Residue.allNmrResidues = property(getter, None, None,
#                                   "AllNmrResidues corresponding to Residue - E.g. (for MR:A.87)"
#                                   " NmrResidues NR:A.87, NR:A.87+0, NR:A.88-1, NR:A.82+5, etc.")

# def getter(self: NmrChain) -> typing.Tuple[NmrResidue]:
#     if not self._wrappedData:
#         return ()
#
#     result = list(self._project._data2Obj.get(x) for x in self._wrappedData.mainResonanceGroups)
#     if not self.isConnected:
#         result.sort()
#     return tuple(result)
#
#
# def setter(self: NmrChain, value):
#     self._wrappedData.mainResonanceGroups = [x._wrappedData for x in value]
#
#
# NmrChain.mainNmrResidues = property(getter, setter, None, """NmrResidues belonging to NmrChain that are NOT defined relative to another NmrResidue
#   (sequenceCode ending in '-1', '+1', etc.) For connected NmrChains in sequential order, otherwise sorted by assignment""")
#
# del getter
# del setter


#=========================================================================================


@newObject(NmrResidue)
def _newNmrResidue(self: NmrChain, sequenceCode: typing.Union[int, str] = None, residueType: str = None,
                   comment: str = None) -> NmrResidue:
    """Create new NmrResidue within NmrChain.

    If NmrChain is connected, append the new NmrResidue to the end of the stretch.

    See the NmrResidue class for details.

    :param sequenceCode:
    :param residueType:
    :param comment:
    :return: a new NmrResidue instance.
    """

    originalSequenceCode = sequenceCode

    apiNmrChain = self._wrappedData
    nmrProject = apiNmrChain.nmrProject

    # TODO:ED residueType cannot be an empty string
    if residueType == '':
        residueType = None

    dd = {'name'       : residueType, 'details': comment,
          'residueType': residueType, 'directNmrChain': apiNmrChain}

    # Convert value to string, and check
    if isinstance(sequenceCode, int):
        sequenceCode = str(sequenceCode)
    elif sequenceCode is not None and not isinstance(sequenceCode, str):
        raise ValueError("Invalid sequenceCode %s must be int, str, or None" % repr(sequenceCode))

    serial = None
    if sequenceCode:

        # Check the sequenceCode is not taken already
        partialId = '%s.%s.' % (self._id, sequenceCode.translate(Pid.remapSeparators))
        ll = self._project.getObjectsByPartialId(className='NmrResidue', idStartsWith=partialId)
        if ll:
            raise ValueError("Existing %s clashes with id %s.%s.%s" %
                             (ll[0].longPid, self.shortName, sequenceCode, residueType or ''))

        # Handle reserved names
        if sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
            # this is a reserved name
            serial = int(sequenceCode[1:])
            obj = nmrProject.findFirstResonanceGroup(serial=serial)
            if obj is None:
                # The implied serial is free - we can set it
                sequenceCode = None
            else:
                # Name clashes with existing NmrResidue
                raise ValueError("Cannot create NmrResidue with reserved name %s" % sequenceCode)
                # # NOTE:ED - renumber the current nmrResidue, instead of error
                # serial = obj.parent._serialDict['resonanceGroups'] + 1
                # sequenceCode = None
    else:
        # Just create new ResonanceGroup with default-type name
        sequenceCode = None

    # Create ResonanceGroup
    dd['sequenceCode'] = sequenceCode
    apiResonanceGroup = nmrProject.newResonanceGroup(**dd)
    result = self._project._data2Obj.get(apiResonanceGroup)
    if result is None:
        raise RuntimeError('Unable to generate new NmrResidue item')

    if serial is not None:
        try:
            # tried to take these out, but are required for loading nef objects :|
            result._resetSerial(serial)
        except ValueError:
            self.project._logger.warning("Could not reset serial of %s to %s - keeping original value"
                                         % (result, serial))

    return result


def _getNmrResidue(self: NmrChain, sequenceCode: typing.Union[int, str] = None,
                   residueType: str = None) -> typing.Optional[NmrResidue]:
    """Get NmrResidue with sequenceCode=sequenceCode and residueType=residueType,
    """
    self = self._project.getByPid(self) if isinstance(self, str) else self
    if not self:
        getLogger().debug('nmrChain is not defined')
        return

    partialId = Pid.IDSEP.join([self.id, str(sequenceCode).translate(Pid.remapSeparators), ''])

    ll = self._project.getObjectsByPartialId(className='NmrResidue', idStartsWith=partialId)
    if ll:
        return ll[0]
    else:
        return self.getNmrResidue(sequenceCode)


def _fetchNmrResidue(self: NmrChain, sequenceCode: typing.Union[int, str] = None,
                     residueType: str = None) -> NmrResidue:
    """Fetch NmrResidue with sequenceCode=sequenceCode and residueType=residueType,
    creating it if necessary.

    if sequenceCode is None will create a new NmrResidue

    if bool(residueType)  is False will return any existing NmrResidue that matches the sequenceCode

    :param sequenceCode:
    :param residueType:
    :return: a new NmrResidue instance.
    """
    # defaults = collections.OrderedDict((('sequenceCode', None), ('residueType', None)))
    #
    # self._startCommandEchoBlock('fetchNmrResidue', values=locals(), defaults=defaults,
    #                             parName='newNmrResidue')
    # try:

    with undoBlock():
        if sequenceCode is None:
            # Make new NmrResidue always
            result = self.newNmrResidue(sequenceCode=None, residueType=residueType)
        else:
            # First see if we have the sequenceCode already
            partialId = '%s.%s.' % (self._id, str(sequenceCode).translate(Pid.remapSeparators))
            partialObj = self._project.getObjectsByPartialId(className='NmrResidue', idStartsWith=partialId)

            if partialObj:
                # there can never be more than one
                result = partialObj[0]
            else:
                result = None

            # Code below superseded as it was extremely slow
            # # Should not be necessary, but it is an easy mistake to pass it as integer instead of string
            # sequenceCode = str(sequenceCode)
            #
            # apiResult = self._wrappedData.findFirstResonanceGroup(sequenceCode=sequenceCode)
            # result = apiResult and self._project._data2Obj[apiResult]

            if result is None:
                # NB - if this cannot be created we get the error from newNmrResidue
                result = self.newNmrResidue(sequenceCode=sequenceCode, residueType=residueType)

            else:
                if residueType and result.residueType != residueType:
                    # Residue types clash - error:
                    raise ValueError(
                            "Existing %s does not match residue type %s" % (result.longPid, repr(residueType))
                            )

                    # test - missing residueType when loading Nef file
                    # result.residueType = residueType      # can't set attribute,so error when creating

        if result is None:
            raise RuntimeError('Unable to generate new NmrResidue item')

    return result


# Connections to parents:

#EJB 20181130: moved to nmrChain
# NmrChain.newNmrResidue = _newNmrResidue
# del _newNmrResidue
# NmrChain.fetchNmrResidue = _fetchNmrResidue

def _renameNmrResidue(self: Project, apiResonanceGroup: ApiResonanceGroup):
    """Reset pid for NmrResidue and all offset NmrResidues.
    """
    if self._apiNotificationBlanking != 0 or self._apiBlocking != 0:
        return
    if (nmrResidue := self._data2Obj.get(apiResonanceGroup)) is None:
        # NOTE:GWV - it shouldn't get here but occasionally it does; e.g. when
        # upgrading a V2 project with correctFinalResult() routine
        getLogger().debug(f'_renameNmrResidue: no V3 object for {apiResonanceGroup}')

    else:
        nmrResidue._finaliseAction('rename')
        # for xx in nmrResidue.offsetNmrResidues:
        #     xx._finaliseAction('rename')


# 20190501:ED haven't investigated this properly
# but not tested fully - but moved the offsetNmrResidue._finaliseAction into nmrResidue._finaliseAction

# Notifiers:
#NBNB TBD We must make Resonance.ResonanceGroup 1..1 when we move beyond transition model
# GWV 20230109: disabled notifiers for sequenceCode and residueType: changed only via rename
# Project._setupApiNotifier(_renameNmrResidue, ApiResonanceGroup, 'setSequenceCode')
Project._setupApiNotifier(_renameNmrResidue, ApiResonanceGroup, 'setDirectNmrChain')
# Project._setupApiNotifier(_renameNmrResidue, ApiResonanceGroup, 'setResidueType')
Project._setupApiNotifier(_renameNmrResidue, ApiResonanceGroup, 'setAssignedResidue')
del _renameNmrResidue


# # Rename notifiers put in to ensure renaming of NmrAtoms:
# className = ApiResonanceGroup._metaclass.qualifiedName()
# Project._apiNotifiers.extend(
#         (('_finaliseApiRename', {}, className, 'setResonances'),
#          ('_finaliseApiRename', {}, className, 'addResonance'),
#          )
#         )

def main():
    val = MoveToEnd.HEAD.value


if __name__ == '__main__':
    main()
