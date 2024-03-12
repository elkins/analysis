"""

Module containing implementation functions for calculating the j(w) values using the Lipari-Szabo / Model-Free framework.

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

        All the classic models (Not the extended) containins the following arguments: ti, ci, w, s2, te, rex
        Functions can be used with or without the tensor information.
        Functions are of the same construction regardless the rotational diffusion model: e.g.: Isotropic, Axially Symmetric, Fully anisotropic.
        - ti:
        - ci:
        - w:
        - te:
        - s2:
        - rex:

    ~~ Speed ~~
    These functions are invoked on an immense scale by an advanced Minimiser.
    They are not called in traditional way, and are not for user usage but optimised for Minimisation only. Unfortunately Jit and Numba won't work/help for these

    It is paramount to keep these functions independent of each other so to be wrapped by the Jit (Just-In-Time), Numba's compiler.

"""

import numpy as np


def _jwTerm(ci, ti, w):
    """See module documentation above"""
    return np.sum(ci*ti/(1+(w*ti)**2))

def _calculateJwModel0(ti, ci, w, s2=None, te=None, rex=None):
    """See module documentation above"""
    return (2/5) * _jwTerm(ci, ti, w)

def _calculateJwModel1(ti, ci, w, s2, te=None, rex=None):
    """See module documentation above"""
    return (2/5) * (s2 * _jwTerm(ci, ti, w))

def _calculateJwModel2(ti, ci, w, s2, te, rex=None):
    """See module documentation above"""
    t = 1/ (1/ti + 1/te)
    return (2/5) * (s2 * _jwTerm(ci, ti, w) + _jwTerm((1 - s2), t, w))

def _calculateJwModel3(ti, ci, w, s2=None, te=None, rex=None):
    """See module documentation above"""
    return _calculateJwModel1(ti, ci, w, s2) # + rex

def _calculateJwModel4(ti, ci, w, s2=None, te=None, rex=None):
    """See module documentation above"""
    return _calculateJwModel2(ti, ci, w, s2, te) #+ rex

