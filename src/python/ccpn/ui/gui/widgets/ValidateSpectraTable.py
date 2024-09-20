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
__dateModified__ = "$dateModified: 2024-09-13 15:20:23 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-10-05 14:38:53 +0100 (Wed, October 05, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore
import pandas as pd
from ccpn.ui.gui.widgets.Column import ColumnClass, Column
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.table._TableModel import _TableModel
from ccpn.ui.gui.widgets.table._TableCommon import EDIT_ROLE, DISPLAY_ROLE, TOOLTIP_ROLE, \
    BACKGROUND_ROLE, CHECK_ROLE, ICON_ROLE, ALIGNMENT_ROLE, CHECKABLE, ENABLED, SELECTABLE, CHECKED, UNCHECKED
from ccpn.util.Common import NOTHING


#=========================================================================================
# ValidateSpectraTable
#=========================================================================================

class _ValidateModel(_TableModel):
    defaultFlags = ENABLED | SELECTABLE | CHECKABLE

    def _getDisplayRole(self, colDef, obj):
        # booleans are returned as None so that only the checkbox and not the 'True|False' text appears
        return None if isinstance((value := colDef.getFormatValue(obj)), bool) else value

    def _getCheckRole(self, colDef, obj):
        # change booleans state to CHECKED/UNCHECKED to make checkboxes appear in table-view
        if isinstance((value := colDef.getValue(obj)), bool):
            return CHECKED if value else UNCHECKED

        return None

    getAttribRole = {DISPLAY_ROLE   : _getDisplayRole,
                     CHECK_ROLE     : _getCheckRole,
                     ICON_ROLE      : lambda self, colDef, obj: colDef.getIcon,
                     EDIT_ROLE      : lambda self, colDef, obj: colDef.getEditValue and colDef.getEditValue(obj),
                     TOOLTIP_ROLE   : lambda self, colDef, obj: colDef.tipText,
                     BACKGROUND_ROLE: lambda self, colDef, obj: colDef.getColor and colDef.getColor(obj),
                     ALIGNMENT_ROLE : lambda self, colDef, obj: colDef.alignment
                     }

    setAttribRole = {
        EDIT_ROLE : lambda self, colDef, obj, value: colDef.setEditValue and colDef.setEditValue(obj, value),
        CHECK_ROLE: lambda self, colDef, obj, value: colDef.setEditValue and colDef.setEditValue(obj, True if (
                value == CHECKED) else False)
        }

    def data(self, index, role=DISPLAY_ROLE):
        # special control over the object properties
        if index.isValid():
            # get the source cell
            row, col = self._sortIndex[index.row()], index.column()
            obj = self._view._objects[row]
            colDef = self._view._columnDefs._columns[col]

            if (func := self.getAttribRole.get(role)) and (funcVal := func(self, colDef, obj)) is not None:
                return funcVal

        return super().data(index, role)

    def setData(self, index, value, role=EDIT_ROLE) -> bool:
        # special control over the object properties
        if index.isValid():
            row, col = self._sortIndex[index.row()], index.column()
            obj = self._view._objects[row]
            colDef = self._view._columnDefs._columns[col]

            if (func := self.setAttribRole.get(role)):
                func(self, colDef, obj, value)

                self._view.viewport().update()  # repaint the view
                return True

        return super().setData(index, role, value)


class ValidateSpectraTable(Table):
    """A table to contain the list of spectra and associated spectrum filePaths
    """

    styleSheet = """QTableView {
                        background-color: transparent;
                        alternate-background-color: transparent;
                        border: %(_BORDER_WIDTH)spx solid palette(mid);
                        border-radius: 2px;
                        gridline-color: %(_GRID_COLOR)s;
                        /* use #f8f088 for yellow selection */
                        selection-background-color: qlineargradient(
                                                        x1: 0, y1: -200, x2: 0, y2: 200,
                                                        stop: 0 palette(highlight), 
                                                        stop: 1 palette(base)
                                                    );
                    }
                    QHeaderView::section {
                        background-color: transparent;
                        border: 0px;
                    }
                    """

    tableModelClass = _ValidateModel

    def __init__(self, parent, *args, **kwds):
        """Initialise the table

        :param parent: parent widget.
        :param args: additional arguments to pass to table-initialisation.
        :param kwds: additional keywords to pass to table-initialisation.
        """
        super().__init__(parent, *args, **kwds)

        # needs to be a pixmap for the table-model
        self._pathPixmap = Icon('icons/directory').pixmap(24, 24)

        # set the table _columns
        self._columnDefs = ColumnClass([])
        self._columnDefs._columns = [
            Column('id', 'name', tipText='Spectrum name', alignment=QtCore.Qt.AlignVCenter),
            Column('dimension', 'dimensionCount', tipText='Number of dimensions', alignment=QtCore.Qt.AlignVCenter),
            Column('dataFormat', 'dataFormat', tipText='Data format', alignment=QtCore.Qt.AlignVCenter),
            Column('filePath', 'filePath', tipText='File path', alignment=QtCore.Qt.AlignVCenter),
            Column('load', None, tipText='Load spectrum', getIcon=self._pathPixmap, alignment=QtCore.Qt.AlignVCenter),
            ]

        self.populateTable()

    #=========================================================================================
    # methods
    #=========================================================================================

    def populateTable(self, spectra=None, editable=True):
        """Populate the table from the current spectrum.

        :param spectra: list of spectra
        :param editable: True/False, for enabling/disabling editing, defaults to True.
        :return:
        """
        if spectra is not None:
            self._objects = spectra
            specData = [(spec.id, spec.dimensionCount, spec.dataFormat, spec.path, None) for spec in spectra]

            df = pd.DataFrame(specData, columns=self._columnDefs.headings)

        else:
            self._objects = []
            df = pd.DataFrame(columns=self._columnDefs.headings)

        self.updateDf(df, resize=True, setHeightToRows=False, setWidthToColumns=False, setOnHeaderOnly=True)

        for row, spec in enumerate(self._objects):
            # could use objectModel here
            self.setBackground(row, 3, 'palegreen')

        self.setTableEnabled(editable)
        self.model().dataChanged.connect(self._dataChanged)

    def _dataChanged(self, *args):
        """Emit tableChanged signal if the table has been edited.

        :param args: catch optional arguments from event.
        :return:
        """
        self.tableChanged.emit()

    def setTableEnabled(self, value):
        """Enable/Disable the table.

        :param value: True/False.
        :return:
        """
        self.setEnabled(value)
        # not sure whether to disable the table or just disable the editing and menu items
        self.setEditable(value)
        for action in self._actions:
            action.setEnabled(value)

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    def setTableMenu(self, tableMenuEnabled=NOTHING):
        """Set up the context menu for the main table.
        """
        # no options from the super-class are required
        self._actions = []

        super().setTableMenu(tableMenuEnabled=False)

    #=========================================================================================
    # Selection/Action methods
    #=========================================================================================

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        :param selected: table indexes selected
        :param deselected: table indexes deselected
        """
        pass

    def actionCallback(self, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        """
        pass
