"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-08-23 19:21:22 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from functools import partial
from ccpn.core.lib.Notifiers import Notifier
from collections import OrderedDict
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight
from ccpn.ui._implementation.PeakListView import PeakListView
from ccpn.ui._implementation.IntegralListView import IntegralListView
from ccpn.ui._implementation.MultipletListView import MultipletListView
from ccpn.core.PeakList import PeakList
from ccpn.core.Spectrum import Spectrum
from ccpn.core.IntegralList import IntegralList
from ccpn.core.MultipletList import MultipletList
from ccpn.ui.gui.lib.GuiSpectrumView import _spectrumViewHasChanged
from ccpn.ui.gui.popups.SpectrumPropertiesPopup import SpectrumPropertiesPopup
from ccpn.core.lib import Pid
from ccpn.ui.gui.lib.GuiStripContextMenus import _SCMitem, ItemTypes, ITEM, _addMenuItems
from ccpn.util import Colour
from ccpn.framework.Application import getCurrent, getProject


class SpectrumToolBar(ToolBar):

    def __init__(self, parent=None, widget=None, **kwds):

        super().__init__(parent=parent, **kwds)
        self.widget = widget
        self._parent = parent
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)

        self.setMouseTracking(True)
        self._spectrumToolBarBlockingLevel = 0
        self.project = getProject()
        self.current = getCurrent()
        self._firstButton = 0
        self._currentSpectrumNotifier = Notifier(self.current,
                                                 [Notifier.CURRENT],
                                                 targetName=Spectrum._pluralLinkName,
                                                 callback=self._onCurrentSpectrumNotifier,
                                                 onceOnly=True),
        self._styleSheet = """
                            /*  currentField is a property on the widgetAction
                                that can be set to True to enable a highlighted border;
                                otherwise defaults to the standard 'checked'
                                section of the stylesheet.
                                There are not many colouirs available in the palette;
                                this uses a qlineargradient to pick a small range
                                between window-colour and medium-grey.
                                This is theme-agnostic, picks a shade always slightly lighter or
                                darker than the current background.
                                [(x1, y1), (x2, y2)] define the box over which the gradient is applied.
                                The widget is interpolated from [(0, 0), (1, 1)] in this box.
                                start, stop are normalised points for setting multiple colours in the gradient.
                            */
                                
                            QToolButton {
                                color: palette(dark);
                                padding: 0px;
                            }
                            QToolButton:checked[currentField=true] {
                                color: palette(text);
                                border: 0.5px solid palette(highlight);
                                border-radius: 2px;
                                background-color: qlineargradient(
                                                        x1: 0, y1: -1, x2: 0, y2: 6,
                                                        stop: 0 palette(window), stop: 1 #808080
                                                    );
                            }
                            QToolButton:checked {
                                color: palette(text);
                                border: 0.5px solid palette(dark);
                                border-radius: 2px;
                                background-color: qlineargradient(
                                                        x1: 0, y1: -1, x2: 0, y2: 6,
                                                        stop: 0 palette(window), stop: 1 #808080
                                                    );
                            }
                            """
        self._setButtonColourScheme()

    @property
    def isBlocked(self):
        """True if spectrumToolBar is blocked
        """
        # read state from widget blocking
        return self.widgetIsBlocked

    @staticmethod
    def _paintButtonToMove(button):
        pixmap = button.grab()  # makes a "ghost" of the button as we drag
        # below makes the pixmap half transparent
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(painter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QtGui.QColor(0, 0, 0, 127))
        painter.end()
        return pixmap

    def _addSubMenusToContext(self, contextMenu, button):

        with self.blockWidgetSignals(recursive=False):
            dd = OrderedDict(
                    [(PeakList, PeakListView), (IntegralList, IntegralListView), (MultipletList, MultipletListView)])
            spectrum = self.widget.project.getByPid(button.actions()[0].objectName())
            if spectrum:
                for coreObj, viewObj in dd.items():
                    smenu = contextMenu.addMenu(coreObj.className)
                    allViews = []
                    # list to check for duplicate objectLists
                    _found = []
                    vv = getattr(self.widget, viewObj._pluralLinkName)
                    if vv:
                        for view in vv:
                            s = coreObj.className
                            o = getattr(view, s[0].lower() + s[1:])
                            if o and o._parent == spectrum and o not in _found:
                                allViews.append(view)
                                _found.append(o)
                    views = list(set(allViews))
                    smenu.setEnabled(len(views) > 0)

                    menuItems = [_SCMitem(name='Show All',
                                          typeItem=ItemTypes.get(ITEM), icon='icons/null',
                                          callback=partial(self._setVisibleAllFromList, True, smenu, views)),
                                 _SCMitem(name='Hide All',
                                          typeItem=ItemTypes.get(ITEM), icon='icons/null',
                                          callback=partial(self._setVisibleAllFromList, False, smenu, views)),
                                 ]

                    _addMenuItems(self.widget, smenu, menuItems)

                    # smenu.addAction('Show All', partial(self._setVisibleAllFromList, True, smenu, views))
                    # smenu.addAction('Hide All', partial(self._setVisibleAllFromList, False, smenu, views))

                    smenu.addSeparator()
                    for view in sorted(views, reverse=False):
                        # print(f'     menu views {coreObj}   {viewObj}   {view}')
                        ccpnObj = view._childClass
                        strip = view._parent._parent
                        toolTip = 'Toggle {0} {1} on strip {2}'.format(coreObj.className, ccpnObj._key, strip.id)
                        if ccpnObj:
                            if len(self.widget.strips) > 1:  #add shows in which strips the view is
                                currentTxt = ''  # add in which strip is current
                                if self.widget.current.strip == strip:
                                    currentTxt = ' Current'
                                action = smenu.addItem('{0} ({1}{2})'.format(ccpnObj.id, strip.id, currentTxt),
                                                       toolTip=toolTip)
                            else:
                                action = smenu.addItem(ccpnObj.id, toolTip=toolTip)

                            action.setCheckable(True)
                            if view.isDisplayed:
                                action.setChecked(True)
                            action.toggled.connect(view.setDisplayed)
                            action.toggled.connect(self._updateGl)

    def _spectrumToolBarItem(self, button):
        spectrum = self.widget.project.getByPid(button.actions()[0].objectName())
        specViews = [spv for spv in self.widget.spectrumViews
                     if spv.spectrum == spectrum]

        if len(specViews) >= 1:
            return _SCMitem(name='Contours',
                            typeItem=ItemTypes.get(ITEM), toolTip='Toggle Spectrum Contours On/Off',
                            callback=partial(self._toggleSpectrumContours, button.actions()[0], specViews[0]),
                            checkable=True,
                            checked=specViews[0]._showContours)

    def _toggleSpectrumContours(self, buttonAction, specView):
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        specView._showContours = not specView._showContours
        _spectrumViewHasChanged({Notifier.OBJECT: specView})

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitPaintEvent()

    def _createToolBarContextMenu(self):
        """
        Creates a context menu for the toolbar with general actions.
        """

        contextMenu = Menu('', self.widget, isFloatWidget=True)
        dd = OrderedDict(
                [(PeakList, PeakListView), (IntegralList, IntegralListView), (MultipletList, MultipletListView)])
        for coreObj, viewObj in dd.items():
            smenuItems = []
            smenu = contextMenu.addMenu(coreObj.className)
            labelsBools = OrderedDict([('Show All', True),
                                       ('Hide All', False)])
            for label, abool in labelsBools.items():
                item = _SCMitem(name=label,
                                typeItem=ItemTypes.get(ITEM), icon='icons/null',
                                callback=partial(self._toggleAllViews, viewObj._pluralLinkName, abool))
                smenuItems.append(item)
            _addMenuItems(self.widget, smenu, smenuItems)

        return contextMenu

    def _toggleAllViews(self, viewPluralLinkName, abool=True):
        """
        :param viewPluralLinkName: peakListViews etc which is defined in the self.widget
        :param abool: True or False
        :return: Toggles all Views on display
        """
        for view in getattr(self.widget, viewPluralLinkName):
            view.setVisible(abool)

    def _createContextMenu(self, button: QtWidgets.QToolButton):
        """
        Creates a context menu containing a command to delete the spectrum from the display and its
        button from the toolbar.
        """
        if not button:
            return None
        if len(button.actions()) < 1:
            return None

        contextMenu = Menu('', self.widget, isFloatWidget=True)

        _addMenuItems(self.widget, contextMenu, [self._spectrumToolBarItem(button)])

        contextMenu.addSeparator()

        self._addSubMenusToContext(contextMenu, button)
        contextMenu.addSeparator()
        isSpectrumInCurrent = self._isSpectrumInCurrent(button)

        menuItems = [
            _SCMitem(name='Current',
                     typeItem=ItemTypes.get(ITEM),
                     callback=partial(self._setSpectrumAsCurrent, button),
                     checkable=True,
                     checked=isSpectrumInCurrent, ),
            _SCMitem(name='Jump on SideBar',
                     typeItem=ItemTypes.get(ITEM), icon='icons/null',
                     callback=partial(self._jumpOnSideBar, button)),
            _SCMitem(name='Properties...',
                     typeItem=ItemTypes.get(ITEM), icon='icons/null',
                     callback=partial(self._showSpectrumProperties, button)),
            _SCMitem(name='Remove Spectrum',
                     typeItem=ItemTypes.get(ITEM), icon='icons/null',
                     callback=partial(self._removeSpectrum, button)),
            ]

        _addMenuItems(self.widget, contextMenu, menuItems)

        return contextMenu

    def _isSpectrumInCurrent(self, button):
        spectrum = self.widget.project.getByPid(button.actions()[0].objectName())
        if spectrum:
            if spectrum in self.current.spectra:
                return True
        return False

    def _setSpectrumAsCurrent(self, button):
        action = button.actions()[0]
        spectrum = self.widget.project.getByPid(action.objectName())
        if spectrum:
            if spectrum in self.current.spectra:
                self.current.removeSpectrum(spectrum)
            else:
                self.current.addSpectrum(spectrum)
            self._setButtonColourScheme()

    def _jumpOnSideBar(self, button):
        spectrum = self.widget.project.getByPid(button.actions()[0].objectName())
        if spectrum:
            sideBar = self.widget.application.ui.mainWindow.sideBar
            sideBar.selectPid(spectrum.pid)

    def _showSpectrumProperties(self, button):
        spectrum = self.widget.project.getByPid(button.actions()[0].objectName())
        mainWindow = self.widget.application.ui.mainWindow
        if spectrum:  #not sure why It needs parent = mainWindow. copied from SideBar
            popup = SpectrumPropertiesPopup(parent=mainWindow, mainWindow=mainWindow, spectrum=spectrum)
            popup.exec_()
            # popup.raise_() # no need to raise()

    def _updateGl(self, ):
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)

        # GLSignals.emitPaintEvent()
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.widget.strips[0], dataDict={})

    def _getSpectrumViewFromButton(self, button):
        spvs = []
        key = [key for key, value in self.widget.spectrumActionDict.items() if value == button.actions()[0]][0]

        for spectrumView in self.widget.spectrumViews:
            if spectrumView.spectrum == key:
                spvs.append(spectrumView)
        if len(spvs) == 1:
            return spvs[0]

    def _setVisibleAllFromList(self, abool, menu, views):
        """
        :param abool: T or F
        :param menu:
        :param views: any of Views obj _pluralLinkName
        :return:
        """
        if views:
            for view in views:
                view.setVisible(abool)
                for action in menu.actions():
                    if action.text() == view.pid:
                        action.setChecked(abool)

    def _spectrumRename(self, data):
        """Rename the spectrum name in the toolbar from a notifier callback
        """
        spectrum = data[Notifier.OBJECT]
        trigger = data[Notifier.TRIGGER]

        if spectrum and trigger in [Notifier.RENAME]:
            oldPid = Pid.Pid(data[Notifier.OLDPID])
            oldId = oldPid.id

            validActions = [action for action in self.actions() if action.text() == oldId]
            for action in validActions:
                action.setText(spectrum.id)
                action.setObjectName(spectrum.pid)
                # setWidgetFont(action, size='SMALL')

    def _removeSpectrum(self, button: QtWidgets.QToolButton):
        """
        Removes the spectrum from the display and its button from the toolbar.
        """
        # event called from right-mouse menu
        key = [key for key, value in self.widget.spectrumActionDict.items() if value == button.actions()[0]][0]
        uniqueViews = set(sv.spectrum for sv in self.widget.spectrumViews)
        for spectrumView in self.widget.spectrumViews:
            if spectrumView.spectrum == key:
                if len(uniqueViews) == 1 and self.project.application.preferences.appearance.closeSpectrumDisplayOnLastSpectrum:
                    # close the spectrumDisplay
                    self.widget.close()
                else:
                    self.widget.removeSpectrum(spectrumView.spectrum)
                break
        else:
            showWarning('Spectrum', 'Spectrum not found in toolbar')

    def _dragButton(self, event):

        toolButton = self.childAt(event.pos())
        self._buttonBeingDragged = toolButton
        allActionsTexts = []

        if toolButton:
            pixmap = self._paintButtonToMove(toolButton)

            mimeData = QtCore.QMimeData()
            mimeData.setText('%d,%d' % (event.x(), event.y()))
            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(pixmap)
            # start the drag operation

            allActionsTexts = [action.text() for action in self.actions()]
            if drag.exec_(QtCore.Qt.MoveAction) == QtCore.Qt.MoveAction:

                point = QtGui.QCursor.pos()
                nextButton = QtWidgets.QApplication.widgetAt(point)

                if isinstance(nextButton, QtWidgets.QToolButton) \
                        and nextButton.actions() \
                        and nextButton.actions()[0] in self.actions():

                    # don't need to move
                    if nextButton == toolButton:
                        return

                    # get the new index and move the spectrum
                    startInd = allActionsTexts.index(toolButton.text())
                    endInd = allActionsTexts.index(nextButton.text())
                    self.widget.moveSpectrumByIndex(startInd, endInd)
                    return

        event.ignore()

    def event(self, event: QtCore.QEvent) -> bool:
        """
        Use the event handler to process events
        """
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # if event.button() == QtCore.Qt.LeftButton: Can't make it working!!!

            if event.button() == QtCore.Qt.RightButton:
                toolButton = self.childAt(event.pos())
                if toolButton:
                    menu = self._createContextMenu(toolButton)
                    if menu:
                        menu.move(event.globalPos().x(), event.globalPos().y() + 10)
                        menu.exec_()
                else:
                    menu = self._createToolBarContextMenu()
                    if menu:
                        menu.move(event.globalPos().x(), event.globalPos().y() + 10)
                        menu.exec_()

            if event.button() == QtCore.Qt.MiddleButton:
                self._dragButton(event)

        return super().event(event)

    def _addNewButton(self, spectrumView):
        _actions = {act.objectName(): act for act in self.actions()}

        # create new action for any spectrumViews without an action (create spectrumView)
        if spectrumView.spectrum.pid not in _actions:
            self._setupAction(spectrumView)

    def reorderButtons(self, spectrumViews):
        """Reorder the buttons to match the spectrumView ordering
        """
        _actions = {act.objectName(): act for act in self.actions()}

        # print(f'   reorderButtons   {spectrumViews}')
        # create new action for any spectrumViews without an action (create spectrumView)
        for specView in spectrumViews:
            if specView.spectrum.pid not in _actions:
                self._setupAction(specView)

        # apply the new ordering
        _newOrder = [_actions[sv.spectrum.pid] for sv in spectrumViews if sv.spectrum.pid in _actions]
        self.insertActions(None, _newOrder)

        # reset the sizes of the action widgets - not sure why they change :|
        for action in _actions.values():
            # get the attached widget
            widget = self.widgetForAction(action)

            _height1 = max(getFontHeight(size='SMALL') or 12, 12)
            widget.setIconSize(QtCore.QSize(_height1 * 10, _height1))
            widget.setStyleSheet(self._styleSheet)

            self._setSizes(action)

    def setButtonsFromSpectrumViews(self, spectrumViews):
        """Set up the spectrumDisplay buttons when initialising a display
        """
        with self.blockWidgetSignals(recursive=False):
            # clear the old actions
            # _actions = {act: act.objectName for act in self.actions}

            for act in list(self.actions()):
                self.removeAction(act)

            for specView in spectrumViews:
                self._setupAction(specView)

    def _setupAction(self, spectrumView):
        """Create and set up a new action attached to the spectrum
        """
        import traceback

        spectrum = spectrumView.spectrum
        spectrumName = spectrum.name

        # print(f'   _setupAction {spectrumView}   {spectrumName}')
        # print(traceback.print_stack())

        # create new action
        _actions = [action for action in self.actions() if action and action.objectName() == spectrum.pid]
        if len(_actions) > 1:
            raise RuntimeError('Too many toolbar actions with the same name')
        if len(_actions) == 1:
            action = _actions[0]
        else:
            action = self.addAction(spectrumName)

        action.setObjectName(spectrum.pid)

        action.setCheckable(True)
        action.setChecked(spectrumView.isDisplayed)
        action.setToolTip(spectrum.name)

        # get the attached widget
        widget = self.widgetForAction(action)

        _height1 = max(getFontHeight(size='SMALL') or 12, 12)
        widget.setIconSize(QtCore.QSize(_height1 * 10, _height1))
        self._setSizes(action)

        widget.spectrumView = spectrumView
        action.spectrumViewPid = spectrumView.pid
        self.widget.spectrumActionDict[spectrum] = action

        # NOTE:ED - UPDATE, the following call sets the icon colours:
        _spectrumViewHasChanged({Notifier.OBJECT: spectrumView})

        action.toggled.connect(partial(self._toggleSpectrumViews, spectrum, action))
        setWidgetFont(action, size='SMALL')
        self._setButtonColourScheme()

    def _toggleSpectrumViews(self, spectrum, action, state):
        """Toggle visibility of spectrumViews attached to this spectrum in the same spectrumDisplay
        """
        specViews = [sv for sv in self.widget.spectrumViews if sv.spectrum == spectrum]
        for sv in specViews:
            sv.setVisible(state)

    def _addSpectrumViewToolButtons(self, spectrumView):
        _strip = spectrumView.strip
        spectrumDisplay = _strip.spectrumDisplay
        if spectrumDisplay.isGrouped:
            return

        # print(f'   _addSpectrumViewToolButtons   {spectrumView}   {spectrumView.isDisplayed}')
        with self.blockWidgetSignals(recursive=False):
            spectrumDisplay = spectrumView.strip.spectrumDisplay
            spectrum = spectrumView.spectrum
            action = spectrumDisplay.spectrumActionDict.get(spectrum)
            if not action:
                # add toolbar action (button)
                spectrumName = spectrum.name
                # This is a bug, it changes the name of button and crashes when moving them across
                # if len(spectrumName) > 12:
                #   spectrumName = spectrumName[:12]+'.....'

                actionList = self.actions()
                try:
                    # try and find the spectrumView in the orderedlist - for undo function
                    # oldList = spectrumDisplay.orderedSpectrumViews(spectrumDisplay.spectrumViews)
                    # NOTE:ED - not tested as gui undo disabled
                    oldList = _strip.getSpectrumViews()
                    if spectrumView in oldList:
                        oldIndex = oldList.index(spectrumView)
                    else:
                        oldIndex = len(oldList)

                    if actionList and oldIndex < len(actionList):
                        nextAction = actionList[oldIndex]

                        # create a new action and move it to the correct place in the list
                        action = self.addAction(spectrumName)
                        action.setObjectName(spectrum.pid)
                        self.insertAction(nextAction, action)
                    else:
                        action = self.addAction(spectrumName)
                        action.setObjectName(spectrum.pid)

                except Exception as es:
                    action = self.addAction(spectrumName)
                    action.setObjectName(spectrum.pid)

                action.setCheckable(True)
                action.setChecked(spectrumView.isDisplayed)
                action.setToolTip(spectrum.name)
                widget = self.widgetForAction(action)

                _height1 = max(getFontHeight(size='SMALL') or 12, 12)
                widget.setIconSize(QtCore.QSize(_height1 * 10, _height1))
                # widget.setIconSize(QtCore.QSize(120, 10))
                self._setSizes(action)
                # WHY _wrappedData and not spectrumView?
                widget.spectrumView = spectrumView
                action.spectrumViewPid = spectrumView.pid

                spectrumDisplay.spectrumActionDict[spectrum] = action
                # The following call sets the icon colours:
                _spectrumViewHasChanged({Notifier.OBJECT: spectrumView})

        # if spectrumDisplay.is1D:
        #     action.toggled.connect(spectrumView.plot.setVisible)
        action.toggled.connect(spectrumView.setVisible)
        setWidgetFont(action, size='SMALL')
        return action

    def _setSizes(self, action):

        widget = self.widgetForAction(action)
        _height1 = max(getFontHeight(size='SMALL') or 12, 12)
        _height2 = max(getFontHeight(size='VLARGE') or 30, 30)
        widget.setIconSize(QtCore.QSize(_height1 * 10, _height1))
        widget.setFixedSize(int(_height2 * 2.5), _height2)

    def setSpectrumGroupActionIcon(self, action, spectrumGroup):
        self._addActionIcon(action, spectrumGroup)

    def setSpectrumActionIcon(self, action, spectrum):
        _sv = [sv for sv in self.spectrumDisplay.spectrumViews if sv.spectrum == spectrum]
        if len(_sv) != 1:
            return

        specView = _sv[0]
        self._addActionIcon(action, specView)

    def _addActionIcon(self, action, obj):
        _iconX = int(60 / self.spectrumDisplay.devicePixelRatio())
        _iconY = int(10 / self.spectrumDisplay.devicePixelRatio())
        pix = QtGui.QPixmap(QtCore.QSize(_iconX, _iconY))

        # print(f'   _addActionIcon  {action}   {obj}')
        if getattr(obj, '_showContours', True) or self.spectrumDisplay.isGrouped:
            if self.spectrumDisplay.is1D:
                _col = obj.sliceColour
            else:
                _col = obj.positiveContourColour

            if _col and _col.startswith('#'):
                pix.fill(QtGui.QColor(_col))

            elif _col in Colour.colorSchemeTable:
                colourList = Colour.colorSchemeTable[_col]

                step = _iconX
                stepX = _iconX
                stepY = len(colourList) - 1
                jj = 0
                painter = QtGui.QPainter(pix)

                for ii in range(_iconX):
                    _interp = (stepX - step) / stepX
                    _intCol = Colour.interpolateColourHex(colourList[min(jj, stepY)], colourList[min(jj + 1, stepY)],
                                                          _interp)

                    painter.setPen(QtGui.QColor(_intCol))
                    painter.drawLine(ii, 0, ii, _iconY)
                    step -= stepY
                    while step < 0:
                        step += stepX
                        jj += 1

                painter.end()

            else:
                pix.fill(QtGui.QColor('gray'))
        else:
            pix.fill(QtGui.QColor('gray'))

        action.setIcon(QtGui.QIcon(pix))

    def _setButtonColourScheme(self):
        for action in self.actions():
            widget = self.widgetForAction(action)
            spectrumView = self.project.getByPid(action.spectrumViewPid)
            if spectrumView is not None:
                spectrum = spectrumView.spectrum
                if spectrum in self.current.spectra:
                    widget.setProperty('currentField', True)
                else:
                    widget.setProperty('currentField', False)
                widget.setStyleSheet(self._styleSheet)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def _onCurrentSpectrumNotifier(self, data):
        self._setButtonColourScheme()
