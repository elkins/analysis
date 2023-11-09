"""
This macro is used to analyse IPAP experiments measuring both the transverse (xy) and longitudinal (z)
15N chemical shift anisotropy–dipolar cross-correlation rate constants (ETA).
See the Dynamics Tutorial for where to find the example input spectra.

This analysis requires 4 different SpectrumGroups:
    - inphase ETAz
    - antiPhase ETAz
    - inphase ETAxy
    - antiPhase ETAxy

Each of the two inphase-antiphase series must contain the same number of spectra measured at the same time points.
The spectra need to be referenced so that the peaks are in the same positions as in the reference spectrum.
This macro requires a source peakList with assignments from a reference Spectrum. The reference spectrum and the
series spectra must have the same axisCodes/dimensions.
Before running the macro, ensure the user settings are correct for your project.
Results: New Peaks for each Spectrum, Collections, input/output dataTables.

The executed  steps are as following:
    -  Create a RelaxationAnalysis instance
    -  Copy-fit-Create 4 collections (one for each series) from the source Peaklist
    -  Create 4 input dataTables
    -  Run the calculation/fitting models
    All these steps can be reproduced on the GUI.

 """
reference = """ Reference: DOI: https://doi.org/10.1002/mrc.1253. 
Direct measurement of the transverse and longitudinal 15N chemical shift anisotropy–dipolar cross-correlation rate constants using 1H-coupled HSQC spectra.
Hall and Fushman 2003. Magn Reson. Chem. 2003, 41:837-842 """

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
__dateModified__ = "$dateModified: 2023-11-09 09:49:31 +0000 (Thu, November 09, 2023) $"
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

# pid for existing objects in the the project.
ETAz_AP_SGpid = 'SG:ETAz_AP'
ETAz_IP_SGpid = 'SG:ETAz_IP'
ETAxy_AP_SGpid = 'SG:ETAxy_AP'
ETAxy_IP_SGpid = 'SG:ETAxy_IP'
SourcePeakListPid = 'PL:GB1_HSQC.2'

# Define names for  the new object we are about to create.
CollectionNameSuffix = '_collection'

ETAz_IP_InputData = 'ETAz_IP_InputData'
ETAz_AP_InputData = 'ETAz_AP_InputData'
ETAxy_IP_InputData = 'ETAxy_IP_InputData'
ETAxy_AP_InputData = 'ETAxy_AP_InputData'

InputDataNameSuffix = '_inputData'

ETAxyResultDataName = 'ETAxyResultData'
ETAzResultDataName = 'ETAzResultData'

############################################################
##################   End User Settings     ########################
############################################################

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.backends.RelaxationAnalysis import RelaxationAnalysisBC
from ccpn.ui.gui.widgets.MessageDialog import  showMessage
from ccpn.core.lib.ContextManagers import busyHandler

## get the objects
ETAz_IP_SG = get(ETAz_IP_SGpid)
ETAz_AP_SG = get(ETAz_AP_SGpid)
ETAxy_IP_SG = get(ETAxy_IP_SGpid)
ETAxy_AP_SG = get(ETAxy_AP_SGpid)
sourcePL = get(SourcePeakListPid)

spectrumGroups =  [
                                ETAz_IP_SG,
                                ETAz_AP_SG,
                                ETAxy_IP_SG,
                                ETAxy_AP_SG
                                ]
mapSpectrumGroupsToInputData = {
                                ETAz_IP_SG :  ETAz_IP_InputData,
                                ETAz_AP_SG: ETAz_AP_InputData,
                                ETAxy_IP_SG: ETAxy_IP_InputData,
                                ETAxy_AP_SG: ETAxy_AP_InputData
                                }

## check all data is in the project
if not all( spectrumGroups + [sourcePL]):
    raise RuntimeError(f'Cannot run the macro. Ensure you have all required data in the project')

## create a RelaxationAnalysis instance
backend = RelaxationAnalysisBC()
totalCopies = len(spectrumGroups)
title = 'Setting up the inputData for the ETA analysis'
text= f"""
This macro is used to analyse IPAP experiments measuring both the transverse (xy) and longitudinal (z)
15N chemical shift anisotropy–dipolar cross-correlation rate constants (ETA).
The executed  steps are as following:
    -  Create a RelaxationAnalysis instance 
    -  Copy and fit peaks from the source PeakList {SourcePeakListPid}
    -  Create 4 sets of Collections of peaks grouped by assignments (one set of Collections for each series/SpectrumGroup) 
    -  Create 4 input dataTables (ETAxy/z inphase/antiphase)
    -  Run the calculation/fitting models
    -  Create 2 Result dataTables. {(ETAxyResultDataName, ETAzResultDataName)}
Note: All these steps can also be reproduced on the Relaxation analysis GUI Module.

For more details see: {reference}

Calculating... Please wait until this window closes.
"""



with busyHandler(title=title, text=text):
    for i, spectrumGroup in enumerate(spectrumGroups):
        collectionName = f'{spectrumGroup.name}{CollectionNameSuffix}'
        dataTableName = mapSpectrumGroupsToInputData.get(spectrumGroup)
        ## Create collections
        msg = f'Progress {i+1}/{len(spectrumGroups)}'
        newCollection = spectrumGroup.copyAndCollectPeaksInSeries(sourcePL,  refit=True,  useSliceColour=True,  newTargetPeakList=False, topCollectionName=collectionName, progressHandlerTitle=msg)
        backend.inputCollection = newCollection
        ## Create Input Data
        newDataTable = backend.newInputDataTableFromSpectrumGroup(spectrumGroup, dataTableName=dataTableName, experimentName=sv.USERDEFINEDEXPERIMENT)

    ## set calculation/fitting model to backend
    calculationModel = backend.getCalculationModelByName(sv.ETAS_CALCULATION_MODEL)
    fittingModel = backend.getFittingModelByName(sv.OnePhaseDecay)
    backend.currentCalculationModel = calculationModel()
    backend.currentFittingModel = fittingModel()

    ########## Fit ETAz #############
    ## get the inputDataTables for the ETAz and set to the backend
    backend.addInputDataTable(project.getDataTable(ETAz_IP_InputData))
    backend.addInputDataTable(project.getDataTable(ETAz_AP_InputData))
    ## Create  the ETAz Result Data
    backend.outputDataTableName = ETAzResultDataName
    ETAz_ResultData = backend.fitInputData()


    ########## Fit ETAxy #############
    ## get the inputDataTables for the ETAxy and set to the backend
    backend.clearInputDataTables()
    backend.addInputDataTable(project.getDataTable(ETAxy_IP_InputData))
    backend.addInputDataTable(project.getDataTable(ETAxy_AP_InputData))
    ## Create  the ETAxy Result Data
    backend.outputDataTableName = ETAxyResultDataName
    ETAxyResultData = backend.fitInputData()

showMessage('Done', 'ETA input dataTable setup completed')
