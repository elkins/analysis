"""
This macro is used to calculate the RelaxationExchange via the ETAs and reduced Spectral density mapping and Sigma-NH.
See Relaxation Tutorial.
Reference: see below

This analysis requires 2 dataTables obtained from the RelaxationAnalysis tools:
    -  RSDM
    - ETAs

Calculation model:
- r20 =  (r1-7/4Jwh) *  (ETAxy / ETAz) + 13/8*Jwh
- rex = r2 - r20
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
__dateModified__ = "$dateModified: 2023-12-04 09:57:01 +0000 (Mon, December 04, 2023) $"
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

ETAxyDataName = 'ETAxyResultData'
ETAzDataName = 'ETAzResultData'
RSDMdataTableName = 'RSDMResults'
ETAzScalingFactor = 1.07
ETAxyScalingFactor = 1.08

##  demo sequence for the GB1 protein . Replace with an empty str if not available, e.g.: sequence  = ''
sequence  = '' #'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
##  secondary structure  for the above sequence  using the DSSP nomenclature.  Replace with an empty str if not available. e.g.: ss_sequence  = ''
ss_sequence   =  '' #  'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'

NOE_limitExclusion = 0.65
spectrometerFrequency=600.13


## Some Graphics Settings
titlePdf  = 'Relaxation Exchange determination via η$_{xy/z}$ analysis'
figureTitleFontSize = 8
interactivePlot = False # True if you want the plot to popup as a new windows, to allow the zooming and panning of the figure.
scatterColor = 'navy'
scatterColorError = 'darkred'
scatterExcludedByNOEColor = 'orange'
scatterSize = 3
scatterErrorLinewidth=0.1
scatterErrorCapSize=0.8
TrimmedLineColour = 'black'
fontTitleSize = 6
fontXSize = 4
fontYSize = 4
scatterFontSize = 5
labelMajorSize = 4
labelMinorSize = 3
titleColor = 'darkblue'
hspace= 0.5

# exporting to pdf: Default save to same location and name.pdf as this macro
#  alternatively, provide a full valid path
outputPath = None

############################################################
##################   End User Settings     ########################
############################################################

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import N15gyromagneticRatio, HgyromagneticRatio
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ccpn.ui.gui.widgets.DrawSS import plotSS
import ccpn.macros.relaxation._macrosLib as macrosLib
from ccpn.ui.gui.widgets.MessageDialog import  showMessage, showMulti
from ccpn.framework.PathsAndUrls import CCPN_SUMMARIES_DIRECTORY
from ccpn.util.Path import joinPath
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
import ccpn.ui.gui.widgets.PulldownListsForObjects as cw
from ccpn.core.lib.Pid import createPid
# create a very simple popup to get the dataTable names

ETAxyDataPid = createPid('DT', ETAxyDataName)
ETAzDataPid = createPid('DT', ETAzDataName)
RSDMDataPid = createPid('DT', RSDMdataTableName)


class DataTableSelection(CcpnDialogMainWidget):
    def __init__(self, parent=None, mainWindow=None, title='Select DataTable',  **kwds):
        super().__init__(parent, setLayout=True, minimumSize=(450, 250), windowTitle=title, **kwds)
        self.mainWindow = mainWindow
        self.application = self.mainWindow.application
        self.project = self.mainWindow.project

        self.setOkButton(callback=self._okClicked, tipText='Run Calculation')
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)
        # # initialise the buttons and dialog size
        self._postInit()

        self.widgetETAxy = cw.DataTablePulldown(self.mainWidget,
                                                mainWindow=self.mainWindow,
                                                labelText='Select the ETAxy DataTable',
                                                showSelectName=True,
                                                grid=(0, 0), callback=None)
        self.widgetETAz = cw.DataTablePulldown(self.mainWidget,
                                               mainWindow=self.mainWindow,
                                               labelText='Select the ETAz DataTable',
                                               showSelectName=True,
                                               grid=(1, 0), callback=None)
        self.widgetRSDM = cw.DataTablePulldown(self.mainWidget,
                                               mainWindow=self.mainWindow,
                                               labelText='Select the RSDM DataTable',
                                               showSelectName=True,
                                               grid=(2, 0), callback=None)
        self.widgetETAxy.pulldownList.select(f'DT:{ETAxyDataName}')
        self.widgetETAz.pulldownList.select(f'DT:{ETAzDataName}')

        for i in self.widgetRSDM.pulldownList.texts:
            if 'RSDM' in i:
                self.widgetRSDM.pulldownList.select(i)
                break


    def _okClicked(self):
        global ETAxyDataPid
        global ETAzDataPid
        global RSDMDataPid
        ETAxyDataPid =self.widgetETAxy.getText()
        ETAzDataPid = self.widgetETAz.getText()
        RSDMDataPid = self.widgetRSDM.getText()
        self.accept()

    def _cancelClicked(self):
        """ Set the objs to None so to don't proceed.
        """""
        global RSDMDataPid
        RSDMDataPid = None

popup = DataTableSelection(None, mainWindow=mainWindow)
popup.exec_()
## get the objects
ETAxyData = get(ETAxyDataPid)
ETAzData =  get(ETAzDataPid)
RSDMdata =  get(RSDMDataPid)

## check all data is in the project
if not all([ETAxyData, ETAzData, RSDMdata]):
    msg = f'Cannot run the macro. Ensure your dataTables are named: {ETAxyDataName, ETAzDataName, RSDMdataTableName}'
    showMessage('Error with input data', msg)
    raise RuntimeError(msg)

## calculate the model values.


nanColumns = [sv.R1,
              sv.R2,
              sv.HETNOE_VALUE,
              sv.J0,
              sv.JwH,
              sv.JwX,
              sv.J0_ERR,
              sv.JwH_ERR,
              sv.JwX_ERR]
RSDMdf =  macrosLib._getFilteredDataFrame(RSDMdata.data, nanColumns)
ETAzdf = ETAzData.data.groupby([sv.COLLECTIONID]).first()
ETAxydf = ETAxyData.data.groupby([sv.COLLECTIONID]).first()

R1 = RSDMdf[sv.R1].values
R2 = RSDMdf[sv.R2].values
NOE = RSDMdf[sv.HETNOE_VALUE].values

R1_ERR = RSDMdf[sv.R1_ERR].values
R2_ERR  = RSDMdf[sv.R2_ERR].values
NOE_ERR = RSDMdf[sv.HETNOE_VALUE_ERR].values

scalingFactor = 1e9
J0 = RSDMdf[sv.J0].values * scalingFactor
J0_ERR = RSDMdf[sv.J0_ERR].values
JWH = RSDMdf[sv.JwH].values * scalingFactor
JWH_ERR = RSDMdf[sv.JwH_ERR].values
JWH7over4 = 7/4*JWH
JWH13over8 = 13/8*JWH
JWN = RSDMdf[sv.JwX].values * scalingFactor
JWN_ERR = RSDMdf[sv.JwX_ERR].values

ETAz = ETAzdf[sv.CROSSRELAXRATIO_VALUE].values
ETAz_err = ETAzdf[sv.CROSSRELAXRATIO_VALUE_ERR].values
ETAxy = ETAxydf[sv.CROSSRELAXRATIO_VALUE].values
ETAxy_err = ETAxydf[sv.CROSSRELAXRATIO_VALUE_ERR].values

# apply scaling factor
ETAz = ETAz * ETAzScalingFactor
ETAxy = ETAxy * ETAxyScalingFactor


x = RSDMdf[sv.NMRRESIDUECODE]
x = x.astype(int)
x = x.values
startSequenceCode = x[0]
endSequenceCode = startSequenceCode + len(ss_sequence)
xSequence = np.arange(startSequenceCode, endSequenceCode)


r2o_from_RSDM = (R1-JWH7over4) * (ETAxy/ETAz) + JWH13over8
rex_from_RSDM = R2 - r2o_from_RSDM

r20FromExpR2 = sdl._calculateR20viaETAxy(R2, ETAxy)
rexFromExpR2 = (R2 - r20FromExpR2)

r20FromExpR1 = sdl._calculateR20viaETAxy(R2, R1)
rexFromExpR1 = (R2 - r20FromExpR1)

sigmaNH = sdl.calculateSigmaNOE(NOE, R1, N15gyromagneticRatio, HgyromagneticRatio)
SigmaNHErr = ((R1_ERR/R1) + (NOE_ERR/NOE)) * sigmaNH
r2oSigma = (R1-(1.249*sigmaNH)) * ((ETAxy/ETAz) + (1.097*sigmaNH))
rexSigma = R2 - r2oSigma

r2o_error = (R1_ERR+(1.249*SigmaNHErr) + (1.079*SigmaNHErr) + (((ETAxy_err/ETAxy) + (ETAz_err/ETAz)) * (ETAxy/ETAz)))
rexSigma_error = R2_ERR + r2o_error

# ReX from Eq 27 doi:10.1016/j.pnmrs.2004.01.001.  R.A Atkinson, B. Kieffer  The role of protein motions in molecular recognition... 44:141-187. 2004
# Model:
# Rex = (3A + B) * [ 2/3J0 - (nxy/nz - 1/2) * jWN]

A = 1 #TODO find where is coming from
B = 1 #TODO find where is coming from

AB = (3*A + B)
AB = 1 # TODO changeME
etaRatio = ETAxy/ETAz
rexViaEtas = AB * ((2/3*J0) - ((etaRatio-1/2)* JWN))

############################################################
##############                Plotting              #########################
############################################################


def _ploteExchangeRates(pdf):
    """ Plot  Rel Exchange with the Sequence """
    fig, axes  = macrosLib._makeFigureLayoutWithOneColumn(3, height_ratios=[3, 3, 1])
    ax, ax2, axss = axes

    ax.plot(x, [0]*len(x), '--', linewidth=0.5)
    ax.errorbar(x, rexFromExpR2, yerr=rexSigma_error, color=scatterColor, ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize)
    ax.plot(x, rexViaEtas, 'o', ms=1, label='eq. 27')

    ax.set_title('R$_{ex}$ via Experimental R2 and η$_{xy}$', fontsize=fontTitleSize, color=titleColor, pad=1)
    ax.set_ylabel('R$_{ex}$', fontsize=fontYSize)
    macrosLib._setXTicks(ax, labelMajorSize, labelMinorSize)
    # macrosLib._setCommonYLim(axRexSDM, rexSigma)
    ax.legend(loc='lower right', prop={'size': 4})
    ax.spines[['right', 'top']].set_visible(False)

    ## plot Secondary structure
    if macrosLib._isSequenceValid(sequence, ss_sequence):
        plotSS(axss, xSequence, sequence, ss_sequence=ss_sequence, startSequenceCode=startSequenceCode, fontsize=5,
           showSequenceNumber=False, )
    else:
           axss.remove()
    ax2.remove()
    plt.tight_layout()
    fig.suptitle(titlePdf, fontsize=figureTitleFontSize, )
    plt.subplots_adjust(top=0.85)
    pdf.savefig()
    return fig

###################      start inline macro       #####################
args = macrosLib.getArgs().parse_args()
globals().update(args.__dict__)


####################     end data preparation     ##################


##  init the plot and save to pdf

directory = joinPath(project.path, CCPN_SUMMARIES_DIRECTORY, 'Rex')
filePath = macrosLib._getExportingPath(__file__, directory)

with PdfPages(filePath) as pdf:
    fig1 = _ploteExchangeRates(pdf)
    info(f'Report saved in {filePath}')

if interactivePlot:
    plt.show()
else:
    plt.close(fig1)

copy = 'Copy Path to Clipboard'
open = 'Open File'
close = 'Close'
reply = showMulti('Report Ready',
                  f'Report saved in {filePath}',
                  texts=[copy, open, close],
                  )
if reply == open:
    application._systemOpen(filePath)

if reply == copy:
    from ccpn.util.Common import copyToClipboard
    copyToClipboard([filePath])


###################      end macro        #########################


