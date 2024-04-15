"""
This module defines the data loading mechanism.

Loader instances have all the information regarding a particular data type
(e.g. a ccpn project, a NEF file, a PDB file, etc. and include a load() function to to the actual
work of loading the data into the project.
"""

#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Geerten Vuister $"
__dateModified__ = "$dateModified: 2024-07-25 10:11:17 +0100 (Thu, July 25, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2021-06-30 10:28:41 +0000 (Fri, June 30, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import OrderedDict, defaultdict
from typing import Tuple

from ccpn.util.Path import Path, aPath
from ccpn.util.traits.TraitBase import TraitBase
from ccpn.util.traits.CcpNmrTraits import Unicode, Any, List, Bool, CPath, Odict, CString, Int
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import singleton


#--------------------------------------------------------------------------------------------
#ToDo Need to review former lib/io/Formats.py and ioFormats.analyseUrl(path)
#--------------------------------------------------------------------------------------------

CCPNMRTGZCOMPRESSED = 'ccpNmrTgzCompressed'
CCPNMRZIPCOMPRESSED = 'ccpNmrZipCompressed'

SPARKYFILE = 'sparkyFile'

# NO_SUFFIX = 'No-suffix'
# ANY_SUFFIX = 'Any-suffix'
from ccpn.framework.constants import NO_SUFFIX, ANY_SUFFIX


def getDataLoaders() -> OrderedDict:
    """Get data loader classes
    :return: a dictionary of (format-identifier-strings, DataLoader classes) as (key, value) pairs
    """
    #--------------------------------------------------------------------------------------------
    # The following imports are just to assure that all the classes have been imported
    # hierarchy matters! but, a priority can be specified to help ordering
    # It is local to prevent circular imports
    #--------------------------------------------------------------------------------------------
    from ccpn.framework.lib.DataLoaders.CcpNmrV3ProjectDataLoader import CcpNmrV3ProjectDataLoader
    from ccpn.framework.lib.DataLoaders.CcpNmrV2ProjectDataLoader import CcpNmrV2ProjectDataLoader
    from ccpn.framework.lib.DataLoaders.SpectrumDataLoader import SpectrumDataLoaderABC
    from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader
    from ccpn.framework.lib.DataLoaders.StarDataLoader import StarDataLoader
    from ccpn.framework.lib.DataLoaders.FastaDataLoader import FastaDataLoader
    from ccpn.framework.lib.DataLoaders.ChemCompDataLoader import ChemCompDataLoader
    from ccpn.framework.lib.DataLoaders.ExcelDataLoader import ExcelDataLoader
    from ccpn.framework.lib.DataLoaders.PdbDataLoader import PdbDataLoader
    from ccpn.framework.lib.DataLoaders.TextDataLoader import TextDataLoader
    from ccpn.framework.lib.DataLoaders.PythonDataLoader import PythonDataLoader
    from ccpn.framework.lib.DataLoaders.HtmlDataLoader import HtmlDataLoader
    from ccpn.framework.lib.DataLoaders.SparkyDataLoader import SparkyDataLoader
    from ccpn.framework.lib.DataLoaders.MmcifDataLoader import MmcifDataLoader
    from ccpn.framework.lib.DataLoaders.DirectoryDataLoader import DirectoryDataLoader

    return DataLoaderABC._dataLoaders


def getSpectrumLoaders() -> dict:
    """Get data spectrum-specific loader classes
    :return: a dictionary of (format-identifier-strings, DataLoader classes) as (key, value) pairs
    """
    _loaders = getDataLoaders()
    return dict([(df, dl) for df, dl in _loaders.items() if dl.isSpectrumLoader])


@singleton
class DataLoaderSuffixDict(OrderedDict):
    """A class to contain a dict of (suffix, [DataLoader class]-list)
    (key, value) pairs;

    The get(suffix) returns a list of klasses for suffix; its maps None or zero-length to NO_SUFFIX
    and any non-existing suffix in the dict to ANY_SUFFIX

    NB: Only to be used internally
    """

    def __init__(self):
        # local import to avoid cycles

        super().__init__(self)

        # Fill the dict
        for dataFormat, klass in getDataLoaders().items():
            suffixes = [NO_SUFFIX, ANY_SUFFIX] if len(klass.suffixes) == 0 else klass.suffixes
            for suffix in suffixes:
                suffix = NO_SUFFIX if suffix is None else suffix
                self[suffix].append(klass)

    def __getitem__(self, item):
        """Can't get subclassed defaultdict to work
        Always assure a list for item
        """
        if not item in self:
            super().__setitem__(item, [])
        return super().__getitem__(item)

    def get(self, suffix) -> list:
        """get a list of klasses for suffix;
        map None or zero-length to NO_SUFFIX and
        map non existing suffix to ANY_SUFFIX
        """
        if suffix is None or len(suffix) == 0:
            return self[NO_SUFFIX]
        elif suffix not in self:
            return self[ANY_SUFFIX]
        else:
            return self[suffix]


def _getPotentialDataLoaders(path) -> list:
    """
    :param path: path to evaluate
    :return list of possible dataLoader classes based on suffix and path type (directory, file)

    NB: Only to be used internally
    CCPNINTERNAL: used in  CcpnNefIo
    """

    if path is None:
        raise ValueError('Undefined path')
    _path = aPath(path)

    _suffixDict = DataLoaderSuffixDict()
    loaders = _suffixDict.get(_path.suffix)

    # if it is a file: exclude loaders that require a directory
    if _path.is_file():  # also False if _path does not exist
        loaders = [ld for ld in loaders if not ld.requireDirectory]

    # if it is a directory: include loaders that do allow a directory
    if _path.is_dir():  # also False if _path does not exist
        loaders = [ld for ld in loaders if ld.allowDirectory]

    return loaders


def _checkPathForDataLoader(path, formatFilter=None) -> list:
    """Check path if it corresponds to any defined data format.
    Optionally only include dataLoader with dataFormat in filter (default: all dataFormats; i.e.
    no filtering).

    :param formatFilter: a tuple/list of dataFormat strings of formats to select for
    :return a list of DataLoader instance(s) (either valid or invalid); last one is potential valid one

    CCPNINTERNAL: used in Gui._getDataLoader
    """
    if not isinstance(path, (str, Path)):
        raise ValueError('checkPathForDataLoader: invalid path %r' % path)

    if formatFilter is None or len(formatFilter) == 0:
        # no filter, allow all by expanding
        formatFilter = list(getDataLoaders().keys())

    _loaders = _getPotentialDataLoaders(path)

    result = []
    for cls in _loaders:
        instance = cls.newFromPath(path)
        if len(_loaders) == 1:
            # There is only one potential loader; it should be valid
            instance.shouldBeValid = True
        result.append(instance)
        # Check if we are done
        if instance.isValid or instance.shouldBeValid:
            if instance.dataFormat in formatFilter:
                return result
            else:
                instance.isValid = False
                instance.shouldBeValid = False
                instance.errorString = f'Valid path "{instance.path}": dataFormat "{instance.dataFormat}" not in formatFilter'

    # we are only here if we haven't found any valid data loader
    result.append(NotFoundDataLoader(path=path))
    return result


def checkPathForDataLoader(path, formatFilter=None):
    """Check path if it corresponds to any defined data format.
    Optionally only include only dataLoader with dataFormat in filter (default: all dataFormats)

    :param formatFilter: a tuple/list of dataFormat strings
    :return a DataLoader instance or None if there was no match
    """
    _loaders = _checkPathForDataLoader(path=path, formatFilter=formatFilter)
    if len(_loaders) > 0 and _loaders[-1].isValid:
        # found a valid one; return that
        return _loaders[-1]

    return None


#--------------------------------------------------------------------------------------------
# DataLoader class
#--------------------------------------------------------------------------------------------

class DataLoaderABC(TraitBase):
    """A DataLoaderABC: has definition for patterns

    Maintains a load() method to call the actual loading function (presumably from self.application
    or self.project
    """

    #=========================================================================================
    # to be subclassed
    #=========================================================================================
    dataFormat = None
    suffixes = []  # a list of suffixes that gets matched to path
    alwaysCreateNewProject = False
    canCreateNewProject = False
    allowDirectory = False  # Can/Can't open a directory
    requireDirectory = False  # explicitly require a directory
    isSpectrumLoader = False  # Subclassed for SpectrumLoaders
    loadFunction = (None, None)  # A (function, attributeName) tuple;
    # :param attributeName:=('project','application') to get obj
    #                       as either self.project or self.application
    # :param function(obj:(Application,Project), path:Path) -> List[newObj1, ...]

    #=========================================================================================
    # end to be subclassed
    #=========================================================================================

    # traits
    path = CPath().tag(info='a path to a file to be loaded')
    application = Any(default_value=None, allow_none=True)
    # NB: project derived via a property from application

    # project related
    createNewProject = Bool(default_value=False).tag(info='flag to indicate if a new project will be created')
    newProjectName = CString(default_value='newProject').tag(info='Name for a new project')
    makeArchive = Bool(default_value=False).tag(
        info='flag to indicate if a project needs to be archived before loading')

    # new implementation, using newFromPath method and validity testing later on
    isValid = Bool(default_value=False).tag(info='flag to indicate if path denotes a valid dataType')
    shouldBeValid = Bool(default_value=False).tag(
        info='flag to indicate that path should denotes a valid dataType, but some elements are missing')
    errorString = CString(default_value='').tag(info='error description for validity testing')
    ignore = Bool(default_value=False).tag(info='flag to indicate if loader needs ignoring')

    # A dict of registered DataLoaders: filled by _registerFormat classmethod, called
    # once after each definition of a new derived class (e.g. PdbDataLoader)
    _dataLoaders = OrderedDict()
    priority = 0  # priority to order the loaders as there are registered, 0 is lowest and processed last

    @classmethod
    def _registerFormat(cls):
        """register cls.dataFormat
        """
        if cls.dataFormat in DataLoaderABC._dataLoaders:
            raise RuntimeError('dataLoader "%s" was already registered' % cls.dataFormat)
        # get the OrderedDict of higher priority dataLoaders
        higher = OrderedDict((k, v) for k, v in DataLoaderABC._dataLoaders.items() if v.priority >= cls.priority)
        # get the OrderedDict of lower priority dataLoaders
        lower = OrderedDict((k, v) for k, v in DataLoaderABC._dataLoaders.items() if v.priority < cls.priority)
        DataLoaderABC._dataLoaders.clear()
        # insert the new cls in the middle
        DataLoaderABC._dataLoaders |= (higher | OrderedDict([(cls.dataFormat, cls)]) | lower)

    #=========================================================================================
    # start of methods
    #=========================================================================================
    def __init__(self, path):
        super().__init__()
        self.path = aPath(path)

        # get default setting for project creation
        self.createNewProject = self.alwaysCreateNewProject or self.canCreateNewProject
        self.makeArchive = False

        # local import to avoid cycles
        from ccpn.framework.Application import getApplication

        self.application = getApplication()
        # NB: self.project derived via a property from application

        self.checkValid()

    @property
    def project(self):
        """Current project instance
        """
        return self.application.project

    @classmethod
    def newFromPath(cls, path):
        """New instance with path
        :return: instance of the class
        """
        instance = cls(path=path)
        return instance

    @classmethod
    def checkForValidFormat(cls, path):
        """check if valid format corresponding to dataFormat
        :return: None or instance of the class

        Can be subclassed;
        GWV 20/09/2022: deprecated; maintained for code backward compatibility; still used in some instances
        """
        instance = cls(path=path)
        if not instance.isValid:
            return None

        return instance

    def checkValid(self) -> bool:
        """Check if self.path is valid.
        Calls _checkPath and _checkSuffix
        sets self.isValid and self.errorString
        :returns True if ok or False otherwise

        Can be subclassed
        """
        self.isValid = False
        self.errorString = f'Validity of {self.path} has not been checked'

        if not self._checkSuffix():
            return False

        if not self._checkPath():
            return False

        self.isValid = True
        self.errorString = ''
        return True

    def load(self):
        """The actual file loading method;
        raises RunTimeError on error
        :return: a list of [objects]

        Can be subclassed
        """
        if not self.isValid:
            raise RuntimeError(f'Error loading "{self.path}"; invalid loader')

        try:
            # get the object (either a project or application), to pass on
            # to the loaderFunc
            loaderFunc, attributeName = self.loadFunction
            obj = getattr(self, attributeName)
            result = loaderFunc(obj, self.path)

        except (ValueError, RuntimeError, RuntimeWarning) as es:
            raise RuntimeError(f'Error loading "{self.path}": {es}') from es

        return result

    def getAllFilePaths(self) -> list:
        """
        Get all the files handles by this loader. Generally, this will be the path that
        the loader represented, but sometimes there might be more; i.e. for certain spectrum
        loaders that handle more files; like a binary and a parameter file.
        To be subclassed for those instances

        :return: list of Path instances
        """
        return [self.path]

    def _checkSuffix(self) -> bool:
        """Check if suffix of self.path confirms to settings of class attribute suffixes.
        sets self.isValid and self.errorString
        :returns True if ok or False otherwise
        """
        _path = self.path
        if len(_path.suffixes) == 0 and NO_SUFFIX in self.suffixes:
            self.isValid = True
            self.errorString = ''
            return True
        if len(_path.suffixes) > 0 and ANY_SUFFIX in self.suffixes:
            self.isValid = True
            self.errorString = ''
            return True
        if len(_path.suffixes) > 0 and _path.suffix in self.suffixes:
            self.isValid = True
            self.errorString = ''
            return True

        self.isValid = False
        self.errorString = f'Invalid path suffix; should be one of {self.suffixes}'
        return False

    def _checkPath(self):
        """Check if self.path exists and confirms to settings of class attributes suffixes and allowDirectory
        do not allow dot-file (e.g. .cshrc)
        :returns True if ok or False otherwise
        """
        _path = self.path
        if not _path.exists():
            self.isValid = False
            self.errorString = f'Path "{_path}" does not exists'
            return False

        if _path.basename == '':
            self.errorString = f'Invalid path "{_path}"'
            self.isValid = False
            return False

        if _path.is_dir() and not self.allowDirectory:
            # path is a directory: cls does not allow
            self.errorString = f'Invalid path "{_path}"; directory not allowed'
            self.isValid = False
            return False

        if not _path.is_dir() and self.requireDirectory:
            # path is a file, but cls requires a directory
            self.errorString = f'Invalid path "{_path}"; directory required'
            self.isValid = False
            return False

        self.errorString = ''
        self.isValid = True
        return True

    @classmethod
    def _documentClass(cls) -> str:
        """:return a documentation string comprised of __doc__ and some class attributes
        """
        if cls.requireDirectory:
            _directory = 'Required'
        elif cls.allowDirectory:
            _directory = 'Allowed'
        else:
            _directory = 'Not allowed'

        if cls.canCreateNewProject:
            _newProject = 'Potentially'
        elif cls.alwaysCreateNewProject:
            _newProject = 'Always'
        else:
            _newProject = 'Never'

        result = cls.__doc__ + \
                 f'\n' + \
                 f'    Valid suffixes:      {cls.suffixes}\n' + \
                 f'    Directory:           {_directory}\n' + \
                 f'    Creates new project: {_newProject}'

        return result

    def __str__(self):
        if self.isValid:
            _valid = 'valid'
        elif self.shouldBeValid:
            _valid = 'shouldBeValid'
        else:
            _valid = 'invalid'
        return f'<{self.__class__.__name__}: {self.path}, {_valid}>'

    __repr__ = __str__


class NotFoundDataLoader(DataLoaderABC):
    """A class denoting the absence of any valid dataLoader
    """
    dataFormat = 'NotFound'
    suffixes = [ANY_SUFFIX, NO_SUFFIX]
    allowDirectory = True

    def checkValid(self) -> bool:
        if not super().checkValid():
            return False
        # Path was valid; set general other error message
        self.shouldBeValid = False
        self.isValid = False
        self.errorString = f'{self.path}: unable to identify a valid dataLoader'
