"""
A set of private functions called for building custom macros.
- DO NOT CHANGE without proper deprecation warnings and info
- use at own risk

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
__dateModified__ = "$dateModified: 2023-11-09 09:49:32 +0000 (Thu, November 09, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2023-02-17 14:03:22 +0000 (Fri, February 17, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================


from ccpn.util.Common import percentage
import numpy as np
from ccpn.util.Path import aPath, fetchDir, joinPath
import matplotlib.pyplot as plt
import argparse
from matplotlib.ticker import MultipleLocator
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.util.floatUtils import fExp, fMan
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv

def _prettyFormat4Legend(value, rounding=3):
    """ Format mantissa to (rounding) round  and exponent for matplotlib """
    return '$%s^{%s}$' %(round(fMan(value),rounding),  fExp(value))

def _makeFigureLayoutWithOneColumn(numberOfRows,  height_ratios, figsize=(5, 3.5), dpi=300):
    fig = plt.figure(figsize=figsize, dpi=dpi)
    if len(height_ratios) != numberOfRows:
        height_ratios = [1]*numberOfRows
    spec = fig.add_gridspec(nrows=numberOfRows, ncols=1, height_ratios=height_ratios)
    axes= []
    for row in range(numberOfRows):
        axis = fig.add_subplot(spec[row, 0])
        axes.append(axis)
    return fig,  axes

def _setRightTopSpinesOff(ax):
    ax.spines[['right', 'top']].set_visible(False)

def _setYLabelOffset(ax, xoffset=-0.05, yoffset=0.5):
    # align the labels to vcenter and middle
    ax.yaxis.set_label_coords(xoffset, yoffset)  # align the labels to vcenter and middle

def _setXTicks(ax, labelMajorSize, labelMinorSize):
    ml = MultipleLocator(1)
    ax.minorticks_on()
    ax.xaxis.set_minor_locator(ml)
    ax.tick_params(axis='both', which='major', labelsize=labelMajorSize)
    ax.tick_params(axis='both', which='minor', labelsize=labelMinorSize)

def _setCommonYLim(ax, ys):
    ys = np.array(ys)
    ys = ys[~np.isnan(ys)]
    extraY = np.ceil(percentage(30, np.max(ys)))
    ylim = np.max(ys) + extraY
    ax.set_ylim([0, ylim])

def _setJoinedX(mainAxis, otherAxes):
    mainAxis.get_shared_x_axes().join(mainAxis, *otherAxes)

def _getExportingPath(macroPath, outputPath=None, suffix='.pdf'):

    """
    :param macroPath: the filepath of the running macro
    :param outputPath:  a user defined path or None to use the default as the macro directory and macro name
    :param suffix: default '.pdf'
    :return: aPath
    ## get the path. no complex checking for paths. This is just for a macro!
    """
    if outputPath is None:  # use the macro file name
        filePath = aPath(macroPath).withoutSuffix()
    else:
        filePath = aPath(outputPath)
    filePath = filePath.addTimeStamp()
    filePath = filePath.assureSuffix(suffix)
    return filePath

def _isSequenceValid(sequence, ss_sequence):
    if sequence  in [None, 'None', np.nan]:
        return False
    if ss_sequence  in [None, 'None', np.nan]:
        return False
    if not isinstance(sequence, str):
        return False
    if not isinstance(ss_sequence, str):
        return False
    if len(ss_sequence) != len(sequence):
        return False
    return True

def _getDataTableForMacro(dataTableName):
    from ccpn.core.DataTable import DataTable
    from ccpn.core.lib.Pid import createPid
    from ccpn.framework.Application import  getProject

    project = getProject()
    if project is None:
        raise RuntimeError('Cannot find Project. This macro can be run only within the Analysis V3 application')
    DT = DataTable.shortClassName
    pid = createPid(DT, dataTableName)
    dataTable = project.getByPid(pid)
    if dataTable is None:
        errorMess = f'''\nCannot find the datatable named:  "{dataTableName}" . 
        \n
        Ensure you have the correct dataTable in the project and set the same name in the macro. 
        (See the User-Data section and general documentation on this macro). '''
        showWarning('Datatable not found', errorMess)
        raise RuntimeError(errorMess)
    return dataTable

def getArgs():
    defaultOutputPath = aPath(__file__).filepath
    defaultDataTableName = 'RSDM_results'
    sequence = 'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
    ss_sequence = 'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'
    interactivePlot = True
    parser = argparse.ArgumentParser( description='Create Relaxation Analysis Plots')
    parser.add_argument('-o',  '--outputPath', help='Output file path ', default=defaultOutputPath)
    parser.add_argument('-d',  '--dataTableName', help='The DataTable name containing the Reduced Spectral Density Mapping results', default=defaultDataTableName)
    parser.add_argument('-se',  '--sequence', help='The protein sequence', default=sequence)
    parser.add_argument('-ss',  '--ss_sequence', help='The protein secondary structure  for the above sequence  using the DSSP nomenclature', default=ss_sequence)
    parser.add_argument('-ip',  '--interactivePlot', help='Open a matplotLib plot', default=True, action=argparse.BooleanOptionalAction)
    return parser


##  Used for the Contouring lines

def findNearestIndex(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx

def labelLine(line,x,label=None,align=True,**kwargs):
    from math import atan2, degrees
    ax = line.axes
    xdata = line.get_xdata()
    ydata = line.get_ydata()
    if (x < xdata[0]) or (x > xdata[-1]):
        print('x label location is outside data range!')
        return
    #Find corresponding y co-ordinate and angle of the line
    ip = 1
    for i in range(len(xdata)):
        if x < xdata[i]:
            ip = i
            break
    y = ydata[ip-1] + (ydata[ip]-ydata[ip-1])*(x-xdata[ip-1])/(xdata[ip]-xdata[ip-1])
    if not label:
        label = line.get_label()
    if align:
        #Compute the slope
        dx = xdata[ip] - xdata[ip-1]
        dy = ydata[ip] - ydata[ip-1]
        ang = degrees(atan2(dy,dx))
        #Transform to screen co-ordinates
        pt = np.array([x,y]).reshape((1,2))
        trans_angle = ax.transData.transform_angles(np.array((ang,)),pt)[0]
    else:
        trans_angle = 0
    if 'color' not in kwargs:
        kwargs['color'] = line.get_color()
    if ('horizontalalignment' not in kwargs) and ('ha' not in kwargs):
        kwargs['ha'] = 'center'
    if ('verticalalignment' not in kwargs) and ('va' not in kwargs):
        kwargs['va'] = 'center'
    if 'backgroundcolor' not in kwargs:
        kwargs['backgroundcolor'] = ax.get_facecolor()
    if 'clip_on' not in kwargs:
        kwargs['clip_on'] = True
    if 'zorder' not in kwargs:
        kwargs['zorder'] = 2.5
    color = kwargs.get('color', )
    fontsize = kwargs.get('fontsize', 5)
    ax.text(x, y, label, rotation=0, color=color, fontsize=fontsize, )
    # ax.text(x,y,label,rotation=trans_angle,**kwargs)

def labelLines(lines, align=True,xvals=None,**kwargs):
    ax = lines[0].axes
    labLines = []
    labels = []
    for line in lines:
        label = line.get_label()
        if "_line" not in label:
            labLines.append(line)
            label = label.lstrip('_')
            labels.append(label)
    if xvals is None:
        xmin,xmax = ax.get_xlim()
        xvals = np.linspace(xmin,xmax,len(labLines)+2)[1:-1]
    for line,x,label in zip(labLines,xvals,labels):
        labelLine(line,x,label,align,**kwargs)
