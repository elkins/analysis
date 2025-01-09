"""
A custom Table using Columns and a standard DataFrame
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
__dateModified__ = "$dateModified: 2025-01-09 20:29:50 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2025-01-09 12:04:37 +0000 (Thu, January 9, 2025) $"
#=========================================================================================
# Start of code
#=========================================================================================


import pandas as pd
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.Column import Column
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.table._TableCommon import INDEX_ROLE
from ccpn.util.OrderedSet import OrderedSet


class CustomDataFrameTable(Table):
    _defaultEditable = False
    _enableSearch = True
    _enableDelete = False
    _enableExport = True
    _enableCopyCell = True

    def __init__(self, parent, dataFrame=None, columns=None, **kwds):
        super().__init__(parent, **kwds)
        self._columnDefs = self.getColumnDefs(columns)
        if dataFrame is None:
            dataFrame = pd.DataFrame()
        self.setDataFrame(dataFrame)

    def getColumnDefs(self, columns=None):
        """ Overide in subclass """
        self._columnDefs = ColumnClass([])
        columns = columns or []
        self._columnDefs._columns = columns
        return self._columnDefs

    def setDataFrame(self, dataFrame):
        self._buildColumnsFromDataFrame(dataFrame)

    def getSelectedObjects(self):
        """
        :return: list of Pandas series object corresponding to the selected row(s).
        """
        sRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0] for idx in self.selectedIndexes())
        if not self._objects:
            return []
        return [self._objects[row] for row in sRows if row is not None and row is not False]

    def getCurrentObject(self):
        """ Deprecated, backcompatibility only"""
        return self.getSelectedObjects()

    @staticmethod
    def _checkColumns(columnDefs, dataframeToBeSet):
        """
        Ensure columns  are compatible between ColumnDefs and setting DataFrame
        Cases:
        1) columnDefs have more definitions than the given DataFrame to be set
        2) columnDefs have fewer definitions than the given DataFrame to be set

        """

        headingFromDefs = [col.rawDataHeading for col in columnDefs._columns]
        columnFromDf = dataframeToBeSet.columns

        missingColumnsInDf = [h for h in headingFromDefs if h not in columnFromDf]
        missingHeadings = [c for c in columnFromDf if c not in headingFromDefs]

        ## case: Heading are more than the columns in the DataFrame.
        ## Update the dataframe with none values
        if len(missingColumnsInDf):
            dataframeToBeSet[missingColumnsInDf] = [None] * len(missingColumnsInDf)

        ## case: Heading defs are fewer than the columns in the DataFrame.
        ##  add definitions but set as internal so to DON'T show these on table.
        if len(missingHeadings) > 0:
            oldHeadings = columnDefs._columns
            newHeadings = []
            for missingHeading in missingHeadings:
                c = Column(headerText=missingHeading,
                           getValue=missingHeading,
                           rawDataHeading=missingHeading,
                           isInternal=True,
                           isHidden=True)
                newHeadings.append(c)
            columnDefs.setColumns(oldHeadings + newHeadings)

    def _buildColumnsFromDataFrame(self, dataFrame):
        hiddenColumns = []
        _internalColumns = []
        data = {}
        self._checkColumns(self._columnDefs, dataFrame)
        for col in self._columnDefs._columns:
            values = dataFrame[col.rawDataHeading].values
            data[col.headerText] = values
            if col.isHidden:
                hiddenColumns.append(col.headerText)
            if col.isInternal:
                _internalColumns.append(col.headerText)
        df = pd.DataFrame(data)
        frames = [s for h, s in dataFrame.iterrows()]
        self._objects = frames

        cols = list(self._internalColumns) if self._internalColumns else []
        cols.extend(_internalColumns)
        self.setInternalColumns(cols)
        self.setDefaultColumns(hiddenColumns)
        self.updateDf(df)
        self.postUpdateDf()

    def getObjects(self):
        return self._objects
