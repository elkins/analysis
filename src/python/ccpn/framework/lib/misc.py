"""Module Documentation here

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-04-15 15:38:25 +0100 (Mon, April 15, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import hashlib
import sys
import os
import json


def _codeFunc(version, valid, licenceType, programList, buildFor, licenceID, numSeats):
    m = hashlib.sha256()
    for value in version, valid, licenceType, programList, buildFor, licenceID, numSeats:
        m.update(bytes(str(value), 'utf-8'))

    return m.hexdigest()


def _decode(key, string):
    decoded_chars = []
    for i in range(len(string)):
        key_c = key[i % len(key)]
        decoded_c = chr(ord(string[i]) - ord(key_c) % 256)
        decoded_chars.append(decoded_c)
    decoded_string = "".join(decoded_chars)
    return decoded_string


def _codeMajorV(v1, v2):
    return type(v1) == str and type(v2) == str and v1 is not None and v2 is not None and v1.split('.')[0] == v2.split('.')[0]


def _check(key=None, doDecode=True):
    from ccpn.framework.Version import applicationVersion as appVersion
    applicationVersion = appVersion.withoutRelease()

    def message(*chars):
        return ''.join([c for c in map(chr, chars)])

    message1 = message(69, 82, 82, 79, 82, 58, 32, 110, 111, 32, 118, 97, 108, 105, 100,
                       32, 108, 105, 99, 101, 110, 99, 101, 32, 102, 105, 108, 101, 10, 65, 98, 111, 114,
                       116, 105, 110, 103, 32, 112, 114, 111, 103, 114, 97, 109, 10)
    message2 = message(69, 82, 82, 79, 82, 58, 32, 105, 110, 118, 97, 108, 105, 100, 32,
                       108, 105, 99, 101, 110, 99, 101, 32, 102, 111, 114, 32, 65, 110, 97, 108, 121, 115,
                       105, 115, 45, 86, 51, 32, 118, 101, 114, 115, 105, 111, 110, 32, 110, 117, 109, 98,
                       101, 114, 32, 34, 37, 115, 34, 10, 65, 98, 111, 114, 116, 105, 110, 103, 32, 112, 114,
                       111, 103, 114, 97, 109, 10)
    message3 = message(69, 82, 82, 79, 82, 58, 32, 65, 110, 97, 108, 121, 115, 105, 115,
                       45, 86, 51, 32, 118, 101, 114, 115, 105, 111, 110, 32, 110, 117, 109, 98, 101, 114,
                       32, 34, 37, 115, 34, 32, 104, 97, 115, 32, 101, 120, 112, 105, 114, 101, 100, 32, 111,
                       110, 32, 37, 115, 10, 65, 98, 111, 114, 116, 105, 110, 103, 32, 112, 114, 111, 103,
                       114, 97, 109, 10)
    message4 = message(80, 114, 111, 103, 114, 97, 109, 32, 108, 105, 99, 101, 110, 99,
                       101, 32, 40, 37, 115, 41, 32, 118, 97, 108, 105, 100, 32, 117, 110, 116, 105, 108,
                       32, 37, 115, 10)

    _l0 = message(98, 117, 105, 108, 100, 70, 111, 114)
    _l1 = message(108, 105, 99, 101, 110, 99, 101, 84, 121, 112, 101)
    _l2 = message(108, 105, 99, 101, 110, 99, 101, 73, 68)
    _l3 = message(99, 104, 101, 99, 107, 83, 117, 109)
    _v0 = message(95, 100, 97, 116, 97)
    _p0 = message(95, 117, 112, 100, 97, 116, 101)
    _p1 = message(95, 99, 104, 101, 99, 107, 75, 101, 121)
    _m0 = message(99, 99, 112, 110, 46, 117, 116, 105, 108, 46, 68, 97, 116, 97)

    _val = _p0 if _m0 in sys.modules else _p1

    if key is None:
        from ccpn.framework.PathsAndUrls import userPreferencesDirectory, ccpnConfigPath

        fname = message(108, 105, 99, 101, 110, 99, 101, 75, 101, 121, 46, 116, 120, 116)
        lfile = os.path.join(userPreferencesDirectory, fname)
        if not os.path.exists(lfile):
            lfile = os.path.join(ccpnConfigPath, fname)

        if not os.path.exists(lfile):
            sys.stderr.write(message1)
            sys.exit(1)

        with open(lfile, 'r', encoding='UTF-8') as fp:
            key = fp.readlines()[0]
            fp.close()

    try:
        keysum = ''
        if doDecode:
            h = hashlib.md5()
            h.update(key.encode('utf-8'))
            keysum = h.hexdigest()
            key = _decode('ccpnVersion3', key)
        ldict = json.loads(key)
        ldict[_l3] = keysum
    except Exception as es:
        sys.stderr.write(message2 % (applicationVersion))
        sys.exit(1)

    if 'code' not in ldict or 'version' not in ldict or 'valid' not in ldict or \
            _l1 not in ldict or 'programList' not in ldict or \
            _l0 not in ldict or _l2 not in ldict or 'numSeats' not in ldict:
        sys.stderr.write(message2 % (applicationVersion))
        sys.exit(1)

    if not _codeMajorV(applicationVersion, ldict['version']):
        sys.stderr.write(message2 % (applicationVersion))
        sys.exit(1)

    if ldict['code'] != _codeFunc(ldict['version'], ldict['valid'], ldict[_l1],
                                  ldict['programList'], ldict[_l0],
                                  ldict[_l2], ldict['numSeats']):
        sys.stderr.write(message2 % (applicationVersion))
        sys.exit(1)

    from ccpn.util import Data
    setattr(Data, _v0, _val)

    for val in (_l0, _l1, _l2, _l3):
        setattr(Data, val, ldict[val])

    if _val == _p0:
        return True

    from ccpn.util.Time import Time, now, year

    if ldict[_l1] == 'developer':
        sys.stderr.write(message4 % (ldict[_l1], now() + year))
        return True

    valid = Time(ldict['valid'])
    if not now() < valid:
        sys.stderr.write(message3 % (applicationVersion, valid))
        sys.exit(1)
    else:
        sys.stderr.write(message4 % (ldict[_l1], valid))

    return True

# TODO. This is checked every time we run a script which imports ccpn modules, which is ok  if is the first time but not ok for multiple instances especially when we are in multiprocessing.
_checked = _check(None, doDecode=True)
