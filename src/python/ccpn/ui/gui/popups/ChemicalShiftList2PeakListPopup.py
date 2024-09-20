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
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================


from ccpn.framework.Application import getApplication, getCurrent, getProject
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from collections import OrderedDict as od
from ccpn.framework.lib.peakListSimulation.peakListFromChemicalShiftList import CSL2SPECTRUM_DICT
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from collections import OrderedDict, defaultdict
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.util.Logging import getLogger

widgetFixedWidth = 80

SELECTEXPTYPE = '< Select Experiment Type >'

class MapperRowWidgetLabels(Widget):

    def __init__(self, parent, **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        col = 0
        self.isotopeCodeLabel = Label(self, 'Isotope', grid=(0,col),
                                      tipText='IsotopeCode. Used to create the new synthetic PeakList')
        col += 1
        self.axisCodeEntryLabel = Label(self, 'AxisCode', grid=(0,col),
                                      tipText='AxisCode. Used to create the new synthetic PeakList '
                                              'and assign the NmrAtom')
        col += 1
        self.mmrAtomEntryLabel = Label(self, 'NmrAtom Name', grid=(0,col),
                                     tipText='NmrAtom Name. Used to assign the NmrAtom to newly created peaks')
        col += 1
        self.offsetEntryLabel = Label(self, 'Offset', grid=(0,col),
                                     tipText='Residue Offset. Used to fetch the correct NmrResidue')

        self.isotopeCodeLabel.setFixedWidth(widgetFixedWidth)
        self.offsetEntryLabel.setFixedWidth(widgetFixedWidth)


class MapperRowWidget(Widget):

    def __init__(self, parent, atomNameMapper, **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        col = 0

        self.isotopeCodeLabel = Label(self, 'IsotopeCode', grid=(0,col),
                                      tipText='IsotopeCode. Used to create the new Synthetic PeakList'
                                              )
        col += 1
        self.axisCodeEntry = LineEdit(self, backgroundText='AxisCode. E.g.: Hn', grid=(0,col),
                                      tipText='AxisCode. Used to create the new Synthetic PeakList '
                                              'and assign the NmrAtom')
        self.axisCodeEntry.setEnabled(False)

        col += 1
        self.mmrAtomEntry = LineEdit(self, backgroundText='Assigning NmrAtom Name. E.g.: H', grid=(0,col),
                                     tipText='NmrAtom Name. Used to assign the NmrAtom to newly created peaks')
        col += 1
        self.offsetEntry = Spinbox(self, grid=(0,col),min=-10, max=10,
                                     tipText='Residue Offset. Used to fetch the correct NmrResidue')

        self.isotopeCodeLabel.setFixedWidth(widgetFixedWidth)
        self.offsetEntry.setFixedWidth(widgetFixedWidth)

        self.getLayout().setAlignment(QtCore.Qt.AlignLeft)
        self.atomNameMapper = atomNameMapper
        self.updateWidgets()


    def updateWidgets(self):

        self.isotopeCodeLabel.set(self.atomNameMapper.isotopeCode)
        self.axisCodeEntry.set(self.atomNameMapper.axisCode)
        for offset, requiredAtomName in self.atomNameMapper.offsetNmrAtomNames.items():
            self.mmrAtomEntry.set(requiredAtomName)
            self.offsetEntry.setValue(offset)
            break #should be always one anyway!

    def upddateMapperFromWidgets(self):
        self.atomNameMapper.axisCode = self.axisCodeEntry.get()
        offsetNmrAtomNames = {self.offsetEntry.get():self.mmrAtomEntry.get()}
        self.atomNameMapper.offsetNmrAtomNames = offsetNmrAtomNames

class ChemicalShiftList2SpectrumPopup(CcpnDialogMainWidget):
    """

    """
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    title = 'Create Synthetic PeakList from ChemicalShiftList (Alpha)'
    def __init__(self, parent=None, chemicalShiftList=None, title=title, **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(500, 300), minimumSize=None, **kwds)

        self.project = getProject()
        self.application = getApplication()
        self.current = getCurrent()
        self.chemicalShiftList = chemicalShiftList
        self.spectrumSynthesizerClass = None
        self._mapperWidgets = defaultdict(list)
        self._createWidgets()

        # enable the buttons
        self.tipText = ''
        self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Create', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        row = 0
        spectrumName = self.chemicalShiftList.name if self.chemicalShiftList else ''
        self.spectrumNameLabel = Label(self.mainWidget, 'New Synthetic PeakList Name', grid=(row, 0),)
        self.spectrumNameEntry = LineEdit(self.mainWidget, text=spectrumName, grid=(row, 1))
        row  += 1
        self.experimentTypelabel = Label(self.mainWidget, 'Experiment Type', grid=(row, 0), )
        self.experimentTypePulldown = PulldownList(self.mainWidget, texts = list(CSL2SPECTRUM_DICT.keys()),
                                                        headerText=SELECTEXPTYPE,
                                                        callback=self._setWidgetsByExperimentType,
                                                        grid=(row, 1))

        row += 1
        self.advancedAssignframe = MoreLessFrame(self.mainWidget, name='Advanced Assignment Options',
                               showMore=False, scrollable=True, grid=(row, 0), gridSpan=(1, 2))
        self.mappersFrame = self.advancedAssignframe.contentsFrame
        row += 1
        # self.selectAnExpTypeLabel = Label(self.mainWidget, SELECTEXPTYPE, grid=(row, 0),
        #                               tipText='Select an Experiment Type to see options')

        self.mappersFrame.getLayout().setAlignment(QtCore.Qt.AlignTop)
        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignTop)


    def _setWidgetsByExperimentType(self, *args):
        pulldown = self.experimentTypePulldown
        selected = pulldown.get()
        self.spectrumSynthesizerClass = CSL2SPECTRUM_DICT.get(selected, None)

        _GREY = '#888888'
        if self.spectrumSynthesizerClass:
            self._clearMapperWidgets(self.mappersFrame.getLayout())
            self._mapperWidgets = defaultdict(list)
            row = 0

            labelsWidget = None
            peakAtomNameMappers = self.spectrumSynthesizerClass.getPeakAtomNameMappers(self.spectrumSynthesizerClass)
            for i, mappers in enumerate(peakAtomNameMappers):
                # loop through mappers to get the required atoms names  etc
                LabeledHLine(self.mappersFrame, text=f'Peak Group {i + 1} ', grid=(row, 0), style='DashLine', colour=_GREY)
                row += 1
                if not labelsWidget:
                    labelsWidget = MapperRowWidgetLabels(self.mappersFrame, grid=(row, 0))

                row += 1
                for mapper in mappers:
                    w = MapperRowWidget(self.mappersFrame, mapper, grid=(row, 0))
                    self._mapperWidgets[i].append(w)
                    row += 1
        self.mappersFrame.getLayout().setAlignment(QtCore.Qt.AlignTop)


    def _clearMapperWidgets(self, layout):
        """Clear all rows """
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _updateMappersFromWidgets(self, spectrumSim):
        mappersGroups = []
        for i, _mapperWidgetList in self._mapperWidgets.items():
            mappers = []
            for _mapperWidget in _mapperWidgetList:
                _mapperWidget.upddateMapperFromWidgets()
                mappers.append(_mapperWidget.atomNameMapper)
            mappersGroups.append(mappers)
        spectrumSim.peakAtomNameMappers = mappersGroups
        return spectrumSim

    def _okCallback(self):
        if self.project and self.chemicalShiftList:
            if self.spectrumSynthesizerClass:
                synthSpectrum = self.spectrumSynthesizerClass(self.chemicalShiftList, {'name':self.spectrumNameEntry.get()})
                self._updateMappersFromWidgets(synthSpectrum)
                # try:
                synthSpectrum.simulatePeakList()
                # except Exception as err:
                # msg = f'Failed to simulate PeakList for {spectrumSim.spectrum} from {self.chemicalShiftList}.\n{err}'
                # getLogger().warning(msg)
                # showWarning('Error', msg)

        self.accept()

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    app = TestApplication()
    popup = ChemicalShiftList2SpectrumPopup()
    popup.show()
    popup.raise_()
    app.start()

