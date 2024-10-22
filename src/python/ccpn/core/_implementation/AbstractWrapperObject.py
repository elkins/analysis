"""
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
__dateModified__ = "$dateModified: 2024-10-18 15:00:18 +0100 (Fri, October 18, 2024) $"
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
import string
import traceback
import typing
import re
from collections import OrderedDict
from copy import deepcopy
import pandas as pd

from ccpnmodel.ccpncore.api.memops import Implementation as ApiImplementation
import ccpn.core._implementation.resetSerial
from ccpn.core._implementation.CoreModel import CoreModel
from ccpn.core._implementation.Updater import Updater, \
    UPDATE_POST_OBJECT_INITIALISATION, UPDATE_POST_PROJECT_INITIALISATION, \
    UPDATE_PRE_OBJECT_INITIALISATION
from ccpn.core.lib import Pid
from ccpn.core.lib.ContextManagers import deleteObject, notificationBlanking, \
    apiNotificationBlanking, ccpNmrV3CoreSetter
from ccpn.core.lib.Notifiers import NotifierBase
from ccpn.framework.Version import VersionString
from ccpn.framework.Application import getApplication
from ccpn.util import Common as commonUtil
from ccpn.util.decorators import logCommand
from ccpn.util.Logging import getLogger


_RENAME_SENTINEL = Pid.Pid('Dummy:_rename')
ILLEGAL_PATH_CHARS = r'<>:"/\|?*&@'
_DISCARD_METHODS = {'get_OldChemicalShift', 'get_OldChemicalShift', '_oldChemicalShifts', 'get_PeakCluster',
                    '_peakClusters'}
_DEBUG = False


@functools.total_ordering
class AbstractWrapperObject(CoreModel, NotifierBase):
    """Abstract class containing common functionality for subclasses.

    **Rules for subclasses:**

    All collection attributes are tuples. For objects these are sorted by pid;
    for simple values they are ordered.

    Non-child collection attributes must have addElement() and removeElement
    functions as appropriate.

    For each child class there will be a newChild factory function, to create
    the child object. There will be a collection attribute for each child,
    grandchild, and generally descendant.

    The object pid is given as NM:key1.key2.key3 ... where NM is the shortClassName,
    and the combination of key1, key2, etc. forms the id, which is the keys of the parent
    classes starting at the top.
    The pid is the object id relative to the project; keys relative to objects lower
    in the hierarchy will omit successively more keys.


    **Code organisation:**

    All code related to a given class lives in the file for the class.
    On importing it, it will insert relevant functions in the parent class.
    All import must be through the ccpn module, where it is guaranteed that
    all modules are imported in the right order.

    All actual data live
    in the data layer underneath these (wrapper) classes and are derived where needed.
    All data storage is done
    at the lower level, not at the wrapper level, and there is no mechanism for
    storing attributes that have been added at the wrapper level. Key and uniqueness
    checking, type checking etc.  is also done at teh lower level.

    Initialising happens by passing in a (lower-level) NmrProject instance to the Project
     __init__;
    all wrapper instances are created automatically starting from there. Unless we change this,
    this means we assume that all data can be found by navigating from an
    NmrProject.

    New classes can be added, provided they match the requirements. All classes
    must form a parent-child tree with the root at Project. All classes must
    have the standard class-level attributes, such as  shortClassName, _childClasses,
    and _pluralLinkName.
    Each class must implement the properties id and _parent, and the methods
    _getAllWrappedData, and rename.
    Note that the properties and the _getAllWrappedData function
    must work from the underlying data, as they will be called before the pid
    and object dictionary data are set up.

    The core classes (except for Project) must define newClass method(s) to
    create any children, AND ALL UNDERLYING DATA, taking in all parameters
    necessary to do so.
    """

    # Defined in CoreModel:

    # # Short class name, for PID. Must be overridden for each subclass
    # shortClassName = None
    #
    # # Class name - necessary since the actual objects may be of a subclass.
    # className = None
    #
    # # Name of the parent class; used to make model linkages
    # _parentClass = None
    #
    # # List of child classes. Will be filled by child-classes registering.
    # _childClasses = []

    #: Name of plural link to instances of class
    _pluralLinkName = 'abstractWrapperClasses'

    _isGuiClass = False  # Overridden by Gui classes
    _isPandasTableClass = False  # Overridden by classes with panda DataFrame tables

    # Wrapper-level notifiers that are set up on code import and
    # registered afresh for every new project
    # _coreNotifiers = []

    # Should notifiers be registered separately for this class?
    # Set to False if multiple wrapper classes wrap the same API class (e.g. PeakList, IntegralList;
    # Peak, Integral) so that API level notifiers are only registered once.
    _registerClassNotifiers = True

    # flag to ignore _newApiObject callback function; GWV: used to gradually remove this aspect
    _ignoreNewApiObjectCallback = False

    # Function to generate custom subclass instances -= overridden in some subclasses
    _factoryFunction = None

    # The updater instance
    _updater = Updater()

    # Default values for parameters to 'new' function. Overridden in subclasses
    _defaultInitValues = None

    # Number of fields that comprise the object's pid; usually 1 but overridden in some subclasses
    # e.g. NmrResidue and Residue. Used to get parent id's
    _numberOfIdFields = 1

    #=========================================================================================
    _NONE_VALUE_STRING = '__NONE__'  # Used to emulate None for strings that otherwise have model restrictions
    _UNKNOWN_VALUE_STRING = 'unknown'  # Used to emulate unknown

    #=========================================================================================

    def __init__(self, project: 'Project', wrappedData: ApiImplementation.DataObject):

        # NB project parameter type is Project. Set in Project.py

        # NB wrappedData must be globally unique. CCPN objects all are,
        # but for non-CCPN objects this must be ensured.

        CoreModel.__init__(self)
        NotifierBase.__init__(self)

        # Check if object is already wrapped
        data2Obj = project._data2Obj
        if wrappedData in data2Obj:
            raise ValueError(
                    'Cannot create new object "%s": one already exists for "%s"' % (self.className, wrappedData))

        # initialise
        self._project = project
        self._wrappedData = wrappedData
        data2Obj[wrappedData] = self

        self._id = None
        self._resetIds()

        # keep last value for undo/redo
        # self._oldPid = None
        self._oldRenamePid = self.pid

        # tuple to hold children that explicitly need finalising after atomic operations
        self._finaliseChildren = []
        self._childActions = []

        # Assign an unique id (per class) if it does not yet exists
        if not hasattr(self._wrappedData, '_uniqueId') or \
                self._wrappedData._uniqueId is None:
            # NOTE:ED - HACK to stop rogue/unnecessary notifiers
            wrapperDict = self._wrappedData.__dict__
            wrapperDict['inConstructor'] = True
            self._wrappedData._uniqueId = self.project._getNextUniqueIdValue(self.className)

            del wrapperDict['inConstructor']

    @property
    def _uniqueId(self) -> int:
        """:return an per-class, persistent, positive-valued unique id (an integer)
        """
        return self._wrappedData._uniqueId

    def _resetIds(self):
        # reset id
        oldId = self._id
        project = self._project
        parent = self._parent
        className = self.className
        if parent is None:
            # This is the project
            _id = self._wrappedData.name
            sortKey = ('',)
        elif parent is project:
            _id = str(self._key)
            sortKey = self._localCcpnSortKey
        else:
            _id = '%s%s%s' % (parent._id, Pid.IDSEP, self._key)
            sortKey = parent._ccpnSortKey[2:] + self._localCcpnSortKey
        self._id = _id

        # A bit inelegant, but Nmrresidue is handled specially,
        # with a _ccpnSortKey property
        if className != 'NmrResidue':
            # self._ccpnSortKey = (id(project), _importOrder.index(className)) + sortKey
            self._ccpnSortKey = (id(project), list(project._className2Class.keys()).index(className)) + sortKey

        # update pid:object mapping dictionary
        dd = project._pid2Obj.get(className)
        if dd is None:
            dd = {}
            project._pid2Obj[className] = dd
            project._pid2Obj[self.shortClassName] = dd
        # assert oldId is not None
        if oldId in dd:
            del dd[oldId]
        dd[_id] = self

    @classmethod
    def _nextKey(cls):
        """Get the next available key from _serialDict
        Limited functionality but helps to get potential Pid of the next _wrapped object """
        from ccpn.framework.Application import getApplication

        # get the current project - doesn't require instance of core objects
        _project = getApplication().project

        try:
            # extract the plural name from the Api name
            _metaName = cls._apiClassQualifiedName.split('.')[-1]
            _metaName = _metaName[0].lower() + _metaName[1:] + 's'
            _serials = _project._wrappedData.topObject._serialDict
            _name = f'@{_serials[_metaName] + 1}'
        except Exception as es:
            _name = 'None'

        return _name

    @classmethod
    def _nextId(cls):
        """Create potential Pid for the next object to be created"""
        from ccpn.core.Project import Project

        # try and create the next Id
        parentClass = cls._parentClass
        if parentClass is None:
            # This is the project
            _id = 'Project'
        elif parentClass == Project:
            _id = str(cls._nextKey())
        else:
            _id = '%s%s%s' % (parentClass._nextId(), Pid.IDSEP, cls._nextKey())

        return _id

    def __bool__(self):
        """Truth value: true - wrapper classes are never empty"""
        return True

    def __lt__(self, other):
        """Ordering implementation function, necessary for making lists sortable.
        """

        if hasattr(other, '_ccpnSortKey'):
            return self._ccpnSortKey < other._ccpnSortKey
        else:
            return id(self) < id(other)

    def __eq__(self, other):
        """Python 2 behaviour - objects equal only to themselves."""
        return self is other

    def __ne__(self, other):
        """Python 2 behaviour - objects equal only to themselves."""
        return self is not other

    def __repr__(self):
        """Object string representation; compatible with application.get()
        """
        return "<%s>" % self.pid

    def __str__(self):
        """Readable string representation; potentially subclassed
        """
        return "<%s>" % self.pid

    __hash__ = object.__hash__

    #=========================================================================================
    # CcpNmr Properties
    #=========================================================================================

    # @property
    # def className(self) -> str:
    #     """Class name - necessary since the actual objects may be of a subclass.
    #     """
    #     return self.__class__.className
    #
    # @property
    # def shortClassName(self) -> str:
    #     """Short class name, for PID. Must be overridden for each subclass.
    #     """
    #     return self.__class__.shortClassName

    @property
    def project(self) -> 'Project':
        """The Project (root)containing the object.
        """
        return self._project

    @property
    def pid(self) -> Pid.Pid:
        """Identifier for the object, unique within the project.
        Set automatically from the short class name and object.id
        E.g. 'NA:A.102.ALA.CA'
        """
        return Pid.Pid(Pid.PREFIXSEP.join((self.shortClassName, self._id)))

    @property
    def longPid(self) -> Pid.Pid:
        """Identifier for the object, unique within the project.
        Set automatically from the full class name and object.id
        E.g. 'NmrAtom:A.102.ALA.CA'
        """
        return Pid.Pid(Pid.PREFIXSEP.join((self.className, self._id)))

    # def _longName(self, name):
    #     """long name generated from the name and the object id
    #     """
    #     return Pid.Pid(Pid.PREFIXSEP.join((name, self._id)))

    @property
    def isDeleted(self) -> bool:
        """True if this object is deleted.
        """
        # The many variants are to make sure this catches deleted objects
        # also during the deletion process, for filtering
        return (not hasattr(self, '_wrappedData') or self._wrappedData is None
                or not hasattr(self._project, '_data2Obj') or self._wrappedData.isDeleted)

    @classmethod
    def _defaultName(cls) -> str:
        """default name to use for objects with a name/title
        """
        return 'my%s' % cls.className

    # @staticmethod
    # def _defaultNameFromSerial(cls, serial):
    #     # Get the next default name using serial, this may already exist
    #     name = 'my%s_%s' % (cls.className, serial)
    #     return name

    @classmethod
    def _uniqueName(cls, parent, name=None, caseSensitive=False) -> str:
        """Return a unique name based on name (set to defaultName if None)
        :param parent: container for self (usually of type Project)
        :param name (str | None): target name (as required)
        :return str: new unique name
        """
        if name is None:
            name = cls._defaultName()
        cls._validateStringValue('name', name)
        name = name.strip()
        if caseSensitive:
            names = [sib.name for sib in getattr(parent, cls._pluralLinkName)]
            while name in names:
                name = commonUtil.incrementName(name)
        else:
            names = [sib.name.lower() for sib in getattr(parent, cls._pluralLinkName)]
            while name.lower() in names:
                name = commonUtil.incrementName(name)
        return name

    @classmethod
    def _uniqueApiName(cls, project, name=None, caseSensitive=False) -> str:
        """Return a unique name based on api name (set to defaultName if None)
        Needed to stop recursion when generating unique names from '.name'
        """
        if name is None:
            name = cls._defaultName()
        cls._validateStringValue('name', name)
        name = name.strip()
        if caseSensitive:
            names = [sib._wrappedData.name for sib in getattr(project, cls._pluralLinkName)]
            while name in names:
                name = commonUtil.incrementName(name)
        else:
            names = [sib._wrappedData.name.lower() for sib in getattr(project, cls._pluralLinkName)]
            while name.lower() in names:
                name = commonUtil.incrementName(name)
        return name

    @classmethod
    def _validateStringValue(cls, attribName: str, value: str,
                             allowWhitespace: bool = False,
                             allowEmpty: bool = False,
                             allowNone: bool = False,
                             limitChars: bool = False,
                             filePathChars: bool = False):
        """Validate the value of any string

        :param attribName: used for reporting
        :param value: value to be validated
        :param allowWhitespace: When True whitespace is allowed.
        :param allowEmpty: When True empty strings are allowed
        :param allowNone: When True values equaling None are allowed.
        :param limitChars: When True values containing non alphanumerics are disallowed.


        CCPNINTERNAL: used in many rename() and newXYZ method of core classes

        Raises an error if a string is not conforming to the allowed and limit rules.
        Validation Rules:
            - Whitespace: space, tab, linefeed, return, formfeed, and vertical tab
            - Empty: '' or ""
            - None: None
            - Limited Chars: Allowable characters are abcdefghijklmnopqrstuvwxyz upper or lower,
              0123456789, @, %, + and, -
        """
        if value is None and not allowNone:
            raise ValueError(f'{cls.__name__}: None not allowed for {attribName!r}')

        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f'{cls.__name__}: {attribName!r} must be a string')

            if len(value) == 0 and not allowEmpty:
                raise ValueError(f'{cls.__name__}: {attribName!r} must be set')

            if Pid.altCharacter in value:
                raise ValueError(
                    f'{cls.__name__}: Character {Pid.altCharacter!r} not allowed in {attribName!r}; got {value!r}')

            if not allowWhitespace and commonUtil.contains_whitespace(value):
                raise ValueError(f'{cls.__name__}: Whitespace not allowed in {attribName!r}; got {value!r}')

            if limitChars and not set(value).issubset(set(string.ascii_letters) | set(string.digits) | set('@%-+')):
                raise ValueError(f'{cls.__name__}: {attribName} should only contain alphanumeric characters and'
                                 f' @, %, + or -')

            if filePathChars and not set(value).isdisjoint(ILLEGAL_PATH_CHARS):
                raise ValueError(f'{cls.__name__}: {attribName} should not include {ILLEGAL_PATH_CHARS}')

    # @staticmethod
    # def _nextAvailableName(cls, project):
    #     # Get the next available name
    #     _cls = getattr(project, cls._pluralLinkName)
    #     nextNumber = len(_cls) + 1
    #     _name = cls.className  #._defaultName(cls, cls)
    #     name = 'my%s_%s' % (_name, nextNumber)  # if nextNumber > 0 else sampleName
    #     names = [d.name for d in _cls]
    #     while name in names:
    #         name = commonUtil.incrementName(name)
    #
    #     return name

    # @staticmethod
    # def _nextAvailableWrappedName(cls, project):
    #     # Get the next available name
    #     _cls = getattr(project, cls._pluralLinkName)
    #     nextNumber = len(_cls) + 1
    #     _name = cls.className  #._defaultName(cls, cls)
    #     name = 'my%s_%s' % (_name, nextNumber)  # if nextNumber > 0 else sampleName
    #     names = [d._wrappedData.name for d in _cls]
    #     while name in names:
    #         name = commonUtil.incrementName(name)
    #
    #     return name

    @property
    def _ccpnInternalData(self) -> dict:
        """Dictionary containing arbitrary type data for internal use.

        Data can be nested strings, numbers, lists, tuples, (ordered) dicts,
        numpy arrays, pandas structures, CCPN Tensor objects, and any
        object that can be serialised to JSON. This does NOT include CCPN or
        CCPN API objects.

        NB This returns the INTERNAL dictionary. There is NO encapsulation

        Data are kept on save and reload, but there is NO guarantee against
        trampling by other code"""
        result = self._wrappedData.ccpnInternalData
        if result is None:
            result = {}
            # with notificationBlanking():
            #     with apiNotificationBlanking():
            #         self._wrappedData.ccpnInternalData = result
            # this avoids having to block everything
            self._wrappedData.__dict__['ccpnInternalData'] = result
        return result

    @_ccpnInternalData.setter
    def _ccpnInternalData(self, value):
        if not (isinstance(value, dict)):
            raise ValueError("_ccpnInternalData must be a dictionary, was %s" % value)
        with notificationBlanking():
            with apiNotificationBlanking():
                self._wrappedData.ccpnInternalData = value

    @property
    def comment(self) -> str:
        """Free-form text comment"""
        return self._none2str(self._wrappedData.details)

    @comment.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def comment(self, value: str):
        self._wrappedData.details = self._str2none(value)

    def appendComment(self, value):
        """Conveniance function to append to comment
        """
        comment = self.comment
        if len(comment) > 0:
            comment += '; '
        comment += value
        self.comment = comment

    #=========================================================================================
    # CcpNmr functionalities
    #=========================================================================================

    @classmethod
    def newPid(cls, *args) -> 'Pid':
        """Create a new pid instance from cls.shortClassName and args
        """
        from ccpn.core.lib.Pid import Pid

        if len(args) < cls._numberOfIdFields:
            raise ValueError('%s.newPid: to few id-fields to generate a valid Pid instance')
        pidFields = [cls.shortClassName] + [str(x) for x in args]
        return Pid.new(*pidFields)

    _CCPNMR_NAMESPACE = '_ccpNmrV3internal'

    def _setInternalParameter(self, parameterName: str, value):
        """Sets parameterName for CCPNINTERNAL namespace to value; value must be json seriliasable"""
        self.setParameter(self._CCPNMR_NAMESPACE, parameterName, value)

    def _getInternalParameter(self, parameterName: str):
        """Gets parameterName for CCPNINTERNAL namespace"""
        return self.getParameter(self._CCPNMR_NAMESPACE, parameterName)

    def _hasInternalParameter(self, parameterName: str):
        """Returns true if parameterName for CCPNINTERNAL namespace exists"""
        return self.hasParameter(self._CCPNMR_NAMESPACE, parameterName)

    def _deleteInternalParameter(self, parameterName: str):
        """Delete the parameter from CCPNINTERNAL namespace if exists and remove namespace if empty"""
        self.deleteParameter(self._CCPNMR_NAMESPACE, parameterName)

    def setParameter(self, namespace: str, parameterName: str, value):
        """Sets parameterName for namespace to value; value must be json serialisable"""
        checkXml = str(value)
        # check that the value does not contains characters incompatible with xml
        pos = re.search('[<>]', checkXml, re.MULTILINE)
        if pos:
            raise RuntimeError("data cannot contain xml tags '{}' at pos {}".format(pos.group(), pos.span()))
        space = self._ccpnInternalData.setdefault(namespace, {})
        space[parameterName] = value
        # Explicit flag assignment to enforce saving
        self._wrappedData.__dict__['isModified'] = True

    def getParameter(self, namespace: str, parameterName: str):
        """:returns value of parameterName for namespace or None if not present
        """
        space = self._ccpnInternalData.get(namespace)
        if space is not None:
            return space.get(parameterName)
        else:
            return None

    def hasParameter(self, namespace: str, parameterName: str):
        """Returns true if parameterName for namespace exists"""
        space = self._ccpnInternalData.get(namespace)
        if space is None:
            return False
        return parameterName in space

    def deleteParameter(self, namespace: str, parameterName: str):
        """Delete the parameter from namespace if exists and remove namespace if empty
        """
        data = self._ccpnInternalData
        space = data.get(namespace)
        if space is None:
            return False
        # remove the parameterName and namespace
        space.pop(parameterName, None)
        if not space:
            data.pop(namespace, None)
        # Explicit flag assignment to enforce saving
        self._wrappedData.__dict__['isModified'] = True

    def _setNonApiAttributes(self, attribs):
        """Set the non-api attributes that are stored in ccpnInternal
        """
        if not isinstance(attribs, dict):
            raise TypeError(f'ERROR: {str(attribs)} must be a dict')

        for att, value in attribs.items():
            setattr(self, att, value)

    def _getInternalParameterRef(self, parameterName: str):
        """Gets reference of parameterName for CCPNINTERNAL namespace without making deepcopy.
        See _getParameterRef below.
        """
        return self._getParameterRef(self._CCPNMR_NAMESPACE, parameterName)

    def _getParameterRef(self, namespace: str, parameterName: str):
        """Returns value of parameterName for namespace; returns None if not present
        CCPNINTERNAL: does not return a copy so do not change.
        Use sparingly!
        Required as some objects in ccpnInternal might contain core objects that deepcopy will interpret as infinitely deep :|
        At the current time -> cross-referencing during run-time,
            but this is conterted to pids when loading/saving.
        """
        space = self._ccpnInternalData.get(namespace)
        if space is not None:
            return space.get(parameterName)

    @staticmethod
    def _str2none(value):
        """Convenience to convert an empty string to None; V2 requirement for some attributes
        """
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError('Non-string type for value argument')
        return None if len(value) == 0 else value

    @staticmethod
    def _none2str(value):
        """Convenience to None return to an empty string; V2 requirement for some attributes
        """
        return '' if value is None else value

    def _saveObjectOrder(self, objs, key):
        """Convenience: save pids of objects under key in the CcpNmr internal space.
        Order can be restored with _restoreObjectOrder
        """
        pids = [obj.pid for obj in objs]
        self._setInternalParameter(key, pids)

    def _restoreObjectOrder(self, objs, key) -> list:
        """Convenience: restore order of objects from saved pids under key in the CcpNmr internal space.
        Order needed to be stored previously with _saveObjectOrder
        """
        if not isinstance(objs, (list, tuple)):
            raise ValueError('Expected a list or tuple for "objects" argument')

        result = objs
        pids = self._getInternalParameter(key)
        # see if we can use the pids to reconstruct the order
        if pids is not None:
            objectsDict = dict([(s.pid, s) for s in objs])
            result = [objectsDict[p] for p in pids if p in objectsDict]
            if len(result) != len(objs):
                # we failed
                result = objs
        return result

    #=========================================================================================
    # CcpNmr abstract properties
    #=========================================================================================

    @property
    def _key(self) -> str:
        """Object local identifier, unique for a given type with a given parent.

        Set automatically from other (immutable) object attributes."""
        raise NotImplementedError("Code error: function not implemented")

    @property
    def _parent(self):
        """Parent (containing) object."""
        raise NotImplementedError("Code error: function not implemented")

    @property
    def id(self) -> str:
        """Identifier for the object, used to generate the pid and longPid.
        Generated by combining the id of the containing object, i.e. the PeakList instance,
        with the value of one or more key attributes that uniquely identify the object in context
        """
        return self._id

    @property
    def _localCcpnSortKey(self) -> typing.Tuple:
        """Local sorting key, in context of parent.
        NBNB Must be overridden is some subclasses to get proper sorting order"""

        if hasattr(self._wrappedData, 'serial'):
            return (self._wrappedData.serial,)
        else:
            return (self._key,)

    #=========================================================================================
    # Abstract /Api methods
    #=========================================================================================

    # def _printClassTree(self, node=None, tabs=0):
    #     """Simple Class-tree printing method
    #      """
    #     if node is None:
    #         node = self
    #     s = '\t' * tabs + '%s' % (node.className)
    #     if node._isGuiClass:
    #         s += '  (GuiClass)'
    #     print(s)
    #     for child in node._childClasses:
    #         self._printClassTree(child, tabs=tabs + 1)

    def _getAllDecendants(self) -> list:
        """Get all objects descending from self; i.e. children, grandchildren, etc
        """
        result = []
        for children in self._getChildren(recursion=True).values():
            result.extend(children)
        return result

    def _getChildrenByClass(self, klass) -> list:
        """GWV: Convenience: get the children of type klass of self.
        klass is string (e.g. 'Peak') or V3 core class
        returns empty list if klass is not a child of self
        """
        klass = klass if isinstance(klass, str) else getattr(klass, 'className')
        result = self._getChildren(classes=[klass]).get(klass)
        if result is None:
            return []
        return result

    def _getChildren(self, classes=('all',), recursion: bool = False) -> OrderedDict:
        """GWV; Construct a dict of (className, ChildrenList) pairs

        :param classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
        :param recursion: Optionally recurse (breath-first)
        :return: a OrderedDict of (className, ChildrenList) pairs

        CCPNINTERNAL: used throughout
        """
        _get = self._project._data2Obj.get
        data = OrderedDict()
        for className, apiChildren in self._getApiChildren(classes=classes).items():
            data.setdefault(className, [])
            for apiChild in apiChildren:
                child = _get(apiChild)
                if child is not None:
                    data[className].append(child)
        # check for recursion
        if recursion:
            children = [child for childList in data.values() for child in childList]
            # for children in data.values():
            for child in children:
                childData = child._getChildren(classes=classes, recursion=recursion)
                for childClassName, childList in childData.items():
                    data.setdefault(childClassName, [])
                    data[childClassName].extend(childList)
            # print('>>>', data)
        return data

    def _getApiChildren(self, classes=('all',)) -> OrderedDict:
        """GWV; Construct a dict of (className, apiChildrenList) pairs

         :param classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
         :return: a OrderedDict of (className, apiChildrenList) pairs

         CCPNINTERNAL: used throughout
         """
        data = OrderedDict()
        for childClass in self._childClasses:

            app = getApplication()
            if childClass._isGuiClass and app and not app.hasGui:
                getLogger().debug(f'-->  _getApiChildren: skipping gui-class {childClass} for NoUi interface')
                continue

            if ('all' in classes) or \
                    (childClass._isGuiClass and 'gui' in classes) or \
                    (not childClass._isGuiClass and 'nonGui' in classes) or \
                    childClass.className in classes:

                childApis = data.setdefault(childClass.className, [])
                for apiObj in childClass._getAllWrappedData(self):
                    childApis.append(apiObj)

        return data

    def _getApiSiblings(self) -> list:
        """GWV; Return a list of apiSiblings of self
         CCPNINTERNAL: used throughout
         """
        if self._parent is None:
            # We are at the root (i.e. Project), no siblings
            return []
        else:
            return self._parent._getApiChildren().get(self.className)

    def _getSiblings(self) -> list:
        """GWV; Return a list of siblings of self
         CCPNINTERNAL: used throughout
         """
        if self._parent is None:
            # We are at the root (i.e. Project), no siblings
            return []
        else:
            return self._parent._getChildren().get(self.className)

    def _getDirectChildren(self):
        """RF; Get list of all objects that have self as a parent
        """
        getDataObj = self._project._data2Obj.get
        result = [getDataObj(y) for x in self._childClasses for y in x._getAllWrappedData(self)]
        return result

    def _getApiObjectTree(self) -> tuple:
        """Retrieve the apiObject tree contained by this object

        CCPNINTERNAL   used for undo's, redo's
        """
        #EJB 20181127: taken from memops.Implementation.DataObject.delete
        #                   should be in the model??

        from ccpn.util.OrderedSet import OrderedSet

        apiObject = self._wrappedData

        apiObjectlist = OrderedSet()
        # objects still to be checked
        objsToBeChecked = list()
        # counter keyed on (obj, roleName) for how many objects at other end of link
        linkCounter = {}

        # topObjects to check if modifiable
        topObjectsToCheck = set()

        objsToBeChecked.append(apiObject)
        while len(objsToBeChecked) > 0:
            obj = objsToBeChecked.pop()
            if obj:
                obj._checkDelete(apiObjectlist, objsToBeChecked, linkCounter,
                                 topObjectsToCheck)  # This builds the list/set

        for topObjectToCheck in topObjectsToCheck:
            if (not (topObjectToCheck.__dict__.get('isModifiable'))):
                raise ValueError("""%s.delete:
           Storage not modifiable""" % apiObject.qualifiedName
                                 + ": %s" % (topObjectToCheck,)
                                 )

        return tuple(apiObjectlist)

    @classmethod
    def _getAllWrappedData(cls, parent) -> list:
        """get list of wrapped data objects for each class that is a child of parent

        List must be sorted at the API level 1) to give a reproducible order,
        2) using serial (if present) and otherwise a natural (i.e.NON-object) key.
        Wrapper level sorting may be (and sometimes is) different.

        """
        if cls not in parent._childClasses:
            raise RuntimeError('Code error: cls not in child classes')

        raise NotImplementedError('Code error: function not implemented')

    def _rename(self, value: str):
        """Generic rename method that individual classes can use for implementation
        of their rename method to minimises code duplication
        """
        # validate the name
        name = self._uniqueName(parent=self.project, name=value)

        # rename functions from here
        oldName = self.name
        # self._oldPid = self.pid

        self._wrappedData.name = name

        return (oldName,)

    def rename(self, value: str):
        """Change the object name or other key attribute(s), changing the object pid,
           and all internal references to maintain consistency.
           Some Objects (Chain, Residue, Atom) cannot be renamed"""
        raise ValueError(f'{self.__class__.__name__} objects cannot be renamed')

    # In addition, each class (except for Project) must define a  newClass method
    # The function (e.g. Project.newMolecule), ... must create a new child object
    # AND ALL UNDERLYING DATA, taking in all parameters necessary to do so.

    @property
    def collections(self) -> tuple:
        """Return the list of collections containing this core object
        """
        # dynamic lookup from the project collectionList
        return self.project._collectionList.searchCollections(self)

    @logCommand(get='self')
    def addToCollection(self, collection):
        """Add core object to the named collection
        """
        from ccpn.core.Collection import Collection

        if not isinstance(collection, Collection):
            raise ValueError(f'{self.__class__.__name__}.addToCollection: {collection} is not a collection')

        collection.addItems([self])

    #=========================================================================================
    # Restore methods
    #=========================================================================================

    _OBJECT_VERSION = '_objectVersion'

    @property
    def _objectVersion(self) -> VersionString:
        """Return the versionString of the object; used in _updateObject
        to implement the update mechanism
        """
        if not self._wrappedData._objectVersion:
            self._wrappedData._objectVersion = str(self.project._saveHistory.lastSavedVersion)
        return VersionString(self._wrappedData._objectVersion)

    @_objectVersion.setter
    def _objectVersion(self, version):
        # call the VersionString class, as it checks for compliance
        # Value is stored as an actual str object, not VersionString object
        version = str(VersionString(version))
        self._wrappedData._objectVersion = version

    def _updateObject(self, updateMethod):
        """Use post-object or post-project updateMethod (as defined in Updater)
        to update the project
        """
        if updateMethod not in (UPDATE_POST_OBJECT_INITIALISATION, UPDATE_POST_PROJECT_INITIALISATION):
            raise ValueError('Invalid updateMethod "%s"' % updateMethod)
        self._updater.update(updateMethod, obj=self)

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Restores object from apiObj; checks for _factoryFunction.
        Restores the children

        :return Restored object

        CCPNINTERNAL: can be subclassed in special cases
        """
        if apiObj is None:
            raise ValueError('_restoreObject: undefined apiObj')

        # # call any pre-initialisation updates
        # cls._updater.update(UPDATE_PRE_OBJECT_INITIALISATION, apiObj, cls)

        # if (factoryFunction := cls._factoryFunction) is None:
        #     # obj = cls(project, apiObj)
        #     obj = cls._newInstanceFromApiData(project=project, apiObj=apiObj)
        # else:
        #     obj = factoryFunction(project, apiObj)

        obj = cls._newInstanceFromApiData(project=project, apiObj=apiObj)
        if obj is None:
            raise RuntimeError(f'Error restoring object encoded by {apiObj}')

        # update _objectVersion from internal parameter store to model (if exists)
        if obj._hasInternalParameter(obj._OBJECT_VERSION):
            _version = obj._getInternalParameter(obj._OBJECT_VERSION)
            obj._deleteInternalParameter(obj._OBJECT_VERSION)
            obj._objectVersion = _version

        # indented debugging just to be sure is running in the correct order
        _indent = getattr(AbstractWrapperObject, '__indent', 1)
        getLogger().debug2(f'{"-" * _indent}>  _restoreObject  {apiObj}')
        setattr(AbstractWrapperObject, '__indent', _indent + 4)

        # restore the children
        obj._restoreChildren()
        obj._postRestore()

        # call any post-initialisation updates
        cls._updater.update(UPDATE_POST_OBJECT_INITIALISATION, obj)

        return obj

    def _restoreChildren(self):
        """Recursively restore children, using existing objects in data model
        """

        project = self._project
        data2Obj = project._data2Obj

        for childClass in self._childClasses:

            app = getApplication()
            if childClass._isGuiClass and app and not app.hasGui:
                # if gui is disabled then skip all gui-core-classes
                getLogger().debug(f'-->  _restoreChildren: skipping gui-class {childClass} for NoUi interface')
                continue

            # recursively create children
            apiObjs = childClass._getAllWrappedData(self)
            for apiObj in apiObjs:
                obj = data2Obj.get(apiObj)

                if obj is None:
                    try:
                        obj = childClass._restoreObject(project=project, apiObj=apiObj)

                    except RuntimeError as es:
                        _text = 'Error restoring api-child %r of %s (%s)' % (apiObj.qualifiedName, self, es)
                        getLogger().warning(_text)
                        if app and app._isInDebugMode:
                            print(traceback.print_exc())

    def _postRestore(self):
        """Handle post-initialising children after all children have been restored
        CCPN-Internal - subclass and call this at the end
        """
        # indented debugging just to be sure is running in the correct order
        _indent = max(getattr(AbstractWrapperObject, '__indent', 5) - 4, 1)
        setattr(AbstractWrapperObject, '__indent', _indent)
        getLogger().debug2(f'<{"-" * _indent}  _postRestore  {self}')

    #  For restore 3.2 branch

    # def _restoreChildren(self, classes=['all']):
    #     """GWV: A method to restore the children of self
    #     classes is either 'gui' or 'nonGui' or 'all' or explicit enumeration of classNames
    #     """
    #     _classMap = dict([(cls.className, cls) for cls in self._childClasses])
    #
    #     # loop over all the child-classses
    #     for clsName, apiChildren in self._getApiChildren(classes=classes).items():
    #
    #         cls = _classMap.get(clsName)
    #         if cls is None:
    #             raise RuntimeError('Undefined class "%s"' % clsName)
    #
    #         for apiChild in apiChildren:
    #
    #             newInstance = self._newInstanceWithApiData(cls=cls, apiData=apiChild)
    #             if newInstance is None:
    #                 raise RuntimeError('Error creating new instance of class "%s"' % clsName)
    #
    #             # add the newInstance to the appropriate mapping dictionaries
    #             self._project._data2Obj[apiChild] = newInstance
    #             _d = self._project._pid2Obj.setdefault(clsName, {})
    #             _d[newInstance.pid] = newInstance
    #
    #             # recursively do the children of newInstance
    #             newInstance._restoreChildren(classes=classes)
    #
    @classmethod
    def _newInstanceFromApiData(cls, project, apiObj):
        """Return a new instance of cls, initialised with data from apiObj
        """
        if apiObj in project._data2Obj:
            # This happens with Window, as it get initialised by the Windowstore and then once
            # more as child of Project
            newInstance = project._data2Obj[apiObj]

        elif (_factoryFunction := cls._factoryFunction) is not None:
            newInstance = _factoryFunction(project, apiObj)

        else:
            newInstance = cls(project, apiObj)

        if newInstance is None:
            raise RuntimeError(f'Error creating new instance of class "{cls.className}"')

        return newInstance

    # def _newInstance(self, *kwds):
    #     """Instantiate a new instance, including the wrappedData
    # future v3.2
    #     Should be subclassed
    #     """
    #     pass

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    @deleteObject()
    def delete(self):
        """Delete object, with all contained objects and underlying data.
        """

        # NBNB clean-up of wrapper structure is done via notifiers.
        # NBNB some child classes must override this function
        self.deleteAllNotifiers()
        self._wrappedData.delete()

    def _deleteChild(self, child):
        """Delete named child object
        CCPN Internal
        """
        raise RuntimeError('Not implemented')

    @deleteObject()
    def _delete(self):
        """Delete self
        """
        # cannot call delete above or the decorator will fail
        self.deleteAllNotifiers()
        self._wrappedData.delete()

    def getByPid(self, pid: str):
        """Get an arbitrary data object from either its pid (e.g. 'SP:HSQC2') or its longPid
        (e.g. 'Spectrum:HSQC2')

        Returns None for invalid or unrecognised input strings.
        """
        # these checks should be done by pid.isValid
        if isinstance(pid, (float, int)):
            return None

        if pid is None or len(pid) is None:
            return None

        obj = None

        # return if the pid does not conform to a pid definition
        if not Pid.Pid.isValid(pid):
            return None

        pid = Pid.Pid(pid)
        dd = self._project._pid2Obj.get(pid.type)
        if dd is not None:
            obj = dd.get(pid.id)
        if obj is not None and obj.isDeleted:
            raise RuntimeError('Pid "%s" defined a deleted object' % pid)
        return obj

    #=========================================================================================
    # CCPN Implementation methods
    #=========================================================================================

    # GWV: not used
    # def getByRelativeId(self, newName: str):
    #     return self._getDescendant(self.project, newName)

    @classmethod
    def _linkWrapperClasses(cls, ancestors: list = None, Project: 'Project' = None, _allGetters=None):
        """Recursively set up links and functions involving children for wrapper classes

        NB classes that have already been linked are ignored, but their children are still processed"""

        if Project:
            assert ancestors, "Code errors, _linkWrapperClasses called with Project but no ancestors"
            newAncestors = ancestors + [cls]
            if cls not in Project._allLinkedWrapperClasses:
                Project._allLinkedWrapperClasses.append(cls)

                classFullName = repr(cls)[7:-1]

                # add getCls in all ancestors
                funcName = 'get' + cls.className
                #  NB Ancestors is never None at this point
                for ancestor in ancestors:
                    # Add getDescendant function
                    def func(self, relativeId: str) -> cls:
                        return cls._getDescendant(self, relativeId)

                    func.__doc__ = "Get contained %s object by relative ID" % classFullName
                    if not hasattr(ancestor, funcName):
                        if _DEBUG:
                            # getLogger is not initialised yet
                            print(f'--> missing getter stub {ancestor}:{funcName}')
                        if funcName in _DISCARD_METHODS:
                            continue
                    setattr(ancestor, funcName, func)
                    _allGetters.setdefault(ancestor.__name__, []).append((1, funcName))

                # Add descendant links
                linkName = cls._pluralLinkName
                for ii in range(len(newAncestors) - 1):
                    ancestor = newAncestors[ii]

                    func = functools.partial(AbstractWrapperObject._allDescendants,
                                             descendantClasses=newAncestors[ii + 1:])
                    # func.__annotations__['return'] = typing.Tuple[cls, ...]
                    if cls.className == 'NmrResidue':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in sequential order "
                                + "(for assigned or connected NmrChains), otherwise in creation order. "
                                + "This is identical to the standard sorting order."
                        )
                    elif cls.className == '_OldChemicalShift':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in NmrAtom creation order "
                                + "This is different from the standard sorting order"
                        )
                    elif cls.className == 'Spectrum':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in approximate creation order "
                                + "This is different from the standard sorting order"
                        )
                    elif cls.className == 'Residue':
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in sequential order "
                                + "This is identical to the standard sorting order"
                        )
                    elif hasattr(cls, 'serial'):
                        docTemplate = ("\- *(%s,)*  - contained %s objects in creation order. "
                                       + "This may differ from the standard sorting order")
                    elif cls.className in ('Data', 'Atom', 'Chain', 'Substance', 'SampleComponent'):
                        docTemplate = (
                                "\- *(%s,)*  - contained %s objects in name order "
                                + "This is identical to the standard sorting order."
                        )
                    else:
                        docTemplate = ("\- *(%s,)*  - contained %s objects in order of underlying key. "
                                       + "This may differ from the standard sorting order")

                    _doc = docTemplate % (classFullName, cls.className)
                    prop = property(func, None, None, _doc)

                    # if f'{ancestor.__name__}.{linkName}' in \
                    #         'SpectrumDisplay.strips Strip.spectrumViews'.split():
                    #     continue

                    if not hasattr(ancestor, linkName):
                        if _DEBUG:
                            print(f'--> missing property stub {ancestor}:{linkName}')
                        if linkName in _DISCARD_METHODS:
                            continue
                    setattr(ancestor, linkName, prop)
                    _allGetters.setdefault(ancestor.__name__, []).append((0, linkName))

                # Add standard Notifiers:
                if cls._registerClassNotifiers:
                    className = cls._apiClassQualifiedName
                    Project._apiNotifiers[:0] = [
                        ('_newApiObject', {'cls': cls}, className, '__init__'),
                        ('_startDeleteCommandBlock', {}, className, 'startDeleteBlock'),
                        ('_finaliseApiDelete', {}, className, 'delete'),
                        ('_endDeleteCommandBlock', {}, className, 'endDeleteBlock'),
                        ('_finaliseApiUnDelete', {}, className, 'undelete'),
                        ('_modifiedApiObject', {}, className, ''),
                        ]
        else:
            # Project class. Start generation here
            Project = cls
            ll = Project._allLinkedWrapperClasses
            # if ll:
            #     raise RuntimeError("ERROR: initialisation attempted more than once")
            newAncestors = [cls]
            ll.append(Project)

        # Fill in Project._className2Class map
        dd = Project._className2Class
        dd[cls.className] = dd[cls.shortClassName] = cls
        Project._className2ClassList.extend([cls.className, cls.shortClassName, cls])

        # 20211113:ED - extra lists to make Collection search quicker as these are immutable at runtime
        dd = Project._classNameLower2Class
        dd[cls.className.lower()] = dd[cls.shortClassName.lower()] = cls
        Project._classNameLower2ClassList.extend([cls.className.lower(), cls.shortClassName.lower(), cls])

        # recursively call next level down the tree
        for cc in cls._childClasses:
            cc._linkWrapperClasses(newAncestors, Project=Project, _allGetters=_allGetters)

    # GWV: Moved to CoreModel
    # @classmethod
    # def _getChildClasses(cls, recursion: bool = False) -> list:
    #     """
    #     :param recursion: use recursion to also add child objects
    #     :return: list of valid child classes of cls
    #
    #     NB: Depth-first ordering
    #
    #     CCPNINTERNAL: Notifier class
    #     """
    #     result = []
    #     for klass in cls._childClasses:
    #         result.append(klass)
    #         if recursion:
    #             result = result + klass._getChildClasses(recursion=recursion)
    #     return result

    # GWV: Moved to CoreModel
    # @classmethod
    # def _getParentClasses(cls) -> list:
    #     """Return a list of parent classes, staring with the root (i.e. Project)
    #     """
    #     result = []
    #     klass = cls
    #     while klass._parentClass is not None:
    #         result.append(klass._parentClass)
    #         klass = klass._parentClass
    #     result.reverse()
    #     return result

    @classmethod
    def _getDescendant(cls, self, relativeId: str):
        """Get descendant of class cls with relative key relativeId
         Implementation function, used to generate getCls functions
         """
        if dd := self._project._pid2Obj.get(cls.className):
            if self is self._project:
                key = '{}'.format(relativeId)  # NOTE:ED - should always be a string
            else:
                key = '{}{}{}'.format(self._id, Pid.IDSEP, relativeId)
            return dd.get(key)
        else:
            return None

    def _allDescendants(self, descendantClasses: (list, tuple)) -> list:
        """get all descendant objects of type decendantClasses[-1] of self,
        following descendantClasses down the data tree.

        E.g. if called on a chain with descendantClasses == [Residue,Atom] the function returns
        a list of all Atoms in a Chain

        NB: the returned list of NmrResidues is sorted; if not: breaks the programme
        """
        from ccpn.core.NmrResidue import NmrResidue  # Local import to avoid cycles
        from ccpn.ui.gui.lib.Strip import Strip
        from ccpn.ui._implementation.PeakView import PeakView
        from ccpn.ui._implementation.MultipletView import MultipletView
        from ccpn.ui._implementation.IntegralView import IntegralView

        if descendantClasses is None or len(descendantClasses) == 0:
            # we should never be here
            raise RuntimeError(f'Error getting all descendants from {self}; decendants tree is empty')

        # get and check the children of type of first descendantClasses
        if descendantClasses[0] not in self._childClasses:
            raise RuntimeError(f'Invalid descendantClass {descendantClasses[0]} for {self}')

        className = descendantClasses[0].className
        # Passing the 'classes' argument limits the dict to className only (for speed)
        children = self._getChildren(classes=[className]).get(className) or []

        objs = []
        if len(descendantClasses) == 1:
            # we are at the end of the recursion tree;
            # The objects are the children of type descendantClass[0] of self
            objs = children

            # # Debugging
            # if className in 'SpectrumView Strip'.split():
            #     ii=0

        else:
            if descendantClasses[0] == Strip and descendantClasses[-1] in [PeakView, MultipletView, IntegralView]:
                # NOTE:ED - hack to remove duplicated peakViews
                children = children[:1]

            # we are not at the end; traverse down the tree for each child
            for child in children:
                objs.extend(child._allDescendants(descendantClasses=descendantClasses[1:]))

        # NB: the returned list of NmrResidues is sorted; if not: breaks the programme
        # GWV: WHY??
        if className == NmrResidue.className:
            objs.sort()

        # print('_allDescendants for %-30s of class %-20r: %s' % \
        #       (self, descendantClasses[0].__name__, objs))
        return objs

    def _unwrapAll(self):
        """remove wrapper from object and child objects
        For special case where wrapper objects are removed without deleting wrappedData"""
        project = self._project
        data2Obj = project._data2Obj

        for childClass in self._childClasses:

            # recursively unwrap children
            for apiObj in childClass._getAllWrappedData(self):
                obj = data2Obj.get(apiObj)
                if obj is not None:
                    obj._unwrapAll()
                    del self._pid2Obj[obj.shortClassName][obj._id]
                del data2Obj[apiObj]

    def _setUniqueStringKey(self, defaultValue: str, keyTag: str = 'name') -> str:
        """(re)set self._wrappedData.keyTag to make it a unique key, using defaultValue
        if not set NB - is called BEFORE data2obj etc. dictionaries are set"""

        wrappedData = self._wrappedData
        if not hasattr(wrappedData, keyTag):
            raise ValueError(
                    f"Cannot set unique {keyTag} for {self.className}: {wrappedData.__class__} object has no attribute {keyTag}"
                    )

        undo = self._project._undo
        if undo is not None:
            undo.increaseBlocking()
        try:
            if wrappedData not in self._project._data2Obj:
                # Necessary because otherwise we likely will have notifiers - that would then break
                wrappedData.root.override = True
            # Set default value if present value is None
            value = getattr(wrappedData, keyTag)
            if value is None:
                value = defaultValue

            # Set to new, unique value if present value is a duplicate
            competitorDict = {
                getattr(x, keyTag)
                for x in self._getAllWrappedData(self._parent)
                if x is not wrappedData
                }
            # 20240522: ED - should it be something like this to only use the api?
            #   - self._parent calls a v3 method
            # competitorDict = {getattr(x, keyTag)
            #                  for x in set(getattr(self._project, self._pluralLinkName, []))
            #                  }
            if value in competitorDict and hasattr(wrappedData, 'serial'):
                # First try appending serial
                value = f'{value}-{wrappedData.serial}'

            while value in competitorDict:
                # Keep incrementing suffix till value is unique
                value = commonUtil.incrementName(value)

            # Set the unique result
            setattr(wrappedData, keyTag, value)

        finally:
            if wrappedData not in self._project._data2Obj:
                wrappedData.root.override = False
            if undo is not None:
                undo.decreaseBlocking()

    # Notifiers and related functions:

    def _finaliseAction(self, action: str, **actionKwds):
        """Do wrapper level finalisation, and execute all notifiers
        action is one of: 'create', 'delete', 'change', 'rename'
        """
        oldPid = None
        # Special case - always update _ids
        if action == 'rename':
            oldPid = self._oldRenamePid

            # Wrapper-level processing
            self._resetIds()

            # update pids on collections and cross-referencing
            newPid = self._oldRenamePid = self.pid
            if oldPid not in [_RENAME_SENTINEL, newPid]:  # the pid after renaming
                self._project._collectionList._resetItemPids(oldPid, newPid)
                self._project._crossReferencing._resetItemPids(self, oldPid=oldPid, action=action)

        elif action in {'create', 'delete'}:
            if self._project._crossReferencing:
                self._project._crossReferencing._resetItemPids(self, action=action)

        if self._childActions:
            # operations that MUST be performed during _finalise
            # irrespective of whether notifiers fire to external objects
            # print(f' CHILD-ACTIONS {self.className}   {self}    {self._childActions}')
            # propagate the action to explicitly associated (generally child) instances
            for func in self._childActions:
                func()
            self._childActions = []

        project = self.project
        # log the time the state of the core-object changed
        project.application._setBackupModifiedTime()
        if project._notificationBlanking:
            return

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # no blanking

        className = self.className
        # NB 'AbstractWrapperObject' not currently in use (Sep 2016), but kept for future needs
        iterator = (project._context2Notifiers.setdefault((name, action), OrderedDict())
                    for name in (className, 'AbstractWrapperObject'))

        if action == 'rename':
            for dd in iterator:
                for notifier in tuple(dd):
                    notifier(self, oldPid, **actionKwds)

            for obj in self._getDirectChildren():
                obj._finaliseAction('rename')

        else:
            # Normal case - just call notifiers
            for dd in iterator:
                for notifier in tuple(dd):
                    notifier(self, **actionKwds)

        # print(f'  {self} ACTIONS   {self._finaliseChildren}')
        # propagate the action to explicitly associated (generally child) instances
        for obj, action in self._finaliseChildren:
            obj._finaliseAction(action)
        self._finaliseChildren = []

        return True

    def _resetSerial(self, newSerial: int):
        """ADVANCED Reset serial of object to newSerial, resetting parent link
        and the nextSerial of the parent.

        Raises ValueError for objects that do not have a serial
        (or, more precisely, where the _wrappedData does not have a serial)."""

        ccpn.core._implementation.resetSerial.resetSerial(self._wrappedData, newSerial)
        self._resetIds()

    def getAsDict(self, _includePrivate=False) -> OrderedDict:
        """
        :return: Ordered dictionary of all class properties and their values. Key= str of property Value=any
        """
        od = OrderedDict()
        for i in dir(self):
            try:  # deals with badly set property which will raise an error instead of returning an attribute.
                att = getattr(self, i)
                if not callable(att):
                    if _includePrivate:
                        od[i] = att
                    else:
                        if not i.startswith('_'):
                            od[i] = att
            except Exception as e:
                getLogger().warning(
                    'Potential error for the property %s in creating dictionary from object: %s . Error: %s' % (
                    i, self, e))
        return od

    def getAsDataFrame(self) -> pd.DataFrame:
        raise RuntimeError('Not implemented')


AbstractWrapperObject.getByPid.__annotations__['return'] = AbstractWrapperObject


def updateObject(fromVersion, toVersion, updateFunction):
    """Class decorator to register updateFunction for a core-class in the _updateFunctions list.
    updateFunction updates fromVersion to the next higher version toVersion
    fromVersion can be None, in which case no initial check on objectVersion is done

    def updateFunction(obj)
        obj: object that is being updated
    """

    def theDecorator(cls):
        """This function will decorate cls with _update, _updateHandler list and registers the updateHandler
        """
        if not hasattr(cls, '_updateFunctions'):
            raise RuntimeError('class %s does not have the attribute _updateFunctions')

        cls._updateFunctions[cls.className].append((fromVersion, toVersion, updateFunction))
        return cls

    return theDecorator
