"""
This module contains dateFrames examples used in the Series Analysis tools
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
__dateModified__ = "$dateModified: 2024-10-03 09:42:40 +0100 (Thu, October 03, 2024) $"
__version__ = "$Revision: 3.2.9.alpha $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv


def getRelaxationInputFrameExample():
    from ccpn.framework.lib.experimentAnalysis.SeriesTables import RelaxationInputFrame
    SERIESSTEPS = [0, 5, 10, 15, 20, 25, 30]
    SERIESUNITS = 's'
    _assignmentValues = [['A', '1', 'ALA', 'H'], # row 1
                         ['A', '1', 'ALA', 'H']]  # row 2

    _seriesValues = [[1000, 550, 316, 180, 85, 56, 31], # row 1
                    [1005, 553, 317, 182, 86, 55, 30]]  # row 2

    df = RelaxationInputFrame()
    df.setSeriesSteps(SERIESSTEPS)
    df.setSeriesUnits(SERIESUNITS)
    df.setAssignmentValues(_assignmentValues)
    df.setSeriesValues(_seriesValues)
    df.build()
    return df

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
    from ccpn.framework.lib.experimentAnalysis.backends.ChemicalShiftPerturbationAnalysis import ChemicalShiftPerturbationAnalysisBC
    csm = ChemicalShiftPerturbationAnalysisBC(application)
    da = csm.newDataTableFromSpectrumGroup(project.spectrumGroups[0],dataTableName='CSM')
    csm.setAlphaFactor(N=0.143)
    csm.addInputDataTable(da)


def _testCSMCalcData():
    """Test the DeltaDelta calculation in the CSM deltaDelta model """
    df = getCSMInputFrameExample()
    from ccpn.framework.lib.experimentAnalysis.fittingModels.binding.SaturationModels import EuclideanCalculationModel
    deltaDeltaModel = EuclideanCalculationModel(alphaFactors=(1, 0.102))
    outputFrame = deltaDeltaModel.fitSeries(df)
    print(outputFrame)



if __name__ == "__main__":

    # relaxationInputFrame = getRelaxationInputFrameExample()
    # print(relaxationInputFrame)
    _testCSMCalcData()




