"""

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-02-29 10:26:55 +0000 (Thu, February 29, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================


import pandas as pd
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import N15gyromagneticRatio, HgyromagneticRatio
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import  RSDMOutputFrame



#####  Reduced Spectral Density Mapping (SDM ) ####

class SDMCalculation(CalculationModel):
    """
    Calculate the Spectral density mapping
    """
    modelName = sv.RSDM
    targetSeriesAnalyses = [sv.RelaxationAnalysis]

    modelInfo = '''Calculate the Reduced Spectral Density Mapping (SDM). Requires three input dataTables: the T1, T2 with calculated rates and NOE values'''
    description = f'''Model:
                  Calculates J0, J(ѠX) and J(ѠH) using the R1, R2 and NOE values.
                  Values in sec/rad
                  See references for details
                  '''
    references = '''
                1) Theory: Farrow,  et al. Spectral density function mapping using 15N relaxation data exclusively. J Biomol NMR 6, 153–162 (1995)
                2) Equations: 13-16. Udgaonkar et al. Backbone dynamics of Barstar: A 15N NMR relaxation study.  Proteins: 41:460-474 (2000)
                '''
    
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

        # need to propagate the exclusions. if any in df1 or df2, then the resulting row is excluded
        dfs = [r1df, r2df, noedf]
        excludedPids = self._getExcludedPidsForDataFrames(dfs, sv.EXCLUDED_NMRRESIDUEPID, sv.NMRRESIDUEPID)

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

        # need to propagate the exclusions. if any in df1 or df2, then the resulting row is excluded

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
        outputFrame[sv.NMRRESIDUEPID] = merged[sv.NMRRESIDUEPID].values
        outputFrame[sv.SERIES_STEP_X] = None
        outputFrame[sv.SERIES_STEP_Y] = None
        outputFrame[sv.CONSTANT_STATS_OUTPUT_TABLE_COLUMNS] = None
        outputFrame[sv.SpectrumPropertiesHeaders] = None
        outputFrame[sv.PeakPropertiesHeaders] = None
        outputFrame[sv.CALCULATION_MODEL] = self.modelName

        # propagate the Exclusions
        for i, row in outputFrame.iterrows():
             outputFrame.loc[i, sv.EXCLUDED_NMRRESIDUEPID] = row[sv.NMRRESIDUEPID] in excludedPids
        return outputFrame
