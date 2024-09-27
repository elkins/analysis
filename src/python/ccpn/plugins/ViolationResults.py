"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-09-20 16:06:51 +0100 (Fri, September 20, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-02-25 16:03:34 +0100 (Fri, February 25, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from PyQt5 import QtWidgets

from ccpn.core.ViolationTable import ViolationTable
from ccpn.core.lib import Pid
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.CcpnSorting import universalSortKey
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Frame import ScrollableFrame
from ccpn.ui.gui.modules.PluginModule import PluginModule
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget, EntryCompoundWidget, LabelCompoundWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import RestraintTablePulldown
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.HLine import LabeledHLine
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.ui.gui.guiSettings import BORDERNOFOCUS_COLOUR
from ccpn.ui.gui.lib.Validators import LineEditValidatorCoreObject
from ccpn.ui.gui.lib.alignWidgets import alignWidgets
from ccpn.framework.lib.Plugin import Plugin
from ccpn.util.AttrDict import AttrDict


LineEditsMinimumWidth = 195
DEFAULTSPACING = 3
DEFAULTMARGINS = (14, 14, 14, 14)
DEFAULT_RUNNAME = 'output'

# Set some tooltip texts
RUNBUTTON = 'Run'
_help = {RUNBUTTON: 'Run the plugin', }
_RESTRAINTTABLE = 'restraintTable'
_VIOLATIONTABLE = 'violationTable'
_VIOLATIONRESULT = 'violationResult'
_RUNNAME = 'runName'


class ViolationResultsGuiPlugin(PluginModule):
    className = 'ViolationResults'

    def __init__(self, mainWindow=None, plugin=None, application=None, **kwds):
        super().__init__(mainWindow=mainWindow, plugin=plugin, application=application)

        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.preferences = mainWindow.application.preferences
        else:
            self.application = None
            self.project = None
            self.preferences = None

        # set up object to pass information to the main plugin
        self.obj = AttrDict()

        # set up the widgets
        self._setWidgets()
        self._populate()

        self._registerNotifiers()
        self.plugin._loggerCallback = self._guiLogger

    def _guiLogger(self, *args):
        self._textEditor.append(*args)

    def _setWidgets(self):
        """Set up the mainwidgets
        """
        # set up a scroll area in the mainWidget
        self._scrollFrame = ScrollableFrame(parent=self.mainWidget,
                                            showBorder=False, setLayout=True,
                                            acceptDrops=True, grid=(0, 0), gridSpan=(1, 1), spacing=(5, 5))
        self._scrollAreaWidget = self._scrollFrame._scrollArea
        self._scrollAreaWidget.setStyleSheet('ScrollArea { border-right: 1px solid %s;'
                                             'border-bottom: 1px solid %s;'
                                             'background: transparent; }' % (BORDERNOFOCUS_COLOUR, BORDERNOFOCUS_COLOUR))
        self._scrollFrame.insertCornerWidget()
        self._scrollFrame.setContentsMargins(*DEFAULTMARGINS)
        self._scrollFrame.getLayout().setSpacing(DEFAULTSPACING)

        # add contents to the scroll frame
        parent = self._scrollFrame
        row = 0
        Label(parent, text='Create Restraint Analysis Data', bold=True, grid=(row, 0))

        row += 1
        self._rTable = RestraintTablePulldown(parent=parent,
                                              mainWindow=self.mainWindow,
                                              labelText='RestraintTable',
                                              grid=(row, 0), gridSpan=(1, 2),
                                              showSelectName=True,
                                              minimumWidths=(250, 100),
                                              sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                              callback=self._selectRTableCallback)

        row += 1
        # only needs to be populated by the restraint-table pulldown
        self._vTable = PulldownListCompoundWidget(parent=parent,
                                                  mainWindow=self.mainWindow,
                                                  labelText="Source ViolationTable",
                                                  grid=(row, 0), gridSpan=(1, 2),
                                                  minimumWidths=(250, 100),
                                                  sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                                  callback=None)

        row += 1
        self._outputName = EntryCompoundWidget(parent=parent,
                                               mainWindow=self.mainWindow,
                                               labelText="Output Name",
                                               grid=(row, 0), gridSpan=(1, 2),
                                               minimumWidths=(250, 100),
                                               sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                               callback=None,
                                               compoundKwds={'backgroundText': '> Enter name <'},
                                               )
        self._outputName.entry.returnPressed.connect(self.runGui)
        self._outputName.entry.textChanged.connect(self._updateLabel)

        row += 1
        self._outputLabel = LabelCompoundWidget(parent=parent,
                                                labelText="Output ViolationTable Name",
                                                grid=(row, 0), gridSpan=(1, 3),
                                                minimumWidths=(250, 100),
                                                )

        row += 1
        texts = [RUNBUTTON]
        tipTexts = [_help[RUNBUTTON]]
        callbacks = [self.runGui]
        ButtonList(parent=parent, texts=texts, callbacks=callbacks, tipTexts=tipTexts,
                   grid=(row, 1), gridSpan=(1, 1), hAlign='r')

        row += 1
        LabeledHLine(parent, text='Output', grid=(row, 0), gridSpan=(1, 3), height=16, colour=getColours()[DIVIDER])

        row += 1
        self._textEditor = TextEditor(parent, grid=(row, 0), gridSpan=(1, 3), enabled=True, addWordWrap=True)
        self._textEditor.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        row += 1
        parent.getLayout().setColumnStretch(2, 2)

        alignWidgets(parent)

    def runGui(self):
        """Run the plugin
        """
        _rTable = self.project.getByPid(self._rTable.getText())
        _vTable = self.project.getByPid(self._vTable.getText())
        _runName = self._outputName.getText()
        _runLabel = self._outputLabel.getText()

        _title = 'Create Restraint Analysis Data'
        if not (_rTable and _vTable):
            showWarning(_title, 'Please select from the pulldowns')
        elif not _runName:
            showWarning(_title, 'Please select output violationTable name')
        elif not self._outputName.entry.validator().isValid:
            showWarning(_title, f'Output violationTable name contains bad characters, or name already exists.\n\n'
                                f'Check the existing violationTables in structureData {_rTable.structureData}')

        else:
            # create the data
            self.obj[_RESTRAINTTABLE] = _rTable
            self.obj[_VIOLATIONTABLE] = _vTable
            self.obj[_RUNNAME] = self._restraintName(_rTable, _runName)

            if (result := self.plugin.run(**self.obj)):
                self._populate(name=result.name)

    @staticmethod
    def _restraintName(rTable, output):
        """Generate the violation-table name from the restraint-table and output name
        """
        return (output or '<output>') + '_' + rTable.name if rTable else ''

    def _updateLabel(self):
        """Update the output violation-table name in the widget as the outpu name is edited
        """
        _rTable = self.project.getByPid(self._rTable.getText())
        _vTable = self.project.getByPid(self._vTable.getText())
        _runName = self._outputName.getText()

        try:
            name = Pid.Pid.new(ViolationTable.shortClassName,
                               _rTable.structureData.name if _rTable else '',
                               self._restraintName(_rTable, _runName)
                               )
        except Exception:
            # ignore bad names
            name = ''

        self._outputLabel.setText(name)

    def _populate(self, name=None):
        """Populate the pulldowns from the project restraintTables
        """
        firstItemName = self._rTable.getFirstItemText()
        if firstItemName:
            # set the item in the pulldown
            self._rTable.select(firstItemName)
        self._outputName.setText(name or DEFAULT_RUNNAME)
        self._selectRTableCallback(firstItemName)

    def _selectRTableCallback(self, pid, deleted=None):
        """Handle the callback from the restraintTable selection
        """
        if (resTable := self.project.getByPid(pid)):
            _texts = [''] + [vt.pid for vt in self.project.violationTables
                             if not (deleted and vt in deleted) and vt.getMetadata(_RESTRAINTTABLE) == pid and vt.getMetadata(_VIOLATIONRESULT) is not True]
            self._vTable.modifyTexts(texts=_texts)

            # set validator to check names in the parent structureData
            _validator = LineEditValidatorCoreObject(parent=self._outputName.entry, target=resTable.structureData, klass=ViolationTable,
                                                     allowSpace=False, allowEmpty=False)
            self._outputName.entry.setValidator(_validator)
            self._outputName.entry.validator().resetCheck()
            self._updateLabel()

    def _violationCallback(self, data):
        """Re-populate the module
        """
        pid = self._rTable.getText()
        trigger = data[Notifier.TRIGGER]

        self._selectRTableCallback(pid, [data[Notifier.OBJECT]] if trigger == 'delete' else None)

    def _registerNotifiers(self):
        """Add notifiers to handle violation-tables
        """
        self.setNotifier(self.project, [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE, Notifier.RENAME],
                         ViolationTable.__name__, self._violationCallback, onceOnly=True)

    def closePlugin(self):
        """Clean up and close plugin
        """
        if self._rTable:
            self._rTable.unRegister()
        super().closePlugin()


class ViolationResultsPlugin(Plugin):
    """Plugin to create violation results from restraintTables and processed violationTables
    """
    PLUGINNAME = 'Create Restraint Analysis Data'
    guiModule = ViolationResultsGuiPlugin

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        self._kwds = AttrDict()
        self._loggerCallback = None

    def _logger(self, *args):
        if self._loggerCallback:
            self._loggerCallback(*args)

    def run(self, **kwargs):
        """Generate the output dataTable
        """
        # pd.set_option('display.max_columns', None)
        # pd.set_option('display.max_rows', 7)

        _requiredColumns = ['model_id', 'restraint_id', 'atoms', 'violation']

        self._logger('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

        # check the parameters
        if not (restraintTable := kwargs.get(_RESTRAINTTABLE)):
            self._logger('ERROR:   RestraintTable not specified')
            return
        if not (violationTable := kwargs.get(_VIOLATIONTABLE)):
            self._logger('ERROR:   ViolationTable not specified')
            return
        _df = violationTable.data
        if _df is None:
            self._logger('ERROR:   ViolationTable contains no data')
            return

        self._logger(f'Running - {self.PLUGINNAME}')
        self._logger(f'  {_df.columns}')

        if _invalidColumns := [col for col in _requiredColumns if col not in _df.columns]:
            self._logger(f'ERROR:   missing required columns {_invalidColumns}')
            return

        if models := [v for k, v in _df.groupby(['model_id'], as_index=False)]:
            self._logger(f'MODELS {len(models)}')
            self._logger(f'{models[0].columns}')

            restraintsFromModels = []
            targetsFromModels = []

            # use the serial to get the restraint from the peak - make list for each model just to check is actually working
            for _mod in models:
                restraintsFromModel = []
                restraintsFromModels.append(restraintsFromModel)
                targetsFromModel = []
                targetsFromModels.append(targetsFromModel)

                for serial in _mod['restraint_id']:
                    restraintId = Pid.IDSEP.join(('' if x is None else str(x)) for x in (restraintTable.structureData.name, restraintTable.name, serial))
                    modelRestraint = self.project.getObjectsByPartialId(className='Restraint', idStartsWith=restraintId)
                    restraintsFromModel.append(modelRestraint[0].pid if modelRestraint else None)
                    targetsFromModel.append((modelRestraint[0].targetValue,
                                             modelRestraint[0].lowerLimit,
                                             modelRestraint[0].upperLimit) if modelRestraint else None)

            # check all the same
            self._logger(str(all(restraintsFromModels[0] == resMod for resMod in restraintsFromModels)))

            # calculate statistics for the violations and concatenate into a single dataFrame
            average = pd.concat([v['violation'].reset_index(drop=True) for v in models],
                                ignore_index=True,
                                axis=1).agg(['min',
                                             'max',
                                             'mean',
                                             'std',
                                             lambda x: int(sum(x > 0.3)),
                                             lambda x: int(sum(x > 0.5)), ], axis=1)

            self._logger('**** average *****')
            self._logger(str(average))

            # # merge the atom columns - done in nef loader?
            # atoms = models[0]['atom1'].map(str) + ' - ' + models[0]['atom2'].map(str)

            # remove the indexing for the next concat
            _atoms = models[0]['atoms'].reset_index(drop=True)
            average.reset_index(drop=True)

            # ensure that the atoms in each cell
            atoms = pd.Series([' - '.join(sorted(st.split(' - '), key=universalSortKey)) if st else None for st in list(_atoms)])

            self._logger('**** atoms *****')
            self._logger(str(atoms))
            pids = pd.DataFrame(restraintsFromModels[0], columns=['pid'])
            targets = pd.DataFrame(targetsFromModels[0], columns=['targetValue', 'lowerLimit', 'upperLimit'])

            # ids = models[0]['restraint_id']
            # subIds = models[0]['restraint_sub_id']

            # build the result dataFrame
            result = pd.concat([pids, atoms, targets, average], ignore_index=True, axis=1)

            # rename the columns (lambda just gives the name 'lambda') - try multiLevel?
            # result.columns = ('RestraintPid', 'Atoms', 'Min', 'Max', 'Mean', 'STD', 'Count>0.3', 'Count>0.5')
            result.columns = ('Restraint Pid', 'Atoms', 'Target Value', 'Lower Limit', 'Upper Limit', 'Min', 'Max', 'Mean', 'STD', 'Count > 0.3', 'Count > 0.5')

            # put into a new dataTable
            if (output := restraintTable.structureData.newViolationTable(name=kwargs.get(_RUNNAME))):
                output.setMetadata(_RESTRAINTTABLE, restraintTable.pid)
                output.setMetadata(_VIOLATIONRESULT, True)
                output.data = result

                self._logger(f'\n Results in structureData:  {restraintTable.structureData.pid}')
                self._logger(f' input restraintTable:      {restraintTable.pid}')
                self._logger(f' input violationTable:      {violationTable.pid}\n')
                self._logger(f' output violationTable:     {output.pid}\n')

                return output

        else:
            self._logger('ERROR:   violationTable contains no models')


# ViolationResultsPlugin.register()  # Registers the plugin


def main():
    """Show the violationResults plugin in a test app
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add the module to mainWindow
    mainWindow.startPlugin(ViolationResultsPlugin)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
