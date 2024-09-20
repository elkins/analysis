"""
This popup is used for creating distance Restraints from a peakList containing assigned peaks.
Alpha release and called from a macro.
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2021-03-05 11:01:32 +0000 (Fri, March 05, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================


import ccpn.core #this is needed it to avoid circular imports
from PyQt5 import QtCore, QtGui, QtWidgets
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
# from ccpn.util.Common import _incrementObjectName, _validateName
from ccpn.core.StructureData import StructureData
from ccpn.core.RestraintTable import RestraintTable

A = str(u"\u212B")

IntensityType = 'intensityType'
Height = 'height'
Volume = 'volume'
MinMerit = 'minMerit'
RefIntensity = 'Ref Intensity'
Normalise = 'normalise'
RefDist = 'refDist'
NegError = 'negError'
PosError = 'posError'
AbsMin = 'absMin'
AbsMax = 'absMax'
Power = 'power'
ResidueRanges = 'ResidueRanges'
NewDsName = 'newDsName'
DefaultNewName = 'MyRestraintData'

DefaultOptions = {
                NewDsName: DefaultNewName,
                IntensityType: Height,
                Normalise: True,
                RefDist: 3.2,
                NegError: 0.2,
                PosError: 0.2,
                AbsMin: 1.72,
                AbsMax: 8.0,
                Power: 6,
                ResidueRanges: None,
                MinMerit: 0.0
                }


class CalculateDistanceRestraintsPopup(CcpnDialogMainWidget):
    """

    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    title = 'Calculate Distance Restraints (Alpha)'
    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(315, 200), minimumSize=None, **kwds)

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
        self.tipText = 'Calculate Distance Restraints from assigned peaks and add to a new Dataset'
        self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Calculate', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        row = 0
        self.nameWidget = cw.EntryCompoundWidget(self.mainWidget, labelText='New Dataset Name',
                                                 entryText=DefaultOptions.get(NewDsName),
                                                 grid=(row, 0), gridSpan=(1, 1))

        row += 1
        self.pLwidget = PeakListPulldown(parent=self.mainWidget,
                                         mainWindow=self.mainWindow,
                                         grid=(row, 0), gridSpan=(1, 1),
                                         showSelectName=True,
                                         minimumWidths=(0, 100),
                                         sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                         callback=None)
        row += 1
        self.intensityTypeW = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Intensity Type',
                                                           texts=[Height, Volume],
                                                           grid=(row, 0), gridSpan=(1, 1))
        row += 1
        _frame = MoreLessFrame(self.mainWidget, name='Advanced',  showMore=False, grid=(row, 0), gridSpan=(1, 2))
        advContentsFrame = _frame.contentsFrame
        advRow = 0
        self.refIntensityW = cw.PulldownListCompoundWidget(advContentsFrame, labelText='Ref Intensity',
                                                           texts=['Mean'],
                                                           grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.normaliseW = cw.CheckBoxCompoundWidget(advContentsFrame, labelText=Normalise.capitalize(),
                                                           checked=DefaultOptions.get(Normalise, True),
                                                           grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.refDistW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Ref Distance (%s)'%A,
                                                    value=DefaultOptions.get(RefDist),
                                                    grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.negErrorW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Lower Frac Error',
                                                    value=DefaultOptions.get(NegError),
                                                    grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.posErrorW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Upper Frac Error',
                                                            value=DefaultOptions.get(PosError),
                                                            grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.absMinW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Lower Dist Limit (%s)'%A,
                                                            value=DefaultOptions.get(AbsMin),
                                                            grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.absMaxW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Upper Dist Limit (%s)'%A,
                                                            value=DefaultOptions.get(AbsMax),
                                                            grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1

        self.powerW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText=Power.capitalize(),
                                                            value=DefaultOptions.get(Power),
                                                            grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1
        self.minMeritW = cw.ScientificSpinBoxCompoundWidget(advContentsFrame, labelText='Min Peak Merit',
                                                         value=DefaultOptions.get(MinMerit),
                                                         grid=(advRow, 0), gridSpan=(1, 1))
        advRow += 1

        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignTop)
        self._populateWsFromProjectInfo()

    def _populateWsFromProjectInfo(self):
        if self.project:
            self.pLwidget.selectFirstItem()
            # name = _incrementObjectName(self.project, StructureData._pluralLinkName, self.nameWidget.getText())
            # self.nameWidget.setText(name)

    @property
    def params(self):
        return self._params

    @params.getter
    def _params(self):
        _params = DefaultOptions
        _params.update({NewDsName: self.nameWidget.getText() or _params[NewDsName]})
        _params.update({IntensityType: self.intensityTypeW.getText() or _params[IntensityType] })
        _params.update({Normalise: self.normaliseW.get() or _params[Normalise]})
        _params.update({RefDist: self.refDistW.getValue() or _params[RefDist]})
        _params.update({NegError: self.negErrorW.getValue() or _params[NegError]})
        _params.update({PosError: self.posErrorW.getValue() or _params[PosError]})
        _params.update({AbsMin: self.absMinW.getValue() or _params[AbsMin]})
        _params.update({AbsMax: self.absMaxW.getValue() or _params[AbsMax]})
        _params.update({Power: self.powerW.getValue() or _params[Power]})
        _params.update({MinMerit: self.minMeritW.getValue() or _params[MinMerit]})
        return _params

    def _okCallback(self):
        import ccpn.core.lib._DistanceRestraintsLib as drl
        if self.project:
            pl = self.pLwidget.getSelectedObject()
            if pl:
                nmrAtoms = drl._getNmrAtomsFromPeakList(pl)
                drl._correctIsotopeCodes(nmrAtoms)
                resonanceSets, atomSets = drl._setupResonanceAndAtomSets(pl)
                drl._newV3DistanceRestraint(pl, **self.params)
                drl._deleteTempResonanceAndAtomSets(self.project, resonanceSets, atomSets)
        self.accept()

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    app = TestApplication()
    popup = CalculateDistanceRestraintsPopup()
    popup.show()
    popup.raise_()
    app.start()
