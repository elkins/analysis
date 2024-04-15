"""
This module contains the diffusion models  used in the Lipari-Szabo conventions:

    1) Isotropic Rotational Diffusion (Isotropic Model):
        This model assumes that the probe molecule undergoes isotropic rotational diffusion, meaning that it rotates freely and uniformly in all directions.

    2) Axial Symmetric (Axial Model):
        The probe molecule is assumed to have an axial symmetry, such as when it is aligned with a preferred axis

    3) Fully Anisotropic (Rhombic Model):
        The fully anisotropic or rhombic model is used when the probe molecule has no preferred axis of rotation, and its rotational diffusion is fully anisotropic.
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
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from abc import ABC, abstractmethod

import pandas as pd


class LipariSzaboModel(ABC):
    name = 'generic'
    model_id = 0
    TcCount = 0  # rotational correlation time count

    def __int__(self, *args, **kwargs):
        pass
        self.params = {}
        self.expData = pd.DataFrame([])

    def objectiveFunction(self, t):
        raise RuntimeError("This method needs to be subclassed")

    def perform_minimization(self):
        minimizer = Minimizer(self.objectiveFunction, self.params, fcn_args=(x, Aexperimental, model_type))
        result = minimizer.minimize(method='differential_evolution')
        return result

class IsotropicModel(LipariSzaboModel):
    name = 'Isotropic'
    model_id = 1
    TcCount = 1  # described total rotational correlation time count


class AxialSymmetricModel(LipariSzaboModel):
    name = 'Axially-Symmetric'
    model_id = 2
    TcCount = 2


class FullyAnisotropicModel(LipariSzaboModel):
    name = 'Fully-Anisotropic'
    model_id = 3
    TcCount = 3


class PartiallyAnisotropicModel(LipariSzaboModel):
    name = 'Partially-Anisotropic'
    modelEnum = 4
    TcCount = 2
    #   not sure





