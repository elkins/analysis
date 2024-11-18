"""
CcpNmr version of the Trailets; all subclassed for added functionalities:
-  _traitOrder
- fixing of default_value issues (see also https://github.com/ipython/traitlets/issues/165)
- json handlers

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               )
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y"
                )
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-11-18 11:44:29 +0000 (Mon, November 18, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2018-05-14 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import pathlib

from collections import OrderedDict
from traitlets import \
    Long, Complex, CComplex, Bytes, CBytes, \
    ObjectName, DottedObjectName, \
    Type, This, ForwardDeclaredInstance, ForwardDeclaredType, \
    Enum, CaselessStrEnum, TCPAddress, CRegExp, \
    TraitType, default, validate, observe, Undefined, HasTraits, TraitError

from traitlets import Any as _Any
from traitlets import Instance as _Instance
from traitlets import Int as _Int
from traitlets import CInt as _CInt
from traitlets import Float as _Float
from traitlets import CFloat as _CFloat
from traitlets import Unicode as _Unicode
from traitlets import CUnicode as _CUnicode
from traitlets import Bool as _Bool
from traitlets import CBool as _CBool

from traitlets import List as _List
from traitlets import Set as _Set
from traitlets import Dict as _Dict
from traitlets import Tuple as _Tuple

from ccpn.util.traits.TraitJsonHandlerBase import TraitJsonHandlerBase, RecursiveDictHandlerABC, \
    RecursiveListHandlerABC
from ccpn.util.AttributeDict import AttributeDict
from ccpn.util.Path import aPath, Path
from ccpn.util.Logging import getLogger

from ccpn.framework.Application import getApplication

class _Ordered(object):
    """A class that maintains and sets trait-order
    """
    _globalTraitOrder = 0

    def __init__(self):
        self._traitOrder = _Ordered._globalTraitOrder
        _Ordered._globalTraitOrder += 1


class Any(_Any, _Ordered):
    def __init__(self, *args, **kwargs):
        if not 'default_value' in kwargs:
            raise ValueError('%s Traitlet without explicit default_value' % self.__class__.__name__)
        _Any.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class Instance(_Instance, _Ordered):
    def __init__(self, *args, **kwargs):
        if not 'default_value' in kwargs:
            raise ValueError('%s Traitlet without explicit default_value' % self.__class__.__name__)
        _Instance.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class Int(_Int, _Ordered):
    def __init__(self, *args, **kwargs):
        _Int.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class CInt(_CInt, _Ordered):
    def __init__(self, *args, **kwargs):
        _CInt.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class Float(_Float, _Ordered):
    def __init__(self, *args, **kwargs):
        _Float.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class CFloat(_CFloat, _Ordered):
    def __init__(self, *args, **kwargs):
        _CFloat.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class Unicode(_Unicode, _Ordered):
    def __init__(self, *args, **kwargs):
        _Unicode.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class CUnicode(_CUnicode, _Ordered):
    def __init__(self, *args, **kwargs):
        _CUnicode.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class Bool(_Bool, _Ordered):
    def __init__(self, *args, **kwargs):
        _Bool.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class CBool(_CBool, _Ordered):
    def __init__(self, *args, **kwargs):
        _CBool.__init__(self, *args, **kwargs)
        _Ordered.__init__(self)


class List(_List, _Ordered):
    """Fixing default_value problem"""

    def __init__(self, trait=None, default_value=[], minlen=0, maxlen=sys.maxsize, **kwargs):
        _List.__init__(self, trait=trait, default_value=default_value, minlen=minlen, maxlen=maxlen, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value


class CList(List, _Ordered):
    """Casting list, any iterable"""

    def validate(self, obj, values):
        # local import, because isotopeRecords in Common cause circular imports £%%$$GRr
        from ccpn.util.Common import isIterable

        if isinstance(values, list):
            pass
        elif isIterable(values):
            values = [val for val in values]
        values = self.validate_elements(obj, values)
        return values


class RecursiveList(List):
    """A list trait that implements recursion of any of the values that are a CcpNmrJson (sub)type
    """
    # trait-specific json handler
    class jsonHandler(RecursiveListHandlerABC):
        klass = list
        recursion = True


class Set(_Set, _Ordered):
    """Fixing default_value problem"""

    def __init__(self, trait=None, default_value=None, minlen=0, maxlen=sys.maxsize, **kwargs):
        _Set.__init__(self, trait=trait, default_value=default_value, minlen=minlen, maxlen=maxlen, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value


class RecursiveSet(Set):
    """A Set trait that implements recursion of any of the values that are a CcpNmrJson (sub)type
    """
    # trait-specific json handler
    class jsonHandler(RecursiveListHandlerABC):
        klass = set
        recursion = True


class Tuple(_Tuple, _Ordered):
    """Fixing default_value problem
    """

    def __init__(self, *traits, **kwargs):
        # DeprecationWarning: Specifying Tuple(default_value=None) for no default is deprecated in traitlets 5.0.5.
        # Use default_value=Undefined
        default_value = kwargs.setdefault('default_value', Undefined)
        _Tuple.__init__(self, *traits, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value


class CTuple(Tuple):
    """Casting tuple, any iterable
    """

    def validate(self, obj, values):
        # local import, because isotopeRecords in Common cause circular imports £%%$$GRr
        from ccpn.util.Common import isIterable

        if isinstance(values, (tuple, list)):
            pass
        elif isIterable(values):
            values = [val for val in values]
        values = self.validate_elements(obj, values)
        return tuple(values)


class RecursiveTuple(Tuple):
    """A tuple trait that implements recursion of any of the values that are a CcpNmrJson (sub)type
    """
    # trait-specific json handler
    class jsonHandler(RecursiveListHandlerABC):
        klass = tuple
        recursion = True


class Dict(_Dict, _Ordered):
    """Fixing default_value problem"""

    def __init__(self, trait=None, traits=None, default_value={}, **kwargs):
        _Dict.__init__(self, trait=trait, traits=traits, default_value=default_value, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value


class RecursiveDict(Dict):
    """A dict trait that implements recursion of any of the values that are a CcpNmrJson (sub)type
    Recursion is active by default, unless tagged with .tag(recursion=False)
    """
    # trait-specific json handler
    class jsonHandler(RecursiveDictHandlerABC):
        klass = dict


class Adict(TraitType, _Ordered):
    """A trait that defines a json serialisable AttributeDict; 
    dicts or (key,value) iterables are automatically cast into AttributeDict
    Recursion is not active
    """
    default_value = AttributeDict()
    info_text = "'an AttributeDict'"

    def __init__(self, default_value={}, allow_none=False, read_only=None, **kwargs):
        TraitType.__init__(self, default_value=default_value, allow_none=allow_none, read_only=read_only, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value

    def validate(self, obj, value):
        """Assure a AttributeDict instance
        """
        if isinstance(value, AttributeDict):
            return value
        elif isinstance(value, dict):
            return AttributeDict(**value)
        elif isinstance(value, list) or isinstance(value, tuple):
            return AttributeDict(value)
        else:
            self.error(obj, value)

    # trait-specific json handler
    class jsonHandler(RecursiveDictHandlerABC):
        klass = AttributeDict
        recursion = False
# end class


class RecursiveAdict(Adict):
    """A trait that defines a json serialisable AttributeDict;
    dicts or (key,value) iterables are automatically cast into AttributeDict
    Recursion is active
    """
    # trait-specific json handler
    class jsonHandler(RecursiveDictHandlerABC):
        klass = AttributeDict
        recursion = True
# end class


class Odict(TraitType, _Ordered):
    """A trait that defines a json serialisable OrderedDict;
    dicts are automatically cast into OrderedDict
    Recursion is not active
    """
    default_value = OrderedDict()
    info_text = "'an OrderedDict'"

    def __init__(self, default_value={}, allow_none=False, read_only=False, **kwargs):
        TraitType.__init__(self, default_value=default_value, allow_none=allow_none, read_only=read_only, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value

    def validate(self, obj, value):
        """Assure a OrderedDict instance
        """
        if isinstance(value, OrderedDict):
            return value
        elif isinstance(value, dict):
            return OrderedDict(list(value.items()))
        else:
            self.error(obj, value)

    # trait-specific json handler
    class jsonHandler(RecursiveDictHandlerABC):
        klass = OrderedDict
        recursion = False
# end class


class RecursiveOdict(Odict):
    """A trait that defines a json serialisable OrderedDict;
    dicts are automatically cast into OrderedDict
    Recursion is active
    """
    # trait-specific json handler
    class jsonHandler(RecursiveDictHandlerABC):
        klass = OrderedDict
        recursion = True
# end class


class Immutable(Any, _Ordered):
    info_text = 'an immutable object, intended to be used as constant'

    def __init__(self, value):
        TraitType.__init__(self, default_value=value, read_only=True)
        _Ordered.__init__(self)

    # trait-specific json handler
    class jsonHandler(TraitJsonHandlerBase):
        """Serialise Immutable to be json compatible.
        """

        # def encode(self, obj, trait): # inherits from base class
        #     return getattr(obj, trait)

        def decode(self, obj, trait, value):
            # force set value
            obj.setTraitValue(trait, value, force=True)
    # end class
#end class


class CPath(TraitType, _Ordered):
    """A trait that defines a casting Path object and is json serialisable
    """
    default_value = aPath('.')
    info_text = "'an Path object'"

    def __init__(self, default_value='', allow_none=False, read_only=False, **kwargs):
        TraitType.__init__(self, default_value=default_value, allow_none=allow_none, read_only=read_only, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value

    def validate(self, obj, value):
        """Assure a Path instance
        """
        if isinstance(value, Path):
            pass

        elif isinstance(value, pathlib.Path) or isinstance(value, str):
            value = Path(value)

        else:
            self.error(obj, value)

        return value

    # trait-specific json handler
    class jsonHandler(TraitJsonHandlerBase):
        """Serialise Path to be json compatible.
        """

        def encode(self, obj, trait):
            # stores as a str for json if not None
            value = getattr(obj, trait)
            if value is not None:
                value = str(value)
            return value

        def decode(self, obj, trait, value):
            # needs conversion from str into Path if not None
            if value is not None:
                value = Path(value)
            setattr(obj, trait, value)
    # end class
# end class


class CString(TraitType, _Ordered):
    """A trait that defines a string object, casts from bytes object and is json serialisable
    """
    default_value = ''
    info_text = "'an string'"

    NONE_VALUE = '__CSTRING_NONE_VALUE__'

    def __init__(self, default_value='', encoding='utf8', allow_none=False, read_only=None, **kwargs):
        TraitType.__init__(self, default_value=default_value, allow_none=allow_none, read_only=read_only, **kwargs)
        _Ordered.__init__(self)
        self.encoding = encoding
        if default_value is not None:
            self.default_value = default_value

    def asBytes(self, value):
        """Return value encoded as a bytes object; encode None"""
        if value is None:
            value = self.NONE_VALUE
        return bytes(value, self.encoding)

    def fromBytes(self, value):
        """Return value decoded from bytes object; decode NONE_VALUE to None"""
        # 3.1.0.alpha2: encountered error that value was of type str
        if isinstance(value, bytes):
            value = value.decode(self.encoding)
        if value == self.NONE_VALUE:
            value = None
        return value

    def validate(self, obj, value):
        """Assure a str instance
        """
        if isinstance(value, str):
            pass

        elif isinstance(value, bytes):
            value = self.fromBytes(value)
            # Test again if None is allowed, as this was missed if it was encoded as NONE_VALUE
            if value is None and not self.allow_none:
                self.error(obj, value)

        else:
            self.error(obj, value)

        return value

    # trait-specific json handler
    class jsonHandler(TraitJsonHandlerBase):
        """json compatible;
        """
        pass
        # def encode(self, obj, trait):
        #     "returns a json serialisable object"
        #     value = getattr(obj, trait)
        #     return CString.asBytes(value)
        #
        # def decode(self, obj, trait, value):
        #     "uses value to generate and set the new (or modified) obj"
        #     value = CString.fromBytes
        #     setattr(obj, trait, value)
# end class


class V3Object(TraitType, _Ordered):
    """A trait that defines a V3-object, json serialisable through its Pid
    """
    default_value = None
    info_text = "A V3-Object"

    def __init__(self, default_value = None, allow_none=True, **kwargs):
        TraitType.__init__(self, default_value=default_value, allow_none=allow_none, **kwargs)
        _Ordered.__init__(self)
        if default_value is not None:
            self.default_value = default_value

    def validate(self, obj, value):
        """Assure a str instance
        """
        from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
        from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC

        if isinstance(value, (AbstractWrapperObject, V3CoreObjectABC)):
            pass
        else:
            self.error(obj, value)

        return value

    # trait-specific json handler
    class jsonHandler(TraitJsonHandlerBase):
        """json compatible;
        """
        def encode(self, obj, trait):
            "returns a json serialisable object"
            value = getattr(obj, trait)
            if value is None:
                return None
            else:
                return value.pid

        def decode(self, obj, trait, value):
            "uses value to generate and set the new (or modified) obj"
            if value is None:
                result = None
            else:
                _app = getApplication()
                if (result := _app.get(value)) is None:
                    getLogger().debug('Error decoding %r; set to None' % value)
            setattr(obj, trait, result)
# end class


class V3ObjectList(List):
    """A trait that defines a list of V3-objects, json serialisable through their Pid's
    """
    default_value = []
    info_text = "A V3-ObjectList"

    def __init__(self, default_value = [], **kwargs):
        List.__init__(self, default_value=default_value, allow_none=False, **kwargs)
        if default_value is not None:
            self.default_value = default_value

        def validate_elements(self, obj, value):
            """Assure a str instance
            """
            from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
            from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC

            for val in value:
                if isinstance(val, (AbstractWrapperObject, V3CoreObjectABC)):
                    pass
                else:
                    self.error(obj, value)

            return value

    # trait-specific json handler
    class jsonHandler(TraitJsonHandlerBase):
        """json compatible;
        """
        def encode(self, obj, trait):
            "returns a json serialisable object"
            value = getattr(obj, trait)
            # make a list of pids
            pids = [val.pid for val in value]
            return pids

        def decode(self, obj, trait, value):
            "uses value to generate and set the new (or modified) obj"
            _app = getApplication()
            # get obj's for the list of pids
            result = [_app.get(val) for val in value]
            if None in result:
                getLogger().warning('Unable to decode some pid\'s to objects; %r' % value)
            setattr(obj, trait, result)
# end class
