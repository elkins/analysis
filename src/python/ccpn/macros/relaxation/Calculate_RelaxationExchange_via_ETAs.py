"""
This macro is used to calculate the RelaxationExchange via the ETAs.
There are several methodologies, to describe the Exchange Rate using ETAs experiments but in this macro we use the model discussed by Hass and Led in DOI: 10.1002/mrc.1845

This model includes two variants for calculating the R20:
1) when the system is rigid and tumble fast and nearly isotropically, we use the R1 and R2 values only and  eq.6 in the journal article
2) when the system is flexible or highly non-spherical.  we use the R2 and ETAxy values only and  eq.5 in the journal article
The Rex is:
 Rex = R2 - R20

This analysis requires 2 dataTables obtained from the RelaxationAnalysis tools:
    -  RSDM
    - ETAs

 """

reference = """ Reference: DOI: 10.1002/mrc.1845 
Evaluation of two simplified 15N-NMR methods for determining µs–ms dynamics of proteins. Mathias A. S. Hass, Jens J. Led. 2006
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
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
RSDMdataTableName = 'RSDMResults'

##  demo sequence for the GB1 protein . Replace with an empty str if not available, e.g.: sequence  = ''
sequence  = '' #'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
##  secondary structure  for the above sequence  using the DSSP nomenclature.  Replace with an empty str if not available. e.g.: ss_sequence  = ''
ss_sequence   =  '' #  'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'

NOE_limitExclusion = 0.65
spectrometerFrequency=600.13


## Some Graphics Settings
titlePdf  = 'Relaxation Exchange determination via η$_{xy}$ and Rates analysis'
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
from ccpn.framework.lib.experimentAnalysis.calculationModels._libraryFunctions import calculateUncertaintiesError, peakErrorBySNRs
from scipy import stats

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

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self.widgetETAxy = cw.DataTablePulldown(self.mainWidget,
                                                mainWindow=self.mainWindow,
                                                labelText='Select the ETAxy DataTable',
                                                showSelectName=True,
                                                grid=(0, 0), callback=None)

        self.widgetRSDM = cw.DataTablePulldown(self.mainWidget,
                                               mainWindow=self.mainWindow,
                                               labelText='Select the RSDM DataTable',
                                               showSelectName=True,
                                               grid=(2, 0), callback=None)
        self.widgetETAxy.pulldownList.select(f'DT:{ETAxyDataName}')
        # self.widgetETAz.pulldownList.select(f'DT:{ETAzDataName}')

        for i in self.widgetRSDM.pulldownList.texts:
            if 'RSDM' in i:
                self.widgetRSDM.pulldownList.select(i)
                break


    def _okClicked(self):
        global ETAxyDataPid
        # global ETAzDataPid
        global RSDMDataPid
        ETAxyDataPid =self.widgetETAxy.getText()
        # ETAzDataPid = self.widgetETAz.getText()
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
RSDMdata =  get(RSDMDataPid)

## check all data is in the project
if not all([ETAxyData, RSDMdata]):
    msg = f'Cannot run the macro. Ensure your dataTables are named: {ETAxyDataName, RSDMdataTableName}'
    showMessage('Error with input data', msg)
    raise RuntimeError(msg)

## get the data from the DataTables as dataframes

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
ETAxydf = ETAxyData.data.groupby([sv.COLLECTIONID]).first()

R1 = RSDMdf[sv.R1].values
R2 = RSDMdf[sv.R2].values

R1_ERR = RSDMdf[sv.R1_ERR].values
R2_ERR  = RSDMdf[sv.R2_ERR].values

ETAxy = ETAxydf[sv.RATE].values
ETAxy_err = ETAxydf[sv.RATE_ERR].values


x = RSDMdf[sv.NMRRESIDUECODE]
x = x.astype(int)
x = x.values
startSequenceCode = x[0]
endSequenceCode = startSequenceCode + len(ss_sequence)
xSequence = np.arange(startSequenceCode, endSequenceCode)


## calculate the model values.
r20FromR2ETAxy = sdl._calculateR20viaETAxy(R2, ETAxy)
rexFromR2ETAxy = (R2 - r20FromR2ETAxy)   #(eq 5) when the system is flexible or highly non-spherical

r20FromR2R1 = sdl._calculateR20viaETAxy(R2, R1) #(eq 6) R2 when the system is rigid and tumble fast and nearly isotropically
rexFromR2R1 = (R2 - r20FromR2R1)


# calculate the minimum Rex (eq 7) for ETAxy
# EtaXY


ratioR2ETAxy = R2/ETAxy
kETAxy = stats.trim_mean(ratioR2ETAxy, proportiontocut=0.1)
R = ETAxy
DK = np.std(kETAxy)
minRexR2ETAxy = sdl._calculateMinimumRex(kETAxy, R, DK, ETAxy_err)


ratioR2R1 = R2/R1
kR2R1 = stats.trim_mean(ratioR2R1, proportiontocut=0.1)
R = R1
DKR2R1 = np.std(kR2R1)
minRexR2R1 = sdl._calculateMinimumRex(kR2R1, R, DKR2R1, R1_ERR)
# minRexR2R1 = [min(sdl._calculateMinimumRex(kR2R1, R, DKR2R1, R1_ERR))]*len(ratioR2R1) this as a straight line


############################################################
##############                Plotting              #########################
############################################################

def _setMargins(axis, y):
    # Calculate standard deviation, max, and min Y values
    std_dev = np.std(y)
    max_y = np.max(y)
    min_y = np.min(y)

    # Calculate a margin based on standard deviation (adjust multiplier as needed)
    margin_multiplier = 2
    margin = std_dev * margin_multiplier
    # Calculate plot limits
    y_min_limit = min_y - margin
    y_max_limit = max_y + margin
    axis.set_ylim([y_min_limit, y_max_limit])

def _ploteExchangeRates(pdf):
    """ Plot  Rel Exchange with the Sequence """
    fig, axes  = macrosLib._makeFigureLayoutWithOneColumn(3, height_ratios=[3, 3, 1])
    ax, ax2, axss = axes
    rigidSystem = 'Rigid and Isotropic System' #use R1


    ax.axhline(y=0, color='grey', linestyle='--',  linewidth=0.5)
    ax.errorbar(x, rexFromR2R1, label='R$_{ex}$ via R$_{1}$',
                color='orange', ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize)
    ax.plot(x, minRexR2R1, label='Minimum R$_{ex}$', linewidth=1)
    eqTitle = 'R$_{ex}$ = R$_{2}$ - < R$_{2}/$R$_{1}$>'
    title = rigidSystem
    ax.set_title(f'{title}\n{eqTitle}', fontsize=fontTitleSize, color=titleColor, pad=1)

    ax.set_ylabel('R$_{ex}$', fontsize=fontYSize)
    macrosLib._setXTicks(ax, labelMajorSize, labelMinorSize)
    ax.legend(loc='best', prop={'size': 4})
    ax.spines[['right', 'top']].set_visible(False)
    _setMargins(ax, rexFromR2R1)


    flexibleSystem = 'Flexible and Non-Spherical System' #use ETAxy
    ax2.axhline(y=0, color='grey', linestyle='--',  linewidth=0.5)
    ax2.errorbar(x, rexFromR2ETAxy, label='R$_{ex}$ via η$_{xy}$', color='green', ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize)
    ax2.plot(x, minRexR2ETAxy,  label='Minimum R$_{ex}$',linewidth=1)
    eqTitle = 'R$_{ex}$ = R$_{2}$ - < R$_{2}/$η$_{xy}$>'
    title = flexibleSystem
    ax2.set_title(f'{title}\n{eqTitle}', fontsize=fontTitleSize, color=titleColor, pad=1)

    ax2.set_ylabel('R$_{ex}$', fontsize=fontYSize)
    macrosLib._setXTicks(ax2, labelMajorSize, labelMinorSize)
    ax2.legend(loc='best', prop={'size': 4})
    ax2.spines[['right', 'top']].set_visible(False)
    _setMargins(ax2, rexFromR2ETAxy)

    ## plot Secondary structure
    if macrosLib._isSequenceValid(sequence, ss_sequence):
        plotSS(axss, xSequence, sequence, ss_sequence=ss_sequence, startSequenceCode=startSequenceCode, fontsize=5,
           showSequenceNumber=False, )
    else:
           axss.remove()

    # adjust limits


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
if False:
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


