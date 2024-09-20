"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-08-09 11:25:08 +0100 (Fri, August 09, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2021-09-17 15:02:29 +0100 (Fri, September 17, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from typing import List

from ccpn.core.NmrAtom import NmrAtom
# from ccpn.core.Peak import Peak
# from ccpn.core.Project import Project
from ccpn.ui.gui.lib.GuiSpectrumDisplay import GuiSpectrumDisplay
from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, navigateToNmrAtomsInStrip
from ccpn.core.lib.ContextManagers import undoStackBlocking, undoBlockWithoutSideBar
from ccpn.util.Logging import getLogger
from ccpn.util.OrderedSet import OrderedSet


def navigateToCurrentPeakPosition(application, selectFirstPeak=False, selectClickedPeak=False, allStrips=False):
    """
    Takes the current peak position and navigates (centres) to that position all strips and spectrum displays of the project.
    Called by shortcut. For a more generic usage refer to:  "navigateToPositionInStrip"
    instead
    """

    project = application.project
    displays = project.spectrumDisplays

    cStrip = application.current.strip
    if selectClickedPeak and not selectFirstPeak:
        peak = cStrip and cStrip._lastClickedObjects and cStrip._lastClickedObjects[0]
    else:
        peak = application.current.peak

    if len(application.current.peaks) > 1 and not selectFirstPeak:
        getLogger().warning(
                'More than one peak selected. Select only one for the "navigateToCurrentPeakPosition" command.')
        return

    if len(displays) < 1:
        getLogger().warning('No Displays where to navigate.')
        return

    if peak is None:
        getLogger().warning('No peak selected.')
        return

    if allStrips:
        for display in displays:
            for strip in display.strips:
                if strip and not strip.isDeleted:
                    navigateToPositionInStrip(strip, peak.position, peak.axisCodes)

    elif cStrip:
        navigateToPositionInStrip(cStrip, peak.position, peak.axisCodes)


def navigateToCurrentNmrResiduePosition(application):
    """
    Takes the current nmrResidue and navigates (centres) to that position all strips and spectrum displays of the project.
    Called by shortcut. For a more generic usage refer to:  "navigateToPositionInStrip"
    instead
    """

    project = application.project
    displays = project.spectrumDisplays
    nmrResidue = application.current.nmrResidue

    if len(application.current.nmrResidues) > 1:
        getLogger().warning(
                'More than one nmrResidue selected. Select only one for the "navigateToCurrentNmrResiduePosition" command.')
        return

    if len(displays) < 1:
        getLogger().warning('No Displays where to navigate.')
        return

    if nmrResidue is None:
        getLogger().warning('No nmrResidue selected.')
        return

    for display in displays:
        for strip in display.strips:
            if strip:
                navigateToNmrResidueInStrip(display, strip, nmrResidue=nmrResidue)


def makeStripPlot(spectrumDisplay: GuiSpectrumDisplay, nmrAtomPairs: List[List[NmrAtom]], autoWidth=True, widths=None):
    if not nmrAtomPairs:
        return

    with undoStackBlocking() as _:  # Do not add to undo/redo stack
        numberOfStrips = len(spectrumDisplay.strips)

        # Make sure there are enough strips to display nmrAtomPairs
        if numberOfStrips < len(nmrAtomPairs):
            for _ii in range(numberOfStrips, len(nmrAtomPairs)):
                # spectrumDisplay.strips[-1].clone()
                spectrumDisplay.addStrip()
        else:  # numberOfStrips >= len(nmrAtomPairs):  # too many strips if >
            for _ii in range(len(nmrAtomPairs), numberOfStrips):
                spectrumDisplay.deleteStrip(spectrumDisplay.strips[-1])
                # spectrumDisplay.removeLastStrip()

        # loop through strips and navigate to appropriate position in strip
        for ii, strip in enumerate(spectrumDisplay.strips):
            if autoWidth:
                widths = ['default'] * len(strip.axisCodes)
            elif not widths:
                widths = None
            if None not in nmrAtomPairs[ii]:
                navigateToNmrAtomsInStrip(strip, nmrAtomPairs[ii], widths=widths)


def makeStripPlotFromSingles(spectrumDisplay: GuiSpectrumDisplay, nmrAtoms: List[NmrAtom], autoWidth=True):
    numberOfStrips = len(spectrumDisplay.strips)

    with undoStackBlocking() as _:  # Do not add to undo/redo stack
        # Make sure there are enough strips to display nmrAtomPairs
        if numberOfStrips < len(nmrAtoms):
            for _ii in range(numberOfStrips, len(nmrAtoms)):
                # spectrumDisplay.strips[-1].clone()
                spectrumDisplay.addStrip()

        # print(spectrumDisplay, nmrAtomPairs, len(nmrAtomPairs), len(spectrumDisplay.strips))
        # loop through strips and navigate to appropriate position in strip
        for ii, strip in enumerate(spectrumDisplay.strips):
            widths = ['default'] * len(strip.axisCodes) if autoWidth else None
            navigateToNmrAtomsInStrip(strip, [nmrAtoms[ii]], widths=widths)


def navigateToPeakInStrip(spectrumDisplay: GuiSpectrumDisplay, strip, peak, widths=None, markPositions=False):
    from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices

    spCodes = spectrumDisplay.axisCodes
    pos = [None] * len(spCodes)
    newWidths = ['full'] * len(spCodes)
    mappedNewWidths = [None] * len(spCodes)
    index = 'YXT'.index(spectrumDisplay.stripArrangement)

    if widths is None and index < 2:
        # set the width in case of nD (n>2)
        _widths = {'H': 0.3, 'C': 1.0, 'N': 1.0}
        # _ac = strip.axisCodes[0]
        _ac = spCodes[index]  # primary axisCode based in stripArrangement
        _w = _widths.setdefault(_ac[0], 1.0)
        newWidths[index] = _w
        # newWidths = [_w, 'full']
    else:
        newWidths = widths

    indices = getAxisCodeMatchIndices(spCodes, peak.axisCodes)

    for ii, ind in enumerate(indices):
        if ind is not None and ind < len(peak.position):
            pos[ii] = peak.position[ind]
            mappedNewWidths[ii] = newWidths[ind]

    navigateToPositionInStrip(strip, pos, spCodes, widths=mappedNewWidths, markPositions=markPositions)
    strip.header.reset()
    strip.header.setLabelText(position='c', text=peak.pid)
    # strip.header.headerVisible = True


def navigateToNmrResidueInStrip(spectrumDisplay: GuiSpectrumDisplay, strip, nmrResidue, widths=None,
                                markPositions=False):
    spCodes = spectrumDisplay.axisCodes
    newWidths = ['full'] * len(spCodes)
    index = 'YXT'.index(spectrumDisplay.stripArrangement)

    if widths is None and index < 2:
        # set the width in case of nD (n>2)
        _widths = {'H': 0.3, 'C': 1.0, 'N': 1.0}
        _ac = spCodes[index]  # primary axisCode based in stripArrangement
        _w = _widths.setdefault(_ac[0], 1.0)
        newWidths[index] = _w
        # newWidths = [_w, 'full']
    else:
        newWidths = widths

    navigateToNmrAtomsInStrip(strip, nmrResidue.nmrAtoms,
                              widths=newWidths, markPositions=markPositions, setNmrResidueLabel=False)

    strip.header.reset()
    strip.header.setLabelText(position='c', text=nmrResidue.pid)
    # strip.header.headerVisible = True


def resetLabelPositions(spectrumDisplay: GuiSpectrumDisplay, selected: bool = False) -> None:
    """
    Automatically tidy the peak/multiplet annotation labels in the x-y plane
    of a window for a given list of peaks/multiplets.

    .. describe:: Input

    Analysis.SpectrumWindow, Analysis GUI

    .. describe: Output

    None
    """
    from ccpn.framework.Application import getApplication

    app = getApplication()

    pViews = list(spectrumDisplay.peakViews)
    if selected and app:
        # only update selected peaks
        pks = OrderedSet(app.current.peaks)
        pViews = [pv for pv in pViews if pv.peak in pks]

    mViews = list(spectrumDisplay.multipletViews)
    if selected and app:
        # only update selected peaks
        mlts = OrderedSet(app.current.multiplets)
        mViews = [mv for mv in mViews if mv.multiplet in mlts]

    views = pViews + mViews
    if not views:
        if selected:
            getLogger().debug('resetLabelPositions: There are no selected peaks/multiplets in the spectrumDisplay')
        return

    with undoBlockWithoutSideBar(app):
        for view in views:
            view.textOffset = (0.0, 0.0)


def arrangeLabelPositions(spectrumDisplay: GuiSpectrumDisplay, selected: bool = False) -> None:
    """

    :param spectrumDisplay:
    """
    from ccpn.framework.Application import getApplication
    from ccpn.ui.gui.lib.textalloc.src import allocate_text

    # if current.strip:
    #     spectrumDisplay = current.strip.spectrumDisplay

    # get the list of texts/positions/points
    # v3views = list(spectrumDisplay.peakViews)
    # strip = current.strip  # spectrumDisplay.strips[0]

    if not spectrumDisplay.strips:
        return

    strip = spectrumDisplay.strips[0]
    px, py = strip._CcpnGLWidget.pixelX, strip._CcpnGLWidget.pixelY  # ppm-per-pixel
    # ppmPoss = strip.positions
    # ppmWidths = strip.widths

    _data2Obj = strip.project._data2Obj
    pkLabels = [
        (_data2Obj.get(pLabel.stringObject._wrappedData.findFirstPeakView(peakListView=plv._wrappedData.peakListView)),
         pLabel.stringObject,
         pLabel)
        for plv, ss in strip._CcpnGLWidget._GLPeaks._GLLabels.items() if plv.isDisplayed
        for pLabel in ss.stringList if not pLabel.stringObject.isDeleted]

    mltLabels = [(_data2Obj.get(
            mLabel.stringObject._wrappedData.findFirstMultipletView(
                multipletListView=mlv._wrappedData.multipletListView)),
                  mLabel.stringObject,
                  mLabel)
        for mlv, ss in strip._CcpnGLWidget._GLMultiplets._GLLabels.items() if mlv.isDisplayed
        for mLabel in ss.stringList if not mLabel.stringObject.isDeleted]

    posnX = []
    posnY = []
    lineWXs = []
    lineWYs = []
    # facsX = []
    # facsY = []
    # pppX = []
    # pppY = []
    # data = []
    ws = []
    hs = []

    app = getApplication()
    if selected and app:
        # only update selected peaks
        pks = OrderedSet(app.current.peaks)  # shouldn't need ordered here?
        mlts = OrderedSet(app.current.multiplets)
        pkLabels = list(filter(lambda obj: obj[1] in pks, pkLabels))
        mltLabels = list(filter(lambda obj: obj[1] in mlts, mltLabels))

        # pkLabels = [(view, view.peak, label) for (view, label) in pkLabels if view.peak in pks]
        # mltLabels = [(view, view.multiplet, label) for (view, label) in mltLabels if view.multiplet in mlts]

    labels = pkLabels + mltLabels

    if not labels:
        if selected:
            getLogger().debug('arrangeLabelPositions: There are no selected peaks/multiplets in the spectrumDisplay')
        return

    # can I use SpectrumCache here?
    dims = spectrumDisplay.spectrumViews[0].dimensionIndices  # 0-based
    for view, obj, label in labels:
        # corePeak = view.peak
        # peak = corePeak._wrappedData

        # dims = spectrumDisplay.spectrumViews[0].displayOrder  # 1-based for the model

        # # ppmPerPoints = corePeak.spectrum.ppmPerPoints
        # peakDimX = peak.findFirstPeakDim(dim=dims[0])
        # peakDimY = peak.findFirstPeakDim(dim=dims[1])
        pos = obj.ppmPositions
        try:
            if spectrumDisplay.is1D:
                if spectrumDisplay._flipped:
                    posX, posY = (obj.height or 0.0), pos[0]
                else:
                    posX, posY = pos[0], (obj.height or 0.0)
            else:
                posX, posY = pos[dims[0]], pos[dims[1]]
        except Exception:
            posX, posY = 0.0, 0.0
        try:
            lineWX, lineWY = lWidths[dims[0]], lWidths[dims[1]]
            vPPX, vPPY = ppms[dims[0]], ppms[dims[1]]
        except Exception:
            lineWX, lineWY = 0.0, 0.0
            vPPX, vPPY = 0, 0
        posnX.append(int(posX / px))  # pixelPosition
        posnY.append(int(posY / py))
        lineWXs.append(max(abs(lineWX * vPPX / px / 2.0), 1e-3))  # semi-major axis
        lineWYs.append(max(abs(lineWY * vPPY / py / 2.0), 1e-3))

        ws.append(label.width)
        hs.append(label.height)

    posnX, posnY = np.array(posnX), np.array(posnY)
    minX, maxX = np.min(posnX), np.max(posnX)
    minY, maxY = np.min(posnY), np.max(posnY)
    # meanX, meanY = np.mean(posnX), np.mean(posnY)
    # makes a little clearly for debugging
    posnX = posnX - minX
    posnY = posnY - minY

    # process from top->bottom
    sortPos = np.argsort(-posnY)
    posnX = posnX[sortPos]
    posnY = posnY[sortPos]
    lineWXs, lineWYs = np.abs(np.array(lineWXs)), np.abs(np.array(lineWYs))
    lineWXs = lineWXs[sortPos]
    lineWYs = lineWYs[sortPos]
    labels = [labels[ind] for ind in sortPos]

    texts = [val.text for _, _, val in labels]  # grab the labels
    # if symbolType is lineWidths then need to apply ellipse-avoidance
    if strip.symbolType in {0, 3}:
        # square or cross
        dx = dy = strip.symbolSize
        x_boxes = [np.array([xx - dx, xx + dx]) for xx in posnX]
        y_boxes = [np.array([yy - dy, yy + dy]) for yy in posnY]
        # no ellipses
        x_points = None
        y_points = None
        a_ellipses = None
        b_ellipses = None
    else:
        # outline/filled lineWidths symbols
        x_points = np.array(posnX)
        y_points = np.array(posnY)
        a_ellipses = np.array(lineWXs)
        b_ellipses = np.array(lineWYs)
        # no boxes
        x_boxes = None
        y_boxes = None

    valid_boxes = allocate_text(posnX, posnY, text_list=texts,
                                x_lims=None,
                                y_lims=None,
                                x_boxes=x_boxes, y_boxes=y_boxes,  # boxes to avoid
                                x_points=x_points, y_points=y_points,  # ellipses to avoid
                                a_ellipses=a_ellipses, b_ellipses=b_ellipses,
                                textsize=14,
                                x_margin=0,
                                y_margin=0,
                                minx_distance=10,  # sort this, have changed internally to pixels
                                maxx_distance=300,
                                miny_distance=10,
                                maxy_distance=300,
                                include_new_lines=False,
                                include_new_boxes=True,
                                verbose=False,
                                )
    non_over, over_ind = valid_boxes

    with undoBlockWithoutSideBar(app):
        # need to check which over_ind are bad and discard
        for posx, posy, moved, (view, _obj, _ss) in zip(posnX, posnY, non_over, labels):
            # offset is always orientated +ve to the top-right
            # view.textOffset = (moved[0] - posx, moved[1] - posy)  # pixels
            try:
                # pixelOffset?
                view.textOffset = (moved[0] - posx) * np.abs(px), (moved[1] - posy) * np.abs(py)  # ppm
            except Exception as es:
                print(es)

    # if over_ind:
    #     getLogger().debug(f'Contains bad label indices {over_ind}')
