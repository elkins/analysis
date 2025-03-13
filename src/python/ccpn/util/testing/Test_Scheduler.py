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
__date__ = "$Date: 2022-04-07 15:46:38 +0100 (Thu, April 07, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore
import sys
import random
import time
import unittest
import datetime
from functools import partial
from itertools import zip_longest

from ccpn.ui.gui.guiSettings import consoleStyle
from ccpn.util.UpdateQueue import UpdateQueue
from ccpn.util.UpdateScheduler import UpdateScheduler


def main():
    """Queue and scheduler testing

    Simulates multiple threads posting events and a user button also posting events.
    Example process prints labels and simulates taking two seconds to finish.
    """


    class SchedulerApplication(QtWidgets.QApplication):
        """Simple application class with timer to process a queue when not busy
        """

        def __init__(self, applicationName='Testing', applicationVersion='0.0.1', organizationName='CCPN',
                     organizationDomain='ccpn.ac.uk'):
            super().__init__([applicationName, ])

            self.setApplicationVersion(applicationVersion)
            self.setOrganizationName(organizationName)
            self.setOrganizationDomain(organizationDomain)

            self._queuePending = UpdateQueue()
            self._queueActive = None
            self._scheduler = UpdateScheduler(self, self._queueProcess, name='QueueTester', log=False,
                                              completeCallback=None)

            self._lock = QtCore.QMutex()
            self._counter = 0
            self.realEvents = []
            self.handledEvents = []
            self._progressSuspension = 0

        def start(self):
            print(f'{consoleStyle.fg.green}   GO!                 {datetime.datetime.now()}{consoleStyle.reset}')
            # start loading random stuff on the queue form two threads
            QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread1'))
            QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread2'))
            QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread3'))

            def _enableBlocking():
                print(f'{consoleStyle.fg.red}BLOCKING{consoleStyle.reset}')
                self._progressSuspension = 1

            def _disableBlocking():
                print(f'{consoleStyle.fg.red}BLOCKING RELEASED{consoleStyle.reset}')
                self._progressSuspension = 0

            # block after 3 seconds - simulate overriding block
            QtCore.QTimer.singleShot(3000, _enableBlocking)
            # unblock after 7 seconds - simulate overriding block
            QtCore.QTimer.singleShot(7000, _disableBlocking)

            self.exec_()

        def _queueProcess(self):
            """Process current items in the queue
            """
            print(f'{consoleStyle.fg.blue}   processing                 {datetime.datetime.now()}{consoleStyle.reset}')
            with QtCore.QMutexLocker(self._lock):
                # protect the queue switching
                self._queueActive = self._queuePending
                self._queuePending = UpdateQueue()

            print(f'{consoleStyle.fg.blue}   len {len(self._queueActive)}{consoleStyle.reset}')
            vals = []
            for itm in list(self._queueActive.items()):
                vals.append(itm)
            print(f'{consoleStyle.fg.blue}       {vals}{consoleStyle.reset}')

            # example pause for 1 second whilst processing events (may happen in qui)
            for ii in range(20):
                self.processEvents()
                time.sleep(1 / 20)
            self.handledEvents.extend(vals)
            print(f'{consoleStyle.fg.blue}       {vals} - end sleep{consoleStyle.reset}')

        def _queueAppend(self, itm):
            """Append a new item to the queue
            """
            self._queuePending.put(itm)
            if not self._scheduler.isActive and not self._scheduler.isBusy:
                print(f'{consoleStyle.fg.magenta}   append & run                    {datetime.datetime.now()}'
                      f'      {itm}{consoleStyle.reset}')
                self._scheduler.start()

            elif self._scheduler.isBusy:
                print(f'{consoleStyle.fg.magenta}   append busy                     {datetime.datetime.now()}'
                      f'      {itm}{consoleStyle.reset}')
                self._scheduler.signalRestart()

            elif self._scheduler.isActive:
                print(f'{consoleStyle.fg.magenta}   append queued                   {datetime.datetime.now()}'
                      f'      {itm}{consoleStyle.reset}')

        def _namedQTimerThread(self, name, count=0):
            """Randomly add items to the queue
            """
            val = f'{consoleStyle.fg.yellow}{name} - {count}{consoleStyle.reset}'

            # add to the deferred queue and store in the realEvents list which holds when the events were created
            self._queueAppend(val)
            self.realEvents.append(val)

            if count < 15:
                # create another random event
                QtCore.QTimer.singleShot(int(random.random() * 800) + 200,
                                         partial(self._namedQTimerThread, name, count + 1))

        def _buttonClicked(self, *args):
            """Handle user clicking button
            """
            if self._counter < 30:
                # add to the deferred queue and store in the realEvents list which holds when the events were created
                self._queueAppend(self._counter)
                self.realEvents.append(self._counter)

                self._counter += 1


    app = SchedulerApplication()

    # make a mall window with a button that adds events to the queue
    window = QtWidgets.QMainWindow()
    fr1 = QtWidgets.QFrame()
    _layout = QtWidgets.QGridLayout()
    fr1.setLayout(_layout)
    window.setCentralWidget(fr1)
    _button = QtWidgets.QPushButton('HELP')
    _layout.addWidget(_button, 0, 0)
    _button.clicked.connect(app._buttonClicked)

    window.show()
    app.start()

    print('\n'.join([f'{qVal}    {rVal}' for qVal, rVal in zip_longest(app.handledEvents, app.realEvents)]))
    assert app.handledEvents == app.realEvents


class SchedulerTester(QtCore.QObject):
    """Queue and scheduler testing

    Simulates multiple threads posting events.
    Example process add labels to a list and simulates taking two seconds to finish.
    """
    threadFinished = QtCore.pyqtSignal(str)

    def __init__(self, application):
        super().__init__()

        self._application = application
        self._queuePending = UpdateQueue()
        self._queueActive = None
        self._scheduler = UpdateScheduler(self, self._queueProcess, name='QueueTester',
                                          log=False, completeCallback=self._finalise)

        self._lock = QtCore.QMutex()
        self._counter = 0
        self.realEvents = []
        self.handledEvents = []
        self._progressSuspension = 0
        self.exitSignal = False

    def start(self):
        print(f'{consoleStyle.fg.green}   GO!                 {datetime.datetime.now()}{consoleStyle.reset}')

        # start loading random stuff on the queue form two threads
        QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread1', priority=1))
        QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread2', priority=1))
        QtCore.QTimer.singleShot(0, partial(self._namedQTimerThread, 'thread3', priority=1))

        def _enableBlocking():
            print(f'{consoleStyle.fg.red}BLOCKING{consoleStyle.reset}')
            self._progressSuspension = 1

        def _disableBlocking():
            print(f'{consoleStyle.fg.red}BLOCKING RELEASED{consoleStyle.reset}')
            self._progressSuspension = 0

        # block after 7 seconds - simulate overriding block
        QtCore.QTimer.singleShot(7000, _enableBlocking)
        # unblock after 10 seconds - simulate overriding block
        QtCore.QTimer.singleShot(11000, _disableBlocking)

    def _queueProcess(self):
        """Process current items in the queue
        """
        print(f'{consoleStyle.fg.blue}   processing                 {datetime.datetime.now()}{consoleStyle.reset}')
        print(f'{consoleStyle.fg.darkmagenta}~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
              f'{consoleStyle.reset}')
        with QtCore.QMutexLocker(self._lock):
            # protect the queue switching
            self._queueActive = self._queuePending
            self._queuePending = UpdateQueue()

        vals = list(self._queueActive.items())

        # example pause for 1 second whilst processing events (may happen in qui)
        for _ in range(20):
            self._application.processEvents()
            time.sleep(0.1)

        # add the events to the processed queue
        self.handledEvents.extend(vals)
        print(f'{consoleStyle.fg.blue}       {vals} - end sleep{consoleStyle.reset}')

    def _queueAppend(self, itm, *, priority=1):
        """Append a new item to the queue
        """
        self._queuePending.put(itm, priority=priority)
        if not self._scheduler.isActive and not self._scheduler.isBusy:
            print(f'{consoleStyle.fg.darkyellow}   append & run                    {datetime.datetime.now()}     '
                  f' {itm}{consoleStyle.reset}')
            self._scheduler.start()

        elif self._scheduler.isBusy:
            print(f'{consoleStyle.fg.darkyellow}   append busy                     {datetime.datetime.now()}      '
                  f'{itm}{consoleStyle.reset}')
            self._scheduler.signalRestart()

        else:
            print(f'{consoleStyle.fg.darkyellow}   append queued                   {datetime.datetime.now()}      '
                  f'{itm}{consoleStyle.reset}')
        for itm in self._queuePending.items():
            print(itm)

    def _namedQTimerThread(self, name, *, priority=1, count=0):
        """Add items to the queue at random intervals
        """
        val = f'{name} - {priority}:{count}'
        print(f'{consoleStyle.fg.darkblue}new event  -  _namedQTimerThread  {val}{consoleStyle.reset}')

        # add to the deferred queue and store in the realEvents list which holds when the events were created
        self._queueAppend(val, priority=priority)
        self.realEvents.append(val)

        if count < 15:
            # create another random event
            QtCore.QTimer.singleShot(int(random.random() * 800) + 200,
                                     partial(self._namedQTimerThread, name, priority=priority, count=count + 1))

        else:
            self.exitSignal += 1
            self.threadFinished.emit(name)

    def _finalise(self):
        """Action when the current queue has been emptied
        """
        print(f'{consoleStyle.fg.darkblue}   active queue processed - pending queue contains '
              f'{len(self._queuePending)} items{consoleStyle.reset}')

    @property
    def queueEmpty(self):
        """Return True if there are no more active/pending items
        """
        return not self._queueActive or not self._queuePending


class TestScheduler(unittest.TestCase):
    """Test-case to check that the queued events are processed in the same order that they are created
    """

    @staticmethod
    def _queueEnd():
        print(f'{consoleStyle.fg.red}END{consoleStyle.reset}')

    def test_scheduler(self):
        # create a simple app
        app = QtWidgets.QApplication(sys.argv)

        # create and start a scheduler test-case
        obj = SchedulerTester(app)
        obj.threadFinished.connect(self._threadFinished)
        obj.start()

        # wait until all the threads have finished
        while obj.exitSignal < 3 or not obj.queueEmpty:
            time.sleep(0.1)
            app.processEvents()

        # process any remaining threads/timers
        QtCore.QTimer.singleShot(0, self._queueEnd)
        app.processEvents()

        # print out the final list of processes and check the order
        print('\n'.join([f'{qVal}    {rVal}' for qVal, rVal in zip_longest(obj.handledEvents, obj.realEvents)]))
        self.assertListEqual(obj.handledEvents, obj.realEvents)
        # not sure how to check/test different priorities other than visually at the end

    @staticmethod
    @QtCore.pyqtSlot(str)
    def _threadFinished(name):
        """Thread has completed all tasks
        """
        print(f'{consoleStyle.fg.yellow}thread finished - {name}{consoleStyle.reset}')


if __name__ == '__main__':
    main()
