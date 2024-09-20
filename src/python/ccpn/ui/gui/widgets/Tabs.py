"""

Basic Usage:
  Example of a popup with 1 tab:
  
  tabWidget = Tabs(self, grid=(0,0), gridSpan=(1,3))
  
  ## create a frame. This will be the container with all the widgets that will go in the first tab
  
  tab1Frame = Frame(self, setLayout=True)
  
  ## add all the children to the frame
  
  label = Label(tab1Frame, "Example tab 1", grid=(0, 0))
  
  ## add the frame to the TabsWidget to activate as a new tab
  
  tabWidget.addTab(tab1Frame, 'Tab1')
  
  
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
__dateModified__ = "$dateModified: 2024-04-23 22:03:04 +0100 (Tue, April 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"

#=========================================================================================
# Start of code
#=========================================================================================


from PyQt5 import QtCore, QtWidgets, QtGui
from ccpn.ui.gui.widgets.Base import Base


class Tabs(QtWidgets.QTabWidget, Base):
    def __init__(self, parent, **kwds):
        super().__init__(parent)
        Base._init(self, **kwds)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._tabBarClickCallback = None
        self.tabBarClicked.connect(self._tabBarClicked)

    def setTabClickCallback(self, callback):
        if callback and callable(callback):
            self._tabBarClickCallback = callback

    def clearTabClickCallback(self):
        self._tabBarClickCallback = None

    def _tabBarClicked(self, index):
        if self._tabBarClickCallback and callable(self._tabBarClickCallback):
            self._tabBarClickCallback(index)

    @property
    def tabs(self):
        return [self.widget(i) for i in range(self.count())]

    @property
    def tabTexts(self):
        return [self.tabText(i) for i in range(self.count())]

    def getSelectedTabText(self):
        index = self.currentIndex()
        tabText = self.tabText(index)
        return tabText

    def getSelectedTab(self):
        index = self.currentIndex()
        tab = self.widget(index)
        return tab

    def selectTabText(self, text):
        for index, tabText in enumerate(self.tabTexts):
            if tabText == text:
                self.setCurrentIndex(index)


if __name__ == '__main__':
    from ccpn import core
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.Frame import Frame
    from ccpn.ui.gui.widgets.Label import Label
    from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget


    app = TestApplication()
    # patch for icon sizes in menus, etc.
    styles = QtWidgets.QStyleFactory()
    app.setStyle(styles.create('fusion'))
    popup = CcpnDialogMainWidget(setLayout=True, size=(200, 300))

    Base.setHighlightPalette(app.palette())
    print(app.palette().highlight().color().name())
    tabWidget = Tabs(popup.mainWidget, grid=(1, 1), gridSpan=(1, 3))
    tab1Frame = Frame(popup, setLayout=True)
    for i in range(5):
        Label(tab1Frame, "Example tab 1", grid=(i, 0))
    tabWidget.addTab(tab1Frame, 'Tab1')

    tab2Frame = Frame(popup, setLayout=True)
    for i in range(5):
        Label(tab2Frame, "Example tab 2", grid=(i, 0))
    tabWidget.addTab(tab2Frame, 'Tab2')

    print('SEL', tabWidget.getSelectedTabText())

    # tabWidget.setStyleSheet(
    #         "QTabBar::tab { border-radius: 5px; }"
    #         # "QTabBar::tab { background: gray; color: white; padding: 10px; } "
    #         # "QTabBar::tab:selected { background: lightgray; } "
    #         # "QTabWidget::pane { border: 5px; } "
    #         # "QWidget { background: lightgray; } "
    #         )
    # tabWidget.setStyleSheet("""QTabBar::tab {
    #         background: rgb(100,110,235);
    #         border-radius: 2px;
    #         border-style: solid;
    #         min-width: 64px;
    #         padding: 4px;
    #         border-top-left-radius: 10px;
    #         border-top-right-radius: 10px;
    #     }
    #     QTabBar { background: transparent; }
    #     /*QTabWidget::pane {
    #     bord    er: 2px solid rgb(160, 170, 220);
    #     }
    #     QTabBar::tab:selected, QTabBar::tab:hover {
    #         background: rgb(227,235,255)
    #     }*/
    #     """)
    popup.exec_()
