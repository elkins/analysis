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
__dateModified__ = "$dateModified: 2024-08-23 19:26:35 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-06-05 13:01:10 +0100 (Mon, June 05, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import json
import typing
import numpy as np
import warnings
from functools import reduce
from operator import mul
from collections import OrderedDict
from scipy.sparse import csr_matrix, csc_matrix, SparseEfficiencyWarning
from ccpn.core.Project import Project
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core._implementation.V3CoreObjectABC import V3CoreObjectABC
from ccpn.framework.Application import getProject
from ccpn.util.Logging import getLogger
from ccpn.util.Common import NOTHING


V3Core = typing.TypeVar('V3Core', bound=AbstractWrapperObject | V3CoreObjectABC)  # these could be mixed in iterables
Sparse = typing.TypeVar('Sparse', csr_matrix, csc_matrix)  # these cannot
TypeV3Core = V3Core.__bound__
TypeSparse = Sparse.__constraints__

# definitions for building the dict
INDICES = 'indices'
INDPTR = 'indptr'
DATA = 'data'
SHAPE = 'shape'
DTYPE = 'dtype'
DFORMAT = 'dformat'
ROWCLASSNAME = 'rowClassName'
COLUMNCLASSNAME = 'columnClassName'
ROWPIDS = 'rowPids'
COLUMNPIDS = 'columnPids'

ROWDATA: int = 0
COLUMNDATA: int = 1
_PID2OBJ = '_pid2Obj'
_OBJ2PID = '_obj2Pid'
_INDEX2PID = '_index2Pid'
_PID2INDEX = '_pid2Index'  # not sure if I need this
_PIDS = '_pids'
_KLASS = '_klass'
_KLASSNAME = '_klassName'
_BUILDFROMPROJECT = '_BUILDFROMPROJECT'

warnings.simplefilter('ignore', SparseEfficiencyWarning)

_CREATE = 'create'
_DELETE = 'delete'
_RENAME = 'rename'
_DELETEPOSTFIX = '-Deleted'


#=========================================================================================
# Helper classes
#=========================================================================================

class _classproperty():
    """Class to define getter for a class-property, similar to a class method.
    """

    def __init__(self, func: callable):
        self._func = func

    def __get__(self, obj, objtype=None):
        return self._func(objtype)


# class _CrossReferenceMeta(type):
#     """Insert class properties."""
#     # :( this seems to hide the methods from the class, but they are still available
#     # but actually works nicely
#     @property
#     def registeredDefaultClassName(cls) -> str:
#         return _CrossReferenceABC._registeredDefaultClassName
# 
#     @property
#     def registeredDefaultJsonType(cls) -> str | None:
#         """Return the json-type of the default registered class.
#         A json-type is a string of the form ccpn.<name>; name is the class-name of a registered class.
#         """
#         if dcn := _CrossReferenceABC.registeredDefaultClassName:
#             return _CrossReferenceABC._classNameToJsonType(dcn)


#=========================================================================================
# _CrossReferenceABC
#=========================================================================================

class _CrossReferenceABC():
    """
    Class to hold the cross-references between project core-objects.
    
    It is defined by two core class-types, e.g. Mark and Strip.
    
    Internally stored as:
        _indexing = {ROWDATA   : {_KLASS    : None,
                                  _KLASSNAME: None,
                                  _PIDS     : [],
                                  _PID2OBJ  : {},
                                  _OBJ2PID  : {},
                                  },
                     COLUMNDATA: {_KLASS    : None,
                                  _KLASSNAME: None,
                                  _PIDS     : [],
                                  _PID2OBJ  : {},
                                  _OBJ2PID  : {},
                                  },
                     }
    """
    #=========================================================================================
    # Subclass registration
    #=========================================================================================

    # A dict that contains the (className, class) mappings for restoring _CrossReferences
    _registeredClasses = OrderedDict()
    _registeredDefaultClassName: str = None
    _JSON_PREFIX: str = 'ccpn.'

    # The class-types for the cross-reference, the order must be strictly observed.
    rowKlass: typing.Type[V3Core] = None
    columnKlass: typing.Type[V3Core] = None

    @staticmethod
    def isRegistered(className: str) -> bool:
        """Return True if className is registered.

        :param str className: className
        :return: class is registered
        :rtype: bool
        """
        if not isinstance(className, str):
            raise TypeError(f'{className} must be of type str')
        return className in _CrossReferenceABC._registeredClasses

    @staticmethod
    def isRegisteredInstance(instance: V3Core) -> bool:
        """Return True if type of instance is a registered class.

        :param V3Core instance: instance of core-class
        :return: instance is registered
        :rtype: bool
        """
        if isinstance(instance, TypeV3Core):
            raise TypeError(f'{instance} must be an instance of a core-class')
        return instance.__class__.__name__ in _CrossReferenceABC._registeredClasses

    @classmethod
    def register(cls, setDefault: bool = False):
        """Register the class.

        :param bool setDefault: set as default class-type
        """
        className = cls.__name__
        # data must be stored under THIS class not any subclasses
        if _CrossReferenceABC.isRegistered(className):
            raise RuntimeError(f'className {className!r} already registered')
        _CrossReferenceABC._registeredClasses[className] = cls
        if setDefault:
            if name := _CrossReferenceABC._registeredDefaultClassName:
                raise RuntimeError(f'Default class {_CrossReferenceABC._registeredClasses[name]} already set')
            # define a default in-case of any unforeseen problems
            _CrossReferenceABC._registeredDefaultClassName = className

    # noinspection PyMethodParameters
    @_classproperty
    def registeredDefaultClassName(cls) -> str:
        """Return the default registered className.

        :return: className
        :rtype: str
        """
        return _CrossReferenceABC._registeredDefaultClassName

    @classmethod
    def registeredJsonTypes(cls) -> tuple[str, ...]:
        """Return the json-types of the registered classes.

        Json-types are strings of the form ccpn.<name>; name is the class-name of a registered class.

        :return: tuple of json strings
        :rtype: tuple[str, ...]
        """
        return tuple(_CrossReferenceABC._classNameToJsonType(typ) for typ in _CrossReferenceABC._registeredClasses)

    @staticmethod
    def _classNameToJsonType(className: str) -> str:
        """Return json-type from given className.

        A json-type is a string of the form ccpn.<className>.

        :return: json-type
        :rtype: str
        """
        return f'{_CrossReferenceABC._JSON_PREFIX}{className}'

    # noinspection PyMethodParameters
    @_classproperty
    def registeredDefaultJsonType(cls) -> str | None:
        """Return the json-type of the default registered class.

        A json-type is a string of the form ccpn.<name>; name is the class-name of a registered class.

        :return: json-type or None
        :rtype: str | None
        """
        if dcn := _CrossReferenceABC.registeredDefaultClassName:
            return _CrossReferenceABC._classNameToJsonType(dcn)

    @classmethod
    def jsonType(cls, instance: V3Core) -> str | None:
        """Return the json-type of the given instance if is a registered class, otherwise None.

        A json-type is a string of the form ccpn.<name>; name is the class-name of a registered class.

        :return: json-type or None
        :rtype: str | None
        """
        name = instance.__class__.__name__
        if name in _CrossReferenceABC._registeredClasses:
            return _CrossReferenceABC._classNameToJsonType(name)

    @staticmethod
    def fromJsonType(jsonType: str) -> typing.Type[V3Core] | None:
        """Return the registered class from the json-type, or None if not defined.

        Json-types are strings of the form ccpn.<name>; name is the class-name of a registered class.

        :return: registered class-type or None
        :rtype: Type[V3Core] | None
        """
        return next((klass for typ, klass in _CrossReferenceABC._registeredClasses.items()
                     if _CrossReferenceABC._classNameToJsonType(typ) == jsonType), None)

    @staticmethod
    def registeredReferencePairs() -> tuple[tuple[typing.Type[V3Core], typing.Type[V3Core]], ...]:
        """Return a tuple of tuples of the form ((class A, class B), ...) for all the registered cross-references classes.

        Class A and Class B are the registered core class types for each cross-reference class.

        :return: tuple of tuples of registered pairs
        :rtype: tuple[tuple[Type[V3Core], Type[V3Core]], ...]
        """
        return tuple((ref.rowKlass, ref.columnKlass)
                     for ref in _CrossReferenceABC._registeredClasses.values() if (ref.rowKlass and ref.columnKlass))

    #=========================================================================================
    # Implementation
    #=========================================================================================

    @classmethod
    def _newFromJson(cls, jsonData: str) -> V3Core | None:
        """Create a new instance from json data.

        :param str jsonData: json string
        :return: new instance or None
        :rtype: V3Core | None
        """
        project = getProject()
        values = _CrossReferenceABC.fromJson(jsonData)

        jType = _CrossReferenceABC._classNameToJsonType(f'_{values.get("rowClassName")}{values.get("columnClassName")}')
        if klass := _CrossReferenceABC.fromJsonType(jType):
            # SHOULD always be a defined json-type
            return klass(project=project, **values)

    @staticmethod
    def _new(rowClassName: str, columnClassName: str) -> V3Core | None:
        """Create a new instance from class-names.

        :param str rowClassName: row class-name
        :param str columnClassName: column class-name
        :return: new instance or None
        :rtype: V3Core | None
        """
        project = getProject()

        jType = _CrossReferenceABC._classNameToJsonType(f'_{rowClassName}{columnClassName}')
        if klass := _CrossReferenceABC.fromJsonType(jType):
            # SHOULD always be a defined json-type
            return klass(project=project, rowClassName=rowClassName, columnClassName=columnClassName)

    @classmethod
    def _oldFromJson(cls, jsonData: str = '') -> V3Core | None:
        """Create an instance from json data.

        CCPNInternal - deprecated, mistake by Ed :|
        """
        project = getProject()
        values = _CrossReferenceABC.fromJson(jsonData)

        # note the lack of an underscore
        jType = _CrossReferenceABC._classNameToJsonType(f'{values.get("rowClassName")}{values.get("columnClassName")}')
        if klass := _CrossReferenceABC.fromJsonType(jType):
            # SHOULD always be a defined json-type
            return klass(project=project, **values)

    #=========================================================================================
    # Instance methods
    #=========================================================================================

    def __init__(self, project: Project,
                 rowClassName: str = None, columnClassName: str = None,
                 indices: list[int] = NOTHING, indptr: list[int] = NOTHING, data: list[int] = NOTHING,
                 shape: tuple[int, int] = NOTHING,
                 dtype: str = 'int8', dformat: str = 'csr',
                 rowPids: list = NOTHING, columnPids: list = NOTHING,
                 ):
        """Create a new instance of cross-reference.
        
        If shape is not specified, then a new cross-reference is created from 
        rowClassName and columnClassName, and from the project attributes.
        
        :param project: current project instance
        :param str rowClassName: name of the first core object type, e.g., 'Mark' or 'Strip'
        :param str columnClassName: name of the second core object type, e.g., 'Mark' or 'Strip'
        :param list[int] indices: parameters defining a sparse matrix in column-row format
        :param list[int] indptr: parameters defining a sparse matrix in column-row format
        :param list[Any] data: parameters defining a sparse matrix in column-row format
        :param tuple[int, int] shape: size of the matrix
        :param str dtype: type of the matrix data (most-probably int8)
        :param str dformat: either sparse-row row or sparse-column
        :param list[str] rowPids: list of pids for the first axis
        :param list[str] columnPids: list of pids for the second axis
        """
        self._indices = indices
        self._indptr = indptr
        self._data = data
        self._shape = shape
        self._dtype = dtype
        self._dformat = dformat
        self._storageType = csr_matrix if dformat == 'csr' else csc_matrix

        self._axes = {}
        self._buildFromProject = None
        self._matrix = None

        if shape == NOTHING:
            # nothing defined yet so get from project properties
            self._makeNewIndexing(project, rowClassName, columnClassName)

        else:
            # rebuild from the loaded sparse-matrix
            self._makeIndexing(project, rowClassName, columnClassName, rowPids, columnPids)

    def _initialiseAxis(self, project: Project, axis: int, className: str) -> dict:
        """Initialise the class and name for axis.

        :param Project project: current project
        :param int axis: axis to initialise
        :param str className: class-name for this axis
        :return: updated axis instance
        :rtype: dict
        """
        dd = self._axes[axis] = {}
        dd[_KLASS] = project._className2Class.get(className)
        dd[_KLASSNAME] = className

        # if klass is None:
        #     RuntimeError(f'{self.__class__.__name__}: className is not defined')

        return dd

    def _newAxis(self, project: Project, axis: int) -> dict:
        """Create a new axis from the project core-object list defined by the axis class.

        :param Project project: current project
        :param int axis: axis to initialise
        :return: new axis instance
        :rtype: dict
        """
        dd = self._axes[axis]
        klass = dd[_KLASS]

        coreObjs = getattr(project, klass._pluralLinkName, [])  # e.g. project.peaks
        _corePids = [obj.pid for obj in coreObjs]

        # make sure to use the correct matching pids/core-objects - order doesn't matter
        dd[_PIDS] = _corePids
        dd[_PID2OBJ] = dict(zip(_corePids, coreObjs))
        dd[_OBJ2PID] = dict(zip(coreObjs, _corePids))

        return dd

    def _makeNewIndexing(self, project: Project, rowClassName: str, columnClassName: str):
        """Make new cross-reference from core-class definitions.

        :param Project project: current project
        :param str rowClassName: class-name for rows
        :param str columnClassName: class-name for columns
        """
        self._axes = {}
        self._initialiseAxis(project, ROWDATA, rowClassName)
        self._initialiseAxis(project, COLUMNDATA, columnClassName)

        self._buildFromProject = True

    def _verifyAxis(self, project: Project, axis: int) -> dict:
        """Verify that the pids are correct.

        :param Project project: current project
        :param int axis: axis to verify
        :return: verified axis instance
        :rtype: dict
        """
        # the order is not necessarily the same as the project order
        dd = self._axes[axis]
        klass = dd[_KLASS]

        coreObjs = getattr(project, klass._pluralLinkName, [])  # e.g. project.peaks

        # check the row pids - order may be different, but not an issue
        _corePids = [obj.pid for obj in coreObjs]
        pids = dd[_PIDS]

        if set(_corePids) != set(pids):
            raise RuntimeError(f'{self.__class__.__name__}: unknown pids in {dd[_KLASSNAME]}')

        # make sure to use the correct matching pids/core-objects - order doesn't matter
        dd[_PID2OBJ] = dict(zip(_corePids, coreObjs))
        dd[_OBJ2PID] = dict(zip(coreObjs, _corePids))

        return dd

    def _makeIndexing(self, project: Project,
                      rowClassName: str, columnClassName: str,
                      rowPids: list[str], columnPids: list[str]):
        """Make the indexing from the current list of indexes and pids.

        :param Project project: current project
        :param str rowClassName: class-name for rows
        :param str columnClassName: class-name for columns
        :param list[str] rowPids: list of pids for rows
        :param list[str] columnPids: list of pids for columns
        """
        # should handle empty lists
        self._axes = {}

        ddRow = self._initialiseAxis(project, ROWDATA, rowClassName)
        ddRow[_PIDS] = rowPids
        ddCol = self._initialiseAxis(project, COLUMNDATA, columnClassName)
        ddCol[_PIDS] = columnPids

        self._buildFromProject = False

    #=========================================================================================
    # Sparse operations
    #=========================================================================================

    @staticmethod
    def sparseMemoryUsage(matrix: Sparse) -> int:
        """Return the number of bytes used for a scipy.sparse-matrix.

        Returns -1 if the matrix is missing any attributes.

        :param sparse matrix: scipy.sparse.csr_matrix or scipy.sparse.csc_matrix
        :return: number of bytes used or -1
        :rtype: int
        :raise TypeError: If matrix is not the correct type
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'insertRow: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')

        try:
            return matrix.data.nbytes + matrix.indptr.nbytes + matrix.indices.nbytes
        except AttributeError:
            return -1

    def insertCol(self, matrix: Sparse, insert_col: int) -> Sparse:
        """Insert an empty column into a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        insert_col must be a valid column number for the matrix.

        :param sparse matrix: sparse-matrix
        :param int insert_col: column number
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'insertCol: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(insert_col, int):
            raise TypeError('insertCol: insert_col is not an int')
        if not (0 <= insert_col <= matrix.shape[1]):
            raise ValueError(f'insertCol: insert_col {insert_col} is out-of-bounds, must be [0, {matrix.shape[1]}]')

        return self._storageType(
                (matrix.data, np.where(matrix.indices < insert_col, matrix.indices, matrix.indices + 1), matrix.indptr),
                shape=(matrix.shape[0], matrix.shape[1] + 1))

        # if inplace:  # Idea for inplace
        #     matrix.indices = np.where(matrix.indices < insert_col, matrix.indices, matrix.indices + 1)
        #     matrix._shape = (matrix.shape[0], matrix.shape[1] + 1)
        #     return matrix
        # else:
        #     return csr_matrix((matrix.data, np.where(matrix.indices < insert_col, matrix.indices, matrix.indices + 1), matrix.indptr),
        #                   shape=(matrix.shape[0], matrix.shape[1] + 1))

    def appendCol(self, matrix: Sparse) -> Sparse:
        """Add a new column to right of the matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        
        :param sparse matrix: sparse-matrix
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        """
        return self.insertCol(matrix, matrix.shape[1])

    def deleteCol(self, matrix: Sparse, delete_col: int) -> Sparse:
        """Delete a column from a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        delete_col must be a valid column number for the matrix.

        :param sparse matrix: sparse-matrix
        :param int delete_col: column number
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'deleteCol: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(delete_col, int):
            raise TypeError('deleteCol: delete_col is not an int')
        if not (0 <= delete_col < matrix.shape[1]):
            raise ValueError(f'deleteCol: delete_col {delete_col} is out-of-bounds, must be [0, {matrix.shape[1] - 1}]')

        # get the indices and data arrays for the remaining elements
        indices = matrix.indices.copy()
        indptr = matrix.indptr.copy()
        data = matrix.data.copy()

        # modify the indices and data arrays to remove the deleted column
        for row in range(matrix.shape[0]):
            row_start = indptr[row]
            row_end = indptr[row + 1]
            if row_end > row_start:
                if (ind := next((col for col in range(row_start, row_end) if indices[col] == delete_col), -1)) != -1:
                    # delete row from the data and decrease indptrs
                    indices = np.delete(indices, ind, 0)
                    data = np.delete(data, ind, 0)
                    indptr[row + 1:] = indptr[row + 1:] - 1

        # move the larger columns to the left
        indices = np.where(indices < delete_col, indices, indices - 1)

        # create a new CSR matrix with the modified indices and data arrays
        return self._storageType((data, indices, indptr), shape=(matrix.shape[0], matrix.shape[1] - 1))

    def deleteColumns(self, matrix: Sparse, columns: list[int, ...] | tuple[int, ...]) -> Sparse:
        """Delete a column from a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        columns must be a valid list/tuple of column numbers for the matrix.

        :param sparse matrix: sparse-matrix
        :param list[int] columns: list/tuple of column numbers
        :return csr_matrix or csc_matrix: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'deleteCol: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(columns, (list, tuple)):
            raise TypeError('deleteColumns: columns is not a list/tuple of ints')
        if not all(0 <= col < matrix.shape[1] for col in columns):
            raise ValueError(
                    f'deleteColumns: columns {columns} contains out-of-bounds column, all must be [0, {matrix.shape[1] - 1}]')

        # get the indices and data arrays for the remaining elements
        indices = matrix.indices.copy()
        indptr = matrix.indptr.copy()
        data = matrix.data.copy()

        for delete_col in sorted(columns, reverse=True):
            # modify the indices and data arrays to remove the deleted column
            for row in range(matrix.shape[0]):
                row_start = indptr[row]
                row_end = indptr[row + 1]
                if row_end > row_start:
                    if (
                            ind := next((col for col in range(row_start, row_end) if indices[col] == delete_col),
                                        -1)) != -1:
                        # delete row from the data and decrease indptrs
                        indices = np.delete(indices, ind, 0)
                        data = np.delete(data, ind, 0)
                        indptr[row + 1:] = indptr[row + 1:] - 1

            # move the larger columns to the left
            indices = np.where(indices < delete_col, indices, indices - 1)

        # create a new CSR matrix with the modified indices and data arrays
        return self._storageType((data, indices, indptr),
                                 shape=(matrix.shape[0], matrix.shape[1] - len(columns)))

    def insertRow(self, matrix: Sparse, insert_row: int) -> Sparse:
        """Insert an empty row into a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        insert_row must be a valid row number for the matrix.

        :param sparse matrix: sparse-matrix
        :param int insert_row: row number
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'insertRow: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(insert_row, int):
            raise TypeError('insertRow: insert_row is not an int')
        if not (0 <= insert_row <= matrix.shape[0]):
            raise ValueError(f'insertRow: insert_row {insert_row} is out-of-bounds, must be [0, {matrix.shape[0]}]')

        return self._storageType(
                (matrix.data, matrix.indices, np.insert(matrix.indptr, insert_row, matrix.indptr[insert_row])),
                shape=(matrix.shape[0] + 1, matrix.shape[1]))

    def appendRow(self, matrix: Sparse) -> Sparse:
        """Add a new row to bottom of the matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.

        :param sparse matrix: sparse-matrix
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        """
        return self.insertRow(matrix, matrix.shape[0])

    def deleteRow(self, matrix: Sparse, delete_row: int) -> Sparse:
        """Delete a row from a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        delete_row must be a valid row number for the matrix.

        :param sparse matrix: sparse-matrix
        :param int delete_row: row number
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'deleteRow: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(delete_row, int):
            raise TypeError('deleteRow: delete_row is not an int')
        if not (0 <= delete_row < matrix.shape[0]):
            raise ValueError(f'deleteRow: delete_row {delete_row} is out-of-bounds, must be [0, {matrix.shape[0] - 1}]')

        indices = matrix.indices.copy()
        indptr = matrix.indptr.copy()
        data = matrix.data.copy()

        row_start = indptr[delete_row]
        row_end = indptr[delete_row + 1]
        indptr = np.delete(indptr, delete_row + 1, 0)

        if row_end != row_start:
            indptr[delete_row + 1:] = indptr[delete_row + 1:] - (row_end - row_start)

            indices = np.delete(indices, range(row_start, row_end), 0)
            data = np.delete(data, range(row_start, row_end), 0)

        # create a new CSR matrix with the modified indices and data arrays
        return self._storageType((data, indices, indptr), shape=(matrix.shape[0] - 1, matrix.shape[1]))

    def deleteRows(self, matrix: Sparse, rows: list[int, ...] | tuple[int, ...]) -> Sparse:
        """Delete a row from a scipy.sparse-matrix.

        matrix must be a scipy sparse-matrix of type csr_matrix or csc_matrix.
        rows must be a valid list/tuple of row numbers for the matrix.

        :param sparse matrix: sparse-matrix
        :param list[int] rows: list/tuple of row numbers
        :return: modified sparse-matrix
        :rtype: csr_matrix | csc_matrix
        :raise ValueError, TypeError: Incorrect input parameters
        """
        if not isinstance(matrix, TypeSparse):
            raise TypeError(f'deleteRow: matrix type is not in ({", ".join(tt.__name__ for tt in TypeSparse)})')
        if not isinstance(rows, (list, tuple)):
            raise TypeError('deleteRows: rows is not a list/tuple of ints')
        if not all(0 <= row < matrix.shape[0] for row in rows):
            raise ValueError(
                    f'deleteRows: rows {rows} contains out-of-bounds row, all must be [0, {matrix.shape[1] - 1}]')

        indices = matrix.indices.copy()
        indptr = matrix.indptr.copy()
        data = matrix.data.copy()

        for delete_row in sorted(rows, reverse=True):
            row_start = indptr[delete_row]
            row_end = indptr[delete_row + 1]
            indptr = np.delete(indptr, delete_row + 1, 0)

            if row_end != row_start:
                indptr[delete_row + 1:] = indptr[delete_row + 1:] - (row_end - row_start)

                indices = np.delete(indices, range(row_start, row_end), 0)
                data = np.delete(data, range(row_start, row_end), 0)

        # create a new CSR matrix with the modified indices and data arrays
        return self._storageType((data, indices, indptr),
                                 shape=(matrix.shape[0] - len(rows), matrix.shape[1]))

    @staticmethod
    def sparseInfo(matrix: Sparse) -> str:
        """Information for sparse-matrix.

        :return: information
        :rtype: str
        """
        nnz = matrix.getnnz()
        shp = matrix.shape
        # information can also be retrieved with repr(matrix)
        return f'{matrix.__class__.__name__}: ' \
               f'shape={shp}, ' \
               f'dtype={str(matrix.dtype)!r}, ' \
               f'format={str(matrix.format)!r}, ' \
               f'ndim={matrix.ndim}, ' \
               f'stored-elements={nnz}, ' \
               f'density={nnz / reduce(mul, shp):.2g}, ' \
               f'nbytes={matrix.data.nbytes + matrix.indptr.nbytes + matrix.indices.nbytes}'

    #=========================================================================================
    # Store/restore operations
    #=========================================================================================

    def _getValidIndexing(self, axis: str = None):
        """Return the list of indexed core-objects that are not deleted.

        :param int axis: axis number
        """
        if axis := self._axes.get(axis):
            pids = axis.get(_PIDS, [])
            pid2Obj = axis.get(_PID2OBJ, {})
            # goodPids = [pid for pid in pids if not pid2Obj[pid].isDeleted]
            # badInds = [ii for ii, pid in enumerate(pids) if pid2Obj[pid].isDeleted]
            goodPids = [pid for pid in pids if ((dPid := pid2Obj.get(pid)) and not dPid.isDeleted)]
            badInds = [ii for ii, pid in enumerate(pids) if ((dPid := pid2Obj.get(pid)) and dPid.isDeleted)]

            return goodPids, badInds

        return [], []

    def toJson(self) -> str:
        """Convert the cross-referencing to json for store/restore.

        :return: json string
        :rtype: str
        """
        if self._data is None:
            raise RuntimeError(f'{self.__class__.__name__}:toJson contains no data')

        rowPids, badRowInds = self._getValidIndexing(ROWDATA)
        columnPids, badColInds = self._getValidIndexing(COLUMNDATA)

        # remove the missing columns/rows and update the indexing if there are gaps
        newSparseMatrix = self._matrix.copy()

        newSparseMatrix = self.deleteColumns(newSparseMatrix, badColInds)
        newSparseMatrix = self.deleteRows(newSparseMatrix, badRowInds)
        newSparseMatrix.eliminate_zeros()

        dd = {INDICES        : newSparseMatrix.indices.tolist(),
              INDPTR         : newSparseMatrix.indptr.tolist(),
              DATA           : newSparseMatrix.data.tolist(),
              SHAPE          : newSparseMatrix.shape,
              DTYPE          : str(newSparseMatrix.dtype),
              DFORMAT        : str(newSparseMatrix.format),
              ROWPIDS        : rowPids,
              COLUMNPIDS     : columnPids,
              ROWCLASSNAME   : self._axes[ROWDATA][_KLASSNAME],
              COLUMNCLASSNAME: self._axes[COLUMNDATA][_KLASSNAME],
              }
        return json.dumps(dd)

    @staticmethod
    def fromJson(jsonData: str) -> dict:
        """Recover from json.

        :param str jsonData: json string
        :return: parameters dictionary
        :rtype: dict
        """
        return json.loads(jsonData)

    def _restoreObject(self, project: Project, *args):
        """Restore the core objects from the indexing.

        :param Project project: current project
        """
        ddRow, ddCol = self._axes[ROWDATA], self._axes[COLUMNDATA]
        if self._buildFromProject:

            self._newAxis(project, ROWDATA)
            self._newAxis(project, COLUMNDATA)

            # create blank matrix
            self._matrix = self._storageType((len(ddRow[_PIDS]), len(ddCol[_PIDS])), dtype=self._dtype)

        else:
            self._verifyAxis(project, ROWDATA)
            self._verifyAxis(project, COLUMNDATA)

            # create matrix from existing data
            self._matrix = self._storageType((self._data, self._indices, self._indptr), shape=self._shape,
                                             dtype=self._dtype)

            # check that dimensions are okay, clean-up
            if (len(ddRow[_PIDS]) != self._matrix.shape[0] or
                    len(ddCol[_PIDS]) != self._matrix.shape[1]):
                # there was an error saving, try and recover or reset
                # NOTE:ED - potentially dangerous, links could disappear, but better than crashing
                self._matrix = self._storageType((len(ddRow[_PIDS]), len(ddCol[_PIDS])), dtype=self._dtype)
                getLogger().warning(f'There was an issue recovering cross-references {self.__class__.__name__}')

    def _updateClass(self, axis: int, coreObject: V3Core,
                     oldPid: str = None, action: str = _CREATE, func: callable = None):
        """Update the state for a row core-object.

        :param int axis: axis number
        :param V3Core coreObject: core-object sourcing notifier
        :param str oldPid: old pid if renaming
        :param str action: notifier action-type
        :param callable func: func to call to update matrix, either row or column operation
        """
        dd = self._axes[axis]
        if coreObject.className != dd[_KLASSNAME]:
            return

        if action == _CREATE:
            # need to differentiate between 'create' and 'undo-create'
            # the first of which should create a clean cross-reference
            pid = coreObject.pid
            if coreObject in dd[_OBJ2PID]:
                # undo has created the object
                newPid = coreObject.pid
                delPid = f'{newPid}{_DELETEPOSTFIX}'

                del dd[_PID2OBJ][delPid]  # 'deleted' pid
                dd[_PID2OBJ][pid] = coreObject
                dd[_OBJ2PID][coreObject] = pid

                # replace in the pid list
                ind = dd[_PIDS].index(delPid)
                dd[_PIDS][ind] = pid

            else:
                # new object
                pid = coreObject.pid
                dd[_PIDS].append(pid)
                dd[_PID2OBJ][pid] = coreObject
                dd[_OBJ2PID][coreObject] = pid
                self._matrix = func(self._matrix)

        elif action == _DELETE:
            if coreObject in dd[_OBJ2PID]:
                # undo has created the object
                del dd[_PID2OBJ][coreObject.pid]  # 'live' pid

                # make new deleted-pid, not really a good place :|
                pid = f'{coreObject.pid}{_DELETEPOSTFIX}'
                dd[_OBJ2PID][coreObject] = pid
                dd[_PID2OBJ][pid] = coreObject

                # replace in the pid list
                ind = dd[_PIDS].index(coreObject.pid)
                dd[_PIDS][ind] = pid

        elif action == _RENAME:
            # NOTE:ED - not tested yet - need a valid cross-reference for this
            if coreObject in dd[_OBJ2PID]:
                # undo has created the object
                del dd[_PID2OBJ][oldPid]  # pid before rename

                # make new deleted-pid, not really a good place :|
                pid = coreObject.pid
                dd[_OBJ2PID][coreObject] = pid
                dd[_PID2OBJ][pid] = coreObject

                # replace in the pid list
                ind = dd[_PIDS].index(oldPid)
                dd[_PIDS][ind] = pid

    def _resetItemPids(self, coreObject: V3Core, oldPid: str = None, action: str = _CREATE):
        """Update the pids from the creation/deletion of the pid.

        :param V3Core coreObject: core-object sourcing notifier
        :param str oldPid: old pid if renaming
        :param str action: notifier action-type
        """
        # pid is contained in one of the lists
        self._updateClass(ROWDATA, coreObject, oldPid, action, func=self.appendRow)
        self._updateClass(COLUMNDATA, coreObject, oldPid, action, func=self.appendCol)

    #=========================================================================================
    # Get/set values in cross-reference
    #=========================================================================================

    def getValues(self, coreObject: V3Core, axis: int) -> tuple[V3Core, ...]:
        """Get the cross-reference objects from the class.

        :param V3Core coreObject: core-object
        :param int axis: axis number
        :return: tuple of core-objects
        :rtype: tuple[V3Core, ...]
        """
        # apply caching?
        pid = coreObject.pid

        if axis == 0:
            # primary object is in row-pids, get information from the columnAxis
            ddRow = self._axes[ROWDATA]

            if pid not in ddRow[_PIDS]:
                getLogger().debug(f'not found {coreObject}')
                return ()

            ddCol = self._axes[COLUMNDATA]
            # get the single row matrix and extract indices which reference pids from other axis
            rr = self._matrix.getrow(ddRow[_PIDS].index(pid))

            outPids = [ddCol[_PIDS][ind] for ind in rr.indices]
            return tuple(filter(lambda obj: not obj.isDeleted, (ddCol[_PID2OBJ][pid] for pid in outPids)))

        else:
            # primary object is in column-pids
            ddCol = self._axes[COLUMNDATA]

            if pid not in ddCol[_PIDS]:
                getLogger().debug(f'not found {coreObject}')
                return ()

            ddRow = self._axes[ROWDATA]
            # get the single row matrix and extract indices which reference pids from other axis
            cc = self._matrix.getcol(ddCol[_PIDS].index(pid)).tocsc()

            outPids = [ddRow[_PIDS][ind] for ind in cc.indices]
            return tuple(filter(lambda obj: not obj.isDeleted, (ddRow[_PID2OBJ][pid] for pid in outPids)))

    def setValues(self, coreObject: V3Core, axis: int, values: list[V3Core, ...] | tuple[V3Core, ...]):
        """Set the cross-reference objects to the class.

        :param V3Core coreObject: core-object
        :param int axis: axis number
        :param list[V3Core, ...] | tuple[V3Core, ...] values: core-objects
        """
        pid = coreObject.pid
        values = values or []

        if axis == 0:
            # primary object is in row-pids, get information from the columnAxis
            ddRow = self._axes[ROWDATA]

            if pid not in ddRow[_PIDS]:
                getLogger().debug(f'not found {coreObject}')
                return ()

            ddCol = self._axes[COLUMNDATA]
            ind = ddRow[_PIDS].index(pid)
            # clear everything in the row
            self._matrix[ind, :] = 0  # quicker way of doing this?

            objs = coreObject.project.getByPids(values)
            for obj in objs:
                self._matrix[ind, ddCol[_PIDS].index(ddCol[_OBJ2PID][obj])] = 1

        else:
            # primary object is in column-pids
            ddCol = self._axes[COLUMNDATA]

            if pid not in ddCol[_PIDS]:
                getLogger().debug(f'not found {coreObject}')
                return ()

            ddRow = self._axes[ROWDATA]
            ind = ddCol[_PIDS].index(pid)
            # clear everything in the column
            self._matrix[:, ind] = 0  # quicker way of doing this?

            objs = coreObject.project.getByPids(values)
            for obj in objs:
                self._matrix[ddRow[_PIDS].index(ddRow[_OBJ2PID][obj]), ind] = 1

        # quickly clean-up
        self._matrix.eliminate_zeros()


#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui._implementation.Mark import Mark
from ccpn.ui._implementation.Strip import Strip
from ccpn.ui._implementation.SpectrumDisplay import SpectrumDisplay
from ccpn.ui._implementation.Window import Window


class MarkStrip(_CrossReferenceABC):
    """Class to handle special case of mark<->strip cross-reference.
    Marks can also belong to a spectrumDisplay or mainWindow (everywhere).

    Marks in a spectrumDisplay will also appear in new strips within the display.
    Similarly, marks belonging to mainWindow will appear in all new strips.

    See below for spectrumDisplay-mainWindow classes.

    This is included to recover marks from pre-3.2 projects.
    Loading a 3.2 project into previous un-updated versions will remove all marks.
    """
    #=========================================================================================
    # Get/set values in cross-reference
    #=========================================================================================

    ...


# register the class with _CrossReferenceABC for json loading/saving
MarkStrip.register()


class _MarkStrip(_CrossReferenceABC):
    """Class to handle special case of mark<->strip cross-reference.
    Marks can also belong to a spectrumDisplay or mainWindow (everywhere).

    Marks in a spectrumDisplay will also appear in new strips within the display.
    Similarly, marks belonging to mainWindow will appear in all new strips.

    See below for spectrumDisplay-mainWindow classes.
    """
    rowKlass = Mark
    columnKlass = Strip

    #=========================================================================================
    # Get/set values in cross-reference
    #=========================================================================================

    ...


# register the class with _CrossReferenceABC for json loading/saving
_MarkStrip.register(setDefault=True)


class _MarkSpectrumDisplay(_CrossReferenceABC):
    """Class to handle special case of mark<->spectrumDisplay cross-reference.
    """
    rowKlass = Mark
    columnKlass = SpectrumDisplay

    #=========================================================================================
    # Get/set values in cross-reference
    #=========================================================================================

    ...


# register the class with _CrossReferenceABC for json loading/saving
_MarkSpectrumDisplay.register()


class _MarkWindow(_CrossReferenceABC):
    """Class to handle special case of mark<->mainWindow cross-reference.
    """
    rowKlass = Mark
    columnKlass = Window

    #=========================================================================================
    # Get/set values in cross-reference
    #=========================================================================================

    ...


# register the class with _CrossReferenceABC for json loading/saving
_MarkWindow.register()
