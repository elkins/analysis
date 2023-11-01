"""
This module defines base classes for Series Analysis
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
__dateModified__ = "$dateModified: 2023-11-01 20:08:05 +0000 (Wed, November 01, 2023) $"
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
import ccpn.framework.lib.experimentAnalysis.fitFunctionsLib as lf
import ccpn.framework.lib.experimentAnalysis.spectralDensityLib as sdl
from ccpn.framework.lib.experimentAnalysis.experimentConstants import N15gyromagneticRatio, HgyromagneticRatio
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult, CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTablesBC import ETAOutputFrame, HetNoeOutputFrame, R2R1OutputFrame, RSDMOutputFrame

#####################################################
###########        Minimisers        ################
#####################################################

class InversionRecoveryMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'InversionRecoveryMinimiser'
    FITTING_FUNC = lf.inversionRecovery_func
    AMPLITUDEstr = sv.AMPLITUDE
    DECAYstr = sv.DECAY
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        DECAYstr:0.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(InversionRecoveryMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), decay=-1.0/sval)
        return update_param_vals(params, self.prefix, **kwargs)


###########################################################

class OnePhaseDecayMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'OnePhaseDecayMinimiser'
    FITTING_FUNC = lf.onePhaseDecay_func
    AMPLITUDEstr = sv.AMPLITUDE
    RATEstr = sv.RATE
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        RATEstr:1.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(OnePhaseDecayMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), rate=abs(sval))
        return update_param_vals(params, self.prefix, **kwargs)

################

class OnePhaseDecayPlateauMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'OnePhaseDecayPlateauMinimiser'
    FITTING_FUNC = lf.onePhaseDecayPlateau_func
    AMPLITUDEstr = sv.AMPLITUDE
    RATEstr = sv.RATE
    PLATEAUstr = sv.PLATEAU
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        RATEstr:1.5,
                        PLATEAUstr:0
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(OnePhaseDecayPlateauMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)


    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""

        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))

        params = self.make_params(
                amplitude=dict(value=np.exp(oval), min=max(data) / 2, max=max(data) * 2),
                rate=dict(value=abs(sval)),
                plateau=dict(value=min(data), min=None, max=min(data) * 2)
                )
        return update_param_vals(params, self.prefix, **kwargs)


class ExpDecayMinimiser(MinimiserModel):
    """
    A model to fit the time constant in a exponential decay
    """
    MODELNAME = 'ExponentialDecayMinimiser'
    FITTING_FUNC = lf.exponentialDecay_func
    AMPLITUDEstr = sv.AMPLITUDE
    DECAYstr = sv.DECAY
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        DECAYstr:0.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(ExpDecayMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), decay=-1.0/sval)
        return update_param_vals(params, self.prefix, **kwargs)


#####################################################
###########       FittingModel       ################
#####################################################

class _RelaxationBaseFittingModel(FittingModelABC):
    """
    A Base model class for T1/T2
    """
    PeakProperty =  sv._HEIGHT

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        getLogger().warning(sv.UNDER_DEVELOPMENT_WARNING)
        ## Keep only one IsotopeCode as we are using only Height/Volume
        inputData = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        minimisedProperty = self.PeakProperty
        if not self.ySeriesStepHeader in inputData.columns:
            inputData[self.ySeriesStepHeader] = inputData[self.PeakProperty]


        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])
        for collectionId, groupDf in grouppedByCollectionsId:
            groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
            seriesSteps = Xs = groupDf[self.xSeriesStepHeader].values
            seriesValues = Ys = groupDf[self.ySeriesStepHeader].values
            minimiser = self.Minimiser()
            try:
                params = minimiser.guess(Ys, Xs)
                minimiser.setMethod(self._minimiserMethod)
                result = minimiser.fit(Ys, params, x=Xs)
            except:
                getLogger().warning(f'Fitting Failed for collectionId: {collectionId} data. Make sure you are using the right model for your data.')
                params = minimiser.params
                result = MinimiserResult(minimiser, params)

            for ix, row in groupDf.iterrows():
                for resultName, resulValue in result.getAllResultsAsDict().items():
                    inputData.loc[ix, resultName] = resulValue
                inputData.loc[ix, sv.MODEL_NAME] = self.ModelName
                inputData.loc[ix, sv.MINIMISER_METHOD] = minimiser.method
                try:
                    nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf)
                    inputData.loc[ix, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames) > 0 else ''
                except:
                    inputData.loc[ix, sv.NMRATOMNAMES] = ''

        return inputData


class OnePhaseDecayModel(_RelaxationBaseFittingModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    ModelName   = sv.OnePhaseDecay
    Info        = '''A model to describe the rate of a decay.  '''
    Description = '''Model:\nY=amplitude*exp(-rate*X)      
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 rate: the rate constant, expressed in reciprocal of the X axis time units,  e.g.: Second-1.
                  '''
    References  = '''
                  '''
    Minimiser = OnePhaseDecayMinimiser
    FullDescription = f'{Info}\n{Description}'

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.RATEstr

class OnePhaseDecayPlateauModel(_RelaxationBaseFittingModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    ModelName   = sv.OnePhaseDecayWithPlateau
    Info        = '''A model to describe the rate of a decay.  '''
    Description = '''Model:\nY=(amplitude - plateau) *exp(-rate*X) + plateau     
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 rate: the rate constant, expressed in reciprocal of the X axis time units,  e.g.: Second-1
                 plateau: the Y value at infinite times. Same units as Y.
                  '''
    References  = '''
                  '''
    Minimiser = OnePhaseDecayPlateauMinimiser
    FullDescription = f'{Info}\n{Description}'

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.RATEstr


class ExponentialDecayModel(_RelaxationBaseFittingModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    ModelName = sv.ExponentialDecay
    Info = '''A model to describe the time constant of a decay (also known as Tau). '''
    Description = '''Model:\nY=amplitude*exp(-X / decay)

                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 decay: the time constant (Tau), same units as  X axis e.g.: Second.
                  '''
    References = '''
                  '''
    Minimiser = ExpDecayMinimiser
    FullDescription = f'{Info}\n{Description}'

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.DECAYstr

class InversionRecoveryFittingModel(_RelaxationBaseFittingModel):
    """
    InversionRecovery model class containing fitting equation and fitting information
    """
    ModelName = sv.InversionRecovery
    Info = '''Inversion Recovery fitting model. '''
    Description = '''Model:\nY = amplitude * (1 - e^{-time/decay})
    
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 decay: the time constant, same units as  X axis.
                  '''
    References = '''
                  '''
    Minimiser = InversionRecoveryMinimiser
    # MaTex =  r'$amplitude*(1 - e^{-time/decay})$'
    FullDescription = f'{Info}\n{Description}'

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""
        return self.Minimiser.DECAYstr

#####################################################
##########  Calculation Models   ####################
#####################################################

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
    ModelName = sv.HETNOE
    Info        = '''Calculate HeteroNuclear NOE Values using peak Intensity (Height or Volume).
    Define your series value with 0 for the unsaturated experiment while 
    use the value 1 for the saturated experiment '''

    Description = '''Model:
                  HnN = I_Sat / I_UnSat
                  Sat = Peak Intensity for the Saturated Spectrum;
                  UnSat = Peak Intensity for the UnSaturated Spectrum, 
                  Value Error calculated as:
                  error = factor * √SNR_Sat^-2 + SNR_UnSat^-2
                  factor = I_Sat/I_UnSat'''
    References  = '''
                1) Kharchenko, V., et al. Dynamic 15N{1H} NOE measurements: a tool for studying protein dynamics. 
                J Biomol NMR 74, 707–716 (2020). https://doi.org/10.1007/s10858-020-00346-6
                '''
    # MaTex       = r'$I_{Sat} / I_{UnSat}$'
    FullDescription = f'{Info}\n{Description}'
    PeakProperty = sv._HEIGHT
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
        inputData = self._getFirstData(inputDataTables)
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
            seriesValues = groupDf[self.PeakProperty]

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
                outputFrame.loc[rowIndex, sv.CALCULATION_MODEL] = self.ModelName

                ## 3) step: add all the other columns as the input data
                firstRow = groupDf.iloc[i]
                outputFrame.loc[rowIndex, firstRow.index.values] = firstRow.values
                nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf) # join the atom names from different rows in a list
                outputFrame.loc[rowIndex, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames)>0 else ''

        return outputFrame


class ETACalculation(CalculationModel):
    """
    Calculate ETA Values for HSQC series
    """
    ModelName =sv.ETAS_CALCULATION_MODEL
    Info = ''''''

    Description = '''Model:
    Measure cross-correlation rates by calculating the ratio of two separate series: in-phase (IP) and anti-phase (AP) (IP/AP) 
                 '''
    References = '''
              1) Direct measurement of the 15 N CSA/dipolar relaxation interference from coupled HSQC spectra. 
              Jennifer B. Hall , Kwaku T. Dayie & David Fushman. Journal of Biomolecular NMR, 26: 181–186, 2003
                '''
    FullDescription = f'{Info}\n{Description}'
    PeakProperty = sv._HEIGHT
    _allowedIntensityTypes = (sv._HEIGHT, sv._VOLUME)
    _minimisedProperty = ModelName

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
                inphaseValue = iphase[self.PeakProperty]
                antiphaseValue = aphase[self.PeakProperty]
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
                outputFrame.loc[index, sv.CALCULATION_MODEL] = self.ModelName
                outputFrame.loc[index, sv.GROUPBYAssignmentHeaders] = \
                    groupDf[sv.GROUPBYAssignmentHeaders].values[0]
                outputFrame.loc[index, sv.NMRATOMNAMES] = 'H,N'
                index += 1
        return outputFrame

class R2R1RatesCalculation(CalculationModel):
    """
    Calculate R2/R1 rates
    """
    ModelName = sv.R2R1
    Info = '''Calculate the ratio R2/R1.  Requires two input dataTables: the T1, T2 with calculated rates (R1, and R2).'''

    Description = f'''Model:
                  ratio =  R2/R1
                  R1 and R2 the decay rate for the T1 and T2 calculated using the {sv.OnePhaseDecay} model.
                  
                  Value Error calculated as:
                  error =  (Re1/R1 + Re2/R2) * R2/R1
                  Re1/Re2 are the respective rate errors for R1 and R2.
                  '''
    References = '''
                '''
    FullDescription = f'{Info}\n{Description}'
    _disableFittingModels = True  # Don't apply any fitting models to this output frame
    _minimisedProperty = None

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
            These names will appear as column headers in the output result frames. """
        return [sv.R2R1, sv.R2R1_ERR]

    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        :param inputDataTables:
        :return: outputFrame
        """
        r1Data = None
        r2Data = None
        datas = [dt.data for dt in inputDataTables]
        for data in datas:
            experiment = data[sv.EXPERIMENT].unique()[-1]
            if experiment == sv.T1:
                r1Data = data
            if experiment == sv.T2:
                r2Data = data
        errorMess = 'Cannot compute model. Ensure the input data contains the %s experiment. '
        if r1Data is None:
            raise RuntimeError(errorMess %sv.T1)
        if r2Data is None:
            raise RuntimeError(errorMess %sv.T2)

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
        ratesRatio = r2 / r1
        ratesProd = r2 * r1
        ## Error calculated as = (E1/R1 + E2/R2) * R2/R1
        ratesErrorRatio = (er1 / r1 + er2 / r2) * r2 / r1
        r1r2_err = lf.calculateUncertaintiesProductError(r1, r2, er1, er2)

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
        outputFrame[sv.R2R1] = ratesRatio
        outputFrame[sv.R2R1_ERR] = ratesErrorRatio
        outputFrame[sv.R1R2] = ratesProd
        outputFrame[sv.R1R2_ERR] = r1r2_err
        outputFrame[sv._ROW_UID] = merged[sv._ROW_UID].values
        outputFrame[sv.PEAKPID] = merged[sv.PEAKPID].values
        outputFrame[sv.SERIES_STEP_X] = None
        outputFrame[sv.SERIES_STEP_Y] = None
        outputFrame[sv.CONSTANT_STATS_OUTPUT_TABLE_COLUMNS] = None
        outputFrame[sv.SpectrumPropertiesHeaders] = None
        outputFrame[sv.PeakPropertiesHeaders] = None
        outputFrame[sv.CALCULATION_MODEL] = self.ModelName
        return outputFrame


#####  Reduced Spectral Density Mapping (SDM ) ####


class SDMCalculation(CalculationModel):
    """
    Calculate the Spectral density mapping
    """
    ModelName = sv.RSDM
    Info = '''Calculate the Reduced Spectral Density Mapping (SDM). Requires three input dataTables: the T1, T2 with calculated rates and NOE values'''
    Description = f'''Model:
                  Calculates J0, J(ѠX) and J(ѠH) using the R1, R2 and NOE values.
                  Values in sec/rad
                  See references for details
                  '''
    References = '''
                1) Theory: Farrow,  et al. Spectral density function mapping using 15N relaxation data exclusively. J Biomol NMR 6, 153–162 (1995)
                2) Equations: 13-16. Udgaonkar et al. Backbone dynamics of Barstar: A 15N NMR relaxation study.  Proteins: 41:460-474 (2000)
                '''
    FullDescription = f'{Info}\n{Description}'
    _disableFittingModels = True  # Don't apply any fitting models to this output frame
    _spectrometerFrequency = 600.130  # hardcoded for development only. default will be taken from 1st spectrum in a series . todo need a way to set options model specific
    _minimisedProperty = None

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
            These names will appear as column headers in the output result frames. """
        return [sv.J0, sv.JwX, sv.JwH]


    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        :param inputDataTables:
        :return: outputFrame
        """
        r1Data = None
        r2Data = None
        noeData = None
        datas = [dt.data for dt in inputDataTables]
        for data in datas:
            experiment = data[sv.EXPERIMENT].unique()[-1]
            if experiment == sv.T1:
                r1Data = data
            if experiment == sv.T2:
                r2Data = data
            if experiment == sv.HETNOE:
                noeData = data
        errorMess = 'Cannot compute model. Ensure the input data contains the %s experiment. '
        if r1Data is None:
            raise RuntimeError(errorMess % sv.T1)
        if r2Data is None:
            raise RuntimeError(errorMess % sv.T2)
        if noeData is None:
            raise RuntimeError(errorMess % sv.HETNOE)

        # get the Rates per nmrResidueCode  for each table\
        r1df = r1Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
        r1df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
        r1df.sort_index(inplace=True)

        r2df = r2Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
        r2df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
        r2df.sort_index(inplace=True)

        noedf = noeData.groupby(sv.NMRRESIDUEPID).first().reset_index()
        noedf.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
        noedf.sort_index(inplace=True)

        suffix1 = f'_{sv.R1}'
        suffix2 = f'_{sv.R2}'
        suffix3 = f'_{sv.HETNOE}'

        merged1 = pd.merge(r1df, r2df, on=[sv.NMRRESIDUEPID], how='left', suffixes=(suffix1, suffix2))
        merged = pd.merge(merged1, noedf, on=[sv.NMRRESIDUEPID], how='left', )

        rate1 = f'{sv.RATE}{suffix1}'
        rate2 = f'{sv.RATE}{suffix2}'
        noeHeder = sv.HETNOE_VALUE
        noeHederErr = sv.HETNOE_VALUE_ERR

        R1 = merged[rate1].values
        R2 = merged[rate2].values
        NOE = merged[noeHeder].values
        R1_err = merged[f'{sv.RATE_ERR}{suffix1}'].values
        R2_err = merged[f'{sv.RATE_ERR}{suffix2}'].values
        NOE_err = merged[noeHederErr].values
        scalingFactor=1e6
        wN = sdl.calculateOmegaN(self._spectrometerFrequency, scalingFactor)
        csaN = -160 / scalingFactor
        C1 = sdl.calculate_c_factor(wN, csaN)
        D1 = sdl.calculate_d_factor()
        j0 = sdl.calculateJ0(NOE, R1, R2, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)
        jwx = sdl.calculateJWx(NOE, R1, R2, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)
        jwh = sdl.calculateJWH(NOE, R1, R2, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)

        j0_ERR = sdl.calculateJ0(NOE_err, R1_err, R2_err, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)
        jwx_ERR = sdl.calculateJWx(NOE_err, R1_err, R2_err, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)
        jwh_ERR = sdl.calculateJWH(NOE_err, R1_err, R2_err, D1, C1, N15gyromagneticRatio, HgyromagneticRatio)

        # keep these columns: MERGINGHEADERS, ROW_UID
        # make the merged dataFrame the correct output type
        outputFrame = RSDMOutputFrame()
        # add the new calculated values

        outputFrame[sv.J0] = j0
        outputFrame[sv.JwX] = jwx
        outputFrame[sv.JwH] = jwh
        outputFrame[sv.J0_ERR] = j0_ERR
        outputFrame[sv.JwX_ERR] = jwx_ERR
        outputFrame[sv.JwH_ERR] = jwh_ERR

        # include also initial R1,R2,NOE data used in the calculations
        outputFrame[sv.R1] = R1
        outputFrame[sv.R1_ERR] = R1_err
        outputFrame[sv.R2] = R2
        outputFrame[sv.R2_ERR] = R2_err
        outputFrame[sv.HETNOE_VALUE] = NOE
        outputFrame[sv.HETNOE_VALUE_ERR] = NOE_err
        for hh in sv.MERGINGHEADERS:
            outputFrame[hh] = merged[hh].values #use .values otherwise is wrongly done
        outputFrame[sv._ROW_UID] = merged[sv._ROW_UID].values
        outputFrame[sv.PEAKPID] = merged[sv.PEAKPID].values
        outputFrame[sv.SERIES_STEP_X] = None
        outputFrame[sv.SERIES_STEP_Y] = None
        outputFrame[sv.CONSTANT_STATS_OUTPUT_TABLE_COLUMNS] = None
        outputFrame[sv.SpectrumPropertiesHeaders] = None
        outputFrame[sv.PeakPropertiesHeaders] = None
        outputFrame[sv.CALCULATION_MODEL] = self.ModelName

        return outputFrame

#####################################################
###########      Register models    #################
#####################################################
FittingModels            = [
                    OnePhaseDecayModel,
                    OnePhaseDecayPlateauModel,
                    ExponentialDecayModel,
                    InversionRecoveryFittingModel,
                    ]


CalculationModels = [
                    HetNoeCalculation,
                    R2R1RatesCalculation,
                    ETACalculation,
                    SDMCalculation
                    ]




