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
__dateModified__ = "$dateModified: 2025-01-09 14:17:01 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-11-21 15:34:29 +0100 (Thu, November 21, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import unittest
import weakref
import pickle
import gc
import functools
from dataclasses import dataclass, field
from base64 import urlsafe_b64encode, urlsafe_b64decode
from ccpn.core.lib.WeakRefLib import (WeakRefPartial, WeakRefProxyPartial,
                                      OrderedWeakKeyDictionary, _consoleStyle,
                                      WeakRefDescriptor, _WeakRefDataClassMeta
                                      )


_DEBUG = False


class _Test_IdHandle:
    """Small class that holds a weak-reference pointer.

    :ivar __id: The id of the referenced object.
    """
    __slots__ = ("__id", "__weakref__")

    def __init__(self, ref):
        """Initialize the _Test_IdHandle instance.

        :param ref: The object to be referenced.
        """
        # Store the id of the caller, though it's not strictly necessary.
        # It's only the existence that's important.
        self.__id = id(ref)

    def __del__(self):
        """Destructor that prints a message when the instance is garbage-collected.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.darkred}>>> {self.__class__.__name__}.__del__{_consoleStyle.reset}')


class Item:
    """
    Small class that holds a weakref.ref to a func.
    If the func is deleted, then __id is deleted.
    Any handle to __id in another weakref.ref will be notified of its deletion.

    :ivar name: The name of the item.
    :ivar _func: A weak-reference to the function.
    :ivar _info: Additional information to be passed to the function.
    :ivar __id: An internal identifier-handle.
    """
    __slots__ = ("name", "_func", "_info", "__id", "__weakref__")

    def __init__(self, name, func=None, info=None):
        """Initialize the Item instance.

        :param name: The name of the item.
        :param func: The function to be weakly-referenced.
        :param info: Additional information to be passed to the function.
        """
        self.name = name
        self._info = info
        self._func = weakref.ref(func, self._remove) if func else None
        self.__id = _Test_IdHandle(self._func)

    def __repr__(self):
        """Return a string representation of the Item instance.

        :return: A string representing the Item instance.
        """
        return f'Item({self.name}:{self._func and self._func()})'

    def _remove(self, weak_ref):
        """Callback function that is called when the weakly-referenced function is deleted.

        :param weak_ref: The weak-reference to the function.
        """
        if _DEBUG:
            print(f'{_consoleStyle.fg.red}>>> {self.__class__.__name__}._remove {weak_ref}   '
                  f'{self}{_consoleStyle.reset}')
        self.__id = None

    @property
    def run(self):
        """Quick method to test that the func is removed.
        """
        if self._func and (func := self._func()):
            return func(self._info)

    @property
    def id(self):
        """Return the internal identifier-handle.

        :return: The internal identifier-handle.
        """
        return self.__id


#=========================================================================================
# TestOrderedWeakKeyDictionary
#=========================================================================================


class TestOrderedWeakKeyDictionary(unittest.TestCase):

    def setUp(self):
        """Set up for tests."""
        self.dictionary = OrderedWeakKeyDictionary()

    def test_set_and_get_item(self):
        """Test setting and getting an item."""
        key = Item('help')
        self.dictionary[key] = "value"
        self.assertEqual(self.dictionary[key], "value")

    def test_key_deletion_when_object_is_garbage_collected(self):
        """Test that keys are removed when their objects are garbage collected."""
        key1, key2 = Item('one'), Item('two')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"
        self.assertIn(key1, self.dictionary.keys())
        print('pre-delete', self.dictionary)

        # Delete the key and force garbage collection
        del key1
        self.assertEqual(len(self.dictionary), 1)
        print('post-delete', self.dictionary)

        gc.collect()

        print('post-garbage-collect', self.dictionary)
        self.assertEqual(len(self.dictionary), 1)

    def test_iteration_over_keys(self):
        """Test iteration over keys."""
        key1, key2 = Item('one'), Item('two')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        self.assertEqual(list(self.dictionary.keys()), [key1, key2])

    def test_iteration_over_items(self):
        """Test iteration over items."""
        key1, key2 = Item('three'), Item('four')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"
        self.assertEqual(list(self.dictionary.items()), [(key1, "value1"), (key2, "value2")])

    def test_iteration_over_values(self):
        """Test iteration over values."""
        key1, key2 = Item('five'), Item('six')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        print(f'==> keys   {list(self.dictionary.keys())}')
        print(f'==> values {list(self.dictionary.values())}')
        print(f'==> items  {list(self.dictionary.items())}')

    def test_copy_method(self):
        """Test the copy method."""
        key1, key2 = Item('seven'), Item('eight')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        copied = self.dictionary.copy()
        self.assertIsInstance(copied, OrderedWeakKeyDictionary)
        self.assertEqual(list(copied.items()), list(self.dictionary.items()))

    def test_deepcopy_method(self):
        """Test the deepcopy method."""
        from copy import deepcopy

        key1, key2 = Item('seven'), Item('eight')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        copied = deepcopy(self.dictionary)
        self.assertIsInstance(copied, OrderedWeakKeyDictionary)
        self.assertEqual(list(copied.items()), list(self.dictionary.items()))

    def test_ordering_preservation(self):
        """Test that ordering is preserved."""
        key1, key2 = Item('nine'), Item('ten')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        self.assertEqual(list(self.dictionary.keys()), [key1, key2])

        # Reassign a value to key1 and check that order doesn't change
        self.dictionary[key1] = "new_value1"
        self.assertEqual(list(self.dictionary.keys()), [key1, key2])

    def test_key_error_on_missing_key(self):
        """Test that accessing a missing key raises KeyError."""
        with self.assertRaises(KeyError):
            _ = self.dictionary[Item('lost')]

    def test_clear(self):
        """Test the clear method."""
        key1, key2 = Item('eleven'), Item('twelve')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        self.dictionary.clear()
        self.assertEqual(len(self.dictionary), 0)

    def test_pop(self):
        """Test the pop method."""
        key1, key2 = Item('thirteen'), Item('fourteen')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        value = self.dictionary.pop(key1)
        self.assertEqual(value, "value1")
        self.assertNotIn(key1, self.dictionary)
        self.assertIn(key2, self.dictionary)

    def test_popitem(self):
        """Test the popitem method."""
        key1, key2 = Item('fifteen'), Item('sixteen')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        key, value = self.dictionary.popitem()
        self.assertEqual(value, "value2")
        self.assertNotIn(key, self.dictionary)
        self.assertEqual(len(self.dictionary), 1)

    def test_movetoend(self):
        """Test the move_to_end method."""
        key1, key2 = Item('seventeen'), Item('eighteen')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"

        self.assertEqual(list(self.dictionary.keys()), [key1, key2])

        self.dictionary.move_to_end(key1)
        self.assertEqual(list(self.dictionary.keys()), [key2, key1])
        self.dictionary.move_to_end(key1)
        self.assertEqual(list(self.dictionary.keys()), [key2, key1])

        self.dictionary.move_to_end(key1, last=False)
        self.assertEqual(list(self.dictionary.keys()), [key1, key2])
        self.dictionary.move_to_end(key1, last=False)
        self.assertEqual(list(self.dictionary.keys()), [key1, key2])

        self.dictionary.move_to_end(key2, last=False)
        self.assertEqual(list(self.dictionary.keys()), [key2, key1])

    def test_iter(self):
        """Test the iter method."""
        key1, key2, key3 = Item('nineteen'), Item('twenty'), Item('twenty-one')
        self.dictionary[key1] = "value1"
        self.dictionary[key2] = "value2"
        self.dictionary[key3] = "value3"
        for key in reversed(self.dictionary):
            print(f'{key}: {self.dictionary[key]}')
        tt = tuple(self.dictionary)
        for key in tt:
            print(f'{key}: {self.dictionary[key]}')

    def test_weakref_partial(self):

        def printPartial1(info: str = None):
            return info

        def printPartial2(info: str = None):
            return info

        def printPartial3(info: str = None):
            return info

        # could use weakref.refs here
        key1 = Item('twenty-two', printPartial1, 'test1')
        key2 = Item('twenty-three', printPartial1, 'test2')
        key3 = Item('twenty-four', printPartial2, 'test3')
        key4 = Item('twenty-four', printPartial3, 'test4')
        self.dictionary[key1.id] = key1
        self.dictionary[key2.id] = key2
        self.dictionary[key3.id] = key3
        self.dictionary[key4.id] = key4

        # remove these, the only handles should now be in the dictionary
        key1 = key2 = key3 = key4 = None

        print(f'pre-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in list(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key].run}')
        printPartial1 = printPartial3 = None

        # functions are deleted, which removes the partials in Item
        # but requires another cycle of garbage collection to remove the keys from the dictionary.
        print(f'post-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in reversed(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key].run}')

    @staticmethod
    def printPartial2(info: str = None, other: str = None):
        return f'{info}{other}'

    def test_weakref_partial2(self):

        # not using the WeakKeyDictionary for this test, so all elements will stay in dict
        self.dictionary = {}  # normal dict

        def printPartial1(info: str = None, other: str = None):
            return f'{info}{other}'

        def printPartial2(info: str = None, other: str = None):
            return f'{info}{other}'

        def printPartial3(info: str = None, other: str = None):
            return f'{info}{other}'

        # can use a mix of partial and WeakRefPartial, as long as WeakRefPartial is the outer class.
        key1 = WeakRefPartial(printPartial1, info='test1')
        key2 = WeakRefPartial(functools.partial(functools.partial(printPartial1,
                                                                  other='test2'),
                                                info='top', other='OVERWRITE'))
        key3 = WeakRefPartial(printPartial2, info='test3')
        key4 = WeakRefPartial(printPartial3, info='test4')
        self.dictionary[key1.id] = key1
        self.dictionary[key2.id] = key2
        self.dictionary[key3.id] = key3
        self.dictionary[key4.id] = key4

        # remove these, the only handles should now be in the dictionary
        key1 = key2 = key3 = key4 = None

        print(f'pre-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in list(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key]()}')
        printPartial1 = printPartial3 = None

        # functions are deleted, which removes the partials in Item
        # but requires another cycle of garbage collection to remove the keys from the dictionary.
        print(f'post-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in reversed(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key]()}')


def _picklePartial1(info: str = None):
    return info


def _picklePartial2(info: str = None):
    return info


def _picklePartial3(info: str = None):
    return info


#=========================================================================================
# TestOrderedWeakKeyDictionaryPickle
#=========================================================================================

class TestOrderedWeakKeyDictionaryPickle(unittest.TestCase):

    def _picklePartial1(info: str = None):
        return info

    def _picklePartial2(info: str = None):
        return info

    def _picklePartial3(info: str = None):
        return info

    def setUp(self):
        """Set up for tests."""
        self.dictionary = {}  # normal dict

    def test_weakref_pickle(self):

        # could use weakref.refs here
        key1 = WeakRefPartial(_picklePartial1, 'test1')
        key2 = WeakRefPartial(_picklePartial1, 'test2')
        key3 = WeakRefPartial(_picklePartial2, 'test3')
        key4 = WeakRefPartial(_picklePartial3, 'test4')
        self.dictionary[key1.id] = key1
        self.dictionary[key2.id] = key2
        self.dictionary[key3.id] = key3
        self.dictionary[key4.id] = key4

        # remove these, the only handles should now be in the dictionary
        key1 = key2 = key3 = key4 = None

        pckl = urlsafe_b64encode(pickle.dumps(self.dictionary,
                                              pickle.HIGHEST_PROTOCOL)).decode('utf-8')
        newdict = pickle.loads(urlsafe_b64decode(pckl.encode('utf-8')))
        # items 'look' the same , but are different weakrefs
        self.assertListEqual(list(map(lambda wr: str(wr), newdict.values())),
                             list(map(lambda wr: str(wr), self.dictionary.values())))

        # new keys are created, but the weakrefs still point to the correct methods
        print(f'post-pickle ~~~~~~~~~~ self.dictionary {len(self.dictionary)}')
        for key in reversed(self.dictionary):
            print(f'{id(key)} {key}: {self.dictionary[key]}   {self.dictionary[key]()}')
        print(f'post-pickle ~~~~~~~~~~ newdict {len(newdict)}')
        for key in reversed(newdict):
            print(f'{id(key)} {key}: {newdict[key]}   {newdict[key]()}')

        for key in newdict:
            newdict[key] = None
        for key in reversed(newdict):
            print(f'{id(key)} {key}: {newdict[key]}')

        key4 = WeakRefPartial(_picklePartial3, 'test5')
        print(f'{key4}')
        del key4

    def test_weakref_partial_proxy(self):
        # not using the WeakKeyDictionary for this test, so all elements will stay in dict
        self.dictionary = {}  # normal dict

        def printPartial1(info: str = None, other: str = None):
            return f'{info}{other}'

        def printPartial2(info: str = None, other: str = None):
            return f'{info}{other}'

        def printPartial3(info: str = None, other: str = None):
            return f'{info}{other}'

        # can use a mix of partial and WeakRefPartial, as long as WeakRefPartial is the outer class.
        key1 = WeakRefProxyPartial(printPartial1, info='test1')
        key2 = WeakRefProxyPartial(functools.partial(functools.partial(printPartial1,
                                                                       other='test2'),
                                                     info='top', other='OVERWRITE'))
        key3 = WeakRefProxyPartial(printPartial2, info='test3')
        key4 = WeakRefProxyPartial(printPartial3, info='test4')
        self.dictionary[key1.id] = key1
        self.dictionary[key2.id] = key2
        self.dictionary[key3.id] = key3
        self.dictionary[key4.id] = key4

        # remove these, the only handles should now be in the dictionary
        key1 = key2 = key3 = key4 = None

        print(f'pre-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in list(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key]()}')
        printPartial1 = printPartial3 = None

        # functions are deleted, which removes the partials in Item
        # but requires another cycle of garbage collection to remove the keys from the dictionary.
        print(f'post-delete ~~~~~~~~~~ {len(self.dictionary)}')
        for key in reversed(self.dictionary):
            print(f'{key}: {self.dictionary[key]}   {self.dictionary[key]()}')


#=========================================================================================
# TestWeakRefDescriptor
#=========================================================================================

class TestWeakRefDescriptor(unittest.TestCase):

    def test_descriptor(info: str = None):
        # Example usage
        class MyClass:
            pass


        @dataclass
        class MyDataClass(metaclass=_WeakRefDataClassMeta):
            """A base class to handle WeakRefDescriptor initialization in dataclasses.
            """
            weak_attr1: WeakRefDescriptor = field(default_factory=WeakRefDescriptor)
            weak_attr2: WeakRefDescriptor = field(default_factory=WeakRefDescriptor)
            other: int = None


        # Define a callback function
        def on_weakref_collected(name):
            print(f'{_consoleStyle.fg.blue}Weak-reference garbage-collected for attribute {name} '
                  f'{_consoleStyle.reset}')

        # Connect the callback function to the trait change
        MyDataClass.weak_attr1.connect(on_weakref_collected)
        MyDataClass.weak_attr2.connect(on_weakref_collected)

        obj1 = MyClass()
        obj2 = MyClass()

        weakKeyOrderedDict = OrderedWeakKeyDictionary()
        weakKeyOrderedDict[obj1] = "value1"
        weakKeyOrderedDict[obj2] = "value2"

        print(list(weakKeyOrderedDict.items()))  # Should print the items

        # Deleting the original references
        del obj1
        del obj2

        # Garbage collection
        gc.collect()

        # The weak-references should be removed from the dictionary
        print(list(weakKeyOrderedDict.items()))  # Should be empty if garbage collected


        # Example usage
        class SomeClass:
            attrib: WeakRefDescriptor = WeakRefDescriptor()

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


#=========================================================================================
# TestWeakRefDescriptorConnect
#=========================================================================================

class TestWeakRefDescriptorConnect(unittest.TestCase):
    class MyClass:
        pass


    def setUp(self):
        """Set up a test class with WeakRefDescriptor."""


        class TestClass:
            attrib = WeakRefDescriptor()


        self.testClassType = TestClass
        self.instance = TestClass()

        self.small = self.MyClass()

    def test_connect_instance_observer(self):
        """Test connecting an observer to an instance."""

        def observer():
            print("Observer called")

        self.testClassType.attrib.__set__(self.instance, self.small)
        self.testClassType.attrib.connect(observer, instance=self.instance)
        self.assertIn(
                observer,
                [obs._func_ref() for obs in self.testClassType.attrib._observers[id(self.instance)]],
                )

    def test_connect_class_observer(self):
        """Test connecting an observer to the class."""

        def observer(instance_id):
            print(f"Observer called for instance: {instance_id}")

        self.testClassType.attrib.connect(observer)
        self.assertIn(
                observer,
                [obs._func_ref() for obs in self.testClassType.attrib._observers[-1]],
                )

    def test_duplicate_connect(self):
        """Test that connecting the same observer twice raises an error."""

        def observer():
            print("Observer called")

        self.testClassType.attrib.__set__(self.instance, self.small)
        self.testClassType.attrib.connect(observer, instance=self.instance)
        with self.assertRaises(TypeError):
            self.testClassType.attrib.connect(observer, instance=self.instance)

    def test_disconnect_instance_observer(self):
        """Test disconnecting an observer from an instance."""

        def observer():
            print("Observer called")

        self.testClassType.attrib.__set__(self.instance, self.small)
        self.testClassType.attrib.connect(observer, instance=self.instance)
        self.testClassType.attrib.disconnect(observer, instance=self.instance)
        self.assertNotIn(
                observer,
                [obs._func_ref() for obs in self.testClassType.attrib._observers.get(id(self.instance), [])],
                )

    def test_disconnect_class_observer(self):
        """Test disconnecting an observer from the class."""

        def observer(instance_id):
            print(f"Observer called for instance: {instance_id}")

        self.testClassType.attrib.connect(observer)
        self.testClassType.attrib.disconnect(observer)
        self.assertNotIn(
                observer,
                [obs._func_ref() for obs in self.testClassType.attrib._observers.get(-1, [])],
                )

    def test_disconnect_nonexistent_observer(self):
        """Test that disconnecting a nonexistent observer raises an error."""

        def observer():
            print("Observer called")

        with self.assertRaises(TypeError):
            self.testClassType.attrib.disconnect(observer, instance=self.instance)

    def test_connect_non_callable(self):
        """Test that connecting a non-callable observer raises an error."""
        self.testClassType.attrib.__set__(self.instance, self.small)
        with self.assertRaises(TypeError):
            self.testClassType.attrib.connect(42, instance=self.instance)

    def test_disconnect_non_callable(self):
        """Test that disconnecting a non-callable observer raises an error."""
        with self.assertRaises(TypeError):
            self.testClassType.attrib.disconnect(42, instance=self.instance)

    def test_garbage_collected_instance(self):
        """Test that observers are notified when a weak-referenced object is garbage collected."""
        collected = []

        def observer():
            collected.append(True)

        obj = self.MyClass()
        self.testClassType.attrib.__set__(self.instance, obj)
        self.testClassType.attrib.connect(observer, instance=self.instance)

        del obj
        weakref.finalize(self.testClassType.attrib, lambda: None)  # Trigger garbage collection

        self.assertTrue(collected)


#=========================================================================================
# TestWeakRefDescriptorIsConnected
#=========================================================================================

def observer():
    print("observer called")


def another_observer():
    print("another_observer called")


class TestWeakRefDescriptorIsConnected(unittest.TestCase):
    """
    Unit tests for the WeakRefDescriptor class.

    These tests validate the behaviour of observer-related methods, including connecting,
    disconnecting, and querying observers for both instance-level and class-level signals.
    """


    class MyClass:
        pass


    def setUp(self):
        """
        Set up test environment by creating a mock class with a WeakRefDescriptor attribute.
        """


        class SomeClass:
            attrib = WeakRefDescriptor()


        self.thing = self.MyClass()
        self.someClassType = SomeClass
        self.instance = SomeClass()
        self.observer = observer
        self.another_observer = another_observer
        self.someClassType.attrib.__set__(self.instance, self.thing)  # Assign an object to attrib

    def test_isConnected(self):
        """
        Test the isConnected method to ensure it accurately reflects observer connections.
        """
        # Initially, no observers are connected
        self.assertFalse(self.someClassType.attrib.isConnected(self.observer, self.instance))

        # Connect observer
        self.someClassType.attrib.connect(self.observer, instance=self.instance)
        self.assertTrue(self.someClassType.attrib.isConnected(self.observer, self.instance))

        # Disconnect observer
        self.someClassType.attrib.disconnect(self.observer, instance=self.instance)
        self.assertFalse(self.someClassType.attrib.isConnected(self.observer, self.instance))

    def test_getObservers(self):
        """
        Test the getObservers method to ensure it retrieves the correct list of observers.
        """
        # Initially, no observers
        self.assertEqual(self.someClassType.attrib.getObservers(self.instance), [])

        # Connect observers
        self.someClassType.attrib.connect(self.observer, instance=self.instance)
        self.someClassType.attrib.connect(self.another_observer, instance=self.instance)

        # Check connected observers
        observers = self.someClassType.attrib.getObservers(self.instance)
        self.assertIn(self.observer, observers)
        self.assertIn(self.another_observer, observers)
        self.assertEqual(len(observers), 2)

        # Disconnect one observer
        self.someClassType.attrib.disconnect(self.observer, instance=self.instance)
        observers = self.someClassType.attrib.getObservers(self.instance)
        self.assertNotIn(self.observer, observers)
        self.assertIn(self.another_observer, observers)
        self.assertEqual(len(observers), 1)

    def test_hasObservers(self):
        """
        Test the hasObservers method to ensure it accurately reflects the presence of observers.
        """
        # Initially, no observers
        self.assertFalse(self.someClassType.attrib.hasObservers(self.instance))

        # Connect an observer
        self.someClassType.attrib.connect(self.observer, instance=self.instance)
        self.assertTrue(self.someClassType.attrib.hasObservers(self.instance))

        # Disconnect the observer
        self.someClassType.attrib.disconnect(self.observer, instance=self.instance)
        self.assertFalse(self.someClassType.attrib.hasObservers(self.instance))

    def test_classLevelObservers(self):
        """
        Test observer connection and disconnection for class-level (global) signals.
        """
        # Class-level observer connection
        self.someClassType.attrib.connect(self.observer)
        self.assertTrue(self.someClassType.attrib.isConnected(self.observer))
        self.assertTrue(self.someClassType.attrib.hasObservers())

        # Disconnect class-level observer
        self.someClassType.attrib.disconnect(self.observer)
        self.assertFalse(self.someClassType.attrib.isConnected(self.observer))
        self.assertFalse(self.someClassType.attrib.hasObservers())

    def test_invalidConnection(self):
        """
        Test the behaviour of connect and disconnect methods when provided with invalid inputs.
        """
        # Attempt to connect non-callable
        with self.assertRaises(TypeError):
            self.someClassType.attrib.connect(None, instance=self.instance)

        # Attempt to disconnect non-callable
        with self.assertRaises(TypeError):
            self.someClassType.attrib.disconnect(None, instance=self.instance)

        # Attempt to connect to an invalid instance
        # with self.assertRaises(TypeError):
        self.someClassType.attrib.connect(self.observer, instance=None)

        self.someClassType.attrib.disconnect(self.observer, instance=None)
        # Attempt to disconnect from an invalid instance
        with self.assertRaises(TypeError):
            self.someClassType.attrib.disconnect(self.observer, instance=None)


if __name__ == "__main__":
    unittest.main()
