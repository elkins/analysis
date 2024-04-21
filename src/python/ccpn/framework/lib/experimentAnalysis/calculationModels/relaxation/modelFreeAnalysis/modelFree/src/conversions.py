"""
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
__dateModified__ = "$dateModified: 2024-04-21 16:02:31 +0100 (Sun, April 21, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np


def teslaToFrequency(B, gamma):
    """
    Convert magnetic field strength from Tesla to frequency observable in a spectrometer.

    :param B: Magnetic field strength in Tesla.
    :param gamma: Gyromagnetic ratio of the particle.
    :return: Precession frequency in Hz.
    """
    return (gamma / (2 * np.pi)) * B

def frequencyToTesla(frequency, gamma):
    """
    Convert frequency observable in a spectrometer to magnetic field strength in Tesla.

    :param frequency: Precession frequency in Hz.
    :param gamma: Gyromagnetic ratio of the particle.
    :return: Magnetic field strength in Tesla.
    """
    return (2 * np.pi * frequency) / gamma


def _latex2matplotlib(latex):
    """
    Convert a LaTeX math expression to Matplotlib format.
    Returns:str: Matplotlib format of the LaTeX expression
    """
    return r"${}$".format(latex)


if __name__ == '__main__':
    # Gyromagnetic ratio for a proton
    gammaProton =  2.6752219 * 1e8  # rad s^-1 T^-1

    # Example conversion from Tesla to frequency
    magneticFieldStrength = 14.1  # Tesla
    frequency = teslaToFrequency(magneticFieldStrength, gammaProton)
    print("Frequency:", frequency*1e-6, "Hz")

    # Example conversion from frequency to Tesla
    frequency = 100e6  # 100 MHz
    magneticFieldStrength = frequencyToTesla(frequency, gammaProton)
    print("Magnetic Field Strength:", magneticFieldStrength, "Tesla")
