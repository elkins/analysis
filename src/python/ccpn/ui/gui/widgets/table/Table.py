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
__dateModified__ = "$dateModified: 2024-07-24 18:04:27 +0100 (Wed, July 24, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-08 17:12:59 +0100 (Thu, September 08, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore

import ccpn.core  # MUST be imported here for correct import-order
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.util.Common import NOTHING


ORIENTATIONS = {'h'                 : QtCore.Qt.Horizontal,
                'horizontal'        : QtCore.Qt.Horizontal,
                'v'                 : QtCore.Qt.Vertical,
                'vertical'          : QtCore.Qt.Vertical,
                QtCore.Qt.Horizontal: QtCore.Qt.Horizontal,
                QtCore.Qt.Vertical  : QtCore.Qt.Vertical,
                }

# define a role to return a cell-value
DTYPE_ROLE = QtCore.Qt.UserRole + 1000
VALUE_ROLE = QtCore.Qt.UserRole + 1001
INDEX_ROLE = QtCore.Qt.UserRole + 1002

EDIT_ROLE = QtCore.Qt.EditRole
_EDITOR_SETTER = ('setColor', 'selectValue', 'setData', 'set', 'setValue', 'setText', 'setFile')
_EDITOR_GETTER = ('get', 'value', 'text', 'getFile')

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
               'ignoreStyleSheet',
               )


#=========================================================================================
# Table
#=========================================================================================

class Table(TableABC, Base):
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
        :param enableCopyCell:
        :param tableMenuEnabled:
        :param toolTipsEnabled:
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
                         )
        baseKwds = {k: v for k, v in kwds.items() if k not in _TABLE_KWDS}
        Base._init(self, ignoreStyleSheet=ignoreStyleSheet, **baseKwds)


#=========================================================================================
# Table testing
#=========================================================================================

def main():
    """Show the test-table
    """
    MAX_ROWS = 7

    import pandas as pd
    import numpy as np
    import random
    from PyQt5 import QtGui, QtWidgets
    from ccpn.ui.gui.widgets.table._TableCommon import CHECKABLE, ENABLED, SELECTABLE
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.Gui import _MyAppProxyStyle


    aminoAcids = ['alanine', 'arginine',
                  'asparagine', 'aspartic-acid', 'ambiguous asparagine/aspartic-acid',
                  'cysteine', 'glutamine', 'glutamic-acid', 'glycine',
                  'ambiguous glutamine/glutamic acid', 'histidine',
                  'isoleucine', 'leucine', 'lysine', 'methionine', 'phenylalanine',
                  'proline', 'serine', 'threonine', 'tryptophan', 'tyrosine', 'valine']
    data = [[aminoAcids[0], 150, 300, 900, float('nan'), 80.1, 'delta'],
            [aminoAcids[1], 200, 500, 300, float('nan'), 34.2, ['help', 'more', 'chips']],
            [aminoAcids[2], 100, np.nan, 1000, True, -float('Inf'), 'charlie'],
            [aminoAcids[3], 999, np.inf, 500, False, float('Inf'), 'echo'],
            [aminoAcids[4], 300, -np.inf, 450, 700, 150.3, 'bravo']
            ]

    # multiIndex columnHeaders
    cols = ["No", "Toyota", "Ford", "Tesla", "Nio", "Other", "NO"]
    rowIndex = ["AAA", "BBB", "CCC", "DDD", "EEE"]  # duplicate index

    for ii in range(MAX_ROWS):
        chrs = ''.join(chr(random.randint(65, 68)) for _ in range(5))
        rowIndex.append(chrs[:3])
        data.append([aminoAcids[5 + ii],
                     300 + random.randint(1, MAX_ROWS),
                     random.random() * 1e6,
                     450 + random.randint(-100, 400),
                     700 + random.randint(-MAX_ROWS, MAX_ROWS),
                     150.3 + random.random() * 1e2,
                     f'bravo{chrs[3:]}' if ii % 2 else f'delta{chrs[3:]}'])

    df = pd.DataFrame(data, columns=cols, index=rowIndex)
    # show the example table
    app = TestApplication()

    # patch for icon sizes in menus, etc.
    styles = QtWidgets.QStyleFactory()
    myStyle = _MyAppProxyStyle(styles.create('fusion'))
    app.setStyle(myStyle)

    win = QtWidgets.QMainWindow()
    frame = QtWidgets.QFrame()
    layout = QtWidgets.QGridLayout()
    frame.setLayout(layout)

    table = TableABC(None, df=df, focusBorderWidth=1, cellPadding=11,
                     showGrid=True, gridColour='white',
                     setWidthToColumns=False, setHeightToRows=False, _resize=True)

    # these two need to be done together - HACK for the minute, need to add a method
    table.model()._enableCheckBoxes = True  # make boolean appear as checkboxes (disables double-click on boolean)
    table.model().defaultFlags = ENABLED | SELECTABLE | CHECKABLE  # checkboxes are clickable
    table.setEditable(False)  # double-clicking disabled (doesn't affect checkboxes)

    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            table.setBackground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x404040))
            table.setForeground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x808080))

    table.setForeground(0,0, QtCore.Qt.green)

    # set some background colours
    cells = ((0, 0, '#80c0ff', '#ffe055'),
             (1, 1, '#fe83cc', '#90efab'), (1, 2, '#fe83cc', '#90efab'),
             (2, 3, '#83fbcc', '#a0a0cc'),
             (3, 2, '#e0ff87', '#344546'), (3, 3, '#e0ff87', '#344546'), (3, 4, '#e0ff87', '#344546'),
             (3, 5, '#e0ff87', '#344546'),
             (4, 2, '#e0f08a', '#030840'), (4, 3, '#e0f08a', '#401254'), (4, 4, '#e0f08a', '#401254'),
             (4, 5, '#e0f08a', '#401254'),
             (6, 2, '#70a04f', '#246482'), (6, 6, '#70a04f', '#246377'),
             (7, 1, '#eebb43', '#378773'), (7, 2, '#eebb43', '#822846'),
             (8, 4, '#7090ef', '#b84dc5'), (8, 5, '#7090ef', '#010135'),
             (9, 0, '#30f06f', '#015002'), (9, 1, '#30f06f', '#ab46cd'),
             (10, 2, '#e0d0e6', '#015002'), (10, 3, '#e0d0e6', '#015002'), (10, 4, '#e0d0e6', '#015002'),
             (11, 2, '#e0d0e6', '#015002'), (11, 3, '#e0d0e6', '#015002'), (11, 4, '#e0d0e6', '#015002'),
             )

    for row, col, backCol, foreCol in cells:
        if 0 <= row < table.rowCount() and 0 <= col < table.columnCount():
            table.setBackground(row, col, backCol)
            table.setForeground(row, col, foreCol)

    # set the horizontalHeader information
    header = table.horizontalHeader()
    # test a single stretching column
    header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
    header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
    header.setStretchLastSection(False)

    win.setCentralWidget(frame)
    frame.layout().addWidget(table, 0, 0)

    win.setWindowTitle(f'Testing {table.__class__.__name__}')
    win.show()

    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
