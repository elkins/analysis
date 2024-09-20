"""
This file contains Framework-related Gui methods;
A first step towards separating them from the Framework class
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
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2024-09-05 15:46:55 +0100 (Thu, September 05, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2022-01-18 10:28:48 +0000 (Tue, January 18, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import platform

from functools import partial
from typing import Optional

from PyQt5 import QtWidgets

from ccpn.framework.PathsAndUrls import \
    macroPath, \
    widgetsPath, \
    CCPN_ARCHIVES_DIRECTORY

from ccpn.core.Project import Project

from ccpn.util.Common import isWindowsOS
from ccpn.util.Logging import getLogger
from ccpn.util.Path import aPath
import ccpn.ui.gui.Layout as Layout

from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.FileDialog import \
    ArchivesFileDialog, \
    LayoutsFileDialog, \
    NMRStarFileDialog

from ccpn.ui.gui.widgets.Menu import \
    SHOWMODULESMENU, \
    CCPNMACROSMENU, \
    TUTORIALSMENU, \
    CCPNPLUGINSMENU, \
    PLUGINSMENU


class GuiBase(object):
    """Just methods taken from Framework for now
    """

    def __init__(self):
        # GWV these attributes should move to the GUI class (in 3.2x ??)
        # For now, initialised by calls in Gui.__init_ as we need programme
        # arguments and preferences to have been initialised
        self._styleSheet = None
        # self._colourScheme = None
        self._themeStyle = None
        self._themeColour = None
        self._themeSDStyle = None
        self._fontSettings = None
        self._menuSpec = None

    def _setupMenus(self):
        """Set up the menu specification.

        The menus are specified by a list of lists (actually, an iterable of iterables, but the term
        ‘list’ will be used here to mean any iterable).  Framework provides 7 menus: Project, Spectrum,
        Molecules, View, Macro, Plugins, Help.  If you want to create your own menu in a subclass of
        Framework, you need to create a list in the style described below, then call
        self.addApplicationMenuSpec and pass in your menu specification list.

        Menu specification lists are composed of two items, the first being a string which is the menu’s
        title, the second is a list of sub-menu items.  Each item can be zero, two or three items long.
        A zero-length list indicates a separator.  If the list is length two and the second item is a
        list, then it specifies a sub-menu in a recursive manner.  If the list is length two and the
        second item is callable, it specifies a menu action with the first item specifying the label
        and the second the callable that is triggered when the menu item is selected.  If the list is
        length three, it is treated as a menu item specification, with the third item a list of keyword,
        value pairs.

        The examples below may make this more clear…

        Create a menu called ‘Test’ with two items and a separator:

        | - Test
        |   | - Item One
        |   | - ------
        |   | - Item Two

        Where clicking on ‘Item One’ calls method self.itemOneMethod and clicking on ‘Item Two’
        calls self.itemTwoMethod

        |    def setupMenus(self):
        |      menuSpec = (‘Test’, [(‘Item One’, self.itemOneMethod),
        |                           (),
        |                           (‘Item Two’, self.itemTwoMethod),
        |                          ]
        |      self.addApplicationMenuSpec(menuSpec)



        More complicated menus are possible.  For example, to create the following menu

        | - Test
        |   | - Item A     ia
        |   | - ------
        |   | - Submenu B
        |      | - Item B1
        |      | - Item B2
        |   | - Item C     id

        where Item A can be activated using the two-key shortcut ‘ia’,
        Submenu B contains two static menu items, B1 and B2
        Submenu item B2 is checkable, but not checked by default
        Item C is disabled by default and has a shortcut of ‘ic’

        |   def setupMenus(self):
        |     subMenuSpecB = [(‘Item B1’, self.itemB1),
        |                     (‘Item B2’, self.itemB2, [(‘checkable’, True),
        |                                               (‘checked’, False)])
        |                    ]
        |
        |     menuSpec = (‘Test’, [(‘Item A’, self.itemA, [(‘shortcut’, ‘ia’)]),
        |                          (),
        |                          (‘Submenu B’, subMenuB),
        |                          (‘Item C’, self.itemA, [(‘shortcut’, ‘ic’),
        |                                                  (‘enabled’, False)]),
        |                         ]
        |     self.addApplicationMenuSpec(menuSpec)


        If we’re using the PyQt GUI, we can get the Qt action representing Item B2 somewhere in our code
        (for example, to change the checked status,) via:

        |   action = application.ui.mainWindow.getMenuAction(‘Test->Submenu B->Item B2’)
        |   action.setChecked(True)

        To see how to add items dynamically, see clearRecentProjects in this class and
        _fillRecentProjectsMenu in GuiMainWindow

        """
        self._menuSpec = ms = []

        ms.append(('File', [
            ("New", self._newProjectCallback, [('shortcut', '⌃n')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            (),
            ("Open...", self._openProjectCallback, [('shortcut', '⌃o')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            ("Open Recent", ()),

            ("Load Data...", self._loadDataCallback, [('shortcut', 'ld')]),
            (),
            ("Save", self._saveCallback, [('shortcut', '⌃s')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            ("Save As...", self._saveAsCallback, [('shortcut', 'sa')]),
            (),
            ("Import", (("Nef File", self._importNefCallback, [('shortcut', 'in'), ('enabled', True)]),
                        ("NmrStar File", self._loadNMRStarFileCallback, [('shortcut', 'bi')]),
                        )),
            ("Export", (("Nef File", self._exportNEF, [('shortcut', 'ex'), ('enabled', True)]),
                        )),
            (),
            ("Layout", (("Save", self._saveLayoutCallback, [('enabled', True)]),
                        ("Save as...", self._saveLayoutAsCallback, [('enabled', True)]),
                        (),
                        ("Restore last", self._restoreLastSavedLayoutCallback, [('enabled', True)]),
                        ("Restore from file...", self._restoreLayoutFromFileCallback, [('enabled', True)]),
                        (),
                        ("Open pre-defined", ()),

                        )),
            ("Summary", self._showProjectSummaryPopup),
            ("Archive", self._archiveProjectCallback, [('enabled', False)]),
            ("Restore From Archive...", self._restoreFromArchiveCallback, [('enabled', False)]),
            (),
            ("Preferences...", self._showApplicationPreferences, [('shortcut', '⌃,')]),
            (),
            ("Quit", self._quitCallback, [('shortcut', '⌃q')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            ]
                   ))

        ms.append(('Edit', [
            ("Undo", self.undo, [('shortcut', '⌃z')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            ("Redo", self.redo, [('shortcut', '⌃y')]),  # Unicode U+2303, NOT the carrot on your keyboard.
            (),

            ("Cut", self._nyi, [('shortcut', '⌃x'), ('enabled', False)]),
            ("Copy", self._nyi, [('shortcut', '⌃c'), ('enabled', False)]),
            ("Paste", self._nyi, [('shortcut', '⌃v'), ('enabled', False)]),
            ("Select all", self._nyi, [('shortcut', '⌃a'), ('enabled', False)]),
            ]
                   ))

        ms.append(('View', [
            ("Chemical Shift Table", partial(self.showChemicalShiftTable, selectFirstItem=True), [('shortcut', 'ct')]),
            ("NmrResidue Table", partial(self.showNmrResidueTable, selectFirstItem=True), [('shortcut', 'nt')]),
            ("Residue Table", partial(self.showResidueTable, selectFirstItem=True)),
            ("Peak Table", partial(self.showPeakTable, selectFirstItem=True), [('shortcut', 'pt')]),
            ("Integral Table", partial(self.showIntegralTable, selectFirstItem=True), [('shortcut', 'it')]),
            ("Multiplet Table", partial(self.showMultipletTable, selectFirstItem=True), [('shortcut', 'mt')]),
            ("Restraint Table", partial(self.showRestraintTable, selectFirstItem=True), [('shortcut', 'rt')]),
            ("Structure Table", partial(self.showStructureTable, selectFirstItem=True), [('shortcut', 'st')]),
            ("Data Table", partial(self.showDataTable, selectFirstItem=True), [('shortcut', 'dt')]),
            ("Violation Table", partial(self.showViolationTable, selectFirstItem=True), [('shortcut', 'vt')]),
            (),
            ("Restraint Analysis Inspector", partial(self.showRestraintAnalysisTable, selectFirstItem=True), [('shortcut', 'at')]),
            ("Chemical Shift Mapping (Beta)", self.showChemicalShiftMappingModule, [('shortcut', 'cm')]),
            ("Relaxation Analysis (Beta)", self.showRelaxationModule, [('shortcut', 'ra')]),

            ("Notes Editor", partial(self.showNotesEditor, selectFirstItem=True), [('shortcut', 'no'),
                                                                                   # ('icon', 'icons/null')
                                                                                   ]),
            # (),
            # ("Chemical Shift Mapping (alpha)", self.showChemicalShiftMappingModule, [('shortcut', 'ma')]),
            # ("Relaxation (alpha)", self.showRelaxationModule, [('shortcut', 're')]),
            (),
            ("In Active Spectrum Display", (("Show/Hide Toolbar", self.toggleToolbar, [('shortcut', 'tb')]),
                                            ("Show/Hide Spectrum Toolbar", self.toggleSpectrumToolbar, [('shortcut', 'sb')]),
                                            ("Show/Hide Phasing Console", self.togglePhaseConsole, [('shortcut', 'pc')]),
                                            (),
                                            ("Set Zoom...", self._setZoomPopup, [('shortcut', 'sz')]),
                                            # ("Reset Zoom", self.resetZoom, [('shortcut', 'rz')]),
                                            (),
                                            ("New SpectrumDisplay with New Strip, Same Axes", self.copyStrip, []),
                                            (" .. with X-Y Axes Flipped", self._flipXYAxisCallback, [('shortcut', 'xy')]),
                                            (" .. with X-Z Axes Flipped", self._flipXZAxisCallback, [('shortcut', 'xz')]),
                                            (" .. with Y-Z Axes Flipped", self._flipYZAxisCallback, [('shortcut', 'yz')]),
                                            (" .. with Axes Flipped...", self.showFlipArbitraryAxisPopup, [('shortcut', 'fa')]),
                                            (),
                                            ("Auto-arrange Labels", self.arrangeLabels, [('shortcut', 'av')]),
                                            ("Reset Labels", self.resetLabels, [('shortcut', 'rv')]),
                                            )),
            ("Show/Hide Crosshairs", self.toggleCrosshairAll, [('shortcut', 'ch')]),
            (),
            (SHOWMODULESMENU, ([
                ("None", None, [('checkable', True),
                                ('checked', False)])
                ])),
            ("Python Console", self._toggleConsoleCallback, [('shortcut', '  '),
                                                             ])
            ]
                   ))

        ms.append(('Spectrum', [
            ("Load Spectra...", self._loadSpectraCallback, [('shortcut', 'ls')]),
            (),
            # ("Spectrum Groups...", self.showSpectrumGroupsPopup, [('shortcut', 'ss')]), # multiple edit temporarly disabled
            ("Set Experiment Types...", self.showExperimentTypePopup, [('shortcut', 'et')]),
            ("Validate Paths...", self.showValidateSpectraPopup, [('shortcut', 'vp')]),
            (),
            ("Pick Peaks", (("Pick 1D Peaks...", self.showPeakPick1DPopup, [('shortcut', 'p1')]),
                            ("Pick ND Peaks...", self.showPeakPickNDPopup, [('shortcut', 'pp')])
                            )),
            ("Copy PeakList...", self.showCopyPeakListPopup, [('shortcut', 'cl')]),
            ("Copy Peaks...", self.showCopyPeaks, [('shortcut', 'cp')]),
            ("Peak Collections...", self.showPeakCollectionsPopup, [('shortcut', 'sc')]),
            # (),
            ("Estimate Peak Volumes...", self.showEstimateVolumesPopup, [('shortcut', 'ev')]),
            ("Estimate Current Peak Volumes", self.showEstimateCurrentVolumesPopup, [('shortcut', 'ec')]),
            ("Reorder PeakList Axes...", self.showReorderPeakListAxesPopup, [('shortcut', 'rl')]),
            (),
            ("Make Strip Plot...", self.makeStripPlotPopup, [('shortcut', 'sp')]),

            (),
            ("Pseudo Spectrum to SpectrumGroup...", self.showPseudoSpectrumPopup),
            ("Make Projection...", self.showProjectionPopup, [('shortcut', 'pj')]),
            (),
            ("Print to File...", self.showPrintSpectrumDisplayPopup, [('shortcut', '⌃p')]),
            ]
                   ))

        ms.append(('Molecules', [
            ("Load ChemComp from Xml...", self._loadDataCallback),
            (),
            ("Chain from FASTA...", self._loadDataCallback),
            (),
            ("New Chain...", self.showCreateChainPopup),
            ("Inspect...", self.inspectMolecule, [('enabled', False)]),
            (),
            ("Residue Information", self.showResidueInformation, [('shortcut', 'ri')]),
            (),
            ("Reference Chemical Shifts", self.showReferenceChemicalShifts, [('shortcut', 'rc')]),
            (),
            ("Edit Molecular Bonds", self.showMolecularBondsPopup, ),
            ]
                   ))

        ms.append(('Macro', [
            ("New Macro Editor", self._showMacroEditorCallback, [('shortcut', 'nm')]),
            (),
            ("Open User Macro...", self._openMacroCallback, [('shortcut', 'om')]),
            ("Open CCPN Macro...", partial(self._openMacroCallback, directory=macroPath)),
            (),
            ("Run...", self.runMacro, [('shortcut', 'rm')]),
            ("Run Recent", ()),
            (CCPNMACROSMENU, ([
                ("None", None, [('checkable', True),
                                ('checked', False)])
                ])),
            (),
            ("Define Macro Shortcuts...", self.defineUserShortcuts, [('shortcut', 'du')]),
            ]
                   ))

        ms.append(('Plugins', [
            (CCPNPLUGINSMENU, ()),
            (PLUGINSMENU, ()),
            ]
                   ))

        if self._isInDebugMode:
            ms.append(('Development', [
                ("Set debug off", partial(self.setDebug, 0)),
                ("Set debug level 1", partial(self.setDebug, 1)),
                ("Set debug level 2", partial(self.setDebug, 2)),
                ("Set debug level 3", partial(self.setDebug, 3)),
                ]
                       ))

        ms.append(('Help', [
            (TUTORIALSMENU, ([
                ("None", None, [('checkable', True),
                                ('checked', False)])
                ])),
            ("Show Tip of the Day", partial(self._displayTipOfTheDay, standalone=True)),
            ("Key Concepts", self._displayKeyConcepts),
            ("Show Shortcuts", self._showShortcuts),
            ("Show API Documentation", self._showVersion3Documentation),
            ("Show License", self._showCcpnLicense),
            (),
            ("CcpNmr Homepage", self._showAboutCcpn),
            ("CcpNmr V3 Forum", self._showForum),
            (),
            # ("Inspect Code...", self.showCodeInspectionPopup, [('shortcut', 'gv'),
            #                                                    ('enabled', False)]),
            # ("Show Issues...", self.showIssuesList),
            ("Check for Updates...", self._showUpdatePopup),
            ("Register...", self._showRegisterPopup),
            (),
            ("About CcpNmr V3...", self._showAboutPopup),
            ]
                   ))

    def _setColourSchemeAndStyleSheet(self):
        """Set the colourScheme and stylesheet as determined by arguments --dark, --light or preferences
        """
        from ccpn.ui.gui.guiSettings import Theme

        prefsApp = self.preferences.appearance
        prefsGen = self.preferences.general

        if self.args.darkColourScheme:
            th = Theme.DARK
        elif self.args.lightColourScheme:
            th = Theme.LIGHT
        else:
            th = Theme.getByDataValue((cs := prefsApp.themeStyle) and cs.lower())
        if th is None:
            raise RuntimeError('invalid theme')

        thName = str(th.dataValue).capitalize()
        self._themeStyle = th
        self._themeColour = prefsApp.themeColour

        _qssPath = widgetsPath / ('%sStyleSheet.qss' % thName)  # assume capitalised
        with _qssPath.open(mode='r') as fp:
            styleSheet = fp.read()
        if platform.system() == 'Linux':
            _qssPath = widgetsPath / ('%sAdditionsLinux.qss' % thName)
            with _qssPath.open(mode='r') as fp:
                additions = fp.read()
            styleSheet += additions
        self._styleSheet = None  #styleSheet - disabled for the minute
        if sd := Theme.getByDataValue((cs := prefsGen.colourScheme) and cs.lower()):
            self._themeSDStyle = sd

    #-----------------------------------------------------------------------------------------
    # callback methods
    #-----------------------------------------------------------------------------------------

    def _nyi(self):
        """Not yet implemented"""
        pass

    #-----------------------------------------------------------------------------------------
    # File --> callback methods
    #-----------------------------------------------------------------------------------------
    def _loadDataCallback(self):
        """Call loadData from the menu and trap errors.
        """
        self.ui.loadData()

    def _newProjectCallback(self):
        """Callback for creating new project
        """
        self.ui.newProject()

    def _openProjectCallback(self):
        """
        Opens a OpenProject dialog box if project directory is not specified.
        Loads the selected project.
        """
        self.ui.loadProject()

    def _importNefCallback(self):
        """menu callback; use ui.loadData to do the lifting
        """
        from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader

        # self.ui.loadData(formatFilter=(NefDataLoader.dataFormat,))
        self._loadDataIgnoreExtension(NefDataLoader)

    def _loadNMRStarFileCallback(self):
        """menu callback; use ui.loadData to do the lifting
        """
        from ccpn.framework.lib.DataLoaders.StarDataLoader import StarDataLoader

        # self.ui.loadData(formatFilter=(StarDataLoader.dataFormat,))
        self._loadDataIgnoreExtension(StarDataLoader)

    def _loadDataIgnoreExtension(self, dataLoader=None) -> list:
        """Load the data defined by dataLoader, provides file dialog.

        :param dataLoader: Data Loader used to import data
        :return: a list of loaded objects
        """
        from ccpn.ui.gui.widgets import FileDialog
        if not dataLoader:
            getLogger().debug('Load failed no DataLoader provided')
            return

        dialog = FileDialog.DataFileDialog(parent=self.mainWindow, acceptMode='load')
        dialog._show()
        if (path := dialog.selectedFile()) is None:
            return []
        paths = [path]

        dataLoaders = []
        for path in paths:
            _path = aPath(path)
            if not _path.exists():
                txt = f'"{path}" does not exist'
                getLogger().warning(txt)
                MessageDialog.showError('Load Data', txt, parent=self)
                continue
            # loads data using the provided dataLoader
            dataLoaders.append(dataLoader(path))

        # unmodified from GUI line 830
        objs = self.ui.application._loadData(dataLoaders)
        if len(objs) == 0:
            _pp = ','.join(f'"{p}"' for p in paths)
            txt = f'No objects were loaded from {_pp}'
            getLogger().warning(txt)
            MessageDialog.showError('Load Data', txt, parent=self.mainWindow)

        return objs

    def _saveCallback(self):
        """The project save callback"""
        if self.project.isTemporary:
            # if temporary then use the saveAs dialog
            self.ui.saveProjectAs()

        # elif self.project.readOnly:
        #     MessageDialog.showWarning('Save Project', 'Project is read-only')

        else:
            self.saveProject()
            # successful = self.saveProject()
            # if not successful:
            #     getLogger().warning("Error saving project")
            #     MessageDialog.showError('Save Project', f'Error saving {self.project}')

    def _saveAsCallback(self):
        """Opens save Project as dialog box and saves project to path specified
        in the file dialog.
        """
        self.ui.saveProjectAs()

    def _archiveProjectCallback(self):

        if (path := self.saveToArchive()) is None:
            MessageDialog.showInfo('Archive Project',
                                   'Unable to archive Project')

        else:
            MessageDialog.showInfo('Archive Project',
                                   'Project archived to %s' % path)
            self.ui.mainWindow._updateRestoreArchiveMenu()

    def _restoreFromArchiveCallback(self):
        """Restore a project from archive
        """
        archivesDirectory = aPath(self.project.path) / CCPN_ARCHIVES_DIRECTORY
        _filter = '*.tgz'
        dialog = ArchivesFileDialog(parent=self.ui.mainWindow,
                                    acceptMode='select',
                                    directory=archivesDirectory,
                                    fileFilter=_filter)
        dialog._show()
        archivePath = dialog.selectedFile()

        if archivePath and \
                (newProject := self.restoreFromArchive(archivePath)) is not None:
            MessageDialog.showInfo('Restore from Archive',
                                   'Project restored as %s' % newProject.path)

    def _saveLayoutCallback(self):
        Layout.updateSavedLayout(self.ui.mainWindow)
        getLogger().info('Layout saved')

    def _saveLayoutAsCallback(self):
        path = _getSaveLayoutPath(self.mainWindow)
        try:
            print(path)
            Layout.saveLayoutToJson(self.mainWindow, jsonFilePath=path)
            getLogger().info('Layout saved to %s' % path)
        except Exception as es:
            getLogger().warning('Impossible to save layout. %s' % es)

    def _restoreLastSavedLayoutCallback(self):
        self.ui.mainWindow.moduleArea._closeAll()
        Layout.restoreLayout(self.ui.mainWindow, self.layout, restoreSpectrumDisplay=True)

    def _restoreLayoutFromFileCallback(self):
        if (path := _getOpenLayoutPath(self.mainWindow)) is None:
            return
        self._restoreLayoutFromFile(path)

    def _showProjectSummaryPopup(self):
        """Show the Project summary popup.
        """
        from ccpn.ui.gui.popups.ProjectSummaryPopup import ProjectSummaryPopup

        if self.ui:
            popup = ProjectSummaryPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow, modal=True)
            popup.show()
            popup.raise_()
            popup.exec_()

    def _showApplicationPreferences(self):
        """
        Displays Application Preferences Popup.
        """
        from ccpn.ui.gui.popups.PreferencesPopup import PreferencesPopup

        popup = PreferencesPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
        popup.exec_()

    def _quitCallback(self, event=None):
        """
        Saves application preferences. Displays message box asking user to save project or not.
        Closes Application.
        """
        self.ui.mainWindow._closeEvent(event=event)

    #-----------------------------------------------------------------------------------------
    # Spectra --> callback methods
    #-----------------------------------------------------------------------------------------
    def _loadSpectraCallback(self):
        """Load all the spectra callback
        """
        self.ui.loadSpectra()

    #-----------------------------------------------------------------------------------------
    # Help -->
    #-----------------------------------------------------------------------------------------

    def _showBeginnersTutorial(self):
        from ccpn.framework.PathsAndUrls import beginnersTutorialPath

        self._systemOpen(beginnersTutorialPath)

    def _showBackboneTutorial(self):
        from ccpn.framework.PathsAndUrls import backboneAssignmentTutorialPath

        self._systemOpen(backboneAssignmentTutorialPath)

    def _showCSPtutorial(self):
        from ccpn.framework.PathsAndUrls import cspTutorialPath

        self._systemOpen(cspTutorialPath)

    def _showScreenTutorial(self):
        from ccpn.framework.PathsAndUrls import screenTutorialPath

        self._systemOpen(screenTutorialPath)

    def _showVersion3Documentation(self):
        """Displays CCPN wrapper documentation in a module.
        """
        from ccpn.framework.PathsAndUrls import ccpnDocumentationUrl, documentationPath

        if self.preferences.appearance.useOnlineDocumentation:
            self._showHtmlFile("Analysis Version-3 Documentation", ccpnDocumentationUrl)
        else:
            self._showHtmlFile("Analysis Version-3 Documentation", documentationPath)

    def _showForum(self):
        """Displays Forum in a module.
        """
        from ccpn.framework.PathsAndUrls import ccpnForum

        self._showHtmlFile("Analysis Version-3 Forum", ccpnForum)

    def _showShortcuts(self):
        from ccpn.framework.PathsAndUrls import shortcutsPath

        self._showHtmlFile("Shortcuts", shortcutsPath)

    def _showAboutPopup(self):
        from ccpn.ui.gui.popups.AboutPopup import AboutPopup

        popup = AboutPopup(parent=self.ui.mainWindow)
        popup.exec_()

    def _showAboutCcpn(self):
        from ccpn.framework.PathsAndUrls import ccpnUrl

        self._showHtmlFile("About CCPN", ccpnUrl)

    def _showIssuesList(self):
        from ccpn.framework.PathsAndUrls import ccpnIssuesUrl

        self._showHtmlFile("CCPN Issues", ccpnIssuesUrl)

    def _showTutorials(self):
        from ccpn.framework.PathsAndUrls import ccpnTutorials

        self._showHtmlFile("CCPN Tutorials", ccpnTutorials)

    def _showRegisterPopup(self):
        """Open the registration popup
        """
        self.ui._registerDetails()

    def _showCcpnLicense(self):
        from ccpn.framework.PathsAndUrls import ccpnLicenceUrl

        self._showHtmlFile("CCPN Licence", ccpnLicenceUrl)

    def _showUpdatePopup(self):
        """Open the update popup
        CCPNINTERNAL: Also called from.Gui._executeUpdates
        """
        from ccpn.framework.update.UpdatePopup import UpdatePopup
        from ccpn.util import Url

        # check valid internet connection first
        if Url.checkInternetConnection():
            updatePopup = UpdatePopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            updatePopup.exec_()

            # if updates have been installed then popup the quit dialog with no cancel button
            if updatePopup._updatesInstalled:
                self.ui.mainWindow._closeWindowFromUpdate(disableCancel=True)

        else:
            MessageDialog.showWarning('Check For Updates',
                                      'Could not connect to the update server, please check your internet connection.')

    #-----------------------------------------------------------------------------------------
    # Inactive
    #-----------------------------------------------------------------------------------------

    def _showLicense(self):
        from ccpn.framework.PathsAndUrls import licensePath

        self._showHtmlFile("CCPN Licence", licensePath)

    def _showSubmitMacroPopup(self):
        """Open the submit macro popup
        """
        from ccpn.ui.gui.popups.SubmitMacroPopup import SubmitMacroPopup
        from ccpn.util import Url

        # check valid internet connection first
        if Url.checkInternetConnection():
            submitMacroPopup = SubmitMacroPopup(parent=self.ui.mainWindow)
            submitMacroPopup.show()
            submitMacroPopup.raise_()

        else:
            MessageDialog.showWarning('Submit Macro',
                                      'Could not connect to the server, please check your internet connection.')

    def _showFeedbackPopup(self):
        """Open the submit feedback popup
        """
        from ccpn.ui.gui.popups.FeedbackPopup import FeedbackPopup
        from ccpn.util import Url

        # check valid internet connection first
        if Url.checkInternetConnection():

            # this is non-modal so you can copy/paste from the project as required
            feedbackPopup = FeedbackPopup(parent=self.ui.mainWindow)
            feedbackPopup.show()
            feedbackPopup.raise_()

        else:
            MessageDialog.showWarning('Submit Feedback',
                                      'Could not connect to the server, please check your internet connection.')

    #-----------------------------------------------------------------------------------------
    # Implementation methods
    #-----------------------------------------------------------------------------------------

    def _showHtmlFile(self, title, urlPath):
        """Displays html files in program QT viewer or using native webbrowser
        depending on useNativeWebbrowser option in preferences
        """
        useNative = self.preferences.general.useNativeWebbrowser

        if useNative:
            import webbrowser
            import posixpath

            # may be a Path object
            urlPath = str(urlPath)

            urlPath = urlPath or ''
            if (urlPath.startswith('http://') or urlPath.startswith('https://')):
                pass
            elif urlPath.startswith('file://'):
                urlPath = urlPath[len('file://'):]
                urlPath = urlPath.replace(os.sep, posixpath.sep) if isWindowsOS() else f'file://{urlPath}'

            elif isWindowsOS():
                urlPath = urlPath.replace(os.sep, posixpath.sep)
            else:
                urlPath = f'file://{urlPath}'

            webbrowser.open(urlPath)
            # self._systemOpen(path)

        else:
            # mainWindow = self.ui.mainWindow
            #
            # mainWindow.newHtmlModule(urlPath=urlPath, position='top', relativeTo=mainWindow.moduleArea)
            getLogger().debug('non-native newHtmlModule has been removed')

    def _addApplicationMenuSpec(self, spec, position=-3):
        """Add an entirely new menu at specified position"""
        self._menuSpec.insert(position, spec)

    def _addApplicationMenuItem(self, menuName, menuItem, position):
        """Add a new item to an existing menu at specified position"""
        for spec in self._menuSpec:
            if spec[0] == menuName:
                spec[1].insert(position, menuItem)
                return

        raise ValueError(f'No menu with name {menuName}')

    def _addApplicationMenuItems(self, menuName, menuItems, position):
        """Add a new items to an existing menu starting at specified position"""
        for n, menuItem in enumerate(menuItems):
            self._addApplicationMenuItem(menuName, menuItem, position + n)

    def _updateCheckableMenuItems(self):
        # This has to be kept in sync with menu items below which are checkable,
        # and also with MODULE_DICT keys
        # The code is terrible because Qt has no easy way to get hold of menus / actions

        mainWindow = self.ui.mainWindow
        if mainWindow is None:
            # We have a UI with no mainWindow - nothing to do.
            return

        menuChildren = mainWindow.menuBar().findChildren(QtWidgets.QMenu)
        if not menuChildren:
            return

        topActionDict = {}
        for topMenu in menuChildren:
            mainActionDict = {mainAction.text(): mainAction for mainAction in topMenu.actions()}

            topActionDict[topMenu.title()] = mainActionDict

        openModuleKeys = set(mainWindow.moduleArea.modules.keys())
        for key, topActionText, mainActionText in (('SEQUENCE', 'Molecules', 'Show Sequence'),
                                                   ('PYTHON CONSOLE', 'View', 'Python Console')):
            if key in openModuleKeys:
                if mainActionDict := topActionDict.get(topActionText):
                    if mainAction := mainActionDict.get(mainActionText):
                        mainAction.setChecked(True)

    @staticmethod
    def _testShortcuts0():
        print('>>> Testing shortcuts0')

    @staticmethod
    def _testShortcuts1():
        print('>>> Testing shortcuts1')

    # GWV 22022/1/24: Copied from Ui
    # def addMenu(self, name, position=None):
    #     """
    #     Add a menu specification for the top menu bar.
    #     """
    #     if position is None:
    #         position = len(self._menuSpec)
    #     self._menuSpec.insert(position, (str(name), []))


#end class

#-----------------------------------------------------------------------------------------
# Helper code
#-----------------------------------------------------------------------------------------

def _getOpenLayoutPath(mainWindow):
    """Opens a saved Layout as dialog box and gets directory specified in the
    file dialog.
    :return selected path or None
    """

    fType = 'JSON (*.json)'
    dialog = LayoutsFileDialog(parent=mainWindow, acceptMode='open', fileFilter=fType)
    dialog._show()
    path = dialog.selectedFile()
    return path or None


def _getSaveLayoutPath(mainWindow):
    """Opens save Layout as dialog box and gets directory specified in the
    file dialog.
    :return selected path or None
    """

    jsonType = '.json'
    fType = 'JSON (*.json)'
    dialog = LayoutsFileDialog(parent=mainWindow, acceptMode='save', fileFilter=fType)
    dialog._show()
    newPath = dialog.selectedFile()
    if not newPath:
        return None

    newPath = aPath(newPath).assureSuffix(jsonType)
    if newPath.exists():
        # should not really need to check the second and third condition above, only
        # the Qt dialog stupidly insists a directory exists before you can select it
        # so if it exists but is empty then don't bother asking the question
        title = 'Overwrite path'
        msg = 'Path "%s" already exists, continue?' % newPath
        if not MessageDialog.showYesNo(title, msg):
            return None

    return newPath
