"""
A popup specific for the Experiment Analysis module
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
__dateModified__ = "$dateModified: 2024-08-07 09:20:37 +0100 (Wed, August 07, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.widgets.RadioButton import CheckBoxCheckedText, CheckBoxCallbacks, CheckBoxTexts, CheckBoxTipTexts
from collections import OrderedDict as od
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.MessageDialog import showWarning, _stoppableProgressBar, progressManager
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.framework.Application import getApplication, getCurrent, getProject, getMainWindow
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from tqdm import tqdm

LastFittingResults = 'Last Fitting results'
ReCalculate = 'Re-Calculate'

class RefitSingularSelectedSeriesPopup(CcpnDialogMainWidget):
    """
    A popup specific for the Experiment Analysis module.
    """
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    def __init__(self, parent, seriesAnalysisModule, collections=None, title='Refit Singular Collection Popup', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        self.mainWindow = getMainWindow()
        self.application = getApplication()
        self.project = getProject()
        self.current = getCurrent()
        self.collections = collections or []
        self._paramsDicts = {}
        self.seriesAnalysisModule = seriesAnalysisModule
        self._backendHandler = self.seriesAnalysisModule.backendHandler
        self.setWidgets()
        self._populate()

        # enable the buttons
        self.setOkButton(callback=self._okClicked, text='Refit', tipText='Refit individually Series using the selected options')
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)
        # initialise the buttons and dialog size
        self._postInit()
        self.getLayout().setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)


    def setWidgets(self):

        row  = 0
        columnWidth = 200
        self._maxSpanW = 3
        texts = [c.pid for c in self.collections]
        fText = '\n'.join(texts)
        self.collectionPidsWidgets = cw.PlainListCompoundWidget(self.mainWidget, labelText='Selected',
                                                            texts=texts, grid=(row, 0),  fixedWidths=(columnWidth, columnWidth), gridSpan=(1, 2),
                                                            compoundKwds={'allowSelections':False, 'contextMenu':False})
        row += 1
        self.initialValueWidget = cw.RadioButtonsCompoundWidget(self.mainWidget, labelText='Initial Values',
                                                            compoundKwds= {
                                                             'texts' : [LastFittingResults, ReCalculate],
                                                             'direction'  : 'v',
                                                             'selectedInd': 1},
                                                            grid=(row, 0),  gridSpan=(1, 2),
                                                            fixedWidths=(columnWidth, columnWidth))
        self._initialValueRadioButtons = self.initialValueWidget.radioButtons
        row += 1


        self.fittingModelWidget = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Fitting Model',
                                                              grid=(row, 0), fixedWidths=(columnWidth, columnWidth), callback=None)
        self._fittingModelPullDown = self.fittingModelWidget.pulldownList
        row += 1

        self.minimiserMethodWidget = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Minimiser Method',
                                                                   grid=(row, 0), fixedWidths=(columnWidth, columnWidth), callback=None)
        self._minimiserModelPullDown = self.minimiserMethodWidget.pulldownList
        row += 1

        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)


    def _populate(self):
        # add models
        models = self._backendHandler.fittingModels
        modelNames  = list(models.keys())
        minimiserMethods = list(sv.MINIMISER_METHODS.keys())
        self._fittingModelPullDown.setData(modelNames)
        if self._backendHandler.currentFittingModel:
            currentModelName = self._backendHandler.currentFittingModel.modelName
            with self._fittingModelPullDown.blockWidgetSignals():
                self._fittingModelPullDown.select(currentModelName)
        self._minimiserModelPullDown.setData(minimiserMethods)


    def _okClicked(self):
        recalculate = self._initialValueRadioButtons.getSelectedText() == ReCalculate
        modelName = self._fittingModelPullDown.getText()
        minimiserMethod = self._minimiserModelPullDown.getText()

        fittingModelClass = self._backendHandler.getFittingModelByName(modelName)
        if fittingModelClass:
            fittingModel = fittingModelClass()
        else:
            showWarning('Cannot refit', f'No model found with name {modelName}')
            return

        with undoBlockWithoutSideBar():
            for collection in tqdm(self.collections):
                self._backendHandler.refitCollection(collection.pid,
                                                     fittingModel=fittingModel,
                                                     minimiserMethod=minimiserMethod,
                                                     resetInitialParams=recalculate,
                                                     )
        self.seriesAnalysisModule.updateAll()
        self.accept()



if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    popup = RefitSingularSelectedSeriesPopup(None)
    popup.show()
    popup.raise_()
    app.start()
