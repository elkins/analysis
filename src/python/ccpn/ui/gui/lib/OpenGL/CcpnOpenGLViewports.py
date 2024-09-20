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
__dateModified__ = "$dateModified: 2024-08-23 19:25:21 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import namedtuple
from ccpn.ui.gui.lib.OpenGL import GL


viewportDimensions = namedtuple('viewportDimensions', 'left bottom width height')


class GLViewports(object):
    # Class to handle the different viewports in the display
    def __init__(self, pixelRatio=1.0):
        # define a new empty list
        self._views = {}
        self._devicePixelRatio = pixelRatio

    @property
    def devicePixelRatio(self):
        return self._devicePixelRatio

    @devicePixelRatio.setter
    def devicePixelRatio(self, pixelRatio):
        if not isinstance(pixelRatio, float):
            raise TypeError('pixelValue must be a float')

        self._devicePixelRatio = pixelRatio

    def addViewport(self, name, parent, left, bottom, rightOffset, topOffset):
        # add a new viewport
        # parent points to the containing widget
        # left, bottom - coordinates of bottom-left corner
        # rightOffset   - offset from the right border
        # topOffset     - offset from the top border
        self._views[name] = (parent, left, bottom, rightOffset, topOffset)

        # e.g., GL.glViewport(0, 35, w-35, h-35)   # leave a 35 width margin for the axes - bottom/right
        #                      0, 35, -35, 0

    def setViewport(self, name):
        # change to the named viewport
        def setVal(offsetType, w, h, leftOffset):
            if offsetType[1] in 'alb':
                return offsetType[0]
            elif offsetType[1] == 'w':
                return w + offsetType[0] - leftOffset
            elif offsetType[1] == 'h':
                return h + offsetType[0]

        if name in self._views:
            thisView = self._views[name]
            w = thisView[0].w  # width()
            h = thisView[0].h + 1  # height()
            l = setVal(thisView[1], w, h, 0)
            b = setVal(thisView[2], w, h, 0)
            wi = setVal(thisView[3], w, h, l)
            he = setVal(thisView[4], w, h, 0)

            ratio = self._devicePixelRatio

            w = max(int(wi * ratio), 2)
            h = max(int(he * ratio), 2)
            GL.glViewport(int(l * ratio),
                          int((b - 1) * ratio),
                          w, h)

            return w, h

        else:
            raise RuntimeError(f'Error: viewport {name} does not exist')

    def getViewport(self, name):
        # change to the named viewport
        def setVal(offsetType, w, h, leftOffset):
            if offsetType[1] in 'alb':
                return offsetType[0]
            elif offsetType[1] == 'w':
                return w + offsetType[0] - leftOffset
            elif offsetType[1] == 'h':
                return h + offsetType[0]

        if name in self._views:
            thisView = self._views[name]
            w = thisView[0].width()
            h = thisView[0].height() + 1
            l = setVal(thisView[1], w, h, 0)
            b = setVal(thisView[2], w, h, 0)
            wi = setVal(thisView[3], w, h, l)
            he = setVal(thisView[4], w, h, 0)

            return viewportDimensions(l, b, max(wi, 1), max(he, 1))

        else:
            raise RuntimeError(f'Error: viewport {name} does not exist')

    def getViewportFromWH(self, name, width, height):
        # change to the named viewport
        def setVal(offsetType, w, h, leftOffset):
            if offsetType[1] in 'alb':
                return offsetType[0]
            elif offsetType[1] == 'w':
                return w + offsetType[0] - leftOffset
            elif offsetType[1] == 'h':
                return h + offsetType[0]

        if name in self._views:
            thisView = self._views[name]
            w = width
            h = height + 1
            l = setVal(thisView[1], w, h, 0)
            b = setVal(thisView[2], w, h, 0)
            wi = setVal(thisView[3], w, h, l)
            he = setVal(thisView[4], w, h, 0)

            return viewportDimensions(l, b, max(wi, 1), max(he, 1))

        else:
            raise RuntimeError(f'Error: viewport {name} does not exist')

    def clearViewports(self):
        """Clear all the current viewports
        """
        self.views = {}
