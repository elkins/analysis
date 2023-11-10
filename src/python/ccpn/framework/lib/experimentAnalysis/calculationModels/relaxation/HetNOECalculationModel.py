"""

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
__dateModified__ = "$dateModified: 2023-11-10 17:12:50 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.DataEnum import DataEnum
from lmfit.models import update_param_vals
import numpy as np
import pandas as pd
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import N15gyromagneticRatio, HgyromagneticRatio
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import ETAOutputFrame, HetNoeOutputFrame, R2R1OutputFrame, RSDMOutputFrame


class HetNoeDefs(DataEnum):
    """
    Definitions used for converting one of  potential variable name used to
    describe a series value for the HetNOE spectrumGroup, e.g.: 'saturated' to 1.
    Series values can be int/float or str.
    Definitions:
        The unSaturated condition:  0 or one of  ('unsat', 'unsaturated', 'nosat', 'noNOE')
        the Saturated: 1 or  one of  ('sat',  'saturated', 'NOE')
    see  ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables for variables

    """

    UNSAT = 0,  sv.UNSAT_OPTIONS
    SAT = 1, sv.SAT_OPTIONS

    @staticmethod
    def getValueForDescription(description: str) -> int:
        """ Get a value as int for a description if  is present in the list of possible description for the DataEnum"""
        for value, descriptions in zip(HetNoeDefs.values(), HetNoeDefs.descriptions()):
            _descriptions = [str(i).lower() for i in descriptions] + [str(value)]
            if str(description).lower() in _descriptions:
                return value

        errorMessage = f'''Description "{description}" not recognised as a HetNOE series value. Please use one of {HetNoeDefs.descriptions()}'''
        getLogger().warning(errorMessage)

class HetNoeCalculation(CalculationModel):
    """
    Calculate HeteroNuclear NOE Values
    """
    modelName = sv.HETNOE
    targetSeriesAnalyses = [sv.RelaxationAnalysis]

    modelInfo        = '''Calculate HeteroNuclear NOE Values using peak Intensity (Height or Volume).
    Define your series value with 0 for the unsaturated experiment while 
    use the value 1 for the saturated experiment '''

    description = '''Model:
                  HnN = I_Sat / I_UnSat
                  Sat = Peak Intensity for the Saturated Spectrum;
                  UnSat = Peak Intensity for the UnSaturated Spectrum, 
                  Value Error calculated as:
                  error = factor * √SNR_Sat^-2 + SNR_UnSat^-2
                  factor = I_Sat/I_UnSat'''
    references  = '''
                1) Kharchenko, V., et al. Dynamic 15N{1H} NOE measurements: a tool for studying protein dynamics. 
                J Biomol NMR 74, 707–716 (2020). https://doi.org/10.1007/s10858-020-00346-6
                '''
    # MaTex       = r'$I_{Sat} / I_{UnSat}$'
    
    peakProperty = sv._HEIGHT
    _allowedIntensityTypes = (sv._HEIGHT, sv._VOLUME)
    _minimisedProperty = None
    _disableFittingModels = True  # Don't apply any fitting models to this output frame

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
            These names will appear as column headers in the output result frames. """
        return [sv.HETNOE_VALUE, sv.HETNOE_VALUE_ERR]

    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        :param inputDataTables: Generic input DataFrames created from the SeriesAnalysisABC "newInputDataTableFromSpectrumGroup"
        :return: outputFrame. A new outputframe with the required Columns defined by the modelArgumentNames
        """
        inputData = self._getFirstInputDataTable(inputDataTables)
        outputFrame = self._getHetNoeOutputFrame(inputData)
        return outputFrame

    #########################
    ### Private functions ###
    #########################

    def _convertNoeLabelToInteger(self, inputData):
        """ Convert a label 'sat' to ones  and 'unsat' to zeros"""

        satDef = HetNoeDefs(1)
        unsatDef = HetNoeDefs(0)
        # df = inputData #.copy()
        inputData[sv.SERIES_STEP_X_label] =  inputData[self.xSeriesStepHeader]
        for i, row in inputData.iterrows():
            seriesStep = row[self.xSeriesStepHeader]
            seriesStepIndex = HetNoeDefs.getValueForDescription(seriesStep)
            noeDef = HetNoeDefs(seriesStepIndex)
            if noeDef.value == satDef.value:
                inputData.loc[i, self.xSeriesStepHeader] = satDef.value
            if noeDef.value == unsatDef.value:
                inputData.loc[i, self.xSeriesStepHeader] = unsatDef.value
        return inputData

    def _getHetNoeOutputFrame(self, inputData):
        """
        Calculate the HetNoe for an input SeriesTable.
        The non-Sat peak is the first in the SpectrumGroup series.
        :param inputData: SeriesInputFrame
        :return: outputFrame (HetNoeOutputFrame)
        """
        unSatIndex = 0 
        satIndex = 1
        outputFrame = HetNoeOutputFrame()
    
        ## Keep only one IsotopeCode as we are using only 15N
        # TODO remove hardcoded 15N
        inputData = inputData[inputData[sv.ISOTOPECODE] == '15N']
        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])

        for collectionId, groupDf in grouppedByCollectionsId:
            groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
            seriesValues = groupDf[self.peakProperty]

            ## make the calculation required by the model
            satPeakSNR = groupDf[sv._SNR].values[satIndex]
            unSatPeakSNR = groupDf[sv._SNR].values[unSatIndex]
            unSatValue = seriesValues.values[unSatIndex]
            satValue = seriesValues.values[satIndex]
            ratio = satValue / unSatValue
            error = lf.peakErrorBySNRs([satPeakSNR, unSatPeakSNR], factor=ratio, power=-2, method='sum')

            ##  Build the outputFrame
            for i in range(2):
                ## 1) step: add the new results to the frame
                rowIndex = f'{collectionId}_{i}'
                outputFrame.loc[rowIndex, self.modelArgumentNames[0]] = ratio
                outputFrame.loc[rowIndex, self.modelArgumentNames[1]] = error

                ## 2) step: add the model metadata
                outputFrame.loc[rowIndex, sv.CALCULATION_MODEL] = self.modelName

                ## 3) step: add all the other columns as the input data
                firstRow = groupDf.iloc[i]
                outputFrame.loc[rowIndex, firstRow.index.values] = firstRow.values
                nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf) # join the atom names from different rows in a list
                outputFrame.loc[rowIndex, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames)>0 else ''

        return outputFrame
