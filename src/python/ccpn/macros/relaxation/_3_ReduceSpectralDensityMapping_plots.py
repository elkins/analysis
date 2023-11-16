"""
A macro for creating plots of  the reduced spectral density mapping from the R1 R2 NOE rates as a function of the sequence code

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-10 15:58:42 +0000 (Fri, November 10, 2023) $"
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

dataTableName = 'RSDM_results'

##  demo sequence for the GB1 protein . Replace with an empty str if not available, e.g.: sequence  = ''
sequence  = 'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
##  secondary structure  for the above sequence  using the DSSP nomenclature.  Replace with an empty str if not available. e.g.: ss_sequence  = ''
ss_sequence   =  'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'

spectrometerFrequency=500.053

## Some Graphics Settings

titlePdf  = 'Reduced Spectral Density Mapping'
windowTitle = f'CcpNmr {application.applicationName} - {titlePdf}'

interactivePlot = True # True if you want the plot to popup as a new windows, to allow the zooming and panning of the figure.

lineColour='black'
theoreticalLineColour = 'blue'
lineErrorColour='red'
lineErrorLW = 0.1
lineErrorCapsize=0
lineErrorCapthick=0.05
fontTitleSize = 6
fontXSize = 4
fontYSize =  4
scatterSize = 1
scatterFontSize = 5
labelMajorSize=4
labelMinorSize=3
titleColor = 'blue'
hspace= 1
figureTitleFontSize = 10
plotLinewidth=0.5

# exporting to pdf: Default save to same location and name.pdf as this macro
#  alternatively, provide a full valid path
outputPath = None

############################################################
##################   End User Settings     ########################
############################################################

import numpy as np
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.macros.relaxation._macrosLib as macrosLib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ccpn.ui.gui.widgets.DrawSS import plotSS
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl

def _plotSDM(pdf):
    # page  RSDM
    fig, axes = macrosLib._makeFigureLayoutWithOneColumn(4, height_ratios=[2, 2, 2, 1])
    axJ0, axJwh, axJwx, axss = axes
    if macrosLib._isSequenceValid(sequence, ss_sequence):
        plotSS(axss, xSequence, sequence, ss_sequence=ss_sequence, showSequenceNumber=False,
           startSequenceCode=startSequenceCode, fontsize=labelMinorSize, )

    axJ0.errorbar(x, J0, yerr=J0_ERR, fmt="o", color=lineColour, ms=scatterSize, ecolor=lineErrorColour, elinewidth=lineErrorLW,
                  capsize=lineErrorCapsize, capthick=lineErrorCapthick)
    axJwh.errorbar(x, JWH087, yerr=JWH087_ERR, fmt="o", color=lineColour, ms=scatterSize, ecolor=lineErrorColour,
                   elinewidth=lineErrorLW, capsize=lineErrorCapsize, capthick=lineErrorCapthick)
    axJwx.errorbar(x, JWN, yerr=JWN_ERR, fmt="o", color=lineColour, ms=scatterSize, ecolor=lineErrorColour,
                   elinewidth=lineErrorLW, capsize=lineErrorCapsize, capthick=lineErrorCapthick)

    axJ0.set_ylim(ymin=0)
    axJwh.set_ylim(ymin=0)
    axJwx.set_ylim(ymin=0)

    axJ0.set_title(L_J0, fontsize=fontTitleSize, color=titleColor)
    axJwh.set_title(L_JWH087, fontsize=fontTitleSize, color='blue')
    axJwx.set_title(L_JWN, fontsize=fontTitleSize, color=titleColor)

    axJ0.set_ylabel(f'{L_J0} {L_SR}', fontsize=fontYSize)
    axJwh.set_ylabel(f'{L_JWH087} {L_SR}', fontsize=fontYSize)
    axJwx.set_ylabel(f'{L_JWN} {L_SR}', fontsize=fontYSize)

    macrosLib._setJoinedX(axss, [axJ0, axJwh, axJwx])
    for ax in [axss, axJ0, axJwh, axJwx]:
        macrosLib._setRightTopSpinesOff(ax)
        macrosLib._setXTicks(ax, labelMajorSize, labelMinorSize)
        ax.yaxis.get_offset_text().set_size(fontYSize)
        ax.yaxis.get_offset_text().set_x(-0.02)
        macrosLib._setYLabelOffset(ax, -0.05, 0.5)

    if not macrosLib._isSequenceValid(sequence, ss_sequence):
        axss.remove()

    axJwx.set_xlabel('Residue Number', fontsize=fontXSize, )
    plt.tight_layout()
    plt.subplots_adjust(hspace=hspace)
    plt.subplots_adjust(top=0.85, )  # space title and plots
    fig.suptitle(titlePdf, fontsize=figureTitleFontSize)
    fig.canvas.manager.set_window_title(windowTitle)

    pdf.savefig()
    return fig


def _plotScatters(pdf):
    fig = plt.figure(dpi=300)
    axj0_jwx = plt.subplot(221)
    axj0_jwh = plt.subplot(223)
    axjwh_jwx = plt.subplot(222)

    maxX = np.max(J0) * 2

    ###   jwN vs J0
    axj0_jwx.scatter(J0, JWN, s=1, color=lineColour, )
    axj0_jwx.plot(rcts, jwNTheoretical, theoreticalLineColour, linewidth=plotLinewidth,)

    for i, txt in enumerate(x):
        axj0_jwx.annotate(str(txt), (J0[i], JWN[i]), fontsize=3)
    axj0_jwx.set_title(f'{L_JWN} vs {L_J0}', fontsize=fontTitleSize, color=titleColor)
    axj0_jwx.set_xlabel(f'{L_J0} {L_SR}', fontsize=fontYSize, )
    axj0_jwx.set_ylabel(f'{L_JWN} {L_SR}', fontsize=fontYSize)
    maxY = np.max(jwNTheoretical) + np.max(jwNTheoretical)/2
    axj0_jwx.set_xlim(xmin=0, xmax=30)
    axj0_jwx.set_ylim(ymin=0, ymax=maxY)

    ##  jwH vs J0
    axj0_jwh.scatter(J0, JWH087, s=1, color=lineColour, )
    axj0_jwh.plot(rcts, jwH087Theoretical, theoreticalLineColour, linewidth=plotLinewidth)

    for i, txt in enumerate(x):
        axj0_jwh.annotate(str(txt), (J0[i], JWH087[i]), fontsize=3)
    axj0_jwh.set_title(f'{L_JWH087} vs {L_J0}', fontsize=fontTitleSize, color=titleColor)
    axj0_jwh.set_xlabel(f'{L_J0} {L_SR}', fontsize=fontYSize, )
    axj0_jwh.set_ylabel(f'{L_JWH087} {L_SR}', fontsize=fontYSize)
    maxY = np.max(jwHTheoretical) + np.max(jwHTheoretical)/2
    axj0_jwh.set_xlim(xmin=0, xmax=30)
    axj0_jwh.set_ylim(ymin=0, ymax=maxY)
    axj0_jwh.get_shared_x_axes().join(axj0_jwh, axj0_jwx)

    ##  jwN vs  jwH
    axjwh_jwx.scatter(JWH087, JWN, s=1, color=lineColour, )
    for i, txt in enumerate(x):
        axjwh_jwx.annotate(str(txt), (JWH087[i], JWN[i]), fontsize=3)
    axjwh_jwx.set_title(f'{L_JWN} vs {L_JWH087}', fontsize=fontTitleSize, color=titleColor)
    axjwh_jwx.set_xlabel(f'{L_JWH087} {L_SR}', fontsize=fontYSize, )
    axjwh_jwx.set_ylabel(f'{L_JWN} {L_SR}', fontsize=fontYSize)

    for ax in [axj0_jwh, axj0_jwx, axjwh_jwx]:
        macrosLib._setRightTopSpinesOff(ax)
        macrosLib._setXTicks(ax, labelMajorSize, labelMinorSize)
        ax.yaxis.get_offset_text().set_size(fontYSize)
        ax.xaxis.get_offset_text().set_size(fontYSize)
        ax.yaxis.get_offset_text().set_x(-0.02)

    plt.tight_layout()
    plt.subplots_adjust(hspace=hspace)
    plt.subplots_adjust(top=0.85, )  # space title and plots
    fig.canvas.manager.set_window_title(windowTitle)
    pdf.savefig()
    return fig


###################      start inline macro       #####################
args = macrosLib.getArgs().parse_args()
globals().update(args.__dict__)

## get the data
dataTable = macrosLib._getDataTableForMacro(dataTableName)
data =  dataTable.data

x = data[sv.NMRRESIDUECODE]
x = x.astype(int)
x = x.values

startSequenceCode = x[0]
endSequenceCode = startSequenceCode + len(ss_sequence)
xSequence = np.arange(startSequenceCode, endSequenceCode)

R1 = data[sv.R1].values
R2 = data[sv.R2].values
NOE = data[sv.HETNOE_VALUE].values

R1_ERR = data[sv.R1_ERR]
R2_ERR  = data[sv.R2_ERR]
NOE_ERR = data[sv.HETNOE_VALUE_ERR]

scalingFactor = 1e-9  # convert from sec to nanosec
J0 = data[sv.J0].values / scalingFactor
JWH = data[sv.JwH].values / scalingFactor
JWH087 = JWH*0.87
JWN = data[sv.JwX].values / scalingFactor
JWN087 = JWN*0.87
J0_ERR = np.abs(data[sv.J0_ERR].values)
JWH_ERR = np.abs(data[sv.JwH_ERR].values)
JWH087_ERR = JWH_ERR*0.87
JWN_ERR = np.abs(data[sv.JwX_ERR].values)

# calculate the theoretical JW Lines
rcts, jwHTheoretical, jwNTheoretical = sdl.calculateJW_at_Tc(spectrometerFrequency=spectrometerFrequency)
jwNTheoretical = np.array(jwNTheoretical) / scalingFactor
jwHTheoretical = np.array(jwHTheoretical) / scalingFactor
jwH087Theoretical = jwHTheoretical*0.87

## matex  labels
L_J0 = '$J_{0}$'
L_JWN = '$J(\omega_{N})$'
L_JWH = '$J(\omega_{H})$'
L_JWH087 = '$J(0.87\omega_{H})$'
L_SR = '(nsec/rad)'


##  init the plot and save to pdf
filePath = macrosLib._getExportingPath(__file__, outputPath)

with PdfPages(filePath) as pdf:
    fig1 = _plotSDM(pdf)
    fig2 = _plotScatters(pdf)
    info(f'Report saved in {filePath}')

if interactivePlot:
    plt.show()
else:
    plt.close(fig1)
    plt.close(fig2)

###################      end macro        #########################



