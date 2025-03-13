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
__dateModified__ = "$dateModified: 2025-03-13 17:53:32 +0000 (Thu, March 13, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-04-07 15:46:23 +0100 (Thu, April 07, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import bisect
import enum
import itertools
import queue
import sys
import threading
from typing import Any, Generator


class Priority(enum.IntEnum):
    High = 0
    Normal = 1
    Low = 2


PRIORITIES = list(sorted(pp for pp in Priority))
_ITEM_PRIORITY = 0
_STORED_ITEM = 1
_DEBUG = False


class UpdateQueue(queue.Queue):
    """Thread-safe priority queue with FIFO order within priority levels."""

    def __init__(self) -> None:
        """Initialize the priority queue with an internal counter for FIFO ordering."""
        super().__init__()
        self._counter = itertools.count()  # Unique counter to preserve insertion order
        self._lock = threading.Lock()  # Ensure thread safety for non-blocking operations

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # subclass primary Queue methods

    def _init(self, maxsize):
        self.queue = []  # implement as a list

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        bisect.insort(self.queue, item)  #, key=lambda itm: itm[0]) <-- default

    def __len__(self) -> int:
        """Return the total number of items currently in the queue.

        :return: The number of items in the queue across all priority levels.
        """
        return len(self.queue)

    def __bool__(self) -> bool:
        """Return True if the queue contains items."""
        return bool(self.queue)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def put(self, item: Any, *, block: bool = True, timeout: float | None = None,
            priority: int = Priority.Normal) -> None:
        """Add an item to the queue, ensuring FIFO order within the same priority.

        :param item: The task to add to the queue.
        :param bool block: If True (default), block until space is available. If False, raise `queue.Full` if full.
        :param float | None timeout: Maximum time to wait for a free slot if `block=True`.
                                     If `None` (default), wait indefinitely.
        :param int priority: The priority level (0=High, 1=Normal, 2=Low). Default is Normal.
        :raises ValueError: If an invalid priority is provided.
        :raises queue.Full: If the queue is full and `block=False`.
        """
        self._checkPriority(priority)
        with self._lock:
            count = next(self._counter)  # Incrementing counter to maintain FIFO order
            super().put(((priority, count), item), block=block, timeout=timeout)  # Store as ((priority, counter), item)
            if _DEBUG:
                sys.stderr.write(f'==> QUEUE {self}   {self._counter}     {count}')
                for itm in self.items():
                    sys.stderr.write(itm)

    def put_nowait(self, item: Any, priority: int = Priority.Normal):
        """Non-blocking version of put(). Raises queue.Full if the queue is full.

        :param item: The task to add.
        :param int priority: The priority level (0=High, 1=Normal, 2=Low). Default is Normal.
        :raises ValueError: If an invalid priority is provided.
        :raises queue.Full: If the queue is at max capacity.
        """
        return self.put(item, block=False, timeout=None, priority=priority)

    def get(self, *, block: bool = True, timeout: float | None = None) -> Any:
        """Retrieve and remove an item from the queue, respecting priority order.

        If multiple items have the same priority, they are retrieved in FIFO order.

        :param block: If True (default), wait for an item if the queue is empty.
                      If False, return immediately or raise queue.Empty.
        :type block: bool
        :param timeout: Maximum time (in seconds) to wait for an item if blocking.
                        If None (default) and block=True, wait indefinitely.
        :type timeout: float | None
        :return: The highest-priority available item, following FIFO order within priority.
        :raises queue.Empty: If no item is available and `block=False` or timeout expires.
        """
        # Extract only the item, ignoring priority and count
        return super().get(block=block, timeout=timeout)[_ITEM_PRIORITY]

    def items(self, reverse: bool = False) -> Generator[Any, None, None]:
        """Return a generator of the items in the queue, sorted by priority and insertion order.

        Note: this is for observation only, and does remove any item from the queue.

        :param reverse: If True, return items in reverse priority order.
        :return: A generator yielding queued items.
        """
        # Extract items non-destructively
        items_list = list(self.queue)  # `self.queue` is the internal list of PriorityQueue
        if reverse:
            items_list = items_list[::-1]  # fast reversal of the list
        yield from (qq[_STORED_ITEM] for qq in items_list)

    @staticmethod
    def _checkPriority(priority: int = Priority.Normal) -> None:
        """Validate the provided priority.

        :param priority: The priority level (0=High, 1=Normal, 2=Low). Default is Normal.
        :type priority: int.
        :raises ValueError: If the priority is not valid.
        """
        if priority not in PRIORITIES:
            raise ValueError(f'Invalid priority {priority}. Expected one of {PRIORITIES}')
