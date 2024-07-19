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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-07-19 16:25:51 +0100 (Fri, July 19, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from PyQt5 import QtWidgets, QtCore

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.RadioButton import RadioButton, EditableRadioButton, RadioButtonWithSubSelection
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Label import Label
from ccpn.util.Logging import getLogger


CHECKED = QtCore.Qt.Checked
UNCHECKED = QtCore.Qt.Unchecked


class RadioButtons(QtWidgets.QWidget, Base):

    def __init__(self, parent, texts=None, selectedInd=None, exclusive=True,
                 callback=None, direction='h', tipTexts=None, objectNames=None, squared=False,
                 extraLabels=None, extraLabelIcons=None, enabledTexts=None,
                 icons=None, initButtons=True, numGridRows=1, numGridCols=None,
                 **kwds):

        """

        :param parent:
        :param texts:
        :param selectedInd:
        :param exclusive:
        :param callback:
        :param direction: str: one of 'v', 'h', 'gv', 'gh'
                                    - If direction is ‘gv’ (grid vertical), buttons are placed top to bottom until the number of rows (numGridRows) is reached, then move to the next column.
                                    e.g. for ABCDEFGH, numGridRows=2:
                                        | A C E G |
                                        | B D F H |
                                    - If direction is ‘gh’ (grid horizontal), buttons are placed left to right until the number of columns (numGridCols) is reached, then move to the next row.
                                    e.g. for ABCDEFGH, numGridRows=2:
                                        | A B C D |
                                        | E F G H |
                                    - If direction is ‘h’ (horizontal) buttons are placed left to right in 1 row with multiple columns
                                        | A B C D E F G H |
                                    - If direction is ‘v’ (vertical) buttons are placed top to bottom in multiple rows and one single column

        :param tipTexts:
        :param objectNames:
        :param squared:
        :param extraLabels:
        :param extraLabelIcons:
        :param enabledTexts:
        :param icons:
        :param initButtons:
        :param numGridRows:
        :param numGridCols:
        :param kwds:
        """

        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)

        if texts is None:
            texts = []

        self.texts = texts
        direction = direction.lower()
        buttonGroup = self.buttonGroup = QtWidgets.QButtonGroup(self)
        self.isExclusive = exclusive
        buttonGroup.setExclusive(self.isExclusive)
        self.squared = squared
        self.extraLabels = extraLabels
        self.extraLabelIcons = extraLabelIcons

        if not tipTexts:
            tipTexts = [None] * len(texts)
        if not objectNames:
            objectNames = [None] * len(texts)

        # added functionality for icons
        # icons is a list of str/tuple
        #
        #   e.g. icons = ('icons/strip-row', 'strip-column')
        #       icons = ( ('icons/strip-row', (24,24)),
        #                 ('strip-column', (24,24))
        #               )
        #       where (24,24) is the size of the bounding box containing the icon

        if not icons:
            icons = [None] * len(texts)

        self.radioButtons = []
        if initButtons:
            self.setButtons(texts, selectedInd, direction, tipTexts, objectNames, icons=icons, numGridRows=numGridRows, numGridCols=numGridCols)

        # for i, text in enumerate(texts):
        #   if 'h' in direction:
        #     grid = (0, i)
        #   else:
        #     grid = (i, 0)
        #   button = RadioButton(self, text, tipText=tipTexts[i], grid=grid, hAlign='l')
        #   self.radioButtons.append(button)
        #
        #   buttonGroup.addButton(button)
        #   buttonGroup.setId(button, i)
        #
        # if selectedInd is not None:
        #   self.radioButtons[selectedInd].setChecked(True)

        buttonGroup.buttonClicked.connect(self._callback)
        self.setCallback(callback)

        if enabledTexts is not None and len(enabledTexts) == len(texts):
            for button, isEnabled in zip(self.radioButtons, enabledTexts):
                button.setEnabled(isEnabled)

    def setButtons(self, texts=None, selectedInd=None, direction='h', tipTexts=None, objectNames=None, silent=False,
                   icons=None, numGridRows=1, numGridCols=None):
        """Change the buttons in the button group"""
        # clear the original buttons
        selected = self.getSelectedText()

        for btn in self.radioButtons:
            self.buttonGroup.removeButton(btn)
            btn.deleteLater()
        self.radioButtons = []

        # Calculate the grid dimensions if direction is 'gv' or 'gh'
        numButtons = len(texts)
        if direction in ['gv', 'gh']:
            if numGridCols is None and direction == 'gh':
                numGridCols = (numButtons + numGridRows - 1) // numGridRows  # Calculate the required number of columns for 'gh'
            elif numGridCols is None and direction == 'gv':
                numGridCols = numButtons // numGridRows + (numButtons % numGridRows > 0)  # Calculate the required number of columns for 'gv'

        # rebuild the button list
        row = 0
        col = 0

        for i, text in enumerate(texts):
            if direction == 'gv':
                grid = (row, col)
                row += 1
                if row == numGridRows:
                    row = 0
                    col += 1
            elif direction == 'gh':
                grid = (row, col)
                col += 1
                if col == numGridCols:
                    col = 0
                    row += 1
            else:
                grid = (0, i) if 'h' in direction else (i, 0)

            if self.extraLabels and len(self.extraLabels) == len(self.texts):
                w = Widget(self, grid=grid, hAlign='l', setLayout=True)
                button = RadioButton(w, text, squared=self.squared, tipText=tipTexts[i], grid=(0, 0), hAlign='l')
                label = Label(w, self.extraLabels[i], grid=(0, 1), hAlign='l')
                if self.extraLabelIcons and len(self.extraLabelIcons) == len(self.texts):
                    label.setPixmap(self.extraLabelIcons[i])
            else:
                button = RadioButton(self, text, squared=self.squared, tipText=tipTexts[i], grid=grid, hAlign='l')
            self.radioButtons.append(button)

            self.buttonGroup.addButton(button)
            self.buttonGroup.setId(button, i)
            if objectNames and objectNames[i]:
                button.setObjectName(objectNames[i])

            # set icons if required - these will automatically go to the left of the text
            if icons and icons[i]:
                thisIcon = icons[i]

                if isinstance(thisIcon, str):
                    # icon list item only contains a name
                    button.setIcon(Icon(thisIcon))

                elif isinstance(thisIcon, (list, tuple)):

                    # icon item contains a list/tuple
                    if thisIcon and isinstance(thisIcon[0], str):
                        #first item is a string name
                        button.setIcon(Icon(thisIcon[0]))

                        # second value must be tuple of integer, length == 2
                        if len(thisIcon) == 2:
                            iconSize = thisIcon[1]

                            if isinstance(iconSize, (list, tuple)) and len(iconSize) == 2 and \
                                    all(isinstance(iconVal, int) for iconVal in iconSize):
                                # set the iconSize
                                button.setIconSize(QtCore.QSize(*iconSize))

        self.texts = texts
        if selectedInd is not None:
            try:
                self.radioButtons[selectedInd].setChecked(True)
                return

            except Exception:
                getLogger().debug(f'setButtons: could not set selectedInd {selectedInd}')
        elif selected:
            if selected in self.texts:
                self.set(selected, silent=silent)
                return

            else:
                getLogger().debug(f'setButtons: could not set selected {selected}')
        elif self.radioButtons:
            self.radioButtons[0].setChecked(True)

    def getRadioButton(self, text):
        for rb in self.radioButtons:
            if rb.text() == text:
                return rb

        raise ValueError(f'radioButton {text} not found in the list')

    def get(self):
        texts = [i.text() for i in self.radioButtons if i.isChecked()]
        if self.isExclusive:
            # could still be undefined
            return texts[-1] if texts else None
        else:
            return texts

    def getIndex(self):
        ixs = [i for i, rb in enumerate(self.radioButtons) if rb.isChecked()]
        if self.isExclusive:
            # if exclusive then one-and-only-one MUST be set
            return ixs[-1] if ixs else 0
        else:
            return ixs

    def __len__(self):
        """Return the number of buttons in the radio-group
        """
        return len(self.buttonGroup.buttons())

    @property
    def isChecked(self):

        return self.buttonGroup.checkedButton() is not None

    def set(self, text, silent=False):
        if text in self.texts:
            i = self.texts.index(text)
            self.setIndex(i)
            if self.callback and not silent:
                self.callback()
        else:
            self.deselectAll()

    def getSelectedText(self):
        for radioButton in self.radioButtons:
            if radioButton.isChecked():
                name = radioButton.text()
                if name:
                    return name

    def setIndex(self, i, blockSignals=False):
        if blockSignals:
            with self.blockWidgetSignals():
                if self.isExclusive:
                    self.deselectAll()
                try:
                    self.radioButtons[i].setChecked(True)
                except Exception:
                    getLogger().debug(f'setIndex: could not set index {i}')

        else:
            if self.isExclusive:
                self.deselectAll()
            try:
                self.radioButtons[i].setChecked(True)
            except Exception:
                getLogger().debug(f'setIndex: could not set index {i}')

    def selectButton(self, button, blockSignals=False):
        if blockSignals:
            with self.blockWidgetSignals():
                if self.isExclusive:
                    self.deselectAll()
                try:
                    i = self.radioButtons.index(button)
                    self.radioButtons[i].setChecked(True)
                except Exception:
                    getLogger().debug(f'selectButton: could not select button {button}')

        else:
            if self.isExclusive:
                self.deselectAll()
            try:
                i = self.radioButtons.index(button)
                self.radioButtons[i].setChecked(True)
            except Exception:
                getLogger().debug(f'selectButton: could not select button {button}')

    def deselectAll(self):
        self.buttonGroup.setExclusive(False)
        for i in self.radioButtons:
            i.setChecked(False)
        self.buttonGroup.setExclusive(self.isExclusive)

    def setCallback(self, callback):

        self.callback = callback

    def _callback(self, button):

        if self.callback and button:
            # button = self.buttonGroup.buttons[ind]
            # FIXME the callback should also pass in the selected value. like pulldown checkbox etc...
            #  e.g. self.callback(self.get())
            self.callback()

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.set(value)


def _fillMissingValuesInSecondList(aa, bb, value):
    if not value:
        value = ''
    if bb is None:
        bb = [value] * len(aa)
    if len(aa) != len(bb):
        if len(aa) > len(bb):
            m = len(aa) - len(bb)
            bb += [value] * m
        else:
            raise NameError('Lists are not of same length.')
    return aa, bb


class RadioButtonsWithSubCheckBoxes(QtWidgets.QWidget, Base):
    """
    Re-implementation of RadioButtons with the option to add a list of Checkboxes.
    Direction: only vertical.
    exclusive only,
    checkBoxesTexts = # orderedDictionary
                {
                RadioButtonText1:
                    {
                    CheckBoxTexts: ['A','B','C'],
                    CheckBoxTipTexts: ['A','B','C'],
                    CheckBoxCheckedText:['B'],
                    CheckBoxCallbacks: [None, None, None]
                    },
                ...
                }

    """

    def __init__(self, parent,
                 texts=None,
                 selectedInd=0,
                 callback=None,
                 tipTexts=None,
                 objectNames=None,
                 ##checkBoxes
                 checkBoxesDictionary=None,  # see docs
                 **kwds):
        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)

        self.texts = texts
        self.parent = parent
        texts, tipTexts = _fillMissingValuesInSecondList(texts, tipTexts, value='')
        self.isExclusive = True
        self.direction = 'v'
        self.callback = callback
        self.radioButtons = []
        self.checkBoxesDictionary = checkBoxesDictionary or {}
        self._setButtons(texts=texts, selectedInd=selectedInd, tipTexts=tipTexts,
                         checkBoxesDictionary=self.checkBoxesDictionary)

    def _setButtons(self, texts, selectedInd, tipTexts, checkBoxesDictionary):
        self.radioButtons = []
        for i, radioButtonText in enumerate(texts):
            checkBoxesDict = checkBoxesDictionary.get(radioButtonText)
            _tiptext = tipTexts[i]
            _checked = i == selectedInd
            radioButtonWithSubSelection = RadioButtonWithSubSelection(self, text=radioButtonText,
                                                                      checked=_checked,
                                                                      tipText=_tiptext,
                                                                      checkBoxDictionary=checkBoxesDict,
                                                                      grid=(i + 1, 0))
            radioButtonWithSubSelection.radioButton.clicked.connect(
                    partial(self._buttonClicked, radioButtonWithSubSelection, i))

            self.radioButtons.append(radioButtonWithSubSelection)

    def setIndex(self, i):
        if self.isExclusive:
            self.deselectAll()
        self.radioButtons[i].setChecked(True)

    def _buttonClicked(self, button, index):
        if not self.isExclusive:
            self.radioButtons[index].setChecked(button.isChecked())
        else:
            self.setIndex(index)

        self._callback(button)

    def _callback(self, button):
        if self.callback and button:
            self.callback(self.get())

    def deselectAll(self):
        for i in self.radioButtons:
            i.setChecked(False)

    def getSelectedText(self):
        for radioButton in self.radioButtons:
            if radioButton.isChecked():
                name = radioButton.getText()
                if name:
                    return name

    def get(self):
        """
        :return: A dictionary of selected radioButton text and a list of Selected CheckBoxes text

        """
        return {radioButton.getText(): radioButton.getSelectedCheckBoxes() for radioButton in self.radioButtons
                if radioButton.isChecked()}

    def getRadioButtonByText(self, text):
        for rb in self.radioButtons:
            if rb.getText() == text:
                return rb


class EditableRadioButtons(Widget, Base):
    """
    Re-implementation of RadioButtons with the option to edit a selection
    """

    def __init__(self, parent, texts=None, backgroundTexts=None, editables=None, selectedInd=None,
                 callback=None, direction='h', tipTexts=None, objectNames=None, icons=None, exclusive=True,
                 **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        if texts is None:
            texts = []

        self.texts = texts
        direction = direction.lower()
        self.direction = direction
        self.isExclusive = exclusive

        texts, editables = _fillMissingValuesInSecondList(texts, editables, value=False)
        texts, tipTexts = _fillMissingValuesInSecondList(texts, tipTexts, value='')
        texts, backgroundTexts = _fillMissingValuesInSecondList(texts, backgroundTexts, value='')
        texts, icons = _fillMissingValuesInSecondList(texts, icons, value=None)

        self.radioButtons = []
        self.callback = callback

        self._setButtons(texts=texts, editables=editables, selectedInd=selectedInd, direction=direction,
                         tipTexts=tipTexts, backgroundTexts=backgroundTexts, objectNames=objectNames, icons=icons, )

    def setButtons(self, *args, **kwargs):
        self._setButtons(*args, **kwargs)

    def _setButtons(self, texts=None, editables=None, selectedInd=None, direction='h', tipTexts=None,
                    objectNames=None, backgroundTexts=None, silent=False, icons=None):
        """Change the buttons in the button group """
        texts, editables = _fillMissingValuesInSecondList(texts, editables, value=False)
        texts, tipTexts = _fillMissingValuesInSecondList(texts, tipTexts, value='')
        texts, backgroundTexts = _fillMissingValuesInSecondList(texts, backgroundTexts, value='')
        selected = self.getSelectedText()
        for btn in self.radioButtons:
            btn.deleteLater()
        self.radioButtons = []
        # rebuild the button list
        for i, text in enumerate(texts):
            grid = (0, i) if 'h' in direction else (i, 0)

            button = EditableRadioButton(self, text=text, editable=editables[i], tipText=tipTexts[i],
                                         backgroundText=backgroundTexts[i],
                                         callbackOneditingFinished=False)  #callback=self.callback,
            button.lineEdit.editingFinished.connect(partial(self._editingFinishedCallback, button, i))
            button.radioButton.clicked.connect(partial(self._buttonClicked, button, i))
            self.radioButtons.append(button)
            layout = self.getLayout()
            layout.addWidget(button, *grid)
            if objectNames and objectNames[i]:
                button.radioButton.setObjectName(objectNames[i])
                button.radioButton.setObjectName(f'radioButton_{objectNames[i]}')
                button.lineEdit.setObjectName(f'lineEdit_{objectNames[i]}')

            if icons and icons[i]:
                thisIcon = icons[i]
                if isinstance(thisIcon, str):
                    button.setIcon(Icon(thisIcon))
                elif isinstance(thisIcon, (list, tuple)):
                    if thisIcon and isinstance(thisIcon[0], str):
                        button.setIcon(Icon(thisIcon[0]))
                        if len(thisIcon) == 2:
                            iconSize = thisIcon[1]
                            if isinstance(iconSize, (list, tuple)) and len(iconSize) == 2 and \
                                    all(isinstance(iconVal, int) for iconVal in iconSize):
                                button.setIconSize(QtCore.QSize(*iconSize))

        self.texts = texts
        if selectedInd is not None:
            try:
                self.radioButtons[selectedInd].setChecked(True)
            except Exception:
                getLogger().debug(f'setButtons: could not set selectedInd {selectedInd}')
        elif selected:
            if selected in self.texts:
                self.set(selected, silent=silent)
            else:
                getLogger().debug(f'setButtons: could not set selected {selected}')
        elif self.radioButtons:
            self.radioButtons[0].setChecked(True)

    def getRadioButton(self, text):
        for rb in self.radioButtons:
            if rb.text() == text:
                return rb
        else:
            raise ValueError('radioButton %s not found in the list' % text)

    def get(self):
        texts = [i.text() for i in self.radioButtons if i.isChecked()]
        if self.isExclusive:
            return texts[-1] if texts else None
        else:
            return texts

    def getIndex(self):
        ixs = [i for i, rb in enumerate(self.radioButtons) if rb.isChecked()]
        if self.isExclusive:
            # if exclusive then one-and-only-one MUST be set
            return ixs[-1] if ixs else 0
        else:
            return ixs

    def set(self, text, silent=False):
        if self.isExclusive:
            self.deselectAll()
        if text in self.texts:
            i = self.texts.index(text)
            self.setIndex(i)
            if self.callback and not silent:
                self.callback()

    def setExclusive(self, value):
        # raise ValueError('Not implemented yet')
        self.isExclusive = value

    def getSelectedText(self):
        for radioButton in self.radioButtons:
            if radioButton.isChecked():
                name = radioButton.text()
                if name:
                    return name

    def setIndex(self, i):
        if self.isExclusive:
            self.deselectAll()
        try:
            self.radioButtons[i].setChecked(True)
        except:
            getLogger().debug(f'setIndex: could not set index {i}')

    def _buttonClicked(self, button, index):
        if not self.isExclusive:
            self.radioButtons[index].setChecked(button.isChecked())
            self._callback(button)
        else:
            self.setIndex(index)
            self._callback(button)

    def deselectAll(self):
        for i in self.radioButtons:
            i.setChecked(False)

    def setCallback(self, callback):
        self.callback = callback

    def _callback(self, button):

        if self.callback and button:
            self.callback(self.get())

    def _editingFinishedCallback(self, button, index):
        if button:
            self._buttonClicked(button, index)

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.getIndex()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setIndex(value)


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog

    def _testCallback(self, *args):
        print('GET:', self.get())
        print('INDEX', self.getIndex())
        print('SELECTED:', self.getSelectedText())

    def _testCall(*args):
        print('ddd', args)

    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test radioButtons', setLayout=True)

    buttonGroup = QtWidgets.QButtonGroup(popup)
    # radioButtons = EditableRadioButtons(parent=popup, texts=['a', ''], tipTexts=['', ''],
    #                                     editables=[False, True], grid=(0, 0),
    #                                     callback=_testCall, direction='v')

    checkBoxesDict = {
        '_txt1':
            {'CheckBoxTexts': ['_cb1Txt1', '_cb1Txt2', '_cb1Txt3']},
        '_txt2':
            {'CheckBoxTexts': ['_cb2Txt1', '_cb2Txt2', '_cb3Txt3']},
        }
    # rbs = RadioButtonsWithSubCheckBoxes(parent=popup,
    #                                     texts=['_txt1','_txt2'],
    #                                     tipTexts=[''],
    #                                     checkBoxesDictionary=checkBoxesDict,
    #                                     grid=(1, 0))
    # radioButtons.setCallback(partial(testCallback, radioButtons))
    # for i in range(10):
    #     button = RadioButton(popup, text='TEST', grid=(i, 0),
    #                          callback=testCall)  # partial(self.assignSelect
    #     buttonGroup.addButton(button)
    from ccpn.ui.gui.widgets.Label import maTex2Pixmap

    mathExamples = [
        r'$\sqrt{\frac{1}{N}\sum_{i=0}^N (\alpha_i*\delta_i)^2}$',
        '$\\lambda_{soil}=k_{soil} / C_{soil}$']

    pixmaps = [maTex2Pixmap(ex) for ex in mathExamples]
    # radioButtons = RadioButtons(popup, texts=['fff', 'gggg'], extraLabels=['', ''], extraLabelIcons=pixmaps, grid=(1, 0))
    radioButtons = RadioButtons(popup, texts='ABCDEFGH', direction='gh', numGridRows=2, numGridCols=7, grid=(1, 0))

    popup.raise_()
    popup.exec()

    app.start()


if __name__ == '__main__':
    main()
