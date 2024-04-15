"""

Module containing implementation functions for calculating  the spectral density function J(ω) values using the Lipari-Szabo formalism.

    ~~ References ~~
        - Lipari, G., & Szabo, A. (1982). Model-Free Approach to the Interpretation of Nuclear Magnetic Resonance Relaxation in Macromolecules. 1. Theory and Range of Validity. Journal of the American Chemical Society, 104(17), 4546–4559. https://doi.org/10.1021/ja00381a009
        - Lipari, G., & Szabo, A. (1982). Model-Free Approach to the Interpretation of Nuclear Magnetic Resonance Relaxation in Macromolecules. 2. Analysis of Experimental Results. Journal of the American Chemical Society, 104(17), 4559–4570. https://doi.org/10.1021/ja00381a010
        - Sahu et al.  (2000). Backbone dynamics of Barstar: A 15N NMR relaxation study. Proteins: 41:460-474. Table 1.

    ~~ Latex ~~
       - Model with no optimised parameters :
          J(w) = \frac{2}{5} \biggl[ \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]

       - Model 1: Optimised S2
          J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]

       - Model 2: Optimised S2, Te
          J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} + \frac{ (1-S^2)\tau}{1+(\tau\omega)^2}\biggr]

       - Model 3: Optimised S2, Rex
          J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr] + R_{ex}

       - Model 4: Optimised S2, Te, Rex
          J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} + \frac{ (1-S^2)\tau_i}{1+(\tau\omega)^2}\biggr]+ R_{ex}

       - Common inner term:
          J(w)_{Inner} = \sum_{i=1}^{n} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}

    ~~ Function Signature, Parameters ~~

        All the classic models (Not the extended) containing the following arguments: ti, ci, w, s2, te, rex
        Functions can be used with or without the tensor information.
        Functions are of the same construction regardless the rotational diffusion model: e.g.: Isotropic, Axially Symmetric, Fully anisotropic.

"""

import numpy as np
from abc import ABC
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv


class SDFHandler:
    """
    The  spectral density function handler used to calculate the J(ω) at a specific condition.

    """

    models = []
    _cached = {}  # Memoization cache

    @classmethod
    def register(cls, model):
        """
        add a model to the registered models
        """
        if model not in cls.models:
            cls.models += [model]
        else:
            raise RuntimeError('Model already registered')

    @classmethod
    def deregister(cls, model):
        """
        add a model to the registered models
        """
        if model in cls.models:
            cls.models.pop(model)

    def getModelsBy(self, attr, value):
        """
        get models by a property
        """
        return [model for model in self.models if getattr(model, attr, None) == value]

    @property
    def classicModels(self):
        """
        Get the original MF density Function models
        :return:
        """
        return [model for model in self.models if model.isClassic and not model.isExtended]

    @property
    def extendedModels(self):
        """
        Get the extended MF density Function models
        :return:
        """
        return [model for model in self.models if model.isExtended]

    def __int__(self):

        self.activeModels = []

    def setActiveModels(self, model_ids):
        models = []
        for model_id in model_ids:
            models += self.getModelsBy('model_id', model_id)
        self.activeModels = models

    def calculate(self, *args, **kwargs):
        """
        Run each calculation for the active models. To be moved on the diffusion model with the Minimiser. each will have a minimiser.

        """
        jws = []
        for model in self.activeModels:
            jw = model.calculate(*args, kwargs)
            jws.append(jw)
        return jws


class _Jmod(ABC):
    """Base class for the various models"""
    name = 'model ABC'
    model_id = 0
    optimisedParams = []
    plusRex = False
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(*args, **kwrgs):
        raise RuntimeError("This method needs to be subclassed")

    @staticmethod
    def _jwTerm(ci, ti, w):
        """See module documentation above"""
        return np.sum(ci * ti / (1 + (w * ti)**2))

    def __repr__(self):
        return f'<SDF: {_Jmod.name}>'

class _Model0(_Jmod):
    name = 'model 0'
    model_id = 0
    optimisedParams = []
    plusRex = False
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(ti, ci, w, *args, **kwargs):
        """See module above"""
        return (2/5) * _Jmod._jwTerm(ci, ti, w)

class _Model1(_Jmod):
    name = 'model 1'
    model_id = 1
    optimisedParams = [sv.S2]
    plusRex = False
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(ti, ci, w, s2, *args, **kwargs):
        """See module above"""
        return (2 / 5) * (s2 * _Jmod._jwTerm(ci, ti, w))

class _Model2(_Jmod):
    name = 'model 2'
    model_id = 2
    optimisedParams = [sv.S2, sv.TE]
    plusRex = False
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(ti, ci, w, s2, te, *args, **kwargs):
        """See module above"""
        t = 1 / (1/ti + 1/te)
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2 =  _Jmod._jwTerm((1 - s2), t, w)
        return (2 / 5) * (s2 * term1 + term2)

class _Model3(_Jmod):
    name = 'model 3'
    model_id = 3
    optimisedParams = [sv.S2]
    plusRex = True
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(ti, ci, w, s2, *args, **kwargs):
        """See module above"""
        return (2 / 5) * (s2 * _Jmod._jwTerm(ci, ti, w))

class _Model4(_Jmod):
    name = 'model 4'
    model_id = 4
    optimisedParams = [sv.S2, sv.TE]
    plusRex = True
    isClassic = True
    isExtended = False

    @staticmethod
    def calculate(ti, ci, w, s2, te, *args, **kwargs):
        """See module above"""
        t = 1 / (1 / ti + 1 / te)
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2 = _Jmod._jwTerm((1 - s2), t, w)
        return (2 / 5) * (s2 * term1 + term2)


SDFHandler.register(_Model0)
SDFHandler.register(_Model1)
SDFHandler.register(_Model2)
SDFHandler.register(_Model3)
SDFHandler.register(_Model4)

