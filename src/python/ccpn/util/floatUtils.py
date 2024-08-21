"""
fExp and fMan are the functions giving the exponent and mantissa of the decimal floating point representation of a float then we'd expect the following statements to all return true:

fExp(154.3) == 2.0
fMan(154.3) == 1.543
fExp(-1000) == 3
fMan(-1000) == -1

fRepr(number) -> (mantissa, exponent)

fRound(number) -> round to nearest base-10 value;
fRound(154.3) == 200

Solution taken from: https://stackoverflow.com/questions/45332056/decompose-a-float-into-mantissa-and-exponent-in-base-10-without-strings
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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-21 13:51:14 +0100 (Wed, August 21, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from decimal import Decimal
import math


def fExp(number) -> int:
    (sign, digits, exponent) = Decimal(number).as_tuple()
    return int(len(digits) + exponent - 1)


def fMan(number) -> float:
    return float(Decimal(number).scaleb(-fExp(number)).normalize())


def fRepr(number) -> tuple:
    """base10 equivalent of math.frepr"""
    return (fMan(number), fExp(number))


def fRound(number) -> float:
    """round to nearest base-10 value"""
    f, e = fRepr(number)
    f = float(int(f + 0.5))
    return f * math.pow(10.0, e)

def numZeros(decimal):
    """ For floats less the 1, Count the number of zeros after the . """
    return math.inf if decimal == 0 else -math.floor(math.log10(abs(decimal))) - 1

def formatValue(value, precision=3):
    """
    Format a numerical value based on its magnitude.
    If the value is within the range [1e-3, 1e3), it is formatted as a standard floating-point number with a specified precision.
    If the value is outside this range, it is formatted in scientific notation with the same precision.
    :param value:  float. The numerical value to format.
    :param precision:   int, optional. The number of decimal places to use in the formatted output. The default is 3.
    :return:  str. The formatted value as a string.
    """
    import numpy as np
    if 1e-3 <= value < 1e3:
        return f"{value:.{precision}f}"
    else:
        return np.format_float_scientific(value, precision=precision, trim='-')
