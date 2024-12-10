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
__dateModified__ = "$dateModified: 2024-11-12 15:24:48 +0000 (Tue, November 12, 2024) $"
__version__ = "$Revision: 3.2.10 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-06-28 18:39:46 +0100 (Mon, June 28, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import time
from contextlib import suppress
import pandas as pd
from collections import OrderedDict
from functools import partial
from contextlib import contextmanager
from ccpn.util.FrozenDict import FrozenDict
from ccpn.util.OrderedSet import OrderedSet, FrozenOrderedSet
from ccpn.util.Common import NOTHING


class PrintFormatter:
    """
    Class to produce formatted strings from python objects.

    Includes standard python objects: list, tuple, dict, set, bytes, str, int, float, complex, bool, type(None)
    and additional objects: OrderedDict, OrderedSet, frozenset, FrozenOrderedSet, FrozenDict, pd.DataFrame.

    Objects not added to formatter will return a pickled object if allowPickle is True, otherwise None.

    Now includes pandas-dataFrames. These are encoded as byte-strings if encodeDataFrame is True.
    If not encoded, they can be formatted, i.e. indented to match the output if required.

    *** The original basis for this came from stackOverflow somewhere, but I can't seem to find it now :|
    """
    VALIDTYPES = (list, dict, str, bytes, int, float, bool, complex, type(None))
    INDEXTYPE = '_indexType'
    COLUMNTYPE = '_columnType'
    MULTIINDEX = pd.MultiIndex.__name__
    RANGEINDEX = pd.RangeIndex.__name__
    MAXSPACES = 32

    _crlf = '\n'
    _useCrlf = True
    _useTab = False
    _spaces = 4
    _encodeDataFrame = False
    _formatDataFrame = True
    _allowPickle = False

    def __init__(self, useTab: bool = NOTHING,
                 spaces: int = NOTHING,
                 useCrlf: bool = NOTHING,
                 encodeDataFrame: bool = NOTHING,
                 formatDataFrame: bool = NOTHING):
        """Initialise the class.

        Use useTab to use the tab character for indenting, otherwise use the number of spaces specified by spaces.
        spaces is the number of space-characters to use for indenting.
        Use useCrlf is True to split each element of the output to a separate line.
        Use encodeDataFrame is True to encode the dataFrames as an ascii byte-string.
        Use formatDataFrame is True to apply indenting and line-splitting to the dataFrames, this may output very long files.
        
        :param useTab: bool
        :param spaces: int
        :param useCrlf: bool
        :param encodeDataFrame: bool
        :param formatDataFrame: bool

        :raises TypeError in incorrect parameters
        """

        # use sentinels, can then be subclassed without editing __init__
        if useTab is not NOTHING:
            if useTab not in (True, False):
                raise TypeError(f'{self.__class__.__name__}: useTab must be True/False')
            self._useTab = useTab
        if spaces is not NOTHING:
            if not isinstance(spaces, int) or not 0 <= spaces < self.MAXSPACES:
                raise TypeError(f'{self.__class__.__name__}: spaces must be an int in range(0, {self.MAXSPACES})')
            self._spaces = spaces
        if useCrlf is not NOTHING:
            if useCrlf not in (True, False):
                raise TypeError(f'{self.__class__.__name__}: useCrlf must be True/False')
            self._useCrlf = useCrlf
        if encodeDataFrame is not NOTHING:
            if encodeDataFrame not in (True, False):
                raise TypeError(f'{self.__class__.__name__}: encodeDataFrame must be True/False')
            self._encodeDataFrame = encodeDataFrame
        if formatDataFrame is not NOTHING:
            if formatDataFrame not in (True, False):
                raise TypeError(f'{self.__class__.__name__}: formatDataFrame must be True/False')
            self._formatDataFrame = formatDataFrame

        self._setTabs()

        self._registeredFormats = {}
        self._literalEvals = {}
        self._indent = 0

        # list of default registered objects
        _registrations = {object          : PrintFormatter.formatObject,
                          dict            : PrintFormatter.formatDict,
                          list            : PrintFormatter.formatList,
                          tuple           : PrintFormatter.formatTuple,
                          set             : PrintFormatter.formatSet,
                          OrderedSet      : partial(PrintFormatter.formatListType, klassName=OrderedSet.__name__),
                          FrozenOrderedSet: partial(PrintFormatter.formatListType, klassName=FrozenOrderedSet.__name__),
                          frozenset       : partial(PrintFormatter.formatSetType, klassName=frozenset.__name__),
                          OrderedDict     : PrintFormatter.formatOrderedDict,
                          FrozenDict      : PrintFormatter.formatFrozenDict,
                          pd.DataFrame    : PrintFormatter.formatDf,
                          }

        # add objects to the formatter
        for obj, func in _registrations.items():
            self.registerFormat(obj, func)

        # add objects to the literal_eval list
        for klass in (
                OrderedDict, OrderedSet, frozenset, FrozenOrderedSet, FrozenDict, self.PythonObject, self.DfObject):
            self.registerLiteralEval(klass)

    #-----------------------------------------------------------------------------------------
    # properties
    #-----------------------------------------------------------------------------------------

    @property
    def useTab(self) -> bool:
        """Use tabs for indenting.
        """
        return self._useTab

    @useTab.setter
    def useTab(self, value):
        if value not in (True, False):
            raise TypeError(f'{self.__class__.__name__}: useTab must be True/False')
        self._useTab = value
        self._setTabs()

    @property
    def spaces(self) -> int:
        """The number of spaces for indenting, if using spaces.
        """
        return self._spaces

    @spaces.setter
    def spaces(self, value):
        if not isinstance(value, int) and 0 <= value < self.MAXSPACES:
            raise TypeError(f'{self.__class__.__name__}: spaces must be an int in range(0, {self.MAXSPACES})')
        self._spaces = value
        self._setTabs()

    @property
    def crlf(self):
        """Return the crlf (end-of-line) characters.
        """
        return self._crlf if self._useCrlf else ''

    @property
    def useCrlf(self) -> bool:
        """Use crlf characters.
        """
        return self._useCrlf

    @useCrlf.setter
    def useCrlf(self, value):
        if value not in (True, False):
            raise TypeError(f'{self.__class__.__name__}: useCrlf must be True/False')
        self._useCrlf = value
        self._setTabs()

    @property
    def encodeDataFrame(self) -> bool:
        """Encode the dataFrames as an ascii byte-string.
        """
        return self._encodeDataFrame

    @encodeDataFrame.setter
    def encodeDataFrame(self, value):
        if value not in (True, False):
            raise TypeError(f'{self.__class__.__name__}: encodeDataFrame must be True/False')
        self._encodeDataFrame = value

    @property
    def formatDataFrame(self) -> bool:
        """Format the dataFrames using the crlf, spaces, tab settings.
        """
        return self._formatDataFrame

    @formatDataFrame.setter
    def formatDataFrame(self, value):
        if value not in (True, False):
            raise TypeError(f'{self.__class__.__name__}: formatDataFrame must be True/False')
        self._formatDataFrame = value

    @property
    def allowPickle(self) -> bool:
        """Allow pickle objects in the output string.
        """
        return self._allowPickle

    def __str__(self):
        """Readable string representation
        """
        return f'<{self.__class__.__name__}: ' \
               f'useTab={self._useTab}, ' \
               f'spaces={self._spaces}, ' \
               f'useCrfl={self._useCrlf}, ' \
               f'encodeDataFrame={self._encodeDataFrame}, ' \
               f'formatDataFrame={self._formatDataFrame}>'

    #-----------------------------------------------------------------------------------------
    # internal
    #-----------------------------------------------------------------------------------------

    def _setTabs(self):
        """Set up the tab/space characters.
        """
        if self._useCrlf:
            self._tabs = '\t' if self._useTab else ' ' * self._spaces
        else:
            self._tabs = ''

    @contextmanager
    def pushTabs(self, *, useTab: bool = False, spaces: int = 4, useCrlf: bool = True):
        """Context manager to temporarily disable the tab/space characters when encoding dataFrames.
        """
        _useTab, _spaces, _useCrlf = self._useTab, self._spaces, self._useCrlf
        if self._encodeDataFrame or not self._formatDataFrame:
            # push current tab-settings
            self._useTab, self._spaces, self._useCrlf = useTab, spaces, useCrlf
            self._setTabs()
        try:
            yield
        finally:
            if self._encodeDataFrame or not self._formatDataFrame:
                # recover tab-settings
                self._useTab, self._spaces, self._useCrlf = _useTab, _spaces, _useCrlf
                self._setTabs()

    def registerFormat(self, obj, callback):
        """Register an object class to formatter.
        """
        self._registeredFormats[obj] = callback

    def registerLiteralEval(self, obj):
        """Register a literalEval object class to formatter.
        """
        self._literalEvals[obj.__name__] = obj

    def __call__(self, value, **args):
        """Call-method to produce output string.
        """
        for key in args:
            setattr(self, key, args[key])
        formatter = self._registeredFormats[type(value) if type(value) in self._registeredFormats else object]
        return formatter(self, value, self._indent)

    def formatDf(self, value, indent, formatString=''):
        """Output format for pandas-dataFrames.
        """
        from base64 import urlsafe_b64encode

        if self._encodeDataFrame:
            with self.pushTabs(spaces=0, useCrlf=False):
                # encode the dataFrame-dict as a string
                df = f"{{\n" \
                     f"'columns'    : {self.formatList(self, value.columns, indent)}, " \
                     f"'index'      : {self.formatList(self, value.index, indent)}, " \
                     f"'data'       : {self.formatList(self, value.values.tolist(), indent)}, " \
                     f"{self.COLUMNTYPE!r} : {type(value.columns).__name__!r}, " \
                     f"{self.INDEXTYPE!r}  : {type(value.index).__name__!r}" \
                     f"}}\n"
                data = f"{urlsafe_b64encode(bytes(df, 'utf-8')).decode('utf-8')!r}"
        else:
            with self.pushTabs(spaces=0, useCrlf=False):
                # store directly as a formatted-dict
                df = {'columns'           : tuple(value.columns.tolist()),
                      'index'             : tuple(value.index.tolist()),
                      'data'              : tuple(value.values.tolist()),
                      f'{self.COLUMNTYPE}': type(value.columns).__name__,
                      f'{self.INDEXTYPE}' : type(value.index).__name__
                      }
                data = self.formatDict(self, df, indent)
                data = '\n'.join(data.split('\\n'))

        return f"DfObject({data})"

    def formatObject(self, value, indent, formatString=''):
        """Fallback method for objects not registered with formatter.
        Returns 'None' if allowPickle is False.
        """
        from base64 import urlsafe_b64encode
        import pickle

        if isinstance(value, self.VALIDTYPES):
            # return python recognised objects if not already processed
            return repr(value)
        elif self._allowPickle:
            # and finally catch any non-recognised object
            return "PythonObject('{0}')".format(
                    urlsafe_b64encode(pickle.dumps(value, pickle.HIGHEST_PROTOCOL)).decode('utf-8'))
        return repr(None)

    def formatDictBase(self, value, indent, formatString=''):
        """Output format for dict/FrozenDict.
        """
        items = [
            self.crlf + self._tabs * (indent + 1) + repr(key) + ': ' +
            (self._registeredFormats[type(value[key])
            if type(value[key]) in self._registeredFormats else object])(self, value[key], indent + 1)
            for key in value
            ]
        return formatString.format(','.join(items) + self.crlf + self._tabs * indent)

    formatDict = partial(formatDictBase, formatString='{{{0}}}')
    formatFrozenDict = partial(formatDictBase, formatString='FrozenDict({{{0}}})')

    def formatBase(self, value, indent, formatString=''):
        """Output format for list.
        """
        items = [
            self.crlf + self._tabs * (indent + 1) +
            (self._registeredFormats[type(item)
            if type(item) in self._registeredFormats else object])(self, item, indent + 1)
            for item in value
            ]
        return formatString.format(','.join(items) + self.crlf + self._tabs * indent)

    formatList = partial(formatBase, formatString='[{0}]')
    formatTuple = partial(formatBase, formatString='({0})')
    formatSet = partial(formatBase, formatString='{{{0}}}')

    def formatKlassBase(self, value, indent, klassName=None, formatString=''):
        """Output format for sets of type klass.
        Currently:  ccpn.util.OrderedSet.OrderedSet
                    frozenset
                    ccpn.util.OrderedSet.FrozenOrderedSet
        """
        items = [
            self.crlf + self._tabs * (indent + 1) +
            (self._registeredFormats[type(item)
            if type(item) in self._registeredFormats else object])(self, item, indent + 1)
            for item in value
            ]
        return formatString.format(klassName, ','.join(items) + self.crlf + self._tabs * indent)

    formatListType = partial(formatKlassBase, formatString='{0}([{1}])')
    formatSetType = partial(formatKlassBase, formatString='{0}({{{1}}})')

    def formatOrderedDict(self, value, indent):
        """Output format for OrderedDict (collections.OrderedDict).
        """
        items = [
            self.crlf + self._tabs * (indent + 1) +
            "(" + repr(key) + ', ' + (self._registeredFormats[
                type(value[key]) if type(value[key]) in self._registeredFormats else object
            ])(self, value[key], indent + 1) + ")"
            for key in value
            ]
        return 'OrderedDict([{0}])'.format(','.join(items) + self.crlf + self._tabs * indent)

    def PythonObject(self, value):
        """Call method to produce object from pickled string.
        Returns None if allowPickle is False.
        """
        from base64 import urlsafe_b64decode
        import pickle

        if type(value) in (str,) and self._allowPickle:
            return pickle.loads(urlsafe_b64decode(value.encode('utf-8')))

    def DfObject(self, value):
        """Call-method to produce object from encoded-dataFrame.
        """
        from base64 import urlsafe_b64decode

        if type(value) not in (str, dict, bytes):
            return
        if type(value) in (dict,):
            # not-encoded - recover from dict
            data = value
        elif type(value) in (str, bytes):
            # encoded - recover from string
            data = self.literal_eval(urlsafe_b64decode(value).decode() if self._encodeDataFrame else value)
        else:
            raise ValueError('malformed DfObject')

        if data is not NOTHING:
            # pop the index/column types - recover dataFrame from column/index/data
            indexType = data.pop(self.INDEXTYPE, False)
            columnType = data.pop(self.COLUMNTYPE, False)
            df = pd.DataFrame(**data)

            with suppress(Exception):
                # recover the index/column types
                if indexType == self.MULTIINDEX:
                    df.index = pd.MultiIndex.from_tuples(df.index)
                elif indexType == self.RANGEINDEX:
                    df.index = pd.RangeIndex(start=min(df.index), stop=max(df.index) + 1)
            with suppress(Exception):
                if columnType == self.MULTIINDEX:
                    df.columns = pd.MultiIndex.from_tuples(df.columns)
                elif columnType == self.RANGEINDEX:
                    df.columns = pd.RangeIndex(start=min(df.columns), stop=max(df.columns) + 1)

            return df

    def literal_eval(self, node_or_string):
        """
        Safely evaluate an expression node or a string containing a Python
        expression.  The string or node provided may only consist of the following
        Python literal structures: strings, bytes, numbers, tuples, lists, dicts,
        sets, booleans, and None.
        """
        from ast import parse, Expression, Constant, UnaryOp, UAdd, USub, Tuple, \
            List, Set, Dict, Call, Add, Sub, BinOp

        if isinstance(node_or_string, str):
            node_or_string = parse(node_or_string, mode='eval')
        if isinstance(node_or_string, Expression):
            node_or_string = node_or_string.body

        def _convert_num(node):
            if isinstance(node, Constant) and type(node.value) in (int, float, complex):
                return node.value
            raise ValueError(f'malformed node or string: {repr(node)}')

        def _convert_signed_num(node):
            if isinstance(node, UnaryOp) and isinstance(node.op, (UAdd, USub)):
                operand = _convert_num(node.operand)
                return + operand if isinstance(node.op, UAdd) else - operand

            return _convert_num(node)

        def _convert_LiteralEval(node, klass):
            if isinstance(node, Call) and node.func.id == klass.__name__:
                mapList = list(map(_convert, node.args))
                if mapList:
                    return klass(mapList[0])

        def _convert(node):
            if isinstance(node, Constant):
                return node.value
            elif isinstance(node, Tuple):
                return tuple(map(_convert, node.elts))
            elif isinstance(node, List):
                return list(map(_convert, node.elts))
            elif isinstance(node, Set):
                return set(map(_convert, node.elts))
            elif isinstance(node, Dict):
                return dict(zip(map(_convert, node.keys),
                                map(_convert, node.values)))
            elif isinstance(node, Call):
                if node.func.id in self._literalEvals:
                    return _convert_LiteralEval(node, self._literalEvals[node.func.id])
            elif isinstance(node, BinOp) and isinstance(node.op, (Add, Sub)):
                left = _convert_signed_num(node.left)
                right = _convert_num(node.right)
                if isinstance(left, (int, float)) and isinstance(right, complex):
                    return left + right if isinstance(node.op, Add) else left - right

            return _convert_signed_num(node)

        return _convert(node_or_string)


#=========================================================================================
# main
#=========================================================================================

def main():
    """Test the output from the printFormatter and recover as the python object.
    """

    import pandas as pd
    import numpy as np
    from base64 import urlsafe_b64decode, urlsafe_b64encode

    rows, cols = 6, 6
    columns = pd.MultiIndex.from_tuples((f"Set{1 + col // 2}", f"num{col + 1}") for col in range(cols))
    data = np.random.random(rows * cols) * 1e4
    df = pd.DataFrame(data.reshape(rows, cols), columns=columns)

    testDict = {
        "Boolean2"  : True,
        "DictOuter" : {
            "ListSet"    : [[0, {1, 2, 3, 4, 5.00000000001, 'more strings'}],
                            [0, 1000000.0],
                            ['Another string', 0.0]],
            "String1"    : 'this is a string',
            "nestedLists": [[0, 0],
                            [0, 1 + 2.00000001j],
                            [0, (1, 2, 3, 4, 5, 6), OrderedDict((
                                ("ListSetInner", [[0, OrderedSet([1, 2, 3, 4, 5.00000001, 'more inner strings'])],
                                                  [0, 1000000.0],
                                                  {'Another inner string', 0.0}]),
                                ("String1Inner", b'this is an inner byte string'),
                                ("String2Inner", b'this is an inner\xe2\x80\x9d byte string'),
                                ("nestedListsInner", [[0, 0],
                                                      [0, 1 + 2.00000001j],
                                                      [0, (1, 2, 3, 4, 5, 6)],
                                                      df])
                                ))
                             ]]
            },
        "nestedDict": {
            "nestedDictItems": FrozenDict({
                "floatItem": 1.23000001,
                "frozen"   : frozenset([67, 78]),
                "frOrdered": FrozenOrderedSet([34, 45])
                })
            },
        "Boolean1"  : (True, None, False),
        }

    pretty = PrintFormatter()

    t0 = time.perf_counter()
    dd = pretty(testDict)
    print(f'dataDict string: \n{dd}')
    print(f'\n~~~~~~~~~~~~~~~~~~~\n')

    t1 = time.perf_counter() - t0
    recover = pretty.literal_eval(dd)
    print(f'Recovered python object: {recover}')
    print(f'\n~~~~~~~~~~~~~~~~~~~\n')

    t2 = time.perf_counter() - t1
    print(df)
    print(type(df.index), type(df.columns))
    print(f'\n~~~~~~~~~~~~~~~~~~~\n')

    # a bit harsh to get the df :|
    newDf = recover.get('DictOuter').get('nestedLists')[2][2].get('nestedListsInner')[3]
    print(newDf)
    print(f'\n~~~~~~~~~~~~~~~~~~~\n')
    # print(type(newDf.index), type(newDf.columns))

    print(t1)
    print(t2)

    print(pretty)
    print(f'{pretty!r}')


if __name__ == '__main__':
    main()
