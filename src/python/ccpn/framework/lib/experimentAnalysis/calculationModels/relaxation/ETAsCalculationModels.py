"""
Calculation models for ETAs experiments. HSQCs and Trosy methods
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
__dateModified__ = "$dateModified: 2023-11-13 10:25:55 +0000 (Mon, November 13, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
import ccpn.framework.lib.experimentAnalysis.calculationModels._libraryFunctions as lf
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import ETAOutputFrame, R2R1OutputFrame


class ETACalculation(CalculationModel):
    """
    Calculate ETA Values for HSQC series
    """
    modelName =sv.ETAS_CALCULATION_MODEL
    targetSeriesAnalyses = [sv.RelaxationAnalysis]

    modelInfo = ''''''

    description = '''Model:
    Measure cross-correlation rates by calculating the ratio of two separate series: in-phase (IP) and anti-phase (AP) (IP/AP) 
                 '''
    references = '''
              1) Direct measurement of the 15 N CSA/dipolar relaxation interference from coupled HSQC spectra. 
              Jennifer B. Hall , Kwaku T. Dayie & David Fushman. Journal of Biomolecular NMR, 26: 181–186, 2003
                '''
    
    peakProperty = sv._HEIGHT
    _allowedIntensityTypes = (sv._HEIGHT, sv._VOLUME)
    _minimisedProperty = modelName

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
            These names will appear as column headers in the output result frames.
            This model does not have argument names. """

        return []

    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        This model requires two inputDataTables created using the  In-phase and Anti-phase spectrumGroups.
        :param inputDataTables: Generic input DataFrames created from the SeriesAnalysisABC "newInputDataTableFromSpectrumGroup"
        :return: outputFrame. A new outputframe with the required Columns defined by the modelArgumentNames
        """
        if not len(inputDataTables) == 2:
            getLogger().warning('This model requires two inputDataTables created using the  In-phase and Anti-phase spectrumGroups.')
            return ETAOutputFrame()
        outputFrame = self._getOutputFrame(inputDataTables)
        return outputFrame

    #########################
    ### Private functions ###
    #########################

    def _getOutputFrame(self, inputDataTables):
        """

        :param inputData: SeriesInputFrame
        :return: outputFrame
        """

        _IP = '_IP'  # in-phase suffix
        _AP = '_AP'  # anti-phase suffix
        PHASE = 'PHASE'
        
        inPhaseData = inputDataTables[0].data
        antiPhaseData = inputDataTables[1].data
        outputFrame = ETAOutputFrame()
        inPhaseData.loc[inPhaseData.index, PHASE] = _IP
        antiPhaseData.loc[antiPhaseData.index, PHASE]  = _AP
        inputData = pd.concat([inPhaseData, antiPhaseData], ignore_index=True)
        ## Keep only one IsotopeCode as we are using only 15N
        inputData = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        isSeriesAscending = all(inputData.get(sv._isSeriesAscending, [False]))
        groupped = inputData.groupby(sv.GROUPBYAssignmentHeaders)
        index = 1
        for ix, groupDf in groupped:
            inphase = groupDf[groupDf[PHASE] == _IP]
            antiphase = groupDf[groupDf[PHASE] == _AP]
            # makesure the sorting is correct

            groupDf.sort_values([self.xSeriesStepHeader], inplace=True, ascending=isSeriesAscending)
            xs = []
            ys = []

            for (inx, iphase), (anx, aphase) in zip(inphase.iterrows(), antiphase.iterrows()):
                inphaseValue = iphase[self.peakProperty]
                antiphaseValue = aphase[self.peakProperty]
                inphaseSNR = iphase[sv._SNR]
                antiphaseSNR = aphase[sv._SNR]
                ratio = inphaseValue / antiphaseValue
                error = lf.peakErrorBySNRs([inphaseSNR, antiphaseSNR], factor=ratio, power=-2, method='sum')
                # build the outputFrame
                # nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf)  # join the atom names from different rows in a list
                seriesUnits = groupDf[sv.SERIESUNIT].unique()
                # outputFrame.loc[collectionId, sv.COLLECTIONID] = collectionId
                outputFrame.loc[index, sv.PEAKPID] = groupDf[sv.PEAKPID].values[0]
                outputFrame.loc[index, sv.COLLECTIONID] = groupDf[sv.COLLECTIONID].values[-1]
                outputFrame.loc[index, sv.COLLECTIONPID] = groupDf[sv.COLLECTIONPID].values[-1]
                outputFrame.loc[index, sv.NMRRESIDUEPID] = groupDf[sv.NMRRESIDUEPID].values[-1]
                outputFrame.loc[index, sv.SERIESUNIT] = seriesUnits[-1]
                outputFrame.loc[index, sv.CROSSRELAXRATIO_VALUE] = ratio
                outputFrame.loc[index, sv.CROSSRELAXRATIO_VALUE_ERR] = error
                outputFrame.loc[index, sv.SERIES_STEP_X] = iphase[sv.SERIES_STEP_X]
                outputFrame.loc[index, sv.SERIES_STEP_Y] = ratio
                outputFrame.loc[index, sv.ISOTOPECODE] =  iphase[sv.ISOTOPECODE]

                xs.append(iphase[sv.SERIES_STEP_X])
                ys.append(ratio)
                outputFrame.loc[index, sv.CALCULATION_MODEL] = self.modelName
                outputFrame.loc[index, sv.GROUPBYAssignmentHeaders] = \
                    groupDf[sv.GROUPBYAssignmentHeaders].values[0]
                outputFrame.loc[index, sv.NMRATOMNAMES] = 'H,N'
                index += 1
        return outputFrame


class RexViaTrosyCalculation(CalculationModel):
    """
    Calculate the Rex value through the 15N TROSY-selected Hahn-echo experiments
    """
    modelName = sv.REXVIATROSY
    modelInfo = '''Calculate the Rex value through the 15N TROSY-selected Hahn-echo experiments.
    This model can be used to map chemical exchange values in proteins with MW > 50 kD.
    '''

    description = f'''Model:
                  '''
    references = '''
    Mapping chemical exchange in proteins with MW > 50 kD. 2003 Jul 30;125(30):8968-9.
    doi: 10.1021/ja035139z. 
     '''
    
    _disableFittingModels = True  # Don't apply any fitting models to this output frame
    _minimisedProperty = None

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
            These names will appear as column headers in the output result frames. """
        return [sv.REX, sv.REX_ERR]


    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        :param inputDataTables:
        :return: outputFrame
        """
        r1Data = None
        r2Data = None
        xyAData = None
        xyBData = None
        zData = None

        datas = [dt.data for dt in inputDataTables]
        for data in datas:
            experiment = data[sv.EXPERIMENT].unique()[-1]
            if experiment == sv.T1:
                r1Data = data
            if experiment == sv.T2:
                r2Data = data
            if experiment == sv.TROSY_XYA:
                xyAData = data
            if experiment == sv.TROSY_XYB:
                xyBData = data
            if experiment == sv.TROSY_Z:
               zData = data

        errorMess = 'Cannot compute model. Ensure the input data contains the %s experiment. '
        if r1Data is None:
            raise RuntimeError(errorMess % sv.T1)
        if r2Data is None:
            raise RuntimeError(errorMess % sv.T2)
        if xyAData is None:
            raise RuntimeError(errorMess % sv.TROSY_XYA)
        if xyBData is None:
            raise RuntimeError(errorMess % sv.TROSY_XYB)
        if zData is None:
            raise RuntimeError(errorMess % sv.TROSY_Z)

        # get the Rates per nmrResidueCode  for each table\
        r1df = r1Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
        r1df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
        r1df.sort_index(inplace=True)

        r2df = r2Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
        r2df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
        r2df.sort_index(inplace=True)

        suffix1 = f'_{sv.R1}'
        suffix2 = f'_{sv.R2}'
        merged = pd.merge(r1df, r2df, on=[sv.NMRRESIDUEPID], how='left', suffixes=(suffix1, suffix2))

        rate1 = f'{sv.RATE}{suffix1}'
        rate2 = f'{sv.RATE}{suffix2}'

        r1 = merged[rate1].values
        r2 = merged[rate2].values
        er1 = merged[f'{sv.RATE_ERR}{suffix1}'].values
        er2 = merged[f'{sv.RATE_ERR}{suffix2}'].values

        ##  calculate the intensity ratios and errors

        ##  calculate the trimmed R2

        ## calculate the NXY value
        ## calculate the Z value
        ## calculate the Rex value

        # clean up suffixes
        merged.columns = merged.columns.str.rstrip(suffix1)
        columnsToDrop = [c for c in merged.columns if suffix2 in c]
        merged.drop(columns=columnsToDrop, inplace=True)

        # keep these columns: MERGINGHEADERS, ROW_UID
        # make the merged dataFrame the correct output type
        outputFrame = R2R1OutputFrame()
        # add the new calculated values
        for hh in sv.MERGINGHEADERS:
            outputFrame[hh] = merged[hh].values

        outputFrame[sv.REX] = None #todo
        outputFrame[sv.REX_ERR] = None #todo

        outputFrame[sv._ROW_UID] = merged[sv._ROW_UID].values
        outputFrame[sv.PEAKPID] = merged[sv.PEAKPID].values
        outputFrame[sv.SERIES_STEP_X] = None
        outputFrame[sv.SERIES_STEP_Y] = None
        outputFrame[sv.CONSTANT_STATS_OUTPUT_TABLE_COLUMNS] = None
        outputFrame[sv.SpectrumPropertiesHeaders] = None
        outputFrame[sv.PeakPropertiesHeaders] = None
        outputFrame[sv.CALCULATION_MODEL] = self.modelName
        return outputFrame

