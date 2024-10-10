"""
Module Documentation here
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-10-01 12:04:16 +0100 (Tue, October 01, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: rhfogh $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
from PyQt5 import QtGui, QtCore, QtWidgets
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.core.lib.AssignmentLib import _fetchNewPeakAssignments
from ccpn.util.OrderedSet import OrderedSet


class SetupNmrResiduesPopup(CcpnDialogMainWidget):
    """
    Dialog to handle creating new nmrAtoms for peaks that have not been assigned
    """
    _PEAKLIST = '_peakList'
    _NMRCHAIN = '_nmrChain'
    _ASSIGNMENT = '_assignment'
    _CURRENTSTRIP = '_currentStrip'
    _BADCOLOR = QtGui.QColor('grey')
    _STRIPCOLOR = QtGui.QColor('dodgerblue')
    _DIVIDERCOLOR = QtGui.QColor('grey')

    storeStateOnReject = True  # store the state if the dialog is cancelled

    def __init__(self, parent=None, mainWindow=None,
                 title='Set up NmrResidues', **kwds):
        """
        Initialise the dialog

        :param parent:
        :param mainWindow:
        :param title:
        :param kwds:
        """
        CcpnDialogMainWidget.__init__(self, parent, setLayout=True, windowTitle=title, **kwds)

        self._parent = parent
        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.current = self.mainWindow.application.current
        else:
            self.mainWindow = self.project = self.current = None

        self._setWidgets()

        self._acceptButtonText = 'Set up NmrResidues'
        self.BUTTON_CANCEL = 'Cancel'

        self.setOkButton(callback=self._setupNmrResidues, text=self._acceptButtonText,
                         tipText='Set up NmrResidues and close')
        self.setCancelButton(callback=self.reject, text=self.BUTTON_CANCEL, tipText='Cancel and close')
        self.setDefaultButton(CcpnDialogMainWidget.OKBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._applyButton = self.getButton(self.OKBUTTON)
        self._applyButton.setEnabled(True)
        self._cancelButton = self.getButton(self.CANCELBUTTON)

        # use below if the popup does not need to close
        # self.assignmentCheckBox = CheckBox(self.mainWidget, text="Keep existing assignments", checked=True, grid=(1, 0), gridSpan=(1, 3))
        #
        # self._acceptButtonText = 'Apply'
        # self._buttonCancel = 'Close'
        #
        # self.setApplyButton(callback=self._setupNmrResidues, text=self._acceptButtonText, tipText='Setup Nmr Residues')
        # self.setCloseButton(callback=self.reject, text=self._buttonCancel, tipText='Close Dialog')
        # self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)
        #
        # self._applyButton = self.getButton(self.APPLYBUTTON)
        # self._applyButton.setEnabled(True)
        # self._cancelButton = self.getButton(self.CLOSEBUTTON)

    def _setWidgets(self):
        """Setup widgets for the dialog
        """
        toolTip = 'PeakLists in the project.\n' \
                  'PeakLists from current.strip are displayed first,\n' \
                  'those visible are highlighted blue.\n' \
                  'Empty peakLists are greyed-out.'
        Label(self.mainWidget, text="Source PeakList ", grid=(0, 0), tipText=toolTip)
        self.peakListPulldown = PulldownList(self.mainWidget, grid=(0, 1), tipText=toolTip)

        toolTip = 'Destination nmrChain for new nmrAtoms'
        Label(self.mainWidget, text="NmrChain ", grid=(0, 2), tipText=toolTip)
        self.nmrChainPulldown = PulldownList(self.mainWidget, grid=(0, 3), tipText=toolTip)

        self.assignmentCheckBox = CheckBox(self.mainWidget, text="Keep existing assignments", checked=True, grid=(1, 0),
                                           gridSpan=(1, 3))
        self.assignmentCheckBox.setToolTip(
                'Keep the existing assignments attached to the peaks when assigning new nmrAtoms,\n'
                'or delete the assignments for each peak first.')

        HLine(self.mainWidget, grid=(2, 0), gridSpan=(1, 4), colour=getColours()[DIVIDER], height=20)
        self.useCurrentStrip = CheckBox(self.mainWidget, text="Select peakList from current strip",
                                        checked=True, grid=(3, 0), gridSpan=(1, 3))
        self.useCurrentStrip.setToolTip('Select the first visible peakList from current.strip,\n'
                                        'or remember the peakList from the previous popup.')

        if self.project:
            self.nmrChainPulldown.setData([nmrChain.pid for nmrChain in self.project.nmrChains])

            allPkLists = OrderedSet(peakList.pid for peakList in self.project.peakLists)
            stripPkLists = visiblePkLists = OrderedSet()
            if self.current and (strip := self.current.strip):
                with contextlib.suppress(Exception):
                    stripPkLists = OrderedSet(plv.peakList.pid for sv in strip.getSpectrumViews()
                                              for plv in sv.peakListViews)
                    visiblePkLists = OrderedSet(plv.peakList.pid for sv in strip.getSpectrumViews() if sv.isDisplayed
                                                for plv in sv.peakListViews if plv.isDisplayed)

            # separate peak-lists into those belonging to the current strip, and all the others
            texts = list(stripPkLists) + list(allPkLists - stripPkLists)
            self.peakListPulldown.setData(texts)
            if stripPkLists:
                self.peakListPulldown.insertSeparator(len(stripPkLists))

            # highlight peak-lists that are bad or empty
            combo: QtWidgets.QComboBox = self.peakListPulldown
            model = combo.model()
            for ind in range(combo.count()):
                if (item := model.item(ind)) is not None:
                    txt = item.text()
                    if (pkList := self.project.getByPid(txt)) is None or not pkList.peaks:
                        item.setData(self._BADCOLOR, role=QtCore.Qt.ForegroundRole)
                    elif txt in visiblePkLists:
                        item.setData(self._STRIPCOLOR, role=QtCore.Qt.ForegroundRole)
                    else:
                        # clears the colour and reverts to palette.Text
                        item.setData(None, role=QtCore.Qt.ForegroundRole)
            combo.repaint()

    def _setupNmrResidues(self):
        peakList = self.project.getByPid(self.peakListPulldown.currentText())
        nmrChain = self.project.getByPid(self.nmrChainPulldown.currentText())
        keepAssignments = self.assignmentCheckBox.isChecked()

        # method handles undoBlock and notifiers
        _fetchNewPeakAssignments(peakList, nmrChain, keepAssignments)

        # remove if popup does not need to close
        self.accept()

    def storeWidgetState(self):
        """Store the state of the checkBoxes between popups
        """
        SetupNmrResiduesPopup._storedState[self._PEAKLIST] = self.peakListPulldown.get()
        SetupNmrResiduesPopup._storedState[self._NMRCHAIN] = self.nmrChainPulldown.get()
        SetupNmrResiduesPopup._storedState[self._ASSIGNMENT] = self.assignmentCheckBox.isChecked()
        SetupNmrResiduesPopup._storedState[self._CURRENTSTRIP] = self.useCurrentStrip.isChecked()

    def restoreWidgetState(self):
        """Restore the state of the checkBoxes
        """
        useCurrent = SetupNmrResiduesPopup._storedState.get(self._CURRENTSTRIP, True)
        if useCurrent:
            if self.current and (strip := self.current.strip):
                # use the first peak-list from the current strip
                if visiblePkLists := [plv.peakList.pid for sv in strip.getSpectrumViews() if sv.isDisplayed
                                      for plv in sv.peakListViews if plv.isDisplayed]:
                    self.peakListPulldown.set(visiblePkLists[0])

        else:
            self.peakListPulldown.set(bool(SetupNmrResiduesPopup._storedState.get(self._PEAKLIST, False)))

        self.nmrChainPulldown.set(bool(SetupNmrResiduesPopup._storedState.get(self._NMRCHAIN, False)))
        self.assignmentCheckBox.set(bool(SetupNmrResiduesPopup._storedState.get(self._ASSIGNMENT, True)))
        self.useCurrentStrip.set(bool(useCurrent))


#=========================================================================================
# main
#=========================================================================================

def main():
    from ccpn.ui.gui.widgets.Application import TestApplication

    # need to keep a handle on the app otherwise gets instantly garbage-collected :|
    app = TestApplication()

    popup = SetupNmrResiduesPopup()
    popup.exec_()


if __name__ == '__main__':
    main()
