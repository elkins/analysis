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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-07-04 09:28:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.lib.SpectrumLib import setContourLevelsFromNoise, DEFAULTLEVELS, DEFAULTMULTIPLIER
from ccpn.core.lib.SpectrumLib import getNoiseEstimate, getNoiseEstimateFromRegion, getClippedRegion
from ccpn.util.OrderedSet import OrderedSet
from ccpn.ui.gui.widgets.Button import Button
# from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.ui.gui.widgets.DoubleSpinbox import ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget, RadioButtonsCompoundWidget
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.guiSettings import getColours, SOFTDIVIDER


COL_WIDTH = 140
NONE_TEXT = '-'
MINIMUM_WIDTH_PER_TAB = 100
MINIMUM_WIDTH = 400
MAXIMUM_WIDTH = 700
ESTIMATEMETHOD = 'estimateMethod'
ESTIMATECONTOURS = 'estimateContours'
ESTIMATEPOSITIVE = 'estimatePositive'
ESTIMATENEGATIVE = 'estimateNegative'
ESTIMATEMULTIPLIER = 'estimateMultiplier'
ESTIMATEDEFAULT = 'estimateDefault'
ESTIMATEAUTO = 'estimateAuto'

lineColour = getColours()[SOFTDIVIDER]


class EstimateNoisePopup(CcpnDialogMainWidget):
    """
    Class to implement a popup for estimating noise in a set of spectra
    """

    def __init__(self, parent=None, mainWindow=None, title='Estimate Noise',
                 strip=None, orderedSpectrumViews=None, **kwds):
        """
        Initialise the widget
        """
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None

        # label the current strip
        self.strip = strip
        self.orderedSpectrumViews = orderedSpectrumViews
        self.orderedSpectra = OrderedSet([spec.spectrum for spec in self.orderedSpectrumViews])

        # create the list of widgets and set the callbacks for each
        self._setWidgets()

        # set up the required buttons for the dialog
        self.setCloseButton(callback=self.accept, enabled=True)
        self.setHelpButton(callback=self.reject, enabled=False)
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

        # populate the widgets
        self._populate()

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()
        # make automatic estimates
        self._autoEstimate()

    def _accept(self):
        """Close button pressed
        """
        self.accept()

    def _setWidgets(self):
        row = 0
        self.topFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 1), hPolicy='minimal')

        row += 1
        HLine(self.mainWidget, grid=(row, 0), gridSpan=(1, 4), colour=lineColour, height=20)

        row += 1
        self.stripLabel = Label(self.mainWidget, grid=(row, 0), gridSpan=(1, 4), bold=True)
        self.stripLabel.setMinimumHeight(20)

        row += 1
        self.tabWidget = Tabs(self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 4))

        row += 1
        self.contourFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 4))

        # add a tab for each spectrum in the spectrumDisplay
        self._noiseTab = []
        for specNum, thisSpec in enumerate(self.orderedSpectra):
            if thisSpec.dimensionCount > 1:
                self._noiseTab.append(NoiseTabNd(parent=self, mainWindow=self.mainWindow, spectrum=thisSpec, strip=self.strip))
            else:
                self._noiseTab.append(NoiseTab(parent=self, mainWindow=self.mainWindow, spectrum=thisSpec, strip=self.strip))

            self.tabWidget.addTab(self._noiseTab[specNum], thisSpec.name)

        self._setTopWidgets()
        self._setContourWidgets()
        if self.strip.spectrumDisplay.is1D:
            self.contourFrame.hide()

    def _setTopWidgets(self):
        """Populate the top-frame"""
        row = 0

        texts = ['Visible Area', 'Random Sampling']
        tipTexts = ['Estimate the noise from the visible plane',
                    'Estimate the noise from a random sampling of the whole spectrum']

        self.estimateOption = RadioButtonsCompoundWidget(self.topFrame, labelText='Estimation method',
                                                         grid=(row, 0), gridSpan=(1, 1), stretch=(0, 0),
                                                         compoundKwds={'direction': 'h',
                                                                       'hPolicy'  : 'minimal',
                                                                       # 'selectedInd': 0,
                                                                       'texts'    : texts,
                                                                       'tipTexts' : tipTexts},
                                                         callback=self._autoEstimate
                                                         )

        # checkbox to recalculate on first popup - True to start
        row += 1
        self.autoCalculate = CheckBoxCompoundWidget(self.topFrame,
                                                    grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                                                    orientation='right',
                                                    labelText='Automatically estimate noise on popup',
                                                    checked=True)

    def _setContourWidgets(self):
        row = 0
        Label(self.contourFrame, text='Contour Options:', grid=(row, 0), gridSpan=(1, 3), vAlign='t', hAlign='l')

        from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget

        row += 1
        self.setPositiveContours = CheckBoxCompoundWidget(self.contourFrame, grid=(row, 0), gridSpan=(1, 3),
                                                          vAlign='top', stretch=(0, 0), hAlign='left',
                                                          orientation='right', margins=(15, 0, 0, 0),
                                                          labelText='Set positive contour levels',
                                                          checked=True
                                                          )

        row += 1
        self.setNegativeContours = CheckBoxCompoundWidget(self.contourFrame, grid=(row, 0), gridSpan=(1, 3),
                                                          vAlign='top', stretch=(0, 0), hAlign='left',
                                                          orientation='right', margins=(15, 0, 0, 0),
                                                          labelText='Set negative contour levels',
                                                          checked=True
                                                          )

        row += 1
        self.setUseSameMultiplier = CheckBoxCompoundWidget(self.contourFrame, grid=(row, 0), gridSpan=(1, 3),
                                                           vAlign='top', stretch=(0, 0), hAlign='left',
                                                           orientation='right', margins=(15, 0, 0, 0),
                                                           labelText='Use same (positive) multiplier for negative contours',
                                                           checked=True
                                                           )

        row += 1
        self.setDefaults = CheckBoxCompoundWidget(self.contourFrame, grid=(row, 0), gridSpan=(1, 3),
                                                  vAlign='top', stretch=(0, 0), hAlign='left',
                                                  orientation='right', margins=(15, 0, 0, 0),
                                                  labelText='Use default multiplier (%0.3f) and contour level count (%i)' % (
                                                      DEFAULTMULTIPLIER, DEFAULTLEVELS),
                                                  checked=True
                                                  )

        # row += 1
        # self.noiseLevelButton = Button(frame, grid=(row, 2), callback=self._setContourLevels, text=buttonLabel)

    def _populate(self):
        # populate any settings in the popup and the tabs
        self.stripLabel.setText(f'Current strip: {self.strip.id}')
        for tab in self._noiseTab:
            tab._populate()

    def _autoEstimate(self):
        # calculate an estimate for each of the tabs
        if self.autoCalculate.isChecked():
            for tab in self._noiseTab:
                if not tab._noiseFromCurrentCursorPosition:
                    tab._estimateNoise()

    def storeWidgetState(self):
        """Store the state of the checkBoxes between popups
        """
        for tab in self._noiseTab:
            # may not be necessary
            tab._storeWidgetState()

        if ESTIMATECONTOURS not in EstimateNoisePopup._storedState:
            EstimateNoisePopup._storedState[ESTIMATECONTOURS] = {ESTIMATEMETHOD: self.estimateOption.getIndex(),
                                                                 ESTIMATEAUTO  : self.autoCalculate.isChecked()
                                                                 }
        else:
            EstimateNoisePopup._storedState[ESTIMATECONTOURS].update({ESTIMATEMETHOD: self.estimateOption.getIndex(),
                                                                      ESTIMATEAUTO  : self.autoCalculate.isChecked()
                                                                      })

        if not self.strip.spectrumDisplay.is1D:
            EstimateNoisePopup._storedState[ESTIMATECONTOURS].update({ESTIMATEPOSITIVE  : self.setPositiveContours.isChecked(),
                                                                      ESTIMATENEGATIVE  : self.setNegativeContours.isChecked(),
                                                                      ESTIMATEMULTIPLIER: self.setUseSameMultiplier.isChecked(),
                                                                      ESTIMATEDEFAULT   : self.setDefaults.isChecked(),
                                                                      })

    def restoreWidgetState(self):
        """Restore the state of the checkBoxes
        """
        for tab in self._noiseTab:
            # may not be necessary
            tab._restoreWidgetState()

        if states := EstimateNoisePopup._storedState.get(ESTIMATECONTOURS):
            self.estimateOption.setIndex(states.get(ESTIMATEMETHOD))
            self.autoCalculate.set(states.get(ESTIMATEAUTO))
            if not self.strip.spectrumDisplay.is1D:
                self.setPositiveContours.set(states.get(ESTIMATEPOSITIVE, False))
                self.setNegativeContours.set(states.get(ESTIMATENEGATIVE, False))
                self.setUseSameMultiplier.set(states.get(ESTIMATEMULTIPLIER, False))
                self.setDefaults.set(states.get(ESTIMATEDEFAULT, False))


class NoiseTab(Widget):
    """Class to contain the information for a single pectrum in the spectrum display
    Holds the common values for 1d and Nd spectra
    """

    def __init__(self, parent=None, mainWindow=None, spectrum=None, strip=None, **kwds):
        """Initialise the tab settings
        """
        super().__init__(parent, setLayout=True, **kwds)
        self.setContentsMargins(5, 5, 5, 5)

        self._parent = parent
        self.mainWindow = mainWindow
        self.current = self.mainWindow.current
        self.spectrum = spectrum
        self.strip = strip
        self._lastNoiseValue = None
        self.noiseLevel = None

        # create the list of widgets and set the callbacks for each
        self._setWidgets()
        self._noiseFromCurrentCursorPosition = False
        self._setFromCurrentCursor()

    def _setWidgets(self):
        # set up the common widgets
        row = 0
        LabeledHLine(self, text='Visible Area', style=HLine.DASH_LINE, colour=lineColour,
                     grid=(row, 0), gridSpan=(1, 3), height=10)

        self.axisCodeLabels = []
        for axis in self.strip.axisCodes:
            row += 1
            Label(self, text=axis, grid=(row, 0), vAlign='t', hAlign='l')
            self.axisCodeLabels.append(Label(self, text=NONE_TEXT, grid=(row, 1), gridSpan=(1, 2), vAlign='t', hAlign='l'))

        row += 1
        LabeledHLine(self, text='Noise', style=HLine.DASH_LINE, colour=lineColour,
                     grid=(row, 0), gridSpan=(1, 3), height=10)

        for label, text in zip(['meanLabel', 'SDLabel', 'maxLabel', 'minLabel'], ['Mean', 'SD', 'Max', 'Min']):
            row += 1
            Label(self, text=text, grid=(row, 0), vAlign='t', hAlign='l')
            setattr(self, label, Label(self, text=NONE_TEXT, grid=(row, 1), gridSpan=(1, 2), vAlign='t', hAlign='l'))

        row += 1
        Label(self, text='Current noise level', grid=(row, 0), vAlign='c', hAlign='l')
        self.currentNoiseLabel = Label(self, text=NONE_TEXT, grid=(row, 1), gridSpan=(1, 2), vAlign='c', hAlign='l')

        row += 1
        Label(self, text='Estimated noise level', grid=(row, 0), vAlign='c', hAlign='l')
        self.noiseLevelSpinBox = ScientificDoubleSpinBox(self, grid=(row, 1), vAlign='t', decimals=1)
        self.noiseLevelSpinBox.setMaximum(1e12)
        self.noiseLevelSpinBox.setMinimum(0.1)
        self.noiseLevelSpinBox.setMinimumCharacters(15)
        self.recalculateLevelsButton = Button(self, grid=(row, 2), callback=self._estimateNoise, text='Re-estimate')

        row += 1
        self.addSpacer(20, 20, expandX=True, expandY=True, grid=(row, 0), gridSpan=(1, 3))

        options = {}

        row += 1
        self.noiseLevelButtons = Button(self, grid=(row, 0), callback=self._setNoiseLevel,
                                        text='Set Noise Level', **options)
        self.noiseLevelToAllButtons = Button(self, grid=(row, 1), callback=self._setNoiseLevelToAll,
                                             text='Set Noise Level To All', **options)
        self.contoursButton = Button(self, grid=(row, 2), callback=self._setContourLevels,
                                     text='Generate Contours', **options)
        self.contoursButton.hide()  # un-hidden for nD

        # remember the row for subclassed Nd below
        self.row = row

    def _populate(self):
        # populate the widgets, but don't perform any calculations
        if self.spectrum.noiseLevel is not None:
            self.currentNoiseLabel.setText(f'{self.spectrum.noiseLevel:8.1e}')

    def _setFromCurrentCursor(self):
        """Add the initial spinbox value from the current cursor position. Implemented only for 1D.
        """
        if self.mainWindow.current is not None and \
                self.spectrum.dimensionCount == 1 and \
                self.current.cursorPosition:
            self.noiseLevelSpinBox.set(float(self.current.cursorPosition[-1]))
            self._noiseFromCurrentCursorPosition = True

    def _estimateNoise(self):
        # get the current mode and call the relevant estimate routine
        ind = self._parent.estimateOption.getIndex()
        if ind == 0:
            self._estimateFromRegion()
        elif ind == 1:
            self._estimateFromRandomSamples()

    def _estimateFromRegion(self):
        if noise := getNoiseEstimateFromRegion(self.spectrum, self.strip):
            regions = getClippedRegion(self.spectrum, self.strip)

            # populate the widgets
            for ii, region in enumerate(regions):
                self.axisCodeLabels[ii].setText('( ' + ', '.join(['%.1f' % rr for rr in region]) + ' )')

            self._lastNoiseValue = noise
            self._setLabels(noise.mean, noise.std, noise.min, noise.max, noise.noiseLevel)

    def _estimateFromRandomSamples(self):
        # populate the widgets
        noise = getNoiseEstimate(self.spectrum)

        # clear the range labels (full range is implied)
        for lbl in self.axisCodeLabels:
            lbl.setText('-')
        self._lastNoiseValue = noise
        self._setLabels(noise.mean, noise.std, noise.min, noise.max, noise.noiseLevel)

    def _setLabels(self, mean, std, min, max, noiseLevel):
        # fill the labels with the new values
        self.meanLabel.setText(f'{mean:8.1e}')
        self.SDLabel.setText(f'{std:8.1e}')
        self.maxLabel.setText(f'{max:8.1e}')
        self.minLabel.setText(f'{min:8.1e}')
        self.noiseLevelSpinBox.setValue(noiseLevel)

    def _setNoiseLevel(self):
        """Apply the current noiseLevel to the spectrum
        """
        value = float(self.noiseLevelSpinBox.value())
        if self._lastNoiseValue is not None: # The user set the noise manually. how to deal with this!?
            noiseSD = self._lastNoiseValue.std
            self.spectrum._noiseSD = float(noiseSD)
        self.spectrum.noiseLevel = value
        self.spectrum.negativeNoiseLevel = -value if value > 0 else value * 2

        self._populate()

    def _setNoiseLevelToAll(self):
        """
        Set the noise level from the current tab to all spectra.
        """
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar

        spectra = self._parent.orderedSpectra
        value = float(self.noiseLevelSpinBox.value())
        noiseSD = None
        if self._lastNoiseValue is not None:
            noiseSD = self._lastNoiseValue.std

        with undoBlockWithoutSideBar():
            for spectrum in spectra:
                spectrum.noiseLevel = value
                spectrum.negativeNoiseLevel = -value if value > 0 else value * 2
                spectrum._noiseSD = float(noiseSD)
        for tab in self._parent._noiseTab:
            tab._populate()

    def _setContourLevels(self):
        """Estimate the contour levels for the current spectrum
        """
        # get the settings from the parent checkboxes
        setContourLevelsFromNoise(self.spectrum, setNoiseLevel=False,
                                  setPositiveContours=self._parent.setPositiveContours.isChecked(),
                                  setNegativeContours=self._parent.setNegativeContours.isChecked(),
                                  useSameMultiplier=self._parent.setUseSameMultiplier.isChecked(),
                                  useDefaultLevels=self._parent.setDefaults.isChecked(),
                                  useDefaultMultiplier=self._parent.setDefaults.isChecked())

    def _storeWidgetState(self):
        """Store the state of the checkBoxes between popups
        """
        pass

    def _restoreWidgetState(self):
        """Restore the state of the checkBoxes
        """
        pass


class NoiseTabNd(NoiseTab):
    """Class to contain the information for a single spectrum in the spectrum display
    Holds the extra widgets for changing Nd contour settings
    """

    def __init__(self, parent=None, mainWindow=None, spectrum=None, strip=None, **kwds):
        """Initialise the tab settings
        """
        super().__init__(parent=parent, mainWindow=mainWindow, spectrum=spectrum, strip=strip, **kwds)
        self._parent = parent

    def _setWidgets(self):
        super()._setWidgets()
        self.contoursButton.show()

    # def _setContourLevels(self):
    #     """Estimate the contour levels for the current spectrum
    #     """
    #     # get the settings from the parent checkboxes
    #     setContourLevelsFromNoise(self.spectrum, setNoiseLevel=False,
    #                               setPositiveContours=self._parent.setPositiveContours.isChecked(),
    #                               setNegativeContours=self._parent.setNegativeContours.isChecked(),
    #                               useSameMultiplier=self._parent.setUseSameMultiplier.isChecked(),
    #                               useDefaultLevels=self._parent.setDefaults.isChecked(),
    #                               useDefaultMultiplier=self._parent.setDefaults.isChecked())

    # def _addContourNoiseButtons(self, row, frame, buttonLabel='Generate Contours'):
    #     row += 1
    #     self.noiseLevelButton = Button(frame, grid=(row, 2), callback=self._setContourLevels, text=buttonLabel)
