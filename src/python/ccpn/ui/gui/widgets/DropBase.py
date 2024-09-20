"""
Define routines for a dropable widget
This module is subclassed by widgets.Base and should not be used directly

GWV April-2017: Drived from an earlier version of DropBase

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
__dateModified__ = "$dateModified: 2024-09-11 13:07:27 +0100 (Wed, September 11, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
import json
from ccpn.util.Logging import getLogger
from PyQt5 import QtGui, QtCore, QtWidgets


# GST maybe this too high level but because of the way drag events are handled cooperatively
# at the moment it needs to be here...
#
# so what should happen (from my reading of the omens / Qt 'Documentation') is all widgets should reject events they
# can't handle, this will then cause the event to percolate out through the visual hierarchy till it finds a module and
# then gets handled, Currently any widget that inherits drop base will pass all events upto drop base which is
# then handling module events which ought i guess be handled by the module after visual hierarchy percolation
#
# This also appears to be leading to code being shared by ccpnModule and DragBase (see DragMoveEvent). Also it could
# be argued that handling drag and drop overlays should be upto CcpnModuleArea not CcpnModule
# we also have the joy of circular imports as well...
#
# if this analysis is wrong do tell me why, i am curious to understand whats going on


class DropBase:
    """
    Class to implement drop and drag
    Callback signature on drop: dropEventCallback(dataDict)
    """

    # drop targets
    URLS = 'urls'
    TEXT = 'text'
    PIDS = 'pids'
    IDS = 'ids'
    DFS = 'dfs'
    _dropTargets = (URLS, TEXT, PIDS, IDS, DFS)

    from ccpn.util.Constants import ccpnmrJsonData as JSONDATA
    from ccpn.util.Constants import ccpnmrModelDataList as MODELDATALIST

    def _init(self, acceptDrops=False, **kwds):

        # print('DEBUG DropBase %r: acceptDrops=%s' % (self, acceptDrops))

        self._dropEventCallback = None
        self._enterEventCallback = None
        self._dragMoveEventCallback = None
        self.setAcceptDrops(acceptDrops)
        self.inDragToMaximisedModule = False

    def setDropEventCallback(self, callback):
        """Set the callback function for drop event."""
        self._dropEventCallback = callback

    def dragEnterEvent(self, event):

        # self.checkForBadDragEvent(event)

        parentModule = self._findModule()

        if parentModule:
            if parentModule.isDragToMaximisedModule(event):
                parentModule.handleDragToMaximisedModule(event)
                return

        dataDict = self.parseEvent(event)
        if dataDict is not None and len(dataDict) > 1:
            event.accept()
            if self._dragMoveEventCallback is not None:
                self._dragMoveEventCallback(dataDict)
        event.accept()

    def setDragMoveEventCallback(self, callback):
        self._dragMoveEventCallback = callback

    def setDragEnterEventCallback(self, callback):
        self._enterEventCallback = callback

    # def dragMoveEvent(self, event):
    #   dataDict = self.parseEvent(event)
    #   if dataDict is not None and len(dataDict) > 1:
    #     if self._dragMoveEventCallback is not None:
    #       self._dragMoveEventCallback(dataDict)
    #       event.accept()
    #       return
    #
    #   event.ignore()
    #   print('>>>dragMoveEvent')

    # super().dragMoveEvent(event)

    def isDragToMaximisedModule(self, event):
        from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModule

        result = False

        parentModule = self._findModule()

        if parentModule is None:
            return result

        data = self.parseEvent(event)

        if not 'source' in data:
            return result

        source = data['source']

        if source is None:
            return result

        if source is parentModule:
            return result

        if not isinstance(source, CcpnModule):
            return result

        result = parentModule.maximised

        return result

    def handleDragToMaximisedModule(self, ev):
        class MyEventFilter(QtCore.QObject):
            def __init__(self, target, statusBar):
                super().__init__()
                self._target = target
                self._statusBar = statusBar

            def eventFilter(self, obj, event):
                try:
                    if event.type() == QtCore.QEvent.DragLeave:
                        self._target.inDragToMaximisedModule = False
                        if self._statusBar is not None:
                            self._statusBar.clearMessage()

                        self._target.removeEventFilter(self)
                        self._target.cleanupFilter = None
                        self.deleteLater()


                except Exception as e:
                    print('exception during event filter cleanup, deleting myself', e)
                    self.deleteLater()

                result = super().eventFilter(obj, event)
                return result


        parentModule = self._findModule()

        if not self.inDragToMaximisedModule and isinstance(ev, (QtGui.QDragEnterEvent, QtGui.QDragMoveEvent)):

            message = "Can't drag to a maximised window"

            statusBar = parentModule.findWindow().statusBar()

            if statusBar is not None:
                statusBar.showMessage(message)
            parentModule.flashMessage(message)

            # GST this cleanup filter is because its is not guarunteed that the DragLeaveEvent will come via
            # the same widget so this is safer
            self.cleanupFilter = MyEventFilter(self, statusBar)
            QtWidgets.QApplication.instance().installEventFilter(self.cleanupFilter)

            ev.setDropAction(QtCore.Qt.IgnoreAction)
            ev.ignore()
            self.inDragToMaximisedModule = True

    def dropEvent(self, event):
        """
        Catch dropEvent and dispatch to processing callback
        'Native' treatment of CcpnModule instances
        """

        if self.inDragToMaximisedModule:
            return

        if inModuleOverlay := self._callModuleDrop(event):
            inModuleOverlay.dropEvent(event)
            self._clearOverlays()
            return

        if self.acceptDrops():
            dataDict = self.parseEvent(event)
            getLogger().debug(f'Accepted drop with data:{dataDict}')
            getLogger().debug(f'DropBase-event>: {self} callback: {self._dropEventCallback} data: {dataDict}')

            if dataDict is not None and len(dataDict) > 1:
                event.accept()
                # follow parents to find first valid callback, until top-level reached
                widg = self
                while widg:
                    if (hasattr(widg, '_dropEventCallback') and widg._dropEventCallback is not None):
                        if not widg._dropEventCallback(dataDict):
                            # dropEvent is not automatically propagating up the qt-widget tree :|
                            event.accept()
                            break
                    widg = widg.parent()
                else:
                    event.ignore()
        else:
            getLogger().debug('Widget not droppable')

        # call to clear the overlays
        self._clearOverlays()

    def parseEvent(self, event) -> dict:
        """
        Interpret drop event; extract urls, text or JSONDATA dicts
        convert PIDS to Pid object's
        return a dict with
          - event, source key,values pairs
          - (type, data) key,value pairs,
        """
        from ccpn.core.lib.Pid import Pid  # this causes circular imports. KEEP LOCAL

        data = dict(
                event=event,
                source=None
                )

        if hasattr(event, 'source'):
            data['source'] = event.source()

        if hasattr(event, 'mimeData'):
            mimeData = event.mimeData()

            if mimeData.hasFormat(DropBase.JSONDATA):
                data['isCcpnJson'] = True
                with contextlib.suppress(Exception):
                    jsonData = json.loads(mimeData.text())
                    if jsonData is not None and len(jsonData) > 0:
                        data.update(jsonData)
                    if self.PIDS in data:
                        newPids = [Pid(pid) for pid in data[self.PIDS]]
                        data[self.PIDS] = newPids

            elif event.mimeData().hasUrls():
                # NOTE:ED - not sure which is correct
                # filePaths = [url.path() for url in event.mimeData().urls()]
                filePaths = [url.toLocalFile() for url in event.mimeData().urls()]
                data[self.URLS] = filePaths

            elif event.mimeData().hasText():
                data[self.TEXT] = event.mimeData().text()

        return data

    # def checkForBadDragEvent(self, ev):
    #
    #     from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModule
    #
    #     parentModule = self._findModule()
    #     if isinstance(ev.source(), CcpnModule) and self is not parentModule:
    #         if not hasattr(self, 'badDragEnter'):
    #             className = self.__class__.__name__
    #
    #             eventType = ''
    #             if isinstance(ev, QtGui.QDragMoveEvent):
    #                 eventType = 'move'
    #             elif isinstance(ev, QtGui.QDragEnterEvent):
    #                 eventType = 'enter'
    #
    #             getLogger().debug('received drag %s from %s which is not a module %i' % (eventType, className, id(self)))
    #
    #             self.badDragEnter = True

    def dragMoveEvent(self, ev):
        """drag move event that propagates through all the widgets
        """
        # self.checkForBadDragEvent(ev)

        parentModule = self._findModule()

        if parentModule:
            if parentModule.isDragToMaximisedModule(ev):
                parentModule.handleDragToMaximisedModule(ev)
                return

        if parentModule:
            data = self.parseEvent(ev)

            from ccpn.ui.gui.widgets.CcpnModuleArea import MODULEAREA_IGNORELIST

            # ignore dropAreas if the source of the event is in the list
            if isinstance(data['source'], MODULEAREA_IGNORELIST):
                return

            p = parentModule.mapFromGlobal(QtGui.QCursor().pos())

            ld = p.x()  # ev.pos().x()
            rd = parentModule.width() - ld
            td = p.y()  # ev.pos().y()
            bd = parentModule.height() - td

            mn = min(ld, rd, td, bd)
            if mn > 30:
                parentModule.dropArea = "center"
            elif (ld == mn or td == mn) and mn > parentModule.height() / 3.:
                parentModule.dropArea = "center"
            elif (rd == mn or ld == mn) and mn > parentModule.width() / 3.:
                parentModule.dropArea = "center"

            elif rd == mn:
                parentModule.dropArea = "right"
            elif ld == mn:
                parentModule.dropArea = "left"
            elif td == mn:
                parentModule.dropArea = "top"
            elif bd == mn:
                parentModule.dropArea = "bottom"

            if ev.source() is parentModule and parentModule.dropArea == 'center':
                #print "  no self-center"
                parentModule.dropArea = None
                # ev.ignore()

            elif parentModule.dropArea not in parentModule.allowedAreas:
                #print "  not allowed"
                parentModule.dropArea = None
                # ev.ignore()

            if 'urls' in data:
                # override the drop area overlay if coming from outside
                parentModule.dropArea = None

            # else:
            #     #print "  ok"
            #     ev.accept()
            parentModule.overlay.setDropArea(parentModule.dropArea)

    def _clearOverlays(self):
        """Clear the overlays for the containing CcpnModule
        """
        par = self._findModule()
        if par:
            par.dragLeaveEvent(None)

    def _callModuleDrop(self, ev):
        """Return true if the containing CcpnModule has been activated in one of the dropAreas
        """
        par = self._findModule()
        if par and par.dropArea:
            return par

    def dragLeaveEvent(self, ev):
        """Clear the overlays when leaving the widgetArea
        """
        par = self._findModule()
        if par:
            par.dragLeaveEvent(ev)
        self.inDragToMaximisedModule = False

    def _findModule(self):
        """Find the CcpnModule containing this widget
        """
        from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModule

        par = self
        while par:
            if isinstance(par, CcpnModule):
                return par
            par = par.parent()  # getParent() may be used for CCPN widgets, not for other QWidgets
