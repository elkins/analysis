"""

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
__dateModified__ = "$dateModified: 2024-09-18 17:27:42 +0100 (Wed, September 18, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import warnings
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMOutputFrame
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.calculationModels._libraryFunctions as lf


def euclideanDistance_func(array1, array2, alphaFactors):
    """
    Calculate the  Euclidean Distance of two set of coordinates using scaling factors. Used in CSM DeltaDeltas
    :param array1: (1d array), coordinate 1
    :param array2: (1d array), coordinate 2 of same shape of array1
    :param alphaFactors: the scaling factors.  same shape of array1 and 2.
    :return: float
    Ref.: Eq.(9) from: M.P. Williamson Progress in Nuclear Magnetic Resonance Spectroscopy 73 (2013) 1–16

    """
    deltas = []
    for a, b, factor in zip(array1, array2, alphaFactors):
        delta = a - b
        delta *= factor
        delta **= 2
        deltas.append(delta)
    return np.sqrt(np.mean(np.array(deltas)))

class EuclideanCalculationModel(CalculationModel):
    """
    ChemicalShift Analysis DeltaDeltas shift distance calculation
    """
    modelName = sv.EUCLIDEAN_DISTANCE
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]
    modelInfo        = 'Calculate The DeltaDelta shifts for a series using the average Euclidean Distance.'
    # maTex       = r'$\sqrt{\frac{1}{N}\sum_{i=0}^N (\alpha_i*\delta_i)^2}$'
    description = f'''Model:
                    d = √ 1/N * ∑(𝝰_i * δ_i)^2
                    {sv.uALPHA}: the alpha factor for each atom of interest
                    i: atom type (isotope code per dimension 1H, 15N...)
                    N: atom count
                    {sv.uDelta}: delta shift per atom in the series
                    (with ∑ i=1 to N)
                    Note peak assignments are not mandatory for the calculation.'''
    references  = '''
                    1) Eq. (9) M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).
                    2) Mureddu, L. & Vuister, G. W. Simple high-resolution NMR spectroscopy as a tool in molecular biology.
                       FEBS J. 286, 2035–2042 (2019).
                  '''
    
    _minimisedProperty = sv.RELDISPLACEMENT

    def __init__(self):
        super().__init__()
        self._alphaFactors = {}
        self._euclideanCalculationMethod = 'mean'

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
          These names will appear as column headers in the output result frames. """
        return [sv.DELTA_DELTA, sv.DELTA_DELTA_ERR]

    def setAlphaFactors(self, values):
        self._alphaFactors = values

    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        Calculate the DeltaDeltas for an input SeriesTable.
        :param inputData: CSMInputFrame
        :return: outputFrame
        """

        outputFrame = CSMOutputFrame()
        outputFrame._buildColumnHeaders()

        inputData = self._getFirstInputDataTable(inputDataTables)

        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])
        rowIndex = 1
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', category=RuntimeWarning)
            while True:
                for collectionId, groupDf in grouppedByCollectionsId:
                    groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
                    dimensions = groupDf[sv.DIMENSION].unique()
                    dataPerDimensionDict = {}
                    for dim in dimensions:
                        dimRow = groupDf[groupDf[sv.DIMENSION] == dim]
                        dataPerDimensionDict[dim] = dimRow[sv._PPMPOSITION].values
                    alphaFactors = []
                    for i in dataPerDimensionDict:  # get the correct alpha factors per IsotopeCode/dimension and not derive it by atomName.
                        ic = groupDf[groupDf[sv.DIMENSION] == i][sv.ISOTOPECODE].unique()[-1]
                        alphaFactors.append(self._alphaFactors.get(ic, 1))
                    values = np.array(list(dataPerDimensionDict.values()))
                    seriesValues4residue = values.T  ## take the series values in axis 1 and create a 2D array. e.g.:[[8.15 123.49][8.17 123.98]]
                    deltaDeltas = EuclideanCalculationModel._calculateDeltaDeltas(seriesValues4residue, alphaFactors)
                    csmValue = np.mean(deltaDeltas[1:])  ## first item is excluded from as it is always 0 by definition.
                    nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf)
                    # seriesSteps = groupDf[self.xSeriesStepHeader].unique() #cannot use unique! Could be series with same value!!
                    seriesUnits = groupDf[sv.SERIESUNIT].unique()
                    seriesAdditionalValue = None
                    if sv.ADDITIONAL_SERIES_STEP_X in groupDf:
                        seriesAdditionalValues = groupDf[sv.ADDITIONAL_SERIES_STEP_X].unique()
                        if seriesAdditionalValues is not None and len(seriesAdditionalValues)>0:
                            seriesAdditionalValue = seriesAdditionalValues[-1]
                    peakPids = groupDf[sv.PEAKPID].unique()
                    snrs = groupDf[sv._SNR].unique()
                    csmValueError = lf.peakErrorBySNRs(snrs, factor=csmValue, power=-2, method='std')
                    for delta, peakPid in zip(deltaDeltas, peakPids):
                        # build the outputFrame
                        peak = self.project.getByPid(peakPid)
                        if not peak:
                            getLogger().warn(f'Cannot find Peak {peakPid}.Skipping...')
                            continue
                        spectrum = peak.spectrum
                        seriesStep = groupDf[groupDf[sv.SPECTRUMPID] == spectrum.pid][sv.SERIES_STEP_X].values[-1]
                        outputFrame.loc[rowIndex, sv.COLLECTIONID] = collectionId
                        outputFrame.loc[rowIndex, sv.PEAKPID] = peakPid
                        outputFrame.loc[rowIndex, sv.COLLECTIONPID] = groupDf[sv.COLLECTIONPID].values[-1]
                        outputFrame.loc[rowIndex, sv.NMRRESIDUEPID] = groupDf[sv.NMRRESIDUEPID].values[-1]
                        outputFrame.loc[rowIndex, sv.SERIES_STEP_Y] = delta
                        outputFrame.loc[rowIndex, self.xSeriesStepHeader] = seriesStep
                        outputFrame.loc[rowIndex, sv.ADDITIONAL_SERIES_STEP_X] = seriesAdditionalValue
                        outputFrame.loc[rowIndex, sv.SERIESUNIT] = seriesUnits[-1]
                        outputFrame.loc[rowIndex, sv.CALCULATION_MODEL] = self.modelName
                        outputFrame.loc[rowIndex, sv.GROUPBYAssignmentHeaders] = \
                        groupDf[sv.GROUPBYAssignmentHeaders].values[0]
                        outputFrame.loc[rowIndex, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames) > 0 else ''
                        if len(self.modelArgumentNames) == 2:
                            for header, value in zip(self.modelArgumentNames, [csmValue, csmValueError]):
                                outputFrame.loc[rowIndex, header] = value
                        rowIndex += 1
                break
        return outputFrame

    @staticmethod
    def _calculateDeltaDeltas(data, alphaFactors):
        """
        :param data: 2D array containing A and B coordinates to measure.
        e.g.: for two HN peaks data will be a 2D array, e.g.: [[  8.15842 123.49895][  8.17385 123.98413]]
        :return: float
        """
        deltaDeltas = []
        origin = data[0] # first set of positions (any dimensionality)
        for coord in data:# the other set of positions (same dim as origin)
            dd = euclideanDistance_func(origin, coord, alphaFactors)
            deltaDeltas.append(dd)
        return deltaDeltas
