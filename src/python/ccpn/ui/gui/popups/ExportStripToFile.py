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
__dateModified__ = "$dateModified: 2024-08-23 19:23:04 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-07-06 15:51:11 +0000 (Thu, July 06, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import OrderedDict as OD
from PyQt5 import QtWidgets, QtCore, QtGui
from dataclasses import dataclass
from functools import partial
from typing import Optional

from ccpn.core.lib.ContextManagers import catchExceptions, queueStateChange
from ccpn.ui.gui.guiSettings import getColours, DIVIDER, BORDERFOCUS
from ccpn.ui.gui.popups.ExportDialog import ExportDialogABC
from ccpn.ui.gui.popups.Dialog import _verifyPopupApply
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.ProjectTreeCheckBoxes import PrintTreeCheckBoxes
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.ColourDialog import ColourDialog
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget, CheckBoxCompoundWidget, DoubleSpinBoxCompoundWidget
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.MessageDialog import showYesNoWarning, showWarning
from ccpn.ui.gui.widgets.HighlightBox import HighlightBox
from ccpn.ui.gui.widgets.Font import getFontHeight, getSystemFonts
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import GLFILENAME, GLGRIDLINES, \
    GLINTEGRALLABELS, GLINTEGRALSYMBOLS, GLMULTIPLETLABELS, \
    GLMULTIPLETSYMBOLS, GLPEAKLABELS, GLPEAKSYMBOLS, GLPEAKARROWS, GLMULTIPLETARROWS, \
    GLPRINTTYPE, GLPAGETYPE, GLPAGESIZE, GLSELECTEDPIDS, \
    GLSPECTRUMBORDERS, GLSPECTRUMCONTOURS, \
    GLSPECTRUMDISPLAY, GLSTRIP, \
    GLWIDGET, GLBACKGROUND, GLBASETHICKNESS, GLSYMBOLTHICKNESS, GLFOREGROUND, \
    GLCONTOURTHICKNESS, GLSHOWSPECTRAONPHASE, \
    GLSTRIPDIRECTION, GLSTRIPPADDING, GLEXPORTDPI, \
    GLFULLLIST, GLEXTENDEDLIST, GLDIAGONALLINE, GLCURSORS, GLDIAGONALSIDEBANDS, \
    GLALIASENABLED, GLALIASSHADE, GLALIASLABELSENABLED, GLSTRIPREGIONS, \
    GLSCALINGMODE, GLSCALINGOPTIONS, GLSCALINGPERCENT, GLSCALINGBYUNITS, \
    GLPRINTFONT, GLUSEPRINTFONT, GLSCALINGAXIS, \
    GLPEAKSYMBOLSENABLED, GLPEAKLABELSENABLED, GLPEAKARROWSENABLED, GLMULTIPLETSYMBOLSENABLED, \
    GLMULTIPLETLABELSENABLED, GLMULTIPLETARROWSENABLED
from ccpn.ui.gui.lib.ChangeStateHandler import changeState
from ccpn.util.Colour import spectrumColours, addNewColour, fillColourPulldown, addNewColourString, hexToRgbRatio, colourNameNoSpace
from ccpn.util.Constants import SCALING_MODES, POSINFINITY
from ccpn.util.Logging import getLogger


EXPORTEXT = 'EXT'
EXPORTFILTER = 'FILTER'
EXPORTPDF = 'PDF'
EXPORTPDFEXTENSION = '.pdf'
EXPORTPDFFILTER = 'pdf files (*.pdf)'
EXPORTSVG = 'SVG'
EXPORTSVGEXTENSION = '.svg'
EXPORTSVGFILTER = 'svg files (*.svg)'
EXPORTPNG = 'PNG'
EXPORTPNGEXTENSION = '.png'
EXPORTPNGFILTER = 'png files (*.png)'
EXPORTPS = 'PS'
EXPORTPSEXTENSION = '.ps'
EXPORTPSFILTER = 'ps files (*.ps)'
EXPORTTYPES = OD(((EXPORTPDF, {EXPORTEXT   : EXPORTPDFEXTENSION,
                               EXPORTFILTER: EXPORTPDFFILTER}),
                  (EXPORTSVG, {EXPORTEXT   : EXPORTSVGEXTENSION,
                               EXPORTFILTER: EXPORTSVGFILTER}),
                  (EXPORTPNG, {EXPORTEXT   : EXPORTPNGEXTENSION,
                               EXPORTFILTER: EXPORTPNGFILTER}),
                  (EXPORTPS, {EXPORTEXT   : EXPORTPSEXTENSION,
                              EXPORTFILTER: EXPORTPSFILTER}),
                  ))
EXPORTFILTERS = EXPORTPDFFILTER
PAGEPORTRAIT = 'portrait'
PAGELANDSCAPE = 'landscape'
PAGETYPES = [PAGEPORTRAIT, PAGELANDSCAPE]

STRIPAXIS = 'Axis'
STRIPMIN = 'Min'
STRIPMAX = 'Max'
STRIPCENTRE = 'Centre'
STRIPWIDTH = 'Width'
STRIPAXISINVERTED = 'AxisInverted'
STRIPBUTTONS = [STRIPAXIS, STRIPMIN, STRIPMAX, STRIPCENTRE, STRIPWIDTH]
STRIPAXES = ['X', 'Y']
DEFAULT_FONT = 'Default Font'

PAGESIZEA0 = 'A0'
PAGESIZEA1 = 'A1'
PAGESIZEA2 = 'A2'
PAGESIZEA3 = 'A3'
PAGESIZEA4 = 'A4'
PAGESIZEA5 = 'A5'
PAGESIZEA6 = 'A6'
PAGESIZELETTER = 'letter'
PAGESIZES = [PAGESIZEA0, PAGESIZEA1, PAGESIZEA2, PAGESIZEA3, PAGESIZEA4, PAGESIZEA5, PAGESIZEA6, PAGESIZELETTER]
PAGESIZE = 'pageSize'
OPTIONSPECTRA = 'Spectra'
OPTIONPEAKLISTS = 'Peak Lists'
OPTIONPRINT = 'Print Options'
OPTIONLIST = (OPTIONSPECTRA, OPTIONPEAKLISTS, OPTIONPRINT)

DEFAULTSPACING = (3, 3)
TABMARGINS = (1, 10, 10, 1)  # l, t, r, b
ZEROMARGINS = (0, 0, 0, 0)  # l, t, r, b

PulldownFill = '--'
DEFAULT_COLOR = QtGui.QColor('black')
PRINT_COLOR = QtGui.QColor('orange')
SELECTAXIS_COLOR = QtGui.QColor('orange')
SELECTAXIS_COLOR2 = QtGui.QColor('mediumseagreen')


@dataclass
class _StripData:
    """Simple class to store strip widget state
    """
    strip = None
    useRegion = False
    minMaxMode = 0
    axes = None
    _widget = None

    _USEREGION = 'useRegion'
    _MINMAXMODE = 'minMaxMode'
    _AXES = 'axes'
    _DECIMALS = 2

    def _initialise(self):
        """Initialise the new dataclass from the strip
        """
        self.axes = [{STRIPMIN         : 0.0,
                      STRIPMAX         : 0.0,
                      STRIPCENTRE      : 0.0,
                      STRIPWIDTH       : 0.0,
                      STRIPAXISINVERTED: False,  # not sure if this is needed
                      },
                     {STRIPMIN         : 0.0,
                      STRIPMAX         : 0.0,
                      STRIPCENTRE      : 0.0,
                      STRIPWIDTH       : 0.0,
                      STRIPAXISINVERTED: False,
                      }]

        if self.strip:
            for ii in range(len(STRIPAXES)):
                dd = self.axes[ii]
                region = self.strip.getAxisRegion(ii)
                dd[STRIPMIN], dd[STRIPMAX] = min(region), max(region)
                dd[STRIPAXISINVERTED] = region[0] > region[1]
                dd[STRIPCENTRE] = self.strip.getAxisPosition(ii)
                dd[STRIPWIDTH] = self.strip.getAxisWidth(ii)

    def __repr__(self):
        """Output the string representation
        """
        return f'<{self.strip}: {self.useRegion}, {self.minMaxMode}, {self.axes}>'

    def toDict(self):
        """Output the contents as a dict
        """

        def _func(val):
            return round(val, self._DECIMALS)

        dd = {self._USEREGION : self.useRegion,
              self._MINMAXMODE: self.minMaxMode,
              self._AXES      : [{STRIPMIN         : _func(axis[STRIPMIN]),
                                  STRIPMAX         : _func(axis[STRIPMAX]),
                                  STRIPCENTRE      : _func(axis[STRIPCENTRE]),
                                  STRIPWIDTH       : _func(axis[STRIPWIDTH]),
                                  STRIPAXISINVERTED: axis[STRIPAXISINVERTED],
                                  } for axis in self.axes],
              }
        return dd

    def fromDict(self, value):
        """update contents from a dict
        """
        self.useRegion = value.get(self._USEREGION)
        self.minMaxMode = value.get(self._MINMAXMODE)
        self.axes = _axes = value.get(self._AXES)

        def _func(val):
            return float(val)

        if _axes:
            self.axes = [{STRIPMIN         : _func(axis[STRIPMIN]),
                          STRIPMAX         : _func(axis[STRIPMAX]),
                          STRIPCENTRE      : _func(axis[STRIPCENTRE]),
                          STRIPWIDTH       : _func(axis[STRIPWIDTH]),
                          STRIPAXISINVERTED: axis[STRIPAXISINVERTED],
                          } for axis in _axes]


class _StripListWidget(ListWidget):
    """ListWidget with a new right-mouse menu
    """

    def __init__(self, *args, parentPopup=None, parentCallbacks=None, **kwds):
        if not (parentCallbacks and len(parentCallbacks) == 3):
            raise RuntimeError('bad parentCallbacks')

        super().__init__(*args, **kwds)

        # copy has not been used on the first popup
        self._firstCopy = False
        self._parentPopup = parentPopup

        # make a persistent menu
        self._stripListMenu = contextMenu = Menu('', self, isFloatWidget=True)
        self._copyOption = contextMenu.addItem("Copy", callback=parentCallbacks[0])
        self._pasteOption = contextMenu.addItem("Paste to", callback=parentCallbacks[1])
        self._pasteAllOption = contextMenu.addItem("Paste to Selection", callback=parentCallbacks[2])

    def getContextMenu(self):
        # return the axis menu
        return self._stripListMenu

    def mousePressEvent(self, event):
        if self.itemAt(event.pos()) is None:
            self.clearSelection()

        # want to call ListWidget handler not superclass
        super(ListWidget, self).mousePressEvent(event)

        # get item under mouse
        clicked = self.itemAt(event.pos())
        self._clickedStripId = clicked.text() if clicked else None

        # enable/disable options based on the selection
        _selection = self.selectedItems()
        self._selectedStripIds = [val.text() for val in _selection]

        _opt = self._clickedStripId and self._clickedStripId in self._selectedStripIds
        self._copyOption.setEnabled(bool(_opt))
        self._copyOption.setText(f'Copy {self._clickedStripId if _opt else "-"}')

        _opt = self._firstCopy and self._clickedStripId and self._clickedStripId in self._selectedStripIds
        self._pasteOption.setEnabled(bool(_opt))
        self._pasteOption.setText(f'Paste to {self._clickedStripId if _opt else "-"}')

        self._pasteAllOption.setEnabled(self._firstCopy and len(_selection) > 1)

        # raise the copy/paste menu
        if event.button() == QtCore.Qt.RightButton and self.contextMenu:
            option = self.raiseContextMenu(event)  # returns the menu action clicked
            if option == self._copyOption:
                # enable the paste buttons if the copy has been used at least once
                self._firstCopy = True


class ExportStripToFilePopup(ExportDialogABC):
    """
    Class to handle printing strips to file
    """
    _SAVESTRIPS = '_strips'
    _SAVECURRENTSTRIP = '_currentStrip'
    _SAVECURRENTAXIS = '_currentAxis'

    storeStateOnReject = True

    # permanently enables the saveAndClose button
    EDITMODE = False

    def __init__(self, parent=None, mainWindow=None, title='Export Strip to File',
                 fileMode='anyFile',
                 acceptMode='export',
                 selectFile=None,
                 fileFilter=EXPORTFILTERS,
                 strips=None,
                 selectedStrip=None,
                 includeSpectrumDisplays=True,
                 **kwds):
        """
        Initialise the widget
        """
        # initialise attributes
        self.strips = strips
        self.objects = {}
        self.includeSpectrumDisplays = includeSpectrumDisplays
        self.strip = None
        self.spectrumDisplay = None
        self.spectrumDisplays = set()
        self.specToExport = None
        self._scalingModeIndex = 0
        self._useFontSetting = None

        self._initialiseStripList()

        # load the available .ttf fonts - load everytime as user may move/add them
        self.familyFonts = getSystemFonts()

        super().__init__(parent=parent, mainWindow=mainWindow, title=title,
                         fileMode=fileMode, acceptMode=acceptMode,
                         selectFile=selectFile,
                         fileFilter=fileFilter,
                         **kwds)

        self.printSettings = self.application.preferences.printSettings

        if not strips:
            showWarning(str(self.windowTitle()), 'No strips selected')
            self.reject()

        self._selectedStrip = selectedStrip or (strips[0] if strips else None)

        self.fullList = GLFULLLIST
        self._copyRangeValue = None

        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)

    def exec_(self) -> Optional[dict]:
        """Disable strip updating while the popup is visible
        """
        for strip in self.strips:
            strip._CcpnGLWidget._disableCursorUpdate = True

        result = super().exec_()

        for strip in self.strips:
            strip._CcpnGLWidget._disableCursorUpdate = False

        return result

    def initialise(self, userFrame):
        """Create the widgets for the userFrame
        """
        sFrame = ScrollableFrame(userFrame, setLayout=True,
                                 scrollBarPolicies=('never', 'asNeeded'),
                                 spacing=DEFAULTSPACING, margins=TABMARGINS,
                                 grid=(0, 0), gridSpan=(1, 3))

        row = 0
        self.objectPulldown = PulldownListCompoundWidget(sFrame,
                                                         grid=(row, 0), gridSpan=(1, 3), vAlign='top', hAlign='left',
                                                         orientation='left',
                                                         labelText='Strip/SpectrumDisplay',
                                                         callback=self._changeObjectPulldownCallback
                                                         )

        # add a spacer to separate from the common save widgets
        row += 1
        HLine(sFrame, grid=(row, 0), gridSpan=(1, 4), colour=getColours()[DIVIDER], height=20)

        row += 1
        topRow = row
        Label(sFrame, text='Page Size', grid=(row, 0), hAlign='left', vAlign='centre')
        self.pageSize = PulldownList(sFrame, vAlign='t', grid=(row, 1),
                                     callback=self._queuePageSizeCallback)
        self.pageSize.setData(texts=PAGESIZES)

        row += 1
        Label(sFrame, text='Page orientation', grid=(row, 0), hAlign='left', vAlign='centre')
        self.pageOrientation = RadioButtons(sFrame, PAGETYPES,
                                            grid=(row, 1), direction='h', hAlign='left', spacing=(20, 0),
                                            callback=self._queuePageOrientationCallback)
        row += 1
        Label(sFrame, text='Print Type', grid=(row, 0), hAlign='left', vAlign='centre')
        self.printType = RadioButtons(sFrame, list(EXPORTTYPES.keys()),
                                      grid=(row, 1), direction='h', hAlign='left', spacing=(20, 0),
                                      callback=self._queuePrintTypeCallback,
                                      # callback=self._changePrintType,
                                      )

        # create a pulldown for the foreground (axes) colour
        row += 1
        foregroundColourFrame = Frame(sFrame, grid=(row, 0), gridSpan=(1, 3), setLayout=True, showBorder=False)
        Label(foregroundColourFrame, text="Foreground Colour", vAlign='c', hAlign='l', grid=(0, 0))
        self.foregroundColourBox = PulldownList(foregroundColourFrame, vAlign='t', grid=(0, 1))
        self.foregroundColourButton = Button(foregroundColourFrame, vAlign='t', hAlign='l', grid=(0, 2), hPolicy='fixed',
                                             icon='icons/colours')
        fillColourPulldown(self.foregroundColourBox, allowAuto=False, includeGradients=False)
        self.foregroundColourBox.currentIndexChanged.connect(self._queueForegroundPulldownCallback)
        self.foregroundColourButton.clicked.connect(self._queueForegroundButtonCallback)

        # create a pulldown for the background colour
        row += 1
        backgroundColourFrame = Frame(sFrame, grid=(row, 0), gridSpan=(1, 3), setLayout=True, showBorder=False)
        Label(backgroundColourFrame, text="Background Colour", vAlign='c', hAlign='l', grid=(0, 0))
        self.backgroundColourBox = PulldownList(backgroundColourFrame, vAlign='t', grid=(0, 1))
        self.backgroundColourButton = Button(backgroundColourFrame, vAlign='t', hAlign='l', grid=(0, 2), hPolicy='fixed',
                                             icon='icons/colours')
        fillColourPulldown(self.backgroundColourBox, allowAuto=False, includeGradients=False)
        self.backgroundColourBox.currentIndexChanged.connect(self._queueBackgroundPulldownCallback)
        self.backgroundColourButton.clicked.connect(self._queueBackgroundButtonCallback)

        row += 1
        self.baseThicknessBox = DoubleSpinBoxCompoundWidget(sFrame, grid=(row, 0), gridSpan=(1, 3), hAlign='left',
                                                            labelText='Line Thickness',
                                                            # value=1.0,
                                                            decimals=2, step=0.05, minimum=0.01, maximum=20,
                                                            callback=self._queueBaseThicknessCallback,
                                                            )

        row += 1
        self.stripPaddingBox = DoubleSpinBoxCompoundWidget(sFrame, grid=(row, 0), gridSpan=(1, 3), hAlign='left',
                                                           labelText='Strip Padding',
                                                           # value=5,
                                                           decimals=0, step=1, minimum=0, maximum=50,
                                                           callback=self._queueStripPaddingCallback,
                                                           )

        row += 1
        self.exportDpiBox = DoubleSpinBoxCompoundWidget(sFrame, grid=(row, 0), gridSpan=(1, 3), hAlign='left',
                                                        labelText='Image dpi',
                                                        # value=300,
                                                        decimals=0, step=5, minimum=36, maximum=2400,
                                                        callback=self._queueDpiCallback,
                                                        )

        row += 1
        HLine(sFrame, grid=(row, 0), gridSpan=(1, 4), colour=getColours()[DIVIDER], height=20)
        row += 1

        self._setupRangeWidget(row, sFrame)
        row += 1

        HLine(sFrame, grid=(row, 0), gridSpan=(1, 4), colour=getColours()[DIVIDER], height=20)
        row += 1

        # widgets for handling screen scaling
        self._setupScalingWidget(row, sFrame)
        row += 1

        # widgets for handling fonts
        self._setupFontWidget(row, sFrame)
        row += 1

        self.treeView = PrintTreeCheckBoxes(sFrame, project=None, grid=(row, 0), gridSpan=(1, 4))
        self.treeView.itemClicked.connect(self._queueGetPrintOptionCallback)

        sFrame.layout().setRowStretch(row, 100)
        sFrame.addSpacer(5, 5, expandX=True, expandY=True, grid=(row, 3))

    def _setupRangeWidget(self, row, userFrame):
        """Set up the widgets for the range frame
        """
        _rangeFrame = Frame(userFrame, setLayout=True, grid=(row, 0), gridSpan=(1, 8), hAlign='left')
        self._rangeLeft = Frame(_rangeFrame, setLayout=True, grid=(0, 0))
        self._rangeRight = Frame(_rangeFrame, setLayout=True, grid=(0, 1), spacing=(0, 4))

        _rangeRow = 0
        self._useRegion = CheckBoxCompoundWidget(
                self._rangeRight,
                grid=(_rangeRow, 0), hAlign='left', gridSpan=(1, 6),
                orientation='right',
                labelText='Use override region for printing',
                callback=self._useOverrideCallback,
                tipText='If checked, use the regions selected below\notherwise use the visible print region for the strip'
                )
        _rangeRow += 1

        # radio buttons for setting mode
        _texts = ['Min/Max', 'Centre/Width']
        _tipTexts = ['Use minimum/maximum values to define the print region', 'Use centre/width values to define the print region']
        self._rangeRadio = RadioButtons(self._rangeRight, texts=_texts, tipTexts=_tipTexts, direction='h', hAlign='l', selectedInd=1,
                                        grid=(_rangeRow, 0), gridSpan=(1, 8),
                                        callback=self._setModeCallback)
        _rangeRow += 1

        # row of labels
        self._axisLabels = []
        for ii, txt in enumerate(STRIPBUTTONS):
            _label = Label(self._rangeRight, grid=(_rangeRow, ii), text=txt, hAlign='left')
            _label.setVisible(ii <= 0)
            self._axisLabels.append(_label)
        _rangeRow += 1

        # rows containing spinboxes
        focusColour = getColours()[BORDERFOCUS]
        axes = STRIPAXES
        self._axisSpinboxes = []
        for ii, axis in enumerate(axes):
            _label = Label(self._rangeRight, text=axis, grid=(_rangeRow, 0), hAlign='left')

            # add a box for the selected row - change colour depending on strip-direction? need to be linked
            _colourBox = HighlightBox(self._rangeRight, grid=(_rangeRow, 0), gridSpan=(1, 6), colour=focusColour, lineWidth=1, showBorder=False)
            _colourBox.setFixedHeight(_label.height() + 4)

            _widgets = [_label]
            for bt in range(len(STRIPBUTTONS[1:])):
                _spinbox = DoubleSpinbox(self._rangeRight, grid=(_rangeRow, bt + 1), decimals=2, step=0.1,  # hAlign='left',
                                         callback=partial(self._setSpinbox, ii, STRIPBUTTONS[bt + 1]))
                _spinbox.setFixedWidth(140)
                _spinbox._widgetRow = ii
                # add a filter to update the selected box around the row
                _spinbox.installEventFilter(self)
                _spinbox.setVisible(False)

                _widgets.append(_spinbox)

            _widgets.append(_colourBox)
            _rangeRow += 1

            # store the widgets for the callbacks...
            self._axisSpinboxes.append(_widgets)

        # buttons for setting the spin-boxes from strip
        _texts = ['Set Print Region', 'Set Min', 'Set Max', 'Set Centre', 'Set Width']
        _tipTexts = ['Set all values for the print region from the selected strip.\nValues are set for the selected row',
                     'Set the minimum value for the print region from the selected strip.\nValue is set for the selected row.\n'
                     'If the maximum value is too low, the minimum value will be set to the closest allowed value',
                     'Set the maximum value for the print region from the selected strip.\nValue is set for the selected row.\n'
                     'If the minimum value is too high, the maximum value will be set to the closest allowed value',
                     'Set the centre value for the print region from the selected strip.\nValue is set for the selected row',
                     'Set the width value for the print region from the selected strip.\nValue is set for the selected row']
        _callbacks = [self._setStripRegion, self._setStripMin, self._setStripMax, self._setStripCentre, self._setStripWidth]
        self._setRangeButtons = ButtonList(self._rangeRight, texts=_texts, tipTexts=_tipTexts,
                                           grid=(_rangeRow, 0), gridSpan=(1, 8), hAlign='l',
                                           callbacks=_callbacks,
                                           setMinimumWidth=False, setLastButtonFocus=False,
                                           )
        for _btn in self._setRangeButtons.buttons[1:]:
            _btn.setVisible(False)
        _rangeRow += 1

        self._rangeRight.addSpacer(5, 5, grid=(_rangeRow, 6), expandX=True)
        self._rangeRight.addSpacer(4, 4, grid=(_rangeRow, 5))
        _rangeRow += 1

        # list to hold the current strips
        Label(self._rangeLeft, grid=(0, 0), text='Strips', hAlign='left')
        self._stripLists = _StripListWidget(self._rangeLeft, grid=(1, 0), callback=self._setRangeState,
                                            multiSelect=True, acceptDrops=False, copyDrop=False,
                                            parentPopup=self,
                                            parentCallbacks=(self._copyRangeCallback,
                                                             self._pasteRangeCallback,
                                                             self._pasteRangeAllCallback)
                                            )
        # self._rangeLeft.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self._rangeLeft.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._stripLists.setFixedHeight(8 * getFontHeight())

        _rangeFrame.getLayout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._rangeRight.getLayout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._rangeRight.layout().setColumnStretch(6, 1000)
        self._rangeRight.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        return _rangeRow

    def _setupScalingWidget(self, row, userFrame):
        """Set up the widgets for the scaling frame
        """
        _frame = Frame(userFrame, setLayout=True, grid=(row, 0), gridSpan=(1, 8), hAlign='left')

        _row = 0
        self.scalingMode = PulldownListCompoundWidget(_frame,
                                                      grid=(_row, 0), hAlign='left',
                                                      orientation='left',
                                                      labelText='Scaling',
                                                      texts=SCALING_MODES,
                                                      tipText='Set the scaling option for printing',
                                                      # callback=self._scalingCallback
                                                      callback=self._queueScalingModeCallback,
                                                      )
        self.scalingPercentage = DoubleSpinbox(_frame, grid=(_row, 1), min=1.0, max=100.0, decimals=0, step=1,
                                               callback=self._queueScalingPercentageCallback
                                               )
        self.scalingUnits = ScientificDoubleSpinBox(_frame, grid=(_row, 2), gridSpan=(1, 2), min=0.0, max=1e10, step=0.1,
                                                    callback=self._queueScalingUnitsCallback,
                                                    )
        self.scalingAxis = PulldownListCompoundWidget(_frame, grid=(_row, 4),
                                                      labelText='Scale Axis', texts=STRIPAXES,
                                                      tipText='Select the axis to apply the scaling to',
                                                      callback=self._queueScalingAxisCallback,
                                                      )
        self.scalingPercentage.setMinimumCharacters(10)
        self.scalingUnits.setMinimumCharacters(10)
        self.scalingUnits.setVisible(False)
        self.scalingAxis.setVisible(False)

    def _setupFontWidget(self, row, userFrame):
        """Set up the widgets for the font frame
        """
        _frame = Frame(userFrame, setLayout=True, grid=(row, 0), gridSpan=(1, 8), hAlign='left')

        _row = 0
        _tip = "If checked, use the selected font and fontSize for printing.\n" \
               "If the font selected is 'Default Font' then the default font will be used at the specified fontSize.\n" \
               "If unchecked, the default font will be scaled proportional to the strip"
        self._useFontCheckbox = CheckBoxCompoundWidget(_frame,
                                                       grid=(_row, 0), hAlign='left',
                                                       orientation='right',
                                                       labelText='Use selected font for printing',
                                                       tipText=_tip,
                                                       callback=self._queueUseFontCallback,
                                                       )

        # self._fontButton = Button(_frame, text='<No Font Set>', grid=(_row, 1), hAlign='l', callback=self._getFont)
        # self._fontButton.setEnabled(False)
        # self._fontButton.setVisible(False)  # hide for the minute - only .ttf fonts work so using a pulldown

        self._fontPulldown = PulldownList(_frame, grid=(_row, 2))
        self._fontSpinbox = DoubleSpinbox(_frame, min=1, max=100, decimals=0, step=1, grid=(_row, 3),
                                          callback=self._queueFontSizeCallback)
        self._fontPulldown.setEnabled(False)
        self._fontSpinbox.setEnabled(False)
        self._fontPulldown.setCallback(self._queueFontNameCallback)
        # self._fontPulldown.setCallback(partial(self._setPulldownTextColour, self._fontPulldown))

    def _initialiseStripList(self):
        """Set up the lists containing strips.spectrumDisplays before populating
        """
        self.objects = None
        self._currentStrip = None
        self._currentStrips = []  # there may be multiple selected in the stripList
        self._currentAxis = 0
        self._stripDict = {}
        self._localStripDict = {}

        if self.strips:
            self.objects = {strip.id: (strip, strip.pid) for strip in self.strips}
            for strip in self.strips:
                # make two copies of the strip ranges
                _data = self._stripDict[strip.id] = _StripData()
                _data.strip = strip
                _data._initialise()

                _data = self._localStripDict[strip.id] = _StripData()
                _data.strip = strip
                _data._initialise()

            # define the contents for the object pulldown
            if len(self.strips) > 1 and self.includeSpectrumDisplays:
                # get the list of spectrumDisplays containing the strips
                specDisplays = {strip.spectrumDisplay for strip in self.strips if len(strip.spectrumDisplay.strips) > 1}

                # add to the pulldown objects
                for spec in specDisplays:
                    self.objects[f'SpectrumDisplay: {spec.id}'] = (spec, spec.pid)

    def _setStripRegion(self, *args):
        try:
            dd = self._stripDict.get(self._currentStrip)
            ii = self._currentAxis
            ddAxis = dd.axes[ii]
            # set all values for the print region
            region = dd.strip.getAxisRegion(ii)
            ddAxis[STRIPMIN], ddAxis[STRIPMAX] = min(region), max(region)
            ddAxis[STRIPCENTRE] = dd.strip.getAxisPosition(ii)
            ddAxis[STRIPWIDTH] = dd.strip.getAxisWidth(ii)

        except Exception:
            getLogger().debug2('Error updating _setStripRegion')
        else:
            self._setRangeState(self._currentStrip)
            self._focusButton(self._currentAxis, STRIPMIN if dd.minMaxMode == 0 else STRIPCENTRE)

            # set the values for the other strips in the spectrum-display
            if (sd := dd.strip.spectrumDisplay) and ((sd.stripArrangement == 'Y' and ii == 1) or
                                                     (sd.stripArrangement == 'X' and ii == 0)):
                for strip in sd.strips:
                    if strip == self._currentStrip:
                        continue

                    ddAxis = self._stripDict.get(strip.id).axes[ii]
                    ddAxis[STRIPMIN], ddAxis[STRIPMAX] = min(region), max(region)
                    ddAxis[STRIPCENTRE] = dd.strip.getAxisPosition(ii)
                    ddAxis[STRIPWIDTH] = dd.strip.getAxisWidth(ii)
                    self._setRangeState(strip, updateCurrent=False)

    @staticmethod
    def _setStripMinValue(ddAxis, value):
        """Set the minimum value
        Update the row values and set the spinbox constraints"""
        _value = min(value, ddAxis[STRIPMAX])
        ddAxis[STRIPMIN] = _value
        # update the centre/width
        _centre = (_value + ddAxis[STRIPMAX]) / 2.0
        ddAxis[STRIPCENTRE] = _centre
        ddAxis[STRIPWIDTH] = abs(ddAxis[STRIPMAX] - _value)

        # value has not been clipped to STRIPMAX value
        return _value == value

    def _stripRegion(self, strip, funcName=None):
        dd = self._stripDict.get(strip)
        ddAxis = dd.axes[self._currentAxis]
        result = None
        if funcName and (func := getattr(dd.strip, funcName, None)):
            result = func(self._currentAxis)
        return dd, ddAxis, result

    def _validStripSetter(self, funcName, focusButton):

        # small object to facilitate passing data to/from iterator
        @dataclass
        class _setterReturn:
            dd = None
            ddAxis = None
            value = None
            okay: bool = False


        try:
            result = _setterReturn()
            result.dd, result.ddAxis, result.value = self._stripRegion(self._currentStrip, funcName)
            yield result

        except Exception:
            getLogger().debug2('Error updating _setStripMin')
        else:
            self._setRangeState(self._currentStrip)
            if not result.okay:
                # flash a quick warning to show that the value has been clipped to the max value
                self._axisSpinboxes[self._currentAxis][STRIPBUTTONS.index(STRIPMIN)]._flashError()

            # set the values for the other strips in the spectrum-display
            if (sd := result.dd.strip.spectrumDisplay) and ((sd.stripArrangement == 'Y' and self._currentAxis == 1) or
                                                            (sd.stripArrangement == 'X' and self._currentAxis == 0)):
                for strip in sd.strips:
                    if strip == self._currentStrip:
                        continue

                    result.dd, result.ddAxis, _ = self._stripRegion(strip.id)
                    yield result
                    self._setRangeState(strip, updateCurrent=False)

            self._focusButton(self._currentAxis, focusButton)

    def _setStripMin(self, *args):

        for stripSet in self._validStripSetter('getAxisRegion', STRIPMIN):
            stripSet.okay = self._setStripMinValue(stripSet.ddAxis, min(stripSet.value))

        # return
        # try:
        #     ddAxis, region = self._stripRegion(self._currentStrip, 'getAxisRegion')
        #     okay = self._setStripMinValue(ddAxis, min(region))
        #
        # except Exception:
        #     getLogger().debug2('Error updating _setStripMin')
        # else:
        #     self._setRangeState(self._currentStrip)
        #     self._focusButton(self._currentAxis, STRIPMIN)
        #     if not okay:
        #         # flash a quick warning to show that the value has been clipped to the max value
        #         self._axisSpinboxes[self._currentAxis][STRIPBUTTONS.index(STRIPMIN)]._flashError()
        #
        #     # set the values for the other strips in the spectrum-display
        #     if (sd := self.spectrumDisplay) and (sd.stripArrangement == 'Y' and self._currentAxis == 1) or (sd.stripArrangement == 'X' and self._currentAxis == 0):
        #         for strip in sd.strips:
        #             if strip == self._currentStrip:
        #                 continue
        #
        #             ddAxis, _ = self._stripRegion(strip.id)
        #             self._setStripMinValue(ddAxis, min(region))
        #             self._setRangeState(strip, updateCurrent=False)

    @staticmethod
    def _setStripMaxValue(ddAxis, value):
        """Set the maximum value
        Update the row values and set the spinbox constraints"""
        _value = max(value, ddAxis[STRIPMIN])
        ddAxis[STRIPMAX] = _value
        # update the centre/width
        _centre = (ddAxis[STRIPMIN] + _value) / 2.0
        ddAxis[STRIPCENTRE] = _centre
        ddAxis[STRIPWIDTH] = abs(_value - ddAxis[STRIPMIN])

        # value has not been clipped to STRIPMIN value
        return _value == value

    def _setStripMax(self, *args):

        for stripSet in self._validStripSetter('getAxisRegion', STRIPMAX):
            stripSet.okay = self._setStripMaxValue(stripSet.ddAxis, max(stripSet.value))

        # return
        # try:
        #     ddAxis, region = self._stripRegion(self._currentStrip, 'getAxisRegion')
        #     okay = self._setStripMaxValue(ddAxis, max(region))
        #
        # except Exception as es:
        #     getLogger().debug2('Error updating _setStripMax')
        # else:
        #     self._setRangeState(self._currentStrip)
        #     self._focusButton(self._currentAxis, STRIPMAX)
        #     if not okay:
        #         # flash a quick warning to show that the value has been clipped to the min value
        #         self._axisSpinboxes[self._currentAxis][STRIPBUTTONS.index(STRIPMAX)]._flashError()
        #
        #     # set the values for the other strips in the spectrum-display
        #     if (sd := self.spectrumDisplay) and (sd.stripArrangement == 'Y' and self._currentAxis == 1) or (sd.stripArrangement == 'X' and self._currentAxis == 0):
        #         for strip in sd.strips:
        #             if strip == self._currentStrip:
        #                 continue
        #
        #             ddAxis, _ = self._stripRegion(strip.id)
        #             self._setStripMaxValue(ddAxis, max(region))
        #             self._setRangeState(strip, updateCurrent=False)

    @staticmethod
    def _setStripCentreValue(ddAxis, centre):
        """Set the centre value
        Update the row values and set the spinbox constraints"""
        ddAxis[STRIPCENTRE] = centre
        # update the min/max
        diff = abs(ddAxis[STRIPWIDTH] / 2.0)
        ddAxis[STRIPMIN] = centre - diff
        ddAxis[STRIPMAX] = centre + diff

    def _setStripCentre(self, *args):
        for stripSet in self._validStripSetter('getAxisPosition', STRIPCENTRE):
            stripSet.okay = self._setStripCentreValue(stripSet.ddAxis, stripSet.value)

        # return
        # try:
        #     ddAxis, centre = self._stripRegion(self._currentStrip, 'getAxisPosition')
        #     self._setStripCentreValue(ddAxis, centre)
        #
        # except Exception:
        #     getLogger().debug2('Error updating _setStripCentre')
        # else:
        #     self._setRangeState(self._currentStrip)
        #     self._focusButton(self._currentAxis, STRIPCENTRE)
        #
        #     # set the values for the other strips in the spectrum-display
        #     if (sd := self.spectrumDisplay) and (sd.stripArrangement == 'Y' and self._currentAxis == 1) or (sd.stripArrangement == 'X' and self._currentAxis == 0):
        #         for strip in sd.strips:
        #             if strip == self._currentStrip:
        #                 continue
        #
        #             ddAxis, _ = self._stripRegion(strip.id)
        #             self._setStripCentreValue(ddAxis, centre)
        #             self._setRangeState(strip, updateCurrent=False)

    @staticmethod
    def _setStripWidthValue(ddAxis, width):
        """Set the width value
        Update the row values and set the spinbox constraints"""
        ddAxis[STRIPWIDTH] = width
        # update the min/max
        centre = ddAxis[STRIPCENTRE]
        ddAxis[STRIPMIN] = centre - abs(width / 2.0)
        ddAxis[STRIPMAX] = centre + abs(width / 2.0)

    def _setStripWidth(self, *args):
        for stripSet in self._validStripSetter('getAxisWidth', STRIPWIDTH):
            stripSet.okay = self._setStripCentreValue(stripSet.ddAxis, stripSet.value)

        # return
        # try:
        #     ddAxis, width = self._stripRegion(self._currentStrip, 'getAxisWidth')
        #     self._setStripWidthValue(ddAxis, width)
        #
        # except Exception as es:
        #     getLogger().debug2('Error updating _setStripWidth')
        # else:
        #     self._setRangeState(self._currentStrip)
        #     self._focusButton(self._currentAxis, STRIPWIDTH)
        #
        #     # set the values for the other strips in the spectrum-display
        #     if (sd := self.spectrumDisplay) and (sd.stripArrangement == 'Y' and self._currentAxis == 1) or (sd.stripArrangement == 'X' and self._currentAxis == 0):
        #         for strip in sd.strips:
        #             if strip == self._currentStrip:
        #                 continue
        #
        #             ddAxis, _ = self._stripRegion(strip.id)
        #             self._setStripWidthValue(ddAxis, width)
        #             self._setRangeState(strip, updateCurrent=False)

    def _setSpinbox(self, row, button, value):
        """Set the value in the storage dict from the spinbox change
        """
        buttonDict = {STRIPMIN   : (self._setStripMinValue, 'getAxisRegion'),
                      STRIPMAX   : (self._setStripMaxValue, 'getAxisRegion'),
                      STRIPCENTRE: (self._setStripCentreValue, 'getAxisPosition'),
                      STRIPWIDTH : (self._setStripWidthValue, 'getAxisWidth')
                      }

        self._setSpinboxAxis(row)
        if (found := buttonDict.get(button)):
            func, funcName = found
            for stripSet in self._validStripSetter(funcName, button):
                stripSet.okay = func(stripSet.ddAxis, value)

        # return
        # #
        # self._setSpinboxAxis(row)
        # try:
        #     _dd = self._stripDict.get(self._currentStrip)
        #
        #     buttonDict = {STRIPMIN: self._setStripMinValue,
        #                   STRIPMAX: self._setStripMaxValue,
        #                   STRIPCENTRE: self._setStripCentreValue,
        #                   STRIPWIDTH: self._setStripWidthValue
        #         }
        #     if (func := buttonDict.get(button)):
        #         func(_dd.axes[row], value)
        #
        # except Exception:
        #     getLogger().debug2('Error updating _setSpinbox')
        # else:
        #     self._setRangeState(self._currentStrip)
        #     self._focusButton(row, button)
        #
        #     # set the values for the other strips in the spectrum-display
        #     if (sd := self.spectrumDisplay) and (sd.stripArrangement == 'Y' and self._currentAxis == 1) or (sd.stripArrangement == 'X' and self._currentAxis == 0):
        #         for strip in sd.strips:
        #             if strip == self._currentStrip:
        #                 continue
        #
        #             ddAxis, _ = self._stripRegion(strip.id)
        #             func(ddAxis, value)
        #             self._setRangeState(strip, updateCurrent=False)

    def _setSpinboxAxis(self, row):
        """Change the current selected row of spinboxes"""
        self._currentAxis = row
        for ii in range(2):
            _box = self._axisSpinboxes[ii][-1]
            if _box.isEnabled():
                _box.showBorder = (self._currentAxis == ii)

    def eventFilter(self, obj, event):
        """Event filter to handle focus change on spinboxes
        """
        if event.type() in [QtCore.QEvent.WindowActivate, QtCore.QEvent.FocusIn]:
            self._setSpinboxAxis(obj._widgetRow)

        return False

    def _useOverrideCallback(self, value):
        """User has checked/unchecked useOverride
        """
        try:
            _dd = self._stripDict.get(self._currentStrip)
            _dd.useRegion = value
        except Exception as es:
            getLogger().debug2('Error updating _useOverrideCallback')
        else:
            self._setRangeState(self._currentStrip)

            # set the values for the other strips in the spectrum-display
            if (sd := _dd.strip.spectrumDisplay):
                for strip in sd.strips:
                    if strip == self._currentStrip:
                        continue

                    ddAxis = self._stripDict.get(strip.id)
                    ddAxis.useRegion = value
                    self._setRangeState(strip, updateCurrent=False)

    def _setModeCallback(self):
        """User has changed minMax/centreWidth mode
        """
        try:
            mode = self._rangeRadio.getIndex()
            # change all to the same mode
            for dd in self._stripDict.values():
                dd.minMaxMode = mode
        except Exception as es:
            getLogger().debug2('Error updating _setModeCallback')
        else:
            self._setRangeState(self._currentStrip)

    def _fontCheckBoxCallback(self, value):
        """Handle checking/unchecking font checkbox
        """
        self._fontPulldown.setEnabled(self._useFontCheckbox.isChecked())
        self._fontSpinbox.setEnabled(self._useFontCheckbox.isChecked())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def populate(self, userframe):
        """Populate the widgets with project
        """
        with self.blockWidgetSignals(self.mainWidget):
            self._populate()

        self._setScalingVisible()
        self._setUseFontVisible()
        self._setPulldownTextColour(self._fontPulldown)

        # set the matching values for the connected strips from the initial strip
        if (dd := self._stripDict.get(self._currentStrip)):
            self._useOverrideCallback(dd.useRegion)
            self._setStripMax()
            self._setStripMin()

    def _populate(self):
        """Populate the widget
        """
        self.printSettings = self.application.preferences.printSettings

        for strip in self.strips:
            # copy from the local to the stripDict
            _value = self._localStripDict[strip.id].toDict()
            self._stripDict[strip.id].fromDict(_value)

            # # NOTE:ED - ranges are currently not saved to preferences correctly
            # _value = self.printSettings.printRanges.get(strip.id)
            # if _value:
            #     self._stripDict[strip.id].fromDict(_value)
            #     self._localStripDict[strip.id].fromDict(_value)

        # define the contents for the object pulldown
        if len(self.strips) > 1:
            pulldownLabel = 'Select Strip:'
            if self.includeSpectrumDisplays:

                # get the list of spectrumDisplays containing the strips
                for strip in self.strips:
                    if len(strip.spectrumDisplay.strips) > 1:
                        pulldownLabel = 'Select Item:'
                        break
        else:
            pulldownLabel = 'Current Strip:'

        self.objectPulldown.setLabelText(pulldownLabel)
        if self.objects:
            self.objectPulldown.pulldownList.setData(sorted(list(self.objects.keys())))
        # set the page types
        self.pageSize.set(self.printSettings.pageSize)
        self.pageOrientation.set(self.printSettings.pageOrientation, silent=True)
        self.printType.set(self.printSettings.printType, silent=True)

        # populate pulldown from foreground colour
        spectrumColourKeys = list(spectrumColours.keys())
        self.foregroundColour = self.printSettings.foregroundColour
        self.backgroundColour = self.printSettings.backgroundColour

        if self.foregroundColour not in spectrumColourKeys:
            # add new colour to the pulldowns if not defined
            addNewColourString(self.foregroundColour)
            fillColourPulldown(self.foregroundColourBox, allowAuto=False, includeGradients=False)
            fillColourPulldown(self.backgroundColourBox, allowAuto=False, includeGradients=False)
        self.foregroundColourBox.setCurrentText(spectrumColours[self.foregroundColour])

        if self.backgroundColour not in spectrumColourKeys:
            # add new colour to the pulldowns if not defined
            addNewColourString(self.backgroundColour)
            fillColourPulldown(self.foregroundColourBox, allowAuto=False, includeGradients=False)
            fillColourPulldown(self.backgroundColourBox, allowAuto=False, includeGradients=False)
        self.backgroundColourBox.setCurrentText(spectrumColours[self.backgroundColour])

        self.baseThicknessBox.setValue(self.printSettings.baseThickness)
        self.stripPaddingBox.setValue(self.printSettings.stripPadding)
        self.exportDpiBox.setValue(self.printSettings.dpi)

        # set the pulldown to current strip if selected
        if self.current and self.current.strip:
            self.objectPulldown.select(self.current.strip.id)
            self.strip = self.current.strip
        elif self.strips:
            self.objectPulldown.select(self.strips[0].id)
            self.strip = self.strips[0]
        else:
            self.strip = None
        self.spectrumDisplay = None

        # fill the range widgets from the strips
        self._populateRange()
        # fill the scaling widgets
        self._populateScaling()
        # fill the font widgets
        self._populateFont()
        # fill the tree from the current strip
        self._populateTreeView()

        # set the default save name
        exType = self.printType.get() or 'PDF'
        if exType in EXPORTTYPES:
            exportExtension = EXPORTTYPES[exType][EXPORTEXT]
        else:
            raise ValueError('bad export type')

        self.setSave(self.objectPulldown.getText() + exportExtension)

    @staticmethod
    def _resetPulldownColours(combo):
        model = combo.model()
        for ii in range(combo.count()):
            idx = model.index(ii)
            itm = combo.itemFromIndex(idx)
            if itm.text().startswith(PulldownFill):
                itm.setFlags(itm.flags() & ~QtCore.Qt.ItemIsEnabled)
                # reset the foreground colour to follow palette
                itm.setData(None, QtCore.Qt.ForegroundRole)

    @staticmethod
    def _setListColours(combo, validStripIds):
        model = combo.model()
        for ind in range(combo.count()):
            idx = model.index(ind)
            itm = combo.itemFromIndex(idx)
            if PulldownFill not in itm.text() and itm.text() in validStripIds:
                itm.setData(PRINT_COLOR, QtCore.Qt.ForegroundRole)
            else:
                itm.setData(None, QtCore.Qt.ForegroundRole)

    def _populateRange(self):
        """Populate the list/spinboxes in range widget
        """
        self._rangeLeft.setVisible(True)  # self.spectrumDisplay is not None)

        self._stripLists.clear()
        if not self.strip:
            return

        self._setRangeState(self.strip.id, _updateQueue=False)

        if self.spectrumDisplay:
            validStripIds = [strip.id for strip in self.spectrumDisplay.strips]
            otherStrips = []
        else:
            validStripIds = [self.strip.id]
            otherStrips = [strip.id for strip in self.strip.spectrumDisplay.strips if strip != self.strip]
        stripGroup = validStripIds + otherStrips

        # validStripIds = [strip.id for strip in self.spectrumDisplay.strips] if self.spectrumDisplay else [self.strip.id]
        ll = ['-- Strips to print --', *validStripIds]
        otherStrips.extend([strip.id for strip in self.strips if strip.id not in ll and strip.id not in otherStrips])
        if otherStrips:
            ll.extend(['-- Other strips --', *otherStrips])

        self._stripLists.addItems(ll)

        # set the correct colours
        self._resetPulldownColours(self._stripLists)
        if len(stripGroup) > 1:
            self._setListColours(self._stripLists, stripGroup)  # probably not necessary with the group division

        self._stripLists.select(self._currentStrip)
        # self._stripLists.setCurrentRow(1)

    def _setRangeState(self, strip, setButton=None, setRow=None, updateCurrent=True, _updateQueue=True):
        try:
            stripId = strip.text()
        except Exception:
            stripId = strip
        finally:
            self._rangeRight.setVisible(False)

            with self.blockWidgetSignals(self._rangeRight):

                if updateCurrent:
                    # set the current-id for updating range dict
                    self._currentStrip = stripId

                # remove constraints so spin-boxes can be updated
                self._setSpinboxConstraints(stripId, state=False)

                if _dd := self._stripDict.get(stripId, None):
                    self._useRegion.set(_dd.useRegion)
                    self._rangeRadio.setIndex(_dd.minMaxMode)

                    # change visibility of buttons dependent on minMaxMode
                    for btn in [STRIPMIN, STRIPMAX]:
                        self._axisLabels[STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 0)
                        for ii in range(len(STRIPAXES)):
                            self._axisSpinboxes[ii][STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 0)
                        self._setRangeButtons.buttons[STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 0)

                    for btn in [STRIPCENTRE, STRIPWIDTH]:
                        self._axisLabels[STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 1)
                        for ii in range(len(STRIPAXES)):
                            self._axisSpinboxes[ii][STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 1)
                        self._setRangeButtons.buttons[STRIPBUTTONS.index(btn)].setVisible(_dd.minMaxMode == 1)

                    for ii in range(len(STRIPAXES)):
                        axis = _dd.axes[ii]
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMIN)].set(axis[STRIPMIN])
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMAX)].set(axis[STRIPMAX])
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPCENTRE)].set(axis[STRIPCENTRE])
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPWIDTH)].set(axis[STRIPWIDTH])

                        for bb in self._axisSpinboxes[ii]:
                            bb.setEnabled(_dd.useRegion)
                        self._axisSpinboxes[ii][-1].showBorder = (_dd.useRegion and (self._currentAxis == ii))

                    # self._rangeRadio.setEnabled(_dd.useRegion)
                    self._setRangeButtons.setEnabled(_dd.useRegion)

                    # set the colours for the highlight boxes
                    if (sd := _dd.strip.spectrumDisplay) and len(sd.strips) > 1:
                        if sd.stripArrangement == 'Y':
                            self._axisSpinboxes[0][-1].setColour(getColours()[BORDERFOCUS])
                            self._axisSpinboxes[1][-1].setColour(SELECTAXIS_COLOR if self.strip in sd.strips else SELECTAXIS_COLOR2)
                        else:
                            self._axisSpinboxes[0][-1].setColour(SELECTAXIS_COLOR if self.strip in sd.strips else SELECTAXIS_COLOR2)
                            self._axisSpinboxes[1][-1].setColour(getColours()[BORDERFOCUS])

                    else:
                        self._axisSpinboxes[0][-1].setColour(getColours()[BORDERFOCUS])
                        self._axisSpinboxes[1][-1].setColour(getColours()[BORDERFOCUS])

                # re-enable constraints
                self._setSpinboxConstraints(stripId)

            self._rangeRight.setVisible(True)
            self._rangeRight.update()

            if _updateQueue:
                self._queuePrintRangesCallback(None)

    def _populateScaling(self):
        """Populate the widgets in the scaling frame
        """
        self._scalingModeIndex = SCALING_MODES.index(self.printSettings.scalingMode)
        self.scalingMode.select(self.printSettings.scalingMode)
        self.scalingPercentage.set(self.printSettings.scalingPercentage)
        self.scalingUnits.set(self.printSettings.scalingUnits)
        self.scalingAxis.select(self.printSettings.scalingAxis)

    def _populateFont(self):
        """Populate the widgets in the font frame
        """
        # fontString = self.application.preferences.printSettings.get('font')
        # if fontString:
        #     self._printFont = fontString
        #     self.setFontText(self._fontButton, fontString)
        # else:
        #     self._printFont = None
        #     self._fontButton.setText('<No Font Set>')

        self._fontPulldown.setData(texts=[DEFAULT_FONT, ] + sorted(list(self.familyFonts.keys())), )

        # add some colour to show the default option
        model = self._fontPulldown.model()
        color = QtGui.QColor('gray')
        model.item(0).setForeground(color)

        fontName = self.printSettings.get('fontName')
        fontSize = self.printSettings.get('fontSize')
        self._fontPulldown.set(fontName)
        self._fontSpinbox.set(fontSize)
        value = self.printSettings.useFont
        self._useFontSetting = value
        self._useFontCheckbox.set(value)

        self._setPulldownTextColour(self._fontPulldown)

    @staticmethod
    def _setPulldownTextColour(combo, value=None):
        """Set the colour of the pulldown text
        """
        ind = combo.currentIndex()
        model = combo.model()
        item = model.item(ind)
        if item is not None:  # and (ind == 0 or combo.isEnabled()):
            color = item.foreground().color()
            # use the palette to change the colour of the selection text - may not match for other themes
            palette = combo.palette()
            palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Text, color)
            combo.setPalette(palette)

    def _focusButton(self, row, button):
        """Set the focus to the selected button
        """
        try:
            self._axisSpinboxes[row][STRIPBUTTONS.index(button)].setFocus()
        except Exception as es:
            getLogger().debug2('Error updating _focusButton')

    def _setSpinboxConstraints(self, stripId, state=True):
        """Set the min/max/width constraints for the spinboxes associated with the stripId
        """
        from math import floor, log10

        def fexp(f):
            return int(floor(log10(abs(f)))) if f != 0 else 0

        try:
            if _dd := self._stripDict.get(stripId, None):
                for ii in range(len(STRIPAXES)):
                    axis = _dd.axes[ii]
                    # set min.max constraints for buttons
                    # not sure if these need to change as the button values are changed
                    self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMIN)].setMaximum(axis[STRIPMAX] if state else POSINFINITY)
                    self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMAX)].setMinimum(axis[STRIPMIN] if state else -POSINFINITY)
                    self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPWIDTH)].setMinimum(0.0)
                    if state:
                        dec = abs(axis[STRIPMAX] - axis[STRIPMIN])
                        step = max(0.1, 10 ** fexp(dec * 0.01))
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMAX)].setSingleStep(step)
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPMIN)].setSingleStep(step)
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPCENTRE)].setSingleStep(step)
                        self._axisSpinboxes[ii][STRIPBUTTONS.index(STRIPWIDTH)].setSingleStep(step)

        except Exception as es:
            getLogger().debug2('Error updating _setSpinboxConstraints')

    def storeWidgetState(self):
        """Store the state of the widgets between popups
        """
        _value = {k: v.toDict() for k, v in self._localStripDict.items()}
        ExportStripToFilePopup._storedState[self._SAVESTRIPS] = _value

        ExportStripToFilePopup._storedState[self._SAVECURRENTSTRIP] = self._currentStrip
        ExportStripToFilePopup._storedState[self._SAVECURRENTAXIS] = self._currentAxis

    def restoreWidgetState(self):
        """Restore the state of the widgets
        """
        values = ExportStripToFilePopup._storedState.get(self._SAVESTRIPS, {})
        for k, v in values.items():
            _val = _StripData()
            _val.fromDict(v)
            self._localStripDict[k] = _val

        if _val := ExportStripToFilePopup._storedState.get(self._SAVECURRENTSTRIP, None):
            self._currentStrip = _val
        self._currentAxis = ExportStripToFilePopup._storedState.get(self._SAVECURRENTAXIS, 0)

    def _changeObjectPulldownCallback(self, value):
        selected = self.objectPulldown.getText()
        exType = self.printType.get()
        if exType in EXPORTTYPES:
            exportExtension = EXPORTTYPES[exType][EXPORTEXT]
        else:
            raise ValueError('bad export type')

        if 'SpectrumDisplay' in selected:
            self.spectrumDisplay = self.objects[selected][0]
            self.strip = self.spectrumDisplay.strips[0]  # self._selectedStrip
            self.setSave(self.spectrumDisplay.id + exportExtension)

            # set the values for the other strips in the spectrum-display
            if self.spectrumDisplay.stripArrangement == 'Y':
                self._axisSpinboxes[0][-1].setColour(getColours()[BORDERFOCUS])
                self._axisSpinboxes[1][-1].setColour('orange')
            else:
                self._axisSpinboxes[0][-1].setColour('orange')
                self._axisSpinboxes[1][-1].setColour(getColours()[BORDERFOCUS])

        else:
            self.spectrumDisplay = None
            self.strip = self.objects[selected][0]

            self.setSave(self.strip.id + exportExtension)

            self._axisSpinboxes[0][-1].setColour(getColours()[BORDERFOCUS])
            self._axisSpinboxes[1][-1].setColour(getColours()[BORDERFOCUS])

        self._currentStrip = self.strip.id
        self._populateRange()

        # fill the scaling widgets
        self._populateScaling()

        selectedList = self.treeView.getCheckStateItems()
        self._populateTreeView(selectedList)

    def _populateTreeView(self, selectList=None):
        self.treeView.clear()

        printItems = []
        if strip := (self.spectrumDisplay.strips[0] if self.spectrumDisplay else self.strip):
            # add Spectra to the treeView
            if strip.spectrumViews:
                item = QtWidgets.QTreeWidgetItem(self.treeView)
                item.setText(0, OPTIONSPECTRA)
                item.setFlags(int(item.flags()) | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                for specView in strip.spectrumViews:
                    child = QtWidgets.QTreeWidgetItem(item)
                    child.setFlags(int(child.flags()) | QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, specView.spectrum)
                    child.setText(0, specView.spectrum.pid)
                    child.setCheckState(0, QtCore.Qt.Unchecked if specView.isDisplayed else QtCore.Qt.Unchecked)

            # find peak/integral/multiplets attached to the spectrumViews
            peakLists = []
            integralLists = []
            multipletLists = []
            for specView in strip.spectrumViews:
                validPeakListViews = list(specView.peakListViews)
                validIntegralListViews = list(specView.integralListViews)
                validMultipletListViews = list(specView.multipletListViews)
                peakLists.extend(validPeakListViews)
                integralLists.extend(validIntegralListViews)
                multipletLists.extend(validMultipletListViews)

            printItems = []
            if peakLists:
                item = QtWidgets.QTreeWidgetItem(self.treeView)
                item.setText(0, OPTIONPEAKLISTS)
                item.setFlags(int(item.flags()) | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                for pp in peakLists:
                    child = QtWidgets.QTreeWidgetItem(item)
                    child.setFlags(int(child.flags()) | QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, pp.peakList)
                    child.setText(0, pp.peakList.pid)
                    child.setCheckState(0, QtCore.Qt.Checked if pp.isDisplayed else QtCore.Qt.Unchecked)

                printItems.extend((GLPEAKSYMBOLS,
                                   GLPEAKARROWS,
                                   GLPEAKLABELS))

            if integralLists:
                item = QtWidgets.QTreeWidgetItem(self.treeView)
                item.setText(0, 'Integral Lists')
                item.setFlags(int(item.flags()) | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                for pp in integralLists:
                    child = QtWidgets.QTreeWidgetItem(item)
                    child.setFlags(int(child.flags()) | QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, pp.integralList)
                    child.setText(0, pp.integralList.pid)
                    child.setCheckState(0, QtCore.Qt.Checked if pp.isDisplayed else QtCore.Qt.Unchecked)

                printItems.extend((GLINTEGRALSYMBOLS,
                                   GLINTEGRALLABELS))

            if multipletLists:
                item = QtWidgets.QTreeWidgetItem(self.treeView)
                item.setText(0, 'Multiplet Lists')
                item.setFlags(int(item.flags()) | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                for pp in multipletLists:
                    child = QtWidgets.QTreeWidgetItem(item)
                    child.setFlags(int(child.flags()) | QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, pp.multipletList)
                    child.setText(0, pp.multipletList.pid)
                    child.setCheckState(0, QtCore.Qt.Checked if pp.isDisplayed else QtCore.Qt.Unchecked)

                printItems.extend((GLMULTIPLETSYMBOLS,
                                   GLMULTIPLETLABELS,
                                   GLMULTIPLETARROWS))

            # populate the treeview with the currently selected peak/integral/multiplet lists
            self.treeView._uncheckAll()
            pidList = []
            for specView in strip.spectrumViews:
                validPeakListViews = [pp.peakList.pid for pp in specView.peakListViews
                                      if pp.isDisplayed
                                      and specView.isDisplayed]
                validIntegralListViews = [pp.integralList.pid for pp in specView.integralListViews
                                          if pp.isDisplayed
                                          and specView.isDisplayed]
                validMultipletListViews = [pp.multipletList.pid for pp in specView.multipletListViews
                                           if pp.isDisplayed
                                           and specView.isDisplayed]
                pidList.extend(validPeakListViews)
                pidList.extend(validIntegralListViews)
                pidList.extend(validMultipletListViews)
                if specView.isDisplayed:
                    pidList.append(specView.spectrum.pid)

            self.treeView.selectObjects(pidList)

        printItems.extend(GLEXTENDEDLIST)

        selectList = selectList or []
        self.printList = []

        # add Print Options to the treeView
        item = QtWidgets.QTreeWidgetItem(self.treeView)
        item.setText(0, OPTIONPRINT)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

        for itemName in printItems:
            child = QtWidgets.QTreeWidgetItem(item)
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setText(0, itemName)

        item.setExpanded(True)

        for child in self.treeView.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            _state = None

            itemName = child.text(0)
            if itemName in OPTIONLIST:
                continue
            if itemName in selectList:
                _state = selectList[itemName]
            else:
                _state = self.printSettings.printOptions.get(itemName)
                # _state = _prefState if _prefState is not None else QtCore.Qt.Checked

            if _state is not None:
                child.setCheckState(0, _state)

    def _changePrintType(self):
        selected = self.printType.get()
        lastPath = self.getSaveTextWidget()

        if selected in EXPORTTYPES:
            ext = EXPORTTYPES[selected][EXPORTEXT]
            filt = EXPORTTYPES[selected][EXPORTFILTER]

            lastPath.assureSuffix(ext)
            self._dialogFilter = filt
            self.updateDialog()
            self._updateButtonText()
            self.updateFilename(lastPath)

        else:
            raise TypeError('bad export type')

    def buildParameters(self):
        """build parameters dict from the user widgets, to be passed to the export method.
        :return: dict - user parameters
        """
        if not self.objects:
            return {}

        selected = self.objectPulldown.getText()
        if 'SpectrumDisplay' in selected:
            spectrumDisplay = self.objects[selected][0]
            strip = self._selectedStrip
            stripDirection = self.spectrumDisplay.stripArrangement
        else:
            spectrumDisplay = None
            strip = self.objects[selected][0]
            stripDirection = self.strip.spectrumDisplay.stripArrangement

        # prType = self.printType.get()
        # pageType = self.pageOrientation.get()
        # foregroundColour = hexToRgbRatio(self.foregroundColour)
        # backgroundColour = hexToRgbRatio(self.backgroundColour)
        # baseThickness = self.baseThicknessBox.getValue()
        #
        # # there are now unique per-spectrumDisplay, may differ from preferences
        # symbolThickness = strip.symbolThickness
        # contourThickness = strip.contourThickness
        # aliasEnabled = strip.aliasEnabled
        # aliasShade = strip.aliasShade
        # aliasLabelsEnabled = strip.aliasLabelsEnabled
        # peakLabelsEnabled = strip.peakLabelsEnabled
        # peakArrowsEnabled = strip.peakArrowsEnabled
        # multipletLabelsEnabled = strip.multipletLabelsEnabled
        # stripPadding = self.stripPaddingBox.getValue()
        # exportDpi = self.exportDpiBox.getValue()

        # fcolName = colourNameNoSpace(self.foregroundColourBox.getText())
        # if fcolName in spectrumColours.values():
        #     fcolName = list(spectrumColours.keys())[list(spectrumColours.values()).index(fcolName)]
        # bcolName = colourNameNoSpace(self.backgroundColourBox.getText())
        # if bcolName in spectrumColours.values():
        #     bcolName = list(spectrumColours.keys())[list(spectrumColours.values()).index(bcolName)]

        if strip:
            # return the parameters
            params = {GLFILENAME              : self.exitFilename,
                      GLSPECTRUMDISPLAY       : spectrumDisplay,
                      GLSTRIP                 : strip,
                      GLWIDGET                : strip._CcpnGLWidget,
                      GLPRINTTYPE             : self.printType.get(),
                      GLPAGETYPE              : self.pageOrientation.get(),
                      GLPAGESIZE              : self.pageSize.get(),
                      GLFOREGROUND            : hexToRgbRatio(self.foregroundColour),
                      GLBACKGROUND            : hexToRgbRatio(self.backgroundColour),
                      GLBASETHICKNESS         : self.baseThicknessBox.getValue(),
                      # unique per spectrumDisplay - may differ from preferences
                      GLSYMBOLTHICKNESS       : strip.symbolThickness,
                      GLCONTOURTHICKNESS      : strip.contourThickness,
                      GLALIASENABLED          : strip.aliasEnabled,
                      GLALIASSHADE            : strip.aliasShade,
                      GLALIASLABELSENABLED    : strip.aliasLabelsEnabled,
                      GLPEAKSYMBOLSENABLED    : strip.peakSymbolsEnabled,
                      GLPEAKLABELSENABLED     : strip.peakLabelsEnabled,
                      GLPEAKARROWSENABLED     : strip.peakArrowsEnabled,
                      GLMULTIPLETSYMBOLSENABLED: strip.multipletSymbolsEnabled,
                      GLMULTIPLETLABELSENABLED: strip.multipletLabelsEnabled,
                      GLMULTIPLETARROWSENABLED: strip.multipletArrowsEnabled,
                      GLSTRIPDIRECTION        : stripDirection,
                      GLSTRIPPADDING          : self.stripPaddingBox.getValue(),
                      GLEXPORTDPI             : self.exportDpiBox.getValue(),
                      GLSELECTEDPIDS          : self.treeView.getSelectedObjectsPids(),
                      GLSTRIPREGIONS          : self._stripDict,
                      GLSCALINGMODE           : self.scalingMode.getIndex(),
                      GLSCALINGPERCENT        : self.scalingPercentage.get(),
                      GLSCALINGBYUNITS        : self.scalingUnits.get(),
                      GLSCALINGAXIS           : self.scalingAxis.getIndex(),
                      GLUSEPRINTFONT          : self._useFontCheckbox.isChecked(),
                      GLPRINTFONT             : (self._fontPulldown.get(), self._fontSpinbox.get()),
                      }
            selectedList = self.treeView.getSelectedItems()
            for itemName in self.fullList:
                params[itemName] = itemName in selectedList

            return params

    def exportToFile(self, filename=None, params=None):
        """Export to file
        :param filename: filename to export
        :param params: dict - user defined parameters for export
        """

        if not params:
            return
        filename = params[GLFILENAME]
        glWidget = params[GLWIDGET]
        prType = params[GLPRINTTYPE]

        with catchExceptions(errorStringTemplate='Error writing file; "%s"', printTraceBack=False):
            if prType == EXPORTPDF:
                if pdfExport := glWidget.exportToPDF(filename, params):
                    pdfExport.writePDFFile()
            elif prType == EXPORTSVG:
                if svgExport := glWidget.exportToSVG(filename, params):
                    svgExport.writeSVGFile()
            elif prType == EXPORTPNG:
                if pngExport := glWidget.exportToPNG(filename, params):
                    pngExport.writePNGFile()
            elif prType == EXPORTPS:
                if pngExport := glWidget.exportToPS(filename, params):
                    pngExport.writePSFile()

    def actionButtons(self):
        self.setOkButton(callback=self._saveAndCloseDialog, text='Export and Close',
                         tipText='Export the strip and close the dialog\nAll changes to the print settings are saved')
        self.setCancelButton(callback=self._closeDialog, text='Close', tipText='Close the dialog\nAll changes to the print settings are saved')
        self.setCloseButton(callback=self._saveDialog, text='Export', tipText='Export the strip')
        self.setHelpButton(callback=self._helpClicked, tipText='Help', enabled=False)
        self.setRevertButton(callback=self._revertClicked, tipText='Revert print settings to the state when the dialog was opened', enabled=False)
        self.setUserButton(callback=self._rejectDialog, text='Cancel',
                           tipText='Close the dialog\nAny changes to the print settings are discarded', enabled=True)
        self.setDefaultButton(self.CANCELBUTTON)

    def _postInit(self):
        """post-initialise functions
        CCPN-Internal to be called at the end of __init__
        """
        with self._changes.blockChanges():
            # stop the popup from firing events
            super()._postInit()
        self._revertButton = self.getButton(self.RESETBUTTON)

    def _closeDialog(self):
        self._applyChanges()
        self._rejectDialog()

    def _saveDialog(self, exitSaveFileName=None):
        """save button has been clicked
        """
        selected = self.printType.get()
        lastPath = self.getSaveTextWidget()

        if selected in EXPORTTYPES:
            lastPath = lastPath.assureSuffix(EXPORTTYPES[selected][EXPORTEXT])

        self.setSaveTextWidget(lastPath)
        self.exitFilename = lastPath

        # NOTE:DT Change when 'Do not prompt again' is more prevalent to check if exists ever
        if self.pathEdited is False:
            # user has not changed the path so we can accept()
            self._exportToFile()
        else:
            # have edited the path so check the new file
            if self.exitFilename.is_file():
                yes = showYesNoWarning('%s already exists.' % self.exitFilename,
                                       'Do you want to replace it?')
                if yes:
                    self._exportToFile()
            else:
                if self.exitFilename.is_dir():
                    showWarning('Export Error:', 'Filename must be a file.')
                else:
                    self._exportToFile()

    def _applyChanges(self):
        """
        The apply button has been clicked
        Define an undo block for setting the properties of the object
        If there is an error setting any values then generate an error message
          If anything has been added to the undo queue then remove it with application.undo()
          repopulate the popup widgets

        This is controlled by a series of dicts that contain change functions - operations that are scheduled
        by changing items in the popup. These functions are executed when the Apply or OK buttons are clicked

        Return True unless any errors occurred
        """
        allChanges = bool(self._changes)
        if not allChanges:
            return True

        # apply all changes
        self._applyAllChanges(self._changes)

        # remove all changes
        self._changes.clear()
        self._revertButton.setEnabled(True)
        return True

    def _saveAndCloseDialog(self, exitSaveFilename=None):
        """save and Close button has been clicked
        """
        selected = self.printType.get()
        lastPath = self.getSaveTextWidget()

        if selected in EXPORTTYPES:
            lastPath = lastPath.assureSuffix(EXPORTTYPES[selected][EXPORTEXT])

        self.setSaveTextWidget(lastPath)
        self.exitFilename = lastPath

        self._applyChanges()
        self._acceptDialog()

    def _revertClicked(self):
        """Revert button signal comes here
        Revert (roll-back) the state of the project to before the popup was opened
        """
        self.populate(self.mainWidget)
        self._revertButton.setEnabled(False)
        self.update()

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        """Subclass keypress to stop enter/return on default button
        """
        if a0.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            return
        super().keyPressEvent(a0)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # list widget copy/paste callBack

    def _copyRangeCallback(self):
        """Copy the axis range values from the selected strip
        """
        clickedId = self._stripLists._clickedStripId
        if clickedId and clickedId in self._stripDict:
            self._copyRangeValue = self._stripDict[clickedId].toDict()

    def _pasteRangeCallback(self):
        """Paste the axis range values into the selected strip
        """
        if self._copyRangeValue is None:
            getLogger().debug('Nothing to paste')
            return

        clickedId = self._stripLists._clickedStripId
        if clickedId and clickedId in self._stripDict:
            self._stripDict[clickedId].fromDict(self._copyRangeValue)

            # update the queued changes
            self._setRangeState(clickedId)

    def _pasteRangeAllCallback(self):
        """Paste the axis range values into all the selected strips
        """
        if self._copyRangeValue is None:
            getLogger().debug('Nothing to paste')
            return

        clickedId = self._stripLists._clickedStripId
        selectedIds = self._stripLists._selectedStripIds
        if clickedId and selectedIds:
            for stripId in selectedIds:
                if stripId in self._stripDict:
                    self._stripDict[stripId].fromDict(self._copyRangeValue)

            # update the queued changes
            self._setRangeState(clickedId)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # page settings

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        if not self._changes.enabled:
            return None

        applyState = True
        revertState = False
        allChanges = bool(self._changes)

        return changeState(self, allChanges, applyState, revertState, None, None, self._revertButton, self._currentNumApplies)

    @queueStateChange(_verifyPopupApply)
    def _queuePageSizeCallback(self, _value):
        value = self.pageSize.get()
        if value != self.printSettings.pageSize:
            return partial(self._setPageSize, value)

    def _setPageSize(self, value):
        """Set the page size
        One of: A0, A1, A2, A3, A4, A5, A6, letter
        """
        self.printSettings.pageSize = value

    @queueStateChange(_verifyPopupApply)
    def _queuePageOrientationCallback(self):
        value = self.pageOrientation.get()
        if value != self.printSettings.pageOrientation:
            return partial(self._setPageOrientation, value)

    def _setPageOrientation(self, value):
        """Set the page orientation - either portrait or landscape
        """
        self.printSettings.pageOrientation = value

    @queueStateChange(_verifyPopupApply)
    def _queuePrintTypeCallback(self):
        value = self.printType.get()
        self._fileNamePrintType(value)
        if value != self.printSettings.printType:
            return partial(self._setPrintType, value)

    def _setPrintType(self, value):
        """Set the print type: pdf, ps, svg, etc.
        """
        self.printSettings.printType = value

    def _fileNamePrintType(self, value):
        """Change print file extensions
            Intented to be used by radio buttons
        :param value: The new print type.
        """
        if value not in EXPORTTYPES:
            raise TypeError('bad export type')

        # filename changes
        path = self.getSaveTextWidget()
        newPath = path.with_suffix(EXPORTTYPES[value][EXPORTEXT])
        self.updateFilename(newPath)

        # popup changes
        self._dialogFilter = EXPORTTYPES[value][EXPORTFILTER]
        self.updateDialog()
        self._updateButtonText()


    def _changeColourButton(self):
        """Popup a dialog and set the colour in the pulldowns
        """
        dialog = ColourDialog(self)
        if newColour := dialog.getColor():
            addNewColour(newColour)
            fillColourPulldown(self.foregroundColourBox, allowAuto=False, includeGradients=False)
            fillColourPulldown(self.backgroundColourBox, allowAuto=False, includeGradients=False)

            return newColour

    def _queueForegroundButtonCallback(self, _value):
        if (newColour := self._changeColourButton()):
            self.foregroundColourBox.setCurrentText(spectrumColours[newColour.name()])
            self.foregroundColour = newColour.name()

    @queueStateChange(_verifyPopupApply)
    def _queueForegroundPulldownCallback(self, _value):
        if _value >= 0:
            colName = colourNameNoSpace(self.foregroundColourBox.getText())
            if colName in spectrumColours.values():
                colName = list(spectrumColours.keys())[list(spectrumColours.values()).index(colName)]
            self.foregroundColour = colName
            if colName != self.printSettings.foregroundColour:
                return partial(self._setForeGroundColour, colName)

    def _setForeGroundColour(self, value):
        self.printSettings.foregroundColour = value

    def _queueBackgroundButtonCallback(self, _value):
        if (newColour := self._changeColourButton()):
            self.backgroundColourBox.setCurrentText(spectrumColours[newColour.name()])
            self.backgroundColour = newColour.name()

    @queueStateChange(_verifyPopupApply)
    def _queueBackgroundPulldownCallback(self, _value):
        if _value >= 0:
            colName = colourNameNoSpace(self.backgroundColourBox.getText())
            if colName in spectrumColours.values():
                colName = list(spectrumColours.keys())[list(spectrumColours.values()).index(colName)]
            self.backgroundColour = colName
            if colName != self.printSettings.backgroundColour:
                return partial(self._setBackgroundColour, colName)

    def _setBackgroundColour(self, value):
        self.printSettings.backgroundColour = value

    @queueStateChange(_verifyPopupApply)
    def _queueBaseThicknessCallback(self, _value):
        textFromValue = self.baseThicknessBox.textFromValue
        oldValue = textFromValue(self.printSettings.baseThickness or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setBaseThickness, _value)

    def _setBaseThickness(self, value):
        self.printSettings.baseThickness = float(value)

    @queueStateChange(_verifyPopupApply)
    def _queueStripPaddingCallback(self, _value):
        textFromValue = self.stripPaddingBox.textFromValue
        oldValue = textFromValue(self.printSettings.stripPadding or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setStripPadding, _value)

    def _setStripPadding(self, value):
        self.printSettings.stripPadding = float(value)

    @queueStateChange(_verifyPopupApply)
    def _queueDpiCallback(self, _value):
        textFromValue = self.exportDpiBox.textFromValue
        oldValue = textFromValue(self.printSettings.dpi or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setDpi, _value)

    def _setDpi(self, value):
        self.printSettings.dpi = float(value)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # scaling

    def _setScalingVisible(self):
        _ind = self._scalingModeIndex
        self.scalingPercentage.setVisible(not _ind)
        self.scalingUnits.setVisible(bool(_ind))
        self.scalingAxis.setVisible(bool(_ind))

    @queueStateChange(_verifyPopupApply)
    def _queueScalingModeCallback(self, _value):
        value = self.scalingMode.getText()
        self._scalingModeIndex = SCALING_MODES.index(value)
        self._setScalingVisible()
        if value != self.printSettings.scalingMode:
            return partial(self._setScalingMode, value)

    def _setScalingMode(self, value):
        self.printSettings.scalingMode = value

    @queueStateChange(_verifyPopupApply)
    def _queueScalingPercentageCallback(self, _value):
        textFromValue = self.scalingPercentage.textFromValue
        oldValue = textFromValue(self.printSettings.scalingPercentage or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setScalingPercentage, _value)

    def _setScalingPercentage(self, value):
        self.printSettings.scalingPercentage = float(value)

    @queueStateChange(_verifyPopupApply)
    def _queueScalingUnitsCallback(self, _value):
        textFromValue = self.scalingUnits.textFromValue
        oldValue = textFromValue(self.printSettings.scalingUnits or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setScalingUnits, _value)

    def _setScalingUnits(self, value):
        self.printSettings.scalingUnits = float(value)

    @queueStateChange(_verifyPopupApply)
    def _queueScalingAxisCallback(self, _value):
        value = self.scalingAxis.getText()
        if value != self.printSettings.scalingAxis:
            return partial(self._setScalingAxis, value)

    def _setScalingAxis(self, value):
        self.printSettings.scalingAxis = value

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # font selection

    def _setUseFontVisible(self):
        """Handle checking/unchecking font checkbox
        """
        self._fontPulldown.setEnabled(self._useFontSetting)
        self._fontSpinbox.setEnabled(self._useFontSetting)

    @queueStateChange(_verifyPopupApply)
    def _queueUseFontCallback(self, _value):
        value = self._useFontCheckbox.isChecked()
        self._useFontSetting = value
        self._setUseFontVisible()
        if value != self.printSettings.useFont:
            return partial(self._setUseFont, value)

    def _setUseFont(self, value):
        self.printSettings.useFont = value

    @queueStateChange(_verifyPopupApply)
    def _queueFontSizeCallback(self, _value):
        textFromValue = self._fontSpinbox.textFromValue
        oldValue = textFromValue(self.printSettings.fontSize or 0.0)
        if _value >= 0 and textFromValue(_value) != oldValue:
            return partial(self._setFontSize, _value)

    def _setFontSize(self, value):
        self.printSettings.fontSize = value

    @queueStateChange(_verifyPopupApply)
    def _queueFontNameCallback(self, _value):
        value = self._fontPulldown.get()
        self._fontNameSetting = value
        self._setPulldownTextColour(self._fontPulldown)
        if value != self.printSettings.fontName:
            return partial(self._setFontName, value)

    def _setFontName(self, value):
        self.printSettings.fontName = value

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # treeview print options

    def _queueGetPrintOptionCallback(self, _value, _state):
        # get the name of the option from the tree
        option = _value.data(0, 0)
        itemName = _value.text(0)
        if itemName not in OPTIONLIST:
            checked = int(_value.checkState(0))
            self._queuePrintOptionsCallback(option, checked)

    @queueStateChange(_verifyPopupApply)
    def _queuePrintOptionsCallback(self, option, checked):
        """Toggle a general checkbox option in the preferences
        Requires the parameter to be called 'option' so that the decorator gives it a unique name
        in the internal updates dict
        """
        if checked != self.printSettings.printOptions.get(option):
            return partial(self._togglePrintOptions, option, checked)

    def _togglePrintOptions(self, option, checked):
        self.printSettings.printOptions[option] = checked

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # print ranges

    @queueStateChange(_verifyPopupApply)
    def _queuePrintRangesCallback(self, _value):
        """Store the print ranges if they have changed
        """
        # get the first spinBox, assume all are the same
        _value = {}
        _valueLocal = {}
        for strip in self.strips:
            _value[strip.id] = self._stripDict[strip.id].toDict()
            _valueLocal[strip.id] = self._localStripDict[strip.id].toDict()
        # any changes to the ranges dict
        if _value != _valueLocal:
            return partial(self._setPrintRange, _value)

    def _setPrintRange(self, value):
        # NOTE:ED - ranges are currently not saved to preferences correctly
        for k, val in value.items():
            self._localStripDict[k].fromDict(val)


def main():
    # from sandbox.Geerten.Refactored.framework import Framework
    # from sandbox.Geerten.Refactored.programArguments import Arguments
    #
    #
    # _makeMainWindowVisible = False
    #
    #
    # class MyProgramme(Framework):
    #     "My first app"
    #     pass
    #
    #
    # myArgs = Arguments()
    # myArgs.noGui = False
    # myArgs.debug = True
    #
    # application = MyProgramme('MyProgramme', '3.0.0-beta3', args=myArgs)
    # ui = application.ui
    # ui.initialize()
    #
    # if _makeMainWindowVisible:
    #     ui.mainWindow._updateMainWindow(newProject=True)
    #     ui.mainWindow.show()
    #     QtWidgets.QApplication.setActiveWindow(ui.mainWindow)
    #
    # dialog = ExportStripToFilePopup(parent=application.mainWindow,
    #                                 mainWindow=application.mainWindow,
    #                                 strips=[],
    #                                 preferences=application.preferences)
    # result = dialog.exec_()

    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    app = newTestApplication()
    application = getApplication()

    dialog = ExportStripToFilePopup(strips=[])
    result = dialog.exec_()


if __name__ == '__main__':
    main()
