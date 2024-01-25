"""
This module defines the various calculation/fitting functions for
Spectral density mapping  in the Series Analysis module.

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-01-25 12:33:46 +0000 (Thu, January 25, 2024) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
from scipy import stats

############################################################
########## Reduced Spectral Density Mapping analysis   #############
############################################################

def calculateSigmaNOE(noe, r1, gx, gh):
    """Calculate the sigma NOE value.
    Eq. 16 Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474"""

    return (noe - 1.0) * r1 * (gx / gh)

def calculateJ0(noe, r1, r2, d, c, gx, gh):
    """Calculate J(0).
     Eq. 13 Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474
    """
    sigmaNOE = calculateSigmaNOE(noe, r1, gx, gh)
    j0 = 3/(2*(3*d + c)) * (-(1/2)*r1 + r2 - (3/5)*sigmaNOE)
    return j0

def calculateJWx(noe, r1, r2, d, c, gx, gh):
    """Calculate J(wx).
     Eq. 14 Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474
    """
    sigmaNOE = calculateSigmaNOE(noe, r1, gx, gh)
    jwx = 1.0 / (3.0 * d + c) * (r1 - (7/5) * sigmaNOE)
    return jwx

def calculateJWH(noe, r1, r2, d, c, gx, gh):
    """Calculate J(wH).
     Eq. 15 Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474
    """
    sigmaNOE = calculateSigmaNOE(noe, r1, gx, gh)
    jwh = sigmaNOE / (5.0*d)
    return jwh

def calculate_d_factor(rNH=1.0150,  cubicAngstromFactor=1e30):
    A = constants.REDUCED_PERM_VACUUM * constants.REDUCED_PLANK * constants.GAMMA_N * constants.GAMMA_H * cubicAngstromFactor
    A /= rNH ** 3.0
    A = A * A / 4.0
    return A

def calculate_c_factor(omegaN, csaN=-160.0):
    """ Calculate the c2 factor"""
    C = omegaN * omegaN * csaN * csaN
    C /= 3.0
    return C

def _polifitJs(j0, jw, order=1):
    """ Fit J0 and Jw(H or N) to a first order polynomial, Return the slope  and intercept  from the fit, and the new fitted Y  """
    coef = slope, intercept = np.polyfit(j0, jw, order)
    poly1d_fn_coefJ0JWH = np.poly1d(coef)
    fittedY = poly1d_fn_coefJ0JWH(j0)
    return slope, intercept, fittedY

def _calculateMolecularTumblingCorrelationTime(omega, alpha, beta):
    """
    solve the Polynomial Structure -> ax^3 + bx^2 + cx + d = 0
    from eq. 18  Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474
    :param omega: omegaN
    :param alpha: the slope for the fitting J0 vs JwN
    :param beta: the intercept for the fitting J0 vs JwN
    :return:
    """
    a = 2 * alpha * (omega**2)
    b = 5 * beta * (omega**2)
    c = 2 * (alpha-1)
    d = 5 * beta
    values = np.roots([a,b,c,d])
    return values

############################################################
############      Estimate S2 and Tc  analysis         #################
############################################################

def _filterLowNoeFromR1R2(r1, r2, noe, noeExclusionLimit=0.65):
    mask = np.argwhere(noe > noeExclusionLimit).flatten()
    r1 = r1[mask]
    r2 = r2[mask]
    return r1, r2

def estimateAverageS2(r1, r2, noe=None, noeExclusionLimit=0.65, method='median', proportiontocut=.1):
    """
    Estimate the average generalized order parameters Sav2
    from experimentally observed R1R2 using the trimmed mean method.
    If Noe are given, filter out residues with Noes < noeExclusionLimit
    - Trimmed mean usage from Eq 3. from  Effective Method for the Discrimination of
        Motional Anisotropy and Chemical Exchange Kneller et al. 2001.
        10.1021/ja017461k
    - median usage from Eq. 7: Fast evaluation of protein dynamics from deficient 15N relaxation data.
        Jaremko et all, 2018,  Journal of Biomolecular NMR (2018) 70:219–228
        https://doi.org/10.1007/s10858-018-0176-3

    s2Av = sqRoot [ func(r1*r2) / max(r1*r2)  ]
    :param r1: array of R1 values
    :param r2: array of R2 values
    :param noe: array of  NOE values
    :param proportiontocut:  float, cut value to calculate the trim average. default 0.1 for a 10%  left/right cut
    :param method: mean or median
    :return: float: S2
    """

    if noe is not None:
        r1, r2 = _filterLowNoeFromR1R2(r1, r2, noe, noeExclusionLimit)
    _pr = r1*r2
    if method=='median':
        p1 = np.median(_pr)
    else:
        p1 = stats.trim_mean(_pr,  proportiontocut=proportiontocut)
    _max = np.max(_pr)
    sAv = np.sqrt(p1/_max)
    return sAv

def estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency):
    """
    Ref:  Equation 6 from Fushman. Backbone dynamics of ribonuclease
    T1 and its complex with   2'GMP studied by
    two-dimensional heteronuclear N M R
    spectroscopy. Journal of Biomolecular NMR, 4 (1994) 61-78 .

    tc = [1 / (2omegaN) ]  * sqRoot[ (6*T1/ T2 ) -7 ]

    :param r1: array of R1 values
    :param r2: array of R2 values
    :return:  float.:  an estimation of the Overall Correlation Time Tc
    """
    t1 = 1/r1
    t2 = 1/r2
    omegaN = calculateOmegaN(spectrometerFrequency, scalingFactor=1e6)
    part1 =  1/(2*omegaN)
    part2 = np.sqrt( ((6*t1)/t2)- 7 )

    return  part1 * part2

def calculateOmegaH(spectrometerFrequency, scalingFactor=1e6):
    """
    :param spectrometerFrequency: float, the spectrometer Frequency in Mz
    :param scalingFactor:  float
    :return: float, OmegaH in Rad/s
    """
    return spectrometerFrequency * 2 * np.pi * scalingFactor  # Rad/s

def calculateOmegaN(spectrometerFrequency, scalingFactor=1e6):
    """
    :param spectrometerFrequency: float, the spectrometer Frequency in Mz
    :param scalingFactor:  float
    :return: float, OmegaN in Rad/s
    """
    omegaH = calculateOmegaH(spectrometerFrequency, scalingFactor)
    omegaN = omegaH * constants.GAMMA_N / constants.GAMMA_H
    return omegaN

def calculateOmegaC(spectrometerFrequency, scalingFactor=1e6):
    """
    :param spectrometerFrequency: float, the spectrometer Frequency in Mz
    :param scalingFactor:  float
    :return: float, OmegaC  (13C)  in Rad/s
    """
    omegaH = calculateOmegaH(spectrometerFrequency, scalingFactor)
    omegaC = omegaH * constants.GAMMA_C / constants.GAMMA_H
    return omegaC

## Exchange lib. Functions to be moded in the correct lib file.

def _calculateR20(d, c, J0, JWH, JWN):
    """
    d, c:  constants, float.
    J0, JWH, JWN,  arrays of floats
    Calculate the transverse relaxation rate R20 in the absence of chemical exchange processes
    from the  spectral  density  function properties.
    :return: r20 array
    """
    r20 = 1/8 * (d**2) * ((4*J0 + 3*JWN + (JWH -JWN) + 6*JWH + 6*(JWH +JWN)) + 1/6 * (c**2) *  (4* J0) + 3 * JWN)
    return r20

def _calculateR20viaETAxy(r2, ETAxy):
    """
    Here the R20 is estimated ETA xy and the averageR2/ETAxy ratio.
    Ref: eq. 5 from Evaluation of two simplified15N-NMR methods fordeterminingμs–ms dynamics of proteins.
    Mathias A. S. Hass and Jens J. Led. Magn. Reson. Chem.2006;44: 761 – 769. DOI: 10.1002/mrc.1845

    :return: r20 array
    """
    r20 = ETAxy * np.nanmean((r2/ETAxy))
    return r20

def _calculateR20viaR1(r2, r1):
    """
    Here the R20 is estimated ETA xy and the average R2/R1 ratio
    Ref: eq. 6 from Evaluation of two simplified15N-NMR methods fordeterminingμs–ms dynamics of proteins.
    Mathias A. S. Hass and Jens J. Led. Magn. Reson. Chem.2006;44: 761 – 769. DOI: 10.1002/mrc.1845
    :return: R20
    """
    r20 = r1 * np.nanmean((r2/r1))
    return r20

def _calculateMinimumRex(K, R, deltaK, deltaR):
    """

    :param k: float, either the trimmed average <R2/R1> or the trimmed average <R2/Nxy>
    :param R: 1D array, R1 rate or Nxy rate
    :param deltaK: standard deviation of the <R2/R1> or <R2/Nxy>
    :param deltaR: experimental uncertainty of R1 or Nxy
    :return: 1D array
    Use R1 and R2 when the system is rigid and tumble fast and nearly isotropically (in solution).
    Use R2/Nxy when the system is flexible or highly non-spherical.
    Ref: DOI:10.1002/mrc.1845. Hass 2006
    """
    a = np.power(deltaK / K , 2)
    b = np.power(deltaR / R , 2)
    minimumRex = K * R * (np.sqrt(a+b))
    return minimumRex

def _calculateNOEp(A, gammaHN, t1, jHpN, jHmN):
    """
    Calculate the steady-state NOE enhancement
    :param A: d_factor
    :param gammaHN:
    :param t1:
    :param jHpN:
    :param jHmN:
    :return:
    """
    return 1.0 + (A * gammaHN * t1 * ((6 * jHpN) - jHmN))

def _calculateJOmegas(t, w):
    """
    eq 10 from Krizova  et al, Journal of Biomolecular NMR 28: 369–384, 2004.  Temperature-dependent spectral density analysis ...
    :param t: total correlation time
    :param w: wH or wX
    :return: jw at a particular w
    """
    j0  = 0.4 * t
    j0 = t
    jw = j0 / ( 1 + 6.25 * (w * j0)**2)
    return jw

def calculateJW_at_Tc(spectrometerFrequency=600.130,
  minRct=0,  maxRct=30.0, stepRct=0.1, rctScalingFactor =  1e-9,  ):
    """
    Calculate JW at a range of rotational correlation times.
    :param spectrometerFrequency:  default 600.130
    :param minRct: minimum rotational correlation Time  (rct) contours value
    :param maxRct: max rct contours value
    :param stepRct: single step on the curve
    :return: tuple  jwHs, jwNs.
    Note is JWH  not JWH0.87
    """
    omegaH = calculateOmegaH(spectrometerFrequency, scalingFactor=1e6)  # Rad/s
    omegaN = calculateOmegaN(spectrometerFrequency, scalingFactor=1e6)
    rct = maxRct
    jwNs = []
    jwHs = []
    rcts = []
    while rct >= minRct:
        rctB = rct * rctScalingFactor  # Seconds
        jN = _calculateJOmegas(rctB, omegaN)
        jH = _calculateJOmegas(rctB, omegaH)
        jH087 = jH*0.87
        jwNs.append(jN)
        jwHs.append(jH087)
        rct -= stepRct
        rcts.append(rct)
    return np.array(rcts), np.array(jwHs),  np.array(jwNs)

