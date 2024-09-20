"""
A macro for creating plots of R1*R2 and R2/R1 for helping in the differentiation of Anisotropy and Chemical Exchange studies.

Reference:
    - An Effective Method for the Discrimination of Motional Anisotropy and Chemical Exchange. Julie M. Kneller, Min Lu, and Clay Bracken.
    American Chemical Society. 2002.  10.1021/ja017461k .
    - Fast evaluation of protein dynamics from deficient 15N relaxation data. Jaremko et all , 2018,  Journal of Biomolecular NMR (2018) 70:219–228
        https://doi.org/10.1007/s10858-018-0176-3

This macro requires a  dataset  created after performing  the Reduced Spectral density Mapping calculation model
on the Relaxation Analysis Module (alpha)
Which is a dataset that contains a table with the following (mandatory) columns:
    -  nmrResidueCode
    -  R1 and  R1_err
    - R2 and  R2_err
    - HetNoe and  HetNoe_err

Macro created for Analysis Version 3.1.1

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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2023-11-07 14:23:29 +0000 (Tue, November 07, 2023) $"
__version__ = "$Revision: 3.2.2 $"
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

dataTableName = 'RSDM_results'

##  demo sequence for the GB1 protein . Replace with an empty str if not available, e.g.: sequence  = ''
sequence  = 'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
##  secondary structure  for the above sequence  using the DSSP nomenclature.  Replace with an empty str if not available. e.g.: ss_sequence  = ''
ss_sequence   =  'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'

NOE_limitExclusion = 0.65
spectrometerFrequency=600.13

## Some Graphics Settings
titlePdf  = 'Anisotropy and Chemical Exchange Determination'
windowTitle = f'CcpNmr {application.applicationName} - {titlePdf}'

figureTitleFontSize = 8
interactivePlot = True # True if you want the plot to popup as a new windows, to allow the zooming and panning of the figure.
scatterColor = 'navy'
scatterColorError = 'darkred'
scatterExcludedByNOEColor = 'orange'
scatterSize = 1
scatterErrorLinewidth=0.1
scatterErrorCapSize=0
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


###################      start macro       #########################

import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ccpn.util.Common import percentage
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.calculationModels._libraryFunctions as lf
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.ui.gui.widgets.DrawSS import plotSS
import ccpn.macros.relaxation._macrosLib as macrosLib



def _ploteRates(pdf):
    """ Plot R1*R2 and R2/R1 with the Sequence """
    fig, axes  = macrosLib._makeFigureLayoutWithOneColumn(3, height_ratios=[3, 3, 1])
    axR2R1, axR1R2, axss = axes
    ## plot R2 / R1
    axR2R1.errorbar(x, R2R1,  yerr=R2R1_ERR, color = scatterColor, ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize )
    # overlay excludeFrom Trimmed calculation on a different colour
    axR2R1.errorbar(x[eind], R2R1[eind], yerr=R2R1_ERR[eind], color=scatterExcludedByNOEColor, ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize,  label = f'hetNOE < {NOE_limitExclusion}')
    axR2R1.plot(xTrimmedR2R1, yTrimmedR2R1, TrimmedLineColour, linewidth=0.5, label ='R$_{2}$/R$_{1}$ 10%-trimmed mean')
    axR2R1.set_title('R$_{2}$/R$_{1}$', fontsize=fontTitleSize, color=titleColor, pad=1)
    axR2R1.set_ylabel('R$_{2}$/R$_{1}$', fontsize=fontYSize)
    macrosLib._setXTicks(axR2R1, labelMajorSize, labelMinorSize)
    macrosLib._setCommonYLim(axR2R1,R2R1)
    axR2R1.legend(loc='best', prop={'size': 4})
    axR2R1.spines[['right', 'top']].set_visible(False)
    ## plot R1 x R2
    axR1R2.errorbar(x, R1R2,  yerr=R1R2_ERR, ms=scatterSize, color = scatterColor, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize, )
    axR1R2.errorbar(x[eind], R1R2[eind], yerr=R1R2_ERR[eind], color=scatterExcludedByNOEColor, ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize,  label = f'hetNOE < {NOE_limitExclusion}')
    axR1R2.plot(xTrimmedR1R2, yTrimmedR1R2, TrimmedLineColour, linewidth=0.5, label ='R$_{1}$*R$_{2}$ 10%-trimmed mean')
    axR1R2.plot(xTrimmedR1R2, yMedianR1R2, 'green', linewidth=0.5, label ='R$_{1}$*R$_{2}$ median')

    axR1R2.set_title('R$_{1}$ * R$_{2}$', fontsize=fontTitleSize, color=titleColor)
    axR1R2.set_ylabel('R$_{1}$ * R$_{2}$', fontsize=fontYSize)
    axR1R2.set_xlabel('Residue Number', fontsize=fontXSize, )
    axR1R2.legend(loc='best', prop={'size': 4})
    axR1R2.spines[['right', 'top']].set_visible(False)
    macrosLib._setCommonYLim(axR1R2, R1R2)
    macrosLib._setXTicks(axR1R2, labelMajorSize, labelMinorSize)
    axss.get_shared_x_axes().join(axss, axR2R1, axR1R2,)

    ## plot Secondary structure
    if macrosLib._isSequenceValid(sequence, ss_sequence):
        plotSS(axss, xSequence, sequence, ss_sequence=ss_sequence, startSequenceCode=startSequenceCode, fontsize=5,
           showSequenceNumber=False, )
    else:
           axss.remove()

    plt.tight_layout()
    fig.suptitle(titlePdf, fontsize=figureTitleFontSize, )
    fig.canvas.manager.set_window_title(windowTitle)
    plt.subplots_adjust(top=0.85)
    pdf.savefig()
    return fig

def _plotScatterRates(pdf):
    fig = plt.figure( figsize=(5, 3.5), dpi=300)
    #  Plot Scatter R1*R2 vs R2/R1
    axRscatter = plt.subplot(111)
    axRscatter.errorbar(R2R1, R1R2,
                        yerr=R1R2_ERR/2,
                        xerr=R2R1_ERR/2,
                        color=scatterColor,
                        alpha=0.7, #t o see better the labels
                        ms=scatterSize, fmt='o', ecolor=scatterColorError, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize, )
    # overlay the excluded
    axRscatter.errorbar(R2R1[eind], R1R2[eind],
                        # yerr=R1R2_ERR[eind]/2,
                        # xerr=R2R1_ERR[eind]/2,
                        color=scatterExcludedByNOEColor,
                        alpha=0.7, #t o see better the labels
                        ms=scatterSize, fmt='o', ecolor=scatterExcludedByNOEColor, elinewidth=scatterErrorLinewidth, capsize=scatterErrorCapSize, )

    for i, txt in enumerate(x):
        extraY = percentage(0.5, R1R2[i])
        yPos = R1R2[i] + extraY
        extraX = percentage(0.5, R2R1[i])
        xPos = R2R1[i] + extraX
        axRscatter.annotate(str(txt), xy=(R2R1[i], R1R2[i]), xytext=(xPos, yPos), fontsize=3.5, arrowprops=dict(facecolor='grey',arrowstyle="-",lw=0.3  ))
    # axRscatter.plot(yTrimmedR2R1, yScatterTrimmedR1R2, TrimmedLineColour, linewidth=0.5, label ='R1R2 median')
    # axRscatter.plot(xScatterTrimmedLine, yTrimmedR1R2, TrimmedLineColour, linewidth=0.5, label ='R1R2 10%-trimmed mean')
    axRscatter.set_title('R$_{1}$R$_{2}$ vs R$_{2}$/R$_{1}$ ', fontsize=fontTitleSize, color=titleColor)
    axRscatter.set_xlabel('R$_{2}$/R$_{1}$', fontsize=fontYSize, )
    axRscatter.set_ylabel('R$_{1}$*R$_{2}$', fontsize=fontYSize)
    axRscatter.spines[['right', 'top']].set_visible(False)
    macrosLib._setXTicks(axRscatter, labelMajorSize, labelMinorSize)
    axRscatter.yaxis.get_offset_text().set_x(-0.02)
    axRscatter.yaxis.get_offset_text().set_size(5)
    axRscatter.xaxis.get_offset_text().set_size(5)
    xminf =  percentage(20, np.median(R2R1))
    yminf =  percentage(20,  np.median(R1R2))
    xmaxf =  percentage(20,  np.median(R2R1))
    ymaxf =  percentage(20,  np.median(R1R2))
    try:
        axRscatter.set_xlim(xmin=min(R2R1)- xminf, xmax=max(R2R1) + xmaxf,)
        axRscatter.set_ylim(ymin=min(R1R2) - yminf, ymax=max(R1R2) + ymaxf,)
    except Exception as err:
        print('cannot find a best fit')
    plt.tight_layout()
    plt.subplots_adjust(hspace=hspace) # space between plots
    plt.subplots_adjust(bottom=0.15,)# space title and plots
    fig.canvas.manager.set_window_title(windowTitle)

    pdf.savefig()
    return fig

###################      start inline macro       #####################
args = macrosLib.getArgs().parse_args()
globals().update(args.__dict__)

## data preparation
## get the various values  and perform the needed calculations

dataTable = macrosLib._getDataTableForMacro(dataTableName)
data =  macrosLib._getFilteredDataFrame(dataTable.data, [sv.R1, sv.R2, sv.HETNOE_VALUE])


x = data[sv.NMRRESIDUECODE]
x = x.astype(int)
x = x.values
startSequenceCode = x[0]
endSequenceCode = startSequenceCode + len(ss_sequence)
xSequence = np.arange(startSequenceCode, endSequenceCode)
R1 = data[sv.R1].values
R2 = data[sv.R2].values
NOE = data[sv.HETNOE_VALUE].values
R1_ERR = data[sv.R1_ERR].values
R2_ERR  = data[sv.R2_ERR].values
NOE_ERR = data[sv.HETNOE_VALUE_ERR].values
R2R1 = R2/R1
R2R1_ERR = lf.calculateUncertaintiesError(R1, R2, R1_ERR, R2_ERR)
R1R2 = R1*R2
R1R2_ERR = lf.calculateUncertaintiesProductError(R1, R2, R1_ERR, R2_ERR)

# calculate NOE-filtered data
fR1, fR2 = sdl._filterLowNoeFromR1R2(R1, R2, NOE, NOE_limitExclusion)
fR1R2 = fR1*fR2
fR2R1 = fR2/fR1
eind =np.argwhere(NOE < NOE_limitExclusion).flatten()


# calculate R1*R2  10%  trimmed mean line
trimmedLineR1R2 = stats.trim_mean(fR1R2,  proportiontocut= 0.1)
medianLineR1R2 = np.median(fR1R2)
xTrimmedR1R2 = x
yTrimmedR1R2 = np.array([trimmedLineR1R2]*len(xTrimmedR1R2))
yMedianR1R2 = np.array([medianLineR1R2]*len(xTrimmedR1R2))
yScatterTrimmedR1R2 = np.linspace(0, np.max(R1R2), len(yTrimmedR1R2))

# calculate R2/R1  10%  trimmed mean line
trimmedLineR2R1 = stats.trim_mean(fR2R1,  proportiontocut= 0.1)
xTrimmedR2R1 = x
yTrimmedR2R1 = np.array([trimmedLineR2R1]*len(xTrimmedR2R1))
xScatterTrimmedLine = np.linspace(0, np.max(R2R1), len(yTrimmedR1R2))

# calculate the S2 average eq.3
avS2 = sdl.estimateAverageS2(R1, R2, NOE, noeExclusionLimit=NOE_limitExclusion, proportiontocut=0.1)
# calculate the OverallCorrelation Time, remove residues over the R1R2 threshold and low NOE
mask = (R1R2 < trimmedLineR1R2) & (NOE > NOE_limitExclusion)
r1f = R1[mask]
r2f = R2[mask]
noef = NOE[mask]
Ct = sdl.estimateOverallCorrelationTimeFromR1R2(r1f, r2f, spectrometerFrequency=spectrometerFrequency)
avCt = abs(np.mean(Ct)*1e9) #in nanoSec


####################     end data preparation     ##################

##  init the plot and save to pdf

filePath = macrosLib._getExportingPath(__file__, outputPath)

with PdfPages(filePath) as pdf:
    fig1 = _ploteRates(pdf)
    fig2 = _plotScatterRates(pdf)
    info(f'Report saved in {filePath}')

if interactivePlot:
    plt.show()
else:
    plt.close(fig1)
    plt.close(fig2)


###################      end macro        #########################


