"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:24 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2023-11-09 18:12:34 +0000 (Thu, November 9, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.exporters1D.exportDialogPyQTGraph import UiForm

from ccpn.ui.gui.exporters1D.OpenGLImageExporter import OpenGLImageExporter
from ccpn.ui.gui.exporters1D.OpenGLPDFExporter import OpenGLPDFExporter
from ccpn.ui.gui.exporters1D.OpenGLSVGExporter import OpenGLSVGExporter
from ccpn.ui.gui.exporters1D.SVGExporter import SVGExporter
from ccpn.ui.gui.exporters1D.TextExporter import TextExporter
from ccpn.ui.gui.exporters1D.ImageExporter import ImageExporter
from ccpn.util.Common import makeIterableList


GLType = 'GL'
Default = 'Default'

ExporterTypes = {GLType : [OpenGLImageExporter, OpenGLPDFExporter, OpenGLSVGExporter],  #[ImageExporter, SVGExporter, TextExporter],
                 Default: [ImageExporter, SVGExporter, TextExporter],
                 }


class CustomExportDialog(QtWidgets.QDialog):
    def __init__(self, scene, titleName=None, exportType=Default):
        super().__init__()
        self.setVisible(False)
        self.shown = False
        self.currentExporter = None
        self.scene = scene
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint)

        # self.selectBox = QtWidgets.QGraphicsRectItem()
        # self.selectBox.setPen(pg.functions.mkPen('y', width=3, style=QtCore.Qt.DashLine))
        # self.selectBox.hide()
        # self.scene.addItem(self.selectBox)

        self.ui = UiForm()
        self.ui.setupUi(self)
        self._setUiStyle()

        if titleName is not None:
            self.setWindowTitle('Export ' + titleName)

        self.exporterType = exportType

        self.ui.closeBtn.clicked.connect(self.close)
        self.ui.exportBtn.clicked.connect(self.exportClicked)
        self.ui.copyBtn.clicked.connect(self.copyClicked)
        self.ui.itemTree.currentItemChanged.connect(self.exportItemChanged)
        self.ui.formatList.currentItemChanged.connect(self.exportFormatChanged)

    def _setUiStyle(self):

        self.ui.label.hide()  #hide this part not needed
        self.ui.itemTree.hide()  #hide this part not needed

        self.ui.label_2.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.ui.label_3.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.ui.paramTree.setAlternatingRowColors(False)

    def updateFormatList(self):

        current = self.ui.formatList.currentItem()
        if current is not None:
            current = str(current.text())
        self.ui.formatList.clear()
        self.exporterClasses = {}

        gotCurrent = False
        if self.exporterType is not None:
            exporterList = ExporterTypes[self.exporterType]
        else:
            exporterList = []

        if exporterList:
            for exp in exporterList:
                self.ui.formatList.addItem(exp.Name)

                self.exporterClasses[exp.Name] = exp
                if exp.Name == current:
                    self.ui.formatList.setCurrentRow(self.ui.formatList.count() - 1)
                    gotCurrent = True

        if not gotCurrent:
            self.ui.formatList.setCurrentRow(0)

    def show(self, item=None):
        if item is not None:
            ## Select next exportable parent of the item originally clicked on
            while not isinstance(item, pg.ViewBox) and not isinstance(item, pg.PlotItem) and item is not None:
                item = item.parentItem()
            ## if this is a ViewBox inside a pg.PlotItem, select the parent instead.
            if isinstance(item, pg.ViewBox) and isinstance(item.parentItem(), pg.PlotItem):
                item = item.parentItem()
            self.updateItemList(select=item)

        self.setVisible(True)
        self.activateWindow()
        self.raise_()
        self.exec()
        if not self.shown:
            self.shown = False
            vcenter = self.scene.getViewWidget().geometry().center()
            a = int(vcenter.x() - self.width() / 2)
            b = int(vcenter.y() - self.height() / 2)
            w = int(self.width())
            h = int(self.height())
            self.setGeometry(a, b, w, h)

    def updateItemList(self, select=None):
        self.ui.itemTree.clear()
        si = QtWidgets.QTreeWidgetItem(["Entire Scene"])
        si.gitem = self.scene
        self.ui.itemTree.addTopLevelItem(si)
        self.ui.itemTree.setCurrentItem(si)
        si.setExpanded(True)
        for child in self.scene.items():
            if child.parentItem() is None:
                self.updateItemTree(child, si, select=select)

    def updateItemTree(self, item, treeItem, select=None):
        si = None
        if isinstance(item, pg.ViewBox):
            si = QtWidgets.QTreeWidgetItem(['ViewBox'])
        elif isinstance(item, pg.PlotItem):
            si = QtWidgets.QTreeWidgetItem(['Plot'])

        if si is not None:
            si.gitem = item
            treeItem.addChild(si)
            treeItem = si
            if si.gitem is select:
                self.ui.itemTree.setCurrentItem(si)

        for ch in item.childItems():
            self.updateItemTree(ch, treeItem, select=select)

    def exportItemChanged(self, item, prev):
        if item is None:
            return
        if item.gitem is self.scene:
            newBounds = self.scene.views()[0].viewRect()
        else:
            newBounds = item.gitem.sceneBoundingRect()
        # self.selectBox.setRect(newBounds)
        # self.selectBox.show()
        self.updateFormatList()

    def exportFormatChanged(self, item, prev):
        if item is None:
            self.currentExporter = None
            self.ui.paramTree.clear()
            return
        expClass = self.exporterClasses[str(item.text())]
        exp = expClass(item=self.ui.itemTree.currentItem().gitem)
        params = exp.parameters()
        if params is None:
            self.ui.paramTree.clear()
        else:
            self.ui.paramTree.setParameters(params)
        self.currentExporter = exp
        self.ui.copyBtn.setEnabled(exp.allowCopy)

    def exportClicked(self):
        # self.selectBox.hide()
        self.currentExporter.export()
        self.reject()

    def copyClicked(self):
        # self.selectBox.hide()
        self.currentExporter.export(copy=True)

    def close(self):
        # self.selectBox.setVisible(False)
        # self.selectBox.hide()
        self.setVisible(False)
        self.reject()


class CustomGLExportDialog(QtWidgets.QDialog):
    def __init__(self, GLWidget, titleName=None, exportType=GLType):
        QtWidgets.QDialog.__init__(self)
        self.setVisible(False)
        self.shown = False
        self.currentExporter = None
        # self.scene = scene
        self.GLWidget = GLWidget
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint)

        # self.selectBox = QtWidgets.QGraphicsRectItem()
        # self.selectBox.setPen(pg.functions.mkPen('y', width=3, style=QtCore.Qt.DashLine))
        # self.selectBox.hide()
        # self.scene.addItem(self.selectBox)

        self.ui = UiForm()
        self.ui.setupUi(self)
        self._setUiStyle()

        if titleName is not None:
            self.setWindowTitle('Export ' + titleName)

        self.exportType = exportType

        self.ui.closeBtn.clicked.connect(self.close)
        self.ui.exportBtn.clicked.connect(self.exportClicked)
        self.ui.copyBtn.clicked.connect(self.copyClicked)
        self.ui.itemTree.currentItemChanged.connect(self.exportItemChanged)
        self.ui.formatList.currentItemChanged.connect(self.exportFormatChanged)

    def _setUiStyle(self):

        self.ui.label.hide()  # hide this part not needed
        self.ui.itemTree.hide()  # hide this part not needed

        self.ui.label_2.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.ui.label_3.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.ui.paramTree.setAlternatingRowColors(False)

    def updateFormatList(self):

        current = self.ui.formatList.currentItem()
        if current is not None:
            current = str(current.text())
        self.ui.formatList.clear()
        self.exporterClasses = {}

        gotCurrent = False
        if self.exportType is not None:
            exporterList = ExporterTypes[self.exportType]
        else:
            exporterList = []

        if exporterList:
            for exp in exporterList:
                self.ui.formatList.addItem(exp.Name)

                self.exporterClasses[exp.Name] = exp
                if exp.Name == current:
                    self.ui.formatList.setCurrentRow(self.ui.formatList.count() - 1)
                    gotCurrent = True

        if not gotCurrent:
            self.ui.formatList.setCurrentRow(0)

    def show(self, item=None):
        if item is not None:
            ## Select next exportable parent of the item originally clicked on
            while not isinstance(item, pg.ViewBox) and not isinstance(item, pg.PlotItem) and item is not None:
                item = item.parentItem()
            ## if this is a ViewBox inside a pg.PlotItem, select the parent instead.
            if isinstance(item, pg.ViewBox) and isinstance(item.parentItem(), pg.PlotItem):
                item = item.parentItem()
            self.updateItemList(select=item)

        self.setVisible(True)
        self.activateWindow()
        self.raise_()
        self.exec()

    def updateItemList(self, select=None):
        self.ui.itemTree.clear()
        si = QtWidgets.QTreeWidgetItem(["Entire Scene"])
        si.gitem = self.GLWidget  #scene
        self.ui.itemTree.addTopLevelItem(si)
        self.ui.itemTree.setCurrentItem(si)
        si.setExpanded(True)
        # for child in self.scene.items():
        #   if child.parentItem() is None:
        #     self.updateItemTree(child, si, select=select)

    def updateItemTree(self, item, treeItem, select=None):
        return

        si = None
        if isinstance(item, pg.ViewBox):
            si = QtWidgets.QTreeWidgetItem(['ViewBox'])
        elif isinstance(item, pg.PlotItem):
            si = QtWidgets.QTreeWidgetItem(['Plot'])

        if si is not None:
            si.gitem = item
            treeItem.addChild(si)
            treeItem = si
            if si.gitem is select:
                self.ui.itemTree.setCurrentItem(si)

        for ch in item.childItems():
            self.updateItemTree(ch, treeItem, select=select)

    def exportItemChanged(self, item, prev):
        if item is None:
            return

        # if item.gitem is self.scene:
        #   newBounds = self.scene.views()[0].viewRect()
        # else:
        #   newBounds = item.gitem.sceneBoundingRect()

        # self.selectBox.setRect(newBounds)
        # self.selectBox.show()
        self.updateFormatList()

    def exportFormatChanged(self, item, prev):
        if item is None:
            self.currentExporter = None
            self.ui.paramTree.clear()
            return
        expClass = self.exporterClasses[str(item.text())]
        exp = expClass(item=self.ui.itemTree.currentItem().gitem)
        params = exp.parameters()
        if params is None:
            self.ui.paramTree.clear()
        else:
            self.ui.paramTree.setParameters(params)
        self.currentExporter = exp
        self.ui.copyBtn.setEnabled(exp.allowCopy)

    def exportClicked(self):
        # self.selectBox.hide()
        self.currentExporter.export()
        self.reject()

    def copyClicked(self):
        # self.selectBox.hide()
        self.currentExporter.export(copy=True)

    def close(self):
        # self.selectBox.setVisible(False)
        # self.selectBox.hide()
        self.setVisible(False)
        self.reject()
