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
__dateModified__ = "$dateModified: 2025-01-09 13:52:33 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2025-01-09 12:52:41 +0100 (Thu, January 09, 2025) $"
#=========================================================================================
# Start of code
#=========================================================================================

# do not remove - required to stop circular imports :|
import ccpn.core

from ccpn.ui.gui.widgets.table.MITable import MITable


def mainMITable():
    """Show the test-table
    """
    MAX_ROWS = 7

    import contextlib
    import time
    import pandas as pd
    import numpy as np
    import random
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.Gui import _MyAppProxyStyle
    from PyQt5 import QtWidgets, QtGui, QtCore
    from ast import literal_eval

    _useMulti = True
    aminoAcids = ['alanine', 'arginine',
                  'asparagine', 'aspartic-acid', 'ambiguous asp...',
                  'cysteine', 'glutamine', 'glutamic-acid', 'glycine',
                  'ambiguous glu...', 'histidine',
                  'isoleucine', 'leucine', 'lysine', 'methionine', 'phenylalanine',
                  'proline', 'serine', 'threonine', 'tryptophan', 'tyrosine', 'valine']
    data = [[aminoAcids[0], 150, 300, 900, float('nan'), 80.1, 'delta', 'help', 0, 1, aminoAcids[0], 150, 300, 900,
             float('nan'), 80.1, 'delta', 'help'],
            [aminoAcids[1], 200, 500, 300, float('nan'), 34.2, ['help', 'more', 'chips'], 12, 2, 3, aminoAcids[1], 200,
             500, 300, float('nan'), 34.2, ['help', 'more', 'chips'], 12],
            [aminoAcids[2], 100, np.nan, 1000, True, -float('Inf'), 'charlie', 'baaa', 4, 5, aminoAcids[2], 100, np.nan,
             1000, True, -float('Inf'), 'charlie', 'baaa'],
            [aminoAcids[3], 999, np.inf, 500, False, float('Inf'), 'echo', True, 6, 7, aminoAcids[3], 999, np.inf, 500,
             False, float('Inf'), 'echo', True],
            [aminoAcids[4], 300, -np.inf, 450, 700, 150.3, 'bravo', False, 8, 9, aminoAcids[4], 300, -np.inf, 450, 700,
             150.3, 'bravo', False]
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
                             f'bravo{chrs[3:]}' if ii % 2 else f'delta{chrs[3:]}',
                             random.randint(0, 3),
                             random.randint(2, 5),
                             aminoAcids[5 + ii],
                             300 + random.randint(1, MAX_ROWS),
                             random.random() * 1e6,
                             450 + random.randint(-100, 400),
                             700 + random.randint(-MAX_ROWS, MAX_ROWS),
                             150.3 + random.random() * 1e2,
                             f'bravo{chrs[3:]}' if ii % 2 else f'delta{chrs[3:]}',
                             ])

        rowIndex = pd.MultiIndex.from_tuples(multiIndex)

        # multiIndex columnHeaders
        cols = pd.MultiIndex.from_tuples([
            ("CCPN", "CCPN", "Again"),
            ("testing", "testing", "Not again"),
            ("Sheep", "Dog", "Llama"),
            ("Sheep", "Dog", "hat"),
            ("Sheep", "Fish", "Biscuits"),
            ("No", "No", "No"),
            ("Why", "Something", "Else"),
            ("Most", "Petrol", "Toyota"),
            ("Most", "Petrol", "Ford"),
            ("Most", "Petrol", "Flowers"),
            ("Most", "Fish", "Chips"),
            ("Most", "Electric", "Tesla\nRAAAAAH!"),
            ("Most", "Electric", "Nio"),
            ("Most", "Quater", "Mass"),
            ("Other", "Other", "Happy"),
            ("Other1", "Other1", "Happy"),
            ("Set", "NONO", "nay"),
            ("Set", "NONO", "aye"),
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

    # show the table
    table = MITable(None, df=df, showGrid=True, showHorizontalHeader=True, dividerColour='orange',
                    selectionCallbackEnabled=False, actionCallbackEnabled=False)
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
    mainMITable()
