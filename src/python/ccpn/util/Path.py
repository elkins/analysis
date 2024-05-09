"""Utilities for path handling

Includes extensions of sys.path functions and CCPN-specific functionality

"""
from __future__ import annotations


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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-05-09 15:51:21 +0100 (Thu, May 09, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================
#
# Convenient I/O functions
#

import importlib
import os
import shutil
import glob
import datetime
import re
from functools import reduce
from operator import add


dirsep = '/'
# note, cannot just use os.sep below because can have window file names cropping up on unix machines
winsep = '\\'

# This does not belong here and should go to PathsAndUrls;
# However, the 'Api.py' and Implementation relies on this, so it should stay
# DO NOT USE!
CCPN_API_DIRECTORY = 'ccpnv3'
CCPN_DIRECTORY_SUFFIX = '.ccpn'
CCPN_BACKUP_SUFFIX = '_backup'
CCPN_ARCHIVES_DIRECTORY = 'archives'
CCPN_SUMMARIES_DIRECTORY = 'summaries'
CCPN_LOGS_DIRECTORY = 'logs'
CCPN_PYTHON = 'miniconda/bin/python'

# Can't do because of circular imports:
# from ccpn.framework.PathsAndUrls import CCPN_API_DIRECTORY, CCPN_DIRECTORY_SUFFIX, \
#       CCPN_BACKUP_SUFFIX, CCPN_ARCHIVES_DIRECTORY, CCPN_LOGS_DIRECTORY,  CCPN_SUMMARIES_DIRECTORY

from pathlib import Path as _Path_
from pathlib import _windows_flavour, _posix_flavour


#=========================================================================================
# Path
#=========================================================================================

class Path(_Path_):
    """Subclassed for compatibility, convenience and enhancements
    """

    # sub classing is broken
    # From: https://codereview.stackexchange.com/questions/162426/subclassing-pathlib-path
    _flavour = _windows_flavour if os.name == 'nt' else _posix_flavour

    @property
    def basename(self):
        """the name of self without any suffixes
        """
        return self.name.split('.')[0]

    @property
    def filepath(self) -> Path:
        """The folder without the filename"""
        return self if self.is_dir() else self.parent

    @property
    def version(self) -> int:
        """Parse self to yield a version integer, presumably generated with the incrementVersion method
        versions are encoded as "(version)" string at the end of basename; e.g. xyz/basename(10).fid
        :return version number or 0 if not found
        """
        basename = self.basename
        _m = re.search('\([0-9]+\)', basename)
        if _m is None:
            return 0

        start, stop = _m.span()
        if stop != len(basename):
            return 0

        try:
            value = int(basename[start + 1:stop - 1])
        except ValueError:
            return 0

        if value < 1:
            return 0

        return value

    @staticmethod
    def _isValid(value, allowLowerAlpha=True, allowUpperAlpha=True, allowNumeric=True,
                 allowUnderscore=True, allowSpace=True, allowDash=True, allowFullstop=True,
                 allowBrackets=True, allowEmpty=False, allowOther: str | None = None):
        """Check the parts of a filename.
        other must be an inclusion test, i.e., other characters that are allowed in value.

            e.g.

            fp = Path('/filepath/fol$d%er/filename.ccpn')
            print(fp.isValidFilePath())                     # --> False
            print(fp.isValidFilePath(allowOther=r'%'))      # --> False
            print(fp.isValidFilePath(allowOther=r'%$'))     # --> True

        Brackets are included to allow possible numbering of folders/filenames.

        :param str value: part of filename to check.
        :param bool allowLowerAlpha: allow lower-case.
        :param bool allowUpperAlpha: allow upper-case.
        :param bool allowNumeric: allow numeric.
        :param bool allowUnderscore: allow underscores.
        :param bool allowSpace: allow spaces.
        :param bool allowDash: allow dash-characters.
        :param bool allowFullstop: allow full-stop.
        :param bool allowBrackets: allow square/round brackets.
        :param bool allowEmpty: allow empty string.
        :param optional(str) allowOther: list of other characters that are allowed, or None.
        :return: True is value is valid.
        """
        # extra characters are inserted into 'bad' discard string as escape characters - saves passing them in like that
        codes = reduce(add, (rf'\{ch}' for ch in allowOther)) if allowOther else ""
        sequences = {'lowerAlpha': (allowLowerAlpha, '[a-z]+'),
                     'upperAlpha': (allowUpperAlpha, '[A-Z]+'),
                     'numeric'   : (allowNumeric, '[0-9]+'),
                     'underscore': (allowUnderscore, '[_]+'),
                     'space'     : (allowSpace, '[ ]+'),
                     'dash'      : (allowDash, '[-]+'),
                     'fullstop'  : (allowFullstop, '[\.]+'),
                     'brackets'  : (allowBrackets, r'[\(\)\[\]]+'),
                     'bad'       : (False, rf'[^a-zA-z0-9\_\ \-\.\(\)\[\]\~{codes is not None and codes or ""}]+'),
                     }

        if not value and not allowEmpty:
            return False

        valids = [True] + [False
                           for vc, (allow, seq) in sequences.items()
                           if not allow and re.findall(seq, value)]

        return all(valids)

    def isValidFilePath(self, allowLowerAlpha: bool = True, allowUpperAlpha: bool = True, allowNumeric: bool = True,
                        allowUnderscore: bool = True, allowSpace: bool = True, allowDash: bool = True, allowFullstop: bool = True,
                        allowBrackets: bool = True, allowEmpty: bool = False,
                        allowOther: str | None = None) -> bool:
        """Return True if the filepath conforms to required parameters.
        allowOther must be an inclusion test, i.e., other characters that are allowed in value.

            e.g.

            fp = Path('/filepath/fol$d%er/filename.ccpn')
            print(fp.isValidFilePath())                     # --> False
            print(fp.isValidFilePath(allowOther=r'%'))      # --> False
            print(fp.isValidFilePath(allowOther=r'%$'))     # --> True

        Brackets are included to allow possible numbering of folders/filenames.

        :param bool allowLowerAlpha: allow lower-case.
        :param bool allowUpperAlpha: allow upper-case.
        :param bool allowNumeric: allow numeric.
        :param bool allowUnderscore: allow underscores.
        :param bool allowSpace: allow spaces.
        :param bool allowDash: allow dash-characters.
        :param bool allowFullstop: allow full-stop.
        :param bool allowBrackets: allow square/round brackets.
        :param bool allowEmpty: allow empty string.
        :param optional(str) allowOther: optional list of other characters that are allowed.
        :return: True if valid.
        """
        if not all(isinstance(val, bool) for val in (allowLowerAlpha, allowUpperAlpha, allowNumeric, allowUnderscore,
                                                     allowSpace, allowDash, allowFullstop, allowBrackets, allowEmpty)):
            raise TypeError(f'{self.__class__.__name__}.isValidFilePath: parameters must be of type bool.')
        if not isinstance(allowOther, str | None):
            raise TypeError(f'{self.__class__.__name__}.isValidFilePath: allowOther must be str or None.')

        fp = all(self._isValid(val, allowLowerAlpha=allowLowerAlpha, allowUpperAlpha=allowUpperAlpha, allowNumeric=allowNumeric,
                               allowUnderscore=allowUnderscore, allowSpace=allowSpace, allowDash=allowDash, allowFullstop=allowFullstop,
                               allowBrackets=allowBrackets, allowEmpty=allowEmpty, allowOther=allowOther)
                 for val in self.parts[1 if self.anchor else 0:-1])

        return fp

    def isValidBasename(self, allowLowerAlpha: bool = True, allowUpperAlpha: bool = True, allowNumeric: bool = True,
                        allowUnderscore: bool = True, allowSpace: bool = True, allowDash: bool = True, allowFullstop: bool = True,
                        allowBrackets: bool = True, allowEmpty: bool = False,
                        allowOther: str | None = None,
                        suffixes: list[str, ...] | None = None) -> bool:
        """Return True if the basename and extension conform to required parameters.
        allowOther must be an inclusion test, i.e., other characters that are allowed in value.

            e.g.

            fp = Path('/filepath/folder/filename$%.ccpn')
            print(fp.isValidBasename())                     # --> False
            print(fp.isValidBasename(allowOther=r'%'))      # --> False
            print(fp.isValidBasename(allowOther=r'%$'))     # --> True

        Brackets are included to allow possible numbering of folders/filenames.
        If suffixes is None, the suffix is not checked.

        :param bool allowLowerAlpha: allow lower-case.
        :param bool allowUpperAlpha: allow upper-case.
        :param bool allowNumeric: allow numeric.
        :param bool allowUnderscore: allow underscores.
        :param bool allowSpace: allow spaces.
        :param bool allowDash: allow dash-characters.
        :param bool allowFullstop: allow full-stop.
        :param bool allowBrackets: allow square/round brackets.
        :param bool allowEmpty: allow empty string.
        :param optional(str) allowOther: optional list of other characters that are allowed.
        :param optional(list(str)) suffixes: optional list of strings of the form '.<suffix>'
        :return: True if valid.
        """
        if not all(isinstance(val, bool) for val in (allowLowerAlpha, allowUpperAlpha, allowNumeric, allowUnderscore,
                                                     allowSpace, allowDash, allowFullstop, allowBrackets, allowEmpty)):
            raise TypeError(f'{self.__class__.__name__}.isValidFilePath: parameters must be of type bool.')
        if not isinstance(allowOther, str | None):
            raise TypeError(f'{self.__class__.__name__}.isValidFilePath: allowOther must be str or None.')
        if not isinstance(suffixes, list | None) or (suffixes and not all(isinstance(val, str) for val in suffixes)):
            raise TypeError(f'{self.__class__.__name__}.isValidFilePath: suffixes must be list of str, or None.')

        bn = self._isValid(self.basename, allowLowerAlpha=allowLowerAlpha, allowUpperAlpha=allowUpperAlpha, allowNumeric=allowNumeric,
                           allowUnderscore=allowUnderscore, allowSpace=allowSpace, allowDash=allowDash, allowFullstop=allowFullstop,
                           allowBrackets=allowBrackets, allowEmpty=allowEmpty, allowOther=allowOther)

        ext = True if suffixes is None else self.suffix in suffixes

        return bn and ext

    @staticmethod
    def _validCharactersMessage() -> str:
        """Return a quick message informing valid characters based on isValidCcpn.
        """
        return '\nPlease only use alphanumeric characters (no accents or other diacritics), ' \
               'underscores (_), dashes (-), and square/round brackets ()[] in your ' \
               'file path and project name.' \
               '\nSpaces are allowed in the file path but not in the project name.' \
               '\n' \
               '\nNOTE: dashes (-), square/round brackets ()[], and other non-alphanumeric characters in your project ' \
               'name may automatically be changed to underscores (_) when loading/saving.'

    def isValidCcpn(self, suffixes: list[str, ...] | None = None) -> bool:
        """Return True if the filename conforms to valid CCPN guidelines:

        Convenience method to quickly check filenames.

        filepath is alphanumeric; it may also contain spaces, underscores, dashes, and square/round brackets.
        basename is alphanumeric; it may also contain underscores, dashes, and square/round brackets. Spaces are not allowed.
        Neither is allowed to be empty.

        If suffix is not supplied, defaults to '.ccpn' (suffix must be '.ccpn' for project folder).

        NOTE that dashes, brackets, and other special characters may be changed to underscores in the loaded project-name,
        but filepath is not altered during loading/saving.

        :param Optional[list] suffixes: optional list of allowed suffixes (including .)
        :return: True if valid.
        """
        return self.isValidFilePath() and \
            self.isValidBasename(allowSpace=False, suffixes=suffixes if suffixes is not None else ['.ccpn', ])

    def addTimeStamp(self, timeFormat='%Y-%m-%d-%H%M%S', sep='-' ) -> Path:
        """Return a Path instance with path.timeStamp-suffix profile
        """
        now = datetime.datetime.now().strftime(timeFormat)
        return self.parent / (self.stem + sep + str(now) + self.suffix)

    def incrementVersion(self) -> Path:
        """return: a Path instance with directory/basename(version).suffixes profile
        """
        _dir = self.parent
        _basename = self.basename
        _version = self.version
        if _version > 0:
            _basename = _basename[: -len(f'({_version})')]

        _version += 1
        return _dir / _basename + f'({_version})' + ''.join(self.suffixes)

    def uniqueVersion(self) -> Path:
        """:return a Path instance which is unique by incrementing version index
        """
        result = Path(self)
        while result.exists():
            result = result.incrementVersion()
        return result

    def normalise(self) -> Path:
        """:return a normalised path
        """
        return Path(os.path.normpath(self.asString()))  # python <= 3.4; strings only

    def open(self, *args, **kwds):
        """Subclassing to catch any long file name errors that allegedly can occur on Windows
        """
        try:
            fp = super().open(*args, **kwds)
        except FileNotFoundError:
            if len(self.asString()) > 256:
                raise FileNotFoundError('Error opening file "%s"; potentially path length (%d) is too large. Consider moving the file'
                                        % (self, len(self.asString()))
                                        )
            else:
                raise FileNotFoundError('Error opening file "%s"' % self)
        return fp

    def globList(self, pattern='*') -> list:
        """Return a list rather than a generator
        """
        return [p for p in self.glob(pattern=pattern)]

    def removeDir(self):
        """Recursively remove content of self and subdirectories
        """
        if not self.is_dir():
            raise ValueError('%s is not a directory' % self)
        _rmdirs(str(self))

    def fetchDir(self, *dirNames) -> Path:
        """Return and (if needed) create all dirNames relative to self
        :return: Path instance of self / dirName[0] / dirName[1] ...
        """
        if not self.is_dir():
            raise ValueError('%s is not a directory' % self)

        result = self
        for dirName in dirNames:
            result = result / dirName
            if not result.exists():
                result.mkdir()
        return result

    def copyDir(self, destination, overwrite=False) -> Path:
        """Recursively copy directory represented by self to destination.
        :param destination: a Path or str denoting the destination
        :return a Path instance of the location of the copied directory
        """
        import shutil

        if not self.exists():
            raise FileNotFoundError(f'"{self}" does not exist')
        if not self.is_dir():
            raise RuntimeError(f'"{self}" is not a directory')

        _dest = aPath(destination)
        if _dest.exists():
            if not overwrite:
                raise FileExistsError(f'"{destination}" already exists and overwrite=False')
            _dest.remove()

        _result = shutil.copytree(self, dst=_dest, symlinks=True)
        return Path(_result)

    def removeFile(self):
        """Remove file represented by self.
        """
        if self.is_dir():
            raise RuntimeError('%s is a directory' % self)
        self.unlink()

    def copyFile(self, destination, overwrite) -> Path:
        """Copy file represented by self to destination.
        if destination is an existing directory: Create new path from self and destination

        :param destination: a Path or string instance. Create new path destination is an existing directory
        :param overwrite: Overwrite existing file
        :return Path instance of the newly created file
        """
        import shutil

        if not self.exists():
            raise FileNotFoundError(f'"{self}" does not exist')
        if not self.is_file():
            raise RuntimeError(f'"{self}" is not a file')

        _dest = aPath(destination)
        if _dest.is_dir():  # implies it exists as is_dir returns False if it doesn't
            _dir, _base, _suffix = self.split3()
            # create a new path from the destination directory and basename, suffix of self
            # NB shutil.copy2 used below can do the same, but always overwrites the target
            _dest = _dest / _base + _suffix

        if _dest.exists() and not overwrite:
            raise FileExistsError(f'"{_dest}" already exists and overwrite=False')

        shutil.copy2(self, _dest)
        return _dest

    def copyfile(self, destination, overwrite):
        """Copy file represented by self to destination.
        deprecated; use copyFile instead
        """
        self.copyFile(destination, overwrite)

    def remove(self):
        """Remove file/directory represented by self if it exists.
        """
        if self.exists():
            if self.is_dir():
                self.removeDir()
            else:
                self.removeFile()

    def assureSuffix(self, suffix) -> Path:
        """Create a Path instance with an assured suffix; adds suffix if not present.
        Does not change suffix if there is one (like with_suffix does).
        :return Path instance with an assured suffix
        """
        if not isinstance(suffix, str):
            raise TypeError('suffix %s must be a str' % str(suffix))

        # strip leading .'s e.g. suffix is '.zip'
        suffix = suffix.lstrip('.')
        if self.suffix != suffix:
            if self.name and self.name != '.':
                _name = '.'.join([str(self.stem), str(suffix)])
                return aPath(os.path.join(str(self.parent), _name))

        return self

    def withoutSuffix(self) -> Path:
        """:return a Path instance of self without suffix
        """
        if len(self.suffixes) > 0:
            return Path(self.with_suffix(''))
        else:
            return self

    def withSuffix(self, suffix) -> Path:
        """Create self with suffix; inverse of withoutSuffix()
        partially copies with_suffix, but does not allow for empty argument
        :return a Path instance of self with suffix
        """
        if suffix is None or len(suffix) == 0:
            raise ValueError('No suffix defined')
        return self.with_suffix(suffix=suffix)

    def listDirFiles(self, extension: str = None) -> list:
        """Obsolete; extension is without a "."
        use listdir instead
        """
        if not extension:
            return list(self.glob('*'))
        else:
            return list(self.glob(f'*.{extension}'))

    def listdir(self, suffix: str = None, excludeDotFiles: bool = True, relative: bool = False) -> list:
        """
        If self is a directory , return a list of its files as Path instance.
        If the suffix is given (e.g.: .pdf, .jpeg...), returns only files of that pattern.
        Non-recursive.

        :param suffix: optional suffix used to filter
        :param excludeDotFiles: flag to exclude (nix) dot-files (e.g. like .cshrc .DSstore); default True
        :param relative: flag to return path relative to self.
        :returns A list with Path instances
        :raises FileNotFoundError or RuntimeError
        """
        if not self.exists():
            raise FileNotFoundError(f'listdir: "{self}" does not exist')

        if not self.is_dir():
            raise RuntimeError(f'listdir: "{self}" is not a directory')

        if not suffix:
            result = [Path(f) for f in self.glob('*')]
        else:
            result = [Path(f) for f in self.glob(f'*{suffix}')]

        if excludeDotFiles:
            result = [f for f in result if not f.basename.startswith('.')]

        if relative:
            result = [f.relative_to(self) for f in result]

        return result

    def split3(self) -> tuple:
        """:return a tuple of (.parent, .stem, .suffix) strings
        """
        return (str(self.parent), str(self.stem), str(self.suffix))

    def split2(self) -> tuple:
        """:return a tuple (.parent, .name) strings
        """
        return (str(self.parent), str(self.name))

    def asString(self) -> str:
        """:return self as a string"""
        return str(self)

    def startswith(self, prefix) -> bool:
        """:return True if self starts with prefix"""
        path = self.asString()
        return path.startswith(prefix)

    def __len__(self):
        return len(self.asString())

    def __hash__(self):
        _p = str(self)
        _hash = _p.__hash__()
        return _hash

    def __eq__(self, other):
        return (str(self).strip() == str(other).strip())

    # No longer needed in Python 3.x
    # def __ne__(self, other):
    #     return not (str(self).strip() == str(other).strip())

    def __add__(self, other):
        return Path(self.asString() + other)


#=========================================================================================
# Functions
#=========================================================================================
def scandirs(dirname):
    """ Recursively find all subdirs"""
    subfolders = [f.path for f in os.scandir(dirname) if f.is_dir()]
    for dirname in list(subfolders):
        subfolders.extend(scandirs(dirname))
    return subfolders

def _rmdirs(path):
    """Recursively delete path and contents; maybe not very fast
    From: https://stackoverflow.com/questions/303200/how-do-i-remove-delete-a-folder-that-is-not-empty-with-python
    """
    path = Path(path)
    # using glob(*) because interdir() created occasional 'directory not empty' crashes (OS issue; Mac hidden files
    # or timing problems?). Maybe need to fallback on ccpn.util.LocalShutil
    for sub in path.glob('*'):
        if sub.is_dir():
            _rmdirs(sub)  # sub is a directory
        else:
            sub.unlink()  # removes files and links
    path.rmdir()


def aPath(path):
    """Return a ~-expanded, left/right spaces-stripped, normalised Path instance"""
    return Path(str(path).strip()).expanduser().normalise()


def normalisePath(path, makeAbsolute=None):
    """
    Normalises the path, e.g. removes redundant .. and slashes and
    makes sure path uses '/' rather than '\\' as can happen on Windows.
    """

    if os.sep == winsep:
        path = path.replace(dirsep, winsep)
        path = os.path.normpath(path)
        path = path.replace(winsep, dirsep)
    else:
        path = path.replace(winsep, dirsep)
        path = os.path.normpath(path)

    if makeAbsolute:
        if path and path[0] != dirsep:
            path = joinPath(os.getcwd(), path)

    return path


def unnormalisePath(path):
    """
    On Unix does nothing, on Windows replaces '/' with '\\'/
    """

    if os.sep != '/':
        path = path.replace('/', os.sep)

    return path


def joinPath(*args):
    """
    The same as os.path.join but normalises the result.
    """

    return normalisePath(os.path.join(*args))


def splitPath(path):
    """
    The same as os.path.split but with normalisation taken into account.
    """

    (head, tail) = os.path.split(unnormalisePath(path))
    head = normalisePath(head)

    return head, tail


def converseSplitPath(path):
    """
    Similar to splitPath but with head being the top directory and tail being the rest.
    """

    pair = splitPath(path)
    head = None
    tail = ''
    while pair[0] and pair[0] not in ('.', '/'):
        head = pair[0]
        tail = joinPath(pair[1], tail)
        pair = splitPath(head)

    if head is None:
        (head, tail) = pair

    return head, tail


def getPathToImport(moduleString):
    """Get absolute path to module (directory or file)"""
    module = importlib.import_module(moduleString)
    return os.path.dirname(module.__file__)


def getTopDirectory():
    """
    Returns the 'top' directory of the containing repository (ccpnv3).
    """

    return os.path.dirname(os.path.dirname(getPythonDirectory()))


def getPythonDirectory():
    """
    Returns the 'top' python directory, the one on the python path.
    """
    return os.path.dirname(getPathToImport('ccpn'))


def deletePath(path):
    """Removes path whether file or directory, taking into account whether symbolic link.
    """

    if not os.path.exists(path):
        return

    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    else:
        shutil.rmtree(path)


def commonSuperDirectory(*fileNames):
    """ Find lowest directory that contains all files in list
    NB does not normalise file names.

    Input: a list of file names
    Output: lowest directory that contains all files. Does *not* end with a file
    """
    return os.path.dirname(os.path.commonprefix(fileNames))


def checkFilePath(filePath, allowDir=True):
    msg = ''
    isOk = True

    if not filePath:
        isOk = False

    elif not os.path.exists(filePath):
        msg = 'Location "%s" does not exist' % filePath
        isOk = False

    elif not os.access(filePath, os.R_OK):
        msg = 'Location "%s" is not readable' % filePath
        isOk = False

    elif os.path.isdir(filePath):
        if allowDir:
            return isOk, msg
        else:
            msg = 'Location "%s" is a directory' % filePath
            isOk = False

    elif not os.path.isfile(filePath):
        msg = 'Location "%s" is not a regular file' % filePath
        isOk = False

    elif os.stat(filePath).st_size == 0:
        msg = 'File "%s" is of zero size ' % filePath
        isOk = False

    return isOk, msg


def suggestFileLocations(fileNames, startDir=None):
    """ From a list of files, return a common superdirectory and a list of
    relative file names. If any of the files do not exist, search for an
    alternative superdirectory that does contain the set of relative file names.
    Searches in either a superdirectory of the starting/current directory,
    or in a direct subdirectory.

    Input: list of file names

    Output: Superdirectory, list of relative file names.
    If no suitable location is found, superdirectory is returned as None
    """

    if not fileNames:
        return None, []

    # set up startDir
    if startDir is None:
        startDir = os.getcwd()
    startDir = normalisePath(startDir, makeAbsolute=True)

    # find common baseDir and paths
    files = [normalisePath(fp, makeAbsolute=True) for fp in fileNames]
    baseDir = commonSuperDirectory(*files)
    prefix = os.path.join(baseDir, '')
    lenPrefix = len(prefix)
    paths = [fp[lenPrefix:] for fp in files]

    if [fp for fp in files if not os.path.exists(fp)]:
        # some file not found.

        # look in superdirectories
        tail = 'junk'
        baseDir = startDir
        while tail:
            for path in paths:
                fp = os.path.join(baseDir, path)
                if not os.path.exists(fp):
                    # a file is not found. try new baseDir
                    break
            else:
                # this one is OK - stop searching
                break
            #
            baseDir, tail = os.path.split(baseDir)

        else:
            # No success - try in a subdirectory (one level) of startDir
            matches = glob.glob(os.path.join(startDir, '*', paths[0]))
            for aMatch in matches:
                baseDir = normalisePath(aMatch[:-len(paths[0])])
                for path in paths:
                    fp = os.path.join(baseDir, path)
                    if not os.path.exists(fp):
                        # a file is not found. try new baseDir
                        break
                else:
                    # this one is OK - stop searching
                    break
            else:
                # we give up
                baseDir = None
    #
    return baseDir, paths


def fetchDir(path, dirName):
    """
    :param path: string of parent path where to add a new subdir
    :param dirName: str of the new sub dir
    :return: if not already existing, creates a new folder with the given name, return the full path as str
    """
    if path is not None:
        newPath = os.path.join(path, dirName)
        if not os.path.exists(newPath):
            os.makedirs(newPath)
            return newPath
        else:
            return newPath


# Original in util.Common
defaultFileNameChar = '_'
separatorFileNameChar = '+'
validFileNamePartChars = ('abcdefghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                          + defaultFileNameChar)
validCcpnFileNameChars = validFileNamePartChars + '-.' + separatorFileNameChar


def makeValidCcpnFilePath(path):
    """Replace invalid chars in path to assure Python 2.1 (used in ObjectDomain) compatibility
    """
    # used in ApiPath.py
    ll = []
    for ii, char in enumerate(path):
        if char not in validFileNamePartChars:
            char = defaultFileNameChar
        ll.append(char)
    return ''.join(ll)


makeValidCcpnPath = makeValidCcpnFilePath


# used in ccpnmodel/ccpncore/lib/chemComp/Io.py"


#=========================================================================================
# main
#=========================================================================================

def main():
    # put into test-cases

    fp = Path('/wergw.e98/help/name.ccpn')
    print(fp.parts)
    print(fp.isValidFilePath(allowUpperAlpha=False, allowUnderscore=False, allowDash=False))
    # True

    print(fp.isValidFilePath(allowUnderscore=False))
    print(fp.isValidFilePath(allowNumeric=False))
    print(fp.isValidFilePath(allowDash=False))
    print(fp.isValidFilePath(allowFullstop=False))
    print(fp.isValidFilePath(allowLowerAlpha=False))
    # True, False, True, False, False

    print('------->')
    fp = Path('/wergwe98/n2$@34a£-$me/name.ccpn')  # --> $@£
    print(fp.isValidFilePath(allowOther=r'@'))
    print(fp.isValidFilePath(allowOther=r'@£$'))
    # False, True

    print('------->')
    fp = Path('/wergwe98/he-lp/n2$@3()4a£-$me.ccpn')  # --> $@£
    print(fp.isValidBasename(suffixes=['', ]))
    print(fp.isValidBasename(suffixes=['.ccpn']))
    # False, False

    print(fp.isValidBasename(allowOther='$'))
    print(fp.isValidBasename(allowOther='£'))
    print(fp.isValidBasename(allowOther='@'))
    print(fp.isValidBasename(allowOther='$£'))
    print(fp.isValidBasename(allowOther='$£@'))
    print(fp.isValidBasename(allowOther='@$£'))  # different order
    print(fp.isValidBasename(allowOther='£@\$'))
    # False, False, False, False, True, True, True

    print('------->')
    fp = Path('/werg-we98/help/name.ccpn')
    print(fp.isValidBasename(suffixes=['', ]))
    print(fp.isValidBasename(suffixes=['.ccpn']))
    print(fp.isValidCcpn())
    # False, True, True

    try:
        print(fp.isValidBasename(suffixes=[34, '.ccpn']))  # type-hints does not recognise lists like this, only tuples
    except TypeError:
        ...

    try:
        print(fp.isValidBasename(suffixes=['', 34]))
    except TypeError:
        ...
    # Error, Error


if __name__ == '__main__':
    main()
