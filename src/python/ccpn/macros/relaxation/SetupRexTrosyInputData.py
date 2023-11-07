"""
This macro is used to set up the 15N TROSY-selected Hahn-echo experiment analysis.
See https://comdnmr.nysbc.org/comd-nmr-dissem/comd-nmr-solution/hahn-echo-15n-trosy-selected And the relative journal article.

This analysis requires 3 different spectrum groups:
    -  TrosyETAxyA
    -  TrosyETAxyB
    - TrosyETAz

each spectrum group will have a single Tau value for each spectrum.
No Fittings are done in this method, just ratios.

This macro requires a source peaklist with assignments.  Source spectrum and series must have the same axisCodes/dimensions.
Before running the macro, ensure the user settings are correct for your project.
Results: New peaks for each spectrum, collections, input/output datatables.

The executed  steps are as following:
    -  Create a RelaxationAnalysis instance
    -  Copy-fit-Create 4 collections ( one for each series) from the source Peaklist
    - Create 4 input data
    - Run the calculation/fitting models
    All these steps can be reproduced on the Gui.

 """
reference = """ Reference: DOI: 10.1021/ja035139z.  
Mapping Chemical Exchange in Proteins with MW > 50 kD
Chunyu Wang, Mark Rance, and Arthur G. Palmer,  J Am Chem Soc. 2003 Jul 30;125(30):8968-9."""

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
__dateModified__ = "$dateModified: 2023-11-07 09:52:04 +0000 (Tue, November 07, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2023-02-03 10:04:03 +0000 (Fri, February 03, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================


############################################################
#####################    User Settings      #######################
############################################################

# INPUT DATA
# pid for existing objects in the the project.
TrosyETAz_SGpid = 'SG:TrosyEtaZ'
TrosyETAxyA_SGpid = 'SG:TrosyEtaXY_alpha'
TrosyETAxyB_SGpid = 'SG:TrosyEtaXY_beta'
SourcePeakListPid = 'PL:GB1_HSQC.2'
T1ResultDataTablePid ='DT:T1Results'
T2ResultDataTablePid = 'DT:T2Results'



# Output Data
# Define names for  the new object we are about to create.
CollectionNameSuffix = '_collection'

ETAz_InputData = 'ETAz_InputData'
ETAxy_A_InputData = 'ETAxy_A_InputData'
ETAxy_B_InputData = 'ETAxy_B_InputData'
RexResultDataTable = 'RexResultData'

InputDataNameSuffix = '_inputData'


############################################################
##################   End User Settings     ########################
############################################################

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.RelaxationAnalysisBC import RelaxationAnalysisBC
from ccpn.ui.gui.widgets.MessageDialog import showMessage
from ccpn.framework.lib.experimentAnalysis.SeriesTablesBC import RexETAOutputFrame
import numpy as np
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking, progressHandler, busyHandler
import pandas as pd
from scipy import stats

## get the objects
TrosyETAz_SG = get(TrosyETAz_SGpid)
TrosyETAxyA_SG = get(TrosyETAxyA_SGpid)
TrosyETAxyB_SG = get(TrosyETAxyB_SGpid)
sourcePL = get(SourcePeakListPid)
T1Data = get(T1ResultDataTablePid)
T2Data = get(T2ResultDataTablePid)


spectrumGroups =  [
                                TrosyETAxyA_SG,
                                TrosyETAxyB_SG,
                                TrosyETAz_SG,
                                ]
mapSpectrumGroupsToInputData = {
                                TrosyETAxyA_SG :  ETAxy_A_InputData,
                                TrosyETAxyB_SG: ETAxy_B_InputData,
                                TrosyETAz_SG: ETAz_InputData,
                                }

experimentsDataDict = {
    ETAxy_A_InputData:sv.TROSY_XYA,
    ETAxy_B_InputData:sv.TROSY_XYB,
    ETAz_InputData: sv.TROSY_Z,
    T1Data.name:sv.T1, #should be already be encoded in the table.
    T2Data.name:sv.T2,
    }


def _calculateZRatio(c, t):
    """
    :param c: float. peak intensity for the third experiment
    :param t:  float. experiment time
    :return: float
    """
    z = (1 / t) * np.log(abs(c / t))
    return z

def _calculateNxyRatio(n, b, t):
    """
    :param n: float. peak intensity for the first experiment
    :param b:  float. peak intensity for the second experiment
    :param t:  float. experiment time
    :return: float
    """
    nxy = (1 / (2 * t)) * np.log(abs(n / b))
    return nxy

## check all data is in the project
if not all( spectrumGroups + [sourcePL]):
    showMessage('Cannot run.', 'Inspect the macro and ensure you have all required data in the project')
    raise RuntimeError(f'Cannot run the macro. Ensure you have all required data in the project')

## create a RelaxationAnalysis instance
backend = RelaxationAnalysisBC()
totalCopies = len(spectrumGroups)
title = 'Setting up the inputData for the Trosy ETAs analysis'
text= f"""
This macro is used to set up the ETAs experiments in a CPMG relaxation analysis.
The executed  steps are as following:
    -  Create a RelaxationAnalysis instance 
    -  Copy and fit peaks from the source PeakList {SourcePeakListPid}
    -  Create 3 collectionLists of peaks grouped by assignments (one collectionLists for each series) 
    -  Create 3 input data. (ETAxyAlpha, ETAxyBeta and ETAz)
    -  Run the calculation/fitting models
    - Create 1 Result datatables. {RexResultDataTable}
Note: All these steps can also be reproduced on the Relaxation analysis Gui Module.

For more details see: {reference}

Calculating... Please wait until this window closes.
"""


if False:
    with busyHandler(title=title, text=text):
        for i, spectrumGroup in enumerate(spectrumGroups):
            collectionName = f'{spectrumGroup.name}{CollectionNameSuffix}'
            dataTableName = mapSpectrumGroupsToInputData.get(spectrumGroup)
            ## Create collections
            msg = f'Progress {i+1}/{len(spectrumGroups)}'
            newCollection = spectrumGroup.copyAndCollectPeaksInSeries(sourcePL,  refit=True,  useSliceColour=True,  newTargetPeakList=False, topCollectionName=collectionName, progressHandlerTitle=msg)
            backend.inputCollection = newCollection
            ## Create Input Data
            experimentName = experimentsDataDict.get(dataTableName)
            newDataTable = backend.newInputDataTableFromSpectrumGroup(spectrumGroup, dataTableName=dataTableName, experimentName=experimentName)

########## Add to input data #############
## get the inputDataTables  and set to the backend
for dataTableN in experimentsDataDict:
    backend.addInputDataTable(project.getDataTable(dataTableN))

## set calculation/fitting model to backend
calculationModel = backend.getCalculationModelByName(sv.REXVIATROSY)
fittingModel = backend.getFittingModelByName(sv.BLANKMODELNAME)
backend.currentCalculationModel = calculationModel()
backend.currentFittingModel = fittingModel()

## Create  the Rex Result Data
backend.outputDataTableName = RexResultDataTable
# Rex_ResultData = backend.fitInputData()

for dataTableN in experimentsDataDict:
            backend.addInputDataTable(project.getDataTable(dataTableN))

r1Data = None
r2Data = None
xyAData = None
xyBData = None
zData = None

datas = [dt.data for dt in backend.inputDataTables]
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

dfs = [r1Data, r2Data, xyAData, xyBData, zData]
# get the Rates per nmrResidueCode  for each table\
for df in dfs:
    df = df.groupby(sv.NMRRESIDUEPID).first().reset_index()
    df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
    df.sort_index(inplace=True)


meanXyAData = xyAData.groupby(sv.NMRRESIDUEPID)[sv._HEIGHT]
meanXyBData = xyBData.groupby(sv.NMRRESIDUEPID)[sv._HEIGHT]
meanZBData = zData.groupby(sv.NMRRESIDUEPID)[sv._HEIGHT]
tauXy = 0.108 #xyAData[sv.SERIES_STEP_X].values[0]
tauZ = 0.108 # zData[sv.SERIES_STEP_X].values[0]
R2values = r2Data[sv.RATE].values
trimmedR2 = stats.trim_mean(R2values,  proportiontocut= 0.1)

rexs = []
for xyA, xyB, z in zip(meanXyAData, meanXyBData, meanZBData):
    xyAmean = xyA[1].unique().mean()
    xyBmean = xyB[1].unique().mean()
    zMean = z[1].unique().mean()
    nmrResiduePid = xyA[0]
    nxy = _calculateNxyRatio(xyAmean, xyBmean, tauXy)
    nz = _calculateZRatio(zMean,  tauZ)

    r1Value = r1Data[r1Data[sv.NMRRESIDUEPID] == nmrResiduePid][sv.RATE].values[0]
    r2Ex = backend.currentCalculationModel._calculateRexViaTrosy(trimmedR2, r1Value, nxy, nz)
    print(nmrResiduePid, r2Ex)
    rexs.append(r2Ex)


suffix1 = f'_{sv.R1}'
suffix2 = f'_{sv.R2}'

r1df = r1Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
r1df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
r1df.sort_index(inplace=True)
r2df = r2Data.groupby(sv.NMRRESIDUEPID).first().reset_index()
r2df.set_index(sv.NMRRESIDUECODE, drop=False, inplace=True)
r2df.sort_index(inplace=True)
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
outputFrame = RexETAOutputFrame()
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
outputFrame[sv.CALCULATION_MODEL] = backend.currentCalculationModel.ModelName

# showMessage('Done', 'Rex calculation via Trosy ETAs completed')
