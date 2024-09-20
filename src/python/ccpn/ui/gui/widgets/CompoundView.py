"""
This widget is based on the CcpNmr ChemBuild.
Credits to Tim Stevens, University of Cambridge December 2010-2012
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
__dateModified__ = "$dateModified: 2024-08-23 19:21:18 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg, QtPrintSupport
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from math import atan2, sin, cos, sqrt, degrees, radians, hypot, pi
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.FileDialog import PDFFileDialog
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, BORDERNOFOCUS


Qt = QtCore.Qt
QPointF = QtCore.QPointF
QRectF = QtCore.QRectF
PI = 3.1415926535898


class CompoundView(QGraphicsView, Base):

    def __init__(self, parent=None, smiles=None, variant=None, preferences=None, **kwds):

        super(CompoundView, self).__init__(parent)
        Base._init(self, **kwds)

        _scene = QGraphicsScene(self)
        # _scene.setSceneRect(0, 0, 300, 300)
        self.setScene(_scene)
        self.setCacheMode(QGraphicsView.CacheBackground)
        # QtWidgets.QGraphicsView.__init__(self, parent)

        self._parent = parent
        self.preferences = preferences

        self.backgroundColor = QtGui.QColor(10, 1, 0, 0)
        self.bondColor = Qt.black

        # self.setCompound = self.setCompound
        self.rotatePos = None
        if variant:
            self.compound = variant.compound
        else:
            self.compound = None

        self.dustbin = set()
        self.variant = variant
        self.atomViews = {}
        self.selectedViews = set()
        self.bondItems = {}
        self.groupItems = {}
        self.update()
        self.nameAtoms = True
        self.showChargeSymbols = True
        self.showChiralities = True
        self.showStats = False
        self.showGroups = False
        self.menuAtomView = None
        self.menuAtom = None
        self.movePos = None
        self.zoomLevel = 1.0
        # Context menu

        self.needMenuAtom = []
        self.needSelectedAtom = []
        self.needFurtherCheck = []
        self.contextMenu = self.setupContextMenu()

        # self.setGeometry(20, 40, 350, 350) #[(1) < left, (2) < up, (3)Width, (4)Height
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setInteractive(True)
        self.resetView()

        self.selectionBox = SelectionBox(self.scene(), self)
        self.scene().addItem(self.selectionBox)

        self.editAtom = None
        self.editWidget = QtWidgets.QLineEdit()
        self.editWidget.setMaxLength(8)
        self.editWidget.resize(50, 30)

        effect = QtWidgets.QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(3)
        effect.setOffset(2, 2)

        #self.editWidget.setGraphicsEffect(effect)
        self.editWidget.returnPressed.connect(self.setAtomName)
        self.editWidget.hide()
        self.editProxy = self.scene().addWidget(self.editWidget)
        self.editProxy.setZValue(2)

        # TODO: Add settings for this
        self.showSkeletalFormula = False
        self.showSkeletalFormulaColor = True
        self.snapToGrid = False

        self.autoChirality = True

        self.addGraphicsItems()

        if self.variant and self.showSkeletalFormula:
            self.variant.snapAtomsToGrid(50.0)
            self.updateAll()

        self.smiles = smiles
        if smiles:
            self.setSmiles(self.smiles)
        self._setFocusColour()
        self._setStyle()

    def _setStyle(self):
        self._checkPalette(self.palette())
        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        self.setBackgroundBrush(pal.base())
        self.background = pal.base().color()
        self.bondColor = pal.text().color()

    def setSmiles(self, smiles):
        """set the smiles"""
        compound = importSmiles(smiles)
        variant = list(compound.variants)[0]
        self.setVariant(variant)
        variant.snapAtomsToGrid(ignoreHydrogens=False)
        self.smiles = smiles
        self.centerView()
        self.resetView()
        self.updateAll()
        self.show()

    def _setFocusColour(self):
        """Set the focus/noFocus colours for the widget."""
        _style = """QGraphicsView {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                        background-color: palette(base);
                    }
                    QGraphicsView:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    QGraphicsView:disabled { background-color: palette(midlight); }
                    """
        self.setStyleSheet(_style)

    def minimumSizeHint(self):
        return QtCore.QSize(200, 200)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #
    #     self.resetCachedContent()
    #     self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
    #     self.zoomLevel = 1.0

        # return QtWidgets.QGraphicsView.resizeEvent(self, event)

    # def paintEvent(self, event: QtGui.QPaintEvent):
    #   return QtWidgets.QGraphicsView.paintEvent(self, event)

    def setAtomName(self):

        atom = self.editAtom

        if not atom:
            return

        text = self.editWidget.text().strip()

        if text and (text != atom.name):
            used = set([a.name for a in atom.compound.atoms])
            if text in used:
                prevAtom = self.compound.atomDict[text]
                name2 = text + '!'
                while name2 in used:
                    name2 = name2 + '!'
                prevAtom.setName(name2)
                atom.setName(text)

            else:
                atom.setName(text)

        self.editAtom = None
        self.editWidget.hide()
        self.updateAll()

    def setCompound(self, compound, variantInd=None, replace=True):
        """ Set the compound on the graphic scene. """
        if compound is not self.compound:

            if replace or not self.compound:
                self.compound = compound
                if variantInd:
                    variant = list(compound.variants)[variantInd]

                else:
                    variants = list(compound.variants)
                    if variants:
                        for variant2 in variants:
                            if (variant2.polyLink == 'none') and (variant2.descriptor == 'neutral'):
                                variant = variant2
                                break
                        else:
                            for variant2 in variants:
                                if variant2.polyLink == 'none':
                                    variant = variant2
                                    break
                            else:
                                variant = variants[0]
                    else:
                        variant = Variant(compound)

                self.setVariant(variant)
                variant.snapAtomsToGrid(ignoreHydrogens=False)
                self.variant = variant
                self.centerView()
                self.resetView()
                self.updateAll()
                # self.show()

            else:
                variant = list(compound.variants)[0]
                x, y = self.getAddPoint()
                self.compound.copyVarAtoms(variant.varAtoms, (x, y))
                self.centerView()
                self.resetView()
                self.updateAll()

        self.centerView()
        self.resetView()
        self.updateAll()

    def queryAtomName(self, atomLabel):

        self.editAtom = atom = atomLabel.atom

        self.editWidget.setText(atom.name or atom.element)
        self.editWidget.setVisible(True)

        center = QtCore.QPointF(self.editWidget.rect().center())
        pos = atomLabel.pos() - center
        self.editProxy.setPos(pos)

    def drawForeground(self, painter, viewRect):

        QtWidgets.QGraphicsView.drawForeground(self, painter, viewRect)

    def drawBackground(self, painter, viewRect):

        transform = painter.transform()
        scale = float(transform.m11())
        unScale = 1.0 / scale

        QtWidgets.QGraphicsView.drawBackground(self, painter, viewRect)

        # Text

        pad = 2.0
        qPoint = QtCore.QPointF
        qRectF = QtCore.QRectF
        painter.setPen(ATOM_NAME_FG)
        painter.setFont(QtGui.QFont("DejaVu Sans Mono", 12))
        painter.scale(unScale, unScale)
        fontMetric = QtGui.QFontMetricsF(painter.font())

        tl = viewRect.topLeft()
        x0 = tl.x() * scale
        y0 = tl.y() * scale
        y1 = y0 + viewRect.height() * scale

    def resetView(self):

        self.resetCachedContent()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def setupContextMenu(self):
        #
        QAction = QtWidgets.QAction
        menu = QtWidgets.QMenu(self)

        action = QAction('Reset View', self, triggered=self.resetView)
        menu.addAction(action)

        subMenu = menu.addMenu('Export')
        action = QAction('Export PDF(3D)', self, triggered=self.exportPdf)
        subMenu.addAction(action)
        action = QAction('Export SVG(2D)', self, triggered=self.exportSvg)
        subMenu.addAction(action)

        subMenu = menu.addMenu('Edit')
        action = QAction('Show Skeletal structure ', self, triggered=self.showSkeletal)
        subMenu.addAction(action)
        action = QAction('Show 3D structure ', self, triggered=self.show3D)
        subMenu.addAction(action)
        action = QAction('Rotate Left', self, triggered=self.rotateLeft)
        subMenu.addAction(action)
        self.needMenuAtom.append(action)
        action = QAction('Rotate Right', self, triggered=self.rotateRight)
        subMenu.addAction(action)

        return menu

    def popupContextMenu(self, pos):

        menuAtomView = self.menuAtomView
        menuAtom = self.menuAtom

        if menuAtom:
            for action in self.needMenuAtom:
                action.setEnabled(True)
        else:
            for action in self.needMenuAtom:
                action.setEnabled(False)

        if self.selectedViews:
            for action in self.needSelectedAtom:
                action.setEnabled(True)

        else:
            for action in self.needSelectedAtom:
                action.setEnabled(False)

        for action, func in self.needFurtherCheck:
            action.setEnabled(bool(func()))

        self.contextMenu.popup(pos)

    def getMenuAtom(self, posFilter=None, negFilter=None):

        if self.variant and self.menuAtom:
            elem = self.menuAtom.element

            if posFilter is None:
                if negFilter is None:
                    return self.menuAtom
                elif elem not in negFilter:
                    return self.menuAtom

            elif elem in posFilter:
                if negFilter is None:
                    return self.menuAtom
                elif elem not in negFilter:
                    return self.menuAtom

    def getMenuLinkAtoms(self):

        if self.variant and self.menuAtom:
            if self.menuAtom.element == 'H':
                atoms = [self.menuAtom, ]

            elif self.menuAtom.element in ('O', 'S'):
                atoms = [self.menuAtom, ]
                for atomB in self.menuAtom.neighbours:
                    if atomB.element == 'H':
                        atoms.append(atomB)
                        break

                else:
                    return

            else:
                return

            return atoms

    def setVariant(self, variant):

        if variant is not self.variant:
            scene = self.scene()

            self.atomViews = {}
            self.selectedViews = set()
            self.bondItems = {}
            self.groupItems = {}

            items = set(scene.items())
            items.remove(self.editProxy)
            items.remove(self.selectionBox)
            # print(items)

            for item in items:
                item.hide()

            for item in items:
                del item

            self.resetCachedContent()
            self.variant = variant
            self.compound = variant.compound
            self._parent.variant = variant
            self._parent.compound = self.compound

            self.addGraphicsItems()
            self.centerView()

    def updateAll(self):

        var = self.variant
        scene = self.scene()

        if var:
            getView = self.atomViews.get
            bondItems = self.bondItems
            getBondItem = bondItems.get
            groupDict = self.groupItems

            usedGroups = set(var.atomGroups)
            for group in usedGroups:
                if group in groupDict:
                    groupDict[group].syncGroup()

                elif group.groupType == EQUIVALENT:
                    EquivItem(scene, self, group)

                elif group.groupType == PROCHIRAL:
                    ProchiralItem(scene, self, group)

                elif group.groupType == AROMATIC:
                    AromaticItem(scene, self, group)

            zombieGroups = set(groupDict.keys()) - usedGroups
            for group in zombieGroups:
                groupItem = groupDict[group]
                del groupDict[group]
                del groupItem

            for atom in var.varAtoms:
                atomView = getView(atom)

                if atomView:
                    atomView.syncToAtom()
                else:
                    atomView = AtomItem(scene, self, atom)

            zombieBonds = set(self.bondItems.keys()) - set(var.bonds)
            for bond in zombieBonds:
                bondItem = bondItems[bond]
                del bondItems[bond]
                del bondItem

            for bond in var.bonds:
                bondItem = getBondItem(bond)

                if not bondItem:
                    bondItem = BondItem(scene, self, bond)

    def addGraphicsItems(self):

        if not self.variant:
            return

        scene = self.scene()

        # Draw groups

        for group in self.variant.atomGroups:
            if group.groupType == EQUIVALENT:
                EquivItem(scene, self, group)

            elif group.groupType == PROCHIRAL:
                ProchiralItem(scene, self, group)

            elif group.groupType == AROMATIC:
                AromaticItem(scene, self, group)

        # Draw atoms

        self.atomViews = {}
        for atom in self.variant.varAtoms:
            a = AtomItem(scene, self, atom)
            scene.addItem(a)
        # Draw bonds
        done = set()
        self.bondItems = bondDict = {}
        for bond in self.variant.bonds:
            atoms = frozenset(bond.varAtoms)
            if atoms in done:
                pass

            bondItem = BondItem(scene, self, bond)
            scene.addItem(bondItem)
            done.add(atoms)

    def centroid(self, views):

        x0 = 0.0
        y0 = 0.0
        n = 0.0

        for view in views:
            x1, y1, z1 = view.atom.coords
            x0 += x1
            y0 += y1
            n += 1.0

        x0 /= n
        y0 /= n

        return x0, y0

    def centroidAtoms(self, atoms):

        x0 = 0.0
        y0 = 0.0
        n = 0.0

        for atom in atoms:
            x1, y1, z1 = atom.coords
            x0 += x1
            y0 += y1
            n += 1.0

        x0 /= n
        y0 /= n

        return x0, y0

    def changeBackground(self):
        pass

    def exportPdf(self):

        if self.compound:
            printer = QtPrintSupport.QPrinter()
            oldRes = printer.resolution()
            newRes = 600.0
            fRes = oldRes / newRes
            printer.setResolution(newRes)

            fType = 'PDF (*.pdf)'
            dialog = PDFFileDialog(parent=self, acceptMode='export', fileFilter=fType)
            dialog._show()
            filePaths = dialog.selectedFiles()
            if filePaths and len(filePaths) > 0:
                filePath = filePaths[0]

                if filePath:
                    printer.setOutputFileName(filePath)
                    pdfPainter = QtGui.QPainter(printer)
                    self.bondColor = Qt.black
                    scene = self.scene()
                    items = scene.items()
                    cache = [None] * len(items)
                    for i, item in enumerate(items):
                        cache[i] = item.cacheMode()
                        item.setCacheMode(item.NoCache)
                    scene.render(pdfPainter)
                    pdfPainter.end()
                    self.bondColor = Qt.white
                    for i in range(len(items)):
                        items[i].setCacheMode(cache[i])

    def exportSvg(self):

        if self.compound:
            printer = QtSvg.QSvgGenerator()
            scene = self.scene()

            w = scene.width()
            h = scene.height()
            paperWidth = 200
            paperHeight = paperWidth * h / w
            resolution = printer.resolution() / 25.4
            printer.setSize(QtCore.QSize(paperWidth * resolution, paperHeight * resolution))

            fType = 'SVG (*.svg)'
            dialog = QtWidgets.QFileDialog
            filePath = dialog.getSaveFileName(self, filter=fType)

            if filePath:
                self.bondColor = QtCore.Qt.black
                printer.setFileName(filePath)
                svgPainter = QtGui.QPainter(printer)
                oldBackground = self.backgroundColor

                items = scene.items()
                cache = [None] * len(items)
                for i, item in enumerate(items):
                    cache[i] = item.cacheMode()
                    item.setCacheMode(item.NoCache)
                scene.render(svgPainter)
                svgPainter.end()
                self.backgroundColor = oldBackground
                self.bondColor = QtCore.Qt.white

                for i in range(len(items)):
                    items[i].setCacheMode(cache[i])

    def showSkeletal(self):
        self.showSkeletalFormula = True
        self.updateAll()

    def show3D(self):
        self.showSkeletalFormula = False
        self.updateAll()

    def rotateLeft(self, angle=PI * 5.0 / 180):

        selected = self.selectedViews or self.atomViews.values()

        if not selected:
            return

        x0, y0 = self.centroid(selected)
        self.rotateAtoms(x0, y0, angle)

    def rotateRight(self, angle=PI * 5.0 / 180):

        selected = self.selectedViews or self.atomViews.values()

        if not selected:
            return

        x0, y0 = self.centroid(selected)
        self.rotateAtoms(x0, y0, -angle)

    def rotateAtoms(self, x0, y0, deltaAngle):

        atoms = [v.atom for v in self.selectedViews]

        if atoms:
            for atom in atoms:
                x, y, z = atom.coords
                dx = x - x0
                dy = y - y0
                r = sqrt(dx * dx + dy * dy)
                angle2 = atan2(dx, dy) + deltaAngle

                x = x0 + r * sin(angle2)
                y = y0 + r * cos(angle2)
                atom.setCoords(x, y, z)

            for atom in atoms:
                atom.updateValences()

        elif self.compound:
            for atom in self.compound.atoms:
                for varAtom in atom.varAtoms:
                    x, y, z = varAtom.coords
                    dx = x - x0
                    dy = y - y0
                    r = sqrt(dx * dx + dy * dy)
                    angle2 = atan2(dx, dy) + deltaAngle

                    x = x0 + r * sin(angle2)
                    y = y0 + r * cos(angle2)
                    varAtom.coords = (x, y, z)

            for atom in self.compound.atoms:
                for varAtom in atom.varAtoms:
                    varAtom.updateValences()

        self.updateAll()

    def centerView(self):

        if self.variant:
            x, y, z = self.variant.getCentroid()

        else:
            x, y = 0, 0

        self.ensureVisible(x - 50, y - 50, 100, 100)

    def resetZoom(self):

        fac = 1.0 / self.zoomLevel
        self.scale(fac, fac)
        self.zoomLevel = 1.0

    def wheelEvent(self, event):

        if event.angleDelta().y() < 0:
            fac = 0.8333
        else:
            fac = 1.2

        newLevel = self.zoomLevel * fac

        if 0.5 < newLevel < 5.0:
            self.zoomLevel = newLevel
            self.scale(fac, fac)

        event.accept()

    def mousePressEvent(self, event):

        QtWidgets.QGraphicsView.mousePressEvent(self, event)

        button = event.button()
        pos = event.pos()
        mods = event.modifiers()
        haveCtrl = mods & Qt.CTRL
        haveShift = mods & Qt.SHIFT

        bondItem = None
        item = self.itemAt(pos)
        if item and isinstance(item, AtomItem):
            self.menuAtomView = item
            self.menuAtom = item.atom
        elif item and isinstance(item, AtomLabel):
            self.menuAtomView = item.atomView
            self.menuAtom = item.atom
        elif item and isinstance(item, BondItem):
            self.menuAtomView = None
            self.menuAtom = None
            if item.getDistToBond(self.mapToScene(pos)) <= 8:
                bondItem = item
        elif item and isinstance(item, AromaticItem):
            self.menuAtomView = None
            self.menuAtom = None
            bondItem = item
        else:
            self.menuAtomView = None
            self.menuAtom = None

            # deal with inconsistency in Qt versions for button naming
        try:
            MiddleButton = Qt.MiddleButton
        except AttributeError:
            MiddleButton = Qt.MidButton

        if button == Qt.LeftButton:

            if not self.menuAtom:
                self.selectionBox.updateRegion(begin=self.mapToScene(pos))

                if not (bondItem or haveCtrl or haveShift):
                    for view in list(self.selectedViews):
                        view.deselect()

        elif button == MiddleButton:
            if (haveCtrl or haveShift):
                selected = self.selectedViews or self.atomViews.values()

                if len(selected) > 1:
                    spos = self.mapToScene(pos)
                    x0, y0 = self.centroid(selected)
                    startAngle = atan2(spos.x() - x0, spos.y() - y0)
                    self.rotatePos = (startAngle, (x0, y0))

            else:
                pos = event.pos()
                h = self.horizontalScrollBar().sliderPosition()
                v = self.verticalScrollBar().sliderPosition()
                self.movePos = pos.x() + h, pos.y() + v

        elif button == Qt.RightButton:
            self.popupContextMenu(event.globalPos())
        #
        for atomView in self.selectedViews:
            atomView.setSelected(True)

        if item is not self.editProxy:
            self.setAtomName()

    def mouseMoveEvent(self, event):

        pos = event.pos()

        self.menuAtomView = None
        self.menuAtom = None

        if self.movePos:

            x0, y0 = self.movePos
            pos = event.pos()
            self.horizontalScrollBar().setSliderPosition(x0 - pos.x())
            self.verticalScrollBar().setSliderPosition(y0 - pos.y())

        elif self.rotatePos:

            startAngle, center = self.rotatePos
            x0, y0 = center
            spos = self.mapToScene(pos)
            dx = spos.x() - x0
            dy = spos.y() - y0
            angle = atan2(dx, dy)
            deltaAngle = angle - startAngle

            self.rotateAtoms(x0, y0, deltaAngle)
            self.rotatePos = (angle, center)
            self.update()

        else:
            self.selectionBox.updateRegion(end=self.mapToScene(pos))

        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):

        if self.selectionBox.region:

            posA = self.selectionBox.region.topLeft()
            posB = self.selectionBox.region.bottomRight()

            if posA != posB:
                xs = [posA.x(), posB.x()]
                ys = [posA.y(), posB.y()]
                xs.sort()
                ys.sort()
                x1, x2 = xs
                y1, y2 = ys

                for atomView in self.atomViews.values():
                    pos = atomView.pos()
                    x = pos.x()
                    y = pos.y()

                    if (x1 < x < x2) and (y1 < y < y2):
                        atomView.select()

        self.selectionBox.updateRegion()
        self.rotatePos = None
        self.movePos = None
        self.update()

        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)

    def getStats(self):
        pass


# def getAddPoint(self):
#     """ Set the compound on the specific position on the graphic scene. """
#     compoundView = CompoundView
#     globalPos = QtGui.QCursor.pos()
#     pos = compoundView.mapFromGlobal(globalPos)
#     widget = compoundView.childAt(pos)
#     if widget:
#       x = pos.x()
#       y = pos.y()
#     else:
#       x = compoundView.width()/2.0
#       y = compoundView.height()/2.0
#     point = compoundView.mapToScene(x, y)
#     return point.x(), point.y()


# Constants


PI = 3.1415926535898

MIMETYPE_ELEMENT = 'application/x-ccpn-element'
MIMETYPE_COMPOUND = 'application/x-ccpn-compound'
MIMETYPE = 'application/x-ccpn'

EQUIVALENT = 'equivalent'
PROCHIRAL = 'prochiral'
NONSTEREO = 'prochiral'
AROMATIC = 'aromatic'

CCPN_MOLTYPES = ('other', 'protein', 'DNA', 'RNA', 'carbohydrate')

ELEMENTS = {'Common'  : ['H', 'C', 'N', 'O', 'P', 'S', 'Se'],
            'Halogens': ['F', 'Cl', 'Br', 'I'],
            'Others'  : ['B', 'Si', 'As'], }

COVALENT_ELEMENTS = set(['H', 'C', 'N', 'O', 'P', 'S', 'Se', 'F', 'Cl', 'Br', 'I', 'B', 'Si', 'As'])

PERIODIC_TABLE = [
    ['Fr', 'Cs', 'Rb', 'K', 'Na', 'Li', 'H', ],
    ['Ra', 'Ba', 'Sr', 'Ca', 'Mg', 'Be', None],
    ['Ac', 'La', None, None, None, None, None],
    ['Th', 'Ce', None, None, None, None, None],
    ['Pa', 'Pr', None, None, None, None, None],
    ['U', 'Nd', None, None, None, None, None],
    ['Np', 'Pm', None, None, None, None, None],
    ['Pu', 'Sm', None, None, None, None, None],
    ['Am', 'Eu', None, None, None, None, None],
    ['Cm', 'Gd', None, None, None, None, None],
    ['Bk', 'Tb', None, None, None, None, None],
    ['Cf', 'Dy', None, None, None, None, None],
    ['Es', 'Ho', None, None, None, None, None],
    ['Fm', 'Er', None, None, None, None, None],
    ['Md', 'Tm', None, None, None, None, None],
    ['No', 'Yb', None, None, None, None, None],
    ['Lr', 'Lu', 'Y', 'Sc', None, None, None],
    ['Rf', 'Hf', 'Zr', 'Ti', None, None, None],
    ['Db', 'Ta', 'Nb', 'V', None, None, None],
    ['Sg', 'W', 'Mo', 'Cr', None, None, None],
    ['Bh', 'Re', 'Tc', 'Mn', None, None, None],
    ['Hs', 'Os', 'Ru', 'Fe', None, None, None],
    ['Mt', 'Ir', 'Rh', 'Co', None, None, None],
    ['Ds', 'Pt', 'Pd', 'Ni', None, None, None],
    ['Rg', 'Au', 'Ag', 'Cu', None, None, None],
    ['Cn', 'Hg', 'Cd', 'Zn', None, None, None],
    [None, 'Tl', 'In', 'Ga', 'Al', 'B', None],
    [None, 'Pb', 'Sn', 'Ge', 'Si', 'C', None],
    [None, 'Bi', 'Sb', 'As', 'P', 'N', None],
    [None, 'Po', 'Te', 'Se', 'S', 'O', None],
    [None, 'At', 'I', 'Br', 'Cl', 'F', None],
    [None, 'Rn', 'Xe', 'Kr', 'Ar', 'Ne', 'He'],
    ]

VAR_TAG_ORDER = {'neutral' : 0,
                 'prot'    : 0,
                 'deprot'  : 1,
                 'link'    : 2,
                 'stereo_1': 3,
                 'stereo_2': 3}

LINKS = [('Previous residue', 'prev', 'link-prev.png'),
         ('Next residue', 'next', 'link-next.png'),
         ('Generic link', 'link', 'link.png')]
LINK = 'link'

DISALLOWED = [set([LINK, LINK]),
              set(['H', 'H']),
              set(['H', LINK])]

HIGHLIGHT = QtGui.QColor(10, 250, 0, 255)
HIGHLIGHT_BG = QtGui.QColor(10, 250, 0, 64)
ATOM_NAME_FG = QtGui.QColor(255, 255, 255, 128)
LINK_COLOR = QtGui.QColor(50, 200, 50, 128)
EQUIV_COLOR = QtGui.QColor(255, 128, 128, 128)
PROCHIRAL_COLOR = QtGui.QColor(128, 192, 255, 128)
ELEMENT_FONT = QtGui.QFont("DejaVu Sans Mono", 9)
ELEMENT_DATA = {
    LINK: (1, LINK_COLOR),
    # element: (default valances, colour, (common valances))
    'C' : (4, QtGui.QColor(180, 180, 180, 255), (4,)),
    'N' : (3, QtGui.QColor(110, 110, 255, 255), (3,)),
    'H' : (1, QtGui.QColor(255, 255, 255, 255), (1,)),
    'O' : (2, QtGui.QColor(255, 80, 80, 255), (2,)),
    'P' : (5, QtGui.QColor(255, 80, 255, 255), (5,)),
    'S' : (2, QtGui.QColor(255, 180, 50, 255), (2, 4, 6)),
    'Se': (2, QtGui.QColor(255, 100, 50, 255), (2,)),
    'F' : (1, QtGui.QColor(255, 255, 128, 255), (1,)),
    'Cl': (1, QtGui.QColor(128, 255, 80, 255), (1,)),
    'Br': (1, QtGui.QColor(255, 128, 80, 255), (1,)),
    'I' : (1, QtGui.QColor(150, 80, 255, 255), (1,)),
    'B' : (3, QtGui.QColor(120, 120, 80, 255), (3,)),
    'Si': (4, QtGui.QColor(200, 200, 255, 255), (4,)),
    'As': (3, QtGui.QColor(230, 80, 255, 255), (3,)),
    'Be': (2, QtGui.QColor(255, 255, 160, 255), (2,)),
    'Mg': (2, QtGui.QColor(255, 255, 160, 255), (0, 2,)),
    'Al': (3, QtGui.QColor(200, 200, 255, 255), (0, 3,)),
    'Fe': (0, QtGui.QColor(160, 160, 255, 255), (0,)),
    '?' : (3, QtGui.QColor(160, 160, 255, 255), (1, 2, 3, 4)), }

PERIODIC_TABLE_COLORS = (QtGui.QColor(255, 160, 160, 255),
                         QtGui.QColor(255, 255, 160, 255),
                         QtGui.QColor(160, 255, 160, 255),
                         QtGui.QColor(160, 160, 255, 255),
                         QtGui.QColor(200, 200, 255, 255),
                         QtGui.QColor(255, 160, 255, 255))

for row, group in enumerate(PERIODIC_TABLE):
    for elem in group:
        if elem not in ELEMENT_DATA:
            if row == 0:
                color = PERIODIC_TABLE_COLORS[0]

            elif row == 1:
                color = PERIODIC_TABLE_COLORS[1]

            elif row < 16:
                color = PERIODIC_TABLE_COLORS[2]

            elif row < 26:
                color = PERIODIC_TABLE_COLORS[3]

            elif row < 30:
                color = PERIODIC_TABLE_COLORS[4]

            else:
                color = PERIODIC_TABLE_COLORS[5]

            ELEMENT_DATA[elem] = (0, color, (0,))

# Constants

ELEMENT_DEFAULT = (0, QtGui.QColor(160, 160, 255, 255), (1,))

# Other oxidation states? Coordination

ATOM = 'atom'
PROPERTY = 'property'
PROPERTIES_ATOM = [
    ('Bonding', (('Toggle aromatic ring', 'toggle-aromatic.png', 'bond-aromatic'),
                 ('Toggle dative bond', 'bond-dative.png', 'bond-dative'))),
    ('Atomic Charge', (('Add positive charge', 'charge-pos.png', '+'),
                       ('Set neutral charge', 'charge-none.png', '0'),
                       ('Add negative charge', 'charge-neg.png', '-'))),
    ('Valence Slots', (('Add valance', 'valence-add.png', 'v+'),
                       ('Remove valance', 'valence-remove.png', 'v-'))),
    ('Stereochemistry', (('Toggle stereo centre', 'stereo.png', 'st'),
                         ('Move atom forward', 'stereo-up.png', 'st+'),
                         ('Move atom backward', 'stereo-down.png', 'st-'))),
    ('Chirality Label', (('R chirality', 'stereo-R.png', 'chiral-r'),
                         ('S chirality', 'stereo-S.png', 'chiral-s'),
                         ('No chirality label', 'stereo-none.png', 'chiral-n'),
                         ('Alpha chirality', 'stereo-a.png', 'chiral-a'),
                         ('Beta chirality', 'stereo-b.png', 'chiral-b'),
                         )), ]  # ('R/S', None, 'chiral-rs'),
PROPERTIES_MULTI = [
    ('Atomic Exchange', (('Toggle variable atom', 'variable-atom.png', 'xv'),
                         ('Toggle fast exchange (H+)', 'exchange-hydrogen.png', 'xf'))),
    ('NMR Groups', (('NMR equivalent', 'nmr-equivalent.png', 'e'),
                    ('NMR non-stereo (e.g. prochiral)', 'nmr-prochiral.png', 'p'),
                    ('No atom group', 'nmr-no-group.png', 'u'))),
    ]
CHARGE_FONT = QtGui.QFont("DejaVu Sans Mono", 11, QtGui.QFont.Bold)
NEG_COLOR = QtGui.QColor(255, 40, 40, 255)
POS_COLOR = QtGui.QColor(40, 40, 255, 255)
CHARGE_BG_COLOR = QtGui.QColor(255, 255, 255, 128)
CHIRAL_FONT = QtGui.QFont("DejaVu Sans Mono", 7, QtGui.QFont.Bold)
CHIRAL_COLOR = QtGui.QColor(255, 255, 0, 255)

ELEMENT_ISO_ABUN = {
    'Ac': ((0.0, 227, 227.0277470),),
    'Ag': ((0.518390, 107, 106.9050930), (0.481610, 109, 108.9047560),),
    'Al': ((1.0, 27, 26.9815384),),
    'Am': ((0.0, 243, 243.0613727), (0.0, 241, 241.0568229),),
    'Ar': ((0.996003, 40, 39.9623831), (0.003365, 36, 35.9675463), (0.000632, 38, 37.9627322),),
    'As': ((1.0, 75, 74.9215964),),
    'At': ((0.0, 211, 210.9874810), (0.0, 210, 209.9871310),),
    'Au': ((1.0, 197, 196.9665520),),
    'B' : ((0.801000, 11, 11.0093055), (0.199000, 10, 10.0129370),),
    'Ba': ((0.716980, 138, 137.9052410), (0.112320, 137, 136.9058210), (0.078540, 136, 135.9045700),
           (0.065920, 135, 134.9056830), (0.024170, 134, 133.9045030), (0.001060, 130, 129.9063100),
           (0.001010, 132, 131.9050560),),
    'Be': ((1.0, 9, 9.0121821),),
    'Bh': ((0.0, 264, 258.0984250),),
    'Bi': ((1.0, 209, 208.9803830),),
    'Bk': ((0.0, 249, 249.0749800), (0.0, 247, 247.0702990),),
    'Br': ((0.506900, 79, 78.9183376), (0.493100, 81, 80.9162910),),
    'C' : ((0.989300, 12, 12.0000000), (0.010700, 13, 13.0033548), (0.0, 14, 14.0032420),),
    'Ca': ((0.969410, 40, 39.9625912), (0.020860, 44, 43.9554811), (0.006470, 42, 41.9586183),
           (0.001870, 48, 47.9525340), (0.001350, 43, 42.9587668), (0.000040, 46, 45.9536928),),
    'Cd': ((0.287300, 114, 113.9033581), (0.241300, 112, 111.9027572), (0.128000, 111, 110.9041820),
           (0.124900, 110, 109.9030060), (0.122200, 113, 112.9044009), (0.074900, 116, 115.9047550),
           (0.012500, 106, 105.9064580), (0.008900, 108, 107.9041830),),
    'Ce': ((0.884500, 140, 139.9054340), (0.111140, 142, 141.9092400), (0.002510, 138, 137.9059860),
           (0.001850, 136, 135.9071400),),
    'Cf': ((0.0, 252, 252.0816200), (0.0, 251, 251.0795800), (0.0, 250, 250.0764000),
           (0.0, 249, 249.0748470),),
    'Cl': ((0.757800, 35, 34.9688527), (0.242200, 37, 36.9659026),),
    'Cm': ((0.0, 248, 248.0723420), (0.0, 247, 247.0703470), (0.0, 246, 246.0672176),
           (0.0, 245, 245.0654856), (0.0, 244, 244.0627463), (0.0, 243, 243.0613822),),
    'Co': ((1.0, 59, 58.9332002),),
    'Cr': ((0.837890, 52, 51.9405119), (0.095010, 53, 52.9406538), (0.043450, 50, 49.9460496),
           (0.023650, 54, 53.9388849),),
    'Cs': ((1.0, 133, 132.9054470),),
    'Cu': ((0.691700, 63, 62.9296011), (0.308300, 65, 64.9277937),),
    'Db': ((0.0, 262, 258.0984250),),
    'Dy': ((0.281800, 164, 163.9291710), (0.255100, 162, 161.9267950), (0.249000, 163, 162.9287280),
           (0.189100, 161, 160.9269300), (0.023400, 160, 159.9251940), (0.001000, 158, 157.9244050),
           (0.000600, 156, 155.9242780),),
    'Er': ((0.336100, 166, 165.9302900), (0.267800, 168, 167.9323680), (0.229300, 167, 166.9320450),
           (0.149300, 170, 169.9354600), (0.016100, 164, 163.9291970), (0.001400, 162, 161.9287750),),
    'Es': ((0.0, 252, 252.0829700),),
    'Eu': ((0.521900, 153, 152.9212260), (0.478100, 151, 150.9198460),),
    'F' : ((1.0, 19, 18.9984032),),
    'Fe': ((0.917540, 56, 55.9349421), (0.058450, 54, 53.9396148), (0.021190, 57, 56.9353987),
           (0.002820, 58, 57.9332805),),
    'Fm': ((0.0, 257, 257.0950990),),
    'Fr': ((0.0, 223, 223.0197307),),
    'Ga': ((0.601080, 69, 68.9255810), (0.398920, 71, 70.9247050),),
    'Gd': ((0.248400, 158, 157.9241010), (0.218600, 160, 159.9270510), (0.204700, 156, 155.9221200),
           (0.156500, 157, 156.9239570), (0.148000, 155, 154.9226190), (0.021800, 154, 153.9208620),
           (0.002000, 152, 151.9197880),),
    'Ge': ((0.362800, 74, 73.9211782), (0.275400, 72, 71.9220762), (0.208400, 70, 69.9242504),
           (0.077300, 73, 72.9234594), (0.076100, 76, 75.9214027),),
    'H' : ((0.999850, 1, 1.0078250), (0.000150, 2, 2.0141018), (0.0, 3, 3.0160492),),
    'He': ((0.999999, 4, 4.0026032), (0.000001, 3, 3.0160293),),
    'Hf': ((0.350800, 180, 179.9465488), (0.272800, 178, 177.9436977), (0.186000, 177, 176.9432200),
           (0.136200, 179, 178.9458151), (0.052600, 176, 175.9414018), (0.001600, 174, 173.9400400),),
    'Hg': ((0.298600, 202, 201.9706260), (0.231000, 200, 199.9683090), (0.168700, 199, 198.9682620),
           (0.131800, 201, 200.9702850), (0.099700, 198, 197.9667520), (0.068700, 204, 203.9734760),
           (0.001500, 196, 195.9658150),),
    'Ho': ((1.0, 165, 164.9303190),),
    'Hs': ((0.0, 277, 258.0984250),),
    'I' : ((1.0, 127, 126.9044680),),
    'In': ((0.957100, 115, 114.9038780), (0.042900, 113, 112.9040610),),
    'Ir': ((0.627000, 193, 192.9629240), (0.373000, 191, 190.9605910),),
    'K' : ((0.932581, 39, 38.9637069), (0.067302, 41, 40.9618260), (0.000117, 40, 39.9639987),),
    'Kr': ((0.570000, 84, 83.9115070), (0.173000, 86, 85.9106103), (0.115800, 82, 81.9134846),
           (0.114900, 83, 82.9141360), (0.022800, 80, 79.9163780), (0.003500, 78, 77.9203860),),
    'La': ((0.999100, 139, 138.9063480), (0.000900, 138, 137.9071070),),
    'Li': ((0.924100, 7, 7.0160040), (0.075900, 6, 6.0151223),),
    'Lr': ((0.0, 262, 258.0984250),),
    'Lu': ((0.974100, 175, 174.9407679), (0.025900, 176, 175.9426824),),
    'Md': ((0.0, 258, 258.0984250), (0.0, 256, 256.0940500),),
    'Mg': ((0.789900, 24, 23.9850419), (0.110100, 26, 25.9825930), (0.100000, 25, 24.9858370),),
    'Mn': ((1.0, 55, 54.9380496),),
    'Mo': ((0.241300, 98, 97.9054078), (0.166800, 96, 95.9046789), (0.159200, 95, 94.9058415),
           (0.148400, 92, 91.9068100), (0.096300, 100, 99.9074770), (0.095500, 97, 96.9060210),
           (0.092500, 94, 93.9050876),),
    'Mt': ((0.0, 268, 258.0984250),),
    'N' : ((0.996320, 14, 14.0030740), (0.003680, 15, 15.0001089),),
    'Na': ((1.0, 23, 22.9897697),),
    'Nb': ((1.0, 93, 92.9063775),),
    'Nd': ((0.272000, 142, 141.9077190), (0.238000, 144, 143.9100830), (0.172000, 146, 145.9131120),
           (0.122000, 143, 142.9098100), (0.083000, 145, 144.9125690), (0.057000, 148, 147.9168890),
           (0.056000, 150, 149.9208870),),
    'Ne': ((0.904800, 20, 19.9924402), (0.092500, 22, 21.9913855), (0.002700, 21, 20.9938467),),
    'Ni': ((0.680769, 58, 57.9353479), (0.262231, 60, 59.9307906), (0.036345, 62, 61.9283488),
           (0.011399, 61, 60.9310604), (0.009256, 64, 63.9279696),),
    'No': ((0.0, 259, 258.0984250),),
    'Np': ((0.0, 239, 239.0529314), (0.0, 237, 237.0481673),),
    'O' : ((0.997570, 16, 15.9949146), (0.002050, 18, 17.9991604), (0.000380, 17, 16.9991315),),
    'Os': ((0.407800, 192, 191.9614790), (0.262600, 190, 189.9584450), (0.161500, 189, 188.9581449),
           (0.132400, 188, 187.9558360), (0.019600, 187, 186.9557479), (0.015900, 186, 185.9538380),
           (0.000200, 184, 183.9524910),),
    'P' : ((1.0, 31, 30.9737615),),
    'Pa': ((1.0, 231, 231.0358789),),
    'Pb': ((0.524000, 208, 207.9766360), (0.241000, 206, 205.9744490), (0.221000, 207, 206.9758810),
           (0.014000, 204, 203.9730290),),
    'Pd': ((0.273300, 106, 105.9034830), (0.264600, 108, 107.9038940), (0.223300, 105, 104.9050840),
           (0.117200, 110, 109.9051520), (0.111400, 104, 103.9040350), (0.010200, 102, 101.9056080),),
    'Pm': ((0.0, 147, 146.9151340), (0.0, 145, 144.9127440),),
    'Po': ((0.0, 210, 209.9828570), (0.0, 209, 208.9824160),),
    'Pr': ((1.0, 141, 140.9076480),),
    'Pt': ((0.338320, 195, 194.9647740), (0.329670, 194, 193.9626640), (0.252420, 196, 195.9649350),
           (0.071630, 198, 197.9678760), (0.007820, 192, 191.9610350), (0.000140, 190, 189.9599300),),
    'Pu': ((0.0, 244, 244.0641980), (0.0, 242, 242.0587368), (0.0, 241, 241.0568453),
           (0.0, 240, 240.0538075), (0.0, 239, 239.0521565), (0.0, 238, 238.0495534),),
    'Ra': ((0.0, 228, 228.0310641), (0.0, 226, 226.0254026), (0.0, 224, 224.0202020),
           (0.0, 223, 223.0184970),),
    'Rb': ((0.721700, 85, 84.9117893), (0.278300, 87, 86.9091835),),
    'Re': ((0.626000, 187, 186.9557508), (0.374000, 185, 184.9529557),),
    'Rf': ((0.0, 261, 258.0984250),),
    'Rh': ((1.0, 103, 102.9055040),),
    'Rn': ((0.0, 222, 222.0175705), (0.0, 220, 220.0113841), (0.0, 211, 210.9905850),),
    'Ru': ((0.315500, 102, 101.9043495), (0.186200, 104, 103.9054300), (0.170600, 101, 100.9055822),
           (0.127600, 99, 98.9059393), (0.126000, 100, 99.9042197), (0.055400, 96, 95.9075980),
           (0.018700, 98, 97.9052870),),
    'S' : ((0.949300, 32, 31.9720707), (0.042900, 34, 33.9678668), (0.007600, 33, 32.9714585),
           (0.000200, 36, 35.9670809),),
    'Sb': ((0.572100, 121, 120.9038180), (0.427900, 123, 122.9042157),),
    'Sc': ((1.0, 45, 44.9559102),),
    'Se': ((0.496100, 80, 79.9165218), (0.237700, 78, 77.9173095), (0.093700, 76, 75.9192141),
           (0.087300, 82, 81.9167000), (0.076300, 77, 76.9199146), (0.008900, 74, 73.9224766),),
    'Sg': ((0.0, 266, 258.0984250),),
    'Si': ((0.922297, 28, 27.9769265), (0.046832, 29, 28.9764947), (0.030872, 30, 29.9737702),),
    'Sm': ((0.267500, 152, 151.9197280), (0.227500, 154, 153.9222050), (0.149900, 147, 146.9148930),
           (0.138200, 149, 148.9171800), (0.112400, 148, 147.9148180), (0.073800, 150, 149.9172710),
           (0.030700, 144, 143.9119950),),
    'Sn': ((0.325800, 120, 119.9021966), (0.242200, 118, 117.9016060), (0.145400, 116, 115.9017440),
           (0.085900, 119, 118.9033090), (0.076800, 117, 116.9029540), (0.057900, 124, 123.9052746),
           (0.046300, 122, 121.9034401), (0.009700, 112, 111.9048210), (0.006600, 114, 113.9027820),
           (0.003400, 115, 114.9033460),),
    'Sr': ((0.825800, 88, 87.9056143), (0.098600, 86, 85.9092624), (0.070000, 87, 86.9088793),
           (0.005600, 84, 83.9134250),),
    'Ta': ((0.999880, 181, 180.9479960), (0.000120, 180, 179.9474660),),
    'Tb': ((1.0, 159, 158.9253430),),
    'Tc': ((0.0, 99, 98.9062546), (0.0, 98, 97.9072160), (0.0, 97, 96.9063650),),
    'Te': ((0.340800, 130, 129.9062228), (0.317400, 128, 127.9044614), (0.188400, 126, 125.9033055),
           (0.070700, 125, 124.9044247), (0.047400, 124, 123.9028195), (0.025500, 122, 121.9030471),
           (0.008900, 123, 122.9042730), (0.000900, 120, 119.9040200),),
    'Th': ((1.0, 232, 232.0380504), (0.0, 230, 230.0331266),),
    'Ti': ((0.737200, 48, 47.9479471), (0.082500, 46, 45.9526295), (0.074400, 47, 46.9517638),
           (0.054100, 49, 48.9478708), (0.051800, 50, 49.9447921),),
    'Tl': ((0.704760, 205, 204.9744120), (0.295240, 203, 202.9723290),),
    'Tm': ((1.0, 169, 168.9342110),),
    'U' : ((0.992745, 238, 238.0507826), (0.007200, 235, 235.0439231), (0.000055, 234, 234.0409456),
           (0.0, 236, 236.0455619), (0.0, 233, 233.0396280),),
    'V' : ((0.997500, 51, 50.9439637), (0.002500, 50, 49.9471628),),
    'W' : ((0.306400, 184, 183.9509326), (0.284300, 186, 185.9543620), (0.265000, 182, 181.9482060),
           (0.143100, 183, 182.9502245), (0.001200, 180, 179.9467060),),
    'Xe': ((0.268900, 132, 131.9041545), (0.264400, 129, 128.9047795), (0.211800, 131, 130.9050819),
           (0.104400, 134, 133.9053945), (0.088700, 136, 135.9072200), (0.040800, 130, 129.9035079),
           (0.019200, 128, 127.9035304), (0.000900, 126, 125.9042690), (0.000900, 124, 123.9058958),),
    'Y' : ((1.0, 89, 88.9058479),),
    'Yb': ((0.318300, 174, 173.9388581), (0.218300, 172, 171.9363777), (0.161300, 173, 172.9382068),
           (0.142800, 171, 170.9363220), (0.127600, 176, 175.9425680), (0.030400, 170, 169.9347590),
           (0.001300, 168, 167.9338940),),
    'Zn': ((0.486300, 64, 63.9291466), (0.279000, 66, 65.9260368), (0.187500, 68, 67.9248476),
           (0.041000, 67, 66.9271309), (0.006200, 70, 69.9253250),),
    'Zr': ((0.514500, 90, 89.9047037), (0.173800, 94, 93.9063158), (0.171500, 92, 91.9050401),
           (0.112200, 91, 90.9056450), (0.028000, 96, 95.9082760),),
    }

Qt = QtCore.Qt
QPointF = QtCore.QPointF
QRectF = QtCore.QRectF

RADIUS = 50.0
BOND_SEP = 3.0
NULL_RECT = QRectF()
NULL_POINT = QPointF()
FONT_METRIC = QtGui.QFontMetricsF(ELEMENT_FONT)

SHADOW_COLOR = QtGui.QColor(64, 64, 64)
SHADOW_RADIUS = 4
SHADOW_OFFSET = (2, 2)

AURA_COLOR = QtGui.QColor(255, 255, 255)
AURA_OFFSET = (0, 0)
AURA_RADIUS = 4

ItemIsMovable = QtWidgets.QGraphicsItem.ItemIsMovable
ItemIsSelectable = QtWidgets.QGraphicsItem.ItemIsSelectable
ItemPositionChange = QtWidgets.QGraphicsItem.ItemPositionChange
ItemSendsGeometryChanges = QtWidgets.QGraphicsItem.ItemSendsGeometryChanges

REGION_PEN = QtGui.QPen(HIGHLIGHT, 0.8, Qt.SolidLine)

BOND_CHANGE_DICT = {'single'      : 'double',
                    'aromatic'    : 'double',
                    'singleplanar': 'double',
                    'double'      : 'triple',
                    'triple'      : 'single',
                    'dative'      : 'single'}


class AtomLabel(QtWidgets.QGraphicsItem):

    def __init__(self, scene, atomView, compoundView, atom):
        super(AtomLabel, self).__init__()

        # QtWidgets.QGraphicsItem.__init__(self)
        self._scene = scene

        #effect = QtWidgets.QGraphicsDropShadowEffect(compoundView)
        #effect.setBlurRadius(SHADOW_RADIUS)
        #effect.setColor(SHADOW_COLOR)
        #effect.setOffset(*SHADOW_OFFSET)

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        #self.setGraphicsEffect(effect)
        self.setZValue(3)
        self.compoundView = compoundView
        self.atomView = atomView
        self.hover = False
        self.atom = atom
        self.bbox = NULL_RECT
        self.drawData = ()
        self.syncLabel()
        self.setCacheMode(self.DeviceCoordinateCache)

    def hoverEnterEvent(self, event):

        self.hover = True
        self.update()

    def hoverLeaveEvent(self, event):

        self.hover = False
        self.update()

    def mouseDoubleClickEvent(self, event):

        if self.atom.element == LINK:
            return

        self.compoundView.queryAtomName(self)

        return QtWidgets.QGraphicsItem.mouseDoubleClickEvent(self, event)

    def syncLabel(self):

        rad = 15.0

        atom = self.atom
        xa, ya, za = atom.coords

        if atom.bonds or atom.freeValences:

            angles = atom.getBondAngles()
            angles += atom.freeValences
            angles = [a % (2.0 * PI) for a in angles]
            angles.sort()
            angles.append(angles[0] + 2.0 * PI)
            diffs = [(round(angles[i + 1] - a, 3), a)
                     for i, a in enumerate(angles[:-1])]
            diffs.sort()

            delta, angle = diffs[-1]
            angle += delta / 2.0

        else:
            angle = 1.0

        name = atom.name
        if name:
            text = name
        else:
            text = '?'

        textRect = FONT_METRIC.tightBoundingRect(text)
        w = textRect.width() / 1.5
        h = textRect.height() / 2.0

        x = xa + (rad + w) * sin(angle)
        y = ya + (rad + h) * cos(angle)

        # Global absolute centre
        self.setPos(QPointF(x, y))

        center = QPointF(-w, h)
        self.drawData = (center, text)
        rect = QRectF(QPointF(-w, -h),
                      QPointF(w, h))
        self.bbox = rect.adjusted(-h, -h, h, h)

        self.update()

    def boundingRect(self):

        if not self.compoundView.nameAtoms:
            return NULL_RECT
        return self.bbox

    def paint(self, painter, option, widget):

        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        #if self.compoundView.showSkeletalFormula and self.atom.element == 'H':
        #for n in self.atom.neighbours:
        #if n.element != 'C':
        #return

        # paint the floating text - needs to match the theme

        useName = self.compoundView.nameAtoms

        if useName and self.drawData:
            point, text = self.drawData

            painter.setFont(ELEMENT_FONT)
            if self.hover:
                painter.setPen(Qt.white)
            elif not isinstance(self.compoundView, QtWidgets.QGraphicsItem):
                if hasattr(self.compoundView, 'setAtomColorWhite'):
                    painter.setPen(Qt.white)
                else:
                    painter.setPen(QtGui.QPalette().windowText().color())

            painter.drawText(point, text)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)


class SelectionBox(QtWidgets.QGraphicsItem):

    def __init__(self, scene, compoundView):
        super().__init__()
        # QtWidgets.QGraphicsItem.__init__(self)
        # self._scene = scene
        # print(self.scene(), scene, 'TEST')

        self.setZValue(1)
        self.compoundView = compoundView
        self.begin = None
        self.region = None

    def updateRegion(self, begin=None, end=None):

        if begin and end:
            self.region = QRectF(begin, end).normalized()
            self.begin = begin

        elif begin:
            self.region = QRectF(begin, begin).normalized()
            self.begin = begin

        elif end and self.begin:
            self.region = QRectF(self.begin, end).normalized()

        else:
            self.region = None
            self.begin = None

        self.update()

    def boundingRect(self):

        if self.region:
            pad = 2
            return self.region.adjusted(-pad, -pad, pad, pad)

        else:
            return NULL_RECT

    def paint(self, painter, option, widget):

        if self.region:
            painter.setPen(REGION_PEN)
            painter.setBrush(HIGHLIGHT_BG)
            painter.drawRect(self.region)


class AtomGroupItem(QtWidgets.QGraphicsItem):

    def __init__(self, scene, compoundView, atomGroup):
        super(AtomGroupItem, self).__init__()
        # QtWidgets.QGraphicsItem.__init__(self)
        self._scene = scene

        compoundView.groupItems[atomGroup] = self

        self.compoundView = compoundView
        self.atomGroup = atomGroup
        self.atoms = atomGroup.varAtoms
        self.setZValue(-1)
        self.bbox = NULL_RECT
        self.drawData = ()
        self.center = NULL_POINT
        self.syncGroup()
        self.setCacheMode(self.DeviceCoordinateCache)

    def boundingRect(self):
        return self.bbox

    def paint(self, painter, option, widget):
        pass


class EquivItem(AtomGroupItem):

    def syncGroup(self):

        coords = [a.coords for a in self.atoms]
        n = float(len(coords))

        xl = [xyz[0] for xyz in coords]
        yl = [xyz[1] for xyz in coords]

        xc = sum(xl) / n
        yc = sum(yl) / n

        xa = min(xl)
        ya = min(yl)

        xb = max(xl)
        yb = max(yl)

        dx = xb - xa
        dy = yb - ya

        self.center = QPointF(xc - xa, yc - ya)

        self.drawData = [QPointF(xyz[0] - xa, xyz[1] - ya) for xyz in coords]

        self.setPos(QPointF(xa, ya))

        rect = QRectF(QPointF(0.0, 0.0),
                      QPointF(dx, dy))

        pad = 2
        self.bbox = rect.normalized().adjusted(-pad, -pad, pad, pad)

        self.update()

    def paint(self, painter, option, widget):

        if not self.compoundView.showGroups:
            return

        pen = QtGui.QPen(EQUIV_COLOR, 2, Qt.DotLine)
        painter.setPen(pen)
        painter.setBrush(EQUIV_COLOR)

        center = self.center
        for point in self.drawData:
            painter.drawLine(point, center)

        pen = QtGui.QPen(EQUIV_COLOR, 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawEllipse(center, 2.0, 2.0)


class ProchiralItem(AtomGroupItem):

    def syncGroup(self):

        atoms = self.atoms

        if len(atoms) == 2:
            atomA, atomB = atoms

            x1, y1, z1 = atomA.coords
            x2, y2, z2 = atomB.coords

            dx = x2 - x1
            dy = y2 - y1

            anchorPoint = QPointF(x1, y1)
            startPoint = QPointF(0.0, 0.0)
            endPoint = QPointF(dx, dy)

        else:
            groupDict = self.compoundView.groupItems

            groups = list(self.atomGroup.subGroups)

            if len(groups) == 2:
                groupA = groups[0]
                groupB = groups[1]

                gItemA = groupDict.get(groupA)
                gItemB = groupDict.get(groupB)

                if gItemA and gItemB:

                    centerA = gItemA.center
                    centerB = gItemB.center

                    anchorPoint = centerA
                    startPoint = self.mapFromItem(gItemA, centerA)
                    endPoint = self.mapFromItem(gItemB, centerB)

                else:
                    self.drawData = None
                    return

            else:
                self.drawData = None
                return

        pad = 2.0
        rect = QRectF(startPoint, endPoint)
        self.center = rect.center()
        self.bbox = rect.normalized().adjusted(-pad, -pad, pad, pad)
        self.drawData = (startPoint, endPoint)
        self.setPos(anchorPoint)
        self.update()

    def paint(self, painter, option, widget):

        if not self.compoundView.showGroups:
            return

        if self.drawData:
            startPoint, endPoint = self.drawData

            pen = QtGui.QPen(PROCHIRAL_COLOR, 2, Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(startPoint, endPoint)


class AromaticItem(AtomGroupItem):

    def syncGroup(self):
        coords = [a.coords for a in self.atoms]

        n = len(coords)
        nl = range(n)
        n = float(n)

        xl = [xyz[0] for xyz in coords]
        yl = [xyz[1] for xyz in coords]

        xc = sum(xl) / n
        yc = sum(yl) / n

        xa = min(xl)
        ya = min(yl)

        xb = max(xl)
        yb = max(yl)

        dx = xb - xa
        dy = yb - ya

        dx2 = [(x - xc) * (x - xc) for x in xl]
        dy2 = [(y - yc) * (y - yc) for y in yl]

        d2 = [dx2[i] + dy2[i] for i in nl]

        r = sqrt(min(d2)) * cos(PI / n)

        r = max(2 * BOND_SEP, r - 2 * BOND_SEP)

        self.center = QPointF(xc - xa, yc - ya)

        self.drawData = [r, r]

        self.setPos(QPointF(xa, ya))

        rect = QRectF(QPointF(0.0, 0.0),
                      QPointF(dx, dy))

        pad = 2
        self.bbox = rect.normalized().adjusted(-pad, -pad, pad, pad)

        self.update()

    def paint(self, painter, option, widget):
        r1, r2 = self.drawData
        center = self.center

        pen = QtGui.QPen(QtGui.QPalette().windowText().color(), 1, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawEllipse(center, r1, r2)


class AtomItem(QtWidgets.QGraphicsItem):

    def __init__(self, scene, compoundView, atom):
        super(AtomItem, self).__init__()

        # QtWidgets.QGraphicsItem.__init__(self)
        self._scene = scene

        compoundView.atomViews[atom] = self

        self.compoundView = compoundView
        self.variant = atom.variant
        self.atom = atom
        self.bondItems = []
        self.bbox = NULL_RECT

        self.setFlag(ItemIsSelectable)
        self.selected = False
        self.setFlag(ItemIsMovable)
        self.setFlag(ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        color = ELEMENT_DATA.get(atom.element, ELEMENT_DEFAULT)[1]
        self.gradient = QtGui.QRadialGradient(0, 0, 9, 4, -4)
        self.gradient.setColorAt(1, color.darker())
        self.gradient.setColorAt(0.5, color)
        self.gradient.setColorAt(0, color.lighter())
        self.gradient2 = QtGui.QRadialGradient(0, 0, 9, 4, -4)
        self.gradient2.setColorAt(1, color.darker().darker())
        self.gradient2.setColorAt(0.5, color.darker())
        self.gradient2.setColorAt(0, color)
        #effect = QtWidgets.QGraphicsDropShadowEffect(compoundView)
        #effect.setBlurRadius(SHADOW_RADIUS)
        #effect.setColor(SHADOW_COLOR)
        #effect.setOffset(*SHADOW_OFFSET)

        #self.setGraphicsEffect(effect)
        self.setCacheMode(self.DeviceCoordinateCache)

        self.highlights = set()
        self.makeBonds = set()
        self.hover = False
        self.rightBond = False
        self.freeDrag = False

        self.atomLabel = AtomLabel(scene, self, compoundView, atom)
        compoundView.scene().addItem(self.atomLabel)

        self.syncToAtom()

    def itemChange(self, change, value):

        if change == ItemPositionChange:
            compoundView = self.compoundView
            x0, y0, z = self.atom.coords

            x = value.x()
            y = value.y()
            dx = x0 - x
            dy = y0 - y

            freeDrag = self.freeDrag

            nSelected = len(compoundView.selectedViews)

            # This code block is to handle position changes of branches when snapping to grid.
            # In practice it will allow two branches to swap places.
            if compoundView.snapToGrid and (dx != 0 or dy != 0) and nSelected <= 1:
                # Find which of the neighbouring atoms form the longest branch. A more proper check
                # to ensure the backbone is found could be done.
                # The shortest branch and the branch of the selected atom can be moved.
                neighbours = sorted(self.atom.neighbours, key=lambda atom: atom.name)
                prevAtom = None
                longestBranchLen = 0
                for neighbour in neighbours:
                    branch = self.atom.findAtomsInBranch(neighbour)
                    branchLen = len(branch)
                    if branchLen > longestBranchLen:
                        prevAtom = neighbour
                        longestBranch = branch
                        longestBranchLen = branchLen
                if prevAtom:
                    xP = prevAtom.coords[0]
                    yP = prevAtom.coords[1]
                    #        bondLength = hypot(x0 - xP, y0 - yP)
                    bondLength = 50  # TODO: A smarter way of setting the right bondlength
                    neighbours = sorted(prevAtom.neighbours, key=lambda atom: atom.name)
                    longestBranchLen = 0
                    # Find a reference atom next to prevAtom to calculate bond angles.
                    frozenNeighbour = None
                    for neighbour in neighbours:
                        if neighbour != self.atom and neighbour.element != 'H':
                            branch = prevAtom.findAtomsInBranch(neighbour)
                            branchLen = len(branch)
                            if branchLen > longestBranchLen:
                                longestBranch = branch
                                longestBranchLen = branchLen
                                frozenNeighbour = neighbour
                                prevAngle = round(degrees(prevAtom.getBondAngle(neighbour)), 0)

                    if frozenNeighbour:
                        neighbour = frozenNeighbour
                        atoms = neighbour.findAtomsInBranch(prevAtom) - set([prevAtom, self.atom])
                    else:
                        for neighbour in self.atom.neighbours:
                            if neighbour.element != 'H':
                                frozenNeighbour = prevAtom
                                prevAngle = 330
                                atoms = set([])
                                break

                    if not frozenNeighbour:
                        print("No frozenNeighbour", longestBranchLen)
                        prevAtom = None
                        freeDrag = True
                else:
                    freeDrag = True

                # If the item was selected and Ctrl is pressed when the item is moved the item does not count a selected. Let it be freely movable.
                # If there are more atoms selected also let them be freely movable.
                if self.selected and not freeDrag:
                    prefAngles = prevAtom.getPreferredBondAngles(prevAngle, None, atoms, False)
                    # If the dragged atom only has neighbours with hydrogens (i.e. the reference atom has no other visible atoms connected) add
                    # an extra possible angle.
                    if frozenNeighbour == prevAtom and prevAngle == 330:
                        prefAngles.append(0)

                    if len(prefAngles) < 2:  # or self.atom.atomInSameRing(prevAtom):
                        value.setX(x0)
                        value.setY(y0)
                        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

                    prevAngle = radians(prevAngle)
                    currAngle = (prevAtom.getBondAngle(self.atom) - prevAngle) % (2.0 * PI)
                    newAngle = (atan2(y - yP, x - xP) - prevAngle) % (2.0 * PI)

                    # Find which preferred angle is closest to the new angle.
                    bestAngle = None
                    bestDiff = None
                    for angle in prefAngles:
                        if angle < 0:
                            angle += 360
                        angle = radians(angle)
                        diff = abs(newAngle - angle)
                        if not bestAngle or diff < bestDiff:
                            bestAngle = angle
                            bestDiff = diff

                    # If the current angle is agreeing best just set the selection circle to where the atom is
                    # and return.
                    if abs(bestAngle - currAngle) < 0.001:
                        value.setX(x0)
                        value.setY(y0)
                        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

                    bestAngle += prevAngle
                    if self.atom.element == 'H':
                        x = xP + bondLength * 0.75 * cos(bestAngle)
                        y = yP + bondLength * 0.75 * sin(bestAngle)
                    else:
                        x = xP + bondLength * cos(bestAngle)
                        y = yP + bondLength * sin(bestAngle)

                self.atom.setCoords(x, y, z)

                if prevAtom and not self.atom.atomInSameRing(prevAtom):
                    # First snap the atoms in the same branch as the selected atom (these will not take the other branch into account when
                    # deciding their positions).
                    sameBranch = sorted(prevAtom.findAtomsInBranch(self.atom) - set([self.atom]))
                    atoms -= longestBranch
                    atoms = sorted(atoms, key=lambda atom: atom.name)
                    if len(sameBranch) > 0:
                        for atom in sameBranch:
                            if atom in atoms:
                                atoms.remove(atom)
                        self.variant.snapAtomsToGrid(sameBranch, self.atom, compoundView.showSkeletalFormula, bondLength=bondLength)

                    # Snap the second branch to the grid taking the first branch into account.
                    if len(atoms) > 0:
                        self.variant.snapAtomsToGrid(atoms, prevAtom, compoundView.showSkeletalFormula, bondLength=bondLength)

                self.compoundView.updateAll()

            # Synch positions
            # implicitly set bonds too
            else:
                self.atom.setCoords(x, y, z)

            # Make bond detection

            d = RADIUS
            # When using snapToGrid the distance between the atoms is so small that double and tripe bonds are created too easily if d2 is not made smaller.
            if compoundView.snapToGrid:
                d2 = d * 0.25
            else:
                d2 = d * 0.5
            r2 = 15
            atomViews = compoundView.atomViews
            self.makeBonds = set()

            addBond = self.makeBonds.add
            valencesS = self.atom.freeValences
            atoms = self.variant.varAtoms - set([self.atom])
            positionsS = [(x + r2 * sin(angle),
                           y + r2 * cos(angle), angle) for angle in valencesS]

            if valencesS:
                for atom in atoms:
                    valences = atom.freeValences

                    if not valences:
                        continue

                    atomView = atomViews.get(atom)
                    if not atomView:
                        continue

                    x1, y1, z1 = atom.coords

                    dx = x1 - x
                    dy = y1 - y
                    dist2 = (dx * dx) + (dy * dy)

                    # consider using items directly
                    if dist2 < d * d:

                        # Other atom
                        positions = [(x1 + r2 * sin(a),
                                      y1 + r2 * cos(a), a) for a in valences]

                        for x2, y2, a2 in positions:
                            for x3, y3, a3 in positionsS:
                                dx2 = x3 - x2
                                dy2 = y3 - y2

                                if (dx2 * dx2) + (dy2 * dy2) < (d2 * d2):
                                    atomView.highlights.add(a2)
                                    self.highlights.add(a3)
                                    addBond((atom, self.atom))

                    atomView.update()
                self.update()

            for bondItem in self.bondItems:
                bondItem.syncToBond()

            groupItems = compoundView.groupItems
            for group in self.atom.atomGroups:
                groupItems[group].syncGroup()

            self.atomLabel.syncLabel()

        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def moveAtom(self, coords):

        if isinstance(coords, tuple):
            (x, y) = coords

        else:
            x = coords.x()
            y = coords.y()

        z = self.atom.coords[2]
        self.atom.setCoords(float(x), float(y), z)
        self.syncToAtom()

    def syncToAtom(self):

        atom = self.atom
        compoundView = self.compoundView

        bondDict = compoundView.bondItems
        self.bondItems = [bondDict[bond] for bond in atom.bonds if bond in bondDict]

        if atom.chirality:
            r = 21.0
        elif atom.freeValences or abs(atom.charge) > 1:
            r = 18.0
        else:
            r = 15.0

        x, y, z = atom.coords

        # Global location
        coords = QPointF(x, y)

        # Define where local origin is in global
        self.setPos(coords)

        rightBond = 0
        leftBond = 0

        if abs(atom.charge) > 1 or atom.chirality:
            adj = 9
        else:
            adj = 0

        #if self.compoundView.showSkeletalFormula:
        #for neighbour in atom.neighbours:
        #nH = 0
        #if neighbour.element == 'H':
        #nH += 1

        #if atom.element != 'C' or atom.freeValences or atom.chirality:# or nH == 4:
        #for neighbour in atom.neighbours:
        #if neighbour.element == 'H':
        #continue
        #nX, nY, nZ = neighbour.coords
        #if nX > x:
        #dY = max(0.0001, abs(nY - y))
        #currD = 1/dY
        #if currD > rightBond:
        #rightBond = currD
        #elif nX < x:
        #dY = max(0.0001, abs(nY - y))
        #currD = 1/dY
        #if currD > rightBond:
        #leftBond = currD

        #adj += 9
        #if nH > 1:
        #adj += 9

        # In local coords
        if rightBond > leftBond:
            self.rightBond = True
            self.bbox = QRectF(QPointF(-r - adj, -r),
                               QPointF(r, r + adj))
        else:
            self.rightBond = False
            self.bbox = QRectF(QPointF(-r, -r),
                               QPointF(r + adj, r + adj))

        for bondItem in self.bondItems:
            bondItem.syncToBond()

        groupItems = compoundView.groupItems
        for group in atom.atomGroups:
            groupItems[group].syncGroup()

        if self.compoundView.autoChirality:
            atom.autoSetChirality()
            for neighbour in atom.neighbours:
                neighbour.autoSetChirality()

        self.atomLabel.syncLabel()
        self.update()

    def boundingRect(self):

        #if self.compoundView.showSkeletalFormula and self.atom.element == 'H':
        #return NULL_RECT
        return self.bbox

    def delete(self):

        compoundView = self.compoundView
        atom = self.atom
        self.deselect()

        # scene = compoundView.scene()

        for bondItem in list(self.bondItems):
            bondItem.delete()

        del compoundView.atomViews[atom]

        # Delete the master atom, not the var one
        masterAtom = atom.atom
        if not masterAtom.isDeleted:
            masterAtom.delete()

        del self.atomLabel
        del self

    def deselect(self):

        self.selected = False
        self.setSelected(False)
        selected = self.compoundView.selectedViews

        if self in selected:
            selected.remove(self)

        for bondItem in self.bondItems:
            bondItem.deselect()

        self.update()

    def select(self):

        self.selected = True
        self.setSelected(True)
        selected = self.compoundView.selectedViews
        selected.add(self)

        for bondItem in self.bondItems:
            atomItemA, atomItemB = bondItem.atomItems

            if atomItemA.selected and atomItemB.selected:
                bondItem.select()

        self.update()

    def hoverEnterEvent(self, event):

        self.hover = True
        self.update()

    def hoverLeaveEvent(self, event):

        self.hover = False
        self.update()

    def mousePressEvent(self, event):

        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

        selected = list(self.compoundView.selectedViews)

        mods = event.modifiers()
        button = event.button()
        haveCtrl = mods & Qt.CTRL
        haveShift = mods & Qt.SHIFT

        if haveCtrl or haveShift:
            if self.selected:
                self.deselect()
            else:
                self.select()

        elif not self.selected:
            for view in selected:
                view.deselect()
            self.select()

        self.update()

    def mouseMoveEvent(self, event):

        mods = event.modifiers()
        haveCtrl = mods & Qt.CTRL

        if haveCtrl:
            self.freeDrag = True
            if not self.selected:
                self.select()

        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

        self.freeDrag = False

    def mouseDoubleClickEvent(self, event):

        if self.atomLabel.hover:
            self.compoundView.queryAtomName(self.atomLabel)
            return

        mods = event.modifiers()
        button = event.button()
        haveCtrl = mods & Qt.CTRL
        haveShift = mods & Qt.SHIFT

        if haveCtrl or haveShift:
            if self.selected:
                self.deselect()
            else:
                self.select()

        else:
            nAtoms = 1
            nPrev = 0
            atoms = set([self.atom])

            while nAtoms != nPrev:
                nPrev = nAtoms
                for atom in list(atoms):
                    atoms.update(atom.neighbours)

                nAtoms = len(atoms)

            viewDict = self.compoundView.atomViews
            for atom in self.variant.varAtoms:
                atomView = viewDict[atom]
                if atom in atoms:
                    atomView.select()
                else:
                    atomView.deselect()

        self.update()

        QtWidgets.QGraphicsItem.mouseDoubleClickEvent(self, event)

    def mouseReleaseEvent(self, event):

        parent = self.compoundView
        atom = self.atom
        x, y, z = atom.coords

        if isinstance(parent, QtWidgets.QGraphicsItem):
            w = parent.boundingRect().width()
            h = parent.boundingRect().height()
        else:
            w = parent.width()
            h = parent.height()

        tl = parent.mapToScene(0, 0)
        br = parent.mapToScene(w, h)
        x1 = tl.x()
        x2 = br.x()
        y1 = tl.y()
        y2 = br.y()

        if x < x1 or y < y1 or x > x2 or y > y2:
            if not atom.neighbours:
                self.delete()

        else:
            d2 = RADIUS / 2.0
            z = atom.coords[2]
            atom.setCoords(float(x), float(y), z)

            atoms = set()
            for varAtomA, varAtomB in self.makeBonds:

                elemA = varAtomA.element
                elemB = varAtomB.element

                if not varAtomA.freeValences:
                    continue

                if not varAtomB.freeValences:
                    continue

                if set([elemA, elemB]) in DISALLOWED:
                    continue

                if varAtomA in varAtomB.neighbours:
                    bond = self.variant.getBond(varAtomA, varAtomB)
                    if varAtomA.freeValences and varAtomB.freeValences:
                        bond.setBondType(BOND_CHANGE_DICT[bond.bondType])
                else:
                    Bond((varAtomA, varAtomB), autoVar=True)

                atoms.add(varAtomA)
                atoms.add(varAtomB)

            #neighbourhood = set()
            #for atom in atoms:
            #  neighbourhood.update(atom.neighbours)

            #if atoms:
            #  #if atoms == neighbourhood:
            #  #  self.variant.minimise2d([atoms.pop(),])
            #  #else:
            #  self.variant.minimise2d([atom,])

            for bond in self.atom.bonds:
                atomA, atomB = bond.varAtoms

                if atomA is not atom:
                    atomA.updateValences()

                if atomB is not atom:
                    atomB.updateValences()

            self.atom.updateValences()

        if isinstance(parent, QtWidgets.QGraphicsItem):
            if parent.showSkeletalFormula:
                parent.alignMolecule()
            else:
                parent.alignMolecule(False)

        self.compoundView.updateAll()  # Render new objs

        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        self.update()

    def paint(self, painter, option, widget):

        textAlign = QtCore.Qt.AlignCenter
        qRect = QRectF
        qBrush = QtGui.QBrush
        qPoint = QPointF
        qPoly = QtGui.QPolygonF

        showChargeSymbols = self.compoundView.showChargeSymbols
        showChiralities = self.compoundView.showChiralities

        highlights = self.highlights
        atom = self.atom

        r = 9.0
        r2 = 15.0
        r3 = 3.0
        d = RADIUS
        d2 = d / 2.0

        elem = atom.element

        drawText = painter.drawText
        drawEllipse = painter.drawEllipse
        drawLine = painter.drawLine
        drawPoly = painter.drawPolygon

        foreCol = QtGui.QColor('#404040')
        painter.setPen(foreCol)
        painter.setFont(ELEMENT_FONT)

        color = ELEMENT_DATA.get(elem, ELEMENT_DEFAULT)[1]
        if isinstance(self.compoundView, QtWidgets.QGraphicsItem):
            # SpecView
            if self.compoundView.container:
                backgroundColor = QtGui.QColor(*self.glWidget._hexToRgba(self.compoundView.container.mainApp.colors[0]))
                foregroundColor = QtGui.QColor(*self.glWidget._hexToRgba(self.compoundView.container.mainApp.colors[1]))
            # Analysis
            elif self.compoundView.glWidget:
                raise NotImplementedError("Needs rewriting - analysisProfile does not exist")
                backgroundColor = QtGui.QColor()
                backgroundColor.setRgbF(*self.glWidget._hexToRgba(self.glWidget.spectrumWindow.analysisProfile.bgColor))
                foregroundColor = foreCol

            # Fallback alternative
            else:
                backgroundColor = Qt.gray
                foregroundColor = Qt.gray
        else:
            backgroundColor = self.compoundView.backgroundColor
            foregroundColor = Qt.blue

        if not self.compoundView.showSkeletalFormula:
            if self.hover:
                brush = qBrush(self.gradient2)
            else:
                brush = qBrush(self.gradient)

            brush.setStyle(Qt.RadialGradientPattern)

        else:
            brush = backgroundColor

        x, y, z = 0, 0, 0
        center = qPoint(x, y)

        painter.setBrush(foregroundColor)
        for angle in atom.freeValences:
            x2 = x + r2 * sin(angle)
            y2 = y + r2 * cos(angle)

            if angle in highlights:
                painter.setBrush(HIGHLIGHT)
                drawEllipse(qPoint(x2, y2), r3, r3)
                painter.setBrush(foregroundColor)
            else:
                drawEllipse(qPoint(x2, y2), r3, r3)

        if showChiralities and atom.chirality:
            if atom.bonds or atom.freeValences:

                angles = atom.getBondAngles()
                angles += atom.freeValences
                angles = [-(a - PI / 2.0) % (2.0 * PI) for a in angles]
                angles.sort()
                angles.append(angles[0] + 2.0 * PI)
                diffs = [(round(angles[i + 1] - a, 3), a)
                         for i, a in enumerate(angles[:-1])]
                diffs.sort()

                delta, angle = diffs[-1]
                angle += delta / 2.0

            else:
                angle = 0.0

        painter.setBrush(brush)
        if self.compoundView.showSkeletalFormula:

            skeletalColor = self.compoundView.showSkeletalFormulaColor
            #nH = 0
            #for neighbour in atom.neighbours:
            #if neighbour.element == 'H':
            #nH += 1

            nDouble = 0
            for bond in atom.bonds:
                if bond.bondType == 'double':
                    nDouble += 1

            #if elem == 'C' and len(atom.freeValences) == 0 and nH < 4 and nDouble < len(atom.bonds):
            if elem == 'C' and len(atom.freeValences) == 0 and nDouble < len(atom.bonds):
                transparent = QtGui.QColor(0, 0, 0, 0)
                painter.setPen(transparent)
                painter.setBrush(transparent)
                painter.drawEllipse(center, r, r)
                if self.selected:
                    painter.setPen(HIGHLIGHT)
                    drawEllipse(center, r + 1, r + 1)
                    painter.setBrush(brush)

                if showChiralities:
                    if atom.chirality and atom.chirality not in ('e', 'z', 'E', 'Z'):
                        painter.setFont(CHIRAL_FONT)

                        if skeletalColor:
                            painter.setPen(CHIRAL_COLOR)
                        else:
                            painter.setPen(foregroundColor)

                        chirality = atom.chirality

                        if chirality in ('r', 's'):
                            chirality = '(%s)' % chirality.upper()

                        fontMetric = QtGui.QFontMetricsF(painter.font())
                        width = fontMetric.width(chirality)
                        height = fontMetric.height()
                        chiralityX = x + (r + 1) * cos(angle) - width / 2
                        chiralityY = y + (r + 1) * sin(angle) + height / 2
                        drawText(qPoint(chiralityX, chiralityY), chirality)

                return

            #if elem == 'H':
            #for n in atom.neighbours:
            #if n.element != 'C':
            #return

            font = painter.font()
            smallFont = painter.font()
            font.setPointSizeF(font.pointSize() * 1.5)
            painter.setFont(font)
            fontMetric = QtGui.QFontMetricsF(painter.font())
            bbox = fontMetric.tightBoundingRect(elem)
            width = fontMetric.width(elem)
            hydrogenWidth = fontMetric.width('H')
            h2 = bbox.height() / 2.0
            w2 = bbox.width() / 2.0

            if not skeletalColor:
                if isinstance(self.compoundView, QtWidgets.QGraphicsItem):
                    # SpecView
                    if self.compoundView.container:
                        color = foregroundColor
                    # Analyis
                    elif self.compoundView.glWidget:
                        color = foregroundColor
                    # Fallback
                    else:
                        color = Qt.darkGray
                else:
                    color = Qt.darkGray

            if elem == LINK:
                angles = atom.getBondAngles() + atom.freeValences

                if angles:
                    startAngle = -1.0 * angles[0]
                    angles = [startAngle + (i * 2 * PI / 3.0) for i in (0, 1, 2)]

                    if self.selected:
                        painter.setPen(HIGHLIGHT)
                        poly = qPoly()
                        for angle in angles:
                            x2 = x + (r + 1) * sin(angle)
                            y2 = y - (r + 1) * cos(angle)
                            poly.append(qPoint(x2, y2))

                        drawPoly(poly)
                        painter.setPen(foregroundColor)

                    poly = qPoly()
                    for angle in angles:
                        x2 = x + r * sin(angle)
                        y2 = y - r * cos(angle)
                        poly.append(qPoint(x2, y2))

                    drawPoly(poly)

            else:
                if self.selected:
                    painter.setPen(HIGHLIGHT)
                    drawEllipse(center, r + 1, r + 1)

                painter.setPen(backgroundColor)
                drawEllipse(center, r, r)
                textPoint = qPoint(x - w2, y + h2)
                painter.setPen(color)
                drawText(textPoint, elem)
                #hydrogenText= hydrogenNr = None
                #if nH != 0:
                #hydrogenText = 'H'
                #if nH > 1:
                #hydrogenNr = "%d" % nH
                #if hydrogenText:
                #nrWidth = 0
                #if hydrogenNr:
                #painter.setFont(smallFont)
                #fontMetric = QtGui.QFontMetricsF(smallFont)
                #nrWidth = fontMetric.width(hydrogenNr)
                #if self.rightBond:
                #textPoint = qPoint(x-width/2-nrWidth, y+h2+bbox.height()/3)
                #else:
                #textPoint = qPoint(x+width/2+hydrogenWidth, y+h2+bbox.height()/3)
                #drawText(textPoint, hydrogenNr)
                #painter.setFont(font)
                #if self.rightBond:
                #textPoint = qPoint(x-width/2-nrWidth-hydrogenWidth, y+h2)
                #else:
                #textPoint = qPoint(x+width/2, y+h2)
                #drawText(textPoint, hydrogenText)

                if skeletalColor:
                    painter.setPen(foregroundColor)

                charge = atom.charge

                if showChiralities:
                    if atom.chirality and atom.chirality not in ('e', 'z', 'E', 'Z'):

                        painter.setFont(CHIRAL_FONT)
                        if skeletalColor:
                            painter.setPen(CHIRAL_COLOR)

                        chirality = atom.chirality
                        if chirality in ('r', 's'):
                            chirality = '(%s)' % chirality.upper()

                        fontMetric = QtGui.QFontMetricsF(painter.font())
                        width = fontMetric.width(chirality)
                        height = fontMetric.height()
                        chiralityX = x + (r + 1) * cos(angle) - width / 2
                        chiralityY = y + (r + 1) * sin(angle) + height / 2
                        drawText(qPoint(chiralityX, chiralityY), chirality)

                    #elif atom.stereo:
                    #  painter.setFont(CHIRAL_FONT)
                    #  painter.setPen(CHIRAL_COLOR)
                    #  drawText(qPoint(x+r, y+r+4), '*')

                if showChargeSymbols:
                    if charge:
                        painter.setFont(smallFont)

                        if charge == -1:
                            text = '-'
                            if skeletalColor:
                                color = NEG_COLOR

                        elif charge == 1:
                            if skeletalColor:
                                color = POS_COLOR
                            text = '+'

                        elif charge > 0:
                            if skeletalColor:
                                color = POS_COLOR
                            text = '%d+' % charge

                        else:
                            if skeletalColor:
                                color = NEG_COLOR
                            text = '%d-' % abs(charge)

                        if skeletalColor:
                            painter.setPen(CHARGE_BG_COLOR)
                        if self.rightBond:
                            painter.setPen(color)
                            drawText(qPoint(x - r - 3, y - r + 3), text)
                        else:
                            painter.setPen(color)
                            drawText(qPoint(x + r - 3, y - r + 3), text)

        else:

            fontMetric = QtGui.QFontMetricsF(painter.font())
            bbox = fontMetric.tightBoundingRect(elem)
            h2 = bbox.height() / 2.0
            w2 = bbox.width() / 2.0

            if elem == LINK:
                angles = atom.getBondAngles() + atom.freeValences

                if angles:
                    startAngle = -1.0 * angles[0]
                    angles = [startAngle + (i * 2 * PI / 3.0) for i in (0, 1, 2)]

                    if self.selected:
                        painter.setPen(HIGHLIGHT)
                        poly = qPoly()
                        for angle in angles:
                            x2 = x + (r + 1) * sin(angle)
                            y2 = y - (r + 1) * cos(angle)
                            poly.append(qPoint(x2, y2))

                        drawPoly(poly)
                        painter.setPen(foreCol)

                    poly = qPoly()
                    for angle in angles:
                        x2 = x + r * sin(angle)
                        y2 = y - r * cos(angle)
                        poly.append(qPoint(x2, y2))

                    drawPoly(poly)


            else:
                if self.selected:
                    painter.setPen(HIGHLIGHT)
                    drawEllipse(center, r + 1, r + 1)
                    painter.setPen(foreCol)

                drawEllipse(center, r, r)
                textPoint = qPoint(x - w2, y + h2)
                drawText(textPoint, elem)

                charge = atom.charge

                if showChiralities:
                    if atom.chirality and atom.chirality not in ('e', 'z', 'E', 'Z'):
                        painter.setFont(CHIRAL_FONT)
                        painter.setPen(CHIRAL_COLOR)
                        chirality = atom.chirality

                        if chirality in ('r', 's'):
                            chirality = '(%s)' % chirality.upper()

                        fontMetric = QtGui.QFontMetricsF(painter.font())
                        width = fontMetric.width(chirality)
                        height = fontMetric.height()
                        chiralityX = x + (r2 + 1) * cos(angle) - width / 2
                        chiralityY = y + (r2 + 1) * sin(angle) + height / 2
                        drawText(qPoint(chiralityX, chiralityY), chirality)

                    #elif atom.stereo:
                    #  painter.setFont(CHIRAL_FONT)
                    #  painter.setPen(CHIRAL_COLOR)
                    #  drawText(qPoint(x+r, y+r+4), '*')

                if showChargeSymbols:
                    if charge:

                        if charge == -1:
                            text = '-'
                            color = NEG_COLOR

                        elif charge == 1:
                            color = POS_COLOR
                            text = '+'

                        elif charge > 0:
                            color = POS_COLOR
                            text = '%d+' % charge

                        else:
                            color = NEG_COLOR
                            text = '%d-' % abs(charge)

                        painter.setFont(CHARGE_FONT)
                        painter.setPen(CHARGE_BG_COLOR)
                        drawText(qPoint(x + r - 2, y - r + 2), text)
                        drawText(qPoint(x + r - 4, y - r + 4), text)
                        drawText(qPoint(x + r - 2, y - r + 4), text)
                        drawText(qPoint(x + r - 4, y - r + 2), text)
                        painter.setPen(color)
                        drawText(qPoint(x + r - 3, y - r + 3), text)

        self.highlights = set()


class BondItem(QtWidgets.QGraphicsItem):

    def __init__(self, scene, compoundView, bond):
        super(BondItem, self).__init__()

        # QtWidgets.QGraphicsItem.__init__(self)
        self._scene = scene

        compoundView.bondItems[bond] = self

        effect = QtWidgets.QGraphicsDropShadowEffect(compoundView)
        effect.setBlurRadius(SHADOW_RADIUS)
        effect.setColor(SHADOW_COLOR)
        effect.setOffset(*SHADOW_OFFSET)

        #self.setGraphicsEffect(effect)
        #self.setFlag(ItemIsSelectable)
        #self.setFlag(ItemIsMovable)

        #self.setCacheMode(self.NoCache)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.selected = False
        self.setZValue(-2)

        self.compoundView = compoundView
        self.bond = bond
        self.atomItems = []
        self.setCacheMode(self.DeviceCoordinateCache)

        self.drawData = ()
        self.bbox = NULL_RECT

        self.syncToBond()

    def delete(self):

        for atomItem in self.atomItems:
            atomItem.bondItems.remove(self)

        compoundView = self.compoundView
        del compoundView.bondItems[self.bond]

        self.bond.deleteAll()
        del self

    def select(self):

        self.selected = True
        self.update()

    def deselect(self):

        self.selected = False
        self.update()

    def syncToBond(self):

        bond = self.bond

        atomA, atomB = bond.varAtoms

        atomDict = self.compoundView.atomViews
        self.atomItems = [atomDict[atomA], atomDict[atomB]]

        for atomItem in self.atomItems:
            if self not in atomItem.bondItems:
                atomItem.bondItems.append(self)

        xa, ya, za = atomA.coords
        xb, yb, zb = atomB.coords

        # Model curation

        dx = xb - xa
        dy = yb - ya
        dz = zb - za

        angleA = atan2(dx, -dy)

        xg = BOND_SEP * cos(angleA)
        yg = BOND_SEP * sin(angleA)

        if atomA.isLabile or atomB.isLabile:
            isLabile = True
            if self.compoundView.showChargeSymbols:
                style = Qt.DashLine
            else:
                style = Qt.SolidLine
        else:
            isLabile = False
            style = Qt.SolidLine

        stereoA = atomA.stereo
        stereoB = atomB.stereo
        if stereoA or stereoB:
            if stereoA:  # if they both are...
                zbase = 0
                index = stereoA.index(atomB)
                nStereo = len(stereoA)
            else:
                zbase = 1
                index = stereoB.index(atomA)
                nStereo = len(stereoB)

            if 3 < nStereo < 8:
                zstep = BOND_STEREO_DICT[nStereo][index]
            else:
                zstep = 0

        else:
            zstep = 0
            zbase = 0

        direction = self.bond.direction
        if direction:
            if direction is atomA:
                direct = 0
            else:
                direct = 1

        else:
            direct = None

        # Geometry

        # Set global position using first point
        self.setPos(QPointF(xa, ya))

        # Draw local relative to origin
        self.drawData = (style, dx, dy, xg, yg, zstep, zbase, direct)

        # Setup render coords

        nLines = int(BOND_TYPE_VALENCES[bond.bondType])
        pad = 2.0 * BOND_SEP * (nLines - 1.0) + 0.75

        if zstep:
            pad += BOND_SEP / 2

        if direct is not None:
            pad += BOND_SEP * 2

        rect = QRectF(QPointF(0.0, 0.0),
                      QPointF(dx, dy))

        self.bbox = rect.normalized().adjusted(-pad, -pad, pad, pad)

        self.update()

    def boundingRect(self):

        #if self.compoundView.showSkeletalFormula:
        #for atom in self.bond.varAtoms:
        #if atom.element == 'H':
        #for n in atom.neighbours:
        #if n.element != 'C':
        #return NULL_RECT
        return self.bbox

    def getDistToBond(self, pos):

        xm = pos.x()
        ym = pos.y()

        atomItemA, atomItemB = self.atomItems
        pos = atomItemA.pos()
        xa = pos.x()
        ya = pos.y()

        pos = atomItemB.pos()
        xb = pos.x()
        yb = pos.y()

        xb -= xa
        yb -= ya

        lb = hypot(xb, yb)

        xb /= lb
        yb /= lb

        xm -= xa
        ym -= ya

        dp = xb * xm + yb * ym

        xb *= dp
        yb *= dp

        xb -= xm
        yb -= ym

        r = hypot(xb, yb)

        return r

    def mousePressEvent(self, event):

        selected = list(self.compoundView.selectedViews)

        mods = event.modifiers()
        button = event.button()
        haveCtrl = mods & Qt.CTRL
        haveShift = mods & Qt.SHIFT

        if self.getDistToBond(self.mapToScene(event.pos())) > 8:
            return

        atomItemA, atomItemB = self.atomItems

        if haveCtrl or haveShift:
            if atomItemA.selected and atomItemB.selected:
                atomItemA.deselect()
                atomItemB.deselect()
            else:
                atomItemA.select()
                atomItemB.select()

        elif not (atomItemA.selected and atomItemB.selected):
            for view in selected:
                view.deselect()
            atomItemA.select()
            atomItemB.select()

        atomItemA.update()
        atomItemB.update()

        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):

        bond = self.bond

        if bond.bondType == 'aromatic':
            return

        if self.getDistToBond(self.mapToScene(event.pos())) > 8:
            return

        varAtom1, varAtom2 = bond.varAtoms

        atomA = varAtom1.atom
        atomB = varAtom2.atom

        for var in bond.compound.variants:

            varAtomA = var.atomDict.get(atomA)
            varAtomB = var.atomDict.get(atomB)

            if varAtomA and varAtomB:
                common = varAtomA.bonds & varAtomB.bonds
                if common:
                    bond = common.pop()

                    if varAtomA.freeValences and varAtomB.freeValences:
                        bond.setBondType(BOND_CHANGE_DICT[bond.bondType])
                        varAtomA.updateValences()
                        varAtomB.updateValences()

                    elif bond.bondType in ('double', 'triple', 'quadruple'):
                        bond.setBondType('single')
                        varAtomA.updateValences()
                        varAtomB.updateValences()

        if self.compoundView.autoChirality:
            varAtom1.autoSetChirality()
            varAtom2.autoSetChirality()

        self.compoundView.updateAll()

    def paint(self, painter, option, widget):

        if not self.drawData:
            return

        if self.selected:
            color = HIGHLIGHT
        elif isinstance(self.compoundView, QtWidgets.QGraphicsItem):
            # SpecView
            if self.compoundView.container:
                color = QtGui.QColor(*self.glWidget._hexToRgba(self.compoundView.container.mainApp.colors[1]))
            # Analysis
            elif self.compoundView.glWidget:
                raise NotImplementedError("Needs rewriting - analysisProfile does not exist")
                backgroundColor = QtGui.QColor()
                backgroundColor.setRgbF(*self.glWidget._hexToRgba(self.glWidget.spectrumWindow.analysisProfile.bgColor))
                color = QtGui.QPalette().windowText().color()
            # Fallback
            else:
                color = self.compoundView.bondColor
        else:
            color = self.compoundView.bondColor

        style, dx, dy, xg, yg, zstep, zbase, direct = self.drawData
        bondType = self.bond.bondType
        drawLine = painter.drawLine

        pen = QtGui.QPen(color, 1.5, style)
        painter.setPen(pen)

        #if self.compoundView.showSkeletalFormula:
        #for atom in self.bond.varAtoms:
        #if atom.element == 'H':
        #for n in atom.neighbours:
        #if n.element != 'C':
        #return

        if bondType in ('single', 'dative'):
            if bondType == 'dative':
                xindent = 3.5 * yg
                yindent = -3.5 * xg

                if direct:
                    x1 = dx - xindent * 1.5
                    y1 = dy - yindent * 1.5
                    x0 = y0 = 0.0

                else:
                    x0 = xindent * 1.5
                    y0 = yindent * 1.5
                    x1 = dx
                    y1 = dy

            else:
                x0 = y0 = 0.0
                x1 = dx
                y1 = dy

            if zstep:
                drawPoly = painter.drawPolygon
                dashPattern = [0.33, 0.5]

                if zbase == 0:  # A basis
                    if zstep < 0:
                        # dashed line
                        pen = QtGui.QPen(color, 4.5, Qt.DotLine)
                        pen.setDashPattern(dashPattern)
                        pen.setCapStyle(Qt.FlatCap)
                        painter.setPen(pen)

                        drawLine(QPointF(x0, y0),
                                 QPointF(x1, y1))

                    else:  #
                        # solid triangle, points at B
                        pen = QtGui.QPen(color, 0.5, Qt.SolidLine)
                        painter.setPen(pen)
                        painter.setBrush(color)
                        p1 = QPointF(dx + xg, dy + yg)
                        p2 = QPointF(dx - xg, dy - yg)
                        p3 = QPointF(x0, x0)

                        drawPoly(p1, p2, p3)

                else:  # B basis
                    if zstep < 0:
                        # dashed line
                        pen = QtGui.QPen(color, 4.5, Qt.DotLine)
                        pen.setDashPattern(dashPattern)
                        pen.setCapStyle(Qt.FlatCap)
                        painter.setPen(pen)

                        drawLine(QPointF(x0, y0),
                                 QPointF(x1, y1))

                    else:
                        # solid triangle, points at A
                        pen = QtGui.QPen(color, 0.5, Qt.SolidLine)
                        painter.setPen(pen)
                        painter.setBrush(color)
                        p1 = QPointF(xg, yg)
                        p2 = QPointF(-xg, -yg)
                        p3 = QPointF(x1, y1)

                        drawPoly(p1, p2, p3)

            else:
                drawLine(QPointF(x0, y0),
                         QPointF(x1, y1))

            if bondType == 'dative':
                drawPoly = painter.drawPolygon
                pen = QtGui.QPen(color, 0.5, Qt.SolidLine)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(color)

                if direct:
                    xc = dx - xindent
                    yc = dy - yindent
                    p1 = QPointF(xc - xindent + 2 * xg, yc - yindent + 2 * yg)
                    p2 = QPointF(xc - xindent - 2 * xg, yc - yindent - 2 * yg)
                    p3 = QPointF(xc, yc)

                else:
                    xc = xindent
                    yc = yindent
                    p1 = QPointF(xc + xindent + 2 * xg, yc + yindent + 2 * yg)
                    p2 = QPointF(xc + xindent - 2 * xg, yc + yindent - 2 * yg)
                    p3 = QPointF(xc, yc)

                drawPoly(p1, p2, p3)


        elif bondType == 'double':

            drawLine(QPointF(xg, yg),
                     QPointF(dx + xg, dy + yg))
            drawLine(QPointF(-xg, -yg),
                     QPointF(dx - xg, dy - yg))

        elif bondType == 'aromatic':
            drawLine(QPointF(0, 0),
                     QPointF(dx, dy))

        elif bondType == 'singleplanar':
            drawLine(QPointF(0, 0),
                     QPointF(dx, dy))

        elif bondType == 'triple':
            drawLine(0, 0, int(dx), int(dy))
            xg *= 2.0
            yg *= 2.0
            drawLine(QPointF(xg, yg),
                     QPointF(dx + xg, dy + yg))
            drawLine(QPointF(-xg, -yg),
                     QPointF(dx - xg, dy - yg))

        elif bondType == 'quadruple':
            drawLine(QPointF(xg, yg),
                     QPointF(dx + xg, dy + yg))
            drawLine(QPointF(-xg, -yg),
                     QPointF(dx - xg, dy - yg))
            xg *= 3.0
            yg *= 3.0
            drawLine(QPointF(xg, yg),
                     QPointF(dx + xg, dy + yg))
            drawLine(QPointF(-xg, -yg),
                     QPointF(dx - xg, dy - yg))

    # Smiles


organicAtoms = set(["B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"])
cnos = set(["C", "N", "O", "S"])


def importSmiles(smilesString, compoundName='Unnamed', project=None):
    compound = Compound(compoundName)
    var = Variant(compound)
    compound.defaultVars.add(var)

    aromatics = set()
    exludeHydrogens = set()
    rings = {}
    branch = []
    chirals = {}

    def _addStereo(varAtom1, varAtom2):

        varAtom1.stereo.append(varAtom2)

        if len(varAtom1.stereo) == 4:
            if chirals[varAtom1] > 0:
                a, b, c, d = varAtom1.stereo
                varAtom1.stereo = [a, d, c, b]

            # del chirals[varAtom1]

    n = len(smilesString)

    i = 0
    hIndex = 1
    prev = None
    bondType = 'single'
    configList = ''
    lastDouble = None
    addOrder = []

    while i < n:
        element = None
        charge = 0
        chiral = 0
        numH = None
        isAromatic = False
        char = smilesString[i:i + 1]

        if prev:
            x, y, z = prev.coords

        else:
            x = 0.0
            y = 0.0
            z = 0.0

        if char.isspace():
            i += 1
            continue

        if smilesString[i:i + 2] in organicAtoms:
            element = smilesString[i:i + 2]

        elif char.upper() in organicAtoms:
            element = char.upper()

            if (element in cnos) and char.islower():
                isAromatic = True

        elif char == '[':

            i += 1
            char = smilesString[i:i + 1]
            while char.isdigit():  # isotope label
                i += 1
                char = smilesString[i:i + 1]

            element = char.upper()
            if (element in cnos) and char.islower():
                isAromatic = True

            i += 1
            char = smilesString[i:i + 1]

            if char == '@':
                i += 1
                chiral = -1
                char = smilesString[i:i + 1]

            if char == '@':
                i += 1
                chiral = 1
                char = smilesString[i:i + 1]

            if char not in 'H+-]':
                element += char

                i += 1
                char = smilesString[i:i + 1]

            if char == 'H':
                numH = 1

                i += 1
                char = smilesString[i:i + 1]

                if char.isdigit():
                    numH = int(char)

                    i += 1
                    char = smilesString[i:i + 1]

            if char == '+':
                while char == '+':
                    charge += 1

                    i += 1
                    char = smilesString[i:i + 1]

                if char.isdigit():
                    charge = int(char)

                    i += 1
                    char = smilesString[i:i + 1]

            if char == '-':

                while char == '-':
                    charge -= 1

                    i += 1
                    char = smilesString[i:i + 1]

                if char.isdigit():
                    charge = -int(char)

                    i += 1
                    char = smilesString[i:i + 1]

        if char == '=':
            bondType = 'double'

        elif char == '#':
            bondType = 'triple'

        elif char == ':':
            bondType = 'aromatic'

        elif char == '-':
            bondType = 'single'

        elif char.isdigit() or char == '%':

            if char.isdigit():
                ringKey = char

            else:
                i += 1
                char = smilesString[i:i + 1]
                ringKey = ''

                while char.isdigit():
                    ringKey += char

                    i += 1
                    char = smilesString[i:i + 1]

                i -= 1
                char = smilesString[i:i + 1]

            if ringKey in rings:
                varAtomB, bondTypeB = rings[ringKey]
                Bond((varAtomB, prev), bondTypeB, autoVar=False)

                if bondTypeB == 'double':
                    lastDouble = (prev, varAtomB)

                if prev in chirals:
                    _addStereo(prev, varAtomB)

                if varAtomB in chirals:
                    _addStereo(varAtomB, prev)

                var.minimise2d(maxCycles=4)

                if ringKey in varAtomB.stereo:
                    index = varAtomB.stereo.index(ringKey)
                    varAtomB.stereo[index] = prev

                if ringKey in prev.stereo:
                    index = prev.stereo.index(ringKey)
                    prev.stereo[index] = varAtomB

                del rings[ringKey]

            else:
                rings[ringKey] = prev, bondType

                if prev in chirals:
                    _addStereo(prev, ringKey)

            bondType = 'single'

        elif char == '(':
            branch.append(prev)

        elif char == ')':
            if branch:
                prev = branch.pop()

        elif char == '/':
            configList += char

        elif char == '\\':
            configList += char

        elif char == '@':
            # TBD proper coordinate-based, clock or anti
            prev.setChirality('RS')

        elif char == '.':
            bondType = None

        elif char == '>':
            bondType = None

        if element:
            atom = Atom(compound, element, None)

            angle = 1.57
            if prev:
                prev.updateValences()
                freeValences = prev.freeValences

                if freeValences:
                    numVal = len(freeValences)
                    m = numVal // 2

                    if numVal % 2 == 0:
                        angle1 = freeValences[m - 1] % (2 * pi)
                        angle2 = freeValences[m] % (2 * pi)
                        s = (sin(angle1) + sin(angle2)) / 2.0
                        c = (cos(angle1) + cos(angle2)) / 2.0
                        angle = atan2(s, c)

                    else:
                        angle = freeValences[m]

            x += 50.0 * sin(angle)
            y += 50.0 * cos(angle)

            varAtom = VarAtom(var, atom, coords=(x, y, z), charge=charge)
            varAtom.updateValences()
            addOrder.append(varAtom)

            if chiral:
                varAtom.stereo = [prev, ]
                chirals[varAtom] = chiral

            if isAromatic:
                aromatics.add(varAtom)

            if numH:
                angles = list(varAtom.freeValences)

                for h in range(numH):
                    if angles:
                        angle = angles.pop()
                    else:
                        angle = 0.0

                    x2 = x + 50.0 * sin(angle)
                    y2 = y + 50.0 * cos(angle)

                    name = 'H%d' % hIndex
                    hIndex += 1
                    masterAtom = Atom(compound, 'H', name)
                    varAtomH = VarAtom(var, masterAtom, coords=(x2, y2, z))
                    Bond((varAtom, varAtomH), 'single', autoVar=False)

                    if varAtom in chirals:
                        _addStereo(varAtom, varAtomH)

            elif numH == 0:
                exludeHydrogens.add(varAtom)

            if prev and bondType:
                Bond((varAtom, prev), bondType, autoVar=False)

                if bondType == 'double':
                    lastDouble = (prev, varAtom)

                bondType = 'single'
                prev.updateValences()
                varAtom.updateValences()
            else:
                bondType = 'single'

            for varAtomB in chirals.keys():
                if varAtomB in varAtom.neighbours:
                    _addStereo(varAtomB, varAtom)

            if lastDouble and len(configList) > 1:

                config = configList[-2:]
                varAtomA, varAtomB = lastDouble
                x1, y1, z1 = varAtomA.coords
                x2, y2, z2 = varAtomB.coords

                dx = x2 - x1
                dy = y2 - y1

                angle = atan2(dx, dy)

                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                da = 1.57
                nudge = 30.0

                if config == '/\\':
                    x3 = nudge * sin(angle + da)
                    y3 = nudge * cos(angle + da)

                    x1 += x3
                    x2 += x3
                    y1 += y3
                    y2 += y3
                    varAtomA.coords = x1, y1, z1
                    varAtomB.coords = x2, y2, z2

                elif config == '//':
                    x3 = nudge * sin(angle + da)
                    y3 = nudge * cos(angle + da)

                    x1 += x3
                    y1 += y3
                    varAtomA.coords = x1, y1, z1

                    x3 = nudge * sin(angle - da)
                    y3 = nudge * cos(angle - da)

                    x2 += x3
                    y2 += y3
                    varAtomB.coords = x2, y2, z2

                elif config == '\\\\':

                    x3 = nudge * sin(angle - da)
                    y3 = nudge * cos(angle - da)

                    x1 += x3
                    y1 += y3
                    varAtomA.coords = x1, y1, z1

                    x3 = nudge * sin(angle + da)
                    y3 = nudge * cos(angle + da)

                    x2 += x3
                    y2 += y3
                    varAtomB.coords = x2, y2, z2

                elif config == '\\/':
                    x3 = nudge * sin(angle - da)
                    y3 = nudge * cos(angle - da)

                    x1 += x3
                    x2 += x3
                    y1 += y3
                    y2 += y3
                    varAtomA.coords = x1, y1, z1
                    varAtomB.coords = x2, y2, z2

                lastDouble = None

            prev = varAtom

        i += 1

    # set aromatics

    if aromatics:
        rings = var.getRings(aromatics)

        for varAtoms2 in rings:
            if varAtoms2 & aromatics == varAtoms2:
                varAtoms3 = [va for va in addOrder if va in varAtoms2]

                x, y, z = var.getCentroid(varAtoms3)
                dAngle = 2.0 * pi / float(len(varAtoms3))

                angle = 0.0
                for j, va in enumerate(varAtoms3):
                    x1 = x + 50.0 * sin(angle)
                    y1 = y + 50.0 * cos(angle)
                    va.coords = (x1, y1, z)
                    angle += dAngle

                AtomGroup(compound, varAtoms2, AROMATIC)
                var.minimise2d(varAtoms2, maxCycles=50)

    # add H
    for varAtom in list(var.varAtoms):
        if varAtom.element not in cnos:
            continue

        if varAtom in exludeHydrogens:
            continue

        varAtom.updateValences()
        newAtoms = []
        x, y, z = varAtom.coords

        for angle in list(varAtom.freeValences):
            x2 = x + 34.0 * sin(angle)
            y2 = y + 34.0 * cos(angle)

            name = 'H%d' % hIndex
            hIndex += 1

            masterAtom = Atom(compound, 'H', name)
            hydrogen = VarAtom(var, masterAtom, coords=(x2, y2, z))
            Bond((hydrogen, varAtom), 'single', autoVar=False)

    compound.center((0, 0, 0))
    var.minimise2d(maxCycles=50)
    var.minimise3d(maxCycles=50)
    var.minimise2d(maxCycles=50)
    var.checkBaseValences()
    #var.shuffleStereo()
    if project:
        try:
            nmrChain = project.newNmrChain(compoundName)
            nmrResidue = nmrChain.newNmrResidue(compoundName)
            for atom in compound.atoms:
                nmrAtom = nmrResidue.fetchNmrAtom(atom.name)
                nmrAtom._compoundViewAtom = atom
            nmrResidue._compoundViewCompound = compound
        except Exception as e:
            print(e)

    return compound


class VarAtom:

    def __init__(self, variantA, atom, freeValences=None, chirality=None,
                 coords=(0.0, 0.0, 0.0), isLabile=False, charge=0):

        if variantA is None:  # Means all vars
            variants = list(atom.compound.variants)
            variant = variants[0]
            otherVars = variants[1:]
        else:
            variant = variantA
            otherVars = []

        self.variant = variant
        self.atom = atom
        self.element = element = atom.element
        self.name = atom.name
        self.isVariable = atom.isVariable
        self.stereo = []

        compound = variant.compound
        compound.isModified = True
        self.compound = compound

        self.isDeleted = False
        self.coords = tuple(coords)
        self.chirality = chirality
        self.isLabile = isLabile
        self.charge = charge

        self.bonds = set()
        self.neighbours = set()
        self.atomGroups = set()

        if element not in variant.elementDict:
            variant.elementDict[element] = set()

        variant.elementDict[element].add(self)
        variant.varAtoms.add(self)
        variant.atomDict[atom] = self
        atom.varAtoms.add(self)

        if freeValences is None:
            self.freeValences = None
            self.updateValences()
        else:
            self.freeValences = list(freeValences)

        self.updateNeighbours()

        for var in otherVars:
            VarAtom(var, atom, freeValences, chirality,
                    coords, isLabile, charge)

            var.updatePolyLink()

        variant.updatePolyLink()

        if atom.isVariable:
            for var in self.compound.variants:
                var.updatePolyLink()
                var.updateDescriptor()

    def __repr__(self):

        aName = self.name
        return '<VarAtom %s>' % (aName)

    def setStereo(self, stereoVarAtoms):
        # Clockwise rule relative to first

        nStereo = len(self.neighbours)
        if nStereo < 4:
            stereoVarAtoms = []

        if stereoVarAtoms:
            if set(stereoVarAtoms) != set(self.neighbours):
                # print "Attempt to set stereo set to non-neighbours"
                return

        atom = self.atom
        for varAtom in atom.varAtoms:

            if len(varAtom.neighbours) != nStereo:
                varAtom.stereo = []

            elif varAtom is self:
                self.stereo = stereoVarAtoms

            else:  # all vars same, as far as possible, respecting a/b forms
                var = varAtom.variant
                stereoVarAtoms2 = [var.atomDict.get(va.atom) for va in stereoVarAtoms]

                if None in stereoVarAtoms2:
                    continue

                if len(stereoVarAtoms2) == nStereo:
                    stereo = stereoVarAtoms2

                    if varAtom.chirality == self.chirality:
                        varAtom.stereo = stereo
                    else:
                        a = stereo[0]
                        rest = stereo[1:]
                        rest.reverse()
                        varAtom.stereo = [a, ] + rest

    def toggleAromatic(self):

        if self.isAromatic():
            self.compound.unsetAromatic([self.atom, ])

        else:
            self.compound.setAromatic([self.atom, ])

    def isHydrogen(self):

        return self.element == 'H'

    def isAromatic(self):

        for group in self.atomGroups:
            if group.groupType == AROMATIC:
                return True

        return False

    def getRings(self):

        stack = []
        rings = set()

        for varAtom in self.neighbours:
            if varAtom.element != 'H':
                stack.append([self, varAtom])

        while stack:

            prev = stack.pop()
            if len(prev) > 8:
                continue

            prevSet = set(prev)

            nextAtoms = set([va for va in prev[-1].neighbours if va.element != 'H'])
            if prev[-2] in nextAtoms:
                nextAtoms.remove(prev[-2])

            for varAtom in nextAtoms:
                if varAtom.element == 'C':
                    if not varAtom.freeValences:
                        if not varAtom.isAromatic:
                            continue

                if varAtom is self:
                    rings.add(frozenset(prev))

                elif varAtom not in prevSet:
                    nextSet = prev[:] + [varAtom, ]
                    stack.append(nextSet)

        filteredRings = set()

        if rings:
            rings = sorted(rings, key=lambda ring: len(ring))
            minSz = len(rings[0])
            minRing = rings[0]
            filteredRings.add(minRing)

            uniqueAtoms = set()
            for ring in rings[1:]:
                unique = ring
                for ring2 in filteredRings:
                    unique = unique - ring2
                    nUnique = len(unique)
                if nUnique > 0 and unique not in uniqueAtoms:
                    for ua in unique:
                        if ua in self.neighbours:
                            break
                    else:
                        continue
                    uniqueAtoms.add(unique)
                    filteredRings.add(ring)

        #      for ring in rings:
        #        if len(ring) < minSz+2:
        #        filteredRings.add(ring)

        return filteredRings

    def setLabile(self, value=True):

        if (self.element == 'H') and (self.isLabile != value):
            neighbourhood = self.getContext()

            compound = self.compound
            compound.isModified = True

            # Set as labile only if the neighbours are the same as this var atom's
            # automatically includes its self

            for var in self.compound.variants:
                varAtom = var.atomDict.get(self.atom)

                if not varAtom:
                    continue

                neighbourhoodB = varAtom.getContext()
                if neighbourhoodB != neighbourhood:
                    continue

                varAtom.isLabile = value

    def setCoords(self, x, y, z):

        # Compound wide for now

        for varAtom in self.atom.varAtoms:
            varAtom.coords = (x, y, z)

        compound = self.compound
        compound.isModified = True

    def setName(self, name):

        self.atom.setName(name)

    def setChirality(self, chirality, autoVar=True):

        if self.element == LINK:
            return

        if self.element == 'H':
            return

        compound = self.compound
        variant = self.variant
        atom = self.atom
        compound.isModified = True

        if chirality is not None:
            nVal = len(self.freeValences) + len(self.bonds)
            nNei = len(self.neighbours)
            if nVal < 3:
                chirality = None

            if nVal > nNei:
                chirality = None

            hydrogens = [a for a in self.neighbours if a.element == 'H']
            if len(hydrogens) > 1:
                chirality = None

        if autoVar:
            variants = list(compound.variants)
            variants.remove(variant)
            variants = [variant, ] + variants
            # this one must be first - so it is not deleted
        else:
            variants = [variant, ]

        if chirality in ('R', 'S'):
            for var in variants:
                varAtom = var.atomDict[atom]
                varAtom.chirality = chirality

            varDict = {}
            for var in variants:
                key = frozenset(var.atomDict.keys())

                if key not in varDict:
                    varDict[key] = []

                varDict[key].append(var)

            for key in varDict:
                vars2 = varDict[key]

                while len(vars2) > 1:
                    var = vars2.pop()
                    var.delete()

        elif chirality in ('a', 'b'):

            varDict = {}
            for var in variants:
                key = frozenset(var.atomDict.keys())

                if key not in varDict:
                    varDict[key] = []

                varDict[key].append(var)

            for key in varDict:
                vars2 = varDict[key]

                while len(vars2) > 2:
                    var = vars2.pop()
                    var.delete()

                while len(vars2) < 2:
                    var = Variant(compound, vars2[0].varAtoms)
                    vars2.append(var)
                    variants.append(var)

                varA, varB = vars2

                if variant is varA:
                    if chirality == 'b':
                        varA, varB = varB, varA

                elif variant is varB:
                    if chirality == 'a':
                        varA, varB = varB, varA

                varAtomA = varA.atomDict[atom]
                varAtomB = varB.atomDict[atom]

                varAtomA.chirality = 'a'
                varAtomB.chirality = 'b'

                if self.stereo:
                    a, b, c, d = self.stereo

                    if chirality == 'a':
                        stereoA = [varA.atomDict[va.atom] for va in [a, b, c, d]]
                        stereoB = [varB.atomDict[va.atom] for va in [a, d, c, b]]
                    else:
                        stereoA = [varA.atomDict[va.atom] for va in [a, d, c, b]]
                        stereoB = [varB.atomDict[va.atom] for va in [a, b, c, d]]

                    varAtomA.stereo = stereoA
                    varAtomB.stereo = stereoB

        elif not chirality:
            for var in variants:
                varAtom = var.atomDict[atom]
                varAtom.chirality = chirality
                varAtom.stereo = []

            varDict = {}
            for var in variants:
                key = frozenset(var.atomDict.keys())

                if key not in varDict:
                    varDict[key] = []

                varDict[key].append(var)

            for key in varDict:
                vars2 = varDict[key]

                while len(vars2) > 1:
                    var = vars2.pop()
                    var.delete()

        # Once all set
        for var in variants:
            var.updateDescriptor()

    def getContext(self):

        # Get all of the (master) atoms surrounding this one

        return set([va.atom for va in self.neighbours])

    def setCharge(self, charge, autoVar=True):

        elem = self.element
        if elem == LINK:
            return

        if elem == 'H':
            return

        compound = self.compound
        compound.isModified = True

        defaultVal = self.atom.baseValences

        neighbourhood = self.getContext()

        if autoVar:
            variants = compound.variants
        else:
            variants = [self.variant, ]

        for var in variants:
            varAtom = var.atomDict.get(self.atom)

            if not varAtom:
                continue

            if varAtom.getContext() != neighbourhood:
                continue

            nVal = len(varAtom.bonds) + len(varAtom.freeValences)
            if (elem in COVALENT_ELEMENTS) and (charge < 0):
                charge = max(-nVal, charge)
                targetVal = defaultVal + charge

            elif (elem in COVALENT_ELEMENTS) and (charge > 0):
                targetVal = defaultVal + charge

            else:
                targetVal = defaultVal

            # add any extra
            while nVal < targetVal:
                varAtom.freeValences.append(0.0)
                nVal += 1

            # remove exess unbound
            while nVal > targetVal:
                if varAtom.freeValences:
                    varAtom.freeValences.pop()
                    nVal -= 1
                else:
                    break

            # otherwise remove extra H
            if nVal > targetVal:
                for bond in list(varAtom.bonds):
                    atomA, atomB = bond.varAtoms

                    if (atomA is not varAtom) and (atomA.element == LINK):
                        bond.delete()
                        nVal -= 1

                    if (atomB is not varAtom) and (atomB.element == LINK):
                        bond.delete()
                        nVal -= 1

                    if (atomA is not varAtom) and (atomA.element == 'H'):
                        bond.delete()
                        nVal -= 1

                    if (atomB is not varAtom) and (atomB.element == 'H'):
                        bond.delete()
                        nVal -= 1

                    if nVal == targetVal:
                        break

            # otherwise remove anything
            if nVal > targetVal:
                for bond in list(varAtom.bonds):
                    bond.delete()
                    nVal -= 1

                    if nVal == targetVal:
                        break

            varAtom.charge = charge
            varAtom.updateValences()

            var.updateDescriptor()

    def getBondAngles(self):

        x1, y1, z1 = self.coords
        angles = []

        for bond in self.bonds:
            varAtoms = set(bond.varAtoms)
            varAtoms.remove(self)

            varAtom = varAtoms.pop()

            x2, y2, z2 = varAtom.coords

            dx = x2 - x1
            dy = y2 - y1

            angle = atan2(dx, dy) % (2.0 * PI)
            angles.append(angle)

        return angles

    def getBondAngle(self, varAtom):

        x1, y1, z1 = self.coords
        x2, y2, z2 = varAtom.coords

        dx = x2 - x1
        dy = y2 - y1

        angle = atan2(dy, dx) % (2.0 * PI)

        return angle

    def getBondToAtom(self, varAtom):

        for bond in self.bonds:
            if self in bond.varAtoms and varAtom in bond.varAtoms:
                return bond

        return None

    def getAtomDist(self, varAtom):

        x1, y1, z1 = self.coords
        x2, y2, z2 = varAtom.coords

        dx = x2 - x1
        dy = y2 - y1

        return hypot(dx, dy)

    def setVariable(self, boolean):

        self.atom.setVariable(boolean)

    def updateValences(self):

        defaultVal = self.atom.baseValences

        if self.freeValences is None:
            if defaultVal:
                gap = 2.0 * PI / defaultVal
                self.freeValences = [gap * i for i in range(defaultVal)]
            else:
                self.freeValences = []

        else:
            bound = self.getBondAngles()

            numVal = defaultVal
            for bond in self.bonds:
                numVal -= BOND_TYPE_VALENCES[bond.bondType]

            if self.element in COVALENT_ELEMENTS:
                numVal += self.charge

            if numVal and self.isAromatic():
                numVal -= 1

            self.freeValences = [0.0] * numVal

            if bound:
                bound.sort()
                bound.append(bound[0] + (2.0 * PI))
                gaps = [(bound[i + 1] - x, x, bound[i + 1], []) for i, x in enumerate(bound[:-1])]
                gaps.sort()
                for i in range(numVal):
                    size, begin, end, indices = gaps[-1]
                    indices.append(i)
                    sizeB = (end - begin) / (len(indices) + 1.0)

                    for k, j in enumerate(indices):
                        delta = (1.0 + k) * sizeB
                        self.freeValences[j] = (begin + delta) % (2 * PI)

                    gaps[-1] = (sizeB, begin, end, indices)
                    gaps.sort()

            elif self.freeValences:
                gap = 2.0 * PI / len(self.freeValences)
                self.freeValences = [gap * i for i in range(numVal)]

    def updateNeighbours(self):

        atoms = set()
        for bond in self.bonds:
            atoms.update(bond.varAtoms)

        if atoms:
            atoms.remove(self)

        if self.neighbours != atoms:
            hydrogens = [a for a in atoms if a.element == 'H']
            changed = atoms ^ self.neighbours

            for atom in changed:
                if (atom.element == 'H') and self.element == 'O':
                    atom.setLabile(True)

                elif (atom.element == 'H') and self.element == 'N':

                    if self.charge and len(hydrogens) > 2:
                        for h in hydrogens:
                            h.setLabile(True)
                    else:
                        for h in hydrogens:
                            h.setLabile(False)

            if (self.element == 'C') and hydrogens:
                hydrogens = [h.atom for h in hydrogens]

                self.compound.unsetAtomsProchiral(hydrogens)
                self.compound.unsetAtomsEquivalent(hydrogens)

                if len(hydrogens) == 2:
                    self.compound.setAtomsProchiral(hydrogens)
                elif len(hydrogens) == 3:
                    self.compound.setAtomsEquivalent(hydrogens)

            self.neighbours = atoms

    def delete(self):

        variant = self.variant
        if self not in variant.varAtoms:
            return

        compound = self.compound
        compound.isModified = True

        atom = self.atom

        for bond in list(self.bonds):
            bond.delete()

        if self.element in variant.elementDict:
            variant.elementDict[self.element].remove(self)

        variant.varAtoms.remove(self)
        del variant.atomDict[atom]
        atom.varAtoms.remove(self)

        # Remove any vars that have identical atoms

        atoms = set([(va.atom, va.chirality) for va in variant.varAtoms])

        for var in list(self.compound.variants):
            if var is variant:
                continue

            atoms2 = set([(va.atom, va.chirality) for va in var.varAtoms])

            if atoms2 == atoms:
                var.delete()

        for group in list(self.atomGroups):
            group.delete()

        if not atom.varAtoms:
            if not atom.isDeleted:
                atom.delete()

        if not variant.varAtoms:
            variant.delete()

    # Snap the atom to one of the specified angles. The angle is chosen based on collisions with already placed atoms.
    def snapToGrid(self, prevAtom, bondLength=50.0, prevAngle=None, angles=[], remainingAtoms=[], ignoreHydrogens=True):

        prevX = prevAtom.coords[0]
        prevY = prevAtom.coords[1]

        oldX, oldY, oldZ = self.coords

        if len(angles) == 0:
            angles = [120, -120]
        if prevAngle == None:
            prevAngle = 210
        for i in range(len(angles)):
            angles[i] = radians((prevAngle + angles[i]) % 360)

        minD = None
        minI = None
        minPen = None

        allAtoms = self.variant.varAtoms - set(remainingAtoms)

        for i, angle in enumerate(angles):
            x = prevX + bondLength * cos(angle)
            y = prevY + bondLength * sin(angle)
            pen = 1
            for atom in allAtoms:
                if atom == self or atom in self.neighbours or (ignoreHydrogens and atom.element == 'H'):
                    continue
                atomDist = hypot(x - atom.coords[0], y - atom.coords[1])
                if atomDist < bondLength:
                    if atomDist < 1:
                        pen *= 100
                        if atomDist < 0.000001:
                            atomDist = 0.000001
                    pen *= 2 * bondLength / atomDist
            if not minPen or pen < minPen:
                minPen = pen
                minI = i
                bestX = x
                bestY = y
            if pen == 1:
                break

        self.coords = (bestX, bestY, oldZ)

        return degrees(angles[minI])

    def getPreferredBondAngles(self, prevAngle, neighbours=None, ignoredAtoms=[], ignoreHydrogens=True):

        bonds = self.bonds
        nBonds = len(bonds)
        angles = []
        ringAtoms = []
        nHydrogens = 0

        if neighbours == None:
            neighbours = sorted(self.neighbours, key=lambda atom: atom.name)

        for neighbour in neighbours:
            if neighbour.element == 'H':
                nHydrogens += 1

        if ignoreHydrogens:
            nBonds -= nHydrogens

        rings = set(self.getRings())

        if len(rings) > 0:
            for ring in rings:
                # Hydrogens receive a special treatment.
                #if not ignoreHydrogens:
                #if nBonds == 4:
                #if nHydrogens == 2:
                #angles = [70, 160, -70, -160]
                #if nHydrogens == 1:
                #angles = [180]
                #return angles
                ringSize = len(ring)
                ringAngle = ((ringSize - 2) * 180) / ringSize
                angle = (180 - 0.5 * ringAngle)
                if nBonds > 3:
                    angle /= nBonds - 2
                if not ignoreHydrogens and abs(360 - angle - 2 * angle) > 0.1:
                    for a in [angle, -angle, 2 * angle, -2 * angle]:
                        angles.append(a)
                else:
                    for a in [angle, -angle]:
                        angles.append(a)
                if angle < 120:
                    angles.append(3 * angle)
            return angles
        else:
            # Triple bonds or two double bonds have a 180 degrees angle.
            nDouble = 0
            for bond in bonds:
                if bond.bondType == 'triple':
                    angles = [180]
                if bond.bondType == 'double':
                    nDouble += 1
            if nDouble == len(bonds):
                angles = [180]
        if len(angles) == 0:
            angles = [120, -120]

        if prevAngle != None and (90 <= prevAngle < 180 or 270 <= prevAngle < 360):
            for i in range(len(angles)):
                angles[i] = -angles[i]

        if nBonds > 2:
            neighbourAngles = []
            for neighbour in neighbours:
                if not neighbour in ignoredAtoms:  # and (not ignoreHydrogens or neighbour.element != 'H'):
                    neighbourAngle = round(degrees(self.getBondAngle(neighbour)), 0)
                    neighbourAngle -= prevAngle
                    neighbourAngles.append(neighbourAngle)
            if nBonds == 4:
                if len(neighbourAngles) > 1:
                    angles = [67.5, 172.5, 120, -120]
                else:
                    angles = [120, -120, 67.5, 172.5]
            elif nBonds >= 4:
                angles = []
                for i in range(1, nBonds):
                    angles.append(i * 360 / nBonds)

            for neighbourAngle in neighbourAngles:
                if abs(neighbourAngle - 120) < 1 or abs(neighbourAngle + 240) < 1:
                    for i in range(len(angles)):
                        angles[i] = -angles[i]
                    break

        return angles

    def findAtomsInBranch(self, firstAtomInBranch, atoms=None):

        if not atoms:
            atoms = set([firstAtomInBranch])

        if not self in atoms:
            temporarySelfAdd = True
            atoms.add(self)
        else:
            temporarySelfAdd = False

        neighbours = set(firstAtomInBranch.neighbours)

        while neighbours:
            neighbour = neighbours.pop()
            if neighbour == self or neighbour in atoms:
                continue

            atoms.add(neighbour)

            if neighbour.element == 'H':
                continue

            for neighbour2 in neighbour.neighbours:
                if neighbour2 in atoms:
                    continue

                atoms.add(neighbour2)
                if neighbour2.element == 'H':
                    continue

                atoms.update(neighbour.findAtomsInBranch(neighbour2, atoms))

        if temporarySelfAdd:
            atoms.remove(self)

        return atoms

    # Returns a list of atoms sorted by their respective branch lengths, shortest first.
    def getBranchesSortedByLength(self):
        branchLens = []
        for a in self.neighbours:
            branchLens.append([len(self.findAtomsInBranch(a)), a])
        branchLens = sorted(branchLens, key=lambda x: x[0])

        branches = [b[1] for b in branchLens]

        return branches

    def atomInSameRing(self, atom):

        selfRings = self.getRings()
        atomRings = atom.getRings()
        if len(selfRings) > 0 and len(atomRings) > 0:
            for ring in atomRings:
                if ring in selfRings:
                    return True
        return False

    def snapRings(self, rings, neighbours, atoms, prevAngle, bondLength):

        skippedAtoms = set([])
        for ring in rings:
            if len(atoms) == 0:
                return
            for ringAtom in ring:
                if ringAtom in atoms:
                    if ringAtom in neighbours:
                        neighbours.remove(ringAtom)
                    atoms.remove(ringAtom)
                else:
                    skippedAtoms.add(ringAtom)
                    if ringAtom != self:
                        prevAngle = None
            self.variant.snapRingToGrid(ring, self, prevAngle, bondLength, skippedAtoms)
            skippedAtoms.add(self)

        for ring in rings:
            for ringAtom in ring:
                if ringAtom in skippedAtoms:
                    continue
                ringAtomRings = ringAtom.getRings()
                if ring in ringAtomRings:
                    ringAtomRings.remove(ring)
                for ringAtomRing in set(ringAtomRings):
                    for atom in atoms:
                        if atom in ringAtomRing:
                            break
                    else:
                        ringAtomRings.remove(ringAtomRing)
                if len(ringAtomRings) > 0:
                    ringAtomRings = sorted(ringAtomRings, key=lambda ring: len(ring), reverse=True)
                    ringAtomNeighbours = sorted(ringAtom.neighbours, key=lambda atom: atom.name)
                    ringAtom.snapRings(ringAtomRings, ringAtomNeighbours, atoms, None, bondLength)

    def autoSetChirality(self):

        variants = self.compound.variants
        atom = self.atom
        stereo = None

        if self.chirality in ['a', 'b']:
            return

        chirality = self.getStereochemistry()
        # Make the automatically set chirality lower case to be able to distinguish it from user specified chirality.
        if chirality:
            chirality = chirality.lower()

        if self.chirality and self.chirality.isupper():
            branches = self.getBranchesSortedByLength()
            if len(branches) == 4:
                stereo = [branches[3], branches[0], branches[2], branches[1]]
            elif len(branches) >= 4:
                stereo = [branches[3], branches[0], branches[2], branches[1], branches[4:]]

                if stereo:
                    self.setStereo(stereo)

        for var in variants:
            varAtom = var.atomDict.get(atom)
            if not varAtom:
                continue

            vAChirality = varAtom.chirality
            if stereo and not varAtom.stereo:
                for a in stereo:
                    varAtom.stereo.append(var.atomDict.get(a.atom))

            chirality = varAtom.getStereochemistry()
            if chirality:
                chirality = chirality.lower()

            if vAChirality and vAChirality.isupper():
                if vAChirality in ('R', 'S'):
                    if chirality and vAChirality.lower() != chirality:
                        temp = varAtom.stereo[3]
                        varAtom.stereo[3] = varAtom.stereo[1]
                        varAtom.stereo[1] = temp
                        chirality = varAtom.getStereochemistry()
                        chirality = chirality.lower()
                        if vAChirality.lower() != chirality:
                            raise Exception("Stereochemistry of %s different even after attempted swap. (%s and %s)" % (varAtom, vAChirality, chirality))
            else:
                varAtom.chirality = chirality

    def getStereochemistry(self):

        neighbours = self.neighbours
        nNeighbours = len(neighbours)

        stereochemistry = None

        if nNeighbours == 4:
            nHydrogens = 0
            for neighbour in neighbours:
                if neighbour.element == 'H':
                    nHydrogens += 1
            if nHydrogens <= 1 and self.stereo != []:
                stereochemistry = self.getStereochemistryRS()

        elif nNeighbours == 3:
            for neighbour in neighbours:
                bond = self.getBondToAtom(neighbour)
                if bond.bondType == 'double':
                    if len(neighbour.neighbours) == 3:
                        stereochemistry = self.getStereochemistryEZ(neighbour)

        return stereochemistry

    def getStereochemistryRS(self):

        prio = self.getPriorities()

        if prio == None:
            return None

        lowPrio = prio[-1]

        refBondAngle = self.getBondAngle(prio[0])
        secondBondAngle = (self.getBondAngle(prio[1]) - refBondAngle) % (2 * PI)
        thirdBondAngle = (self.getBondAngle(prio[2]) - refBondAngle) % (2 * PI)

        if secondBondAngle < thirdBondAngle:
            stereo = 1
        elif secondBondAngle > thirdBondAngle:
            stereo = -1
        else:
            return None

        lowPrioIndex = self.stereo.index(lowPrio)

        if lowPrioIndex == 3:
            stereo *= -1
        elif lowPrioIndex != 1:
            lowHighAngle = abs(self.getBondAngle(lowPrio) - self.getBondAngle(self.stereo[3])) % (2 * PI)
            if lowHighAngle > PI / 2:
                stereo *= -1

        if stereo == 1:
            return "R"
        if stereo == -1:
            return "S"
        return None

    def getStereochemistryEZ(self, other):

        selfPrio = self.getPriorities()
        if selfPrio == None:
            return None
        otherPrio = other.getPriorities()
        if otherPrio == None:
            return None

        angleMain = self.getBondAngle(other)
        selfHighPrio = selfLowPrio = None
        otherHighPrio = otherLowPrio = None
        for atom in selfPrio:
            if atom != other:
                if selfHighPrio == None:
                    selfHighPrio = atom
                else:
                    selfLowPrio = atom
        for atom in otherPrio:
            if atom != self:
                if otherHighPrio == None:
                    otherHighPrio = atom
                else:
                    otherLowPrio = atom
        angleHighPrio = selfHighPrio.getBondAngle(otherHighPrio)
        angleLowPrio = selfHighPrio.getBondAngle(otherLowPrio)

        diff = abs(angleMain - angleHighPrio)
        altDiff = abs(angleMain - angleLowPrio)
        diff = min(diff, abs(2 * PI - diff))
        altDiff = min(altDiff, abs(2 * PI - altDiff))

        if diff < altDiff:
            return 'Z'
        if diff > altDiff:
            return 'E'

        return None

    # This function returns a list of neighbours ranked according to Cahn-Ingold-Prelog rules (not taking more than the fourth level of neighbours into account).
    # The neighbour with highest priority is first in the returned list.
    def getPriorities(self):

        prio = 0

        firstList = self.getFirstNeighbourPriorities()
        foundSimilar = False
        for i, item in enumerate(firstList):
            for otherItem in firstList[(i + 1):]:
                if item[1] == otherItem[1]:
                    foundSimilar = True
                    break
            if foundSimilar:
                break
        if foundSimilar:
            secondList = self.getSecondNeighbourPriorities()
            thirdList = self.getThirdNeighbourPriorities()
            fourthList = self.getFourthNeighbourPriorities()

        n = len(firstList)

        prioList = [None] * n

        while prio < n:
            item = firstList[prio]
            if prio + 1 == n:
                prioList[prio] = item[0]
                prio += 1
            else:
                nextItem = firstList[prio + 1]
                if item[1] != nextItem[1]:
                    prioList[prio] = item[0]
                    prio += 1
                    continue

                similar = [prio, prio + 1]
                i = 2
                while prio + i < n and firstList[prio][1] == firstList[prio + i][1]:
                    similar.append(prio + i)
                    i += 1

                nSim = len(similar)
                while nSim > 0:
                    newN = 0
                    for i in range(1, nSim):
                        this = similar[i]
                        prev = similar[i - 1]
                        if secondList[prev][-1] == secondList[this][-1] and thirdList[prev][-1] == thirdList[this][-1] and \
                                fourthList[prev][-1] == fourthList[this][-1]:
                            return None

                        if secondList[prev][-1] < secondList[this][-1] or \
                                (secondList[prev][-1] == secondList[this][-1] and (thirdList[prev][-1] < thirdList[this][-1] or \
                                                                                   (thirdList[prev][-1] == thirdList[this][-1] and fourthList[prev][-1] <
                                                                                    fourthList[this][-1]))):
                            temp = similar[i]
                            similar[i] = similar[i - 1]
                            similar[i - 1] = temp
                            newN = i
                    nSim = newN

                for item in similar:
                    prioList[prio] = firstList[item][0]
                    prio += 1

        return prioList

    # This should actually be the atomic number, but here the mass number of the main isotope is used instead. Should still
    # sort in the same order.
    def priorityNumber(self):

        if self.atom.element == LINK:
            return ELEMENT_ISO_ABUN['C'][0][1]
        return ELEMENT_ISO_ABUN[self.atom.element][0][1]

    def getFirstNeighbourPriorities(self):

        priorityList = []

        for neighbour in self.neighbours:
            p = neighbour.priorityNumber()
            priorityList.append([neighbour, p])

        priorityList = sorted(priorityList, key=lambda neighbour: neighbour[1], reverse=True)

        return priorityList

    def getSecondNeighbourPriorities(self):

        priorityList = []
        maxLen = None

        for a, p in self.getFirstNeighbourPriorities():
            if a == None:
                continue

            localPriorityList = []
            for atom, prio in a.getFirstNeighbourPriorities():
                if atom != self:
                    localPriorityList.append([atom, prio])
                bond = a.getBondToAtom(atom)
                if bond.bondType == 'double' or bond.bondType == 'triple' or a.isAromatic():
                    localPriorityList.append([None, prio])
                    if bond.bondType == 'triple':
                        localPriorityList.append([None, prio])

            localPriorityList = sorted(localPriorityList, key=lambda neighbour: neighbour[1], reverse=True)

            l = len(localPriorityList)
            if maxLen == None or l > maxLen:
                maxLen = l

            priorityList.append(localPriorityList)

        maxLen -= 1

        for localPriorityList in priorityList:
            score = 0
            for i, (a, p) in enumerate(localPriorityList):
                score += p * (10**((maxLen - i) * 2))

            localPriorityList.append([None, score])

        return priorityList

    def getThirdNeighbourPriorities(self):

        priorityList = []
        maxLen = None

        for lst in self.getSecondNeighbourPriorities():

            localPriorityList = []
            for a, p in lst:
                if a is None:
                    continue

                for atom, prio in a.getFirstNeighbourPriorities():
                    if atom not in self.neighbours:
                        localPriorityList.append([atom, prio])
                    bond = a.getBondToAtom(atom)
                    if bond.bondType == 'double' or bond.bondType == 'triple' or a.isAromatic():
                        localPriorityList.append([None, prio])
                        if bond.bondType == 'triple':
                            localPriorityList.append([None, prio])

            l = len(localPriorityList)
            if maxLen is None or l > maxLen:
                maxLen = l

            priorityList.append(localPriorityList)

        maxLen -= 1

        for localPriorityList in priorityList:
            score = 0
            for i, (a, p) in enumerate(localPriorityList):
                score += p * (10**((maxLen - i) * 2))

            localPriorityList.append([None, score])

        return priorityList

    def getFourthNeighbourPriorities(self):

        priorityList = []
        maxLen = None
        nextNeighbours = set()

        for lst in self.getThirdNeighbourPriorities():

            localPriorityList = []
            for a, p in lst:
                if a is None:
                    continue

                for atom, prio in a.getFirstNeighbourPriorities():
                    localPriorityList.append([atom, prio])

            l = len(localPriorityList)
            if maxLen is None or l > maxLen:
                maxLen = l

            priorityList.append(localPriorityList)

        maxLen -= 1

        for localPriorityList in priorityList:
            score = 0
            for i, (a, p) in enumerate(localPriorityList):
                score += p * (10**((maxLen - i) * 2))

            localPriorityList.append([None, score])

        return priorityList


def vectorsSubtract(v1, v2):
    """ Subtract vectors v1 and v2.
  """

    n = len(v1)
    if n != len(v2):
        raise Exception('length of v1 != length of v2')

    v = n * [0]
    for i in range(n):
        v[i] = v1[i] - v2[i]

    return v


def dotProduct(v1, v2):
    """ The inner product between v1 and v2.
  """

    n = len(v1)
    if (n != len(v2)):
        raise Exception('v1 and v2 must be same length')

    d = 0
    for i in range(n):
        d = d + v1[i] * v2[i]

    return d


def crossProduct(v1, v2):
    """ Returns the cross product of v1 and v2.
  Both must be 3-dimensional vectors.
  """

    if (len(v1) != 3 or len(v2) != 3):
        raise Exception('v1 and v2 must be of length 3')

    return [v1[1] * v2[2] - v1[2] * v2[1], v1[2] * v2[0] - v1[0] * v2[2], v1[0] * v2[1] - v1[1] * v2[0]]


class Variant:

    def __init__(self, compound, templateVarAtoms=None):

        self.compound = compound
        self.polyLink = None  # Auto derived
        self.descriptor = None  # Auto derived
        self.varAtoms = set()
        self.bonds = set()
        self.atomDict = {}
        self.atomGroups = set()
        self.elementDict = {}

        compound.isModified = True
        compound.variants.add(self)

        if templateVarAtoms:
            self.copyAtoms(templateVarAtoms, (0, 0), False)

        self.updatePolyLink()
        self.updateDescriptor()

    def __repr__(self):

        h, l, s = self.descriptor
        return '<Variant %s %s %s %s>' % (self.polyLink, h, l, s)

    def delete(self):

        compound = self.compound
        compound.isModified = True
        for varAtom in list(self.varAtoms):
            varAtom.delete()

        self.varAtoms = set()
        self.bonds = set()
        self.atomDict = {}
        self.elementDict = {}

        if len(compound.variants) > 1:
            if self in compound.variants:
                compound.variants.remove(self)

            del self

        nVars = len(compound.variants)
        for atom in compound.atoms:
            if atom.isVariable and (len(atom.varAtoms) == nVars):
                atom.isVariable = False

        for var in compound.variants:
            var.updatePolyLink()
            var.updateDescriptor()

    def setDefault(self, value=True):

        compound = self.compound
        compound.isModified = True
        defaultVars = compound.defaultVars
        current = set([v for v in defaultVars if v.polyLink == self.polyLink])

        if value:
            for var in current:
                defaultVars.remove(var)
            defaultVars.add(self)

        elif self in current:
            defaultVars.remove(self)

    def getRings(self, varAtoms):

        for varAtom in varAtoms:
            if varAtom.variant is not self:
                msg = 'Variant.getRings: Input VarAtom does not belong to Variant'
                raise Exception(msg)

        varAtoms = set(varAtoms)
        rings = []

        while varAtoms:
            varAtom = varAtoms.pop()
            rings += varAtom.getRings()

            for varAtoms2 in rings:
                varAtoms = varAtoms - varAtoms2

        return rings

    def checkBaseValences(self):

        for varAtom in self.varAtoms:
            baseValances = len(varAtom.freeValences) - varAtom.charge
            for bond in varAtom.bonds:
                baseValances += BOND_TYPE_VALENCES[bond.bondType]

            if varAtom.isAromatic():
                baseValances += 1

            if varAtom.atom.baseValences != baseValances:
                varAtom.atom.setBaseValences(baseValances)

    def shuffleStereo(self):

        for varAtom in self.varAtoms:
            stereo = varAtom.stereo

            if stereo:
                if len(stereo) != 4:
                    continue

                indices = {}
                for i, va in enumerate(stereo):
                    indices[va] = i

                sortList = [(len(va.neighbours), va.name, va) for va in stereo]
                sortList.sort()

                a, b, c, d = stereo

                perms = [[a, b, c, d], [a, c, d, b], [a, d, b, c],
                         [b, a, d, c], [b, d, c, a], [b, c, a, d],
                         [c, a, b, d], [c, b, d, a], [c, d, a, b],
                         [d, a, c, b], [d, c, b, a], [d, b, a, c]]

                w, x, y, z = [v[2] for v in sortList]

                for p, q, r, s in perms:
                    if p in (y, z) and r in (y, z):
                        varAtom.stereo = [p, q, r, s]
                        break

    def deduceStereo(self):

        for varAtom in self.varAtoms:
            neighbours = list(varAtom.neighbours)

            if len(neighbours) < 4:
                continue

            center = varAtom.coords

            vecs = [(vectorsSubtract(va.coords, center), va) for va in neighbours]
            vec1, va1 = vecs[0]

            dotProds = [(dotProduct(vec, vec1), vec, va) for vec, va in vecs[1:]]
            dotProds.sort()

            dp, vec2, va2 = dotProds[0]

            norm = crossProduct(vec1, vec2)
            len1 = sqrt(dotProduct(norm, norm))

            angles = []
            for dp, vec, va in dotProds[1:]:
                len2 = sqrt(dotProduct(vec, vec)) * len1

                c = dotProduct(vec, norm) / len2
                cp = crossProduct(vec, norm)
                s = sqrt(dotProduct(cp, cp)) / len2

                angle = atan2(s, c)
                angles.append((angle, va))

            angles.sort()

            stereo = [va1, ]
            stereo += [x[1] for x in angles]
            stereo += [va2, ]

            varAtom.stereo = stereo

        self.shuffleStereo()

    def addLink(self, linkType, replaceAtoms):

        compound = self.compound
        compound.isModified = True

        #existing = self.elementDict[LINK]
        hydrogens = [va for va in replaceAtoms if va.element == 'H']
        oxygens = [va for va in replaceAtoms if va.element == 'O']

        if not hydrogens:
            return

        linkH = None
        linkO = None
        bound = None
        context = None

        for o in oxygens:
            oNeighbours = set(o.neighbours)
            for h in hydrogens:
                if h in oNeighbours:
                    linkH = h.atom
                    linkO = o.atom
                    oNeighbours.remove(h)
                    if oNeighbours:
                        boundAtom = oNeighbours.pop()
                        bound = boundAtom.atom
                        context = boundAtom.getContext()
                    break
            else:
                continue
            break

        if not linkH:
            h = hydrogens[0]
            linkH = h.atom
            hNeighbours = set(h.neighbours)

            if hNeighbours:
                boundAtom = hNeighbours.pop()
                bound = boundAtom.atom
                context = boundAtom.getContext()

        variants = list(compound.variants)
        newAtom = None

        for va in bound.varAtoms:
            for va2 in va.neighbours:
                if va2.element == LINK:
                    return va2

        linkMasterAtom = compound.getAtom(LINK, linkType)

        # Replace terminal Hs
        if linkO:
            oldOtherH = []
        else:
            oldOtherH = [a for a in context if a.element == 'H']
            oldOtherH.remove(linkH)

        # New middle Hs
        newOtherH = [Atom(compound, 'H', None) for a in oldOtherH]

        for var in variants:
            atomH = var.atomDict.get(linkH)

            if not atomH:
                continue

            atomO = None
            if linkO:
                atomO = var.atomDict.get(linkO)

                if not atomO:
                    continue

            atomB = None
            contextB = None
            if bound:
                atomB = var.atomDict[bound]

                if not atomB:
                    continue

                contextB = atomB.getContext()
                if contextB != context:
                    continue

            atoms = set(var.varAtoms)
            atoms.remove(atomH)
            coordsH = []

            if atomO:
                coords = atomO.coords
                atoms.remove(atomO)

            else:
                coords = atomH.coords

                for atomH2 in oldOtherH:
                    varAtomH2 = var.atomDict.get(atomH2)
                    coordsH.append(varAtomH2.coords)
                    atoms.remove(varAtomH2)

            newVar = Variant(compound, atoms)

            varAtom = VarAtom(newVar, linkMasterAtom, coords=coords)

            if atomB:
                varAtomB = newVar.atomDict[bound]
                varAtomB.updateValences()
                newVar.getBond(varAtom, varAtomB, autoVar=False)

            if var is self:
                newAtom = varAtom

            for i, newH in enumerate(newOtherH):
                varAtomB = newVar.atomDict[bound]
                varAtomB.updateValences()
                varAtom = VarAtom(newVar, newH, coords=coordsH[i])
                newVar.getBond(varAtom, varAtomB, autoVar=False)

            newVar.updatePolyLink()
            newVar.updateDescriptor()

        # Try auto amide name
        if bound and (bound.element == 'N') and len(newOtherH) == 1:
            if 'H' not in compound.atomDict:
                newOtherH[0].setName('H')

        return newAtom

    def getBond(self, varAtomA, varAtomB, autoVar=True):

        if not varAtomA.freeValences:
            return

        if not varAtomB.freeValences:
            return

        if varAtomA in varAtomB.neighbours:
            common = set(varAtomA.bonds & varAtomB.bonds)
            return common.pop()

        return Bond((varAtomA, varAtomB), autoVar=autoVar)

    def updatePolyLink(self):

        linkNames = [a.name for a in self.elementDict.get(LINK, [])]

        prevLink = [x for x in linkNames if 'prev' in x]
        nextLink = [x for x in linkNames if 'next' in x]

        if prevLink and nextLink:
            self.polyLink = 'middle'
        elif prevLink:
            self.polyLink = 'end'
        elif nextLink:
            self.polyLink = 'start'
        elif linkNames:
            self.polyLink = 'linked'
        else:
            self.polyLink = 'free'

    def updateDescriptor(self):

        self.descriptor = self.getDescriptor()

    def getCommonIsoMass(self):

        mass = 0.0
        for element in self.elementDict:
            if element == LINK:
                continue

            n = len(self.elementDict[element])
            mass += n * ELEMENT_ISO_ABUN[element][0][2]

        return mass

    def getMolFormula(self):

        counts = {}
        for element in self.elementDict:
            if element == LINK:
                continue

            counts[element] = len(self.elementDict[element])

        elements = counts.keys()
        elements.sort()
        if 'H' in elements:
            elements.remove('H')
            elements.insert(0, 'H')

        if 'C' in elements:
            elements.remove('C')
            elements.insert(0, 'C')

        formula = []
        for elem in elements:
            n = counts[elem]
            if n > 1:
                text = '%s%d' % (elem, n)
            else:
                text = elem

            formula.append(text)

        formula = ' '.join(formula)

        return formula

    def getDescriptor(self, ccpnStyle=False):

        if ccpnStyle:
            prot = 'prot'
            deprot = 'deprot'
            link = 'link'
            sep = ':'
            joinStr = ';'

        else:
            prot = '+'
            deprot = '-'
            link = ''
            sep = ''
            joinStr = ','

        neutral = 'neutral'

        equivVars = [v for v in self.compound.variants if v.polyLink == self.polyLink]

        hAtomVars = {}
        stereoTypes = {}

        for var in equivVars:
            for atom in var.varAtoms:
                name = atom.name
                if name not in stereoTypes:
                    stereoTypes[name] = set()

                stereoTypes[name].add(atom.chirality)

                if (atom.element == 'H') and atom.atom.isVariable:
                    if name not in hAtomVars:
                        hAtomVars[name] = set()

                    hAtomVars[name].add(var)
        tags = []
        tagsLink = []
        tagsStereo = []
        tagsProton = []

        # Links

        linkAtoms = self.elementDict.get(LINK, [])
        genLinks = [a for a in linkAtoms
                    if ('prev' not in a.name) \
                    and ('next' not in a.name)]

        for atom in genLinks:
            neighbours = atom.neighbours
            name = ','.join([a.name for a in neighbours])
            tags.append((link, name))
            tagsLink.append((link, name))

        # Protonation
        isNeutral = sum([abs(va.charge) for va in self.varAtoms]) == 0

        # Names of variable atoms
        for name in hAtomVars:

            # Vars that have this hydrogen
            varsA = hAtomVars[name]

            if self in varsA:
                tags.append((prot, name))
                tagsProton.append((prot, name))

            else:
                tags.append((deprot, name))
                tagsProton.append((deprot, name))

        # stereochemistry

        if ccpnStyle:
            stereoDict = {'R': 1, 'S': 2, 'a': 1, 'b': 2}
            for atom in self.varAtoms:
                name = atom.name
                if (atom.chirality) and len(stereoTypes.get(name, [])) > 1:
                    tags.append(('stereo_%d' % stereoDict[atom.chirality], name))
                    tagsStereo.append(('stereo_%d' % stereoDict[atom.chirality], name))

        else:
            for atom in self.varAtoms:
                name = atom.name
                if (atom.chirality) and len(stereoTypes.get(name, [])) > 1:
                    tags.append((atom.chirality, name))
                    tagsStereo.append((atom.chirality, name))

        #if isNeutral and not (tagsStereo or tagsLink):
        #  tags = []
        #  tagsProton = []

        if ccpnStyle:
            tagNames = []
            sortDict = {}
            for cat, name in tags:
                if cat not in sortDict:
                    sortDict[cat] = []

                sortDict[cat].append(name)

            cats = [(VAR_TAG_ORDER[cat], cat) for cat in sortDict.keys()]
            cats.sort()

            for i, cat in cats:
                if cat == 'link':
                    if self.compound.ccpMolType not in ('protein', 'RNA', 'DNA'):
                        continue

                if cat == neutral:
                    tagNames.append(neutral)
                else:
                    names = sortDict[cat]
                    names.sort()
                    tagStr = ','.join(names)
                    tagNames.append('%s%s%s' % (cat, sep, tagStr))

            return str(joinStr.join(tagNames)) or neutral

        else:
            if isNeutral:
                defaultH = neutral
            else:
                defaultH = 'default'

            tagsProton.sort()
            tagsProton = joinStr.join(['%s%s' % x for x in tagsProton]) or defaultH
            tagsStereo.sort()
            tagsStereo = joinStr.join(['(%s)%s' % x for x in tagsStereo]) or 'default'
            tagsLink.sort()
            tagsLink = joinStr.join(['%s%s' % x for x in tagsLink]) or 'none'

            return tagsProton, tagsLink, tagsStereo

    def copyAtoms(self, varAtoms, coords=None, tempNames=True):

        if not varAtoms:
            return

        compound = self.compound
        compound.isModified = True

        cx = 0.0
        cy = 0.0
        n = 0.0

        for atom in varAtoms:
            x, y, z = atom.coords
            cx += x
            cy += y
            n += 1.0

        cx /= n
        cy /= n

        if coords is None:
            x0, y0 = cx, cy
        else:
            x0, y0 = coords

        mapping = {}
        bonds = set()
        groups = set()

        newAtoms = set()
        addList = [(a.name, a) for a in varAtoms]
        addList.sort()

        for name, atom in addList:

            if atom.element == LINK:
                if 'prev' in name:
                    if self.polyLink == 'middle':
                        continue
                    elif self.polyLink == 'end':
                        continue
                if 'next' in name:
                    if self.polyLink == 'middle':
                        continue
                    elif self.polyLink == 'start':
                        continue

            x, y, z = atom.coords
            dx = x - cx
            dy = y - cy

            bonds.update(atom.bonds)
            groups.update(atom.atomGroups)

            if tempNames:
                name = '@%s' % name

            masterAtom = compound.getAtom(atom.element, name, atom.atom.isVariable)
            masterAtom.baseValences = atom.atom.baseValences

            newAtom = VarAtom(self, masterAtom, atom.freeValences,
                              atom.chirality, (x0 + dx, y0 + dy, z),
                              atom.isLabile, atom.charge)
            newAtoms.add(newAtom)

            mapping[atom] = newAtom

        for bond in bonds:
            atomA, atomB = bond.varAtoms
            newAtomA = mapping.get(atomA)
            newAtomB = mapping.get(atomB)

            if newAtomA and newAtomB:
                Bond((newAtomA, newAtomB), bondType=bond.bondType, autoVar=False)

        for group in groups:

            newAtomsG = set()
            for varAtom in group.varAtoms:
                if varAtom not in mapping:
                    break

                newAtomsG.add(mapping[varAtom])

            else:
                AtomGroup(compound, newAtomsG, groupType=group.groupType)

        for varAtom in mapping:
            if varAtom.stereo:
                stereo = []
                for varAtom2 in varAtom.stereo:
                    newAtom = mapping.get(varAtom2)

                    if newAtom:
                        stereo.append(newAtom)
                    else:
                        break

                else:
                    mapping[varAtom].setStereo(stereo)

        for var in self.compound.variants:
            var.updatePolyLink()
            var.updateDescriptor()

        return newAtoms

    def minimise2d(self, atoms=None, maxCycles=250, bondLength=50.0, drawFunc=None):

        from math import sqrt

        allAtoms = list(self.varAtoms)
        if not atoms:
            atoms = set(self.varAtoms)

            if len(atoms) < 2:
                return

            atoms.pop()

        if not atoms:
            return

        compound = self.compound
        compound.isModified = True

        from random import random, shuffle

        cx = 0.0
        cy = 0.0
        cz = 0.0
        for atom in atoms:
            x, y, z = atom.coords
            x += random()
            y += random()
            atom.coords = x, y, z
            cx += x
            cy += y
            cz += x

        n = float(len(atoms))
        cx /= n
        cy /= n
        cz /= n

        #self.minimise3d(atoms, maxCycles*5, bondLength, drawFunc)
        #self.center(atoms, (cx, cy, cz))

        distances = {}
        distances2 = {}
        bondLengths = {}
        getBond = self.getBond

        aromatics = set()
        for varAtom in atoms:
            elem = varAtom.element
            neighbours = varAtom.neighbours
            n = float(len(neighbours))

            for atomGroup in varAtom.atomGroups:
                if atomGroup.groupType == AROMATIC:
                    aromatics.add(atomGroup)

            for varAtom2 in neighbours:
                elem2 = varAtom2.element

                if 'H' in (elem2, elem):
                    bl = 0.75 * bondLength
                else:
                    bond = set(varAtom2.bonds & varAtom.bonds).pop()

                    if bond.bondType in ('double', 'triple'):
                        bl = 0.87 * bondLength
                    else:
                        bl = bondLength

                key = frozenset([varAtom2, varAtom])
                bondLengths[key] = bl

        for group in aromatics:
            varAtoms = group.varAtoms
            n = float(len(varAtoms))
            t = (n - 2.0) * PI / (2.0 * n)
            dist = bondLength * 2.0 * sin(t)

            for varAtom in varAtoms:
                neighbours = [va for va in varAtom.neighbours if va in varAtoms]

                if len(neighbours) == 2:
                    distances2[frozenset(neighbours)] = dist

        b2 = bondLength * bondLength
        r2limit = 4 * b2

        for c in range(maxCycles):
            change = 0.0

            g = 0.005 * float(maxCycles - c) / maxCycles

            for atom in atoms:
                neighbours = atom.neighbours

                if not neighbours:
                    continue

                vx = 0.0
                vy = 0.0
                x, y, z = atom.coords

                for atom2 in allAtoms:  # only neighbours?
                    if atom2 is atom:
                        continue

                    x2, y2, z2 = atom2.coords

                    dx = x - x2
                    dy = y - y2
                    r2 = (dx * dx) + (dy * dy)
                    pair = frozenset([atom, atom2])

                    if pair in distances2:
                        f = distances2[pair] - sqrt(r2)

                    elif atom2 in neighbours:
                        f = bondLengths[pair] - sqrt(r2)

                    elif r2 < r2limit:
                        f = 5e6 / (r2 * r2)

                    else:
                        continue

                    f = min(2.0, max(-2.0, f))
                    vx += dx * f * g
                    vy += dy * f * g

                x += max(min(10.0 * vx, 10.0), -10.0)
                y += max(min(10.0 * vy, 10.0), -10.0)

                atom.coords = (x, y, z)
                change += abs(vx)
                change += abs(vy)

            if (c % 5 == 0) and drawFunc:
                self.center(atoms, (cx, cy, cz))
                drawFunc()

            shuffle(allAtoms)

            # quit early if nothing happens
            if change < 0.01:
                break

        for atom in atoms:
            x, y, z = atom.coords
            atom.setCoords(x, y, 0.0)  # updates all vars
            atom.updateValences()

        if drawFunc:
            drawFunc()

    def getCentroid(self, atoms=None):

        if not atoms:
            atoms = self.varAtoms

        xs = 0.0
        ys = 0.0
        zs = 0.0
        n = 0.0

        for varAtom in atoms:
            x1, y1, z1 = varAtom.coords
            xs += x1
            ys += y1
            zs += z1
            n += 1.0

        if n:
            xs /= n
            ys /= n
            zs /= n
            return (xs, ys, zs)

        else:
            return (0.0, 0.0, 0.0)

    def center(self, atoms=None, origin=None):

        if not atoms:
            atoms = self.varAtoms

        if origin:
            x0, y0, z0 = origin

        else:
            x0 = 0.0
            y0 = 0.0
            z0 = 0.0

        xs, ys, zs = self.getCentroid(atoms)
        xs -= x0
        ys -= y0
        zs -= z0

        for varAtom in atoms:
            x1, y1, z1 = varAtom.coords

            x1 -= xs
            y1 -= ys
            z1 -= zs

            varAtom.coords = x1, y1, z1

    def minimise3d(self, atoms=None, maxCycles=100, bondLength=50.0, drawFunc=None):

        from math import sqrt
        from random import random, shuffle

        allAtoms = list(self.varAtoms)
        if not atoms:
            atoms = set(self.varAtoms)

            if len(atoms) < 2:
                return

            atoms.pop()

        if not atoms:
            return

        compound = self.compound
        compound.isModified = True

        distances = {}

        aromatics = set()
        bl = bondLength * 2.0
        for varAtom in atoms:
            neighbours = [n for n in varAtom.neighbours if n.element != 'H']
            n = float(len(neighbours))

            for varAtom2 in neighbours:
                for varAtom3 in neighbours:

                    if varAtom2 is not varAtom3:

                        if n == 3.0:
                            distances[frozenset([varAtom2, varAtom3])] = bl * 0.8660254
                        else:
                            distances[frozenset([varAtom2, varAtom3])] = bl * 0.5

        for group in aromatics:
            varAtoms = group.varAtoms
            n = float(len(varAtoms))

            for varAtom in varAtoms:
                neighbours = [va for va in varAtom.neighbours if va in varAtoms]

                if len(neighbours) == 2:
                    varAtomA, varAtomB = neighbours
                    distances[frozenset([varAtom, varAtomA])] = bondLength
                    distances[frozenset([varAtom, varAtomB])] = bondLength
                    t = (n - 2.0) * PI / n
                    distances[frozenset([varAtomA, varAtomB])] = bondLength * 2.0 * sin(t)

        cx = 0.0
        cy = 0.0
        cz = 0.0
        for atom in atoms:
            x, y, z = atom.coords
            x += random()
            y += random()
            z += random()
            atom.coords = x, y, z
            cx += x
            cy += y
            cz += z

        n = float(len(atoms))
        cx /= n
        cy /= n
        cz /= n

        b2 = bondLength * bondLength
        r2limit = 4 * b2

        for c in range(maxCycles):
            change = 0.0
            g = 5.0 * float(c) / maxCycles

            for atom in atoms:
                neighbours = atom.neighbours

                if not neighbours:
                    continue

                vx = 0.0
                vy = 0.0
                vz = 0.0
                x, y, z = atom.coords

                for atom2 in allAtoms:  # only neighbours?
                    if atom2 is atom:
                        continue

                    x2, y2, z2 = atom2.coords

                    dx = x - x2
                    dy = y - y2
                    dz = z - z2
                    r2 = max(0.001, (dx * dx) + (dy * dy) + (dz * dz))

                    pair = frozenset([atom, atom2])
                    if pair in distances:
                        dl = 1 * (distances[pair] - sqrt(r2))
                        vx += dx * dl / r2
                        vy += dy * dl / r2
                        vz += dz * dl / r2

                    elif atom2 in neighbours:
                        dl = 1 * (bondLength - sqrt(r2))
                        vx += dx * dl / r2
                        vy += dy * dl / r2
                        vz += dz * dl / r2

                    else:
                        f = 5 * b2 / (r2 * r2)
                        vx += dx * f
                        vy += dy * f
                        vz += dz * f

                    f = dz / r2
                    vz += g * dz * f

                x += max(min(10.0 * vx, 10), -10)
                y += max(min(10.0 * vy, 10), -10)
                z += max(min(10.0 * vz, 10), -10)

                atom.coords = (x, y, z)
                change += vx
                change += vy
                change += vz

            if (c % 5 == 0) and drawFunc:
                self.center(atoms, (cx, cy, cz))
                drawFunc()
            shuffle(allAtoms)

            # quit early if nothing happens
            if abs(change) < 1e-4:
                break

        for atom in atoms:
            x, y, z = atom.coords
            atom.setCoords(x, y, z)  # updates all vars
            atom.updateValences()

        if drawFunc:
            drawFunc()

    # This function snaps the atoms in atoms to suitable bond angles. When determining where to place atoms
    # only already placed atoms are taken into account (i.e. those that are not present in atoms)
    def snapAtomsToGrid(self, atoms=None, prevAtom=None, ignoreHydrogens=True, bondLength=50.0):

        if not atoms:
            atoms = sorted(self.varAtoms, key=lambda atom: atom.name)
            prevX = prevY = prevZ = None
        else:
            if len(atoms) < 1:
                return

        chiralities = []
        for atom in atoms:
            if atom.chirality:
                for c in chiralities:
                    if c[0] == atom.name:
                        break
                else:
                    chiralities.append((atom.name, atom.chirality))

        # Make a separate list of hydrogens, which will be placed last.
        hydrogens = []
        atomsTemp = list(atoms)
        for atom in atomsTemp:
            if atom.element == 'H':
                #if ignoreHydrogens:
                atoms.remove(atom)
                hydrogens.append(atom)

        atom = None
        neighbour = None

        molCnt = 0

        prevAngle = None

        # prevAtom is an already positioned atom and is used as a reference for placing its neighbouring atoms.
        if prevAtom:
            prevX, prevY, prevZ = prevAtom.coords
            neighbours = sorted(prevAtom.neighbours, key=lambda atom: atom.name)
            for neighbour in neighbours:
                if neighbour.element != 'H' and neighbour in atoms:
                    atom = neighbour
                    break
            # Find a reference angle to an already placed atom.
            for neighbour in neighbours:
                if neighbour != prevAtom and neighbour.element != 'H' and neighbour not in atoms:
                    prevAngle = degrees(prevAtom.getBondAngle(neighbour))
                    break

            # If a reference atom was submitted and it is in a ring snap the ring before proceeding to other atoms.
            atom = prevAtom
            rings = sorted(atom.getRings(), key=lambda ring: len(ring), reverse=True)
            atom.snapRings(rings, neighbours, atoms, prevAngle, bondLength)
            atom = None

        while atoms:
            # Find an atom with an already placed neighbour
            for atom in atoms:
                neighbours = sorted(atom.neighbours, key=lambda atom: atom.name)
                for neighbour in neighbours:
                    if neighbour.element != 'H' and neighbour not in atoms:
                        prevX, prevY, prevZ = neighbour.coords
                        prevAtom = neighbour
                        neighbours2 = sorted(neighbour.neighbours, key=lambda atom: atom.name[-1])
                        # Try to find a reference angle (if the neighbour has a neighbour that has been placed).
                        for neighbour2 in neighbours2:
                            if neighbour2 != atom and neighbour2 not in atoms and (not ignoreHydrogens or neighbour2.element != 'H'):
                                prevAngle = round(degrees(neighbour.getBondAngle(neighbour2)), 0)
                                break
                        else:
                            prevAngle = None
                        break
                else:
                    continue
                break
            else:
                prevAtom = None
                atom = None

            if atom and atom in atoms:
                atoms.remove(atom)
            if not atom:
                # Start by placing the atom involved in most rings. This can help avoid clashes.
                atomWithMostRings = None
                mostRings = 0
                for atom in atoms:
                    nRings = len(atom.getRings())
                    if nRings > mostRings:
                        atomWithMostRings = atom
                        mostRings = nRings
                if mostRings > 0:
                    atom = atomWithMostRings
                    atoms.remove(atom)
                else:
                    atom = atoms.pop(0)
                # Set default coordinates since this is the first atom.
                atom.coords = (20 + 250 * molCnt, 20, atom.coords[2])
                molCnt += 1

            angles = []

            neighbours = sorted(atom.neighbours, key=lambda atom: atom.name)
            if prevAtom:
                prevChiral = prevAtom.chirality
                angles = prevAtom.getPreferredBondAngles(prevAngle, None, atoms + [atom])
                if prevChiral and prevChiral.upper() in ('E', 'Z'):
                    for prevNeighbour in prevAtom.neighbours:
                        if prevAtom.getBondToAtom(prevNeighbour).bondType == 'double' and not prevNeighbour in atoms:
                            prio = prevAtom.getPriorities()
                            prioIndex = prio.index(atom)
                            if prioIndex == 0 or (prioIndex == 1 and prio[0] == prevNeighbour):
                                selfHeavy = True
                            else:
                                selfHeavy = False
                            prevPrio = prevNeighbour.getPriorities()
                            for p in prevPrio:
                                if prevAtom != p:
                                    if p not in atoms:
                                        prevAngle = round(degrees(prevAtom.getBondAngle(prevNeighbour)), 0)
                                        angles = prevAtom.getPreferredBondAngles(prevAngle, None, atoms + [atom], ignoreHydrogens)
                                        prevHeavyNeighbourAngle = degrees(p.getBondAngle(prevNeighbour))
                                        if (selfHeavy and prevChiral.upper() in ('Z')) or \
                                                (not selfHeavy and prevChiral.upper() in ('E')):
                                            angles = [round(prevAngle - prevHeavyNeighbourAngle, 0)]
                                        else:
                                            angles = [-round(prevAngle - prevHeavyNeighbourAngle, 0)]
                                    break
                            break

            if not prevAtom or prevX == None or prevY == None:
                prevX, prevY, prevZ = atom.coords
                prevAtom = atom
                prevAngle = None
            else:
                bonds = set(prevAtom.bonds & atom.bonds)
                if len(bonds) > 0:
                    bond = bonds.pop()
                else:
                    msg = 'Variant.snapAtomsToGrid: Cannot find bond between atoms to snap (%s and %s).' % (atom, prevAtom)
                    raise Exception(msg)

                if bond.bondType == 'triple' or bond.bondType == 'double':
                    bl = bondLength * 0.87
                else:
                    bl = bondLength

                prevAngle = atom.snapToGrid(prevAtom, bl, prevAngle, angles, atoms, ignoreHydrogens)
                prevAngle = (180 + prevAngle) % 360

            rings = sorted(atom.getRings(), key=lambda ring: len(ring), reverse=True)
            if len(rings) > 0:
                atom.snapRings(rings, neighbours, atoms, prevAngle, bondLength)

        # Place the hydrogens
        if hydrogens:
            while hydrogens:
                atom = hydrogens.pop()
                # If placing hydrogens bound to a ring make sure that the prevAtom
                # is also in a ring. This makes it possible to avoid hydrogens
                # inside the ring.
                if atom.getRings():
                    for prevAtom in atom.neighbours:
                        if prevAtom.getRings():
                            break
                else:
                    prevAtom = set(atom.neighbours).pop()

                prevX, prevY, prevZ = prevAtom.coords
                neighbours = sorted(prevAtom.neighbours, key=lambda atom: atom.name)
                for neighbour in neighbours:
                    if neighbour != atom and not neighbour in hydrogens:
                        prevAngle = round(degrees(prevAtom.getBondAngle(neighbour)), 0)
                        break

                angles = prevAtom.getPreferredBondAngles(prevAngle, neighbours, hydrogens + [atom], ignoreHydrogens=False)

                atom.snapToGrid(prevAtom, bondLength * 0.75, prevAngle, angles, hydrogens, ignoreHydrogens=False)

        for c in chiralities:
            for a in self.varAtoms:
                if a.name == c[0]:
                    sc = a.getStereochemistry()
                    if sc and sc.upper() != c[1].upper():
                        if sc.upper() in ('R', 'S'):
                            temp = a.stereo[3]
                            a.stereo[3] = a.stereo[1]
                            a.stereo[1] = temp

    # Snap the atoms in a ring to the preferred bond angles.
    def snapRingToGrid(self, ring, anchor=None, prevAngle=None, bondLength=45.0, skippedAtoms=set([])):

        #    ringAtoms = set(ring)
        ringAtoms = sorted(ring, key=lambda atom: atom.name)
        ringSize = len(ringAtoms)

        if ringSize < 3:
            msg = 'Variant.snapRingToGrid: Ring size must be larger than 2'
            raise Exception(msg)

        prevAtom = None

        ringAngle = ((ringSize - 2) * 180) / ringSize

        if anchor and anchor in ringAtoms:
            ringAtoms.remove(anchor)

        for skippedAtom in skippedAtoms:
            if skippedAtom in ringAtoms:
                ringAtoms.remove(skippedAtom)

        # Find a suitable angle of the "anchor atom" relative to a neighbour outside the ring.
        if anchor:
            atom = anchor
            neighbours = anchor.neighbours
            nNeighbours = len(neighbours)
            for neighbour in neighbours:
                if neighbour.element == 'H':
                    nNeighbours -= 1
            angle = (180 - 0.5 * ringAngle)
            if nNeighbours > 3:
                angle /= nNeighbours - 2
            angles = [angle]
            if not prevAngle:
                for neighbour in neighbours:
                    if neighbour in ring and neighbour not in ringAtoms:
                        prevAngle = degrees(atom.getBondAngle(neighbour))
                        break
                    if neighbour in skippedAtoms:
                        d = atom.getAtomDist(neighbour)
                        if abs(d - bondLength) < 0.001:
                            prevAngle = degrees(atom.getBondAngle(neighbour))
                else:
                    if not prevAngle:
                        prevAngle = 330
        else:
            atom = ringAtoms.pop(0)
            prevAngle = 330
            angles = [-ringAngle]

        if len(skippedAtoms) > 1:
            skippedNeighbours = anchor.neighbours & skippedAtoms

            if skippedNeighbours:
                sortedSkippedAtoms = sorted(skippedAtoms, key=lambda atom: atom.name)
                #        for skippedNeighbour in skippedNeighbours:
                #          if sortedSkippedAtoms.index(skippedNeighbour) != 0:
                #            ringAngle = -ringAngle
                #            break
                angles = [-ringAngle, ringAngle]
                anchor = None

        prevAtom = atom
        while ringAtoms:
            neighbours = sorted(prevAtom.neighbours & ring - skippedAtoms, key=lambda atom: atom.name)
            found = False
            atom = None
            if len(neighbours) != 0:
                for atom in neighbours:
                    if atom in ringAtoms:
                        break
            if not atom:
                for atom in ringAtoms:
                    neighbours = atom.neighbours & ring
                    if len(neighbours) > 0:
                        neighbour = neighbours.pop()
                        nextNeighbours = neighbour.neighbours & ring - set(ringAtoms)
                        if atom in nextNeighbours:
                            nextNeighbours.remove(atom)
                        nextNeighbour = nextNeighbours.pop()
                        prevAtom = neighbour
                        prevAngle = degrees(neighbour.getBondAngle(nextNeighbour))
            oldPrevAngle = prevAngle
            prevAngle = atom.snapToGrid(prevAtom, bondLength, prevAngle, angles)
            if not anchor and abs((oldPrevAngle + ringAngle) % 360 - prevAngle) < 1:
                angles = [ringAngle]
                anchor = None
            else:
                angles = [-ringAngle]
            prevAngle = (180 + prevAngle) % 360
            ringAtoms.remove(atom)
            prevAtom = atom

    def autoNameAtoms(self, varAtoms):

        used = self.compound.atomDict
        nonH = [a for a in varAtoms if a.element not in ('H', LINK)]
        hydrogens = [a for a in varAtoms if a.element == 'H']

        if nonH:
            nAtoms = 1
            nPrev = 0
            atom = nonH[0]
            atoms = set([atom, ])
            orderList = [atom]

            while nAtoms != nPrev:
                nPrev = nAtoms
                for atom in list(atoms):
                    for atomB in atom.neighbours:
                        if atomB.element in ('H', LINK):
                            continue

                        if atomB not in atoms:
                            orderList.append(atomB)
                            atoms.add(atomB)

                nAtoms = len(atoms)

            for i, atom in enumerate(orderList):
                atom.setName('@%d%s' % (i, atom.name))

            i = 1
            for atom in orderList:

                name = '%s%d' % (atom.element, i)
                while name in used:
                    i += 1
                    name = '%s%d' % (atom.element, i)

                atom.setName(name)

        if hydrogens:
            for i, atom in enumerate(hydrogens):
                atom.setName('@%d%s' % (i, atom.name))

            for atom in hydrogens:
                for atomB in atom.neighbours:
                    if atomB.element in ('H', LINK):
                        continue

                    totalH = [a for a in atomB.neighbours if a.element == 'H']

                    name = nameBase = 'H%s' % (atomB.name[len(atomB.element):])

                    if len(totalH) > 1:
                        index = totalH.index(atom)
                        number = '%d' % (index + 1)
                        if nameBase[-1].isdigit():
                            name = nameBase + '_' + number
                        else:
                            name = nameBase + number

                        i = 1
                        while name in used:
                            number = '%d' % (i)
                            if nameBase[-1].isdigit():
                                name = nameBase + '_' + number
                            else:
                                name = nameBase + number
                            i += 1

                    if atomB.element != 'C':
                        i = 1
                        while name in used:
                            name = 'H%s_%d' % (atomB.name, i)
                            i += 1

                    i = 1
                    while name in used:
                        name = 'H%d' % (i)
                        i += 1

                    atom.setName(name)
                    break


################


class Atom:

    def __init__(self, compound, element, name, isVariable=False):

        self.compound = compound
        self.element = element
        self.isVariable = isVariable
        self.varAtoms = set()
        self.isDeleted = False
        self.baseValences = ELEMENT_DATA.get(element, ELEMENT_DEFAULT)[0]

        if not name:
            self.defaultName()

        else:
            self.name = name

        compound.isModified = True
        compound.atoms.add(self)
        compound.atomDict[self.name] = self

        if isVariable:
            for varAtom in self.varAtoms:
                var = varAtom.variant
                var.updateDescriptor()

    def __repr__(self):

        return '<Atom %s %s>' % (self.element, self.name)

    def setName(self, name):

        if name == self.name:
            return

        compound = self.compound
        compound.isModified = True
        prevName = self.name

        used = set(compound.atomDict.keys())
        if name in used:
            name = self.defaultName()
            #raise Exception('Atom name "%s" already in use' % name)
            #return

        self.name = name

        neighbours = set()
        for varAtom in self.varAtoms:
            varAtom.name = name
            var = varAtom.variant

            if self.element == LINK:
                var.updatePolyLink()
            else:
                neighbours.update([va.atom for va in varAtom.neighbours])

        if self.isVariable:
            for var in compound.variants:
                var.updateDescriptor()

        if prevName not in compound.atomDict:
            print("Atom Dict missing", prevName)
            nn = compound.atomDict.keys()
            nn.sort()
            print(', '.join(nn))
        else:
            del compound.atomDict[prevName]

        compound.atomDict[name] = self

        for atom in neighbours:
            if atom.element == LINK:
                if ('prev' not in atom.name) and ('next' not in atom.name):
                    atom.setName('link_%s' % name)

    def defaultName(self):

        atoms = self.compound.atoms
        used = set([a.name for a in atoms])

        elem = self.element

        i = 1
        name = '%s%d' % (elem, i)

        while name in used:
            i += 1
            name = '%s%d' % (elem, i)

        self.name = name

        return name

    def setBaseValences(self, n):

        self.baseValences = n
        for varAtom in self.varAtoms:
            varAtom.updateValences()

    def setVariable(self, value=True):

        compound = self.compound
        compound.isModified = True
        variants = list(compound.variants)

        for varAtom in self.varAtoms:
            varAtom.isVariable = value

        if value and not self.isVariable:
            self.isVariable = value
            # if it is variable need duplicate vars +/- this atom

            if self.element == 'H':
                for varAtom in self.varAtoms:
                    varAtom.isLabile = True

            for varA in variants:
                # If a var has this atom
                if self not in varA.atomDict:
                    continue

                varAtomA = varA.atomDict[self]
                bound = [va.atom for va in varAtomA.neighbours if va.element != 'H']

                # make a copy without this atom
                atomsA = set(varA.varAtoms)
                atomsA.remove(varAtomA)

                var = Variant(self.compound, atomsA)

                for atomB in bound:
                    varAtomB = var.atomDict.get(atomB)

                    if varAtomB:
                        varAtomB.setCharge(varAtomB.charge - 1, autoVar=False)

        elif not value:
            self.isVariable = value
            # If it is not variable only need the one eqiv var with this atom

            for varA in variants:
                # If a var has this atom
                if self not in varA.atomDict:
                    continue

                # Remove other vars that are the same, save this atom
                atomsA = set([va.atom for va in varA.varAtoms])
                atomsA.remove(self)

                for varB in variants:
                    if varB is varA:
                        continue

                    atomsB = set([va.atom for va in varB.varAtoms])

                    if atomsA == atomsB:
                        varB.delete()

        for var in self.compound.variants:
            var.updatePolyLink()
            var.updateDescriptor()
            names = [a.name for a in var.varAtoms]
            names.sort()

    def delete(self):

        self.isDeleted = True
        compound = self.compound
        compound.isModified = True
        varAtoms = list(self.varAtoms)

        if self.element == LINK:
            # Delete all vars with same link

            for varAtom in varAtoms:
                if len(self.compound.variants) == 1:
                    break
                else:
                    varAtom.variant.delete()

        for varAtom in varAtoms:
            varAtom.delete()  # deletes bonds and updates any neighbours

        compound.atoms.remove(self)
        del compound.atomDict[self.name]

        for var in self.compound.variants:
            var.updatePolyLink()
            var.updateDescriptor()

        del self


class AtomGroup:

    def __init__(self, compound, varAtoms, groupType):

        self.compound = compound
        self.varAtoms = set(varAtoms)
        self.groupType = groupType
        self.subGroups = set()
        self.variant = list(varAtoms)[0].variant

        compound = self.compound
        compound.isModified = True

        existing = set()
        orphaned = set()
        for varAtom in varAtoms:
            if varAtom.atomGroups:
                existing.update(varAtom.atomGroups)
            else:
                orphaned.add(varAtom)

        if groupType == AROMATIC:
            if existing:
                for group in existing:
                    if group.groupType == AROMATIC:
                        varAtoms2 = set(group.varAtoms)

                        if len(varAtoms) > len(varAtoms2):
                            if not varAtoms2 - varAtoms:
                                group.delete()

                        else:
                            if not varAtoms - varAtoms2:
                                group.delete()

        elif existing:
            # Check union with single other group; replace any
            if len(existing) == 1:
                group = existing.pop()
                if group.groupType != AROMATIC:
                    group.delete()

            # Subgroups only allowed if fill current completely
            # Subgroups must be defined first
            elif orphaned:
                for group in existing:
                    if group.groupType != AROMATIC:
                        group.delete()

            else:
                self.subGroups = existing

        for varAtom in varAtoms:
            varAtom.atomGroups.add(self)

        self.variant.atomGroups.add(self)
        compound.atomGroups.add(self)

        if self.groupType == AROMATIC:
            for varAtom in self.varAtoms:
                for bond in varAtom.bonds:
                    varAtomA, varAtomB = bond.varAtoms

                    if (varAtomA in self.varAtoms) and (varAtomB in self.varAtoms):
                        bond.bondType = 'aromatic'

                varAtom.updateValences()

    def delete(self):

        compound = self.compound
        compound.isModified = True

        for varAtom in self.varAtoms:
            varAtom.atomGroups.remove(self)

        self.variant.atomGroups.remove(self)
        compound.atomGroups.remove(self)

        if self.groupType == AROMATIC:
            for bond in varAtom.bonds:
                varAtomA, varAtomB = bond.varAtoms

                if (varAtomA in self.varAtoms) and (varAtomB in self.varAtoms):
                    bond.bondType = 'single'

            for varAtom in self.varAtoms:
                varAtom.updateValences()

        del self


BOND_TYPE_VALENCES = {'single': 1, 'double': 2, 'aromatic': 1, 'quadruple': 4,
                      'triple': 3, 'singleplanar': 1, 'dative': 1}

BOND_STEREO_DICT = {4: (0, -1, 0, 1),  # tetrahedral
                    5: (0, -1, 0, 1, 0),  # trigonal bipyramidal
                    6: (0, -1, -1, 1, 1, 0),  # octahedral
                    7: (0, -1, -1, 1, 1, 0, 0),  # pentagonal bipyramidal
                    }


class Bond:

    def __init__(self, varAtoms, bondType='single', autoVar=True):

        varAtomA, varAtomB = varAtoms

        if varAtomA.variant is not varAtomB.variant:
            raise Exception('VarAtom mismatch in bond formation %s-%s' % (varAtomA.name, varAtomB.name))

        self.varAtoms = set(varAtoms)

        self.variant = variant = varAtomA.variant
        self.compound = self.variant.compound
        self.compound.isModified = True
        self.direction = varAtomA if bondType == 'dative' else None

        varAtomA.bonds.add(self)
        varAtomB.bonds.add(self)

        self.bondType = bondType
        self.removeDuplicates()

        varAtomA.updateValences()  # Need this before auto varing
        varAtomB.updateValences()

        variant.bonds.add(self)
        varAtomA.updateNeighbours()
        varAtomB.updateNeighbours()

        nameA = varAtomA.name
        nameB = varAtomB.name
        atomA = varAtomA.atom
        atomB = varAtomB.atom

        elementA = varAtomA.element
        elementB = varAtomB.element

        nameLink = None
        nameH = None
        if (elementA == LINK) and (nameA == LINK):
            nameLink = (varAtomA, varAtomB)
        elif (elementB == LINK) and (nameB == LINK):
            nameLink = (varAtomB, varAtomA)
        elif (elementA == 'H') and nameB:
            nameH = (varAtomA, varAtomB)
        elif (elementB == 'H') and nameA:
            nameH = (varAtomB, varAtomA)

        if nameLink:
            varAtom1, varAtom2 = nameLink
            name = varAtom2.name or varAtom2.element
            varAtom1.atom.setName('%s_%s' % (LINK, name))

        elif nameH and autoVar:
            varAtom1, varAtom2 = nameH
            name = varAtom2.name
            if name.startswith(varAtom2.element):
                name = name[len(varAtom2.element):]

            if name:
                firstName = 'H' + name
                hydrogens = [a for a in varAtom2.neighbours if a.element == 'H']

                if len(hydrogens) > 1:
                    variant.autoNameAtoms(hydrogens)

        if autoVar:
            failedVars = set()
            for var in list(self.compound.variants):
                if var is not variant:
                    atomDict = var.atomDict
                    varAtomC = atomDict.get(atomA)
                    varAtomD = atomDict.get(atomB)

                    if varAtomC and varAtomD:  # Both exist in this var
                        getBond = var.getBond(varAtomC, varAtomD, autoVar=False)

                        if not getBond:
                            if varAtomC not in varAtomD.neighbours:
                                failedVars.add(var)

                    elif varAtomC and not varAtomC.neighbours:
                        varAtomC.delete()  # E.g. proton not in this link var

                    elif varAtomD and not varAtomD.neighbours:
                        varAtomD.delete()  # E.g. proton not in this link var

            for var in failedVars:
                var.delete()

            if elementA == 'O' and elementB == 'H':
                self.checkCarboxylVar(varAtomA, varAtomB)

            elif elementB == 'O' and elementA == 'H':
                self.checkCarboxylVar(varAtomB, varAtomA)

            elif elementA == 'N' and elementB == 'H':
                self.checkAmineVar(varAtomA, varAtomB)

            elif elementB == 'N' and elementA == 'H':
                self.checkAmineVar(varAtomB, varAtomA)

        varAtomA.updateValences()
        varAtomB.updateValences()

    def __repr__(self):

        aNames = [a.name for a in self.varAtoms]
        aNames.sort()
        aName = '-'.join(aNames)

        return '<Bond %s %s>' % (aName, self.bondType)

    def checkCarboxylVar(self, oAtom, hAtom):

        neighbours = set(oAtom.neighbours)
        neighbours.remove(hAtom)

        if not neighbours:
            return

        other = neighbours.pop()

        if other.element == 'C':
            neighbours2 = set(other.neighbours)
            neighbours2.remove(oAtom)
            variant = oAtom.variant
            compound = variant.compound
            bondsC = set(other.bonds)

            for atom in neighbours2:
                if atom.element == 'O':
                    bondsO = set(atom.bonds)
                    common = bondsO & bondsC
                    if not common:
                        continue

                    if common.pop().bondType != 'double':
                        continue

                    hAtom.atom.setVariable(True)

                    for varAtom in oAtom.atom.varAtoms:
                        if varAtom.freeValences:
                            varAtom.setCharge(-1)

                    for var in compound.variants:
                        var.updatePolyLink()
                        var.updateDescriptor()

    def checkAmineVar(self, nAtom, hAtom):

        neighbours = nAtom.neighbours
        hydrogens = [a for a in neighbours if a.element == 'H']

        if len(hydrogens) > 2 and len(neighbours) == 4:
            compound = nAtom.variant.compound
            hAtom.setVariable(True)

            for varAtom in nAtom.atom.varAtoms:
                if varAtom.freeValences:
                    varAtom.setCharge(0)

            for var in compound.variants:
                var.updatePolyLink()
                var.updateDescriptor()

    def setBondType(self, bondType):

        if bondType != self.bondType:
            compound = self.compound
            compound.isModified = True

            varAtomA, varAtomB = self.varAtoms
            nValPrev = BOND_TYPE_VALENCES[self.bondType]
            nValNext = BOND_TYPE_VALENCES[bondType]
            added = nValNext - nValPrev

            while added > 0:
                if varAtomA.freeValences:
                    varAtomA.freeValences.pop()

                if varAtomB.freeValences:
                    varAtomB.freeValences.pop()

                added -= 1

            while added < 0:
                varAtomA.freeValences.append(0.0)
                varAtomB.freeValences.append(0.0)
                added += 1

            if bondType == 'dative':
                if self.direction is varAtomA:
                    self.direction = varAtomB
                else:
                    self.direction = varAtomA

            if added:
                varAtomA.updateValences()
                varAtomB.updateValences()

            self.bondType = bondType

    def removeDuplicates(self):

        varAtomA, varAtomB = self.varAtoms

        nVals = int(BOND_TYPE_VALENCES[self.bondType])

        # Could trap errors here

        commonBonds = varAtomA.bonds & varAtomB.bonds
        n = len(commonBonds)

        if n > 1:
            for bond in commonBonds:
                if bond is not self:
                    bond.delete()

    def delete(self):

        compound = self.compound
        compound.isModified = True

        varAtomA, varAtomB = self.varAtoms
        varAtomA.variant.bonds.remove(self)

        varAtomA.bonds.remove(self)
        varAtomB.bonds.remove(self)

        varAtomA.stereo = []
        varAtomB.stereo = []

        varAtomA.freeValences.append(0.0)
        varAtomB.freeValences.append(0.0)

        groups = varAtomA.atomGroups | varAtomB.atomGroups
        for group in groups:
            if group.groupType == AROMATIC:
                if self.bondType == AROMATIC:
                    group.delete()
            else:
                group.delete()

        varAtomA.updateValences()
        varAtomB.updateValences()

        varAtomA.updateNeighbours()
        varAtomB.updateNeighbours()

        del self

    def deleteAll(self):

        atoms = set([va.atom for va in self.varAtoms])

        delBonds = []
        for var in self.compound.variants:
            for bond in var.bonds:
                atoms2 = set([va.atom for va in bond.varAtoms])

                if atoms == atoms2:
                    delBonds.append(bond)

        for bond in delBonds:
            bond.delete()


def loadCompoundPickle(fileName):
    pass


class Compound:

    def __init__(self, name):

        self.name = name
        self.keywords = set()
        self.details = None
        self.variants = set()
        self.atoms = set()
        self.atomDict = {}
        self.atomGroups = set()
        self.defaultVars = set()
        self.ccpCode = None
        self.ccpMolType = 'other'
        self.isModified = True

    def hasSubGraph(self, fragement):

        pass

    def getAtom(self, element, name, isVariable=False):

        atom = self.atomDict.get(name)
        print(atom, 'atom')
        if not atom:
            atom = Atom(self, element, name, isVariable)
        print('atomatom', atom)
        return atom

    def getCcpMolType(self):
        pass

    def save(self, filePath):
        pass

    def delete(self):

        for var in list(self.variants):
            var.delete()

        del self

    def center(self, origin=None):

        if origin:
            x0, y0, z0 = origin

        else:
            x0 = 0.0
            y0 = 0.0
            z0 = 0.0

        xs = 0.0
        ys = 0.0
        zs = 0.0
        n = 0.0

        for atom in self.atoms:
            for varAtom in atom.varAtoms:
                x1, y1, z1 = varAtom.coords
                xs += x1
                ys += y1
                zs += z1
                n += 1.0

        if n:
            xs /= n
            ys /= n
            zs /= n

            xs -= x0
            ys -= y0
            zs -= z0

            for atom in self.atoms:
                for varAtom in atom.varAtoms:
                    x1, y1, z1 = varAtom.coords

                    x1 -= xs
                    y1 -= ys
                    z1 -= zs

                    varAtom.coords = x1, y1, z1

    def setAromatic(self, atoms):

        atoms = set([a for a in atoms if a.element != 'H'])
        self.unsetAromatic(atoms)

        # TBD check ring

        for var in self.variants:
            varAtoms = set([var.atomDict.get(a) for a in atoms]) - set([None, ])

            rings = var.getRings(varAtoms)

            for varAtoms2 in rings:
                AtomGroup(self, varAtoms2, AROMATIC)

    def unsetAromatic(self, atoms):

        atoms = set([a for a in atoms if a.element != 'H'])

        for atom in atoms:
            for varAtom in atom.varAtoms:
                groups = [g for g in varAtom.atomGroups if g.groupType == AROMATIC]
                for group in groups:
                    group.delete()

    def setAtomGroup(self, atoms, groupType):

        self.unsetAtomGroup(atoms, groupType)

        elements = set([a.element for a in atoms])

        for elem in elements:
            atomsB = [a for a in atoms if a.element == elem]
            nAtoms = len(atomsB)
            if nAtoms < 2:
                continue

            for var in self.variants:
                varAtoms = set([var.atomDict.get(a) for a in atomsB])

                if None in varAtoms:
                    # This var cannot support group
                    continue

                AtomGroup(self, varAtoms, groupType)

    def unsetAtomGroup(self, atoms, groupType):

        for atom in atoms:
            for varAtom in atom.varAtoms:
                for group in list(varAtom.atomGroups):
                    if group.groupType == groupType:
                        group.delete()

    def setAtomsEquivalent(self, atoms):

        self.setAtomGroup(atoms, EQUIVALENT)

    def setAtomsProchiral(self, atoms):

        self.setAtomGroup(atoms, PROCHIRAL)

    def unsetAtomsEquivalent(self, atoms):

        self.unsetAtomGroup(atoms, EQUIVALENT)

    def unsetAtomsProchiral(self, atoms):

        self.unsetAtomGroup(atoms, PROCHIRAL)

    def resolveTempAtomNames(self):

        used = self.atomDict
        for var in self.variants:
            renameVarAtoms = []

            for varAtom in var.varAtoms:
                name = varAtom.name

                if name[0] == '@':
                    if name[1:] in used:
                        renameVarAtoms.append(varAtom)
                    else:
                        varAtom.setName(name[1:])

            if renameVarAtoms:
                var.autoNameAtoms(renameVarAtoms)

    def copyVarAtoms(self, atoms, coords=None):

        if not atoms:
            return

        for var in self.variants:
            var.copyAtoms(atoms, coords=coords)

        self.resolveTempAtomNames()
        self.isModified = True

    def copyCompound(self, compoundB, coords=None, refVar=None):

        if not coords:
            coords = (0, 0)

        atomVarsA = [(list(v.varAtoms), v) for v in self.variants]
        polyLinks = set([v.polyLink for v in self.variants]) - set(['none', 'free'])
        newRefAtoms = []

        for atomsA, varA in atomVarsA:

            i = 0
            for varB in compoundB.variants:
                if polyLinks and (varB.polyLink not in ('none', 'free')):
                    continue

                atomsB = varB.varAtoms

                if i == 0:
                    if refVar and varA is refVar:
                        newRefAtoms = varA.copyAtoms(atomsB, coords)

                    else:
                        varA.copyAtoms(atomsB, coords)

                else:
                    varC = Variant(self, atomsA)
                    varC.copyAtoms(atomsB, coords)

                i += 1

        self.resolveTempAtomNames()
        self.isModified = True

        return newRefAtoms

    def addHydrogens(self):

        hydrogens = set()

        for var in self.variants:
            for varAtom in set(var.varAtoms):
                if varAtom.element == 'H':
                    continue

                newAtoms = []
                x, y, z = varAtom.coords

                for angle in list(varAtom.freeValences):
                    x2 = x + 34.0 * sin(angle)
                    y2 = y + 34.0 * cos(angle)

                    masterAtom = Atom(self, 'H', None)
                    VarAtom(var, masterAtom, coords=(x2, y2, 0.0))  # All vars

                    hydrogen = var.atomDict[masterAtom]
                    newAtoms.append(hydrogen)
                    hydrogens.add(hydrogen)

                for newAtom in newAtoms:
                    Bond((varAtom, newAtom), autoVar=True)

        return hydrogens


def importChemComp(chemComp, variantInd: int = 0):
    # Main Compound

    ccpCode = chemComp.ccpCode
    molType = chemComp.molType
    memopsRoot = chemComp.root
    chemCompCoord = memopsRoot.findFirstChemCompCoord(molType=molType, ccpCode=ccpCode)

    name = chemComp.name or '%s:%s' % (molType, ccpCode)

    compound = Compound(name)
    compound.ccpCode = ccpCode
    compound.ccpMolType = molType

    # Main Atoms

    atomMap = {}
    aromaticAtoms = set()
    for chemAtom in chemComp.chemAtoms:

        if chemAtom.className == 'LinkAtom':
            element = LINK

            if ('prev' in chemAtom.name) or ('next' in chemAtom.name):
                name = chemAtom.name

            else:
                linkEnd = chemAtom.boundLinkEnd
                name = 'link_' + linkEnd.boundChemAtom.name

        else:
            element = chemAtom.chemElement.symbol
            name = chemAtom.name

        if name not in atomMap:
            atom = Atom(compound, element, name)
            atomMap[name] = atom

    # Vars and VarAtoms
    if chemCompCoord:
        getVarCoord = chemCompCoord.findFirstChemCompVarCoord

    for chemCompVar in chemComp.chemCompVars:
        varAtomMap = {}
        variant = Variant(compound)
        variant.polyLink = chemCompVar.linking

        if chemCompVar.isDefaultVar:
            variant.setDefault(True)

        descriptor = chemCompVar.descriptor
        descs = descriptor.split(';')

        varProts = set()
        for desc in descs:
            if 'prot' in desc:
                hNames = desc.split(':')[1]
                varProts.update(hNames.split(','))

        if chemCompCoord:
            chemCompVarCoord = getVarCoord(linking=chemCompVar.linking,
                                           descriptor=chemCompVar.descriptor)
            if not chemCompVarCoord:
                chemCompVarCoord = getVarCoord(linking=chemCompVar.linking)

            if not chemCompVarCoord:
                chemCompVarCoord = getVarCoord()

        else:
            chemCompVarCoord = None

        chemAtoms = chemCompVar.chemAtoms
        for chemAtom in chemAtoms:
            if chemAtom.className == 'LinkAtom':
                labile = None
                chirality = None

                if ('prev' in chemAtom.name) or ('next' in chemAtom.name):
                    name = chemAtom.name
                else:
                    linkEnd = chemAtom.boundLinkEnd
                    name = 'link_' + linkEnd.boundChemAtom.name

            else:
                name = chemAtom.name
                labile = chemAtom.waterExchangeable
                chirality = chemAtom.chirality

                if chirality == 'unknown':
                    chirality = None

                if not chirality:
                    subTypes = chemComp.findAllChemAtoms(name=chemAtom.name)

                    if len(subTypes) > 1:
                        stereoTag = 'stereo_%d' % chemAtom.subType

                        for tag in descs:
                            if tag.startswith(stereoTag):

                                if chemAtom.name in tag:

                                    if (chemAtom.subType - 1) % 2 == 0:
                                        chirality = 'a'
                                    else:
                                        chirality = 'b'

                                break

            coords = (0.0, 0.0, 0.0)
            if chemCompVarCoord:
                chemAtomCoord = chemCompVarCoord.findFirstChemAtomCoord(chemAtom=chemAtom)

                if chemAtomCoord:
                    coords = (chemAtomCoord.x * 50,
                              chemAtomCoord.y * 50,
                              chemAtomCoord.z * 50)

            atom = atomMap[name]
            if not atom.isVariable:
                atom.isVariable = atom.name in varProts

            varAtom = VarAtom(variant, atom, chirality=chirality,
                              coords=coords, isLabile=labile)
            varAtomMap[chemAtom] = varAtom

        # Make bond for each var

        for chemBond in chemComp.chemBonds:
            varAtoms = [varAtomMap.get(a) for a in chemBond.chemAtoms]

            if None in varAtoms:
                # Bond only in different var
                continue

            bond = Bond(varAtoms, chemBond.bondType, autoVar=False)

            if chemBond.bondType == 'aromatic':
                atomsA = [atomMap[a.name] for a in chemBond.chemAtoms]
                aromaticAtoms.update(atomsA)

            if chemBond.bondType == 'dative':
                if varAtoms[1].element in 'CNPOSFClI':
                    bond.direction = varAtoms[0]
                else:
                    bond.direction = varAtoms[1]

        variant.updateDescriptor()

    # AtomGroups

    # Simple first

    for chemAtomSet in chemComp.chemAtomSets:
        if chemAtomSet.chemAtomSets:
            continue

        chemAtomsB = chemAtomSet.chemAtoms
        atoms = set([atomMap[ca.name] for ca in chemAtomsB])

        for var in compound.variants:
            varAtoms = set([var.atomDict.get(a) for a in atoms])

            if None in varAtoms:
                # This var cannot hold the group
                continue

            if chemAtomSet.isEquivalent is True:
                groupType = EQUIVALENT
            elif chemAtomSet.isProchiral:
                groupType = NONSTEREO
            elif chemAtomSet.isEquivalent is None:
                groupType = EQUIVALENT
            else:
                continue

            AtomGroup(compound, varAtoms, groupType)

    # Compound second

    for chemAtomSet in chemComp.chemAtomSets:
        if not chemAtomSet.chemAtomSets:
            continue

        chemAtomsB = set()
        for chemAtomSetB in chemAtomSet.chemAtomSets:
            chemAtomsB.update(chemAtomSetB.chemAtoms)
        atoms = set([atomMap[ca.name] for ca in chemAtomsB])

        for var in compound.variants:
            varAtoms = set([var.atomDict.get(a) for a in atoms])

            if None in varAtoms:
                # This var cannot hold the group
                continue

            if chemAtomSet.isEquivalent is True:
                groupType = EQUIVALENT
            elif chemAtomSet.isProchiral:
                groupType = NONSTEREO
            elif chemAtomSet.isEquivalent is None:
                groupType = EQUIVALENT
            else:
                continue

            # Automatically fills subGroups that were defined first
            AtomGroup(compound, varAtoms, groupType)

    # Curate charges and link names

    for atom in compound.atoms:
        elem = atom.element

        if elem in (LINK, 'C', 'H'):
            name = atom.name
            if elem == LINK and 'prev' not in name and 'next' not in name:
                if atom.varAtoms:
                    varAtom = list(atom.varAtoms)[0]

                    if varAtom.neighbours:
                        bound = list(varAtom.neighbours)[0]
                        atom.setName('link_' + bound.name)

            continue

        defaultVal = ELEMENT_DATA.get(elem, ELEMENT_DEFAULT)[0]

        for varAtom in atom.varAtoms:

            for varAtomB in varAtom.neighbours:
                if varAtomB.freeValences:
                    break

            else:
                nVal = sum([BOND_TYPE_VALENCES[b.bondType] for b in varAtom.bonds])
                charge = nVal - defaultVal

                if charge:
                    varAtom.setCharge(charge, autoVar=False)

    # Aromatics

    if aromaticAtoms:
        compound.setAromatic(aromaticAtoms)

    compound.center((0.0, 0.0, 0.0))
    for var in compound.variants:
        var.checkBaseValences()

    return compound


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test Table', setLayout=True)

    smilesText = 'CC(=O)OC1=CC=CC=C1C(=O)O'
    compoundView = CompoundView(popup, smiles=smilesText, )
    c = compoundView.compound
    print([a.groupType for a in c.atomGroups])
    print([a.varAtoms for a in c.atomGroups])
    print([a.subGroups for a in c.atomGroups])
    popup.getLayout().addWidget(compoundView)
    compoundView.centerView()
    compoundView.updateAll()

    popup.show()
    popup.raise_()
    app.start()
