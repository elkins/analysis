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
__dateModified__ = "$dateModified: 2025-01-09 20:33:18 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2025-01-09 12:39:07 +0100 (Thu, January 09, 2025) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore

# do not remove - required to stop circular imports :|
import ccpn.core
from ccpn.ui.gui.widgets.table.Table import Table


def _printClassId(val=0):
    # val will be the id of the class containing the pointer which has been garbage-collected
    # must be outside main to avoid garbage-collection (in this test)
    print(f'_printClassId - Garbage-collected: {hex(val)}')


def _printClassNoId():
    # val will be the id of the class containing the pointer which has been garbage-collected
    # must be outside main to avoid garbage-collection (in this test)
    print(f'_printClassNoId - Garbage-collected')


def maintable():
    """Show the test-table
    """
    MAX_ROWS = 7

    import pandas as pd
    import numpy as np
    import random
    from PyQt5 import QtGui, QtWidgets
    from ccpn.ui.gui.widgets.table._TableCommon import CHECKABLE, ENABLED, SELECTABLE
    from ccpn.ui.gui.widgets.table._TableAdditions import TableMenuABC
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

    table = Table(None, df=df, focusBorderWidth=1, cellPadding=11,
                  showGrid=True, gridColour=None,
                  setWidthToColumns=False, setHeightToRows=False, _resize=True,
                  selectionCallbackEnabled=False, actionCallbackEnabled=False)

    # these two need to be done together - HACK for the minute, need to add a method
    table.model()._enableCheckBoxes = True  # make boolean appear as checkboxes (disables double-click on boolean)
    table.model().defaultFlags = ENABLED | SELECTABLE | CHECKABLE  # checkboxes are clickable
    table.setEditable(False)  # double-clicking disabled (doesn't affect checkboxes)

    for row in range(table.rowCount() * 2 // 3):
        for col in range(table.columnCount()):
            table.setBackground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x404040))
            table.setForeground(row, col, QtGui.QColor(random.randint(0, 256**3) & 0x3f3f3f | 0x808080))
    for row in range(table.rowCount() // 2):
        for col in range(table.columnCount() // 2):
            table.setBorderVisible(row, col, True)

    table.setForeground(0, 0, QtCore.Qt.green)
    # will be return the id of one of TableMenuABC subclasses
    # instance-based signal
    TableMenuABC._parent.connect(_printClassNoId, table.searchMenu)
    # # class-based signal
    TableMenuABC._parent.connect(_printClassId)

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

    print(hex(id(table)))
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    maintable()


def maintablemodel():
    # Create a Pandas DataFrame.
    import pandas as pd

    technologies = {
        'Courses': ['a', 'b', 'b', 'c', 'd', 'c', 'a', 'b', 'd', 'd', 'a', 'c', 'e', 'f'],
        'Fee'    : [1, 8, 3, 6, 12, 89, 12, 5, 9, 34, 15, 65, 60, 20],
        }
    df = pd.DataFrame(technologies)
    print(df)

    # print('Group by: Courses, Fee')
    # df2=df.sort_values(['Courses','Fee'], ascending=False).groupby('Courses').head()
    # print(df2)

    print('Group by: Courses, Fee  -  max->min by max of each group')
    # max->min by max of each group
    df2 = df.copy()
    df2['max'] = df2.groupby('Courses')['Fee'].transform('max')
    df2 = df2.sort_values(['max', 'Fee'], ascending=False).drop('max', axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  min->max by min of each group')
    # min->max by min of each group
    df2 = df.copy()
    df2['min'] = df2.groupby('Courses')['Fee'].transform('min')
    df2 = df2.sort_values(['min', 'Fee'], ascending=True).drop('min', axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  min->max of each group / max->min within group')
    # min->max of each group / max->min within group
    df2 = df.copy()
    df2['max'] = df2.groupby('Courses')['Fee'].transform('max')
    df2['diff'] = df2['max'] - df2['Fee']
    df2 = df2.sort_values(['max', 'diff'], ascending=True)  # .drop(['max', 'diff'], axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  max->min of each group / min->max within group')
    # max->min of each group / min->max within group
    df2 = df.copy()
    df2['min'] = df2.groupby('Courses')['Fee'].transform('min')
    df2['diff'] = df2['min'] - df2['Fee']
    df2 = df2.sort_values(['min', 'diff'], ascending=False).drop(['min', 'diff'], axis=1)
    print(df2)
