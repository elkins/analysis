"""Local enhancements to json, adding support for reading and writing
pandas.Series, pandas.DataFrame, numpy.ndarray, OrderedDict,
and ccpnmodel.ccpncore.Tensor

pandas.Panel is deprecated and will be loaded as a pandas.DataFrame
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:25 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import json
import numpy
import pandas
import contextlib
from collections import OrderedDict


ORDEREDDICT = 'OrderedDict'
DATAFRAME = 'pandas.DataFrame'
SERIES = 'pandas.Series'
NDARRAY = 'numpy.ndarray'
CROSSREFERENCE = 'ccpn.cross-reference'
TENSOR = 'ccpncore.Tensor'
PANEL = 'pandas.Panel'


def load(fp, **kwds):
    """Load json from file fp with extended object type support"""
    return json.load(fp, object_pairs_hook=_ccpnObjectPairHook, **kwds)


def loads(s: str, **kwds):
    """Load json from string s with extended object type support"""
    return json.loads(s, object_pairs_hook=_ccpnObjectPairHook, **kwds)


def dump(obj: object, fp: str, indent: int = 2, **kwds):
    """Dump object to json file with extended object type support"""
    return json.dump(obj, fp, indent=indent, cls=_CcpnMultiEncoder, **kwds)


def dumps(obj: object, indent: int = 2, **kwds):
    """Dump object to json string with extended object type support"""
    return json.dumps(obj, indent=indent, cls=_CcpnMultiEncoder, **kwds)


def _dataFrameToDict(df) -> dict:
    """
    Ensure a dataframe is properly converted to a dict
    so that can be dumped correctly to a Json.
    Note has to be done this way to avoid data-loss with tiny/large floats.
    Cannot  use simply dataframe.to_dict(), won't restore correctly.
    :param df:
    :return: data
    """
    index = list(df.index)
    columns = list(df.columns)
    values = df.values.tolist()
    return {'index': index, 'columns': columns, 'data': values}


class _CcpnMultiEncoder(json.JSONEncoder):
    """Overrides normal JSON encoder, supporting additional types.
    """

    def default(self, obj):

        # Sentinel - reset if we find a supported type
        typ = None
        data = None

        # stop circular imports
        from ccpn.core._implementation.DataFrameABC import DataFrameABC
        from ccpn.core._implementation.CrossReference import _CrossReferenceABC

        if isinstance(obj, OrderedDict):
            typ = ORDEREDDICT
            data = list(obj.items())

        elif isinstance(obj, DataFrameABC):
            # Works like pandas.DataFrame (see comments there), but instantiates subclass.
            if not (typ := DataFrameABC.jsonType(obj)):
                # in-case of any undefined/unregistered subclasses
                typ = DataFrameABC.registeredDefaultJsonType

            dataDict = _dataFrameToDict(obj)
            data = json.dumps(dataDict)
            # data = obj.to_json(orient='split')

        elif isinstance(obj, pandas.DataFrame):
            # NOTE:ED - this converts both None and NaN to 'null'
            # We assume that pandas will get back the correct value from the type of the array
            # (NaN in numeric data, None in object data).
            typ = DATAFRAME
            dataDict = _dataFrameToDict(obj)
            data = json.dumps(dataDict)
            # data = obj.to_json(orient='split')

        elif isinstance(obj, pandas.Series):
            # NOTE:ED - this converts both None and NaN to 'null'
            # We assume that pandas will get back the correct value from the type of teh array
            # (NaN in numeric data, None in object data).
            typ = SERIES
            data = obj.to_json(orient='split')

        # elif isinstance(obj, pandas.Panel):
        #     # NBNB NOT TESTED
        #     frame = obj.to_frame()
        #     data = frame.to_json(orient='split')

        elif isinstance(obj, numpy.ndarray):
            typ = NDARRAY
            data = obj.tolist()

        elif isinstance(obj, _CrossReferenceABC):
            if not (typ := _CrossReferenceABC.jsonType(obj)):
                # in-case of any undefined/unregistered subclasses
                typ = _CrossReferenceABC.registeredDefaultJsonType

            data = obj.toJson()

        else:
            with contextlib.suppress(ImportError):
                # Put here to avoid circular imports
                from ccpn.util.Tensor import Tensor

                if isinstance(obj, Tensor):
                    typ = TENSOR
                    data = obj._toDict()

        # We are done.
        if typ is None:
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, obj)

        else:
            from xml.sax.saxutils import escape

            # NB we assume that this OrderedDict will not be further processed, but that its contents will
            return OrderedDict((('__type__', typ), ('__data__', escape(data))))


def _ccpnObjectPairHook(pairs):
    if len(pairs) == 2:
        tag1, typ = pairs[0]
        tag2, data = pairs[1]
        if tag1 == '__type__' and tag2 == '__data__':

            from ccpn.core._implementation.DataFrameABC import DataFrameABC
            from ccpn.core._implementation.CrossReference import _CrossReferenceABC

            if typ == ORDEREDDICT:
                return OrderedDict(data)

            elif typ in DataFrameABC.registeredJsonTypes():
                # check for registered subclasses of DataFrameABC
                result = None
                try:
                    # result = pandas.read_json(data, orient='split')
                    result = pandas.DataFrame(**json.loads(data))
                    if klass := DataFrameABC.fromJsonType(typ):
                        # SHOULD always be a defined json-type
                        result = klass(result)
                finally:
                    return result

            elif typ == DATAFRAME:
                # return pandas.DataFrame(data=data.get('data'), index=data.get('index'),
                #                         columns=data.get('columns'))
                # return pandas.read_json(data, orient='split')
                return pandas.DataFrame(**json.loads(data))

            elif typ == PANEL:
                # NBNB NOT TESTED
                # return pandas.read_json(data, orient='split').to_panel()
                # pandas.Panel is deprecated so return as a DataFrame
                return pandas.read_json(data, orient='split')

            elif typ == SERIES:
                # columns = data.get('columns')
                # # Does the series name get stored in columns? Presumably. Let us try
                # name = columns[0] if columns else None
                # return pandas.Series(data=data.get('data'), index=data.get('index'),
                #                      name=name)
                return pandas.read_json(data, typ='series', orient='split')

            elif typ == NDARRAY:
                return numpy.array(data)

            elif typ == TENSOR:
                # Put here to avoid circular imports
                from ccpn.util.Tensor import Tensor

                return Tensor._fromDict(data)

            elif typ == CROSSREFERENCE:
                # ignore the original type for the minute
                return _CrossReferenceABC._oldFromJson(data)

            elif typ in _CrossReferenceABC.registeredJsonTypes():
                # check for registered subclasses of DataFrameABC
                try:
                    return _CrossReferenceABC._newFromJson(data)

                except Exception:
                    return None

    # default option, std json behaviour
    return dict(pairs)
