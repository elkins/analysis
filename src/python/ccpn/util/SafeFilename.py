"""
Functions to append a number to the end of a filename if it already exists
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
__dateModified__ = "$dateModified: 2025-03-21 15:35:20 +0000 (Fri, March 21, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-06-16 16:28:31 +0000 (Fri, June 16, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import re
import itertools
import errno
import os
import sys
from typing import Generator, IO
from contextlib import contextmanager


_DEBUGFUNC = None  # sys.stderr.write
_MAXITERATIONS = 100
# available options for the spacer
SPACERS = [None, '', ' ', '-', '_', ' copy ']


def _unescape_string(escaped_string):
    return re.sub(r'\\(.)', r'\1', escaped_string)


def _iter_incrementing_file_names(path: str, endswith: str = '',
                                  spacer: str | None = None, brackets: bool = True) -> Generator[str, None, None]:
    """
    Iterate incrementing file names. Start with `path` and add `_(n)` before the extension,
    where `n` starts at 1 and increases.

    endswith can be provided to ensure that endings are not duplicated, e.g., `file_new_new_new (1)`, etc.

    :param path: The file path to start with.
    :type path: str
    :param endswith: A string to insert before the number. Defaults to an empty string.
    :type endswith: str, optional
    :param spacer: Add a character or string before the number. Defaults to none.
    :type spacer: str, optional
    :param brackets: Whether to add brackets around the number. Defaults to True.
    :type brackets: bool, optional
    :yield: Incrementing file names with the given pattern.
    :rtype: Generator[str, None, None]
    :raises TypeError: If an invalid `spacer` or `brackets` argument is provided.
    :raises RuntimeError: If the file naming pattern is invalid or max iterations are exceeded.
    """
    if spacer not in SPACERS:
        raise TypeError(f'Invalid spacer {spacer!r}, must be one of {SPACERS}')
    if not isinstance(brackets, bool):
        raise TypeError(f'Invalid brackets {brackets}')

    yield path  # First yield the original path without a number

    prefix, ext = os.path.splitext(path)

    # now start appending the incrementing numbers before the extension
    preB = '\(' if brackets else ''
    postB = '\)' if brackets else ''
    endswith = re.escape(endswith)  # escape all the strings, stops unwanted encoding in filter
    spacer = re.escape(spacer or '')
    reFilter = rf'(.*?)({endswith})?({spacer})?({preB})?([\d]*)({postB})?$'
    if _DEBUGFUNC:
        _DEBUGFUNC(f'==>  searching {spacer}:{preB}:{postB}  {prefix}  {ext}    {reFilter}\n')
    if not (match := re.search(reFilter, prefix)):
        raise RuntimeError('Invalid file naming pattern.')

    num = int(match.group(5) or '0') + 1  # get the next initial available number
    # unescape to remove all `\` again to rebuild string
    grps = [match.group(1),
            _unescape_string(endswith),
            _unescape_string(spacer),
            _unescape_string(preB),
            str(num),
            _unescape_string(postB),
            ext]
    for ii in itertools.islice(itertools.count(start=num, step=1), _MAXITERATIONS):
        # insert the next number
        grps[4] = str(ii)
        if _DEBUGFUNC:
            _DEBUGFUNC(f'==>  {"".join(filter(None, grps))}\n')
        yield ''.join(filter(None, grps))

    raise RuntimeError('Maximum filename search exceeded')


@contextmanager
def safeOpen(path: str, mode: str, endswith: str = '', spacer: str | None = None, brackets: bool = True) \
        -> Generator[tuple[IO, str], None, None]:
    """
    Open a file safely, avoiding overwrites by adding a numbered suffix if the file already exists.

    A safe filename is created of the form:
        filename[endswith][spacer][open-bracket]number[close-bracket].extension

    **Usage:**
    ::

        with safeOpen(path, [options]) as (fd, safeFileName):
            ...

    fd is the file descriptor, to be used as with open, e.g., fd.read()
    safeFileName is the new safe filename.

    **Examples**

    Basic Usage:
    ::

        path = "report.txt"
        with safeOpen(path, 'w'):
            ...

    opens `report.txt` (if it doesn't exist) or `report(1).txt`, `report(2).txt`, etc.

    Custom Endswith and Spacer:
    ::

        path = "data3.csv"
        with safeOpen(path, 'w', endswith="_backup", spacer="-", brackets=False):
            ...

    opens `data3.csv` (if it doesn't exist) or `data_backup-4.csv`, `data_backup-5.csv`, etc.

    If the initial file contains '_backup', it will always be included:
    ::

        path = "data_backup-3.csv"
        with safeOpen(path, 'w', endswith="_backup", spacer="-", brackets=False):
            ...

    opens `data_backup-3.csv` (if it doesn't exist) or `data_backup-4.csv`, `data_backup-5.csv`, etc.

    :param path: The target file path.
    :type path: str
    :param mode: The file opening mode.
    :type mode: str
    :param endswith: A string to insert before the number. Defaults to an empty string.
    :type endswith: str, optional
    :param spacer: Add a character or string before the number. Defaults to none.
    :type spacer: str, optional
    :param brackets: Whether to add brackets around the number. Defaults to True.
    :type brackets: bool, optional
    :yield: A tuple containing the file handle and the new safe filename.
    :rtype: Generator[tuple[IO, str], None, None]
    :raises OSError: If an error occurs while opening the file.
    """
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

    if 'b' in mode and sys.platform.startswith('win') and hasattr(os, 'O_BINARY'):
        flags |= os.O_BINARY

    # repeat over filenames with iterating number
    for filename in _iter_incrementing_file_names(path, endswith=endswith, spacer=spacer, brackets=brackets):
        try:
            file_handle = os.open(filename, flags)
        except OSError as es:
            if es.errno == errno.EEXIST:
                continue  # Try the next filename
            raise
        else:
            # yield the file descriptor and new, safe filename
            with os.fdopen(file_handle, mode) as fd:
                yield fd, filename
            # ...and exit
            return


def getSafeFilename(path: str, *, endswith: str = '', spacer: str | None = None,
                    brackets: bool = True,
                    mode: str = 'w', test: bool = False) -> str | None:
    """
    Get the first available safe filename, avoiding potential overwrites by adding a numbered suffix if
    the file already exists.

    A safe filename is created of the form:
        filename[endswith][spacer][open-bracket]number[close-bracket].extension

    If `test` is `True`, an attempt will be made to open the file with the specified mode,
    raising any errors as appropriate.

    **Examples**

    Basic Usage:
    ::

        path = "report.txt"
        safe_filename = getSafeFilename(path)
        print(safe_filename)

    creates `report.txt` (if it doesn't exist) or `report(1).txt`, `report(2).txt`, etc.

    Custom Endswith and Spacer:
    ::

        path = "data3.csv"
        safe_filename = getSafeFilename(path, endswith="_backup", spacer="-", brackets=False)
        print(safe_filename)

    creates `data3.csv` (if it doesn't exist) or `data_backup-4.csv`, `data_backup-5.csv`, etc.

    If the initial file contains '_backup', it will always be included:
    ::

        path = "data_backup-3.csv"
        safe_filename = getSafeFilename(path, endswith="_backup", spacer="-", brackets=False)
        print(safe_filename)

    creates `data_backup-3.csv` (if it doesn't exist) or `data_backup-4.csv`, `data_backup-5.csv`, etc.

    :param path: The target file path.
    :type path: str
    :param endswith: A string to insert before the number. Defaults to an empty string.
    :type endswith: str, optional
    :param spacer: Add a character or string before the number. Defaults to none.
    :type spacer: str, optional
    :param brackets: Whether to add brackets around the number. Defaults to True.
    :type brackets: bool, optional
    :param mode: The file opening mode.
    :type mode: str
    :param test: Whether to try and open the file with the specified mode. Defaults to False.
    :type test: bool, optional
    :return: A safe filename that does not yet exist.
    :rtype: str | None
    :raises OSError: If an error occurs while opening the file.
    """
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

    if 'b' in mode and sys.platform.startswith('win') and hasattr(os, 'O_BINARY'):
        flags |= os.O_BINARY

    # repeat over filenames with iterating number
    for filename in _iter_incrementing_file_names(path, endswith=endswith, spacer=spacer, brackets=brackets):
        if test:
            try:
                # open the file with the specified mode
                file_handle = os.open(filename, flags)
            except OSError as es:
                if es.errno == errno.EEXIST:
                    continue  # Try the next filename
                raise
            else:
                os.close(file_handle)
                os.remove(filename)
                if _DEBUGFUNC:
                    _DEBUGFUNC(f'==>  valid {filename}\n')
                # return the new filename
                return filename

        elif not os.path.exists(filename):
            if _DEBUGFUNC:
                _DEBUGFUNC(f'==>  valid {filename}\n')
            # return the new filename
            return filename


def main():
    path = '/Users/ejb66/default1.ccpn'
    getSafeFilename(path, endswith='_new', spacer=' copy ')
    path = '/Users/ejb66/default_new8.ccpn'
    getSafeFilename(path, endswith='_new', spacer=' copy ')
    path = '/Users/ejb66/default3.ccpn'
    getSafeFilename(path, endswith='_new', brackets=False)
    path = '/Users/ejb66/default3.ccpn'
    getSafeFilename(path, brackets=False)


if __name__ == '__main__':
    main()
