"""
Abstract base class to easily implement a popup to edit attributes of V3 layer objects
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtCore
from collections import namedtuple
from functools import partial
from ccpn.core.lib.ContextManagers import queueStateChange
from ccpn.util.Common import makeIterableList, stringToCamelCase
from ccpn.util.OrderedSet import OrderedSet
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget, _verifyPopupApply
from ccpn.ui.gui.lib.ChangeStateHandler import changeState
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.ColourDialog import ColourDialog
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.RadioButton import RadioButton
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Slider import Slider
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.FileDialog import LineEditButtonDialog
from ccpn.ui.gui.widgets.GLLinearRegionsPlot import GLTargetButtonSpinBoxes
from ccpn.ui.gui.widgets.PythonEditor import QCodeEditor
from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget, CheckBoxCompoundWidget, \
    DoubleSpinBoxCompoundWidget, SelectorWidget, InputPulldown, \
    ColourSelectionWidget, LineEditPopup, ListCompoundWidget, EntryCompoundWidget, TextEditorCompoundWidget, \
    RadioButtonsCompoundWidget, ScientificSpinBoxCompoundWidget, SpinBoxCompoundWidget, EntryPathCompoundWidget


ATTRGETTER = 0
ATTRSETTER = 1
ATTRSIGNAL = 2
ATTRPRESET = 3

_commonWidgetsEdits = {
    CheckBox.__name__                       : (CheckBox.get, CheckBox.setChecked, None),
    ColourDialog.__name__                   : (ColourDialog.getColor, ColourDialog.setColour, None),
    DoubleSpinbox.__name__                  : (DoubleSpinbox.value, DoubleSpinbox.setValue, None),
    ScientificDoubleSpinBox.__name__        : (ScientificDoubleSpinBox.value, ScientificDoubleSpinBox.setValue, None),

    LineEdit.__name__                       : (LineEdit.get, LineEdit.setText, None),
    LineEditButtonDialog.__name__           : (LineEditButtonDialog.get, LineEditButtonDialog.setText, None),
    PulldownList.__name__                   : (PulldownList.currentText, PulldownList.set, None),
    RadioButtons.__name__                   : (RadioButtons.get, RadioButtons.set, None),
    RadioButton.__name__                    : (RadioButton.isChecked, RadioButton.setChecked, None),

    Slider.__name__                         : (Slider.get, Slider.setValue, None),
    Spinbox.__name__                        : (Spinbox.value, Spinbox.set, None),
    TextEditor.__name__                     : (TextEditor.get, TextEditor.setText, None),
    GLTargetButtonSpinBoxes.__name__        : (GLTargetButtonSpinBoxes.get, GLTargetButtonSpinBoxes.setValues, None),

    PulldownListCompoundWidget.__name__     : (PulldownListCompoundWidget.getText, PulldownListCompoundWidget.select,
                                               ('pulldownList.activated', 'pulldownList.pulldownTextEdited')),

    ListCompoundWidget.__name__             : (ListCompoundWidget.getTexts, ListCompoundWidget.setTexts, None),
    CheckBoxCompoundWidget.__name__         : (CheckBoxCompoundWidget.get, CheckBoxCompoundWidget.set, None),
    DoubleSpinBoxCompoundWidget.__name__    : (DoubleSpinBoxCompoundWidget.getValue, DoubleSpinBoxCompoundWidget.setValue,
                                               ('doubleSpinBox.valueChanged')),
    ScientificSpinBoxCompoundWidget.__name__: (ScientificSpinBoxCompoundWidget.getValue, ScientificSpinBoxCompoundWidget.setValue,
                                               ('scientificSpinBox.valueChanged')),
    SpinBoxCompoundWidget.__name__          : (SpinBoxCompoundWidget.getValue, SpinBoxCompoundWidget.setValue,
                                               ('spinBox.valueChanged')),

    SelectorWidget.__name__                 : (SelectorWidget.getText, SelectorWidget.select, None),
    InputPulldown.__name__                  : (InputPulldown.currentText, InputPulldown.set, None),
    ColourSelectionWidget.__name__          : (ColourSelectionWidget.currentText, ColourSelectionWidget.setColour, None),
    LineEditPopup.__name__                  : (LineEditPopup.get, LineEditPopup.set, None),
    QCodeEditor.__name__                    : (QCodeEditor.get, QCodeEditor.set, None),

    EntryCompoundWidget.__name__            : (EntryCompoundWidget.getText, EntryCompoundWidget.setText, 'entry.textEdited'),
    TextEditorCompoundWidget.__name__       : (TextEditorCompoundWidget.getText, TextEditorCompoundWidget.setText, 'textEditor.textChanged'),
    NmrChainPulldown.__name__               : (NmrChainPulldown.getText, NmrChainPulldown.select, 'pulldownList.activated'),
    RadioButtonsCompoundWidget.__name__     : (RadioButtonsCompoundWidget.getIndex, RadioButtonsCompoundWidget.setIndex,
                                               'radioButtons.buttonGroup.buttonClicked'),
    EntryPathCompoundWidget.__name__        : (EntryPathCompoundWidget.getText, EntryPathCompoundWidget.setText, 'entry.lineEdit.textChanged'),
    # ADD TABLES
    # ADD Others
    }

Item = namedtuple('Item', 'name widget getFunction setFunction presetFunction callback parameters')


#=========================================================================================
# General methods
#=========================================================================================

def getAttributeTipText(klass, attr):
    """Generate a tipText from the attribute of the given class.
     tipText is of the form:
      klass.attr

      Type: <type of the attribute>

      DocString: <string read from klass.attr.__doc__>

    :param klass: klass containing the attribute.
    :param attr: attribute name.
    :return: tipText string.
    """
    try:
        attrib = getattr(klass, attr)
        at = attr
        ty = type(attrib).__name__
        st = attrib.__str__()
        dc = attrib.__doc__

        if ty == 'property':
            return f'{klass.__name__}.{at}\n' \
                   f'Type:   {ty}\n' \
                   f'{dc}'
        else:
            return f'{klass.__name__}.{at}\n' \
                   f'Type:   {ty}\n' \
                   f'String form:    {st}\n' \
                   f'{dc}'
    except Exception:
        return None


#=========================================================================================
# AttributeEditorPopupABC
#=========================================================================================

class AttributeEditorPopupABC(CcpnDialogMainWidget):
    """
    Abstract base class to implement a popup for editing properties
    """

    klass = None  # The class whose properties are edited/displayed
    attributes = []  # A list of (attributeName, getFunction, setFunction, kwds) tuples;

    # get/set-Function have getattr, setattr profile
    # if setFunction is None: display attribute value without option to change value
    # kwds: optional kwds passed to LineEdit constructor

    EDITMODE = True
    WINDOWPREFIX = 'Edit '

    ENABLEREVERT = True

    hWidth = None
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    def __init__(self, parent=None, mainWindow=None, obj=None, editMode=None, **kwds):
        """
        Initialise the widget
        """
        if editMode is not None:
            self.EDITMODE = editMode
            self.WINDOWPREFIX = 'Edit ' if editMode else 'New '

        super().__init__(parent, setLayout=True,
                         windowTitle=self.WINDOWPREFIX + self.klass.className, **kwds)

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.application.project
        self.current = mainWindow.application.current

        if self.EDITMODE:
            self.obj = obj
        else:
            self.obj = self._newContainer()
            self._populateInitialValues()

        # create the list of widgets and set the callbacks for each
        self._setAttributeWidgets()

        # set up the required buttons for the dialog
        self.setOkButton(callback=self._okClicked, enabled=False)
        self.setCancelButton(callback=self._cancelClicked)
        self.setHelpButton(callback=self._helpClicked, enabled=False)
        if self.ENABLEREVERT:
            self.setRevertButton(callback=self._revertClicked, enabled=False)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

        # populate the widgets
        self._populate()
        # constraint and align widget sizes
        self._defineMinimumSizeWidgets()

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._okButton = self.dialogButtons.button(self.OKBUTTON)
        self._cancelButton = self.dialogButtons.button(self.CANCELBUTTON)
        self._helpButton = self.dialogButtons.button(self.HELPBUTTON)
        self._revertButton = self.dialogButtons.button(self.RESETBUTTON)

    def _setAttributeWidgets(self):
        """Create the attributes in the main widget area
        """
        self.edits = {}  # An (attributeName, widgetType) dict

        # if self.hWidth is None:
        #     # set the hWidth for the popup
        #     optionTexts = [attr for attr, _, _, _, _, _, _ in self.attributes]
        #     _, maxDim = getTextDimensionsFromFont(textList=optionTexts)
        #     self.hWidth = maxDim.width()

        for row, attribItem in enumerate(self.attributes):
            _label, attrType, getFunction, setFunction, presetFunction, callback, kwds = attribItem

            # remove whitespaces to give the attribute name in the class
            attr = stringToCamelCase(_label)
            tipText = getAttributeTipText(self.klass, attr)

            editable = setFunction is not None
            newWidget = attrType(self.mainWidget, mainWindow=self.mainWindow, labelText=_label, editable=editable,
                                 grid=(row, 0),
                                 tipText=tipText, compoundKwds=kwds)  #, **kwds)

            # connect the signal
            if attrType and attrType.__name__ in _commonWidgetsEdits:
                attrSignalTypes = _commonWidgetsEdits[attrType.__name__][ATTRSIGNAL]

                for attrST in makeIterableList(attrSignalTypes):
                    this = newWidget

                    # iterate through the attributeName to get the signals to connect to (for compound widgets)
                    if attrST:
                        for th in attrST.split('.'):
                            this = getattr(this, th, None)
                            if this is None:
                                break
                        else:
                            if this is not None:
                                # attach the connect signal and store in the widget
                                queueCallback = partial(self._queueSetValue, attr, attrType, getFunction, setFunction, presetFunction, callback, row)
                                this.connect(queueCallback)
                                newWidget._queueCallback = queueCallback

                if callback:
                    newWidget.setCallback(callback=partial(callback, self))

            self.edits[attr] = (newWidget, self.attributes, attribItem)

            setattr(self, attr, newWidget)

    def _defineMinimumSizeWidgets(self):
        groups = {}
        # iterate to find the minimum heights/widths for the compound widgets
        for attr, (compWidg, _aSet, _aItem) in self.edits.items():
            if layout := compWidg.layout():
                grp = _aSet and getattr(_aSet, '_group', 0)
                if grp is None:
                    # is _group is not defined will default to 0 and will align, specify None to skip alignment
                    continue

                rSize, cSize = groups.setdefault(grp, [np.zeros(layout.rowCount(), dtype=int),
                                                       np.zeros(layout.columnCount(), dtype=int)])

                for cc in range(layout.count()):
                    if (itm := layout.itemAt(cc)) and (widg := itm.widget()):

                        size = widg.sizeHint()
                        row, col, cols, rows = layout.getItemPosition(cc)

                        if row > rSize.shape[0] - 1:
                            # extend the array if it isn't long enough
                            np.resize(rSize, row + 1)
                            rSize[row] = 0
                        rSize[row] = max(rSize[row], size.height())
                        if col > cSize.shape[0] - 1:
                            np.resize(cSize, col + 1)
                            cSize[col] = 0
                        cSize[col] = max(cSize[col], size.width())

        # 2nd pass: iterate and set the minimum width constraints - check for heights
        for attr, (compWidg, _aSet, _aItem) in self.edits.items():
            if layout := compWidg.layout():
                grp = _aSet and getattr(_aSet, '_group', 0)
                if grp is None:
                    # is _group is not defined will default to 0 and will align, specify None to skip alignment
                    continue
                rSize, cSize = groups.setdefault(grp, [np.zeros(layout.rowCount(), dtype=int),
                                                       np.zeros(layout.columnCount(), dtype=int)])

                for col, width in enumerate(cSize):
                    if width:
                        layout.setColumnMinimumWidth(col, width)

    def _populate(self):
        """Populate the widgets in the popup
        """
        self._changes.clear()
        with self._changes.blockChanges():
            for _label, attrType, getFunction, _, _presetFunction, _, _ in self.attributes:
                # remove whitespaces to give the attribute name in the class
                attr = stringToCamelCase(_label)

                # populate the widget
                if attr in self.edits and attrType and attrType.__name__ in _commonWidgetsEdits:
                    thisEdit = _commonWidgetsEdits[attrType.__name__]
                    attrSetter = thisEdit[ATTRSETTER]

                    if _presetFunction:
                        # call the preset function for the widget (e.g. populate pulldowns with modified list)
                        _presetFunction(self, self.obj)

                    if getFunction:  # and self.EDITMODE:
                        # set the current value
                        value = getFunction(self.obj, attr, None)
                        compWidget, _attSet, _attItem = self.edits[attr]
                        attrSetter(compWidget, value)

    def _populateInitialValues(self):
        """Populate the initial values for an empty object
        """
        self.obj.name = self.klass._uniqueName(self.project)

    def _newContainer(self):
        """Make a new container to hold attributes for objects not created yet
        """
        return _attribContainer(self)

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        if not self._changes.enabled:
            return None

        applyState = True
        revertState = False
        allChanges = bool(self._changes)

        return changeState(self, allChanges, applyState, revertState, self._okButton, None, self._revertButton, 0)

    @queueStateChange(_verifyPopupApply)
    def _queueSetValue(self, attr, attrType, getFunction, setFunction, presetFunction, callback, dim, _value=None):
        """Queue the function for setting the attribute in the calling object (dim needs to stay for the decorator)
        """
        # _value needs to be None because this is also called by widget.callBack which does not add the extra parameter

        if attrType and attrType.__name__ in _commonWidgetsEdits:
            attrGetter = _commonWidgetsEdits[attrType.__name__][ATTRGETTER]
            compWidget, _attSet, _attItem = self.edits[attr]
            value = attrGetter(compWidget)

            if getFunction:  # and self.EDITMODE:
                oldValue = self._getValue(attr, getFunction, None)
                if (value or None) != (oldValue or None):
                    return partial(self._setValue, attr, setFunction, value)

    def _getValue(self, attr, getFunction, default):
        """Function for getting the attribute, called by _queueSetValue

        This can be subclassed to modify reading from the object
        as maybe required in a new object
        """
        return getFunction(self.obj, attr, default)

    def _setValue(self, attr, setFunction, value):
        """Function for setting the attribute, called by _applyAllChanges

        This can be subclassed to completely disable writing to the object
        as maybe required in a new object
        """
        setFunction(self.obj, attr, value)

    def _refreshGLItems(self):
        """emit a signal to rebuild any required GL items
        Not required here
        """
        pass


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Attribute classes
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

NEWHIDDENGROUP = '_NEWHIDDENGROUP'
CLOSEHIDDENGROUP = '_CLOSEHIDDENGROUP'
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from ccpn.util.DataEnum import DataEnum
# from collections import namedtuple
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.util.AttrDict import AttrDict


# AttributeItem = namedtuple('AttributeItem', ('attr', 'attrType', 'getFunction', 'setFunction', 'presetFunction', 'callback', 'kwds',))


class AttributeListType(DataEnum):
    VERTICAL = 0, 'vertical'
    HORIZONTAL = 1, 'horizontal'
    MORELESS = 2, 'moreLess'
    TABFRAME = 3, 'tabFrame'
    TAB = 4, 'tab'
    EMPTYFRAME = 5, 'frame'


class AttributeABC:
    ATTRIBUTELISTTYPE = AttributeListType.VERTICAL

    def __init__(self, *attributeList, queueStates=True, newContainer=True, hWidth=100, fieldWidth=None, group=None, **kwds):
        self._attributes = attributeList
        self._row = 0
        self._col = 0
        self._queueStates = queueStates
        self._newContainer = newContainer
        self._container = None
        self._kwds = kwds
        self._hWidth = hWidth
        self._fieldWidth = fieldWidth
        self._group = group

    def createContainer(self, parent, attribSet, grid=None, gridSpan=(1, 1), _indent=0):
        # create the new container here, including gridSpan?
        if attribSet:
            grid = attribSet.nextGridPosition()
            attribSet.nextPosition()
        else:
            grid = (0, 0)

        self._content = self._container = Frame(parent, setLayout=True, grid=grid, **self._kwds)
        self._container.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.nextPosition()
        return self._container

    def addAttribItem(self, parentRoot, attribItem, _indent=0):
        # add a new widget to the current container
        if not self._container:
            raise RuntimeError('Container not instantiated')

        # add widget here
        _label, attrType, getFunction, setFunction, presetFunction, callback, kwds = attribItem

        # remove whitespaces to give the attribute name in the class
        attr = stringToCamelCase(_label)
        tipText = getAttributeTipText(parentRoot.klass, attr)

        editable = setFunction is not None
        newWidget = attrType(self._container, mainWindow=parentRoot.mainWindow,
                             labelText=_label, editable=editable,
                             grid=(self._row, self._col),
                             # fixedWidths=(self._hWidth, self._fieldWidth, None, None, None),  # not very nice, but simple :|
                             tipText=tipText, compoundKwds=kwds)  #, **kwds)

        # connect the signal
        if attrType and attrType.__name__ in _commonWidgetsEdits:
            attrSignalTypes = _commonWidgetsEdits[attrType.__name__][ATTRSIGNAL]

            for attrST in makeIterableList(attrSignalTypes):
                this = newWidget

                # iterate through the attributeName to get the signals to connect to (for compound widgets)
                if attrST:
                    for th in attrST.split('.'):
                        this = getattr(this, th, None)
                        if this is None:
                            break
                    else:
                        if this is not None:
                            # attach the connect signal and store in the widget
                            queueCallback = partial(parentRoot._queueSetValue, attr, attrType, getFunction, setFunction, presetFunction, callback, self._row)
                            this.connect(queueCallback)
                            newWidget._queueCallback = queueCallback

            if callback:
                newWidget.setCallback(callback=partial(callback, self))

        parentRoot.edits[attr] = (newWidget, self, attribItem)
        if self._queueStates:
            parentRoot._VALIDATTRS.add(attr)

        # add the popup attribute corresponding to attr
        setattr(parentRoot, attr, newWidget)
        self.nextPosition()

    def nextPosition(self):
        """Move the pointer to the next position
        """
        self._row += 1

    def nextGridPosition(self):
        return (self._row, self._col)


class VList(AttributeABC):
    # contains everything from the baseClass
    pass


class HList(AttributeABC):
    ATTRIBUTELISTTYPE = AttributeListType.HORIZONTAL

    def nextPosition(self):
        """Move the pointer to the next position
        """
        self._col += 1


class MoreLess(AttributeABC):
    ATTRIBUTELISTTYPE = AttributeListType.MORELESS

    def createContainer(self, parent, attribSet, grid=None, gridSpan=(1, 1), _indent=0):
        # create the new container here, including gridSpan
        if attribSet:
            grid = attribSet.nextGridPosition()
            attribSet.nextPosition()
        else:
            grid = (0, 0)

        self._content = _frame = MoreLessFrame(parent, showMore=False, grid=grid, **self._kwds)
        self._container = _frame.contentsFrame
        self._container.getLayout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.nextPosition()
        return self._container


from ccpn.ui.gui.widgets.HLine import LabeledHLine
from ccpn.ui.gui.widgets.VLine import LabeledVLine


class Separator(AttributeABC):

    def __init__(self, name=None, *args, **kwds):
        super().__init__()
        self._name = name or ''

    def createContainer(self, parent, attribSet, grid=None, *args, **kwds):
        if attribSet:
            grid = attribSet.nextGridPosition()
            attribSet.nextPosition()
        else:
            grid = (0, 0)

        if attribSet.ATTRIBUTELISTTYPE == AttributeListType.HORIZONTAL:
            self._frame = LabeledVLine(parent, text=self._name,
                                       grid=grid, gridSpan=(1, 1), lineWidth=1, height=None, colour=getColours()[DIVIDER])
        else:
            self._frame = LabeledHLine(parent, text=self._name,
                                       grid=grid, gridSpan=(1, 1), lineWidth=1, height=None, colour=getColours()[DIVIDER])

        self._content = self._container = None
        self.nextPosition()

        return self._container

    def setVisible(self, value):
        self._frame.setVisible(value)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ComplexAttributeEditorPopupABC
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ComplexAttributeEditorPopupABC(AttributeEditorPopupABC):
    """
    Abstract base class to implement a popup for editing complex properties
    """
    attributes = VList([])  # A container holding a list of attributes/containers

    # each attribute is of type (attributeName, getFunction, setFunction, kwds) tuples;
    # or a container type VList/HList/MoreLess

    def _setAttributeSet(self, attribSetParent, attribSet, _indent=0):

        # start by making new container
        attribSet.createContainer(attribSetParent._container if attribSetParent else self.mainWidget,
                                  attribSetParent,
                                  _indent=_indent)

        for attribItem in attribSet._attributes:
            if isinstance(attribItem, AttributeABC):
                # recurse into the list
                self._setAttributeSet(attribSet,
                                      attribItem,
                                      _indent=_indent + 4)

            elif isinstance(attribItem, Item):
                # add widget
                attribSet.addAttribItem(self, attribItem)

            else:
                raise RuntimeError('Container not type defined')

    def _setAttributeWidgets(self):
        """Create the attributes in the main widget area
        """
        # raise an error if the top object is not a container
        if not isinstance(self.attributes, AttributeABC):
            raise RuntimeError('Container not type defined')

        self.edits = {}  # An (attributeName, widgetType) dict
        self._VALIDATTRS = OrderedSet()

        # create the list of widgets and set the callbacks for each
        self._setAttributeSet(None, self.attributes)

    @staticmethod
    def _linkAttributeGroups(attribGroups):
        if attribGroups and len(attribGroups):
            for groupNum, groups in attribGroups.items():
                widths = [klass._hWidth for klass in groups]
                if widths and len(widths) > 1:
                    maxHWidth = np.max(widths)
                    for klass in groups:
                        klass._hWidth = maxHWidth

    # def _defineMinimumWidthSet(self, attribSet, attribGroups):
    #
    #     if attribSet._group is not None:
    #         if attribSet._group not in attribGroups:
    #             attribGroups[attribSet._group] = (attribSet,)
    #         else:
    #             attribGroups[attribSet._group] += (attribSet,)
    #
    #     if not attribSet._hWidth:
    #         # calculate a new _hWidth if undefined
    #         optionTexts = [attribItem[0] for attribItem in attribSet._attributes if isinstance(attribItem, tuple)]
    #         _, maxDim = getTextDimensionsFromFont(textList=optionTexts)
    #         attribSet._hWidth = maxDim.width()
    #
    #     for attribItem in attribSet._attributes:
    #         if isinstance(attribItem, AttributeABC):
    #             # recurse into the list
    #             self._defineMinimumWidthSet(attribItem, attribGroups)

    def _populateIterator(self, attribList):
        for attribItem in attribList._attributes:

            if isinstance(attribItem, AttributeABC):
                # must be another subgroup of attributes - AttributeABC
                self._populateIterator(attribItem)

            elif isinstance(attribItem, Item):
                # these are now in the containerList
                attr, attrType, getFunction, _, _presetFunction, _, _ = attribItem

                # remove whitespaces to give the attribute name in the class, make first letter lowercase
                attr = stringToCamelCase(attr)

                # populate the widget
                if attr in self.edits and attrType and attrType.__name__ in _commonWidgetsEdits:
                    thisEdit = _commonWidgetsEdits[attrType.__name__]
                    attrSetter = thisEdit[ATTRSETTER]

                    if _presetFunction:
                        # call the preset function for the widget (e.g. populate pulldowns with modified list)
                        _presetFunction(self, self.obj)

                    if getFunction:  # and self.EDITMODE:
                        # set the current value
                        value = getFunction(self.obj, attr, None)
                        compWidget, _attSet, _attItem = self.edits[attr]
                        attrSetter(compWidget, value)
                        # attrSetter(self.edits[attr], value)

            else:
                raise RuntimeError('Container type not defined')

    def _populate(self):

        self._changes.clear()
        with self._changes.blockChanges():
            # start with the top object - must be a container class
            self._populateIterator(self.attributes)

    def _setValue(self, attr, setFunction, value):
        """Function for setting the attribute, called by _applyAllChanges

        This can be subclassed to completely disable writing to the object
        as maybe required in a new object
        """
        if attr in self._VALIDATTRS:
            setFunction(self.obj, attr, value)

    def _newContainer(self):
        """Make a new container to hold attributes for objects not created yet
        """
        return _complexAttribContainer(self)


class _complexAttribContainer(AttrDict):
    """
    Class to simulate a blank object in new/edit popup.
    """

    def _setAttributes(self, attribList):
        for attribItem in attribList._attributes:

            if isinstance(attribItem, AttributeABC):
                # must be another subgroup of attributes - AttributeABC
                self._setAttributes(attribItem)

            elif isinstance(attribItem, Item):
                _label = stringToCamelCase(attribItem[0])
                self[_label] = None

            else:
                raise RuntimeError('Container type not defined')

    def __init__(self, popupClass):
        """Create a list of attributes from the container class
        """
        super().__init__()
        # self._popupClass = popupClass

        self._setAttributes(popupClass.attributes)


class _attribContainer(AttrDict):
    """
    Class to simulate a simple blank object in new/edit popup.
    """

    def __init__(self, popupClass):
        """Create a list of attributes from the container class
        """
        super().__init__()
        for attribItem in popupClass.attributes:
            _label = stringToCamelCase(attribItem[0])
            self[_label] = None
