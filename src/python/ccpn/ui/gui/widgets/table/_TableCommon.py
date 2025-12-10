"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-11-20 13:19:04 +0000 (Wed, November 20, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-02-17 10:41:16 +0100 (Fri, February 17, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing
from PyQt5 import QtCore, QtGui, QtWidgets
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import Counter


ORIENTATIONS = {'h'                 : QtCore.Qt.Horizontal,
                'horizontal'        : QtCore.Qt.Horizontal,
                'v'                 : QtCore.Qt.Vertical,
                'vertical'          : QtCore.Qt.Vertical,
                QtCore.Qt.Horizontal: QtCore.Qt.Horizontal,
                QtCore.Qt.Vertical  : QtCore.Qt.Vertical,
                }

# standard definitions for roles applicable to QTableModel
USER_ROLE = QtCore.Qt.UserRole
EDIT_ROLE = QtCore.Qt.EditRole
DISPLAY_ROLE = QtCore.Qt.DisplayRole
TOOLTIP_ROLE = QtCore.Qt.ToolTipRole
STATUS_ROLE = QtCore.Qt.StatusTipRole
BACKGROUND_ROLE = QtCore.Qt.BackgroundRole
BACKGROUNDCOLOR_ROLE = QtCore.Qt.BackgroundColorRole
FOREGROUND_ROLE = QtCore.Qt.ForegroundRole
CHECK_ROLE = QtCore.Qt.CheckStateRole
ICON_ROLE = QtCore.Qt.DecorationRole
SIZE_ROLE = QtCore.Qt.SizeHintRole
ALIGNMENT_ROLE = QtCore.Qt.TextAlignmentRole
FONT_ROLE = QtCore.Qt.FontRole
NO_PROPS = QtCore.Qt.NoItemFlags
CHECKABLE = QtCore.Qt.ItemIsUserCheckable
ENABLED = QtCore.Qt.ItemIsEnabled
SELECTABLE = QtCore.Qt.ItemIsSelectable
EDITABLE = QtCore.Qt.ItemIsEditable
CHECKED = QtCore.Qt.Checked
UNCHECKED = QtCore.Qt.Unchecked
PARTIALLY_CHECKED = QtCore.Qt.PartiallyChecked

# indexing for faster accessing of cached table-data
BACKGROUND_INDEX = 0
FOREGROUND_INDEX = 1
BORDER_INDEX = 2
FONT_INDEX = 3
DISPLAY_INDEX = 4
USER_INDEX = 5

# define roles to return cell-values
DTYPE_ROLE = QtCore.Qt.UserRole + 1000
VALUE_ROLE = QtCore.Qt.UserRole + 1001

# a role to map the table-index to the cell in the df
INDEX_ROLE = QtCore.Qt.UserRole + 1002
BORDER_ROLE = QtCore.Qt.UserRole + 1003

# extra colour options
ROWCOLOUR_ROLE = QtCore.Qt.UserRole + 1004
COLUMNCOLOUR_ROLE = QtCore.Qt.UserRole + 1005

SELECT_ROWS = QtWidgets.QTableView.SelectRows
SELECT_COLUMNS = QtWidgets.QTableView.SelectColumns
HORIZONTAL = QtCore.Qt.Horizontal
VERTICAL = QtCore.Qt.Vertical

QColor = QtGui.QColor
QIcon = QtGui.QIcon
QSize = QtCore.QSize

MOUSE_MARGIN = 3

_EDITOR_SETTER = ('setColor', 'selectValue', 'setData', 'set', 'setValue', 'setText', 'setFile')
_EDITOR_GETTER = ('get', 'value', 'text', 'getFile')


@dataclass
class _TableSelection():
    """Small Class to pass row/column information from the main-table to the headers
    """
    orientation: int = None
    rows: list[int] = field(default_factory=list)
    columns: list[int] = field(default_factory=list)


#=========================================================================================
# Trait definitions for a json-serialisable multi-index column-header
#=========================================================================================

from ccpn.util.traits.CcpNmrJson import CcpNmrJson, Constants
from ccpn.util.traits.CcpNmrTraits import RecursiveList, Enum, Unicode, Bool, Int, Tuple, Union
from ccpn.util.Common import NOTHING as _NOTHING


class ColumnType(Enum):
    GROUP = 0
    ITEM = 1


_MAXDEPTH = 8
_MULTIINDEX = tuple[str | None, ...] | str | None
TraitColumnABCType = typing.TypeVar('TraitColumnABCType', bound='_TraitColumnABC')
ColumnItemType = typing.TypeVar('ColumnItemType', bound='ColumnItem')
ColumnGroupType = typing.TypeVar('ColumnGroupType', bound='ColumnGroup')
_CHILDREN = TraitColumnABCType | list[TraitColumnABCType] | tuple[TraitColumnABCType, ...]
_CHILDRENTAG = 'children'


class _TraitColumnABC(CcpNmrJson):
    _columnType: ColumnType
    classVersion: float = 1.0  # for json saving
    saveAllTraitsToJson: bool = True
    keysInOrder: bool = True
    name = Union([Unicode(allow_none=True).tag(info='index/column cell-name'),
                  Tuple(allow_none=True,
                        trait=Unicode(allow_none=True),
                        maxlen=_MAXDEPTH).tag(info='tuple of multi-index name')], default_value=None)
    movable = Bool(default_value=False).tag(info='flag to indicate that the index/column can be moved within its '
                                                 'parent')
    internal = Bool(default_value=False).tag(info='the index/column is private and always hidden')
    index = Int(allow_none=True, default_value=None).tag(info='index of the index/column if re-ordering is allowed')
    locked = Bool(default_value=False).tag(info='allow/do not allow changes to properties after')
    visible = True
    _parent = None
    _inConstructor = 0
    # attributes to handle ignoring _metadata in the json-dumps
    # as may contain times/dates that stop quick comparisons
    # currently hard-coded, assumes that recursion is handled by a subclass, e.g, see ColumnGroup
    _excludeMetadata = False
    _excludeMetadataLast = False
    _excludeDepth = 0

    def __init__(self, name: _MULTIINDEX, movable: bool, internal: bool, locked: bool, index: int):
        super().__init__()
        self.name = name
        self.movable = movable
        self.internal = internal
        self.index = index
        self.locked = locked

    def __setattr__(self, key: str, value: typing.Any):
        if key != 'locked' and not key.startswith('_') and not self._inConstructor and self.locked:
            raise RuntimeError(f'{self.__class__.__name__}.{key}: class is locked')
        super().__setattr__(key, value)

    #-----------------------------------------------------------------------------------------
    # properties

    @property
    def _isLeaf(self) -> bool:
        """Indicates whether the current object is a leaf node.

        A leaf node is a terminal element in a tree-like structure that does
        not have any child elements; it represents a real column.

        :return: True if the object is a leaf node, False otherwise.
        :rtype: bool
        """
        return True

    @property
    def fullName(self, wildCard: str | None = None) -> tuple[str | None, ...]:
        """Return the full-name as a tuple, includes the names of the parents.

        :param str wildCard: A single character to replace the names (default is None).
        :return: A tuple containing the full name, including the names of the parents.
        :rtype: tuple[str | None, ...]

        :raises TypeError: If `wildCard` is not None and its length is not 1.

        .. note::
           - If `wildCard` is provided, it must be a single character.
           - The method constructs the full name by appending the current object's name to the names of its parents.
        """
        if wildCard is not None and len(wildCard) != 1:
            raise TypeError(f'{self.__class__.__name__}.fullName: invalid wildCard {wildCard!r}')
        this = (self.name,) * (self.maxDepth() - self.depth)
        return self._fullName(wildCard) + this

    @property
    def depth(self) -> int:
        """Return depth from the top of the tree.
        """
        return 1 + (self._parent.depth if self._parent else 0)

    #-----------------------------------------------------------------------------------------
    # methods

    def root(self) -> TraitColumnABCType:
        """Return the top-element of the tree.
        """
        if self._parent:
            return self._parent.root()
        return self

    def toJsonNoMetaData(self, **kwds) -> str:
        with self._excludeBlock():
            return self.toJson(**kwds)

    def maxDepth(self) -> int:
        """Return the maximum depth of the tree.
        """
        # get the root of the tree and calculate the depth from there
        return self.root()._maxdepth()

    def traverse(self, includeBranches: bool = True, includeLeaves: bool = True,
                 recursive: bool = True) -> typing.Generator[TraitColumnABCType, None, None]:
        """Traverse the tree.

        :param bool includeBranches: Whether to include branch nodes in the traversal (default is True).
        :param bool includeLeaves: Whether to include leaf nodes in the traversal (default is None).
        :param bool recursive: Whether to traverse the tree recursively (default is True).
        :return: A generator yielding the nodes of the tree based on the specified parameters.
        :rtype: typing.Generator[TraitColumnABCType, None, None]

        .. note::
           - If `includeLeaves` is True, the current node is yielded.
        """
        if includeLeaves:
            yield self

    def match(self, **searchParameters) -> bool:
        """
        Check if the current object matches the given search parameters.

        :param searchParameters: Keyword arguments representing the attributes to match.
        :return: `True` if the object matches all specified attributes, otherwise `False`.
        :rtype: bool

        .. note::
           - Attributes in `searchParameters` are checked against the object's attributes.
           - The method uses `_NOTHING` as a sentinel to handle attributes that might not exist on the object.
           - If all specified attributes match the corresponding values of the object's attributes, the object matches.

        Example::
            # Example usage
            if node.match(visible=True, name="targetNode"):
                print("Node matches the criteria.")
        """
        return all(getattr(self, key, _NOTHING) == value for key, value in searchParameters.items())

    def search(self, includeBranches: bool = True, includeLeaves: bool = True,
               recursive: bool = True,
               **searchParameters,
               ) -> typing.Generator[TraitColumnABCType, None, None]:
        """Search for nodes in the tree that match the given attributes.

        :param bool includeBranches: Whether to include branch nodes in the traversal (default is True).
        :param bool includeLeaves: Whether to include leaf nodes in the traversal (default is True).
        :param bool recursive: Whether to traverse the tree recursively (default is True).
        :param searchParameters: Keyword arguments representing the attributes to search for.
        :return: A generator yielding the object if it matches the search parameters.
        :rtype: typing.Generator[TraitColumnABCType, None, None]

        .. note::
           - The search is conducted using the `traverse` method to iterate over nodes.
           - Nodes are filtered based on the provided `searchParameters`.
           - Attributes not specified in `searchParameters` are ignored.
           - The method uses `match` to determine if a node satisfies the search criteria.

        Example::
            # Example usage
            results = root.search(recursive=True, name="targetNode", visible=True)
            for node in results:
                print(node.name)
        """
        for node in self.traverse(includeBranches, includeLeaves, recursive):
            if node.match(**searchParameters):
                yield node

    #-----------------------------------------------------------------------------------------
    # implementation

    def _setParent(self, parent: ColumnGroupType | None = None):
        with self._attributeUnlocking():
            if not isinstance(parent, ColumnGroup | type(None)):
                raise RuntimeError(f'{self.__class__.__name__}._setParent: '
                                   f'invalid parent type {type(parent).__name__}')
            self._parent = parent

    @contextmanager
    def _attributeUnlocking(self):
        """Allow writing to locked-attributes.
        """
        self._inConstructor += 1
        try:
            yield  # yield control to the calling method
        finally:
            self._inConstructor -= 1
            if self._inConstructor < 0:
                raise RuntimeError(f'*** {self.__class__.__name__}: _inConstructor below 0')

    @contextmanager
    def _excludeBlock(self):
        """Exclude metadata from toJson.
        """
        self._setExcludeFlag()
        try:
            yield  # yield control to the calling method
        finally:
            self._clearExcludeFlag()

    def _setExcludeFlag(self):
        """Block all Changes to self.
        """
        # block metadata on first entry
        if self._excludeDepth == 0:
            # remember last state
            self._excludeMetadataLast = self._excludeMetadata
            self._excludeMetadata = True
        self._excludeDepth += 1

    def _clearExcludeFlag(self):
        """Unblock all changes to self.
        """
        if self._excludeDepth > 0:
            self._excludeDepth -= 1
            # unblock metadata on last exit
            if self._excludeDepth == 0:
                self._excludeMetadata = self._excludeMetadataLast
        else:
            raise RuntimeError(f'{self} Exclude already at 0')

    def _encode(self) -> list:
        """Return self as list of (trait, value) tuples.
        """

        # get all traits that need saving to json
        # Subtle but important implementation change relative to the previous one-liner
        # Allow trait-specific saveToJson metadata (i.e. 'tag'), to override object's saveAllToJson
        traitsToEncode = [] if self._excludeMetadata else [Constants.METADATA]
        for trait in self.keys():
            # check if saveToJson was defined for this trait
            _saveTraitToJson = self.trait_metadata(traitname=trait, key='saveToJson', default=None)
            # if saveToJson was not defined for this trait, check saveAllToJson flag
            if _saveTraitToJson is None:
                # We didn't obtain a result
                if self.saveAllTraitsToJson:
                    _saveTraitToJson = True
                else:
                    _saveTraitToJson = False

            if _saveTraitToJson:
                traitsToEncode.append(trait)

        # create a list of (trait, value) tuples
        dataList = []
        for trait in traitsToEncode:
            handler = self._getJsonHandler(trait)
            if handler is not None:
                dataList.append((trait, handler().encode(self, trait)))
            else:
                dataList.append((trait, getattr(self, trait)))
        return dataList

    def _decode(self, dataDict: dict) -> TraitColumnABCType:
        """Populate/update self with data from dataDict.
        """
        with self._attributeUnlocking():
            # allow creating new items, but keep the 'locked' state
            super()._decode(dataDict)
        return self

    def _fullName(self, wildCard: str | None = None) -> tuple[str | None, ...]:
        _full = ((wildCard,) if wildCard else self._parent._fullName(wildCard)) if self._parent else ()
        return _full + (self.name,)

    def _maxdepth(self) -> int:
        """Return the depth of this item.
        """
        return 1


#=========================================================================================
# ColumnGroup/ColumnItem - subclassed from _TraitColumnABC
#=========================================================================================

class ColumnItem(_TraitColumnABC):
    """Class defining the leaf items of a column-group tree-structure.
    These correspond to the actual table-columns.
    """
    _columnType: ColumnType = ColumnType.ITEM
    # individual columns have a visibility
    visible = Bool(default_value=True).tag(info='flag to indicate that the column is visible')

    def __init__(self, *, name: _MULTIINDEX = None,
                 visible: bool = True, movable: bool = False, internal: bool = False, locked: bool = False,
                 index: int = None):
        """Initialize the object with optional name, visibility, and various flags.

        :param _MULTIINDEX name: The name of the object (default is None).
        :param bool visible: Flag indicating if the object is visible (default is True).
        :param bool movable: Flag indicating if the object is movable (default is False).
        :param bool internal: Flag indicating if the object is internal (default is False).
        :param bool locked: Flag indicating if the object is locked (default is False).
        :param int index: The index of the object (default is None).
        """
        super().__init__(name, movable, internal, locked, index)
        with self._attributeUnlocking():
            self.visible = visible

    #-----------------------------------------------------------------------------------------
    # properties

    @property
    def columnId(self) -> str | None:
        """Retrieves the column identifier based on the 'name' attribute.
        If 'name' is a list or other iterable, it returns the last element of the iterable as the column identifier.

        :return: The column identifier as a string if 'name' is valid, otherwise None.
        :rtype: str | None

        .. note::
            - If 'name' is None, the method returns None.
            - If 'name' is a string, it directly returns the value of 'name'.
            - If 'name' is an iterable (such as a list or tuple), it returns the last item in the iterable.
        """
        if self.name is None:
            return
        return self.name if isinstance(self.name, str) else self.name[-1]


class ColumnGroup(_TraitColumnABC):
    """Class defining the branch items of a column-group tree-structure.
    This is a recursive container for ColumnGroups and ColumnItems.
    """
    _columnType: ColumnType = ColumnType.GROUP
    groupId = Unicode(allow_none=True).tag(info='column-group identifier')
    children: list[_TraitColumnABC] = RecursiveList().tag(info='list to hold a group of columns/nested-groups')

    def __init__(self, *children: _CHILDREN,
                 name: _MULTIINDEX = None, groupId: str | None = None,
                 movable: bool = False, internal: bool = False, locked: bool = False,
                 index: int = None, **kwargs):
        """Initialize the object with optional children, name, group ID, and various flags.

        :param _CHILDREN children: Positional arguments representing child elements. The first item may be a list.
        :param _MULTIINDEX name: The name of the object (default is None).
        :param str groupId: The group ID of the object (default is None).
        :param bool movable: Flag indicating if the object is movable (default is False).
        :param bool internal: Flag indicating if the object is internal (default is False).
        :param bool locked: Flag indicating if the object is locked (default is False).
        :param int index: The index of the object (default is None).
        :param kwargs: Additional keyword arguments. Only 'children' is expected.

        :raises TypeError: If both positional children and 'children' keyword argument are specified.
        :raises TypeError: If unexpected keyword arguments are provided.

        .. note::
           - If 'children' keyword argument is provided, it overrides the positional arguments.
           - The 'children' keyword argument should be a list or a single item that can be converted to a list.
        """
        super().__init__(name, movable, internal, locked, index)
        # *children is presented as a tuple, first item may be a list
        if (kwChildren := kwargs.pop(_CHILDRENTAG, [])) and children:
            raise TypeError(f"Specify either positional arguments or the {_CHILDRENTAG!r} keyword argument, not both.")
        if kwargs:
            # check for any non-required keywords
            raise TypeError(f'Unexpected keyword arguments: {list(kwargs.keys())}')
        if kwChildren:
            # use the kwChildren argument instead of the positional arguments
            children = kwChildren if isinstance(kwChildren, list) else [kwChildren]
        with self._attributeUnlocking():
            self.groupId = groupId
            self.children = self._validatedChildren(*children)

    #-----------------------------------------------------------------------------------------
    # properties

    @property
    def visible(self) -> bool:
        """Return True if any of its direct children are visible.
        """
        # group visibility is derived from children, a single visible child will imply that a parent is visible
        return any(att.visible for att in self.children)

    @property
    def _isLeaf(self) -> bool:
        """Indicates whether the current object is a leaf node.

        A leaf node is a terminal element in a tree-like structure that does
        not have any child elements. This implementation always returns False,
        indicating that the object is not a leaf node; it represents a virtual group of columns.

        :return: False, as the object is not a leaf node.
        :rtype: bool
        """
        return False

    @property
    def fullName(self, wildCard: str | None = None) -> tuple[str | None, ...]:
        """Return the full-name as a tuple, includes the names of the parents.

        :param str wildCard: A single character to replace the names (default is None).
        :return: A tuple containing the full name, including the names of the parents.
        :rtype: tuple[str | None, ...]

        :raises TypeError: If the method is called on an object that is not a `ColumnItem`.

        .. note::
           - This method raises a TypeError indicating it can only be applied to `ColumnItem` instances.
        """
        raise TypeError(f'{self.__class__.__name__}.addChildren: can only apply to {ColumnItem.__name__}s')

    #-----------------------------------------------------------------------------------------
    # methods

    def addChildren(self, *children: _CHILDREN):
        """Add the children to the group.

        :param _CHILDREN children: Children to be added. Can be provided as comma-separated items or a single list.
        """
        self.children += self._validatedChildren(*children)

    def clear(self):
        """Remove all children from the group.
        """
        for ch in self.children:
            # set the parent of the child to fix the hierarchy
            ch._setParent(None)
        self.children = []

    def traverse(self, includeBranches: bool = True, includeLeaves: bool = True,
                 recursive: bool = True) -> typing.Generator[TraitColumnABCType, None, None]:
        """Traverse the tree.

        :param bool includeBranches: Whether to include branch nodes in the traversal (default is True).
        :param bool includeLeaves: Whether to include leaf nodes in the traversal (default is True).
        :param bool recursive: Whether to traverse the tree recursively (default is True).
        :return: A generator yielding the nodes of the tree based on the specified parameters.
        :rtype: typing.Generator[TraitColumnABCType, None, None]

        .. note::
           - If `includeBranches` is True, the current node is yielded.
           - If `recursive` is True, the method traverses the children recursively.
           - If `recursive` is False, only the immediate children are considered,
                filtered by `includeBranches` and `includeLeaves`.
        """
        if includeBranches:
            yield self
        if recursive:
            for ch in self.children:
                yield from ch.traverse(includeBranches, includeLeaves, recursive)
        else:
            yield from filter(lambda ch: (ch._isLeaf and includeLeaves) or
                                         (not ch._isLeaf and includeBranches), self.children)

    #-----------------------------------------------------------------------------------------
    # implementation

    def _setExcludeFlag(self):
        """Block all Changes to self and children.
        """
        super()._setExcludeFlag()
        for att in self.children:
            # a little hard-coded for now :|
            att._setExcludeFlag()

    def _clearExcludeFlag(self):
        """Unblock all changes to self and children.
        """
        super()._clearExcludeFlag()
        for att in self.children:
            att._clearExcludeFlag()

    def _validatedChildren(self, *children: _CHILDREN) -> list[TraitColumnABCType]:
        """Validate the children.
        Check that all are the correct type, and children is defined correctly.
        If all correct, update their parents. Calling method will either append and overwrite children.

        :param _CHILDREN children: Children to be validated. Can be provided as comma-separated items or a single list/tuple.
        :return: A list of validated children.
        :rtype: list[TraitColumnABCType]

        :raises TypeError: If any child is not of type [_TraitColumnABC], or if a child's name already exists.
        :raises ValueError: If there are duplicate names among the children to be added.

        .. note::
           - If a single list or tuple is provided as the only argument, it will be unpacked.
           - Each child's parent will be set to the current instance to maintain the hierarchy.
        """
        if len(children) == 1 and isinstance(children[0], list | tuple):
            children = children[0]
        for idx, ch in enumerate(children):
            if not isinstance(ch, _TraitColumnABC):
                raise TypeError(f'{self.__class__.__name__}.addChildren: '
                                f'children must all be of type [{ColumnGroup.__name__}, {ColumnItem.__name__}], '
                                f'item {idx + 1} is type({type(ch).__name__})')
            if any(ch.name == myChild.name for myChild in self.children):
                raise TypeError(f'{self.__class__.__name__}.addChildren: '
                                f'child.name {ch.name!r} already exists')
        names = Counter(ch.name for ch in children)
        if len(names) != len(children):
            raise ValueError(f'{self.__class__.__name__}.addChildren: contains duplicate names')
        for ch in children:
            # set the parent of the child to fix the hierarchy
            ch._setParent(self)
        return list(children)

    def _decode(self, dataDict) -> ColumnGroupType:
        """Populate/update self with data from dataDict.
        """
        with self._attributeUnlocking():
            super()._decode(dataDict)
            # recover the parents of the children
            for ch in self.children:
                ch._setParent(self)
        return self

    def _maxdepth(self) -> int:
        """Recursively calculate the maxmimum depth of the tree.
        """
        return super()._maxdepth() + (max(ch._maxdepth() for ch in self.children) if self.children else 0)


ColumnGroup.register()
ColumnItem.register()
