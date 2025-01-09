"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-01-09 20:26:39 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-08 17:50:58 +0100 (Thu, September 08, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import numpy as np
# from PyQt5 import QtCore, QtGui
#
# from ccpn.ui.gui.guiSettings import getColours, GUITABLE_ITEM_FOREGROUND
#
#
# #=========================================================================================
# # _SimplePandasTableHeaderModel
# #=========================================================================================
#
# class _SimplePandasTableHeaderModel(QtCore.QAbstractTableModel):
#     """A simple table model to view pandas DataFrames
#     """
#     _defaultForegroundColour = QtGui.QColor(getColours()[GUITABLE_ITEM_FOREGROUND])
#
#     def __init__(self, row, column):
#         """Initialise the pandas model
#         Allocates space for foreground/background colours
#         """
#         QtCore.QAbstractTableModel.__init__(self)
#         # create numpy arrays to match the data that will hold background colour
#         self._colour = np.zeros((row, column), dtype=object)
#         self._df = np.zeros((row, column), dtype=object)
#
#     def rowCount(self, parent=None):
#         """Return the row count for the dataFrame
#         """
#         return self._df.shape[0]
#
#     def columnCount(self, parent=None):
#         """Return the column count for the dataFrame
#         """
#         return self._df.shape[1]
#
#     def data(self, index, role=QtCore.Qt.DisplayRole):
#         """Process the data callback for the model
#         """
#         if index.isValid():
#             # get the source cell
#             row, col = index.row(), index.column()
#
#             if role == QtCore.Qt.DisplayRole:
#                 return str(self._df[row, col])
#
#             elif role == QtCore.Qt.BackgroundRole:
#                 if (colourDict := self._colour[row, col]):
#                     # get the colour from the dict
#                     return colourDict.get(role)
#
#             elif role == QtCore.Qt.ForegroundRole:
#                 if (colourDict := self._colour[row, col]):
#                     # get the colour from the dict
#                     return colourDict.get(role)
#
#                 # return the default foreground colour
#                 return self._defaultForegroundColour
#
#             elif role == QtCore.Qt.ToolTipRole:
#                 data = self._df[row, col]
#
#                 return str(data)
#
#         return None
