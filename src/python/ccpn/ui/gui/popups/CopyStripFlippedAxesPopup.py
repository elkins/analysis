"""
Module Documentation here
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
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2019-11-27 12:20:27 +0000 (Wed, November 27, 2019) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets
from itertools import permutations

from ccpn.util.Logging import getLogger
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, undoStackBlocking
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.lib.StripLib import copyStripAxisPositionsAndWidths


class CopyStripFlippedSpectraPopup(CcpnDialogMainWidget):
    """
    Set the axis ordering for the new spectrumDisplay from a popup
    """

    def __init__(self, parent=None, mainWindow=None, strip=None, title='Copy Strip with Axes Flipped', label='', positions=None, **kwds):
        # super().__init__(parent, mainWindow=mainWindow, title=title, **kwds)
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # make sure there's a strip
        if not strip:
            return

        self.mainWindow = mainWindow
        self.project = self.mainWindow.project
        self.application = self.mainWindow.application
        self.current = self.application.current
        self.strip = strip
        self.axisCodes = strip.axisCodes
        self._axisOrderingOptions = tuple(permutations(list(range(len(self.axisCodes)))))
        self._axisOrdering = None
        self._positions = positions

        if strip.axisCodes:
            row = 0
            Label(self.mainWidget, text=f'{label} - {str(self._axisOrdering)}', bold=True, grid=(row, 0), gridSpan=(1, 3))

            row += 1
            self.preferredAxisOrderPulldown = PulldownListCompoundWidget(self.mainWidget,
                                                                         labelText="Select Axis Ordering:",
                                                                         grid=(row, 0), gridSpan=(1, 3), vAlign='t',
                                                                         callback=self._setAxisCodeOrdering)
            self.preferredAxisOrderPulldown.setPreSelect(self._fillPreferredWidget)

            # enable the buttons
            self.setOkButton(callback=self._accept)
            self.setCancelButton(callback=self.reject)
            self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

            self._populate()

        else:
            self.close()

    def _populate(self):
        self._fillPreferredWidget()

    def _fillPreferredWidget(self):
        """Fill the pullDown with the currently available permutations of the axis codes
        """
        specOrder = None

        ll = ['<None>']
        axisPerms = []
        if self.mainWindow:
            # add permutations for the axes
            axisPerms = permutations(list(self.axisCodes))
            ll += [" ".join(perm) for perm in axisPerms]

        self.preferredAxisOrderPulldown.pulldownList.setData(ll)
        self.preferredAxisOrderPulldown.setIndex(1)

    def _setAxisCodeOrdering(self, value):
        """Set the preferred axis ordering from the pullDown selection
        """
        indx = self.preferredAxisOrderPulldown.getIndex()
        self._axisOrdering = self._axisOrderingOptions[indx - 1] if indx > 0 else None

    def _accept(self):
        self.accept()

        try:
            display = self.strip._flipAxes(axisOrderIndices=self._axisOrdering, positions=self._positions)
        except (RuntimeError, ValueError) as es:
            getLogger().warning(f'flipAxes {es}')
