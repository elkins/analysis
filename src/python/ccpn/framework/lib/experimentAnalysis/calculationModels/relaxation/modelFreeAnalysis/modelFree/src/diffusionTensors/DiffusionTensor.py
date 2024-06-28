"""
This module contains the diffusion tensor structure object.
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
__dateModified__ = "$dateModified: 2024-06-28 10:33:01 +0100 (Fri, June 28, 2024) $"
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
from Bio.PDB import PDBParser
from ccpn.util.Path import aPath
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ..io.Logger import getLogger
from . import structureLib as lib
from decorator import decorator

@decorator
def isStructureAvailalble(func, self, *args, **kwargs):
    _property = '_structureObj'  # Change this to the desired property name
    if getattr(self, _property) is None:
        getLogger().warn(f'Cannot execute {func.__name__} without a valid {_property}. Returning None')
        return
    return func(self, *args, **kwargs)

class StructureHandler(object):
    """
    The object to handle the structural information from file.
    Only PDB files are available at the moment, maybe CIF will be supported in the future.

    """
    def __init__(self, parent):
        self.parent = parent
        self.settingsHandler = self.parent.settingsHandler
        self.inputsHandler = self.parent.inputsHandler
        self.outputsHandler = self.parent.outputsHandler
        self._structureId = 'protein'  # the id that will be used for the structure object
        self._parserType = 'pdb'
        self._structureFilePath = self.inputsHandler._validatePath(self.inputsHandler.molecularStructure_path)
        self._parser = None
        self._setParser()
        self._structureObj = None

        ## store handles to data to avoid recalculating
        self._coords = None
        self._gyrationTensor = None
        self._eigenvalues = None
        self._eigenvectors = None

        if self._structureFilePath:
            self._structureObj = self._parseStructure()
            self._setEigenProperties()

    @property
    def structureObj(self):
        return self._structureObj

    @isStructureAvailalble
    def getCoords(self):
        if self._coords is None:
            self._coords = lib._getCoords(structure=self._structureObj)
        return self._coords

    def getGyrationTensor(self):
        """The gyrationTensor for the structure
          :return: nD array (3X3)
          """
        coords = self.getCoords()
        if self._gyrationTensor is None:
            com = lib._getCOM(coords)
            self._gyrationTensor = lib._calculateGyrationTensor(coords, com)
        return self._gyrationTensor

    def _setEigenProperties(self):
        """
        Set the eigenvalues, eigenvectors  from a gyration Tensor
        :return: tuple. Returns two objects, a 1-D array containing the eigenvalues, and
        a matrix corresponding to the eigenvectors.
        """
        self._eigenvalues, self._eigenvectors = np.linalg.eigh(self.getGyrationTensor())

    def isIsotropic(self):
        return lib._isStructureIsotropic(self._eigenvalues, tolerance=.2)

    def isAxiallySymmetric(self):
        return lib._isStructureAxiallySymmetric(self._eigenvalues, tolerance=.2)

    def isFullyAnisotropic(self):
        return lib._isStructureFullyAnisotropic(self._eigenvalues, tolerance=.2)

    def getEllipsoidShape(self):
        if self.isAxiallySymmetric():
            return lib._determineEllipsoidShape(self._eigenvalues)
        else:
            getLogger().warn('Cannot determine the Ellipsoid Shape for a non Axially-Symmetric structure')

    def getShape(self):
        """Get approximately the shape of the molecular structure based on the gyration Tensor eigenvalues."""
        if self.isIsotropic():
            return sv.ISOTROPIC
        if self.isAxiallySymmetric():
            return sv.AXIALLY_SYMMETRIC
        else:
            return sv.ANISOTROPIC

    def get_NH_anglesByResidueDict(self):
        """For each residue, get the angle between the NH vector and the principal axis.
         Note it could be an ensemble, in that case we take the mean of all angles.
         :return: dict {str : tuple(mean, std)} --> {residue_id : (mean angle in degrees, std of all angles)}"""

        principalAxis = lib._getPrincipalAxisDiffusion(self._eigenvalues, self._eigenvectors)
        vectorsByResidueDict = lib._calculate_NH_vectors(self._structureObj)
        anglesByResidueDict = lib._calculateThetaAnglesByVectors(vectorsByResidueDict, principalAxis)
        return anglesByResidueDict

    def get_NH_cosineAnglesByResidueDict(self):
        """For each residue, get the angles between the NH vector and the principal axis.
         :return: dict {str : array(x,y,z)...}"""
        vectorsDict = lib._calculate_NH_vectors(self._structureObj)
        tensor = self.getGyrationTensor()
        cosinesByResidueDict = lib._calculateDirectionCosinesByVectors(vectorsDict, tensor)
        return cosinesByResidueDict

    def _calculateAnisotropicCoeficients(self, directionCosineNHvector, Dxx, Dyy,Dzz):
        return lib._calculateAnisotropicCoeficients(directionCosineNHvector, Dxx, Dyy,Dzz)

    def _setParser(self):
        """ Get the parser from filePath.
        Only PDB available at the moment"""
        if self._parserType == 'pdb':
            self._parser = PDBParser(QUIET=True)
        else: #get from path
            path = self._structureFilePath
            if path.is_file() and len(path.suffixes) >= 1 and path.suffixes[-1] == '.pdb':
                self._parser = PDBParser(QUIET=True)
            else:
                getLogger().warn(f'Error loading file {path}. This file is not yet supported. Please use a .pdb file')
        return self._parser

    def _parseStructure(self):
        """ Use the parser to load a file and initiate the structure object"""
        parser = self._parser
        structure = None
        if parser is not None:
            structure = parser.get_structure(self._structureId, str(self._structureFilePath))
        return structure
