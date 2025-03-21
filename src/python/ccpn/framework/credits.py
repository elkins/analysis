"""
This module defines the code for creating the credits
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-03-21 15:37:05 +0000 (Fri, March 21, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import contextlib


authors = ('Ed Brooksbank', 'Victoria A Higman', 'Luca Mureddu', 'Eliza Płoskoń',
           'Timothy J Ragan', 'Brian O Smith', 'Daniel Thompson', 'Gary S Thompson', 'Geerten W Vuister')


def _strList(inlist: tuple, maxlen: int = 80) -> list:
    outstr = ''
    # skip = False  # print commas and ampersand
    lencount = maxlen

    nameList = sorted(inlist, key=lambda name: name.split()[-1])

    outList = []

    for cName in nameList[:-1]:
        skip = False
        if len(outstr + cName) > lencount and cName not in nameList[-2:]:
            outstr += f'{cName}, '
            outList.append(outstr)
            lencount += maxlen
            skip = True
            outstr = ''
        elif cName not in nameList[-2:]:
            outstr += f'{cName}, '
        else:
            outstr += cName

    outstr = nameList[0] if len(nameList) == 1 else f'{outstr} & {nameList[-1]}'
    if outstr:
        outList.append(outstr)

    return outList


def printCreditsText(fp, programName, version):
    """Initial text to terminal """
    from ccpn.framework.PathsAndUrls import ccpnLicenceUrl

    lines = [f"{programName}, "
             f"version: {version}",
             "",
             f"{__copyright__}",
             "",
             f"CCPN licence. See {ccpnLicenceUrl}. Not to be distributed without prior consent!",
             ""]

    # lines.append("%s" % __copyright__[0:__copyright__.index('-')] + '- 2016')

    with contextlib.suppress(Exception):
        prefix = "Active Developers:   "
        if isinstance(authors, str):
            lines.append(f"{prefix}{authors}")
        elif isinstance(authors, (list, tuple)):
            authorList = _strList(authors, maxlen=60)
            lines.append(f"{prefix}{authorList[0]}")
            lines.extend(f"{' ' * len(prefix)}{crLine}" for crLine in authorList[1:])
        lines.append(" " * len(prefix) + "See https://ccpn.ac.uk/about/people/ for more information.")

    lines.append("")

    with contextlib.suppress(Exception):
        if isinstance(__reference__, str):
            lines.append(f"Please cite:  {__reference__}")
        elif isinstance(__reference__, tuple):
            lines.append(f"Please cite:  {__reference__[0]}")
            lines.extend(f"              {refLine}" for refLine in __reference__[1:])

    lines.extend(("",
                  "DISCLAIMER:   This program is offered 'as-is'. Under no circumstances will the authors, CCPN,",
                  "              the Department of Molecular and Cell Biology, or the University of Leicester be",
                  "              liable of any damage, loss of data, loss of revenue or any other undesired",
                  "              consequences originating from the usage of this software."))

    # print with aligning '|'s
    maxlen = max(map(len, lines))
    if (lang := os.getenv('LANG')) and 'utf' in lang.lower():
        tl, tt, tr = '\u2552', '\u2550', '\u2555'
        ll, rr = '\u2502', '\u2502'
        bl, bb, br = '\u2558', '\u2550', '\u255b'
    else:
        tl, tt, tr = '=', '=', '='
        ll, rr = '|', '|'
        bl, bb, br = '=', '=', '='
    fp.write(f'\n{tl}{tt * (maxlen + 6)}{tr}\n')
    for line in lines:
        fp.write(f'{ll}   {line:<{maxlen}}   {rr}\n')
    fp.write(f'{bl}{bb * (maxlen + 6)}{br}\n')
