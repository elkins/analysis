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
__dateModified__ = "$dateModified: 2023-11-10 16:12:23 +0000 (Fri, November 10, 2023) $"
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
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf

class _BlankMinimiser(MinimiserModel):
    """
    Blank Minimiser which fits a blank function!. Used as space-holder/example
    """

    FITTING_FUNC = lf.blank_func
    Astr = sv.ARGA  # They must be exactly as they are defined in the FITTING_FUNC arguments!
    Bstr = sv.ARGB

    defaultParams = {Astr:np.nan,
                     Bstr:np.nan}

    def __init__(self, **kwargs):
        super().__init__(_BlankMinimiser.FITTING_FUNC, **kwargs)
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
    modelName = sv.BLANKMODELNAME
    TargetSeriesAnalyses = [sv.RelaxationAnalysis,
                                            sv.JCouplingAnalysis,
                                            sv.RDCAnalysis,
                                            sv.PREAnalysis,
                                            sv.PCSAnalysis
                                            ]

    Info = 'Fit data to using the Blank model.'
    Description = ' An empty model used as a placeholder. Does not fit any data.'
    References = ''' None
                '''
    MaTex = ''
    Minimiser = _BlankMinimiser
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
            outputFrame.loc[outputFrame.index, sv.MODEL_NAME] = self.modelName
            outputFrame.loc[outputFrame.index, sv.MINIMISER_METHOD] = minimiser.method

        return outputFrame



