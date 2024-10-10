"""
This module defines the data loading mechanism for loading a Fasta file
"""

#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               )
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y"
                )
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2024-09-24 15:57:23 +0100 (Tue, September 24, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2021-06-30 10:28:41 +0000 (Fri, June 30, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.framework.lib.DataLoaders.DataLoaderABC import DataLoaderABC
from ccpn.core.Project import Project


class FastaDataLoader(DataLoaderABC):
    """The Fasta data-loader.
    """
    dataFormat = 'fastaFile'
    suffixes = ['.fasta']  # a list of suffixes that get matched to path
    loadFunction = (Project._loadFastaFile, 'project')

    def load(self):
        """Subclassed to ignore self.isValid check in original load method.

        Required for GuiBase _loadFastaCallback to work.
        """
        try:
            # get the object (either a project or application), to pass on
            # to the loaderFunc
            loaderFunc, attributeName = self.loadFunction
            obj = getattr(self, attributeName)
            result = loaderFunc(obj, self.path)

        except (ValueError, RuntimeError, RuntimeWarning) as es:
            raise RuntimeError(f'Error loading "{self.path}": {es}') from es
        return result

FastaDataLoader._registerFormat()
