from abc import ABC, abstractmethod
import numpy as np
from lmfit import Parameter, Parameters
from tqdm import tqdm
from scipy.stats import norm

class ParameterUncertaintyEstimation(ABC):
    """
    Abstract base class for parameter uncertainty estimation.
    """
    name = 'ParameterUncertaintyEstimation'
    shortDescription = ''
    paramScaleVariation = 0.10 # percentage of allowance for generating random samples values
    _constraintRandomVariation = True
    parameterUncertaintiesFunc = np.std
    parameterValueFunc = np.median
    minimiseOptions = {'ftol'   : 1e-9,
                                   'xtol'   : 1e-9,
                                   'gtol'   : 1e-9,
                                   'maxfev' : 100000,
                                   'verbose': True}

    def __init__(self, minimiserCls, params, objectiveFunc, minimiserMethod, nSamples, **minimiserKwargs):
        """
        Initialize the ParameterUncertaintyEstimation.

        :param minimiserCls: The class of the minimiser (e.g., lmfit.Minimizer).
        :param params: The lmfit Parameters object containing the optimized parameters.
        :param objectiveFunc: The objective function to be minimized.
        :param minimiserMethod: The minimization method (e.g., 'leastsq', 'nelder', etc.).
        :param nSamples: Number of samples (iterations).
        :param minimiserKwargs: Additional keyword arguments for the minimizer.

        minimiseOptions:
                ftol: This sets the tolerance of the change in the objective function value between iterations. The optimization will stop when the change in the objective function is less than ftol.
                xtol: This sets the tolerance for the change in the parameter values between iterations. The optimization will stop when the relative change in the parameters is less than xtol.
                gtol: This sets the tolerance for the gradient of the objective function. The optimization will stop when the maximum absolute gradient component is less than gtol.
                maxfev: This sets the maximum number of function evaluations allowed during the optimization. If the optimization reaches this limit, it will stop even if the convergence criteria (ftol, xtol, gtol) are not met.
                verbose: If True, it prints messages about the progress of the optimization.
                These options help control the convergence criteria and the maximum number of iterations for the optimization algorithm.
                Adjusting these values can affect the speed and accuracy of the optimization process.
                The default values  (1e-9 for ftol, xtol, gtol, 10000 for maxfev, and True for verbose) are common default values that work well for many cases.
        """

        self.minimiserCls = minimiserCls
        self.params = params
        self.objectiveFunc = objectiveFunc
        self.minimiserMethod = minimiserMethod
        self.minimiserKwargs = minimiserKwargs
        self.nSamples = nSamples
        self._minimiserResults = []


    @abstractmethod
    def estimateUncertainties(self, prefixMessage):
        """
        Abstract method to estimate parameter uncertainties.
        """
        pass

    def createRandomParams(self, *args):
        """
        Create a new lmfit Parameters object with random parameter values within the defined limits.

        :param params: The original lmfit Parameters object.
        :return: The new lmfit Parameters object with random parameter values.
        """
        newParams = Parameters()

        for paramName, param in self.params.items():
            if param.vary == True:
                if param.min is not None and param.max is not None:
                    original_value = param.value
                    percentage = self.paramScaleVariation
                    std_deviation = abs(original_value * percentage)
                    # Generate new value
                    new_value = np.random.normal(original_value, std_deviation)
                    # Set minimum and maximum limits
                    min_value = param.min
                    max_value = param.max
                    # Clip the new value to ensure it stays within the limits
                    paramValue = np.clip(new_value, min_value, max_value)
                else:
                    value = param.value
                    scale = abs(self.paramScaleVariation * value)
                    paramValue = np.random.normal(value, scale)
            else:
                paramValue = param.value

            newParam = Parameter(name=paramName, value=paramValue, min=param.min, max=param.max, vary=param.vary)
            newParams.add_many(newParam)

        return newParams

    def _newResultParams(self, parameterValues, parameterUncertainties):
        # Create new lmfit Parameters object with Monte Carlo uncertainties
        newParams = Parameters()
        for i, (name, param) in enumerate(self.params.items()):
            param = Parameter(name=name, value=parameterValues[i])
            param.stderr = parameterUncertainties[i]
            newParams.add_many(param)
        return newParams

    def getChisqrs(self):
        """get the x2 from all the minimisers"""
        return np.array([mm.chisqr for mm in self._minimiserResults ])


    def getBestFitParams(self):
        """ Go over the minimiserResultClasses and get the resulting params"""
        parameterSamples = np.zeros((len(self.params), self.nSamples))
        for i, minimiserResult in enumerate(self._minimiserResults):
            for j, paramName in enumerate(minimiserResult.params):
                parameterSamples[j, i] = minimiserResult.params[paramName].value

        # Calculate parameter medians and uncertainties from Monte Carlo samples
        parameterValues = np.median(parameterSamples, axis=1)
        parameterUncertainties = np.std(parameterSamples, axis=1)
        newParams = self._newResultParams(parameterValues, parameterUncertainties)
        return newParams


class MonteCarloSimulation(ParameterUncertaintyEstimation):
    """
    Subclass of ParameterUncertaintyEstimation for Monte Carlo simulations.
    """

    name = 'MonteCarlo'
    shortDescription = '''Monte Carlo simulates a system or model many times using random input parameters to estimate its behavior and uncertainty.'''

    def __init__(self, *args, **kwargs):
        """
        Initialize the MonteCarloSimulation.
        """
        super().__init__(*args, **kwargs)


    def estimateUncertainties(self, prefixMessage, **minimiseOptions):
        """
        Perform Monte Carlo simulations for parameter uncertainties.

        :return: The new lmfit Parameters object with Monte Carlo uncertainties.
        """
        self._minimiserResults = []

        for i in tqdm(range(self.nSamples), desc=f'{prefixMessage} Monte Carlo simulations'):
            # Generate random samples around the optimised parameter values
            mcParams = self.createRandomParams()
            # Re-optimize parameters with updated values
            mcMinimizer = self.minimiserCls(self.objectiveFunc, mcParams, method=self.minimiserMethod, **self.minimiserKwargs)
            mcResult = mcMinimizer.minimize(method=self.minimiserMethod, options=self.minimiseOptions)
            self._minimiserResults.append(mcResult)
        # create the new params as for the
        newParams = self.getBestFitParams()
        return newParams


class BootstrapSimulation(ParameterUncertaintyEstimation):
    """
    Subclass of ParameterUncertaintyEstimation for bootstrapping.
    """
    name = 'Bootstrap'
    shortDescription = '''Bootstrap estimates the uncertainty in a statistic from a sample by repeatedly resampling the original data.'''

    def __init__(self, *args,  **kwargs):
        """
        Initialize the BootstrapSimulation.
        """
        super().__init__(*args, **kwargs)

    def createRandomParams(self):
        """
        Create a new lmfit Parameters object with random parameter values within the defined limits.

        :param params: The original lmfit Parameters object.
        :return: The new lmfit Parameters object with random parameter values.
        """
        newParams = Parameters()
        for paramName, param in self.params.items():
            values = [param.value for param in self.params.values()]
            sampleIndices = np.random.choice(len(values), len(values), replace=True)
            bootstrapValues = [values[idx] for idx in sampleIndices]
            bootstrapParam = Parameter(name=paramName, value=bootstrapValues[i])
            # Update limits
            if param.min is not None:
                bootstrapParam.min = param.min
            if param.max is not None:
                bootstrapParam.max = param.max
            newParams.add_many(bootstrapParam)

        return newParams

    def estimateUncertainties(self):
        """
        Perform bootstrapping for parameter uncertainties.
        :return: The new lmfit Parameters object with bootstrapped uncertainties.
        """
        self._minimiserResults = [] # re-initialise the results

        for i in tqdm(range(self.nSamples), desc='Bootstrapping'):
            # Generate bootstrap sample
            bootstrapParams = self.createRandomParams()
            # Re-optimize parameters with bootstrap sample
            bsMinimizer = self.minimiserCls(self.objectiveFunc, bootstrapParams, method=self.minimiserMethod, **self.minimiserKwargs)
            bsResult = bsMinimizer.minimize(method=self.minimiserMethod)
            self._minimiserResults.append(bsResult)

        # create the new params as for the
        newParams = self.getBestFitParams()
        return newParams


class Jackknife(ParameterUncertaintyEstimation):
    """
    Subclass of ParameterUncertaintyEstimation for Jackknife resampling.
    """

    name = 'Jackknife'
    shortDescription = '''Similar to bootstrapping, the jackknife method involves systematically leaving out one observation at a time from the dataset, calculating the statistic of interest each time. 
    The variability in these statistics estimates the uncertainty. '''

    def __init__(self, *args, **kwargs):
        """
        Initialize the Jackknife resampling.
        """
        super().__init__(*args, **kwargs)


    def createRandomParams(self, idx):
        """
        Create a new lmfit Parameters object with the i-th data point removed.

        :param idx: Index of the data point to leave out.
        :return: The new lmfit Parameters object.
        """
        newParams = Parameters()
        for paramName, param in self.params.items():
            if param.min is not None and param.max is not None:
                randValue = np.random.uniform(param.min, param.max)
            else:
                randValue = np.random.normal(param.value, 1.0)

            if paramName != idx:
                newParam = Parameter(name=paramName, value=randValue, min=param.min, max=param.max)
                newParams.add_many(newParam)

        return newParams

    def estimateUncertainties(self):
        """
        Perform Jackknife resampling for parameter uncertainties.
        For each iteration of Jackknife, we leave out one data point, fit the model with the remaining data points, and store the parameter values
        :return: The new lmfit Parameters object with Jackknife uncertainties.
        """
        self._minimiserResults = []

        for i in tqdm(range(len(self.objectiveFunc)), desc='Jackknife Resampling'):
            # Create a new Parameters object with the i-th data point removed
            jackknifeParams = self.createRandomParams(i)
            # Fit the model with the jackknifeParams
            jackknifeMinimizer = self.minimiserCls(self.objectiveFunc, jackknifeParams, method=self.minimiserMethod, **self.minimiserKwargs)
            jackknifeResult = jackknifeMinimizer.minimize(method=self.minimiserMethod)
            self._minimiserResults.append(jackknifeResult)

        # Create the new params based on the minimizer results
        newParams = self.getBestFitParams()
        return newParams



