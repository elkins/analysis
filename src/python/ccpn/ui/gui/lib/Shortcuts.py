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
__dateModified__ = "$dateModified: 2024-06-26 14:52:13 +0100 (Wed, June 26, 2024) $"
__version__ = "$Revision: 3.2.4 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:34 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtGui, QtCore
from functools import partial

from ccpn.util.Logging import getLogger


SHORTCUT_KEYS = 'keys'
SHORTCUT_KEYSTRING = 'keyString'
SHORTCUT_OBJECT = 'obj'
SHORTCUT_FUNC = 'func'
SHORTCUT_CONTEXT = 'context'
SHORTCUT_SHORTCUT = 'shortcut'

_shortcutList = {}


class Shortcuts:

    application = None

    def _setShortcuts(self, mainWindow):
        """
        Sets shortcuts for functions not specified in the main window menubar
        :param mainWindow: the MainWindow instance (couod be self, but not always (i.e. for TempAreaWindow)
        """
        # avoiding circular imports
        from ccpn.core.lib import AssignmentLib
        from ccpn.ui.gui.lib import SpectrumDisplayLib

        context = QtCore.Qt.WidgetWithChildrenShortcut
        # addShortCut("c, h", self, self.toggleCrosshairAll, context=context)
        addShortCut("e, n", self, mainWindow.showEstimateNoisePopup, context=context)
        addShortCut("g, s", self, mainWindow.toggleGridAll, context=context)
        addShortCut("Del", self, partial(mainWindow.deleteSelectedItems), context=context)
        addShortCut("Backspace", self, partial(mainWindow.deleteSelectedItems), context=context)
        addShortCut("m, k", self, mainWindow.createMark, context=context)
        addShortCut("m, c", self, mainWindow.clearMarks, context=context)
        addShortCut("m, x", self, partial(mainWindow.createMark, 0), context=context)
        addShortCut("m, y", self, partial(mainWindow.createMark, 1), context=context)
        addShortCut("m, z", self, partial(mainWindow.createMark, 2), context=context)
        addShortCut("m, w", self, partial(mainWindow.createMark, 3), context=context)
        addShortCut("p, m", self, mainWindow.createPeakAxisMarks, context=context)
        addShortCut("p, x", self, partial(mainWindow.createPeakAxisMarks, 0), context=context)
        addShortCut("p, y", self, partial(mainWindow.createPeakAxisMarks, 1), context=context)
        addShortCut("p, z", self, partial(mainWindow.createPeakAxisMarks, 2), context=context)
        addShortCut("p, w", self, partial(mainWindow.createPeakAxisMarks, 3), context=context)
        addShortCut("u, m", self, mainWindow.createMultipletAxisMarks, context=context)
        addShortCut("u, x", self, partial(mainWindow.createMultipletAxisMarks, 0), context=context)
        addShortCut("u, y", self, partial(mainWindow.createMultipletAxisMarks, 1), context=context)
        addShortCut("u, z", self, partial(mainWindow.createMultipletAxisMarks, 2), context=context)
        addShortCut("u, w", self, partial(mainWindow.createMultipletAxisMarks, 3), context=context)
        addShortCut("f, n", self, partial(SpectrumDisplayLib.navigateToCurrentNmrResiduePosition,
                                          mainWindow.application), context=context)
        addShortCut("f, p", self, partial(SpectrumDisplayLib.navigateToCurrentPeakPosition,
                                          mainWindow.application), context=context)
        # addShortCut("p, g", self, mainWindow.propagateAssignments, context=context)  # defined in menu
        # addShortCut("c, a", self, mainWindow.copyAssignments,
        #             context=context)
        addShortCut("c, z", self, mainWindow._clearCurrentPeaks, context=context)
        addShortCut("c, o", self, mainWindow.setContourLevels, context=context)

        addShortCut("f, t", self, mainWindow.filterOnCurrentTable, context=context)
        addShortCut("t, u", self, partial(mainWindow.traceScaleUp, self), context=context)
        addShortCut("t, d", self, partial(mainWindow.traceScaleDown, self), context=context)
        addShortCut("t, h", self, partial(mainWindow.toggleHTrace, self), context=context)
        addShortCut("t, v", self, partial(mainWindow.toggleVTrace, self), context=context)
        addShortCut("t, a", self, mainWindow.newPhasingTrace, context=context)
        addShortCut("t, r", self, mainWindow.removePhasingTraces, context=context)
        addShortCut("p, v", self, mainWindow.setPhasingPivot, context=context)

        addShortCut("s, k", self, mainWindow.stackSpectra, context=context)
        addShortCut("l, a", self, partial(mainWindow.toggleLastAxisOnly, self), context=context)

        addShortCut("a, m", self, mainWindow.addMultiplet, context=context)
        addShortCut("x, m", self, mainWindow.mergeCurrentMultiplet, context=context)
        addShortCut("c, c", self, mainWindow.newCollectionOfCurrentPeaks, context=context)
        addShortCut("i, 1", self, mainWindow.add1DIntegral, context=context)
        addShortCut("g, p", self, mainWindow.getCurrentPositionAndStrip, context=context)
        addShortCut("r, p", self, partial(mainWindow.refitCurrentPeaks, singularMode=True), context=context)
        addShortCut("r, g", self, partial(mainWindow.refitCurrentPeaks, singularMode=False), context=context)
        addShortCut("r, h", self, mainWindow.recalculateCurrentPeakHeights, context=context)
        addShortCut("Tab,Tab", self, mainWindow.moveToNextSpectrum, context=context)
        addShortCut("Tab, q", self, mainWindow.moveToPreviousSpectrum, context=context)
        addShortCut("Tab, a", self, mainWindow.showAllSpectra, context=context)
        addShortCut("Tab, z", self, mainWindow.hideAllSpectra, context=context)
        addShortCut("Tab, x", self, mainWindow.invertSelectedSpectra, context=context)
        addShortCut("m, m", self, mainWindow.switchMouseMode, context=context)
        addShortCut("s, e", self, mainWindow.snapCurrentPeaksToExtremum, context=context)

        addShortCut("z, s", self, mainWindow.storeZoom, context=context)
        addShortCut("z, r", self, mainWindow.restoreZoom, context=context)
        addShortCut("z, p", self, mainWindow.previousZoom, context=context)
        addShortCut("z, n", self, mainWindow.nextZoom, context=context)
        addShortCut("z, i", self, mainWindow.zoomIn, context=context)
        addShortCut("z, o", self, mainWindow.zoomOut, context=context)
        addShortCut("=", self, mainWindow.zoomIn, context=context)  # overrides openGL _panSpectrum
        addShortCut("+", self, mainWindow.zoomIn, context=context)
        addShortCut("-", self, mainWindow.zoomOut, context=context)

        # THESE REMOVE CONTROL FROM TABLES

        # addShortCut("Up", self, partial(mainWindow.panSpectrum, 'up'), context=context)
        # addShortCut("Down", self, partial(mainWindow.panSpectrum, 'down'), context=context)
        # addShortCut("Left", self, partial(mainWindow.panSpectrum, 'left'), context=context)
        # addShortCut("Right", self, partial(mainWindow.panSpectrum, 'right'), context=context)

        # addShortCut("Shift+Up", self, partial(mainWindow.movePeaks, 'up'), context=context)
        # addShortCut("Shift+Down", self, partial(mainWindow.movePeaks, 'down'), context=context)
        # addShortCut("Shift+Left", self, partial(mainWindow.movePeaks, 'left'), context=context)
        # addShortCut("Shift+Right", self, partial(mainWindow.movePeaks, 'right'), context=context)

        addShortCut("z, a", self, mainWindow.resetAllZoom, context=context)

        addShortCut("p, l", self, mainWindow.cycleSymbolLabelling, context=context)
        addShortCut("p, s", self, mainWindow.cyclePeakSymbols, context=context)
        # addShortCut("Space, Space", self, mainWindow.toggleConsole, context=context) # this is not needed here, already set on Menus!!
        # addShortCut("CTRL+a", self, mainWindow.selectAllPeaks, context=context)

        addShortCut("q, q", self, mainWindow._lowerContourBaseCallback, context=context)
        addShortCut("w, w", self, mainWindow._raiseContourBaseCallback, context=context)
        addShortCut("j, j", self, mainWindow.previousZPlane, context=context)
        addShortCut("k, k", self, mainWindow.nextZPlane, context=context)

    #     addShortCut("q, w, p, l", self, mainWindow.testLongShortcut, context=context)
    #
    # def testLongShortcut(self):
    #     print('>>>long')

    def _setUserShortcuts(self, preferences=None, mainWindow=None):

        # Avoiding circular imports
        from ccpn.ui.gui.popups.ShortcutsPopup import UserShortcuts

        # TODO:ED fix this circular link
        self.application._userShortcuts = UserShortcuts(mainWindow=mainWindow)  # set a new set of shortcuts

        context = QtCore.Qt.ApplicationShortcut
        userShortcuts = preferences.shortcuts
        for shortcut, function in userShortcuts.items():

            try:
                self.application._userShortcuts.addUserShortcut(shortcut, function)

                addShortCut("%s, %s" % (shortcut[0], shortcut[1]), self,
                            partial(UserShortcuts.runUserShortcut, self.application._userShortcuts, shortcut),
                            context)

            except:
                getLogger().warning('Error setting user shortcuts function')

            # if function.split('(')[0] == 'runMacro':
            #   QtWidgets.QShortcut(QtGui.QKeySequence("%s, %s" % (shortcut[0], shortcut[1])),
            #             self, partial(self.namespace['runMacro'], function.split('(')[1].split(')')[0]), context=context)
            #
            # else:
            #   stub = self.namespace.get(function.split('.')[0])
            #   try:
            #     QtWidgets.QShortcut(QtGui.QKeySequence("%s, %s" % (shortcut[0], shortcut[1])), self,
            #                     reduce(getattr, function.split('.')[1:], stub), context=context)
            #   except:
            #     getLogger().warning('Function cannot be found')


def addShortCut(keys: str | QtGui.QKeySequence = None, obj=None, func=None, context=None, autoRepeat=False):
    """
    Add a new shortcut to the widget/context and store in the shortcut list
    :param keys: - string containing the keys; e.g., 'a, b' or the keySequence object
                  e.g., QtGui.QKeySequence.SelectAll
    :param obj: - widget to attach keySequence to
    :param func: - function to attach
    :param context: - context; e.g., WidgetShortcut|ApplicationShortcut
    """
    from ccpn.ui.gui.lib.GuiMainWindow import GuiMainWindow

    if isinstance(keys, str):
        # print(keys, func)
        keys = QtGui.QKeySequence(keys)

    shortcut = QtWidgets.QShortcut(keys, obj, func, context=context)
    shortcut.setAutoRepeat(autoRepeat)
    storeShortcut(keys, obj, func, context, shortcut)
    tl = keys.toString()
    if isinstance(obj, GuiMainWindow):
        obj._storeShortcut(tl, func)
    return shortcut


def storeShortcut(keys: str | QtGui.QKeySequence = None, obj=None, func=None, context=None, shortcut=None):
    """
    Store the new shortcut in the dict, may be an Action from the menu
    :param keys: - string containing the keys; e.g., 'a, b' or the keySequence object
                  e.g., QtGui.QKeySequence.SelectAll
    :param obj: - widget to attach keySequence to
    :param func: - function to attach
    :param context: - context; e.g., WidgetShortcut|ApplicationShortcut
    """
    if obj not in _shortcutList:
        _shortcutList[obj] = {}

    if isinstance(keys, str):
        keys = QtGui.QKeySequence(keys)

        keyString = keys.toString()
        shortcutItem = {SHORTCUT_KEYS     : keys,
                        SHORTCUT_KEYSTRING: keyString,
                        SHORTCUT_OBJECT   : obj,
                        SHORTCUT_FUNC     : func,
                        SHORTCUT_CONTEXT  : context,
                        SHORTCUT_SHORTCUT : shortcut}
        _shortcutList[obj][keyString] = shortcutItem


def clearShortcuts(widget=None):
    """
    Clear all shortcuts that exist in all objects from the current widget
    :param widget - target widget:
    """
    context = QtCore.Qt.WidgetWithChildrenShortcut
    for obj in _shortcutList.values():
        for shortcutItem in obj.values():
            QtWidgets.QShortcut(shortcutItem[SHORTCUT_KEYS], widget, context=context)
