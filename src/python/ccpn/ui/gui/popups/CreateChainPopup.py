"""
Module Documentation here

 'Ala Leu Ala Leu Ala Ser Asp Glu Trp Val Leu Ala Leu Ala Leu Leu Ala Ala Trp Glu Arg Thr Leu Ala Ala Trp Glu Arg Thr Tyr Tyr Ala Leu Leu Ala Ala Trp Glu Arg Thr Tyr'
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
__dateModified__ = "$dateModified: 2025-03-20 17:23:40 +0000 (Thu, March 20, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-07-04 15:21:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from functools import partial

from ccpn.util.AttrDict import AttrDict
from ccpn.framework.Application import getProject
from html.parser import HTMLParser
from ccpn.core.Chain import Chain
from ccpn.core.lib.ChainLib import SequenceHandler, CCPCODE, CODE1LETTER, CODE3LETTER, ISVALID, INPUT, ERRORS, _copySequenceToClipboard
from ccpn.core.lib.MoleculeLib import _nextChainCode
from ccpn.core.lib.ContextManagers import queueStateChange
from ccpn.core.lib.WeakRefLib import WeakRefDescriptor
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, Qt
from ccpn.ui.gui.popups.AttributeEditorPopupABC import AttributeEditorPopupABC
from ccpn.ui.gui.popups.Dialog import _verifyPopupApply
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.CheckBox import CheckBox

DefaultAddAtomGroups = True
DefaultAddPseudoAtoms = False
DefaultAddNonstereoAtoms = True
DefaultSetBoundsForAtomGroups = False
ONELETTERCODE = 'One-Letter Code'
THREELETTERCODE = 'Three-Letter Code'
CCPCODESELECTION = 'Ccp Code'

RED = '#d55e00'
BLACK = 'black'

def divideChunks(l, n):
  for i in range(0, len(l), n):
    yield l[i:i + n]


class _HTMLSequenceEditorParser(HTMLParser):
    """ This is a custom parser to ensure the SequenceEditor.plainText works properly and without any subscripts.
    html to plainText
     Note: This class could be redundant if we had BeautifulSoup:
     html to plainText  could be achieved with BeautifulSoup package in a couple E.g.:

    ::

        def toPlainText(self:SequenceEditor): ...
            soup = BeautifulSoup(html_string, 'html.parser')
            subscripts = soup.find_all('span', style=lambda value: value and 'vertical-align:sub' in value)
            for sub in subscripts:
                sub.decompose()
            return soup.getText(' ', strip=True)

     """

    def __init__(self):
        super().__init__()
        self.text = ""
        self.inStyle = False
        self.inSubscript = False
        self.firstDataEncountered = False

    def feed(self, data: str) -> None:
        index = data.find("<!DOCTYPE")
        # If "<!DOCTYPE" is found, remove everything before it
        if index != -1:
            data = data[index:]
        return super().feed(data)

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.inStyle = True
        elif tag == "span":
            for attr in attrs:
                if attr[0] == "style" and "vertical-align:sub" in attr[1]:
                    self.inSubscript = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.inStyle = False
        elif tag == "span":
            self.inSubscript = False

    def handle_data(self, data):
        if not self.inStyle and not self.inSubscript and data.strip():
            if not self.firstDataEncountered:
                self.text += data.strip() + " "
                self.firstDataEncountered = True
            else:
                self.text += data.strip() + " "

class _SequenceTextEditorBase(TextEditor):
    textChangedSignal = pyqtSignal()
    _codeType = CODE1LETTER
    _plainTextSeparator = ''
    demoSequence = 'ABCD'
    extraContextMenuActions = {
        'Copy all to clipboard as 1LetterCodes' : { 'codeType':CODE1LETTER, 'separatorType': '', 'enabled':True},
        'Copy all to clipboard as 3LetterCodes': {'codeType':CODE3LETTER, 'separatorType':' ', 'enabled': True},
        'Copy all to clipboard as CcpCodes': {'codeType':CCPCODE, 'separatorType':' ',  'enabled': True},
        }
    parentPopup = WeakRefDescriptor()

    def __init__(self, parent, parentPopup, maxColumns=10,  callback=None,  **kwargs):
        super().__init__(parent, backgroundText=self.demoSequence,  **kwargs)

        self.parentPopup = parentPopup # needed to get notifications on dynamic value changes.
        self.maxColumns = maxColumns
        self.callback = callback
        self._project = getProject()
        self._molType = self._getMolType()
        self._htmlFormattingMode = False
        self._sequenceHandler = SequenceHandler(self._project, moleculeType=self._molType, errorMode='warn', supressWarning=True)
        self.sequenceStartsAt = self.parentPopup.startingSequenceCodeWidget.get()
        self.parentPopup.startingSequenceCodeWidget.valueChanged.connect(self._setStartingSequenceCode)
        self.parentPopup.molTypePulldown.currentIndexChanged.connect(self._setMolType)
        self.setPlaceholderText(str(self.backgroundText))
        self.mouseLeft.connect(self._editingFinishedCallback)


    def toPlainText(self):
        htmlString = self.toHtml()
        parser = _HTMLSequenceEditorParser()
        parser.feed(htmlString)
        return parser.text.strip()

    def setHtmlSequence(self, sequence:str):
        df = self._sequenceToDataFrame(sequence)
        sequenceHtml = self._dataFrameToHtml(df)
        self.setHtml(sequenceHtml)

    def setPlainSequence(self, sequence:str):
        if self._codeType in [CODE1LETTER, CODE3LETTER]:
            sequence = sequence.upper()
        sequenceMap = self._parseSequence(sequence)
        formattedSequence = sequenceMap.get(self._codeType, '')
        sequence = self._plainTextSeparator.join(formattedSequence)
        self.setText(sequence)

    def getSequence(self):
        sequenceMap = self.getSequenceMap()
        formattedSequence = sequenceMap.get(self._codeType)
        return formattedSequence

    def getSequenceMap(self):
        text = self.toPlainText()
        return self._parseSequence(text)

    def  _parseSequence(self, sequence):
        """Parse the sequence depending on the TextEditor subclass behaviour.
        :param sequence: str
        :return dict
        """
        sequenceMap = self._sequenceHandler.parseSequence(sequence)
        return sequenceMap

    def getSequenceAsCcpCode(self):
        sequenceMap = self.getSequenceMap()
        ccpCodeSequence = sequenceMap.get(CCPCODE)
        return ccpCodeSequence

    def _isValidSequence(self):
        sequenceMap = self.getSequenceMap()
        isValid = sequenceMap.get(ISVALID)
        return isValid

    def _sequenceToDataFrame(self, text):
        if self._codeType in [CODE1LETTER, CODE3LETTER]:
            text = text.upper()
        sequenceMap = self._parseSequence(text)
        input = sequenceMap.get(INPUT)
        errorIndex = sequenceMap.get(ERRORS)
        formattedSequence = sequenceMap.get(self._codeType)
        if len(errorIndex)>0:
            formattedSequence = input
        df = self._listToDataFrame(formattedSequence, maxColumns=self.maxColumns, startAccumulatedCount=1)
        return df

    def isMultipleOfMaxColumnsCount(self, number):
        return number % self.maxColumns == 0

    @staticmethod
    def _listToDataFrame(stringList, maxColumns=10, startAccumulatedCount=1):
        """ Create a dataframe given a list of string. Each item is a code in the sequence.
        Make a maximum of column. Start an accumulated value count from a given starting point.
        Index= the accumulated values"""
        numRows = len(stringList) // maxColumns
        if len(stringList) % maxColumns != 0:
            numRows += 1
        # Pad the string list with None to make it rectangular
        stringList = stringList + [None] * (numRows * maxColumns - len(stringList))
        data = [stringList[i:i + maxColumns] for i in range(0, len(stringList), maxColumns)]
        df = pd.DataFrame(data)
        accumulatedCount = df.apply(lambda row: row.count(), axis=1).cumsum() + startAccumulatedCount - 1
        df.set_index(accumulatedCount, inplace=True)
        return df

    def _getDataFrameSequenceCodes(self, dataFrame):

        sequenceCodesDF = pd.DataFrame(index=dataFrame.index, columns=dataFrame.columns)
        sequenceStartsAt =self.sequenceStartsAt
        for i in range(dataFrame.shape[0]):
            for j in range(dataFrame.shape[1]):
                sequenceCodesDF.iloc[i, j] = sequenceStartsAt
                sequenceStartsAt += 1
        return sequenceCodesDF

    def _dataFrameToHtml(self, dataFrame):
        standardsOnly = self._codeType == CODE1LETTER
        allowedValues = self._sequenceHandler.getAvailableCodeByType(self._codeType, standardsOnly=standardsOnly)
        html = "<table style='border-collapse: collapse; width: 100%;'>"
        sequenceCodesDF = self._getDataFrameSequenceCodes(dataFrame)

        for (colSeqNum, seqNumRow), (inx, row) in zip(sequenceCodesDF.iterrows(), dataFrame.iterrows()):
            html += "<tr>"
            for (ixSeqNum, seqNum), (inxRow, value) in zip(seqNumRow.items(), row.items()):
                value = str(value).replace(' ', '').replace(',', '').replace('None', '')
                if not value:
                    continue
                isValid = value in allowedValues
                colour = RED if not isValid else BLACK
                cellBorderStyle = f'border: 2px solid  {colour};' if not isValid else ''

                if value:
                    if int(seqNum) % 5 == 0 or int(seqNum) % 10 == 0:  # add a subscript if it's a multiple of 5/10
                        value += f'<sub>{seqNum}</sub>'

                html += f"<td style='color: {colour}; text-align: center; padding: 3px; {cellBorderStyle}'>{value}</td>"

            html += "</tr>"

        html += "</table>"
        return html


    def formatSequenceAsHTML(self):
        text = self.toPlainText()
        with self.blockWidgetSignals():
            self.setHtmlSequence(text)
        self._htmlFormattingMode = True

    def formatSequenceAsText(self):
        text = self.toPlainText()
        with self.blockWidgetSignals():
            self.setPlainSequence(text)
        self._htmlFormattingMode = False

    def _getMolType(self):
        return self.parentPopup.molTypePulldown.get()

    def _setStartingSequenceCode(self, *args):
        self.sequenceStartsAt = self.parentPopup.startingSequenceCodeWidget.get()
        if self._htmlFormattingMode:
            self.formatSequenceAsHTML()

    def _setMolType(self, *args):
        self._molType = self.parentPopup.molTypePulldown.get()
        self._sequenceHandler.setMoleculeType(self._molType)
        if self._htmlFormattingMode:
            self.formatSequenceAsHTML()

    def context_menu(self):
        self.standardContextMenu = self.createStandardContextMenu()
        # Create a custom context menu
        self.customContextMenu = menu = Menu('Editor', self)
        self.customContextMenu.addActions(self.standardContextMenu.actions())  # Add standard actions
        self.customContextMenu.addSeparator()
        for key, values in self.extraContextMenuActions.items():
            codeType = values.get('codeType')
            separatorType = values.get('separatorType','')
            sequenceMap = self.getSequenceMap()
            enabled = values.get('enabled')
            if not self._isValidSequence() or not self.getSequence():
                enabled = False
            callback = partial(_copySequenceToClipboard, sequenceMap, codeType, separatorType)
            menu.addItem(text=key, callback=callback, enabled=enabled)
        self.customContextMenu.exec_(QtGui.QCursor.pos())

    def _editingFinishedCallback(self, *args, **kwargs):
        if self.callback:
            sequenceMap = self.getSequenceMap()
            self.callback(sequenceMap)

    def keyPressEvent(self, event):

        if event.key() in [
                           Qt.Key_Return,
                            Qt.Key_Enter]:
            self.textChangedSignal.emit()
            return super().keyPressEvent(event)

        return super().keyPressEvent(event)


class _1LetterCodeSequenceEditor(_SequenceTextEditorBase):

    _codeType = CODE1LETTER
    _name = ONELETTERCODE
    demoSequence = '''Standard residues only: ALSTWYA'''

    def  _parseSequence(self, sequence):
        """Parse the sequence ensuring is always a one-Letter code .
        :param sequence: str
        :return dict
        """
        # Remove spaces, newline characters, and common separators
        sequence = self._sequenceHandler._cleanString(sequence)
        sequenceMap = self._sequenceHandler.parseSequence(sequence)
        return sequenceMap

class _3LetterCodeSequenceEditor(_SequenceTextEditorBase):
    _codeType = CODE3LETTER
    _name = THREELETTERCODE
    demoSequence = '''Three letter codes space or comma-separated. E.G.:  ALA ARG ASN'''
    _plainTextSeparator = ' '

    def  _parseSequence(self, sequence):
        """Parse the sequence ensuring is alwyas a one-Letter code .
        :param sequence: str
        :return dict
        """
        # Remove spaces, newline characters, and common separators
        sequence = self._sequenceHandler._cleanString(sequence)
        codeLength = self._sequenceHandler._get3CodeLengthByMolType()
        sequence = list(divideChunks(sequence, codeLength))
        sequenceMap = self._sequenceHandler.parseSequence(sequence)
        return sequenceMap

class _CcpCodeSequenceEditor(_SequenceTextEditorBase):
    _codeType = CCPCODE
    _name = CCPCODESELECTION
    _plainTextSeparator = ' '

    demoSequence = '''Any CcpCode: \n Ala Arg Ser or \n Ala Arg Ser Atp or \n MyCcpCode etc '''


    def  _parseSequence(self, sequence):
        """Parse the sequence ensuring is alwyas a one-Letter code .
        :param sequence: str
        :return dict
        """
        # Remove spaces, newline characters, and common separators
        sequence = self._sequenceHandler._strSequenceToList(sequence, codeLength=-1)
        sequenceMap = self._sequenceHandler.parseSequence(sequence)
        return sequenceMap

class _SequenceTabs(Tabs):
    def __init__(self, parent, parentPopup, callback=None, **kwds):
        super().__init__(parent, **kwds)
        self._tabEditors = {}
        self._editorsClasses = [_1LetterCodeSequenceEditor,  _3LetterCodeSequenceEditor, _CcpCodeSequenceEditor]
        for i, editorCls in enumerate(self._editorsClasses):
            editor = editorCls(self, parentPopup=parentPopup,  callback= callback)
            self._tabEditors[editor._name] = editor
            self.addTab(editor, editor._name)

    def getSequence(self):
        tabName = self.getSelectedTabText()
        sequenceEditor =  self._tabEditors.get(tabName)
        sequence = sequenceEditor.getSequence()
        return sequence

    def getSequenceAsCcpCode(self):
        """Get the sequence from the selected Editor and convert it to a CcpCode. """
        tabName = self.getSelectedTabText()
        sequenceEditor = self._tabEditors.get(tabName)
        sequence = sequenceEditor.getSequenceAsCcpCode()
        return sequence

    def _isValidSequence(self):
        tabName = self.getSelectedTabText()
        sequenceEditor = self._tabEditors.get(tabName)
        return sequenceEditor._isValidSequence()

    def setSequence(self, sequence, editorName=None):
        if editorName is None: #set  the sequence to all tabs
            for k, sequenceEditor in self._tabEditors.items():
                sequenceEditor.setHtmlSequence(sequence)
        else:
            sequenceEditor = self._tabEditors.get(editorName)
            if sequenceEditor is not None:
                sequenceEditor.setHtmlSequence(sequence)
                self.selectTabText(editorName)

    def _reformatSelected(self):
        sequenceEditor = self._tabEditors.get(self.getSelectedTabText())
        if sequenceEditor is not None:
            sequenceEditor.formatSequenceAsHTML()

    def _setPlainSequence(self):
        sequenceEditor = self._tabEditors.get(self.getSelectedTabText())
        if sequenceEditor is not None:
            sequenceEditor.formatSequenceAsText()


class CreateChainPopup(AttributeEditorPopupABC):
    """
    Create new chain popup
    """
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    klass = Chain  # The class whose properties are edited/displayed
    attributes = []  # A list of (attributeName, getFunction, setFunction, kwds) tuples;

    EDITMODE = False
    WINDOWPREFIX = 'New '

    ENABLEREVERT = True
    _code = None

    def __init__(self, parent=None, mainWindow=None, project=None, **kwds):
        """
        Initialise the widget
        """
        # flag required because using attributeDialog which tries to populate
        self._popupReady = False

        super().__init__(parent, mainWindow=mainWindow, size=(500, 300), **kwds)

        # set up the widgets
        self._setWidgets()

        # define the blank object to hold the new attributes
        self._defineObject()
        # attach the callbacks for the widgets
        self.moleculeEdit.textChanged.connect(self._queueSetMoleculeName)
        self.commentName.textChanged.connect(self._queueSetComment)
        self.startingSequenceCodeWidget.valueChanged.connect(self._queueSetSequenceStart)
        self.lineEdit2a.textChanged.connect(self._queueSetChainCode)

        self.molTypePulldown.currentIndexChanged.connect(self._queueSetMolType)
        self.expandAtomsFromAtomSetW.clicked.connect(self._queueSetExpandAtomsFromAtomSets)
        self.addNonstereoAtomsW.clicked.connect(self._queueSetAddNonstereoAtomsW)
        self.addPseudoAtomsW.clicked.connect(self._queueSetAddPseudoAtomsW)
        self.makeCyclicPolymer.clicked.connect(self._queueSetMakeCyclic)

        self._popupReady = True
        self._populate()

    def _setWidgets(self):
        """Set up the widgets
        """
        minimumWidth = 200
        minimumWidthEditors = 400
        minimumHeightEditors = 300

        row = 1
        label5a = Label(self.mainWidget, 'Chain Name', grid=(row, 0))
        self._code = _nextChainCode(self.project)
        self.lineEdit2a = LineEdit(self.mainWidget, grid=(row, 1), text=self._code, hAlign='left', minimumWidth=minimumWidth)

        row += 1
        label2a = Label(self.mainWidget, text="Substance Name", grid=(row, 0), )
        self.moleculeEdit = LineEdit(self.mainWidget, text="", grid=(row, 1), textAlignment='l', backgroundText='> Enter name <', hAlign='left', minimumWidth=minimumWidth)
        row += 1
        label2b = Label(self.mainWidget, text="Molecule Type", grid=(row, 0))
        self.molTypePulldown = PulldownList(self.mainWidget, grid=(row, 1), hAlign='left', minimumWidth=minimumWidth)
        row += 1
        comment = Label(self.mainWidget, text="Comment", grid=(row, 0))
        self.commentName = LineEdit(self.mainWidget, text="", grid=(row, 1),  textAlignment='l', backgroundText='> Optional <', hAlign='left', minimumWidth=minimumWidth)

        row += 1
        self.molTypes = ['protein', 'DNA', 'RNA', 'other']
        self.molTypePulldown.setData(self.molTypes)

        row += 1
        label = Label(self.mainWidget, 'Sequence Start', grid=(row, 0))
        self.startingSequenceCodeWidget = Spinbox(self.mainWidget, grid=(row, 1), value=1, min=-1000000,
                                                  max=1000000, hAlign='left', minimumWidth=minimumWidth)
        row += 1
        label3a = Label(self.mainWidget, text="Sequence", grid=(row, 0))
        self.sequenceTabWidget = _SequenceTabs(self.mainWidget, parentPopup=self,
                                                     setLayout=True, grid=(row, 1), gridSpan=(1, 3),
                                                      callback=self._checkSequenceValid,
                                                      minimumWidth=minimumWidthEditors,
                                                      minimumHeight=minimumHeightEditors)
        row += 1
        self.sequenceButtons = ButtonList(self.mainWidget, texts=['',''],
                                          tipTexts=['Reformat the sequence as plain text block','Reformat and validate the sequence in blocks of 10'],
                                          icons=['icons/sequenceBy1.png', 'icons/ReFormat.png'], callbacks=[self._setPlainSequence, self._reformatSequence],
                                          hAlign='right',   grid=(row, 1), gridSpan=(1, 3))

        row += 1
        tipText6a = "Adds atoms to represent NMR-equivalent groups, e.g. HB% for the alanine methyl atoms\n" \
                     "HB1, HB2 and HB3 or HDx,HDy,HD%,CDx,CDy,CD% etc. for the Tyr aromatic ring atoms."
        label6a = Label(self.mainWidget, 'Add NMR equivalent atoms', tipText=tipText6a, grid=(row, 0))
        self.expandAtomsFromAtomSetW = CheckBox(self.mainWidget, checked=DefaultAddAtomGroups,
                                                tipText=tipText6a, grid=(row, 1), hAlign='left')
        row += 1
        tipText7a = "Adds new atoms for non-stereospecific atoms (if any).\n" \
                    "E.g., adds HBx and HBy in addition to HB2 and HB3 for a CH2 group,\n" \
                    "or HGx% and HGy% in addition to Val HG1% and HG2%.\n" \
                    "This option is available only if 'Add NMR equivalent Atoms' is selected."
        label7a = Label(self.mainWidget, 'Add non-stereospecific atoms', tipText=tipText7a, grid=(row, 0))
        self.addNonstereoAtomsW = CheckBox(self.mainWidget, checked=DefaultAddNonstereoAtoms,
                                           tipText=tipText7a, grid=(row, 1), hAlign='left', minimumWidth=minimumWidth)
        row += 1
        tipText8a = "Adds IUPAC proton pseudo-atoms, e.g. for the NMR-equivalent Val HG11, HG12, HG13 atoms\n" \
                    "a new atom HG1% and an extra pseudo-atom MG1 will be created;\n" \
                    "also for the Val HG1% and HG2% atoms, HG% and pseudo-atom QG will be created.\n" \
                    "This option is available only if 'Add NMR equivalent Atoms' is selected."
        label8a = Label(self.mainWidget, 'Add extra pseudo-atoms', tipText=tipText8a, grid=(row, 0))
        self.addPseudoAtomsW = CheckBox(self.mainWidget, checked=DefaultAddPseudoAtoms,
                                        tipText=tipText8a, grid=(row, 1), hAlign='left', minimumWidth=minimumWidth)
        self._togglePseudoAtomOptions(self.expandAtomsFromAtomSetW.get())

        row += 1
        tipText9a = "Make a cyclic polymer;\n" \
                    "    H1, H2, H3 and OXT atoms will be removed."
        label8a = Label(self.mainWidget, 'Cyclic Polymer', tipText=tipText9a, grid=(row, 0))
        self.makeCyclicPolymer = CheckBox(self.mainWidget, checked=False,
                                          tipText=tipText9a, grid=(row, 1), hAlign='left', minimumWidth=minimumWidth)

    def _defineObject(self):
        """Initialise the new object
        """
        # define the blank object to hold the new attributes
        self.obj = AttrDict()
        self.obj.compoundName = None
        self.obj.startNumber = 1
        self.obj.shortName = self._code
        self.obj.sequence = None
        self.obj.sequenceCcpCodes = None

        self.obj.comment = None
        self.obj.molType = self.molTypes[0]
        self.obj.expandFromAtomSets = DefaultAddAtomGroups
        self.obj.addPseudoAtoms = DefaultAddPseudoAtoms
        self.obj.addNonstereoAtoms = DefaultAddNonstereoAtoms
        self.obj.isCyclic = False

    def _okClicked(self):

            super()._okClicked()

    def _applyAllChanges(self, changes):
        """Apply all changes and create sequence from self.obj
        """
        super()._applyAllChanges(changes)

        self._createChain()

    def _populate(self):
        """Populate the widgets
        """
        if self._popupReady:
            with self._changes.blockChanges():
                self.moleculeEdit.setText(self.obj.compoundName)
                self.commentName.setText(self.obj.comment)
                self.molTypePulldown.setCurrentText(self.obj.molType)
                if self.obj.sequenceCcpCodes:
                    sequenceCcpCodes = ' '.join(self.obj.sequenceCcpCodes)
                    self.sequenceTabWidget.setSequence(sequenceCcpCodes, editorName=CCPCODESELECTION)
                self.startingSequenceCodeWidget.set(self.obj.startNumber)
                self.lineEdit2a.setText(self.obj.shortName)
                self.expandAtomsFromAtomSetW.set(self.obj.expandFromAtomSets)
                self.addNonstereoAtomsW.set(self.obj.addNonstereoAtoms)
                self.addPseudoAtomsW.set(self.obj.addPseudoAtoms)
                self.makeCyclicPolymer.set(self.obj.isCyclic)
            self._reformatSequence()

    def _isValidSequence(self):
        """Return True if the Sequence in the current editor can create a valid chain """
        return  self.sequenceTabWidget._isValidSequence()

    def _reformatSequence(self):
        self.sequenceTabWidget._reformatSelected()

    def _setPlainSequence(self):
        self.sequenceTabWidget._setPlainSequence()

    def _checkSequenceValid(self, *args):
        _isValidSequence = self._isValidSequence()
        self.getButton(self.OKBUTTON).setEnabled(_isValidSequence)
        if not _isValidSequence:
            self._reformatSequence()

    def _createChain(self):
        """Creates the chain.
        """
        self.obj.sequence = self.sequenceTabWidget.getSequenceAsCcpCode()
        self.project.createChain(**self.obj)

    def _togglePseudoAtomOptions(self, value):
        isParentChecked = self.expandAtomsFromAtomSetW.get()
        self.addNonstereoAtomsW.setEnabled(isParentChecked)
        self.addPseudoAtomsW.setEnabled(isParentChecked)

    @queueStateChange(_verifyPopupApply)
    def _queueSetExpandAtomsFromAtomSets(self, value):
        """Queue changes to the expandFromAtomSets
        """
        prefValue = self.obj.expandFromAtomSets
        if value != prefValue:
            return partial(self._setExpandAtomsFromAtomSets, value)

    def _setExpandAtomsFromAtomSets(self, value: str):
        """Sets expandFromAtomSets of molecule being created.
        """
        self.obj.expandFromAtomSets = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAddNonstereoAtomsW(self, value):
        """Queue changes to the expandFromAtomSets
        """
        prefValue = self.obj.addNonstereoAtoms
        if value != prefValue:
            return partial(self._setSetAddNonstereoAtomsW, value)

    def _setSetAddNonstereoAtomsW(self, value: str):
        """Sets AddNonstereoAtoms of molecule being created.
        """
        self.obj.addNonstereoAtoms = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetAddPseudoAtomsW(self, value):
        """Queue changes to the SetAddPseudoAtomsW
        """
        prefValue = self.obj.addPseudoAtoms
        if value != prefValue:
            return partial(self._setSetAddPseudoAtomsW, value)

    def _setSetAddPseudoAtomsW(self, value: str):
        """Sets addPseudoAtoms of molecule being created.
        """
        self.obj.addPseudoAtoms = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMoleculeName(self, value):
        """Queue changes to the moleculeName
        """
        prefValue = self.obj.compoundName or None
        if value != prefValue:
            return partial(self._setMoleculeName, value)

    def _setMoleculeName(self, value: str):
        """Sets name of molecule being created.
        """
        self.obj.compoundName = value or None

    @queueStateChange(_verifyPopupApply)
    def _queueSetComment(self, value):
        """Queue changes to comment
        """
        prefValue = self.obj.comment or None
        if value != prefValue:
            return partial(self._setComment, value)

    def _setComment(self, value: str):
        """Sets comment of molecule being created.
        """
        self.obj.comment = value or None

    @queueStateChange(_verifyPopupApply)
    def _queueSetSequenceStart(self, value):
        """Queue changes to sequenceStart
        """
        textFromValue = self.startingSequenceCodeWidget.textFromValue
        prefValue = textFromValue(self.obj.startNumber)
        if textFromValue(value) != prefValue:
            return partial(self._setSequenceStart, value)

    def _setSequenceStart(self, value: int):
        """Sets sequence start for sequence being created
        """
        self.obj.startNumber = int(value)

    @queueStateChange(_verifyPopupApply)
    def _queueSetChainCode(self, value):
        """Queue changes to chainCode
        """
        prefValue = self.obj.shortName or None
        if value != prefValue:
            return partial(self._setChainCode, value)

    def _setChainCode(self, value: str):
        """Sets chain code for sequence being created.
        """
        self.obj.shortName = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMolType(self, value):
        """Queue changes to molecule type
        """
        value = self.molTypes[value]
        if value != self.obj.molType:
            return partial(self._setMolType, value)

    def _setMolType(self, value: str):
        """Sets the molecule type
        """
        self.obj.molType = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetMakeCyclic(self, value):
        """Queue changes to the SetV
        """
        prefValue = self.obj.isCyclic
        if value != prefValue:
            return partial(self._setMakeCyclic, value)

    def _setMakeCyclic(self, value: str):
        """Sets cyclic state of molecule being created.
        """
        self.obj.isCyclic = value
