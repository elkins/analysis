"""
Create Collections of peaks from a SpectrumGroup Series.
Used for ExperimentAnalysis
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:23 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.RadioButton import RadioButton
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.PulldownListsForObjects import SpectrumGroupPulldown, PeakListPulldown
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.framework.lib.experimentAnalysis.FollowPeakInSeries import AVAILABLEFOLLOWPEAKS


INPLACE = 'In Place'
FOLLOW = 'Follow'
LAST = 'Last Created'
NEW = 'Create New'
FINDPEAKS = 'Find Peaks'
USEEXISTINGPEAKS = 'Use Existing Peaks'


def showWarningPopup():
    showWarning('Under implementation!', 'This popup is not active yet.')


class SeriesPeakCollectionPopup(CcpnDialogMainWidget):
    def __init__(self, parent=None, mainWindow=None, title='Series Peak Collection',
                 collectionName='collectionName', spectrumGroup=None, **kwds):
        super().__init__(parent, setLayout=True, size=(200, 350), minimumSize=None, windowTitle=title, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = self.mainWindow.application
            self.project = self.mainWindow.project
            self.current = self.application.current
        else:
            self.mainWindow = None
            self.application = None
            self.project = None
            self.current = None
        self._collectionName = collectionName
        self._sourcePeakList = None
        self._spectrumGroup = spectrumGroup
        self._topCollection = None
        self._fixedWidthsCW = [200, 200]
        self.setWidgets()
        self._populate()

        # enable the buttons
        self.setOkButton(callback=self._okClicked, tipText='Create Collections')
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def setWidgets(self):
        row = 0
        self.spectrumGroupCW = SpectrumGroupPulldown(self.mainWidget, mainWindow=self.mainWindow,
                                                     labelText='SpectrumGroup', grid=(row, 0),
                                                     gridSpan=(1, 2))
        if self._spectrumGroup is not None:
            self.spectrumGroupCW.select(self._spectrumGroup.pid)
        # fixedWidths=self._fixedWidthsCW)
        row += 1
        self.sourcePeakListCW = PeakListPulldown(self.mainWidget,
                                                 mainWindow=self.mainWindow,
                                                 labelText='Source PeakList', grid=(row, 0),
                                                 gridSpan=(1, 2))
        # fixedWidths=self._fixedWidthsCW)
        row += 1
        self.collectionNameCW = cw.EntryCompoundWidget(self.mainWidget,
                                                       entryText=self._collectionName,
                                                       labelText='Collection Name', grid=(row, 0),
                                                       gridSpan=(1, 2))
        row += 1

        ## InPlace Peak options
        self.inplaceRadioButton = RadioButton(self.mainWidget, text='Copy Peaks In Place',
                                              callback=self._toggleFrames, grid=(row, 0))
        row += 1
        self._inplaceFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 2))
        row += 1
        subRow = 0
        ## follow Peaks options
        self.followRadioButton = RadioButton(self.mainWidget, text='Follow Peaks', callback=self._toggleFrames, grid=(row, 0))
        row += 1
        self._followFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(2, 2))
        self.followPeakOptionstLabel = Label(self._followFrame, text='Select Mode', grid=(subRow, 0))
        self.followPeakOptionsRB = RadioButtons(self._followFrame, texts=[USEEXISTINGPEAKS],  # texts=[FINDPEAKS, USEEXISTINGPEAKS],
                                                selectedInd=0, grid=(subRow, 1))
        subRow += 1
        engines = list(AVAILABLEFOLLOWPEAKS.keys())
        self.followMethodLabel = Label(self._followFrame, text='Method', grid=(subRow, 0))
        self.followMethodPD = PulldownList(self._followFrame, texts=engines, grid=(subRow, 1))
        subRow += 1
        self.copyAssignmentsLabel = Label(self._followFrame, text='Copy Assignments', grid=(subRow, 0))
        self.copyAssignmentsOption = CheckBox(self._followFrame, text='', checked=False, grid=(subRow, 1))
        subRow += 1
        row += subRow

        HLine(self.mainWidget, grid=(row, 0), gridSpan=(1, 2))

        ## Common for both options
        row += 1
        self.usePeakListLabel = Label(self.mainWidget, text='Use peakList', grid=(row, 0))
        self.usePeakListLabelRB = RadioButtons(self.mainWidget, texts=[LAST, NEW], grid=(row, 1))
        row += 1
        self.refitLabel = Label(self.mainWidget, text='Refitting', grid=(row, 0))
        self.refitOption = CheckBox(self.mainWidget, text='Refit Peaks At Position',
                                    tipText='Recalculate the peak height and linewidths preserving the original peak position',
                                    checked=True, grid=(row, 1))
        row += 1
        self.coloursLabel = Label(self.mainWidget, text='Colouring', grid=(row, 0))
        self.coloursOption = CheckBox(self.mainWidget, text='Use colour from contours', checked=True,
                                      tipText='Use contour colours for peak symbols and texts',
                                      grid=(row, 1))
        row += 1

        self.inplaceRadioButton.click()
        # self.followRadioButton.setEnabled(False)

    @property
    def sourcePeakList(self):
        return self.project.getByPid(self.sourcePeakListCW.pulldownList.getText())

    @property
    def spectrumGroup(self):
        return self.project.getByPid(self.spectrumGroupCW.pulldownList.getText())

    @property
    def collectionName(self):
        return self.collectionNameCW.getText()

    @property
    def copyInPlace(self):
        return self.inplaceRadioButton.isChecked()

    @property
    def _copyAssignments(self):
        return self.copyAssignmentsOption.isChecked()

    @property
    def _isNewTargetPeakListNeeded(self):
        return self.usePeakListLabelRB.getSelectedText() == NEW

    @property
    def _followMethod(self):
        return self.followMethodPD.getText()

    @property
    def _isFindPeaksNeeded(self):
        return self.followPeakOptionsRB.getSelectedText() == FINDPEAKS

    def _toggleFrames(self, *args):
        if self.inplaceRadioButton.isChecked():
            self._inplaceFrame.setVisible(True)
            self._followFrame.setVisible(False)
            self.usePeakListLabelRB.setEnabled(True)
        else:
            self._followFrame.setVisible(True)
            self._inplaceFrame.setVisible(False)
            self.usePeakListLabelRB.set(LAST)
            self.usePeakListLabelRB.setEnabled(False)

    def _populate(self):
        self._populateSourcePeakListPullDown()
        self._populateSpectrumGroupPullDown()

    def _okClicked(self):

        if not self.spectrumGroup:
            showWarning('Missing SpectrumGroup', 'Select a SpectrumGroup first')
            return
        if not self.sourcePeakList:
            showWarning('Missing PeakList', 'Select a source PeakList first')
            return

        refit = self.refitOption.isChecked()
        useSliceColour = self.coloursOption.isChecked()
        with undoBlockWithoutSideBar():
            if self.copyInPlace:
                self._topCollection = self.spectrumGroup.copyAndCollectPeaksInSeries(self.sourcePeakList,
                                                                                     refit=refit,
                                                                                     useSliceColour=useSliceColour,
                                                                                     newTargetPeakList=self._isNewTargetPeakListNeeded,
                                                                                     topCollectionName=self.collectionName
                                                                                     )
            else:
                self._topCollection = self.spectrumGroup.followAndCollectPeaksInSeries(self.sourcePeakList,
                                                                                       engine=self._followMethod,
                                                                                       newTargetPeakList=self._isNewTargetPeakListNeeded,
                                                                                       pickPeaks=self._isFindPeaksNeeded,
                                                                                       copyAssignment=self._copyAssignments,
                                                                                       useSliceColour=useSliceColour,
                                                                                       topCollectionName=self.collectionName
                                                                                       )

        self.accept()

    def _populateSourcePeakListPullDown(self):
        """Populate the pulldown with the list of spectra in the project
        """
        if not self.project:
            return
        pass

    def _populateSpectrumGroupPullDown(self, *args):
        """
        """
        if not self.project:
            return
        pass

    def _cleanupDialog(self):
        """Clean up notifiers for closing
        """
        if self.spectrumGroupCW:
            self.spectrumGroupCW.unRegister()
        if self.sourcePeakListCW:
            self.sourcePeakListCW.unRegister()


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    popup = SeriesPeakCollectionPopup()
    popup.exec_()


if __name__ == '__main__':
    main()
