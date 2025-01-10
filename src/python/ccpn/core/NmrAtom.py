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

import math
from typing import Union, Tuple, Sequence
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.Project import Project
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core._implementation.AbsorbResonance import absorbResonance
from ccpn.core.lib import Pid
from ccpn.core.lib.Util import AtomIdTuple
from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpnmodel.ccpncore.lib import Constants
from ccpn.util.Common import makeIterableList
from ccpn.util.decorators import logCommand
from ccpn.util.isotopes import isotopeCode2Nucleus, getIsotopeRecords
from ccpn.core.lib.ContextManagers import newObject, renameObject, undoBlock, ccpNmrV3CoreSetter
from ccpn.util.Logging import getLogger
from collections import defaultdict


UnknownIsotopeCode = '?'


class NmrAtom(AbstractWrapperObject):
    """NmrAtom objects are used for assignment. An NmrAtom within an assigned NmrResidue is
    by definition assigned to the Atom with the same name (if any).

    NmrAtoms serve as a way of connecting a named nucleus to an observed chemical shift,
    and peaks are assigned to NmrAtoms. Renaming an NmrAtom (or its containing NmrResidue or
    NmrChain) automatically updates peak assignments and ChemicalShifts that use the NmrAtom,
    preserving the link.

    """

    #: Short class name, for PID.
    shortClassName = 'NA'
    # Attribute it necessary as subclasses must use superclass className
    className = 'NmrAtom'

    _parentClass = NmrResidue

    #: Name of plural link to instances of class
    _pluralLinkName = 'nmrAtoms'

    # the attribute name used by current
    _currentAttributeName = 'nmrAtoms'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = Nmr.Resonance._metaclass.qualifiedName()
    _wrappedData: Nmr.Resonance

    # Internal NameSpace
    _AMBIGUITYCODE = '_ambiguityCode'
    _ORIGINALNAME = '_originalName'

    def __init__(self, project: Project, wrappedData):

        # internal lists to hold the current chemicalShifts
        self._chemicalShifts = []

        super().__init__(project, wrappedData)

    #-----------------------------------------------------------------------------------------
    # CCPN properties
    #-----------------------------------------------------------------------------------------

    @property
    def _apiResonance(self) -> Nmr.Resonance:
        """ CCPN atom matching Atom"""
        return self._wrappedData

    @property
    def _parent(self) -> NmrResidue:
        """Parent (containing) object."""
        return self._project._data2Obj.get(self._wrappedData.resonanceGroup)

    nmrResidue: NmrResidue = _parent

    @property
    def _key(self) -> str:
        """Atom name string (e.g. 'HA') regularised as used for ID"""
        return self._wrappedData.name.translate(Pid.remapSeparators)

    @classmethod
    def _nextKey(cls):
        """Get the next available key from _serialDict
        Limited functionality but helps to get potential Pid of the next _wrapped object
        In this case Pid element is of the form '@_<num>' but subject to change"""
        from ccpn.framework.Application import getApplication

        _project = getApplication().project

        _metaName = cls._apiClassQualifiedName.split('.')[-1]
        _metaName = _metaName[0].lower() + _metaName[1:] + 's'
        _name = f'@_{_project._wrappedData.topObject._serialDict[_metaName]}'

        return _name

    @property
    def _localCcpnSortKey(self) -> Tuple:
        """Local sorting key, in context of parent."""

        # We want sorting by name, even though Resonances have serials
        return (self._key,)

    @property
    def _idTuple(self) -> AtomIdTuple:
        """ID as chainCode, sequenceCode, residueType, atomName namedtuple
        Note: Unlike the _id and key, these do NOT have reserved characters mapped to '^'
        _idTuple replaces empty strings with None"""
        parent = self._parent
        ll = [parent._parent.shortName, parent.sequenceCode, parent.residueType, self.name]
        return AtomIdTuple(*(x or None for x in ll))

    @property
    def name(self) -> str:
        """Atom name string (e.g. 'HA')"""
        return self._wrappedData.name

    @name.setter
    def name(self, value: str):
        """set Atom name"""
        self.rename(value)

    @property
    def serial(self) -> int:
        """NmrAtom serial number - set at creation and unchangeable"""
        return self._wrappedData.serial

    #from ccpn.core.Atom import Atom: This will break the import sequence
    @property
    def atom(self) -> 'Atom':
        """Atom to which NmrAtom is assigned; resetting the atom will rename the NmrAtom"""
        return self._project.getAtom(self._id)

    @property
    def isotopeCode(self) -> str:
        """isotopeCode of NmrAtom. Used to facilitate the nmrAtom assignment."""
        value = self._wrappedData.isotopeCode
        if value in [UnknownIsotopeCode, self._UNKNOWN_VALUE_STRING]:
            value = None
        return value

    def _setIsotopeCode(self, value):
        """
        :param value:  value must be defined, if not set then can set to arbitrary value see UnknownIsotopeCode definition
        this means it can still be set at any isotopeCode later, otherwise
        need to undo or create new nmrAtom

        CCPNINTERNAL: used in _newNmrAtom, Peak.assignDimension
        """
        if not isinstance(value, (str, type(None))):
            raise ValueError(f'isotopeCode must be of type string (or None); got {value}')
        if value is not None and value not in list(getIsotopeRecords().keys()) + [UnknownIsotopeCode]:
            raise ValueError(f'Invalid isotopeCode {value}')

        self._wrappedData.isotopeCode = value or UnknownIsotopeCode

    @property
    def boundNmrAtoms(self) -> list['NmrAtom']:
        """NmrAtoms directly bound to this one, as calculated from assignment and
        NmrAtom name matches (NOT from peak assignment)"""
        getDataObj = self._project._data2Obj.get
        ll = self._wrappedData.getBoundResonances()
        result = [getDataObj(x) for x in ll]

        nmrResidue = self.nmrResidue
        if nmrResidue.residue is None:
            # NmrResidue is unassigned. Add ad-hoc protein inter-residue bonds
            if self.name == 'N':
                for rx in (nmrResidue.previousNmrResidue, nmrResidue.getOffsetNmrResidue(-1)):
                    if rx is not None:
                        na = rx.getNmrAtom('C')
                        if na is not None:
                            result.append(na)
            elif self.name == 'C':
                for rx in (nmrResidue.nextNmrResidue, nmrResidue.getOffsetNmrResidue(1)):
                    if rx is not None:
                        na = rx.getNmrAtom('N')
                        if na is not None:
                            result.append(na)
        #
        return result

    @property
    def assignedPeaks(self) -> Tuple['Peak', ...]:
        """All Peaks assigned to the NmrAtom"""
        apiResonance = self._wrappedData
        apiPeaks = {x.peakDim.peak for x in apiResonance.peakDimContribs}
        apiPeaks |= {x.peakDim.peak for x in apiResonance.peakDimContribNs}

        data2Obj = self._project._data2Obj.get
        return tuple(filter(None, map(data2Obj, apiPeaks)))

    @property
    def _ambiguityCode(self):
        """Return the ambiguityCode
        """
        result = self._getInternalParameter(self._AMBIGUITYCODE)
        return result

    @_ambiguityCode.setter
    @ccpNmrV3CoreSetter()
    def _ambiguityCode(self, value):
        """Set the ambiguityCode
        """
        self._setInternalParameter(self._AMBIGUITYCODE, value)

    @property
    def _originalName(self):
        """Return the originalName
        """
        result = self._getInternalParameter(self._ORIGINALNAME)
        return result

    @_originalName.setter
    @ccpNmrV3CoreSetter()
    def _originalName(self, value):
        """Set the originalName
        """
        self._setInternalParameter(self._ORIGINALNAME, value)

    @logCommand(get='self')
    def deassign(self):
        """Reset NmrAtom back to its originalName, cutting all assignment links"""
        self._wrappedData.name = None

    @logCommand(get='self')
    def assignTo(self, chainCode: str = None, sequenceCode: Union[int, str] = None,
                 residueType: str = None, name: str = None, mergeToExisting=False) -> 'NmrAtom':
        """Assign NmrAtom to naming parameters) and return the reassigned result

        If the assignedTo NmrAtom already exists the function raises ValueError.
        If mergeToExisting is True it instead merges the current NmrAtom into the target
        and returns the merged target. Note: Merging is NOT undoable

        WARNING: is mergeToExisting is True, always use in the form "x = x.assignTo(...)",
        as the call 'x.assignTo(...) may cause the source x object to be deleted.

        Passing in empty parameters (e.g. chainCode=None) leaves the current value unchanged. E.g.:
        for NmrAtom NR:A.121.ALA.HA calling with sequenceCode=124 will assign to
        (chainCode='A', sequenceCode=124, residueType='ALA', atomName='HA')


        The function works as:

        nmrChain = project.fetchNmrChain(shortName=chainCode)

        nmrResidue = nmrChain.fetchNmrResidue(sequenceCode=sequenceCode, residueType=residueType)

        (or nmrChain.fetchNmrResidue(sequenceCode=sequenceCode) if residueType is None)
        """

        oldPid = self.longPid
        apiResonance = self._apiResonance
        apiResonanceGroup = apiResonance.resonanceGroup

        with undoBlock():
            if sequenceCode is not None:
                sequenceCode = str(sequenceCode) or None

            # set missing parameters to existing values
            chainCode = chainCode or apiResonanceGroup.nmrChain.code
            sequenceCode = sequenceCode or apiResonanceGroup.sequenceCode
            residueType = residueType or apiResonanceGroup.residueType
            name = name or apiResonance.name

            for ss in chainCode, sequenceCode, residueType, name:
                if ss and Pid.altCharacter in ss:
                    raise ValueError(
                            f"Character {Pid.altCharacter} not allowed in ccpn.NmrAtom id : {chainCode}.{sequenceCode}.{residueType}.{name}"
                            )

            oldNmrResidue = self.nmrResidue
            nmrChain = self._project.fetchNmrChain(chainCode)
            if residueType:
                nmrResidue = nmrChain.fetchNmrResidue(sequenceCode, residueType)
            else:
                nmrResidue = nmrChain.fetchNmrResidue(sequenceCode)

            if name:
                # result is matching NmrAtom, or (if None) self
                result = nmrResidue.getNmrAtom(name) or self
            else:
                # No NmrAtom can match, result is self
                result = self

            if nmrResidue is oldNmrResidue:
                if name != self.name:
                    # self.name can never be returned as None
                    if result is self:
                        # self._wrappedData.name = name or None
                        self.rename(name or None)
                    elif mergeToExisting:
                        result.mergeNmrAtoms(self)
                    else:
                        raise ValueError("New assignment clash with existing assignment,"
                                         " and merging is disallowed")

            else:
                if result is self:
                    # if nmrResidue.getNmrAtom(self.name) is None:
                    #     if name != self.name:
                    #         # self._wrappedData.name = name or None
                    #         self.rename(name or None)
                    #     # self._apiResonance.resonanceGroup = nmrResidue._apiResonanceGroup
                    #     self._setApiResonanceGroup(self._apiResonance, nmrResidue)
                    #
                    # elif name is None or oldNmrResidue.getNmrAtom(name) is None:
                    #     if name != self.name:
                    #         # self._wrappedData.name = name or None
                    #         self.rename(name or None)
                    #     # self._apiResonance.resonanceGroup = nmrResidue._apiResonanceGroup
                    #     self._setApiResonanceGroup(self._apiResonance, nmrResidue)
                    #
                    # else:
                    #     # self._wrappedData.name = None  # Necessary to avoid name clashes
                    #     self.rename(None)  # Necessary to avoid name clashes
                    #     self._apiResonance.resonanceGroup = nmrResidue._apiResonanceGroup
                    #     # self._setApiResonanceGroup(self._apiResonance, nmrResidue)
                    #     # self._wrappedData.name = name
                    #     self.rename(name or None)

                    # Necessary to avoid name clashes - also handles all notifiers
                    #   is it firing too many now though?
                    self.rename(None)
                    self._apiResonance.resonanceGroup = nmrResidue._apiResonanceGroup
                    self.rename(name or None)

                elif mergeToExisting:
                    result.mergeNmrAtoms(self)

                else:
                    raise ValueError("New assignment clash with existing assignment,"
                                     " and merging is disallowed")

        return result

    @logCommand(get='self')
    def mergeNmrAtoms(self, nmrAtoms: Union['NmrAtom', Sequence['NmrAtom']]):
        nmrAtoms = makeIterableList(nmrAtoms)
        nmrAtoms = [self.project.getByPid(nmrAtom) if isinstance(nmrAtom, str) else nmrAtom for nmrAtom in nmrAtoms]
        if not all(isinstance(nmrAtom, NmrAtom) for nmrAtom in nmrAtoms):
            raise TypeError('nmrAtoms can only contain items of type NmrAtom')
        if self in nmrAtoms:
            raise TypeError('nmrAtom cannot be merged with itself')

        with undoBlock():
            for nmrAtom in nmrAtoms:
                absorbResonance(self, nmrAtom)

    @property
    def _oldChemicalShifts(self) -> Tuple:
        """Returns ChemicalShift objects connected to NmrAtom"""
        getDataObj = self._project._data2Obj.get
        return tuple(sorted(getDataObj(x) for x in self._wrappedData.shifts))

    def _getAttribute(self, attrName) -> Tuple:
        """Returns contents of api attribute
        """
        if hasattr(self._wrappedData, attrName):
            return getattr(self._wrappedData, attrName)

        raise TypeError(f'nmrAtom does not have attribute {attrName}')

    @property
    def chemicalShifts(self) -> tuple:
        """Return the chemicalShifts containing the nmrAtom
        """
        return tuple(self._chemicalShifts)

    #-----------------------------------------------------------------------------------------
    # Implementation functions
    #-----------------------------------------------------------------------------------------

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Subclassed to replace unknown isotopCodes"""
        result = super(NmrAtom, cls)._restoreObject(project=project, apiObj=apiObj)

        # Update Unknown to None
        if result.isotopeCode == UnknownIsotopeCode:
            result._setIsotopeCode(None)

        return result

    @classmethod
    def _getAllWrappedData(cls, parent: NmrResidue) -> list:
        """get wrappedData (ApiResonance) for all NmrAtom children of parent NmrResidue
        """
        return parent._wrappedData.sortedResonances()

    @renameObject()
    def _setApiName(self, value):
        """Set a serial format name of the form ?@<n> from the current serial number
        functionality provided by the api
        CCPN Internal - should only be used during nef import
        """
        oldName = self._wrappedData.name
        # self._oldPid = self.pid

        self._wrappedData.name = value
        self._resetIds()

        return (oldName,)

    def _makeUniqueName(self) -> str:
        """Generate a unique name in the form @n (e.g. @_123) or @symbol_n (e.g. @H_34)
        :return the generated name
        """
        if (self.isotopeCode is not None and
                (symbol := isotopeCode2Nucleus(self.isotopeCode)) is not None and
                len(symbol) > 0):
            _name = '@%s_%d' % (symbol[0:1], self._uniqueId)
        else:
            _name = '@_%d' % self._uniqueId
        return _name

    # Sub-class two methods to get '@' names
    @classmethod
    def _defaultName(cls) -> str:
        return '@'

    @classmethod
    def _uniqueName(cls, parent: nmrResidue, name=None, caseSensitive=False) -> str:
        """Subclassed to get the '@' default name behavior.
        :param parent: in this case, parent MUST be of type NmrResidue
        :param name (str | None): target name (as required)
        :return str: new unique name
        """
        if name is None:
            _id = parent.project._queryNextUniqueIdValue(cls.className)
            name = '%s_%d' % (cls._defaultName(), _id)
        return super(NmrAtom, cls)._uniqueName(parent=parent, name=name, caseSensitive=caseSensitive)

    def _finaliseAction(self, action: str, **actionKwds):
        """Subclassed to handle associated offsetNMrResidues
        """
        if action == 'rename':
            # rename the nmrAtom in the chemicalShifts
            self._childActions.append(self._renameChemicalShifts)
            self._finaliseChildren.extend((sh, 'change') for sh in self.chemicalShifts)

        elif action == 'delete':
            # store the old parent information - may be required for some modules
            self._oldNmrResidue = self.nmrResidue
            self._oldAssignedPeaks = self.assignedPeaks
        elif action == 'create':
            self._oldNmrResidue = None
            self._oldAssignedPeaks = ()

        if not super()._finaliseAction(action, **actionKwds):
            return

    @renameObject()
    @logCommand(get='self')
    def rename(self, value: str = None):
        """Rename the NmrAtom, changing its name, Pid, and internal representation.
        """

        if value == self.name: return

        if value is None:
            value = self._makeUniqueName()
            getLogger().debug(
                    f'Renaming an {self} without a specified value. Name set to the auto-generated option: {value}.'
                    )
        NmrAtom._validateStringValue('name', value)

        previous = self._parent.getNmrAtom(value.translate(Pid.remapSeparators))
        if previous is not None:
            raise ValueError(f'NmrAtom.rename: "{value}" conflicts with {previous}')

        # with renameObjectContextManager(self) as addUndoItem:
        isotopeCode = self.isotopeCode
        oldName = self.name
        # self._oldPid = self.pid

        # clear the isotopeCode so that the name may be changed (model restriction)
        self._wrappedData.isotopeCode = UnknownIsotopeCode
        self._wrappedData.name = value
        # set isotopeCode to the correct value
        self._wrappedData.isotopeCode = isotopeCode or UnknownIsotopeCode  # self._UNKNOWN_VALUE_STRING

        # now handled by _finaliseAction
        # self._childActions.append(self._renameChemicalShifts)
        # self._finaliseChildren.extend((sh, 'change') for sh in self.chemicalShifts)

        return (oldName,)

    def _renameChemicalShifts(self):
        # update chemicalShifts
        for cs in self.chemicalShifts:
            cs._renameNmrAtom(self)

    def delete(self):
        """Delete self and update the chemicalShift values
        """
        _shifts = self.chemicalShifts  # tuple from property

        with undoBlock():
            for sh in _shifts:
                sh.nmrAtom = None
            # delete the nmrAtom - notifiers handled by decorator
            self._delete()
            # clean-up/delete the chemical-shifts
            for sh in _shifts:
                sh.delete()

    #-----------------------------------------------------------------------------------------
    # CCPN functions
    #-----------------------------------------------------------------------------------------

    def _getAssignedPeakValues(self, spectra, peakLists=None, theProperty='ppmPosition'):
        """
        CCPN internal. Used in ChemicalShift mapping and Relaxation Analysis tools.
        Convenient routine to avoid nested "for-loops".
        Given a set of spectra, get the value of a particular property for the assigned-peak-dimension.
        Return a dictionary where the spectrum is the key and the value is the list of a given peak property.
        :param spectra: list of CCPN spectra.
        :param peakLists: list of CCPN peakLists to use as a sub-filter, otherwise use all available in spectra.
        :param theProperty: one of (ppmPosition, pointPosition, lineWidth, height, volume). Notes:
              height and volume are not a dim property but a peak property. Taken here to avoid code duplication.
        :return: dictionary {obj:list}
            E.g.: for <NA:A.53.ASN.N>  theProperty='ppmPosition' it returns
                {<SP:Tstar-free>: [119.80854378483475], <SP:Tstar-2:0eq>: [119.93958073136751], ...}

        """
        from ccpn.core.lib.peakUtils import _POINTPOSITION, _PPMPOSITION, _LINEWIDTH, HEIGHT, VOLUME

        if peakLists is None:
            peakLists = [pl for sp in spectra for pl in sp.peakLists]

        valuesDict = defaultdict(list)
        for contrib in self._wrappedData.peakDimContribs:
            if contrib.isDeleted:
                continue
            peakDim = contrib.peakDim
            apiPeak = peakDim.peak
            if apiPeak.isDeleted or peakDim.isDeleted and apiPeak.figOfMerit == 0.0:  #figure of merit shouldn't be filtered here!?
                continue
            apiPeakList = apiPeak.peakList
            peakList = self.project._data2Obj[apiPeakList]
            spectrum = peakList.spectrum
            if peakList not in peakLists:
                continue
            propertyDict = {
                _POINTPOSITION: peakDim.position,
                _PPMPOSITION  : peakDim.realValue,
                _LINEWIDTH    : peakDim.lineWidth,
                HEIGHT        : apiPeak.height,
                VOLUME        : apiPeak.volume,
                }
            valuesDict[spectrum].append(propertyDict.get(theProperty))

        return valuesDict

    def _recalculateShiftValue(self, spectra, simulatedPeakScale: float = 0.0001):
        """Get a new shift value from the assignedPeaks
        """

        apiResonance = self._wrappedData
        sum1 = sum2 = N = 0.0
        peakDims = []
        peaks = set()

        for contrib in apiResonance.peakDimContribs:

            if contrib.isDeleted:
                # Function may be called during PeakDimContrib deletion
                continue

            peakDim = contrib.peakDim
            apiPeak = peakDim.peak

            if apiPeak.isDeleted or peakDim.isDeleted or apiPeak.figOfMerit == 0.0:
                continue

            apiPeakList = apiPeak.peakList
            spectrum = self.project._data2Obj[apiPeakList].spectrum
            if spectrum not in spectra:
                continue

            # NBNB TBD: Old Rasmus comment - peak splittings are not yet handled in V3. TBD add them
            value = peakDim.realValue
            weight = apiPeak.figOfMerit

            if apiPeakList.isSimulated:
                weight *= simulatedPeakScale

            peakDims.append(peakDim)
            peaks.add(apiPeak)

            if value is not None and weight is not None:
                vw = value * weight
                sum1 += vw
                sum2 += value * vw
                N += weight

        if N <= 0.0:
            # no contributions
            return None, None

        mean = sum1 / N
        mean2 = sum2 / N
        sigma2 = abs(mean2 - (mean * mean))
        sigma = math.sqrt(sigma2)

        # valueError (sigma) undefined for single contributions
        return mean, (sigma if len(peakDims) > 1 else None)

    #-----------------------------------------------------------------------------------------
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #-----------------------------------------------------------------------------------------


#=========================================================================================
# Connections to parents:
#=========================================================================================


@newObject(NmrAtom)
def _newNmrAtom(self: NmrResidue, name: str = None, isotopeCode: str = None, comment: str = None, **kwds) -> NmrAtom:
    """Create new NmrAtom within NmrResidue.
    See the NmrAtom class for details

    :param name: string name of the new nmrAtom; If name is None, generate a default name of form
                 e.g. '@_123, @H_211', '@N_45', ...
    :param isotopeCode: optional isotope code
    :param comment: optional string comment
    :return: a new NmrAtom instance.
    """

    apiNmrProject = self._project._wrappedData
    resonanceGroup = self._wrappedData

    if not isinstance(name, (str, type(None))):
        raise TypeError(f'Name {name} must be of type string (or None)')
    if not isinstance(comment, (str, type(None))):
        raise TypeError(f'Comment {comment} must be of type string (or None)')

    # if not name:
    #     # generate (temporary) default name, to be changed later after we created the object
    #     _name = NmrAtom._uniqueName(self.project)
    #
    # else:
    #     # Check for name clashes
    #     _name = name
    #     previous = self.getNmrAtom(_name.translate(Pid.remapSeparators))
    #     if previous is not None:
    #         raise ValueError(f'newNmrAtom: name {_name!r} clashes with {previous}')

    # ensure uniqueName
    _name = NmrAtom._uniqueName(self, name=name)

    # Create the api object
    # Always create first with unknown isotopeCode
    dd = {'resonanceGroup': resonanceGroup, 'isotopeCode': UnknownIsotopeCode, 'name': _name}
    obj = apiNmrProject.newResonance(**dd)

    if (result := self._project._data2Obj.get(obj)) is None:
        raise RuntimeError('Unable to generate new NmrAtom item')

    # Check/set isotopeCode; it has to be set after the creation to avoid API errors.
    result._setIsotopeCode(isotopeCode)

    if comment:
        # set the comment if defined
        result.comment = comment

    # Set additional optional attributes supplied as kwds arguments
    for key, value in kwds.items():
        setattr(result, key, value)

    return result


def _fetchNmrAtom(self: NmrResidue, name: str, isotopeCode=None):
    """Fetch NmrAtom with name=name, creating it if necessary

    :param name: string name for new nmrAto if created
    :return: new or existing nmrAtom
    """
    # resonanceGroup = self._wrappedData

    with undoBlock():
        result = (self.getNmrAtom(name.translate(Pid.remapSeparators)) or
                  self.newNmrAtom(name=name, isotopeCode=isotopeCode))

        if result is None:
            raise RuntimeError('Unable to generate new NmrAtom item')

    return result


def _produceNmrAtom(self: Project, atomId: str = None, chainCode: str = None,
                    sequenceCode: Union[int, str] = None,
                    residueType: str = None, name: str = None) -> NmrAtom:
    """Get chainCode, sequenceCode, residueType and atomName from dot-separated atomId or Pid
    or explicit parameters, and find or create an NmrAtom that matches
    Empty chainCode gets NmrChain:@- ; empty sequenceCode get a new NmrResidue"""

    with undoBlock():

        # Get ID parts to use
        if sequenceCode is not None:
            sequenceCode = str(sequenceCode) or None
        params = [chainCode, sequenceCode, residueType, name]
        if atomId:
            if any(params):
                raise ValueError("_produceNmrAtom: other parameters only allowed if atomId is None")

            #TODO: use .fields attribute of Pid instance

            # Remove colon prefix, if any
            atomId = atomId.split(Pid.PREFIXSEP, 1)[-1]
            for ii, val in enumerate(Pid.splitId(atomId)):
                if val:
                    params[ii] = val
            chainCode, sequenceCode, residueType, name = params

        if name is None:
            raise ValueError("NmrAtom name must be set")

        elif Pid.altCharacter in name:
            raise ValueError(
                    f"Character {Pid.altCharacter} not allowed in ccpn.NmrAtom.name"
                    )

        # Produce chain
        nmrChain = self.fetchNmrChain(shortName=chainCode or Constants.defaultNmrChainCode)
        nmrResidue = nmrChain.fetchNmrResidue(sequenceCode=sequenceCode, residueType=residueType)
        result = nmrResidue.fetchNmrAtom(name)

        if result is None:
            raise RuntimeError('Unable to generate new NmrAtom item')

    return result


#EJB 20181203: moved to NmrResidue
# NmrResidue.newNmrAtom = _newNmrAtom
# del _newNmrAtom
# NmrResidue.fetchNmrAtom = _fetchNmrAtom

#EJB 20181203: moved to nmrAtom
# Project._produceNmrAtom = _produceNmrAtom

# Notifiers:
# className = Nmr.Resonance._metaclass.qualifiedName()
# Project._apiNotifiers.extend(
#         (('_finaliseApiRename', {}, className, 'setImplName'),
#          ('_finaliseApiRename', {}, className, 'setResonanceGroup'),
#          )
#         )
for clazz in Nmr.AbstractPeakDimContrib._metaclass.getNonAbstractSubtypes():
    className = clazz.qualifiedName()
    Project._apiNotifiers.extend(
            (('_modifiedLink', {'classNames': ('NmrAtom', 'Peak')}, className, 'create'),
             ('_modifiedLink', {'classNames': ('NmrAtom', 'Peak')}, className, 'delete'),
             )
            )
