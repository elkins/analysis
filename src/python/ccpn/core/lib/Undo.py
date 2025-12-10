"""General undo handle supporting undo/redo stack

PyApiGen.py inserts the following line:

from ccpn.core.lib.Undo import _deleteAllApiObjects, restoreOriginalLinks, no_op

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
__dateModified__ = "$dateModified: 2025-05-02 10:38:36 +0100 (Fri, May 02, 2025) $"
__version__ = "$Revision: 3.3.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import threading
from enum import Enum
from functools import partial, update_wrapper
from collections import deque

from ccpn.util.Logging import getLogger
from ccpn.util.OrderedSet import OrderedSet


MAXUNDOWAYPOINTS = 50
MAXUNDOOPERATIONS = 1000000


def _deleteAllApiObjects(objsToBeDeleted):
    """Delete all API objects in collection, together.
    Does NOT look for additional deletes or do any checks. Programmer beware!!!
    Does NOT do undo handling, as it is designed to be used within the Undo machinery
    """

    # CCPNINTERNAL
    # NBNB Use with EXTREME CARE, and make sure you get ALL API objects being created

    for obj in objsToBeDeleted:
        if (obj.__dict__.get('isDeleted')):
            raise ValueError("""%s: _deleteAllApiObjects
       called on deleted object""" % obj.qualifiedName
                             )

    for obj in objsToBeDeleted:
        for notify in obj.__class__._notifies.get('preDelete', ()):
            notify(obj)

    for obj in objsToBeDeleted:
        # objsToBeDeleted is passed in so that the references to the children of object are severed
        obj._singleDelete(objsToBeDeleted)

    # do Notifiers
    for obj in objsToBeDeleted:
        for notify in obj.__class__._notifies.get('delete', ()):
            notify(obj)


def restoreOriginalLinks(obj2Value, linkName):
    """Set obj values using obj2Value dictionary"""
    for obj, val in obj2Value.items():
        setattr(obj, linkName, val)


def no_op():
    """Does nothing - for special undo situations where only one direction must act"""
    return


def resetUndo(memopsRoot, maxWaypoints=MAXUNDOWAYPOINTS, maxOperations=MAXUNDOOPERATIONS,
              debug: bool = False, application=None):
    """Set or reset undo stack, using passed-in parameters.
    NB setting either parameter to 0 removes the undo stack."""

    undo = memopsRoot._undo
    if undo is not None:
        undo.clear()

    if maxWaypoints and maxOperations:
        memopsRoot._undo = Undo(maxWaypoints=maxWaypoints, maxOperations=maxOperations,
                                debug=debug, application=application)
    else:
        memopsRoot._undo = None


class UndoEvents(Enum):
    UNDO_UNDO = 1
    UNDO_REDO = 2
    UNDO_CLEAR = 3
    UNDO_ADD = 4
    UNDO_MARK_SAVE = 5
    UNDO_MARK_CLEAN = 6


class UndoObserver():
    """
    Class to store functions to call when undo stack operations are performed
    """

    def __init__(self):
        self._callbacks = OrderedSet()

    def add(self, callback):
        self._callbacks.add(callback)

    def clear(self):
        self._callbacks.clear()

    def remove(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def call(self, action):
        for callback in self._callbacks:
            action(callback)


#=========================================================================================
# Undo
#=========================================================================================

class Undo(deque):
    """Implementation of an undo and redo stack, with possibility of waypoints.
       A waypoint is the level at which an undo happens, and each of them could
       consist of multiple individual undo operations.

       To create a waypoint use newWaypoint().
    """

    # TODO: get rid of debug and use logging function instead
    def __init__(self, maxWaypoints=MAXUNDOWAYPOINTS, maxOperations=MAXUNDOOPERATIONS, debug=False, application=None):
        """Create Undo object with maximum stack length maxUndoCount"""

        self.maxWaypoints = maxWaypoints
        self.maxOperations = maxOperations
        self.nextIndex = 0  # points to next free slot (or first slot to redo)
        self.waypoints = []  # array of last item in each waypoint
        self._blocked = False  # Block/unblock switch - internal use only
        self._undoItemBlockingLevel = 0  # Blocking level - modify with increase/decreaseBlocking only
        self._waypointBlockingLevel = 0  # Waypoint blocking - modify with increase/decreaseWaypointBlocking/ only
        self._storageBlockingLevel = 0  # Waypoint blocking - modify with increase/decreaseWaypointBlocking/ only
        self._newItemCount = 0  # the number of new items that have been added since the last new waypoint
        self._itemAtLastSave = None
        self._lastEventMarkClean = True
        self.undoChanged = UndoObserver()

        if maxWaypoints:
            self.newWaypoint()  # DO NOT CHANGE THIS ONE
        deque.__init__(self)

        # Set to True to un-blank errors during undo/redo
        self._debug = debug
        self.application = application

        # CCPNInternal - required for v2 pytests that do not create v3-application
        self._allowNoApplication = False
        self._lastFuncCall = None

        self._lock: threading.Lock = threading.Lock()

    @property
    def undoItemBlocking(self):
        """Undo blocking. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""
        return self._undoItemBlockingLevel > 0

    @property
    def undoItemBlockingLevel(self):
        """Undo blocking Level. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""

        # needed for a single occurrence in api
        return self._undoItemBlockingLevel

    def markSave(self):
        if len(self) > 0:
            lastItem = self.nextIndex - 1
            try:
                self._itemAtLastSave = self[lastItem]
            except IndexError as ie:
                getLogger().debug('Error on markSave %s' % ie)
        self._lastEventMarkClean = True
        self.undoChanged.call(lambda x: x(UndoEvents.UNDO_MARK_SAVE))

    def isDirty(self):
        result = False
        lastItem = self.nextIndex - 1
        try:
            if len(self) > 0 and (self._itemAtLastSave is None):
                result = True
            elif len(self) > 0 and lastItem > 0 and (self[lastItem] != self._itemAtLastSave):
                result = True
        except IndexError as ie:
            getLogger().debug('Error checking isDirty %s' % ie)
        return result

    def markClean(self):
        self._itemAtLastSave = None
        self._lastEventMarkClean = True
        self.undoChanged.call(lambda x: x(UndoEvents.UNDO_MARK_CLEAN))

    def markUndoClear(self):
        self._itemAtLastSave = None
        self._lastEventMarkClean = True
        self.undoChanged.call(lambda x: x(UndoEvents.UNDO_CLEAR))

    def increaseBlocking(self):
        """Set one more level of blocking"""
        self._undoItemBlockingLevel += 1

    def decreaseBlocking(self):
        """Reduce level of blocking - when level reaches zero, undo is unblocked"""
        if self._undoItemBlockingLevel > 0:
            self._undoItemBlockingLevel -= 1

    def increaseStorageBlocking(self):
        """Set one more level of storage-blocking"""
        self._storageBlockingLevel += 1

    def decreaseStorageBlocking(self):
        """Reduce level of storage-blocking - when level reaches zero, undo is unblocked"""
        if self._storageBlockingLevel > 0:
            self._storageBlockingLevel -= 1

    @property
    def storageBlockingLevel(self):
        return self._storageBlockingLevel

    @property
    def undoList(self):
        try:
            undoState = (self.maxWaypoints,
                         self.maxOperations,
                         self.nextIndex,
                         self.waypoints,
                         self._blocked,
                         self.undoItemBlocking,
                         len(self),
                         self._newItemCount,
                         self[-1],
                         [(undoFunc[0].__name__, undoFunc[1].__name__) for undoFunc in self],
                         [undoFunc[0].__name__ for undoFunc in self],
                         [undoFunc[1].__name__ for undoFunc in self])
        except Exception:
            undoState = (self.maxWaypoints,
                         self.maxOperations,
                         self.nextIndex,
                         self.waypoints,
                         self._blocked,
                         self.undoItemBlocking,
                         len(self),
                         self._newItemCount,
                         None, None, None, None)
        return undoState

    @property
    def waypointBlocking(self):
        """Undo blocking. If true (non-zero) undo setting is blocked.
        Allows multiple external functions to set blocking without trampling each other

        Modify with increaseBlocking/decreaseBlocking only"""
        return self._waypointBlockingLevel > 0

    def increaseWaypointBlocking(self):
        """Set one more level of blocking"""
        self._waypointBlockingLevel += 1

    def decreaseWaypointBlocking(self):
        """Reduce level of blocking - when level reaches zero, undo is unblocked"""
        if self.waypointBlocking:
            self._waypointBlockingLevel -= 1

    def newWaypoint(self):
        """Start new waypoint
        """
        if self.maxWaypoints < 1:
            raise ValueError("Attempt to set waypoint on Undo object that does not allow them")

        waypoints = self.waypoints

        if self._blocked or self._undoItemBlockingLevel or self.waypointBlocking:  # ejb - added self._blocked 9/6/17
            return

        # set the number of items added to the undo deque since the new waypoint was created
        self._newItemCount = 0

        if self.nextIndex < 1:
            return

        if waypoints and waypoints[-1] == self.nextIndex - 1:  # don't need to add a new waypoint
            return  # if is the same as the last one

        waypoints.append(self.nextIndex - 1)  # add the new waypoint to the end

        # if the list is too big then cull the first item
        if len(waypoints) > self.maxWaypoints:
            nRemove = waypoints[0]
            self.nextIndex -= nRemove
            for ii in range(nRemove):
                _popLeftItem = self.popleft()

            del waypoints[0]
            for ii, junk in enumerate(waypoints):
                waypoints[ii] -= nRemove

    @staticmethod
    def _wrappedPartial(func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func

    def _newItem(self, undoPartial=None, redoPartial=None):
        """Add predefined partial(*) item to the undo stack.
        """
        if self._blocked or self._undoItemBlockingLevel:
            return

        if self._debug:
            getLogger().debug2('undo._newItem %s %s %s' % (self.undoItemBlocking, undoPartial,
                                                          redoPartial))

        # clear out redos that are no longer going to be doable
        for n in range(len(self) - self.nextIndex):
            self.pop()

        # add new undo/redo methods to the deque - keep a count
        self.append((undoPartial, redoPartial))
        self._newItemCount += 1

        # fix waypoints:
        ll = self.waypoints
        _waypoints = [ii for ii, wp in enumerate(ll) if wp == ll[-1]]
        if _waypoints:
            if len(_waypoints) > 2:
                raise RuntimeError('waypoint length error')
            # need to back-track to the previous value if duplicated
            ll[:] = ll[:_waypoints[0] + 1]
        while ll and ll[-1] >= self.nextIndex:
            ll.pop()

        # correct for maxOperations
        if len(self) > self.maxOperations:
            self.popleft()
            ll = self.waypoints
            if ll:
                for n, val in enumerate(ll):
                    ll[n] = val - 1
                if ll[0] < 0:
                    del ll[0]
        else:
            self.nextIndex += 1

        if self._lastEventMarkClean:
            # NOTE:ED - only do it for the first new item?
            self._lastEventMarkClean = False
            self.undoChanged.call(lambda x: x(UndoEvents.UNDO_ADD))

    def newItem(self, undoMethod, redoMethod, undoArgs=None, undoKwargs=None,
                redoArgs=None, redoKwargs=None):
        """Add item to the undo stack.
        """
        if self._blocked or self._undoItemBlockingLevel:
            return

        if self._debug:
            getLogger().debug2('undo.newItem %s %s %s %s %s %s %s' % (self.undoItemBlocking, undoMethod,
                                                                      redoMethod, undoArgs,
                                                                      undoKwargs, redoArgs,
                                                                      redoKwargs))

        if not undoArgs:
            undoArgs = ()
        if not redoArgs:
            redoArgs = ()

        # clear out redos that are no longer going to be doable
        for n in range(len(self) - self.nextIndex):
            self.pop()

        # add new data
        if undoKwargs is None:
            undoCall = self._wrappedPartial(undoMethod, *undoArgs)
        else:
            undoCall = self._wrappedPartial(undoMethod, *undoArgs, **undoKwargs)
        if redoKwargs is None:
            redoCall = self._wrappedPartial(redoMethod, *redoArgs)
        else:
            redoCall = self._wrappedPartial(redoMethod, *redoArgs, **redoKwargs)

        # add new undo/redo methods to the deque - keep a count
        newItem = (undoCall, redoCall)
        self.append(newItem)
        self._newItemCount += 1

        # fix waypoints:
        ll = self.waypoints
        _waypoints = [ii for ii, wp in enumerate(ll) if wp == ll[-1]]
        if _waypoints:
            if len(_waypoints) > 2:
                raise RuntimeError('waypoint length error')
            # need to back-track to the previous value if duplicated
            ll[:] = ll[:_waypoints[0] + 1]
        while ll and ll[-1] >= self.nextIndex:
            ll.pop()

        # correct for maxOperations
        if len(self) > self.maxOperations:
            self.popleft()
            ll = self.waypoints
            if ll:
                for n, val in enumerate(ll):
                    ll[n] = val - 1
                if ll[0] < 0:
                    del ll[0]
        else:
            self.nextIndex += 1

        #GST hack to get round bug
        #GST when extra
        #badKeys = ('includePositiveContours', 'includeNegativeContours', 'spectrumAliasing')
        #badKeys = tuple(sorted(badKeys))

        #testKeys = undoArgs[0].keys()
        #testKeys = tuple(sorted(testKeys))

        if self._lastEventMarkClean:  #and testKeys != badKeys:
            # NOTE:ED - only do it for the first new item?
            self._lastEventMarkClean = False
            self.undoChanged.call(lambda x: x(UndoEvents.UNDO_ADD))

    @property
    def allowNoApplication(self):
        """Return True if undo/redo suspension is temporarily disabled
        CCPNInternal - only required for v2 pytesting
        """
        return self._allowNoApplication

    @allowNoApplication.setter
    def allowNoApplication(self, value):
        """Allow setting of the allowNoApplication flag only if V3-application is not present
        """
        if self.application:
            raise RuntimeError(
                    f'{self.__class__.__name__}.allowNoApplication cannot be modified if V3-application is present')
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.allowNoApplication must be a bool')

        self._allowNoApplication = value

    #-----------------------------------------------------------------------------------------
    # undo
    #-----------------------------------------------------------------------------------------

    def canUndo(self) -> bool:
        """True if an undo operation can be performed
        """
        return self.nextIndex > 0

    def undo(self):
        """Undo one operation - or one waypoint if waypoints are set

        For now errors are handled by printing a warning and clearing the undo object
        """
        if self.nextIndex == 0 or self._blocked:
            return
        elif self.maxWaypoints:
            undoTo = -1
            for val in self.waypoints:
                if val < self.nextIndex - 1:
                    undoTo = val
                else:
                    break
        else:
            undoTo = max(self.nextIndex - 2, -1)

        # block addition of items while operating
        self._blocked = True
        self._lastFuncCall = None

        if self.application and self.application._disableUndoException:
            # mode is activated with switch --disable-undo-exception
            # allows the program to crash with a full error-trace
            # this is dangerous as it may crash and leave _blocked in a compromised state

            self._processUndos(undoTo)

            # Added by Rasmus March 2015. Surely we need to reset self._blocked?
            self._blocked = False

        else:
            try:
                self._processUndos(undoTo)

            except Exception as es:
                from ccpn.util.Logging import getLogger

                getLogger().warning(f'Error while undoing ({es}): aborting undo-operation.')
                if self.application and self.application._ccpnLogging:
                    self._logObjects()
                if self._debug:
                    sys.stderr.write(f'UNDO DEBUG: error in undo. Last undo function was: {self._lastFuncCall}\n')
                    raise es

                # self.clear()
                # Skipping undo-block
                self.nextIndex = undoTo + 1

            finally:
                # Added by Rasmus March 2015. Surely we need to reset self._blocked?
                self._blocked = False

        self.undoChanged.call(lambda x: x(UndoEvents.UNDO_UNDO))

    def _processUndos(self, undoTo):
        """Process the functions on the undo-stack in undo order with/without an undoBlock.
        undoBlock automatically handles sidebar notifications
        """
        from ccpn.core.lib.ContextManagers import undoBlock

        if self._allowNoApplication:
            # process the stack without a V3-application, required for pytest of v2 cases with undo
            self._processUndo(undoTo)
        else:
            with undoBlock():
                self._processUndo(undoTo)

    def _processUndo(self, undoTo):
        """Process the functions on the undo-stack in undo order
        """
        for n in range(self.nextIndex - 1, undoTo, -1):
            undoCall, _redoCall = self[n]
            self._lastFuncCall = repr(undoCall)

            if undoCall:
                undoCall()

        self.nextIndex = undoTo + 1

    #-----------------------------------------------------------------------------------------
    # redo
    #-----------------------------------------------------------------------------------------

    def canRedo(self) -> bool:
        """True if a redo operation can be performed
        """
        return self.nextIndex < len(self)

    def redo(self):
        """Redo one waypoint - or one operation if waypoints are not set.

        For now errors are handled by printing a warning and clearing the undo object
        """
        if self.nextIndex >= len(self) or self._blocked:
            return
        elif self.maxWaypoints:
            redoTo = len(self) - 1
            for val in reversed(self.waypoints):
                if val >= self.nextIndex:
                    redoTo = val
                else:
                    break
        else:
            redoTo = min(self.nextIndex, len(self))

        # block addition of items while operating
        self._blocked = True
        self._lastFuncCall = None

        if self.application and self.application._disableUndoException:
            # mode is activated with switch --disable-undo-exception
            # allows the program to crash with a full error-trace
            # this is dangerous as it may crash and leave _blocked in a compromised state

            self._processRedos(redoTo)

            # Added by Rasmus March 2015. Surely we need to reset self._blocked?
            self._blocked = False

        else:
            try:
                self._processRedos(redoTo)

            except Exception as es:
                from ccpn.util.Logging import getLogger

                getLogger().warning(f'Error while redoing ({es}). Aborting redo operation.')
                if self.application and self.application._ccpnLogging:
                    self._logObjects()
                if self._debug:
                    sys.stderr.write(f'REDO DEBUG: error in redo. Last redo call was: {self._lastFuncCall}\n')
                    raise es
                # self.clear()
                self.nextIndex = redoTo + 1

            finally:
                # Added by Rasmus March 2015. Surely we need to reset self._blocked?
                self._blocked = False

        self.undoChanged.call(lambda x: x(UndoEvents.UNDO_REDO))

    def _processRedos(self, redoTo):
        """Process the functions on the undo-stack in redo order with/without an undoBlock.
        undoBlock automatically handles sidebar notifications
        """
        from ccpn.core.lib.ContextManagers import undoBlock

        if self._allowNoApplication:
            self._processRedo(redoTo)
        else:
            # process the stack without a V3-application, required for pytest of v2 cases with undo
            with undoBlock():
                self._processRedo(redoTo)

    def _processRedo(self, redoTo):
        """Process the functions on the undo-stack in redo order
        """
        redoCall = None
        for n in range(self.nextIndex, redoTo + 1):
            _undoCall, redoCall = self[n]
            self._lastFuncCall = repr(redoCall)

            if redoCall:
                redoCall()

        self.nextIndex = redoTo + 1

        return redoCall

    def clearRedoItems(self):
        """Clear the items above the current next index, if there has been an error adding items
        """
        # remove unwanted items from the top of the undo deque
        while len(self) > self.nextIndex:
            self.pop()

        # fix waypoints - remove any that are left beyond the new end of the undo deque:
        ll = self.waypoints
        while ll and ll[-1] >= self.nextIndex - 1:
            ll.pop()

        self._newItemCount = 0

    #-----------------------------------------------------------------------------------------
    # other
    #-----------------------------------------------------------------------------------------

    def clear(self):
        """Clear and reset undo object
        """
        self.nextIndex = 0
        self.waypoints.clear()
        self._blocked = False
        self._undoItemBlockingLevel = 0
        deque.clear(self)
        self.markUndoClear()

    @property
    def locked(self):
        return self._lock.locked()

    def numItems(self):
        """Return the number of undo items currently on the undo deque
        """
        return len(self)

    @property
    def newItemsAdded(self):
        """Return the number of new items that have been added to the undo deque since
        the last new waypoint was created
        """
        return self._newItemCount

    def _logObjects(self):
        """Ccpn Internal - log objects under review to the logger
        Activated with switch --ccpn-logging
        """
        if self.application and self.application.project:
            _project = self.application.project
            _log = getLogger().debug

            # list the peak info
            _log('peakDims ~~~~~~~~~~~')
            _log('\n'.join([str(pk) for pk in _project.peaks]))
            pks = [pk._wrappedData for pk in _project.peaks]
            for pk in pks:
                for pkDim in pk.sortedPeakDims():
                    _log(f'{pkDim}')
                    for pkDimContrib in pkDim.sortedPeakDimContribs():
                        _log(f'    {pkDimContrib}   {pkDimContrib.resonance}')

            _log('peakContribs ~~~~~~~~~~~')
            for pk in pks:
                for pkContrib in pk.sortedPeakContribs():
                    _log(f'  {pkContrib}')
                    for pkDimContrib in pkContrib.sortedPeakDimContribs():
                        _log(f'    {pkDimContrib}   {pkDimContrib.resonance}')

            _log('shifts ~~~~~~~~~~~')
            _log('\n'.join([str(sh) for sh in _project.chemicalShifts]))
            shifts = [sh._wrappedData for sh in _project.chemicalShifts]
            for sh in _project.chemicalShifts:
                _log(f'    {sh}    {sh.nmrAtom}')
            for sh in shifts:
                _log(f'   {sh}   {sh.isDeleted}  {sh.resonance}')

            _log('resonanceGroups ~~~~~~~~~~~')
            _log('\n'.join([str(res) for res in _project.nmrResidues]))
            ress = [res._wrappedData for res in _project.nmrResidues]
            for res in ress:
                _log(f'   {res}')

            _log('resonances ~~~~~~~~~~~')
            _log('\n'.join([str(res) for res in _project.nmrAtoms]))
            ress = [res._wrappedData for res in _project.nmrAtoms]
            for res in ress:
                _log(f'   {res}')
                for sh in res.sortedShifts():
                    _log(f'       {sh}')
