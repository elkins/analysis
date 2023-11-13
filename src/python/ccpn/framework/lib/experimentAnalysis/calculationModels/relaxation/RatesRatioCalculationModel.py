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
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import R2R1OutputFrame


class R2R1RatesCalculation(CalculationModel):
    """
    Calculate R2/R1 rates
    """
    modelName = sv.R2R1
    targetSeriesAnalyses = [sv.RelaxationAnalysis]

    modelInfo = '''Calculate the ratio R2/R1.  Requires two input dataTables: the T1, T2 with calculated rates (R1, and R2).'''

    description = f'''Model:
                  ratio =  R2/R1
                  R1 and R2 the decay rate for the T1 and T2 calculated using the {sv.OnePhaseDecay} model.
                  
                  Value Error calculated as:
                  error =  (Re1/R1 + Re2/R2) * R2/R1
                  Re1/Re2 are the respective rate errors for R1 and R2.
                  '''
    references = '''
                '''
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
        outputFrame[sv.CALCULATION_MODEL] = self.modelName
        return outputFrame
