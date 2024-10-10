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
__dateModified__ = "$dateModified: 2024-10-04 16:03:30 +0100 (Fri, October 04, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-10-28 11:21:59 +0100 (Thu, October 28, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import collections
import collections.abc
import math
import numbers
import typing
import numpy
import pandas as pd
import re
from functools import partial
from ccpn.util import Sorting
from ccpn.util.ListFromString import listFromString
from ccpn.core.lib.ContextManagers import undoStackBlocking, undoBlockWithoutSideBar


# Pid.IDSEP - but we do not want to import from ccpn.core here
IDSEP = '.'
NaN = math.nan
_REGEXNEFCOMPATIBLE = u'[^0-9a-zA-Z]+'


class DataFrameABC(pd.DataFrame):
    """
    Pandas DataFrame

    The DataFrameABC is based on a Pandas DataFrame.  All the functionality of DataFrames
    is available, but we have added a number of convenience methods for working with the data.

      Functions taking a record and returning True or False can
      be supplied via the func keyword argument.

      For example:
        DataFrameABC.selector(func=lambda r: (r[‘bFactor’]< 70) and (r[‘bFactor’]>60))
        which will select everything with a bFactor between 60 and 70 exclusive.
        The selector can be converted to a filter by setting the inverse keyword to True, so that
        any record that matches the criteria are excluded from the selection.

      Finally, selectors can be combined using Boolean operations.  The following statement:

        s = DataFrameABC.selector(atomNames=’N, CA’)

      is equivalent to:

        s1 = DataFrameABC.selector(atomNames=’CA’)
        s2 = DataFrameABC.selector(atomNames=’N’)
        s = s1 | s2  # Matches either s1 OR s2

      While this statement:
        .. code-block::
        s = DataFrameABC.selector(atomNames=’N, CA’, modelNumbers = ‘1-3’)

      is equivalent to:

        s1 = DataFrameABC.selector(atomNames=’N, CA’)
        s2 = DataFrameABC.selector(modelNumbers = ‘1-3’)
        s = s1 & s2  # Matches both s1 AND s2

      Once you have a selector, you can use it to extract a copy of the rows you want from the
      ensemble via DataFrameABC.extract(). extract() accepts a selector and a list of columns to extract.
      If no selector is provided, extract() will use any criteria provided to generate a selector
      on-the-fly for selection (in fact, this is the recommended usage pattern.)

      The extract() method has some important caveats:
      1. It is very important to remember that extract() gives a COPY of the data, not the original
          data. If you change the data in the extracted ensemble, the original data will remain
          unaltered.
      2. If you use a selector created from one DataFrameABC on a different DataFrameABC, it will fail if they
         don’t have exactly the same number of records.  If they do have the same number of records,
         you will get the records with the corresponding numbers, which is probably not what you want.
      3. In order to avoid the problem in 2., the recommended usage pattern is to let extract()
         create the selector on-the-fly.
      4. If you must create complex selectors, please make sure that you create the selector from the
         exact DataFrameABC you wish to extract from.

    2.	There are several ways to access the data within the DataFrameABC (or an extracted subset
      thereof.) If your DataFrameABC has multiple records, copies of the columns can be accessed by name.
      For example:
        occupancies = DataFrameABC['occupancy']  # Gives a Pandas Series; for a list use list(occupancies)
      Alternatively, you can convert the records into a tuple of namedTuples using the
      as_namedTuples() method.

      If you have a single record, the values can be accessed by column name.
      For example:
        atomName = singleRecordEnsemble[‘atomName’]

      Instead, it’s often better to loop over copies of all the records in a subset using the
      iterrecords() iterator:
        for record in DataFrameABC.iterrecords():
          print(record[‘x’], record[‘y’], record[‘z’])

      or the itertuples() iterator:
        for record in DataFrameABC.itertuples():
          print(record.x, record.y, record.z)

      Finally, all the standard Pandas methods for accessing the data are still available.
      We leave it to the interested coder to investigate that.

      3. Writing data to the DataFrameABC is by far the most tricky operation.  There are two primary
         issues to be dealt with:  putting data in the right place within the DataFrameABC, and making
         sure you’re writing to the DataFrameABC and not a copy of the DataFrameABC.

      The easiest case is probably the least common for users: creating an DataFrameABC from scratch.
      In this case, the best way to create the DataFrameABC is to assign several equal-length lists or
      tuples to columns within the DataFrameABC:
        data = DataFrameABC()
        data[‘modelNumber’] = [1,1,1,2,2,2]
        data[‘chainCode’] = [‘A’, ‘A’, ‘A’, ‘A’, ‘A’, ‘A’]
        # Etc,…
        data = DataFrameABC.reset_index(drop=True)  # Cleanup the indexing

      More commonly, users may want to alter values in a pre-existing DataFrameABC.  The method
      setValues() can be used for this.  The first parameter to setValues() tells setValues() which
      record to change, and can be an index, a single record selector or a single record DataFrameABC
      (this last option is easily achieved with the iterrecords() method.)
      Any subsequent keyword parameters passed to setValues() are the column names and values to set.
      For example:
        extracted = DataFrameABC.extract(residueNames='MET', atomNames='CB')
        for record in extracted.iterrecords():
          if record[‘x’] > 999:
            DataFrameABC.setValues(record, x=999, y=999, z=999)

      Just like extract(), exactly matching the source of your selector/selecting DataFrameABC and the
      DataFrameABC you call setValues() on is vital to prevent unpredictable behavior.
      You have been warned!

      There are currently no insert functions.  You can, if you wish, append a row to the DataFrameABC
      using setValues and passing an index value not currently in the ensemble:
        maxIndexValue = DataFrameABC.index.max()
        DataFrameABC.setValues(maxIndexValue+1, x=0, y=1, z=2)


    ADVANCED: Pandas experts should note that we override __setattr__, __setitem__, and __str__,
    so some behaviours will be different. Specifically columns with reserved names are type-checked,
    and you cannot add new columns with data that match only part of the existing rows.

    NOTE: If subclassing, remember to add classes to ccpn.util.jsonIo.py
    """

    RECORDNAME = 'DataFrameABC'

    # Key is column name, value is (type, customSetterName) tuple
    _reservedColumns = collections.OrderedDict()

    #=========================================================================================
    # Subclass registration
    #=========================================================================================

    # A dict that contains the (className, class) mappings for restoring dataFrameABCs
    _registeredClasses = collections.OrderedDict()
    _registeredDefaultClassName = None
    _JSON_PREFIX = 'ccpn.'


    class _classproperty():
        """Class to define getter for a class-property, similar to a class method.
        """

        def __init__(self, func):
            self._func = func

        def __get__(self, obj, objtype=None):
            return self._func(objtype)


    @staticmethod
    def isRegistered(className) -> bool:
        """Return True if className is registered.
        """
        if not isinstance(className, str):
            raise TypeError(f'{className} must be of type str')
        return className in DataFrameABC._registeredClasses

    @staticmethod
    def isRegisteredInstance(instance) -> bool:
        """Return True if type of instance is a registered class.
        """
        if isinstance(instance, type):
            raise TypeError(f'{instance} must be an instance of a class')
        return instance.__class__.__name__ in DataFrameABC._registeredClasses

    @classmethod
    def register(cls, setDefault=False):
        """Register the class.
        """
        className = cls.__name__
        if cls.isRegistered(className):
            raise RuntimeError(f'className {className!r} already registered')
        cls._registeredClasses[className] = cls
        if setDefault:
            if name := DataFrameABC._registeredDefaultClassName:
                raise RuntimeError(f'Default class {DataFrameABC._registeredClasses[name]} already set')

            # define a default in-case of any unforeseen problems
            DataFrameABC._registeredDefaultClassName = className

    @_classproperty
    def registeredDefaultClassName(self):
        """Return the default registered className.
        """
        return DataFrameABC._registeredDefaultClassName

    @classmethod
    def registeredJsonTypes(cls) -> tuple:
        """Return the json-types of the registered classes.
        Json-types are strings of the form ccpn.<name>; name is the class-name of a registered class.
        :return: tuple of str.
        """
        return tuple(f'{DataFrameABC._JSON_PREFIX}{typ}' for typ in DataFrameABC._registeredClasses)

    @staticmethod
    def _classNameToJsonType(className) -> str:
        """Return json-type from given className.
        A json-type is a string of the form ccpn.<className>.
        """
        return f'{DataFrameABC._JSON_PREFIX}{className}'

    @_classproperty
    def registeredDefaultJsonType(self):
        """Return the json-type of the default registered class.
        A json-type is a string of the form ccpn.<name>; name is the class-name of a registered class.
        """
        if DataFrameABC.registeredDefaultClassName:
            return DataFrameABC._classNameToJsonType(DataFrameABC.registeredDefaultClassName)

    @classmethod
    def jsonType(cls, instance) -> typing.Optional[str]:
        """Return the json-type of the given instance if is a registered class, otherwise None.
        A json-type is a string of the form ccpn.<name>; name is the class-name of a registered class.
        :return: str or None.
        """
        name = instance.__class__.__name__
        if name in DataFrameABC._registeredClasses:
            return DataFrameABC._classNameToJsonType(name)

    @staticmethod
    def fromJsonType(jsonType) -> typing.Optional[callable]:
        """Return the registered class from the json-type, or None if not defined.
        Json-types are strings of the form ccpn.<name>; name is the class-name of a registered class.
        :return: registered class-type.
        """
        return next((klass for typ, klass in DataFrameABC._registeredClasses.items()
                     if DataFrameABC._classNameToJsonType(typ) == jsonType), None)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _containingObject(self) -> typing.Optional['DataTable']:
        """CCPN wrapper object containing instance. """
        return self._containerDataTable

    @_containingObject.setter
    def _containingObject(self, value):
        """Get containing object"""
        if (value is None or (hasattr(value, 'className') and value._isPandasTableClass)):
            self._containerDataTable = value
        else:
            raise ValueError(
                    f'{self.__class__.__name__}._containingObject must be None, subclass of DataTable, was {value}')

    @property
    def _dataTable(self) -> typing.Optional['DataTable']:
        """Get containing DataTable, whether container is DataTable or Model"""
        result = self._containerDataTable
        if hasattr(result, 'className') and result.className == 'Model':
            result = result.dataTable

        return result

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Link to containing DataTable - to allow logging, echoing, and undo
        self._containerDataTable = None

    def _finaliseParent(self, action: str):
        """finalise an action on the parent - should be a subclass of DataTable.
        """
        if self._containerDataTable:
            self._containerDataTable._finaliseAction(action)

    #=========================================================================================
    # Making selections
    #=========================================================================================

    def selector(self, *args, **kwds) -> pd.Series:
        """
        Make a boolean selector restricted to rows matching the parameters specified.
        Returns Pandas Series of booleans
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def _stringSelector(self, expression: typing.Union[str, typing.Iterable[str]],
                        columnName: str) -> pd.Series:
        """Select column 'columnName' based on 'expression',
        which must either be or convert to a sequence of strings
        """
        if isinstance(expression, str):
            expression = listFromString(expression)
        return self[columnName].isin(expression)

    def _indexSelector(self, expression: typing.Union[str, int, typing.Iterable]):
        """Select index based on 'expression'
        """
        if isinstance(expression, str):
            expression = listFromString(expression)
            expression = [int(ii) for ii in expression]  # ejb - check for the other _selectors
        elif isinstance(expression, int):
            expression = [expression, ]
        return self.index.isin(expression)

    def _funcSelector(self, func: callable) -> pd.Series:
        return self.apply(func, axis=1)

    #=========================================================================================
    # Selectors
    #=========================================================================================

    # @property
    # def _ExampleSelector(self) -> pd.Series:
    #     """
    #     Return a selector that selects series from dataframe.
    # 
    #     The selector is specific for:
    #       Ca, C, O, Nh, Hn
    #     """
    #     return self.selector(atomNames=['CA', 'C', 'N', 'O', 'H'])

    #=========================================================================================
    # extracting selections
    #=========================================================================================

    def extract(self, selector: pd.Series = None, *columnNames: str, **kwargs) -> 'DataFrameABC':
        """
        Extracts a copy of a subset of records from DataFrameABC

        Params:

          selector : Boolean Pandas series the same length as the number of rows in the DataFrameABC
                      If no selector is given, the keyword arguments are passed on to the selector
                      function and used to make a selector to use.

          *columnNames: All positional arguments indicate the columns to extract.
                        If there are no columnNames, all columns are extracted.

          **kwargs: All keyword-value arguments are passed to the selector function.

        Returns a new DataFrameABC
        """
        if not columnNames:
            columnNames = self.columns

        if selector is None:
            return self.extract(self.selector(**kwargs), *columnNames)

        else:
            try:
                if self.shape[0] == selector.shape[0]:
                    newEx = self.loc[selector, columnNames]
                    return newEx

                else:
                    raise ValueError('Selectors must be the same length as the number of records.')
            except AttributeError:
                raise ValueError("selector must be a Pandas series or None")

    #=========================================================================================
    # Record-wise access
    #=========================================================================================

    def iterrecords(self) -> 'DataFrameABC':
        """
        An iterator over the records in the DataFrameABC
        """
        for idx, record in self.iterrows():
            yield self.__class__(record.to_frame().T)

    def records(self) -> typing.Tuple['DataFrameABC', ...]:
        return tuple(self.iterrecords())

    def as_namedtuples(self) -> typing.Tuple[typing.Tuple, ...]:
        """
        An tuple of namedtuples containing the records in the DataFrameABC
        """
        return tuple(self.itertuples(name=f'{self.RECORDNAME}Record'))

    #=========================================================================================
    # Record-wise assignment of values
    #=========================================================================================

    def addRow(self, **kwargs):
        """
        Add row with values matching kwargs, setting index to next available index
        See setValues for details
        """
        nextIndex = max(self.index) + 1 if self.shape[0] else 1
        self.setValues(nextIndex, **kwargs)

    def _insertSelectedRows(self, **kwargs):
        """
        Re-insert rows that have been deleted with deleteSelectedRows below
        This is for use by undo/redo only
        """

        if self._containingObject is None:
            # process without undoStack
            insertSet = kwargs['iSR']
            for thisInsertSet in insertSet:
                for rowInd in thisInsertSet:
                    self._insertRow(int(rowInd), **thisInsertSet[rowInd])

            self._finaliseParent('change')  # spawn a change event in StructureEnsemble

        else:
            with undoBlockWithoutSideBar():
                insertSet = kwargs['iSR']
                for thisInsertSet in insertSet:
                    for rowInd in thisInsertSet:
                        self._insertRow(int(rowInd), **thisInsertSet[rowInd])

                self._finaliseParent('change')  # spawn a change event in StructureEnsemble

    def deleteSelectedRows(self, **kwargs):
        """
        Delete rows identified by selector.
        For example (index='1, 2, 6-7, 9')
                    (modelNumbers='1, 2') or
                    (residueNames='LEU, THR')

        In the cases of the reserved columns, the name may need to be plural for deletion

        e.g. above, the column headed modelNumberm ay be accessed as 'modelNumbers'

        **kwargs: All keyword-value arguments are passed to the selector function.

        Selector created, e.g. by self.selector)
        """

        rowSelector = self.selector(**kwargs)

        selection = self.extract(rowSelector)
        if not selection.shape[0]:
            # nothing to delete
            return

        deleteRows = selection.as_namedtuples()

        if self._containingObject is None:
            # process without undoStack
            colData = []
            for rows in deleteRows:
                colInd = getattr(rows, 'Index')
                colData.append({str(colInd): dict((x, self.loc[colInd].get(x)) for x in self.columns)})

            self.drop(self[rowSelector].index, inplace=True)
            self.reset_index(drop=True, inplace=True)

            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():
                colData = []
                for rows in deleteRows:
                    colInd = getattr(rows, 'Index')
                    colData.append({str(colInd): dict((x, self.loc[colInd].get(x)) for x in self.columns)})

                self.drop(self[rowSelector].index, inplace=True)
                self.reset_index(drop=True, inplace=True)

                with undoStackBlocking() as addUndoItem:
                    addUndoItem(undo=partial(self._insertSelectedRows, iSR=colData),
                                redo=partial(self.deleteSelectedRows, **kwargs))

                self._finaliseParent('change')

    def _insertRow(self, *args, **kwargs):
        """
        Currently called by undo to re-insert a row.
        Add the **kwargs to new element at the bottom of each column.
        Modify the index and sort the new row into the correct position.
        Only for use by deleteCol for undo/redo functionality

        :param *args: index in args[0]
        :param kwargs: dict of items to reinsert
        """
        if self._containingObject is None:
            # process without undoStack
            index = int(args[0])
            ln = self.shape[0]  # current rows
            for key in kwargs:
                self.loc[ln + 1, key] = kwargs[key]  # force an extra row

            neworder = [x for x in range(1, index)] + [x for x in range(index + 1, ln + 2)] + [index]
            self.index = neworder  # set the new index
            self.sort_index(inplace=True)  # and re-sort the table

            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():

                index = int(args[0])
                ln = self.shape[0]  # current rows
                for key in kwargs:
                    self.loc[ln + 1, key] = kwargs[key]  # force an extra row

                neworder = [x for x in range(1, index)] + [x for x in range(index + 1, ln + 2)] + [index]
                self.index = neworder  # set the new index
                self.sort_index(inplace=True)  # and re-sort the table

                self._finaliseParent('change')

    def deleteRow(self, rowNumber: None):
        """
        Delete a numbered row of the table.
        Row must be an integer and exist in the table.

        :param rowNumber: row to delete
        """
        if rowNumber is None:
            raise TypeError('deleteRow: required positional argument')
        if not isinstance(rowNumber, int):
            raise TypeError('deleteRow: Row is not an int')
        if rowNumber not in self.index:  # the index must exist
            raise ValueError('deleteRow: Row does not exist')

        index = rowNumber
        if self._containingObject is None:
            # process without undoStack
            self.drop(index, inplace=True)  # delete the row
            self.reset_index(drop=True, inplace=True)  # reset the index

            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():

                colData = dict((x, self.loc[index].get(x)) for x in self.columns)  # grab the original values

                self.drop(index, inplace=True)  # delete the row
                self.reset_index(drop=True, inplace=True)  # reset the index

                with undoStackBlocking() as addUndoItem:
                    addUndoItem(undo=partial(self._insertRow, index, **colData),
                                redo=partial(self.deleteRow, index))

                self._finaliseParent('change')

    def _insertCol(self, colName, colNum, colData):
        """
        Currently called by undo to re-insert a column.
        Add the **kwargs to the column across the index.
        Currently, *args are not checked for multiple values
        Only for use by deleteCol for undo/redo functionality

        :param *args: colIndex in args[0]
        :param colData: items to reinsert as a Dict
        """
        if self._containingObject is None:
            # process without undoStack
            self.insert(colNum, colName, colData)
            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():
                self.insert(colNum, colName, colData)
                self._finaliseParent('change')

    def deleteCol(self, columnName=None):
        """
        Delete a named column from the table, the columnName must be a string and exist in the table.

        :param columnName:  name of the column
        """
        if columnName is None:
            raise TypeError('deleteCol: required positional argument')
        if not isinstance(columnName, str):
            raise TypeError('deleteCol: Column is not a string')
        if columnName not in self.columns:  # the index must exist
            raise ValueError('deleteCol: Column does not exist.')

        colName = columnName
        colNum = list(self.columns).index(colName)

        if self._containingObject is None:
            # process without undoStack
            self.drop(colName, axis=1, inplace=True)
            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():
                # colData = dict((str(sInd), self.loc[sInd].get(colName)) for sInd in self.index)  # grab the original values
                colData = self[colName].copy()
                self.drop(colName, axis=1, inplace=True)

                with undoStackBlocking() as addUndoItem:
                    addUndoItem(undo=partial(self._insertCol, colName, colNum, colData),
                                redo=partial(self.deleteCol, colName))

                self._finaliseParent('change')

    def setValues(self, accessor: typing.Union[int, 'DataFrameABC', pd.Series], **kwargs) -> None:
        """
        Allows you to easily set values (in place) for fields in the EnsembleData

        Params:
          accessor : int, DataFrameABC, Selector
                     If an integer is given, the value will be set on the row at that index,
                     a new row will be added if the value is the next free index,
                     or ValueError will be raised.

                     If a single row DataFrameABC is given, the value will be set on the matching row.

                     If a selector that matches a single row is given, the value will be set on that
                     matching row

                     Multi-row DataFrameABC or selectors are not allowed.
                     (consider using DataFrameABC.iterrecords() to iterate)

          kwargs : columns on which to set the values

        """

        # Row selection:
        rowExists = True
        if isinstance(accessor, pd.Int64Index):
            accessor = int(accessor[0])  # ejb - accessor becomes the wrong type on undo

        if isinstance(accessor, (int, numpy.integer)):
            # This is utter ****! Why are numpy.integers not ints, or at least with a common superclass?
            # Shows again that numpy is an alien growth within python.
            index = accessor
            if index in self.index:
                rowExists = True
            else:
                rowExists = False
                nextIndex = max(self.index) + 1 if self.shape[0] else 1
                if index != nextIndex:
                    raise ValueError("setValues cannot create a new row, "
                                     "unless accessor is the next free integer index")

            if kwargs:
                # ejb - only get those values that have the correct index
                sl = self.loc[index]
                oldKw = dict((x, sl[x]) for x in kwargs)
            else:
                oldKw = dict((x, self[x]) for x in kwargs)  # get everything, as no kwargs specified

        elif isinstance(accessor, DataFrameABC):
            if accessor.shape[0] != 1:
                raise ValueError(f'Only single row {self.__class__.__name__}s can be used for setting.')
            index = accessor.index

            aant = accessor.as_namedtuples()  # testing for below
            slan = self.loc[index].as_namedtuples()

            if not (index[0] in self.index and aant == slan):
                raise ValueError(f'{self.__class__.__name__}s used for selection must be '
                                 f'(or match) row in current {self.__class__.__name__}')

            sl = self.loc[index].as_namedtuples()  # DataFrameABC get
            nt = sl[0]._asdict()
            oldKw = dict((x, nt[x]) for x in kwargs)

        elif isinstance(accessor, pd.Series):  # selector
            rows = accessor[accessor == True]
            if rows.shape[0] != 1:
                raise ValueError('Boolean selector must select a single row.')
            index = rows.index
            if index[0] not in self.index:
                raise ValueError('Boolean selector must select an existing row')

            try:
                sl = self.loc[index].as_namedtuples()  # ensemble get
                nt = sl[0]._asdict()
                oldKw = dict((x, nt[x]) for x in kwargs)
            except KeyError:
                raise ValueError("Attempt to set columns not present in DataFrame: %s"
                                 % list(kwargs))

        else:
            raise TypeError('accessor must be index, ensemble row, or selector.')

        if rowExists and not kwargs:
            # No changes - and setting with an empty dictionary gives an error
            return

        # input data and columns
        values = {}
        kwargsCopy = kwargs.copy()
        for col in self.columns:

            # dataType, typeConverterName = self._reservedColumns.get(col) or (None, None)

            if col in kwargsCopy:
                value = kwargsCopy.pop(col)

                values[col] = value

            elif not rowExists:
                # For new rows we want None rather than NaN as the default values
                # For existing rows we leave the existing value
                values[col] = None

        if kwargsCopy:
            # Some input did not match columns
            raise ValueError("Attempt to set columns not present in DataFrameABC: %s"
                             % list(kwargsCopy))

        if self._containingObject is None:
            # process without undoStack
            for key, val in values.items():
                self.loc[index, key] = val

            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():
                with undoStackBlocking() as addUndoItem:

                    # We must do this one by one - passing in the dictionary
                    # gives you a series, and coerces None to NaN.

                    # Internally this calls self.__setitem__.
                    # Type handling is done there and can be skipped here.
                    # NB, various obvious alternatives, like just setting the row, do NOT work.

                    self.loc[index, values.keys()] = list(values.values())
                    if rowExists:
                        # Undo modification of existing row
                        addUndoItem(undo=partial(self.setValues, index, **oldKw),
                                    redo=partial(self.setValues, index, **kwargs))
                    else:
                        # undo addition of new row
                        addUndoItem(undo=partial(self.drop, index, inplace=True),
                                    redo=partial(self.setValues, index, **kwargs))

                    self._finaliseParent('change')

    def getByHeader(self, headerName: str, matchingValues: list):
        """
        Get a subset of this TableFrame if the given matchingValues are present in the given HeaderName column.
        :param headerName: str
        :param matchingValues: list of value to be present in the dataFrame in the given header.
        :return: filtered dataFrame
        """
        if headerName not in self.columns:
            return
        return self[self[headerName].isin(matchingValues)]

    #=========================================================================================
    # Pandas compatibility methods
    #=========================================================================================

    @property
    def _constructor(self):
        return self.__class__

    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name in self._reservedColumns and name in self:
            # notification done at the __setitem__ level
            self[name] = value
        else:
            super().__setattr__(name, value)
            self._finaliseParent('change')

    #=========================================================================================
    # Property type checking
    #=========================================================================================

    def _ccpnUnSort(self, oldIndex):
        """Custom Unsort: revert the table to its presorted state
        """
        self.index = oldIndex
        self.sort_index(inplace=True)
        self.reset_index(drop=True, inplace=True)  # use the correct reset_index

    def ccpnSort(self, *columns: str):
        """Custom sort. Sorts mixed-type columns by type, sorting None and NaN at the start

        If nmrSequenceCode or nmrAtomName or nmrChainCode are included in columns
        uses custom sort *for all strings* so that e.g. '@3' comes before '@12' and '7b' before '22a'
        """
        # Set sorting key for sorting mixed incompatible types
        if ('nmrSequenceCode' in columns or 'nmrAtomName' in columns
                or 'nmrChainCode' in columns):
            # Sort so that all strings containing integers are sorted by the integer
            # E.g. '@9' before '@12', and '3' before '21b'
            # Basically a heuristic to sort nmrSequenceCode or nmrAtomName in sensible order
            sortKey = Sorting.universalNaturalSortKey
        else:
            # sort strings normally
            sortKey = Sorting.universalSortKey

        self._ccpnSort(sortKey, *columns)

    def _ccpnSort(self, sortKey, *columns: str):
        """Custom sort. Sorts mixed-type columns by type, sorting None and NaN at the start

        If nmrSequenceCode or nmrAtomName or nmrChainCode are included in columns
        uses custom sort *for all strings* so that e.g. '@3' comes before '@12' and '7b' before '22a' """
        cols = list(self[x] for x in columns)
        cols.append(self.index)

        # old index in sorted order
        reordered = list(tt[-1] for tt in sorted(zip(*cols), key=sortKey))
        ll = list((prev, new + 1) for new, prev in enumerate(reordered))
        newIndex = list(tt[1] for tt in sorted(ll))

        if self._containingObject is None:
            # process without undoStack
            self.index = newIndex
            self.sort_index(inplace=True)
            self.reset_index(drop=True, inplace=True)  # use the correct reset_index

            self._finaliseParent('change')

        else:
            with undoBlockWithoutSideBar():
                with undoStackBlocking() as addUndoItem:
                    self.index = newIndex
                    self.sort_index(inplace=True)

                    # reset index to one-origin successive integers
                    self.reset_index(drop=True, inplace=True)  # use the correct reset_index

                    addUndoItem(undo=partial(self._ccpnUnSort, reordered),
                                redo=partial(self.ccpnSort, *columns))

                self._finaliseParent('change')

    def clear(self):
        """
        :return: empty dataframe
        """
        self.drop(self.index, inplace=True)

    def reset_index(self, *args, inplace=False, **kwargs):
        """reset_index - overridden to generate index starting at one.
        """
        if inplace:
            super().reset_index(*args, inplace=True, **kwargs)
            self.index = self.index + 1
            self._finaliseParent('change')
        else:
            new_obj = self.copy()
            self.__class__.__bases__[0].reset_index(new_obj, *args, inplace=True, **kwargs)
            new_obj.index = new_obj.index + 1
            return new_obj

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """If the key is a single string with a reserved column name
        the value(s) must be of the right type, and the operation is echoed and undoable.
        Other keys are treated like native Pandas operations: no echoing, no undoing,
        and no type checking.
        """

        firstData = not (self.shape[0])

        try:
            # may be a multi-column set, which is not implemented yet
            columnTypeData = self._reservedColumns.get(key) or (None, None)
        except Exception as es:
            # proceed as normal without dataType check
            columnTypeData = (None, None)

        if columnTypeData is None:
            # Not a reserved column name - set the value. No echoing or undo. - currently bypassed?
            super().__setitem__(key, value)

        else:
            # Reserved column name (which must be a plain string)
            if self._containingObject is None:
                # process without any blocking or undoStack
                oldValue = self.get(key)
                if oldValue is not None:
                    oldValue = oldValue.copy()

                # Set the value using normal Pandas behaviour.
                # Anyway it is impossible to modify the input, as it could take so many forms
                # We clean up the type castings etc. lower down
                super().__setitem__(key, value)

                dataType, typeConverterName = columnTypeData
                try:

                    if typeConverterName:
                        if hasattr(self, typeConverterName):
                            # get typeConverter and call it. It modifies self in place.
                            getattr(self, typeConverterName)()
                        else:
                            raise RuntimeError("Code Error. Invalid type converter name %s for column %s"
                                               % (typeConverterName, key))
                    elif dataType:
                        # We set again to make sure of the dataType, None can be ignored
                        ll = fitToDataType(self[key], dataType)
                        if dataType is int and None in ll:
                            super().__setitem__(key, pd.Series(ll, self.index, dtype=object))
                        else:
                            super().__setitem__(key, pd.Series(ll, self.index, dtype=dataType))

                    if firstData:
                        self.reset_index(drop=True, inplace=True)

                    self._finaliseParent('change')

                except Exception as es:
                    # We set the new value before the try:, so we need to go back to the previous state
                    if oldValue is None:
                        self.drop(key, axis=1, inplace=True)
                    else:
                        super().__setitem__(key, oldValue)
                    raise

            else:
                with undoBlockWithoutSideBar():
                    with undoStackBlocking() as addUndoItem:
                        # WE need a copy, not a view, as this is used for undoing etc.
                        oldValue = self.get(key)
                        if oldValue is not None:
                            oldValue = oldValue.copy()

                        # Set the value using normal Pandas-behaviour.
                        # Anyway it is impossible to modify the input, as it could take so many forms
                        # We clean up the type castings etc. lower down
                        super().__setitem__(key, value)

                        dataType, typeConverterName = columnTypeData
                        try:

                            if typeConverterName:
                                if hasattr(self, typeConverterName):
                                    # get typeConverter and call it. It modifies self in place.
                                    getattr(self, typeConverterName)()
                                else:
                                    raise RuntimeError("Code Error. Invalid type converter name %s for column %s"
                                                       % (typeConverterName, key))
                            elif dataType:
                                # We set again to make sure of the dataType
                                ll = fitToDataType(self[key], dataType)
                                if dataType is int and None in ll:
                                    super().__setitem__(key, pd.Series(ll, self.index, dtype=object))
                                else:
                                    # not always guaranteed a .loc can change ints to floats :|
                                    super().__setitem__(key, pd.Series(ll, self.index, dtype=dataType))

                            if firstData:
                                self.reset_index(drop=True, inplace=True)

                            # add item to the undo-stack
                            if oldValue is None:
                                # undo addition of new column
                                addUndoItem(undo=partial(self.drop, key, axis=1, inplace=True),
                                            redo=partial(self.__setitem__, key, value))
                            else:
                                # Undo overwrite of existing column
                                addUndoItem(undo=partial(super().__setitem__, key, oldValue),
                                            redo=partial(self.__setitem__, key, value))

                            self._finaliseParent('change')

                        except Exception as es:
                            # We set the new value before the try:, so we need to go back to the previous state
                            if oldValue is None:
                                self.drop(key, axis=1, inplace=True)
                            else:
                                super().__setitem__(key, oldValue)
                            raise

    @property
    def nefCompatibleColumns(self):
        """Return the columns as nef compatible,
        changes all upper to lower, replaces all others with _
        Appends number to end of duplicate columns.
        This is not reversible, but the actual columns are stored in the metadata.
        """
        cols = []
        for col in self.columns:
            header = re.sub(_REGEXNEFCOMPATIBLE, '_', col.lower())
            # iterate until a non-repeating header is found
            newHeader = next((''.join([header, str(_count or '')])
                              for _count in range(len(self.columns))
                              if ''.join([header, str(_count or '')]) not in cols), None
                             )
            cols.append(newHeader)
        return cols


def fitToDataType(data: collections.abc.Sequence, dataType: type, force: bool = False) -> list:
    """Convert any data sequence to a list of dataType.

    If force will convert all values to type, if possible, and set None otherwise.
    Otherwise, will check that all values are of correct type or None,
    and raise ValueError otherwise.

    force=True will work for types int, float, or str; it may or may not work for other types
    """
    Real = numbers.Real

    if dataType is float:
        if force:
            # Convert all convertible to float (including e.g. '3.7')
            return list(pd.to_numeric(data, errors='coerce'))
        else:
            # Convert None to NaN and return if all-float
            dd = {None: float('NaN')}
            try:
                return list(x if isinstance(x, Real) else dd[x] for x in data)
            except KeyError:
                raise ValueError("Data contain non-float values")

    elif dataType is int:
        # See valueToOptionalInt function for details
        return list(valueToOptionalInt(x, force=force) for x in data)

    else:
        # This certainly works for str and may mostly work for other types
        # (e.g. bool will fail for numpy arrays)
        return list(valueToOptionalType(x, dataType, force=force) for x in data)


def valueToOptionalType(x, dataType: type, force=False) -> typing.Optional['dataType']:
    """Converts  None and NaN to None, and returns list of optional dataType

    if force is True tries to coerce value to dataType
    """
    if x is None:
        return None

    elif isinstance(x, numbers.Real) and math.isnan(x):
        return None

    elif isinstance(x, dataType):
        return x

    elif force:
        try:
            return dataType(x)
        except:
            raise TypeError("Value %s does not correspond to type %s" % (x, dataType))

    else:
        raise TypeError("Value %s does not correspond to type %s" % (x, dataType))


def valueToOptionalInt(x, force: bool = False) -> typing.Optional[int]:
    """Converts None and NaN to None, and integer-valued floats to their int value

    if force is True calls float(x) before testing
    """
    if x is None or isinstance(x, numbers.Real) and math.isnan(x):
        return None

    if force:
        try:
            x = float(x)
        except:
            return None
        if math.fmod(x, 1):
            return None
        else:
            return int(x)

    elif isinstance(x, numbers.Real) and not math.fmod(x, 1):
        # value equal to integer
        return int(x)

    elif isinstance(x, str):
        try:
            return int(x)
        except ValueError:
            raise TypeError("Value %s does not correspond to an integer" % x)

    else:
        raise TypeError("Value %s does not correspond to an integer" % x)
