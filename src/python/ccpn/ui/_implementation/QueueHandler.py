"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-03-13 18:14:44 +0000 (Thu, March 13, 2025) $"
__version__ = "$Revision: 3.2.12 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-07 11:25:37 +0100 (Wed, September 07, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from typing import Callable
from PyQt5 import QtCore
from time import time_ns
from ccpn.core.lib.Notifiers import _removeDuplicatedNotifiers
from ccpn.util.Logging import getLogger
from ccpn.util.UpdateScheduler import UpdateScheduler
from ccpn.util.UpdateQueue import UpdateQueue
from ccpn.framework.Application import getApplication


_DEFAULT_QUEUE_LENGTH = 25


class QueueHandler():
    """Small class holding the queue-handler information.

    This class manages a queue system for handling update notifications.
    It supports processing queued tasks with a scheduler, ensures safe access with a mutex,
    and provides callbacks for queue completion and overflow handling.
    """
    _parent = None
    application = None
    project = None
    name = 'unknown'
    _scheduler: UpdateScheduler | None = None
    _queuePending: UpdateQueue
    _queueActive: UpdateQueue | None
    _lock: QtCore.QMutex
    _completeCallback = Callable | None
    _queueFullCallback = Callable | None

    # Queue handling parameters
    log = False
    maximumQueueLength: int = _DEFAULT_QUEUE_LENGTH

    def __init__(self, parent,
                 completeCallback: Callable | None = None,
                 queueFullCallback: Callable | None = None,
                 name: str = 'unknown',
                 log: bool = False,
                 maximumQueueLength: int | None = _DEFAULT_QUEUE_LENGTH):
        """Initialise the scheduler for the queue-handler.

        :param parent: The parent object that owns this queue handler.
        :type parent: object
        :param completeCallback: Optional callback executed when the queue becomes empty.
        :type completeCallback: Callable | None
        :param queueFullCallback: Optional callback executed when the queue exceeds `maximumQueueLength`.
        :type queueFullCallback: Callable | None
        :param name: The name identifier for this queue handler, defaults to 'unknown'.
        :type name: str
        :param log: Whether to enable logging for queue processing events, defaults to False.
        :type log: bool
        :param maximumQueueLength: The maximum number of events allowed in the queue.
        :type maximumQueueLength: int | None
        :raises TypeError: If any of the parameters are of an invalid type.
        :raises RuntimeError: If the application instance is not defined.
        """
        # check parameters
        if not parent:
            raise TypeError(f'{self.__class__.__name__}.__init__: parent is not defined')

        if not (callable(completeCallback) or completeCallback is None):
            raise TypeError(f'{self.__class__.__name__}.__init__: completeCallback is not callable|None')
        if not (callable(queueFullCallback) or queueFullCallback is None):
            raise TypeError(f'{self.__class__.__name__}.__init__: queueFullCallback is not callable|None')

        if not isinstance(name, str) or not name:
            raise TypeError(f'{self.__class__.__name__}.__init__: name is not of type str')
        if not isinstance(log, bool):
            raise TypeError(f'{self.__class__.__name__}.__init__: log is not True/False')
        if not isinstance(maximumQueueLength, (int, type(None))):
            raise TypeError(f'{self.__class__.__name__}.__init__: maximumQueueLength must be of type int|None')

        # store parameters
        self._parent = parent

        if not (app := getApplication()):
            raise RuntimeError(f'{self.__class__.__name__}.__init__: application is not defined')
        self.application = app
        self.project = app._project

        self.name = name
        self.log = log
        self._completeCallback = completeCallback
        self._queueFullCallback = queueFullCallback
        self._queuePending = UpdateQueue()
        self._queueActive = None
        self._lock = QtCore.QMutex()

        _project = getApplication().project

        # initialise a scheduler
        self._scheduler = UpdateScheduler(self.project, self._queueProcess, name, log, completeCallback)

    def __enter__(self) -> tuple[UpdateQueue | None, UpdateQueue, QtCore.QMutex]:
        """Enter the runtime context for the queue handler.

        :return: Tuple containing the active queue, pending queue, and lock.
        :rtype: tuple[UpdateQueue | None, UpdateQueue, QtCore.QMutex]
        """
        return self._queueActive, self._queuePending, self._lock

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object | None) -> None:
        """Exit the runtime context for the queue handler.

        :param exc_type: Exception type if an error occurred.
        :param exc_val: Exception value if an error occurred.
        :param exc_tb: Exception traceback if an error occurred.
        """
        pass

    def _queueGeneralNotifier(self, func: Callable, data: object) -> None:
        """Add a notifier function with data to the queue.

        :param func: The function to be added to the queue.
        :type func: Callable
        :param data: The data associated with the function call.
        :type data: object
        """
        self.queueAppend([func, data])

    def queueFull(self) -> None:
        """Handle cases when the queue is too large.

        This method is called when the queue exceeds `maximumQueueLength`.
        It triggers the `queueFullCallback`, if defined.
        """
        if self._queueFullCallback:
            self._queueFullCallback()

    def _queueProcess(self) -> None:
        """Process the current items in the queue.

        This method transfers pending queue items to the active queue
        and processes them sequentially. If the queue is too large,
        the `queueFull()` method is triggered instead.

        Any exceptions raised during queue execution are logged.
        """
        with QtCore.QMutexLocker(self._lock):
            # protect the queue switching
            self._queueActive = self._queuePending
            self._queuePending = UpdateQueue()

        _startTime = time_ns()
        _useQueueFull = (self.maximumQueueLength not in [0, None] and len(self._queueActive) > self.maximumQueueLength)
        if self.log:
            # log the queue-time if required
            getLogger().debug(f'_queueProcess  {self._parent}  len: {len(self._queueActive)}  '
                              f'useQueueFull: {_useQueueFull}')

        if _useQueueFull:
            # rebuild from scratch if the queue is too big
            if self.application and self.application._disableModuleException:
                self._queueActive = None
                self.queueFull()
            else:
                try:
                    self._queueActive = None
                    self.queueFull()
                except Exception as es:
                    getLogger().debug(f'Error in {self._parent.__class__.__name__} update queueFull: {es}')
        else:
            executeQueue = _removeDuplicatedNotifiers(self._queueActive)
            for itm in executeQueue:
                if self.application and self.application._disableModuleException:
                    func, data = itm
                    func(data)
                else:
                    # Exception is handled with debug statement
                    try:
                        func, data = itm
                        func(data)
                    except Exception as es:
                        getLogger().debug(f'Error in {self._parent.__class__.__name__} update - {es}')

        if self.log:
            getLogger().debug(f'_queueProcess  {self._parent}  elapsed time: {(time_ns() - _startTime) / 1e9}')

    def queueAppend(self, itm: list[Callable, object]) -> None:
        """Append a new item to the queue for processing.

        If the scheduler is not active or busy, it will be started automatically.

        :param itm: The item (function and data) to append to the queue.
        :type itm: tuple[Callable, object]
        """
        self._queuePending.put(itm)
        if not self._scheduler.isActive and not self._scheduler.isBusy:
            self._scheduler.start()
        elif self._scheduler.isBusy:
            # caught during the queue processing event, need to restart
            self._scheduler.signalRestart()
