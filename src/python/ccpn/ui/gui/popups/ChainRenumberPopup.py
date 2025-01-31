from PyQt5 import QtWidgets, QtGui, QtCore

from ccpn.core import NmrChain, Chain
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces import tipText_
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import ChainPulldown
from ccpn.util.Logging import getLogger
from ccpn.util.Path import aPath
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Spinbox import Spinbox


COLWIDTH = 140
LineEditsMinimumWidth = 195
DEFAULTSPACING = 3
DEFAULTMARGINS = (14, 14, 14, 14)


class ChainRenumberPopup(CcpnDialogMainWidget):
    """
    Renumber a Chain/NmrChain.
    """

    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    def __init__(self, parent=None, mainWindow=None, chain: NmrChain | Chain = None, **kwds):
        """
        Initialise the popup
        """
        super().__init__(parent, setLayout=True, windowTitle=f'Renumber Chain', **kwds)

        if not chain:
            getLogger().warning('no chain found')

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = self.mainWindow.application
            self.project = self.mainWindow.project
            self.current = self.application.current
        else:
            self.mainWindow = None
            self.application = None
            self.project = None
            self.current = None

        self._setWidgets(initialChain=chain)
        self.setUserButton2(callback=self._applyClicked, text='Apply')
        self.setUserButton(callback=self._applyClicked, text='Apply and Close')
        self.setCloseButton(callback=self.reject)
        self.setDefaultButton(self.CLOSEBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._applyAndCloseButton = self.getButton(self.USERBUTTON)
        self._applyButton = self.getButton(self.USERBUTTON2)
        self._closeButton = self.getButton(self.CLOSEBUTTON)

        self._applyAndCloseButton.setEnabled(False)
        self._applyButton.setEnabled(False)

    def _setWidgets(self, initialChain: NmrChain | Chain = None):
        widget = self.mainWidget
        widget.layout().setAlignment(QtCore.Qt.AlignTop)

        row = 0
        self._initPulldown(widget, chain=initialChain)

        row += 2
        Label(widget, 'Offset', grid=(row, 0), )
        self.offsetSpinBox = Spinbox(widget, value=0, step=1, grid=(row, 0), hAlign='r')
        self.offsetSpinBox.valueChanged.connect(self._valueChanged)

        row += 1
        Label(widget, 'Start', grid=(row, 0), )
        self.startSpinBox = Spinbox(widget, value=0, step=1, grid=(row, 0), hAlign='r')
        self.startSpinBox.valueChanged.connect(self._valueChanged)

        row += 1
        Label(widget, 'Stop', grid=(row, 0), )
        self.stopSpinBox = Spinbox(widget, value=0, step=1, grid=(row, 0), hAlign='r')
        self.stopSpinBox.valueChanged.connect(self._valueChanged)

    def _initPulldown(self, widget, chain: NmrChain | Chain = None):
        if isinstance(chain, NmrChain):
            from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown
            self.pulldown = NmrChainPulldown(parent=widget, default=chain, grid=(0, 0))

        elif isinstance(chain, Chain):
            from ccpn.ui.gui.widgets.PulldownListsForObjects import ChainPulldown
            self.pulldown = ChainPulldown(parent=widget, default=chain, grid=(0, 0))
        else:
            getLogger().warning('Pulldown not initialised, no NmrChain or Chain given.')

    def _valueChanged(self):
        offset = self.offsetSpinBox.value()
        start = self.startSpinBox.value()
        stop = self.stopSpinBox.value()

        if offset == 0 and start == 0 and stop == 0:
            self._applyAndCloseButton.setEnabled(False)
            self._applyButton.setEnabled(False)
        else:
            self._applyAndCloseButton.setEnabled(True)
            self._applyButton.setEnabled(True)

    def _applyChanges(self):
        offset = self.offsetSpinBox.value()
        start = self.startSpinBox.value() or None
        stop = self.stopSpinBox.value() or None

        currentChain = self.project.getByPid(self.pulldown.getText())

        if isinstance(currentChain, NmrChain):
            currentChain.renumberNmrResidues(offset=offset, start=start, stop=stop)
        elif isinstance(currentChain, Chain):
            currentChain.renumberResidues(offset=offset, start=start, stop=stop)
        else:
            getLogger().warning('chain is not a NmrChain or Chain')

        self.offsetSpinBox.setValue(0)

    def _applyClicked(self):
        self._applyChanges()

    def _applyAndCloseClicked(self):
        self._applyChanges()
        self.close()


#=========================================================================================
# Main
#=========================================================================================


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    app = TestApplication()

    popup = ChainRenumberPopup(mainWindow=None)
    popup.exec_()


if __name__ == '__main__':
    main()
