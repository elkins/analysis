"""
This module defines the various calculation/fitting functions for
Spectral density mapping  in the Series Analysis module.

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
__dateModified__ = "$dateModified: 2024-02-16 17:53:11 +0000 (Fri, February 16, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from numba import jit
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.util.decorators import requireDictKeys
from random import random, randint
from math import sqrt, exp
import pandas as pd
from ccpn.util.DataEnum import DataEnum




#### -----------   Lipari-Szabo (Model Free) analysis  ----------- #####

"""
    Calculate the spectral density J(ω) value(s) for the original Lipari-Szabo, 
    Model equations in Latex:
        J(w) = \frac{2}{5} \biggl[ \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]
        J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]
        J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} + \frac{ (1-S^2)\tau}{1+(\tau\omega)^2}\biggr]
        J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr] + R_{ex}
        J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} + \frac{ (1-S^2)\tau_i}{1+(\tau\omega)^2}\biggr]+ R_{ex}

"""


def _jwTerm(ci, ti, w):
    return np.sum(ci*ti / (1+(w* ti)**2))

def _calculateJwModel0(ti, ci, w, s2=None, te=None, rex=None):
    tTerm = _jwTerm(ci, ti, w)
    return 2/5 * (tTerm)

def _calculateJwModel1(ti, ci, w, s2, te=None, rex=None):
    tTerm = _jwTerm(ci, ti, w)
    return 2/5 * (s2*tTerm)

def _calculateJwModel2(ti, ci, w, s2, te, rex=None):
    tTerm = _jwTerm(ci, ti, w)
    s2Term = _jwTerm((1 - s2), te, w)
    return 2/5 * (s2 * tTerm + s2Term)

def _calculateJwModel3(ti, ci, w, s2=None, te=None, rex=None):
    m1 = _calculateJwModel1(ti, ci, w, s2)
    return m1 + rex

def _calculateJwModel4(ti, ci, w, s2=None, te=None, rex=None):
    m2 = _calculateJwModel1(ti, ci, w, s2)
    return m2 + rex




# -----------   Original Isotropic model  ----------- #

@jit(nopython=True)
def calculate_Jw_isotropic(S_square, tau_c, tau, omega):

    """
    Calculate the spectral density function J(omega) using the original isotropic model described by Lipari-Szabo.

    Reference:
    E.q 1 and 2.  Model-Free Approach to the Interpretation of Nuclear Magnetic Resonance Relaxation in Macromolecules. .1
                Theory and Range of Validity. Giovanni Lipari and Attila Szabo. Am. Chem. Soc. 1982, 104, 4546-4559
    or Eq 8 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
    Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    Latex:
        1)   J(\omega) = \frac{2}{5} \biggl[\frac { S^2 \tau_c} {1+(\tau_c\omega)^2} + \frac {(1-S^2)\tau} {1+(\omega\tau)^2} \biggr]
        2)   \tau^{-1} = \tau_c^{-1} + \tau_e^{-1}
    

    :param S_square:  (float): Generalised order parameter squared (S^2).
    :param tau_c:  (float): Correlation time (\tau_c).
    :param tau: (float): effective correlation time (\tau).
    :param omega:  (float): Value of omega (\omega).

    Returns:
        float: Spectral density function J(omega) calculated using the provided parameters.

    """
    tPrime = t = 1 / (1/tau_c + 1/tau)
    aTerm = _calculateJOmegaTerm(S_square, tau_c, omega)
    bTerm = _calculateJOmegaTerm((1-S_square), tPrime, omega)
    Jw =  (2/5) * (aTerm + bTerm)
    return Jw


# -----------   Axially Symmetric model  ----------- #

@jit(nopython=True)
def calculate_Jw_anisotropic(x,y,z, R1, R2, R3, omega):
    """
    Calculate the spectral density function J(omega) using the fully  anisotropic rotational Diffusion model

    Reference:
    E.q 11 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
    Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    Latex
        J(w) eq. 11 of reference
        J(\omega) = \frac{2}{5} \biggl[ C_1 \frac {\tau_1}
                                                    {1+\omega^2\tau_1^2} + C_2 \frac {\tau_2}
                                                    {1+\omega^2\tau_2^2} + C_3 \frac {\tau_3}
                                                    {1+\omega^2\tau_3^2} + C_+ \frac {\tau_+}
                                                    {1+\omega^2\tau_+^2} + C_- \frac {\tau_-}
                                                    {1+\omega^2\tau_-^2}
                                                \biggr]
        where C1 C2 C3 C+ C-:
         C_1 = 6y^2z^2
         C_2 = 6x^2z^2
         C_3 = 6x^2y^2
         C_+ = d + e
         C_- = d - e

        where d and e:
        d = \frac{1}{2} \biggl[ 3(x^4 + y^4 + z^4) - 1  \biggr]
        e = \frac{1}{6} \biggl[\delta_1 (3x^4 + 6y^2z^2 -1) + (3y^4 + 6x^2z^2 -1) + (3z^4 + 6x^2y^2 -1) \biggr]

        Deltas:
        \delta_x = \frac{(R_x - R)}{(R_2 - L^2)^{1/2}} x = 1, 2, 3 respectively
        R = \frac{1}{3}(R_1 + R_2 + R_3)
        L^2 = \frac{1}{3}(R_1R_2 + R_1R_3 + R_2R_3)

        The five correlation times characterising overall rotation are defined by:
        {\tau_1^{-1}} = 4R_1 + R_2 + R_3
        {\tau_2^{-1}} = R_1 + 4R_2 + R_3
        {\tau_3^{-1}} = R_1 + R_2 + 4R_3
        {\tau_+^{-1}} = 6\biggl[R+{(R^2 - L^2)^{1/2}}\biggr]
        {\tau_-^{-1}} = 6\biggl[R-{(R^2 - L^2)^{1/2}}\biggr]

    Returns:
        float: Spectral density function J(omega) calculated using the provided parameters.
    """

    # Calculate R and L^2
    R = (R1 + R2 + R3) / 3
    L2 = (R1 * R2 + R1 * R3 + R2 * R3) / 3

    # Calculate deltas
    delta1 = (R1 - R) / np.sqrt(R2 - L2)
    delta2 = (R2 - R) / np.sqrt(R1 - L2)
    delta3 = (R3 - R) / np.sqrt(R2 - L2)

    # Calculate C1, C2, C3
    C1 = 6 * y**2 * z**2
    C2 = 6 * x**2 * z**2
    C3 = 6 * x**2 * y**2

    # Calculate e and d
    _et1 = delta1 * (3*x**4 + 6*y**2*z**2 - 1)
    _et2 = delta2 * (3*y**4 + 6*x**2*z**2 - 1)
    _et3 = delta3 * (3*z**4 + 6*x**2*y**2 - 1)

    e = ( _et1 + _et2 + _et3) / 6
    d = 0.5 * (3 * (x**4 + y**4 + z**4) - 1)

    # Calculate C+, C-
    Cplus = d + e
    Cminus = d - e

    # Calculate correlation times
    tau1 = 1 / (4 * R1 + R2 + R3)
    tau2 = 1 / (R1 + 4 * R2 + R3)
    tau3 = 1 / (R1 + R2 + 4 * R3)
    tauPlus = 6 * (R + np.sqrt(R**2 - L2))
    tauMinus = 6 * (R - np.sqrt(R**2 - L2))

    # calculate the single terms for Jw
    c1Term = _calculateJOmegaTerm(C1, tau1, omega)
    c2Term = _calculateJOmegaTerm(C2, tau2, omega)
    c3Term = _calculateJOmegaTerm(C3, tau3, omega)
    cPlusTerm = _calculateJOmegaTerm(Cplus, tauPlus, omega)
    cMenusTerm = _calculateJOmegaTerm(Cminus, tauMinus, omega)

    Jw = (2 / 5) * (c1Term + c2Term + c3Term + cPlusTerm + cMenusTerm)

    return Jw

@jit(nopython=True)
def calculate_Jw_AxiallySymmetric(Dperpendicular, Dparallel, omega, theta):
    """
    Calculate the spectral density function J(omega) using the Axially Symmetric rotational Diffusion model

    Reference:
    E.q 12 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
    Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    Latex
        J(w) eq. 12 of reference
        J(\omega) = \frac{2}{5} \biggl[ A \frac {\tau_A} {1+\omega^2\tau_A^2} + B \frac {\tau_B} {1+\omega^2\tau_B^2} + C \frac {\tau_C} {1+\omega^2\tau_C^2} \biggr]

        Coefficients
        A = \frac{1}{4} \: (3 \cos^2 \theta -1)^2
        B = 3 \sin^2 \theta \cos^2 \theta
        C = \frac{3}{4} \: \sin^4 \theta

        TAUs
        {\tau_A} = \frac{1}{6R_2}
        {\tau_B} = \frac{1}{R_1 + 5R_2}
        {\tau_C} = \frac{1}{4R_1 + 2R_2}

        where theta is the angle between the N-H vector and the unique axis of the diffusion tensor

    Returns:
        float: Spectral density function J(omega) calculated using the provided parameters.
    """
    R1 = Dperpendicular
    R2 = Dparallel
    A = (1/4) * (3 * np.cos(theta)**2 - 1)**2
    B = 3 * np.sin(theta)**2 * np.cos(theta)**2
    C = (3/4) * np.sin(theta)**4

    tauA = 1 / (6 * R2)
    tauB = 1 / (R1 + 5 * R2)
    tauC = 1 / (4 * R1 + 2 * R2)

    aTerm = _calculateJOmegaTerm(A, tauA, omega)
    bTerm = _calculateJOmegaTerm(B, tauB, omega)
    cTerm = _calculateJOmegaTerm(C, tauC, omega)

    return (2/5) * (aTerm + bTerm + cTerm)

@jit(nopython=True)
def calculate_Jw_isotropicModelExtended(s2, rct, w, s2f=1.0, ictfast=0, ictslow=0 ):
    """
    Calculate the J(w) using the extended  Lipari-Szabo model
    for an isotropic system .
    eq 8.  Backbone dynamics of Barstar: A 15N NMR relaxation study.
    Udgaonkar et al 2000. Proteins: 41:460-474
    :param s2:  The generalised order parameter
    :param rct:  or tm, the global rotational correlation time
    :param ict:  or te, The effective internal correlation time
    :param w: omega w for a given nuclei (eg. wN)
    :param s2f: The generalised order parameter for the faster motion
    :param ictfast: The effective internal correlation time for the faster motion.
    :param ictslow: The effective internal correlation time for the slower motion.
    :return: j
    """
    if ictfast == 0.0:
        ict_fast_p = 0.0
    else:
        ict_fast_p = 1.0 / (1.0 / rct + 1.0 / ictfast)

    if ictslow == 0.0:
        ict_slow_p = 0.0
    else:
        ict_slow_p = 1.0 / (1.0 / rct + 1.0 / ictslow)

    # The spectral density value
    _1 = s2 * rct / (1.0 + (rct * w) ** 2)
    _2 = (1.0 - s2f) * ict_fast_p / (1.0 + (ict_fast_p * w) ** 2)
    _3 = (s2f - s2) * ict_slow_p / (1.0 + (ict_slow_p * w) ** 2)
    j = 0.4 * (_1 + _2 + _3)
    
    return j


def angle_between_vectors(vector1, vector2):
    """
    Calculate the angle (in radians) between two vectors.

    Args:
    - vector1: First vector as a numpy array.
    - vector2: Second vector as a numpy array.

    Returns:
    - angle: Angle between the vectors in radians.
    """
    # Calculate dot product and magnitudes
    dot_product = np.dot(vector1, vector2)
    magnitude1 = np.linalg.norm(vector1)
    magnitude2 = np.linalg.norm(vector2)

    # Calculate angle in radians
    angle = np.arccos(dot_product / (magnitude1 * magnitude2))

    return angle


def calculate_Dperpendicular_Dparallel(diffusion_tensor):
    # Compute eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(diffusion_tensor)

    # Sort eigenvalues in descending order
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]

    # Extract Dparallel (largest eigenvalue) and Dperpendicular (average of the two smaller eigenvalues)
    Dparallel = eigenvalues_sorted[0]
    Dperpendicular = np.mean(eigenvalues_sorted[1:])

    return Dperpendicular, Dparallel


def calculate_axially_symmetric_rotational_diffusion_tensor(R1, R2):
    """
        Calculate the principal components for an axially symmetric rotational diffusion tensor using the Lipari-Szabo model.

    :param R1: float,  Longitudinal relaxation rates (1/s)
    :param R2: float: Transverse relaxation rates (1/s)
    :return: tuple  - Dxx, Dyy, Dzz: Principal components of the rotational diffusion tensor (s^-1)
    """
    # Convert relaxation rates to rad/s
    omega_r1 = 2 * np.pi * R1
    omega_r2 = 2 * np.pi * R2
    # Calculate principal components of the rotational diffusion tensor using Lipari-Szabo model
    Dxx = (2/5) * (1/omega_r2)
    Dyy = (2/5) * (1/(0.5 * (1/omega_r1 + 5/omega_r2)))
    Dzz = (2/5) * (1/(0.25 * (1/omega_r1 + 2/omega_r2)))

    return Dxx, Dyy, Dzz


def calculate_nh_vector(residue):
    """
    Calculate the N-H vector for a residue.

    Parameters:
        residue (Bio.PDB.Residue): Residue object containing N and H atoms.

    Returns:
        numpy.array: Vector representing the N-H bond.
    """
    n_atom = residue['N']  # Assuming N atom is labeled as 'N' in the PDB file
    h_atom = residue['H']  # Assuming H atom is labeled as 'H' in the PDB file
    nh_vector = h_atom.get_vector() - n_atom.get_vector()
    return nh_vector.get_array()

def calculate_theta(nh_vector, diffusion_axis):
    """
    Calculate the angle theta between the N-H vector and the diffusion axis.

    Parameters:
        nh_vector (numpy.array): Vector representing the N-H bond.
        diffusion_axis (numpy.array): Vector representing the unique axis of the diffusion tensor.

    Returns:
        float: Angle theta in degrees.
    """
    nh_unit = nh_vector / np.linalg.norm(nh_vector)
    axis_unit = diffusion_axis / np.linalg.norm(diffusion_axis)
    cos_theta = np.dot(nh_unit, axis_unit)
    theta = np.arccos(cos_theta) * (180 / np.pi)  # Convert radians to degrees
    return theta


@jit(nopython = True)
def _calculateR1(A, jN, jHpN, jHmN, C):
    """
    Calculate the longitudinal relaxation rate (R1)
    :param A: d_factor
    :param jN:
    :param jHpN:
    :param jHmN:
    :param C: c_factor
    :return:  R1
    """
    r1 = A * ((3 * jN) + (6 * jHpN) + jHmN) + C * jN
    return r1

@jit(nopython = True)
def _calculateR2(A, C, j0, jH, jHmN, jHpN, jN, rex=0.0):
    """
    Calculate the transverse relaxation rate (R2)
    :param A: d_factor
    :param C: c_factor
    :param j0:
    :param jH:
    :param jHmN:
    :param jHpN:
    :param jN:
    :param rex:
    :return:  R2
    """
    r2 = 0.5 * A * ((4 * j0) + (3 * jN) + (6 * jHpN) + (6 * jH) + jHmN) + C * (2 * j0 / 3.0 + 0.5 * jN) + rex
    return r2

@jit(nopython = True)
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

##### calculate the Ssquared, Te and Exchange from T1 T2 NOE using the original model-free

def calculateSpectralDensityContourLines(spectrometerFrequency=600.130,
                                         lenNh=1.0150,   ict=50.0,  csaN=-160.0,
                                         minS2=0.3,  maxS2=1.0, stepS2=0.1,
                                         minRct=5.0,  maxRct=14.0, stepRct=1.0,
                                         rctScalingFactor =  1e-9,
                                         ictScalingFactor = 1e-12):
    """
    Calculate the contouring lines using the isotropic model for S2 and the rotational correlation Time  (rct).
    Used to overlay with the T1 vs T2  in a scatter  plot.
    :param spectrometerFrequency:  default 600.130
    :param lenNh: NH bond Length. default 1.0150 Armstrong
    :param ict: the internalCorrelationTime Te
    :param csaN: value of the axially symmetric chemical shift tensor for 15N. Default -160 ppm
    :param minS2: minimum S2 contours value
    :param maxS2: max S2 contours value
    :param stepS2: single step on the curve
    :param minRct: minimum rotational correlation Time  (rct) contours value
    :param maxRct: max rct contours value
    :param stepRct: single step on the curve
    :return: tuple  rctLines, s2Lines
    """
    rctLines = []
    s2Lines = []
    omegaH = sdl.calculateOmegaH(spectrometerFrequency, scalingFactor=1e6)  # Rad/s
    omegaN = sdl.calculateOmegaN(spectrometerFrequency, scalingFactor=1e6)
    csaN /= 1e6  # Was  ppm
    A = sdl.calculate_d_factor(lenNh)
    C = sdl.calculate_c_factor(omegaN, csaN)
    rct = maxRct
    ict *= ictScalingFactor  # Seconds

    while rct >= minRct:
        line = []
        s2 = 50
        while s2 > 0.1:
            rctB = rct * rctScalingFactor  # Seconds
            jH = calculate_Jw_isotropic(s2, rctB, ict, omegaH)
            jN = calculate_Jw_isotropic(s2, rctB, ict, omegaN)
            jHpN = calculate_Jw_isotropic(s2, rctB, ict, omegaH + omegaN)
            jHmN = calculate_Jw_isotropic(s2, rctB, ict, omegaH - omegaN)
            j0 = calculate_Jw_isotropic(s2, rctB, ict, 0.0)
            r1 = _calculateR1(A, jN, jHpN, jHmN, C)
            r2 = _calculateR2(A, C, j0, jH, jHmN, jHpN, jN)
            t1 = 1e3 / r1  # ms
            t2 = 1e3 / r2  # ms
            line.append([t1, t2])
            s2 /= 1.4
        rctLines.append([rct, line])
        rct -= stepRct

    s2 = maxS2
    while s2 >= minS2:
        line = []
        rct = 0.05
        while rct < 50:
            rctB = rct * rctScalingFactor  # Nanoseconds
            jH = calculate_Jw_isotropic(s2, rctB, ict, omegaH)
            jN = calculate_Jw_isotropic(s2, rctB, ict, omegaN)
            jHpN = calculate_Jw_isotropic(s2, rctB, ict, omegaH + omegaN)
            jHmN = calculate_Jw_isotropic(s2, rctB, ict, omegaH - omegaN)
            j0 = calculate_Jw_isotropic(s2, rctB, ict, 0.0)
            r1 = _calculateR1(A, jN, jHpN, jHmN, C)
            r2 = _calculateR2(A, C, j0, jH, jHmN, jHpN, jN)
            t1 = 1e3 / r1  # ms
            t2 = 1e3 / r2  # ms
            line.append([t1, t2])
            rct += 0.1
        s2Lines.append([s2, line])
        s2 -= stepS2

    return rctLines, s2Lines

def fitIsotropicModel(t1, t2, noe, sf=600, tmFix=None, teFix=None, s2Fix=None,
                      tmMin=1e-9, tmMax=100e-9, teMin=1e-12, teMax=1e-9,
                      csaN = 160 * 1e-6 , rNH = 1.015,
                      rexFix=None, rexMax=15.0, niter=10000):
    """
    Fit the IsotropicModel of Lipari Szabo using a genetic algorithm-like approach for optimization.
    - Calculation of various factors and initialization of parameters.
    - Creation of an ensemble of solutions with different combinations of initial parameter values.
    - Calculation of scores for each solution in the ensemble based on the fitness criteria.
    - Sorting and selecting the top 10 solutions with the lowest scores.
    - Iterative optimization using a mutation process to generate new solutions.
    - Updating the ensemble with the new solutions if they have better scores.
    - The optimization process continues for a specified number of iterations (niter).
    - The final result is a tuple containing the number of iterations performed and the top 10 solutions with their respective scores.

    """
    # rNH = 1.015
    # csaN = 160 * 1e-6  # 160 ppm
    omegaH = sdl.calculateOmegaH(sf, scalingFactor=1e6)
    omegaN = sdl.calculateOmegaN(sf, scalingFactor=1e6)
    gammaHN = constants.GAMMA_H /  constants.GAMMA_N

    A = sdl.calculate_d_factor(rNH)
    C = sdl.calculate_c_factor(omegaN, csaN)

    # Init params
    if s2Fix is None:
        s2Start = [x * 0.05 for x in range(1, 20)]
    else:
        s2Start = [s2Fix, ]

    if teFix is None:
        teStart = [x * 1e-12 for x in [10, 30, 70, 100, 300, 700, 1000]]
    else:
        teStart = [teFix, ]

    if tmFix is None:
        tmStart = [x * 1e-9 for x in range(1, 30)]
    else:
        tmStart = [tmFix, ]

    if rexFix is None:
        rexStart = [float(x) for x in range(int(rexMax))]
    else:
        rexStart = [rexFix, ]

    # Init ensemble of solutions
    ensemble = []
    for s2 in s2Start:
        for te in teStart:
            for tm in tmStart:
                for rex in rexStart:
                    ensemble.append((None, s2, te, tm, rex))

    # Init scores
    for k, (score, s2, te, tm, rex) in enumerate(ensemble):
        jH = calculate_Jw_isotropic(s2, tm, te, omegaH)
        jN = calculate_Jw_isotropic(s2, tm, te, omegaN)
        jHpN = calculate_Jw_isotropic(s2, tm, te, omegaH + omegaN)
        jHmN = calculate_Jw_isotropic(s2, tm, te, omegaH - omegaN)
        j0 = calculate_Jw_isotropic(s2, tm, te, 0.0)

        r1 = _calculateR1(A, jN, jHpN, jHmN, C )
        r2 = _calculateR2(A, C, j0, jH, jHmN, jHpN, jN, rex)

        t1p = 1.0 / r1
        t2p = 1.0 / r2

        d1 = (t1p - t1) / t1
        d2 = (t2p - t2) / t2

        score = (d1 * d1) + (d2 * d2)

        if noe is None:
            noep = 0.0

        else:
            noep = _calculateNOEp(A, gammaHN, t1, jHpN, jHmN)
            dn = (noep - noe) / 2.0
            score += (dn * dn)

        ensemble[k] = (score, s2, te, tm, rex, t1p, t2p, noep)

    ensemble.sort()
    ensemble = ensemble[:10]
    ensembleSize = len(ensemble)

    bestScore = 1e99

    for i in range(niter):

        f = i / float(niter)
        f = exp(-10.0 * f)
        # Mutate

        ensemble.sort()
        prevScore, s2, te, tm, rex, t1p, t2p, noep = ensemble[-1]  # Biggest is worst

        if ensemble[0][0] < 1e-10:
            break

        if not s2Fix:
            # d = ((random() + 0.618 - 1.0) * f) + 1.0
            d = ((random() - 0.382) * f) + 1.0
            s2 = max(0.0, min(1.0, s2 * d))

        if not tmFix:
            d = ((random() - 0.382) * f) + 1.0
            tm = max(tmMin, min(tmMax, tm * d))

        if not teFix:
            d = ((random() - 0.382) * f) + 1.0
            te = max(teMin, min(teMax, te * d))

        d = ((random() - 0.382) * f) + 1.0
        rex = max(0.0, min(rexMax, rex * d))

        jH = calculate_Jw_isotropic(s2, tm, te, omegaH)
        jN = calculate_Jw_isotropic(s2, tm, te, omegaN)
        jHpN = calculate_Jw_isotropic(s2, tm, te, omegaH + omegaN)
        jHmN = calculate_Jw_isotropic(s2, tm, te, omegaH - omegaN)
        j0 = calculate_Jw_isotropic(s2, tm, te, 0.0)

        r1 = _calculateR1(A, jN, jHpN, jHmN, C)
        r2 = _calculateR2(A, C, j0, jH, jHmN, jHpN, jN, rex)

        t1p = 1.0 / r1
        t2p = 1.0 / r2

        d1 = (t1p - t1) / t1
        d2 = (t2p - t2) / t2

        score = (d1 * d1) + (d2 * d2)
        if noe is None:
            noep = 0.0
        else:
            noep = _calculateNOEp(A, gammaHN, t1, jHpN, jHmN)
            dn = (noep - noe) / 2.0
            score += (dn * dn)

        ratio = exp(prevScore - score)

        if ratio > 1.0:  # random():
            ensemble[-1] = (score, s2, te, tm, rex, t1p, t2p, noep)
        else:
            k = randint(0, ensembleSize - 1)
            score, s2, te, tm, rex, t1p, t2p, noep = ensemble[k]
            ensemble[-1] = (score, s2, te, tm, rex, t1p, t2p, noep)

        if score < bestScore:
            bestScore = score

    return i, ensemble


def _fitIsotropicModelFromT1T2NOE(resultRSDM_dataframe, spectrometerFrequency=500.010, unit='s'):
    """
    :param resultRSDM_dataframe:
    :param spectrometerFrequency:
    :return:
    """
    T1 = np.array([])
    T2 = np.array([])
    NOE = np.array([])
    CODES = np.array([])

    resultDf = pd.DataFrame()
    initialDf = pd.DataFrame()

    if sv.T1 in resultRSDM_dataframe.columns:
        T1 = resultRSDM_dataframe[sv.T1].values
        T2 = resultRSDM_dataframe[sv.T2].values
        NOE = resultRSDM_dataframe[sv.HETNOE].values

    if sv.R1 in resultRSDM_dataframe.columns:
        R1 = resultRSDM_dataframe[sv.R1].values
        R2 = resultRSDM_dataframe[sv.R2].values
        NOE =  resultRSDM_dataframe[sv.HETNOE].values
        CODES = resultRSDM_dataframe[sv.NMRRESIDUECODE].values
        T1 = 1 / R1
        T2 = 1 / R2

    sf = spectrometerFrequency

    t1Unit = constants.MS_UNIT_MULTIPLIERS[unit]
    t2Unit = constants.MS_UNIT_MULTIPLIERS[unit]

    n = len(T1)
    n2 = n - 1
    jj = range(n)
    s2Best = [0.0] * n
    teBest = [0.0] * n
    rexBest = [0.0] * n

    t1s = [v for v in T1 if v]
    t2s = [v for v in T2 if v]
    noes = [v for v in NOE if v]

    m = len(t1s)

    t1 = sum(t1s) / float(m)
    t2 = sum(t2s) / float(m)
    noe = sum(noes) / float(m)

    t12 = [v / t2s[i] for i, v in enumerate(t1s) if v]
    t12m = sum(t12) / float(len(t12))
    deltas = [abs(v - t12m) / t12m for v in t12]
    w = [1.0 / (v * v) for v in deltas]

    t1 = sum([t1s[j] * w[j] for j in range(m)]) / sum(w)
    t2 = sum([t2s[j] * w[j] for j in range(m)]) / sum(w)

    if noes:
        noe = sum([noes[j] * w[j] for j in range(m)]) / sum(w)
    else:
        noe = None

    i, ensemble = fitIsotropicModel(t1, t2, noe, sf, tmFix=None, teFix=None, s2Fix=None,
                                    tmMin=1e-9, tmMax=100e-9, teMin=1e-12, teMax=1e-10,
                                    rexFix=0.0)
    ensemble.sort()
    score, s2, te0, tm0, rex, t1t, t2t, noet = ensemble[0]

    initialDf.loc['mean', sv.S2] = s2
    initialDf.loc['mean', sv.TE] = te0 * 1e12
    initialDf.loc['mean', sv.REX] = rex
    initialDf.loc['mean', sv.TM] = tm0 * 1e9
    initialDf.loc['mean', 'score'] = score

    # Do the individual
    for j in jj:
        t1 = T1[j]
        t2 = T2[j]
        noe = NOE[j]

        if t1 is None:
            continue

        seqCode = CODES[j]

        i, ensemble = fitIsotropicModel(t1, t2, noe, sf, tmFix=tm0, teFix=None, s2Fix=None,
                                        tmMin=tm0 * 0.1, tmMax=tm0 * 5, teMin=te0 / 100, teMax=te0 * 20,
                                        rexFix=0.0, rexMax=15.0)
        ensemble.sort()
        score, s2, te, tm, rex, t1t, t2t, noet = ensemble[0]

        if s2 > 0.995:
            i, ensemble = fitIsotropicModel(t1, t2, noe, sf, tmFix=tm0, teFix=None, s2Fix=None,
                                            teMin=te / 10, teMax=te * 10,
                                            rexFix=None, rexMax=15.0)
            ensemble.sort()
            score, s2, te, tm, rex, t1t, t2t, noet = ensemble[0]

        teBest[j] = te
        s2Best[j] = s2
        rexBest[j] = rex

        # data = (s2, te * 1e12, tm * 1e9, rex, t1, t1t, t2, t2t, noe or 0.0, noet, score, i)
        # print(seqCode,
        #       'S2: %5.3f Te: %5.1f Tm: %5.3f Rex: %5.3f T1: %5.3f %5.3f T2: %5.3f %5.3f NOE: %5.3f %5.3f %e %6d' % data)
        resultDf.loc[j, sv.NMRRESIDUECODE] = seqCode
        resultDf.loc[j, sv.S2] = s2
        resultDf.loc[j, sv.TE] = te * 1e12
        resultDf.loc[j, sv.REX] = rex
        resultDf.loc[j, sv.TM] = tm * 1e9
        resultDf.loc[j, 'iteration'] = i
        resultDf.loc[j, 'score'] = score

    return resultDf, initialDf #could put in the same df, with the initialDf as first row

