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
__dateModified__ = "$dateModified: 2024-11-01 19:40:51 +0000 (Fri, November 01, 2024) $"
__version__ = "$Revision: 3.2.9 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-02-17 10:41:16 +0100 (Fri, February 17, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from dataclasses import dataclass, field


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

from ccpn.util.DataEnum import DataEnum
from dataclasses import dataclass, field
from contextlib import contextmanager
from ccpn.util.traits.CcpNmrJson import CcpNmrJson, TraitJsonHandlerBase, Constants
from ccpn.util.traits.CcpNmrTraits import List, Path, RecursiveList, Enum, Unicode, Bool, Int
from traitlets import HasTraits


class MIColumnType(Enum):
    GROUP = 0
    ITEM = 1


class _TraitColumnABC(CcpNmrJson):
    _columnType: MIColumnType
    classVersion = 1.0  # for json saving
    saveAllTraitsToJson = True
    keysInOrder = True
    name = Unicode(allow_none=True).tag(info='column name')
    groupId = Unicode(allow_none=True).tag(info='column group identifier')
    movable = Bool(default_value=False).tag(info='flag to indicate that the column can be moved within its parent')
    index = Int(allow_none=True, default_value=None).tag(info='index of the column if re-ordering is allowed')
    # attributes to handle ignore _metadata in the json-dumps
    # as may contain times/dates that stop quick comparisons
    # currently hard-coded, assumes that recursion is handled by subclass, e.g, see TraitColumnGroup
    _excludeMetadata = False
    _excludeMetadataLast = False
    _excludeDepth = 0

    def __init__(self, name: str, groupId: str, movable: bool, index: int):
        super().__init__()
        self.name = name
        self.groupId = groupId
        self.movable = movable
        self.index = index

    @contextmanager
    def _excludeBlock(self):
        """Exclude metadata from the json-dumps.
        """
        self._setExcludeFlag()
        try:
            yield  # yield control to the calling process
        finally:
            self._clearExcludeFlag()

    def _setExcludeFlag(self):
        """Block all Changes to the dict
        """
        # block metadata on first entry
        if self._excludeDepth == 0:
            # remember last state
            self._excludeMetadataLast = self._excludeMetadata
            self._excludeMetadata = True
        self._excludeDepth += 1

    def _clearExcludeFlag(self):
        """Unblock all changes to the dict
        """
        if self._excludeDepth > 0:
            self._excludeDepth -= 1
            # unblock metadata on last exit
            if self._excludeDepth == 0:
                self._excludeMetadata = self._excludeMetadataLast
        else:
            raise RuntimeError(f'{self} Exclude already at 0')

    def toJsonNoMetaData(self, **kwds):
        with self._excludeBlock():
            return self.toJson(**kwds)

    def _encode(self):
        """Return self as list of (trait, value) tuples
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


class ColumnGroup(_TraitColumnABC):
    _columnType: MIColumnType = MIColumnType.GROUP
    children = RecursiveList().tag(info='list to hold a group of columns/nested groups')

    def __init__(self, *children: _TraitColumnABC,
                 name: str = '', groupId: str = '',
                 movable: bool = False, index: int = None):
        super().__init__(name, groupId, movable, index)
        self.children = children

    def _setExcludeFlag(self):
        """Block all Changes to the dict
        """
        super()._setExcludeFlag()
        for att in self.children:
            # a little hard-coded for now :|
            att._setExcludeFlag()

    def _clearExcludeFlag(self):
        """Unblock all changes to the dict
        """
        super()._clearExcludeFlag()
        for att in self.children:
            att._clearExcludeFlag()

    @property
    def visible(self):
        """Return True if any of its direct children are visible.
        """
        return any(att.visible for att in self.children)


class ColumnItem(_TraitColumnABC):
    _columnType: MIColumnType = MIColumnType.ITEM
    visible = Bool(default_value=True).tag(info='flag to indicate that the column is visible')

    def __init__(self, *, name: str = '', groupId: str = '',
                 visible: bool = True, movable: bool = False, index: int = None):
        super().__init__(name, groupId, movable, index)
        self.visible = visible
