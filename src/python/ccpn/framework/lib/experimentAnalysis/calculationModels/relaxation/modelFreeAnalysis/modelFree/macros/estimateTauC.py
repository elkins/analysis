import numpy as np
import pandas as pd


# Define the gyromagnetic ratios for hydrogen and nitrogen
class constants:
    GAMMA_H = 267.513e6  # Gyromagnetic ratio for Hydrogen in rad T^-1 s^-1
    GAMMA_N = -27.116e6  # Gyromagnetic ratio for Nitrogen-15 in rad T^-1 s^-1


def calculateOmegaH(spectrometerFrequency, scalingFactor=1e6):
    """
    Calculate the Larmor frequency for Hydrogen in rad/s.

    :param spectrometerFrequency: float, the spectrometer frequency in MHz
    :param scalingFactor: float, default is 1e6 to convert MHz to Hz
    :return: float, OmegaH in rad/s
    """
    return spectrometerFrequency * 2 * np.pi * scalingFactor  # Rad/s


def calculateOmegaN(spectrometerFrequency, scalingFactor=1e6):
    """
    Calculate the Larmor frequency for Nitrogen in rad/s.

    :param spectrometerFrequency: float, the spectrometer frequency in MHz
    :param scalingFactor: float, default is 1e6 to convert MHz to Hz
    :return: float, OmegaN in rad/s
    """
    omegaH = calculateOmegaH(spectrometerFrequency, scalingFactor)
    omegaN = abs(omegaH * constants.GAMMA_N / constants.GAMMA_H)
    return omegaN


def estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency):
    """
    Estimate the overall rotational correlation time (tc) from R1 and R2 relaxation rates.

    Reference: Equation 6 from Fushman et al. (1994)
    "Backbone dynamics of ribonuclease T1 and its complex with 2'GMP studied by
    two-dimensional heteronuclear NMR spectroscopy". Journal of Biomolecular NMR, 4 (1994) 61-78.

    tc = [1 / (2 * omegaN)] * sqrt[(6 * R2 / R1) - 7]

    :param r1: array of R1 values
    :param r2: array of R2 values
    :param spectrometerFrequency: float, the spectrometer frequency in MHz
    :return: float, an estimation of the overall correlation time (tc)
    """

    # Calculate the Larmor frequency for Nitrogen in rad/s
    omegaN = calculateOmegaN(spectrometerFrequency)

    # Calculate parts of the correlation time formula
    part1 = 1 / (2 * omegaN)
    part2 = np.sqrt((6 * r2 / r1) - 7)

    # Calculate the overall correlation time (tau_c)
    tau_c = part1 * part2

    return tau_c


# Example usage

import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl


gb1p = '/Users/luca/Projects/AnalysisV3/src/python/ccpn/framework/lib/experimentAnalysis/calculationModels/relaxation/modelFreeAnalysis/examples/5/inputs/GB1_rates.xlsx'

taucFields = []
taucFields2 = []
sheets = pd.read_excel(gb1p, sheet_name=None)
for sheet_name, df in sheets.items():
    r1 = df['R1'].values
    r2 = df['R2'].values
    # Calculate the overall correlation time
    localTcs = estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency=float(sheet_name))
    fieldTc = np.median(localTcs)
    taucFields.append(fieldTc)
    localTcs2 = sdl.estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency=float(sheet_name))
    fieldTc2 = np.median(localTcs2)
    taucFields2.append(fieldTc2)
    s2 = sdl.estimateAverageS2(r1, r2, noe=None, noeExclusionLimit=0.65, method='median', proportiontocut=.1)
    print(s2)

tc = np.mean(taucFields)
print("Estimated Overall Correlation Time (tau_c):", tc)
tc2 = np.mean(taucFields2)
print("Estimated Overall Correlation Time (tau_c) 2:", tc2)
