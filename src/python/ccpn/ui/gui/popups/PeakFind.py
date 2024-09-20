"""Module Documentation here

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
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget


COLWIDTH = 140


class PeakFindPopup(CcpnDialogMainWidget):
    """
    PeakFind for nD spectra
    This popup works only for nDs. (Should be renamed?)
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    def __init__(self, parent=None, mainWindow=None, **kwds):
        super().__init__(parent, setLayout=True, windowTitle='Pick ND peaks', **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.application = self.mainWindow.application
            self.current = self.application.current
        else:
            self.mainWindow = self.project = self.application = self.current = None

        # set up the popup
        self._setWidgets()
        self._populate()

        # enable the buttons
        self.setOkButton(text='Find Peaks', callback=self._pickPeaks, tipText='Find Peaks')
        self.setCancelButton(callback=self.reject)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def _setWidgets(self):
        """Set up the widgets for the popup.
        """
        widget = self.mainWidget

        self.peakListLabel = Label(widget, text="PeakList ", grid=(0, 0))
        self.peakListPulldown = PulldownList(widget, grid=(0, 1), gridSpan=(1, 2), hAlign='l', callback=self._selectPeakList)

        self.checkBoxWidget = Frame(widget, setLayout=True, grid=(1, 0), gridSpan=(1, 6))

        Label(self.checkBoxWidget, 'Pick', grid=(0, 0))
        self.spectrumContourSelect = RadioButtons(self.checkBoxWidget, grid=(0, 1), texts=['Positive only', 'Negative only', 'Both'],
                                                  selectedInd=2, callback=None, direction='h',
                                                  hAlign='l',
                                                  tipTexts=['Only pick positive peaks', 'Only pick negative peaks', 'Pick all peaks'],
                                                  )
        self.checkBox1, self.checkBox2, self.checkBox3 = self.spectrumContourSelect.radioButtons

        self.limitsFrame = Frame(parent=widget, setLayout=True, spacing=(5, 0),
                                 showBorder=False, fShape='noFrame',
                                 grid=(2, 0), gridSpan=(1, 6))

        self.estimateFrame = Frame(parent=widget, setLayout=True, spacing=(5, 0),
                                   showBorder=False, fShape='noFrame',
                                   grid=(3, 0), gridSpan=(1, 6))

        self.estimateLineWidths = CheckBoxCompoundWidget(self.estimateFrame,
                                                         grid=(0, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                                                         # fixedWidths=(COLWIDTH, 30),
                                                         orientation='right',
                                                         labelText='Fit Peaks',
                                                         checked=True
                                                         )
        self.estimateLineWidths.setVisible(False)

        self.estimateVolumes = CheckBoxCompoundWidget(self.estimateFrame,
                                                      grid=(1, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                                                      # fixedWidths=(COLWIDTH, 30),
                                                      orientation='right',
                                                      labelText='Estimate Peak Volumes',
                                                      checked=False
                                                      )

        self.peakListPulldown.setData([peakList.pid for peakList in self.project.peakLists
                                       if peakList.spectrum.dimensionCount != 1])
        if self.current is not None and self.current.strip is not None and len(self.current.strip.spectra) > 0:
            self.peakListPulldown.select(self.current.strip.spectra[-1].peakLists[-1].pid)
        self.peakList = self.project.getByPid(self.peakListPulldown.currentText())

    def _populate(self):
        """Populate the widgets
        """
        # populate the estimateFrame
        self._updateContents()

    def _selectPeakList(self, item):
        self.peakList = self.project.getByPid(item)
        self._updateContents()

    def _pickPeaks(self):
        peakList = self.peakList
        positions = [[x.value(), y.value()] for x, y in zip(self.minPositionBoxes, self.maxPositionBoxes)]

        # Positive only
        doNeg = False if self.checkBox1.isChecked() else True
        # negative only
        doPos = False if self.checkBox2.isChecked() else True

        doLineWidths = self.estimateLineWidths.isChecked()
        doVolumes = self.estimateVolumes.isChecked()

        # Checking the third box turns the others off and sets both. Hence, default
        # peakList.pickPeaksNd(positions, doPos=doPos, doNeg=doNeg, fitMethod='gaussian')

        axisCodeDict = dict((code, positions[ii]) for ii, code in enumerate(self.peakList.spectrum.axisCodes))

        _spectrum = peakList.spectrum
        # may create a peakPicker instance if not defined, subject to settings in preferences
        _peakPicker = _spectrum.peakPicker
        if _peakPicker:
            _peakPicker.dropFactor = self.application.preferences.general.peakDropFactor
            _peakPicker.setLineWidths = doLineWidths  # currently set to True in the peak-picker :|
            pks = _spectrum.pickPeaks(peakList,
                                      _spectrum.positiveContourBase if doPos else None,
                                      _spectrum.negativeContourBase if doNeg else None,
                                      **axisCodeDict)

            # estimate the peak volumes for the selected peaks
            if doVolumes and doLineWidths:
                peakList.estimateVolumes(peaks=pks, volumeIntegralLimit=self.application.preferences.general.volumeIntegralLimit)

        self.accept()

    def _updateContents(self):

        # update the contents of the limits frame to the new spectrum
        layout = self.limitsFrame.getLayout()

        rowCount = layout.rowCount()
        colCount = layout.columnCount()

        for r in range(2, 7):
            for m in range(0, colCount):
                item = layout.itemAtPosition(r, m)
                if item:
                    if item.widget():
                        item.widget().hide()
                layout.removeItem(item)

        self.minPositionBoxes = []
        self.maxPositionBoxes = []

        if self.peakList is not None:
            for ii in range(self.peakList.spectrum.dimensionCount):
                dim1MinLabel = Label(self.limitsFrame, text='F%s ' % str(ii + 1) + self.peakList.spectrum.axisCodes[ii] + ' min', grid=(2 + ii, 0), vAlign='t')
                dim1MinDoubleSpinBox = DoubleSpinbox(self.limitsFrame, grid=(2 + ii, 1), vAlign='t')
                dim1MinDoubleSpinBox.setMinimum(self.peakList.spectrum.aliasingLimits[ii][0])
                dim1MinDoubleSpinBox.setMaximum(self.peakList.spectrum.aliasingLimits[ii][1])
                dim1MinDoubleSpinBox.setValue(self.peakList.spectrum.aliasingLimits[ii][0])
                dim1MaxLabel = Label(self.limitsFrame, text='F%s ' % str(ii + 1) + self.peakList.spectrum.axisCodes[ii] + ' max', grid=(2 + ii, 2), vAlign='t')
                dim1MaxDoubleSpinBox = DoubleSpinbox(self.limitsFrame, grid=(2 + ii, 3))
                dim1MaxDoubleSpinBox.setMinimum(self.peakList.spectrum.aliasingLimits[ii][0])
                dim1MaxDoubleSpinBox.setMaximum(self.peakList.spectrum.aliasingLimits[ii][1])
                dim1MaxDoubleSpinBox.setValue(self.peakList.spectrum.aliasingLimits[ii][1])
                self.minPositionBoxes.append(dim1MinDoubleSpinBox)
                self.maxPositionBoxes.append(dim1MaxDoubleSpinBox)
            # self.excludedRegionsButton = Button(self, grid=(self.peakList.spectrum.dimensionCount+3, 0), text='Exclude Regions')
            # self.excludedRegionsButton.setCheckable(True)
            # self.excludedRegionsButton.toggled.connect(self.toggleExcludedRegionsPopup)

    def _toggleExcludedRegionsPopup(self):

        if not hasattr(self, 'excludedRegionsPopup'):
            self.raiseExcludedRegionsPopup()
        else:
            if self.excludedRegionsButton.isChecked():
                self.excludedRegionsPopup.show()
            else:
                self.excludedRegionsPopup.hide()

    def raiseExcludedRegionsPopup(self):
        self.excludedRegionsPopup = ExcludeRegions(self, self.peakList)
        self.layout().addWidget(self.excludedRegionsPopup, 5, 0, 1, 4)


class ExcludeRegions(QtWidgets.QWidget, Base):
    def __init__(self, parent, peakList):
        super(ExcludeRegions, self).__init__(parent)
        self.regionCount = 0
        self.peakList = peakList
        self.addRegionButton = Button(self, text='Add Region', callback=self._addRegion, grid=(20, 0), gridSpan=(1, 3))
        self.removeRegionButton = Button(self, text='Remove Region', callback=self._removeRegion, grid=(20, 3), gridSpan=(1, 3))
        self.excludedRegions = []

    def _addRegion(self):
        self.regionCount += 1
        minRegion = []
        maxRegion = []
        for ii in range(self.peakList.spectrum.dimensionCount):
            print(self.peakList.spectrum.dimensionCount)
            dim1MinLabel = Label(self, text='F%s ' % str(1 + ii) + self.peakList.spectrum.axisCodes[ii] + ' min', grid=(1 + ii * self.regionCount, 0),
                                 vAlign='t')
            dim1MinDoubleSpinBox = DoubleSpinbox(self, grid=(1 + ii * self.regionCount, 1), vAlign='t')
            dim1MinDoubleSpinBox.setMinimum(self.peakList.spectrum.aliasingLimits[ii][0])
            dim1MinDoubleSpinBox.setMaximum(self.peakList.spectrum.aliasingLimits[ii][1])
            dim1MinDoubleSpinBox.setValue(self.peakList.spectrum.aliasingLimits[ii][0])
            minRegion.append(dim1MinDoubleSpinBox)
            dim1MaxLabel = Label(self, text='F%s ' % str(1 + ii) + self.peakList.spectrum.axisCodes[ii] + ' max', grid=(1 + ii * self.regionCount, 2),
                                 vAlign='t')
            dim1MaxDoubleSpinBox = DoubleSpinbox(self, grid=(1 + ii * self.regionCount, 3))
            dim1MaxDoubleSpinBox.setMinimum(self.peakList.spectrum.aliasingLimits[ii][0])
            dim1MaxDoubleSpinBox.setMaximum(self.peakList.spectrum.aliasingLimits[ii][1])
            dim1MaxDoubleSpinBox.setValue(self.peakList.spectrum.aliasingLimits[ii][1])
            maxRegion.append(dim1MaxDoubleSpinBox)

            # self.minPositionBoxes.append(dim1MinDoubleSpinBox)
            # self.maxPositionBoxes.append(dim1MaxDoubleSpinBox)
        self.excludedRegions.append([minRegion, maxRegion])
        self.regionCount += 1

    def _removeRegion(self):
        for i in range(5):
            item = self.layout().itemAtPosition(self.regionCount, i)
            # print(item, i, self.regionCount)
            # self.regionCount-=1
