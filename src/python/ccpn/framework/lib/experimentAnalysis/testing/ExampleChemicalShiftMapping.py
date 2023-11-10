
"""
This module contains Chemical Shift Analysis examples

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
__dateModified__ = "$dateModified: 2023-11-10 15:58:41 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================


import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt


def getCSMInputFrameExample():
    from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMInputFrame
    SERIESSTEPS = [0, 1]
    SERIESUNITS = 'eq'
    _assignmentValues = [
                        ['A', '3', 'VAL', 'H'],     # row 1
                        ['A', '3', 'VAL', 'N'],     # row 2
                        ['A', '4', 'ASP', 'H'],     # row 3
                        ['A', '4', 'ASP', 'N'],     # row 4
                        ['A', '9', 'ARG', 'H'],     # row 5
                        ['A', '9', 'ARG', 'N']      # row 6
                        ]


    _seriesValues = [
                    [8.15842,   8.17385],           # row 1
                    [123.49895, 123.98413],         # row 2
                    [8.26403,   8.26183],           # row 3
                    [124.26134, 124.41618],         # row 4
                    [8.31992,   7.90225],           # row 5
                    [123.35951, 120.79318]          # row 6
                    ]

    df = CSMInputFrame()
    df.setSeriesSteps(SERIESSTEPS)
    df.setSeriesUnits(SERIESUNITS)
    df.setAssignmentValues(_assignmentValues)
    df.setSeriesValues(_seriesValues)
    df.build()
    return df

def getCSMInputFrameExample2():
    from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMInputFrame
    SERIESSTEPS = [0, 0.5, 1.0, 1.5, 2.0]
    SERIESUNITS = 'eq'
    _assignmentValues = [
                        ['A', '73', 'VAL', 'H'],     # row 1
                        ['A', '73', 'VAL', 'N'],     # row 2
                        ]


    _seriesValues = [
                    [ 8.328, 8.244456, 8.190638, 8.164658, 8.147034],           # row 1
                    [118.764, 118.444586, 118.239704, 118.135157, 118.069626],  # row 2
                    ]
    df = CSMInputFrame()
    df.setSeriesSteps(SERIESSTEPS)
    df.setSeriesUnits(SERIESUNITS)
    df.setAssignmentValues(_assignmentValues)
    df.setSeriesValues(_seriesValues)
    df.build()
    return df

def _testCreateCSInputDataFromSpectrumGroup(spectrumGroup):
    # macro level run from a suitable project. Eg. "TstarCompleted" in example Data
    from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMInputFrame
    df = CSMInputFrame()
    df.buildFromSpectrumGroup(spectrumGroup, sv._PPMPOSITION)
    return df


def _testCreateChemicalShiftMappingAnalysisObj():
    from ccpn.framework.lib.experimentAnalysis.backends.ChemicalShiftMappingAnalysis import ChemicalShiftMappingAnalysisBC
    csm = ChemicalShiftMappingAnalysisBC(application)
    da = csm.newDataTableFromSpectrumGroup(project.spectrumGroups[0],dataTableName='CSM')
    csm.setAlphaFactor(N=0.143)
    csm.addInputDataTable(da)


def _testCSMCalcData():
    """Test the DeltaDelta calculation in the CSM deltaDelta model """
    df = getCSMInputFrameExample()
    from ccpn.framework.lib.experimentAnalysis.fittingModels.binding.SaturationModels import EuclideanCalculationModel
    deltaDeltaModel = EuclideanCalculationModel(alphaFactors=(1, 0.102))
    outputFrame = deltaDeltaModel.calculateValues(df)



def oneSiteBindingCurve(x, kd, bmax):
    """
    :param x: 1d array
    :param kd: the initial kd value
    :param bmax:
    :return:
    """
    return (bmax * x) / (x + kd)


def _testOneBindingSiteFitting():

    x = [0. , 0.5 ,1. , 1.5 ,2. ]
    y = [0. , 0.65349544 ,1.09422492 ,1.53495441 ,1.71732523]
    xs = np.array(x)
    ys = np.array(y)

    aFunc = oneSiteBindingCurve

    param = curve_fit(aFunc, xs, ys)
    xhalfUnscaled, bMaxUnscaled = param[0]
    paramScaled = curve_fit(aFunc, xs, ys)
    xf = np.linspace(np.min(xs), np.max(xs)+2, 100)
    yf = aFunc(xf, *paramScaled[0])
    x_atHalf_Y, bmax = paramScaled[0]
    print(x_atHalf_Y, bmax )

    plt.plot(xs, ys, 'o')
    plt.plot(xf, yf)
    plt.show()


if __name__ == "__main__":
    _testCSMCalcData()
    # _testOneBindingSiteFitting()




