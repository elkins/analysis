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
__dateModified__ = "$dateModified: 2025-01-09 20:41:18 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-08-17 13:51:55 +0100 (Wed, August 17, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore
import pandas as pd

from ccpn.core.lib.SpectrumLib import MagnetisationTransferTypes, \
    MagnetisationTransferParameters, MagnetisationTransferTuple
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.table._TableDelegates import _SmallPulldown, _SimplePulldownTableDelegate


EDIT_ROLE = QtCore.Qt.EditRole


#=========================================================================================
# MagnetisationTransferTable
#=========================================================================================

class MagnetisationTransferTable(TableABC):
    """A table to contain the list of magnetisation-transfers for a spectrum.
    Transfers are set for a particular experiment-type or user defined.
    """

    TableDelegateClass = _SimplePulldownTableDelegate

    def __init__(self, parent, spectrum=None, *args, **kwds):
        """Initialise the table

        :param parent: parent widget.
        :param spectrum: target spectrum.
        :param args: additional arguments to pass to table-initialisation.
        :param kwds: additional keywords to pass to table-initialisation.
        """
        super().__init__(parent, *args, **kwds)

        # set the spectrum-specific information
        self.spectrum = spectrum
        self.dimensions = self.spectrum and self.spectrum.dimensionCount or 0
        self._magTransfers = self.spectrum and self.spectrum.magnetisationTransfers or None

        # define the column definitions
        colDefs = ((int, [val + 1 for val in range(self.dimensions)]),
                   (int, [val + 1 for val in range(self.dimensions)]),
                   (str, MagnetisationTransferTypes),
                   (bool, [True, False]),
                   )

        # create the column objects
        _cols = [
            (MagnetisationTransferTypes[ii], lambda row: True, None, None, None)
            for ii, col in enumerate(MagnetisationTransferParameters)
            ]

        # set the table _columns
        self._columnDefs = ColumnClass(_cols)

        for ii, (colType, options) in enumerate(colDefs):
            # define the edit widget for each column
            col = self._columnDefs.columns[ii]
            col.editClass = _SmallPulldown
            col.editKw = {'texts': options}

        self._rightClickedTableIndex = None  # last selected item in a table before raising the context menu. Enabled with mousePress event filter

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSortingEnabled(False)

    @property
    def _df(self):
        """Return the Pandas-dataFrame holding the data.
        """
        return self.model().df

    #=========================================================================================
    # methods
    #=========================================================================================

    def getMagnetisationTransfers(self):
        """Get the magnetisation-transfers from the table.
        """
        return tuple(MagnetisationTransferTuple(*row) for row in self._df.itertuples(index=False))

    def populateTable(self, magnetisationTransfers=None, editable=True):
        """Populate the table from the current spectrum.
        If magnetisation-transfers are not specified, then existing values are used.

        :param magnetisationTransfers: tuple/list of MagnetisationTransferTuples.
        :param editable: True/False, for enabling/disabling editing, defaults to True.
        :return:
        """
        if magnetisationTransfers is not None:
            self._magTransfers = magnetisationTransfers

        if self._magTransfers is not None:
            df = pd.DataFrame(self._magTransfers, columns=MagnetisationTransferParameters)

        else:
            df = pd.DataFrame(columns=MagnetisationTransferParameters)

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
        menu = self._thisTableMenu

        # no options from the super-class are required
        self._actions = [menu.addAction('New', self._newTransfer),
                         menu.addAction('Remove selected', self._removeTransfer)
                         ]

        return menu

    def _newTransfer(self):
        """Add new magnetisation-transfer to the table.
        """
        mt = list(self._magTransfers)
        mt.append(MagnetisationTransferTuple(1, 2, 'onebond', False))
        self._magTransfers = tuple(mt)
        self.populateTable(self._magTransfers)
        self._dataChanged()

    def _removeTransfer(self):
        """Remove the selected magnetisation-transfer from the table.
        """
        model = self.selectionModel()
        if selection := (model and model.selectedRows()):
            _sortIndex = self.model()._sortIndex
            for idx in selection:
                row = _sortIndex[idx.row()]

                mt = list(self._magTransfers)
                del mt[row]

                self._magTransfers = tuple(mt)
                self.populateTable(self._magTransfers)
                self._dataChanged()
                return
