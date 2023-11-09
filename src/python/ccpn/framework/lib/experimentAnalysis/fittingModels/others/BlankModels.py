"""
This module defines Blank Models for Series Analysis
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-09 09:49:31 +0000 (Thu, November 09, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from ccpn.core.DataTable import TableFrame
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult,\
    CalculationModel
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf


class BlankCalculationModel(CalculationModel):
    """
    Blank Calculation model for Series Analysis
    """

    ModelName = sv.BLANKMODELNAME
    Info = 'Blank Model'
    Description = 'A blank model containing no calculation. This will show only raw data.'
    _minimisedProperty = None

    def calculateValues(self, inputDataTables):
        """Return a frame with Collection Pids and value/error as Nones"""
        inputData = self._getFirstData(inputDataTables)
        outputFrame = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        outputFrame.loc[outputFrame.index, self.modelArgumentNames] = None
        return outputFrame

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
          These names will appear as column headers in the output result frames. """
        return [sv.VALUE, sv.VALUE_ERR]



##### Fitting Model

class BlankMinimiser(MinimiserModel):
    """
    Blank Minimiser which fits a blank function!. Used as space-holder/example
    """

    FITTING_FUNC = lf.blank_func
    Astr = sv.ARGA  # They must be exactly as they are defined in the FITTING_FUNC arguments!
    Bstr = sv.ARGB

    defaultParams = {Astr:np.nan,
                     Bstr:np.nan}

    def __init__(self, **kwargs):
        super().__init__(BlankMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        return self.params

class BlankFittingModel(FittingModelABC):
    """
    Blank model which fits a blank function!. Used as space-holder/example
    """
    ModelName = sv.BLANKMODELNAME
    Info = 'Fit data to using the Blank model.'
    Description = ' ... '
    References = ''' None
                '''
    MaTex = ''
    Minimiser = BlankMinimiser
    PeakProperty = None
    _minimisedProperty = None

    def fitSeries(self, inputData: TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        getLogger().warning(sv.UNDER_DEVELOPMENT_WARNING)
        getLogger().info('Performing a blank fitting model. No new output expected.')

        if sv.ISOTOPECODE not in inputData.columns:
            raise RuntimeError(f'Impossible to perform any fitting routine. Missing {sv.ISOTOPECODE} mandatory colum ')

        minimiser = self.Minimiser()
        params = minimiser.params
        outputFrame = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        result = MinimiserResult(minimiser, params) #Don't do the fitting. Just return a mock of results as np.nan
        for resultName, resulValue in result.getAllResultsAsDict().items():
            outputFrame.loc[outputFrame.index, resultName] = resulValue
            outputFrame.loc[outputFrame.index, sv.MODEL_NAME] = self.ModelName
            outputFrame.loc[outputFrame.index, sv.MINIMISER_METHOD] = minimiser.method

        return outputFrame



