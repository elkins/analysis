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
__modifiedBy__ = "$modifiedBy: Vicky Higman $"
__dateModified__ = "$dateModified: 2024-06-03 10:27:55 +0100 (Mon, June 03, 2024) $"
__version__ = "$Revision: 3.2.4 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.SettingsWidgets import SpectrumSelectionWidget
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons, RadioButtonsWithSubCheckBoxes
from ccpn.ui.gui.widgets.RadioButton import CheckBoxCheckedText, CheckBoxCallbacks, CheckBoxTexts, CheckBoxTipTexts
from collections import OrderedDict as od
from ccpn.ui.gui.widgets.MessageDialog import showWarning, _stoppableProgressBar, progressManager
import ccpn.ui.gui.widgets.CompoundWidgets as cw


_OnlyPositionAndAssignments = 'Copy position and assignments'
_IncludeAllPeakProperties   = 'Copy all existing properties'
_SnapToExtremum             = 'Snap to extremum'
_RefitPeaks                 = 'Refit peaks'
_RefitPeaksAtPosition       = 'Refit peaks at position'
_RecalculateVolume          = 'Recalculate volume'
_tipTextOnlyPos             = f'''Copy Peaks and include only the original position and assignments (if available).\nAdditionally, execute the selected operations'''
_tipTextIncludeAll          = f'''Copy Peaks and include all the original properties: \nPosition, Assignments, Heights, Linewidths, Volumes etc...'''
_tipTextSnapToExtremum      = 'Snap all new peaks to extremum. Default properties set in the General Preferences'
_tipTextRefitPeaks          = 'Refit all new peaks. Default properties set in the General Preferences'
_tipTextRefitPeaksAtPosition= 'Refit peaks and force to maintain the original position. Default properties set in the General Preferences'
_tipTextRecalculateVolume   = 'Recalculate volume for all peaks. Requires a Refit.'


class CopyPeakListPopup(CcpnDialogMainWidget):
    def __init__(self, parent=None, mainWindow=None, title='Copy PeakList', spectrumDisplay=None,
                 selectItem=None, **kwds):
        super().__init__(parent, setLayout=True, minimumSize=(450, 250), windowTitle=title, **kwds)

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

        self.spectrumDisplay = spectrumDisplay
        self.sourcePeakList = None
        self.targetSpectrum = None
        self.defaultPeakList = self._getDefaultPeakList() if selectItem is None else \
                               self.application.get(selectItem)

        self.setWidgets()
        self._populate()

        # enable the buttons
        self.setOkButton(callback=self._okClicked, tipText='Copy PeakList')
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()
        self._extraActionDefs = {
                                _SnapToExtremum: self._snapPeaksToExtremum,
                                _RefitPeaks: self._refitPeaks,
                                _RecalculateVolume: self._recalculateVolume,
                                _RefitPeaksAtPosition: self._refitPeaksAtPositions,
                                }

    def setWidgets(self):
        self.sourcePeakListPullDownCW = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Source PeakList',
                                                              grid=(0, 0), callback=self._populateTargetSpectraPullDown)

        self.sourcePeakListPullDown = self.sourcePeakListPullDownCW.pulldownList
        self.targetSpectraPullDownCW = SpectrumSelectionWidget(self.mainWidget,
                                                                     labelText='Target Spectra',
                                                                     grid=(1, 0),
                                                                     tipText='Select Target Spectra',
                                                                     standardListItems=[str(sp.pid) for sp in
                                                                                        self.project.spectra])
        self.targetSpectraPullDown = self.targetSpectraPullDownCW.pulldownList

        checkBoxTexts = [_SnapToExtremum, _RefitPeaks, _RefitPeaksAtPosition, _RecalculateVolume]
        checkBoxTipTexts = [_tipTextSnapToExtremum, _tipTextRefitPeaks, _tipTextRefitPeaksAtPosition,
                            _tipTextRecalculateVolume]

        checkBoxesDict = od([
                            (_OnlyPositionAndAssignments,
                             {
                             CheckBoxTexts: checkBoxTexts,
                             CheckBoxCheckedText: [_SnapToExtremum, _RefitPeaks, _RecalculateVolume],
                             CheckBoxTipTexts: checkBoxTipTexts,
                             CheckBoxCallbacks: [self._subSelectionCallback] * len(checkBoxTexts)
                             }
                            ),
                            ])

        self.copyOptionsRadioButtons = RadioButtonsWithSubCheckBoxes(self.mainWidget,
                                                                     texts=[_OnlyPositionAndAssignments,
                                                                            _IncludeAllPeakProperties],
                                                                     selectedInd=0,
                                                                     tipTexts=[_tipTextOnlyPos, _tipTextIncludeAll],
                                                                     checkBoxesDictionary=checkBoxesDict,
                                                                     grid=(2, 0),
                                                                     )

    def _populate(self):
        self._populateSourcePeakListPullDown()
        self._populateTargetSpectraPullDown()

    def _okClicked(self):
        with undoBlockWithoutSideBar():
            # self.targetSpectrum = self.project.getByPid(self.targetSpectraPullDown.getTexts())
            self.sourcePeakList = self.project.getByPid(self.sourcePeakListPullDown.getText())
            # self._copyPeakListToSpectrum()

            spectra = self.project.getObjectsByPids(self.targetSpectraPullDownCW.getTexts())

            errors = []
            for sp in spectra:
                self.targetSpectrum = sp
                try:
                    self._copyPeakListToSpectrum()
                except Exception as es:
                    errors.append(f'• {es}')

            if errors:
                _msg = (f'Your current values raise the following error{"s" if len(errors) > 1 else ""}:\n\n' +
                        '\n'.join(errors))
                showWarning(str(self.windowTitle()), _msg)

        self.accept()

    def _executeAfterCopyPeaks(self, peakList):

        # execute further operations to the new peakList if required.
        ddValues = self.copyOptionsRadioButtons.get()
        extraActionsTexts = ddValues.get(_OnlyPositionAndAssignments, [])
        for action in extraActionsTexts:
            func = self._extraActionDefs.get(action)
            if func:
                func(peakList)

    def _copyPeakListToSpectrum(self):
        includeAllProperties = self.copyOptionsRadioButtons.getSelectedText() == _IncludeAllPeakProperties

        if self.sourcePeakList is not None:
            try:
                if self.targetSpectrum is not None:
                    with progressManager(self, 'Copying Peaks. See terminal window for more info...'):
                        newPeakList = self.sourcePeakList.copyTo(self.targetSpectrum,
                                                                 includeAllPeakProperties=includeAllProperties)
                        self._executeAfterCopyPeaks(newPeakList)

            except Exception as es:
                getLogger().warning(f'Error copying peakList: {str(es)}')
                raise Exception(es)
                # showWarning(str(self.windowTitle()), str(es))

    def _populateSourcePeakListPullDown(self):
        """Populate the pulldown with the list of spectra in the project
        """
        if not self.project:
            return

        if len(self.project.peakLists) == 0:
            raise RuntimeError('Project has no PeakList\'s')

        sourcePullDownData = [str(pl.pid) for pl in self.project.peakLists]
        self.sourcePeakListPullDown.setData(sourcePullDownData)
        if self.defaultPeakList is not None:
            self.sourcePeakListPullDown.select(self.defaultPeakList.pid)
            self.sourcePeakList = self.defaultPeakList
        # self._selectDefaultPeakList()

    def _populateTargetSpectraPullDown(self, *args):
        """Populate the pulldown with the list of spectra on the selected spectrumDisplay and select the
        first visible spectrum
        """
        if not self.project:
            return

        sourcePeakList = self.application.get(args[0]) if len(args) > 0 else self.sourcePeakList

        if sourcePeakList is None:
            visibleSpectra = spectra = self.project.spectra
        else:
            _dimCount = sourcePeakList.spectrum.dimensionCount
            visibleSpectra = spectra = [spec for spec in self.project.spectra if spec.dimensionCount <= _dimCount]

            if self.spectrumDisplay is not None:
                _tmp = self.spectrumDisplay.strips[0].getVisibleSpectra()
                visibleSpectra = [spec for spec in _tmp if spec.dimensionCount <= _dimCount]

        if spectra:
            targetPullDownData = [str(sp.pid) for sp in spectra]
            self.targetSpectraPullDown.setData(targetPullDownData)

            if visibleSpectra:
                for vs in visibleSpectra:
                    self.targetSpectraPullDown.select(vs.pid)

    def _getDefaultPeakList(self):
        """:return the default PeakList based on current settings, or None
        """
        result = None
        if not self.current:
            return result

        if self.current.peak is not None:
            result = self.current.peak.peakList

        elif self.current.strip is not None and not self.current.strip.isDeleted:
            _spec = self.current.strip.spectra[0]
            result = _spec.peakLists[-1]

        elif len(self.project.peakLists) > 0:
            result = self.project.peakLists[0]

        return result

    def _subSelectionCallback(self, checked):
        """
        This routine is to ensure there are not mutually exclusive selections.
        Behaviour:
            allowed combinations:
                - _SnapToExtremum, _RefitPeaks, _RecalculateVolume
                - _SnapToExtremum, _RecalculateVolume
                - _RefitPeaks, _RecalculateVolume
                - _RefitPeaksAtPosition, _RecalculateVolume

            not allowed:
                - _RecalculateVolume alone
                - _RefitPeaksAtPosition excludes any of  _RefitPeaks, _SnapToExtremum

        It is convoluted and a refactor might be needed for readability.
        But double check the intended behaviour is maintained!

        :param checked: bool
        :return: None
        """
        clicked = self.sender().getText()
        radioButton = self.copyOptionsRadioButtons.getRadioButtonByText(_OnlyPositionAndAssignments)
        _include = radioButton.getSelectedCheckBoxes()
        _exclude = []

        if clicked == _RefitPeaksAtPosition:
            if checked:
                _exclude += [_SnapToExtremum, _RefitPeaks]

        if clicked == _SnapToExtremum:
            _exclude += [_RefitPeaksAtPosition]

        if clicked == _RefitPeaks:
            _exclude += [_RefitPeaksAtPosition]

        if _RecalculateVolume in _include:
            if _RefitPeaks not in _include:
                if _RefitPeaksAtPosition not in _include:
                    _include += [_RefitPeaks]

        newSelection = list(set([i for i in _include if i not in _exclude]))
        radioButton.setSelectedCheckBoxes(newSelection)

    def _refitPeaks(self, peakList, keepPosition=False):
        peaks = peakList.peaks
        fitMethod = self.application.preferences.general.peakFittingMethod
        getLogger().info('Refitting peaks')
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                for peak in peaks:
                    peak.fit(fitMethod=fitMethod, keepPosition=keepPosition)

    def _refitPeaksAtPositions(self, peakList, keepPosition=True):
        self._refitPeaks(peakList, keepPosition=keepPosition)

    def _recalculateVolume(self, peakList):
        getLogger().info('Recalculating  peak volumes.')
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                peakList.estimateVolumes()

    def _snapPeaksToExtremum(self, peakList):
        # get the default from the preferences
        minDropFactor = self.application.preferences.general.peakDropFactor
        searchBoxMode = self.application.preferences.general.searchBoxMode
        searchBoxDoFit = self.application.preferences.general.searchBoxDoFit
        fitMethod = self.application.preferences.general.peakFittingMethod
        peaks = peakList.peaks
        getLogger().info('Snapping Peaks To Extremum.')
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                peaks.sort(key=lambda x: x.position[0], reverse=False)  # reorder peaks by position
                for peak in peaks:
                    peak.snapToExtremum(halfBoxSearchWidth=4, halfBoxFitWidth=4,
                                        minDropFactor=minDropFactor, searchBoxMode=searchBoxMode,
                                        searchBoxDoFit=searchBoxDoFit, fitMethod=fitMethod)


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    import ccpn.core.testing.WrapperTesting as WT


    app = TestApplication()

    thisWT = WT.WrapperTesting()
    thisWT.setUp()

    app.project = thisWT.project

    popup = CopyPeakListPopup()  # too many errors for testing here...

    popup.show()
    popup.raise_()

    app.start()

    WT.WrapperTesting.tearDown(thisWT)
