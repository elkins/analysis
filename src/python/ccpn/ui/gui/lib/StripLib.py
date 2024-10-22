"""
Strip Library functionalities
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
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2024-10-10 10:55:30 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing

from ccpn.core import NmrAtom
from ccpn.core.ChemicalShift import ChemicalShift
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices
from ccpn.core.lib.ContextManagers import undoStackBlocking
from ccpn.ui.gui.lib.GuiStrip import GuiStrip
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.util.Common import reorder
from ccpn.util.Logging import getLogger
from ccpn.util.isotopes import name2IsotopeCode


def _getCurrentZoomRatio(viewRange):
    xRange, yRange = viewRange
    xMin, xMax = xRange
    xRatio = (xMax - xMin)
    yMin, yMax = yRange
    yRatio = (yMax - yMin)
    return xRatio, yRatio


def navigateToPositionInStrip(strip,
                              positions: list[typing.Optional[float]],
                              axisCodes: list[typing.Optional[str]] = None,
                              widths: list[typing.Optional[float]] = None,
                              markPositions: bool = False):
    """
    Takes a strip, a list of positions and optionally, a parallel list of axisCodes.
    Navigates to specified positions in strip using axisCodes, if specified, otherwise it navigates
    to the positions in the displayed axis order of the strip.
    """

    if not axisCodes:
        axisCodes = strip.axisCodes

    # below does not work for the Navigate-To right-mouse menu option because in the width
    # setting further down, stripAxisIndex is not necessarily the same as ii
    # so the width in the z axis can be set to some huge number by mistake
    # if widths is None:
    #   widths = _getCurrentZoomRatio(strip.viewBox.viewRange())

    # GWV would like an undo; first collect current settings
    # _currentPosition = [a.position for a in strip.orderedaxes]
    # _currentWidths = [a.width for a in strip.orderedaxes]
    # _currentAxisCodes = strip.axisCodes

    indices = getAxisCodeMatchIndices(axisCodes=axisCodes, refAxisCodes=strip.axisCodes)

    for ii, axisCode in enumerate(axisCodes):
        if indices[ii] is None or ii >= len(positions):
            continue
        stripAxisIndex = indices[ii]

        if positions[ii] is not None:
            _setStripAxisPosition(strip, axisIndex=stripAxisIndex, position=positions[ii], update=True)

        if widths:  # is not None:      # and strip._CcpnGLWidget.aspectRatioMode == 0:
            try:
                if widths[ii]:

                    if isinstance(widths[ii], float):
                        # if this item in the list contains a float, set the axis width to that float value
                        _setStripAxisWidth(strip, axisIndex=stripAxisIndex, width=widths[ii], update=True)

                    elif isinstance(widths[ii], str):
                        # if the list item is a str with value, full, reset the corresponding axis
                        if widths[ii] == 'full':
                            _setStripToLimits(strip, axisIndex=stripAxisIndex, update=True)

                        elif widths[ii] == 'default' and stripAxisIndex < 2:
                            # if the list item is a str with value, default, set width to 5ppm for hetero-nuclei and 0.5ppm for 1H
                            if name2IsotopeCode(axisCode) in ['13C', '15N']:
                                _setStripAxisWidth(strip, axisIndex=stripAxisIndex, width=5.0, update=True)
                            else:
                                _setStripAxisWidth(strip, axisIndex=stripAxisIndex, width=0.5, update=True)

            except Exception as es:
                getLogger().debug(f'navigateToPositionInStrip: {es}')

    if markPositions:
        # may need to change to strip.mark..
        strip.spectrumDisplay.mainWindow.markPpmPositions(axisCodes=axisCodes, positions=positions)

    strip._updatePlaneAxes()

    # redraw the contours
    strip._updateVisibility()
    # build here so it doesn't conflict with OpenGl update
    strip._CcpnGLWidget.buildAllContours()
    # strip._CcpnGLWidget.update()

    strip._CcpnGLWidget.emitAllAxesChanged()


def _setStripAxisPosition(strip, axisIndex, position, update=True):
    if axisIndex < 2:
        strip.setAxisPosition(axisIndex=axisIndex, position=position, update=update)
    else:
        strip.orderedAxes[axisIndex].position = position


def _setStripAxisWidth(strip, axisIndex, width, update=True):
    if axisIndex < 2:
        strip.setAxisWidth(axisIndex=axisIndex, width=width, update=update)
    else:
        strip.orderedAxes[axisIndex].width = width


def _setStripToLimits(strip, axisIndex, update=True):
    region = strip.getAxisLimits(axisIndex)
    strip.setAxisRegion(axisIndex=axisIndex, region=region, update=update)


def copyStripAxisPositionsAndWidths(fromStrip, toStrip, positions=None):
    """copy the strip axes to the new strip
    """
    if positions is None:
        # use the position from the source strip
        positions = [axis.position for axis in fromStrip.orderedAxes]

    widths = [axis.width for axis in fromStrip.orderedAxes]
    # remove non-XY widths
    for ii in range(2, len(widths)):
        widths[ii] = None

    positions = reorder(positions, fromStrip.axisCodes, toStrip.axisCodes)
    widths = reorder(widths, fromStrip.axisCodes, toStrip.axisCodes)

    for ii in range(2, len(widths)):
        widths[ii] = None

    navigateToPositionInStrip(toStrip, positions, toStrip.axisCodes, widths)


def matchAxesAndNmrAtoms(strip: GuiStrip, nmrAtoms: typing.List[NmrAtom]):
    shiftDict = {}
    if not strip.spectra:
        return

    shiftList = strip.spectra[0].chemicalShiftList
    for axis in strip.orderedAxes:

        if not axis:
            raise RuntimeError(f'strip {str(strip)} contains undefined axes')

        # shiftDict[axis.code] = []
        # for nmr in nmrAtoms:
        #     if nmr.isotopeCode == name2IsotopeCode(axis.code):
        #         shift = shiftList.getChemicalShift(nmrAtom=nmr)
        #         if shift is not None and shift.value is not None and isPositionWithinfBounds(strip, shift, axis):
        #             shiftDict[axis.code].append(shift)

        shiftDict[axis.code] = []
        for nmr in nmrAtoms:
            if nmr.isotopeCode == name2IsotopeCode(axis.code):
                shifts = nmr.chemicalShifts
                if len(shifts) == 1:
                    shiftDict[axis.code].append(shifts[0])
                else:
                    for shift in shifts:
                        if (shift is not None and shift.value is not None
                                and set(shift.chemicalShiftList.spectra) & set(strip.getVisibleSpectra())):
                            shiftDict[axis.code].append(shift)

    return shiftDict


def isPositionWithinfBounds(strip: GuiStrip, shift: ChemicalShift, axis: object):
    """
    Determines whether a given shift is within the bounds of the specified axis of the specified
    strip.

    NBNB Bug Fixed by Rasmus 13/3/2016.
    This was not used then. Maybe it should be?

    Modified to use aliasingLimits instead of spectrumLimits. Rasmus, 24/7/2016

    """
    if shift is None or shift.value is None:
        # quick check that shift exists and is not empty
        return False

    minima = []
    maxima = []

    axisIndex = strip.axisOrder.index(axis.code)

    for spectrumView in strip.spectrumViews:
        spectrumIndices = spectrumView.dimensionIndices
        if 0 <= axisIndex < len(spectrumIndices) and (index := spectrumIndices[axisIndex]) is not None:
            minima.append(spectrumView.spectrum.aliasingLimits[index][0])
            maxima.append(spectrumView.spectrum.aliasingLimits[index][1])

    return min(minima) < shift.value <= max(maxima) if maxima else True


def navigateToNmrAtomsInStrip(strip: GuiStrip, nmrAtoms: typing.List[NmrAtom], widths=None,
                              markPositions: bool = False, setNmrResidueLabel=False,
                              axisMask=None):
    """
    Takes an NmrResidue and optional spectrum displays and strips and navigates the strips
    and spectrum displays to the positions specified by the peak.
    """
    getLogger().debug('strip: %r, nmrAtoms:%s, widths=%s, markPositions:%s, setSpinSystemLabel:%s' %
                      (strip.pid, nmrAtoms, widths, markPositions, setNmrResidueLabel)
                      )

    if not strip:
        getLogger().warning('navigateToNmrAtomsInStrip: no strip specified')
        return

    if len(nmrAtoms) == 0:
        getLogger().warning('navigateToNmrAtomsInStrip: no atoms specified')
        return

    if not strip.spectra:
        getLogger().error('navigateToNmrAtomsInStrip: strip has no spectra')
        return

    shiftDict = matchAxesAndNmrAtoms(strip, nmrAtoms)
    # atomPositions = shiftDict[strip.axisOrder[2]]
    atomPositions = [[x.value for x in shiftDict[axisCode]] for axisCode in strip.axisOrder if axisCode in shiftDict]
    #print('shiftDict>>', shiftDict)
    #print('atomPositions', atomPositions)

    # positions = []
    # for atomPos in atomPositions:
    #     # 20181029: GWV amended to take first value only
    #     if atomPos and len(atomPos) >= 1:
    #         positions.append(atomPos[0])
    #         # if len(atomPos) < 2:
    #         #   positions.append(atomPos[0])
    #         # else:
    #         #   # positions.append(max(atomPos)-min(atomPos)/2)
    #         #
    #         #   # get the midpoint of each axis
    #         #   #positions.append((max(atomPos)+min(atomPos))/2)
    #
    #     else:
    #         positions.append('')
    positions = [atomPos[0] if atomPos else None for atomPos in atomPositions]

    if axisMask:
        positions = [pos if mask else None for pos, mask in zip(positions, axisMask)]
    navigateToPositionInStrip(strip, positions, widths=widths)

    if markPositions:
        strip.spectrumDisplay.mainWindow.markPositions(list(shiftDict.keys()),
                                                       list(shiftDict.values()),
                                                       strips=strip.spectrumDisplay.strips)

    strip.header.reset()
    if setNmrResidueLabel and nmrAtoms:
        # set the centre strip header label
        strip.header.setLabelText(position='c', text=nmrAtoms[0].nmrResidue.pid)
        strip.header.headerVisible = True

    # redraw the contours
    strip._updateVisibility()
    # if len(strip.orderedAxes) > 2:
    #     strip.axisRegionChanged(strip.orderedAxes[2])

    for thisSpecView in strip.spectrumDisplay.spectrumViews:
        thisSpecView.buildContours = True
        thisSpecView.update()


def navigateToNmrResidueInDisplay(nmrResidue, display, stripIndex=0, widths=None,
                                  showSequentialResidues=False, markPositions=True,
                                  showDropHeaders=False, axisMask=None, keepExistingStrips=False):
    """
    Navigate in to nmrResidue in strip[stripIndex] of display, with optionally-1, +1 residues in
    strips[stripIndex-1] and strips[stripIndex+1].
    return list of strips

    :param nmrResidue: nmrResidue to display
    :param display: target spectrumDisplay for nmrResidue
    :param stripIndex: location of strip in display (assumed 0 if connected and showSequentialResidues)
    :param widths: ignored (for now)
    :param showSequentialResidues: boolean selecting if sequential strips are displayed
    :param markPositions: boolean selecting if marks are displayed
    :return: list of strips
    """

    getLogger().debug('display=%r, nmrResidue=%r, showSequentialResidues=%s, markPositions=%s' %
                      (display.id, nmrResidue.id, showSequentialResidues, markPositions)
                      )

    nmrResidue = nmrResidue.mainNmrResidue
    strips = []
    if showSequentialResidues and (nmrResidue.nmrChain.isConnected
                                   or nmrResidue.residue is not None):
        # showing sequential strips

        # NB Rasmus 11/7/2017.
        # For showSequentialResidues we want to show the exact number of strips,
        # resetting what was there earlier, rather than keeping old ones around
        # NB if we go back to showing long stretches, this will have to be changed.
        # Meanwhile we ignore stripINdex in this branch of the 'if' statement

        # Previous code, kept for comparison :
        # stripIndex = 0  # for now enforce this, o/w below would be more complicated
        #
        # previousNmrResidue = nmrResidue.previousNmrResidue
        # nextNmrResidue = nmrResidue.nextNmrResidue
        # minNumStrips = 1
        # if previousNmrResidue:
        #   minNumStrips += 1
        # if nextNmrResidue:
        #   minNumStrips += 1
        #
        # # showing sequential strips
        # while len(display.strips) < minNumStrips:
        #     display.addStrip()
        #
        # # display the previousNmrResidue if not None
        # if previousNmrResidue is not None:
        #   navigateToNmrAtomsInStrip(display.strips[stripIndex], previousNmrResidue.nmrAtoms,
        #                             widths=None, markPositions=False, setNmrResidueLabel=True)
        #   strips.append(display.strips[stripIndex])
        #   stripIndex += 1
        #
        # if nmrResidue is not None: # this better be true or would hit Exception long before you get here
        #   navigateToNmrAtomsInStrip(display.strips[stripIndex], nmrResidue.nmrAtoms,
        #                             widths=None, markPositions=markPositions, setNmrResidueLabel=True)
        #   strips.append(display.strips[stripIndex])
        #   stripIndex += 1
        #
        # # display the nextNmrResidue if not None
        # if nextNmrResidue is not None:
        #   navigateToNmrAtomsInStrip(display.strips[stripIndex], nextNmrResidue.nmrAtoms,
        #                             widths=None, markPositions=False, setNmrResidueLabel=True)
        #   strips.append(display.strips[stripIndex]) now enforce this, o/w below would be more complicated

        # show the three connected nmrResidues in the strip
        # but always show the end three if connected and the strip long enough

        allNmrResidues = nmrResidue._getAllConnectedList()
        if len(allNmrResidues) < 3:
            nmrResidues = allNmrResidues  # display those that we have
        else:
            nmrMid = allNmrResidues.index(nmrResidue)  # get the index of the required element
            nmrMid = min(max(nmrMid, 1), len(allNmrResidues) - 2)
            nmrResidues = allNmrResidues[nmrMid - 1:nmrMid + 2]

        # nmrResidues = []
        # previousNmrResidue = nmrResidue.previousNmrResidue
        # if previousNmrResidue:
        #   nmrResidues.append(previousNmrResidue)
        # nmrResidues.append(nmrResidue)
        # nextNmrResidue = nmrResidue.nextNmrResidue
        # if nextNmrResidue:
        #   nmrResidues.append(nextNmrResidue)

        with undoStackBlocking() as _:  # Do not add to undo/redo stack
            stripCount = len(nmrResidues)
            while len(display.strips) < stripCount:
                display.addStrip()
            while len(display.strips) > stripCount and not keepExistingStrips:
                display.deleteStrip(display.strips[-1])
            strips = display.strips

            # widths = ['default'] * len(display.strips)
            for ii, nr in enumerate(nmrResidues):
                navigateToNmrAtomsInStrip(strips[ii], nr.nmrAtoms,
                                          widths=widths, markPositions=markPositions, setNmrResidueLabel=True,
                                          axisMask=axisMask)

                # add connection tags to start/end sequential strips - may later allow insertion of nmrResidues
                if allNmrResidues.index(nr) == 0 and not nr.previousNmrResidue:
                    # enable dropping onto the left arrow
                    # strips[ii].header.setLabelText(position='l', text='<<<')
                    strips[ii].header.setLabelText(position='l', text='')
                    strips[ii].header.setLabelObject(position='c', obj=nr)

                    strips[ii].header.setEnabledLeftDrop(showDropHeaders)

                if allNmrResidues.index(nr) == (len(allNmrResidues) - 1) and not nr.nextNmrResidue:
                    # enable dropping onto the right label
                    # strips[ii].header.setLabelText(position='r', text='>>>')
                    strips[ii].header.setLabelText(position='r', text='')
                    strips[ii].header.setLabelObject(position='c', obj=nr)

                    strips[ii].header.setEnabledRightDrop(showDropHeaders)

    else:
        # not showing sequential strips
        # widths = ['default'] * len(display.strips)
        # for strip in display.strips[stripIndex + 1:]:
        #     display.deleteStrip(strip)

        with undoStackBlocking() as _:  # Do not add to undo/redo stack
            while len(display.strips) > stripIndex + 1 and not keepExistingStrips:
                display.deleteStrip(display.strips[-1])

            navigateToNmrAtomsInStrip(display.strips[stripIndex], nmrResidue.nmrAtoms,
                                      widths=widths, markPositions=markPositions, setNmrResidueLabel=True,
                                      axisMask=axisMask)
            strips.append(display.strips[stripIndex])

            # add connection tags to non-sequential strips
            # strips[0].header.setLabelText(position='l', text='<<<')
            # strips[0].header.setLabelText(position='r', text='>>>')
            strips[0].header.setLabelText(position='l', text='')
            strips[0].header.setLabelText(position='r', text='')
            # set the object for the centre label
            strips[0].header.setLabelObject(position='c', obj=nmrResidue)

            if not nmrResidue.previousNmrResidue:
                strips[0].header.setEnabledLeftDrop(showDropHeaders)
            if not nmrResidue.nextNmrResidue:
                strips[0].header.setEnabledRightDrop(showDropHeaders)

    return strips


def markNmrAtoms(mainWindow, nmrAtoms: typing.List[NmrAtom], guiTarget: GuiStrip = None):
    displays = list(mainWindow.spectrumDisplays)
    if not displays:
        getLogger().warning('No Spectrum Displays')
        showWarning('markNmrAtoms', 'No spectrum Displays')
        return

    # default strip if guiTarget is None
    guiTarget = guiTarget if guiTarget else displays[0].strips[0]

    shiftDict = matchAxesAndNmrAtoms(guiTarget, nmrAtoms)
    mainWindow.markPositions(list(shiftDict.keys()),
                             list(shiftDict.values()),
                             strips=guiTarget)
