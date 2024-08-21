"""
This module defines base classes for Series Analysis.

The fitting models are based on the Lmfit framework.
Note that the package Lmfit refers to the Minimisers as Models.
In the Series Analysis context we use the term Model more broadly and we refer to the top object containing the Metadata for the Minimiser, fitting functions etc.

Lmfit Minimisers:
    ’leastsq’: Levenberg-Marquardt (default)
    ’least_squares’: Least-Squares minimization, using Trust Region Reflective method
    ’differential_evolution’: differential evolution
    ’brute’: brute force method
    ’basinhopping’: basinhopping
    ’ampgo’: Adaptive Memory Programming for Global Optimization
    ’nelder’: Nelder-Mead
    ’lbfgsb’: L-BFGS-B
    ’powell’: Powell
    ’cg’: Conjugate-Gradient
    ’newton’: Newton-CG
    ’cobyla’: Cobyla
    ’bfgs’: BFGS
    ’tnc’: Truncated Newton
    ’trust-ncg’: Newton-CG trust-region
    ’trust-exact’: nearly exact trust-region
    ’trust-krylov’: Newton GLTR trust-region
    ’trust-constr’: trust-region for constrained optimization
    ’dogleg’: Dog-leg trust-region
    ’slsqp’: Sequential Linear Squares Programming
    ’emcee’: Maximum likelihood via Monte-Carlo Markov Chain
    ’shgo’: Simplicial Homology Global Optimization
    ’dual_annealing’: Dual Annealing optimization

    <-> WARNING <-> :
    Do not change the function signature for a fitting function without amending the Minimiser default parameters or
    will result in a broken Model.
    E.g.:
            Minimiser:
                defaultParams = {
                                            'Kd' : 1.0,
                                            'BMax': 10
                                            }
            Minimiser.fittingFunc:
            the  function's argument are EXACTLY as defined in the defaultParams dictionary keys:
                def oneSiteBinding_func(x, Kd, BMax): ...

    See MinimiserModel _defaultParams for more info.


"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-21 19:06:29 +0100 (Wed, August 21, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import warnings
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from copy import deepcopy
from pandas import Series, isnull
from collections import defaultdict
from lmfit import Model, Minimizer, Parameter, Parameters
from lmfit.model import ModelResult, _align
from ccpn.core.DataTable import TableFrame
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.Application import getApplication, getProject


class FittingModelABC(ABC):

    modelName                 = None                          # The Model name.
    targetSeriesAnalyses   = []                                # A list of Series Analysis Names where this model will be available. E.G.: [sv.RelaxationAnalysis,... ]
    modelInfo                     = ''                                # A brief description of the fitting model.
    description                   = ''                                # A simplified representation of the used equation(s).
    maTex                          = r''                              # MaTex representation of the used equation(s). see https://matplotlib.org/3.5.0/tutorials/text/mathtext.html
    references                   = ''                                # A list of journal article references. E.g.: DOIs or title/authors/year/journal; web-pages.
    Minimiser                     = None                         # The fitting minimiser model object (initiated)
    peakProperty               = sv._HEIGHT              # The peak property to fit. One of ['height', 'lineWidth', 'volume', 'ppmPosition']
    _minimisedProperty      = sv._HEIGHT            # Similarly to peakProperty, The same as peakProperty for most of the models.
                                                                             # Added because models can be fitted using any properties (data) e.g. ratios.   This will appear as  Y label in the fitting plot.
    isEnabled                        = True                       # True to enable selection on the GUI. False to show but greyed-out and unselectable
    isGUIVisible                     = True                      # True to show on GUI. False to don't display on widgets but still available from backend. (good for testing)
    requiredInputData            = 1                           # ensure there is the correct amount of input data. Should also check the types (?)
    _autoRegisterModel        = True                      # Register to the Backend when dynamically loading its Python module from disk
    _requiredInputDataColumns = []                      # The mandatory column headers required for this model to function correctly
    _columnMaps = {}                                            # Internal. Used for updating the columns and back-compatibility with previous software versions

    def __init__(self, *args, **kwargs):
        self.application = getApplication()
        self.project = getProject()
        self._minimiserMethod = sv.LEASTSQ
        self._uncertaintiesMethod = sv.COVMATRIX
        self._uncertaintiesSampleSize = 100  # Number of iterations for the _uncertaintiesMethod calculations

        self._modelArgumentNames = []
        self._rawDataHeaders = [] # strings of columnHeaders
        self.xSeriesStepHeader = sv.SERIES_STEP_X
        self.ySeriesStepHeader = sv.SERIES_STEP_Y
        self.xSeriesStepAdditionalHeader = sv.ADDITIONAL_SERIES_STEP_X #e.g. global protein concentration
        self._ySeriesLabel = self.peakProperty # this is only used in the Plot Y Axis label.

    @abstractmethod
    def fitSeries(self, inputData:TableFrame, *args, **kwargs) -> TableFrame:
        """
        :param inputData: a TableFrame containing all necessary data for the fitting calculations
        :return: an output TableFrame with fitted data
        """
        pass

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the minimiser fitting function or calculation models.
          These names will be used in the models and will appear as column headers in the output result frames. """
        if self.Minimiser:
            return self.Minimiser.getParamNames(self.Minimiser)
        return []

    @property
    def modelArgumentUnits(self):
        """ The list of  units as str for the argument results."""
        return [''] * len(self.modelArgumentNames)

    @property
    def modelArgumentErrorNames(self):
        """ The list of parameters errors """
        return [f'{vv}{sv._ERR}' for vv in self.modelArgumentNames ]

    @property
    def modelGlobalParamNames(self):
        """ The list of parameters as str that are minimised globally in the minimiser fitting function. """
        if self.Minimiser:
            return self.Minimiser.getGlobalParamNames(self.Minimiser)
        return []

    @property
    def modelFixedParamNames(self):
        """ The list of parameters as str that are minimised globally in the minimiser fitting function. """
        if self.Minimiser:
            return self.Minimiser.getFixedParamNames(self.Minimiser)
        return []

    @property
    def rawDataHeaders(self):
        """ The list of rawData Column headers to appear in output frames and tables."""
        return self._rawDataHeaders

    @property
    def modelStatsNames(self):
        """ The list of statistical names used in the minimiser fitting function .
          These names will be used in the models and will appear as column headers in the output result frames. """
        if self.Minimiser:
            return self.Minimiser.getStatParamNames(self.Minimiser)
        return []

    @staticmethod
    def getFittingFunc(cls):
        """Get the Fitting Function used by the Minimiser """
        if cls.Minimiser is not None:
            return cls.Minimiser.FITTING_FUNC

    @staticmethod
    def fullDescription(cls):
        """A complete description of the model metadata and its journal article references (if any)"""
        return f'{cls.modelInfo} \n {cls.description}\nSee References: {cls.references}'

    def setMinimiserMethod(self, method:str):
        self._minimiserMethod = method

    def setUncertaintiesMethod(self, method:str):
        self._uncertaintiesMethod = method

    def setSampleSize(self, size:int):
        self._uncertaintiesSampleSize = size

    def getUncertaintiesMethod(self):
        return self._uncertaintiesMethod

    def getSampleSize(self):
        return self._uncertaintiesSampleSize

    def _getFirstInputDataTable(self, inputDataTables):
        """ _INTERNAL. Used to get the first available
        data from a dataTable for models that require only one dataFrame as input"""

        if len(inputDataTables) == 0:
            getLogger().warning(f'''No valid dataTable given as InputData. ''')
            return None
        if len(inputDataTables) == 1:
            inputDataTable = inputDataTables[0]
        else:
            inputDataTable = inputDataTables[-1]
            getLogger().warning(f'''Multiple dataTable given as InputData.  Using last added: {inputDataTable.pid}''')
        return inputDataTable.data

    def _getAllArgNames(self):
        _all = self.modelArgumentNames + self.modelArgumentErrorNames + self.modelStatsNames
        return _all

    def _getExcludedPidsForDataFrames(self, dataFrames, exclusionHeader, pidHeader):
        """Get all the excluded pids for a set of dataFrames. """
        excludedPids = []
        for df in dataFrames:
            if exclusionHeader in df and pidHeader in df:
                _innerExcludedPids = df[df[exclusionHeader] == True][pidHeader].values
                excludedPids.extend(_innerExcludedPids)
        return list(set(excludedPids))

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""
        if len(self.modelArgumentNames) >0:
            return self.modelArgumentNames[0]
        return None

    def __str__(self):
        return f'<{self.__class__.__name__}: {self.modelName}>'

    __repr__ = __str__

def rSQR_func(y, redchi, ddof=2):
    """
    Calculate the R2 (called from the minimiser results).
    :param redchi: Chi-square. From the Minimiser Obj can be retrieved as "result.redchi"
    :return: r2
    """
    var = np.var(y, ddof=ddof)
    if var != 0:
        r2 = 1 - redchi / var
        return r2



class MinimiserModel(Model):
    """
    The lower base class for the fitting minimisation routines.
    Based on the package LMFIT.
    Called for each row in the input SeriesDataTable.
    Parameters
    ----------
    independent_vars : :obj:`list` of :obj:`str`, optional
        Arguments to the model function that are independent variables
        default is ['x']).
    prefix : str, optional
        String to prepend to parameter names, needed to add two Models
        that have parameter names in common.
    nan_policy : {'raise', 'propagate', 'omit'}, optional
        How to handle NaN and missing values in data. See Notes below.
    **kwargs : optional
        Keyword arguments to pass to :class:`Model`.
    Notes
    -----
    1. `nan_policy` sets what to do when a NaN or missing value is seen in
    the data. Should be one of:
        - `'raise'` : raise a `ValueError` (default)
        - `'propagate'` : do nothing
        - `'omit'` : drop missing data

    ----- ccpn internal ----

     _defaultParams must be set.
        It is a dict containing as key the fitting func argument to be optimised (excluding x)
        and an initial default value. (Arbitrary at this stage or None. Initial values are calculated separately in the "guess" method).

        Also, these arguments as a string must be exactly as they are defined in the FITTING_FUNC arguments!
        Example fitFunc with args decay and amplitude:

            def expDecay(x, decay, amplitude):...
            defaultParams = {
                            'decay'    : 0.3,
                            'amplitude': 1
                            }
            (note x is not necessary to be defined here, it is part of the "independent_vars" set automatically)
        This because there is a clever signature inspection that sets on-the-fly args as class attributes,
        and they are used throughout the code.  <is an odd behaviour but too hard/dangerous to change!>
        defaultParams are also used to autogenerate Gui definitions in tables and widget entries.

    """
    FITTING_FUNC  = None
    MODELNAME     = 'Minimiser'
    method                = sv.LEASTSQ
    label                    = ''
    defaultParams = {} # N.B Very important. see docs above.
    _defaultGlobalParams = [] # used only as preselection when doing a Global fitting.
    _fixedParams = []

    def fit(self, data, params=None, weights=None, method='leastsq',
            iter_cb=None, scale_covar=True, verbose=False, fit_kws=None,
            nan_policy='propagate', calc_covar=True, max_nfev=None, **kwargs):
        """Fit the model to the data using the supplied Parameters.

        Parameters
        ----------
        data : array_like
            Array of data to be fit.
        params : Parameters, optional
            Parameters to use in fit (default is None).
        weights : array_like, optional
            Weights to use for the calculation of the fit residual
            (default is None). Must have the same size as `data`.
        method : str, optional
            Name of fitting method to use (default is `'leastsq'`).
        iter_cb : callable, optional
            Callback function to call at each iteration (default is None).
        scale_covar : bool, optional
            Whether to automatically scale the covariance matrix when
            calculating uncertainties (default is True).
        verbose : bool, optional
            Whether to print a message when a new parameter is added
            because of a hint (default is True).
        fit_kws : dict, optional
            Options to pass to the minimizer being used.
        nan_policy : {'raise', 'propagate', 'omit'}, optional
            What to do when encountering NaNs when fitting Model.
        calc_covar : bool, optional
            Whether to calculate the covariance matrix (default is True)
            for solvers other than `'leastsq'` and `'least_squares'`.
            Requires the ``numdifftools`` package to be installed.
        max_nfev : int or None, optional
            Maximum number of function evaluations (default is None). The
            default value depends on the fitting method.
        **kwargs : optional
            Arguments to pass to the model function, possibly overriding
            parameters.

        Returns
        -------
        ModelResult

        Notes
        -----
        1. if `params` is None, the values for all parameters are expected
        to be provided as keyword arguments. If `params` is given, and a
        keyword argument for a parameter value is also given, the keyword
        argument will be used.

        2. all non-parameter arguments for the model function, **including
        all the independent variables** will need to be passed in using
        keyword arguments.

        3. Parameters (however passed in), are copied on input, so the
        original Parameter objects are unchanged, and the updated values
        are in the returned `ModelResult`.

        Examples
        --------
        Take ``t`` to be the independent variable and data to be the curve
        we will fit. Use keyword arguments to set initial guesses:

        """

        if params is None:
            params = self.make_params(verbose=verbose)
        else:
            params = deepcopy(params)
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', category=RuntimeWarning)
            # If any kwargs match parameter names, override params.
            param_kwargs = set(kwargs.keys()) & set(self.param_names)
            for name in param_kwargs:
                p = kwargs[name]
                if isinstance(p, Parameter):
                    p.name = name  # allows N=Parameter(value=5) with implicit name
                    params[name] = deepcopy(p)
                else:
                    params[name].set(value=p)
                del kwargs[name]

            # All remaining kwargs should correspond to independent variables.
            for name in kwargs:
                if name not in self.independent_vars:
                    getLogger.warn(f"The keyword argument {name} does not " +
                                  "match any arguments of the model function. " +
                                  "It will be ignored.", UserWarning)

            # If any parameter is not initialized raise a more helpful error.
            missing_param = any(p not in params.keys() for p in self.param_names)
            blank_param = any((p.value is None and p.expr is None)
                              for p in params.values())
            if missing_param or blank_param:
                msg = ('Assign each parameter an initial value by passing '
                       'Parameters or keyword arguments to fit.\n')
                missing = [p for p in self.param_names if p not in params.keys()]
                blank = [name for name, p in params.items()
                         if p.value is None and p.expr is None]
                msg += f'Missing parameters: {str(missing)}\n'
                msg += f'Non initialized parameters: {str(blank)}'
                raise ValueError(msg)

            # Handle null/missing values.
            if nan_policy is not None:
                self.nan_policy = nan_policy
            mask = None
            if self.nan_policy == 'omit':
                mask = ~isnull(data)
                if mask is not None:
                    data = data[mask]
                if weights is not None:
                    weights = _align(weights, mask, data)

            # If independent_vars and data are alignable (pandas), align them,
            # and apply the mask from above if there is one.
            for var in self.independent_vars:
                if not np.isscalar(kwargs[var]):
                    kwargs[var] = _align(kwargs[var], mask, data)

            # Make sure `dtype` for data is always `float64` or `complex128`
            if np.isrealobj(data):
                data = np.asfarray(data)
            elif np.iscomplexobj(data):
                data = np.asarray(data, dtype='complex128')

            # Coerce `dtype` for independent variable(s) to `float64` or
            # `complex128` when the variable has one of the following types: list,
            # tuple, numpy.ndarray, or pandas.Series
            for var in self.independent_vars:
                var_data = kwargs[var]
                if isinstance(var_data, (list, tuple, np.ndarray, Series)):
                    if np.isrealobj(var_data):
                        kwargs[var] = np.asfarray(var_data)
                    elif np.iscomplexobj(var_data):
                        kwargs[var] = np.asarray(var_data, dtype='complex128')

            if fit_kws is None:
                fit_kws = {}
            result = MinimiserResult(self, params, method=self.method, iter_cb=iter_cb,
                                 scale_covar=scale_covar, fcn_kws=kwargs,
                                 nan_policy=self.nan_policy, calc_covar=calc_covar,
                                 max_nfev=max_nfev, **fit_kws)
            result.fit(data=data, weights=weights, method=self.method, nan_policy=self.nan_policy)
            result.components = self.components
            if result.redchi is not None:
                result.r2 = rSQR_func(redchi=result.redchi, y=data)
        return result

    def setMethod(self, method):
        self.method = method

    def guess(self, data, x, **kws):
        pass

    def _createParams(self):
        """ Make the default params namespaces. Without values"""
        params = Parameters()
        for name, value in self.defaultParams.items():
            params[name] = Parameter(name=name, value=value, vary=name in self._fixedParams)
        return params

    @staticmethod
    def getParamNames(cls):
        """ get the list of parameters as str used in the fitting function  """
        return list(cls.defaultParams.keys())
    
    @staticmethod
    def getGlobalParamNames(cls):
        """ get the list of parameters as str used in the fitting function  """
        return cls._defaultGlobalParams

    @staticmethod
    def getFixedParamNames(cls):
        """ get the list of parameters as str used in the fitting function  """
        return cls._fixedParams

    def getStatParamNames(self):
        """
        Get the common statistical ParamNames .
        :return: list
        """
        stats =  [sv.RSQR, sv.CHISQR, sv.REDCHI, sv.AIC, sv.BIC]
        return stats

    def updateParam(self, params, paramName, **kwargs):
        if paramName in params:
            for key, value in kwargs.items():
                if hasattr(params[paramName], key):
                    setattr(params[paramName], key, value)
                else:
                    getLogger().warning(f"Attribute {key} does not exist on parameter {paramName}")
        else:
            getLogger().warning(f"Parameter {paramName} does not exist in params")
        return params

MINIMISER_STAT_MAPPING_NAMES = {sv.MINIMISER_METHOD :'method',
                                                                   sv.RSQR                : 'r2',
                                                                   sv.CHISQR         : 'chisqr',
                                                                   sv.REDCHI  : 'redchi',
                                                                   sv.AIC            : 'aic',
                                                                   sv.BIC          : 'bic',
                                                                   }

class GlobalMinimiser(Minimizer):
    def __init__(self, func, x, data, globalParamNames, localParamNames, fixedParamNames, *args, **kwargs):
        """

        :param func: callable. The model function to be used for fitting.
        :param x: array-like. The x-values for the model function.
        :param data: array-like. The observed data to fit against, with each row corresponding to a dataset.
        :param globalParamNames: list of str. Names of the global parameters.
        :param localParamNames: list of str. Base names for the local parameters, indexed by dataset.
        :param fixedParamNames: list of str. Base names for the fixed parameters, similarly as the global, but they will not vary during the minimisation.
        :param args: Additional positional arguments for Minimiser.
        :param kwargs: Additional keyword arguments for Minimiser.
        """
        self.func = func
        self.x = x
        self.data = data
        self._concData = np.concatenate(self.data)
        self.globalParamNames = globalParamNames
        self.localParamNames = localParamNames
        self.fixedParamNames = fixedParamNames

        # Define a residual function that will be used for minimization
        def residual(params):
            return self._globalResidual(params)
        super().__init__(residual, *args, **kwargs)

    def minimize(self, method='leastsq', params=None, **kws):
        result = super().minimize(method, params=params, **kws)
        r2 = rSQR_func(self._concData, result.redchi)
        result.r2 = r2
        return result

    def _globalResidual(self, params):
        residuals = []
        globalValues = {name: params[name].value for name in self.globalParamNames}
        fixedValues = {name: params[name].value for name in self.fixedParamNames}
        for i in range(self.data.shape[0]):
            localValues = {}
            if len(self.localParamNames)>0:
                localValues = {name: params[f'{name}_{i}'].value for name in  self.localParamNames}
            yFit = self.func(self.x, **globalValues, **localValues, **fixedValues)
            residuals.append(yFit - self.data[i])
        return np.concatenate(residuals)

    @staticmethod
    def getGlobalStatisticalResult(minimiserResult):
        """
        Get the common statistical results from the global fit.
        Provide a measure of how well the global model fits all datasets combined.
        :return: dict
        """
        dd = {}
        for nn, vv in MINIMISER_STAT_MAPPING_NAMES.items():
            dd[nn] = getattr(minimiserResult, vv, None)
        return dd

    @staticmethod
    def getIndividualParamsForResult(minimiserResult, pids):
        """
        Grab the locally minimised param results.
        We need the original Param Name from userData, because in the Global minimisation, the local Params get a suffix (_x).
        Also we need to ensure is the right param per collection. We have the PID stored in the userData.
        :param minimiserResult: the object (MinimiserResult) returned after running GlobalMinimiser(...).minimize()
        :param pids: list of pids used for the global minimisation
        :return:
        """
        result = minimiserResult
        params4Pids = defaultdict(dict)
        for pid in pids:
            for paramName, param in result.params.items():
                userData = param.user_data or {}
                if userData.get(sv._PARAMTYPE) == sv._LOCAL:
                    localParamName = userData.get(sv._PARAMNAME)
                    minimisedPid = userData.get(sv.PID)
                    if minimisedPid == pid:
                        params4Pids[pid].update({localParamName:param.value})
                        params4Pids[pid].update({f'{localParamName}{sv._ERR}': param.stderr})
                else: # all other params are globals. no need of matching the pid here.
                    params4Pids[pid].update({paramName: param.value})
                    params4Pids[pid].update({f'{paramName}{sv._ERR}': param.stderr})
        return params4Pids


class MinimiserResult(ModelResult):
    """Result from the Model fit.

       This has many attributes and methods for viewing and working with the
       results of a fit using Model. It inherits from Minimizer, so that it
       can be used to modify and re-run the fit for the Model.

       """

    def __init__(self, model, params, data=None, weights=None, scaleMinMax=False,
                 method=sv.LEASTSQ, fcn_args=None, fcn_kws=None,
                 iter_cb=None, scale_covar=True, nan_policy=sv.PROPAGATE_MODE,
                 calc_covar=True, max_nfev=None, **fit_kws):
        """
        Parameters
        ----------
        model : Model
            Model to use.
        params : Parameters
            Parameters with initial values for model.
        data : array_like, optional
            Data to be modeled.
        weights : array_like, optional
            Weights to multiply ``(data-model)`` for fit residual.
        scaleMinMax: bool, True to scale data 0-1

        method : str, optional
            Name of minimization method to use (default is `'leastsq'`).
        fcn_args : sequence, optional
            Positional arguments to send to model function.
        fcn_dict : dict, optional
            Keyword arguments to send to model function.
        iter_cb : callable, optional
            Function to call on each iteration of fit.
        scale_covar : bool, optional
            Whether to scale covariance matrix for uncertainty evaluation.
        nan_policy : {'raise', 'propagate', 'omit'}, optional
            What to do when encountering NaNs when fitting Model.
        calc_covar : bool, optional
            Whether to calculate the covariance matrix (default is True)
            for solvers other than `'leastsq'` and `'least_squares'`.
            Requires the ``numdifftools`` package to be installed.
        max_nfev : int or None, optional
            Maximum number of function evaluations (default is None). The
            default value depends on the fitting method.
        **fit_kws : optional
            Keyword arguments to send to minimization routine.

        """
        self.r2 = None
        self._simulatedParams = None # best fit from running the Resampling for uncertainties
        self.scaleMinMax = scaleMinMax

        super().__init__( model, params, data=data, weights=weights,
                 method=method, fcn_args=fcn_args, fcn_kws=fcn_kws,
                 iter_cb=iter_cb, scale_covar=scale_covar, nan_policy=nan_policy,
                 calc_covar=calc_covar, max_nfev=max_nfev, **fit_kws)

    def getStatisticalResult(self):
        """
        Get the common statistical results from the fit.
        :return: dict
        """
        dd = {}
        for nn, vv in MINIMISER_STAT_MAPPING_NAMES.items():
            dd[nn] = getattr(self, vv, None)
        return dd

    def getParametersResult(self, params=None):
        """
        Get the parameter results from the fit. E.g.: amplitude, decay and errors for a T1 fitting model
        :return: dict
        """
        dd = {}
        if params is None:
            params = self.params
        for paramName, paramObj in params.items():
            error = f'{paramName}{sv._ERR}'
            dd[paramName] = None
            dd[error] = None
            if paramObj is not None:
                dd.update({paramName:paramObj.value})
                dd[error] = paramObj.stderr
        return dd

    def getAllResultsAsDict(self, params=None):
        """
        :return: A dict with all minimiser results
        """
        outputDict = {}
        for key, value in self.getParametersResult(params=params).items():
            outputDict[key] = value
        for key, value in self.getStatisticalResult().items():
            outputDict[key] = value
        return outputDict

    def getAllResultsAsDataFrame(self):
        """
        :return: A dataFrame with all minimiser results
        """
        outputDict = self.getAllResultsAsDict()
        df = pd.DataFrame(outputDict, index=[0])
        return df

    def calculateStandardErrors(self, x,y, uncertaintiesMethod='covMatrix', nonParametric=True, samples=200, noiseScale=0.5,  fraction=0.1):
        availavableMethods = {
                              sv.COVMATRIX:      self.covMatrixUncertaintiesEstimation,
                              sv.MONTECARLO:  self.monteCarloUncertaintiesEstimation,
                              sv.BOOTSTRAP:     self.bootstrapUncertaintiesEstimation,
                              sv.JACKKNIFE:        self.jackKnifeUncertaintiesEstimation
                              }
        if uncertaintiesMethod not in availavableMethods:
            raise RuntimeError('Invalid method. Use one of: covMatrix, monteCarlo, bootstrap, jackKnife ')
        fun = availavableMethods.get(uncertaintiesMethod, self.covMatrixUncertaintiesEstimation)
        params = fun(x, y, nSamples=samples, noiseScale=noiseScale, nonParametric=nonParametric, fraction=fraction)
        return params

    def plot(self, datafmt='o', fitfmt='-', initfmt='--', showPlot=True, xlabel=None,
             ylabel=None, yerr=None, numpoints=None, fig=None, data_kws=None,
             fit_kws=None, init_kws=None, ax_res_kws=None, ax_fit_kws=None,
             fig_kws=None, show_init=False, parse_complex='abs', title=None):
        """Plot the fit results and residuals using matplotlib.

        The method will produce a matplotlib figure (if package available)
        with both results of the fit and the residuals plotted. If the fit
        model included weights, errorbars will also be plotted. To show
        the initial conditions for the fit, pass the argument
        ``show_init=True``.

        Parameters
        ----------
        datafmt : str, optional
            Matplotlib format string for data points.
        fitfmt : str, optional
            Matplotlib format string for fitted curve.
        initfmt : str, optional
            Matplotlib format string for initial conditions for the fit.
        xlabel : str, optional
            Matplotlib format string for labeling the x-axis.
        ylabel : str, optional
            Matplotlib format string for labeling the y-axis.
        yerr : numpy.ndarray, optional
            Array of uncertainties for data array.
        numpoints : int, optional
            If provided, the final and initial fit curves are evaluated
            not only at data points, but refined to contain `numpoints`
            points in total.
        fig : matplotlib.figure.Figure, optional
            The figure to plot on. The default is None, which means use
            the current pyplot figure or create one if there is none.
        data_kws : dict, optional
            Keyword arguments passed to the plot function for data points.
        fit_kws : dict, optional
            Keyword arguments passed to the plot function for fitted curve.
        init_kws : dict, optional
            Keyword arguments passed to the plot function for the initial
            conditions of the fit.
        ax_res_kws : dict, optional
            Keyword arguments for the axes for the residuals plot.
        ax_fit_kws : dict, optional
            Keyword arguments for the axes for the fit plot.
        fig_kws : dict, optional
            Keyword arguments for a new figure, if a new one is created.
        show_init : bool, optional
            Whether to show the initial conditions for the fit (default is
            False).
        parse_complex : {'abs', 'real', 'imag', 'angle'}, optional
            How to reduce complex data for plotting. Options are one of:
            `'abs'` (default), `'real'`, `'imag'`, or `'angle'`, which
            correspond to the NumPy functions with the same name.
        title : str, optional
            Matplotlib format string for figure title.

        Returns
        -------
        matplotlib.figure.Figure

        See Also
        --------
        ModelResult.plot_fit : Plot the fit results using matplotlib.
        ModelResult.plot_residuals : Plot the fit residuals using matplotlib.

        Notes
        -----
        The method combines `ModelResult.plot_fit` and
        `ModelResult.plot_residuals`.

        If `yerr` is specified or if the fit model included weights, then
        `matplotlib.axes.Axes.errorbar` is used to plot the data. If
        `yerr` is not specified and the fit includes weights, `yerr` set
        to ``1/self.weights``.

        If model returns complex data, `yerr` is treated the same way that
        weights are in this case.

        If `fig` is None then `matplotlib.pyplot.figure(**fig_kws)` is
        called, otherwise `fig_kws` is ignored.

        """
        from matplotlib import pyplot as plt
        if data_kws is None:
            data_kws = {}
        if fit_kws is None:
            fit_kws = {}
        if init_kws is None:
            init_kws = {}
        if ax_res_kws is None:
            ax_res_kws = {}
        if ax_fit_kws is None:
            ax_fit_kws = {}

        # make a square figure with side equal to the default figure's x-size
        figxsize = plt.rcParams['figure.figsize'][0]
        fig_kws_ = dict(figsize=(figxsize, figxsize))
        if fig_kws is not None:
            fig_kws_.update(fig_kws)

        if len(self.model.independent_vars) != 1:
            getLogger().warning('Fit can only be plotted if the model function has one '
                  'independent variable.')
            return False

        if not isinstance(fig, plt.Figure):
            fig = plt.figure(**fig_kws_)

        gs = plt.GridSpec(nrows=3, ncols=1, height_ratios=[1, 4, 1])
        ax_res = fig.add_subplot(gs[0], **ax_res_kws)
        ax_fit = fig.add_subplot(gs[1], sharex=ax_res, **ax_fit_kws)
        ax_table = fig.add_subplot(gs[2], **ax_fit_kws)

        self.plot_fit(ax=ax_fit, datafmt=datafmt, fitfmt=fitfmt, yerr=yerr,
                      initfmt=initfmt, xlabel=xlabel, ylabel=ylabel,
                      numpoints=numpoints, data_kws=data_kws,
                      fit_kws=fit_kws, init_kws=init_kws, ax_kws=ax_fit_kws,
                      show_init=show_init, parse_complex=parse_complex,
                      title=title)
        self.plot_residuals(ax=ax_res, datafmt=datafmt, yerr=yerr,
                            data_kws=data_kws, fit_kws=fit_kws,
                            ax_kws=ax_res_kws, parse_complex=parse_complex,
                            title=title)
        plt.setp(ax_res.get_xticklabels(), visible=False)
        ax_fit.set_title(self.model.label)
        # make a table with stats
        fig.patch.set_visible(False)
        ax_table.axis('off')
        ax_table.axis('tight')

        df = self.getAllResultsAsDataFrame()

        table = ax_table.table(cellText=df.values, colLabels=df.columns,  loc='center')
        table.auto_set_font_size(False) #or plots very tiny
        table.set_fontsize(5)
        fig.tight_layout()

        if showPlot:
            plt.show()
        return fig


    ## ~~~~~~~~~ Uncertainties Estimation Methods~~~~~~~~~

    def _newParametersFromUncertainties(self, paramSamples):
        """
        Make a new Parameters from the uncertainties of parameters from the sampled values.
        :param paramSamples: A defaultdict of lists where each key is a parameter name and each value is a list of sampled values.
        :return: A Parameters object with the newly calculated parameters values and uncertainties.
        """
        newParams = Parameters()
        for name, values in paramSamples.items():
            param = Parameter(name=name, value=np.median(values))
            param.stderr = np.std(values)
            newParams.add_many(param)
        return newParams

    def _updateStdErr(self, paramSamples):
        """
        Update the stdErr in Parameters from the uncertainties of parameters from the sampled values.
        :param paramSamples: A defaultdict of lists where each key is a parameter name and each value is a list of sampled values.
        :return: A Parameters object with the newly calculated parameters values and uncertainties.
        """
        for name, values in paramSamples.items():
            param = self.params.get(name)
            if param is None:
                continue
            param.stderr = np.std(values)
        return self.params

    @staticmethod
    def _getSyntheticY(y, best_fit, residuals, noiseScale=0.5, seed=None):
        """
        Generate synthetic data (syntheticY) based on the model's best fit and its residuals.

        This method is used in parametric error estimation and Monte Carlo simulations to create synthetic datasets
        that mimic the variability in the observed data. By introducing noise, it allows for the estimation of uncertainties
        in model parameters under different scenarios. This is a conventional method, though there are other approaches.

        :param y: Array-like, the original observed data.
        :param best_fit: Array-like, the model's best-fit values corresponding to y.
        :param residuals: Array-like, the residuals (differences between observed data and best fit).
        :param noiseScale: Float, scaling factor for the noise added to the synthetic data (default is 0.5).
        :param seed: Integer, seed for the random number generator to ensure reproducibility (default is None).
        :return: Array-like, synthetic dataset with noise added.
        """
        if seed is not None:
            np.random.seed(seed)
        syntheticY = best_fit + np.random.normal(0, noiseScale * np.std(residuals), size=len(y))
        return syntheticY

    def covMatrixUncertaintiesEstimation(self, *args, **kwargs):
        """The default method for LMFIT just for explicit access and documentation. This method give the same result as param.sterr.
        In lmfit, the default method for calculating the standard errors (sterr) of the model parameters is  based on the covariance matrix of the parameters.
        The covariance matrix of the parameter estimates is computed as part of the fitting process. This matrix reflects the estimated variances and covariances between parameters.
        The standard errors for each parameter are derived from the diagonal elements of the covariance matrix. Specifically: the standard error for each parameter is the square root of the corresponding diagonal element of the covariance matrix.
        The standard error (sterr) for parameter  p_i  is given by  \text{SE}(p_i) = \sqrt{\text{Cov}(p_i, p_i)} .
        """
        return self.params

    def monteCarloUncertaintiesEstimation(self, x, y, nSamples=1000, noiseScale=0.5, nonParametric=None, **kwargs):
        """
        Perform Monte Carlo error estimation on model parameters.
        :param x:  (array-like): The independent variable data.
        :param y: (array-like): The dependent variable data.
        :param nSamples: (int, optional): The number of Monte Carlo samples to generate. Default is 1000.
        :param noiseScale: (float, optional): A scaling factor for the noise added to the synthetic data.
                                      This scales the standard deviation of the noise based on residuals. Default is 1.
        :return: The Parameters obj with the newly calculated parameters values
        """
        paramSamples = defaultdict(list)
        bestFitResult = None
        bestR2 = -np.inf
        for _ in range(nSamples):
            syntheticY =  self._getSyntheticY(y, self.best_fit, self.residual, noiseScale=noiseScale)
            syntheticResult = self.model.fit(syntheticY, self.params, x=x, nan_policy=self.nan_policy)
            if syntheticResult.redchi is not None:
                syntheticResult.r2 = r2 = rSQR_func(redchi=syntheticResult.redchi, y=y)
                if r2 > bestR2: # Check if this is the best fit so far
                    bestR2 = r2
                    bestFitResult = syntheticResult
            for name, param in syntheticResult.params.items():
                paramSamples[name].append(param.value)
        if bestFitResult is not None:
            self._simulatedParams = bestFitResult.params # _update ResultParams From BestFit
        return self._updateStdErr(paramSamples)

    def jackKnifeUncertaintiesEstimation(self, x, y, nSamples=1000, noiseScale=0.5,  nonParametric=True,  fraction=0.1, **kwargs):
        """
        Perform Jackknife error estimation on model parameters by leaving out a fraction of the data.
        :param x: (array-like): The independent variable data.
        :param y: (array-like): The dependent variable data.
        :param nSamples: (int, optional): The number of Jackknife samples to generate. Default is 10.
        :param fraction: (float, optional): The fraction of the dataset to leave out for each Jackknife iteration. Default is 0.2.
        :param method: (str, optional): The method to use for error estimation. 'non-parametric' or 'parametric'. Default is 'non-parametric'.
        :return: The Parameters object with the newly calculated parameters values.
        """
        n = len(y)
        nLeaveOut = max(1, int(fraction * n))  # Number of data points to leave out in each iteration
        paramSamples = defaultdict(list)
        bestFitResult = None
        bestR2 = -np.inf
        if nonParametric: # Classic or default behaviour
            for _ in range(nSamples):
                # Generate a Jackknife sample by leaving out a fraction of the data points
                indicesToLeaveOut = np.random.choice(n, nLeaveOut, replace=False)
                jackknifeX = np.delete(x, indicesToLeaveOut)
                jackknifeY = np.delete(y, indicesToLeaveOut)
                syntheticResult = self.model.fit(jackknifeY, self.params, x=jackknifeX, nan_policy=self.nan_policy)
                if syntheticResult.redchi is not None:
                    syntheticResult.r2 = r2 = rSQR_func(redchi=syntheticResult.redchi, y=y)
                    if r2 > bestR2:  # Check if this is the best fit so far
                        bestR2 = r2
                        bestFitResult = syntheticResult
                for name, param in syntheticResult.params.items():
                    paramSamples[name].append(param.value)

        else: # nonParametric
            for _ in range(nSamples):
                # Generate Jackknife sample by leaving out a fraction of the data points
                indicesToLeaveOut = np.random.choice(n, nLeaveOut, replace=False)
                jackknifeX = np.delete(x, indicesToLeaveOut)
                jackknifeY = np.delete(y, indicesToLeaveOut)
                bestFit = np.delete(self.best_fit , indicesToLeaveOut)
                # then add noise like for MonteCarlo
                syntheticY = self._getSyntheticY(jackknifeY, bestFit, self.residual, noiseScale=noiseScale)
                syntheticResult = self.model.fit(syntheticY, self.params, x=jackknifeX, nan_policy=self.nan_policy)
                if syntheticResult.redchi is not None:
                    syntheticResult.r2 = r2 = rSQR_func(redchi=syntheticResult.redchi, y=y)
                    if r2 > bestR2:  # Check if this is the best fit so far
                        bestR2 = r2
                        bestFitResult = syntheticResult
                for name, param in syntheticResult.params.items():
                    paramSamples[name].append(param.value)
        if bestFitResult is not None:
            self._simulatedParams = bestFitResult.params  # _update ResultParams From BestFit
        return self._updateStdErr(paramSamples)

    def bootstrapUncertaintiesEstimation(self, x, y, nSamples=1000, noiseScale=0.5, nonParametric=True, **kwargs):
        """
        Perform bootstrap error estimation on model parameters.
        :param x: (array-like): The independent variable data.
        :param y: (array-like): The dependent variable data.
        :param nSamples: (int, optional): The number of bootstrap samples to generate. Default is 1000.
        :param nonParametric: (bool, optional): The bootstrap method to use. True for non-parametric bootstrapping,
                                          False for parametric bootstrapping. Default is 'non-parametric'.
        :return: The Parameters object with the newly calculated stderr values.
        """
        paramSamples = defaultdict(list)
        bestFitResult = None
        bestR2 = -np.inf
        if nonParametric: # Classic or default behaviour
            for _ in range(nSamples):
                # Generate bootstrap sample by resampling the data points
                indices = np.random.choice(len(y), size=len(y), replace=True)
                bootstrapX = x[indices]
                bootstrapY = y[indices]
                syntheticResult = self.model.fit(bootstrapY, self.params, x=bootstrapX, nan_policy=self.nan_policy)
                if syntheticResult.redchi is not None:
                    syntheticResult.r2 = r2 = rSQR_func(redchi=syntheticResult.redchi, y=y)
                    if r2 > bestR2:  # Check if this is the best fit so far
                        bestR2 = r2
                        bestFitResult = syntheticResult
                for name, param in syntheticResult.params.items():
                    paramSamples[name].append(param.value)

        else:
            for _ in range(nSamples):
                syntheticY = self._getSyntheticY(y, self.best_fit, self.residual, noiseScale=noiseScale)
                syntheticResult = self.model.fit(syntheticY,  self.params, x=x, nan_policy=self.nan_policy)
                if syntheticResult.redchi is not None:
                    syntheticResult.r2 = r2 = rSQR_func(redchi=syntheticResult.redchi, y=y)
                    if r2 > bestR2:  # Check if this is the best fit so far
                        bestR2 = r2
                        bestFitResult = syntheticResult
                for name, param in syntheticResult.params.items():
                    paramSamples[name].append(param.value)
        if bestFitResult is not None:
            self._simulatedParams = bestFitResult.params  # update ResultParams From BestFit
        return self._updateStdErr(paramSamples)

