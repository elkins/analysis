"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2025-01-09 20:41:19 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-11-24 12:32:46 +0100 (Thu, November 24, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd

from ccpn.ui.gui.widgets.Column import ColumnClass, Column
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.table._TableDelegates import _SimplePulldownTableDelegate


METADATACOLUMNS = ['name', 'parameter']


#=========================================================================================
# MetadataTable
#=========================================================================================

class MetadataTable(TableABC):
    """A table to contain metadata of a core object.
    """

    TableDelegateClass = _SimplePulldownTableDelegate

    def __init__(self, parent, obj=None, *args, **kwds):
        """Initialise the table

        :param parent: parent widget.
        :param spectrum: target spectrum.
        :param args: additional arguments to pass to table-initialisation.
        :param kwds: additional keywords to pass to table-initialisation.
        """
        super().__init__(parent, *args, **kwds)

        # set the core-object specific information
        self.obj = obj

        # set the table _columns
        self._columnDefs = ColumnClass([])
        self._columnDefs._columns = [Column(col, lambda row: True) for col in METADATACOLUMNS]

        self._rightClickedTableIndex = None  # last selected item in a table before raising the context menu. Enabled with mousePress event filter

    @property
    def _df(self):
        """Return the Pandas-dataFrame holding the data.
        """
        return self.model().df

    #=========================================================================================
    # methods
    #=========================================================================================

    def getMetadata(self):
        """Get the metadata from the table.
        """
        return tuple(self._df.itertuples(index=False))

    def populateTable(self, metadata=None, editable=True):
        """Populate the table from the current core-object.
        If metadata are not specified, then existing values are used.

        :param metadata: dict of metadata.
        :param editable: True/False, for enabling/disabling editing, defaults to True.
        :return:
        """
        if metadata is not None:
            self._metadata = metadata

        if self._metadata is not None:
            df = pd.DataFrame(self._metadata, columns=METADATACOLUMNS)

        else:
            df = pd.DataFrame(columns=METADATACOLUMNS)

        self.updateDf(df, resize=True, setHeightToRows=True, setWidthToColumns=True, setOnHeaderOnly=True)

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

    def addTableMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        return self._thisTableMenu
