from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt
import sys
import string

# Import your constants
from ccpnmr.chemBuild.general.Constants import LINK, LINKS, ELEMENTS, CCPN_MOLTYPES


# Define field labels
NAME = 'Name'
CCPCODE = 'Ccp Code'
MOLTYPE = 'Molecule Type'
FileExt = '.xml'
ALLTYPES = ['< Select >'] + list(CCPN_MOLTYPES)
PREVIEWFILENAME = 'ChemComp File Name'

class ChemCompExportDialog(QDialog):
    def __init__(self, parent=None, data=None, disabledMolTypes=None):
        super().__init__(parent)
        self.setWindowTitle('ChemComp Export Dialog')

        # Fix the window size
        self.setMaximumWidth(500)

        # Layout
        layout = QVBoxLayout(self)

        # First Line Edit
        self.label1 = QLabel(NAME)
        self.nameW = QLineEdit(self)
        self.errorLabel1 = QLabel('❌ Non-ASCII characters are not allowed', self)
        self.errorLabel1.setStyleSheet('color: red;')
        self.errorLabel1.hide()
        layout.addWidget(self.label1)
        layout.addWidget(self.nameW)
        layout.addWidget(self.errorLabel1)

        # Second Line Edit
        self.label2 = QLabel(CCPCODE)
        self.ccpCodeW = QLineEdit(self)
        self.errorLabel2 = QLabel('❌ Non-ASCII characters are not allowed', self)
        self.errorLabel2.setStyleSheet('color: red;')
        self.errorLabel2.hide()
        layout.addWidget(self.label2)
        layout.addWidget(self.ccpCodeW)
        layout.addWidget(self.errorLabel2)

        # ComboBox
        self.label3 = QLabel(MOLTYPE)
        self.molTypeW = QComboBox(self)
        self.molTypeW.addItems(ALLTYPES)
        self.disabledMolTypes = disabledMolTypes
        self._disableLabelsOnPullDown(self.molTypeW, disabledMolTypes)
        layout.addWidget(self.label3)
        layout.addWidget(self.molTypeW)

        # Mandatory Error Label
        self.mandatoryLabel = QLabel('❌ All fields are required!', self)
        self.mandatoryLabel.setStyleSheet('color: red;')
        self.mandatoryLabel.hide()
        layout.addWidget(self.mandatoryLabel)

        self.filenameLabel = QLabel(PREVIEWFILENAME)
        self.filenameLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.filenameLabel)

        self.sumLabel = QLabel('')
        self.sumLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.sumLabel)

        # OK Button (Initially Disabled)
        self.okButton = QPushButton('OK', self)
        self.okButton.setEnabled(False)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)

        # Connect signals
        self.nameW.textChanged.connect(lambda: self.validateAscii(self.nameW, self.errorLabel1))
        self.ccpCodeW.textChanged.connect(lambda: self.validateAscii(self.ccpCodeW, self.errorLabel2))
        self.nameW.textChanged.connect(self.updateState)
        self.ccpCodeW.textChanged.connect(self.updateState)
        self.molTypeW.currentTextChanged.connect(self.updateState)

        # Initialize UI state
        if data is not None:
            self.setWidgets(data)
        self.updateState()

    def getSelection(self):
        """Return dictionary of current widget values."""
        return {
            NAME: self.getName(),
            CCPCODE: self.getCcpCode(),
            MOLTYPE: self.getMolType()
        }

    def setWidgets(self, data):
        """Set widget values from a dictionary."""
        self.nameW.setText(data.get(NAME, ''))
        self.ccpCodeW.setText(data.get(CCPCODE, ''))
        index = self.molTypeW.findText(data.get(MOLTYPE, ''), Qt.MatchFixedString)
        if index >= 0:
            selected_item = self.molTypeW.itemText(index)
            if selected_item not in self.disabledMolTypes:
                self.molTypeW.setCurrentIndex(index)
        self.updateState()

    def getFileName(self):
        values = [self.getMolType(), self.getCcpCode(), self.getName()] # must be this order ! molType+ccpCode+guid
        if self._allEntryValid():
            text = f"{'+'.join(filter(None, values))}{FileExt}"
            return text
        return None

    def getName(self):
        return self.nameW.text().strip()

    def getCcpCode(self):
        return self.ccpCodeW.text().strip()

    def getMolType(self):
        return self.molTypeW.currentText()

    def updateSumLabel(self):
        """Update the sum label dynamically."""
        fn = self.getFileName()
        if fn:
            self.sumLabel.setText(fn)
        else:
            self.sumLabel.setText(f"N/A")

    def validateAscii(self, lineEdit, errorLabel):
        """Ensure input contains only alphanumeric ASCII characters and show warning if needed."""
        text = lineEdit.text()

        # Define disallowed characters
        invalid_chars = ['+', ',', '.']

        # Create a valid string with only alphanumeric characters and excluding invalid characters
        validText = ''.join(c for c in text if
                            c.isalnum() and
                            c not in invalid_chars and
                            c in string.printable)

        # Track removed characters
        removed = {c for c in text if c not in validText}

        if removed:
            print(f'Non-alphanumeric or disallowed characters removed: {", ".join(removed)}')

        if text != validText:
            # Identify the first invalid character for error message
            invalidChar = next((c for c in text if not c.isalnum() or c in invalid_chars), None)
            if invalidChar:
                errorLabel.setText(f'❌ Invalid character: {repr(invalidChar)}')
                errorLabel.show()
            lineEdit.setText(validText)
        else:
            errorLabel.hide()

        self.updateState()

    def _allEntryValid(self):
        return all([self.getName(),
                     self.getCcpCode(),
                     self.getMolType() in CCPN_MOLTYPES])

    def updateState(self):
        """Enable OK button only if all fields are filled and update sum label."""
        filled = self._allEntryValid()
        self.okButton.setEnabled(filled)
        self.mandatoryLabel.setVisible(not filled)
        self.updateSumLabel()

    @staticmethod
    def _getItemIndex(combobox, text):
        for i in range(combobox.count()):
            if combobox.itemText(i) == text:
                return i

    def _disableLabelsOnPullDown(self, combobox, texts):
        """ Disable items from pulldown (not selectable, not clickable). And if given, changes the colour """
        for text in texts:
            if text is not None and self._getItemIndex(combobox, text) is not None:
                if item := combobox.model().item(self._getItemIndex(combobox, text) ):
                    item.setEnabled(False)

# Run the dialog standalone
if __name__ == '__main__':
    app = QApplication(sys.argv)
    data =  {
            NAME: 'MySugar',
            CCPCODE: 'HEX',
            MOLTYPE: CCPN_MOLTYPES[-1]
        }
    dialog = ChemCompExportDialog(data=data)
    if dialog.exec_():
        print(dialog.getSelection())
    sys.exit(app.exec_())