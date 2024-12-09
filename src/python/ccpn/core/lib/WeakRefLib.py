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
__dateModified__ = "$dateModified: 2024-12-09 12:51:06 +0000 (Mon, December 09, 2024) $"
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
from dataclasses import Field, dataclass, field
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
    # smaller version of that defined in Common to remove any non-built-in imports
    reset = '\033[0m'


    class fg:
        darkred = '\033[31m'
        darkyellow = '\033[33m'
        red = '\033[91m'
        green = '\033[92m'
        lightgrey = '\033[37m'


#=========================================================================================
# WeakRefDescriptor
#=========================================================================================

class WeakRefDescriptor:
    """
    A descriptor that stores values as weak references tied to specific instances.

    This allows attributes to reference objects without preventing their garbage collection.
    When the referenced object is collected, the corresponding entry is automatically removed.
    """
    __slots__ = "_storage", "__weakref__"
    _storage: weakref.WeakValueDictionary[int, Any]

    def __init__(self) -> None:
        """
        Initialise a new WeakRefDescriptor instance.
        """
        # A WeakValueDictionary to store weak references keyed by instance IDs.
        self._storage: weakref.WeakValueDictionary[int, Any] = weakref.WeakValueDictionary()

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
        if _DEBUG:
            print(f'{_consoleStyle.fg.lightgrey}>>> {self.__class__.__name__}.__get__ {id(instance)}'
                  f'{_consoleStyle.reset}')
        return self._storage.get(id(instance), None)

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
            print(f'{_consoleStyle.fg.lightgrey}>>> {self.__class__.__name__}.__set__ {id(instance)}'
                  f'{_consoleStyle.reset}')
        if value is not None:
            # Store the value as a weak-reference associated with the instance ID.
            self._storage[id(instance)] = value
        else:
            # Remove the entry if the value is None.
            self._storage.pop(id(instance), None)

    def __delete__(self, instance: Any) -> None:
        """
        Remove the value associated with the instance from the weak-reference storage.

        :param instance: The instance for which the value is being deleted.
        """
        self._storage.pop(id(instance), None)


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
            setattr(cls_new, k, WeakRefDescriptor())
        return cls_new


#=========================================================================================
# WeakRefPartial
#=========================================================================================

WeakRefPartialType = TypeVar("WeakRefPartialType", bound=Callable)


class PartialLike(Protocol):
    args: tuple
    keywords: dict

    # cheeky way to add args and keywords to pycharm type-hinting
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
        """Destructor that prints a message when the instance is destroyed,
        if debugging is enabled.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.darkred}>>> {self.__class__.__name__}.__del__ {id(self)}{_consoleStyle.reset}')


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
            # wrap any nested partials
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func
        self = super().__new__(cls)

        def remove(wref, selfref=weakref.ref(self)):
            """
            Callback function that is called when the weakly referenced object is deleted.

            Contains a weakref to Self that ensures that if the wrapper has already been collected then
            no action is required.

            :param wref: The weak-reference to the object.
            """
            if (sref := selfref()) is not None:
                if _DEBUG:
                    print(f'{_consoleStyle.fg.red}>>> {self.__class__.__name__}._remove '
                          f'{sref} - {wref}{_consoleStyle.reset}')
                # remove the handle, it could be used as a reference elsewhere
                sref.__id = None

        self._func_ref = weakref.ref(func, remove)  # Store a weak-reference to func
        self.args = args
        self.keywords = keywords
        self.__id = _IdHandle(self)
        return self

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
        if (not callable(func) or not isinstance(args, tuple) or
                (kwds is not None and not isinstance(kwds, dict)) or
                (namespace is not None and not isinstance(namespace, dict))):
            raise TypeError("Invalid partial state")

        args = tuple(args)  # Just in case it's a subclass
        if kwds is None:
            kwds = {}
        elif type(kwds) is not dict:  # XXX does it need to be *exactly* dict?
            kwds = dict(kwds)
        if namespace is None:
            namespace = {}
        self.__dict__ = namespace

        def remove(wref, selfref=weakref.ref(self)):
            """
            Callback function that is called when the weakly referenced object is deleted.

            :param wref: The weak-reference to the object.
            """
            if (sref := selfref()) is not None:
                if _DEBUG:
                    print(f'{_consoleStyle.fg.red}>>> {self.__class__.__name__}._remove '
                          f'{sref} - {wref}{_consoleStyle.reset}')
                # remove the handle, it could be used as a reference elsewhere
                sref.__id = None

        self._func_ref = weakref.ref(func, remove)  # Restore the weak-reference
        self.args = args
        self.keywords = kwds
        # not sure resetting the handle is strictly necessary
        self.__id = _IdHandle(self)

    @property
    def id(self):
        """
        Return the internal identifier-handle.

        :return: The internal identifier-handle.
        """
        return self.__id

    # def _remove(self, weak_ref):
    #     """
    #     Callback function that is called when the weakly referenced object is deleted.
    #
    #     :param weak_ref: The weak-reference to the object.
    #     """
    #     if _DEBUG:
    #         print(f'{_consoleStyle.fg.red}>>> {self.__class__.__name__}._remove '
    #               f'{weak_ref}{_consoleStyle.reset}')
    #     self.__id = None


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
                # handle _commit_removals when _iterating set is empty
                wc._commit_removals()


class OrderedWeakKeyDictionary(collections.OrderedDict):
    """
    A dictionary that preserves the order of keys and holds weak-references to the keys.

    Keys are weakly referenced, allowing them to be garbage-collected when no strong
    references exist. This ensures memory-efficient storage while maintaining order.
    """

    def __init__(self, orderedDict=None):

        # this allows a weakref.ref(self) pointing to self to be inserted into the class
        def remove(key, selfref=weakref.ref(self)):
            if (sref := selfref()) is not None:
                if sref._iterating:
                    sref._pending_removals.append(key)
                else:
                    with suppress(KeyError):
                        if _DEBUG:
                            print(f'{_consoleStyle.fg.red}>>> {self.__class__.__name__}.__delitem__ {key}'
                                  f'{_consoleStyle.reset}')
                        super(OrderedWeakKeyDictionary, self).__delitem__(key)

        self._remove = remove
        # A list of dead weakrefs (keys to be removed)
        self._pending_removals = []
        self._iterating = set()
        self._dirty_len = False
        super().__init__(orderedDict or {})

    #-----------------------------------------------------------------------------------------
    # internal

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
            weak_key = weakref.ref(key, self._remove)
        else:
            weak_key = key
        if _DEBUG:
            print(f'{_consoleStyle.fg.green}>>> {self.__class__.__name__}.__setitem__ '
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
    # private

    def _commit_removals(self):
        # NOTE: We don't need to call this method before mutating the dict,
        # because a dead weakref never compares equal to a live weakref,
        # even if they happened to refer to equal objects.
        # However, it means keys may already have been removed.
        while self._pending_removals:
            if (key := self._pending_removals.pop()):
                with suppress(KeyError):
                    if _DEBUG:
                        print(f'{_consoleStyle.fg.darkyellow}>>> {self.__class__.__name__}.__delitem__ pending {key}'
                              f'{_consoleStyle.reset}')
                    super(OrderedWeakKeyDictionary, self).__delitem__(key)

    def _scrub_removals(self):
        self._pending_removals = [k for k in self._pending_removals if k in self]
        self._dirty_len = False

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
            # should just do one iteration backwards
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
            # this is very expensive - superclass does not allow messing about :|
            currentOrder = list(super().items())
            self.clear()
            self[key] = value
            super().update(currentOrder)


#=========================================================================================
# testing
#=========================================================================================

@dataclass
class MyDataClass(metaclass=_WeakRefDataClassMeta):
    """A base class to handle WeakRefDescriptor initialization in dataclasses.
    """
    weak_attr1: WeakRefDescriptor = field(default_factory=WeakRefDescriptor)
    weak_attr2: WeakRefDescriptor = field(default_factory=WeakRefDescriptor)
    other: int = None


def main():
    # Example usage
    class MyClass:
        pass


    obj1 = MyClass()
    obj2 = MyClass()

    weakKeyOrderedDict = OrderedWeakKeyDictionary()
    weakKeyOrderedDict[obj1] = "value1"
    weakKeyOrderedDict[obj2] = "value2"

    print(list(weakKeyOrderedDict.items()))  # Should print the items

    # Deleting the original references
    del obj1
    del obj2

    # Garbage collection will remove k1
    import gc

    gc.collect()

    # The weak-references should be removed from the dictionary
    print(list(weakKeyOrderedDict.items()))  # Should be empty if garbage collected


    # Example usage
    class SomeClass:
        def __init__(self, value):
            self._value = value

        def __str__(self):
            return f'{id(self)}:{self._value}'


    obj1 = SomeClass('first')
    obj2 = SomeClass('second')
    obj3 = SomeClass('third')
    obj4 = SomeClass('fourth')

    # Create a dataclass instance
    data = MyDataClass(weak_attr1=obj1, weak_attr2=obj2, other=23)
    data2 = MyDataClass(weak_attr1=obj3)

    print(f'1~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(data.weak_attr1)  # Outputs: <SomeClass instance>
    print(data.weak_attr2)  # Outputs: <SomeClass instance>
    print(data)
    print(data2)

    print(f'2~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    # Test garbage collection
    del obj1
    print(data.weak_attr1)  # Outputs: None (obj1 is garbage-collected)
    print(data)
    print(f'3~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    del obj2
    print(data.weak_attr2)  # Outputs: None (obj2 is garbage-collected)
    print(data)
    print(f'4~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(data)
    print(f'5~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    data2.weak_attr2 = obj4
    print(data.weak_attr1)  # Outputs: <SomeClass instance>
    print(data.weak_attr2)  # Outputs: <SomeClass instance>
    print(data2.weak_attr1)  # Outputs: <SomeClass instance>
    print(data2.weak_attr2)  # Outputs: <SomeClass instance>

    del data2.weak_attr2
    print(data2)


if __name__ == '__main__':
    main()
