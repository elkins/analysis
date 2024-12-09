"""
This file contains ResidueTableModule and ResidueTable classes

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
__dateModified__ = "$dateModified: 2024-12-09 14:19:10 +0000 (Mon, December 09, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import OrderedDict

from ccpn.core.Chain import Chain
from ccpn.core.Residue import Residue
from ccpn.core.Atom import Atom
from ccpn.core.lib import CcpnSorting
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.widgets.PulldownListsForObjects import ChainPulldown
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.SettingsWidgets import StripPlot, ModuleSettingsWidget
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.util.Logging import getLogger


logger = getLogger()

ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


class ResidueTableModule(CcpnTableModule):
    """This class implements the module by wrapping a ResidueTable instance
    """
    className = 'ResidueTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'
    activePulldownClass = Chain
    _allowRename = True

    def __init__(self, mainWindow=None, name='Residue Table',
                 chain=None, selectFirstItem=False):
        """Initialise the Module widgets
        """
        super().__init__(mainWindow=mainWindow, name=name)

        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = self.project = self.current = None

        # set the widgets and callbacks
        self._setWidgets(self.settingsWidget, self.mainWidget, chain, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, chain, selectFirstItem):
        """Set up the widgets for the module
        """
        self._settings = None
        if self.activePulldownClass:
            # add to settings widget - see sequenceGraph for more detailed example
            settingsDict = OrderedDict(((LINKTOPULLDOWNCLASS, {'label'   : 'Link to current %s' % self.activePulldownClass.className,
                                                               'tipText' : 'Set/update current %s when selecting from pulldown' % self.activePulldownClass.className,
                                                               'callBack': None,
                                                               'enabled' : True,
                                                               'checked' : False,
                                                               '_init'   : None,
                                                               }),
                                        ))
            self._settings = ModuleSettingsWidget(parent=settingsWidget, mainWindow=self.mainWindow,
                                                  settingsDict=settingsDict,
                                                  grid=(0, 0))

        # add the frame containing the pulldown and table
        self._mainFrame = ResidueTableFrame(parent=mainWidget,
                                            mainWindow=self.mainWindow,
                                            moduleParent=self,
                                            chain=chain, selectFirstItem=selectFirstItem,
                                            grid=(0, 0))

    @property
    def tableFrame(self):
        """Return the table frame
        """
        return self._mainFrame

    @property
    def _tableWidget(self):
        """Return the table widget in the table frame
        """
        return self._mainFrame._tableWidget

    def _setCallbacks(self):
        """Set the active callbacks for the module
        """
        if self.activePulldownClass:
            self._setCurrentPulldown = Notifier(self.current,
                                                [Notifier.CURRENT],
                                                targetName=self.activePulldownClass._pluralLinkName,
                                                callback=self._mainFrame._selectCurrentPulldownClass)

            # set the active callback from the pulldown
            self._mainFrame.setActivePulldownClass(coreClass=self.activePulldownClass,
                                                   checkBox=self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget'])

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._mainFrame._processDroppedItems

    def selectTable(self, table):
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def _closeModule(self):
        if self.tableFrame:
            self.tableFrame._cleanupWidget()
            self._mainFrame = None
        if self.activePulldownClass and self._setCurrentPulldown:
            self._setCurrentPulldown.unRegister()
            self._setCurrentPulldown = None
        super()._closeModule()


#=========================================================================================
# _NewResidueTableWidget
#=========================================================================================

class _NewResidueTableWidget(_CoreTableWidgetABC):
    """Class to present a residue Table
    """
    className = '_NewResidueTableWidget'
    attributeName = 'chains'

    defaultHidden = ['Pid', 'Chain']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden
    _INDEX = 'Index'

    # define self._columns here
    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = Chain
    rowClass = Residue
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = {Atom: 'residue'}
    selectCurrent = True
    callBackClass = Residue
    search = False

    # set the queue handling parameters
    _maximumQueueLength = 25

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _sourceObjects(self):
        """Get/set the list of source objects
        """
        return (self._table and self._table.residues) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.residues = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.residues

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.residues = value
        else:
            self.current.clearResidues()

    #=========================================================================================
    # Action callbacks
    #=========================================================================================

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        # classItem is usually a type such as PeakList, MultipletList
        # with an attribute such as peaks/peaks
        return [cellItem._oldResidue] if cellItem.isDeleted else [cellItem.residue], Notifier.CHANGE

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, chain=None):
        """format of column = (Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """
        cols = ColumnClass([
            ('Index', lambda residue: self._nmrIndex(residue), 'Index of Residue in the Chain', None, None),
            ('Pid', lambda residue: residue.pid, 'Pid of Residue', None, None),
            ('_object', lambda residue: residue, 'Object', None, None),
            ('Chain', lambda residue: residue.chain.id, 'Chain containing the Residue', None, None),
            ('Sequence', lambda residue: residue.sequenceCode, 'Sequence code of Residue', None, None),
            ('Type', lambda residue: residue.residueType, 'Residue type', None, None),
            ('Atoms', lambda residue: self._getAtomNames(residue), 'Atoms in Residue', None, None),
            ('Comment', lambda nmr: self._getCommentText(nmr), 'Notes',
             lambda nmr, value: self._setComment(nmr, value), None)
            ])

        return cols

    #=========================================================================================
    # Updates
    #=========================================================================================

    #=========================================================================================
    # object properties
    #=========================================================================================

    @staticmethod
    def _nmrIndex(res):
        """CCPN-INTERNAL: Insert an index into ObjectTable
        """
        try:
            return res.chain.residues.index(res)
        except:
            return None

    @staticmethod
    def _getAtomNames(residue):
        """Returns a sorted list of Atom names
        """
        return ', '.join(sorted(set([atom.name for atom in residue.atoms if not atom.isDeleted]),
                                key=CcpnSorting.stringSortKey))

    @staticmethod
    def _getResiduePeakCount(residue):
        """Returns peak list count
        """
        l1 = [peak for atom in residue.atoms for peak in atom.assignedPeaks]
        return len(set(l1))


#=========================================================================================
# ResidueTableFrame
#=========================================================================================

class ResidueTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewResidueTableWidget
    _PulldownKlass = ChainPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 chain=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=chain, selectFirstItem=selectFirstItem, **kwds)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        return self.current.chain

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.chain = value


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the ResidueTable module
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = ResidueTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
