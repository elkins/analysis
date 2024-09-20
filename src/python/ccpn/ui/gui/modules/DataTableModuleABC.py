# import pandas as pd
# from ccpn.ui.gui.modules.CcpnModule import CcpnModule
# from ccpn.ui.gui.widgets.GuiTable import GuiTable, _getValueByHeader, _setValueByHeader
# from ccpn.ui.gui.widgets.Column import Column, ColumnClass
# from PyQt5 import QtGui, QtWidgets, QtCore, QtOpenGL
# from ccpn.ui.gui.widgets.Label import Label
# from ccpn.ui.gui.widgets.Frame import Frame
# from ccpn.ui.gui.widgets.DropBase import DropBase
# from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
#
#
# ALL = '<all>'
#
#
# class GuiDataTableBC(GuiTable):
#     """
#
#     """
#     className = 'GuiDataTableBC'
#
#     OBJECT = 'object'
#     TABLE = 'table'
#
#     def __init__(self, dataTable, parent=None, mainWindow=None, moduleParent=None,
#                  allowRowDragAndDrop=True,
#                  **kwds):
#         self.mainWindow = mainWindow
#         self.dataTable = dataTable
#
#         super().__init__(parent=parent,
#                          mainWindow=self.mainWindow,
#                          dataFrameObject=None,
#                          setLayout=True,
#                          autoResize=True, multiSelect=True,
#                          selectionCallback=self.selection,
#                          actionCallback=self.action,
#                          checkBoxCallback=self.actionCheckBox,
#                          allowRowDragAndDrop=allowRowDragAndDrop,
#                          grid=(0, 0)
#                          )
#         self.moduleParent = moduleParent
#
#     def selection(self, *args):
#         pass
#
#     def action(self, *args):
#         pass
#
#     def actionCheckBox(self, *args):
#         pass
#
#     def setDataTable(self, dataTable):
#         df = dataTable.data
#         if len(dataTable.data) > 0:
#             colDefs = ColumnClass([(x, lambda row: _getValueByHeader(row, x), None, None, None) for x in df.columns])
#             columnsMap = {x: x for x in df.columns}
#             dfo = self.getDataFromFrame(self, df, colDefs, columnsMap)
#             self.setTableFromDataFrameObject(dataFrameObject=dfo, columnDefs=colDefs)
#             self.selectIndex(0)
#
#
# class DataTableModuleBC(CcpnModule):
#     """
#     This class implements the module by wrapping a TableExample instance
#     """
#     includeSettingsWidget = True
#     maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
#     settingsPosition = 'left'
#
#     className = 'DataTableModule'
#
#     def __init__(self, dataTable=None, mainWindow=None, name='Generic DataTable Module'):
#         """
#         Initialise the Module widgets
#         """
#         super().__init__(mainWindow=mainWindow, name=name)
#
#         # Derive application, project, and current from mainWindow
#         self.mainWindow = mainWindow
#         self.dataTable = dataTable
#
#         # main window
#         row = 0
#         self.frame = Frame(self.mainWidget, setLayout=True, grid=(row, 0))
#         self.guiTable = GuiDataTableBC(dataTable=self.dataTable, parent=self.frame, mainWindow=self.mainWindow, moduleParent=self, grid=(0, 0))
#
#         # self.setGuiNotifier(self.table, [GuiNotifier.DROPEVENT],
#         #                             [DropBase.DFS], callback=self._handleDroppedItems)
#         # self.setGuiNotifier(self.table, [GuiNotifier.ENTEREVENT],
#         #                     [DropBase.DFS], callback=self._handleEnteredtems)
#         if self.dataTable:
#             self.setDataTable(self.dataTable)
#
#     def setDataTable(self, dataTable):
#         if dataTable:
#             self.guiTable.setDataTable(dataTable)
#
#     def _handleDroppedItems(self, dd):
#         print('DROPPED: ', dd)
#
#     def _handleEnteredtems(self, dd):
#         print('_handleEnteredtems', dd)
#
#
# def main():
#     from ccpn.ui.gui.widgets.Application import TestApplication
#     from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea
#
#     app = TestApplication()
#     win = QtWidgets.QMainWindow()
#     moduleArea = CcpnModuleArea(mainWindow=None, )
#     m = DataTableModuleBC(mainWindow=None)
#     t = m.table
#     # print('Selected', t.getSelectedObjects())
#     moduleArea.addModule(m)
#     win.setCentralWidget(moduleArea)
#     win.resize(1000, 2000)
#     win.show()
#     app.start()
#
#
# if __name__ == '__main__':
#     main()
