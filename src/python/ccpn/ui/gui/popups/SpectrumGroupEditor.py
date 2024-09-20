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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-09-20 14:00:50 +0100 (Fri, September 20, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from PyQt5 import QtWidgets, QtGui, QtCore
from ast import literal_eval
from typing import Tuple, Any
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
import contextlib

import pandas as pd

from ccpn.util.Common import _compareDict
from ccpn.ui.gui.popups.Dialog import handleDialogApply, _verifyPopupApply
from ccpn.core.lib.ContextManagers import undoStackBlocking
from ccpn.core.lib.ContextManagers import queueStateChange
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup, SeriesTypes
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.PulldownListsForObjects import SpectrumGroupPulldown
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.SeriesUnitsWidget import SeriesUnitWidget, QUANTITY, TYPE, UNIT
from ccpn.core.lib.SeriesUnitConverter import SERIESUNITS, GENERIC, UNITLESS, ARBITRARYUNIT, TEMPERATURE
from ccpn.ui.gui.widgets.TextEditor import PlainTextEditor
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.guiSettings import COLOUR_SCHEMES, getColours, DIVIDER, setColourScheme, FONTLIST, ZPlaneNavigationModes
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget, DoubleSpinBoxCompoundWidget, ButtonListCompoundWidget, EntryCompoundWidget
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.popups._GroupEditorPopupABC import _GroupEditorPopupABC
from ccpn.ui.gui.popups.SpectrumPropertiesPopup import ColourTab, ContoursTab, Colour1dFrame, ColourNdFrame
from ccpn.util.AttrDict import AttrDict
from ccpn.util.Constants import ALL_SERIES_UNITS
from ccpn.ui.gui.lib.ChangeStateHandler import changeState, ChangeDict
import re
import numpy as np


DEFAULTSPACING = (3, 3)
TABMARGINS = (1, 10, 1, 5)  # l, t, r, b
INVALIDROWCOLOUR = QtGui.QColor('lightpink')
SPECTRATABNUM = 0
GENERAL1DTABNUM = 2
GENERALNDTABNUM = 1
SERIESTABNUM = 3
NUMTABS = 4
SPECTRA_LABEL = 'Spectra'
GENERALTAB1D_LABEL = 'General 1d'
GENERALTABND_LABEL = 'General Nd'
SERIES_LABEL = 'Series'
MAX_WIDGET_COUNT = 50  # For severe speed issues. If a SG contains more Spectra than this value, widgets are not created.
TAB_WARNING_MSG = f'This option is not available for Spectrum Groups containing more than {MAX_WIDGET_COUNT} spectra.'

_PidsHeader = 'Pids'
_WidgetsHeader = 'Widgets'
_ValuesHeader = 'Values'
_AdditionalValuesHeader = 'AdditionalValues'
ASCENDINGDEF = ''' Reorder spectra by Ascending series values: smaller value to be on top. i.e. A... Z or 1... 10 '''
DESCENDINGDEF = ''' Reorder spectra by Descending series values: larger value to be on top. i.e. Z.. A or 10... 1 '''
SELECT = '< Select >'

def _getEntryOrderValues(spectra):
    """Get the entry order of the series spectra in the Project"""
    project = spectra[0].project
    allSpectraPids =  [str(x.pid) for x in project.spectra]
    seriesSpectraPids =  [str(x.pid) for x in spectra]
    longList = np.array(allSpectraPids)
    values = [np.where(longList == pid)[0][0] for pid in seriesSpectraPids]

    return values

def _getEnumerateOrderValues(spectra):
    """Get the enumeration of series spectra """
    values = np.arange(start=1, stop=len(spectra)+1)
    return values

def _getPidNumberValues(spectra):
    """Get the last group of number from the pid of series spectra """
    values = []
    pids = [x.pid for x in spectra]
    for pid in pids:
        # Find all groups of digits in the string
        digits = re.findall(r'\d+', str(pid))
        if digits:
            # Take the last group of digits
            number_str = digits[-1]
            values.append(number_str)
        else:
            values.append('')
    if len(pids) != len(values):
        return [''] * len(pids)
    return values

def _getTemperatureValues(spectra):
    values = [x.temperature if x.temperature else '' for x in spectra ]
    return values

def _getNoiseLevelValues(spectra):
    values = [x.noiseLevel if x.noiseLevel else '' for x in spectra]
    return values

def _getSpinningRateValues(spectra):
    values = [x.spinningRate if x.spinningRate else '' for x in spectra]
    return values

def _getEmptyValues(spectra):
    values = ['']*len(spectra)
    return values


FILLING_BY_PROPERTIES = {
                                    'Enumeration': {
                                                        'callback': _getEnumerateOrderValues,
                                                        'tipText' : 'Enumerate by the current order',
                                                        QUANTITY  : GENERIC,
                                                        TYPE      : SeriesTypes.INTEGER.description,
                                                        UNIT      : ARBITRARYUNIT
                                                        },
                                    'Project Entry Order' :{
                                                        'callback':_getEntryOrderValues,
                                                        'tipText': 'Enumerate by the entry order in the project',
                                                        QUANTITY: GENERIC,
                                                        TYPE: SeriesTypes.INTEGER.description,
                                                        UNIT: ARBITRARYUNIT
                                                        },
                                    'Pid Number': {
                                                        'callback':_getPidNumberValues,
                                                        'tipText': 'Use the last group of numbers defined in the Pid (if any)',
                                                        QUANTITY: GENERIC,
                                                        TYPE    : SeriesTypes.FLOAT.description,
                                                        UNIT    : ARBITRARYUNIT
                                                         },
                                    'Temperature':{
                                                        'callback':_getTemperatureValues,
                                                        'tipText': 'Temperature',
                                                        QUANTITY: TEMPERATURE,
                                                        TYPE    : SeriesTypes.FLOAT.description,
                                                        UNIT    :  'K'
                                                         },
                                    'Noise Level':{
                                                        'callback':_getNoiseLevelValues,
                                                        'tipText': 'Noise Level',
                                                        QUANTITY: GENERIC,
                                                        TYPE    : SeriesTypes.FLOAT.description,
                                                        UNIT    : ARBITRARYUNIT
                                                         },

                                    'Clear All':{
                                                        'callback': _getEmptyValues,
                                                        'tipText': 'Remove all existing values',
                                                        QUANTITY: GENERIC,
                                                        TYPE    : SeriesTypes.FLOAT.description,
                                                        UNIT    : ARBITRARYUNIT
                                        },
                                    }

FILLINGBYOPTIONS = list(FILLING_BY_PROPERTIES.keys())
FILLINGBYTIPTEXTS = [v.get('tipText') for k,v in FILLING_BY_PROPERTIES.items()]


class SpectrumGroupEditor(_GroupEditorPopupABC):
    """
    A popup to create and manage SpectrumGroups

    Used in 'New' or 'Edit' mode:
    - For creating new SpectrumGroup (editMode==False); optionally uses passed in spectra list
      i.e. NewSpectrumGroup of SideBar and Context menu of SideBar

    - For editing existing SpectrumGroup (editMode==True); requires spectrumGroup argument
      i.e. Edit of SpectrumGroup of SideBar
    or
      For selecting and editing SpectrumGroup (editMode==True)
      i.e. Menu Spectrum->Edit SpectrumGroup...

    """
    _class = SpectrumGroup
    _classItemAttribute = 'spectra'  # Attribute in _class containing items
    _classPulldown = SpectrumGroupPulldown

    _projectNewMethod = 'newSpectrumGroup'  # Method of Project to create new _class instance
    _projectItemAttribute = 'spectra'  # Attribute of Project containing items

    # define these
    _singularItemName = 'Spectrum'  # eg 'Spectrum'
    _pluralItemName = 'Spectra'  # eg 'Spectra'

    _setRevertButton = False

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

        _colourTabs1d = [self._colourTabs1d.widget(tt) for tt in range(self._colourTabs1d.count())]
        _colourTabsNd = [self._colourTabsNd.widget(tt) for tt in range(self._colourTabsNd.count())]
        # if not (_colourTabs1d or _colourTabsNd):
        #     raise RuntimeError("Code error: tabs not implemented")

        _allTabs = self.getActiveTabList()

        # get the list of widgets that have been changed - exit if all empty
        allChanges = any(t._changes for t in _allTabs if t is not None) or bool(self._currentEditorState())
        if not allChanges:
            return True

        # handle clicking of the Apply/OK button
        with handleDialogApply(self) as error:

            # get the list of spectra that have changed - for refreshing the displays
            spectrumList = []
            for t in (_colourTabs1d + _colourTabsNd):
                if t is not None:
                    changes = t._changes
                    if changes:
                        spectrumList.append(t.spectrum)

            # add an undo item to redraw these spectra
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=partial(self._updateGl, spectrumList))

            # call the _groupEditor _applyChanges method which sets the group items
            if not super()._applyChanges():
                error.errorValue = True

            # add a redo item to redraw these spectra
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=partial(self._updateGl, spectrumList))

            # rebuild the contours as required
            for spec in spectrumList:
                for specViews in spec.spectrumViews:
                    specViews.buildContours = True
            self._updateGl(spectrumList)

        # everything has happened - disable the apply button
        self._applyButton.setEnabled(False)

        # check for any errors
        if error.errorValue:
            # repopulate popup on an error
            self._populate()
            return False

        # remove all changes
        for tab in (_colourTabs1d + _colourTabsNd):
            tab._changes = ChangeDict()

        # self._currentNumApplies += 1
        # self._revertButton.setEnabled(True)
        return True

    @staticmethod
    def convertListToProperType(lst):
        """A fallback attempt to convert to a proper type """
        def convertType(value):
            if value in ['', ' ', None, np.nan]:
                return None
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
        return [convertType(item) for item in lst]

    def _groupInit(self):
        # apply the changes to the listed spectra spectraTab._changes
        if self.spectraTab._changes:
            self._applyAllChanges(self.spectraTab._changes)

        for tt in range(self._colourTabs1d.count()):
            if _changes := self._colourTabs1d.widget(tt)._changes:
                self._applyAllChanges(_changes)

        for tt in range(self._colourTabsNd.count()):
            if _changes := self._colourTabsNd.widget(tt)._changes:
                self._applyAllChanges(_changes)

        with contextlib.suppress(Exception):
            if _changes := self._group1dColours._changes:
                # self._group1dColours.spectrumGroup = self.obj
                self._applyAllChanges(_changes)
                if self.obj != self._group1dColours.spectrumGroup:
                    # if a dummy spectrumGroup then copy to actual group
                    for k, val in self._group1dColours.spectrumGroup.items():
                        setattr(self.obj, k, val)

        with contextlib.suppress(Exception):
            if _changes := self._groupNdColours._changes:
                # self._groupNdColours.spectrumGroup = self.obj
                self._applyAllChanges(_changes)
                if self.obj != self._groupNdColours.spectrumGroup:
                    # if a dummy spectrumGroup then copy to actual group
                    for k, val in self._groupNdColours.spectrumGroup.items():
                        setattr(self.obj, k, val)

        self._spectrumGroupSeriesEdited = OrderedDict()
        self._spectrumGroupSeriesValues = list(self.obj.series)
        self._spectrumGroupAdditionalSeriesValues = list(self.obj.additionalSeries)

        # set the series values - this may crash
        if self.seriesTab._changes:
            self._applyAllChanges(self.seriesTab._changes)

        ## apply the units to the object. Could not use the _spectrumGroupSeriesUnitsEdited succesfully. gave up.
        self.obj.seriesQuantity = self.seriesTab.seriesUnitWidget.getQuantity()
        self.obj.seriesUnits = self.seriesTab.seriesUnitWidget.getUnit()
        self.obj.seriesType = self.seriesTab.seriesUnitWidget.getTypeCode()

        df = self.seriesTab._getDFfromSeriesWidgets()
        if df.empty:
            return

        seriesTypeCallable = self.seriesTab.seriesUnitWidget.getTypeCallable()
        values = df[_ValuesHeader].values
        if seriesTypeCallable is not None:
            vv = [seriesTypeCallable(v) if v else None for v in values]
        else:
            vv = self.convertListToProperType(values)
        if len(self.obj.spectra) == 0:
            self.obj.series = []
        else:
            self.obj.series = vv

        #add the additional values to the object
        _allAdditionalValues = df[_AdditionalValuesHeader].values
        _allAdditionalValues = self.convertListToProperType([_allAdditionalValues[0]])
        _allAdditionalValues = tuple(_allAdditionalValues)
        _allAdditionalValues = (_allAdditionalValues,)*len(self.obj.series)
        self.obj.additionalSeries = _allAdditionalValues

    _groupEditorInitMethod = _groupInit

    # make this a tabbed dialog, with the default widget going into tab 0
    _useTab = 0
    _numberTabs = 4  # create the first tab

    def __init__(self, parent=None, mainWindow=None, editMode=True, obj=None, defaultItems=None, size=(700, 550), **kwds):
        """
        Initialise the widget, note defaultItems is only used for create
        """
        super().__init__(parent=parent, mainWindow=mainWindow, editMode=editMode, obj=obj, defaultItems=defaultItems, size=size, **kwds)

        self.TAB_NAMES = ((SPECTRA_LABEL, self._initSpectraTab),
                          (GENERALTABND_LABEL, self._initGeneralTabNd),
                          (GENERALTAB1D_LABEL, self._initGeneralTab1d),
                          (SERIES_LABEL, self._initSeriesTab))

        if obj and editMode:
            defaultItems = obj.spectra
        # replace the tab widget with a new seriesWidget
        seriesTabContents = SeriesFrame(parent=self, container=self, mainWindow=self.mainWindow, spectrumGroup=obj, editMode=editMode,
                                        showCopyOptions=True if defaultItems and len(defaultItems) > 1 else False,
                                        defaultItems=defaultItems or ())
        self._tabWidget.widget(SERIESTABNUM).setWidget(seriesTabContents)

        # get pointers to the tabs
        self.spectraTab = self._tabWidget.widget(SPECTRATABNUM)._scrollContents
        self.generalTab1d = self._tabWidget.widget(GENERAL1DTABNUM)._scrollContents
        self.generalTabNd = self._tabWidget.widget(GENERALNDTABNUM)._scrollContents
        self.seriesTab = self._tabWidget.widget(SERIESTABNUM)._scrollContents

        self._generalTabWidget1d = self._tabWidget.widget(GENERAL1DTABNUM)
        self._generalTabWidgetNd = self._tabWidget.widget(GENERALNDTABNUM)

        self.currentSpectra = self._getSpectraFromList()

        # this should be the list when the popup is opened
        self._defaultSpectra = self.currentSpectra
        self._defaultName = self._editedObject.name if self._editedObject else ''
        self._defaultComment = self._editedObject.comment if self._editedObject else ''

        # set the labels in the first pass
        for tNum, (tabName, tabFunc) in enumerate(self.TAB_NAMES):
            self._tabWidget.setTabText(tNum, tabName)

        self.setDefaultButton(None)
        self.setSizeGripEnabled(False)

    def _postInit(self):

        super()._postInit()
        for tNum, (tabName, tabFunc) in enumerate(self.TAB_NAMES):
            if tabFunc:
                tabFunc()
        self._populate(populateSeries=False)  # populateSeries MUST be False here. already done  1Line above  tabFunc(). It is not needed to populate again all!
        self.connectSignals()

    def connectSignals(self):
        # connect to changes in the spectrumGroup
        self.nameEdit.textChanged.connect(self.seriesTab._queueChangeName)
        self.commentEdit.textChanged.connect(self.seriesTab._queueChangeComment)
        self.targetListWidget.model().dataChanged.connect(self._spectraChanged)
        self.targetListWidget.model().rowsRemoved.connect(self._spectraChanged)
        self.targetListWidget.model().rowsInserted.connect(self._spectraChanged)
        self.targetListWidget.model().rowsMoved.connect(self._spectraChanged)

    def getActiveTabList(self):
        """Return the list of active tabs
        """
        # test the colour tabs for the moment
        _1dTabs = tuple(self._colourTabs1d.widget(ii) for ii in range(self._colourTabs1d.count()))
        _NdTabs = tuple(self._colourTabsNd.widget(ii) for ii in range(self._colourTabsNd.count()))
        _1dGroup = (self._group1dColours,) if _1dTabs else ()
        _NdGroup = (self._groupNdColours,) if _NdTabs else ()

        tabs = _1dTabs + _NdTabs + _1dGroup + _NdGroup + (self.spectraTab, self.seriesTab)
        return tabs

    def _initSpectraTab(self):
        thisTab = self.spectraTab
        thisTab._changes = ChangeDict()

    def _init1DColourTabs(self):

        spectra1d = [spec for spec in (self.currentSpectra or []) if spec.dimensionCount == 1]
        for specNum, thisSpec in enumerate(spectra1d):

            if thisSpec.dimensionCount == 1:
                contoursTab = ColourTab(parent=self, container=self, mainWindow=self.mainWindow, spectrum=thisSpec,
                                        showCopyOptions=True if len(spectra1d) > 1 else False,
                                        copyToSpectra=spectra1d)

                self._colourTabs1d.addTab(contoursTab, thisSpec.name)
                contoursTab.setContentsMargins(*TABMARGINS)

        self._colourTabs1d.setTabClickCallback(self._tabClicked1d)
        self._colourTabs1d.tabCloseRequested.connect(self._closeColourTab1d)
        index = self._tabWidget.indexOf(self._generalTabWidget1d)
        if self._colourTabs1d.count() == 0:
            if (0 <= index < NUMTABS):
                self._tabWidget.removeTab(index)

    def _initGeneralTab1d(self):
        thisTab = self.generalTab1d

        self._group1dColours = Colour1dFrame(parent=thisTab, mainWindow=self.mainWindow, container=self, editMode=self.EDITMODE, spectrumGroup=self.obj,
                                             grid=(0, 0), setLayout=True)

        self._colourDisabledFrame = Frame(thisTab, setLayout=True, showBorder=False,
                                          grid=(1, 0), vAlign='t')
        iconLabel = Label(self._colourDisabledFrame, icon=Icon('icons/exclamation_small'), grid=(0, 0), hAlign='l')
        tabWarningLabel = Label(self._colourDisabledFrame, text=TAB_WARNING_MSG, grid=(0, 1), hAlign='l', )
        self._colourDisabledFrame.hide()

        self._colourTabs1d = Tabs(thisTab, grid=(2, 0))
        self._oldTabs = OrderedDict()

        self._group1dColours.setContentsMargins(5, 5, 5, 5)
        thisTab.setContentsMargins(0, 0, 0, 0)

        # remember the state when switching tabs
        self.copyCheckBoxState = []

        if len(self.currentSpectra) > MAX_WIDGET_COUNT:
            self._setDisabledColourTab()
        else:
            self._init1DColourTabs()

    def _initGeneralTabNd(self):
        thisTab = self.generalTabNd

        self._groupNdColours = ColourNdFrame(parent=thisTab, mainWindow=self.mainWindow, container=self, editMode=self.EDITMODE, spectrumGroup=self.obj,
                                             grid=(0, 0), setLayout=True)

        self._colourTabsNd = Tabs(thisTab, grid=(1, 0))

        self._groupNdColours.setContentsMargins(5, 5, 5, 5)
        thisTab.setContentsMargins(0, 0, 0, 0)

        # remember the state when switching tabs
        self.copyCheckBoxState = []

        spectraNd = [spec for spec in (self.currentSpectra or []) if spec.dimensionCount > 1]
        for specNum, thisSpec in enumerate(spectraNd):

            if thisSpec.dimensionCount > 1:
                contoursTab = ContoursTab(parent=self, container=self, mainWindow=self.mainWindow, spectrum=thisSpec,
                                          showCopyOptions=True if len(spectraNd) > 1 else False,
                                          copyToSpectra=spectraNd)

                self._colourTabsNd.addTab(contoursTab, thisSpec.name)
                contoursTab.setContentsMargins(*TABMARGINS)

        self._colourTabsNd.setTabClickCallback(self._tabClickedNd)
        self._colourTabsNd.tabCloseRequested.connect(self._closeColourTabNd)

        index = self._tabWidget.indexOf(self._generalTabWidgetNd)
        if self._colourTabsNd.count() == 0:
            if (0 <= index < NUMTABS):
                self._tabWidget.removeTab(index)

    def _initSeriesTab(self):
        thisTab = self.seriesTab
        thisTab._changes = ChangeDict()
        thisTab._populateSeries()

    def _fillPullDowns(self):
        for colourTab in (self._colourTabs1d, self._colourTabsNd):
            for aTab in tuple(colourTab.widget(ii) for ii in range(colourTab.count())):
                aTab._fillPullDowns()

        with contextlib.suppress(Exception):
            self._group1dColours._fillPullDowns()
        with contextlib.suppress(Exception):
            self._groupNdColours._fillPullDowns()

    def _populate(self, populateSeries=True):
        """Populate the widgets in the tabs
        """
        ## NOTE:ED - check that the  widgets are populated correctly - may be called exponentially from not
        ## blocking the notification-change
        super()._populate()
        with self.seriesTab._changes.blockChanges():
            self._spectraChanged()

        # check whether any tabs need removing here
        for colourTab in (self._colourTabs1d, self._colourTabsNd):
            for aTab in tuple(colourTab.widget(ii) for ii in range(colourTab.count())):
                aTab._populateColour()

        with contextlib.suppress(Exception):
            self._group1dColours._populateColour()
        with contextlib.suppress(Exception):
            self._groupNdColours._populateColour()


        if populateSeries:
            with self.blockWidgetSignals():  # we already filled when calling _spectraChanged
                self.seriesTab._fillSeriesFrame(self._defaultSpectra, spectrumGroup=self.obj)
                self.seriesTab._populateSeries()

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        try:
            editName = self.nameEdit.text()
            defaultName = self._defaultName
            editComment = self.commentEdit.text() or None
            defaultComment = self._defaultComment
            pidState = self._groupedObjects
            pidList = [str(spec.pid) for spec in self._defaultSpectra]

            revertState = (pidState != pidList) or (editName != defaultName) or (editComment != defaultComment)
            # applyState = (True if pidState else False) and (True if editName else False)  # and revertState
            # only need a name, can now have an empty group
            applyState = (True if editName else False)  # and revertState

            tabs = self.getActiveTabList()
            allChanges = any(t._changes for t in tabs if t is not None)

        except Exception as es:
            return None

        return changeState(self, allChanges, applyState, revertState, self._applyButton, None, self._revertButton, 0)

    def _tabClicked1d(self, index):
        """Callback for clicking a tab - needed for refilling the checkboxes and populating the pulldown
        """
        for colourTab in (self._colourTabs1d,):
            aTabs = tuple(colourTab.widget(ii) for ii in range(colourTab.count()))
            if aTabs and hasattr(aTabs[index], '_populateCheckBoxes'):
                aTabs[index]._populateCheckBoxes()

    def _tabClickedNd(self, index):
        """Callback for clicking a tab - needed for refilling the checkboxes and populating the pulldown
        """
        for colourTab in (self._colourTabsNd,):
            aTabs = tuple(colourTab.widget(ii) for ii in range(colourTab.count()))
            if aTabs and hasattr(aTabs[index], '_populateCheckBoxes'):
                aTabs[index]._populateCheckBoxes()

    def _getSpectraFromList(self):
        """Get the list of spectra from the list
        """
        spectra = [self.project.getByPid(spectrum) if isinstance(spectrum, str) else spectrum for spectrum in self._groupedObjects]

        return [spec for spec in spectra if spec]

    def _cleanColourTab(self, spectrum):
        """Remove the unwanted queue items from spectra reomved from the spectrumQueue
        """
        with self.blockWidgetSignals():
            for colourTab in (self._colourTabs1d, self._colourTabsNd):
                for aTab in tuple(colourTab.widget(ii) for ii in range(colourTab.count())):
                    if aTab.spectrum == spectrum:
                        aTab._cleanWidgetQueue()

    def _removeTab(self, spectrum):
        """Remove the unwanted queue items from spectra reomved from the spectrumQueue
        """
        for colourTab in (self._colourTabs1d, self._colourTabsNd):
            for aTab in tuple(colourTab.widget(ii) for ii in range(colourTab.count())):
                if aTab.spectrum == spectrum:
                    pass

    def _closeColourTab1d(self, index):
        self._colourTabs1d.removeTab(index)

    def _closeColourTabNd(self, index):
        self._colourTabsNd.removeTab(index)

    def _targetPullDownCallback(self, value=None):
        """Callback when selecting the left spectrumGroup pulldown item
        """
        obj = self.project.getByPid(value)
        if obj:
            # set the new object
            self.defaultObject = obj
        super(SpectrumGroupEditor, self)._targetPullDownCallback(value)

    def _spectraChanged(self, *args):
        """Respond to a change in the list of spectra to add the spectrumGroup
        """
        self._spectraChanged1d()
        self._spectraChangedNd()
        # call the series frame as this contains code for updating _changes
        self.seriesTab._queueChangeSpectrumList()
        self.seriesTab._fillSeriesFrame(self.currentSpectra, spectrumGroup=self.obj)

    def _spectraChanged1d(self):
        self._newSpectra = self._getSpectraFromList()

        if len(self._newSpectra) > MAX_WIDGET_COUNT:
            self._setDisabledColourTab()
            return
        self._colourTabs1d.show()
        self._colourDisabledFrame.hide()
        deleteSet = (set(self.currentSpectra) - set(self._newSpectra))
        newSet = (set(self.currentSpectra) - set(self._newSpectra))

        # only select the 1d spectra
        deleteSet = [spec for spec in deleteSet if spec.dimensionCount == 1]
        spectra1d = [spec for spec in self._newSpectra if spec.dimensionCount == 1]

        for spec in deleteSet:
            # remove tab widget
            self._cleanColourTab(spec)
            if spec in self.seriesTab._currentSeriesValues:
                del self.seriesTab._currentSeriesValues[spec]  # why this del here
        # remove all in reverse order, keep old ones
        for ii in range(self._colourTabs1d.count() - 1, -1, -1):
            tab = self._colourTabs1d.widget(ii)
            self._oldTabs[tab.spectrum] = tab
            self._colourTabs1d.removeTab(ii)

        for spec in spectra1d:
            # add new tab widget here
            if spec in self._oldTabs:
                self._colourTabs1d.addTab(self._oldTabs[spec], spec.name)
                self._oldTabs[spec].setCopyOptionsVisible(True if len(spectra1d) > 1 else False)

                # make sure the new spectrum lists are up-to-date
                self._oldTabs[spec]._updateSpectra(spec, spectra1d)
                self._oldTabs[spec]._populateColour()
            else:
                if spec.dimensionCount == 1:
                    contoursTab = ColourTab(parent=self, container=self, mainWindow=self.mainWindow, spectrum=spec,
                                            showCopyOptions=True if len(spectra1d) > 1 else False,
                                            copyToSpectra=spectra1d)

                    self._colourTabs1d.addTab(contoursTab, spec.name)  #this indent looks wrong
                    contoursTab.setContentsMargins(*TABMARGINS)
                    contoursTab._populateColour()

        # set the visibility of the general 1d tab
        index = self._tabWidget.indexOf(self._generalTabWidget1d)
        if self._colourTabs1d.count() == 0:
            if (0 <= index < NUMTABS):
                self._tabWidget.removeTab(index)
        else:
            if not (0 <= index < NUMTABS):
                self._tabWidget.insertTab(1, self._generalTabWidget1d, GENERALTAB1D_LABEL)

        # update the current list
        self.currentSpectra = self._newSpectra
        self.seriesTab._setSeriesOptionsEnabled(len(self.currentSpectra) > 0)


    def _spectraChangedNd(self):
        self._newSpectra = self._getSpectraFromList()

        deleteSet = (set(self.currentSpectra) - set(self._newSpectra))
        newSet = (set(self.currentSpectra) - set(self._newSpectra))

        # only select the 1d spectra
        deleteSet = [spec for spec in deleteSet if spec.dimensionCount > 1]
        spectraNd = [spec for spec in self._newSpectra if spec.dimensionCount > 1]

        for spec in deleteSet:
            # remove tab widget
            self._cleanColourTab(spec)
            if spec in self.seriesTab._currentSeriesValues:
                del self.seriesTab._currentSeriesValues[spec]

        # remove all in reverse order, keep old ones
        for ii in range(self._colourTabsNd.count() - 1, -1, -1):
            tab = self._colourTabsNd.widget(ii)
            self._oldTabs[tab.spectrum] = tab
            self._colourTabsNd.removeTab(ii)

        for spec in spectraNd:
            # add new tab widget here
            if spec in self._oldTabs:
                self._colourTabsNd.addTab(self._oldTabs[spec], spec.name)
                self._oldTabs[spec].setCopyOptionsVisible(True if len(spectraNd) > 1 else False)

                # make sure the new spectrum lists are up-to-date
                self._oldTabs[spec]._updateSpectra(spec, spectraNd)
                self._oldTabs[spec]._populateColour()
            else:
                if spec.dimensionCount > 1:
                    contoursTab = ContoursTab(parent=self, container=self, mainWindow=self.mainWindow, spectrum=spec,
                                              showCopyOptions=True if len(spectraNd) > 1 else False,
                                              copyToSpectra=spectraNd)

                    self._colourTabsNd.addTab(contoursTab, spec.name)
                    contoursTab.setContentsMargins(*TABMARGINS)
                    contoursTab._populateColour()

        # set the visibility of the general 1d tab
        index = self._tabWidget.indexOf(self._generalTabWidgetNd)
        if self._colourTabsNd.count() == 0:
            if (0 <= index < NUMTABS):
                self._tabWidget.removeTab(index)
        else:
            if not (0 <= index < NUMTABS):
                self._tabWidget.insertTab(self._tabWidget.count() - 1, self._generalTabWidgetNd, GENERALTABND_LABEL)

        # update the current list
        self.currentSpectra = self._newSpectra
        self.seriesTab._setSeriesOptionsEnabled(len(self.currentSpectra) > 0)


    def copySpectra(self, fromSpectrum, toSpectra):
        """Copy the contents of tabs to other spectra
        """
        colourTabs = [self._colourTabs1d.widget(ii) for ii in range(self._colourTabs1d.count())] + \
                     [self._colourTabsNd.widget(ii) for ii in range(self._colourTabsNd.count())]
        for aTab in colourTabs:
            if aTab.spectrum == fromSpectrum:
                fromSpectrumTab = aTab
                for aTab in [tab for tab in colourTabs if tab != fromSpectrumTab and tab.spectrum in toSpectra]:
                    aTab._copySpectrumAttributes(fromSpectrumTab)

    def _setDisabledColourTab(self):
        self._colourTabs1d.hide()
        self._colourDisabledFrame.show()
        for sp in self.currentSpectra:
            self._cleanColourTab(sp)


class SeriesFrame(Frame):
    _editMode = False

    def __init__(self, parent=None, container=None, mainWindow=None, spectrumGroup=None, editMode=False,
                 showCopyOptions=False, defaultItems=None):

        super().__init__(parent, setLayout=True, spacing=DEFAULTSPACING)

        self._parent = parent
        self._container = container
        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.preferences = self.application.preferences
        self._editMode = editMode
        self._seriesEnabled = True
        # check that the spectrum and the copyToSpectra list are correctly defined
        getByPid = self.application.project.getByPid
        self.spectrumGroup = getByPid(spectrumGroup) if isinstance(spectrumGroup, str) else spectrumGroup
        if not isinstance(self.spectrumGroup, (SpectrumGroup, type(None))):
            raise TypeError('spectrumGroup must be of type spectrumGroup or None')

        if not isinstance(defaultItems, (Iterable, type(None))):
            raise TypeError('copyToSpectra must be of type Iterable/None')
        if defaultItems:
            self._copyToSpectra = [getByPid(spectrum) if isinstance(spectrum, str) else spectrum for spectrum in defaultItems]
            for spec in self._copyToSpectra:
                if not isinstance(spec, (Spectrum, type(None))):
                    raise TypeError('copyToSpectra is not defined correctly.')
        else:
            self._copyToSpectra = None

        self._changes = ChangeDict()
        self._editors = OrderedDict()
        self._currentSeriesValues = OrderedDict()

        if self._editMode:
            self.defaultObject = spectrumGroup
        else:
            # create a dummy object that SHOULD contain the required attributes
            self.defaultObject = _SpectrumGroupContainer()
            self.defaultObject.spectra = defaultItems

        ## Set widgets
        self._operationFrames = [] #add a list of frames that need to be disabled if No spectra
        self._mainLayoutRow = 0
        self._mainLayoutCol = 0
        self._mainLayoutGridSpan = (1,3)
        lineColour = getColours()[DIVIDER]
        self.labelMinimumWidth = 120 #label size for the compound widgets. needed for looking nicely aligned (to the left)
        self.widgetlMinimumWidth = 200


        ## Series Predefined selections  section
        self._presetOptionsFrame = Frame(self, setLayout=True, grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._operationFrames += [self._presetOptionsFrame]
        self._presetOptionsRow = 0
        _HLine = LabeledHLine(parent=self._presetOptionsFrame, text='Preset options', colour=lineColour, grid=(self._presetOptionsRow, 0), gridSpan=self._mainLayoutGridSpan)
        self._presetOptionsRow += 1
        self._fiilBySpectrumPropertyPulldown = PulldownListCompoundWidget(self._presetOptionsFrame,
                                                                          labelText='Populate By',
                                                                          texts=FILLINGBYOPTIONS,
                                                                          toolTips=FILLINGBYTIPTEXTS,
                                                                          callback=self._setValueFromSpectrumProperty,
                                                                          grid=(self._presetOptionsRow, 1),
                                                                          compoundKwds={'headerText':SELECT},
                                                                          minimumWidths=(self.labelMinimumWidth, self.widgetlMinimumWidth))

        self._mainLayoutRow += 1

        ## Units section
        self._seriesUnitsFrame = Frame(self, setLayout=True, showBorder=False,  grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._operationFrames += [self._seriesUnitsFrame]
        self._seriesUnitsFrameRow = 0
        _HLine = LabeledHLine(parent=self._seriesUnitsFrame, text='Units', grid=(self._seriesUnitsFrameRow, 0), colour=lineColour, gridSpan=self._mainLayoutGridSpan)
        self._seriesUnitsFrameRow += 1
        self.seriesUnitWidget = SeriesUnitWidget(self._seriesUnitsFrame, callback=self._seriesUnitWidgetCallback, labelMinimumWidth=self.labelMinimumWidth, grid=(self._seriesUnitsFrameRow, 0))
        self.seriesUnitWidget.quantitySelectionChanged.connect(partial(self._queueChangeSeriesQuantity, self.seriesUnitWidget, self.defaultObject))
        self.seriesUnitWidget.unitSelectionChanged.connect(partial(self._queueChangeSeriesUnits, self.seriesUnitWidget, self.defaultObject))
        self.seriesUnitWidget.typeSelectionChanged.connect(partial(self._queueChangeSeriesType, self.seriesUnitWidget, self.defaultObject))
        self.seriesUnitWidget.deselectedAllSignal.connect(partial(self._allUnitsOptionsChanged, self.seriesUnitWidget, self.defaultObject))



        self.seriesUnitWidget.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)  # Align top and left
        self._mainLayoutRow += 1

        ## Series Values  section
        self._seriesValuesFrame = Frame(self, setLayout=True, showBorder=False, grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._operationFrames += [self._seriesValuesFrame]
        self._seriesValuesFrameRow = 0
        self._seriesValuesFrameCol = 0
        _HLine = LabeledHLine(parent=self._seriesValuesFrame, text='Values', colour=lineColour, grid=(self._seriesValuesFrameRow, self._seriesValuesFrameCol), gridSpan=self._mainLayoutGridSpan)
        self._seriesValuesFrameRow += 1
        self._seriesFrameRow = self._seriesValuesFrameRow
        self._seriesFrame = Frame(self, setLayout=True, showBorder=False, grid=(self._seriesValuesFrameRow, self._seriesValuesFrameCol), gridSpan=self._mainLayoutGridSpan)
        self._mainLayoutRow += 1

        ## Series Additional Values  section
        self._seriesAdditionalValuesFrame = Frame(self, setLayout=True, showBorder=False, grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._operationFrames += [self._seriesAdditionalValuesFrame]
        self._seriesAdditionalValuesFrameRow = 0
        _HLine = LabeledHLine(parent=self._seriesAdditionalValuesFrame, text='Additional Values', colour=lineColour, grid=(self._seriesAdditionalValuesFrameRow, 0), gridSpan=self._mainLayoutGridSpan)
        self._seriesAdditionalValuesFrameRow += 1
        tipText = 'Additional Series Value in the same units as the main series values. E.g.: Global protein concentration. '
        self.additionalValueEditor = EntryCompoundWidget(self._seriesAdditionalValuesFrame,
                                                                 labelText='Global Value', tipText=tipText,
                                                                 compoundKwds={'backgroundText':''},
                                                                 callback=None, #set as signal on editing finished
                                                                 grid=(self._seriesAdditionalValuesFrameRow, 0),
                                                                 minimumWidths=(self.labelMinimumWidth, self.widgetlMinimumWidth))
        self.additionalValueEditor.entry.textChanged.connect(partial(self._queueChangeAdditionalSeriesValues, self.additionalValueEditor, self.defaultObject))

        self._mainLayoutRow += 1

        ## Series Actions  section
        self._actionsFrame = Frame(self, setLayout=True, grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._operationFrames += [self._actionsFrame]
        self._actionsFrameRow = 0
        _HLine = LabeledHLine(parent=self._actionsFrame, text='Actions', colour=lineColour, grid=(self._actionsFrameRow, 0), gridSpan=self._mainLayoutGridSpan)
        self._actionsFrameRow += 1
        buttonMinimumWidth = int(self.widgetlMinimumWidth/2)
        self._orderButtons = ButtonListCompoundWidget(self._actionsFrame,
                                                                            labelText='Reorder Series',
                                                                            texts=['Small to Large', 'Large to Small'],
                                                                            tipTexts=[ASCENDINGDEF, DESCENDINGDEF],
                                                                            callbacks=[partial(self._reorderSpectraBySeries, True), partial(self._reorderSpectraBySeries, False)],
                                                                            grid=(self._actionsFrameRow, 1),
                                                                            minimumWidths=(self.labelMinimumWidth, self.widgetlMinimumWidth),
                                                                            buttonMinimumWidth=buttonMinimumWidth)
        self._actionsFrameRow += 1
        self._convertButtons = ButtonListCompoundWidget(self._actionsFrame,
                                                      labelText='Convert to SI ',
                                                      texts=['Apply'],
                                                      tipTexts=['Convert the Series values to the SI Base Unit for the selected quantity'],
                                                      callbacks=[self._convertSeriesToSiUnits],
                                                      grid=(self._actionsFrameRow, 1),
                                                      minimumWidths=(self.labelMinimumWidth, self.widgetlMinimumWidth),
                                                      buttonMinimumWidth=buttonMinimumWidth)

        self._toggleConversionButton()
        self._actionsFrameRow += 1
        self._mainLayoutRow += 1

        ## Error Icons section
        self._errorsFrame = Frame(self, setLayout=True, grid=(self._mainLayoutRow, self._mainLayoutCol), gridSpan=self._mainLayoutGridSpan)
        self._errorsFrameRow = 0
        _HLine = LabeledHLine(parent=self._errorsFrame, text='Warnings', colour=lineColour, grid=(self._errorsFrameRow, 0), gridSpan=self._mainLayoutGridSpan)
        self._errorsFrameRow += 1

        self._errorFrameSeriesValues = Frame(self._errorsFrame, setLayout=True, grid=(self._errorsFrameRow, 0), gridSpan=self._mainLayoutGridSpan)
        # add a frame containing an error message if the series values are not all the same type
        self.errorIcon = Icon('icons/exclamation_small')
        self._errors = ['All series values must be of the same type: either all Float, Integer, or String, or all empty.']
        for i, error in enumerate(self._errors):
            iconLabel = Label(self._errorFrameSeriesValues, grid=(i, 0))
            iconLabel.setPixmap(self.errorIcon.pixmap(16, 16))
            label = Label(self._errorFrameSeriesValues, error, grid=(i, 1))
        self._errorFrameSeriesValues.hide()
        self._errorFrameSeriesValues.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)  # Align top and left

        # set the background to transparent so matches the colour of the tab
        self.setAutoFillBackground(False)
        self.setStyleSheet('Frame { background: transparent; }')

        if len(defaultItems) ==0:
            self._setSeriesOptionsEnabled(False)
        if self._seriesEnabled:
            self._fillSeriesFrame(defaultItems=defaultItems, spectrumGroup=self.defaultObject)
        self.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)  # Align top and left
        self.getLayout().setRowStretch(self._mainLayoutRow+1, 10)  # set stretch to last frame to expand when resize the window

    def _getDFfromSeriesWidgets(self):
        dd = defaultdict(list)
        _additionalValues = self.additionalValueEditor.getText() #note: the initial _additionalValues is only one global value. Eventually will be multiple per spectrum.
        for sp, widget in self._editors.items():
            dd[_WidgetsHeader].append(widget)
            dd[_ValuesHeader].append(widget.get())
            dd[_AdditionalValuesHeader].append(_additionalValues)
            dd[_PidsHeader].append(sp.pid)
        df = pd.DataFrame(dd)
        return df

    def _applyNewValuesFromDF(self, dataFrame):
        for i, row in dataFrame.iterrows():
            widget = row[_WidgetsHeader]
            widget.set(str(row[_ValuesHeader]))
        additionalSIValues = dataFrame[_AdditionalValuesHeader].values
        if len(additionalSIValues)>0:
            vv = additionalSIValues[0]
            additionalSIValue = str(vv) if vv is not None else ''
            self.additionalValueEditor.setText(additionalSIValue)

    def _reorderSpectraBySeries(self, ascending=True):
        """
        Sort on-the-fly all widgets based on Series lineEdit values.
        To sort a spectrumGroup object by Series (using the terminal), use the method
        "SpectrumGroup > sortSpectraBySeries() "
        """
        selType = self.seriesUnitWidget.getType()
        isNumericTab = selType == SeriesTypes.INTEGER.description or selType == SeriesTypes.FLOAT.description

        df = self._getDFfromSeriesWidgets()
        if isNumericTab:  # set _ValuesHeader to numeric and ignore potential errors (empty boxes, or str conversion)
            df[_ValuesHeader] = pd.to_numeric(df[_ValuesHeader], errors='coerce')  #  errors='coerce' is essential here!
        sortedDf = df.sort_values(by=_ValuesHeader, ascending=ascending)  # do sorting
        self._applyNewValuesFromDF(sortedDf)
        self._parent._groupedObjects =  sortedDf[_PidsHeader].values.tolist()


    # Some convinient actions
    def _convertSeriesToSiUnits(self, *args):
        quantity = self.seriesUnitWidget.getQuantity()
        selectedUnit = self.seriesUnitWidget.getUnit()
        unitCls = SERIESUNITS.get(quantity)
        df = self._getDFfromSeriesWidgets()
        if quantity == GENERIC:
            return
        siValues = []
        additionalSIValues = []
        baseUnit = unitCls.SI_baseUnit
        if unitCls is not None:
            values = pd.to_numeric(df[_ValuesHeader], errors='coerce')  #  errors='coerce' is essential here!
            additionalValues = pd.to_numeric(df[_AdditionalValuesHeader], errors='coerce')  #  errors='coerce' is essential here!
            for value, additionalValue  in zip(values, additionalValues):
                unitObj = unitCls(value, selectedUnit)
                addUnitObj = unitCls(additionalValue, selectedUnit)
                siValues.append(unitObj.toSI())
                additionalSIValues.append(addUnitObj.toSI())
        df[_ValuesHeader] = siValues
        df[_AdditionalValuesHeader] = additionalSIValues
        self._applyNewValuesFromDF(df)
        self.seriesUnitWidget.setUnit(baseUnit)
        self._toggleConversionButton()


    def _seriesUnitWidgetCallback(self, *args):
        self._toggleConversionButton()
        unitTxt = self.seriesUnitWidget.getUnit()

    def _toggleConversionButton(self, *args):
        quantity = self.seriesUnitWidget.getQuantity()
        if quantity == GENERIC:
            self._convertButtons.setEnabled(False)
            return
        enable = False
        selectedUnit = self.seriesUnitWidget.getUnit()
        unitClass = SERIESUNITS.get(quantity)
        if unitClass is not None:
            baseUnit = unitClass.SI_baseUnit
            enable = baseUnit != selectedUnit # don't enable if the selected is already a Base Unit
        self._convertButtons.setEnabled(enable)

    def _setValueFromSpectrumProperty(self, selection):

        propertyOption = FILLING_BY_PROPERTIES.get(selection)
        if propertyOption is None:
            return
        callback = propertyOption.get('callback')
        if callback is None:
            return
        df = self._getDFfromSeriesWidgets()
        if len(df)==0:
            return
        pids = df[_PidsHeader].values
        spectra = [self.application.project.getByPid(x) for x in pids]
        if len(spectra)==0:
            return
        values = callback(spectra)
        for i, (index, row) in enumerate(df.iterrows()):
            value = values[i]
            widget = row[_WidgetsHeader]
            widget.set(str(value))
        # do the units selections
        vv = {QUANTITY:propertyOption.get(QUANTITY),
              TYPE:propertyOption.get(TYPE),
              UNIT:propertyOption.get(UNIT)}

        if selection == 'Clear All':
            self.seriesUnitWidget.deselectAll()
        else:
            self.seriesUnitWidget.setValues(vv)
        self._allUnitsOptionsChanged(self.seriesUnitWidget, self.defaultObject)
        self._parent._applyButton.setEnabled(True)
        self._fiilBySpectrumPropertyPulldown.select(SELECT, blockSignals=True) # revert selection to the header
        self._toggleConversionButton()


    def _setSeriesOptionsEnabled(self, _bool):
        self._seriesEnabled = _bool
        for frame in self._operationFrames:
            frame.setEnabled(_bool)
        self._seriesFrame.setVisible(_bool)


    def _fillSeriesFrame(self, defaultItems, spectrumGroup=None):
        """Reset the contents of the series frame for changed spectrum list
        """
        if not self._seriesEnabled:
            return
        # remove previous editor values
        for spec, editor in self._editors.items():
            editor.textChanged.disconnect()
            self._currentSeriesValues[spec] = editor.get()

        self._changes.clear()
        self._editors = OrderedDict()
        self.defaultObject = spectrumGroup

        with self._changes.blockChanges():
            # empty the frame
            if self._seriesFrame:
                self._seriesFrame.hide()
                self._seriesFrame.deleteLater()

            self._seriesFrame = Frame(self._seriesValuesFrame, setLayout=True, showBorder=False,
                                      grid=(self._seriesValuesFrameRow, self._seriesValuesFrameCol), gridSpan=self._mainLayoutGridSpan,
                                      vAlign='t')
            self.getLayout().setAlignment(QtCore.Qt.AlignTop)
            # add new editors with the new values
            for sRow, spec in enumerate(defaultItems):
                seriesLabel = Label(self._seriesFrame, text=spec.pid, grid=(sRow, 0), vAlign='t', minimumWidth=self.labelMinimumWidth)
                seriesLabel.setFixedHeight(30)

                editorFrame = Frame(self._seriesFrame, setLayout=True, grid=(sRow, 1), vAlign='t')
                seriesEditor = PlainTextEditor(editorFrame, grid=(0, 0), fitToContents=True, minimumWidth=self.labelMinimumWidth)
                seriesEditor.setMinimumSize(50, 25)

                # attributes for setting size when using resize-grip
                seriesEditor._minimumWidth = 50
                seriesEditor._minimumHeight = 25
                seriesEditor.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

                if spec in self._currentSeriesValues and self._currentSeriesValues[spec] is not None:
                    # print('filling seriesEditor value: %s' % self._currentSeriesValues[spec])
                    seriesEditor.set(self._currentSeriesValues[spec])

                # add the callback after setting the initial values
                seriesEditor.textChanged.connect(partial(self._queueChangeSpectrumSeriesValues,
                                                         seriesEditor, self.defaultObject,
                                                         spec, sRow))

                self._editors[spec] = seriesEditor

        self._seriesFrame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

    def _populateSeries(self):
        """Populate the texteditors - seriesValues and seriesUnits for the spectrumGroup
        """
        if not self._seriesEnabled:
            return
        if self.defaultObject:
            with self._changes.blockChanges():
                seriesType = self.defaultObject.seriesType
                seriesTypeAsString = ''
                if seriesType is not None:
                    seriesTypeData = SeriesTypes(seriesType)
                    seriesTypeAsString = seriesTypeData.description

                vv = {QUANTITY: self.defaultObject.seriesQuantity,
                      UNIT: self.defaultObject.seriesUnits,
                      TYPE: seriesTypeAsString
                      }

                self.seriesUnitWidget.setValues(vv)
                self._spectrumGroupSeriesQuantityEdited = self.defaultObject.seriesQuantity
                self._spectrumGroupSeriesUnitsEdited = self.defaultObject.seriesUnits
                self._spectrumGroupSeriesTypeEdited = self.defaultObject.seriesType

                series = self.defaultObject.series
                if series:
                    for spec, textEditor in self._editors.items():
                        try:
                            ii = self.defaultObject.spectra.index(spec)
                        except:
                            pass
                        try:
                            if self.seriesUnitWidget.getType() == SeriesTypes.FLOAT.description:
                                seriesValue = float(series[ii])
                            elif self.seriesUnitWidget.getType() == SeriesTypes.INTEGER.description:
                                seriesValue = int(series[ii])
                            elif self.seriesUnitWidget.getType()  == SeriesTypes.STRING.description:
                                seriesValue = str(series[ii])
                            elif series[ii] in [None, np.nan, '', ' ']:
                                seriesValue = ''
                            else:
                                seriesValue = repr(series[ii])
                        except Exception as es:
                            textEditor.set('')
                        else:
                            # print('populating textEditor value: %s' % seriesValue)
                            textEditor.set(str(seriesValue))
            # add the additional Series values
            additionalSeries = self.defaultObject.additionalSeries
            ## keep only the first global value for now.
            additionalValue = additionalSeries[0][0] if additionalSeries and additionalSeries[0] else ''
            if additionalValue is None:
                additionalValue = ''
            self.additionalValueEditor.setText(str(additionalValue))
        self._validateEditors()

    def _getValuesFromTextEdit(self):
        # read the values from the textEditors and put in dict for later
        for spec, editor in self._editors.items():
            self._currentSeriesValues[spec] = editor.get()

    def _cleanSpacers(self, widget):
        # remove unneeded spacers
        layout = widget.getLayout()
        spacers = [layout.itemAt(itmNum) for itmNum in range(layout.count()) if isinstance(layout.itemAt(itmNum), Spacer)]
        for sp in spacers:
            layout.removeItem(sp)

    @queueStateChange(_verifyPopupApply)
    def _queueChangeAdditionalSeriesValues(self,  editor, spectrumGroup, *args, **kwargs):
        # TODO need to add the validator as in the main series
        value = editor.getText()
        if value in ['', ' ', None, np.nan]:
            additionalSeriesValues = None
        else:
            additionalSeriesValues = self._parent.convertListToProperType(tuple(value,))

        ##  In the initial implementation, all spectra additional Values in series are the same. e.g. the global protein concentration in a titration
        spectrum = spectrumGroup.spectra[0]
        specValues = spectrum._getAdditionalSeriesItems(spectrumGroup.pid) if spectrumGroup else None

        if additionalSeriesValues != specValues:
            return partial(self._changeSpectrumAdditionalSeriesValues, spectrumGroup, additionalSeriesValues)



    @queueStateChange(_verifyPopupApply)
    def _queueChangeSpectrumSeriesValues(self, editor, spectrumGroup, spectrum, dim):
        # queue the value if has changed from the original
        value = editor.get()
        try:
            if self.seriesUnitWidget.getType() == SeriesTypes.FLOAT.description:
                seriesValue = float(value)
            elif self.seriesUnitWidget.getType() == SeriesTypes.INTEGER.description:
                seriesValue = int(value)
            elif self.seriesUnitWidget.getType() == SeriesTypes.STRING.description:
                seriesValue = str(value)
            else:
                seriesValue = literal_eval(value)

        except Exception as es:
            # return partial(self._changeSpectrumSeriesValues, spectrumGroup, spectrum, dim, ERRORSTRING)
            pass

        else:
            specValue = spectrum._getSeriesItemsById(spectrumGroup.pid) if spectrumGroup else None
            if seriesValue != specValue:
                return partial(self._changeSpectrumSeriesValues, spectrumGroup, spectrum, dim, seriesValue)

        finally:
            self._validateEditors()

    def _validateEditors(self):
        """Check that all the editors contain the same type of seriesValues
        """
        errorState = False
        errorDict = False
        heightSum = 0.0
        literalTypes = set()
        literalDictCompare = None
        seenValues = []
        for editor in self._editors.values():
            value = editor.get()
            seenValues.append(value)
            palette = editor.viewport().palette()
            colour = editor._background
            try:
                seriesValue = None
                if self.seriesUnitWidget.getType() == SeriesTypes.FLOAT.description:
                    seriesValue = float(value)
                elif self.seriesUnitWidget.getType() == SeriesTypes.INTEGER.description:
                    seriesValue = int(value)
                elif self.seriesUnitWidget.getType() == SeriesTypes.STRING.description:
                    seriesValue = str(value)
                else:
                    seriesValue = literal_eval(value)
                    literalTypes.add(type(seriesValue))

                    # compare whether the dicts contain the same keys - not essential
                    if not literalDictCompare:
                        literalDictCompare = seriesValue
                    else:
                        if isinstance(literalDictCompare, dict) and isinstance(seriesValue, dict):
                            cmp = _compareDict(literalDictCompare, seriesValue)
                            if not cmp:
                                colour = INVALIDROWCOLOUR
                                errorDict = True

            except Exception as es:
                # catch exception raised by bad literals
                colour = INVALIDROWCOLOUR
                errorState = True

            finally:
                if literalTypes and len(literalTypes) > 1:
                    colour = INVALIDROWCOLOUR
                    errorState = True

                palette.setColor(editor.viewport().backgroundRole(), colour)
                editor.viewport().setPalette(palette)

            # rowHeight = QtGui.QFontMetrics(editor.document().defaultFont()).height()
            # lineCount = editor.document().lineCount()
            #
            # minHeight = (rowHeight + 1) * (lineCount + 1)
            # height = max(editor._minimumHeight, minHeight)
            # heightSum += height
            # editor.setMaximumHeight(height)
            # editor.updateGeometry()

        # if they are all empty then is a VALID state
        if all(item == '' for item in seenValues):
            errorState = False
            for editor in self._editors.values():
                palette = editor.viewport().palette()
                colour = editor._background
                palette.setColor(editor.viewport().backgroundRole(), colour)
                editor.viewport().setPalette(palette)
            self._parent._applyButton.setEnabled(True)
        self._errorFrameSeriesValues.setVisible(errorState)

    def _changeSpectrumSeriesValues(self, spectrumGroup, spectrum, dim, value):
        # set the spectrum series value from here
        # spectrum.seriesValue = value
        # bit of a hack here - called by _groupInit which builds the spectrumGroup series
        self._parent._spectrumGroupSeriesEdited[dim] = value

    def _changeSpectrumAdditionalSeriesValues(self, spectrumGroup, additionalSeriesValues):
        """
        :param spectrumGroup:
        :param additionalSeriesValues:  tuple of tuples
        :return:
        """
        ## careful here. An initial hack to allow only one glbal additional series value per spectrumGroup
        for i, sp in enumerate(spectrumGroup.spectra):
            self._parent._spectrumGroupAdditionalSeriesValues[i] = additionalSeriesValues

    @queueStateChange(_verifyPopupApply)
    def _queueChangeSeriesUnits(self, editor, spectrumGroup, *args, **kwargs):
        """callback from editing the seriesUnits - respond to every keypress
        """
        if spectrumGroup is None:
            return
        value = editor.getUnit()
        specValue = spectrumGroup.seriesUnits
        if value != specValue:
            return partial(self._changeSeriesUnits, spectrumGroup, value)

    def _changeSeriesUnits(self, spectrumGroup, value):
        """set the spectrumGroup seriesUnits
        """
        self._parent._spectrumGroupSeriesUnitsEdited = value

    @queueStateChange(_verifyPopupApply)
    def _queueChangeSeriesQuantity(self, editor, spectrumGroup, *args, **kwargs):
        """callback from editing the seriesQuantity - respond to every keypress
        """
        value = editor.getQuantity()
        if spectrumGroup is None:
            return
        specValue = spectrumGroup.seriesQuantity
        if value != specValue:
            return partial(self._changeSeriesQuantity, spectrumGroup, value)

    def _changeSeriesQuantity(self, spectrumGroup, value):
        """set the spectrumGroup seriesUnits
        """
        self._parent._spectrumGroupSeriesQuantityEdited = value

    def _getChangeState(self):
        """Get the change state from the parent widget
        """
        return self._parent._getChangeState()

    @queueStateChange(_verifyPopupApply)
    def _queueChangeSeriesType(self, editor, spectrumGroup, *args, **kwargs):
        """callback from editing the seriesType
        """
        if spectrumGroup is None:
            return
        self._validateEditors()
        dataType = self.seriesUnitWidget.getType()
        specType = spectrumGroup.seriesType

        if dataType is None and dataType != specType:
            return partial(self._changeSeriesType, spectrumGroup, None)

        descriptions = SeriesTypes.descriptions()
        if dataType in descriptions:
            typeCode = descriptions.index(dataType)
            if typeCode != specType:
                return partial(self._changeSeriesType, spectrumGroup, typeCode)

    def _changeSeriesType(self, spectrumGroup, typeCode):
        """
        set the spectrumGroup seriesType
        :param spectrumGroup:
        :param typeCode: int,  see SeriesTypes
        :return: None
        """

        self._parent._spectrumGroupSeriesTypeEdited = typeCode

    # @queueStateChange(_verifyPopupApply)
    def _allUnitsOptionsChanged(self, editor, spectrumGroup, *args, **kwargs):
        ## change the states for the varies property
        ## check if there are series values and if yes, add error to specify the units
        self._queueChangeSeriesQuantity(self.seriesUnitWidget, self.defaultObject)
        self._queueChangeSeriesUnits(self.seriesUnitWidget, self.defaultObject)
        self._queueChangeSeriesType(self.seriesUnitWidget, self.defaultObject)
        self._validateEditors()


    @queueStateChange(_verifyPopupApply)
    def _queueChangeName(self, _value):
        """callback from editing the name
        """
        editName = self._parent.nameEdit.text()
        defaultName = self._parent._defaultName

        if editName != defaultName:
            return partial(self._changeName, editName)

    def _changeName(self, value):
        """set the spectrumGroup
        """
        # doesn't need to do anything, just insert an item into the revert _changes dict
        pass

    @queueStateChange(_verifyPopupApply)
    def _queueChangeComment(self, _value):
        """callback from editing the comment
        """
        editComment = self._parent.commentEdit.text() or None
        defaultComment = self._parent._defaultComment

        if editComment != defaultComment:
            return partial(self._changeComment, editComment)

    def _changeComment(self, value):
        """set the spectrumGroup
        """
        # doesn't need to do anything, just insert an item into the revert _changes dict
        pass

    @queueStateChange(_verifyPopupApply)
    def _queueChangeSpectrumList(self):
        """callback from changing the spectra in the list
        """
        pidList = self._parent._groupedObjects
        defaultList = self._parent._defaultSpectra

        if pidList != defaultList:
            return partial(self._changeSpectrumList, pidList)

    def _changeSpectrumList(self, value):
        """set the spectra in the spectrumGroup
        """
        # doesn't need to do anything, just insert an item into the revert _changes dict
        pass


class _SpectrumGroupContainer(AttrDict):
    """
    Class to simulate a spectrumGroup in popup.
    """

    def __init__(self):
        super(_SpectrumGroupContainer, self).__init__()
        self.pid = id(self)
        self.spectra = []
        self._modifiedSpectra = set()
        self._setDefaultSeriesValues()
        self._seriesUnits = None
        self._seriesQuantity = None
        self._seriesType = 0

    @property
    def series(self) -> Tuple[Any, ...]:
        """Returns a tuple of series items for the attached spectra

        series = (val1, val2, ..., valN)

        where val1-valN correspond to the series items in the attached spectra associated with this group
        For a spectrum with no values, returns None in place of Item

        Duplicated from spectrumGroup.series
        """
        series = ()
        for spectrum in self.spectra:
            series += (spectrum._getSeriesItemsById(self.pid),)

        return series

    @property
    def additionalSeries(self) -> Tuple[Any, ...]:
        """Returns a tuple of additional series items for the attached spectra

        series = ((val1, val2, ..., valN), ...  )

        where (val1-valN) correspond to the series items in the attached spectra associated with this group
        For a spectrum with no values, returns None in place of Item
         Duplicated from spectrumGroup.additionalSeries
        """
        result = [sp._getAdditionalSeriesItems(self) for sp in self.spectra]
        return tuple(result)

    @property
    def seriesUnits(self):
        """Return the seriesUnits for the simulated spectrumGroup
        """
        return self._seriesUnits

    @property
    def seriesQuantity(self):
        """Return the seriesQuantity for the simulated spectrumGroup
        """
        return self._seriesQuantity

    @property
    def seriesType(self):
        """Return the type for seriesValues widget entry
        """
        return self._seriesType

    def _setDefaultSeriesValues(self):
        for spec in self.spectra:
            spec._setSeriesItemsById(self.pid, None)

    def _removeDefaultSeriesValues(self):
        for spec in self.spectra:
            spec._removeSeriesItemsById(self.pid)

    def __del__(self):
        """destructor required to cleanup ids in altered spectra
        """
        self._removeDefaultSeriesValues()
