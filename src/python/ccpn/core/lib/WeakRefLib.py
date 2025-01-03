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
__dateModified__ = "$dateModified: 2025-01-03 17:12:13 +0000 (Fri, January 03, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-12-05 14:31:02 +0100 (Thu, December 05, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import collections
import weakref
from contextlib import suppress
from dataclasses import Field
from reprlib import recursive_repr
from typing import Any, Callable, TypeVar, Protocol


_DEBUG = False


class _consoleStyle():
    """Colors class:reset all colors with colors.reset; two
    subclasses fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold
    """
    # Smaller version of that defined in Common to remove any non-built-in imports
    reset = '\033[0m'


    class fg:
        darkred = '\033[31m'
        darkyellow = '\033[33m'
        red = '\033[91m'
        green = '\033[92m'
        lightgrey = '\033[37m'
        yellow = '\033[93m'
        magenta = '\033[95m'
        white = '\033[97m'


#=========================================================================================
# WeakRefDescriptor
#=========================================================================================

from PyQt5.QtCore import pyqtSignal as Signal, QObject


class WeakRefDescriptor(QObject):
    """
    A descriptor that stores values as weak references tied to specific instances.

    This allows attributes to reference objects without preventing their garbage collection.
    When the referenced object is collected, the corresponding entry is automatically removed.
    """
    # __slots__ = "_storage", "_attrName", "_connected", "__weakref__"
    _storage: weakref.WeakValueDictionary[int, Any]
    _attrName: str
    _connected: bool

    # Define a signal that will be emitted when a weak reference is set to None
    _weakrefCollected: Signal = Signal(str)

    def __init__(self) -> None:
        """
        Initialise a new WeakRefDescriptor instance.
        """
        super().__init__()
        # A WeakValueDictionary to store weak references keyed by instance IDs.
        self._storage: weakref.WeakValueDictionary[int, Any] = weakref.WeakValueDictionary()
        self._connected: bool = False

    def __set_name__(self, owner, name):
        """
        Store the name of the attribute this descriptor is assigned to.
        Can be used for returning  the name when an instance has been garbage-collected.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.magenta}--> {self.__class__.__name__}.__set_name__ {hex(id(owner))} {name}'
                  f'{_consoleStyle.reset}')
        self._attrName: str = name

    def __get__(self, instance: Any, owner: Any) -> Any | None:
        """
        Retrieve the value associated with the instance from the weak-reference storage.

        :param instance: The instance for which the attribute is being accessed.
        :param owner: The owner class of the descriptor.
        :return: The value stored for the instance, or None if no value exists.
        """
        if instance is None:
            # If accessed on the class rather than an instance, return the descriptor itself.
            return self
        result = self._storage.get(id(instance), None)
        if _DEBUG:
            print(f'{_consoleStyle.fg.lightgrey}--> {self.__class__.__name__}.__get__  <==  {hex(id(instance))}'
                  f' {result}{_consoleStyle.reset}')
        return result

    def __set__(self, instance: Any, value: Any) -> None:
        """
        Set a value for the instance in the weak-reference storage.

        :param instance: The instance for which the value is being set.
        :param value: The value to store. Must not be another WeakRefDescriptor.
        """
        if isinstance(value, WeakRefDescriptor):
            # Prevent setting the descriptor itself as a value.
            return
        if _DEBUG:
            print(f'{_consoleStyle.fg.lightgrey}--> {self.__class__.__name__}.__set__  -->  {hex(id(instance))} '
                  f'{value}{_consoleStyle.reset}')
        if value is not None:
            # Store the value as a weak-reference associated with the instance ID.
            self._storage[id(instance)] = value
            # Register a callback to emit the trait change when the object is collected
            weakref.finalize(value, self._onWeakrefCollected, id(instance))
        else:
            # Remove the entry if the value is None.
            self._storage.pop(id(instance), None)

    def __delete__(self, instance: Any) -> None:
        """
        Remove the value associated with the instance from the weak-reference storage.

        :param instance: The instance for which the value is being deleted.
        """
        self._storage.pop(id(instance), None)

    def _onWeakrefCollected(self, _instanceId: int) -> None:
        """
        Callback function that is called when a weak-referenced object is collected.

        :param _instanceId: The ID of the instance whose weak reference was collected.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.yellow}--> Weak reference collected for instance ID '
                  f'{_instanceId}{self}{_consoleStyle.reset}')
        self._weakrefCollected.emit(self._attrName)

    #-----------------------------------------------------------------------------------------
    # public

    def connect(self, handler):
        if not self._connected:
            self._connected = True
            return self._weakrefCollected.connect(handler)

    def disconnect(self):
        if self._connected:
            with suppress(AttributeError):
                self._weakrefCollected.disconnect()


class _WeakRefDataClassMeta(type):
    """
    A metaclass to handle the initialisation of `WeakRefDescriptor` instances in dataclasses.

    This metaclass inspects the class attributes during class creation, identifies fields
    using `WeakRefDescriptor` as a `default_factory`, and replaces them with actual instances
    of `WeakRefDescriptor`. It ensures that weak-reference descriptors are properly initialized
    in dataclass-like structures.
    """

    def __new__(cls, name, bases, dct):
        """
        Create a new class, initializing `WeakRefDescriptor` instances as needed.

        :param cls: The metaclass itself.
        :param name: The name of the new class being created.
        :param bases: A tuple of base classes for the new class.
        :param dct: The dictionary of attributes for the new class.

        :return: A newly created class with `WeakRefDescriptor` fields properly initialized.
        """
        # Identify attributes defined as fields with a WeakRefDescriptor default_factory.
        _weakrefs = {key for key, value in dct.items()
                     if isinstance(value, Field) and value.default_factory is WeakRefDescriptor}
        # Remove identified weak-reference fields from the initial attribute dictionary.
        dct = {k: v for k, v in dct.items() if k not in _weakrefs}
        # Create the new class using the modified attribute dictionary.
        cls_new = super().__new__(cls, name, bases, dct)
        # Assign WeakRefDescriptor instances to the new class for the identified weak-reference fields.
        for k in _weakrefs:
            setattr(cls_new, k, weakref := WeakRefDescriptor())
            # set the name for the weakref-garbage-collection signal
            weakref.__set_name__('_attrName', k)
        return cls_new


#=========================================================================================
# WeakRefPartial
#=========================================================================================

WeakRefPartialType = TypeVar("WeakRefPartialType", bound=Callable)
WeakRefProxyPartialType = TypeVar("WeakRefProxyPartialType", bound=Callable)


class PartialLike(Protocol):
    args: tuple
    keywords: dict

    # Cheeky way to add args and keywords to pycharm type-hinting
    def __call__(self, *args, **kwargs):
        ...


class _IdHandle:
    """
    Small class that holds a weak-reference pointer.
    This can then be used by weakref.ref.

    :ivar __id: The id of the referenced object.
    """
    __slots__ = "__id", "__weakref__"

    def __init__(self, ref):
        """Initialize the _IdHandle instance.

        :param ref: The object to be referenced.
        """
        # Store the id of the caller, though it's not strictly necessary.
        # It's only the existence of Self that's important.
        self.__id = id(ref)

    def __del__(self):
        """Destructor that prints a message when the instance is garbage-collected,
        if debugging is enabled.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.darkred}--> {self.__class__.__name__}.__del__ {hex(id(self))}'
                  f'{_consoleStyle.reset}')


class WeakRefPartial:
    """
    A new function with partial application of the given arguments and keywords.

    This class allows creating a callable object where some arguments and/or keyword
    arguments are pre-filled for the specified function. The function is stored as a
    weak-reference, so it will not prevent the function from being garbage collected.
    If the function is deleted, calling the partial object raises a ``ReferenceError``.

    :ivar _func_ref: A weak-reference to the callable function.
    :vartype _func_ref: weakref.ref
    :ivar args: Positional arguments pre-filled for the function.
    :vartype args: tuple
    :ivar keywords: Keyword arguments pre-filled for the function.
    :vartype keywords: dict.
    """

    __slots__ = "_func_ref", "args", "keywords", "__id", "__dict__", "__weakref__"

    def __new__(cls, func: Callable[..., Any] | PartialLike, /,
                *args: Any, **keywords: Any) -> WeakRefPartialType:
        """
        Initialize a new partial object.

        :param func: The callable function to partially apply.
        :type func: Callable
        :param args: Positional arguments to pre-fill.
        :type args: Any
        :param keywords: Keyword arguments to pre-fill.
        :type keywords: Any
        :raises TypeError: If the first argument is not callable.
        """
        if not callable(func):
            raise TypeError("The first argument must be callable")
        if hasattr(func, "func"):
            # Wrap any nested partials
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func
        self = super().__new__(cls)

        # Pre-create a weakref to self for the weakref delete-callback
        selfref = weakref.ref(self)
        # Store a weak-reference to func
        self._func_ref = weakref.ref(func, lambda wref: WeakRefPartial.__remove(wref, selfref))
        self.args = args
        self.keywords = keywords
        self.__id = _IdHandle(self)
        return self

    #-----------------------------------------------------------------------------------------
    # Internal

    def __call__(self, /, *args: Any, **keywords: Any) -> Any | None:
        """
        Call the function with pre-filled and additional arguments.

        :param args: Additional positional arguments to pass to the function.
        :type args: Any
        :param keywords: Additional keyword arguments to pass to the function.
        :type keywords: Any
        :return: The result of the function call.
        :raises ReferenceError: If the referenced function has been deleted.
        """
        if not (func := self._func_ref()):
            return
        keywords = {**self.keywords, **keywords}
        return func(*self.args, *args, **keywords)

    @recursive_repr()
    def __repr__(self) -> str:
        """
        Return a string representation of the partial object.

        :return: A string representation of the partial object.
        :rtype: str
        """
        if (func := self._func_ref()) is None:
            func_repr = "<deleted function>"
        else:
            func_repr = repr(func)
        qualname = type(self).__qualname__
        args = [func_repr]
        args.extend(repr(x) for x in self.args)
        args.extend(f"{k}={v!r}" for (k, v) in self.keywords.items())
        if type(self).__module__ == "functools":
            return f"functools.{qualname}({', '.join(args)})"
        return f"{qualname}({', '.join(args)})"

    def __reduce__(self) -> tuple:
        """
        Prepare the partial object for pickling.

        :return: A tuple containing the class, arguments, and state.
        :rtype: tuple
        :raises ReferenceError: If the referenced function has been deleted.
        """
        func = self._func_ref()
        return type(self), (func,), (func, self.args, self.keywords or None, self.__dict__ or None)

    def __setstate__(self, state: tuple) -> None:
        """
        Restore the state of the partial object during unpickling.

        :param state: A tuple containing the function, arguments, keywords, and dictionary.
        :type state: tuple
        :raises TypeError: If the state is invalid.
        """
        if not isinstance(state, tuple):
            raise TypeError("Argument to __setstate__ must be a tuple")
        if len(state) != 4:
            raise TypeError(f"Expected 4 items in state, got {len(state)}")
        func, args, kwds, namespace = state
        # Validate state components
        if (not callable(func) or not isinstance(args, tuple) or
                (kwds is not None and not isinstance(kwds, dict)) or
                (namespace is not None and not isinstance(namespace, dict))):
            raise TypeError("Invalid partial state")
        # Ensure arguments are a tuple (even if it's a subclass)
        args = tuple(args)
        if kwds is None:
            kwds = {}
        elif type(kwds) is not dict:  # XXX does it need to be *exactly* dict?
            kwds = dict(kwds)
        # Initialise namespace dictionary
        if namespace is None:
            namespace = {}
        self.__dict__ = namespace

        selfref = weakref.ref(self)
        # Restore the weak-reference
        self._func_ref = weakref.ref(func, lambda wref: WeakRefPartial.__remove(wref, selfref))
        self.args = args
        self.keywords = kwds
        # Initialise a unique ID handle (if required), not sure resetting the handle is strictly necessary
        self.__id = _IdHandle(self)

    def __bool__(self) -> bool:
        """
        Check whether the referenced function still exists.

        :return: True if the weakly-referenced function is still valid, False otherwise.
        :rtype: bool
        """
        return self._func_ref() is not None

    #-----------------------------------------------------------------------------------------
    # Properties

    @property
    def id(self) -> _IdHandle | None:
        """
        Return the internal identifier-handle.

        :return: The internal identifier-handle.
        """
        return self.__id

    #-----------------------------------------------------------------------------------------
    # Private

    @staticmethod
    def __remove(wref: weakref.ref, selfref: weakref.ref):
        """
        Callback function that is called when the weakly-referenced object is deleted.

        This function contains a weak reference to the instance (`selfref`) to ensure that
        if the wrapper has already been collected, no action is required.

        :param wref: The weak reference to the object that is being monitored.
        :type wref: weakref.ref
        :param selfref: A weak reference to the instance of the class.
        :type selfref: weakref.ref
        """
        # Use a staticmethod instead of a monkey-patch
        if (sref := selfref()) is not None:
            if _DEBUG:
                print(f'{_consoleStyle.fg.red}--> {sref.__class__.__name__}._remove '
                      f'{sref} - {wref}{_consoleStyle.reset}')
            # Remove the handle, it could be used as a reference elsewhere
            sref.__id = None


class WeakRefProxyPartial:
    """
    A new function with partial application of the given arguments and keywords.

    This class allows creating a callable object where some arguments and/or keyword
    arguments are pre-filled for the specified function. The function is stored as a
    weak-reference, so it will not prevent the function from being garbage collected.
    If the function is deleted, calling the partial object raises a ``ReferenceError``.

    :ivar _func_ref: A weak-reference to the callable function.
    :vartype _func_ref: weakref.proxy
    :ivar args: Positional arguments pre-filled for the function.
    :vartype args: tuple
    :ivar keywords: Keyword arguments pre-filled for the function.
    :vartype keywords: dict.
    """

    __slots__ = "_func_ref", "args", "keywords", "__id", "__dict__", "__weakref__"

    def __new__(cls, func: Callable[..., Any] | PartialLike, /,
                *args: Any, **keywords: Any) -> WeakRefProxyPartialType:
        """
        Initialize a new partial object.

        :param func: The callable function to partially apply.
        :type func: Callable
        :param args: Positional arguments to pre-fill.
        :type args: Any
        :param keywords: Keyword arguments to pre-fill.
        :type keywords: Any
        :raises TypeError: If the first argument is not callable.
        """
        if not callable(func):
            raise TypeError("The first argument must be callable")
        if hasattr(func, "func"):
            # Wrap any nested partials
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func
        self = super().__new__(cls)

        # Pre-create a weakref to self for the weakref delete-callback
        selfref = weakref.ref(self)
        # Store a weak-reference to func
        self._func_ref = weakref.proxy(func, lambda _wref: WeakRefProxyPartial.__remove(selfref))
        self.args = args
        self.keywords = keywords
        self.__id = _IdHandle(self)
        return self

    #-----------------------------------------------------------------------------------------
    # Internal

    def __call__(self, /, *args: Any, **keywords: Any) -> Any | None:
        """
        Call the function with pre-filled and additional arguments.

        :param args: Additional positional arguments to pass to the function.
        :type args: Any
        :param keywords: Additional keyword arguments to pass to the function.
        :type keywords: Any
        :return: The result of the function call.
        :raises ReferenceError: If the referenced function has been deleted.
        """
        try:
            weakref.getweakrefcount(self._func_ref)
            keywords = {**self.keywords, **keywords}
            return self._func_ref(*self.args, *args, **keywords)
        except ReferenceError:
            return None

    @recursive_repr()
    def __repr__(self) -> str:
        """
        Return a string representation of the partial object.

        :return: A string representation of the partial object.
        :rtype: str
        """
        try:
            weakref.getweakrefcount(self._func_ref)
            func_repr = repr(self._func_ref)
        except ReferenceError:
            func_repr = "<deleted function>"
        qualname = type(self).__qualname__
        args = [func_repr]
        args.extend(repr(x) for x in self.args)
        args.extend(f"{k}={v!r}" for (k, v) in self.keywords.items())
        if type(self).__module__ == "functools":
            return f"functools.{qualname}({', '.join(args)})"
        return f"{qualname}({', '.join(args)})"

    def __bool__(self) -> bool:
        """
        Check whether the referenced function still exists.

        :return: True if the weakly-referenced function is still valid, False otherwise.
        :rtype: bool
        """
        try:
            weakref.getweakrefcount(self._func_ref)
            return True
        except ReferenceError:
            return False

    #-----------------------------------------------------------------------------------------
    # Properties

    @property
    def id(self) -> _IdHandle | None:
        """
        Return the internal identifier-handle.

        :return: The internal identifier-handle.
        """
        return self.__id

    #-----------------------------------------------------------------------------------------
    # Private

    @staticmethod
    def __remove(selfref: weakref.ref):
        """
        Callback function that is called when the weakly-referenced object is deleted.

        This function contains a weak reference to the instance (`selfref`) to ensure that
        if the wrapper has already been collected, no action is required.

        :param selfref: A weak reference to the instance of the class.
        :type selfref: weakref.ref
        """
        # Use a staticmethod instead of a monkey-patch
        if (sref := selfref()) is not None:
            if _DEBUG:
                print(f'{_consoleStyle.fg.red}--> {sref.__class__.__name__}._remove '
                      f'{sref}{_consoleStyle.reset}')
            # Remove the handle, it could be used as a reference elsewhere
            sref.__id = None


#=========================================================================================
# OrderedWeakKeyDictionary
#=========================================================================================

class _IterationGuard:
    # This context manager registers itself in the current iterators of the
    # weak container, such as to delay all removals until the context manager
    # exits.
    # This technique should be relatively thread-safe (since sets are).

    def __init__(self, weakcontainer):
        # Don't create cycles
        self.weakcontainer = weakref.ref(weakcontainer)

    def __enter__(self):
        if (wc := self.weakcontainer()) is not None:
            wc._iterating.add(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (wc := self.weakcontainer()) is not None:
            st = wc._iterating
            st.remove(self)
            if not st:
                # Handle _commit_removals when _iterating set is empty
                wc._commit_removals()


class OrderedWeakKeyDictionary(collections.OrderedDict):
    """
    A dictionary that preserves the order of keys and holds weak-references to the keys.

    Keys are weakly-referenced, allowing them to be garbage-collected when no strong
    references exist. This ensures memory-efficient storage while maintaining order.
    """

    def __init__(self, orderedDict=None):
        # A list of dead weak-refs (keys to be removed)
        self._pending_removals = []
        self._iterating = set()
        self._dirty_len = False
        super().__init__(orderedDict or {})

    #-----------------------------------------------------------------------------------------
    # Internal

    def __getitem__(self, key):
        """Retrieve the value for the specified key.
        """
        if ref := next((ref for ref in super().keys() if ref() == key), None):
            return super().__getitem__(ref)
        raise KeyError(key)

    def __setitem__(self, key, value):
        """Add or update an item in the dictionary. Keys are stored as weak-references.
        """
        if not isinstance(key, weakref.ReferenceType):
            _selfref = weakref.ref(self)
            weak_key = weakref.ref(key, lambda wref: OrderedWeakKeyDictionary.__remove(wref, _selfref))
        else:
            weak_key = key
        if _DEBUG:
            print(f'{_consoleStyle.fg.green}--> {self.__class__.__name__}.__setitem__ '
                  f'{hex(id(self))} {weak_key}{_consoleStyle.reset}')
        super().__setitem__(weak_key, value)

    def __delitem__(self, key):
        """Remove an item from the dictionary by its key.
        """
        if ref := next((ref for ref in super().keys() if ref() == key), None):
            self._dirty_len = True
            return super().__delitem__(ref)
        raise KeyError(key)

    def __contains__(self, key):
        """Check if a key exists in the dictionary.
        """
        return any(ref == key for ref in self.keys())

    def __iter__(self):
        """Iterate over valid (non-collected) weak-references in the dictionary.
        """
        # Iterate over the parent OrderedDict
        with _IterationGuard(self):
            # Yield only valid references
            yield from (obj for ref in super().__iter__() if (obj := ref()) is not None)

    def __reversed__(self):
        """Iterate over valid (non-collected) weak-references in the dictionary in reverse order.
        """
        # Iterate over the parent OrderedDict in reverse
        with _IterationGuard(self):
            # Yield only valid references
            yield from (obj for ref in super().__reversed__() if (obj := ref()) is not None)

    def __deepcopy__(self, memo):
        from copy import deepcopy

        new = self.__class__()
        with _IterationGuard(self):
            for key, value in self.items():
                new[key] = deepcopy(value, memo)
        return new

    def __len__(self):
        if self._dirty_len and self._pending_removals:
            # self._pending_removals may still contain keys which were
            # explicitly removed, we have to scrub them (see issue #21173).
            self._scrub_removals()
        return super().__len__() - len(self._pending_removals)

    #-----------------------------------------------------------------------------------------
    # Private

    def _commit_removals(self):
        # NOTE: We don't need to call this method before mutating the dict,
        # because a dead weakref never compares equal to a live weakref,
        # even if they happened to refer to equal objects.
        # However, it means keys may already have been removed.
        while self._pending_removals:
            if (key := self._pending_removals.pop()):
                with suppress(KeyError):
                    if _DEBUG:
                        print(f'{_consoleStyle.fg.darkyellow}--> {self.__class__.__name__}.__delitem__ pending {key}'
                              f'{_consoleStyle.reset}')
                    super(OrderedWeakKeyDictionary, self).__delitem__(key)

    def _scrub_removals(self):
        self._pending_removals = [k for k in self._pending_removals if k in self]
        self._dirty_len = False

    @staticmethod
    def __remove(key: Any, selfref: weakref.ref):
        """
        Removes the specified key from the `OrderedWeakKeyDictionary`, handling the removal
        either immediately or deferring it depending on the state of the object.

        If the object is currently iterating over its items, the removal is postponed and
        queued for later execution. Otherwise, the key is immediately removed from the
        dictionary. The method suppresses `KeyError` exceptions during the removal process.

        :param key: The key to be removed from the dictionary.
        :type key: Any
        :param selfref: A weak reference to the object containing the dictionary. Used to access
                        the object and its state without creating strong references.
        :type selfref: weakref.ref
        """
        if (sref := selfref()) is not None:
            if sref._iterating:
                sref._pending_removals.append(key)
            else:
                with suppress(KeyError):
                    if _DEBUG:
                        print(f'{_consoleStyle.fg.red}--> {sref.__class__.__name__}.__delitem__ {key}'
                              f'{_consoleStyle.reset}')
                    super(OrderedWeakKeyDictionary, sref).__delitem__(key)

    #-----------------------------------------------------------------------------------------
    # Methods

    def keys(self):
        """Iterate over non-collected keys in the dictionary.
        """
        with _IterationGuard(self):
            yield from (obj for ref in super().keys() if (obj := ref()) is not None)

    def items(self):
        """Iterate over key-value pairs with non-collected keys.
        """
        with _IterationGuard(self):
            yield from ((obj, value) for ref, value in super().items() if (obj := ref()) is not None)

    def values(self):
        """Iterate over values in the dictionary.
        """
        with _IterationGuard(self):
            yield from (self[ref] for ref in self.keys())

    def keyrefs(self):
        """Return a list of weak-references to the keys.

        The references are not guaranteed to be 'live' at the time
        they are used, so the result of calling the references needs
        to be checked before being used.  This can be used to avoid
        creating references that will cause the garbage collector to
        keep the keys around longer than needed.

        """
        return list(super().keys())

    def copy(self):
        new = OrderedWeakKeyDictionary()
        with _IterationGuard(self):
            for key, value in self.items():
                new[key] = value
        return new

    def popitem(self, last: bool = True):
        """Remove and return a (key, value) pair from the dictionary.
        Pairs are returned in LIFO order if last is True or FIFO order if False.
        """
        # Get the first or last item before calling popitem
        if last:
            # Should just do one iteration backwards
            ref, value = next((itm for itm in reversed(super().items())), None)
        else:
            ref, value = next((itm for itm in super().items()), None)
        key = ref()
        self._dirty_len = True
        super().__delitem__(ref)
        return key, value

    def pop(self, key):
        self._dirty_len = True
        return super().pop(key)

    def move_to_end(self, key, last=True):
        value = self.pop(key)
        if last:
            self[key] = value
        else:
            # This is very expensive - superclass does not allow messing about :|
            currentOrder = list(super().items())
            self.clear()
            self[key] = value
            super().update(currentOrder)

#=========================================================================================
# Testing - see Test_WeakRefLib.py
#=========================================================================================
