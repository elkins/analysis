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
__dateModified__ = "$dateModified: 2024-07-19 16:25:51 +0100 (Fri, July 19, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-05-28 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets

import decimal
from functools import partial
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from collections import OrderedDict
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.framework.Application import getApplication, getMainWindow, getProject, getCurrent
from ccpn.core.lib.SeriesUnitConverter import SERIESUNITS

print('Imports done')
class SeriesUnitWidget(ScrollableFrame):

    def __init__(self, parent, **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        self._setWidgets()

    def _setWidgets(self):
        i = 0
        quantitySelections = list(SERIESUNITS.keys())
        labelUnit = Label(self, text="Quantity", grid=(i, 0))
        self.quantitySelection = RadioButtons(self, texts=quantitySelections, callback=self._quantitySelectionCallback,  grid=(i, 1), direction='gv', numGridRows=4)
        i += 1
        self.unitsSelection = RadioButtons(self, texts=[], callback=self._unitsSelectionCallback, grid=(i, 1))

    def _quantitySelectionCallback(self):
        selected = self.quantitySelection.getSelectedText()
        print(selected, 'ELE')
        selectedUnit = SERIESUNITS.get(selected)
        unit = selectedUnit(1, selectedUnit.SI_baseUnit)
        self.unitsSelection.setButtons(unit.unitsSelection, tipTexts=unit.unitsTipTextSelection ,selectedInd=0, direction='h', numGridRows=4)

    def _unitsSelectionCallback(self):
        print('SELCT ')

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication


    app = TestApplication()
    print('TestApplication done')
    popup = CcpnDialog(windowTitle='Test', setLayout=True)
    print('popup done')

    popup.setGeometry(200, 200, 200, 200)

    widget = SeriesUnitWidget(popup, mainWindow=None, grid=(0, 0))
    print('SeriesUnitWidget done')
    popup.exec_()
    print('exec_ done')
    # app.start()
