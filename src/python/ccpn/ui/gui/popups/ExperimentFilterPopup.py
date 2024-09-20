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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.FilteringPulldownList import FilteringPulldownList
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.RadioButton import RadioButton
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget


class ExperimentFilterPopup(CcpnDialogMainWidget):
    FIXEDHEIGHT = True
    FIXEDWIDTH = True

    def __init__(self, parent=None, mainWindow=None, spectrum=None,
                 title: str = 'Experiment Type Filter', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        self.mainWindow = mainWindow
        self.application = self.mainWindow.application
        self.project = self.mainWindow.project
        self.experimentClassification = self.application._experimentClassifications
        self.expType = None

        # Set up the main widgets
        self._setWidgets(spectrum)

        self.setOkButton(callback=self._setExperimentType, text='Apply')
        self.setCloseButton(callback=self.close)
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _setWidgets(self, spectrum):
        """Set up the main widgets
        """
        detectionBox = Frame(self.mainWidget, setLayout=True, grid=(0, 0), showBorder=False)
        filterBox = Frame(self.mainWidget, setLayout=True, grid=(1, 0), showBorder=False)
        selectionBox = Frame(self.mainWidget, setLayout=True, grid=(3, 0), showBorder=False)
        self.transferSwitches = []
        # filter by detection nucleus
        self.cCheckBox = CheckBox(detectionBox, grid=(0, 0), hAlign='r', callback=self.updateChoices)
        cLabel = Label(detectionBox, text='C-detected', grid=(0, 1), hAlign='l')
        self.hCheckBox = CheckBox(detectionBox, grid=(0, 2), hAlign='r', callback=self.updateChoices)
        hLabel = Label(detectionBox, text='H-detected', grid=(0, 3), hAlign='l')
        self.otherCheckBox = CheckBox(detectionBox, grid=(0, 4), hAlign='r', callback=self.updateChoices)
        nLabel = Label(detectionBox, text='Other', grid=(0, 5), hAlign='l')
        # filter by transfer technique
        self.anyCheckbox = RadioButton(filterBox, grid=(0, 0), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(0, 1), hAlign='l', text='Any')
        self.throughSpaceCheckbox = RadioButton(filterBox, grid=(0, 2), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(0, 3), hAlign='l', text='through space')
        self.relayedCheckBox = RadioButton(filterBox, grid=(0, 4), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(0, 5), hAlign='l', text='relayed')
        self.relaxationCheckBox = RadioButton(filterBox, grid=(0, 6), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(0, 7), hAlign='l', text='relaxation')
        self.mqCheckBox = RadioButton(filterBox, grid=(1, 0), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(1, 1), hAlign='l', text='MQ')
        self.quantificationCheckBox = RadioButton(filterBox, grid=(1, 2), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(1, 3), hAlign='l', text='quantification')
        self.jResolvedCheckBox = RadioButton(filterBox, grid=(1, 4), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(1, 5), hAlign='l', text='J resolved')
        self.projectedCheckBox = RadioButton(filterBox, grid=(1, 6), callback=self.updateChoices, hAlign='r')
        Label(filterBox, grid=(1, 7), hAlign='l', text='projection')
        self.noneOfTheAboveCheckbox = RadioButton(filterBox, grid=(2, 0), callback=self.updateChoices, hAlign='r')
        Label(filterBox, 'None of the Above', grid=(2, 1), gridSpan=(1, 3))
        if not spectrum.experimentType:
            self.anyCheckbox.setChecked(True)
            self.cCheckBox.setChecked(True)
            self.hCheckBox.setChecked(True)
            self.otherCheckBox.setChecked(True)
        experimentLabel = Label(selectionBox, text='%s experiment type' % spectrum.pid, grid=(0, 0), hAlign='l')
        self.experimentPulldown = FilteringPulldownList(selectionBox, grid=(1, 0))
        self.experimentTypes = spectrum.project._experimentTypeMap
        axisCodes = []
        for isotopeCode in spectrum.isotopeCodes:
            axisCodes.append(''.join([char for char in isotopeCode if not char.isdigit()]))
        atomCodes = tuple(sorted(axisCodes))
        self.classifications = list(self.experimentClassification[spectrum.dimensionCount].get(atomCodes))
        self.experimentNames = self.experimentTypes[spectrum.dimensionCount].get(atomCodes)
        self.texts = []
        self.objects = []
        for k, v in self.experimentNames.items():
            # ll = [x for x in self.classifications if x.name == v]
            ll = [x for x in self.classifications if x.synonym == k]
            self.objects.append(ll[0])
            self.texts.append(k)
        self.updateChoices()

    def _setExperimentType(self):

        self.expType = self.experimentPulldown.currentText()
        self.accept()

    def close(self):
        self.expType = None
        self.reject()

    def updateChoices(self):
        filteredExperimentObjects = set()

        # filter by acquisition nucleus
        detectionNuclei = []
        if self.cCheckBox.isChecked():
            detectionNuclei.append('13C')
        if self.hCheckBox.isChecked():
            detectionNuclei.append('1H')
        if self.otherCheckBox.isChecked():
            detectionNuclei.extend(['15N', '19F', '23Na', '79Br'])

        if self.anyCheckbox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects
             if x.acquisitionNucleus in detectionNuclei]
        if self.noneOfTheAboveCheckbox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if not x.isThroughSpace and
             not x.isRelayed and not x.isRelaxation and not x.isJResolved and not x.isMultipleQuantum
             and not x.isProjection and not x.isQuantification
             and x.acquisitionNucleus in detectionNuclei]
        if self.throughSpaceCheckbox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isThroughSpace
             and x.acquisitionNucleus in detectionNuclei]
        if self.relayedCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isRelayed
             and x.acquisitionNucleus in detectionNuclei]
        if self.relaxationCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isRelaxation
             and x.acquisitionNucleus in detectionNuclei]
        if self.jResolvedCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isJResolved
             and x.acquisitionNucleus in detectionNuclei]
        if self.mqCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isMultipleQuantum
             and x.acquisitionNucleus in detectionNuclei]
        if self.projectedCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isProjection
             and x.acquisitionNucleus in detectionNuclei]
        if self.quantificationCheckBox.isChecked():
            [filteredExperimentObjects.add(x) for x in self.objects if x.isQuantification
             and x.acquisitionNucleus in detectionNuclei]

        texts = []
        objects = []
        for ii, expObject in enumerate(self.objects):
            if expObject in filteredExperimentObjects:
                objects.append(expObject)
                texts.append(self.texts[ii])
        self.experimentPulldown.setData(texts=texts, objects=objects)
