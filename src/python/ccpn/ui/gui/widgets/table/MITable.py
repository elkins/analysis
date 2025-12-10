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
__dateModified__ = "$dateModified: 2025-01-09 18:58:06 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-27 14:43:33 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.Base import Base
from ccpn.util.Common import NOTHING
from ccpn.ui.gui.widgets.table.MITableABC import MITableABC


_TABLE_KWDS = ('parent', 'df',
               'multiSelect', 'selectRows',
               'showHorizontalHeader', 'showVerticalHeader',
               'borderWidth', 'cellPadding', 'focusBorderWidth', 'gridColour',
               '_resize', 'setWidthToColumns', 'setHeightToRows',
               'setOnHeaderOnly', 'showGrid', 'wordWrap',
               'alternatingRows',
               'selectionCallback', 'selectionCallbackEnabled',
               'actionCallback', 'actionCallbackEnabled',
               'enableExport', 'enableDelete', 'enableSearch', 'enableCopyCell',
               'tableMenuEnabled', 'toolTipsEnabled',
               'dividerColour',
               'ignoreStyleSheet',
               )


#=========================================================================================
# MITable
#=========================================================================================

class MITable(MITableABC, Base):
    """
    New table class to integrate into ccpn-widgets
    """

    _enableSelectionCallback = True
    _enableActionCallback = True

    def __init__(self, parent, *, df=None,
                 multiSelect=True, selectRows=True,
                 showHorizontalHeader=True, showVerticalHeader=True,
                 borderWidth=2, cellPadding=2, focusBorderWidth=1, gridColour=None,
                 _resize=False, setWidthToColumns=False, setHeightToRows=False,
                 setOnHeaderOnly=False, showGrid=False, wordWrap=False,
                 alternatingRows=True,
                 selectionCallback=NOTHING, selectionCallbackEnabled=NOTHING,
                 actionCallback=NOTHING, actionCallbackEnabled=NOTHING,
                 enableExport=NOTHING, enableDelete=NOTHING, enableSearch=NOTHING, enableCopyCell=NOTHING,
                 tableMenuEnabled=NOTHING, toolTipsEnabled=NOTHING,
                 dividerColour=None,
                 # local parameters
                 ignoreStyleSheet=True,
                 **kwds):
        """Initialise the table.

        :param parent:
        :param df:
        :param multiSelect:
        :param selectRows:
        :param showHorizontalHeader:
        :param showVerticalHeader:
        :param borderWidth:
        :param cellPadding:
        :param focusBorderWidth:
        :param gridColour:
        :param _resize:
        :param setWidthToColumns:
        :param setHeightToRows:
        :param setOnHeaderOnly:
        :param showGrid:
        :param wordWrap:
        :param alternatingRows:
        :param selectionCallback:
        :param selectionCallbackEnabled:
        :param actionCallback:
        :param actionCallbackEnabled:
        :param enableExport:
        :param enableDelete:
        :param enableSearch:
        :param enableCopyCell:
        :param tableMenuEnabled:
        :param toolTipsEnabled:
        :param dividerColour:
        :param ignoreStyleSheet:
        :param kwds:
        """
        super().__init__(parent, df=df,
                         multiSelect=multiSelect, selectRows=selectRows,
                         showHorizontalHeader=showHorizontalHeader, showVerticalHeader=showVerticalHeader,
                         borderWidth=borderWidth, cellPadding=cellPadding, focusBorderWidth=focusBorderWidth,
                         gridColour=gridColour,
                         _resize=_resize, setWidthToColumns=setWidthToColumns, setHeightToRows=setHeightToRows,
                         setOnHeaderOnly=setOnHeaderOnly, showGrid=showGrid, wordWrap=wordWrap,
                         alternatingRows=alternatingRows,
                         selectionCallback=selectionCallback, selectionCallbackEnabled=selectionCallbackEnabled,
                         actionCallback=actionCallback, actionCallbackEnabled=actionCallbackEnabled,
                         enableExport=enableExport, enableDelete=enableDelete, enableSearch=enableSearch,
                         enableCopyCell=enableCopyCell,
                         tableMenuEnabled=tableMenuEnabled, toolTipsEnabled=toolTipsEnabled,
                         dividerColour=dividerColour
                         )
        baseKwds = {k: v for k, v in kwds.items() if k not in _TABLE_KWDS}
        Base._init(self, ignoreStyleSheet=ignoreStyleSheet, **baseKwds)
