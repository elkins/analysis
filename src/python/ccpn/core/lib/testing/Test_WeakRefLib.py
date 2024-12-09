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
__date__ = "$Date: 2024-11-21 15:34:29 +0100 (Thu, November 21, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import unittest
import weakref
from ccpn.core.lib.WeakRefLib import WeakRefPartial, OrderedWeakKeyDictionary, _consoleStyle


_DEBUG = True


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
        """Destructor that prints a message when the instance is destroyed.
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
        :param func: The function to be weakly referenced.
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

        import gc

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
        # self.assertEqual(list(self.dictionary.values()), ["value1", "value2"])

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

    def test_weakref_partial2(self):
        from functools import partial

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
        key2 = WeakRefPartial(partial(partial(printPartial1, other='test2'), info='top', other='OVERWRITE'))
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


class TestOrderedWeakKeyDictionaryPickle(unittest.TestCase):

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

        from base64 import urlsafe_b64encode, urlsafe_b64decode
        import pickle

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


if __name__ == '__main__':
    unittest.main()
