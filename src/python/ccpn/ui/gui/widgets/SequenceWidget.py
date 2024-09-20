"""
This file contains the SequenceModule module

GWV: modified 1-9/12/2016
GWV: 13/04/2017: Disconnected from Sequence Graph; Needs refactoring
GWV: 22/4/2018: New handling of colours

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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-08-23 19:21:22 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing

from PyQt5 import QtCore, QtGui, QtWidgets
from collections import OrderedDict
from collections.abc import Iterable
from ccpn.core.Chain import Chain
from ccpn.core.Residue import Residue
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrChain import NmrChain
from ccpn.core.lib.Notifiers import Notifier

from ccpn.ui.gui.guiSettings import getColours
from ccpn.ui.gui.guiSettings import (GUICHAINRESIDUE_ASSIGNED, GUICHAINRESIDUE_POSSIBLE,
                                     GUICHAINRESIDUE_WARNING, SEQUENCEMODULE_DRAGMOVE)
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.MessageDialog import showYesNo
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.widgets.MessageDialog import progressManager, showWarning
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight


#==========================================================================================
# Sequence Widget scenes and graphics-views
#==========================================================================================

class _SequenceWidgetScene(QtWidgets.QGraphicsScene):
    """Scene with drop-event to handle dropping nmrResidues onto a chain.
    """

    def __init__(self, parent, moduleParent=None, *args, **kwds):
        """Initialise the widget.
        """

        self.moduleParent = moduleParent
        super(_SequenceWidgetScene, self).__init__(parent, *args, **kwds)

    def dragMoveEvent(self, event):
        """Handle dragging of items from the sequence-graph to the sequence-widget.
        """
        parent = self.moduleParent

        # pos = event.scenePos()
        # pos = QtCore.QPointF(pos.x(), pos.y() - 25)  # WB: TODO: -25 is a hack to take account of scrollbar height

        item = parent._getGuiItem(self)
        if item:
            # _highlight is an overlay of the guiNmrResidue but with a highlight colour
            parent._highlight.setHtml(
                    '<div style="color: %s; text-align: center;"><strong>' % parent.colours[SEQUENCEMODULE_DRAGMOVE] +
                    item.toPlainText() + '</strong></div>')
            parent._highlight.setPos(item.pos())
        else:
            parent._highlight.setPlainText('')

        event.accept()

        super(_SequenceWidgetScene, self).dragMoveEvent(event)

    def dropEvent(self, event):
        """Handle dropping items onto the sequence-widget.
        """
        parent = self.moduleParent

        parent._highlight.setPlainText('')
        data, dataType = _interpretEvent(event)

        if dataType == 'pids':

            # check that the drop event contains the correct information
            # if isinstance(data, Iterable) and len(data) == 2:
            #   nmrChain = self.mainWindow.project.getByPid(data[0])
            #   nmrResidue = self.mainWindow.project.getByPid(data[1])
            #   if isinstance(nmrChain, NmrChain) and isinstance(nmrResidue, NmrResidue):
            #     if nmrResidue.nmrChain == nmrChain:
            #       self._processNmrChains(data, event)

            if isinstance(data, Iterable):
                for dataItem in data:
                    obj = parent.mainWindow.project.getByPid(dataItem)
                    if isinstance(obj, NmrChain) or isinstance(obj, NmrResidue):
                        parent._processNmrChains(obj)
                        break

        super(_SequenceWidgetScene, self).dropEvent(event)


class _SequenceWidgetGraphicsView(QtWidgets.QGraphicsView):
    """Graphics-view with a left-mouse drag.
    """
    _lastDragMode = None

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the press-event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            # set the drag-mode
            self._lastDragMode = self.dragMode()
            self.setDragMode(self.ScrollHandDrag)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the release-event.
        """
        super().mouseReleaseEvent(event)

        if self._lastDragMode is not None:
            # undo the drag-mode
            self.setDragMode(self._lastDragMode)
            self._lastDragMode = None

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        """Handle the drag-move-event.
        """
        super().dragMoveEvent(event)

        if self._lastDragMode is not None:
            # undo the drag-mode
            self.setDragMode(self._lastDragMode)
            self._lastDragMode = None


#==========================================================================================
# Sequence-widget
#==========================================================================================

class SequenceWidget():
    """
    The widget displays all chains in the project as one-letter amino acids. The one letter residue
    sequence codes are all instances of the GuiChainResidue class and the style applied to a residue
    indicates its assignment state and, when coupled with the Sequence Graph module, indicates if a
    stretch of residues matches a given stretch of connected NmrResidues. The QGraphicsScene and
    QGraphicsView instances provide the canvas on to which the amino acids representations are drawn.
    """

    def __init__(self, moduleParent=None, parent=None, mainWindow=None, name='Sequence', chains=None):
        """Initialise the widget
        """

        self.moduleParent = moduleParent
        self._parent = parent
        self.mainWindow = mainWindow
        self.project = mainWindow.application.project
        self._chains = chains or []

        self._parent.setAcceptDrops(True)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.scene = _SequenceWidgetScene(self._parent, moduleParent=self)
        self.scrollContents = _SequenceWidgetGraphicsView(self.scrollArea.scene)
        self.scrollContents.setAcceptDrops(True)
        self.scrollContents.setInteractive(True)
        self.scrollContents.setAlignment(QtCore.Qt.AlignTop)
        self.scrollContents.setGeometry(QtCore.QRect(0, 0, 380, 1000))
        self.horizontalLayout2 = QtWidgets.QHBoxLayout(self.scrollContents)
        self.scrollArea.setWidget(self.scrollContents)

        self.colours = getColours()
        self.residueCount = 0

        self._parent.layout().addWidget(self.scrollArea)

        self.chainLabels = OrderedDict()
        self._highlight = None
        self._initialiseChainLabels()

        #GWV: removed fixed height restrictions but maximum height instead
        #self.setFixedHeight(2*self.widgetHeight)
        #self.scrollContents.setFixedHeight(2*self.widgetHeight)
        # self._parent.setMaximumHeight(100)
        # self.scrollContents.setMaximumHeight(100)
        self._setStyle()

        #GWV: explicit initialisation to prevent crashes
        self._chainNotifier = None
        self._residueNotifier = None
        self._residueDeleteNotifier = None
        self._chainDeleteNotifier = None
        self._nmrResidueNotifier = None
        self._registerNotifiers()

    def _setStyle(self):
        """Set the focus/noFocus colours for the widget.
        """
        _style = """QGraphicsView {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                    }
                    QGraphicsView:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    QGraphicsView:disabled { background-color: palette(midlight); }
                    """
        self.scrollArea.setStyleSheet(_style)

    def _getGuiItem(self, scene):
        for item in scene.items():
            if item.isUnderMouse() and item != self._highlight:
                if hasattr(item, 'residue'):
                    # self._highlight.setPlainText(item.toPlainText())
                    return item
        else:
            return None

    def _processNmrChains(self, data: typing.Union[NmrChain, NmrResidue]):
        """
        Processes a list of NmrResidue Pids and assigns the residue onto which the data is dropped and
        all succeeding residues according to the length of the list.
        """

        guiRes = self._getGuiItem(self.scrollArea.scene)
        #self.scene.itemAt(event.scenePos())

        # if not hasattr(guiRes, 'residue'):
        #   return

        if isinstance(data, NmrChain):
            nmrChain = data  #self.mainWindow.project.getByPid(data)
            selectedNmrResidue = nmrChain.nmrResidues[0]
        elif isinstance(data, NmrResidue):
            selectedNmrResidue = data
            nmrChain = data.nmrChain
        else:
            return

        # selectedNmrResidue = self.mainWindow.project.getByPid(data[1])   # ejb - new, pass in selected nmrResidue
        residues = [guiRes.residue]
        # toAssign = [nmrResidue for nmrResidue in nmrChain.nmrResidues if '-1' not in nmrResidue.sequenceCode]
        toAssign = nmrChain.mainNmrResidues
        chainRes = guiRes.residue

        if toAssign:
            if isinstance(data, NmrChain):
                selectedNmrResidue = toAssign[0]
                residues = [chainRes]
                idStr = 'nmrChain: %s to residue: %s' % (toAssign[0].nmrChain.id, residues[0].id)
            else:
                try:
                    selectedNmrResidue = selectedNmrResidue.mainNmrResidue

                    # get the connected nmrResidues
                    if selectedNmrResidue in toAssign:
                        indL = indR = toAssign.index(selectedNmrResidue)

                        while toAssign[indL].previousNmrResidue and indL > 0 and chainRes:
                            indL -= 1
                            chainRes = chainRes.previousResidue

                        endRes = chainRes
                        while toAssign[indR].nextNmrResidue and indR < len(toAssign) and endRes:
                            indR += 1
                            endRes = endRes.nextResidue

                        toAssign = toAssign[indL:indR + 1]

                    else:
                        showWarning('Sequence Graph',
                                    'nmrResidue %s does not belong to nmrChain' % str(selectedNmrResidue.pid))
                        return

                    # # get the first residue of the chain
                    # leftAssignNum = toAssign.index(selectedNmrResidue)
                    # for resLeft in range(leftAssignNum):
                    #     if not selectedNmrResidue.previousNmrResidue:
                    #         break
                    #     leftAssignNum -= 1
                    #     chainRes = chainRes.previousResidue
                    #
                    # endRes = chainRes
                    # for resRight in range(len(toAssign) - 1):
                    #     endRes = endRes.nextResidue

                except Exception as es:
                    showWarning('Sequence Graph', str(es))
                    return

                if not chainRes:
                    showWarning('Sequence Graph', 'Too close to the start of the chain')
                    return

                if not endRes:
                    showWarning('Sequence Graph', 'Too close to the end of the chain')
                    return

                residues = [chainRes]

                idStr = 'nmrChain: %s;\nnmrResidue: %s to residue: %s' % (
                    toAssign[0].nmrChain.id, selectedNmrResidue.id, guiRes.residue.id)

            result = showYesNo('Assignment', 'Assign %s?' % idStr)
            if result:

                with progressManager(self.mainWindow, 'Assigning %s' % idStr):

                    update = False
                    if nmrChain.id == '@-':
                        # assume that it is the only one
                        try:
                            nmrChain.assignSingleResidue(selectedNmrResidue, residues[0])
                            update = True
                        except Exception as es:
                            showWarning('Sequence Graph', str(es))
                            return
                    else:

                        # toAssign is the list of mainNmrResidues of the chain
                        for ii in range(len(toAssign) - 1):
                            resid = residues[ii]
                            nxt = resid.nextResidue  #TODO:ED may not have a .nextResidue
                            residues.append(nxt)

                        try:
                            nmrChain.assignConnectedResidues(residues[0])
                            update = True
                        except Exception as es:
                            showWarning('Sequence Graph', str(es))

                    # highlight the new items in the chain
                    if update:
                        thisChain = residues[0].chain

                        if (chLabel := self.chainLabels.get(thisChain)):
                            for res in residues:
                                guiResidue = chLabel.residueDict.get(res.sequenceCode)
                                guiResidue._setStyleAssigned()

                        # for chainLabel in self.chainLabels:
                        #     if chainLabel.chain == thisChain:
                        #         for ii, res in enumerate(residues):
                        #             guiResidue = chainLabel.residueDict.get(res.sequenceCode)
                        #             guiResidue._setStyleAssigned()
                        #         break

                        if self.moduleParent and thisChain:
                            self.moduleParent._setCurrentOnLinkedNmrChain(thisChain.nmrChain)

    def populateFromSequenceGraphs(self):
        """
        Take the selected chain from the first opened sequenceGraph and highlight in module
        """
        # get the list of open sequenceGraphs

        # self.moduleParent.predictSequencePosition(self.moduleParent.predictedStretch)
        return

        # from ccpn.AnalysisAssign.modules.SequenceGraph import SequenceGraphModule
        # seqGraphs = [sg for sg in SequenceGraphModule.getInstances()]
        #
        # if seqGraphs:
        #   try:
        #     seqGraphs[0].predictSequencePosition(seqGraphs[0].predictedStretch)
        #   except Exception as es:
        #     getLogger().warning('Error: no predictedStretch found: %s' % str(es))

    def _clearStretches(self, chain):
        """
        CCPN INTERNAL called in predictSequencePosition method of SequenceGraph.
        Highlights regions on the sequence specified by the list of residues passed in.
        """
        if (chLabel := self.chainLabels.get(chain)):
            for res1 in chLabel.residueDict.values():
                res1._styleResidue()

    def _highlightPossibleStretches(self, chain, residues: typing.List[Residue]):
        """
        CCPN INTERNAL called in predictSequencePosition method of SequenceGraph.
        Highlights regions on the sequence specified by the list of residues passed in.
        """
        # for res1 in self.chainLabels[chainNum].residueDict.values():
        #   res1._styleResidue()

        try:
            # self._clearStretches(chainNum)

            guiResidues = []
            _labelDict = self.chainLabels[chain].residueDict
            for residue in residues:
                guiResidue = _labelDict[residue.sequenceCode]
                guiResidues.append(guiResidue)

                if guiResidue.residue.nmrResidue is not None:
                    guiResidue._setStyleWarningAssigned()
                else:
                    guiResidue._setStylePossibleAssigned()

        except Exception as es:
            getLogger().warning('_highlightPossibleStretches: %s' % str(es))

    def _addChainLabel(self, chain: Chain, placeholder=False, tryToUseSequenceCodes=False):
        """Creates and adds a GuiChainLabel to the sequence module.

        :param chain: core Chain or None
        :param placeholder: True|False, if True, adds an empty object
        :param tryToUseSequenceCodes: True|False use sequence codes
        :return:
        """
        if len(self._chains) == 1 and len(self.chainLabels) == 1:
            self.scrollArea.scene.clear()  # remove and delete all contents
            self.chainLabels.clear()
            self.widgetHeight = 0

        self.chainLabel = GuiChainLabel(self, self.mainWindow, self.scrollArea.scene, position=[0, self.widgetHeight],
                                        chain=chain, placeholder=placeholder,
                                        tryToUseSequenceCodes=tryToUseSequenceCodes)
        self.scrollArea.scene.addItem(self.chainLabel)
        self.chainLabels[chain] = self.chainLabel
        self.widgetHeight = (0.9 * (self.chainLabel.boundingRect().height())) * len(self.chainLabels)

    def _registerNotifiers(self):
        """register notifiers
        """
        self._residueNotifier = Notifier(self.project,
                                         [Notifier.CREATE, Notifier.CHANGE],
                                         'Residue',
                                         # self._addChainResidueCallback,
                                         self._refreshChainLabels,  # testing
                                         onceOnly=True)
        self._residueDeleteNotifier = Notifier(self.project,
                                               [Notifier.DELETE],
                                               'Residue',
                                               # self._deleteChainResidueCallback,
                                               self._refreshChainLabels,
                                               onceOnly=True)
        self._nmrResidueNotifier = Notifier(self.project,
                                            [Notifier.CHANGE],
                                            'NmrResidue',
                                            self._refreshChainLabels,
                                            onceOnly=True)

    def _unRegisterNotifiers(self):
        """unregister notifiers
        """
        if self._chainNotifier:
            self._chainNotifier.unRegister()
            self._chainNotifier = None
        if self._residueNotifier:
            self._residueNotifier.unRegister()
            self._residueNotifier = None
        if self._residueDeleteNotifier:
            self._residueDeleteNotifier.unRegister()
            self._residueDeleteNotifier = None
        if self._chainDeleteNotifier:
            self._chainDeleteNotifier.unRegister()
            self._chainDeleteNotifier = None
        if self._nmrResidueNotifier:
            self._nmrResidueNotifier.unRegister()
            self._nmrResidueNotifier = None

    def _closeModule(self):
        """
        CCPN-INTERNAL: used to close the module
        """
        self._unRegisterNotifiers()

    def close(self):
        """
        Close the table from the commandline
        """
        self._closeModule()  # ejb - needed when closing/opening project

    def setChains(self, chains):
        self._chains = chains
        self._initialiseChainLabels()

    def _initialiseChainLabels(self):
        """initialise the chain label widgets
        """
        self.scrollArea.scene.clear()
        self.chainLabels.clear()
        self.widgetHeight = 0  # dynamically calculated from the number of chains

        if not self._chains:
            self._addChainLabel(chain=None, placeholder=True)
        else:
            for chain in self._chains:
                if not chain.isDeleted:
                    self._addChainLabel(chain, tryToUseSequenceCodes=True)

        self._highlight = QtWidgets.QGraphicsTextItem()
        # self._highlight.setDefaultTextColor(QtGui.QColor(self.colours[SEQUENCEMODULE_TEXT]))

        setWidgetFont(self._highlight, size='MEDIUM')
        self._highlight.setPlainText('')
        self.scrollArea.scene.addItem(self._highlight)

    def _refreshChainLabels(self, data=None):
        """callback to refresh chains notifier
        """
        if not data:
            return

        self._initialiseChainLabels()

        # highlight any predicted stretches
        self.populateFromSequenceGraphs()


class GuiChainLabel(QtWidgets.QGraphicsTextItem):
    """
    This class is acts as an anchor for each chain displayed in the Sequence Module.
    On instantiation an instance of the GuiChainResidue class is created for each residue in the chain
    along with a dictionary mapping Residue objects and GuiChainResidues, which is required for assignment.
    """

    def __init__(self, sequenceWidget, mainWindow, scene, position, chain, placeholder=None,
                 tryToUseSequenceCodes=False):
        QtWidgets.QGraphicsTextItem.__init__(self)

        self.sequenceWidget = sequenceWidget
        self.mainWindow = mainWindow
        self.scene = scene
        self.chain = chain
        self.project = mainWindow.application.project

        self.items = [self]  # keeps track of items specific to this chainLabel
        self.colours = getColours()
        setWidgetFont(self, size='MEDIUM')

        self.setPos(QtCore.QPointF(position[0], position[1]))
        if placeholder:
            self.text = 'No Chains Selected'
        else:
            self.text = '%s:%s' % (chain.compoundName, chain.shortName)
        self.setHtml('<div style=><strong>' + self.text + ' </strong></div>')

        self.residueDict = {}
        self.currentIndex = 0
        self.labelPosition = self.boundingRect().width()
        self.yPosition = position[1]

        if chain:
            # useSequenceCode = False
            # if tryToUseSequenceCodes:
            #   # mark residues where sequence is multiple of 10 when you can
            #   # simple rules: sequenceCodes must be integers and consecutive
            #   prevCode = None
            #   for residue in chain.residues:
            #     try:
            #       code = int(residue.sequenceCode)
            #       if prevCode and code != (prevCode+1):
            #         break
            #       prevCode = code
            #     except: # not an integer
            #       break
            #   else:
            #     useSequenceCode = True
            for idx, residue in enumerate(chain.residues):
                self._addResidue(idx, residue)

        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)
        self._checkPalette(self.mainWindow.palette())

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        """Change text colour when theme changes.
        QGraphicsItems have no palette/stylesheet, so need change-event.
        """
        self.setDefaultTextColor(pal.highlight().color())

    def _addResidue(self, idx, residue):
        """Add residue and optional sequenceCode."""
        newResidue = GuiChainResidue(self, self.mainWindow, residue, self.scene,
                                     self.labelPosition, self.currentIndex, self.yPosition)
        self.scene.addItem(newResidue)
        self.items.append(newResidue)
        self.residueDict[residue.sequenceCode] = newResidue
        self.currentIndex += 1

        if idx % 10 == 9:  # print out every 10
            numberItem = QtWidgets.QGraphicsTextItem(residue.sequenceCode)
            setWidgetFont(numberItem, size='TINY')
            _spacing = getFontHeight(size='MEDIUM')
            # tweaking to get position at bottom-left
            xPos = self.labelPosition + (_spacing * self.currentIndex) - (_spacing * 0.25)
            yPos = self.yPosition + _spacing * 0.5
            numberItem.setPos(QtCore.QPointF(xPos, yPos))
            numberItem.setDefaultTextColor(QtGui.QColor('#808080'))  # medium-gray, theme agnostic
            self.scene.addItem(numberItem)
            self.items.append(numberItem)
            self.currentIndex += 1


#==========================================================================================
# functions
#==========================================================================================

# WB: TODO: this used to be in some util library but the
# way drag and drop is done now has changed but
# until someone figures out how to do it the new
# way then we are stuck with the below
# (looks like only first part of if below is needed)
def _interpretEvent(event):
    """ Interpret drop event and return (type, data)
    """

    import json
    from ccpn.util.Constants import ccpnmrJsonData

    mimeData = event.mimeData()
    if mimeData.hasFormat(ccpnmrJsonData):
        jsonData = json.loads(mimeData.text())
        pids = jsonData.get('pids')

        if pids is not None:
            # internal data transfer - series of pids
            return (pids, 'pids')

            # NBNB TBD add here slots for between-applications transfer, and other types as needed

    elif event.mimeData().hasUrls():
        filePaths = [url.path() for url in event.mimeData().urls()]
        return (filePaths, 'urls')

    elif event.mimeData().hasText():
        return (event.mimeData().text(), 'text')

    return (None, None)


#==========================================================================================
# GuiChainResidue
#==========================================================================================

class GuiChainResidue(QtWidgets.QGraphicsTextItem, Base):
    fontSize = 20
    assignedState = 0

    def __init__(self, guiChainLabel, mainWindow, residue, scene, labelPosition, index, yPosition):

        QtWidgets.QGraphicsTextItem.__init__(self)
        Base._init(self, acceptDrops=True)

        self.guiChainLabel = guiChainLabel
        self.mainWindow = mainWindow
        self.residue = residue
        self.scene = scene

        setWidgetFont(self, size='MEDIUM')
        _spacing = getFontHeight(size='MEDIUM')
        self.colours = getColours()
        self.setPlainText(residue.shortName)
        position = labelPosition + (_spacing * index)

        self.setPos(QtCore.QPointF(position, yPosition))
        self.residueNumber = residue.sequenceCode

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable | self.flags())
        self._styleResidue()

        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        """Change text colour when theme changes.
        QGraphicsItems have no palette/stylesheet, so need change-event.
        """
        self.setDefaultTextColor(pal.text().color())
        # might need to do this if the colours are different for light/dark, see assignedState below
        # self.colours = getColours()

    def _styleResidue(self):
        """A convenience function for applying the correct styling to GuiChainResidues depending on their state.
        """
        try:
            if self.residue.nmrResidue is not None:
                self._setStyleAssigned()
            else:
                self._setStyleUnAssigned()
        except:
            getLogger().warning('GuiChainResidue has been deleted')

    def _setStyleUnAssigned(self):
        self.assignedState = 0
        self.setPlainText(self.residue.shortName)

    def _setStyleAssigned(self):
        self.assignedState = 1
        self.setHtml('<div style="color: %s; text-align: center;"><strong>' % self.colours[GUICHAINRESIDUE_ASSIGNED] +
                     self.residue.shortName + '</strong></div>')

    def _setStylePossibleAssigned(self):
        self.assignedState = 2
        self.setHtml('<div style="color: %s; "text-align: center;">' % self.colours[GUICHAINRESIDUE_POSSIBLE] +
                     self.residue.shortName + '</div')

    def _setStyleWarningAssigned(self):
        self.assignedState = 3
        self.setHtml('<div style="color: %s; "text-align: center;">' % self.colours[GUICHAINRESIDUE_WARNING] +
                     self.residue.shortName + '</div')

    def _setFontBold(self):
        """
        Sets font to bold, necessary as QtWidgets.QGraphicsTextItems are used for display of residue
        one-letter codes.
        """
        fmt = QtGui.QTextCharFormat()
        fmt.setFontWeight(75)
        self.textCursor().mergeCharFormat(fmt)
