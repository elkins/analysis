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
__dateModified__ = "$dateModified: 2025-03-10 18:54:22 +0000 (Mon, March 10, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-04-03 10:29:12 +0000 (Fri, April 03, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

from enum import Enum
from types import DynamicClassAttribute
from typing import Any, TypeVar, Generic
from typing_extensions import Self


ValueType = TypeVar("ValueType")  # Type for value
DataValueType = TypeVar("DataValueType")  # Type for dataValue
_T = TypeVar("_T")  # Individual Type for property
_SENTINEL = object()


class _TypeDynamicClassAttribute(DynamicClassAttribute, Generic[_T]):
    """A subclass of DynamicClassAttribute with type-annotations."""
    ...

    def __get__(self, __instance: Any, __owner: type | None = None) -> _T:
        """Get the value or dataValue from the class or instance, enforcing type constraints."""
        # Return the actual value from the class/instance
        return super().__get__(__instance, __owner)


class DataEnum(Generic[ValueType, DataValueType], Enum):
    """Class to handle enumerated types with associated descriptions and dataValues.

    e.g.
        # name = value, optional description and optional dataValue
        FLOAT = 0, 'Float', <dataValue 1>
        INTEGER = 1, 'Integer', <dataValue 2>
        STRING = 2, 'String', <dataValue 3>
    """
    # ensure that enums are consistently defined
    _value_: ValueType
    _description_: str | None
    _dataValue_: DataValueType

    def __new__(cls, value: ValueType, description: str = None, dataValue: DataValueType = None) -> Self:
        """
        Create a new instance of an enum member.

        :param value: The value of the enum member.
        :type value: ValueType
        :param description: An optional description for the enum member.
        :type description: str, optional
        :param dataValue: An optional data-value for the enum member.
        :type dataValue: DataValueType, optional
        :return: A new instance of the enum member.
        :rtype: Self
        :raises TypeError: If the value type is inconsistent with existing members.
        """
        obj = object.__new__(cls)
        # Get the first existing member's value-type for consistency check
        if (first_member := next(iter(cls.__members__.values()), _SENTINEL)) is not _SENTINEL and \
                not isinstance(value, (expected_type := type(first_member.value))):
            raise TypeError(f"All values in {cls.__name__} must be of type {expected_type.__name__}")
        obj._value_ = value
        # add optional extra information
        obj._description_ = description
        obj._dataValue_ = dataValue
        return obj

    def __repr__(self) -> str:
        """
        Return the string representation of the enum member.

        If the dataValue is not None, include it in the representation.

        :return: The string representation of the enum member.
        :rtype: str
        """
        if self._dataValue_ is not None:
            # Include dataValue if it exists.
            return f"<{self.__class__.__name__}.{self._name_}: {self._value_!r}, {self._dataValue_!r}>"
        else:
            return f"<{self.__class__.__name__}.{self._name_}: {self._value_!r}>"

    # ensure the dataValue is read-only
    @_TypeDynamicClassAttribute
    def value(self) -> ValueType:
        """Return the dataValue."""
        return super().value

    # ensure the dataValue is read-only
    @_TypeDynamicClassAttribute
    def dataValue(self) -> DataValueType:
        """Return the dataValue."""
        return self._dataValue_

    # ensure the description is read-only
    @_TypeDynamicClassAttribute
    def description(self) -> str | None:
        """Return the description."""
        return self._description_

    def prev(self) -> Self:
        """Return the previous member."""
        cls = self.__class__
        members = list(cls)
        index = members.index(self) - 1
        return members[index % len(members)]

    def next(self) -> Self:
        """Return the next member."""
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        return members[index % len(members)]

    @classmethod
    def getByDataValue(cls, value: Any) -> Self | tuple[Self] | None:
        """
        Search for a member(s) by dataValue.

        Search the members for a matching dataValue. Return a single member if only one
        found, or a list for multiple members; otherwise, return None.
        :param str value: search parameter.
        :return: found member(s) or None.
        :rtype: Self | tuple[Self] | None
        """
        members = tuple(val for val in list(cls) if val._dataValue_ == value)
        if members:
            if len(members) == 1:
                return members[0]
            return members

    @classmethod
    def getByDescription(cls, value: str | None) -> Self | tuple[Self] | None:
        """
        Search for a member(s) by description.

        Search the members for a matching description. Return a single member if only one
        found, or a list for multiple members; otherwise, return None.
        :param str value: search parameter.
        :return: found member(s) or None.
        :rtype: Self | tuple[Self] | None
        """
        members = tuple(val for val in list(cls) if val._description_ == value)
        if members:
            if len(members) == 1:
                return members[0]
            return members

    @classmethod
    def dataValues(cls) -> tuple[DataValueType, ...] | None:
        """
        Return a tuple of all dataValues, or None if no dataValues are defined for any members.

        :return: Tuple of all dataValues or None if no dataValues are defined.
        :rtype: tuple[DataValueType, ...] | None
        """
        result = tuple(v._dataValue_ for v in cls)
        return result if any(val is not None for val in result) else None

    @classmethod
    def descriptions(cls) -> tuple[str | None, ...] | None:
        """
        Return a tuple of all descriptions, or None if no descriptions are defined for any members.

        :return: Tuple of all descriptions or None if no descriptions are defined.
        :rtype: tuple[str | None, ...] | None
        """
        result = tuple(v._description_ for v in cls)
        return result if any(val is not None for val in result) else None

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """
        Return a tuple of all names.

        :return: Tuple of all names.
        :rtype: tuple[str, ...]
        """
        return tuple(v._name_ for v in cls)

    @classmethod
    def values(cls) -> tuple[ValueType, ...]:
        """
        Return a tuple of all values.

        :return: Tuple of all values.
        :rtype: tuple[ValueType, ...]
        """
        return tuple(v._value_ for v in cls)

    @classmethod
    def get(cls, value: str) -> Self:
        """
        Return the enumerated type from the name.

        :param value: The name of the enumerated type to retrieve.
        :type value: str
        :return: The enumerated type corresponding to the given name.
        :rtype: Self
        :raises ValueError: If the name is not found in the enumeration.
        """
        try:
            return cls.__getitem__(value)
        except KeyError:
            raise ValueError(f'value must be one of {repr(cls.names())}')


#=========================================================================================

def main():
    """
    A few small tests for the labelled Enum
    """


    class Test(DataEnum):
        FLOAT = 0, None, 'Float'
        INTEGER = 1, None, 'Integer'
        STRING = 2, 'Some type of string', 'String'
        OTHER = 3, None, 'Integer'


    ll = Test.dataValues()
    print(ll)
    test = Test(2)
    print(test)
    print(test.name)
    print(test.value)
    print(test.description)
    print(test.description and test.description.startswith('Some'))
    print(test.prev())
    print(test.next())
    print(test.next().next())
    print(1 in [v.value for v in Test])
    print('Integer' in [v.description for v in Test])
    print(Test(1))
    print(Test.STRING)
    print(Test.dataValues() is None)
    print(Test.get('FLOAT'))
    print(Test.getByDescription(None))
    print(ll[Test.get('STRING').value])
    try:
        print(int(Test.get('OTHER').dataValue))
    except ValueError:
        ...
    try:
        print(ll[Test.get('STRING').dataValue])
    except TypeError:
        ...
    try:
        print(Test.value)
    except AttributeError:
        ...


if __name__ == '__main__':
    # call the testing method
    main()
