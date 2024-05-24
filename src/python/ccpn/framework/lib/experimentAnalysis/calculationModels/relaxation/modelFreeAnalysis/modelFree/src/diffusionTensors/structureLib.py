"""
This module contains Structure-related library functions.

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
__dateModified__ = "$dateModified: 2024-05-24 16:14:10 +0100 (Fri, May 24, 2024) $"
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
import math
import warnings
from collections import defaultdict
from ccpn.util.Path import aPath
from Bio.PDB import PDBParser
from Bio.PDB.vectors import Vector

def getStructure(file):
    """Get the Structure object from a file. Only available for PDB extensions"""
    structure = None
    path = aPath(file)
    if path.is_file() and len(path.suffixes) >= 1 and path.suffixes[-1] == '.pdb':
        parser = PDBParser()
        structure = parser.get_structure("protein", str(path))
    return structure

def _getCoords(structure):
    coords = np.array([atom.get_coord() for atom in structure.get_atoms()])
    return coords

def _getCOM(coords):
    """
    Get the center of mass for coords
    :param coords:
    :return: float. the COM
    """
    return np.mean(coords, axis=0)

def _getSquaredDistances(coords, com):
    """
    Calculate the squared distances of the coords from the center of mass
    :param coords:
    :param com:
    :return: float the squared distances
    """
    return np.sum((coords - com)**2, axis=1)

def _getGyrationRadius(squaredDistances):
    """
    Calculate the radius of gyration for a structure
    :param squaredDistances:
    :return: float. the Gyration Radius
    """
    gyrationRadius = np.sqrt(np.mean(squaredDistances))
    return gyrationRadius

def _calculateGyrationTensor(coords, com):
    """
    :param coords: array, all structure coord
    :param com: foat,  the center of mass
    :return: array, of shape 3X3.
    """
    tensor = np.mean(np.einsum('ij,ik->ijk', coords - com, coords - com), axis=0)
    return tensor

def _getEigenvalues(gyrationRadiusTensor):
    """
    Get the eigenvalues from a gyration Radius Tensor
    :param gyrationRadiusTensor: array, 3X3
    :return: 1D array. eigenvalues
    """
    eigenvalues, eigenvectors = np.linalg.eigh(gyrationRadiusTensor)
    return eigenvalues

def _getEigenvectors(gyrationRadiusTensor):
    """
    Get the eigenvectors from a gyration Radius Tensor
    :param gyrationRadiusTensor: array, 3X3
    :return: nD array. eigenvectors, same shape of the tensor, (3X3 for the structure)
    """
    eigenvalues, eigenvectors = np.linalg.eigh(gyrationRadiusTensor)
    return eigenvectors

def _isStructureIsotropic(eigenvalues, tolerance=.2):
    """ Check if the structure is approximately spherical.
    For a system to be approximately spherical, the eigenvalues of the RoG tensor should ideally be similar, but not necessarily identical (a perfect spherical structure is unlikely to exist).
    If the ratios are close to 1:1:1, within a tolerance of 20%, the system is approximately spherical, indicating that the mass is distributed relatively evenly in all directions.
    An example of this system is the M FERRITIN. Pdb: 1MFR
    """
    ratios = eigenvalues / eigenvalues.mean()
    isApproxSpherical = np.allclose(ratios,  np.mean(ratios), rtol=tolerance)
    return isApproxSpherical

def _isStructureAxiallySymmetric(eigenvalues, tolerance=.2):
    """ Check if the structure is approximately Axially Symmetric.
    For a system to be approximately Axially Symmetric, 2 of the eigenvalues of the RoG tensor should ideally be similar, but not necessarily identical.
    If 2 out of 3 ratios are close  within a tolerance of 20%, the system is approximately Axially Symmetric, indicating that the mass is elongated in one direction.
    An example of this system is GB1, or  ARC REPRESSOR-OPERATOR, pdb: 1PAR.
    """
    sortedIx = np.argsort(eigenvalues)
    sortedEigenvalues = eigenvalues[sortedIx]
    isApproxAxiallySymmetric = np.allclose(sortedEigenvalues[:2], sortedEigenvalues[:2].mean(), rtol=tolerance)  # Tolerance of 20% for axially symmetric

    return isApproxAxiallySymmetric

def _isStructureFullyAnisotropic(eigenvalues, tolerance=.2):
    """ Check if the structure is FullyAnisotropic system.
    Its mass distribution is not symmetric in any direction.
    """
    isAnisotropic = not _isStructureAxiallySymmetric(eigenvalues, tolerance)
    return isAnisotropic

def _determineEllipsoidShape(eigenvalues):
    """Determine is If the Ellipsoid is rotated about its major axis, aka prolate, (like a rugby ball or an egg);
     or if it is rotated about its minor axis, aka oblate, (flattened like a plate or a coin) """
    # Sort eigenvalues to identify the symmetry axis

    D_perpendicular, D_parallel = _calculateDperpendicularDparallelEigenvalues(eigenvalues)
    if D_parallel > D_perpendicular:
        return "Prolate"
    elif D_parallel < D_perpendicular:
        return "Oblate"
    else:
        return ""

def _getPrincipalAxisDiffusion(eigenvalues, eigenvectors):
    principalAxis = eigenvectors[:, np.argmax(eigenvalues)]
    return Vector(principalAxis)


def _calculateDperpendicularDparallelEigenvalues(eigenvalues):
    """
    Calculate the parallel and perpendicular elements from the eigenvalues
    :param eigenvalues: 1D array
    :return: tuple, Dperpendicular, Dparallel
    """
    # Sort eigenvalues in descending order
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]
    # Extract Dparallel (largest eigenvalue) and Dperpendicular (average of the two smaller eigenvalues)
    Dparallel = eigenvalues_sorted[0]
    Dperpendicular = np.mean(eigenvalues_sorted[1:])

    return Dperpendicular, Dparallel


def _calculate_NH_vectors(structure):
    """Given a structure, calculate the NH vector for each residue in each chain and model (could be an ensemble). """
    NH_vectorsByResidue = defaultdict(list)
    for model in structure:
        for chain in model:
            for residue in chain:
                try:
                    N_atom = residue['N']
                    H_atom = residue['H']
                    N_coord = Vector(N_atom.get_coord())
                    H_coord = Vector(H_atom.get_coord())
                    NH_Vector = H_coord - N_coord
                    residueId = residue.get_id()[1] #get only the residue number
                    NH_vectorsByResidue[residueId].append(NH_Vector)
                except KeyError:
                    warnings.warn(f'Error in {residue.get_id()} while calculating the NH vector. Could be caused by missing atoms information for the residue.')
                    continue

    return NH_vectorsByResidue


def _calculateNHAngle(nhVector, principalAxis):
    """
    Calculate the angle between a vector and a principal axis.
    :param nhVector:
    :param principalAxis:
    :return:  The angle in degrees between the nhVector and the principalAxis.
    """
    nhVector = nhVector.normalized()
    principalAxis = principalAxis.normalized()
    cosTheta = np.dot(nhVector, principalAxis)
    cosTheta = np.clip(cosTheta, -1.0, 1.0)  # Ensure value is in valid range for arccos
    theta = np.arccos(cosTheta)
    return np.degrees(theta)

def _calculateAnglesByVectors(vectorsDict, principalAxis):
    """
    Calculate the angle between the NH vector and the principal axis. Note Could be an ensemble, in that case we take the mean.
    :param vectorsDict: {residue_id : [NH_vector, ...] }
    :return:  dict.  {residue_id : (mean angle in degree, std) }
    """
    NH_anglesByResidue = {}

    for residue_id, vectors in vectorsDict.items():
        angles = []
        for vector in vectors:
            angle = _calculateNHAngle(vector, principalAxis)
            angles.append(angle)
        _mean, _std = np.mean(angles), np.std(angles, ddof=1) #for a single structure (not an ensemble), the std is nan.
        NH_anglesByResidue[residue_id] = (_mean, _std)
    return NH_anglesByResidue




## Quick testing
if __name__ == "__main__":
    gb1 = '/Users/luca/Documents/NMR-Data/Relaxation/Fred_Musket/GB1/FWM_analysis_gb1_relax/gb1.pdb'
    ferritin_Spherical = '/Users/luca/Downloads/1mfr.pdb'
    t4_fullyAnisotropic = '/Users/luca/Downloads/8dwj_T4-primosome_alone.pdb'
    arc_axially = '/Users/luca/Downloads/1par_arc_s.pdb'
    il17f = '/Users/luca/Downloads/6hgo_s.pdb'
    ensemble = '/Users/luca/Downloads/6qf8_ensemble.pdb'
    ensemble_pep = '/Users/luca/Downloads/2juy.pdb'

    parser = PDBParser(QUIET=True,)
    structure = parser.get_structure("protein", str(gb1))
   # structure = getStructure(ensemble)

    coords = _getCoords(structure)
    com = _getCOM(coords)
    dist2 = _getSquaredDistances(coords,com)
    gyrationRadius = _getGyrationRadius(dist2)
    tensor = _calculateGyrationTensor(coords, com)
    eigenvalues = _getEigenvalues(tensor)
    eigenvectors = _getEigenvectors(tensor)
    structureIsotropic = _isStructureIsotropic(eigenvalues)
    structureAxiallySymmetric = _isStructureAxiallySymmetric(eigenvalues)
    structureFullyAnisotropic = _isStructureFullyAnisotropic(eigenvalues)

    print("Radius of Gyration:", gyrationRadius)
    print("eigenvalues:", eigenvalues)
    print("eigenvectors:\n", eigenvectors)
    print(f"The RoG tensor is approx_isotropic?  {structureIsotropic}")
    print(f"The RoG tensor is approximately axially symmetric?  {structureAxiallySymmetric}")
    print(f"The RoG tensor is Fully Anisotropic?  {structureFullyAnisotropic}")
    if _isStructureAxiallySymmetric:
        shape = _determineEllipsoidShape(eigenvalues)
        print(f"The overall shape is  {shape}")

    # Example usage:
    print('=='*10, 'ANGLES: ')
    Dperpendicular, Dparallel = _calculateDperpendicularDparallelEigenvalues(eigenvalues)
    print(f"_|_E_perpendicular:  {Dperpendicular};  // E_parallel : {Dparallel}")

    pa =  _getPrincipalAxisDiffusion(eigenvalues, eigenvectors)
    vbyRes = _calculate_NH_vectors(structure)
    anglesByRes = _calculateAnglesByVectors(vbyRes, pa)
    for residue_id, angleValues in anglesByRes.items():
        angle, std = angleValues
        print(f'Residue {residue_id} angle: {angle}')


    # GB1 example
    print('====== GB1 Demo ========')
    Gb1TcIso = 4.40 #ns
    Diso = 1/(6*Gb1TcIso)
    Dperp = 0.75*Diso
    Dpar = 1.25*Diso
    ta = 1/(6*Dpar)
    tb = 1/(Dperp + 5*Dpar)
    tc = 1/(4*Dperp + 2*Dpar)
    print(f'Gb1_Tauc_Iso: {Gb1TcIso} ns')
    print(f'Gb1_Diso: {Diso} 1/ns')
    print(f'Gb1_Dperp: {Dperp} 1/ns')
    print(f'Gb1_Dpar: {Dpar} 1/ns')
    print(f'Gb1_TauA: {round(ta,3)} ns')
    print(f'Gb1_TauB: {round(tb,3)} ns')
    print(f'Gb1_TauC: {round(tc,3)} ns')
