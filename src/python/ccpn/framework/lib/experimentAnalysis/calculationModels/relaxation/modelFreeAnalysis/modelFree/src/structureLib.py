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
__dateModified__ = "$dateModified: 2024-05-20 09:41:35 +0100 (Mon, May 20, 2024) $"
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
from ccpn.util.Path import aPath
from Bio.PDB import PDBParser

def getStructure(file):
    """Get the Structure object from a file. Only available for PDB extensions"""
    structure = None
    path = aPath(file)
    if path.is_file() and len(path.suffixes) >= 1 and path.suffixes[-1] == '.pdb':
        parser = PDBParser()
        structure = parser.get_structure("protein", str(path))
    return structure

def getCoords(structure):
    coords = np.array([atom.get_coord() for atom in structure.get_atoms()])
    return coords

def getCOM(coords):
    """
    Get the center of mass for coords
    :param coords:
    :return: float. the COM
    """
    return np.mean(coords, axis=0)

def getSquaredDistances(coords, com):
    """
    Calculate the squared distances of the coords from the center of mass
    :param coords:
    :param com:
    :return: float the squared distances
    """
    return np.sum((coords - com)**2, axis=1)

def getGyrationRadius(squaredDistances):
    """
    Calculate the radius of gyration for a structure
    :param squaredDistances:
    :return: float. the Gyration Radius
    """
    gyrationRadius = np.sqrt(np.mean(squaredDistances))
    return gyrationRadius

def calculateGyrationRadiusTensor(coords, com):
    """
    :param coords: array, all structure coord
    :param com: foat,  the center of mass
    :return: array, of shape 3X3.
    """
    tensor = np.mean(np.einsum('ij,ik->ijk', coords - com, coords - com), axis=0)
    return tensor

def getEigenvalues(gyrationRadiusTensor):
    """
    Get the eigenvalues from a gyration Radius Tensor
    :param gyrationRadiusTensor: array, 3X3
    :return: 1D array. eigenvalues
    """
    eigenvalues, eigenvectors = np.linalg.eigh(gyrationRadiusTensor)
    return eigenvalues

def getEigenvectors(gyrationRadiusTensor):
    """
    Get the eigenvectors from a gyration Radius Tensor
    :param gyrationRadiusTensor: array, 3X3
    :return: nD array. eigenvectors, same shape of the tensor, (3X3 for the structure)
    """
    eigenvalues, eigenvectors = np.linalg.eigh(gyrationRadiusTensor)
    return eigenvectors

def isStructureIsotropic(eigenvalues, tolerance=.2):
    """ Check if the structure is approximately spherical.
    For a system to be approximately spherical, the eigenvalues of the RoG tensor should ideally be similar, but not necessarily identical (a perfect spherical structure is unlikely to exist).
    If the ratios are close to 1:1:1, within a tolerance of 20%, the system is approximately spherical, indicating that the mass is distributed relatively evenly in all directions.
    An example of this system is the M FERRITIN. Pdb: 1MFR
    """
    ratios = eigenvalues / eigenvalues.mean()
    isApproxSpherical = np.allclose(ratios,  np.mean(ratios), rtol=tolerance)
    return isApproxSpherical

def isStructureAxiallySymmetric(eigenvalues, tolerance=.2):
    """ Check if the structure is approximately Axially Symmetric.
    For a system to be approximately Axially Symmetric, 2 of the eigenvalues of the RoG tensor should ideally be similar, but not necessarily identical.
    If 2 out of 3 ratios are close  within a tolerance of 20%, the system is approximately Axially Symmetric, indicating that the mass is elongated in one direction.
    An example of this system is GB1, or  ARC REPRESSOR-OPERATOR, pdb: 1PAR.
    """
    sortedIx = np.argsort(eigenvalues)
    sortedEigenvalues = eigenvalues[sortedIx]
    isApproxAxiallySymmetric = np.allclose(sortedEigenvalues[:2], sortedEigenvalues[:2].mean(), rtol=tolerance)  # Tolerance of 20% for axially symmetric

    return isApproxAxiallySymmetric

def isStructureFullyAnisotropic(eigenvalues, tolerance=.2):
    """ Check if the structure is FullyAnisotropic system.
    Its mass distribution is not symmetric in any direction.
    """
    isAnisotropic = not isStructureAxiallySymmetric(eigenvalues, tolerance)
    return isAnisotropic



## Quick testing
if __name__ == "__main__":
    gb1 = '/Users/luca/Documents/NMR-Data/Relaxation/Fred_Musket/GB1/FWM_analysis_gb1_relax/gb1.pdb'
    ferritin_Spherical = '/Users/luca/Downloads/1mfr.pdb'
    t4_fullyAnisotropic = '/Users/luca/Downloads/8dwj_T4-primosome_alone.pdb'
    arc_axially = '/Users/luca/Downloads/1par_arc_s.pdb'
    il17f = '/Users/luca/Downloads/6hgo_s.pdb'

    structure = getStructure(gb1)

    coords = getCoords(structure)
    com = getCOM(coords)
    dist2 = getSquaredDistances(coords,com)
    gyrationRadius = getGyrationRadius(dist2)
    tensor = calculateGyrationRadiusTensor(coords, com)
    eigenvalues = getEigenvalues(tensor)
    eigenvectors = getEigenvectors(tensor)
    _isStructureIsotropic = isStructureIsotropic(eigenvalues)
    _isStructureAxiallySymmetric = isStructureAxiallySymmetric(eigenvalues)
    _isStructureFullyAnisotropic = isStructureFullyAnisotropic(eigenvalues)

    print("Radius of Gyration:", gyrationRadius)
    print("eigenvalues:", eigenvalues)
    print("eigenvectors:\n", eigenvectors)
    print(f"The RoG tensor is approx_isotropic?  {_isStructureIsotropic}")
    print(f"The RoG tensor is approximately axially symmetric?  {_isStructureAxiallySymmetric}")
    print(f"The RoG tensor is Fully Anisotropic?  {_isStructureFullyAnisotropic}")
