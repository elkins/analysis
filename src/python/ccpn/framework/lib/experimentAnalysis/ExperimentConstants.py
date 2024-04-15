"""
This module defines the various constants used in the ExperimentAnalysis models

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
__dateModified__ = "$dateModified: 2024-04-15 15:38:24 +0100 (Mon, April 15, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from math import pi

# ------------- Spectral density mapping functions  ------------- #

MS_UNIT_MULTIPLIERS = {
                        's': 1000.0,
                       'ms': 1.0,
                       'us': 1e-3,
                       'ns': 1e-6,
                        }

PlanckConstant                = 6.62606876 * 1e-34
DiracConstant                  = PlanckConstant / (2.0 * pi)
MagneticConstant            = 4.0 * pi * 1e-7                      # permeability of vacuum (free space)
BoltzmannConstant          = 1.380650424 * 1e-23        #  in SI units of J.K^-1

## Gyromagetic Ratio (MHz/T) to be moved to the IsotopeRecords Json?
GMR_1H           =  42.577
GMR_1H_H2O  =  42.576
GMR_2H           =  6.536
GMR_3H           =  45.415
GMR_3He          =  -32.434
GMR_7Li       =  16.546
GMR_13C     = 10.708
GMR_14N     =  3.077
GMR_15N     =  -4.316
GMR_17O     =  -5.772
GMR_19F     =  40.078
GMR_23Na   = 11.262
GMR_27Al    = 11.103
GMR_29Si    =  -8.465
GMR_31P     =  17.235


## https://en.wikipedia.org/wiki/Gyromagnetic_ratio
REDUCED_PLANK = 1.05457162853e-34
GAMMA_H = 42.576 * 1e6 * 2 * pi             # Hz/T
GAMMA_N = -4.3156 * 1e6 * 2 * pi            # Hz/T
GAMMA_C =  6.728 * 1e7                          # Hz/T
REDUCED_PERM_VACUUM = 1e-7
GAMMA_HN = GAMMA_H / GAMMA_N

## Magnetogyric Ratio ->  Ɣ in rad s^-1*T^-1
HgyromagneticRatio = 26.7522212 * 1e7   # Ɣ in rad s^-1*T^-1
N15gyromagneticRatio = -2.7126 * 1e7
C13gyromagneticRatio = 6.728 * 1e7

## Chemical shift anisotropy (CSA) and bond lengths.
N15_CSA = -172 * 1e-6
NH_BOND_LENGTH = 1.02 * 1e-10

