"""
This module contains the code for the ValidateSpectra popup
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
__dateModified__ = "$dateModified: 2024-09-13 15:20:23 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-02-04 11:28:53 +0000 (Thu, February 04, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import OrderedDict

from PyQt5 import QtGui

from ccpn.core.lib.DataStore import DataRedirection, DataStore, PathRedirections
from ccpn.util.Path import aPath, Path
from ccpn.util.Logging import getLogger

from ccpn.framework.constants import UNDEFINED_STRING

from ccpn.core.lib.SpectrumDataSources.EmptySpectrumDataSource import EmptySpectrumDataSource
from ccpn.core.lib.SpectrumDataSources.SpectrumDataSourceABC import getDataFormats
from ccpn.core.lib.SpectrumLib import getSpectrumDataSource

from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.FileDialog import SpectrumFileDialog, OtherFileDialog
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import ValidatedLineEdit
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.CheckBox import CheckBox

from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showOkCancel
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame

from ccpn.ui.gui.guiSettings import COLOUR_BLIND_LIGHTGREEN, COLOUR_BLIND_MEDIUM, COLOUR_BLIND_DARKGREEN, \
    COLOUR_BLIND_RED, COLOUR_BLIND_ORANGE


EMPTY = EmptySpectrumDataSource.dataFormat
VALID_ROWCOLOUR = COLOUR_BLIND_LIGHTGREEN
VALID_CHANGED_ROWCOLOUR = COLOUR_BLIND_DARKGREEN
WARNING_ROWCOLOUR = COLOUR_BLIND_MEDIUM
INVALID_ROWCOLOUR = COLOUR_BLIND_RED
INVALID_CHANGED_ROWCOLOUR = COLOUR_BLIND_ORANGE

LIGHTGREY = QtGui.QColor('lightgrey')


#=========================================================================================
# PathRowABC
#=========================================================================================

class PathRowABC(object):
    """Implements all functionality for a row with label, text and button to select a file path
    """

    dialogFileMode = 1

    LABEL_COLLUMN = 0
    DATA_COLLUMN = 1
    BUTTON_COLLUMN = 2

    def __init__(self, parentWidget, rowIndex, labelText, obj, enabled=True, callback=None):
        """
        :param parentWidget: widget for row to be inserted
        :param labelText: text for the label; ignored if None or zero length
        :param rowIndex: row index
        :param obj: object being displayed
        :param callback: func(self) is called when changing value of the dataWidget
        """
        # if self.validatorClass is None:
        #     raise NotImplementedError('Define %s.validatorClass' % self.__class__.__name__)

        self.labelText = labelText
        self.obj = obj
        self.enabled = enabled
        self._callback = callback  # callback for this row upon change of value /validate()
        # is defined called as: callback(self)

        self.rowIndex = None  # Undefined; set by _addRowWidgets

        self.isValid = True
        self.errorString = ''  # To be set by checkValid method
        self.hasWarning = False
        self.validator = None  # validator instance of type self.validatorClass

        self.initialValue = self.getPath()

        self.labelWidget = None
        self.dataWidget = None
        self.buttonWidget = None

        self.initDone = False  # This will silence the validation
        with parentWidget.blockWidgetSignals():
            self._addRowWidgets(parentWidget=parentWidget, rowIndex=rowIndex)
            # self.revert()  # sets initial values to widgets
        self.initDone = True
        # self.validate()

    @property
    def text(self) -> str:
        """:return the text content of the dataWidget
        """
        return self.getText()

    @text.setter
    def text(self, value):
        self.setText(value)

    @property
    def hasChanged(self) -> bool:
        """:return True if the text value has changed
        """
        return (self.initialValue != self.text)  #and not self._firstTime

    @property
    def isNotValid(self) -> bool:
        return not self.isValid

    def _addRowWidgets(self, parentWidget, rowIndex):
        """Add widgets for the row to parentWidget
        :return self
        """
        self.rowIndex = rowIndex
        if self.labelText is not None and len(self.labelText) > 0:
            self.labelWidget = Label(parentWidget, text=self.labelText, grid=(self.rowIndex, self.LABEL_COLLUMN),
                                     hAlign='left',
                                     hPolicy='minimum',
                                     )
        else:
            self.labelWidget = None

        self.dataWidget = ValidatedLineEdit(parentWidget, textAlignment='left',
                                            backgroundText=UNDEFINED_STRING,
                                            grid=(self.rowIndex, self.DATA_COLLUMN),
                                            # hAlign='left',  # breaks the expanding of widget
                                            hPolicy='minimumExpanding',
                                            validatorCallback=self.validatorCallback
                                            )

        if not self.enabled:
            _font = self.dataWidget.font()
            _font.setItalic(True)
            self.dataWidget.setFont(_font)
            self.dataWidget.setReadOnly(True)
            # self.setColour(LIGHTGREY)

        self.buttonWidget = Button(parentWidget, grid=(self.rowIndex, self.BUTTON_COLLUMN), callback=self._getDialog,
                                   hPolicy='fixed',
                                   icon='icons/directory')

        return self

    def _getDialog(self):

        dialogPath = self.getDialogPath()
        dialog = SpectrumFileDialog(parent=self.buttonWidget, acceptMode='select', directory=dialogPath)
        dialog._show()

        choices = dialog.selectedFiles()
        if choices is not None and len(choices) > 0 and len(choices[0]) > 0:
            newPath = choices[0]
            self.setText(newPath)

    def setEnabled(self, enable):
        """Enable or disable the row
        """
        if self.dataWidget is None:
            raise RuntimeError('No row widgets defined')

        self.enabled = enable
        if self.labelWidget:
            self.labelWidget.setEnabled(self.enabled)
        self.dataWidget.setEnabled(self.enabled)
        self.buttonWidget.setVisible(self.enabled)

    def setLabel(self, text):
        """Set the labelWidget to text
        """
        if self.labelWidget is None:
            raise RuntimeError('No label widget defined')
        self.labelWidget.setText(text)

    def getLabel(self, text) -> str:
        """:return the text of the labelWidget
        """
        if self.labelWidget is None:
            raise RuntimeError('No label widget defined')
        return self.labelWidget.text()

    def getText(self) -> str:
        """:return the text of the dataWidget (i.e. the path)
        """
        if self.dataWidget is None:
            raise RuntimeError('No data widget defined')
        return self.dataWidget.text()

    def setText(self, text):
        """Set the dataWidget to text"""
        if self.dataWidget is None:
            raise RuntimeError('No data widget defined')
        self.dataWidget.setText(text)

    def setPath(self, path):
        """Set the path name of the object;
        requires subclassing
        """
        pass

    def getPath(self) -> str:
        """Get the path name from the object to edit;
        requires subclassing
        """
        pass

    def getDialogPath(self) -> str:
        """Get the directory path to start the selection dialog;
        optionally can be subclassed
        """
        dirPath = Path.cwd()
        return str(dirPath)

    def update(self, path=None):
        """Set path, or get from widget;
        if self.isValid, call self.setPath with current widget value
        """
        if path is None:
            path = self.getText()
        else:
            self.setText(path)  # This also validates the path

        if self.isValid and self.initDone and self.hasChanged:  # This avoids setting on initialisation
            self.setPath(path)

    def revert(self):
        """Revert the widget to initial value;
        implicitly calls validator through the setText method
        """
        self.setText(self.initialValue)

    def checkValid(self, value) -> bool:
        """Routine for checking value is valid; called from validatorCallback and validate method
        should be sub-classed
        """
        raise NotImplementedError('checkValid method not implemented')

    def validatorCallback(self, value) -> bool:
        """Callback for the WidgetValidator instance and validate method;
        """
        if not self.initDone:
            return True

        self.hasWarning = False
        self.isValid = self.checkValid(value)

        if self._callback:
            self._callback(self)

        self.colourRow()

        return self.isValid

    def validate(self) -> bool:
        """Validate the current value of dataWidget of self (a row),
        :return True if valid or not initDone
        """
        if not self.initDone:
            return True
        value = self.dataWidget.get()
        return self.validatorCallback(value)

    def setColour(self, colour):
        """Set the (base) colour of the dataWidget
        """
        if isinstance(colour, str):
            colour = QtGui.QColor(colour)
        if not isinstance(colour, QtGui.QColor):
            raise ValueError('Invalid colour ("%s"' % colour)
        palette = self.dataWidget.palette()
        palette.setColor(QtGui.QPalette.Base, colour)
        self.dataWidget.setPalette(palette)

    def colourRow(self):
        """Set colours of enabled row depending on its state
        """
        if not self.enabled:
            return

        # row has a warning
        if self.hasWarning:
            self.setColour(WARNING_ROWCOLOUR)

        # row is valid
        elif self.isValid:
            if self.hasChanged:
                self.setColour(VALID_CHANGED_ROWCOLOUR)
            else:
                self.setColour(VALID_ROWCOLOUR)

        # row is not valid
        else:
            if self.hasChanged:
                self.setColour(INVALID_CHANGED_ROWCOLOUR)
            else:
                self.setColour(INVALID_ROWCOLOUR)

    def setVisible(self, visible):
        """set visibility of row
        """
        if self.labelWidget:
            self.labelWidget.setVisible(visible)

        self.dataWidget.setVisible(visible)
        self.buttonWidget.setVisible(visible)

    def __str__(self):
        return f'<{self.__class__.__name__} (V:{self.isValid}, W:{self.hasWarning}, C:{self.hasChanged}): {self.text}>'

    __repr__ = __str__


# end class


#=========================================================================================
# SpectrumPathRow
#=========================================================================================

class SpectrumPathRow(PathRowABC):
    """
    A class to implement a row for spectrum paths
    """
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    dialogFileMode = 1

    SELECT_COLLUMN = 0
    LABEL_COLLUMN = 1
    DATAFORMAT_COLLUMN = 2
    DATA_COLLUMN = 4
    BUTTON_COLLUMN = 5
    RELOAD_COLLUMN = 3
    REVERT_COLLUMN = 6

    AUTODETECT = '> Auto-detect <'

    def __init__(self, parentWidget, rowIndex, labelText, spectrum, enabled=True, callback=None,
                 addExtraButtons=False):
        """
        :param parentWidget: widget for row to be inserted
        :param labelText: text for the label
        :param rowIndex: row index
        :param spectrum: spectrum whose path is being displayed
        :param callback: func(self) is called when changing value of the dataWidget
        :param addExtraButtons: flag to add the extra buttons
        """

        self._addExtraButtons = addExtraButtons
        self.selectButton = None
        self.reloadButtonWidget = None
        self.dataFormatWidget = None
        self.revertButtonWidget = None

        self.initialDataFormat = spectrum.dataFormat
        self.dataStore = None
        self.dataSource = None

        super(SpectrumPathRow, self).__init__(parentWidget=parentWidget, rowIndex=rowIndex, labelText=labelText,
                                              obj=spectrum, enabled=enabled, callback=callback
                                              )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def checkValid(self, value) -> bool:
        """Routine for checking value is valid; called from validatorCallback and validate method
        """
        dataFormat = self.dataFormat  # This will get the value from the dataFormatWidget (if defined)
        # or from the spectrum otherwise

        # Check if path is valid for dataFormat.
        self.dataStore, self.dataSource = getSpectrumDataSource(path=value, dataFormat=dataFormat)

        self.errorString = ''
        self.hasWarning = False

        if dataFormat == EMPTY:
            # Empty dataFormat: special treatment;
            if len(value) == 0:
                # value can be empty, in which case dataStore is '.'
                isValid = True
            else:
                # Check if value exists
                if not (isValid := self.dataStore.exists()):
                    self.errorString = f'Path "{value}" does not exist'
                else:
                    self.hasWarning = True
                    self.errorString = f'Path "{value}" is ignored for Empty dataFormat'

        else:
            if self.dataSource is None:
                self.errorString = f'Path "{value}" does not define a valid SpectrumDataSource type'
                isValid = False

            elif self.dataSource.isNotValid or not self.dataSource.checkParameters(self.spectrum):
                self.errorString = self.dataSource.errorString
                isValid = False

            else:
                isValid = True

        return isValid

    def validatorCallback(self, value) -> bool:
        """Callback for the WidgetValidator instance and validate method;
        """
        if not self.initDone:
            return True

        super().validatorCallback(value)  # This will call checkValid above

        # add a tooltip text describing possible errors
        if not self.isValid or self.hasWarning:
            self.dataWidget.setToolTip(f'{self.errorString}')

        elif self.isValid:
            if self.hasChanged:
                self.dataWidget.setToolTip('Path has changed and is valid')
            else:
                self.dataWidget.setToolTip('Path is valid')

        else:
            self.dataWidget.setToolTip('')

        return self.isValid

    def _addRowWidgets(self, parentWidget, rowIndex):
        """Add widgets for the row to parentWidget
        returns self
        """
        self.initDone = False
        if self._addExtraButtons:
            self.selectButton = CheckBox(parent=parentWidget, grid=(rowIndex, self.SELECT_COLLUMN),
                                         callback=self._selectButtonCallback, hPolicy='fixed'
                                         )
            dataFormats = list(getDataFormats().keys())
            self.dataFormatWidget = PulldownList(parent=parentWidget, grid=(rowIndex, self.DATAFORMAT_COLLUMN),
                                                 texts=dataFormats, headerEnabled=True, headerText=self.AUTODETECT,
                                                 hPolicy='fixed',
                                                 callback=self._dataFormatCallback)
            self.reloadButtonWidget = Button(parent=parentWidget, icon='icons/redo', tipText='Auto detect dataFormat',
                                             grid=(rowIndex, self.RELOAD_COLLUMN),
                                             hPolicy='fixed',
                                             callback=self._reopenCallback)
            self.revertButtonWidget = Button(parent=parentWidget, icon='icons/revert', tipText='Revert dataFormat and path to original values',
                                             grid=(rowIndex, self.REVERT_COLLUMN),
                                             hPolicy='fixed',
                                             callback=self._revertCallback)

        super()._addRowWidgets(parentWidget=parentWidget, rowIndex=rowIndex)
        self.initDone = True  # Statement does not chnage anything as the super class has already reverted it;
        # Here for clarity

    def setVisible(self, visible):
        """set visibility of row
        """
        super().setVisible(visible=visible)
        if self.selectButton is not None:
            self.selectButton.setVisible(visible)
        if self.reloadButtonWidget is not None:
            self.reloadButtonWidget.setVisible(visible)
        if self.revertButtonWidget is not None:
            self.revertButtonWidget.setVisible(visible)
        if self.dataFormatWidget is not None:
            self.dataFormatWidget.setVisible(visible)

    def setEnabled(self, enable):
        """Enable the widgets
        """
        super().setEnabled(enable=enable)
        if self.selectButton is not None:
            self.selectButton.setEnabled(enable)
        if self.reloadButtonWidget is not None:
            self.reloadButtonWidget.setEnabled(enable)
        if self.revertButtonWidget is not None:
            self.revertButtonWidget.setEnabled(enable)
        if self.dataFormatWidget is not None:
            self.dataFormatWidget.setEnabled(enable)

    @property
    def spectrum(self):
        """:return The spectrum instance used for initialisation
        """
        return self.obj

    @property
    def dataFormat(self) -> str:
        """:return the value of the dataFormatWidget (if defined), with None if set to AUTODETECT
        If there is not dataFormat Widget, return dataFormat of the spectrumInstance
        """
        if self.dataFormatWidget is not None:
            dataFormat = self.dataFormatWidget.get()
            if dataFormat == self.AUTODETECT:
                dataFormat = None
        else:
            dataFormat = self.spectrum.dataFormat
        return dataFormat

    @dataFormat.setter
    def dataFormat(self, value):
        """Set the dataFormatWidget (if defined); change None to AUTODETECT
        """
        if self.dataFormatWidget is not None:
            if value is None:
                value = self.AUTODETECT
            self.dataFormatWidget.set(value)

    @property
    def isSelected(self):
        """Return the value of the selection button
        """
        return self.selectButton.get()

    @isSelected.setter
    def isSelected(self, value):
        """Set the value of the selection button
        """
        self.selectButton.set(value)

    @property
    def hasChanged(self) -> bool:
        """:return True if settings have changed
        """
        if self.dataFormatWidget is not None:
            return super().hasChanged or self.dataFormat != self.initialDataFormat
        else:
            return super().hasChanged

    def revert(self):
        """Revert to initial values
        """
        if self.dataFormatWidget is not None:
            self.dataFormat = self.initialDataFormat
        super().revert()

    def _selectButtonCallback(self, *args):
        """Callback when changing the selection button
        """
        # bid ugly, but use callback to determine if things need changing;
        # Do not want to use self.validate(), as this is potentially slow, and this callback from
        # the selectButton is going to be called often; e.g. when entering text in the search box
        self._callback(row=self)

    def _dataFormatCallback(self, dataFormat):
        """Callback when changing the dataFormat
        """
        self.validate()

    def _reopen(self, path, dataFormat=None) -> tuple:
        """Reopen path using dataFormat; examine for dataFormat if None
        :return a (dataStore, dataSource) tuple
        """
        dataStore, dataSource = getSpectrumDataSource(path=path, dataFormat=dataFormat)

        # check if we found something valid; if so, change the dataFormat
        if dataStore is not None and dataSource is not None and dataSource.isValid:
            self.dataFormat = dataSource.dataFormat

        return dataStore, dataSource

    def _reopenCallback(self):
        """Callback when pressing reload
        """
        _path = self.getText()
        if len(_path) == 0:
            showWarning(f'Auto-detect dataFormat for {self.obj.name}',
                        f'Undefined path'
                        )
            return

        ok = showOkCancel(f'Auto-detect dataFormat for {self.obj.name}',
                          f'This will try to open "{_path}" and determine the dataFormat')

        if not ok:
            return

        dataStore, dataSource = self._reopen(path=_path, dataFormat=None)

        if dataStore is not None and not dataStore.exists():
            showWarning(f'Auto-detect dataFormat for {self.obj.name}',
                        f'"{_path}" does not exist'
                        )

        elif dataSource is None:
            showWarning(f'Auto-detect dataFormat for {self.obj.name}',
                        f'Failed to detect valid dataFormat'
                        )

        elif dataSource is not None and not dataSource.isValid:
            showWarning(f'Auto-detect dataFormat for {self.obj.name}',
                        f'{dataSource.errorString}'
                        )

    def _revertCallback(self):
        """Callback when pressing revert/undo
        """
        self.revert()

    def getPath(self) -> str:
        """Get the filePath from spectrum
        """
        path = str(self.obj.filePath)
        if path == UNDEFINED_STRING:
            path = ''
        return path

    def setPath(self, path):
        """set the filePath of Spectrum"""
        # For speed reasons, we check if it any different from before, or was not valid to start with
        if self.hasChanged:
            try:
                self.spectrum._openFile(path=path, dataFormat=self.dataFormat)
            except Exception as es:
                getLogger().debug2(f'ignoring filePath, dataFormat error {es}')

    def getDialogPath(self) -> str:
        """Get the directory path to start the selection;
        traverse up the tree to find a valid directory
        """
        _path = self.obj.path.parent
        atRoot = False
        while not _path.exists() and not atRoot:
            atRoot = (_path.parent == _path.root)
            _path = _path.parent
        if atRoot:
            _path = aPath('~')
        return str(_path)


# end class


#=========================================================================================
# RedirectPathRow
#=========================================================================================

class RedirectPathRow(PathRowABC):
    """
    A class to implement a row for Redirection object
    """
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    dialogFileMode = 2

    def checkValid(self, value) -> bool:
        """return True is value is valid
        """
        filePath = aPath(value)
        isValid = filePath.exists() and filePath.is_dir()
        return isValid

    def getPath(self):
        return str(self.obj.path)

    def setPath(self, path):
        self.obj.path = path


# end class


# Radiobuttons
VALID_SPECTRA = 'valid'
INVALID_SPECTRA = 'invalid'
CHANGED_SPECTRA = 'changed'
WARNING_SPECTRA = 'warning'
EMPTY_SPECTRA = 'empty'
SELECTED_SPECTRA = 'selected'
ALL_SPECTRA = 'all'
buttons = (ALL_SPECTRA, VALID_SPECTRA, INVALID_SPECTRA, WARNING_SPECTRA,
           EMPTY_SPECTRA, CHANGED_SPECTRA, SELECTED_SPECTRA)

_showBorders = False  # for debugging


#=========================================================================================
# ValidateSpectraPopup
#=========================================================================================

class ValidateSpectraPopup(CcpnDialog):
    """
    Class to generate a popup to validate the paths of the (selected) spectra.
    """

    def __init__(self, parent=None, mainWindow=None, spectra=None,
                 title='Validate Spectra Paths', defaultSelected=ALL_SPECTRA, **kwds):

        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)
        self.setMinimumHeight(600)
        self.setMinimumWidth(1000)

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.application.project
        self.current = mainWindow.application.current
        self.preferences = self.application.preferences

        if spectra is None:
            self.spectra = self.project.spectra
        else:
            self.spectra = spectra

        self._defaultSelectedIndx = buttons.index(defaultSelected) \
            if defaultSelected in buttons else buttons.index(ALL_SPECTRA)

        self.redirectData = OrderedDict()  # dict with (redirection, RedirectPathRow) tuples
        self.spectrumData = OrderedDict()  # dict with (spectrum, SpectrumPathRow) tuples
        self.dataRow = None  # remember the $DATA row
        self._selectedRows = []  # Selected rows: a list of (spectrum, row) tuples; (filled later)
        self._foundRow = False  # Search found a row

        row = 0

        # TODO I think there is a QT bug here - need to set a dummy button first otherwise a click is emitted, will investigate
        rogueButton = Button(self, grid=(0, 0))
        rogueButton.hide()
        row += 1

        # Frames: Top containers in the popup

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Frame1: Path redirections inside a MoreLessFrame
        _f = MoreLessFrame(self, mainWindow=self.mainWindow,
                           name='Redirections', bold=True, showMore=True,
                           setLayout=True, grid=(row, 0),
                           frameMargins=(0, 5, 0, 5),
                           hPolicy='expanding',
                           )

        _frame1 = Frame(_f.contentsFrame, setLayout=True, grid=(0, 0), showBorder=_showBorders)
        self._populateFrame1(_frame1)
        row += 1

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Frame2: Spectra inside a MoreLessFrame
        _f = MoreLessFrame(self, mainWindow=self.mainWindow,
                           name='Spectra', bold=True, showMore=True,
                           setLayout=True, grid=(row, 0),
                           frameMargins=(0, 5, 0, 5),
                           hPolicy='expanding',
                           )
        _frame2 = Frame(_f.contentsFrame, setLayout=True, grid=(0, 0), showBorder=_showBorders,
                        # hAlignment='left', hPolicy='expanding',  # This messes up the various alignments
                        # vAlignment='top', vPolicy='expanding',
                        )
        self._populateFrame2(_frame2)
        row += 1

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Frame3: Path manipulations inside a MoreLessFrame
        _f = MoreLessFrame(self, mainWindow=self.mainWindow,
                           name='Search / Modify', bold=True, showMore=False,  # closed on default
                           setLayout=True, grid=(row, 0),
                           frameMargins=(0, 5, 0, 5),
                           hPolicy='expanding',
                           )
        _frame3 = Frame(_f.contentsFrame, setLayout=True, grid=(0, 0), showBorder=_showBorders,
                        hAlign='left', hPolicy='minimal',  # required to get alignment right
                        )
        self._populateFrame3(_frame3)
        row += 1

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # add exit buttons
        self.addSpacer(5, 15, grid=(row, 0))
        row += 1

        self.applyButtons = ButtonList(self,
                                       texts=['Cancel',
                                              'Apply and Close'],
                                       callbacks=[self._cancelButtonCallback,
                                                  self._closeButtonCallback],
                                       tipTexts=['Cancel and close',
                                                 'Apply changes and close the popup'],
                                       direction='h',
                                       hAlign='r', grid=(row, 0),
                                       vAlign='b',
                                       )

    def _populateFrame1(self, frame):
        """populate Frame1 with a list of spectrum buttons and filepath buttons
        """
        for idx, redirect in enumerate(PathRedirections()):
            _row = RedirectPathRow(parentWidget=frame, rowIndex=idx,
                                   obj=redirect,
                                   labelText=redirect.identifier,
                                   enabled=(idx == 0),
                                   callback=self._dataRowCallback)
            _row.revert()  # Will set initial values and validate
            if idx == 0:
                self.dataRow = _row  # remember the row for $DATA
            self.redirectData[redirect] = _row

    def _populateFrame2(self, frame):
        """Populate the Spectrum frame
        """
        specRow = 0

        # radiobuttons
        _bFrame = Frame(frame, setLayout=True, showBorder=_showBorders, fShape='noFrame',
                        grid=(specRow, 0),  #gridSpan=(1, _colSpan),
                        vAlign='top', hAlign='left'
                        )
        specRow += 1

        _bFrame.addSpacer(25, 40, grid=(0, 0))  # Clears the label and buttons from top of MoreLessFrame and
        # the stat of the spectrum scroll area with rows
        _l = Label(_bFrame, text="Show: ", grid=(0, 1), bold=False, hAlign='left')
        self.showValid = RadioButtons(_bFrame,
                                      texts=['%s  ' % b for b in buttons],  # hack to add some space!
                                      selectedInd=self._defaultSelectedIndx,
                                      callback=self._radiobuttonsCallback,
                                      direction='h',
                                      grid=(0, 2), hAlign='l',
                                      tipTexts=None,
                                      )

        # set up a scrolling frame
        self.scrollFrame = ScrollableFrame(frame, setLayout=True, showBorder=_showBorders,
                                           grid=(specRow, 0),
                                           hPolicy='expanding',
                                           vAlign='top', vPolicy='minimal')
        specRow += 1

        # populate the widget with a list of spectrum buttons and filepath buttons
        scrollRow = 0
        _colSpan = 6

        # Label(self.scrollFrame, text='Spectra', bold=True,
        #       grid=(scrollRow, SpectrumPathRow.LABEL_COLLUMN), hAlign='left')
        # Label(self.scrollFrame, text='dataFormat', bold=True,
        #       grid=(scrollRow, SpectrumPathRow.DATAFORMAT_COLLUMN), hAlign='centre')
        # Label(self.scrollFrame, text='Path', bold=True,
        #       grid=(scrollRow, SpectrumPathRow.DATA_COLLUMN), hAlign='centre')
        # scrollRow += 1

        for sp in self.project.spectra:
            # enabled = (not sp.isEmptySpectrum())
            _axisCodes = ','.join(sp.axisCodes)
            _row = SpectrumPathRow(parentWidget=self.scrollFrame,
                                   rowIndex=scrollRow,
                                   labelText=f'{sp.pid}  ({sp.dimensionCount}D: {_axisCodes})',
                                   spectrum=sp, enabled=True,
                                   callback=self._spectrumRowCallback,
                                   addExtraButtons=True,
                                   )
            _row.revert()  # Will set initial values and validate
            scrollRow += 1
            self.spectrumData[sp] = _row
            self._selectedRows.append((sp, _row))

    def _populateFrame3(self, frame):
        """Populate the third frame with path manipulations
        """
        mlRow = 0
        _lWidth = 120

        _l = Label(frame, text='DataFormat(s)', grid=(mlRow, 0), hAlign='left')

        _b = Button(frame, text='Auto-detect', icon='icons/redo', grid=(mlRow, 1),
                    callback=self._reopenAllCallback,
                    tipText='Re-open all path(s), determining and setting dataFormat',
                    hAlign='left', hPolicy='minimal', minimumWidth=150)
        mlRow += 1

        _l = Label(frame, text='Path(s)', grid=(mlRow, 0),
                   hAlign='left', hPolicy='minimal')

        _b = ButtonList(frame,
                        texts=['Make absolute', 'Make relative', 'Revert'],
                        # icons=[None, None, 'icons/revert'],  # looks ugly
                        callbacks=[self._makeAbsoluteCallback,
                                   self._makeRelativeCallback,
                                   self._revertButtonCallback,
                                   ],
                        tipTexts=['Expand any redirections into an absolute path',
                                  'Reduce an absolute path into a relative path using redirections',
                                  'Revert to initial path',
                                  ],
                        setLastButtonFocus=False,
                        direction='h',
                        grid=(mlRow, 1), gridSpan=(1, 1),
                        hAlign='left', hPolicy='minimal'
                        )
        mlRow += 1

        #-------- Search and replace
        _l = Label(frame, text='Search', grid=(mlRow, 0), hAlign='left', hPolicy='minimal')
        # _l.setFixedWidth(_lWidth)

        minWidth = 250
        _sFrame = Frame(frame, setLayout=True, showBorder=_showBorders,
                        grid=(mlRow, 1), gridSpan=(1, 1),
                        hAlign='left', hPolicy='minimal'
                        )
        sRow = 0
        mlRow += 1

        self.seachLine = ValidatedLineEdit(_sFrame, grid=(sRow, 1), minimumWidth=minWidth,
                                           backgroundText='> Enter text <',
                                           validatorCallback=self._validateSearchCallback
                                           )
        self.seachLine.setClearButtonEnabled(True)

        self.replaceLabel = Label(_sFrame, text='Replace with', grid=(sRow, 2))
        self.replaceLine = ValidatedLineEdit(_sFrame, grid=(sRow, 3), minimumWidth=minWidth,
                                             backgroundText='> Enter text <',
                                             validatorCallback=self._validateReplaceCallback
                                             )
        self.replaceLine.setClearButtonEnabled(True)

        self.directoryButton = Button(_sFrame, grid=(sRow, 4), callback=self._getDirectoryCallback,
                                      icon='icons/directory')

        self.goButton = Button(_sFrame, text='Go', grid=(sRow, 5), callback=self._goButtonCallback, minimumWidth=50)
        sRow += 1
        #-------- End search and replace

    def _makeAbsoluteCallback(self):
        """Callback for make absolute button; converts all paths of visible rows
        to absolute paths
        """
        for sp, row in self._selectedRows:
            _path = row.getText()
            if len(_path) > 0:
                ds = DataStore.newFromPath(path=_path, autoRedirect=True)
                row.setText(ds.aPath().asString())

    def _makeRelativeCallback(self):
        """Callback for make relative button; converts all paths of visible rows to relative paths
        """
        for sp, row in self._selectedRows:
            _path = row.getText()
            if len(_path) > 0:
                ds = DataStore.newFromPath(path=_path, autoRedirect=True)
                row.setText(ds.path.asString())

    def _reopenAllCallback(self):
        """Callback for reopen all of visible rows
        """
        for sp, row in self._selectedRows:
            _path = row.getText()
            if len(_path) > 0:
                row._reopen(path=_path)

    def _getDirectoryCallback(self):
        """Callback when pressing directory button
        """
        dialog = OtherFileDialog(parent=self, acceptMode='select')
        dialog._show()

        choices = dialog.selectedFiles()
        if choices is not None and len(choices) > 0 and len(choices[0]) > 0:
            value = choices[0]
            self.replaceLine.setText(value)

    def _validateReplaceCallback(self, value):
        """Callback when the value of the replace line changes
        """
        # self._foundRow is True if the search line has some valid text
        replaceText = self.replaceLine.get()
        self.goButton.setEnabled(self._foundRow and len(replaceText) > 0)

    def _validateSearchCallback(self, value):
        """Callback when the value of the search line changes;
        set selection of all rows matching value
        """
        searchText = self.seachLine.get()
        _lText = len(searchText) > 0

        self._foundRow = False
        for spectrum, row in self._selectedRows:
            path = row.getText()
            if _lText and (idx := path.find(searchText)) >= 0:
                row.dataWidget.setSelection(idx, len(searchText))
                row.isSelected = True
                self._foundRow = True
            else:
                row.dataWidget.setSelection(0, 0)
                row.isSelected = False
            self._showRow(row)

        replaceText = self.replaceLine.get()
        self.goButton.setEnabled(self._foundRow and len(replaceText) > 0)

    def _goButtonCallback(self):
        """Callback when pressing the go button on Search and replace; apply to visible rows
        """
        searchText = self.seachLine.get()
        replaceText = self.replaceLine.get()
        if len(searchText) == 0 or len(replaceText) == 0:
            return

        for sp, row in self._selectedRows:
            _path = row.getText()
            newPath = _path.replace(searchText, replaceText, 1)
            if newPath != _path:
                # we replaced some text, update and validate the widgets
                row.setText(newPath)

    def _radiobuttonsCallback(self):
        """Toggle rows on or off depending on their state and the settings of the radio buttons
        Callback for the radio buttons
        """
        self._selectedRows = []
        for spectrum, row in self.spectrumData.items():
            if self._doShow(row):
                row.setVisible(True)
                self._selectedRows.append((spectrum, row))
            else:
                row.setVisible(False)

    def _doShow(self, row) -> bool:
        """:return True if row should be shown
        """
        doShow = False
        # hasChanged = row.hasChanged
        # isValid = row.isValid
        # hasWarning = row.hasWarning
        # dataFormat = row.dataFormat

        if hasattr(self, 'showValid') and self.showValid is not None:  # just checking that the widget exist
            # (not the case on initialisation!)
            doShow = False
            ind = self.showValid.getIndex()
            if ind == buttons.index(CHANGED_SPECTRA) and row.hasChanged:  # show only changed
                doShow = True
            elif ind == buttons.index(WARNING_SPECTRA) and row.hasWarning:  # show only warning
                doShow = True
            elif ind == buttons.index(SELECTED_SPECTRA) and row.isSelected:  # show Empty spectra
                doShow = True
            elif ind == buttons.index(EMPTY_SPECTRA) and row.dataFormat == EMPTY:  # show Empty spectra
                doShow = True
            elif ind == buttons.index(VALID_SPECTRA) and row.isValid and not row.hasWarning:  # show only valid
                doShow = True
            elif ind == buttons.index(INVALID_SPECTRA) and row.isNotValid and not row.hasWarning:  # show only invalid
                doShow = True
            elif ind == buttons.index(ALL_SPECTRA):  # show all
                doShow = True
        return doShow

    def _showRow(self, row):
        """show row depending on isValid, hasChanged of row and settings of radio buttons
        """
        doShow = self._doShow(row)
        row.setVisible(doShow)

    def _spectrumRowCallback(self, row):
        """
        Callback used for spectrum rows
        Modify colours of $DATA and Empty spectrum rows
        Toggle row on or off depending on its state and the settings of the radio buttons
        :param row: SpectrumPathRow instance
        """

        # Special case: set WARNING for the rows starting with $DATA if not correct
        if row.text.startswith(DataRedirection().identifier) \
                and self.dataRow is not None and self.dataRow.isNotValid:
            row.isValid = False
            row.hasWarning = True
            row.errorString = f'Path might be invalid because $DATA is not valid'

        _lPath = (len(row.getText()) > 0)  # non-empty path
        dataFormat = row.dataFormat

        row.colourRow()  # This needs to be here to function, but does not make sense as
        # row.validateCallback should do this too !?

        # Set state of reload button: path>0, exists and auto-detect
        if _lPath and row.dataStore.exists() and dataFormat is None:
            row.reloadButtonWidget.setEnabled(True)
        else:
            row.reloadButtonWidget.setEnabled(False)

        # set state of the revert button
        row.revertButtonWidget.setEnabled(row.hasChanged)

        self._showRow(row)

    def _dataRowCallback(self, dataRow):
        """Callback from $DATA url to validate all the spectrum rows as $DATA may have changed.
        """
        # Update the relevant SpectrumRows
        for spectrum, row in self.spectrumData.items():
            if row.text.startswith(DataRedirection().identifier):
                row.validate()

    def _revertButtonCallback(self):
        """Revert selected rows to initial settings
        """
        for spectrum, row in self._selectedRows:
            row.revert()

    def _cancelButtonCallback(self):
        """Cancel, i.e. no update and close popup
        """
        self.accept()

    def _closeButtonCallback(self):
        """Apply and close popup.
        DataRow and SpectrumRows still need updating
        """
        self.dataRow.update()

        for spectrum, row in self.spectrumData.items():
            row.update()

        self.accept()
