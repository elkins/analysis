"""
A widget to handle the Series Units for the SpectrumGroup popup
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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-07-30 17:22:58 +0100 (Tue, July 30, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-05-28 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


from PyQt5 import QtWidgets, QtCore, QtGui
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.core.lib.SeriesUnitConverter import SERIESUNITS
from ccpn.core.SpectrumGroup import SeriesTypes
from ccpn.ui.gui.widgets.HLine import HLine

QUANTITY = 'Quantity'
TYPE = 'Type'
UNIT = 'Unit'


class SeriesUnitWidget(ScrollableFrame):
    quantitySelectionChanged = QtCore.pyqtSignal(str)
    unitSelectionChanged = QtCore.pyqtSignal(str)
    typeSelectionChanged = QtCore.pyqtSignal(str)
    deselectedAllSignal = QtCore.pyqtSignal()

    def __init__(self, parent, callback=None, labelMinimumWidth=100,  **kwds):
        super().__init__(parent, minimumSizes=(50,150), margins=(0, 10, 0, 10), setLayout=True, **kwds)
        self._globalCallback = callback

        i = 0
        quantitySelections = list(SERIESUNITS.keys())
        labelQuantity = Label(self, text=QUANTITY, grid=(i, 0), minimumWidth=labelMinimumWidth)
        self.quantitySelection = RadioButtons(self, texts=quantitySelections,
                                              callback=self._quantitySelectionCallback, selectedInd=None,
                                              grid=(i, 1), direction='gv', numGridRows=4,
                                              hAlign='l')
        self.quantitySelection.deselectAll() # Ensure we don't prepopulate any selection
        i += 1
        HLine(self, style=QtCore.Qt.DashLine, grid=(i, 0), gridSpan=(1, 1), height=10)
        i += 1
        labelUnit = Label(self, text=UNIT, grid=(i, 0), minimumWidth=labelMinimumWidth)
        self.unitsSelection = RadioButtons(self, texts=[], callback=self._unitSelectionCallback, grid=(i, 1), hAlign='l')

        i += 1
        HLine(self, style=QtCore.Qt.DashLine, grid=(i, 0), gridSpan=(1, 1), height=10)
        i += 1
        labelType = Label(self, text=TYPE, grid=(i, 0), minimumWidth=labelMinimumWidth)
        self.dataTypeSelection = RadioButtons(self, texts=[str(val.description) for val in SeriesTypes],
                                              callback=self._typeSelectionCallback, grid=(i, 1), hAlign='l')
        self.dataTypeSelection.deselectAll()
        HLine(self, style=QtCore.Qt.DashLine, grid=(i, 0), gridSpan=(1, 1), height=10)
        i += 1
        # self._quantitySelectionCallback()
        self.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)  # Align top and left
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def _quantitySelectionCallback(self, emitSignals=True):
        selected = self.quantitySelection.getSelectedText()
        selectedUnit = SERIESUNITS.get(selected)
        if selectedUnit is not None:
            unit = selectedUnit(1, selectedUnit.SI_baseUnit)
            self.unitsSelection.setButtons(unit.unitsSelection, tipTexts=unit.unitsTipTextSelection ,selectedInd=0, direction='h',)
            self._toggleDataType(unit)
        if emitSignals:
            self._callback()
            self.quantitySelectionChanged.emit(selected)

    def _toggleDataType(self, unitObject):
        allowed = [seriesType.description for seriesType in unitObject._allowedDataTypes]
        selected = self.dataTypeSelection.getSelectedText()
        if selected not in allowed:
            self.dataTypeSelection.deselectAll()
            if len(allowed) == 1:
                self.dataTypeSelection.set(allowed[0], silent=True)
        self.dataTypeSelection.setEnabledTexts(allowed)

    def _unitSelectionCallback(self):
        self._callback()
        vv = self.unitsSelection.getSelectedText()
        self.unitSelectionChanged.emit(vv)

    def _typeSelectionCallback(self):
        self._callback()
        vv = self.dataTypeSelection.getSelectedText()
        self.typeSelectionChanged.emit(vv)


    def _callback(self, *args, **kwargs):
        values = self.getValues()
        if self._globalCallback is  not None:
            self._globalCallback(values)

    def getValues(self):
        """Get a dict of selected value"""
        dd = {
            QUANTITY: self.quantitySelection.getSelectedText(),
            UNIT: self.unitsSelection.getSelectedText(),
            TYPE: self.dataTypeSelection.getSelectedText(),
            }
        return dd

    def setUnit(self, unit):
        self.unitsSelection.set(unit, silent=True)

    def setValues(self, dd):
        """Get a dict of selected value"""
        self.quantitySelection.set(dd.get(QUANTITY),  silent=True)
        self._quantitySelectionCallback(False)
        self.dataTypeSelection.set(dd.get(TYPE),  silent=True)
        self.unitsSelection.set(dd.get(UNIT), silent=True)

    def deselectAll(self):
        self.quantitySelection.deselectAll()
        self.unitsSelection.set([], silent=True)
        self.dataTypeSelection.deselectAll()
        self.deselectedAllSignal.emit()

    def getUnit(self):
        return self.getValues().get(UNIT)

    def getQuantity(self):
        return self.getValues().get(QUANTITY)

    def getType(self):
        return self.getValues().get(TYPE)

    def getTypeCode(self):
        """ Return 0, 1, 2 for 'Float', 'Integer', 'String'"""
        dataType =  self.getValues().get(TYPE)
        descriptions = SeriesTypes.descriptions()
        if dataType in descriptions:
            typeCode = descriptions.index(dataType)
            return typeCode

    def getTypeCallable(self):
        """ Return float, int, str types for 'Float', 'Integer', 'String'"""

        dataType =  self.getValues().get(TYPE)
        callableType = SeriesTypes._dataTypesMapping().get(dataType)
        return callableType


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication

    def _testCallback(*args):
        print('CALLED', args)


    app = TestApplication()
    print('TestApplication done')
    popup = CcpnDialog(windowTitle='Test', setLayout=True)
    print('popup done')

    popup.setGeometry(200, 200, 200, 200)

    widget = SeriesUnitWidget(popup, mainWindow=None, grid=(0, 0))
    dd = {
        QUANTITY: 'Mass',
        UNIT    : 'g',
        TYPE    : 'Int',
        }
    # widget.setValues(dd)
    print('SeriesUnitWidget done')
    widget.unitSelectionChanged.connect(_testCallback)

    popup.exec_()
    print('exec_ done')
    # app.start()
