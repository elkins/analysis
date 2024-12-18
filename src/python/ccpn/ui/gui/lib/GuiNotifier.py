"""
Notifier extensions for Gui objects, wrapping it into a class that also acts as the called 
function, displatching the 'user' callback if required.
The Notifier can be defined relative to any valid V3 Widget
object as it first checks if the triggered signature is valid.

The callback function is passed a callback dictionary with relevant info (see
docstring of Notifier class. This idea was copied from the Traitlets package.

Very similar (and if fact based upon) the Notifier Class for core objects,
but separate to keep graphics code isolated

April 2017: First design by Geerten Vuister

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
__dateModified__ = "$dateModified: 2024-12-18 13:24:48 +0000 (Wed, December 18, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-18 15:19:30 +0100 (Tue, April 18, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys

from functools import partial
from collections import OrderedDict
from typing import Callable, Any, Optional

from PyQt5 import QtGui, QtWidgets

from ccpn.core.lib.Notifiers import NotifierABC
from ccpn.ui.gui.widgets.DropBase import DropBase

from ccpn.util.Logging import getLogger


logger = getLogger()

# ED: not sure what this if for, but pycharm complains about the arguments
# def skip(*args, **kwargs):
#     "Do nothing"
#     pass


class GuiNotifier(NotifierABC):
    """
     GuiNotifier class:

    triggers callback function with signature:  callback(callbackDict [, *args] [, **kwargs])

    ____________________________________________________________________________________________________________________

    trigger             targetName           callbackDict keys          Notes
    ____________________________________________________________________________________________________________________

    Notifier.DROPEVENT  [dropTargets]         theObject,                theObject should inherit from QtWidgets.QWidget
                                                                        and be droppable
                                              targetName                targetName: optional dropTargets to filter for
                                                                        before callback (None to skip), as defined in
                                                                        DropBase
                                              trigger,
                                              notifier,
                                              event, isCcpnJson,
                                              [dropTargets]


    dropTargets: keywords defining type of dropped objects: currently implemented: 'urls', 'text', 'pids' (see DropBase)

    Implemention:

      The callback provides a dict with several key, value pairs and optional arguments and/or keyword
      arguments if defined in the instantiation of the Notifier object. (idea following the Traitlets concept).
      Note that this dict also contains a reference to the GuiNotifier object itself; this way it can be used
      to pass-on additional implementation specfic information to the callback function.

      On Intialisation, the GuiNotifier instance sets the appropriate callback functions of the widget,
      as defined in DropBase, from which each Ccpn-Widget derives.

    """

    # Trigger keywords
    DROPEVENT = 'dropEvent'
    ENTEREVENT = 'enterEvent'
    DRAGMOVEEVENT = 'dragMoveEvent'
    _triggerKeywords = (DROPEVENT, ENTEREVENT, DRAGMOVEEVENT)

    def __init__(self, theObject: Any, triggers: list, targetName: list,
                 callback: Callable[..., Optional[str]], debug=False, **kwargs):
        """
        Create GuiNotifier object;

        :param theObject: Widget to watch
        :param triggers: list of trigger keywords callback; i.e. (DROPEVENT, ENTEREVENT, DRAGMOVEEVENT)
        :param targetName: optional list of dropTargets (URLS, TEXT, PIDS, IDS) or None
        :param callback: callback function with signature: callback(callbackDict [, *args] [, **kwargs])
        :param debug: set debug
        :param **kwargs: optional keyword,value arguments to callback
        """
        super().__init__(theObject=theObject, triggers=triggers, targetName=targetName, debug=debug,
                         callback=callback, **kwargs
                         )

        # some sanity checks
        if not isinstance(theObject, QtWidgets.QWidget):
            raise RuntimeError('Invalid object (%r), expected object of type QWidget' % theObject)

        self._unregister = []  # list of tuples needed for unregistering

        # register the callbacks
        for trigger in self._triggers:

            if trigger == GuiNotifier.DROPEVENT:

                # if not self._theObject.acceptDrops():
                #     raise RuntimeError('GuiNotifier.__init__: Widget "%s" does not accept drops' % self._theObject)

                if targetName is not None:
                    for target in targetName:
                        if target not in DropBase._dropTargets:
                            raise RuntimeError('GuiNotifier.__init__: invalid dropTarget "%s"' % (target))

                notifier = (trigger, targetName)
                self._theObject.setDropEventCallback(partial(self, notifier=notifier))
                self._unregister.append((trigger, targetName))
                self._isRegistered = True

            elif trigger == GuiNotifier.ENTEREVENT:
                notifier = (trigger, targetName)
                self._theObject.setDragEnterEventCallback(partial(self, notifier=notifier))
                self._unregister.append((trigger, targetName))
                self._isRegistered = True

            elif trigger == GuiNotifier.DRAGMOVEEVENT:
                notifier = (trigger, targetName)
                self._theObject.setDragMoveEventCallback(partial(self, notifier=notifier))
                self._unregister.append((trigger, targetName))
                self._isRegistered = True

        if not self.isRegistered():
            raise RuntimeWarning('GuiNotifier.__init__: no notifiers intialised for theObject=%s, targetName=%r, triggers=%s ' % \
                                 (theObject, targetName, triggers))
        if self._debug:
            sys.stderr.write('>>> registered %s\n' % self)

    def unRegister(self):
        """
        unregister the notifiers
        """
        if not self.isRegistered():
            return

        for trigger, targetName in self._unregister:
            if trigger == GuiNotifier.DROPEVENT:
                self._theObject.setDropEventCallback(None)
            elif trigger == GuiNotifier.ENTEREVENT:
                self._theObject.setDragEnterEventCallback(None)
            elif trigger == GuiNotifier.DRAGMOVEEVENT:
                self._theObject.setDragMoveEventCallback(None)

        super().unRegister()  # the end as it clears all attributes

    def __call__(self, data: dict, notifier: tuple = None):
        """
        wrapper, accommodating the different triggers before firing the callback
        """
        if not self.isRegistered():
            logger.warning('Triggering unregistered guiNotifier %s' % self)
            return

        if self._isBlanked:
            return

        trigger, targetName = notifier

        if self._debug:
            sys.stderr.write('>>> Notifier.__call__: %s \n--> notifier=%s data=%s\n' % \
                             (self, notifier, data)
                             )

        # DROPEVENT
        if trigger == GuiNotifier.DROPEVENT:
            # optionally filter for targetName
            skip = False
            if targetName is not None:
                skip = True
                for target in targetName:
                    if target in data.keys():
                        skip = False
                        break
            if skip: return

        callbackDict = dict(
                notifier=self,
                trigger=trigger,
                theObject=self._theObject,
                targetName=targetName,
                )
        callbackDict.update(data)
        self._callback(callbackDict, **self._kwargs)
        return


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.BasePopup import BasePopup
    from ccpn.ui.gui.widgets.Label import Label
    from ccpn.ui.gui.widgets.Widget import Widget
    from ccpn.ui.gui.widgets.Button import Button

    from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


    class MyWidget(Widget):
        buttonPressed1 = pyqtSignal(str)
        buttonPressed2 = pyqtSignal(dict)

        def __init__(self, parent, name, **kwds):
            super(MyWidget, self).__init__(parent=parent, setLayout=True, **kwds)
            self.name = name
            self.label = Label(parent=self, grid=(0, 0), text=name, bold=True, textColour='black', textSize='18')
            self.button = Button(parent=self, grid=(1, 0), text='Button-' + name, callback=self._pressed)

        def _pressed(self):
            bText = self.button.getText()
            print(bText + ' was pressed')
            # str signal
            self.buttonPressed1.emit(bText)
            # dict signal
            bDict = {'text': bText}
            self.buttonPressed2.emit(bDict)

        @pyqtSlot(str)
        def _receivedSignal1(self, text):
            print(self.name + ' received signal1:', text)

        @pyqtSlot(dict)
        def _receivedSignal2(self, aDict):
            print(self.name + ' received signal2:', aDict)


    class TestPopup(BasePopup):
        def body(self, parent):
            mainWidget = Widget(parent, setLayout=True)
            widget1 = MyWidget(parent=mainWidget, name='Widget-1', grid=(0, 0), bgColor=(255, 255, 0))
            widget2 = MyWidget(parent=mainWidget, name='Widget-2', grid=(1, 0), bgColor=(255, 0, 0))
            # connect the signals to the str variant
            widget1.buttonPressed1.connect(widget2._receivedSignal1)  # widget2 listens to widget1.buttonPressed1 signal
            widget2.buttonPressed1.connect(widget1._receivedSignal1)  # widget1 listens to widget1.buttonPressed1 signal
            # connect the signals to the dict variant
            widget1.buttonPressed2.connect(widget2._receivedSignal2)  # widget2 listens to widget1.buttonPressed2 signal
            widget2.buttonPressed2.connect(widget1._receivedSignal2)  # widget1 listens to widget1.buttonPressed2 signal


    app = TestApplication()
    popup = TestPopup(title='Testing slots and signals', setLayout=True)
    popup.resize(200, 400)
    app.start()
