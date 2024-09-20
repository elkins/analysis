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
__dateModified__ = "$dateModified: 2024-04-22 13:20:12 +0100 (Mon, April 22, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-07-04 15:21:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore, QtGui
from contextlib import contextmanager, suppress
from dataclasses import dataclass

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.ui.gui.widgets.DialogButtonBox import DialogButtonBox
from ccpn.ui.gui.guiSettings import getColours
from ccpn.ui.gui.lib.ChangeStateHandler import ChangeDict
from ccpn.util.Logging import getLogger


def _updateGl(self, spectrumList):
    from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

    # # spawn a redraw-event of the contours
    # for spec in spectrumList:
    #     for specViews in spec.spectrumViews:
    #         specViews.buildContours = True

    GLSignals = GLNotifier(parent=self)
    GLSignals.emitPaintEvent()


HORIZONTAL = 'horizontal'
VERTICAL = 'vertical'
ORIENTATIONLIST = (HORIZONTAL, VERTICAL)
DEFAULTSPACING = 3
# DEFAULTMARGINS = (24, 8, 24, 18)
GETCHANGESTATE = '_getChangeState'
_DONTSHOWMESSAGE = "Don't show this again"
_DONTSHOWPOPUP = 'dontShowPopup'
_POPUPS = 'popups'

_DEBUG = False


class _DialogHook(type(QtWidgets.QDialog), type(Base)):
    """Metaclass implementing a post-initialise hook, ALWAYS called after __init__ has finished
    """

    def __call__(self, *args, **kwargs):
        if _DEBUG: getLogger().debug2(f'--> pre-create dialog {self}')
        instance = super().__call__(*args, **kwargs)
        # call the post-__init__ hook
        instance._postInit()
        if _DEBUG: getLogger().debug2(f'--> post-create dialog {self}')
        return instance


class CcpnDialogMainWidget(QtWidgets.QDialog, Base, metaclass=_DialogHook):
    """
    Class to handle popup dialogs
    """
    RESETBUTTON = QtWidgets.QDialogButtonBox.Reset
    CLOSEBUTTON = QtWidgets.QDialogButtonBox.Close
    CANCELBUTTON = QtWidgets.QDialogButtonBox.Cancel
    DISCARDBUTTON = QtWidgets.QDialogButtonBox.Discard
    APPLYBUTTON = QtWidgets.QDialogButtonBox.Apply
    USERBUTTON = '_userButton'
    USERBUTTON2 = '_userButton2'
    OKBUTTON = QtWidgets.QDialogButtonBox.Ok
    HELPBUTTON = QtWidgets.QDialogButtonBox.Help
    DEFAULTBUTTON = CLOSEBUTTON

    REVERTBUTTONTEXT = 'Revert'
    CANCELBUTTONTEXT = 'Cancel'
    CLOSEBUTTONTEXT = 'Close'
    APPLYBUTTONTEXT = 'Apply'
    OKBUTTONTEXT = 'OK'

    # ok button is disabled on __init__ if the revert button has been enabled, requires call to _postInit
    DISABLEOK = False

    USESCROLLWIDGET = False
    FIXEDWIDTH = True
    FIXEDHEIGHT = True
    ENABLEICONS = False
    DONTSHOWENABLED = False
    FORCEWIDTHTOTITLE = True
    _defaultResponse = None
    _defaultButton = None

    EDITMODE = True
    DEFAULTMARGINS = (14, 14, 14, 14)

    # a dict to store any required widgets' states between popups
    _storedState = {}
    storeStateOnReject = False

    def __init__(self, parent=None, windowTitle='', setLayout=False,
                 orientation=HORIZONTAL, size=None, minimumSize=None, **kwds):
        if _DEBUG: getLogger().debug2(f'--> pre __init__ {self}')

        # error-flag to disable exec_ if there is an error during initialising
        self.errorFlag = False

        super().__init__(parent)
        Base._init(self, setLayout=setLayout, **kwds)

        if orientation not in ORIENTATIONLIST:
            raise TypeError(f'orientation not in {ORIENTATIONLIST}')

        self.setWindowTitle(windowTitle)
        self.setContentsMargins(*self.DEFAULTMARGINS)
        self.getLayout().setSpacing(0)

        self._orientation = orientation
        # get the initial size as a QSize
        try:
            self._size = QtCore.QSize(*size) if size else None
        except Exception:
            raise TypeError(f'bad size {size}') from None

        # get the initial size as a QSize
        try:
            self._minimumSize = QtCore.QSize(*minimumSize) if minimumSize else None
        except Exception:
            raise TypeError(f'bad minimumSize {size}') from None

        # set up the mainWidget area
        self.mainWidget = Frame(self, setLayout=True, showBorder=False, grid=(0, 0))
        self.mainWidget.setAutoFillBackground(False)

        if self.USESCROLLWIDGET:
            # not resizing correctly on first show

            # self.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
            # self.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

            # set up a scroll area
            self._scrollArea = ScrollArea(self, setLayout=True, grid=(0, 0))
            self._scrollArea.setWidgetResizable(True)
            self._scrollArea.setWidget(self.mainWidget)
            self._scrollArea.setStyleSheet("""ScrollArea { border: 0px; background: transparent; }""")

        self._setDontShow()

        # self.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        # self.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # self._scrollArea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # self._scrollArea.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        # Spacer(self, 2, 2, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
        #        grid=(1, 1))

        # self._frameOptionsNested.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Minimum)
        # self.mainWidget.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        self.mainWidget.setContentsMargins(0, 0, 0, 0)
        self.mainWidget.getLayout().setSpacing(DEFAULTSPACING)

        self._buttonOptions = {}
        self.dialogButtons = None

        # keep a record of how many times the apply button has been pressed
        self._currentNumApplies = 0

        # clear the changes list
        self._changes = ChangeDict()

        # self.setDefaultButton()

        # GST stops a file icon being shown
        self.setWindowFilePath('')
        self.setWindowIcon(QtGui.QIcon())

        # set the background/fontSize for the tooltips, fraction slower but don't need to import the colour-names
        # self.setStyleSheet('QToolTip {{ background-color: {TOOLTIP_BACKGROUND}; '
        #                    'color: {TOOLTIP_FOREGROUND}; '
        #                    'font-size: {_size}pt ; }}'.format(_size=self.font().pointSize(), **getColours()))

        ## WARNING ==> setAttribute WA_DeleteOnClose, True :
        ## This flag should be used after checking all popup are closed correctly
        ## and there is no access to the object after deleting it,
        ## otherwise will raise threading issues
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        if _DEBUG: getLogger().debug2(f'--> post __init__ {self}')

    def _postInit(self):
        """post-initialise functions
        CCPN-Internal to be called at the end of __init__
        """
        if _DEBUG: getLogger().debug2(f'--> pre _postInit {self}')

        # set the desired buttons, and size of dialog
        self._setButtons()
        self._setDialogSize()

        # set the initial enabled/disabled state of buttons
        if self.getButton(self.OKBUTTON) and self.DISABLEOK:
            self.getButton(self.OKBUTTON).setEnabled(False or not self.EDITMODE)
        if self.getButton(self.APPLYBUTTON):
            self.getButton(self.APPLYBUTTON).setEnabled(False)
        if self.getButton(self.RESETBUTTON):
            self.getButton(self.RESETBUTTON).setEnabled(False)

        # restore the state of any required widgets
        self.restoreWidgetState()

        if _DEBUG: getLogger().debug2(f'--> post _postInit {self}')

    def _setDialogSize(self):
        """Set the fixed/free dialog size from size or sizeHint
        """
        # get the initial size as a QSize
        try:
            size = self._size if isinstance(self._size, QtCore.QSize) else \
                QtCore.QSize(*self._size) if self._size else None
        except Exception:
            raise TypeError(f'bad size {self._size}') from None

        # get the size of the title
        fontMetric = QtGui.QFontMetrics(self.font())
        # get an estimate for an average character width - 100 is arbitrary
        _w = max(self.sizeHint().width(),
                 (100 + fontMetric.boundingRect(self.windowTitle()).width()) if self.FORCEWIDTHTOTITLE else 0)
        _size = QtCore.QSize(size.width() if size else _w,
                             size.height() if size else self.sizeHint().height())

        # get the initial minimumSize as a QSize
        try:
            minimumSize = self._minimumSize if isinstance(self._minimumSize, QtCore.QSize) else \
                QtCore.QSize(*self._minimumSize) if self._minimumSize else None
        except Exception:
            raise TypeError(f'bad minimumSize {self._minimumSize}') from None

        _minimumSize = QtCore.QSize(minimumSize.width() if minimumSize else _w,
                                    minimumSize.height() if minimumSize else self.sizeHint().height())

        # set the fixed sized policies as required
        if self.FIXEDWIDTH:
            self.setFixedWidth(max(_size.width(), _minimumSize.width()))
            # this is very strange, setting fixed<dimension> does not necessarily set the policy :|
            # self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, self.sizePolicy().verticalPolicy())
        elif minimumSize:
            # set minimumSize from settings
            self.setMinimumWidth(_minimumSize.width())

        if self.FIXEDHEIGHT:
            self.setFixedHeight(max(_size.height(), _minimumSize.height()))
            # self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QtWidgets.QSizePolicy.Fixed)
        elif minimumSize:
            # set minimumSize from settings
            self.setMinimumHeight(_minimumSize.height())

        # self.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.Fixed if self.FIXEDWIDTH else QtWidgets.QSizePolicy.MinimumExpanding,
        #                               QtWidgets.QSizePolicy.Fixed if self.FIXEDHEIGHT else QtWidgets.QSizePolicy.MinimumExpanding, )
        self.resize(_size)

    # # pyqt5.15 does not allow setting with a float
    # def setMinimumWidth(self, p_int):
    #     super().setMinimumWidth(int(p_int))
    #
    # def setMinimumHeight(self, p_int):
    #     super().setMinimumHeight(int(p_int))
    #
    # def setMaximumWidth(self, p_int):
    #     super().setMaximumWidth(int(p_int))
    #
    # def setMaximumHeight(self, p_int):
    #     super().setMaximumHeight(int(p_int))

    def setOkButton(self, callback=None, text=None,
                    tipText='Apply changes and close',
                    icon='icons/dialog-apply.png',
                    enabled=True, visible=True):
        """Add an Ok button to the dialog box
        """
        return self._addButton(buttons=self.OKBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setCloseButton(self, callback=None, text=None,
                       tipText='Keep all applied changes and close',
                       icon='icons/window-close',
                       enabled=True, visible=True):
        """Add a Close button to the dialog box
        """
        return self._addButton(buttons=self.CLOSEBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setCancelButton(self, callback=None, text=None,
                        tipText='Roll-back all applied changes and close',
                        icon='icons/window-close',
                        enabled=True, visible=True):
        """Add a Cancel button to the dialog box
        """
        return self._addButton(buttons=self.CANCELBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setRevertButton(self, callback=None, text='Revert',
                        tipText='Roll-back all applied changes',
                        icon='icons/undo',
                        enabled=True, visible=True):
        """Add a Revert button to the dialog box
        """
        self.DISABLEOK = True
        return self._addButton(buttons=self.RESETBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setHelpButton(self, callback=None, text=None,
                      tipText='Help',
                      icon='icons/system-help',
                      enabled=True, visible=True):
        """Add a Help button to the dialog box
        """
        return self._addButton(buttons=self.HELPBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setDiscardButton(self, callback=None, text=None,
                         tipText='Discard changes',
                         icon='icons/orange-apply',
                         enabled=True, visible=True):
        """Add an Apply button to the dialog box
        """
        return self._addButton(buttons=self.DISCARDBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setApplyButton(self, callback=None, text=None,
                       tipText='Apply changes',
                       icon='icons/orange-apply',
                       enabled=True, visible=True):
        """Add an Apply button to the dialog box
        """
        return self._addButton(buttons=self.APPLYBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setUserButton(self, callback=None, text=None,
                      tipText='User action',
                      icon='icons/orange-apply',
                      enabled=True, visible=True):
        """Add a User button to the dialog box
        """
        return self._addButton(buttons=self.USERBUTTON, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def setUserButton2(self, callback=None, text=None,
                       tipText='User action 2',
                       icon='icons/orange-apply',
                       enabled=True, visible=True):
        """Add 2nd User button to the dialog box
        """
        return self._addButton(buttons=self.USERBUTTON2, callbacks=callback,
                               texts=text, tipTexts=tipText, icons=icon,
                               enabledStates=enabled, visibleStates=visible)

    def _addButton(self, **kwds):
        """Add button settings to the buttonList
        """
        if self.dialogButtons:
            raise RuntimeError("Error: cannot add buttons after __init__")

        for k, v in kwds.items():
            if k not in self._buttonOptions:
                self._buttonOptions[k] = (v,)
            else:
                self._buttonOptions[k] += (v,)

    def _setButtons(self):
        """Set the buttons for the dialog
        """
        grid = (1, 0) if self._orientation.startswith('h') else (0, 1)

        self.dialogButtons = DialogButtonBox(self, grid=grid,
                                             orientation=self._orientation,
                                             defaultButton=self._defaultButton,
                                             enableIcons=self.ENABLEICONS,
                                             **self._buttonOptions)
        self.dialogButtons.setContentsMargins(0, 18, 0, 0)

    def _setDontShow(self):
        from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget  # circular import :|

        # put a Don't Show checkbox at the bottom of the dialog if needed
        if not self.DONTSHOWENABLED:
            return

        grid = (2, 0)
        gridSpan = (1, 1) if self._orientation.startswith('h') else (1, 1)  # reserved
        try:
            from ccpn.framework.Application import getApplication

            # retrieve from preferences
            app = getApplication()
            popup = app.preferences.popups[self.__class__.__name__]
            state = bool(popup[_DONTSHOWPOPUP])
        except Exception:
            # any error should hide the checkbox
            return

        self._dontShowCheckBox = CheckBoxCompoundWidget(self,
                                                        grid=grid, gridSpan=gridSpan, hAlign='left',
                                                        orientation='right', stretch=(0, 0),
                                                        labelText=_DONTSHOWMESSAGE,
                                                        tipText='This popup can be enabled again from preferences->appearance',
                                                        checked=state,
                                                        )

        spc = self._dontShowCheckBox.sizeHint().height()
        self._dontShowCheckBox.setContentsMargins(0, spc // 4, 0, 0)

    def setDefaultButton(self, button=CLOSEBUTTON):
        """Set the default dialog button
        """
        self._defaultButton = button

    def getButton(self, buttonName):
        """Get the button from the buttonNames defined in the class
        """
        return self.dialogButtons.button(buttonName)

    def _fixedSize(self):
        self._sPolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self._sPolicy.setHorizontalStretch(0)
        self._sPolicy.setVerticalStretch(0)
        self.setSizePolicy(self._sPolicy)
        self.setFixedSize(self.maximumWidth(), self.maximumHeight())
        self.setSizeGripEnabled(False)

    def _revertClicked(self):
        """Revert button signal comes here
        Revert (roll-back) the state of the project to before the popup was opened
        """
        if self.project and self.project._undo:
            for _ in range(self._currentNumApplies):
                self.project._undo.undo()

        self._populate()

        # reset the buttons
        self._setButtonState()

    def _setButtonState(self):
        """Set the state of the ok/apply/cancel buttons
        """
        if not hasattr(self, GETCHANGESTATE):
            raise RuntimeError(f'widget {self} must have changes defined')
        _getChanges = getattr(self, GETCHANGESTATE)
        if not callable(_getChanges):
            raise RuntimeError(f'changes method for {self} not correctly defined')

        # get the information from the popup - which must handle its own nested _changes
        _changes = _getChanges()
        if not _changes:
            return
        popup, changeState, applyState, revertState, okButton, applyButton, revertButton, numApplies = _changes

        if popup:
            # disable the required buttons
            if okButton:
                okButton.setEnabled(False or not self.EDITMODE)
            if applyButton:
                applyButton.setEnabled(False)
            if revertButton:
                revertButton.setEnabled(False)

    def _cancelClicked(self):
        """Cancel button signal comes here
        """
        self._revertClicked()
        self.reject()

    def _closeClicked(self):
        """Close button signal comes here
        """
        self.reject()

    def _applyClicked(self):
        """Apply button signal comes here
        """
        self._applyChanges()

    def _okClicked(self):
        """OK button signal comes here
        """
        if self._applyChanges() is True:
            self.accept()

    def _helpClicked(self):
        """Help button signal comes here
        """
        pass

    def exec_(self) -> int:
        """Execute the dialog
        """
        if self.DONTSHOWENABLED:
            try:
                from ccpn.framework.Application import getApplication

                # store in preferences
                app = getApplication()
                popup = app.preferences.popups[self.__class__.__name__]
                state = popup[_DONTSHOWPOPUP]
            except Exception:
                state = False

            if state:
                # what is the default response for this dialog?
                # needs to be defined/set in the subclass of __init__
                if not self._defaultResponse:
                    raise RuntimeError('Popup defaultResponse is not defined')

                self._defaultResponse()
                return 0

        # call the super-class if there are no errors during initialising
        # return an error-state here other than None?
        result = None if self.errorFlag else super().exec_()

        return result

    @contextmanager
    def handleUserClicked(self):
        """Context manager to handle user actions in dialogs.
        """
        from ccpn.core.lib.ContextManagers import undoStackBlocking  # this causes circular imports. KEEP LOCAL

        # handle clicking of a user button
        with handleDialogApply(self) as error:
            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._refreshGLItems)

            # pass control to the calling function -user can set errorValue to stop accept
            yield error

            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=self._refreshGLItems)

            # redraw the items
            self._refreshGLItems()

        # check for any errors
        if error.errorValue:
            return False

        self.accept()

    def _applyAllChanges(self, changes):
        """Execute the Apply/OK functions
        """
        for v in changes.values():
            v()

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
        from ccpn.core.lib.ContextManagers import undoStackBlocking

        if self.EDITMODE:
            # get the list of widgets that have been changed - exit if all empty
            allChanges = bool(self._changes)
            if not allChanges:
                return True

        valid = True
        # handle clicking of the Apply/OK button
        with handleDialogApply(self) as error:

            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._refreshGLItems)

            # apply all functions to the object
            changes = self._changes
            if changes or not self.EDITMODE:
                # check whether the popup needs to be closed
                error.cleanUndo = bool(self._applyAllChanges(changes))

            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=self._refreshGLItems)

            # redraw the items
            self._refreshGLItems()

        # check for any errors
        if error.errorValue or error.cleanUndo:
            # repopulate popup on an error
            # self._populate()
            return False

        # everything has happened - disable the apply button
        if self.dialogButtons.button(self.APPLYBUTTON):
            self.dialogButtons.button(self.APPLYBUTTON).setEnabled(False)

        # remove all changes
        self._changes.clear()

        self._currentNumApplies += 1
        if self.dialogButtons.button(self.RESETBUTTON):
            self.dialogButtons.button(self.RESETBUTTON).setEnabled(True)

        return True

    def accept(self) -> None:
        result = super(CcpnDialogMainWidget, self).accept()

        # store the state of any required widgets
        self.storeWidgetState()

        getLogger().debug2(f'Clean up dialog {self} on accept')
        self._cleanupDialog()
        self._storeDontShow()

        return result

    def reject(self) -> None:
        result = super(CcpnDialogMainWidget, self).reject()

        if self.storeStateOnReject:
            # store the state of any required widgets
            self.storeWidgetState()

        getLogger().debug2(f'Clean up dialog {self} on reject')
        self._cleanupDialog()

        return result

    def _storeDontShow(self):
        if self.DONTSHOWENABLED:
            with suppress(Exception):
                from ccpn.framework.Application import getApplication

                # store in preferences
                if app := getApplication():
                    popups = app.preferences.setdefault(_POPUPS, {})
                    popup = popups.setdefault(self.__class__.__name__, {})
                    # should really get from a property rather than a widget
                    #  - if widget does not show then the initial state may not be set
                    popup[_DONTSHOWPOPUP] = self._dontShowCheckBox.isChecked()

    def _cleanupDialog(self):
        """Clean-up any extra widgets/data before closing
        """
        getLogger().debug2(f'Cleaning-up dialog {self} - subclass as required')

    def _refreshGLItems(self):
        """emit a signal to rebuild any required GL items
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def getActiveTabList(self):
        """Get a list of tabs for calulating the changes to settings
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def storeWidgetState(self):
        """Store the state of any required widgets between popups
        """
        # TO BE SUBCLASSED
        pass

    def restoreWidgetState(self):
        """Restore the state of any required widgets
        """
        # TO BE SUBCLASSED
        pass


#=========================================================================================
# CcpnDialog
#=========================================================================================

class CcpnDialog(QtWidgets.QDialog, Base):
    """
    Class to handle popup dialogs
    """

    REVERTBUTTONTEXT = 'Revert'
    CANCELBUTTONTEXT = 'Cancel'
    CLOSEBUTTONTEXT = 'Close'
    APPLYBUTTONTEXT = 'Apply'
    OKBUTTONTEXT = 'OK'

    def __init__(self, parent=None, windowTitle='', setLayout=False, size=(300, 100), **kwds):
        super().__init__(parent)
        Base._init(self, setLayout=setLayout, **kwds)

        self.setWindowTitle(windowTitle)
        self.setContentsMargins(15, 15, 15, 15)
        self.resize(*size)

        # GST stops a file icon being shown
        self.setWindowFilePath('')
        self.setWindowIcon(QtGui.QIcon())

    def _fixedSize(self):
        self._sPolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self._sPolicy.setHorizontalStretch(0)
        self._sPolicy.setVerticalStretch(0)
        self.setSizePolicy(self._sPolicy)
        self.setFixedSize(self.maximumWidth(), self.maximumHeight())
        self.setSizeGripEnabled(False)

    @staticmethod
    def setDefaultButton(button):
        if not isinstance(button, QtWidgets.QPushButton):
            raise TypeError(f'{str(button)} is not a button')

        button.setDefault(True)
        button.setAutoDefault(True)


def dialogErrorReport(self, undo, es):
    """Show warning popup and check the undo stack for items that need to be culled
    """
    from ccpn.ui.gui.widgets.MessageDialog import showWarning

    if es:
        showWarning(str(self.windowTitle()), str(es))

    # should only undo if something new has been added to the undo deque
    # may cause a problem as some things may be set with the same values
    # and still be added to the change list, so only undo if length has changed

    # get the name of the class propagating the error
    errorName = str(self.__class__.__name__)

    if undo.newItemsAdded:
        # undo any valid items and clear the stack above the current undo point
        undo.undo()
        undo.clearRedoItems()

        getLogger().debug(f'>>>Undo.{errorName}._applychanges')
    else:
        getLogger().debug(f'>>>Undo.{errorName}._applychanges nothing to remove')


@contextmanager
def handleDialogApply(self):
    """Context manager to wrap the apply button for dialogs
    Error trapping is contained inside the undoBlockWithoutSideBar, any error raised is placed in
    the errorValue of the yielded object and a warning popup is raised

    e.g.

        with handleDialogApply(self) as error:
            ...  code block here ...

        if error.errorValue:
            # an error occurred in the code block
    """

    from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar

    undo = self.project._undo


    # simple class to export variables from the generator function
    @dataclass
    class errorContent():
        errorValue = None
        cleanUndo = False


    try:
        # add an undoBlockWithoutSideBar
        with undoBlockWithoutSideBar():

            # transfer control to the calling function
            error = errorContent()
            yield error

    except Exception as es:

        # if an error occurs, report as a warning popup and return error to the calling method
        dialogErrorReport(self, undo, es)
        error.errorValue = es

        # re-raise the error if in debug mode
        if self.application._isInDebugMode:
            raise es

    else:
        if error.cleanUndo:
            # clean-up with warning popup
            dialogErrorReport(self, undo, None)


def _verifyPopupApply(self, attributeName, value, last, *postArgs, **postKwds):
    """Change the state of the apply button based on the changes in the tabs
    """
    if not hasattr(self, GETCHANGESTATE):
        raise RuntimeError(f'widget {self} must have changes defined')
    _getChanges = getattr(self, GETCHANGESTATE)
    if not callable(_getChanges):
        raise RuntimeError(f'changes method for {self} not correctly defined')

    # _changes must be a ChangeDict and be enabled to accept changes from the gui
    if not self._changes.enabled:
        return

    # if attributeName is defined use as key to dict to store change functions
    # append postFixes if you need to differentiate partial functions
    if attributeName:

        # append the extra parameters to the end of attributeName to give a unique
        # identifier into _changes dict, to differentiate same-name partial functions
        for pf in postArgs:
            if pf is not None:
                attributeName += str(pf)
        for k, pf in sorted(postKwds.items()):
            if pf is not None:
                attributeName += str(pf)
        attributeName += f'{id(self)}'

        if value:
            # store in dict - overwrite as required
            self._changes[attributeName] = value
            if not last:
                # put to the front if needed - could put priority into the attribute-name and then sort
                self._changes.move_to_end(attributeName, last=False)

        elif attributeName in self._changes:
            # delete from dict - empty dict implies no changes
            del self._changes[attributeName]

        getLogger().debug2(
                f">>>attrib {attributeName} {self._changes[attributeName] if attributeName in self._changes else 'None'}")

        if getattr(self, 'LIVEDIALOG', None):
            self._changeSettings()

    # get the information from the popup - which must handle its own nested _changes
    _changes = _getChanges()
    if not _changes:
        return

    popup, changeState, applyState, revertState, okButton, applyButton, revertButton, numApplies = _changes

    if popup:
        # set button states depending on number of changes - ok button or apply button can be selected
        applyChanges = changeState and applyState
        revertChanges = changeState or revertState
        if okButton:
            okButton.setEnabled(applyChanges or not popup.EDITMODE)
        if applyButton:
            applyButton.setEnabled(applyChanges)
        if revertButton:
            revertButton.setEnabled(revertChanges or numApplies)
