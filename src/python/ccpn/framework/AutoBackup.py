"""
This file contains AutoBackup class
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
__dateModified__ = "$dateModified: 2024-10-02 10:04:24 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2022-02-05 10:28:48 +0000 (Saturday, February 5, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from time import time, perf_counter
from queue import Queue
from PyQt5 import QtCore
from math import isclose

from ccpn.framework import Application
from ccpn.ui.gui.guiSettings import consoleStyle
from ccpn.util.Logging import getLogger


CEND = consoleStyle.reset


class AutoBackupHandler:
    """Class to handle backups

    Has 2 timers:
    One to run at a specified interval to check whether the gui has been idle for sufficient time.
    Other to perform the backup.
    """
    _checkIdleQueue = Queue(maxsize=3)
    _busy = False
    _backupEnabled = False

    def __init__(self, eventFunction, eventInterval=1800):
        """Initialise the class.

        :param callable eventFunction: function to call when system considered idle.
        :param int eventInterval: number of seconds to wait between events.
        """
        # this is a hack as the loggers are a mess
        if Application.getApplication().args.debug3_backup_thread:
            self._logger = getLogger().debug3
        else:
            self._logger = lambda x: ...

        self._eventFunction = eventFunction
        self._eventInterval = int(eventInterval * 1000)
        self._qTimerInterval = -1
        self._backupEnabled = False  # needs an explicit start-event
        self._time = perf_counter()
        self._backupModifiedTime = perf_counter()

        # initialise the timers
        self._createTimers()

        self._logger(f'event thread created {time()}{CEND}')
        self._lock = QtCore.QMutex()

    def _createTimers(self):
        """Create timers
        """
        self._logger(f'{consoleStyle.fg.green}new timer interval {self._eventInterval}{CEND}')

        # interval checking timer
        self._qTimer = tt = QtCore.QTimer()
        tt.setSingleShot(True)
        tt.timeout.connect(self._timerEvent)
        # timer to check that the system is idle(ish)
        self._idleTimer = tt = QtCore.QTimer()
        tt.setSingleShot(True)
        tt.setInterval(0)
        tt.timeout.connect(self._updateQTimer)

        # quick debug-timer to show the activity every few seconds
        # self.__timerLog = tt = QtCore.QTimer()
        # tt.setSingleShot(False)
        # tt.setInterval(5000)
        # tt.timeout.connect(lambda: self._logger(f'{consoleStyle.fg.green} --> time '
        #                                         f'{self._qTimer.isActive()}:{self._backupEnabled}:'
        #                                         f'{self._qTimer.remainingTime()}{CEND}'))
        # tt.start()
        self._resetQueue()

    @property
    def backupEnabled(self) -> bool:
        """Return True if backups are enabled.
        It can also be true if the backups have been disabled or killed.
        This determines whether a new backup is scheduled automatically from a previous backup.
        """
        return self._backupEnabled

    def setEnabled(self, state: bool):
        """Set the backup-enabled state.
        True -> backups will execute at regular intervals as specified by _eventInterval.
        """
        self._backupEnabled = state

    def start(self):
        """Start the timer
        """
        interval = self._eventInterval if self._qTimerInterval == -1 else self._qTimerInterval
        self._start(interval)
        self._qTimerInterval = -1
        self._logger(f'{consoleStyle.fg.green} --> starting {interval}{CEND}')

    def stop(self):
        """Stop the timer.
        """
        self._qTimerInterval = self._qTimer.remainingTime()
        self._stopQTimers()
        self._resetQueue()
        self._busy = False
        self._logger(f'{consoleStyle.fg.cyan} --> clear - {self._qTimerInterval}{CEND}')

    def _stopQTimers(self):
        """Stop the timer.
        """
        # make sure that nothing is running
        self._qTimer.stop()
        self._idleTimer.stop()

    def kill(self):
        """Kill the timer.
        """
        self._qTimerInterval = -1
        self._stopQTimers()
        self._resetQueue()
        self._busy = False
        self._logger(f'{consoleStyle.fg.darkred} --> kill - {self._qTimerInterval}{CEND}')

    def setInterval(self, interval):
        """Set the interval between events.

        :param int interval: time between events in seconds.
        """
        self._stopQTimers()
        self._resetQueue()
        self._eventInterval = int(interval * 1000)
        self._logger(f'{consoleStyle.fg.cyan} --> setinterval {interval}{CEND}')

    def _resetQueue(self):
        """Reset interval timer queue
        - system needs to wait until full again before executing scheduled event.
        """
        # empty the timer queues
        while not self._checkIdleQueue.empty():
            self._checkIdleQueue.get()

    def _start(self, interval=0):
        """Start the timer.
        """
        # clean up timers
        self._stopQTimers()
        self._time = perf_counter()
        # restart the interval timer
        self._qTimer.start(interval)
        self._logger(f'{consoleStyle.fg.cyan} --> _start {interval}{CEND}')

    def _timerEvent(self):
        # update the timer-queue when next idle
        self._idleTimer.start()

    def _updateQTimer(self):
        """Check whether enough idle intervals have passed.
        This is called when idle.
        """
        self._busy = True
        if self._checkIdleQueue.full():
            # make room for the next time
            self._checkIdleQueue.get()
        delta = round(perf_counter() - self._time, 3)
        self._checkIdleQueue.put(delta)
        self._logger(f'{consoleStyle.fg.lightgrey} --> update idle {delta}  {self._checkIdleQueue.queue}{CEND}')

        if self._isIdle:
            try:
                with QtCore.QMutexLocker(self._lock):
                    # lock the backup thread to protect the save-operation
                    t0 = perf_counter()
                    # check if the app is busy, and ignore until next time
                    self._logger(f'{consoleStyle.fg.yellow} --> calling event {self._eventFunction}{CEND}')
                    self._eventFunction()
                    self._resetQueue()
                    if self._backupEnabled:
                        # autoBackups are enabled so restart
                        self._start(self._eventInterval)
                    self._logger(f'{consoleStyle.fg.lightgrey} --> elapsed time '
                                 f'{round(perf_counter() - t0, 3)}:{self._backupEnabled}:{self._eventInterval}{CEND}')
            finally:
                # clean up busy-state
                self._busy = False
        else:
            # restart when gui is idle, check every second until event is performed
            self._logger(f'{consoleStyle.fg.darkyellow} --> thread is busy, waiting {CEND}')
            self._start(1000)

    @property
    def _isIdle(self) -> bool:
        """Check whether the UI is idle.
        gets the performance-queue from the singleshot-events and checks whether all are within tolerance,
        True -> nothing has happened for a few seconds.
        """
        qq = list(self._checkIdleQueue.queue)
        if check := all(isclose(qVal, 1.0, abs_tol=2e-2) for qVal in qq):
            self._logger(f'{consoleStyle.fg.yellow} --> QUEUE {qq}  {check}  {CEND}')
        return check and self._checkIdleQueue.full()

    def manualBackup(self, autoBackupEnabled: bool):
        """Trigger a manual firing of the eventFunction.
        """
        if self._busy:
            # currently in the backup operation (although should technically be covered by the mutex)
            self._logger(f'{consoleStyle.fg.red} --> BUSY {CEND}')
            return
        self.stop()
        self._logger(f'{consoleStyle.fg.green} --> manualBackup {self._backupEnabled}{CEND}')
        # spawn a backup event
        self._updateQTimer()
