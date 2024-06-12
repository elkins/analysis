"""

Module containing implementation functions for calculating  the spectral density function J(ω) values using the Lipari-Szabo formalism.

    ~~ References ~~
        - Lipari, G., & Szabo, A. (1982). Model-Free Approach to the Interpretation of Nuclear Magnetic Resonance Relaxation in Macromolecules. 1. Theory and Range of Validity. Journal of the American Chemical Society, 104(17), 4546–4559. https://doi.org/10.1021/ja00381a009
        - Lipari, G., & Szabo, A. (1982). Model-Free Approach to the Interpretation of Nuclear Magnetic Resonance Relaxation in Macromolecules. 2. Analysis of Experimental Results. Journal of the American Chemical Society, 104(17), 4559–4570. https://doi.org/10.1021/ja00381a010
        - Sahu et al.  (2000). Backbone dynamics of Barstar: A 15N NMR relaxation study. Proteins: 41:460-474. Table 1.

    ~~ Function Signature, Parameters ~~

        Functions can be used with or without the tensor information.
        Functions are of the same construction regardless the rotational diffusion model: e.g.: Isotropic, Axially Symmetric, Fully anisotropic.
        Models with the Flag plusRex are the same as the  parent model, except that when evoked to calculate the rate of interest that requires the Rex term, e.g.: R2 , then Rex is added to the
        rate calculation ant NOT in the spectralFunction

"""

import numpy as np
from abc import ABC, abstractmethod
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv


class SDFHandler(object):
    """
    The  spectral density function handler used to calculate the J(ω) at a specific condition.

    """

    models = {}
    _cached = {}  # Memoization cache

    @classmethod
    def register(cls, model):
        """
        add a model to the registered models
        """
        if model.model_id not in cls.models:
            cls.models[model.model_id] = model
        else:
            raise RuntimeError('Model already registered')

    @classmethod
    def deregister(cls, model):
        """
        add a model to the registered models
        """
        if model.model_id in cls.models:
            cls.models.pop(model.model_id, None)

    @staticmethod
    def getById(model_id):
        return SDFHandler.models.get(model_id)

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

    def __init__(self, settingsHandler):
        self.settingsHandler = settingsHandler
        self.activeModels = []
        self.setActiveModels(self.settingsHandler.spectralDensityFuncModels)

    def setActiveModels(self, model_ids):
        models = []
        for model_id in model_ids:
            models += self.getModelsBy('model_id', model_id)
        self.activeModels = models


# ~~~~~~~~~~ ABC Model implementation ~~~~~~~~~~ #

class _Jmod(ABC):
    """Base class for the various models"""
    name = 'model ABC'
    model_id = 0
    parentModel_id = None
    optimisedParams = []
    plusRex = False
    isClassic = True
    isExtended = False
    latex = 'J(w)_{Inner} = \sum_{i=1}^{n} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}'  # to reproduce in a text document
    category = [sv.LIPARISZABO_Original]

    @staticmethod
    def calculate(*args, **kwrgs):
        raise RuntimeError("This method needs to be subclassed")

    @staticmethod
    def _jwTerm(ci, ti, w):
        """
        Convenient method. The inner term in any Lipari-Szabo model
        :param ci: 1d array
        :param ti:  1d array
        :param w: float. omega
        :return: j(w) inner term
        """
        return np.sum(ci * ti / (1 + (w * ti)**2))

    def __repr__(self):
        return f'<SDF: {_Jmod.name}>'


# ~~~~~~~~~~ Specialised Models ~~~~~~~~~~ #

class _Model0(_Jmod):
    name = 'model 0'
    model_id = 0
    optimisedParams = []
    plusRex = False
    isClassic = True
    isExtended = False
    latex = 'J(w) = \frac{2}{5} \biggl[ \sum_{i=1}^{n} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]'

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        ci = kwargs.get(sv.Ci)
        ti = kwargs.get(sv.Ti)
        w = kwargs.get(sv.W)
        return (2/5) * _Jmod._jwTerm(ci, ti, w)

class _Model1(_Jmod):
    name = 'model 1'
    model_id = 1
    optimisedParams = [sv.S2]
    plusRex = False
    isClassic = True
    isExtended = False
    latex = 'J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr]'

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        s2 = kwargs.get(sv.S2)
        ci = kwargs.get(sv.Ci)
        ti = kwargs.get(sv.Ti)
        w = kwargs.get(sv.W)
        return (2 / 5) * (s2 * _Jmod._jwTerm(ci, ti, w))

class _Model2(_Jmod):
    name = 'model 2'
    model_id = 2
    optimisedParams = [sv.S2, sv.TE]
    plusRex = False
    isClassic = True
    isExtended = False
    latex = 'J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} + \frac{ (1-S^2)\tau}{1+(\tau\omega)^2}\biggr]'

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        s2 = kwargs.get(sv.S2)
        ci = kwargs.get(sv.Ci)
        ti = kwargs.get(sv.Ti)
        te = kwargs.get(sv.TE)
        w = kwargs.get(sv.W)
        t  = 1 / (1/np.mean(ti) + 1/te)
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2 =  _Jmod._jwTerm((1 - s2), t, w)
        return (2 / 5) * (s2 * term1 + term2)

class _Model3(_Jmod):
    name = 'model 3'
    model_id = 3
    parentModel_id = 1
    optimisedParams = [sv.S2, sv.REX]
    plusRex = True
    isClassic = True
    isExtended = False
    latex = 'J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}\biggr] + R_{ex}'
                #Note Rex is not technically used in the calculation and minimisation but only for calculating R2

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        return _Model1.calculate(**kwargs)


class _Model4(_Jmod):
    name = 'model 4'
    model_id = 4
    parentModel_id = 2
    optimisedParams = [sv.S2, sv.TE, sv.REX]
    plusRex = True
    isClassic = True
    isExtended = False
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} +
     \frac{ (1-S^2)\tau_i}{1+(\tau\omega)^2}\biggr]+ R_{ex}'''  # *Rex see above

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        return _Model2.calculate(**kwargs)

class _Model5(_Jmod):
    name = 'model 5'
    model_id = 5
    optimisedParams = [sv.S2, sv.S2f, sv.Ts]
    plusRex = False
    isClassic = False
    isExtended = True
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2} +
     \frac{ (S^2_f-S^2)(\tau_s+\tau_i) \tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2}\biggr]'''
    category = [sv.LIPARISZABO_Extended]

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        s2 = kwargs.get(sv.S2)
        ci = kwargs.get(sv.Ci)
        ti = kwargs.get(sv.Ti)
        ts = kwargs.get(sv.Tf)
        w = kwargs.get(sv.W)
        s2f = kwargs.get(sv.W)
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2num = ((s2f -s2) * (ts + ti)) * ts          # nominator
        term2den= (ts + ti)**2 + (ts*ti*w)**2           # denominator
        term2 = term2num/term2den
        return (2 / 5) * (s2 * term1 + term2)

class _Model6(_Jmod):
    name = 'model 6'
    model_id = 6
    optimisedParams = [sv.S2, sv.S2f, sv.Ts, sv.Tf]
    plusRex = False
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (1-S^2_f)(\tau_f+\tau_i) \tau_f} {(\tau_f+\tau_i)^2 +(\tau_f\tau_i\omega)^2}
     + \frac{ (S^2_f-S^2)(\tau_s+\tau_i)\tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2} \biggr] '''

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        s2 = kwargs.get(sv.S2)
        ci = kwargs.get(sv.Ci)
        ti = kwargs.get(sv.Ti)
        tf = kwargs.get(sv.Tf)
        ts = kwargs.get(sv.Tf)
        w = kwargs.get(sv.W)
        s2f = kwargs.get(sv.W)
        term1 = _Jmod._jwTerm(ci, ti, w)
        # Term 2
        term2num = ((1-s2f) * (tf + ti)) * tf
        term2den= (tf + ti)**2 + (tf*ti*w)**2
        term2 = term2num/term2den
        # Term 3
        term3num = ((s2f -s2) * (ts + ti)) * ts
        term3den =  (ts + ti)**2 + (ts*ti*w)**2
        term3 = term3num/term3den
        return (2 / 5) * (s2 * term1 + term2 + term3)

class _Model7(_Jmod):
    name = 'model 7'
    model_id = 7
    parentModel_id = 5
    optimisedParams = [sv.S2, sv.S2f, sv.Ts, sv.REX]
    plusRex = True
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (S^2_f-S^2)(\tau_s+\tau_i) \tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2}\biggr] + R_{ex}'''

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        return _Model5.calculate(**kwargs)


class _Model8(_Jmod):
    name = 'model 8'
    model_id = 8
    parentModel_id = 6
    optimisedParams = [sv.S2, sv.S2f, sv.Ts, sv.Tf, sv.REX]
    plusRex = True
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2 \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (1-S^2_f)(\tau_f+\tau_i) \tau_f} {(\tau_f+\tau_i)^2 +(\tau_f\tau_i\omega)^2}
     + \frac{ (S^2_f-S^2)(\tau_s+\tau_i)\tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2} \biggr] + R_{ex}'''

    @staticmethod
    def calculate(**kwargs):
        """See module above"""
        return _Model6.calculate(**kwargs)

class _Model9(_Jmod):
    name = 'model 9'
    model_id = 9
    optimisedParams = [sv.S2s, sv.S2f, sv.Ts]
    plusRex = False
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = ('J(w) = \frac{2}{5} \biggl[ S^2_fS^2_s \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}'
             ' + \frac{ (1-S^2_s)(\tau_s+\tau_i) \tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2}  \biggr]')

    @staticmethod
    def calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs):
        """See module above"""
        s = s2f*s2s
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2num = ((1-s2s) * (ts + ti)) * ts
        term2den= (ts + ti)**2 + (ts*ti*w)**2
        term2 = term2num/term2den
        return (2 / 5) * (s* term1 + term2)

class _Model10(_Jmod):
    name = 'model 10'
    model_id = 10
    optimisedParams = [sv.S2s, sv.S2f, sv.Ts,  sv.Tf]
    plusRex = False
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2_fS^2_s \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (1-S^2_f)(\tau_f+\tau_i) \tau_f} {(\tau_f+\tau_i)^2 +(\tau_f\tau_i\omega)^2}
      + \frac{ (1-S^2_s)(\tau_s+\tau_i)S^2_f\tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2} \biggr]'''

    @staticmethod
    def calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs):
        """See module above"""
        s = s2f*s2s
        term1 = _Jmod._jwTerm(ci, ti, w)
        term2num = ((1-s2f) * (tf + ti)) * tf
        term2den= (tf + ti)**2 + (tf*ti*w)**2
        term2 = term2num/term2den
        term3num = ((1-s2s) * (ts + ti)) * ts * s2f
        term3den= (ts + ti)**2 + (ts*ti*w)**2
        term3 = term3num/term3den
        return (2 / 5) * (s* term1 + term2 + term3)


class _Model11(_Jmod):
    name = 'model 11'
    model_id = 11
    parentModel_id = 9
    optimisedParams = [sv.S2s, sv.S2f, sv.Ts, sv.REX]
    plusRex = True
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2_fS^2_s \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (1-S^2_s)(\tau_s+\tau_i) \tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2}  \biggr] + R_{ex}'''

    @staticmethod
    def calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs):
        """See module above"""
        return _Model9.calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs)

class _Model12(_Jmod):
    name = 'model 12'
    model_id = 12
    parentModel_id = 10
    optimisedParams = [sv.S2s, sv.S2f, sv.Ts, sv.Tf, sv.REX]
    plusRex = True
    isClassic = False
    isExtended = True
    category = [sv.LIPARISZABO_Extended]
    latex = '''J(w) = \frac{2}{5} \biggl[ S^2_fS^2_s \sum_{i=1}^{3} \frac{c_i \cdot \tau_i}{1+(\tau_i\omega)^2}
     + \frac{ (1-S^2_f)(\tau_f+\tau_i) \tau_f} {(\tau_f+\tau_i)^2 +(\tau_f\tau_i\omega)^2}
      + \frac{ (1-S^2_s)(\tau_s+\tau_i)S^2_f\tau_s} {(\tau_s+\tau_i)^2 +(\tau_s\tau_i\omega)^2} \biggr]  + R_{ex}'''

    @staticmethod
    def calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs):
        """See module above"""
        return _Model10.calculate(ti, ci, w,  te, s2f, s2s,  ts, tf, *args, **kwargs)


# -------  Register the models -------- #

# original with S2, Te,
SDFHandler.register(_Model0)
SDFHandler.register(_Model1)
SDFHandler.register(_Model2)
SDFHandler.register(_Model3)
SDFHandler.register(_Model4)

# extended with S2f, Ts, Tf
SDFHandler.register(_Model5)
SDFHandler.register(_Model6)
SDFHandler.register(_Model7)
SDFHandler.register(_Model8)

# extended with S2f, S2s, Ts, Tf
SDFHandler.register(_Model9)
SDFHandler.register(_Model10)
SDFHandler.register(_Model11)
SDFHandler.register(_Model12)

