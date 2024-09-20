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
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import datetime
from PyQt5 import QtGui
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.util import Path


# This text is being copied on the clipboard only. Is not the source of the image in the popup.
# The image is in ccpn.ui.gui.widgets
year = datetime.date.today().year

TEXT = '''
Copyright (C) CCPN project (www.ccpn.ac.uk) 2014 - %s

**Active Developers:**
Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń,
Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister

**This program uses:**
The CCPN data model: J Biomol NMR (2006) 36:147–155, DOI 10.1007/s10858-006-9076-z 
PyQtGraph (https://www.pyqtgraph.org)
PyQt (https://pyqt.sourceforge.net)
Miniconda, subject to Anaconda End User Licence Agreement (https://docs.continuum.io/anaconda/eula)

**Disclaimer:**
This program is offered 'as-is'. Under no circumstances will the authors, CCPN, the Department of Molecular 
and Cell Biology, or the University of Leicester be liable for any damage, loss of data, loss of revenue or 
any other undesired consequences originating from the usage of this software.
''' % year


class AboutPopup(CcpnDialog):
    def __init__(self, parent=None, title='About CcpNmr', **kwds):
        CcpnDialog.__init__(self, parent, setLayout=True, windowTitle=title, **kwds)

        pathPNG = os.path.join(Path.getPathToImport('ccpn.ui.gui.widgets'), 'AboutCcpNmr.png')
        self.label = Label(self, grid=(0, 0))
        self.label.setPixmap(QtGui.QPixmap(pathPNG))

        self.buttons = ButtonList(self, texts=['Close', 'Copy'],
                                  callbacks=[self.accept, self._copyToClipboard],
                                  tipTexts=['Close window', 'Copy text to clipboard'],
                                  grid=(1, 0), hAlign='r')

        self.setMaximumWidth(self.size().width())
        self.setMaximumSize(self.maximumWidth(), self.maximumHeight())

    @staticmethod
    def _copyToClipboard():
        """TEXT being copied on the clipboard """
        from ccpn.util.Common import copyToClipboard

        copyToClipboard([TEXT])


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    popup = AboutPopup()

    popup.show()
    popup.raise_()

    app.start()


if __name__ == '__main__':
    main()
