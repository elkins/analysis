from PyQt5 import QtCore

from ccpn.core import NmrChain, Chain
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Spinbox import Spinbox


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
        self.setUserButton(callback=self._applyAndCloseClicked, text='Apply and Close')
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

        row += 1
        self.correspondingLabel = Label(widget, f'Renumber corresponding Chain', grid=(row, 0), )
        self.correspondingCheckbox = CheckBox(widget, value=True, grid=(row, 0), hAlign='r')

        self._chainChanged()

    def _initPulldown(self, widget, chain: NmrChain | Chain = None):
        if isinstance(chain, NmrChain):
            from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown
            self.pulldown = NmrChainPulldown(parent=widget, mainWindow=self.mainWindow,
                                             default=chain, grid=(0, 0), callback=self._chainChanged)

        elif isinstance(chain, Chain):
            from ccpn.ui.gui.widgets.PulldownListsForObjects import ChainPulldown
            self.pulldown = ChainPulldown(parent=widget, mainWindow=self.mainWindow,
                                          default=chain, grid=(0, 0), callback=self._chainChanged)
        else:
            getLogger().warning('Pulldown not initialised, no NmrChain or Chain given.')

    @staticmethod
    def _checkCorresponding(currentChain):
        corresponding = False

        if isinstance(currentChain, Chain):
            if currentChain.nmrChain:
                corresponding = True
        if isinstance(currentChain, NmrChain):
            if currentChain.chain:
                corresponding = True

        return corresponding

    def _chainChanged(self, obj=None):
        currentChain = self.project.getByPid(self.pulldown.getText())

        # just in case it somehow changes to between classes
        prefix = "" if isinstance(currentChain, NmrChain) else "Nmr"
        self.correspondingLabel.setText(f'Renumber corresponding {prefix}Chain')

        # if there is a corresponding Chain/NmrChain enable/disable checkbox
        self.correspondingCheckbox.setEnabled(self._checkCorresponding(currentChain))
        self.correspondingCheckbox.setVisible(self._checkCorresponding(currentChain))
        self.correspondingLabel.setVisible(self._checkCorresponding(currentChain))

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

        nmrChain = chain = None

        currentChain = self.project.getByPid(self.pulldown.getText())
        correspondingBox = self.correspondingCheckbox.isChecked()
        checkCorresponding = self._checkCorresponding(currentChain)

        if isinstance(currentChain, Chain):
            chain = currentChain
            if correspondingBox and checkCorresponding:
                nmrChain = chain.nmrChain
        if isinstance(currentChain, NmrChain):
            nmrChain = currentChain
            if correspondingBox and checkCorresponding:
                chain = nmrChain.chain

        reset = False
        if nmrChain:
            nmrChain.renumberNmrResidues(offset=offset, start=start, stop=stop)
            reset = True
        if chain:
            chain.renumberResidues(offset=offset, start=start, stop=stop)
            reset = True
        if not (nmrChain or chain):
            getLogger().warning('chain is not a NmrChain or Chain')

        # reset offset box
        if reset:
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
