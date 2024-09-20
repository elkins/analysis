
"""
Alpha version of a popup for setting up a structure calculation using Xplor-NIH calculations.
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
__modifiedBy__ = "$Author: Luca Mureddu $"
__dateModified__ = "$Date: 2021-04-27 16:04:57 +0100 (Tue, April 27, 2021) $"
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2021-04-27 16:04:57 +0100 (Tue, April 27, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.PulldownListsForObjects import RestraintTablePulldown, PeakListPulldown, ChemicalShiftListPulldown, ChainPulldown
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ListWidget import ListWidgetPair
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import MessageDialog
import os
import datetime
from distutils.dir_util import copy_tree
from ccpn.ui.gui.widgets.FileDialog import OtherFileDialog
from ccpn.framework.Application import getApplication


# if len(application.preferences.externalPrograms.get('xplor')) < 2:
#     showWarning('XPLOR PATH NOT SET UP', 'Please make sure you have set the path in preferences.')
#     sys.exit()
# if len(application.preferences.externalPrograms.get('talosn')) < 2:
#     showWarning('TALOSN PATH NOT SET UP', 'Please make sure you have set the path in preferences.')
#     sys.exit()



application = getApplication()


if application:
    # Path for Xplor NIH executable. Those calculations are
    i = 0

def removeRestraints(restraintsList, moveToPeakListPID):
    for restraint in restraintsList.restraints:
        if 'remove' in restraint.comment:
            restraint.peaks[0].comment = 'moved, violated restraint'
            restraint.peaks[0].copyTo(moveToPeakListPID)
            restraint.peaks[0].delete()
    return

class SRemoveUnwantedRestraintsPopup(CcpnDialogMainWidget):
    """

    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    title = 'Remove Unwanted Restraints (Alpha)'
    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(500, 10), minimumSize=None, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.current = self.application.current
            self.project = mainWindow.project

        else:
            self.mainWindow = None
            self.application = None
            self.current = None
            self.project = None

        self._createWidgets()

        # enable the buttons
        self.tipText = ''
        self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Move', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        row = 0

        self.rlWidget = RestraintTablePulldown(parent=self.mainWidget,
                                               mainWindow=self.mainWindow,
                                               grid=(row, 0), gridSpan=(1,3),
                                               showSelectName=True,
                                               minimumWidths=(0, 100),
                                               sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                               callback=None)

        row += 1
        self.plsWidget = PeakListPulldown(parent=self.mainWidget,
                                         mainWindow=self.mainWindow,
                                         grid=(row, 0), gridSpan=(1,3),
                                         showSelectName=True,
                                         minimumWidths=(0, 100),
                                         sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                         callback=None)

        self._populateWsFromProjectInfo()

    def _populateWsFromProjectInfo(self):
        if self.project:
            self.rlWidget.selectFirstItem()
            self.plsWidget.selectFirstItem()

    def _okCallback(self):
        if self.project:
            rl = self.rlWidget.getSelectedObject()
            pl = self.plsWidget.getSelectedObject()

            if not rl:
                MessageDialog.showWarning('', 'Select a Restraint List')
                return
            if not pl:
                MessageDialog.showWarning('', 'Select a destination Peak List')
                return

            # run the calculation
            print('Running with peakLists: %s, Restraints: %s,' %(pl, rl))
            removeRestraints(restraintsList=rl,
                             moveToPeakListPID = pl)

        self.accept()

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    # app = TestApplication()
    popup = SRemoveUnwantedRestraintsPopup(mainWindow=mainWindow)
    popup.show()
    popup.raise_()
    # app.start()

