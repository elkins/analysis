"""Module Documentation here

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-12-03 14:30:55 +0000 (Tue, December 03, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.dockarea.DockDrop import DockDrop
from pyqtgraph.dockarea.Dock import DockLabel, Dock, VerticalLabel
from pyqtgraph.dockarea.Container import SplitContainer

from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.lib.GuiGenerator import generateWidget
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.ColourDialog import ColourDialog
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox, ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.RadioButton import RadioButton
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Slider import Slider
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.FileDialog import LineEditButtonDialog
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.popups.PickPeaks1DPopup import ExcludeRegions
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from collections import OrderedDict
from ccpn.framework.lib.pipeline.PipelineBase import Pipeline
from ccpn.ui.gui.widgets.GLLinearRegionsPlot import GLTargetButtonSpinBoxes
from ccpn.util.Logging import getLogger
from ccpn.framework.lib.pipeline.PipeBase import PIPE_CATEGORIES, PIPE_CATEGORY
from functools import partial
from ccpn.ui.gui.widgets.Font import getFont
from ccpn.ui.gui.guiSettings import getColours, LABEL_FOREGROUND
from ccpn.util.Colour import hexToRgb


commonWidgets = {
    CheckBox.__name__               : ('get', 'setChecked'),
    ColourDialog.__name__           : ('getColor', 'setColor'),
    DoubleSpinbox.__name__          : ('value', 'setValue'),
    ScientificDoubleSpinBox.__name__: ('value', 'setValue'),
    Label.__name__                  : ('get', 'setText'),
    LineEdit.__name__               : ('get', 'setText'),
    LineEditButtonDialog.__name__   : ('get', 'setText'),
    PulldownList.__name__           : ('currentText', 'set'),
    RadioButton.__name__            : ('get', 'set'),
    RadioButtons.__name__           : ('get', 'set'),
    Slider.__name__                 : ('get', 'setValue'),
    Spinbox.__name__                : ('value', 'set'),
    TextEditor.__name__             : ('get', 'setText'),
    GLTargetButtonSpinBoxes.__name__: ('get', 'setValues'),
    ExcludeRegions.__name__         : ('_getExcludedRegions', '_set'),

    # ObjectTable.__name__:    ('getSelectedRows',         '_highLightObjs'), works only with objs
    }


def _getWidgetByAtt(cls, name):
    """

    :param cls: the class where the widget lives
    :param name: widget variable name
    :return: widget obj
    """
    w = getattr(cls, name, None)
    if w is not None:
        return w


PipelineBoxDragStyle = """Dock > QWidget {border: 1px solid #78FF00; border-radius: 1px;}"""

_defaultGreen = '#60B41D'
_runningOrange = '#f5b41d'
_standbyBlue = '#a0b5fa'
_failedRed = '#f51d41'
_completedGreen = '#08fc59'


def _getPipeBoxStyleSheet(backgroundColour=_defaultGreen):
    return f"""PipelineBoxLabel{{
                                                  background-color : {backgroundColour};
                                                  color : #000000;
                                                  border-top-right-radius: 1r;
                                                  border-top-left-radius: 1r;
                                                  border-bottom-right-radius: 0px;
                                                  border-bottom-left-radius: 0px;
                                                  border-width: 0px;
                                                  border-bottom: 0px;
                                                  padding-left: 1px;
                                                  padding-right: 1px;
                                                  }}"""


PipelineBoxLabelStyle = _getPipeBoxStyleSheet(_defaultGreen)


class _VContainer(SplitContainer):
    def __init__(self, area):
        SplitContainer.__init__(self, area, QtCore.Qt.Vertical)

    def type(self):
        return 'vertical'

    def updateStretch(self):
        x = 0
        y = 0
        sizes = []
        for i in range(self.count()):
            wx, wy = self.widget(i).stretch()
            y += wy
            x = max(x, wx)
            sizes.append(wy)
        self.setStretch(x, y)

        tot = float(sum(sizes))
        if tot == 0:
            scale = 1.0
        else:
            scale = self.height() / tot

        self.setSizes([int(s * scale) for s in sizes])
        self.setChildrenCollapsible(False)
        self.setChildrenCollapsible(False)


class _PipelineDropAreaOverlay(Widget):
    """Overlay widget that draws drop areas during a drag-drop operation"""

    def __init__(self, parent):
        super().__init__(parent)
        self.dropArea = None
        self.hide()
        # self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def setDropArea(self, area):
        self.dropArea = area
        if area is None:
            self.hide()
        else:
            prgn = self.getParent().rect()
            rgn = QtCore.QRect(prgn)
            w = min(10, prgn.width() / 3.)
            h = int(min(30, prgn.height() / 3.))

            if self.dropArea == 'top':
                rgn.setHeight(h)
            elif self.dropArea == 'bottom':
                rgn.setTop(rgn.top() + prgn.height() - h)
            else:
                rgn.setHeight(0)

            self.setGeometry(rgn)
            self.show()

        self.update()
        self.update()

    def paintEvent(self, ev):
        if self.dropArea is None:
            return
        p = QtGui.QPainter(self)
        rgn = self.rect()

        #TODO:LUCA insert stylesheet
        p.setBrush(QtGui.QBrush(QtGui.QColor(120, 255, 0, 50)))
        p.setPen(QtGui.QPen(QtGui.QColor(123, 245, 150), 3))
        p.drawRect(rgn)


class PipelineDropArea(DockArea):
    def __init__(self, parent, guiPipeline, mainWindow=None, **kwds):
        super().__init__()
        self.setStyleSheet("""QSplitter{background-color: transparent;}
                          QSplitter::handle:vertical {background-color: transparent;height: 1px;}""")

        self.parent = parent
        self.guiPipeline = guiPipeline
        self.mainWindow = mainWindow

        self.inputData = None
        self.overlay = _PipelineDropAreaOverlay(self)
        self.textLabel = 'Drop Pipes'

        colours = getColours()

        self.fontLabel = getFont(size='LARGE')
        self.colourLabel = hexToRgb(colours[LABEL_FOREGROUND])
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.layout.setAlignment(QtCore.Qt.AlignTop)

    @property
    def currentGuiPipes(self) -> list:
        'return all current Pipes in area'
        if self is not None:
            Pipes = list(self.findAll()[1].values())
            return Pipes

    @property
    def currentPipesClassNames(self) -> list:
        'return the name of all current modules in area'
        if self is not None:
            classNames = [guiPipe.__class__.__name__ for guiPipe in self.currentGuiPipes]
            return classNames

    @property
    def currentPipesNames(self) -> list:
        'return the name of all current modules in area'
        if self is not None:
            pipesNames = list(self.findAll()[1].keys())
            return pipesNames

    @property
    def currentPipesNamesAndClasses(self):
        d = []
        for pipeName, guiPipe in self.findAll()[1].items():
            d.append((pipeName, guiPipe.__class__.__name__))
        return d

    @property
    def guiPipesState(self):
        d = []
        for pipeName, guiPipe in self.findAll()[1].items():
            d.append((guiPipe.__class__.__name__, pipeName, guiPipe.widgetsState, guiPipe.isActive))
        return d

    def dragEnterEvent(self, ev):
        src = ev.source()

        if isinstance(src, PipesTree) or isinstance(src, ListWidget):
            ev.accept()
        else:
            ev.ignore()

    def _paint(self, ev, paintLabel=True):
        QPainter = QtGui.QPainter
        painter = QPainter(self)
        # set font
        painter.setFont(self.fontLabel)
        painter.setPen(QtGui.QColor(*self.colourLabel))
        rgn = self.contentsRect()
        rgn = QtCore.QRect(rgn.left(), rgn.top(), rgn.width(), rgn.height())
        align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter
        if paintLabel:
            self.hint = painter.drawText(rgn, align, self.textLabel)
        painter.setRenderHint(QPainter.Antialiasing)
        rectPath = QtGui.QPainterPath()
        height = self.height() - 2
        rectPath.addRoundedRect(QtCore.QRectF(1, 1, self.width() - 2, height), 1, 1)
        painter.drawPath(rectPath)
        painter.end()

    def paintEvent(self, ev):
        """
        Draws central label
        """
        if not self.currentPipesNames:
            self._paint(ev)
        else:
            self._paint(ev, paintLabel=False)

    def dropEvent(self, ev):

        src = ev.source()
        if isinstance(src, PipesTree) or isinstance(src, ListWidget):
            selectedList = src.selectedItems()
            names = [i.text() for i in selectedList]
            for sel in names:
                guiPipeName = self.guiPipeline._getSerialName(str(sel))
                self.guiPipeline._addGuiPipe(guiPipeName, sel, position=self.dropArea)
            ev.accept()
        self.dropArea = None
        self.overlay.setDropArea(self.dropArea)

    def dragMoveEvent(self, ev):
        # print "drag move"

        ld = ev.pos().x()
        rd = self.width() - ld
        td = ev.pos().y()
        bd = self.height() - td

        mn = min(ld, rd, td, bd)
        if (ld == mn or td == mn) and mn > self.height() / 3.:
            self.dropArea = "top"
            # self.dropArea = "center"
        elif (rd == mn or ld == mn) and mn > self.width() / 3.:
            self.dropArea = "bottom"
        elif rd == mn and td > bd:
            self.dropArea = "bottom"
        elif rd == mn and td < bd:
            self.dropArea = "top"
        elif ld == mn and td > bd:
            self.dropArea = "bottom"
        elif ld == mn and td < bd:
            self.dropArea = "top"
        elif ld == mn:
            self.dropArea = "left"
        elif td == mn:
            self.dropArea = "top"
        elif bd == mn:
            self.dropArea = "bottom"

        if ev.source() is self and self.dropArea == 'center':
            self.dropArea = None
            ev.ignore()
        elif self.dropArea not in self.allowedAreas:
            self.dropArea = None
            ev.ignore()
        else:
            # print "  ok"
            ev.accept()
        self.overlay.setDropArea(self.dropArea)

    def addBox(self, box=None, position='bottom', relativeTo=None, **kwds):
        """With these settings the user can close all the boxes from the label 'close box' or pop up and
         when re-add a new box it makes sure there is a container available.
        """
        if box is None:
            box = GuiPipe(name='New GuiPipe', **kwds)

        if position is None:
            position = 'bottom'
        neededContainer = {'bottom': 'vertical', 'top': 'vertical', }[position]

        if relativeTo is None:
            neighbor = None
            container = self.addContainer(neededContainer, self.topContainer)

        if relativeTo is None or relativeTo is self:
            if self.topContainer is None:
                container = self
                neighbor = None
            else:
                container = self.topContainer
                neighbor = None
        else:
            if isinstance(relativeTo, str):
                relativeTo = self.boxes[relativeTo]
            container = self.getContainer(relativeTo)
            neighbor = relativeTo

        if neededContainer != container.type() and container.type() == 'tab':
            neighbor = container
            container = container.container()

        if neededContainer != container.type():
            if neighbor is None:
                container = self.addContainer(neededContainer, self.topContainer)
            else:
                container = self.addContainer(neededContainer, neighbor)

        insertPos = {'bottom': 'after', 'top': 'before', }[position]

        if container is not None:
            container.insert(box, insertPos, neighbor)
        else:
            container = self.topContainer
            container.insert(box, insertPos, neighbor)
        box.area = self
        self.docks[box.name()] = box
        return box

    def makeContainer(self, typ):
        new = _VContainer(self)
        new.setChildrenCollapsible(False)
        return new

    def apoptose(self):
        pass

    def orderedBoxes(self, obj):
        if isinstance(obj, Dock):
            return (obj)
        else:
            boxes = []
            if hasattr(obj, 'count'):
                for i in range(obj.count()):
                    boxes.append(self.orderedBoxes(obj.widget(i)))
            return boxes

    def _restoreState(self, state):
        try:
            self.restoreState(state)
        except Exception as err:
            getLogger().warning('Error restoring pipeline. %s' % err)

    def closeAll(self):
        for guiPipe in self.currentGuiPipes:
            guiPipe.close()


class GuiPipeDrop(DockDrop):
    """Provides dock-dropping methods"""

    def __init__(self, allowedAreas=None):
        DockDrop.__init__(self)


class GuiPipe(Dock, GuiPipeDrop):
    preferredPipe = True
    pipeName = ''
    pipe = None
    info = "Pipe details not available yet."  #This will appear as toolTip when hovering the GuiPipe Label.
    _alreadyOpened = False  #Use this to open the guiPipe only once. Inside the GuiPipe do: MyGuiPipe._alreadyOpened = True

    def __init__(self, parent, name, project=None, widgetsParams=None, **kwds):
        """

        :param parent: guiPipeline
        :param name: string for the new GuiPipe
        :param params: dict of all widgets variable names and their values
        :param project: ccpn Project
        :param kwds: any other
        """
        super().__init__(name, self)
        self._pulldownSGHeaderText = '-- Select SG --'
        self._warningIcon = Icon('icons/warning')
        self.ccpnModule = False
        self.pipelineBox = True
        self.autoOrient = False
        self.isAutoGenerated = False
        self._parent = parent
        self._allChildren = set()

        self.inputData = []
        if isinstance(self._parent, Pipeline):
            self.inputData = self._parent.inputData
            self.spectrumGroups = self._parent.spectrumGroups

        if name is None:
            name = 'New Pipe'
        self.pipeName = name

        self._updateLabel(name)

        self.dragStyle = PipelineBoxDragStyle
        self.overlay = _PipelineDropAreaOverlay(self)

        self.project = None
        if project is not None:
            self.project = project

        if self._parent is not None:
            try:
                self.application = self._parent.application
                self.current = self.application.current
            except:
                pass

        self._widgetsState = None
        if widgetsParams is not None:
            self.restoreWidgetsState(**widgetsParams)

        ######  pipeLayout
        self.pipeFrame = Frame(self, setLayout=False)
        self.pipeLayout = QtWidgets.QGridLayout()
        self.pipeFrame.setLayout(self.pipeLayout)
        self.layout.addWidget(self.pipeFrame)

        # self.layout.setAlignment(self.pipeFrame, QtCore.Qt.AlignTop)
        # self.layout.setContentsMargins(5,5,5,5)

        self._kwargs = None
        if self.pipe is not None:
            self.pipe._kwargs = self._kwargs

    def name(self):
        return self.pipeName

    @property
    def widgetsState(self):
        return self._widgetsState

    @widgetsState.getter
    def widgetsState(self):
        """return  {"variableName":"value"}  of all gui Variables  """
        widgetsState = {}
        for varName, varObj in vars(self).items():
            if varObj.__class__.__name__ in commonWidgets.keys():
                try:  # try because widgets can be dinamically deleted
                    widgetsState[varName] = getattr(varObj, commonWidgets[varObj.__class__.__name__][0])()
                except Exception as e:
                    getLogger().debug('Error %s' % str(e))
        self._kwargs = widgetsState
        return widgetsState

    def restoreWidgetsState(self, **widgetsState):
        'Restore the gui params. To Call it: _setParams(**{"variableName":"value"})  '
        for variableName, value in widgetsState.items():
            try:
                widget = getattr(self, str(variableName))
                if widget.__class__.__name__ in commonWidgets.keys():
                    setWidget = getattr(widget, commonWidgets[widget.__class__.__name__][1])
                    setWidget(value)
            except Exception as e:
                getLogger().debug('Impossible to restore %s value for %s. (%s)' % (variableName, self.pipeName, str(e)))

    def _findChildren(self, widget):
        for i in widget.children():
            self._allChildren.update({i})
            self._findChildren(i)

    def _formatLabelWidgets(self):
        """
        Replace the underscore with empty spaces in all labels
        """
        self._findChildren(self)
        for num, w in enumerate(self._allChildren):
            if w.__class__.__name__ == Label.__name__:
                text = w.get()
                if '_' in text:
                    newText = text.replace('_', ' ')
                    w.setText(newText)

    def _updateWidgets(self):
        """
        Override this method to update the widgets that are fed by input data
        """
        pass

    def implements(self, name=None):
        if name is None:
            return ['GuiPipe']
        else:
            return name == 'GuiPipe'

    def _updateLabel(self, name):
        self.label.deleteLater()  # delete original Label
        self.label = PipelineBoxLabel(name.upper(), self)
        self.label.closeButton.clicked.connect(self._closePipe)
        self.label.dock = self
        # self.label.arrowDownButton.clicked.connect(self.moveBoxDown)§
        # self.label.arrowUpButton.clicked.connect(self.moveBoxUp)
        self.moveLabel = True
        self.orientation = 'horizontal'

    def closePipe(self):
        self.setParent(None)
        self.label.setParent(None)

    def _closePipe(self):
        self.closePipe()

    def _setSpectrumGroupPullDowns(self, widgetVariables, headerText='N/A', headerEnabled=False, headerIcon=None):
        """ Used to set the spectrum groups pid in the pulldowns. Called from various guiPipes"""
        spectrumGroups = list(self.spectrumGroups)
        if len(spectrumGroups) > 0:
            for widgetVariable in widgetVariables:
                selected = _getWidgetByAtt(self, widgetVariable).get()
                # getLogger().debug(selected)

                _getWidgetByAtt(self, widgetVariable).setData(texts=[sg.pid for sg in spectrumGroups],
                                                              objects=spectrumGroups,
                                                              headerText=headerText, headerEnabled=headerEnabled,
                                                              headerIcon=headerIcon)
                # Below a mechanism to autoselect spectrumGroups Pulldown based on the pid. Eg autoselect the Control SG pulldown if in the inputData there is a SG with the name Control in its pid.
                if selected == self._pulldownSGHeaderText:
                    pids = [sg.pid for sg in spectrumGroups]
                    for pid in pids:
                        if len(widgetVariable.split('_')) > 0:
                            for subText in widgetVariable.split('_'):
                                firstLabelLetter = subText[0]
                                _id = pid.id
                                firstPidLetter = _id[0]
                                if firstLabelLetter.lower() == firstPidLetter.lower():
                                    selected = pid
                                    continue
                _getWidgetByAtt(self, widgetVariable).select(selected)

        else:
            for widgetVariable in widgetVariables:
                _getWidgetByAtt(self, widgetVariable)._clear()

    def _setMaxValueRefPeakList(self, widgetVariable):
        """ Used to set the reference PeakList limits. Called from various guiPipes"""
        data = list(self.inputData)
        if len(data) > 0:
            for spectrum in data:
                if spectrum is not None:
                    if spectrum.peakLists:
                        pls = spectrum.peakLists
                        _getWidgetByAtt(self, widgetVariable).setMaximum(len(pls) - 1)
        else:
            _getWidgetByAtt(self, widgetVariable).setMaximum(0)

    def rename(self, newName):
        self.label.name = newName

    def _moveBoxDown(self):
        name = self.name()
        boxes = self.pipelineArea.childState(self.pipelineArea.topContainer)[1]
        boxesNames = []
        for i, box in enumerate(boxes):
            boxesNames.append(box[1])
        i = boxesNames.index(name)
        count = len(boxes)
        j = i
        while j < count - 1:
            next = self.pipelineArea.docks[str(boxesNames[i + 1])]
            self.pipelineArea.moveDock(self, 'bottom', next)
            j += 1

    def _moveBoxUp(self):
        name = self.name()
        boxes = self.pipelineArea.childState(self.pipelineArea.topContainer)[1]
        boxesNames = []
        for i, box in enumerate(boxes):
            boxesNames.append(box[1])
        i = boxesNames.index(name)
        j = i
        while j > 0:
            next = self.pipelineArea.docks[str(boxesNames[i - 1])]
            self.pipelineArea.moveDock(self, 'top', next)
            j = j - 1

    def startDrag(self):
        # if len(self.pipelineArea.findAll()[1].keys()) > 1:
        self.drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        self.drag.setMimeData(mime)
        dragPixmap = self.grab()
        # self.drag.setPixmap(
        #     dragPixmap.scaledToWidth(128) if dragPixmap.width() < dragPixmap.height() else dragPixmap.scaledToHeight(
        #         128))
        # make sure that the dragPixmap is not too big
        self.drag.setPixmap(dragPixmap.scaledToWidth(max(32, min(128, dragPixmap.width())))
                            if dragPixmap.width() < dragPixmap.height() else
                            dragPixmap.scaledToHeight(max(32, min(128, dragPixmap.height()))))

        self.widgetArea.setStyleSheet(self.dragStyle)
        self.update()
        action = self.drag.exec_()
        self.updateStyle()

    def dragEnterEvent(self, ev):
        src = ev.source()
        if hasattr(src, 'implements') and src.implements('GuiPipe'):
            ev.accept()
        elif isinstance(src, PipesTree) or isinstance(src, ListWidget):
            ev.accept()
        else:
            ev.ignore()

    # def dragMoveEvent(self, *args):
    #     DockDrop.dragMoveEvent(self, *args)

    def dragMoveEvent(self, ev):
        # print "drag move"

        ld = ev.pos().x()
        rd = self.width() - ld
        td = ev.pos().y()
        bd = self.height() - td

        mn = min(ld, rd, td, bd)
        if (ld == mn or td == mn) and mn > self.height() / 3.:
            self.dropArea = "top"
            # self.dropArea = "center"
        elif (rd == mn or ld == mn) and mn > self.width() / 3.:
            self.dropArea = "bottom"
        elif rd == mn and td > bd:
            self.dropArea = "bottom"
        elif rd == mn and td < bd:
            self.dropArea = "top"
        elif ld == mn and td > bd:
            self.dropArea = "bottom"
        elif ld == mn and td < bd:
            self.dropArea = "top"
        elif ld == mn:
            self.dropArea = "left"
        elif td == mn:
            self.dropArea = "top"
        elif bd == mn:
            self.dropArea = "bottom"

        # DockDrop.dragMoveEvent(self, *args)

        if ev.source() is self and self.dropArea == 'center':
            self.dropArea = None
            ev.ignore()
        elif self.dropArea not in self.allowedAreas:
            self.dropArea = None
            ev.ignore()
        else:
            # print "  ok"
            ev.accept()
        self.overlay.setDropArea(self.dropArea)

    def dragLeaveEvent(self, *args):
        DockDrop.dragLeaveEvent(self, *args)

    def dropEvent(self, *args):
        if len(args) > 0:
            ev = args[0]
            src = ev.source()

            src = ev.source()
            if isinstance(src, PipesTree) or isinstance(src, ListWidget):
                selectedList = src.selectedItems()
                names = [i.text() for i in selectedList]
                for name in names:
                    position = self.dropArea
                    guiPipeName = self._parent._getSerialName(str(name))
                    self._parent._addGuiPipe(guiPipeName, name, position=position, relativeTo=self)
                self.dropArea = None
                self.overlay.setDropArea(self.dropArea)
                ev.accept()
            else:
                DockDrop.dropEvent(self, *args)

    def setActive(self, state):
        self.label.checkBox.setChecked(state)

    @property
    def isActive(self):
        checkBox = self.label.checkBox
        if checkBox.isChecked():
            return True
        else:
            return False


class AutoGeneratedGuiPipe(GuiPipe):
    """
    GuiPipe step base class.


    For Autogeneration of Gui:
    In order to genenerate a (crude) gui, you'll need to populate the params class variable.
      First, make it an iterable:
        params = []
      Now, add variables in the order you want the input boxes to show up.
      Every variable is declared in a mapping (generally a dictionary) with two required keys:
        'variable' : The keyward parameter that will be used when the function is called.
        'value' : the possible values.  See below.
      In addition to the required keys, several optional keys can be used:
        label : the label used.  If this is left out, the variable name will be used instead.
        default : the default value
        stepsize : the stepsize for spinboxes.  If you include this for non-spinboxes it will be ignored

      The 'value' entry:
        The type of widget generated is controled by the value of this entry,
        if the value is an iterable, the type of widget is controlled by the first item in the iterable
        strings are not considered iterables here.
          value type                       : type of widget
          string                           : LineEdit
          boolean                          : Checkbox
          Iterable(strings)                : PulldownList
          Iterable(int, int)               : Spinbox
          Iterable(float, float)           : DoubleSpinbox
          Iterable(Iterables(str, object)) : PulldownList where the object is passed instead of the string

    """

    pipeName = ''
    autoGuiParams = {}

    def __init__(self, parent, name, **kwds):
        """

        :param parent: guiPipeline
        :param name: string for the new GuiPipe
        :param params: dict of all widgets variable names and their values
        :param project: ccpn Project
        :param kwds: any other
        """
        GuiPipe.__init__(self, parent=parent, name=name)
        self._kwargs = {}
        self.pipeName = name
        self.isAutoGenerated = True

        if self.autoGuiParams is not None:
            self.guiPipe = generateWidget(self.autoGuiParams, widget=self,
                                          argsDict=self._kwargs, columns=4)

        else:
            self.guiPipe = self


class PipelineBoxLabel(DockLabel, VerticalLabel):
    def __init__(self, name, *args):
        super(PipelineBoxLabel, self).__init__(name, *args)
        QtWidgets.QLabel.__init__(self)
        self.updateStyle()
        self.setExtraButtons()
        self.name = name

        # This is a terrible way to get the parent. Need to check the hierarchy classes from QtGraph and fix this
        if len(args) > 0:
            if isinstance(args[0], GuiPipe):
                self._parent = args[0]
                if self._parent:
                    self.setToolTip(self._parent.info)

    def updateStyle(self):
        self.hStyle = PipelineBoxLabelStyle
        self.setStyleSheet(self.hStyle)
        pass

    def setExtraButtons(self):
        self.checkBox = CheckBox(self, text='Active', callback=None)
        self.checkBox.setMaximumHeight(15)
        self.closeButton = Button(self, icon='icons/close_cross')
        self.closeButton.setStyleSheet("""QPushButton {background-color: transparent;
                                                  color:black;
                                                  border: 0px solid transparent}""")
        self.closeButton.setIconSize(QtCore.QSize(15, 15))

    def mousePressEvent(self, ev):

        if ev.button() == QtCore.Qt.LeftButton:
            self.pressPos = ev.pos()
            self.startedDrag = False
            ev.accept()

        if ev.button() == QtCore.Qt.RightButton:
            menu = self._createContextMenu()
            if menu:
                menu.move(ev.globalPos().x(), ev.globalPos().y() + 10)
                menu.exec()

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            pass

    def resizeEvent(self, ev):
        size = ev.size().height()

        pos = QtCore.QPoint(ev.size().width() - 20, 0)
        self.closeButton.move(pos)
        pos = QtCore.QPoint(ev.size().width() - 80, 0)
        self.checkBox.move(pos)
        super(DockLabel, self).resizeEvent(ev)

    def mouseMoveEvent(self, ev):
        if not self.startedDrag and (ev.pos()).manhattanLength() > QtWidgets.QApplication.startDragDistance():
            if self.dock is not None:
                self.dock.startDrag()
        ev.accept()

    # def mouseMoveEvent(self, ev):
    #     """Handle the mouse move event to spawn a drag event - copied from super-class
    #     """
    #
    #         if not self.mouseMoved:
    #             lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
    #             self.mouseMoved = (lpos - self.pressPos).manhattanLength() > QtWidgets.QApplication.startDragDistance()
    #
    #         if self.mouseMoved and ev.buttons() == QtCore.Qt.MouseButton.LeftButton:
    #             # emit a drag started event
    #             self.sigDragEntered.emit(self.parent(), ev)
    #             self.dock.startDrag()
    #
    #         ev.accept()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        rgn = self.contentsRect()
        align = self.alignment()
        self.hint = p.drawText(rgn, align, self.name)
        p.end()

        self.setMaximumHeight(self.hint.height())
        # self.setMinimumHeight(15)
        # self.setMaximumWidth(16777215)

    def _createContextMenu(self):
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addAction('Close', self._parent.closePipe)
        contextMenu.addAction('Close All', self._parent._parent._closeAllGuiPipes)
        return contextMenu


class pipeTreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent, name, isPipeCategory=False, draggable=False, expanded=True, **kwds):
        super().__init__(parent)
        self.pipeName = name
        self.isPipeCategory = isPipeCategory
        self.setText(0, name)
        if draggable:
            self.setFlags(self.flags() | QtCore.Qt.ItemIsDragEnabled)
        else:
            self.setFlags(self.flags() ^ QtCore.Qt.ItemIsDragEnabled)
        self.setExpanded(expanded)

    def text(self):
        return self.pipeName


class PipesTree(QtWidgets.QTreeWidget, Base):
    def __init__(self, parent, guiPipeline, **kwds):
        super().__init__(parent)
        Base._init(self, acceptDrops=False, **kwds)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.itemDoubleClicked.connect(self._itemDoubleClickCallback)
        self.parent = parent
        self.guiPipeline = guiPipeline
        self.setHeaderLabel('Double click or drag&drop ->')
        self._selectableItems = []
        self._availablePipeNames = []

    def _addPipesToTree(self):
        """
        Add the pipes to the tree based on the category.
        """
        self.clear()
        from collections import defaultdict

        allPipes = [(p.pipeCategory, p.pipeName) for p in self.guiPipeline.pipes if hasattr(p, PIPE_CATEGORY)]
        d = defaultdict(list)
        for k, v in allPipes:
            d[k].append(v)
        dd = OrderedDict([(el, d[el]) for el in PIPE_CATEGORIES])
        self.buildTree(dd)

    def buildTree(self, dd):
        for categoryName, pipeNames in dd.items():
            if isinstance(pipeNames, list):
                if len(pipeNames) > 0:  # add a branch only if there are available pipes for that category
                    categoryItem = pipeTreeItem(self, categoryName, isPipeCategory=True)
                    for pipeName in sorted(pipeNames):
                        pipeItem = pipeTreeItem(categoryItem, pipeName, draggable=True)
                        # pipeItem.setIcon(0, Icon('icons/mario-pipe'))
                        self._selectableItems.append(pipeItem)
                        self._availablePipeNames.append(pipeName)

    def mouseReleaseEvent(self, event):
        """Re-implementation of the mouse press event so right click can be used to delete items from the
        sidebar.
        """
        if event.button() == QtCore.Qt.RightButton:
            for item in self.selectedItems():
                if item is not None:
                    if not item.isPipeCategory:
                        self._raiseContextMenu(event, item)
                        event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _itemDoubleClickCallback(self, item):
        if not item.isPipeCategory:
            self.guiPipeline.addPipe(item.pipeName)

    def _infoCallback(self, pipeName):
        from ccpn.ui.gui.widgets.MessageDialog import showInfo

        pipe = self.guiPipeline.getPipeFromName(pipeName)
        showInfo(pipeName, 'Not implemented yet')

    def _raiseContextMenu(self, event, item):
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem("Add to pipeline ", callback=self._addToPipelineCallback)
        contextMenu.addItem("Clear pipeline", callback=self.guiPipeline._closeAllGuiPipes)
        contextMenu.addSeparator()
        contextMenu.addItem("Info", callback=partial(self._infoCallback, item.pipeName))
        contextMenu.move(event.globalPos().x(), event.globalPos().y() + 10)
        contextMenu.exec_()

    def _addToPipelineCallback(self):
        selectedItems = self.selectedItems()
        names = [i.pipeName for i in selectedItems if not i.isPipeCategory]
        for name in names:
            self.guiPipeline.addPipe(name)

    def selectItems(self, names):
        items = []
        for name in names:
            found = self.findItems(name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
            items.extend(found)
        if items:
            self.clearSelection()
            for item in items:
                item.setSelected(True)
                if item.parent():
                    item.parent().setExpanded(True)
                    self.scrollToItem(item)


def testGuiPipe(GuiPipe):
    """

    :param GuiPipe:
    :return:  Open the Gui pipe in a mock Gui pipeline
    """
    from PyQt5 import QtWidgets
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    win = QtWidgets.QMainWindow()

    pipeline = PipelineDropArea(win)
    demoGuiPipe = GuiPipe(parent=pipeline)
    pipeline.addDock(demoGuiPipe)

    win.setCentralWidget(pipeline)
    win.resize(1000, 500)
    win.show()

    app.start()
