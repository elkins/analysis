"""
A  popup to launch several macros that generate various relaxation plots.
These macros require a DataTable containing the results of a Reduced Spectral density Mapping analysis.
See the Dynamics tutorial to learn how to create such a  dataTable.
See each individual macros for details.
All macros are a demo/starting point. Modify as needed.
Macro created for Analysis Version 3.1.1
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
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2023-02-17 14:03:22 +0000 (Fri, February 17, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import ccpn.core #this is needed it to avoid circular imports
import pandas as pd
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from PyQt5 import QtCore, QtGui, QtWidgets
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.PulldownListsForObjects import DataTablePulldown
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.util.Path import aPath, fetchDir, joinPath
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import matplotlib.pyplot as plt

plt.close('all') #make sure all plots are closed first

TIPTEXT = ''' 
A  popup to launch several macros that generate various relaxation plots.
These macros require a DataTable containing the results of a Reduced Spectral density Mapping analysis.
See the Dynamics tutorial to learn how to create such a  dataTable. '''

thisDirPath = aPath(__file__).filepath
project._checkProjectSubDirectories()
plotsPath = project.plotsPath

SEQUENCE = 'KLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDAATKTFTVTE'
SS_SEQUENCE = 'BBBBBCCCCBBBBBBCCCCHHHHHHHHHHHHHHCCCCCBBBBCCCCCBBBBBC'
Rates = 'Rates'
AnisotropyDetermination = 'Anisotropy Determination'
ReducedSpectralDensityMapping = 'Reduced Spectral Density Mapping'
T1T2ContouredScatter = 'T1 vs T2 Contoured Scatter'

MINIMUMWIDTHS = (150, 300)

MACROS_DICT = {
                            Rates: '_1_RelaxationRates_plots.py',
                            AnisotropyDetermination: '_2_AnisotropyDetermination_plots.py',
                            ReducedSpectralDensityMapping: '_3_ReduceSpectralDensityMapping_plots.py',
                            T1T2ContouredScatter: '_4_T1T2_contourScatter_plot.py',
                            }

NeededColumns_DICT = {
                            Rates: [sv.R1, sv.R1_ERR, sv.R2_ERR, sv.R2, sv.HETNOE_VALUE, sv.HETNOE_VALUE_ERR],
                            AnisotropyDetermination:  [sv.R1, sv.R1_ERR, sv.R2_ERR, sv.R2, sv.HETNOE_VALUE, sv.HETNOE_VALUE_ERR],
                            ReducedSpectralDensityMapping: [sv.R1, sv.R1_ERR, sv.R2_ERR, sv.R2, sv.J0_ERR, sv.J0, sv.JwH, sv.JwH, sv.JwH_ERR, sv.JwX_ERR],
                            T1T2ContouredScatter: [sv.R1, sv.R1_ERR, sv.R2_ERR, sv.R2],
                            }

class RelaxationPlotsPopup(CcpnDialogMainWidget):
    """
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    title = 'Relaxation Plots Popup (Alpha)'
    def __init__(self, parent=None, mainWindow=None,
                 title=title,  **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(500, 200), minimumSize=None, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.current = self.application.current
            self.project = mainWindow.project

        else:
            self.mainWindow = None
            self.application = None
            self.current = None
            self.project = None

        self._createWidgets()

        # enable the buttons
        self.tipText = TIPTEXT
        self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Generate', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        row = 0

        self.dtwidget = DataTablePulldown(parent=self.mainWidget,
                                         mainWindow=self.mainWindow,
                                         grid=(row, 0),
                                         showSelectName=True,
                                         minimumWidths=MINIMUMWIDTHS,
                                         # sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                          gridSpan=(1, 2),
                                         callback=None)
        row += 1
        self.filePathW = cw.EntryPathCompoundWidget(self.mainWidget, labelText='Output Dir Path',
                                                     entryText=str(plotsPath),
                                                    lineEditMinimumWidth=300,
                                                    minimumWidths=MINIMUMWIDTHS,
                                                    compoundKwds = {'fileMode': 'directory'},
                                                    gridSpan=(1, 1),
                                                           grid=(row, 0))
        self.filePathW.entry.lineEdit.setMinimumWidth(MINIMUMWIDTHS[1])

        row += 1
        self.seWidget = cw.EntryCompoundWidget(self.mainWidget, labelText='Sequence',
                                               tipText='One letter code sequence without spaces. Leave empty if not available',
                                               entryText=SEQUENCE,
                                               minimumWidths=MINIMUMWIDTHS,
                                               compoundKwds={
                                                   'backgroundText':f'One-Letter code. E.G.: {SEQUENCE}',
                                                   },
                                               gridSpan=(1, 1),
                                               grid=(row, 0))
        row += 1
        self.ssWidget = cw.EntryCompoundWidget(self.mainWidget, labelText='Secondary Structure',
                                               tipText='One letter code secondary structure sequence without spaces.  DSSP nomenclature. Leave empty if not available',
                                               entryText=SS_SEQUENCE,
                                               minimumWidths=MINIMUMWIDTHS,
                                               compoundKwds={
                                                   'backgroundText': f'DSSP One-Letter code. E.G.: {SS_SEQUENCE}',
                                                   },
                                               gridSpan=(1, 1),
                                               grid=(row, 0))
        row += 1
        self.optionsCB = cw.CheckBoxesCompoundWidget(self.mainWidget, labelText='Reports',
                                               tipText='',
                                               texts=list(MACROS_DICT.keys()),
                                                compoundKwds= {'direction': 'v',
                                                                      'selectAll': True,
                                                                      'hAlign': 'left'
                                                                      },
                                               minimumWidths=MINIMUMWIDTHS,
                                               gridSpan=(1, 1),
                                               grid=(row, 0))
        row += 1
        self._interactivePlotW = cw.CheckBoxCompoundWidget(self.mainWidget, labelText='Interactive Plots',
                                                     tipText='Open an interactive plot, zoomable and resizable.',
                                                     text='Open Plots',
                                                     checked=True,
                                                     minimumWidths=MINIMUMWIDTHS,
                                                     gridSpan=(1, 1),
                                                     grid=(row, 0))

        self.optionsCB.getLayout().setAlignment(QtCore.Qt.AlignLeft)
        self._interactivePlotW.getLayout().setAlignment(QtCore.Qt.AlignLeft)
        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignTop)


    def _okCallback(self):
        dataTableName = None
        dataTable = None
        if self.project:
            dataTable = self.project.getByPid(self.dtwidget.getText())
            if dataTable is not None:
                dataTableName = dataTable.name
            else:
                showWarning('Missing dataset','Please select a valid dataset.')
                return
        if dataTable is None:
            return
        # check the datatable is ok to create the available plots

        outputPath = self.filePathW.getText()

        sequence = self.seWidget.getText()
        ss = self.ssWidget.getText()
        selectedOptions = self.optionsCB.get()
        isInteractive = self._interactivePlotW.get()
        for selectedOption in selectedOptions:
            macroPathName = MACROS_DICT.get(selectedOption, None)
            if macroPathName is not None:

                data = dataTable.data
                neededColumns = NeededColumns_DICT.get(selectedOption, [])
                neededColumnSeries = pd.Series(neededColumns)
                if not neededColumnSeries.isin(data.columns).all():
                    title, msg = f'Cannot generate the {selectedOption} plots',\
                                 f'The following columns are mandatory: {neededColumns}. Please use a DataTable derived from a {sv.RSDM} analysis'
                    showWarning(title, msg)
                    continue
                macroPath = aPath(joinPath(thisDirPath, macroPathName))
                macroName = macroPath.basename
                filePath = aPath(joinPath(outputPath, macroName))
                filePath = filePath.assureSuffix('.pdf')
                itCommand = '--interactivePlot' if isInteractive else '--no-interactivePlot'
                commands = [
                                    f'-d {dataTableName}',
                                    f'-o {filePath}',
                                    f'-se {sequence}',
                                    f'-ss {ss}',
                                    f'{itCommand}',
                            ]
                if self.application is not None:
                    self.application.runMacro(macroPath, commands)

        self.accept()

if __name__ == '__main__':
    popup = RelaxationPlotsPopup(mainWindow=mainWindow)
    popup.show()
    popup.raise_()
