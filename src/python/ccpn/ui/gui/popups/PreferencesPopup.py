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
__dateModified__ = "$dateModified: 2024-10-09 19:49:20 +0100 (Wed, October 09, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import os
from collections import OrderedDict
import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui
from functools import partial
from copy import deepcopy
from ccpn.core.PeakList import GAUSSIANMETHOD, PARABOLICMETHOD, LORENTZIANMETHOD
from ccpn.core.MultipletList import MULTIPLETAVERAGINGTYPES
from ccpn.core.lib.DataStore import DataStore
from ccpn.core.lib.ContextManagers import queueStateChange, undoStackBlocking
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.LineEdit import LineEdit, PasswordEdit
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
# from ccpn.ui.gui.widgets.MessageDialog import showYesNo
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Slider import Slider
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Font import (DEFAULTFONTNAME, DEFAULTFONTSIZE, DEFAULTFONTREGULAR, getFontHeight,
                                      getSystemFonts, getFont, getSystemFont, TABLEFONT, updateSystemFonts)
from ccpn.ui.gui.widgets.CompoundWidgets import ButtonCompoundWidget
from ccpn.ui.gui.widgets.ColourDialog import ColourDialog
from ccpn.ui.gui.widgets.FileDialog import (SpectrumFileDialog, ProjectFileDialog, AuxiliaryFileDialog,
                                            LayoutsFileDialog, MacrosFileDialog, PluginsFileDialog, PipelineFileDialog,
                                            ExecutablesFileDialog, ProjectSaveFileDialog)
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.popups.Dialog import handleDialogApply, _verifyPopupApply
# from ccpn.ui.gui.popups.ValidateSpectraPopup import ValidateSpectraForPreferences
from ccpn.ui.gui.guiSettings import (getColours, DIVIDER, Theme, DEFAULT_HIGHLIGHT,
                                     setColourScheme, FONTLIST, ZPlaneNavigationModes)
from ccpn.ui.gui.lib.GuiPath import PathEdit, VALIDFILE
from ccpn.ui.gui.lib.ChangeStateHandler import changeState
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLGlobal import GLFONT_DEFAULTSIZE, _OLDGLFONT_SIZES
from ccpn.util.Logging import getLogger
from ccpn.util.Colour import (spectrumColours, addNewColour, coloursFromHue, fillPulldownFromNames,
                              fillColourPulldown, colourNameNoSpace, _setColourPulldown)
from ccpn.util.UserPreferences import UserPreferences
# from ccpn.util.Common import camelCaseToString
from ccpn.util.Path import aPath, Path
from ccpn.util.Constants import AXISUNITS
from ccpn.framework.Translation import languages
from ccpn.framework.lib.pipeline.PipesLoader import _fetchUserPipesPath
from ccpn.framework.Preferences import getPreferences


PEAKFITTINGDEFAULTS = [PARABOLICMETHOD, GAUSSIANMETHOD, LORENTZIANMETHOD]

# FIXME separate pure GUI to project/preferences properties
# The code sets Gui Parameters assuming that  Preference is not None and has a bunch of attributes.


PulldownListsMinimumWidth = 200
LineEditsMinimumWidth = 195
NotImplementedTipText = 'This option has not been implemented yet'
DEFAULTSPACING = (3, 3)
TABMARGINS = (1, 10, 10, 1)  # l, t, r, b
ZEROMARGINS = (0, 0, 0, 0)  # l, t, r, b

FONTLABELFORMAT = '_fontLabel{}'
FONTDATAFORMAT = '_fontData{}'
FONTSTRING = '_fontString'
FONTPREFS = 'font{}'

PROFILING_SORTINGS = OrderedDict([  # (arg to go on script, tipText)
    ('time', 'internal time'),
    ('calls', 'call count'),
    ('cumulative', 'cumulative time'),
    ('file', 'file name'),
    ('module', 'file name'),
    ('pcalls', 'primitive call count'),
    ('line', 'line number'),
    ('name', 'function name'),
    ('nfl', 'name/file/line'),
    ('stdname', 'standard name'),
    ])

DefaultProfileLines = .2  # % of tot lines to be printed when profiling
DefaultProfileMaxNoLines = 10  # Max number of lines to be printed when profiling

ShowMaxLines = OrderedDict([
    ('Minimal', DefaultProfileMaxNoLines),
    ('Top', DefaultProfileLines),
    ('Half', 0.5),
    ('All', 1.0)
    ])

# Options dict for userWorkingPath. If changed the respective match cases need to
# be changed to reflect this. (_enableUserWorkingPath _setWorkingPathDataStore)
OPTIONS_DICT = {0: "User-defined", 1: "Alongside", 2: "Inside"}
INV_OPTIONS_DICT = dict(map(reversed, OPTIONS_DICT.items()))


def _updateSettings(self, newPrefs, updateColourScheme, updateSpectrumDisplays, userWorkingPath=None):
    from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

    pref = self.application.preferences

    # remember the previous autoBackup settings
    lastBackup = (pref.general.autoBackupEnabled, pref.general.autoBackupFrequency)

    # update the preferences, but keep in place
    pref.clear()
    pref.update(newPrefs)

    # application preferences updated so re-save
    self.application._savePreferences()

    if (pref.general.autoBackupEnabled, pref.general.autoBackupFrequency) != lastBackup:
        # update the autoBackup with the new settings
        self.application._updateAutoBackup(resetInterval=True)

    # update the current userWorkingPath in the active file dialogs
    if userWorkingPath:
        _dialog = ProjectFileDialog(parent=self.mainWindow)
        _dialog.initialPath = aPath(userWorkingPath).filepath
        _dialog = ProjectSaveFileDialog(parent=self.mainWindow)
        _dialog.initialPath = aPath(userWorkingPath).filepath

    self._updateDisplay(updateColourScheme, updateSpectrumDisplays)

    GLSignals = GLNotifier(parent=self)
    GLSignals.emitPaintEvent()


def _refreshGLItems():
    pass


def _makeLabel(parent, text, grid, **kwds) -> Label:
    """Convenience routine to make a Label with uniform settings
    :return Label instance
    """
    kwds.setdefault('hAlign', 'r')
    kwds.setdefault('margins', (0, 3, 10, 3))
    label = Label(parent, text=text, grid=grid, **kwds)
    return label


def _makeLine(parent, grid, text=None, **kwds):
    """Convenience routine to make a horizontal Line, optionally with text and with uniform settings
    """
    kwds.setdefault('gridSpan', (1, 3))
    kwds.setdefault('colour', getColours()[DIVIDER])
    kwds.setdefault('height', 30)
    if text is None:
        result = HLine(parent=parent, grid=grid, **kwds)
    else:
        result = LabeledHLine(parent=parent, text=text, grid=grid, **kwds)
    return result


def _makeCheckBox(parent, row, text, callback, toolTip=None, visible=True, enabled=True, **kwds):
    """Convenience routine to make a row with a label and a checkbox
    :return CheckBox instance
    """
    _label = _makeLabel(parent, text=text, grid=(row, 0), **kwds)
    _checkBox = CheckBox(parent, grid=(row, 1), hAlign='l', hPolicy='minimal', spacing=(0, 0))
    _checkBox.toggled.connect(callback)
    if toolTip is not None:
        _label.setToolTip(toolTip)
        _checkBox.setToolTip(toolTip)
    if not visible:
        # temporarily hide options
        _label.setVisible(False)
        _checkBox.setVisible(False)
    if not enabled:
        # temporarily disable
        _label.setEnabled(False)
        _checkBox.setEnabled(False)
    return _checkBox


def _makeButton(parent, row, text, callback, toolTip=None, buttonText=None, **kwds):
    """Convenience routine to make a row with a label and a button
    :return Button instance
    """
    _label = _makeLabel(parent, text=text, grid=(row, 0), **kwds)
    _button = Button(parent, text=buttonText, grid=(row, 1), hAlign='l', hPolicy='minimal', spacing=(0, 0))
    _button.pressed.connect(callback)
    if toolTip is not None:
        _label.setToolTip(toolTip)
        _button.setToolTip(toolTip)
    return _button


class PreferencesPopup(CcpnDialogMainWidget):
    FIXEDHEIGHT = False
    FIXEDWIDTH = False

    def __init__(self, parent=None, mainWindow=None, title='Preferences', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, size=None, **kwds)

        self.mainWindow = mainWindow
        if self.mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
        else:
            self.application = None
            self.project = None

        if not self.project:
            MessageDialog.showWarning(title, 'No project loaded')
            self.close()
            return
        # get the current preferences from application
        if not (_preferences := getPreferences()):
            MessageDialog.showWarning(title, 'Preferences cannot be found')
            self.close()
            return

        # copy the current preferences
        self.preferences = deepcopy(_preferences)

        # grab the class with the preferences methods
        self._userPreferences = UserPreferences(readPreferences=False)

        # store the original values - needs to be recursive
        self._lastPrefs = deepcopy(self.preferences)

        self._setTabs()

        # enable the buttons
        self.setOkButton(callback=self._okClicked)
        self.setApplyButton(callback=self._applyClicked)
        self.setCancelButton(callback=self._cancelClicked)
        self.setHelpButton(callback=self._helpClicked, enabled=False)
        self.setRevertButton(callback=self._revertClicked, enabled=False)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

        self._populate()

        tabs = tuple(self.tabWidget.widget(ii) for ii in range(self.tabWidget.count()))
        w = max(tab.sizeHint().width() for tab in tabs) + 150
        h = max(tab.sizeHint().height() for tab in tabs)
        h = max((h, 800))
        self._size = QtCore.QSize(w, h)
        self.setMinimumWidth(w)
        self.setMaximumWidth(int(w * 1.5))

        # keep a backup of the working paths in the dialogs
        self._tempDialog = ProjectFileDialog()
        self._tempDialog._storePaths()

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._okButton = self.getButton(self.OKBUTTON)
        self._applyButton = self.getButton(self.APPLYBUTTON)
        self._revertButton = self.getButton(self.RESETBUTTON)

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        if not self._changes.enabled:
            return None

        applyState = True
        revertState = False
        allChanges = True if self._changes else False

        return changeState(self, allChanges, applyState, revertState, self._okButton, self._applyButton,
                           self._revertButton, self._currentNumApplies)

    def getActiveTabList(self):
        """Return the list of active tabs
        """
        return tuple(self.tabWidget.widget(ii) for ii in range(self.tabWidget.count()))

    def _revertClicked(self):
        """Revert button signal comes here
        Revert (roll-back) the state of the project to before the popup was opened
        """
        # Reset preferences to previous state
        if self._currentNumApplies > 0:

            if self.project and self.project._undo:
                for undos in range(self._currentNumApplies):
                    self.project._undo.undo()

            self.application._savePreferences()

        # retrieve the original preferences
        self.preferences = deepcopy(self._lastPrefs)
        self._populate()
        self._okButton.setEnabled(False)
        self._applyButton.setEnabled(False)
        self._revertButton.setEnabled(False)

    def _updateSpectrumDisplays(self):

        for display in self.project.spectrumDisplays:

            for strip in display.strips:
                with strip.blockWidgetSignals():
                    # NOTE:ED - should only set those values that have changed

                    _prefsGen = self.application.preferences.general
                    strip.symbolLabelling = _prefsGen.annotationType
                    strip.symbolType = _prefsGen.symbolType
                    strip.symbolSize = _prefsGen.symbolSizePixel
                    strip.multipletLabelling = _prefsGen.multipletAnnotationType
                    strip.multipletType = _prefsGen.multipletType

                    strip.symbolThickness = _prefsGen.symbolThickness
                    strip.gridVisible = _prefsGen.showGrid
                    strip.contourThickness = _prefsGen.contourThickness
                    strip.crosshairVisible = _prefsGen.showCrosshair
                    strip.sideBandsVisible = _prefsGen.showSideBands

                    strip.spectrumBordersVisible = _prefsGen.showSpectrumBorder

                    strip.aliasEnabled = _prefsGen.aliasEnabled
                    strip.aliasShade = _prefsGen.aliasShade
                    strip.aliasLabelsEnabled = _prefsGen.aliasLabelsEnabled

                    strip.peakSymbolsEnabled = _prefsGen.peakSymbolsEnabled
                    strip.peakLabelsEnabled = _prefsGen.peakLabelsEnabled
                    strip.peakArrowsEnabled = _prefsGen.peakArrowsEnabled
                    strip.multipletSymbolsEnabled = _prefsGen.multipletSymbolsEnabled
                    strip.multipletLabelsEnabled = _prefsGen.multipletLabelsEnabled
                    strip.multipletArrowsEnabled = _prefsGen.multipletArrowsEnabled

                    strip.arrowType = _prefsGen.arrowType
                    strip.arrowSize = _prefsGen.arrowSize
                    strip.arrowMinimum = _prefsGen.arrowMinimum

                # strip._frameGuide.resetColourTheme()

    def _updateDisplay(self, updateColourScheme, updateSpectrumDisplays):
        if updateColourScheme:
            prefs = self.application.preferences
            # change the colour theme
            if pal := setColourScheme(Theme.getByDataValue(prefs.appearance.themeStyle),
                            prefs.appearance.themeColour,
                            Theme.getByDataValue(prefs.general.colourScheme),
                            force=True):
                self.application.ui.qtApp.setPalette(pal)
                QtCore.QTimer.singleShot(0, partial(self.application.ui.qtApp.sigPaletteChanged.emit, pal,
                                                    prefs.appearance.themeStyle,
                                                    prefs.appearance.themeColour,
                                                    prefs.general.colourScheme)
                                         )
            self.application._correctColours()

        if updateSpectrumDisplays:
            self._updateSpectrumDisplays()

        # colour theme has changed - flag displays to update
        self._updateGui(updateSpectrumDisplays)

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

        # this will apply the immediate guiChanges with an undo block
        # applyToSDs = self.preferences.general.applyToSpectrumDisplays

        # need to get from the checkBox, otherwise out-of-sync
        applyToSDs = self.useApplyToSpectrumDisplaysBox.isChecked()

        allChanges = True if self._changes else False
        if not allChanges:
            return True

        # handle clicking of the Apply/OK button
        with handleDialogApply(self) as error:

            # remember the last state before applying changes
            lastPrefs = deepcopy(self.preferences)

            # apply all changes - only to self.preferences
            self._applyAllChanges(self._changes)

            # check whether the colourScheme needs updating
            _changeColour = (self.preferences.general.colourScheme != lastPrefs.general.colourScheme or
                             self.preferences.appearance.themeStyle != lastPrefs.appearance.themeStyle or
                             self.preferences.appearance.themeColour != lastPrefs.appearance.themeColour)
            _changeUserWorkingPath = self.preferences.general.userWorkingPath != lastPrefs.general.userWorkingPath

            # read the last working path set in the file dialogs
            _dialog = ProjectFileDialog(parent=self.mainWindow)
            _lastUserWorkingPath = _dialog.initialPath.asString()  # an aPath

            _newUserWorkingPath = self.preferences.general.userWorkingPath

            # add an undo item to update settings
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=partial(_updateSettings, self, lastPrefs, _changeColour, applyToSDs,
                                         _lastUserWorkingPath if _changeUserWorkingPath else None))

            # remember the new state - between addUndoItems because it may append to the undo stack
            newPrefs = deepcopy(self.preferences)
            _updateSettings(self, newPrefs, _changeColour, applyToSDs,
                            _newUserWorkingPath if _changeUserWorkingPath else None)

            # add a redo item to update settings
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=partial(_updateSettings, self, newPrefs, _changeColour, applyToSDs,
                                         _newUserWorkingPath if _changeUserWorkingPath else None))

            # everything has happened - disable the apply button
            self._applyButton.setEnabled(False)

        # check for any errors
        if error.errorValue:
            # re-populate popup from self.preferences on error
            self._populate()

            # revert the dialog paths
            self._tempDialog._restorePaths()
            return False

        # remove all changes
        self._changes.clear()

        self._currentNumApplies += 1
        self._revertButton.setEnabled(True)
        return True

    def _cleanupDialog(self):
        super()._cleanupDialog()
        if self._availableFontTable:
            self._availableFontTable.close()

    def reject(self) -> None:
        # revert the dialog paths
        self._tempDialog._restorePaths()

        super().reject()

    def _updateGui(self, updateSpectrumDisplays):

        # prompt the GLwidgets to update
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitEvent(triggers=[GLNotifier.GLALLCONTOURS,
                                      GLNotifier.GLALLPEAKS,
                                      GLNotifier.GLALLMULTIPLETS,
                                      GLNotifier.GLPREFERENCES])

        for specDisplay in self.project.spectrumDisplays:
            # update the fixed/locked state
            if specDisplay.strips and updateSpectrumDisplays:

                if not specDisplay.is1D:
                    specDisplay.zPlaneNavigationMode = ZPlaneNavigationModes(
                            self.application.preferences.general.zPlaneNavigationMode).dataValue
                    specDisplay.attachZPlaneWidgets()
                specDisplay._stripDirectionChangedInSettings(self.application.preferences.general.stripArrangement)
                # specDisplay.setVisibleAxes()

                # update the ratios from preferences
                specDisplay.strips[0].updateAxisRatios()

    def _setTabs(self):
        """Creates the tabs as Frame Widget. All the children widgets will go in the Frame.
        Each frame will be the widgets parent.
        Tabs are displayed by the order how appear here.
        """
        self.tabWidget = Tabs(self.mainWidget, grid=(0, 0), gridSpan=(1, 3))
        self.tabWidget.setContentsMargins(*ZEROMARGINS)
        # self.tabWidget.getLayout().setSpacing(0)

        for (tabFunc, tabName) in ((self._setGeneralTabWidgets, 'General'),
                                   (self._setSpectrumTabWidgets, 'Spectrum'),
                                   (self._setPeaksTabWidgets, 'Peaks'),
                                   (self._setExternalProgramsTabWidgets, 'External Programs'),
                                   (self._setAppearanceTabWidgets, 'Appearance'),
                                   (self._setMacroEditorTabWidgets, 'Macro Editor')
                                   ):
            fr = ScrollableFrame(self.mainWidget, setLayout=True, spacing=DEFAULTSPACING,
                                 scrollBarPolicies=('never', 'asNeeded'), margins=TABMARGINS)

            self.tabWidget.addTab(fr.scrollArea, tabName)
            tabFunc(parent=fr)

    def _setGeneralTabWidgets(self, parent):
        """Insert a widget in here to appear in the General Tab
        """
        row = -1

        row += 1
        self.languageLabel = _makeLabel(parent, text="Language", grid=(row, 0), enabled=False)
        self.languageBox = PulldownList(parent, grid=(row, 1), hAlign='l', enabled=False)
        self.languageBox.addItems(languages)
        self.languageBox.setMinimumWidth(PulldownListsMinimumWidth)
        self.languageBox.currentIndexChanged.connect(self._queueChangeLanguage)

        #====== Layouts ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Layouts")

        row += 1
        self.autoSaveLayoutOnQuitBox = _makeCheckBox(parent, row=row, text="Auto-save on 'Quit'",
                                                     callback=partial(self._queueToggleGeneralOptions,
                                                                      'autoSaveLayoutOnQuit'))

        row += 1
        self.restoreLayoutOnOpeningBox = _makeCheckBox(parent, row=row, text="Restore on 'Open'",
                                                       callback=partial(self._queueToggleGeneralOptions,
                                                                        'restoreLayoutOnOpening'))

        #====== Auto Backups ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Auto Backups")

        row += 1
        tTip = 'Automatically make backups at regular intervals.'
        self.autoBackupEnabledBox = _makeCheckBox(parent, row=row, text="Auto backup",
                                                  callback=partial(self._queueToggleGeneralOptions,
                                                                   'autoBackupEnabled'),
                                                  toolTip=tTip)

        row += 1
        tTip = 'The time interval, in minutes, for making backups.'
        self.autoBackupFrequencyLabel = _makeLabel(parent, text="Backup frequency (mins)", grid=(row, 0))
        self.autoBackupFrequencyData = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', min=1, decimals=0, step=10)
        self.autoBackupFrequencyLabel.setToolTip(tTip)
        self.autoBackupFrequencyData.setToolTip(tTip)
        self.autoBackupFrequencyData.setMinimumWidth(LineEditsMinimumWidth)
        self.autoBackupFrequencyData.valueChanged.connect(self._queueSetAutoBackupFrequency)

        row += 1
        tTip = 'The number of auto-backups to keep. If the number of backups exceeds this value the oldest backup is removed.\n' \
               'If this value is changed, older backups may need to be manually deleted.'
        self.autoBackupCountLabel = _makeLabel(parent, text="Number of auto-backups", grid=(row, 0))
        self.autoBackupCountData = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', min=1, decimals=0, step=1)
        self.autoBackupCountLabel.setToolTip(tTip)
        self.autoBackupCountData.setToolTip(tTip)
        self.autoBackupCountData.setMinimumWidth(LineEditsMinimumWidth)
        self.autoBackupCountData.valueChanged.connect(self._queueSetAutoBackupCount)

        row += 1
        tTip = 'Make a backup every time a project is saved by the user.'
        self.backupSaveEnabledBox = _makeCheckBox(parent, row=row, text="Backup on 'Save'",
                                                  callback=partial(self._queueToggleGeneralOptions,
                                                                   'backupSaveEnabled'),
                                                  toolTip=tTip,
                                                  visible=True, enabled=False)
        row += 1
        tTip = 'The number of user-backups to keep.\n' \
               'A backup is written to the backup folder every time a project is saved by the user.\n' \
               'If the number of backups exceeds this value, the oldest backup is removed.\n' \
               'If this value is changed, older backups may need to be manually deleted.'
        self.backupSaveCountLabel = _makeLabel(parent, text="Number of backups on user-save", grid=(row, 0))
        self.backupSaveCountData = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', min=1, decimals=0, step=1)
        self.backupSaveCountLabel.setToolTip(tTip)
        self.backupSaveCountData.setToolTip(tTip)
        self.backupSaveCountData.setMinimumWidth(LineEditsMinimumWidth)
        self.backupSaveCountData.valueChanged.connect(self._queueSetBackupSaveCount)

        row += 1
        self._backupButton = _makeButton(parent, text='', row=row,
                                         buttonText='View backups',
                                         toolTip='Manually clean up auto- and user-backups in this project',
                                         callback=self._queueShowBackupsDialog)

        #====== Paths ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Paths")
        self.workingPathDataStore = None

        row += 1
        # self.useProjectPathBox = _makeCheckBox(parent, row=row, text="Application uses project path",
        #                                        callback=partial(self._queueToggleGeneralOptions, 'useProjectPath'),
        #                                        toolTip='Set the application working path to the project folder on loading')

        self.userWorkingPathRadioLabel = _makeLabel(parent, "Application working path rule", grid=(row, 0), )

        self.userWorkingPathRadio = RadioButtons(parent,
                                                 texts=OPTIONS_DICT.values(),
                                                 direction='h',
                                                 grid=(row, 1),
                                                 callback=self._queueRadioWorkingPath)
        row += 1

        self.userWorkingPathLabel = _makeLabel(parent, "Application working path ", grid=(row, 0), )
        self.userWorkingPathData = PathEdit(parent, grid=(row, 1), vAlign='t')
        self.userWorkingPathData.setMinimumWidth(LineEditsMinimumWidth)
        self.userWorkingPathButton = Button(parent, grid=(row, 2), callback=self._getUserWorkingPath,
                                            icon='icons/directory', hPolicy='fixed')
        self.userWorkingPathData.textChanged.connect(self._queueSetUserWorkingPath)

        row += 1
        userLayouts = _makeLabel(parent, text="Layouts ", grid=(row, 0))
        self.userLayoutsPathData = PathEdit(parent, grid=(row, 1), vAlign='t')
        self.userLayoutsPathData.setMinimumWidth(LineEditsMinimumWidth)
        self.userLayoutsLeButton = Button(parent, grid=(row, 2), callback=self._getUserLayoutsPath,
                                          icon='icons/directory', hPolicy='fixed')
        self.userLayoutsPathData.textChanged.connect(self._queueSetuserLayoutsPath)

        row += 1
        self.auxiliaryFilesLabel = _makeLabel(parent, text="Auxiliary files", grid=(row, 0))
        self.auxiliaryFilesData = PathEdit(parent, grid=(row, 1), vAlign='t')
        self.auxiliaryFilesData.setMinimumWidth(LineEditsMinimumWidth)
        self.auxiliaryFilesDataButton = Button(parent, grid=(row, 2), callback=self._getAuxiliaryFilesPath,
                                               icon='icons/directory', hPolicy='fixed')
        self.auxiliaryFilesData.textChanged.connect(self._queueSetAuxiliaryFilesPath)

        row += 1
        self.macroPathLabel = _makeLabel(parent, text="Macro's", grid=(row, 0))
        self.macroPathData = PathEdit(parent, grid=(row, 1), vAlign='t')
        self.macroPathData.setMinimumWidth(LineEditsMinimumWidth)
        self.macroPathDataButton = Button(parent, grid=(row, 2), callback=self._getMacroFilesPath,
                                          icon='icons/directory', hPolicy='fixed')
        self.macroPathData.textChanged.connect(self._queueSetMacroFilesPath)

        row += 1
        self.pluginPathLabel = _makeLabel(parent, text="Plugins", grid=(row, 0))
        self.pluginPathData = PathEdit(parent, grid=(row, 1), vAlign='t', tipText=NotImplementedTipText)
        self.pluginPathData.setMinimumWidth(LineEditsMinimumWidth)
        self.pluginPathDataButton = Button(parent, grid=(row, 2), callback=self._getPluginFilesPath,
                                           icon='icons/directory', hPolicy='fixed')
        self.pluginPathData.textChanged.connect(self._queueSetPluginFilesPath)

        row += 1
        self.pipesPathLabel = _makeLabel(parent, text="Pipes", grid=(row, 0), )
        self.userPipesPath = PathEdit(parent, grid=(row, 1), vAlign='t', tipText='')
        self.userPipesPath.setMinimumWidth(LineEditsMinimumWidth)
        self.pipesPathDataButton = Button(parent, grid=(row, 2), callback=self._getUserPipesPath,
                                          icon='icons/directory', hPolicy='fixed')
        self.userPipesPath.textChanged.connect(self._queueSetPipesFilesPath)

        #====== Proxy Settings ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Proxy Settings")

        row += 1
        self.useProxyBox = _makeCheckBox(parent, row=row, text="Use proxy settings",
                                         callback=self._queueSetUseProxy)

        row += 1
        self.verifySSLBox = _makeCheckBox(parent, row=row, text="Verify SSL certificates",
                                          callback=self._queueSetVerifySSL)

        row += 1
        self.proxyAddressLabel = _makeLabel(parent, text="Proxy server", grid=(row, 0))
        self.proxyAddressData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyAddressData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyAddressData.textEdited.connect(self._queueSetProxyAddress)

        row += 1
        self.proxyPortLabel = _makeLabel(parent, text="Port", grid=(row, 0))
        self.proxyPortData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyPortData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyPortData.textEdited.connect(self._queueSetProxyPort)

        row += 1
        self.useProxyPasswordBox = _makeCheckBox(parent, row=row, text="Server requires password",
                                                 callback=self._queueSetUseProxyPassword)

        row += 1
        self.proxyUsernameLabel = _makeLabel(parent, text="Username", grid=(row, 0))
        self.proxyUsernameData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyUsernameData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyUsernameData.textEdited.connect(self._queueSetProxyUsername)

        row += 1
        self.proxyPasswordLabel = _makeLabel(parent, text="Password", grid=(row, 0))
        self.proxyPasswordData = PasswordEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyPasswordData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyPasswordData.textEdited.connect(self._queueSetProxyPassword)

        # Add spacer to prevent rows from spreading into empty space
        row += 1
        parent.addSpacer(15, 2, expandX=True, expandY=True, grid=(row, 1), gridSpan=(1, 1))

    def _setAppearanceTabWidgets(self, parent):
        """Insert a widget in here to appear in the Appearance Tab
        """

        row = -1

        row += 1
        self.themeStyleLabel = _makeLabel(parent, text="Style", grid=(row, 0))
        self.themeStyleBox = PulldownList(parent, grid=(row, 1), hAlign='l')
        # self.themeStyleBox.setToolTip('Set SpectrumDisplay background')
        self.themeStyleBox.setMinimumWidth(PulldownListsMinimumWidth)
        # remove the default option for the minute, only the MacOS follows theme (badly on fusion style)
        self.themeStyleBox.addItems(Theme.dataValues()[:2])
        if (model := self.themeStyleBox.model()) and \
                (indx := self.themeStyleBox.getItemIndex(Theme.DEFAULT.dataValue)) is not None:
            if item := model.item(indx):
                # disable the 'default' option
                item.setEnabled(False)
        self._oldThemeStyle = None
        self.themeStyleBox.currentIndexChanged.connect(self._queueChangeThemeStyle)

        row += 1
        self.themeColourLabel = _makeLabel(parent, text="Highlight colour", grid=(row, 0))
        self.themeColourBox = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.themeColourBox.setToolTip('Highlight colour')
        self.themeColourBox.setMinimumWidth(PulldownListsMinimumWidth)
        colourNames = ['default'] + coloursFromHue()
        fillPulldownFromNames(self.themeColourBox, colourNames, allowAuto=False, default=DEFAULT_HIGHLIGHT)
        self.themeColourBox.insertSeparator(1)
        self._oldThemeColour = None
        self.themeColourBox.currentIndexChanged.connect(self._queueChangeThemeColour)

        #====== OS Behavior ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="OS Behavior")

        row += 1
        self.useNativeFileBox = _makeCheckBox(parent, text="Use native file dialogs", row=row,
                                              callback=partial(self._queueToggleGeneralOptions, 'useNative'))

        row += 1
        self.useNativeWebBox = _makeCheckBox(parent, text="Use native web browser", row=row,
                                             callback=partial(self._queueToggleGeneralOptions, 'useNativeWebbrowser'))
        self.useNativeWebBox.setEnabled(False)

        row += 1
        self.useNativeMenus = _makeCheckBox(parent, text="Use native menus (requires restart)", row=row,
                                            callback=partial(self._queueToggleGeneralOptions, 'useNativeMenus'))

        #====== Module Behavior ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Module Behavior")

        row += 1
        self.rememberLastClosedModule = _makeCheckBox(parent, row=row, text="Remember last settings",
                                                      callback=self._queueSetRememberLastClosedModuleState)

        row += 1
        self.runPyConsoleOnMacroEditor = _makeCheckBox(parent, row=row, text="Auto-open python console",
                                                       callback=self._queueSetAutoOpenPythonConsoleOnMacroEditor,
                                                       toolTip="Open python console when opening a macro editor module")

        row += 1
        self.useOnlineDocumentation = _makeCheckBox(parent, row=row, text="Use online api-documentation",
                                                    callback=self._queueSetUseOnlineDocumentation,
                                                    toolTip="Use the online api-documentation instead of the local folder")
        self.useOnlineDocumentation.setEnabled(False)

        row += 1
        self.closeSpectrumDisplayOnLastSpectrum = _makeCheckBox(parent, row=row,
                                                                text="Close spectrum display on last spectrum",
                                                                callback=self._queueSetCloseSpectrumDisplayOnLastSpectrum,
                                                                toolTip="Close spectrum displays if the last spectrum has been removed or deleted")

        # row += 1
        # # not sure whether this is needed
        # self.closeSpectrumDisplayOnLastStrip = _makeCheckBox(parent, row=row, text="Close spectrumDisplay on last strip",
        #                                                      callback=self._queueSetCloseSpectrumDisplayOnLastStrip,
        #                                                      toolTip="Close spectrumDisplay if the last strip has been removed")

        row += 1
        self.showAllDialogs = _makeButton(parent, text="Re-enable hidden dialogs", row=row, buttonText='Enable',
                                          toolTip="Show all dialogs that have previously been hidden with \"Don't show this again\" checkbox",
                                          callback=self._queueShowAllDialogs)

        #====== Tip of the Day ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Tip of the Day")

        row += 1
        self.showTipsAtStartUp = _makeCheckBox(parent, text="Show at startup", row=row,
                                               callback=self._queueSetShowTipsAtStartUp)

        row += 1
        self.showAllTips = _makeButton(parent, text="Tip history", row=row, buttonText='Clear',
                                       toolTip="Show all tips on next restart",
                                       callback=self._queueShowAllTips)

        # GWV: option removed as test is done after Drop
        # row += 1
        # HLine(parent, grid=(row, 0), gridSpan=(1, 3), colour=_dividerColour, height=20)
        #
        # row += 1
        # self.useImportNefPopupLabel = Label(parent, text="Show Import Popup\n    on dropped Nef Files", grid=(row, 0))
        # self.useImportNefPopupBox = CheckBox(parent, grid=(row, 1))
        # self.useImportNefPopupBox.toggled.connect(partial(self._queueToggleAppearanceOptions, 'openImportPopupOnDroppedNef'))

        #====== Fonts ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Fonts (requires restart)")

        # NOTE:ED - testing new font loader
        for num, fontName in enumerate(FONTLIST):
            row += 1
            _label = _makeLabel(parent, text=f"{fontName}", grid=(row, 0))
            _data = Button(parent, grid=(row, 1), callback=partial(self._getFont, num, fontName), hAlign='l')
            _data.setMinimumWidth(PulldownListsMinimumWidth)

            setattr(self, FONTLABELFORMAT.format(num), _label)
            setattr(self, FONTDATAFORMAT.format(num), _data)

        row += 1
        self.glFontSizeLabel = _makeLabel(parent, text="Spectrum display font-size", grid=(row, 0))
        self.glFontSizeData = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.glFontSizeData.setMinimumWidth(PulldownListsMinimumWidth)
        self.glFontSizeData.currentIndexChanged.connect(self._queueChangeGLFontSize)

        row += 1
        self.glAxisFontSizeLabel = _makeLabel(parent, text="Spectrum display axes font-size", grid=(row, 0))
        self.glAxisFontSizeData = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.glAxisFontSizeData.setMinimumWidth(PulldownListsMinimumWidth)
        self.glAxisFontSizeData.currentIndexChanged.connect(self._queueChangeGLAxisFontSize)

        row += 1
        _label = _makeLabel(parent, text='Available printing-fonts', grid=(row, 0), vAlign='t')
        _label.setToolTip('The list of fonts that are available to the spectrumDisplay print action.\n'
                          'This is not all the installed fonts, only the .ttf fonts that can be\nused when printing spectrumDisplays to file.')
        ft = self._availableFontTable = Table(parent, grid=(row, 1), gridSpan=(1, 2), hAlign='l',
                                              showHorizontalHeader=False, showVerticalHeader=False,
                                              selectionCallbackEnabled=False, actionCallbackEnabled=False,
                                              tableMenuEnabled=False, toolTipsEnabled=False,
                                              )
        ft.setEditable(False)
        ft.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        ft.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        ft.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        parent.getLayout().addWidget(ft, row, 1, 1, 2)  # there is a bug somewhere if not done like this :|
        self._updateFontTable(ft)
        ft.setToolTip('The list of fonts that are available to the spectrumDisplay print action.\n'
                      'This is not all the installed fonts, only the .ttf fonts that can be\nused when printing spectrumDisplays to file.')

        parent.layout().setRowStretch(row, 5)  # let the table expand vertically

        row += 1
        btn = ButtonCompoundWidget(parent, grid=(row, 1), gridSpan=(1, 2),
                                   text=' update printing-fonts ', buttonAlignment='right', icon=Icon('icons/redo'),
                                   enabled=True,
                                   minimumWidths=(25, 25, 25), callback=self._updateAvailableFonts)
        btn.setToolTip('Update the current printing-fonts if there are new fonts available')

        row += 1
        parent.addSpacer(15, 2, expandX=True, expandY=True, grid=(row, 2), gridSpan=(1, 1))

    def _setMacroEditorTabWidgets(self, parent):
        row = 0
        #==== Saving ====#
        row += 1
        _makeLine(parent, grid=(row, 0), text="Macro Saving")
        row += 1
        self.macroAutoSaveBox = _makeCheckBox(parent, text="Autosave Macros", row=row,
                                              callback=partial(self._queueToggleGeneralOptions, 'macroAutosave'))

        #==== Default Profiler Settings ====#
        row += 1
        _makeLine(parent, grid=(row, 0), text="Default Profiler Settings")
        row += 1
        self.safeProfileFileCheckBox = _makeCheckBox(parent, text="Save Profiler to disk", row=row,
                                                     callback=partial(self._queueToggleGeneralOptions,
                                                                      'macroSaveProfile'))
        row += 1
        self.sortProfileFilePulldownLabel = _makeLabel(parent, text="Profiler output sorting", grid=(row, 0))
        self.sortProfileFilePulldown = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.sortProfileFilePulldown.setMinimumWidth(LineEditsMinimumWidth)
        self.sortProfileFilePulldown.currentIndexChanged.connect(self._queueChangeSortProfile)
        row += 1
        self.showLinesPulldownLabel = _makeLabel(parent, text="Profiler output limits", grid=(row, 0))
        self.showLinesPulldown = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.showLinesPulldown.setMinimumWidth(LineEditsMinimumWidth)
        self.showLinesPulldown.currentIndexChanged.connect(self._queueChangeShowLines)

    @queueStateChange(_verifyPopupApply)
    def _queueChangeSortProfile(self, value):
        modes = list(PROFILING_SORTINGS.keys())
        value = modes[value]
        if value != self.preferences.general.macroSortProfile:
            return partial(self._changeSortProfile, value)

    def _changeSortProfile(self, value):
        self.preferences.general.macroSortProfile = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeShowLines(self, value):
        lines = list(ShowMaxLines.keys())
        value = lines[value]
        if value != self.preferences.general.macroShowLines:
            return partial(self._changeShowLines, value)

    def _changeShowLines(self, value):
        self.preferences.general.macroShowLines = value

    def _queueShowBackupsDialog(self):
        self._setShowBackupsDialog()

        # return a 'null' function so that the revert/okay buttons appear correctly
        return lambda: True

    def _setShowBackupsDialog(self):
        from ccpn.ui.gui.popups.CleanupBackups import CleanupBackups

        popup = CleanupBackups(parent=self, mainWindow=self.mainWindow)
        popup.exec_()

    def _queueShowAllDialogs(self):
        self._setShowAllDialogs()

        # return a 'null' function so that the revert/OK buttons appear correctly
        return lambda: True

    def _setShowAllDialogs(self):
        pp = self.preferences.popups
        for dlg, kwds in pp.items():
            kwds['dontShowPopup'] = False
        self.showAllDialogs.setEnabled(False)

    @queueStateChange(_verifyPopupApply)
    def _queueShowAllTips(self):
        self._setShowAllTips()

        # return a 'null' function so that the revert/OK buttons appear correctly
        return lambda: True

    def _setShowAllTips(self):
        self.preferences.general.seenTipsOfTheDay.clear()
        self.showAllTips.setEnabled(False)

    @queueStateChange(_verifyPopupApply)
    def _queueSetShowTipsAtStartUp(self, _value):
        value = self.showTipsAtStartUp.isChecked()
        if value != self.preferences.general.showTipOfTheDay:
            return partial(self._setShowTipsAtStartup, value)

    def _setShowTipsAtStartup(self, state):
        self.preferences.general.showTipOfTheDay = state

    @queueStateChange(_verifyPopupApply)
    def _queueSetRememberLastClosedModuleState(self, _value):
        value = self.rememberLastClosedModule.isChecked()
        if value != self.preferences.appearance.rememberLastClosedModuleState:
            return partial(self._setRememberLastClosedModuleState, value)

    def _setRememberLastClosedModuleState(self, state):
        self.preferences.appearance.rememberLastClosedModuleState = state

    @queueStateChange(_verifyPopupApply)
    def _queueSetAutoOpenPythonConsoleOnMacroEditor(self, _value):
        value = self.rememberLastClosedModule.isChecked()
        if value != self.preferences.appearance.autoOpenPythonConsoleOnMacroEditor:
            return partial(self._setAutoOpenPythonConsoleOnMacroEditor, value)

    def _setAutoOpenPythonConsoleOnMacroEditor(self, state):
        self.preferences.appearance.autoOpenPythonConsoleOnMacroEditor = state

    # def _queueClearSeenTips(self):
    #     #GST in this case the default should be no, but we can't do this yet... as yesNo doesn't support it
    #     #    also yes now should allow custom button names and have default and action button separated...
    #     result = showYesNo(parent=self, title="Reset Seen tips", message="Are you sure you want to clear the seen tips list")
    #     if result:
    #         self.preferences.general.seenTipsOfTheDay.clear()

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseOnlineDocumentation(self, _value):
        value = self.useOnlineDocumentation.isChecked()
        if value != self.preferences.appearance.useOnlineDocumentation:
            return partial(self._setUseOnlineDocumentation, value)

    def _setUseOnlineDocumentation(self, state):
        self.preferences.appearance.useOnlineDocumentation = state

    @queueStateChange(_verifyPopupApply)
    def _queueSetCloseSpectrumDisplayOnLastSpectrum(self, _value):
        value = self.closeSpectrumDisplayOnLastSpectrum.isChecked()
        if value != self.preferences.appearance.closeSpectrumDisplayOnLastSpectrum:
            return partial(self._setCloseSpectrumDisplayOnLastSpectrum, value)

    def _setCloseSpectrumDisplayOnLastSpectrum(self, state):
        self.preferences.appearance.closeSpectrumDisplayOnLastSpectrum = state

    @queueStateChange(_verifyPopupApply)
    def _queueSetCloseSpectrumDisplayOnLastStrip(self, _value):
        value = self.closeSpectrumDisplayOnLastStrip.isChecked()
        if value != self.preferences.appearance.closeSpectrumDisplayOnLastStrip:
            return partial(self._setCloseSpectrumDisplayOnLastStrip, value)

    def _setCloseSpectrumDisplayOnLastStrip(self, state):
        self.preferences.appearance.closeSpectrumDisplayOnLastStrip = state

    def _populateAppearanceTab(self):
        """Populate the widgets in the appearanceTab
        """
        prefGen = self.preferences.general
        prefApp = self.preferences.appearance

        self.useNativeFileBox.setChecked(prefGen.useNative)
        self.useNativeMenus.setChecked(prefGen.useNativeMenus)
        self.useNativeWebBox.setChecked(prefGen.useNativeWebbrowser)
        # self.useImportNefPopupBox.setChecked(prefApp.openImportPopupOnDroppedNef)

        self.themeStyleBox.setCurrentIndex(max(0, self.themeStyleBox.findText(prefApp.themeStyle)))
        self.themeColourBox.setCurrentIndex(max(0, self.themeColourBox.findText(prefApp.themeColour)))

        for fontNum, fontName in enumerate(FONTLIST):
            value = prefApp[FONTPREFS.format(fontNum)]
            _fontAttr = getattr(self, FONTDATAFORMAT.format(fontNum))
            self.setFontText(_fontAttr, value)

        self.glFontSizeData.addItems([str(val) for val in _OLDGLFONT_SIZES])
        self.glFontSizeData.setCurrentIndex(self.glFontSizeData.findText(str(prefApp.spectrumDisplayFontSize)))

        self.glAxisFontSizeData.addItems([str(val) for val in _OLDGLFONT_SIZES])
        self.glAxisFontSizeData.setCurrentIndex(
                self.glAxisFontSizeData.findText(str(prefApp.spectrumDisplayAxisFontSize)))

        self.showAllDialogs.setEnabled(True)
        self.showTipsAtStartUp.setChecked(prefGen.showTipOfTheDay)
        self.showAllTips.setEnabled(len(prefGen.seenTipsOfTheDay) > 0)

        self.rememberLastClosedModule.setChecked(prefApp.rememberLastClosedModuleState)
        self.runPyConsoleOnMacroEditor.setChecked(prefApp.autoOpenPythonConsoleOnMacroEditor)
        self.useOnlineDocumentation.setChecked(prefApp.useOnlineDocumentation)
        self.closeSpectrumDisplayOnLastSpectrum.setChecked(prefApp.closeSpectrumDisplayOnLastSpectrum)
        # self.closeSpectrumDisplayOnLastStrip.setChecked(prefApp.closeSpectrumDisplayOnLastStrip)

    def _populateMacroEditorTab(self):

        prefGen = self.preferences.general
        self.macroAutoSaveBox.setChecked(prefGen.macroAutosave)
        self.safeProfileFileCheckBox.setChecked(prefGen.macroSaveProfile)

        self.sortProfileFilePulldown.addItems(PROFILING_SORTINGS.keys())
        index = self.sortProfileFilePulldown.findText(prefGen.macroSortProfile)
        self.sortProfileFilePulldown.setCurrentIndex(index)

        self.showLinesPulldown.addItems(ShowMaxLines.keys())
        self.showLinesPulldown.setCurrentIndex(self.showLinesPulldown.findText(prefGen.macroShowLines))

    def _populate(self):
        """Populate the widgets in the tabs
        """
        # clear all changes
        self._changes.clear()

        with self._changes.blockChanges():
            self.useApplyToSpectrumDisplaysBox.setChecked(self.preferences.general.applyToSpectrumDisplays)
            self._populateGeneralTab()
            self._populateSpectrumTab()
            self._populatePeaksTab()
            self._populateExternalProgramsTab()
            self._populateAppearanceTab()
            self._populateMacroEditorTab()

    def setFontText(self, widget, fontString):
        """Set the contents of the widget the details of the font
        """
        try:
            fontList = fontString.split(',')
            if len(fontList) == 10:
                name, size, _, _, _, _, _, _, _, _ = fontList
                tp = None
            elif len(fontList) == 11:
                name, size, _, _, _, _, _, _, _, _, tp = fontList
            else:
                name, size, tp = DEFAULTFONTNAME, DEFAULTFONTSIZE, DEFAULTFONTREGULAR
        except Exception:
            name, size, tp = DEFAULTFONTNAME, DEFAULTFONTSIZE, DEFAULTFONTREGULAR

        fontName = f'{name}, {size}pt, {tp}' if tp else f'{name}, {size}pt'
        widget._fontString = fontString
        widget.setText(fontName)

    def _updateAvailableFonts(self, value):
        """Update the loaded system-fonts
        """
        updateSystemFonts()

        self._updateFontTable(self._availableFontTable)

    @staticmethod
    def _updateFontTable(table):
        """Update the fonts in the table
        """
        db = sorted((fnt, '!@£$%&*(),.; The Quick brown fox jumped over the lazy dog, 0123456789') for fnt in
                    getSystemFonts())
        table.updateDf(pd.DataFrame(db, columns=['name', 'font']))

        # set the font-type for the second column to match the font-name
        ps = getFont(TABLEFONT, size='VLARGE').pointSize()
        for rr, (fnt, _) in enumerate(db):
            # set the font for each cell in the table
            rowFnt = getSystemFont(fnt, None, ps)
            table.model().setCellFont(rr, 1, rowFnt)

        # resize the table-items
        table.resizeColumnToContents(0)
        table.resizeRowsToContents()

    def _populateGeneralTab(self):
        """Populate the widgets in the generalTab
        """
        self.languageBox.setCurrentIndex(self.languageBox.findText(self.preferences.general.language))
        self.autoSaveLayoutOnQuitBox.setChecked(self.preferences.general.autoSaveLayoutOnQuit)
        self.restoreLayoutOnOpeningBox.setChecked(self.preferences.general.restoreLayoutOnOpening)

        self.autoBackupEnabledBox.setChecked(self.preferences.general.autoBackupEnabled)
        self.autoBackupFrequencyData.setValue(self.preferences.general.autoBackupFrequency)
        self.autoBackupCountData.setValue(self.preferences.general.autoBackupCount)
        self.backupSaveEnabledBox.setChecked(self.preferences.general.backupSaveEnabled)
        self.backupSaveCountData.setValue(self.preferences.general.backupSaveCount)

        # not needed setting the index sets path.
        # self.userWorkingPathData.setText(self.preferences.general.userWorkingPath)
        self.userWorkingPathRadio.setIndex(INV_OPTIONS_DICT[self.preferences.general.useProjectPath])

        self.userLayoutsPathData.setText(self.preferences.general.userLayoutsPath)
        self.auxiliaryFilesData.setText(self.preferences.general.auxiliaryFilesPath)
        self.macroPathData.setText(self.preferences.general.userMacroPath)
        self.pluginPathData.setText(self.preferences.general.userPluginPath)

        userPipesPath = _fetchUserPipesPath(self.application)  # gets from preferences or creates the default dir
        self.userPipesPath.setText(str(userPipesPath))

        self.verifySSLBox.setChecked(self.preferences.proxySettings.verifySSL)
        self.useProxyBox.setChecked(self.preferences.proxySettings.useProxy)
        self.proxyAddressData.setText(str(self.preferences.proxySettings.proxyAddress))
        self.proxyPortData.setText(str(self.preferences.proxySettings.proxyPort))
        self.useProxyPasswordBox.setChecked(self.preferences.proxySettings.useProxyPassword)
        self.proxyUsernameData.setText(str(self.preferences.proxySettings.proxyUsername))
        self.proxyPasswordData.setText(
                self._userPreferences.decodeValue(str(self.preferences.proxySettings.proxyPassword)))

        # set the enabled state of some settings boxes
        self._enableProxyButtons()
        # self._enableAutoBackupFrequency()
        self._enableUserWorkingPath()

    def _populateSpectrumTab(self):
        """Populate the widgets in the spectrumTab
        """
        self.autoSetDataPathBox.setChecked(self.preferences.general.autoSetDataPath)
        self.userDataPathText.setText(self.preferences.general.dataPath)

        # populate ValidateFrame
        # self._validateFrame._populate()

        self.regionPaddingData.setValue(float('%.1f' % (100 * self.preferences.general.stripRegionPadding)))

        self.showToolbarBox.setChecked(self.preferences.general.showToolbar)
        self.spectrumBorderBox.setChecked(self.preferences.general.showSpectrumBorder)
        self.showGridBox.setChecked(self.preferences.general.showGrid)
        self.showCrosshairBox.setChecked(self.preferences.general.showCrosshair)
        self.showSideBandsBox.setChecked(self.preferences.general.showSideBands)
        self.showLastAxisOnlyBox.setChecked(self.preferences.general.lastAxisOnly)
        self.matchAxisCode.setIndex(self.preferences.general.matchAxisCode)
        self.axisOrderingOptions.setIndex(self.preferences.general.axisOrderingOptions)
        self.spectrumScalingData.setValue(float(self.preferences.general.scalingFactorStep))
        self.zoomCentre.setIndex(self.preferences.general.zoomCentreType)
        self.zoomPercentData.setValue(int(self.preferences.general.zoomPercent))
        self.stripWidthZoomPercentData.setValue(int(self.preferences.general.stripWidthZoomPercent))
        self.aspectRatioModeData.setIndex(self.preferences.general.aspectRatioMode)
        self.stripArrangementButtons.setIndex(self.preferences.general.stripArrangement)
        self.zPlaneNavigationModeData.setIndex(self.preferences.general.zPlaneNavigationMode)

        self.xAxisUnitsData.setIndex(self.preferences.general.xAxisUnits)
        self.yAxisUnitsData.setIndex(self.preferences.general.yAxisUnits)

        self.showZoomXLimitApplyBox.setChecked(self.preferences.general.zoomXLimitApply)
        self.showZoomYLimitApplyBox.setChecked(self.preferences.general.zoomYLimitApply)
        self.showIntensityLimitBox.setValue(self.preferences.general.intensityLimit)
        self.annotationsData.setIndex(self.preferences.general.annotationType)
        self.symbol.setIndex(self.preferences.general.symbolType)
        self.symbolSizePixelData.setValue(int('%i' % self.preferences.general.symbolSizePixel))
        self.symbolThicknessData.setValue(int(self.preferences.general.symbolThickness))

        self.multipletAnnotationData.setIndex(self.preferences.general.multipletAnnotationType)
        self.multipletSymbol.setIndex(self.preferences.general.multipletType)

        self.arrow.setIndex(self.preferences.general.arrowType)
        self.arrowSizeData.setValue(int(self.preferences.general.arrowSize))
        self.arrowMinimumData.setValue(int(self.preferences.general.arrowMinimum))

        # _enabled = self.preferences.general.aliasEnabled
        # self.aliasEnabledData.setChecked(_enabled)
        # self.aliasShadeData.setValue(self.preferences.general.aliasShade)
        # self.aliasLabelsEnabledData.setChecked(self.preferences.general.aliasLabelsEnabled)
        # self.aliasLabelsEnabledData.setEnabled(_enabled)
        # self.aliasShadeData.setEnabled(_enabled)

        self.contourThicknessData.setValue(int(self.preferences.general.contourThickness))
        # change from description to dataValue for pulldown
        desc = Theme.getByDataValue(self.preferences.general.colourScheme).description
        self.colourSchemeBox.setCurrentIndex(self.colourSchemeBox.findText(desc))

        self.autoCorrectBox.setChecked(self.preferences.general.autoCorrectColours)
        _setColourPulldown(self.marksDefaultColourBox, self.preferences.general.defaultMarksColour)
        self.showSideBandsData.setValue(int(self.preferences.general.numSideBands))

        # multipletAveraging = self.preferences.general.multipletAveraging
        # self.multipletAveraging.setIndex(MULTIPLETAVERAGINGTYPES.index(multipletAveraging) if multipletAveraging in MULTIPLETAVERAGINGTYPES else 0)
        self.singleContoursBox.setChecked(self.preferences.general.generateSinglePlaneContours)
        # self.negativeTraceColourBox.setChecked(self.preferences.general.traceIncludeNegative)

        for aspect, aspectValue in self.preferences.general.aspectRatios.items():
            if aspect in self.aspectData:
                self.aspectData[aspect].setValue(aspectValue)

    def _populatePeaksTab(self):
        """Populate the widgets in the PeaksTab
        """

        from ccpn.core.lib.PeakPickers.PeakPickerABC import getPeakPickerTypes
        from ccpn.core.lib.PeakPickers.PeakPicker1D import PeakPicker1D
        from ccpn.core.lib.PeakPickers.PeakPickerNd import PeakPickerNd

        self.dropFactorData.set(self.preferences.general.peakDropFactor * 100.0)
        self.peakFactor1D.set(self.preferences.general.peakFactor1D * 100.0)

        _peakPickers = getPeakPickerTypes()
        self.peakPicker1dData.setData(texts=sorted([name for name, pp in _peakPickers.items()]))
        self.peakPickerNdData.setData(texts=sorted([name for name, pp in _peakPickers.items() if not pp.onlyFor1D]))

        default1DPickerType = self.preferences.general.peakPicker1d
        if not default1DPickerType or default1DPickerType not in _peakPickers:
            # default to the hard-coded peak-picker
            default1DPickerType = PeakPicker1D.peakPickerType

        defaultNDPickerType = self.preferences.general.peakPickerNd
        if not defaultNDPickerType or defaultNDPickerType not in _peakPickers:
            # default to the hard-coded peak-picker
            defaultNDPickerType = PeakPickerNd.peakPickerType

        self.peakPicker1dData.set(default1DPickerType)
        self.peakPickerNdData.set(defaultNDPickerType)

        self.peakFittingMethod.setIndex(PEAKFITTINGDEFAULTS.index(self.preferences.general.peakFittingMethod))

        self.volumeIntegralLimitData.set(self.preferences.general.volumeIntegralLimit)

        multipletAveraging = self.preferences.general.multipletAveraging
        self.multipletAveraging.setIndex(MULTIPLETAVERAGINGTYPES.index(multipletAveraging)
                                         if multipletAveraging in MULTIPLETAVERAGINGTYPES else 0)

        self.useSearchBoxModeBox.setChecked(self.preferences.general.searchBoxMode)
        self.useSearchBoxDoFitBox.setChecked(self.preferences.general.searchBoxDoFit)
        self.doNegPeak1DBox.setChecked(self.preferences.general.negativePeakPick1D)

        for key, value in self.preferences.general.searchBoxWidths1d.items():
            if key in self.searchBox1dData:
                self.searchBox1dData[key].setValue(value)

        for key, value in self.preferences.general.searchBoxWidthsNd.items():
            if key in self.searchBoxNdData:
                self.searchBoxNdData[key].setValue(value)

        _enabled = self.preferences.general.aliasEnabled
        self.aliasEnabledData.setChecked(_enabled)
        self.aliasShadeData.setValue(self.preferences.general.aliasShade)
        self.aliasLabelsEnabledData.setChecked(self.preferences.general.aliasLabelsEnabled)
        self.aliasLabelsEnabledData.setEnabled(_enabled)
        self.aliasShadeData.setEnabled(_enabled)

        self.peakSymbolsEnabledData.setChecked(self.preferences.general.peakSymbolsEnabled)
        self.peakLabelsEnabledData.setChecked(self.preferences.general.peakLabelsEnabled)
        self.peakArrowsEnabledData.setChecked(self.preferences.general.peakArrowsEnabled)
        self.multipletSymbolsEnabledData.setChecked(self.preferences.general.multipletSymbolsEnabled)
        self.multipletLabelsEnabledData.setChecked(self.preferences.general.multipletLabelsEnabled)
        self.multipletArrowsEnabledData.setChecked(self.preferences.general.multipletArrowsEnabled)

    def _populateExternalProgramsTab(self):
        """Populate the widgets in the externalProgramsTab
        """
        with self._changes.blockChanges():
            for external, (extPath, _, _) in self.externalPaths.items():
                value = self.preferences.externalPrograms[external]
                extPath.setText(value)

    def _setSpectrumTabWidgets(self, parent):
        """Insert a widget in here to appear in the Spectrum Tab. Parent = the Frame obj where the widget should live
        """

        row = -1

        #====== Data Path ($DATA) ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Data Path ($DATA)")

        row += 1
        self.autoSetDataPathBox = _makeCheckBox(parent, text="Auto set", row=row,
                                                callback=partial(self._queueToggleGeneralOptions, 'autoSetDataPath'))

        row += 1
        self.userDataPathLabel = _makeLabel(parent, text="Data path", grid=(row, 0))
        self.userDataPathText = PathEdit(parent, grid=(row, 1), vAlign='t')
        self.userDataPathText.setMinimumWidth(LineEditsMinimumWidth)
        self.userDataPathText.textChanged.connect(self._queueSetUserDataPath)
        self.userDataPathButton = Button(parent, grid=(row, 2), callback=self._getUserDataPath, icon='icons/directory',
                                         hPolicy='fixed', hAlign='left')

        #====== Spectrum Display ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Spectrum Display")

        row += 1
        self.matchAxisCodeLabel = _makeLabel(parent, text="Match axis codes by", grid=(row, 0))
        self.matchAxisCode = RadioButtons(parent, texts=['Atom type', 'Full axis code'],
                                          callback=self._queueSetMatchAxisCode,
                                          direction='h',
                                          grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                          tipTexts=None,
                                          )

        row += 1
        self.axisOrderingOptionsLabel = _makeLabel(parent, text="Displayed axes order", grid=(row, 0))
        self.axisOrderingOptions = RadioButtons(parent,
                                                texts=['Use spectrum settings', 'Always ask'],
                                                callback=self._queueSetAxisOrderingOptions,
                                                direction='h',
                                                grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                                tipTexts=None,
                                                )

        row += 1
        _height = getFontHeight(size='VLARGE') or 24
        self.stripArrangementLabel = _makeLabel(parent, text="Strip arrangement", grid=(row, 0))
        self.stripArrangementButtons = RadioButtons(parent, texts=['    ', '    ', '    '],
                                                    # selectedInd=stripArrangement,
                                                    direction='horizontal',
                                                    grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                    tipTexts=None,
                                                    icons=[('icons/strip-row', (_height, _height)),
                                                           ('icons/strip-column', (_height, _height)),
                                                           ('icons/strip-tile', (_height, _height))
                                                           ],
                                                    )
        # NOTE:ED - temporarily disable/hide the Tile button
        self.stripArrangementButtons.radioButtons[2].setEnabled(False)
        self.stripArrangementButtons.radioButtons[2].setVisible(False)
        self.stripArrangementButtons.setCallback(self._queueSetStripArrangement)

        row += 1
        self.showLastAxisOnlyLabel = _makeLabel(parent, text="Strips share X- or Y-axis", grid=(row, 0))
        self.showLastAxisOnlyBox = CheckBox(parent, grid=(row, 1))
        self.showLastAxisOnlyBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'lastAxisOnly'))

        # # add validate frame
        # row += 1
        # self._validateFrame = ValidateSpectraForPreferences(parent, mainWindow=self.mainWindow, spectra=self.project.spectra,
        #                                                     setLayout=True, showBorder=False, grid=(row, 0), gridSpan=(1, 3))
        #
        # self._validateFrame._filePathCallback = self._queueSetValidateFilePath
        # self._validateFrame._dataUrlCallback = self._queueSetValidateDataUrl
        # self._validateFrame._matchDataUrlWidths = parent
        # self._validateFrame._matchFilePathWidths = parent
        #
        # self._validateFrame.setVisible(False)

        row += 1
        self.xAxisUnits = _makeLabel(parent, text="Default X-axis units", grid=(row, 0))
        self.xAxisUnitsData = RadioButtons(parent, texts=AXISUNITS,
                                           # selectedInd=xAxisUnits,
                                           callback=self._queueSetXUnits,
                                           direction='h',
                                           grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                           tipTexts=None,
                                           )

        row += 1
        self.yAxisUnits = _makeLabel(parent, text="Default Y-axis units", grid=(row, 0))
        self.yAxisUnitsData = RadioButtons(parent, texts=AXISUNITS,
                                           # selectedInd=yAxisUnits,
                                           callback=self._queueSetYUnits,
                                           direction='h',
                                           grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                           tipTexts=None)

        row += 1
        self.zPlaneNavigationModeLabel = _makeLabel(parent, text="Plane navigation mode", grid=(row, 0))
        self.zPlaneNavigationModeData = RadioButtons(parent, texts=[val.description for val in ZPlaneNavigationModes],
                                                     callback=self._queueSetZPlaneNavigationMode,
                                                     direction='h',
                                                     grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                                     tipTexts=(
                                                         'Plane navigation tools are located at the bottom of the spectrumDisplay,\nand will operate on the selected strip in that spectrumDisplay',
                                                         'Plane navigation tools are located at the bottom of each strip',
                                                         'Plane navigation tools are displayed in the upper-left corner of each strip'),
                                                     )
        self.zPlaneNavigationModeLabel.setToolTip('Select where the Plane navigation tools are located')

        row += 1
        self.useApplyToSpectrumDisplaysLabel = _makeLabel(parent, text="Apply to open spectrum displays", grid=(row, 0))
        self.useApplyToSpectrumDisplaysBox = CheckBox(parent, grid=(row, 1))
        self.useApplyToSpectrumDisplaysBox.toggled.connect(partial(self._queueApplyToSpectrumDisplays,
                                                                   'applyToSpectrumDisplays'))

        #====== Aspect ratios ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Aspect Ratios")

        row += 1
        self.aspectRatioModeLabel = _makeLabel(parent, text="Mode", grid=(row, 0))
        self.aspectRatioModeData = RadioButtons(parent, texts=['Free', 'Locked', 'Fixed'],
                                                callback=self._queueSetAspectRatioMode,
                                                direction='h',
                                                grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                                tipTexts=None,
                                                )

        row += 1
        _makeLabel(parent, text='Fixed aspect ratios:', grid=(row, 0))

        # row += 1
        self.aspectLabel = {}
        self.aspectData = {}
        for ii, key in enumerate(sorted(self.preferences.general.aspectRatios.keys())):
            row += 1
            self.aspectLabel[key] = Label(parent, text=key, grid=(row, 0), hAlign='r')
            self.aspectData[key] = ScientificDoubleSpinBox(parent, min=0.5, grid=(row, 1), hAlign='l')
            self.aspectData[key].setMinimumWidth(LineEditsMinimumWidth)
            self.aspectData[key].valueChanged.connect(partial(self._queueSetAspect, key, ii))

        # ====== Scaling ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Scaling")
        row += 1
        self.spectrumScalingLabel = _makeLabel(parent, text="Single step scaling factor",
                                               tipText='Set the single step for rescaling a current spectrum using the shortcuts.',
                                               grid=(row, 0))
        self.spectrumScalingData = ScientificDoubleSpinBox(parent, step=0.01, min=None, max=None, grid=(row, 1),
                                                           hAlign='l')
        self.spectrumScalingData.setMinimumWidth(LineEditsMinimumWidth)
        self.spectrumScalingData.valueChanged.connect(self._queueSetSpectrumScaling)

        #====== Zooming ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Zooming")

        row += 1
        self.zoomCentreLabel = _makeLabel(parent, text="Zoom centre", grid=(row, 0))
        self.zoomCentre = RadioButtons(parent, texts=['Mouse', 'Screen'],
                                       callback=self._queueSetZoomCentre,
                                       direction='h',
                                       grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                       tipTexts=None,
                                       )
        row += 1
        self.zoomPercentLabel = _makeLabel(parent, text="Manual zoom (%)", grid=(row, 0))
        self.zoomPercentData = DoubleSpinbox(parent, step=1,
                                             min=1, max=100, grid=(row, 1), hAlign='l')
        self.zoomPercentData.setMinimumWidth(LineEditsMinimumWidth)
        self.zoomPercentData.valueChanged.connect(self._queueSetZoomPercent)

        row += 1
        self.stripWidthZoomPercentLabel = _makeLabel(parent, text="Strip width zoom (%)", grid=(row, 0))
        self.stripWidthZoomPercentData = DoubleSpinbox(parent, step=1,
                                                       min=1, max=100, grid=(row, 1), hAlign='l')
        self.stripWidthZoomPercentData.setMinimumWidth(LineEditsMinimumWidth)
        self.stripWidthZoomPercentData.valueChanged.connect(self._queueSetStripWidthZoomPercent)

        row += 1
        self.showZoomXLimitApplyLabel = _makeLabel(parent, text="X-axis zoom limit", grid=(row, 0))
        self.showZoomXLimitApplyBox = CheckBox(parent, grid=(row, 1))
        self.showZoomXLimitApplyBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'zoomXLimitApply'))

        row += 1
        self.showZoomYLimitApplyLabel = _makeLabel(parent, text="Y-axis zoom limit", grid=(row, 0))
        self.showZoomYLimitApplyBox = CheckBox(parent, grid=(row, 1))
        self.showZoomYLimitApplyBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'zoomYLimitApply'))

        row += 1
        self.showIntensityLimitLabel = _makeLabel(parent, text='Intensity-axis zoom limit', grid=(row, 0))
        self.showIntensityLimitBox = ScientificDoubleSpinBox(parent, min=1e-6, grid=(row, 1), hAlign='l')
        self.showIntensityLimitBox.setMinimumWidth(LineEditsMinimumWidth)
        self.showIntensityLimitBox.valueChanged.connect(self._queueSetIntensityLimit)

        #====== Show ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Show")

        row += 1
        self.regionPaddingLabel = _makeLabel(parent, text="Spectral padding (%)", grid=(row, 0))
        self.regionPaddingData = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', decimals=1, step=0.1, min=0, max=100)
        self.regionPaddingData.setMinimumWidth(LineEditsMinimumWidth)
        self.regionPaddingData.valueChanged.connect(self._queueSetRegionPadding)

        ### Not fully Tested, Had some issues with $Path routines in setting the path of the copied spectra.
        ###  Needs more testing for different spectra formats etc. Disabled until completion.
        # row += 1
        # self.keepSPWithinProjectTipText = 'Keep a copy of spectra inside the project directory. Useful when changing the original spectra location path'
        # self.keepSPWithinProject = Label(parent, text="Keep a Copy Inside Project", grid=(row, 0))
        # self.keepSPWithinProjectBox = CheckBox(parent, grid=(row, 1), checked=self.preferences.general.keepSpectraInsideProject,
        #                                        tipText=self.keepSPWithinProjectTipText)
        # self.keepSPWithinProjectBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'keepSpectraInsideProject'))

        row += 1
        self.showToolbarLabel = _makeLabel(parent, text="ToolBar(s)", grid=(row, 0))
        self.showToolbarBox = CheckBox(parent, grid=(row, 1))
        self.showToolbarBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'showToolbar'))

        row += 1
        self.spectrumBorderLabel = _makeLabel(parent, text="Spectrum borders", grid=(row, 0))
        self.spectrumBorderBox = CheckBox(parent, grid=(row, 1))
        self.spectrumBorderBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'showSpectrumBorder'))

        row += 1
        self.showGridLabel = _makeLabel(parent, text="Grids", grid=(row, 0))
        self.showGridBox = CheckBox(parent, grid=(row, 1))
        self.showGridBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'showGrid'))

        row += 1
        self.showCrosshairLabel = _makeLabel(parent, text="Crosshairs", grid=(row, 0))
        self.showCrosshairBox = CheckBox(parent, grid=(row, 1))
        self.showCrosshairBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'showCrosshair'))

        row += 1
        self.showSideBandsLabel = _makeLabel(parent, text="MAS side-bands", grid=(row, 0))
        self.showSideBandsBox = CheckBox(parent, grid=(row, 1))
        self.showSideBandsBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'showSideBands'))

        row += 1
        self.showSideBands = _makeLabel(parent, text='Number of MAS side-bands', grid=(row, 0))
        self.showSideBandsData = DoubleSpinbox(parent, step=1, min=0, max=25, grid=(row, 1), hAlign='l', decimals=0)
        self.showSideBandsData.setMinimumWidth(LineEditsMinimumWidth)
        self.showSideBandsData.valueChanged.connect(self._queueSetNumSideBands)

        #====== Contours and Colours ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Contour and Colours")

        row += 1
        self.singleContoursLabel = _makeLabel(parent, text="Single contours per plane", grid=(row, 0))
        self.singleContoursBox = CheckBox(parent, grid=(row, 1))
        self.singleContoursBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'generateSinglePlaneContours'))

        row += 1
        self.contourThicknessLabel = _makeLabel(parent, text="Contour thickness (pixel)", grid=(row, 0))
        self.contourThicknessData = Spinbox(parent, step=1,
                                            min=1, max=20, grid=(row, 1), hAlign='l')
        self.contourThicknessData.setMinimumWidth(LineEditsMinimumWidth)
        self.contourThicknessData.valueChanged.connect(self._queueSetContourThickness)

        row += 1
        self.colourSchemeLabel = _makeLabel(parent, text="Spectrum display style", grid=(row, 0))
        self.colourSchemeBox = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.colourSchemeBox.setToolTip('Set SpectrumDisplay style')
        self.colourSchemeBox.setMinimumWidth(PulldownListsMinimumWidth)
        self.colourSchemeBox.addItems(Theme.descriptions())
        self._oldColourScheme = None
        self.colourSchemeBox.currentIndexChanged.connect(self._queueChangeColourScheme)

        row += 1
        self.autoCorrectLabel = _makeLabel(parent, text="Autocorrect colours", grid=(row, 0))
        self.autoCorrectBox = CheckBox(parent, grid=(row, 1))
        self.autoCorrectBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'autoCorrectColours'))

        row += 1
        self.marksDefaultColourLabel = _makeLabel(parent, text="Default marks colour", grid=(row, 0))
        _colourFrame = Frame(parent, setLayout=True, grid=(row, 1), hAlign='l', gridSpan=(1, 2))
        self.marksDefaultColourBox = PulldownList(_colourFrame, grid=(0, 0))
        self.marksDefaultColourBox.setMinimumWidth(LineEditsMinimumWidth)

        # populate colour pulldown and set to the current colour
        fillColourPulldown(self.marksDefaultColourBox, allowAuto=False, includeGradients=True)
        self.marksDefaultColourBox.currentIndexChanged.connect(self._queueChangeMarksColourIndex)

        # add a colour dialog button
        self.marksDefaultColourButton = Button(_colourFrame, grid=(0, 1), hAlign='l',
                                               icon='icons/colours', hPolicy='fixed')
        self.marksDefaultColourButton.clicked.connect(self._queueChangeMarksColourButton)

        row += 1
        self.negativeTraceColourLabel = _makeLabel(parent, text="Negative colour for phasing traces", grid=(row, 0))
        self.negativeTraceColourBox = CheckBox(parent, grid=(row, 1))
        self.negativeTraceColourBox.toggled.connect(partial(self._queueToggleGeneralOptions, 'traceIncludeNegative'))

        #==== add spacer to stop columns changing width
        row += 1
        parent.addSpacer(15, 2, expandX=True, expandY=True, grid=(row, 1), gridSpan=(1, 1))

    def _setPeaksTabWidgets(self, parent):
        """Insert a widget in here to appear in the Peaks and Multiplets Tab. Parent = the Frame obj where the widget should live
        """
        row = -1

        #====== Peak Picking ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Peak Picking")

        row += 1
        self.peakFittingMethodLabel = _makeLabel(parent, text="Peak interpolation method", grid=(row, 0))
        self.peakFittingMethod = RadioButtons(parent, texts=PEAKFITTINGDEFAULTS,
                                              callback=self._queueSetPeakFittingMethod,
                                              direction='h',
                                              grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                              tipTexts=None,
                                              )
        row += 1
        self.peakPicker1dLabel = _makeLabel(parent, text="Default 1D peak picker", grid=(row, 0))
        self.peakPicker1dData = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.peakPicker1dData.setMinimumWidth(LineEditsMinimumWidth)
        self.peakPicker1dData.currentIndexChanged.connect(self._queueChangePeakPicker1dIndex)

        row += 1
        self.dropFactorLabel = _makeLabel(parent, text="1D Peak picking drop (%)",
                                          tipText='Increase to filter out more', grid=(row, 0))
        self.peakFactor1D = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', decimals=1, step=0.1, min=-100, max=100)
        self.peakFactor1D.setMinimumWidth(LineEditsMinimumWidth)
        self.peakFactor1D.valueChanged.connect(self._queueSetDropFactor1D)

        row += 1
        self.peakPickerNdLabel = _makeLabel(parent, text="Default nD peak picker", grid=(row, 0))
        self.peakPickerNdData = PulldownList(parent, grid=(row, 1), hAlign='l')
        self.peakPickerNdData.setMinimumWidth(LineEditsMinimumWidth)
        self.peakPickerNdData.currentIndexChanged.connect(self._queueChangePeakPickerNdIndex)

        row += 1
        self.dropFactorLabel = _makeLabel(parent, text="nD Peak picking drop (%)", grid=(row, 0))
        self.dropFactorData = DoubleSpinbox(parent, grid=(row, 1), hAlign='l', decimals=1, step=0.1, min=0, max=100)
        self.dropFactorData.setMinimumWidth(LineEditsMinimumWidth)
        self.dropFactorData.valueChanged.connect(self._queueSetDropFactor)

        row += 1
        self.volumeIntegralLimitLabel = _makeLabel(parent, text="Volume integral limit", grid=(row, 0))
        self.volumeIntegralLimitData = DoubleSpinbox(parent, step=0.05, decimals=2,
                                                     min=1.0, max=5.0, grid=(row, 1), hAlign='l')
        self.volumeIntegralLimitData.setMinimumWidth(LineEditsMinimumWidth)
        self.volumeIntegralLimitData.valueChanged.connect(self._queueSetVolumeIntegralLimit)

        row += 1
        self.peakSymbolsEnabledLabel = _makeLabel(parent, text="Show peak symbols", grid=(row, 0))
        self.peakSymbolsEnabledData = CheckBox(parent, grid=(row, 1))
        self.peakSymbolsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions, 'peakSymbolsEnabled'))

        row += 1
        self.peakLabelsEnabledLabel = _makeLabel(parent, text="Show peak labels", grid=(row, 0))
        self.peakLabelsEnabledData = CheckBox(parent, grid=(row, 1))
        self.peakLabelsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions, 'peakLabelsEnabled'))

        row += 1
        self.multipletSymbolsEnabledLabel = _makeLabel(parent, text="Show multiplet symbols", grid=(row, 0))
        self.multipletSymbolsEnabledData = CheckBox(parent, grid=(row, 1))
        self.multipletSymbolsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions,
                                                                 'multipletSymbolsEnabled'))

        row += 1
        self.multipletLabelsEnabledLabel = _makeLabel(parent, text="Show multiplet labels", grid=(row, 0))
        self.multipletLabelsEnabledData = CheckBox(parent, grid=(row, 1))
        self.multipletLabelsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions,
                                                                'multipletLabelsEnabled'))

        row += 1
        self.aliasEnabledLabel = _makeLabel(parent, text="Show aliased peaks", grid=(row, 0))
        self.aliasEnabledData = CheckBox(parent, grid=(row, 1))
        self.aliasEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions, 'aliasEnabled'))

        row += 1
        self.aliasLabelsEnabledLabel = _makeLabel(parent, text="Show aliased labels", grid=(row, 0))
        self.aliasLabelsEnabledData = CheckBox(parent, grid=(row, 1))
        self.aliasLabelsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions, 'aliasLabelsEnabled'))

        row += 1
        self.aliasShadeLabel = _makeLabel(parent, text="Label opacity", grid=(row, 0))
        _sliderBox = Frame(parent, setLayout=True, grid=(row, 1), hAlign='l')
        # self.aliasShadeData = Slider(parent, grid=(row, 1), hAlign='l')
        Label(_sliderBox, text="0%", grid=(0, 0), hAlign='l')
        self.aliasShadeData = Slider(_sliderBox, grid=(0, 1), hAlign='l')
        Label(_sliderBox, text="100%", grid=(0, 2), hAlign='l')
        self.aliasShadeData.setMinimumWidth(LineEditsMinimumWidth)
        self.aliasShadeData.valueChanged.connect(self._queueSetAliasShade)

        row += 1
        self.peakArrowsEnabledLabel = _makeLabel(parent, text="Show peak arrows", grid=(row, 0))
        self.peakArrowsEnabledData = CheckBox(parent, grid=(row, 1))
        self.peakArrowsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions,
                                                           'peakArrowsEnabled'))

        row += 1
        self.multipletArrowsEnabledLabel = _makeLabel(parent, text="Show multiplet arrows", grid=(row, 0))
        self.multipletArrowsEnabledData = CheckBox(parent, grid=(row, 1))
        self.multipletArrowsEnabledData.toggled.connect(partial(self._queueToggleGeneralOptions,
                                                                'multipletArrowsEnabled'))

        #====== Peak Fitting ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Peak Fitting")

        row += 1
        self.useSearchBoxDoFitLabel = _makeLabel(parent, text="Fit after snap-to-extrema", grid=(row, 0))
        self.useSearchBoxDoFitBox = CheckBox(parent, grid=(row, 1))
        self.useSearchBoxDoFitBox.toggled.connect(self._queueSetUseSearchBoxDoFit)
        _toolTip = 'Option to apply fitting method after initial snap to extrema'
        self.useSearchBoxDoFitLabel.setToolTip(_toolTip)
        self.useSearchBoxDoFitBox.setToolTip(_toolTip)

        row += 1
        self.doNegPeak1DLabel = _makeLabel(parent, text="Include negative peaks 1D", grid=(row, 0))
        self.doNegPeak1DBox = CheckBox(parent, grid=(row, 1))
        self.doNegPeak1DBox.toggled.connect(self._queueSetdoNegPeak1D)
        _toolTip = 'Pick and snap to negative regions of the spectra'
        self.doNegPeak1DLabel.setToolTip(_toolTip)
        self.doNegPeak1DBox.setToolTip(_toolTip)
        row += 1

        self.useSearchBoxModeLabel = _makeLabel(parent, text="Use search box", grid=(row, 0))
        self.useSearchBoxModeBox = CheckBox(parent, grid=(row, 1))
        self.useSearchBoxModeBox.toggled.connect(self._queueSetUseSearchBoxMode)
        self.useSearchBoxModeLabel.setToolTip(
                'Use defined search box widths (ppm)\nor default to ±4 index points.\nNote, default will depend on resolution of spectrum')
        self.useSearchBoxModeBox.setToolTip(
                'Use defined search box widths (ppm)\nor default to ±4 index points.\nNote, default will depend on resolution of spectrum')

        row += 1
        _makeLabel(parent, text="1D box widths (ppm):", grid=(row, 0))

        self.searchBox1dLabel = {}
        self.searchBox1dData = {}
        for ii, key in enumerate(sorted(self.preferences.general.searchBoxWidths1d.keys())):
            row += 1
            self.searchBox1dLabel[key] = _makeLabel(parent, text=key, grid=(row, 0))
            self.searchBox1dData[key] = ScientificDoubleSpinBox(parent, min=0.0001, grid=(row, 1), hAlign='l')
            self.searchBox1dData[key].setMinimumWidth(LineEditsMinimumWidth)
            self.searchBox1dData[key].valueChanged.connect(partial(self._queueSetSearchBox1d, key, ii))

        row += 1
        _makeLabel(parent, text="nD box widths (ppm):", grid=(row, 0))

        # self.searchBoxNdLabel = {}
        self.searchBoxNdData = {}
        for ii, key in enumerate(sorted(self.preferences.general.searchBoxWidthsNd.keys())):
            row += 1
            _makeLabel(parent, text=key, grid=(row, 0))
            self.searchBoxNdData[key] = ScientificDoubleSpinBox(parent, min=0.0001, grid=(row, 1), hAlign='l')
            self.searchBoxNdData[key].setMinimumWidth(LineEditsMinimumWidth)
            self.searchBoxNdData[key].valueChanged.connect(partial(self._queueSetSearchBoxNd, key, ii))

        #======  Peak Symbols ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Peak Symbols")

        row += 1
        self.annotationsLabel = _makeLabel(parent, text="Label", grid=(row, 0))
        self.annotationsData = RadioButtons(parent,
                                            texts=['Short', 'Full', 'NmrAtom Pid', 'Minimal', 'Peak Pid', 'ClusterId',
                                                   'Annotation'],
                                            callback=self._queueSetAnnotations,
                                            direction='h',
                                            grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                            tipTexts=None,
                                            )
        row += 1
        self.symbolsLabel = _makeLabel(parent, text="Symbol", grid=(row, 0))
        self.symbol = RadioButtons(parent, texts=['Cross', 'lineWidths', 'Filled lineWidths', 'Plus'],
                                   callback=self._queueSetSymbol,
                                   direction='h',
                                   grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                   tipTexts=None,
                                   )

        row += 1
        self.symbolSizePixelLabel = _makeLabel(parent, text="Size (pixel)", grid=(row, 0))
        self.symbolSizePixelData = Spinbox(parent, step=1,
                                           min=2, max=50, grid=(row, 1), hAlign='l')
        self.symbolSizePixelData.setMinimumWidth(LineEditsMinimumWidth)
        self.symbolSizePixelData.valueChanged.connect(self._queueSetSymbolSizePixel)

        row += 1
        self.symbolThicknessLabel = _makeLabel(parent, text="Thickness (pixel)", grid=(row, 0))
        self.symbolThicknessData = Spinbox(parent, step=1,
                                           min=1, max=20, grid=(row, 1), hAlign='l')
        self.symbolThicknessData.setMinimumWidth(LineEditsMinimumWidth)
        self.symbolThicknessData.valueChanged.connect(self._queueSetSymbolThickness)

        #======  Multiplet Symbols ======
        row += 1
        _makeLine(parent, grid=(row, 0), text='Multiplet Symbols')

        row += 1
        _texts = ['Short', 'Full', 'NmrAtom Pid', 'Minimal', 'Multiplet Pid', 'ClusterId', 'Annotation']
        _names = ['annMDS_Short', 'annMDS_Full', 'annMDS_Pid', 'annMDS_Minimal', 'annMDS_Id', 'annMDS_ClusterId',
                  'annMDS_Annotation']

        self.multipletAnnotationLabel = Label(parent, text="Label", hAlign='r', grid=(row, 0))
        self.multipletAnnotationData = RadioButtons(parent, texts=_texts,
                                                    objectNames=_names,
                                                    callback=self._queueSetMultipletAnnotation,
                                                    direction='h',
                                                    grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                    tipTexts=None,
                                                    )
        self.multipletAnnotationData.radioButtons[2].setVisible(False)
        self.multipletAnnotationData.radioButtons[5].setVisible(False)

        row += 1
        _texts = ['Cross']
        _names = ['symMDS_Cross']

        self.multipletLabel = Label(parent, text="Symbol", hAlign='r', grid=(row, 0))
        self.multipletSymbol = RadioButtons(parent, texts=_texts,
                                            objectNames=_names,
                                            callback=self._queueSetMultipletSymbol,
                                            direction='h',
                                            grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                            tipTexts=None,
                                            )

        # only one symbol - will add more later
        self.multipletLabel.setVisible(False)
        self.multipletSymbol.setVisible(False)

        #======  Peak/Multiplet Arrows ======
        row += 1
        _makeLine(parent, grid=(row, 0), text='Arrows')

        row += 1
        self.arrowsLabel = _makeLabel(parent, text="Arrow", grid=(row, 0))
        self.arrow = RadioButtons(parent, texts=['Line', 'Wedge', 'Arrow'],
                                  callback=self._queueSetArrow,
                                  direction='h',
                                  grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                  tipTexts=None,
                                  )

        row += 1
        self.arrowSizeLabel = _makeLabel(parent, text="Size (pixels)", grid=(row, 0))
        self.arrowSizeData = Spinbox(parent, step=1,
                                     min=1, max=20, grid=(row, 1), hAlign='l')
        self.arrowSizeData.setMinimumWidth(LineEditsMinimumWidth)
        self.arrowSizeData.valueChanged.connect(self._queueSetArrowSize)

        row += 1
        self.arrowMinimumLabel = _makeLabel(parent, text="Minimum length (pixels)", grid=(row, 0))
        self.arrowMinimumData = Spinbox(parent, step=1,
                                        min=1, max=100, grid=(row, 1), hAlign='l')
        self.arrowMinimumData.setMinimumWidth(LineEditsMinimumWidth)
        self.arrowMinimumData.valueChanged.connect(self._queueSetArrowMinimum)

        #====== Multiplets other ======
        row += 1
        _makeLine(parent, grid=(row, 0), text="Multiplets")

        row += 1
        self.multipletAveragingLabel = _makeLabel(parent, text="Multiplet averaging", grid=(row, 0))
        self.multipletAveraging = RadioButtons(parent, texts=MULTIPLETAVERAGINGTYPES,
                                               callback=self._queueSetMultipletAveraging,
                                               direction='h',
                                               grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                               tipTexts=None,
                                               )

        #==== add spacer to stop columns changing width
        row += 1
        parent.addSpacer(15, 2, expandX=True, expandY=True, grid=(row, 1), gridSpan=(1, 1))

    @queueStateChange(_verifyPopupApply)
    def _queueChangeMarksColourIndex(self, value):
        if value >= 0:
            colName = colourNameNoSpace(self.marksDefaultColourBox.getText())
            if colName in spectrumColours.values():
                colName = list(spectrumColours.keys())[list(spectrumColours.values()).index(colName)]
            if colName != self.preferences.general.defaultMarksColour:
                # and list(spectrumColours.keys())[value] != self.preferences.general.defaultMarksColour:
                return partial(self._changeMarksColourIndex, value)

    def _changeMarksColourIndex(self, value):
        """Change the default maerks colour in the preferences
        """
        colName = colourNameNoSpace(self.marksDefaultColourBox.currentText())
        if colName in spectrumColours.values():
            newColour = list(spectrumColours.keys())[list(spectrumColours.values()).index(colName)]
        else:
            newColour = colName

        if newColour:
            self.preferences.general.defaultMarksColour = newColour

    def _queueChangeMarksColourButton(self):
        """set the default marks colour from the colour dialog
        """
        dialog = ColourDialog(self)
        newColour = dialog.getColor()
        if newColour is not None:
            addNewColour(newColour)
            fillColourPulldown(self.marksDefaultColourBox, allowAuto=False, includeGradients=True)
            self.marksDefaultColourBox.setCurrentText(spectrumColours[newColour.name()])

    def _setExternalProgramsTabWidgets(self, parent):
        """Insert a widget in here to appear in the externalPrograms Tab
        """
        self.externalPaths = {}

        row = 0
        # self.preferences.externalPrograms is a (programName, programPath) dict
        for idx, programName in enumerate(sorted(self.preferences.externalPrograms.keys())):
            _makeLabel(parent, text=programName, grid=(row, 0))

            externalPath = PathEdit(parent, grid=(row, 1), hAlign='t', fileMode=VALIDFILE)
            externalPath.setMinimumWidth(LineEditsMinimumWidth)
            externalPath.textChanged.connect(partial(self._queueSetExternalPath, programName, idx))

            externalButton = Button(parent, grid=(row, 2), callback=partial(self._getExternalPath, programName),
                                    icon='icons/directory', hPolicy='fixed')

            externalTestButton = Button(parent, grid=(row, 3), callback=partial(self._testExternalPath, programName),
                                        text='test', hPolicy='fixed')

            self.externalPaths[programName] = (externalPath, externalButton, externalTestButton)

            row += 1

        # add spacer to stop columns changing width
        row += 1
        parent.addSpacer(15, 2, expandX=True, expandY=True, grid=(row, 1), gridSpan=(1, 1))

    def _testExternalPath(self, external):
        if external not in self.preferences.externalPrograms:
            raise RuntimeError(f'{external} not defined')
        if external not in self.externalPaths:
            raise RuntimeError(f'{external} not defined in preferences')

        widgetList = self.externalPaths[external]
        try:
            extPath, _, _ = widgetList

            program = extPath.get()
            if not self._testExternalProgram(program):
                self.sender().setText('Failed')
            else:
                self.sender().setText('Success')

        except Exception as es:
            raise RuntimeError(f'{external} does not contain the correct widgets')

    @staticmethod
    def _testExternalProgram(program):
        import subprocess

        try:
            # TODO:ED check whether relative or absolute path and test
            # import ccpn.framework.PathsAndUrls as PAU
            # pathCwd = PAU.ccpnCodePath
            # programPath = os.path.abspath(os.path.join(pathCwd, program))

            p = subprocess.Popen(program,
                                 shell=False,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            return True

        except Exception as e:
            getLogger().warning(f'Testing External program: Failed.{str(e)}')
            return False

    @queueStateChange(_verifyPopupApply)
    def _queueSetUserDataPath(self, _value):
        value = self.userDataPathText.get()
        if value != self.preferences.general.dataPath:
            return partial(self._setUserDataPath, value)

    def _setUserDataPath(self, value):
        self.preferences.general.dataPath = value
        dialog = SpectrumFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getUserDataPath(self):
        currentDataPath = aPath(self.userDataPathText.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = SpectrumFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.userDataPathText.setText(directory[0])

    def _enableUserDataPath(self):
        """callback upon changing autoSetDataPathBox"""
        value = self.autoSetDataPathBox.get()
        self.userDataPathText.enableWidget(not value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetUserWorkingPath(self, _value):
        value = self.userWorkingPathData.get()
        option = OPTIONS_DICT[self.userWorkingPathRadio.getIndex()]
        self._setWorkingPathDataStore(option, _value)

        if value != self.preferences.general.userWorkingPath:
            return self._setUserWorkingPath

    def _setUserWorkingPath(self):
        """ Sets the user working path and sets the dialog initial path
        .. note:: Working path setting is based purely on the current state
        of the radio buttons
        """
        option = OPTIONS_DICT[self.userWorkingPathRadio.getIndex()]
        path = self.workingPathDataStore.path

        if option == "User-defined":  # saves user set result in preferences dict
            self.preferences.general.userSetWorkingPath = path.asString()

        self.preferences.general.userWorkingPath = path.asString()
        dialog = ProjectFileDialog(parent=self)
        dialog.initialPath = path

    def _getUserWorkingPath(self):
        currentDataPath = aPath(self.userWorkingPathData.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = ProjectFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.userWorkingPathData.setText(directory[0])

    def _enableUserWorkingPath(self):
        """Enables/disables the userWorkingPath based on radio button
        .. note:: Calls _setDataStore() to change the userWorkingPath text
        """
        option = OPTIONS_DICT[self.userWorkingPathRadio.getIndex()]
        self._setWorkingPathDataStore(option)
        match option:
            case "User-defined":
                self.userWorkingPathData.enableWidget(True)
                self.userWorkingPathButton.setEnabled(True)
            case "Alongside" | "Inside":
                self.userWorkingPathData.enableWidget(False)
                self.userWorkingPathButton.setEnabled(False)
            case _:
                raise RuntimeError(f'Invalid choice returned; This should not happen')

        self.userWorkingPathData.set(self.workingPathDataStore.path.asString())

    def _setWorkingPathDataStore(self, option: str = None, path: str|Path = None):
        """Set the dataStore to path based on option

        If option is user-defined and path is provided workingPathDataStore
        is always set to Path, else it is set to previously written user-defined
        text.
        """
        if option is None:
            option = OPTIONS_DICT[self.userWorkingPathRadio.getIndex()]

        match option:
            case "User-defined":
                # If path is passed as arg user is writing data
                # else get from prefs as its radio button change.
                if path:
                    self.workingPathDataStore = DataStore.newFromPath(
                            path=aPath(self.userWorkingPathData.text()))
                else:
                    self.workingPathDataStore = DataStore.newFromPath(
                            path=aPath(self.preferences.general.userSetWorkingPath))
            case "Alongside":
                self.workingPathDataStore = DataStore.newFromPath(path=Path(self.project.path).parent)
            case "Inside":
                self.workingPathDataStore = DataStore.newFromPath(path=Path(self.project.path))
            case _:  # All other cases raise error.
                raise RuntimeError(f'Invalid choice returned; This should not happen')

    @queueStateChange(_verifyPopupApply)
    def _queueSetAuxiliaryFilesPath(self, _value):
        value = self.auxiliaryFilesData.get()
        if value != self.preferences.general.auxiliaryFilesPath:
            return partial(self._setAuxiliaryFilesPath, value)

    def _setAuxiliaryFilesPath(self, value):
        self.preferences.general.auxiliaryFilesPath = value
        dialog = AuxiliaryFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getAuxiliaryFilesPath(self):
        currentDataPath = aPath(self.auxiliaryFilesData.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = AuxiliaryFileDialog(parent=self, acceptMode='select', directory=currentDataPath,
                                     _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.auxiliaryFilesData.setText(directory[0])

    # @queueStateChange(_verifyPopupApply)
    # def _queueSetValidateDataUrl(self, dataUrl, newUrl, urlValid, dim):
    #     """Set the new url in the dataUrl
    #     dim is required by the decorator to give a unique id for dataUrl row
    #     """
    #     if newUrl != dataUrl.url.path:
    #         return partial(self._validatePreferencesDataUrl, dataUrl, newUrl, urlValid, dim)
    #
    # def _validatePreferencesDataUrl(self, dataUrl, newUrl, urlValid, dim):
    #     """Put the new dataUrl into the dataUrl and the preferences.general.dataPath
    #     Extra step incase urlValid needs to be checked
    #     """
    #     if dim == 0:
    #         # must be the first dataUrl for the preferences
    #         # self.preferences.general.dataPath = newUrl
    #         pass
    #
    #     # if urlValid:
    #     # self._validateFrame.dataUrlFunc(dataUrl, newUrl)

    # @queueStateChange(_verifyPopupApply)
    # def _queueSetValidateFilePath(self, spectrum, filePath, dim):
    #     """Set the new filePath for the spectrum
    #     dim is required by the decorator to give a unique id for filePath row
    #     """
    #     if filePath != spectrum.filePath:
    #         return partial(self._validateFrame.filePathFunc, spectrum, filePath)

    @queueStateChange(_verifyPopupApply)
    def _queueSetuserLayoutsPath(self, _value):
        value = self.userLayoutsPathData.get()
        if value != self.preferences.general.userLayoutsPath:
            return partial(self._setUserLayoutsPath, value)

    def _setUserLayoutsPath(self, value):
        self.preferences.general.userLayoutsPath = value
        dialog = LayoutsFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getUserLayoutsPath(self):
        currentDataPath = aPath(self.userLayoutsPathData.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = LayoutsFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.userLayoutsPathData.setText(directory[0])

    @queueStateChange(_verifyPopupApply)
    def _queueSetMacroFilesPath(self, _value):
        value = self.macroPathData.get()
        if value != self.preferences.general.userMacroPath:
            return partial(self._setMacroFilesPath, value)

    def _setMacroFilesPath(self, value):
        self.preferences.general.userMacroPath = value
        dialog = MacrosFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getMacroFilesPath(self):
        currentDataPath = aPath(self.macroPathData.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = MacrosFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.macroPathData.setText(directory[0])

    @queueStateChange(_verifyPopupApply)
    def _queueSetPluginFilesPath(self, _value):
        value = self.pluginPathData.get()
        if value != self.preferences.general.userPluginPath:
            return partial(self._setPluginFilesPath, value)

    def _setPluginFilesPath(self, value):
        self.preferences.general.userPluginPath = value
        dialog = PluginsFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getPluginFilesPath(self):
        currentDataPath = aPath(self.pluginPathData.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = PluginsFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.pluginPathData.setText(directory[0])

    @queueStateChange(_verifyPopupApply)
    def _queueSetPipesFilesPath(self, _value):
        value = self.userPipesPath.get()
        if value != self.preferences.general.userPipesPath:
            return partial(self._setPipesFilesPath, value)

    def _setPipesFilesPath(self, value):
        self.preferences.general.userPipesPath = value
        dialog = PipelineFileDialog(parent=self)
        dialog.initialPath = aPath(value).filepath

    def _getUserPipesPath(self):
        currentDataPath = aPath(self.userPipesPath.text() or '~')
        currentDataPath = currentDataPath if currentDataPath.exists() else aPath('~')
        dialog = PipelineFileDialog(parent=self, acceptMode='select', directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self.userPipesPath.setText(directory[0])
            self._setPipesFilesPath(directory[0])

    @queueStateChange(_verifyPopupApply)
    def _queueChangeLanguage(self, value):
        value = languages[value]
        if value != self.preferences.general.language:
            return partial(self._changeLanguage, value)

    def _changeLanguage(self, value):
        self.preferences.general.language = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeColourScheme(self, value):
        value = self.colourSchemeBox.getText()
        # pulldown list is descriptions, need to change to dataValue in preferences
        value = Theme.getByDescription(value).dataValue
        if value != self.preferences.general.colourScheme:
            return partial(self._changeColourScheme, value)

    def _changeColourScheme(self, value):
        self.preferences.general.colourScheme = value

    @queueStateChange(_verifyPopupApply)
    def _queueRadioWorkingPath(self):
        option = OPTIONS_DICT[self.userWorkingPathRadio.getIndex()]
        self._enableUserWorkingPath()
        if option != self.preferences.general.useProjectPath:
            self._changeRadioWorkingPath(option)

    def _changeRadioWorkingPath(self, option):
        self.preferences.general.useProjectPath = option

    @queueStateChange(_verifyPopupApply)
    def _queueToggleGeneralOptions(self, option, checked):
        """Toggle a general checkbox option in the preferences
        Requires the parameter to be called 'option' so that the decorator gives it a unique name
        in the internal updates dict
        """
        # if option == 'useProjectPath':
        #     self._enableUserWorkingPath()

        if option == 'autoSetDataPath':
            self._enableUserDataPath()

        # elif option == 'autoBackupEnabled':
        #     self._enableAutoBackupFrequency()

        elif option == 'aliasEnabled':
            _enabled = self.aliasEnabledData.get()
            self.aliasLabelsEnabledData.setEnabled(_enabled)
            self.aliasShadeData.setEnabled(_enabled)

        if checked != self.preferences.general[option]:
            # change the enabled state of checkboxes as required
            return partial(self._toggleGeneralOptions, option, checked)

    def _toggleGeneralOptions(self, option, checked):
        self.preferences.general[option] = checked

    @queueStateChange(_verifyPopupApply)
    def _queueToggleAppearanceOptions(self, option, checked):
        """Toggle a general checkbox option in the preferences
        Requires the parameter to be called 'option' so that the decorator gives it a unique name
        in the internal updates dict
        """
        if checked != self.preferences.appearance[option]:
            return partial(self._toggleAppearanceOptions, option, checked)

    def _toggleAppearanceOptions(self, option, checked):
        self.preferences.appearance[option] = checked

    @queueStateChange(_verifyPopupApply)
    def _queueSetExternalPath(self, external, dim, _value):
        """Queue the change to the correct item in preferences
        """
        if external not in self.preferences.externalPrograms:
            raise RuntimeError(f'{external} not defined')
        if external not in self.externalPaths:
            raise RuntimeError(f'{external} not defined in preferences')

        widgetList = self.externalPaths[external]
        try:
            extPath, extButton, extTestButton = widgetList

            value = extPath.get()
            oldValue = self.preferences.externalPrograms[external]
            if value != oldValue:
                extTestButton.setText('test')

                return partial(self._setExternalPath, external, value)

        except Exception as es:
            raise RuntimeError(f'{external} does not contain the correct widgets {es}')

    def _setExternalPath(self, external, value):
        """Set the path in preferences
        """
        if 'externalPrograms' in self.preferences and external in self.preferences.externalPrograms:
            self.preferences.externalPrograms[external] = value

    def _getExternalPath(self, external):
        """Get the correct path from preferences
        """
        # NOTE:ED - native dialog on OSX does not show contents of an .app dir.

        if external not in self.preferences.externalPrograms:
            raise RuntimeError(f'{external} not defined')
        if external not in self.externalPaths:
            raise RuntimeError(f'{external} not defined in preferences')

        widgetList = self.externalPaths[external]
        try:
            extPath, _, _ = widgetList

            value = extPath.get()
            dialog = ExecutablesFileDialog(parent=self, acceptMode='select', directory=str(value))
            dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
            dialog._show()
            if file := dialog.selectedFile():
                extPath.setText(file)

        except Exception:
            raise RuntimeError(f'{external} does not contain the correct widgets')

    @queueStateChange(_verifyPopupApply)
    def _queueSetAutoBackupFrequency(self, _value):
        # raise NotImplementedError('AutoBackup is not available in the current release')
        textFromValue = self.autoBackupFrequencyData.textFromValue
        value = self.autoBackupFrequencyData.get()
        prefValue = textFromValue(self.preferences.general.autoBackupFrequency)
        if textFromValue(value) != prefValue:
            return partial(self._setAutoBackupFrequency, value)

    def _setAutoBackupFrequency(self, value):
        # raise NotImplementedError('AutoBackup is not available in the current release')
        self.preferences.general.autoBackupFrequency = int(value)

    def _enableAutoBackupFrequency(self):
        # raise NotImplementedError('AutoBackup is not available in the current release')
        value = self.autoBackupEnabledBox.get()
        self.autoBackupFrequencyData.enableWidget(value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetAutoBackupCount(self, _value):
        textFromValue = self.autoBackupCountData.textFromValue
        value = self.autoBackupCountData.get()
        prefValue = textFromValue(self.preferences.general.autoBackupCount)
        if textFromValue(value) != prefValue:
            return partial(self._setAutoBackupCount, value)

    def _setAutoBackupCount(self, value):
        self.preferences.general.autoBackupCount = int(value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetBackupSaveCount(self, _value):
        textFromValue = self.backupSaveCountData.textFromValue
        value = self.backupSaveCountData.get()
        prefValue = textFromValue(self.preferences.general.backupSaveCount)
        if textFromValue(value) != prefValue:
            return partial(self._setBackupSaveCount, value)

    def _setBackupSaveCount(self, value):
        self.preferences.general.backupSaveCount = int(value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetRegionPadding(self, _value):
        textFromValue = self.regionPaddingData.textFromValue
        value = self.regionPaddingData.get()
        prefValue = textFromValue(100.0 * self.preferences.general.stripRegionPadding)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setRegionPadding, 0.01 * value)

    def _setRegionPadding(self, value):
        self.preferences.general.stripRegionPadding = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetDropFactor(self, _value):
        textFromValue = self.dropFactorData.textFromValue
        value = self.dropFactorData.get()
        prefValue = textFromValue(100.0 * self.preferences.general.peakDropFactor)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setDropFactor, 0.01 * value)

    def _setDropFactor(self, value):
        self.preferences.general.peakDropFactor = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetDropFactor1D(self, _value):
        textFromValue = self.peakFactor1D.textFromValue
        value = self.peakFactor1D.get()
        prefValue = textFromValue(100.0 * self.preferences.general.peakFactor1D)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._set1DPeakFactor, 0.01 * value)

    def _set1DPeakFactor(self, value):
        self.preferences.general.peakFactor1D = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetSymbolSizePixel(self, _value):
        value = self.symbolSizePixelData.get()
        if value != self.preferences.general.symbolSizePixel:
            return partial(self._setSymbolSizePixel, value)

    def _setSymbolSizePixel(self, value):
        """Set the size of the symbols (pixels)
        """
        self.preferences.general.symbolSizePixel = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetSymbolThickness(self, _value):
        value = self.symbolThicknessData.get()
        if value != self.preferences.general.symbolThickness:
            return partial(self._setSymbolThickness, value)

    def _setSymbolThickness(self, value):
        """Set the Thickness of the peak symbols (pixel)
        """
        self.preferences.general.symbolThickness = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetArrowSize(self, _value):
        value = self.arrowSizeData.get()
        if value != self.preferences.general.arrowSize:
            return partial(self._setArrowSize, value)

    def _setArrowSize(self, value):
        """Set the Thickness of the peak arrows (pixel)
        """
        self.preferences.general.arrowSize = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetArrowMinimum(self, _value):
        value = self.arrowMinimumData.get()
        if value != self.preferences.general.arrowMinimum:
            return partial(self._setArrowMinimum, value)

    def _setArrowMinimum(self, value):
        """Set the visibility threshold of the peak arrows (pixel)
        """
        self.preferences.general.arrowMinimum = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetContourThickness(self, _value):
        value = self.contourThicknessData.get()
        if value != self.preferences.general.contourThickness:
            return partial(self._setContourThickness, value)

    def _setContourThickness(self, value):
        """Set the Thickness of the peak contours (ppm)
        """
        self.preferences.general.contourThickness = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAliasShade(self, _value):
        value = int(self.aliasShadeData.get())
        if value != self.preferences.general.aliasShade:
            return partial(self._setAliasShade, value)

    def _setAliasShade(self, value):
        """Set the aliased peaks Shade 0.0->1.0; 0.0 is invisible
        """
        self.preferences.general.aliasShade = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetXUnits(self):
        value = self.xAxisUnitsData.getIndex()
        if value != self.preferences.general.xAxisUnits:
            return partial(self.setXAxisUnits, value)

    def setXAxisUnits(self, value):
        """Set the xAxisUnits
        """
        self.preferences.general.xAxisUnits = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetYUnits(self):
        value = self.yAxisUnitsData.getIndex()
        if value != self.preferences.general.yAxisUnits:
            return partial(self.setYAxisUnits, value)

    def setYAxisUnits(self, value):
        """Set the yAxisUnits
        """
        self.preferences.general.yAxisUnits = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetZPlaneNavigationMode(self):
        value = self.zPlaneNavigationModeData.getIndex()
        if value != self.preferences.general.zPlaneNavigationMode:
            return partial(self._setZPlaneNavigationMode, value)

    def _setZPlaneNavigationMode(self, value):
        """Set the zPlaneNavigationMode
        """
        self.preferences.general.zPlaneNavigationMode = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAspectRatioMode(self):
        value = self.aspectRatioModeData.getIndex()
        if value != self.preferences.general.aspectRatioMode:
            return partial(self._setAspectRatioMode, value)

    def _setAspectRatioMode(self, value):
        """Set the aspectRatioMode
        """
        self.preferences.general.aspectRatioMode = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAnnotations(self):
        value = self.annotationsData.getIndex()
        if value != self.preferences.general.annotationType:
            return partial(self._setAnnotations, value)

    def _setAnnotations(self, value):
        """Set the annotation type for the pid labels
        """
        self.preferences.general.annotationType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetSymbol(self):
        value = self.symbol.getIndex()
        if value != self.preferences.general.symbolType:
            return partial(self._setSymbol, value)

    def _setSymbol(self, value):
        """Set the peak symbol type - currently a cross or lineWidths
        """
        self.preferences.general.symbolType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMultipletAnnotation(self):
        value = self.multipletAnnotationData.getIndex()
        if value != self.preferences.general.multipletAnnotationType:
            return partial(self._setMultipletAnnotation, value)

    def _setMultipletAnnotation(self, value):
        """Set the multiplet annotation type for the labels
        """
        self.preferences.general.multipletAnnotationType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMultipletSymbol(self):
        value = self.multipletSymbol.getIndex()
        if value != self.preferences.general.multipletType:
            return partial(self._setMultipletSymbol, value)

    def _setMultipletSymbol(self, value):
        """Set the multiplet symbol type
        """
        self.preferences.general.multipletType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetArrow(self):
        value = self.arrow.getIndex()
        if value != self.preferences.general.arrowType:
            return partial(self._setArrow, value)

    def _setArrow(self, value):
        """Set the arrow type.
        """
        self.preferences.general.arrowType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetStripArrangement(self):
        value = self.stripArrangementButtons.getIndex()
        if value != self.preferences.general.stripArrangement:
            return partial(self._setStripArrangement, value)

    def _setStripArrangement(self, value):
        """Set the stripArrangement
        """
        self.preferences.general.stripArrangement = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetZoomCentre(self):
        value = self.zoomCentre.getIndex()
        if value != self.preferences.general.zoomCentreType:
            return partial(self._setZoomCentre, value)

    def _setZoomCentre(self, value):
        """Set the zoom centring method to either mouse position or centre of the screen
        """
        self.preferences.general.zoomCentreType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetZoomPercent(self, _value):
        textFromValue = self.zoomPercentData.textFromValue
        value = self.zoomPercentData.get()
        prefValue = textFromValue(self.preferences.general.zoomPercent)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setZoomPercent, value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetSpectrumScaling(self, _value):
        value = self.spectrumScalingData.get()
        return partial(self._setSpectrumScaling, value)

    def _setSpectrumScaling(self, value):
        """Set the value for manual zoom
        """
        self.preferences.general.scalingFactorStep = value

    def _setZoomPercent(self, value):
        """Set the value for manual zoom
        """
        self.preferences.general.zoomPercent = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetStripWidthZoomPercent(self, _value):
        textFromValue = self.stripWidthZoomPercentData.textFromValue
        value = self.stripWidthZoomPercentData.get()
        prefValue = textFromValue(self.preferences.general.stripWidthZoomPercent)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setStripWidthZoomPercent, value)

    def _setStripWidthZoomPercent(self, value):
        """Set the value for increasing/decreasing width of strips
        """
        self.preferences.general.stripWidthZoomPercent = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetNumSideBands(self, _value):
        textFromValue = self.showSideBandsData.textFromValue
        value = self.showSideBandsData.get()
        prefValue = textFromValue(self.preferences.general.numSideBands)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setNumSideBands, value)

    def _setNumSideBands(self, value):
        """Set the value for number of sideband gridlines to display
        """
        self.preferences.general.numSideBands = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMatchAxisCode(self):
        value = self.matchAxisCode.getIndex()
        if value != self.preferences.general.matchAxisCode:
            return partial(self._setMatchAxisCode, value)

    def _setMatchAxisCode(self, value):
        """Set the matching of the axis codes across different strips
        """
        self.preferences.general.matchAxisCode = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAxisOrderingOptions(self):
        value = self.axisOrderingOptions.getIndex()
        if value != self.preferences.general.axisOrderingOptions:
            return partial(self._setAxisOrderingOptions, value)

    def _setAxisOrderingOptions(self, value):
        """Set the option for the axis ordering of strips when opening a new display
        """
        self.preferences.general.axisOrderingOptions = value

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @queueStateChange(_verifyPopupApply)
    def _queueChangePeakPicker1dIndex(self, _value):
        value = self.peakPicker1dData.get() or None
        if value != self.preferences.general.peakPicker1d:
            return partial(self._setPeakPicker1d, value)

    def _setPeakPicker1d(self, value):
        """Set the default peak picker for 1d spectra
        """
        self.preferences.general.peakPicker1d = value
        spectra = [sp for sp in self.project.spectra if sp.dimensionCount == 1]
        self._updatePeakPickerOnSpectra(spectra, value)

    @queueStateChange(_verifyPopupApply)
    def _queueChangePeakPickerNdIndex(self, _value):
        value = self.peakPickerNdData.get() or None
        if value != self.preferences.general.peakPickerNd:
            return partial(self._setPeakPickerNd, value)

    def _setPeakPickerNd(self, value):
        """Set the default peak picker for Nd spectra
        """
        self.preferences.general.peakPickerNd = value
        spectra = [sp for sp in self.project.spectra if sp.dimensionCount > 1]
        self._updatePeakPickerOnSpectra(spectra, value)

    @staticmethod
    def _updatePeakPickerOnSpectra(spectra, value):
        from ccpn.core.lib.ContextManagers import undoBlock
        from ccpn.core.lib.PeakPickers.PeakPickerABC import getPeakPickerTypes

        PeakPicker = getPeakPickerTypes().get(value)
        if PeakPicker is None:  # Don't use a fetch or fallback to default. User should select one.
            raise RuntimeError(f'Cannot find a PeakPicker called {value}.')
        getLogger().info(f'Setting the {value} PeakPicker to Spectra')
        with undoBlock():
            for sp in spectra:
                if sp.peakPicker and sp.peakPicker.peakPickerType == value:
                    continue  # is the same. no need to reset.
                sp.peakPicker = None
                thePeakPicker = PeakPicker(spectrum=sp)
                sp.peakPicker = thePeakPicker

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @queueStateChange(_verifyPopupApply)
    def _queueSetPeakFittingMethod(self):
        value = PEAKFITTINGDEFAULTS[self.peakFittingMethod.getIndex()]
        if value != self.preferences.general.peakFittingMethod:
            return partial(self._setPeakFittingMethod, value)

    def _setPeakFittingMethod(self, value):
        """Set the matching of the axis codes across different strips
        """
        self.preferences.general.peakFittingMethod = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAspect(self, aspect, dim, _value):
        """dim is required by the decorator to give a unique id for aspect dim
        """
        textFromValue = self.aspectData[aspect].textFromValue
        value = self.aspectData[aspect].get()
        prefValue = textFromValue(self.preferences.general.aspectRatios[aspect])
        if textFromValue(value) != prefValue:
            return partial(self._setAspect, aspect, value)

    def _setAspect(self, aspect, value):
        """Set the aspect ratio for the axes
        """
        self.preferences.general.aspectRatios[aspect] = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseSearchBoxMode(self, _value):
        value = self.useSearchBoxModeBox.get()
        if value != self.preferences.general.searchBoxMode:
            return partial(self._setUseSearchBoxMode, value)

    def _setUseSearchBoxMode(self, value):
        self.preferences.general.searchBoxMode = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseSearchBoxDoFit(self, _value):
        value = self.useSearchBoxDoFitBox.get()
        if value != self.preferences.general.searchBoxDoFit:
            return partial(self._setUseSearchBoxDoFit, value)

    def _setUseSearchBoxDoFit(self, value):
        self.preferences.general.searchBoxDoFit = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetdoNegPeak1D(self, _value):
        value = self.doNegPeak1DBox.get()
        if value != self.preferences.general.negativePeakPick1D:
            return partial(self._setUseSearchBoxDoFit, value)

    def _setdoNegPeak1D(self, value):
        self.preferences.general.negativePeakPick1D = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetSearchBox1d(self, searchBox1d, dim, _value):
        """dim is required by the decorator to give a unique id for searchBox dim
        """
        textFromValue = self.searchBox1dData[searchBox1d].textFromValue
        value = self.searchBox1dData[searchBox1d].get()
        prefValue = textFromValue(self.preferences.general.searchBoxWidths1d[searchBox1d])
        if textFromValue(value) != prefValue:
            return partial(self._setSearchBox1d, searchBox1d, value)

    def _setSearchBox1d(self, searchBox1d, value):
        """Set the searchBox1d width for the axes
        """
        self.preferences.general.searchBoxWidths1d[searchBox1d] = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetSearchBoxNd(self, searchBoxNd, dim, _value):
        """dim is required by the decorator to give a unique id for searchBox dim
        """
        textFromValue = self.searchBoxNdData[searchBoxNd].textFromValue
        value = self.searchBoxNdData[searchBoxNd].get()
        prefValue = textFromValue(self.preferences.general.searchBoxWidthsNd[searchBoxNd])
        if textFromValue(value) != prefValue:
            return partial(self._setSearchBoxNd, searchBoxNd, value)

    def _setSearchBoxNd(self, searchBoxNd, value):
        """Set the searchBoxNd width for the axes
        """
        self.preferences.general.searchBoxWidthsNd[searchBoxNd] = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetIntensityLimit(self, _value):
        textFromValue = self.showIntensityLimitBox.textFromValue
        value = self.showIntensityLimitBox.get()
        prefValue = textFromValue(self.preferences.general.intensityLimit)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setIntensityLimit, value)

    def _setIntensityLimit(self, value):
        """Set the value for the minimum intensity limit
        """
        self.preferences.general.intensityLimit = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMultipletAveraging(self):
        value = self.multipletAveraging.getIndex()
        if value != self.preferences.general.multipletAveraging:
            return partial(self._setMultipletAveraging, value)

    def _setMultipletAveraging(self, value):
        """Set the multiplet averaging type - normal or weighted
        """
        self.preferences.general.multipletAveraging = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetVolumeIntegralLimit(self, _value):
        textFromValue = self.volumeIntegralLimitData.textFromValue
        value = self.volumeIntegralLimitData.get()
        prefValue = textFromValue(self.preferences.general.volumeIntegralLimit)
        if value >= 0 and textFromValue(value) != prefValue:
            return partial(self._setVolumeIntegralLimit, value)

    def _setVolumeIntegralLimit(self, value):
        """Set the value for increasing/decreasing width of strips
        """
        self.preferences.general.volumeIntegralLimit = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetVerifySSL(self, _value):
        value = self.verifySSLBox.get()
        if value != self.preferences.proxySettings.verifySSL:
            return partial(self._setVerifySSL, value)

    def _setVerifySSL(self, value):
        self.preferences.proxySettings.verifySSL = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseProxy(self, _value):
        value = self.useProxyBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useProxy:
            return partial(self._setUseProxy, value)

    def _setUseProxy(self, value):
        self.preferences.proxySettings.useProxy = value

    @queueStateChange(_verifyPopupApply)
    def _queueUseSystemProxy(self):
        value = self.useSystemProxyBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useSystemProxy:
            return partial(self._setUseSystemProxy, value)

    def _setUseSystemProxy(self, value):
        self.preferences.proxySettings.useSystemProxy = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyAddress(self, _value):
        value = self.proxyAddressData.get()
        if value != self.preferences.proxySettings.proxyAddress:
            return partial(self._setProxyAddress, value)

    def _setProxyAddress(self, value):
        self.preferences.proxySettings.proxyAddress = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyPort(self, _value):
        value = self.proxyPortData.get()
        if value != self.preferences.proxySettings.proxyPort:
            return partial(self._setProxyPort, value)

    def _setProxyPort(self, value):
        self.preferences.proxySettings.proxyPort = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseProxyPassword(self, _value):
        value = self.useProxyPasswordBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useProxyPassword:
            return partial(self._setUseProxyPassword, value)

    def _setUseProxyPassword(self, value):
        self.preferences.proxySettings.useProxyPassword = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyUsername(self, _value):
        value = self.proxyUsernameData.get()
        if value != self.preferences.proxySettings.proxyUsername:
            return partial(self._setProxyUsername, value)

    def _setProxyUsername(self, value):
        self.preferences.proxySettings.proxyUsername = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyPassword(self, _value):
        value = self._userPreferences.encodeValue(str(self.proxyPasswordData.get()))
        if value != self.preferences.proxySettings.proxyPassword:
            return partial(self._setProxyPassword, value)

    def _setProxyPassword(self, value):
        self.preferences.proxySettings.proxyPassword = value

    def _enableProxyButtons(self):
        """Enable/disable proxy widgets based on check boxes
        """
        usePW = self.useProxyPasswordBox.get()
        useProxy = self.useProxyBox.get()

        self.proxyAddressData.enableWidget(useProxy)
        self.proxyPortData.enableWidget(useProxy)
        self.useProxyPasswordBox.enableWidget(useProxy)
        self.proxyUsernameData.enableWidget(useProxy and usePW)
        self.proxyPasswordData.enableWidget(useProxy and usePW)

    @queueStateChange(_verifyPopupApply)
    def _queueApplyToSpectrumDisplays(self, option, checked):
        """Toggle a general checkbox option in the preferences
        Requires the parameter to be called 'option' so that the decorator gives it a unique name
        in the internal updates dict
        - not sure whether needed now
        """
        if checked != self.preferences.general[option]:
            return partial(self._toggleGeneralOptions, option, checked)

    @queueStateChange(_verifyPopupApply)
    def _queueSetFont(self, dim):
        _fontAttr = getattr(self, FONTDATAFORMAT.format(dim))
        value = _fontAttr._fontString
        if value != self.preferences.appearance[FONTPREFS.format(dim)]:
            return partial(self._setFont, dim, value)

    def _setFont(self, dim, value):
        self.preferences.appearance[FONTPREFS.format(dim)] = value

    def _getFont(self, dim, fontName):
        # Simple font grabber from the system
        _fontAttr = getattr(self, FONTDATAFORMAT.format(dim))
        value = _fontAttr._fontString
        _font = QtGui.QFont()
        _font.fromString(value)
        newFont, ok = QtWidgets.QFontDialog.getFont(_font, caption='Select {} Font'.format(fontName))
        if ok:
            self.setFontText(_fontAttr, newFont.toString())
            # add the font change to the apply queue
            self._queueSetFont(dim)

    @queueStateChange(_verifyPopupApply)
    def _queueChangeGLFontSize(self, value):
        value = int(self.glFontSizeData.getText() or str(GLFONT_DEFAULTSIZE))
        if value != self.preferences.appearance.spectrumDisplayFontSize:
            return partial(self._changeGLFontSize, value)

    def _changeGLFontSize(self, value):
        self.preferences.appearance.spectrumDisplayFontSize = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeGLAxisFontSize(self, value):
        value = int(self.glAxisFontSizeData.getText() or str(GLFONT_DEFAULTSIZE))
        if value != self.preferences.appearance.spectrumDisplayAxisFontSize:
            return partial(self._changeGLAxisFontSize, value)

    def _changeGLAxisFontSize(self, value):
        self.preferences.appearance.spectrumDisplayAxisFontSize = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeThemeStyle(self, value):
        value = self.themeStyleBox.getText()
        if value != self.preferences.appearance.themeStyle:
            return partial(self._changeThemeStyle, value)

    def _changeThemeStyle(self, value):
        self.preferences.appearance.themeStyle = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeThemeColour(self, value):
        value = self.themeColourBox.getText()
        if value != self.preferences.appearance.themeColour:
            return partial(self._changeThemeColour, value)

    def _changeThemeColour(self, value):
        self.preferences.appearance.themeColour = value

