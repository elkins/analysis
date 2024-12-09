"""Miscellaneous common utilities
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


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
__dateModified__ = "$dateModified: 2024-12-09 12:39:16 +0000 (Mon, December 09, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import datetime
import os
import random
import re
import sys
import string
import platform
import collections
from itertools import islice, cycle, zip_longest
from string import whitespace
from contextlib import suppress
from typing import Any, Iterable, Iterator

from ccpn.util.OrderedSet import OrderedSet
from ccpn.util import Constants
from ccpn.util.decorators import singleton


_DEBUG = False
# define a simple sentinel
NOTHING = object()

# Max value used for random integer. Set to be expressible as a signed 32-bit integer.
maxRandomInt = 2000000000

WHITESPACE_AND_NULL = {'\x00', '\t', '\n', '\r', '\x0b', '\x0c'}


# # valid characters for file names
# # NB string.ascii_letters and string.digits are not compatible
# # with Python 2.1 (used in ObjectDomain)
# defaultFileNameChar = '_'
# separatorFileNameChar = '+'
# validFileNamePartChars = ('abcdefghijklmnopqrstuvwxyz'
#                           'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
#                           + defaultFileNameChar)
# validCcpnFileNameChars = validFileNamePartChars + '-.' + separatorFileNameChar

# # Not used - Rasmus 20/2/2017
# Sentinel = collections.namedtuple('Sentinel', ['value'])


# def convertStringToFileName(fileNameString, validChars=validCcpnFileNameChars,
#                             defaultChar=defaultFileNameChar):
#     ll = [x for x in fileNameString]
#     for ii, char in enumerate(ll):
#         if char not in validChars:
#             ll[ii] = defaultChar
#     #
#     return ''.join(ll)

#
# def getCcpFileString(fileNameString):
#     """
#     Changes an input string to the one used for a component of file names.
#     """
#
#     return convertStringToFileName(fileNameString, validFileNamePartChars,
#                                    defaultFileNameChar)


def incrementName(name, split: str = '_'):
    """Add '_1' to name or change suffix '_n' to '_(n+1).
    If name is only a number increment by 1
    """
    ll = name.rsplit(split, 1)
    if len(ll) == 2:
        with suppress(ValueError):
            ll[1] = str(int(ll[1]) + 1)
            return split.join(ll)

    elif len(ll) == 1:
        with suppress(ValueError):
            return str(int(ll[0]) + 1)

    return name + split + '1'


# def _incrementObjectName(project, pluralLinkName, name):
#     """ fetch an incremented name if an object in list (project.xs) has already taken it. """
#     originalName = name
#     names = [d.name for d in getattr(project, pluralLinkName) if hasattr(d, 'name')]
#     while name in names:
#         name = incrementName(name)
#     if originalName != name:
#         getLogger().info('Name:% already assigned. Renamed to %s' % (originalName, name))
#     return name

def recursiveImport(dirname, modname=None, ignoreModules=None, force=False):
    """ recursively import all .py files
    (not starting with '__' and not containing internal '.' in their name)
    from directory dirname and all its subdirectories, provided they
    contain '__init__.py'
    Serves to check that files compile without error

    modname is the module name (dot-separated) corresponding to the directory
    dirName.
    If modname is None, dirname must be on the pythonPath

    Note that there are potential problems if the files we want are not
    the ones encountered first on the pythonPath
    """

    # Must be imported here, as entire file must be importable from Python 2 NefIo
    from . import Path

    listdir = os.listdir(dirname)
    try:
        listdir.remove('__init__.py')
    except ValueError:
        if not force:
            return

    files = []

    if ignoreModules is None:
        ignoreModules = []

    if modname is None:
        prefix = ''
    else:
        prefix = modname + '.'

    listdir2 = []
    for name in listdir:
        head, ext = os.path.splitext(name)
        if (prefix + head) in ignoreModules:
            pass
        elif ext == '.py' and head.find('.') == -1:
            files.append(head)
        else:
            listdir2.append(name)

    # import directory and underlying directories
    if modname:
        # Note that files is never empty, so module is lowest level not toplevel
        for ff in files:
            try:
                __import__(modname, {}, {}, [ff])
            except:
                # We want log output, not an Exception in all cases here
                from .Logging import getLogger

                getLogger().warning("Import failed for %s.%s" % (modname, ff))

    for name in listdir2:
        newdirname = Path.joinPath(dirname, name)
        if os.path.isdir(newdirname) and name.find('.') == -1:
            recursiveImport(newdirname, prefix + name, ignoreModules)


@singleton
class Process(object):
    """A simple (singleton)class to hold information about the process:
    pid:int
    username:str
    platform:str
    executable:Path : python executable as a Path instance
    initialWorkingDirectory:Path  : cwd() when first started as a Path instance
    """

    def __init__(self):
        import psutil
        from ccpn.util.Path import aPath

        proc = psutil.Process()

        self.pid = proc.pid
        self.username = proc.username()
        self.platform = sys.platform
        self.executable = aPath(proc.exe())
        self.initialWorkingDirectory = aPath(proc.cwd())

    def __str__(self):
        return f'<Process: pid={self.pid}, username={self.username}>'


def getProcess() -> Process:
    """Get the process info; e.g. getProcess().username
    :return The Process instance
    """
    return Process()


def isWindowsOS():
    return sys.platform[:3].lower() == 'win'


def isMacOS():
    return sys.platform[:6].lower() == 'darwin'


def isLinux():
    return sys.platform[:5].lower() == 'linux'


def isUbuntu():
    return 'ubuntu' in platform.version().lower()


def isUbuntuVersion(value: str = ''):
    from subprocess import Popen, PIPE

    HOSTNAMECTL = 'hostnamectl'
    OPERATING_SYSTEM = 'Operating System'

    if isUbuntu() and (osQuery := Popen(HOSTNAMECTL, stdout=PIPE, stderr=PIPE)):
        osStatus, _osError = osQuery.communicate()
        if osQuery.poll() == 0:
            for line in osStatus.decode("utf-8").split('\n'):
                if OPERATING_SYSTEM in line and value in line:
                    return True

    return False


def isRHEL(version: int | None = 8):
    import csv
    import pathlib

    if not isLinux():
        return False

    try:
        path = pathlib.Path("/etc/os-release")
        with open(path) as fp:
            reader = csv.reader(fp, delimiter="=")
            os_release = dict(reader)

        if (os_release.get('ID', '') == 'rhel' or 'rhel' in os_release.get('ID_LIKE', '')) and \
                (not version or
                 ((version_id := os_release.get('VERSION_ID', '')) and
                  version_id.startswith(str(version) + '.'))):
            return True
    except Exception:
        return False

    return False


def parseSequenceCode(value):
    """split sequence code into (seqCode,seqInsertCode, offset) tuple
    """
    # sequenceCodePattern = re.compile('(\d+)?(.*?)(\+\d+|\-\d+)?$')

    tt = Constants.sequenceCodePattern.match(value.strip()).groups()

    if tt[0] is None and not tt[1]:
        # special case: entire string matches offset modifier and is misread
        return None, tt[2], None
    else:
        return (
            tt[0] and int(tt[0]),  # None or an integer
            tt[1],  # Text string, possibly empty
            tt[2] and int(tt[2]),  # None or an integer
            )


def splitIntFromChars(value):
    """convert a string with a leading integer optionally followed by characters
    into an (integer,string) tuple
    """
    value = value.strip()

    for ii in reversed(range(1, len(value) + 1)):
        try:
            number = int(value[:ii])
            chars = value[ii:]
            break
        except ValueError:
            continue
    else:
        number = None
        chars = value

    return number, chars


def groupIntoChunks(aList, chunkSize, reverse=True):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(aList), chunkSize):
        yield sorted(aList[i:i + chunkSize], key=float, reverse=reverse)


def dictionaryProduct(dict1, dict2):
    """multiply input {a:x}, {b:y} to result {(a,b):x*y} dictionary
    """
    result = {}
    for key1, val1 in dict1.items():
        for key2, val2 in dict2.items():
            result[(key1, key2)] = val1 * val2
    return result


def uniquify(sequence):
    """Get list of unique elements in sequence, in order of first appearance
    """
    seen = set()
    seen_add = seen.add
    return [x for x in sequence if x not in seen and not seen_add(x)]  # NB: not seen.add(x) is always True; i.e. this
    # part just adds the element during the list comprehension


def flatten(items):
    """Yield items from any nested iterable; see Reference.
    Here is a general approach that applies to numbers, strings, nested lists and mixed containers.
    From: https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-list-of-lists/952952#952952
    ref: This solution is modified from a recipe in Beazley, D. and B. Jones. Recipe 4.14, Python Cookbook 3rd
         Ed., O'Reilly Media Inc. Sebastopol, CA: 2013.
    """
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def isClose(a, b, relTolerance=1e-05, absTolerance=1e-08):
    """Are a and b identical within reasonable floating point tolerance?
    Uses sum of relative (relTolerance) and absolute (absTolerance) difference

    Inspired by numpy.isclose()
    """
    return (abs(a - b) <= (absTolerance + relTolerance * abs(b)))


def isIterable(obj) -> bool:
    """Returns True if obj is iterable
    """
    try:
        iter(obj)
        return True
    except TypeError:
        pass
    return False


def indexOfMaxValue(theList):
    """Return the index of the item in theList with the maximum value
    :param theList: an iterable
    :return index value or -1 for an empty list
    """
    if not isIterable(theList):
        raise TypeError('indexOfMaxValue: theList is not iterable')
    if len(theList) == 0:
        return -1
    idx = max((val, i) for i, val in enumerate(theList))[1]
    return idx


def indexOfMinValue(theList):
    """Return the index of the item in theList with the minimum value
    :param theList: an iterable
    :return index value or -1 for an empty list
    """
    if not isIterable(theList):
        raise TypeError('indexOfMaxValue: theList is not iterable')
    if len(theList) == 0:
        return -1
    idx = min((val, i) for i, val in enumerate(theList))[1]
    return idx


def getTimeStamp():
    """Get iso-formtted timestamp
    """
    return datetime.datetime.today().isoformat()


def getUuid(programName, timeStamp=None):
    """Get UUid following the NEF convention
    """
    if timeStamp is None:
        timeStamp = getTimeStamp()
    return '%s-%s-%s' % (programName, timeStamp, random.randint(0, maxRandomInt))


def reorder(values, axisCodes, refAxisCodes):
    """reorder values in axisCode order to refAxisCode order, by matching axisCodes

    NB, the result will be the length of refAxisCodes, with additional Nones inserted
    if this is longer than the values.

    NB if there are multiple matches possible, one is chosen by heuristics"""
    from ccpn.core.lib.AxisCodeLib import _axisCodeMapIndices  # this causes circular imports. KEEP LOCAL

    if len(values) != len(axisCodes):
        raise ValueError("Length mismatch between %s and %s" % (values, axisCodes))
    remapping = _axisCodeMapIndices(axisCodes, refAxisCodes)
    result = list(values[x] for x in remapping)
    #
    return result


def _getShortUniqueID():
    import uuid

    _id = uuid.uuid4()
    shortID = str(_id).split('-')[-1]
    return str(shortID)


def stringifier(*fields, **options):
    """Get stringifier function, that will format an object x according to

    <str(x): field1=x.field1, field2=x.field2, ...>

    All floating point values encountered will be formatted according to floatFormat"""

    # Unfortunately necessary as this package must be read from v2io
    # and python 2 does not have keyword-only arguments
    # What we should do is the function definition below:
    # def stringifier(*fields, floatFormat=None):
    if 'floatFormat' in options:
        floatFormat = options.pop('floatFormat')
    else:
        floatFormat = None
    if options:
        raise ValueError("Unknown options: %s" % ', '.join(sorted(options.keys())))

    # Proper body of function starts here
    if floatFormat is None:
        # use default formatter, avoiding continuous creation of new ones
        localFormatter = stdLocalFormatter
    else:
        localFormatter = LocalFormatter(overrideFloatFormat=floatFormat)

    fieldFormats = []
    for field in fields:
        # String will be 'field1={_obj.field1}
        fieldFormats.append('{0}={{_obj.{0}!r}}'.format(field))

    formatString = '<{_obj.pid!s}| ' + ', '.join(fieldFormats) + '>'

    def formatter(x):
        # return localFormatter.format(format_string=formatString, _obj=x)
        return localFormatter.format(formatString, _obj=x)

    return formatter


def contains_whitespace(s):
    return True in [c in s for c in string.whitespace]


def contains_whitespace_nospace(s):
    return True in [c in s for c in string.whitespace if c != ' ']


def sortByPriorityList(values, priority, initialSort=True, initialSortReverse=False):
    """
    Sorts an iterable according to a list of priority items.
    Usage:
        sort_by_priority_list(values=[1,2,2,3], priority=[2,3,1])
        [2, 2, 3, 1]
    """
    if initialSort:
        values.sort(reverse=initialSortReverse)
    priority_dict = {k: i for i, k in enumerate(priority)}

    def priority_getter(value):
        return priority_dict.get(value, len(values))

    return sorted(values, key=priority_getter)


def makeIterableList(inList=None):
    """
    Take a nested collection of (tuples, lists or sets) and concatenate into a single list.
    Also changes a single item into a list.
    Removes any Nones from the list
    :param inList: list of tuples, lists, sets or single items
    :return: a single list
    """
    # if isinstance(inList, Iterable) and not isinstance(inList, str):
    if isinstance(inList, (tuple, list, set)):
        return [y for x in inList for y in makeIterableList(x) if inList]
    else:
        if inList is not None:
            return [inList]
        else:
            return []


def flattenLists(lists):
    """
    Take a list of lists and concatenate into a single list.
    Remove any Nones from the list
    :param lists: a list of lists
    :return: list.  a single list
    """
    return makeIterableList(lists)


def _truncateText(text, splitter=' , ', maxWords=4):
    """Splits the text by the given splitter. If more then maxWords, it return the maxWord plus dots, otherwise just the text"""
    words = text.split(splitter)
    if len(words) > maxWords:
        return splitter.join(words[:maxWords]) + ' ...'
    else:
        return text


def _traverse(obj, tree_types=(list, tuple)):
    """
    used to flat the state in a long list
    """
    if isinstance(obj, tree_types):
        for value in obj:
            for subvalue in _traverse(value, tree_types):
                yield subvalue
    else:
        yield obj


def percentage(percent, whole):
    return (percent * whole) / 100.0


def modifyByFraction(value, fraction):
    """
    Modify the given value by a specified fraction.

    Parameters:
    value (int, float): The original value to be modified.
    fraction (float): The fraction representing the change (positive for increase, negative for decrease).

    Returns:
    float: The modified value after the operation.
    """
    # Calculate the modified value
    new_value = value * (1 + fraction)  # Use fraction directly for both add and subtract

    return new_value


def _add(x, y):
    if y > 0:
        return _add(x, y - 1) + 1
    elif y < 0:
        return _add(x, y + 1) - 1
    else:
        return x


def _sub(x, y):
    if y > 0:
        return _sub(x, y - 1) - 1
    elif y < 0:
        return _sub(x, y + 1) + 1
    else:
        return x


def _fillListToLenght(aList, desiredLength, fillingValue=None):
    """
    Appends Nones to list to get length of list equal to the desiredLength.
    If the starting list is longer than the desiredLength: raise AttributeError
    """
    diffLenght = desiredLength - len(aList)
    if diffLenght < 0:
        raise AttributeError('The given list has a longer length than the desiredLength.')
    return aList + [fillingValue] * diffLenght


def splitDataFrameWithinRange(dataframe, column1, column2, minX, maxX, minY, maxY):
    """
    :param dataframe: dataframe with index a pid type, columns str, values floats or ints
    :param column1: label1 , eg PC1
    :param column2: label1 , eg PC2
    :param minX:  min value for Y
    :param maxX:  Max value for X
    :param minY: min value for Y
    :param maxY: max value for Y
    :return:  inners  a dataframe like the unput  but containing only the values within the ranges  and
              outers (rest) not included in inners
    """

    bools = dataframe[column1].between(minX, maxX, inclusive=True) & dataframe[column2].between(minY, maxY,
                                                                                                inclusive=True)
    inners = dataframe[bools]
    outers = dataframe[-bools]
    filteredInners = inners.filter(items=[column1, column2])
    filteredOuters = outers.filter(items=[column1, column2])

    return filteredInners, filteredOuters


class LocalFormatter(string.Formatter):
    """Overrides the string formatter to change the float formatting"""

    def __init__(self, overrideFloatFormat='.6g'):
        super(LocalFormatter, self).__init__()
        self.overrideFloatFormat = overrideFloatFormat

    def convert_field(self, value, conversion):
        # do any conversion on the resulting object
        # NB, conversion parameter is not used

        if hasattr(value, 'pid'):
            return str(value)
        elif isinstance(value, float):
            return format(value, self.overrideFloatFormat)
        elif type(value) == tuple:
            # Deliberate. We do NOT want to catch tuple subtypes here
            end = ',)' if len(value) == 1 else ')'
            return '(' + ', '.join(self.convert_field(x, 'r') for x in value) + end
        elif type(value) == list:
            # Deliberate. We do NOT want to catch list subtypes here
            return '[' + ', '.join(self.convert_field(x, 'r') for x in value) + ']'
        elif conversion is None:
            return value
        elif conversion == 's':
            return str(value)
        elif conversion == 'r':
            return repr(value)
        elif conversion == 'a':
            try:
                return ascii(value)
            except NameError:
                # Likely we are in Python 2.
                # As ascii behaves like Python 2 repr, this should be the correct workaround
                return repr(value)
        raise ValueError("Unknown conversion specifier {0!s}".format(conversion))


stdLocalFormatter = LocalFormatter()


def _SortByMatch(item):
    """quick sorting key for axisCode match tuples
    """
    return -item[2]  # sort from high to low


def _atoi(text):
    return int(text) if text.isdigit() else text


def _naturalKeyObjs(obj, theProperty='name'):
    text = getattr(obj, theProperty)
    return [_atoi(c) for c in re.split(r'(\d+)', text)]


def naturalSortList(ll, reverse=True):
    """
    :param ll: a list of strings
    :param reverse: reverse the sort-order
    :return: a sorted list by natural sort
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanumKey = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(ll, key=alphanumKey, reverse=reverse)


def sortObjectByName(objs, reverse=True):
    """
    :param objs: list of objects that contains the property name. E.g. sample.name
    :param reverse: bool. False: descending order.
                          True: ascending order.
    :return: None
    Sorts the objects by digit if present in the name, otherwise alphabetically.
    """
    objs.sort(key=_naturalKeyObjs, reverse=reverse)


def greekKey(word):
    """Sort key for sorting a list by the equivalent greek letter
    """
    greekSort = '0123456789@ABGDEZHQIKLMNXOPRSTUFCYWabgdezhqiklmnxoprstufcyw'
    greekLetterCount = len(greekSort)

    key = (0,)
    if word:
        key = (ord(word[0]),)
        key += tuple(greekSort.index(c) if c in greekSort else greekLetterCount for c in word[1:])
    return key


def getIsotopeListFromCode(isotopeCode):
    """Return a list of defined atom names based on the isotopeCode
    """
    from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

    if isotopeCode in NEF_ATOM_NAMES:
        atomNames = [atomName for atomName in NEF_ATOM_NAMES[isotopeCode]]
    else:
        keys = sorted(NEF_ATOM_NAMES.keys(), key=lambda kk: kk.strip('0123456789'))
        atomNames = list(OrderedSet([atomName for key in keys for atomName in NEF_ATOM_NAMES[key]]))

    return atomNames


def _compareDict(d1, d2):
    """Compare the keys in two dictionaries
    Routine is recursive, empty dicts are ignored
    """
    for k in d1:
        if k not in d2:
            return False
        if type(d1[k]) == dict and d1[k]:
            if type(d2[k]) == dict and d2[k]:
                compare = _compareDict(d1[k], d2[k])
                if not compare:
                    return False
            else:
                return False
    for k in d2:
        if k not in d1:
            return False
        if type(d2[k]) == dict and d2[k]:
            if type(d1[k]) == dict and d1[k]:
                compare = _compareDict(d1[k], d2[k])
                if not compare:
                    return False
            else:
                return False

    return True


# GWV 14/01/2021: replaced by near similar _validateStringValue classmethod on AbtractWrapper
# def _validateName(project, cls, value: str, attribName: str = 'name', allowWhitespace: bool = False, allowEmpty: bool = False,
#                   allowNone: bool = False, allowLeadingTrailingWhitespace: bool = False, allowSpace: bool = True,
#                   checkExisting: bool = True):
#     """Check that the attribName is valid
#     """
#     from ccpn.core.lib import Pid  # avoids circular imports
#
#     if value is not None:
#         if not isinstance(value, str):
#             raise TypeError('{}.{} must be a string'.format(cls.className, attribName))
#         if not value and not allowEmpty:
#             raise ValueError('{}.{} must be set'.format(cls.className, attribName))
#         if Pid.altCharacter in value:
#             raise ValueError('Character {} not allowed in {}.{}'.format(Pid.altCharacter, cls.className, attribName))
#         if allowWhitespace:
#             if not allowSpace and ' ' in value:
#                 raise ValueError('space not allowed in {}.{}'.format(cls.className, attribName))
#         else:
#             if allowSpace and contains_whitespace_nospace(value):
#                 raise ValueError('whitespace not allowed in {}.{}'.format(cls.className, attribName))
#             elif not allowSpace and contains_whitespace(value):
#                 raise ValueError('whitespace not allowed in {}.{}'.format(cls.className, attribName))
#         if not allowLeadingTrailingWhitespace and value != value.strip():
#             raise ValueError('{}.{} cannot contain leading/trailing whitespace'.format(cls.className, attribName))
#
#     elif not allowNone:
#         raise ValueError('None not allowed in {}.{}'.format(cls.className, attribName))
#
#     # previous = project.getByRelativeId(value)
#     # if previous not in (None, cls):
#     #     raise ValueError('{} already exists'.format(previous.longPid))
#
#     if checkExisting:
#         # this is not valid for nmrAtoms
#         found = [obj for obj in getattr(project, cls._pluralLinkName, []) if getattr(obj, attribName, None) == value]
#         if found:
#             raise ValueError('{} already exists'.format(found[0].id))
#
#     # will only get here if all the tests pass
#     return True


def stringToCamelCase(label):
    """Change string to camelCase format
    Removes whitespaces, and changes first character to lower case
    """
    attr = label.translate({ord(c): None for c in whitespace})
    return attr[0].lower() + attr[1:]


CAMELCASEPTN = r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))'
CAMELCASEREP = r' \1'


# alternative camelCase split = r'((?<=[a-z])[A-Z]|(?<=[A-Z])[A-Z](?=[a-z]))''

def camelCaseToString(name):
    """Change a camelCase string to string with spaces in front of capitals.
    Groups of capitals are taken as acronyms and only the last letter of a group is separated.
    The first letter is capitalised except in the special case of a camel case string beginning
    <lowerCase,uppercase>, in which case the first lowercase letter is preserved.
    e.g.
    camelCase -> Camel Case
    TLAAcronym -> TLA Acronym
    pHValue -> pH Value
    """
    if name[0:1].islower() and name[1:2].isupper():
        return name[0:1] + re.sub(CAMELCASEPTN, CAMELCASEREP, name[1:])
    else:
        label = re.sub(CAMELCASEPTN, CAMELCASEREP, name)
        return label[0:1].upper() + label[1:]


# GWV 20210113: moved to Project.py as only used there and was creating circular imports

# def isValidPath(projectName, stripFullPath=True, stripExtension=True):
#     """Check whether the project name is valid after stripping fullpath and extension
#     Can only contain alphanumeric characters and underscores
#
#     :param projectName: name of project to check
#     :param stripFullPath: set to true to remove leading directory
#     :param stripExtension: set to true to remove extension
#     :return: True if valid else False
#     """
#     if not projectName:
#         return
#
#     if isinstance(projectName, str):
#
#         name = os.path.basename(projectName) if stripFullPath else projectName
#         name = os.path.splitext(name)[0] if stripExtension else name
#
#         STRIPCHARS = '_'
#         for ss in STRIPCHARS:
#             name = name.replace(ss, '')
#
#         if name.isalnum():
#             return True
#
#
# def isValidFileNameLength(projectName, stripFullPath=True, stripExtension=True):
#     """Check whether the project name is valid after stripping fullpath and extension
#     Can only contain alphanumeric characters and underscores
#
#     :param projectName: name of project to check
#     :param stripFullPath: set to true to remove leading directory
#     :param stripExtension: set to true to remove extension
#     :return: True if length <= 32 else False
#     """
#     if not projectName:
#         return
#
#     if isinstance(projectName, str):
#         name = os.path.basename(projectName) if stripFullPath else projectName
#         name = os.path.splitext(name)[0] if stripExtension else name
#
#         return len(name) <= 32


def zipCycle(*iterables: Iterable[Any], emptyDefault: Any = None) -> Iterator[tuple[Any, ...]]:
    """
    Make an iterator returning elements from the iterable and saving a copy of each.
    When the iterable is exhausted, return elements from the saved copy.

    :param iterables: Any number of iterables to zip together.
    :param emptyDefault: The default value to return for exhausted iterables.
    :return: An iterator of tuples containing the zipped elements.

    Example:
        for i in zipCycle(range(2), range(5), ['a', 'b', 'c'], []):
            print(i)
        (0, 0, 'a', None)
        (1, 1, 'b', None)
        (0, 2, 'c', None)
        (1, 3, 'a', None)
        (0, 4, 'b', None)
    """
    if not iterables:
        return  # No iterables provided, nothing to yield
    cycles = [cycle(iterable) for iterable in iterables]
    # not sure how to get rid of the pycharm type-checking warning here
    for _ in zip_longest(*iterables, fillvalue=emptyDefault):
        yield tuple(next(cycle_, emptyDefault) for cycle_ in cycles)


def _getObjectsByPids(project, pids):
    return project.getObjectsByPids(pids)


def _getPidsFromObjects(project, objs):
    return project.getPidsByObjects(objs)


def copyToClipboard(items):
    """
    :param items: a list of items to be copied to Clipboard.
                  Each value is single quoted if a str (Pid if an AbstractWrapperObject instance),
                  or preserved the format for other cases. All values are comma separated.

    A very simple implementation of str to clipboard.
    An ideal implementation should deal with AbstractWrapperObjects using some sort of parser to be able to perform
    actions such as copy-paste peakLists via NEF etc.
    """
    import pandas as pd
    from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
    from ccpn.util.Logging import getLogger

    texts = []
    for i in items:
        if isinstance(i, AbstractWrapperObject):
            txt = f"""'{i.pid}'"""  # wrap a Pid with quotes if the format is of instance AbstractWrapperObject
        if hasattr(i, 'pid'):
            txt = f"""'{i.pid}'"""  # wrap a Pid with quotes if the format is of instance <object> with attribute pid
        elif isinstance(i, str):
            txt = f"""'{i}'"""  # wrap with quotes if the format is a string
        else:
            txt = f"""{i}"""  # otherwise preserve the format (e.g. floats, int...)
        texts.append(txt)
    values = '{}'.format(', '.join(sorted(set(texts), key=texts.index)))
    df = pd.DataFrame([values])
    df.to_clipboard(index=False, header=False)
    getLogger().info("Copied to clipboard: %s" % values)


def fetchPythonModules(paths):
    """
    A  dynamic module importer.
    Load Python module if is not already loaded from disk, return the module if is already imported
    :param paths: list. List of paths from where retrieve the Python files
    :return: A list of  loaded Python modules.
    """

    import sys
    import pkgutil as _pkgutil
    import traceback
    from ccpn.util.Logging import getLogger

    modules = []
    # change to strings - pathlib objects don't work
    paths = [str(path) for path in paths]

    for loader, name, isPpkg in _pkgutil.walk_packages(paths):
        if name:
            try:
                found = loader.find_module(name)
                if found:
                    module = sys.modules.get(name)
                    if module is not None:  # already loaded.
                        modules.append(module)
                        continue
                    else:
                        module = found.load_module(name)
                        modules.append(module)

            except Exception as err:
                traceback.print_tb(err.__traceback__)
                getLogger().warning('Error Loading Module %s. %s' % (name, str(err)))
    return modules


def consume(iterator, n=None):
    """Advance the iterator n-steps ahead. If n is None, consume entirely
    """
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)


#=========================================================================================
# main
#=========================================================================================

def main():
    # quick testing
    # make sure that zeroes are still included
    print(makeIterableList(((0, 1, 2, [[[], [None, 0]]], None, (0, {3, 4, 5, 5, None, 0}, 4, 5)))))

    for i in zipCycle(range(2), range(5), ['a', 'b', 'c'], []):
        print(i)


if __name__ == '__main__':
    main()
