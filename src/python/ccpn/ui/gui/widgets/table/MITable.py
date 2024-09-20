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
__dateModified__ = "$dateModified: 2024-09-04 18:51:19 +0100 (Wed, September 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-27 14:43:33 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import ccpn.core
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
                         borderWidth=borderWidth, cellPadding=cellPadding, focusBorderWidth=focusBorderWidth, gridColour=gridColour,
                         _resize=_resize, setWidthToColumns=setWidthToColumns, setHeightToRows=setHeightToRows,
                         setOnHeaderOnly=setOnHeaderOnly, showGrid=showGrid, wordWrap=wordWrap,
                         alternatingRows=alternatingRows,
                         selectionCallback=selectionCallback, selectionCallbackEnabled=selectionCallbackEnabled,
                         actionCallback=actionCallback, actionCallbackEnabled=actionCallbackEnabled,
                         enableExport=enableExport, enableDelete=enableDelete, enableSearch=enableSearch, enableCopyCell=enableCopyCell,
                         tableMenuEnabled=tableMenuEnabled, toolTipsEnabled=toolTipsEnabled,
                         dividerColour=dividerColour
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

    import sys
    import numpy as np
    import pandas as pd
    import random
    import contextlib
    import time
    import pandas as pd
    import numpy as np
    import random
    from ccpn.ui.gui.widgets.table._TableCommon import CHECKABLE, ENABLED, SELECTABLE
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.Gui import _MyAppProxyStyle

    from PyQt5 import QtWidgets, QtGui, QtCore
    from ast import literal_eval
    from ccpn.util.PrintFormatter import PrintFormatter

    _useMulti = True

    aminoAcids = ['alanine', 'arginine',
                  'asparagine', 'aspartic-acid', 'ambiguous asparagine/aspartic-acid',
                  'cysteine', 'glutamine', 'glutamic-acid', 'glycine',
                  'ambiguous glutamine/glutamic acid', 'histidine',
                  'isoleucine', 'leucine', 'lysine', 'methionine', 'phenylalanine',
                  'proline', 'serine', 'threonine', 'tryptophan', 'tyrosine', 'valine']
    data = [[aminoAcids[0], 150, 300, 900, float('nan'), 80.1, 'delta', 'help'],
            [aminoAcids[1], 200, 500, 300, float('nan'), 34.2, ['help', 'more', 'chips'], 12],
            [aminoAcids[2], 100, np.nan, 1000, True, -float('Inf'), 'charlie', 'baaa'],
            [aminoAcids[3], 999, np.inf, 500, False, float('Inf'), 'echo', True],
            [aminoAcids[4], 300, -np.inf, 450, 700, 150.3, 'bravo', False]
            ]

    if _useMulti:
        multiIndex = [
            ("No", "No", "No"),
            ("Most", "Petrol", "Toyota"),
            ("Most", "Petrol", "Ford"),
            ("Most", "Electric", "Tesla"),
            ("Most", "Electric", "Nio"),
            ("Other", "Other", "Other"),
            ("Other", "More", "NO"),
            ]

        for ii in range(MAX_ROWS):
            chrs = ''.join(chr(random.randint(65, 68)) for _ in range(5))
            if len(multiIndex) < 12:
                multiIndex.append((chrs[0], chrs[1:3], chrs[3:]))
            if len(data) < 12:
                data.append([aminoAcids[5 + ii],
                             300 + random.randint(1, MAX_ROWS),
                             random.random() * 1e6,
                             450 + random.randint(-100, 400),
                             700 + random.randint(-MAX_ROWS, MAX_ROWS),
                             150.3 + random.random() * 1e2,
                             f'bravo{chrs[3:]}' if ii % 2 else f'delta{chrs[3:]}'])

        rowIndex = pd.MultiIndex.from_tuples(multiIndex)

        # multiIndex columnHeaders
        cols = pd.MultiIndex.from_tuples([
            ("No", "No", "No"),
            ("Most", "Petrol", "Toyota"),
            ("Most", "Petrol", "Ford"),
            ("Most", "Electric", "Tesla\nRAAAAAH!"),
            ("Most", "Electric", "Nio"),
            ("Other", "Other", "NO"),
            ("Set", "NO", "NO"),
            ("Set", "NO", "YES"),
            ])

    else:
        # multiIndex columnHeaders
        cols = ("No", "Toyota", "Ford", "Tesla\nWAAAAH!", "Nio", "Other", "NO", "YES")
        rowIndex = ("AAA", "BBB", "CCC", "DDD", "EEE")

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

    with contextlib.suppress(Exception):
        # recovers the df, but the index/columns are mangled, need resetting as MultiIndex
        dfOut = df.to_json(orient='columns')
        _reload = pd.read_json(dfOut, orient='columns')
        _reload.columns = pd.MultiIndex.from_tuples([literal_eval(ss) for ss in _reload.columns.tolist()])
        _reload.index = pd.MultiIndex.from_tuples([literal_eval(ss) for ss in _reload.index.tolist()])

    # # my class to store python-objects as strings - recovers df exactly
    # pretty = PrintFormatter()
    # pretty.ALLOWPICKLE = False  # useful for passing information between threads
    # _loadPickle = pretty(df)
    # _reloadPickle = pretty.literal_eval(_loadPickle)
    #
    # print('PICKLED dataFrame')
    # print(_loadPickle)

    # show the table
    table = MITableABC(None, df=df, showGrid=True, showHorizontalHeader=True, dividerColour='orange')
    table.setEditable(True)
    table.setTextElideMode(QtCore.Qt.ElideMiddle)

    # set random colours
    for row in range(table.rowCount() * 2 // 3):
        for col in range(table.columnCount()):
            table.setBackground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x404040))
            table.setForeground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x808080))
    for row in range(table.rowCount() // 2):
        for col in range(table.columnCount() // 2):
            table.setBorderVisible(row, col, True)

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
        if 0 <= row < (table.rowCount() * 2 // 3) and 0 <= col < table.columnCount():
            table.setBackground(row, col, backCol)
            table.setForeground(row, col, foreCol)


    tt = table._df.columns.tolist()
    print(tt, tt[0], type(tt[0]))

    time.sleep(0.5)
    table.resizeColumnsToContents()
    table.resizeRowsToContents()

    win.setCentralWidget(frame)
    frame.layout().addWidget(table, 0, 0)

    win.setWindowTitle(f'Testing {table.__class__.__name__}')
    win.show()

    app.start()

    # this needs some proper methods
    print('Sort order:')
    idxs = [table.model().index(row, 0) for row in range(table.rowCount())]
    print([val[0] for val in table.model().mapToSource(idxs)])


if __name__ == '__main__':
    """Call the test function
    """
    main()
