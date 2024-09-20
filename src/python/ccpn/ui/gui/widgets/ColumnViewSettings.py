"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:24 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from collections import Counter

from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.core.lib.DataFrameObject import DataFrameObject


class ColumnViewSettingsPopup(CcpnDialogMainWidget):
    FIXEDHEIGHT = False
    FIXEDWIDTH = True

    def __init__(self, table, dataFrameObject=None, parent=None, hiddenColumns=None, title='Column Settings', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, minimumSize=(250, 250), **kwds)

        self.tableHandler = table

        # self.dataFrameObject = dataFrameObject
        self.widgetColumnViewSettings = ColumnViewSettings(self.mainWidget, table=table,
                                                           dfObject=dataFrameObject,
                                                           grid=(0, 0))

        self.setCloseButton(callback=self._close, tipText='Close')
        self.setDefaultButton(self.CLOSEBUTTON)

    def getHiddenColumns(self):
        return self.widgetColumnViewSettings.hiddenColumns

    # def setHiddenColumns(self, texts):
    #     self.widgetColumnViewSettings._hiddenColumns = texts

    def _close(self):
        """Save the hidden columns to the table class. So it remembers when you open again the popup
        """
        # hiddenColumns = self.getHiddenColumns()
        # # self.dataFrameObject.hiddenColumns = hiddenColumns
        # self.tableHandler.setHiddenColumns(hiddenColumns, False)
        self.accept()

        return self.getHiddenColumns()

    def _cleanupDialog(self):
        """Clean up widgets that are causing seq-fault on garbage-collection.
        """
        # NOTE:ED - these NEED to be cleaned, one causes a threading error if not deleted
        self.tableHandler = None
        self.widgetColumnViewSettings.deleteLater()


#=========================================================================================
# ColumnViewSettings
#=========================================================================================

SEARCH_MODES = ['Literal', 'Case Sensitive Literal', 'Regular Expression']
CheckboxTipText = 'Select column to be visible on the table.'


class ColumnViewSettings(Frame):
    """ hide show check boxes corresponding to the table columns """

    def __init__(self, parent=None, table=None, dfObject=None, direction='v', **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        self.direction = direction

        # only need the pd.DataFrame
        if isinstance(dfObject, DataFrameObject):
            self._df = dfObject.dataFrame
        elif isinstance(dfObject, pd.DataFrame):
            self._df = dfObject
        else:
            raise ValueError(f'dfObject is the wrong type - {type(dfObject)}')

        self.tableHandler = table
        self.checkBoxes = []
        self._hideColumnWidths = {}

        self._setWidgets()

    def _setWidgets(self):

        self.filterLabel = Label(self, text='Display Columns', grid=(0, 0))
        # self.widgetFrame = Frame(self, setLayout=True, margins=(5, 5, 5, 5), grid=(1, 0))

        self.widgetFrame = ScrollableFrame(parent=self,
                                           showBorder=False, setLayout=True,
                                           grid=(1, 0))

        self.buttonList = ButtonList(self,
                                     texts=['Select All', 'Deselect All'],
                                     callbacks=[self._setCheckBoxes, self._clearCheckBoxes],
                                     grid=(2, 0), gridSpan=(1, 2))

        self._initCheckBoxes()

    def _initCheckBoxes(self):
        i = 1
        if columns := list(self._df.columns):
            hiddenColumns = self.tableHandler.hiddenColumns or []

            for i, colum in enumerate(columns):

                # always ignore the _internal columns
                if colum not in self.tableHandler._internalColumns:
                    chcked = colum not in hiddenColumns

                    if isinstance(self._df.columns, pd.MultiIndex):
                        cc = Counter(colum)
                        if len(cc) == 1:
                            txt = colum and colum[0] or ''
                        else:
                            txt = ' - '.join(colum)
                    else:
                        txt = str(colum)

                    if self.direction == 'v':
                        i += 1
                        cb = CheckBox(self.widgetFrame, text=txt, grid=(i, 1), callback=self._checkBoxCallBack,
                                      checked=chcked,
                                      hAlign='l', tipText=CheckboxTipText)

                    else:
                        cb = CheckBox(self.widgetFrame, text=txt, grid=(1, i), callback=self._checkBoxCallBack,
                                      checked=chcked,
                                      hAlign='l', tipText=CheckboxTipText)

                    cb.setObject(colum)
                    self.checkBoxes.append(cb)

    @property
    def hiddenColumns(self):
        return self.tableHandler.hiddenColumns

    def _setCheckBoxes(self, *args):
        """Tick all the checkboxes to show all the columns.
        """
        for cb in reversed(self.checkBoxes):
            cb.setChecked(True)
            self._checkBoxUpdate(cb)

    def _clearCheckBoxes(self, *args):
        """Clear all the checkboxes to hide all the columns.
        """
        # first column always becomes the default
        for cb in reversed(self.checkBoxes):
            cb.setChecked(False)
            self._checkBoxUpdate(cb)

        # check the last check box and disable if necessary
        self._checkLastCheckbox()

    def _checkBoxCallBack(self):
        """Handle clicking a checkbox.
        """
        currentCheckBox = self.sender()
        self._checkBoxUpdate(currentCheckBox)

    def _checkBoxUpdate(self, currentCheckBox):
        if not self.checkBoxes or not currentCheckBox:
            return

        if not (obj := currentCheckBox.getObject()):
            return
        i = self._df.columns.get_loc(obj)

        checkedBoxes = []
        for checkBox in self.checkBoxes:
            checkBox.setEnabled(True)
            if checkBox.isChecked():
                checkedBoxes.append(checkBox)

        if checkedBoxes:
            if currentCheckBox.isChecked():
                self.tableHandler._showColumnName(self._df.columns[i])
            else:
                self.tableHandler._hideColumnName(self._df.columns[i])
        else:
            # always display at least one column, disables the last checkbox
            currentCheckBox.setEnabled(False)
            currentCheckBox.setChecked(True)

        self._checkLastCheckbox()

    def _checkLastCheckbox(self):
        """Check whether there is a single checkbox remaining and disable as necessary.
        """
        checkedBoxes = list(filter(lambda ch: ch.isChecked(), self.checkBoxes))

        if len(checkedBoxes) == 1:
            # always display at least one column, disables the last checkbox
            checkedBoxes[0].setEnabled(False)
            checkedBoxes[0].setChecked(True)

    def updateWidgets(self, table):
        self.tableHandler = table
        if self.checkBoxes:
            for cb in self.checkBoxes:
                cb.deleteLater()
        self.checkBoxes = []
        self._initCheckBoxes()

    # def _hideColumn(self, i, name):
    #     self.tableHandler.hideColumn(i)
    #     if name not in self.tableHandler._hiddenColumns:
    #         self.tableHandler._hiddenColumns.append(name)
    #
    # def _showColumn(self, i, name):
    #     self.tableHandler.showColumn(i)
    #     self.tableHandler.resizeColumnToContents(i)
    #     if name in self.tableHandler._hiddenColumns:
    #         self.tableHandler._hiddenColumns.remove(name)

    def refreshHiddenColumns(self):
        # show/hide the columns in the list
        columns = self.tableHandler.columnTexts

        for i, colName in enumerate(columns):
            if colName in self.tableHandler._hiddenColumns:
                self.tableHandler._hideColumnName(colName)
            else:
                self.tableHandler._showColumnName(colName)
