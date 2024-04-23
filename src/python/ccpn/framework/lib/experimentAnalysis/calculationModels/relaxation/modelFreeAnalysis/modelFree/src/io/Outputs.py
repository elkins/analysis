"""
I/O module
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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-04-23 12:58:39 +0100 (Tue, April 23, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from ccpn.util.decorators import singleton
from ccpn.util.Path import aPath

@singleton
class OutputContainer():
    """A singleton class used to register output Paths and other output related object.
    """
    outputHandler = None

    def register(self, outputHandler):
        self.outputHandler = outputHandler

    @property
    def outputDir(self):
        return self.outputHandler.outputDirPath


def getOutputDir():
    container = OutputContainer()
    if container.outputHandler is not None:
        return container.outputDir

class OutputsHandler(object):

    def __init__(self, parent, outputDirPath, **kwrgs):
        self.parent = parent
        self.outputDirPath = aPath(outputDirPath)
        _container = OutputContainer().register(self)


