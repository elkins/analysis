"""Module Documentation here

Read-Only Project
^^^^^^^^^^^^^^^^^

Test should contain the following folders, as of 3.1.1

::

    _temporary
    \----temp1.ccpn
        \----Archives
        \----Backup
            \----Backup folder 1.ccpnV3backup
        \----ccpnv3
            \----ccp
                \----lims
                    \----RefSampleComponent
                    \----Sample
                \----molecule
                    \----MolStructure
                    \----MolSystem
                \----nmr
                    \----Nmr
            \----memops
                \----implementation
        \----data
            \----plugins
            \----spectra
        \----logs
        \----scripts
        \----state
        \----summaries
        
    \----temp2.ccpn
        \----ccpnv3
            \----ccp
                \----lims
                    \----RefSampleComponent
                    \----Sample
                \----molecule
                    \----MolStructure
                    \----MolSystem
                \----nmr
                    \----Nmr
            \----memops
                \----implementation

    \----temp3.ccpn
        \----Archives
        \----Backup
            \----Backup folder 1.ccpnV3backup
        \----ccpnv3
            \----ccp
                \----lims
                    \----RefSampleComponent
                    \----Sample
                \----molecule
                    \----MolStructure
                    \----MolSystem
                \----nmr
                    \----Nmr
            \----memops
                \----implementation
        \----data
            \----plugins
            \----spectra
        \----logs
        \----scripts
        \----state
        \----summaries


Projects on loading only require the ccpnv3 folder.

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-03-21 15:38:20 +0000 (Fri, March 21, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import sys
import time
import shutil
import contextlib

from PyQt5 import QtCore, QtWidgets
from ccpn.core.testing.WrapperTesting import WrapperTesting
from ccpn.ui.gui.guiSettings import consoleStyle
from ccpn.util.Path import aPath
from ccpn.util.OrderedSet import OrderedSet
from ccpn.framework.PathsAndUrls import userCcpnPath
from ccpn.framework.Application import getApplication


TEMPFOLDER = '_temporary'
TEMPPROJECT1 = 'temp1.ccpn'
TEMPPROJECT2 = 'temp2.ccpn'
TEMPPROJECT3 = 'temp3.ccpn'
V3FOLDER = 'ccpnv3'

tempFolder = userCcpnPath / TEMPFOLDER
tempProjectDir1 = tempFolder / TEMPPROJECT1
tempProjectDir2 = tempFolder / TEMPPROJECT2
tempProjectDir3 = tempFolder / TEMPPROJECT3

_printAll = True
os.system('')  # activates console text colours


class ProjectReadOnly(WrapperTesting):
    # Path of project to load (None for new project)
    projectPath = None
    eventCount = 0
    dirEvents = set()
    fileEvents = set()

    noLogging = False
    noDebugLogging = False
    noEchoLogging = False  # block all logging to the terminal - debug<n>|warning|info
    _lock = QtCore.QMutex()

    def _fileEvent(self, fp):
        with QtCore.QMutexLocker(self._lock):  # is this required? :|
            if fp.endswith('.DS_Store'):
                # skip OS files
                return
            if fp in self.fileEvents:
                print(f'{consoleStyle.fg.darkmagenta}    file ***       {fp}')
                return
            self.fileEvents.add(fp)
            if _printAll:
                print(f'{consoleStyle.fg.magenta}    file     {len(self.fileEvents):2}    {fp}')

    def _dirEvent(self, fp):
        # STILL sometimes getting a duplicate dirEvent, OR a missing event in the middle of a directory structure
        with QtCore.QMutexLocker(self._lock):  # is this required? :|
            if fp in self.dirEvents:
                print(f'{consoleStyle.fg.darkgreen}    dir  ***       {fp}')
                return
            self.dirEvents.add(fp)
            if _printAll:
                print(f'{consoleStyle.fg.green}    dir      {len(self.dirEvents):2}    {fp}')

    def _wait(self, app, watcher):
        # add any new files to the watcher
        self.watchWalk(watcher, tempProjectDir1)
        self.watchWalk(watcher, tempProjectDir2)
        self.watchWalk(watcher, tempProjectDir3)

        # wait for arbitrary time for IO to complete
        time.sleep(6)
        app.processEvents()

    @staticmethod
    def watchWalk(watcher, path):
        with contextlib.suppress(Exception):
            for root, dirs, files in os.walk(str(path)):
                for dd in dirs:
                    r = aPath(root) / dd
                    watcher.addPath(str(r))
                for ff in files:
                    r = aPath(root) / ff
                    watcher.addPath(str(r))

    @contextlib.contextmanager
    def checkEvents(self, app, watcher):
        self.dirEvents = set()
        self.fileEvents = set()
        try:
            yield
        finally:
            self._wait(app, watcher)
            print(f'dirEvents {len(self.dirEvents)}')
            print(f'fileEvents {len(self.fileEvents)}')

    def test_readOnly(self):
        app = QtWidgets.QApplication(sys.argv)

        application = getApplication()
        project = application.project

        # current working-folder
        curDir = os.getcwd()
        # thisFile = aPath(curDir) / __file__

        # make a test-folder in the user's ~/.ccpn path
        userCcpnPath.fetchDir(TEMPFOLDER)
        # clean-up
        for fp in (TEMPPROJECT1, TEMPPROJECT2, TEMPPROJECT3):
            if (tempFolder / fp).exists():
                (tempFolder / fp).removeDir()

        self._watched_dir = tempFolder
        self._previous_dirs = OrderedSet(os.path.join(root, dir_name)
                                         for root, dirs, _ in os.walk(self._watched_dir, topdown=True)
                                         for dir_name in dirs)

        # used to check IO-events, whether project-folder or contents has changed
        watcher = QtCore.QFileSystemWatcher()
        watcher.addPath(str(tempFolder))
        watcher.directoryChanged.connect(self._dirEvent)
        watcher.fileChanged.connect(self._fileEvent)

        # Write the empty project to the temp-folder
        print('Writing project - waiting...')

        with self.checkEvents(app, watcher):
            # start from an empty project
            project.setReadOnly(False)
            application.saveProjectAs(tempProjectDir1, overwrite=True)

        # NOTE:ED - /_temporary folder has changed, contains new project
        """
        * dir-event
        ** file-event
        >> has contents
        x not watched

        App opens with a new project.
        watch _temporary folder
        Save project to _temporary should spawn dir-event for temp1.ccpn          
        (using set(), watcher may spawn 1 or 2 events on this folder, could be OS timing between touching files)
        
        _temporary
            *\----temp1.ccpn
                x\----Archives
                x\----Backup
                x\----ccpnv3
                    >>
                x\----data
                    >>
                x\----logs
                x\----scripts
                x\----state
                x\----summaries
        """
        self.assertEqual(len(self.dirEvents), 1)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        with self.checkEvents(app, watcher):
            # copy just the v2-folder
            shutil.copytree(tempProjectDir1 / V3FOLDER, tempProjectDir2 / V3FOLDER)
            shutil.copytree(tempProjectDir1 / V3FOLDER, tempProjectDir3 / V3FOLDER)

        # NOTE:ED - /_temporary folder has changed, contains 2 new projects
        """
        * dir-event
        ** file-event
        >> has contents

        All files/dir below _temporary are watched
        Copy the ccpnv3 folder to 2 new dirs to give 2 new minimal, empty projects: temp2/temp3.ccpn
        
        _temporary folder has changed, contains two new projects, notifies new dirs
        
        _temporary
            \----temp1.ccpn
                >>
            *\----temp2.ccpn                << creating folder
            *\----temp3.ccpn                << creating folder
        """
        # events registered as a set, so top-folder only once
        self.assertEqual(len(self.dirEvents), 1)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Creating objects - waiting...')

        print(project, id(project), project._wrappedData, id(project._wrappedData))
        print(project._getChildren())

        with self.checkEvents(app, watcher):
            project.setReadOnly(True)

            # create new objects that will use different .xml files
            project.newChemicalShiftList()
            nmrChain = project.newNmrChain()
            nmrChain.newNmrResidue()
            project.newSample()
            project.newSubstance()
            project.newStructureEnsemble()
            project.newComplex()
            project.newDataTable()
            project.newCollection()
            project.newNote()
            spectrum = project.newEmptySpectrum(isotopeCodes=('1H', '15N'))
            pkList = spectrum.newPeakList()
            pkList.newPeak(ppmPositions=[5.5, 5.5])

            # should do nothing as read-only, and no files/logging should okay
            application.saveProject()

        """
        * dir-event
        ** file-event
        >> has contents

        read-only should be no notifications
        
        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn
                >>
            \----temp3.ccpn
                >>
        """
        # NOTE:ED - no changes, project is read-only
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Enable writing - waiting...')

        with self.checkEvents(app, watcher):
            # allow saving again, but nothing should write
            project.setReadOnly(False)

        """
        * dir-event
        ** file-event
        >> has contents

        read-only has been disabled but should not write anything until explicit save, or crash-event

        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn
                >>
            \----temp3.ccpn
                >>
        """
        # NOTE:ED - not read-only, but no write
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Writing project again - waiting...')
        print(project, id(project))
        print(project._getChildren())

        with self.checkEvents(app, watcher):
            # should now write the files
            application.saveProject()

        """
        * dir-event
        ** file-event
        >> has contents
        x not watched
        
        explicit save-event, writes project files
        writes to the same log-file as same instance of app running
        backup is created in backup folder
                
        _temporary
            \----temp1.ccpn                     << current project
                \----Archives
                *\----Backup
                    >>
                *\----ccpnv3
                    *\----ccp
                        *\----lims
                            *\----RefSampleComponent
                                **file.xml
                            *\----Sample
                                **file.xml
                        *\----molecule
                            x\----MolStructure  << not in previous file-structure
                                >>
                            *\----MolSystem
                                **file.xml
                        *\----nmr
                            *\----Nmr
                                **file.xml
                    *\----memops
                        *\----implementation
                            **file.xml
                \----data
                    \----plugins
                    \----spectra
                *\----logs
                    **log.txt
                \----scripts
                *\----state
                    *\----spectra
                        >>
                    **state-file.json
                    **Current
                \----summaries
                
            \----temp2.ccpn
                \----ccpnv3
                    >>
            \----temp3.ccpn
                \----ccpnv3
                    >>
        """
        # NOTE:ED - all folders written to
        self.assertEqual(len(self.dirEvents), 15)
        self.assertTrue(all(f'{TEMPPROJECT1}/' in dd for dd in self.dirEvents))
        self.assertEqual(len(self.fileEvents), 8)
        self.assertTrue(all(f'{TEMPPROJECT1}/' in ff for ff in self.fileEvents))
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.xml')]), 5)
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.json')]), 1)
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.txt')]), 1)
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('/Current')]), 1)
        # Current does not have the .json extension :| will sort later

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Open new project 2 - waiting...')

        with self.checkEvents(app, watcher):
            project = application.loadProject(tempProjectDir2)

        """
        * dir-event
        ** file-event
        >> has contents

        loading new project - temp2.ccpn
        old project temp.ccpn is closed, as this is not read-only, log is NOT updated,
        project is NOT isModified
        
        _temporary
            \----temp1.ccpn             << previous project
                \----Archives
                \----Backup
                    >>
                \----ccpnv3
                    >>
                \----data
                    >>
                \----logs
                    >>
                \----scripts
                \----state
                    >>
                \----summaries

            \----temp2.ccpn             << loading
                >>
            \----temp3.ccpn
                >>
        """
        # NOTE:ED -  *** SHOULDN'T SAVE, PROJECT IS CLEAN :|
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)
        self.assertTrue(all(f'{TEMPPROJECT1}/logs' in dd for dd in self.dirEvents))
        self.assertTrue(all(f'{TEMPPROJECT1}/logs' in ff for ff in self.fileEvents))

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print(project, id(project), project._wrappedData, id(project._wrappedData))
        print(project._getChildren())

        with self.checkEvents(app, watcher):
            project.setReadOnly(True)

            # create new objects that will use different .xml files
            project.newChemicalShiftList()
            nmrChain = project.newNmrChain()
            nmrChain.newNmrResidue()
            project.newSample()
            project.newSubstance()
            project.newStructureEnsemble()
            project.newComplex()
            project.newDataTable()
            project.newCollection()
            project.newNote()
            spectrum = project.newEmptySpectrum(isotopeCodes=('1H', '15N'))
            pkList = spectrum.newPeakList()
            pkList.newPeak(ppmPositions=[5.5, 5.5])

            # should do nothing as read-only, and no files/logging should okay
            application.saveProject()

        """
        * dir-event
        ** file-event
        >> has contents

        temp2.ccpn is read-only, should not write anything until explicit save, or crash-event

        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn             << current project
                >>
            \----temp3.ccpn
                >>
        """
        # NOTE:ED - nothing written, temp.ccpn read-only
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Open new project 3 - waiting...')

        with self.checkEvents(app, watcher):
            project = application.loadProject(tempProjectDir3)

        """
        * dir-event
        ** file-event
        >> has contents

        read-only has been disabled but should not write anything until explicit save, or crash-event

        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn             << previous project
                >>
            \----temp3.ccpn             << loading
                >>
        """
        # NOTE:ED - nothing written, temp.ccpn read-only
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print(project, id(project), project._wrappedData, id(project._wrappedData))
        print(project._getChildren())

        with self.checkEvents(app, watcher):
            # create new objects that will use different .xml files
            project.newChemicalShiftList()
            nmrChain = project.newNmrChain()
            nmrChain.newNmrResidue()
            project.newSample()
            project.newSubstance()
            project.newStructureEnsemble()
            project.newComplex()
            project.newDataTable()
            project.newCollection()
            project.newNote()
            spectrum = project.newEmptySpectrum(isotopeCodes=('1H', '15N'))
            pkList = spectrum.newPeakList()
            pkList.newPeak(ppmPositions=[5.5, 5.5])

            # just set near the end somewhere
            project.setReadOnly(False)

            # not read-only, update files
            application.saveProject()

        """
        _temporary folder has changed
        * dir-event
        ** file-event
        >> has contents
        x not watched
                
        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn
                >>
                
            \----temp3.ccpn                 << current project
                x\----Archives
                x\----Backup
                    >>
                *\----ccpnv3
                    *\----ccp
                        *\----lims
                            *\----RefSampleComponent
                                **file.xml
                            *\----Sample
                                **file.xml
                        *\----molecule
                            x\----MolStructure      << not in previous file-structure
                                >>
                            *\----MolSystem
                                **file.xml
                        *\----nmr
                            *\----Nmr
                                **file.xml
                    *\----memops
                        *\----implementation
                            **file.xml
                x\----data
                    \----plugins
                    \----spectra
                x\----logs
                    >>
                x\----scripts
                x\----state
                    x\----spectra
                x\----summaries
        """
        # NOTE:ED - all folders written to
        # not watching backups/state/logs
        self.assertEqual(len(self.dirEvents), 11)
        self.assertTrue(all(f'{TEMPPROJECT3}/' in dd for dd in self.dirEvents))
        self.assertEqual(len(self.fileEvents), 5)
        self.assertTrue(all(f'{TEMPPROJECT3}/' in ff for ff in self.fileEvents))
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.xml')]), 5)
        # no json/txt - folders not watching

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Open new project 2 - waiting...')

        with self.checkEvents(app, watcher):
            # add new item to current project
            # NOTE:ED - SHOULD really be an error here for a modified project, or dialog-box
            project.newNote()

            project = application.loadProject(tempProjectDir2)

        """
        _temporary folder has changed
        * dir-event
        ** file-event
        >> has contents

        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn                 << loading
                >>

            \----temp3.ccpn                 << previous project
                \----Archives
                \----Backup
                    >>
                \----ccpnv3
                    >>
                \----data
                    \----plugins
                    \----spectra
                *\----logs
                    **log.txt
                \----scripts
                \----state
                    >>
                \----summaries
        """
        # NOTE:ED - log written to, folder and file, update log, same log file
        self.assertEqual(len(self.dirEvents), 1)
        self.assertEqual(len(self.fileEvents), 1)
        self.assertTrue(all(f'{TEMPPROJECT3}/logs' in dd for dd in self.dirEvents))
        self.assertTrue(all(f'{TEMPPROJECT3}/logs' in ff for ff in self.fileEvents))

        print(project, id(project), project._wrappedData, id(project._wrappedData))
        print(project._getChildren())

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Open new project 3 again - waiting...')

        with self.checkEvents(app, watcher):
            project = application.loadProject(tempProjectDir3)

        """
        * dir-event
        ** file-event
        >> has contents

        read-only has been disabled but should not write anything until explicit save, or crash-event

        _temporary
            \----temp1.ccpn
                >>
            \----temp2.ccpn             << previous project
                >>
            \----temp3.ccpn             << loading
                >>
        """
        # NOTE:ED - nothing written, project2 should be clean
        self.assertEqual(len(self.dirEvents), 0)
        self.assertEqual(len(self.fileEvents), 0)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print('Writing project again - waiting...')
        print(project, id(project))
        print(project._getChildren())

        with self.checkEvents(app, watcher):
            # should now write the files
            application.saveProject()

        """
        * dir-event
        ** file-event
        >> has contents

        explicit save-event, writes project files
        writes to the same log-file as same instance of app running
        backup is created in backup folder

        _temporary
            \----temp1.ccpn
                \----ccpnv3
                    >>
            \----temp2.ccpn
                \----ccpnv3
                    >>

            \----temp3.ccpn                     << current project
                \----Archives
                *\----Backup
                    >>
                *\----ccpnv3
                    *\----ccp
                        *\----lims
                            *\----RefSampleComponent
                                **file.xml
                            *\----Sample
                                **file.xml
                        *\----molecule              <== SOMETIMES this is skipped :|
                            *\----MolStructure
                                **file.xml
                            *\----MolSystem
                                **file.xml
                        *\----nmr
                            *\----Nmr
                                **file.xml
                    *\----memops
                        *\----implementation
                            **file.xml
                \----data
                    \----plugins
                    \----spectra
                *\----logs
                    **log.txt
                \----scripts
                *\----state
                    *\----spectra
                        *emptySpectrum.json
                    **state-file.json
                    **Current
                \----summaries
        """
        # NOTE:ED - this is a hack for OS that I cannot find :|
        moleculeDir = any(map(lambda fp: fp.endswith('temp3.ccpn/ccpnv3/ccp/molecule'), self.dirEvents))
        dirCount = 16 if moleculeDir else 15

        # NOTE:ED - all folders written to
        self.assertEqual(len(self.dirEvents), dirCount)
        self.assertTrue(all(f'{TEMPPROJECT3}/' in dd for dd in self.dirEvents))
        self.assertEqual(len(self.fileEvents), 10)
        self.assertTrue(all(f'{TEMPPROJECT3}/' in ff for ff in self.fileEvents))
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.xml')]), 6)

        # spectrum now in watched list
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.json')]), 2)
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('.txt')]), 1)
        self.assertEqual(len([ff for ff in self.fileEvents if ff.endswith('/Current')]), 1)
        # Current does not have the .json extension :| will sort later
