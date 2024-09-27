"""
Xml loading code

=========================================================================================
The routines are adapted from and (partially/mostly/all?) replace :
  ccpn.core._implementation.Io
  ccpnmodel.ccpncore.lib.Io.Api
  ccpnmodel.ccpncore.lib.ApiPath
  ccpnmodel/ccpncore/memops/format/xml/XmlIO.py


api.memops.implementation
<MemopsRoot>
    .topObjects  --> a (frozen)set of topObject Instances
    .__dict__('topObjects') --> a dict of (guid,topObject) pairs
    .root  --> self
    .repositories --> a (frozen)set of Repository Instances
    ._upgradesFromV2
    ._movedPackageNames   --> (see below)
    ._notifies --> dict (class attribute)
    ._undo
    .isLoaded
    .isDeleted
    .isModified
    .isModifiable
    .name

    def sortedNmrProjects() (in api.Implementation.memops:19120)
                                        --> calls self.refreshTopObjects('ccp.nmr.Nmr)
    .nmrProjects --> a (frozen)set of NmrProject Instances

    def newNmrProject(name)             --> calls self.refreshTopObjects('ccp.nmr.Nmr)
                                        --> calls self.refreshTopObjects('ccp.lims.Sample)
                                            (2x; once from SampleStore, once from Sample)
                                        --> calls self.refreshTopObjects('ccp.lims.RefSampleComponent') (2x)
                                        --> calls self.refreshTopObjects('ccp.molecule.MolSystem')
                                        --> calls self.refreshTopObjects('ccp.nmr.NmrConstraint')
                                        from initialiseGraphicsData
                                        --> calls self.refreshTopObjects('ccpnmr.gui.Window') (3x)
                                        --> calls self.refreshTopObjects('ccpnmr.gui.Task') (2x)

                                        and then all over again upon restoring project through
                                        _getAllWrappedData(), which calls sortedXYZ type routines

                                        --> newChemicalShiftList, ... calls _getApiObjectTree, which calls
                                            _checkDelete which does refreshTopObjects on 'cambridge.Dangle'
                                            ....
                                        --> Project._update through AbstractWrapperObject._getAllDecendants:685, again
                                            refreshTopObjects on 'ccp.nmr.NmrEntry', 'ccp.nmr.NmrConstraint',
                                            'ccp.nmr.NmrConstraint' ....

    def refreshTopObjects(packageName) (in api.Implementation.memops:14737)
                                        --> loops over repositories with packageName
                                               uses Repository.getFileLocation(packageName)
                                               loops over xml-files in repository path / packageName
                                               uses guid extracted from the filepath to check if object exists
                                        --> ultimately calls XmlIo.loadFromFile(memopsToot, path)
                                            inserts Path.CCPN_API_DIRECTORY via ApiPath.getTopObjIdFromFileName
                                        --> calls XmlIo.loadFromStream)topObject=MemeosRoot):
                                        --> ultimately calls xml.Implementation.loadFromStream(topObject=MemopsRoot)

    def save()

    def saveAll()

    def saveModified()

    def saveTo(repository)

    <Repository>
        .stored                         --> frozenset of PackageLocator instances
        def getFileLocation(packageName) (in api.Implementation.memops:21594)  --> inserts Path.CCPN_API_DIRECTORY)

        <PackageLocator>
            .packageName
            .repositories

    <TopObject>                             --> essentially stored under MemopsRoot instance
        .guid                               --> a str defining the TopObject, matches the basename of the xml-file
        .__dict__('activeRepositories') -> list(Repository instances)
        .activeRepositories -> tuple(Repositories)
        .packageName
        .root -> MemopsRoot instance
        .isLoaded
        .isDeleted
        .isModified
        .isModifiable
        .name

        def load()                          --> calls loadFrom
        def loadFrom(repository)            --> calls XmlIo.loadTopObject

        def save()                          --> calls loadFrom
        def saveTo(repository)              --> calls XmlIo.save


==> <memops.Implementation.Repository ['generalData']>
ccpnmr.AnalysisProfile
==> <memops.Implementation.Repository ['refData']>
ccp.molecule.ChemComp
ccp.molecule.ChemCompCoord
ccp.molecule.ChemCompCharge
ccp.molecule.ChemElement
ccp.molecule.ChemCompLabel
ccp.molecule.StereoChemistry
ccp.nmr.NmrExpPrototype
ccp.nmr.NmrReference
ccpnmr.AnalysisProfile
==> <memops.Implementation.Repository ['backup']>
==> <memops.Implementation.Repository ['userData']>
ccp.molecule.ChemCompLabel
ccp.molecule.ChemComp
ccp.nmr.NmrExpPrototype
ccp.molecule.ChemCompCoord
ccp.molecule.ChemCompCharge
any


xml.memops.Implementation.py
    def loadFromStream(stream, topObjId=None, topObject=None, partialLoad=False):
                ---> load xml file
    :param topObjId: guid or name; must match
    :param topObject: None, MemopsRoot instance or TopObject instance
    :returns The object

=== Other Notes ===
closing a project calls:
 _closeAPIobjects, --> _getAPIObjectsStatus
--> APIStatus.buildAll --> api.memops.Implementation.getLabellingSchemes
--> refreshTopObjects --> reads xml-labelling schemes

Upon first opening the application, the default project get initialised and
the getExperimentClassifications triggers a refresh of the 'ccp.nmr.NmrExpProtoType'
package in refData. Fortunately, this is not read upon all subsequent newProject
loads only do the ~7 elementary topObjects, Framework is holding on to the
experimentClassificationDict.

From code:
# Special hack for moving data of renamed packages on upgrade
for newName, oldName in project._movedPackageNames.items():
    movePackageData(project, newName, oldName)

xmlLoader2.memopsRoot._movedPackageNames
            new-name                 old-name
Out[59]: {'ccp.molecule.Symmetry': 'molsim.Symmetry'}
--> implemented in XmlLoader.loadProject for V2 projects


=== Hotfixed methods ===

Using: ccpnmodel.ccpncore.lib.ApiPath._addModuleFunctionsToApiClass
       called from ccpnmodel.ccpncore.api.memops.Implementation

Imports Modules from ccpnmodel.ccpncore.lib:

Imported ccpnmodel.ccpncore.lib._memops.Implementation.MemopsRoot
Imported ccpnmodel.ccpncore.lib._ccp.general.DataLocation.AbstractDataStore
Imported ccpnmodel.ccpncore.lib._ccp.molecule.Molecule.Molecule
Imported ccpnmodel.ccpncore.lib._ccp.lims.RefSampleComponent.RefSampleComponentStore
Imported ccpnmodel.ccpncore.lib._ccp.molecule.MolSystem.Atom
Imported ccpnmodel.ccpncore.lib._ccp.molecule.MolSystem.Chain
Imported ccpnmodel.ccpncore.lib._ccp.molecule.MolSystem.MolSystem
Imported ccpnmodel.ccpncore.lib._ccp.molecule.MolSystem.Residue
Imported ccpnmodel.ccpncore.lib._ccp.nmr.NmrExpPrototype.RefExperiment
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.AbstractDataDim
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.DataSource
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.Experiment
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.NmrProject
--> inserts NmrProject.initialiseData() and NmrProject.initialiseGraphicsData()
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.Peak
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.PeakList
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.Resonance
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.ResonanceGroup
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.Shift
Imported ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.ShiftList
Imported ccpnmodel.ccpncore.lib._ccp.nmr.NmrConstraint.GenericConstraint

ccpncore.lib.chemComp.Io  --> fetchChemComp  (and others) : uses XmlIo.LoadFromFile


=========================================================================================

"""
from __future__ import annotations  # pycharm still highlights as errors


#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Geerten Vuister $"
__dateModified__ = "$dateModified: 2023-01-10 14:30:43 +0000 (Tue, January 10, 2023) $"
__version__ = "$Revision: 3.1.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2018-05-14 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import re
import sys
from contextlib import contextmanager

from ccpnmodel.ccpncore.api.memops import Implementation
from ccpnmodel.ccpncore.memops.metamodel import Constants as metaConstants
from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import NmrProject
from ccpnmodel.ccpncore.memops.format.xml import XmlIO
from ccpnmodel.v_3_0_2.upgrade import correctFinalResult

# from ccpn.core.Project import Project
from ccpn.core.lib.ProjectLib import checkProjectName, isV2project, isV3project
from ccpn.core.lib.ContextManagers import _apiBlocking

from ccpn.util.traits.TraitBase import TraitBase
from ccpn.util.traits.CcpNmrTraits import Unicode, Bool, CPath, Any, Int, Dict, List, Tuple
from ccpn.util.Common import getProcess

from ccpn.util.Logging import getLogger
from ccpn.util.Path import Path, aPath

from ccpn.framework.Application import getApplication
from ccpn.framework.PathsAndUrls import \
    CCPN_API_DIRECTORY, \
    CCPN_DIRECTORY_SUFFIX, \
    CCPN_BACKUP_SUFFIX, \
    ccpnmodelDataPythonPath, \
    userCcpnDataPath, \
    CCPN_BACKUPS_DIRECTORY

from ccpn.ui.gui.guiSettings import consoleStyle


#--------------------------------------------------------------------------------------------
# definitions
#--------------------------------------------------------------------------------------------

MEMOPS = metaConstants.modellingPackageName
IMPLEMENTATION = metaConstants.implementationPackageName
MEMOPS_PACKAGE = f'{MEMOPS}.{IMPLEMENTATION}'
# API_SUB_DIRECTORIES     = ['ccp', 'ccpnmr', MEMOPS]

XML_SUFFIX = '.xml'
BACKUP_SUFFIX = '.ccpnV3backup'
AUTOBACKUP_SUFFIX = '.ccpnV3autobackup'
TEMPBACKUP_SUFFIX = '.ccpnV3tempbackup'
KEY_SEPARATOR = '+'

XML_LOADER_ATTR = 'xmlLoader'  # attribute name for MemopsRoot
ACTIVE_REPOSITORIES_ATTR = 'activeRepositories'

# repositories
USERDATA = 'userData'
REFDATA = 'refData'
GENERALDATA = 'generalData'
BACKUPDATA = 'backup'
REPOSITORIES = [USERDATA, REFDATA, GENERALDATA, BACKUPDATA]

USERDATA_PACKAGES = ['ccp.nmr.Nmr',
                     'ccp.lims.RefSampleComponent',
                     'ccp.lims.Sample'
                     'ccp.molecule.MolSystem',
                     'ccpnmr.gui.Task',
                     'ccpnmr.gui.Window',
                     ]

# Current reference data packages with xml-data
REFDATA_PACKAGES = ['ccp.molecule.ChemCompCoord',
                    'ccp.molecule.ChemComp',
                    'ccp.molecule.ChemElement',
                    'ccp.molecule.ChemCompLabel',
                    'ccp.nmr.NmrExpPrototype',
                    'ccp.nmr.NmrReference'
                    ]

#TODO: original code implemented silencing of garbage collection on reading/writing: still valid?
SILENCE_GARBAGE_COLLECTION = False


class XmlLoaderABC(TraitBase):
    """Base class for the data structure
    """
    root = Any(default_value=None, allow_none=True)
    _id = Tuple()

    _readOnly = Bool(False)  # flag indicating a read-only project, default False, but True for V2 projects
    logger = Any(default_value=None, allow_none=True)

    def __init__(self, root, readOnly: bool = False):
        super().__init__()
        self.root = root

        self._setReadOnly(readOnly)
        self.logger = getLogger()

    @property
    def id(self) -> tuple:
        """:return the id as a tuple
        """
        return self._id

    @property
    def readOnly(self):
        """Return the read-only state
        """
        return self._readOnly

    def _setReadOnly(self, value):
        """Set the read-only state
        CCPNInternal - subclasses should only be initiated by the root of the loader tree
        """
        self._readOnly = value

    @property
    def _readOnlyState(self) -> str:
        """Return a quick reference read-only state of the object
        """
        return 'T' if self.readOnly else 'F'

    def addToLookup(self):
        """Add self.id to the root lookup dict
        """
        self.root._lookupDict[self.id] = self

    def lookup(self, id: tuple):
        """Lookup object corresponding to id, or root if id is None
        """
        if id is None:
            return self.root
        else:
            return self.root._lookupDict.get(id)

    def getTopObjects(self) -> list:
        """:return a list with topObjects
        to be sub-classed
        """
        return [self]

    @property
    def loadedTopObjects(self) -> list:
        """:return a list of all loaded topObjects
        """
        return [topObj for topObj in self.getTopObjects() if topObj.isLoaded]


class TopObject(XmlLoaderABC):
    """
    A class to maintain a TopObject, i.e. a child of a Package
    """
    _guid = Unicode(default_value=None, allow_none=True)
    _path = CPath(default_value=None, allow_none=True)
    isLoaded = Bool(False)  # Flag to indicate load has been completed
    isReading = Int(default_value=0)  # Reading indicator, as topObjects recursive get called to load!

    # parent
    package = Any(default_value=None, allow_none=True)

    # data
    apiTopObject = Any(default_value=None, allow_none=True)

    def __init__(self, package: Package, path: Path, readOnly: bool = False):

        if package is None:
            raise ValueError('package is None')

        super().__init__(root=package.root, readOnly=readOnly)

        self.package = package
        self._path = path.relative_to(self.package.path)
        self._guid = self._getGuidFromXmlPath(path)

        # ApiTopObject only knows about its guid and packageName, not its repository!
        # However, the two should be unique for the _id
        self._id = (None, self.package.name, self.guid)
        self.addToLookup()

    @property
    def guid(self) -> str:
        """:return the guid of the topObject
        """
        return self._guid

    @property
    def path(self) -> Path:
        """:return the full path of the topObject
        """
        return self.package.path / self._path

    @property
    def apiName(self) -> (str, None):
        """:return a constructed name from the apiTopObject or None if apiTopObject
                   is undefined
        """
        if self.apiTopObject is None:
            return None
        _atop = self.apiTopObject
        _name = _atop.name if hasattr(_atop, 'name') else 'noName'
        return f'{_atop.className}-{_name}'

    def load(self, reload: bool = False) -> TopObject:
        """Load self, either as a new api topObject or reload for an existing api topObject
        :param reload: flag to indicated reloading an existing apiTopObject (from xml)
        :return self
        """
        if self.isLoaded and not reload:
            return self

        # check self and memops for existence of apiTopObject;
        # Sometimes they get created prior to loading
        if self.apiTopObject is None:
            _apiTopObjects = forceGetattr(self.root.memopsRoot, 'topObjects')
            self.apiTopObject = _apiTopObjects.get(self.guid)
            if not self.apiTopObject:
                getLogger().debug2(f'{consoleStyle.fg.darkyellow}Undefined apiTopObject '
                                   f'{self.guid}{consoleStyle.reset}')

        _stack = self.root.loadingStack
        _stack.append(self)
        self._loadFromXml()
        _stack.pop()

        return self

    def _getGuidFromXmlPath(self, xmlPath) -> str:
        """Get the guid from the xml path
        :param xmlPath: Path instance defining the xml file
        :return guid as string
        """
        if not xmlPath.suffix == XML_SUFFIX:
            raise ValueError(f'"{xmlPath}" is not a valid xml-file')

        guid = xmlPath.basename.split(KEY_SEPARATOR)[-1]
        return guid

    def _loadFromXml(self):
        """Load api topObject from self.path
        """
        if not self.path.exists():
            raise FileNotFoundError(f'Failed to load {self.path!r}: file does not exist')

        if not self.isReading:
            self.isReading += 1
            with self.path.open('r') as fp:
                if self.apiTopObject is None:
                    try:
                        apiTopObject = loadFromStream(stream=fp,
                                                      topObject=self.root.memopsRoot,
                                                      topObjId=self.guid,
                                                      partialLoad=False)
                    except Exception as es:
                        raise RuntimeError(f'Failed to load "{self.path}": {es}') from es

                else:
                    try:
                        apiTopObject = self.apiTopObject
                        # Routine does not return an object if called with apiTopObj!!
                        result = loadFromStream(stream=fp,
                                                topObject=apiTopObject,
                                                topObjId=apiTopObject.guid,
                                                partialLoad=False)


                    except Exception as es:
                        raise RuntimeError(f'Failed to load "{self.path}": {es}') from es

            if apiTopObject is None:
                raise RuntimeError(f'Failed to load "{self.path}": unknown error')

            self.apiTopObject = apiTopObject
            self.isLoaded = True  # xml-file reflects contents

            # need to hack this as no other access method exists
            forceSetattr(apiTopObject, 'isModified', False)
            forceSetattr(apiTopObject, 'isLoaded', True)
            forceSetattr(apiTopObject, ACTIVE_REPOSITORIES_ATTR, [self.package.repository.apiRepository])

            self.isReading -= 1

        return

    def save(self, updateIsModified=True):
        """Save the apiTopObject to the xml file defined by self.path
        """
        if self.apiTopObject is None:
            getLogger().warning(f'{consoleStyle.fg.red}Cannot save {self._path}: '
                                f'undefined apiTopObject{consoleStyle.reset}')
            return

        if self.apiTopObject.isDeleted:
            # ignore deleted objects
            self.logger.debug2(f'Ignoring deleted object {self.apiTopObject}')
            return

        if not self.readOnly and not self.root.writeBlockingLevel:
            try:
                if not self.package.path.exists():
                    self.package.path.mkdir(parents=True, exist_ok=False)
                with self.path.open('w') as fp:
                    saveToStream(fp, self.apiTopObject)

            except (PermissionError, FileNotFoundError):
                self.logger.info('Saving: folder may be read-only')
            else:
                if updateIsModified:
                    # make sure that isModified is not updated if the file is not saved
                    forceSetattr(self.apiTopObject, 'isModified', False)
                self.isLoaded = True  # xml-file reflects contents

    def saveBackup(self, updateIsModified=True, autoBackupPath=None):
        """Save the apiTopObject to the xml file defined by self.path / CCPN_BACKUPS_DIRECTORY
        """
        if self.apiTopObject is None:
            getLogger().warning(f'{consoleStyle.fg.red}Cannot save {self._path}: '
                                f'undefined apiTopObject{consoleStyle.reset}')
            return
        if self.apiTopObject.isDeleted:
            # ignore deleted objects
            self.logger.debug2(f'ignoring deleted object {self.apiTopObject}')
            return
        if not autoBackupPath:
            raise ValueError('Auto-backup path is not defined')

        if not self.readOnly and not self.root.writeBlockingLevel:
            try:
                path = autoBackupPath / self.package.relativePath / self._path
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=False)
                with path.open('w') as fp:
                    saveToStream(fp, self.apiTopObject)

            except (PermissionError, FileNotFoundError):
                self.logger.info('Backing up: folder may be read-only')
            else:
                if updateIsModified:
                    # make sure that isModified is not updated if the file is not saved
                    forceSetattr(self.apiTopObject, 'isModified', False)

    def __str__(self):
        _loaded = 'loaded' if self.isLoaded else 'not-loaded'
        return f'<{self.__class__.__name__}: ({self.package.repository.name},{self.package.name}) "{self.guid}" ({_loaded})>'

    __repr__ = __str__


class Package(XmlLoaderABC):
    """
    A class to maintain a package, i.e. a child of a Repository
    Does not have an api equivalent.
    """
    _name = Unicode(default_value=None, allow_none=True)
    _path = CPath(default_value=None, allow_none=True)
    # parent
    repository = Any(default_value=None, allow_none=True)
    # children
    topObjects = List(default_value=[])  # top objects associated with this package

    def __init__(self, repository: Repository, path: Path, createPath: bool = False, readOnly: bool = False):
        """Initialise the object, optionally create the package path
        """
        if repository is None:
            raise ValueError('repository is None')

        super().__init__(root=repository.root, readOnly=readOnly)

        self.repository = repository

        self._path = path.relative_to(self.repository.path)
        if self.path.exists() and not self.path.is_dir():
            raise FileExistsError(f'{self.path} exists but is not a directory')

        if not self.path.exists() and createPath and not self.readOnly:
            try:
                self.path.mkdir(parents=True, exist_ok=False)
            except (PermissionError, FileNotFoundError):
                self.logger.info('Folder may be read-only')

        self._name = '.'.join(self._path.parts)
        self._id = (self.repository.name, self.name, None)
        self.addToLookup()

        self.topObjects = []
        if self.path.exists():
            for _path in self.xmlPaths:
                self._addTopObject(_path)

        # print('>>>', self)

    @property
    def name(self) -> str:
        """:return name of Package
        """
        return self._name

    @property
    def path(self) -> Path:
        """:return the full path of the Package
        """
        return self.repository.path / self._path

    @property
    def relativePath(self) -> Path:
        """:return the path of the Package relative to the topObject
        """
        return self._path

    @property
    def isMemops(self) -> bool:
        """:return: True is package is the memops package
        """
        return self.name == f'{MEMOPS}.{IMPLEMENTATION}'

    @property
    def xmlPaths(self) -> list:
        """:return a list of xml files present in self.path as Path instances
        """
        if not self.path.exists():
            return []

        result = list(self.path.listdir(suffix=XML_SUFFIX,
                                        excludeDotFiles=True,
                                        relative=False)
                      )
        return result

    @property
    def isLoaded(self) -> bool:
        """:return True if all topObjects have been loaded
        """
        return all(topObj.isLoaded for topObj in self.topObjects)

    def getTopObjects(self) -> list:
        """:return a list with topObjects
        """
        return self.topObjects

    def load(self, reload=False) -> list:
        """Load all topObject's of the package
        :return a list of all loaded topObjects
        """
        if self.isLoaded and not reload:
            return self.getTopObjects()

        result = []
        for topObj in self.getTopObjects():
            if not topObj.isLoaded or reload:
                topObj.load(reload=reload)
            result.append(topObj)

        return result

    def _addTopObject(self, path) -> TopObject:
        """Add TopObject instance defined by path
        :return TopObject instance
        """
        topObj = TopObject(package=self, path=path, readOnly=self.readOnly)
        self.topObjects.append(topObj)
        return topObj

    def _renamePackage(self, newName):
        """Move/Rename the package to newName;
        Use for V2 packages that have been renamed
        """
        if not self.root.isV2:
            raise RuntimeError(f'_renamePackage {self.name} to {newName}: Only for Version-2 projects')

        oldName = self.name
        oldPath = self.path
        oldId = self._id

        self._name = newName
        self._path = Path().joinpath(*newName.split('.'))
        # make a symlink to the old package directory
        if not self.readOnly:
            try:
                if self.path.exists() and self.path.is_symlink():
                    self.path.unlink()
                self.path.symlink_to(oldPath, target_is_directory=True)
            except (PermissionError, FileNotFoundError):
                self.logger.info('Folder may be read-only')

        self._id = (self.repository.name, self.name, None)
        # We keep the old _id's in the lookup, as I do not know how the
        # apiTopObjects will be referred to
        self.addToLookup()
        for topObj in self.topObjects:
            _id = (None, self.name, topObj.guid)
            topObj._id = _id
            topObj.addToLookup()

    def _setReadOnly(self, value):
        super()._setReadOnly(value)
        for topObj in self.topObjects:
            topObj._setReadOnly(value)

    @property
    def _readOnlyState(self) -> str:
        """Return a quick reference read-only state of the object and its XML children
        """
        return super()._readOnlyState + ''.join([obj._readOnlyState for obj in self.topObjects])

    def __str__(self):
        _defined = len(self.topObjects)
        _loaded = len(self.loadedTopObjects)
        return f'<Package "{self.name}": xmls:{_defined}; loaded:{_loaded}>'

    __repr__ = __str__


class Repository(XmlLoaderABC):
    """
    A class to maintain some repository info, as it is too hard to get this from the model
    """
    name = Unicode(default_value=None, allow_none=True)
    path = CPath(default_value=None, allow_none=True)
    useParent = Bool(False)  # Use the parent of the path to set the api url

    apiRepository = Any(default_value=None, allow_none=True)  # The corresponding api Repository instance

    # children
    packages = List()

    def __init__(self, xmlLoader: XmlLoader, name: str, path: Path, useParent: bool, createPath: bool = False,
                 readOnly: bool = False):
        """Initialise the object, optionally create the path
        """
        if xmlLoader is None:
            raise ValueError('xmlLoader is None')

        super().__init__(root=xmlLoader.root, readOnly=readOnly)

        self.name = name
        self._id = (self.name, None, None)
        self.addToLookup()

        self.path = path
        self.useParent = useParent
        self.apiRepository = xmlLoader.memopsRoot.findFirstRepository(name=name)

        if not self.path.exists() and createPath:
            self.path.mkdir(parents=True, exist_ok=False)

        if self.path.exists():
            self._definePackagesFromPath()

    def getTopObjects(self) -> list:
        """:return a list with topObjects as contained in the packages
        """
        result = []
        for pkg in self.packages:
            result.extend(pkg.getTopObjects())
        return result

    def load(self, reload=False) -> list:
        """Load all topObjects, as contained in the packages
        :param reload: flag to indicate reloading of all topObjects
        :return a list with all loaded topObjects
        """
        result = []
        for pkg in self.packages:
            if not pkg.isMemops:
                result.extend(pkg.load(reload=reload))
        return result

    def _definePackagesFromApi(self):
        """find and define (from apiRepository) the already (existing/possible) packages
        !!! This gives too many, as some package locators have both refData and userData
        """
        self.packages = []
        for _pLocator in [_p for _p in self.apiRepository.getStored()
                          if not (_p.targetName == 'any')
                          ]:
            for repo in _pLocator.repositories:
                if repo.name == self.name:
                    self._addPackage(name=_pLocator.targetName, createPath=False)

    def _definePackagesFromPath(self):
        """find and define the already existing packages from self.path
        """
        self.packages = []
        _paths = self._findPackagePaths()
        for _pkgPath in _paths:
            self._addPackage(path=_pkgPath, createPath=False)

    def _addPackage(self, name=None, path=None, createPath=False) -> Package:
        """Define and add a new package, either by name or by path,
        optionally create the Package directory
        :param name: the name of the package
        :param path: the path to the package
        :return newly created Package instance
        """
        if name is None and path is None:
            raise ValueError('Neither name nor path are defined')

        if name is not None and path is not None:
            raise ValueError('Both name and path are defined')

        if name is not None:
            path = self.path.joinpath(*name.split('.'))

        _pkg = Package(self, path=path, createPath=createPath, readOnly=self.readOnly)
        if not _pkg.isMemops:
            self.packages.append(_pkg)

        return _pkg

    def _findPackagePaths(self, path=None) -> list:
        """Recursively find all packages under path, initialised to self.path;
        Assume a package to be a directory containing XML files and no further
        containing packages
        :param path: path to initiate the search; defaults to self.path (i.e the root
                     of the repository.
        :return A list Path instances, each representing a package
        """
        if path is None:
            path = self.path

        result = []
        for _p in path.listdir(excludeDotFiles=True):

            if _p.is_dir():
                # recursion
                result.extend(self._findPackagePaths(_p))

            elif _p.suffix == XML_SUFFIX:
                # we found a xml-file in this directory; hence we assume path
                # is a package with xml-encoding TopObjects
                result.append(path)
                break

            else:
                pass

        # print(f'>returning> {path} found:{len(result)}')
        return result

    @property
    def apiRepositoryPath(self) -> Path:
        """:return Path instance of the current path defined in the apiRepository
        """
        if self.apiRepository is None:
            raise RuntimeError(f'{self}: no apiRepository defined')
        return aPath(self.apiRepository.url.path)

    def _updateApiRepositoryPath(self):
        """Update the url of the apiRepository, accounting for using parent of path
        """
        if self.apiRepositoryPath is None:
            raise RuntimeError('Undefined apiRepositoryPath')
        _path = self.path.parent if self.useParent else self.path
        _url = Implementation.Url(path=_path.asString())
        self.apiRepository.setUrl(_url)

    def _setReadOnly(self, value):
        super()._setReadOnly(value)
        for package in self.packages:
            package._setReadOnly(value)

    @property
    def _readOnlyState(self) -> str:
        """Return a quick reference read-only state of the object and its XML children
        """
        return super()._readOnlyState + ''.join([obj._readOnlyState for obj in self.packages])

    def __str__(self):
        return f'<Repository "{self.name}": loaded:{len(self.loadedTopObjects)}>'

    __repr__ = __str__


class XmlLoader(XmlLoaderABC):
    """
    Class to access and load the api (v2/3) data; 
    Does all the magic
    """

    #--------------------------------------------------------------------------------------------
    # @formatter:off

    path                 = CPath(default_value=None, allow_none=True)  # The V3 project path
    apiUserPath          = CPath(default_value=None, allow_none=True)  # The path as contained in the xml
    pathHasChanged       = Bool(False)  # indicates if repository data path is different from current path

    isV2                 = Bool(False)  # flag indicating V2 project, default False only set for loading
    # readOnly             = Bool(False)  # flag indicating a read-only project, default False, but True for V2 projects

    name                 = Unicode()    # project name, derived from path;
    nameHasChanged       = Bool(False)  # indicates if repository name is different from current name

    readingBlockingLevel = Int(default_value=0)  # reading blocking
    writeBlockingLevel   = Int(default_value=0)  # write blocking

    memopsXmlPath        = CPath(default_value=None, allow_none=True)  # The path to the memops (project) xml-file
    memopsRoot           = Any(default_value=None, allow_none=True)    # The MemopsRoot of the old-style V2 project object;
                                                                       # identical to self.apiNmrProject.root

    apiNmrProject        = Any(default_value=None, allow_none=True)    # The api NMR project

    # the children
    repositories         = List(default_value=[])  # List with Repository instances

    loadingStack         = List(default_value=[])  # for debugging

    # useFileLogger        = False  # Toggling the logging from Api calls (!?) (to be eliminated)
    MAX_BACKUPS_ON_SAVE  = 10  # Maximum number of backups to keep on save

    # @formatter:on
    #--------------------------------------------------------------------------------------------

    def __init__(self, path: Path, name: str = None, readOnly: bool = False, create: bool = False):
        """Initialise the XmlLoader instance
        :param path: path to the V3/V2 directory; must exist or allow creation
        :param name: optional name of the project, extracted from path's basename if None
        :param readOnly: flag denoting read-only status
        :param create: flag to indicate creation if path does not exist; implies readOnly=False
        :raises FileNotFoundError
        """

        super().__init__(root=self, readOnly=readOnly)

        # self.logger = getLogger()
        # self.readOnly = readOnly

        if isV2project(path):
            self.isV2 = True
            self.setReadOnly(True)

        self.path = aPath(path)

        if not self.path.isValidCcpn(suffixes=['', '.xml', '.ccpn']):
            raise RuntimeWarning(f'Path contains invalid characters.\n{self.path._validCharactersMessage()}')

        if not self.path.exists():
            if create:
                self.path.mkdir(parents=True, exist_ok=False)
            else:
                raise FileNotFoundError(f'Path "{self.path}" does not exist')

        if name is None:
            self._setNameFromPath()
        else:
            if (_name := checkProjectName(name, correctName=True)) != name:
                raise ValueError(f'Invalid name "{name}" (invalid characters or too long)')
            self.name = _name

        # a dict of (_id, object pair)
        self._lookupDict = {}
        self._id = ('root', None, None)
        self.addToLookup()

    def _setNameFromPath(self):
        """Set name from self.path
        """
        if self.path is None:
            raise RuntimeError('undefined path')
        _name = str(self.path.basename)
        if (_newName := checkProjectName(_name)) != _name:
            self.logger.warning(f'Changed project name to "{_newName}"')
        self.name = _newName

    #--------------------------------------------------------------------------------------------

    @property
    def readOnly(self):
        """Return the read-only state
        """
        return self._readOnly

    def setReadOnly(self, value):
        """Set the read-only state for all loaded xml objects
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setReadOnly must be a bool')

        super()._setReadOnly(value)
        for rep in self.repositories:
            rep._setReadOnly(value)

    @property
    def _readOnlyState(self) -> str:
        """Return a quick reference read-only state of the object and its XML children
        """
        return super()._readOnlyState + ''.join([obj._readOnlyState for obj in self.repositories])

    @property
    def v3Path(self) -> Path:
        """returns the path to the CcpNmr repository as Path object
        Takes account of the optional V2-status
        """
        if self.path is None:
            raise RuntimeError('XmlLoader: undefined path')
        if self.isV2:
            return self.path
        else:
            return self.path / CCPN_API_DIRECTORY

    @property
    def v3MemopsPath(self) -> Path:
        """returns the path to the memops directory as Path object
        """
        return self.v3Path / MEMOPS

    @property
    def v3ImplementationPath(self) -> Path:
        """returns the path to the implementation directory as Path object
        """
        return self.v3MemopsPath / IMPLEMENTATION

    @property
    def backupsPath(self) -> Path:
        """returns the path to the backup directory as Path object
        """
        return self.path / CCPN_BACKUPS_DIRECTORY

    @property
    def xmlProjectFile(self) -> Path:
        """:return the api memops project xml file as Path object
        """
        return self.v3ImplementationPath / (self.name + XML_SUFFIX)

    @property
    def apiName(self):
        """:return name of the project as extracted from self.memopsRoot
        """
        if self.memopsRoot is None:
            raise RuntimeError('undefined memopsRoot project root')
        return getattr(self.memopsRoot, 'name')

    def getTopObjects(self) -> list:
        """:return a list with the TopObject instances
        """
        result = []
        for repo in self.repositories:
            result.extend(repo.getTopObjects())
        return result

    # @property
    # def apiNmrDataStores(self) -> list:
    #     """The data store of NMR spectral data?"""
    #     return [d for ds in self.memopsRoot.dataLocationStores for d in ds.dataStores]
    #
    # @property
    # def apiNmrDataStoreUrls(self) -> list:
    #     """The url's of the data store of NMR spectral data"""
    #     return [d.dataUrl.url for d in self.apiNmrDataStores]

    # @property
    # def apiDataLocationPaths(self) -> dict:
    #     """Return a dict with (data-location, path) key,value pairs"""
    #     return dict([
    #         (loc, v.url.path) for loc,v in self.apiDataLocationUrls.items()
    #     ])

    @property
    def projectNeedsUpdate(self):
        """Indicates if V3 upgrade needs calling"""
        return self.memopsRoot._upgradedFromV2

    def _defineRepositories(self):
        """Define the Repository instances
        """
        self.repositories = []
        _repo = Repository(xmlLoader=self,
                           name=USERDATA,
                           path=self.v3Path,
                           # USERDATA: no 'ccpnv3' as this gets added deep in the bowels of the api code
                           useParent=not self.isV2,
                           createPath=True,
                           readOnly=self.readOnly
                           )
        self.repositories.append(_repo)

        _repo = Repository(xmlLoader=self,
                           name=REFDATA,
                           path=ccpnmodelDataPythonPath / CCPN_API_DIRECTORY,
                           # REFDATA: no 'ccpnv3' as this gets added deep in the bowels of the api code
                           useParent=True,
                           createPath=False,
                           readOnly=self.readOnly
                           )
        self.repositories.append(_repo)

        # These apiRepositories have been deprecated
        # _repo = Repository(name=GENERALDATA,
        #                    path=userCcpnDataPath,
        #                    useParent=False,
        #                    xmlLoader=self)
        # self.repositories.append(_repo)
        #
        # _repo = Repository(name=self.BACKUPDATA,
        #                    path=self.path.parent / (self.path.stem + CCPN_BACKUP_SUFFIX + CCPN_DIRECTORY_SUFFIX),
        #                    useParent=False,
        #                    xmlLoader=self)
        # self.repositories.append(_repo)

    @property
    def userData(self):
        """:return The userData Repository Instance (if defined), else None
        """
        return self.lookup((USERDATA, None, None))

    @property
    def refData(self):
        """:return The refData Repository Instance (if defined), else None
        """
        return self.lookup((REFDATA, None, None))

    #--------------------------------------------------------------------------------------------
    # New
    #--------------------------------------------------------------------------------------------

    # @debug1Enter()
    def newProject(self, overwrite=False):
        """Creates new project;
        :return a (api) NmrProject instance
        :raises FileExistsError or RuntimeError
        """
        if self.readOnly:
            raise RuntimeError(f'Project "{self.name}" is read-only')

        if self.path.exists():
            if not overwrite:
                raise FileExistsError(f'newProject: path "{self.path}" already exists')
            else:
                self.path.removeDir()

        self.path.mkdir(parents=True, exist_ok=False)

        self.isV2 = False

        self.memopsRoot = Implementation.MemopsRoot(name=self.name)
        if self.memopsRoot is None:
            raise RuntimeError('No valid memopsRoot instance could be created')
        setattr(self.memopsRoot, XML_LOADER_ATTR, self)  # back linkage

        self.memopsRoot._logger = getLogger()  # memopsRoot needs a logger

        # define the Repositories instances, and update the paths
        self._defineRepositories()
        self._updateApiRepositoryPaths()

        # Create apiNmrProject and other relevant user topObjects
        with self.blockReading():
            self.apiNmrProject = self.memopsRoot.newNmrProject(name=self.name)  # creates the Nmr repository
            self._initApiData()

            app = getApplication()
            if not app or app.hasGui:
                # And the Graphics data
                self._initApiGraphicsData()

        # associate the topObjects with their repository / package
        self._updateTopObjects()

        self.setUnmodified()

        self._debugInfo('After newProject:')
        return self.apiNmrProject

    @classmethod
    def newFromLoader(cls, xmlLoader, path=None, create=False) -> XmlLoader:
        """Create a new instance using loader; set path, memopsRoot and apiNmrProject
        :return An XmlLoader instance
        """
        if not isinstance(xmlLoader, XmlLoader):
            raise ValueError(f'Expected XmlLoader instance, got {xmlLoader}')

        if path is None:
            path = xmlLoader.path

        result = cls(path=path, create=create)

        result.memopsRoot = xmlLoader.memopsRoot
        setattr(result.memopsRoot, XML_LOADER_ATTR, result)

        result._setFromMemops(xmlLoader.memopsRoot)
        result.apiUserPath = xmlLoader.apiUserPath
        result.pathHasChanged = (result.path != result.apiUserPath)
        result.nameHasChanged = (result.name != result.apiName)

        return result

    def _setFromMemops(self, memopsRoot):
        """Set memopsRoot and apiNmrProject(and memopsRoot) data
        """
        # can't do : result.apiNmrProject = list(memopsRoot.nmrProjects)[0]
        # as this triggers another call to memopsRoot.refreshTopObjects()
        nmrProjects = list(forceGetattr(memopsRoot, 'nmrProjects').values())
        self.apiNmrProject = nmrProjects[0]

        self._defineRepositories()
        self._updateApiRepositoryPaths()
        self._updateTopObjects()

    @classmethod
    def newFromMemops(cls, memopsRoot):
        """Create a new instance using memopsRoot; set path, memopsRoot and apiNmrProject
        :return An XmlLoader instance
        """
        userData = memopsRoot.findFirstRepository(name=USERDATA)
        result = cls(path=userData.url.path)

        result.memopsRoot = memopsRoot
        setattr(memopsRoot, XML_LOADER_ATTR, result)

        result._setFromMemops(memopsRoot)

        return result

    @classmethod
    def newFromProject(cls, project):
        """Create a new instance and set path, memopsRoot and apiNmrProject 
        from project;
        :return An XmlLoader instance
        """
        result = cls(path=project.path)
        result.isV2 = False
        result._setFromProject(project)
        return result

    def _setFromProject(self, project):
        """Set the XmlLoader memopsRoot and apiNmrProject from
        the Project instance.
        :return An XmlLoader instance
        """
        self.apiNmrProject = project._wrappedData
        self.memopsRoot = self.apiNmrProject.root
        setattr(self.memopsRoot, XML_LOADER_ATTR, self)
        self._defineRepositories()
        self._updateApiRepositoryPaths()
        self._updateTopObjects()

    #--------------------------------------------------------------------------------------------
    # Loading
    #--------------------------------------------------------------------------------------------

    # @debug1Enter()
    def loadProject(self) -> NmrProject:
        """Loads ccpn project as defined by self.path;
        :return api NmrProject instance
        :raises FileNotFoundError and RuntimeError
        """

        if not self.path.exists():
            raise FileNotFoundError(f'path "{self.path}" does not exist')

        if not self.path.is_dir():
            raise FileNotFoundError(f'path "{self.path}" is not a directory')

        self.isV2 = isV2project(self.path)

        # load memops; sets self.memopsRoot
        _projectXml = self._getXmlProjectFile()
        try:
            self._loadMemopsFromXml(_projectXml, partialLoad=False)

        except Exception as es:
            if not self.isV2:
                raise RuntimeError(f'XmlLoader.loadProject: {es}') from es

            self.logger.debug(f'XmlLoader.loadProject: loading "{_projectXml}" '
                              f'failed on first try; retrying patial load')
            self._loadMemopsFromXml(_projectXml, partialLoad=True)

        if self.memopsRoot is None:
            raise RuntimeError(f'Failed loading project from "{_projectXml}"')

        setattr(self.memopsRoot, XML_LOADER_ATTR, self)  # back linkage

        # call to sortedNmrProjects will also load the topObjects via
        # memopsRoot.refreshTopObjects
        nmrProjects = self.memopsRoot.sortedNmrProjects()
        if nmrProjects is None or len(nmrProjects) == 0:
            raise RuntimeError(
                    f'No valid NMR project data could be loaded from "{self.path}"'
                    )
        elif len(nmrProjects) > 1:
            self.logger.warning(
                    f'Multiple NMR projects defined by "{self.path}": loading only first one.'
                    )
        self.apiNmrProject = nmrProjects[0]

        # We appear to have to do this often, as 'stray' topObjects appear
        self._updateTopObjects()
        # self.userData.load(reload=False)  # load all remaining userdata

        if self.isV2:
            # Following previous code (Api.py:460): Special hack for moving data
            # of renamed packages on upgrade
            for newName, oldName in self.memopsRoot._movedPackageNames.items():
                if (pkg := self.lookup((USERDATA, oldName))) is not None:
                    pkg._renamePackage(newName)
            with _apiBlocking():
                # upgrade api data
                correctFinalResult(self.memopsRoot)

        # init the V3 project data
        self._initApiData()

        app = getApplication()
        if not app or app.hasGui:
            if self.isV2:
                with _apiBlocking():
                    # init the Graphics data - no feedback to v3-project
                    self._initApiGraphicsData()
            else:
                # init the Graphics data
                self._initApiGraphicsData()

        self._updateTopObjects()
        self.setUnmodified()
        self._debugInfo('After loadProject:')
        return self.apiNmrProject

    # @debug2Leave()
    def _getXmlProjectFile(self) -> Path:
        """Scan apiImplementationPath for possible memops xml files; 
        :return the likely candidate as a Path instance
        """
        # first check for the 'proper' xmlProjectFile
        # GWV: would love this to be a fixed path, e.g. project.xml,
        # but downstream (V2) code checks for match between name attribute
        # in this xml file and a passed-in argument to the call, which can
        # currently only be derived from the stem of the xml path.
        if self.xmlProjectFile.exists():
            return self.xmlProjectFile.resolve()

        # It did not exist; maybe project was renamed. Try to find another candidate
        projectFiles = list(self.v3ImplementationPath.glob(f'*{XML_SUFFIX}'))
        if len(projectFiles) > 0:
            return aPath(projectFiles[0]).resolve()

        raise FileNotFoundError(f'No valid xml-file in "{self.v3ImplementationPath}"')

    # @debug3Enter()
    def _loadMemopsFromXml(self, xmlProjectFile=None, partialLoad=False):
        """Loads and returns MemopsRoot instance from xmlProjectFile
        Adapted from XmlIO.loadProjectFile
        :raises FileNotFound or RuntimeError
        """
        if xmlProjectFile is None:
            xmlProjectFile = self._getXmlProjectFile()

        if not xmlProjectFile.exists():
            raise FileNotFoundError(f'Invalid xmlProjectFile "{xmlProjectFile}"')

        # the memops name might differ from self.name, as the project
        # might have moved/renamed. Hence, derive it from the xml-file
        # as the name argument is required to match!! (WHY???)
        _name = xmlProjectFile.basename
        with xmlProjectFile.open('r') as fp:
            self.memopsRoot = loadFromStream(stream=fp, topObjId=_name, partialLoad=partialLoad)

        if self.memopsRoot is None:
            raise RuntimeError(f'Loading memops from "{xmlProjectFile}" failed')

        self.memopsXmlPath = xmlProjectFile
        self.memopsRoot._logger = getLogger()  # memopsRoot needs a logger

        # code adapted from XmlIO.loadProjectFile; not sure what it is doing.
        # GWV: the only way to get a hold and modify? (forceGetattr() returns a tuple)
        activeRepositories = list(forceGetattr(self.memopsRoot, ACTIVE_REPOSITORIES_ATTR))
        if not activeRepositories:  # len is zero
            _repo = self.memopsRoot.findFirstRepository(name=USERDATA)
            forceSetattr(self.memopsRoot, ACTIVE_REPOSITORIES_ATTR, [_repo])

        # define the Repositories instances
        self._defineRepositories()

        self.apiUserPath = self.userData.apiRepository.url.path
        self.pathHasChanged = (self.apiUserPath != self.path)
        self.nameHasChanged = (self.apiName != self.name)

        # update various things
        self._updateApiRepositoryPaths()

        if not self.readOnly:
            if self.nameHasChanged:
                try:
                    # the only one to rename should be the primary project xml
                    # xmlProjectFile.removeFile()
                    self._rename(self.name)  # Check below if we save
                except (PermissionError, FileNotFoundError):
                    self.logger.info('Folder may be read-only')

            # if (self.pathHasChanged or self.nameHasChanged):
            #     try:
            #         print(f'{self.pathHasChanged}   {self.path}    {self.apiUserPath}   {self.userData.apiRepository.url.path}')
            #         self._saveMemopsToXml()
            #     except (PermissionError, FileNotFoundError):
            #         self.logger.warning('Folder may be read-only')

        self._debugInfo('After loading memopsRoot:')

    #--------------------------------------------------------------------------------------------
    # Saving
    #--------------------------------------------------------------------------------------------

    def saveUserData(self, keepFallBack: bool = True, updateIsModified: bool = True, autoBackup: bool = False):
        """Save userData topObjects to Xml.
        :param keepFallBack: retain current ccpnv3 directory in backups
        :param updateIsModified: if False, the isModified flag of the apiTopObjects are retained 'as-is'
                                 and not set to False. This can be used e.g. when creating backups,
                                 which should not change the isModified status.
        :raises RuntimeError on error
        """
        # NOTE:ED - quick hack for backup
        if autoBackup:
            self.backupUserData(updateIsModified=False)
            return

        if self.readOnly:
            raise RuntimeError(f'Project "{self.name}" is read-only')
        if self.writeBlockingLevel:
            getLogger().debug('blocking save of .xml files')
            return

        # Assure that all apiTopObjects are accounted for; some may have been created
        self._updateTopObjects()

        topObjects = self.userData.getTopObjects()
        if len(topObjects) == 0:
            raise RuntimeError('No data to save; this should not happen')

        app = getApplication()
        try:
            # check if we have to keep current ccpnv3 directory before moving it
            if self.v3Path.exists() and keepFallBack:  # and app.preferences.general.backupSaveEnabled:

                self.backupsPath.mkdir(exist_ok=True, parents=False)

                # check existing save/auto-backups
                _existing = [_p for _p in self.backupsPath.listdir(suffix=BACKUP_SUFFIX)
                             if _p.basename.startswith(CCPN_API_DIRECTORY)]
                if len(_existing) >= app.preferences.general.backupSaveCount:
                    # only remove the oldest backup, fileName contains date
                    #   if the count has been reduced, there may be more many backup here,
                    #   but we don't want to delete all the extras, only the oldest; they may still be important.
                    _existing.sort()
                    _p = _existing.pop(0)
                    _p.removeDir()

                # create the new backup by moving current v3Path
                bPath = self.backupsPath / (CCPN_API_DIRECTORY + BACKUP_SUFFIX)
                bPath = bPath.addTimeStamp()
                self.v3Path.rename(bPath)

            # NOTE:ED 2024-09-23 There is currently an issue if backupSaveEnabled is False
            #   All .xml files are written to the existing folder, old files are not deleted.
            #   But deleting, e.g., structureData requires the deletion of a .xml file in the NMRConstraint folder
            #   Currently writing to the same folder does not delete the old files which are then loaded when the
            #   project is loaded an reappear as the original objects.
            #   So, must always save one backup until issue is resolved :|
            #   Possible solutions - keep tally of old files and new files, and rename old files as .bak
            #           or just rename everything to .bak before saving?
            #   can-of-worms as any errors could result in renaming too many files
            #   Loader checks whether .xml on load belong to the current project state...
            #   keepFallBack=False will have the same issue

        except (PermissionError, FileNotFoundError):
            getLogger().debug('Saving user-data: folder may be read-only')

        else:
            # Force rename to assure correctness
            self._rename(self.name)
            # save memops file in v3Path
            self._saveMemopsToXml(updateIsModified=updateIsModified)

            # save all topObject to xml files in v3Path
            for topObject in topObjects:
                topObject.save(updateIsModified=updateIsModified)

    def _saveMemopsToXml(self, updateIsModified=True):
        """Saves memopsRoot to self.xmlProjectFile;
        :param updateIsModified: flag to update isModified status
        """
        # shouldn't need all these error-checks, just being careful
        if self.readOnly:
            getLogger().debug(f'Project {self.name!r} is read-only')
            return

        if self.writeBlockingLevel:
            getLogger().debug(f'blocking save: {self.xmlProjectFile}')
            return

        _xmlFile = self.xmlProjectFile
        try:
            _xmlFile.parent.mkdir(parents=True, exist_ok=True)
            with _xmlFile.open('w') as fp:
                saveToStream(stream=fp, apiTopObject=self.memopsRoot)

            if updateIsModified:
                # make sure that isModified is not updated if the file is not saved
                forceSetattr(self.memopsRoot, 'isModified', False)

        except (PermissionError, FileNotFoundError):
            getLogger().info('Saving Memops: folder may be read-only')

        self.memopsXmlPath = _xmlFile

    def backupUserData(self, updateIsModified: bool = False):
        """Save userData topObjects to Xml.
        :param updateIsModified: if False, the isModified flag of the apiTopObjects are retained 'as-is'
                                 and not set to False. This can be used e.g. when creating backups,
                                 which should not change the isModified status.
        :raises RuntimeError on error
        """
        if self.readOnly:
            raise RuntimeError(f'Project "{self.name}" is read-only')

        if self.writeBlockingLevel:
            getLogger().debug('blocking save of .xml files')
            return

        # Assure that all apiTopObjects are accounted for; some may have been created
        self._updateTopObjects()

        topObjects = self.userData.getTopObjects()
        if len(topObjects) == 0:
            raise RuntimeError('No data to save; this should not happen')

        app = getApplication()
        try:
            self.backupsPath.mkdir(exist_ok=True, parents=False)

            # check existing save/auto-backups
            _existing = [_p for _p in self.backupsPath.listdir(suffix=AUTOBACKUP_SUFFIX)
                         if _p.basename.startswith(CCPN_API_DIRECTORY)]
            if len(_existing) >= app.preferences.general.autoBackupCount:
                # only remove the oldest backup, fileName contains date
                #   if the count has been reduced, there may be more many backup here,
                #   but we don't want to delete all the extras, only the oldest; they may still be important.
                _existing.sort()
                _p = _existing.pop(0)
                _p.removeDir()

            # create the new backup by moving current v3Path
            bPath = self.backupsPath / (CCPN_API_DIRECTORY + AUTOBACKUP_SUFFIX)
            bPath = bPath.addTimeStamp()
            bPath.mkdir(exist_ok=True, parents=False)

        except (PermissionError, FileNotFoundError):
            getLogger().debug('Backing up user-data: folder may be read-only')

        else:
            # Force rename to assure correctness
            self._rename(self.name)
            # save memops file in v3Path
            self._backupMemopsToXml(updateIsModified=updateIsModified, autoBackupPath=bPath)

            # save all topObject to xml files in v3Path
            for topObject in topObjects:
                topObject.saveBackup(updateIsModified=updateIsModified, autoBackupPath=bPath)

    def _backupMemopsToXml(self, updateIsModified=True, autoBackupPath=None):
        """Saves memopsRoot to back-up folder;
        :param updateIsModified: flag to update isModified status
        """
        # shouldn't need all these error-checks, just being careful
        if self.readOnly:
            getLogger().debug(f'Project {self.name!r} is read-only')
            return

        if self.writeBlockingLevel:
            getLogger().debug(f'blocking save: {self.xmlProjectFile}')
            return

        if not autoBackupPath:
            raise ValueError('Auto-backup path is not defined')

        _xmlFile = autoBackupPath / MEMOPS / IMPLEMENTATION / (self.name + XML_SUFFIX)
        try:
            _xmlFile.parent.mkdir(parents=True, exist_ok=True)
            with _xmlFile.open('w') as fp:
                saveToStream(stream=fp, apiTopObject=self.memopsRoot)

            if updateIsModified:
                # make sure that isModified is not updated if the file is not saved
                forceSetattr(self.memopsRoot, 'isModified', False)

        except (PermissionError, FileNotFoundError):
            self.logger.debug('Backing up Memops: folder may be read-only')

    #--------------------------------------------------------------------------------------------

    def _updateApiRepositoryPaths(self):
        """Update the repository paths
        """
        for repo in self.repositories:
            repo._updateApiRepositoryPath()

    def _updateTopObjects(self):
        """Update using the apiTopObjects in memopsRoot;
        allocating each one to a repository/package;
        """
        count = 0
        for apiTopObj in self.memopsRoot.topObjects:

            _guid = apiTopObj.guid
            _pkgName = apiTopObj.packageName

            if (_topObj := self.lookup((None, _pkgName, _guid))) is None:
                # This happens, e.g. for newProjects;
                # see if we can create the required objects

                _repoName, _pkgName, _guid = _getIdFromTopObject(apiTopObj)
                if (_repo := self.lookup((_repoName, None, None))) is None:
                    # This is an unrecoverable error
                    raise RuntimeError(f'TopObject {apiTopObj} does not have a repository defined')

                if (_pkg := self.lookup((_repoName, _pkgName, None))) is None:
                    # No package, can create one
                    getLogger().debug(f'Creating Package "{_pkgName}" for apiTopObject {apiTopObj}: ')
                    _pkg = _repo._addPackage(name=_pkgName, createPath=True)

                _xmlPath = _getXmlPathFromApiTopObject(_pkg, apiTopObj)
                _topObj = _pkg._addTopObject(path=_xmlPath)
                _topObj.apiTopObject = apiTopObj
                _topObj.save()

            _topObj.apiTopObject = apiTopObj
            count += 1

        getLogger().debug(f'Updated {count} TopObjects')

    # @debug3Enter()
    def _rename(self, newName: str):
        """Update self.name and memopsRoot name
        :param newName: the new name of the project
        """
        # setattr(self.memopsRoot, 'name', self.name) is not allowed as the name attribute is frozen
        # Hence: forceSetattr
        forceSetattr(self.memopsRoot, 'name', newName)
        self.name = newName

    # @debug3Enter()
    def _initApiData(self):
        if self.apiNmrProject is None:
            raise RuntimeError('undefined Api data repository')
        #GWV: This seems to restore all the data stores
        self.apiNmrProject.initialiseData()

    def _initApiGraphicsData(self):
        if self.apiNmrProject is None:
            raise RuntimeError('undefined Api data repository')
        # GWV: This seems to restore all the data stores for the graphics elements
        self.apiNmrProject.initialiseGraphicsData()

    def setUnmodified(self):
        """Set all topObject and self to unmodified status"""
        # set memopsRoot and all topObjects as not-modified
        for topObject in [self.memopsRoot] + list(self.memopsRoot.topObjects):
            forceSetattr(topObject, 'isModified', False)

        getLogger().debug('Setting loader to unModified')

    @contextmanager
    def blockReading(self):
        """context manager for blocking any reading of xml-files
        """
        self.readingBlockingLevel += 1
        try:
            yield

        finally:
            self.readingBlockingLevel -= 1

    @contextmanager
    def blockWriting(self):
        """context manager for blocking any reading of xml-files
        """
        self.writeBlockingLevel += 1
        try:
            yield

        finally:
            self.writeBlockingLevel -= 1

    def _debugInfo(self, topLine=None):
        """bit of debugging info"""
        if topLine is not None:
            self.logger.debug2(f'>>> {topLine}')
        self.logger.debug2(f'... xmlLoader      : {self}')
        self.logger.debug2(f'... memopsRoot      : {self.memopsRoot}')
        self.logger.debug2(f'... repositories: {self.repositories}')

    def __str__(self):
        version = 'V2' if self.isV2 else 'V3'
        return f'<XmlLoader: "{self.name}" ({version})>'

    __repr__ = __str__


#end class


def saveToStream(stream, apiTopObject, mapping=None, comment=None, simplified=True, compact=True, expanded=False):
    """ wrapper function, to handle garbage collection for Xml export.
    Copied from XmlIO.py
    :raise RuntimeError on error
    """
    import gc
    from ccpnmodel.ccpncore.xml.memops import Implementation as XmlImp

    # garbage collection suspended in original code;
    _gcEnabled = gc.isenabled()
    if SILENCE_GARBAGE_COLLECTION and _gcEnabled:
        gc.disable()

    try:
        XmlImp.saveToStream(stream, apiTopObject,
                            mapping=mapping, comment=comment,
                            simplified=simplified, compact=compact,
                            expanded=expanded)

    except Exception as es:
        getLogger().error(f'While saving xml file: {es}')
        raise RuntimeError(es) from es

    finally:
        if SILENCE_GARBAGE_COLLECTION and _gcEnabled:
            gc.enable()


# @debug3Enter()
def loadFromStream(stream, topObjId=None, topObject=None, partialLoad=False):
    """ Wrapper function, to handle garbage collection for Xml import.
    Adapted from XmlIO.py loadFromStream
    :raise RuntimeError on error
    """
    import gc
    from ccpnmodel.ccpncore.xml.memops import Implementation as XmlImp

    # garbage collection suspended in original code;
    _gcEnabled = gc.isenabled()
    if SILENCE_GARBAGE_COLLECTION and _gcEnabled:
        gc.disable()

    try:
        getLogger().debug2(f'{consoleStyle.fg.darkblue}Loading stream {topObject}{consoleStyle.reset}')
        result = XmlImp.loadFromStream(stream,
                                       topObjId=topObjId,
                                       topObject=topObject,
                                       partialLoad=partialLoad)
    except Exception as es:
        getLogger().error(f'While loading xml file: {es}')
        raise RuntimeError(es) from es

    finally:
        if SILENCE_GARBAGE_COLLECTION and _gcEnabled:
            gc.enable()

    return result


def _getIdFromTopObject(topObj) -> tuple:
    """:return from the topObject api-settings an id tuple, i.e.
    (repoName, packageName, guid)
    """

    activeRepositories = list(forceGetattr(topObj, ACTIVE_REPOSITORIES_ATTR))

    if not activeRepositories:
        # This sometimes happens; the model does not always sets a
        # a repository; eg. when creating a new project
        # Allocate these to the userData
        memopsRoot = topObj.root
        ff = memopsRoot.findFirstPackageLocator
        repositories = list((ff(targetName=USERDATA) or ff(targetName='any')).repositories)
        activeRepositories.extend(repositories)
        forceSetattr(topObj, ACTIVE_REPOSITORIES_ATTR, activeRepositories)
        # dataDict[ACTIVE_REPOSITORIES_ATTR] = activeRepositories

    if not activeRepositories:
        # getLogger().debug(f'No repository found for "{packageName}"')
        raise RuntimeError(f'No repository found for {topObj}')

    elif len(activeRepositories) > 1:
        getLogger().debug(f'Several repositories found for {topObj}; using first one {repositories[0]}')
    apiRepo = activeRepositories[0]

    return (apiRepo.name, topObj.packageName, topObj.guid)


def _getXmlPathFromApiTopObject(package, apiTopObject) -> Path:
    """:return xml-path of api topObject as a Path instance
    :param package: Package instance
    :param apiTopObject: the api TopObject instance
    :return the xml path
    """
    # the xml-path is constructed from the
    # - repository path and the packageName (encoded as the sub-directories)
    #   i.e., the package path
    # - and keys and guid of the topObject
    # However, gui.Window has "<ccp.nmr.Nmr.NmrProject ['tstar2assigned']>" as key, which
    # needs regularlising to '_ccp_nmr_Nmr_NmrProject___tstar2assigned___' using a regular
    # expression
    # (GWV: why is the storage so complicated, dependent on file-name syntax and inconsistent??)

    if apiTopObject is None:
        raise RuntimeError(f'Undefined apiTopObject')

    _keys = [re.sub('[\[\]<>+-. \'\"]', '_', str(key)) for key in apiTopObject.getFullKey()]
    _keyStr = KEY_SEPARATOR.join(_keys)

    _xmlPath = package.path / (_keyStr + KEY_SEPARATOR + apiTopObject.guid + XML_SUFFIX)

    return _xmlPath


def forceSetattr(obj, attributeName, value):
    """Force setting of attributeName
    """
    obj.__dict__[attributeName] = value


def forceGetattr(obj, attributeName):
    """Force getting of attributeName
    """
    if not attributeName in obj.__dict__.keys():
        raise AttributeError('Object "%s" does not have attribute "%s"' % (obj, attributeName))

    value = obj.__dict__[attributeName]
    return value


#=========================================================================================
# Hot-fixing:
#   MemopsRoot.refreshTopObjects
#=========================================================================================

def _refreshTopObjects(memopsRoot, packageName):
    """Load the xml-files of packageName;
    Hot-fixed method
    """
    if not isinstance(memopsRoot, Implementation.MemopsRoot):
        raise ValueError(f'invalid memopsRoot: {memopsRoot}')

    if packageName is None or packageName == MEMOPS_PACKAGE:
        raise ValueError(f'Invalid packageName "{packageName}"')

    # # fix absence of active repositories; not sure if/why this happens
    # activeRepositories = memopsRoot.__dict__[ACTIVE_REPOSITORIES_ATTR]
    # if not activeRepositories:  # len is zero
    #     _repo = memopsRoot.findFirstRepository(name=USERDATA)
    #     memopsRoot.__dict__[ACTIVE_REPOSITORIES_ATTR] = [_repo]

    # Find our xml-loader; if not, just skip as this likely is the result of
    # initialising the MemopsRoot instance; we'll return later
    if not hasattr(memopsRoot, XML_LOADER_ATTR):
        # xmlLoader = XmlLoader.newFromMemops(memopsRoot)
        # setattr(memopsRoot, XML_LOADER_ATTR, xmlLoader)
        # raise RuntimeError(f'MemopsRoot.refreshTopObjects: no XmlLoader instance')
        getLogger().debug(f'MemopsRoot.refreshTopObjects: no xmlLoader (yet), skipping loading {packageName}')
        return

    # getLogger().debug(f'MemopsRoot.refreshTopObjects: try loading {packageName}')

    xmlLoader = getattr(memopsRoot, XML_LOADER_ATTR)  # use back linkage

    if xmlLoader.readingBlockingLevel:
        return

    # We have to find the package: that is a problem as a package has no info on its
    # parent repository, and (potentially?) package's by the same name can live in two
    # repositories!
    # For now, going to assume that there is only one location, checking first the
    # reference data, next the userData.

    if (pkg := xmlLoader.lookup((REFDATA, packageName, None))) is not None:
        pass

    elif (pkg := xmlLoader.lookup((USERDATA, packageName, None))) is not None:
        pass

    else:
        getLogger().debug2(f'No Package instance found for "{packageName}"; skipping')
        return

    # print(f'>DEBUG refreshTopObjects> {pkg}: loaded:{pkg.isLoaded}')
    if not pkg.isLoaded:
        pkg.load(reload=False)

    return


# Hotfix
Implementation.MemopsRoot.refreshTopObjects = _refreshTopObjects


# topObject.load (Implementation:4983) and topObject.loadFrom (implementation:4999)
def _load(apiTopObject):
    """
    Load apiTopObject
    """
    if not isinstance(apiTopObject, Implementation.TopObject):
        raise ValueError(f'Invalid apiTopObject {apiTopObject}')

    # Find our xml-loader; if not, for just return as this likely results from
    # a 'new' instance
    memopsRoot = apiTopObject.root
    if not hasattr(memopsRoot, XML_LOADER_ATTR):
        # xmlLoader = XmlLoader.newFromMemops(memopsRoot)
        # setattr(memopsRoot, XML_LOADER_ATTR, xmlLoader)
        # raise RuntimeError(f'TopObject.loadFrom: no XmlLoader instancee for memopsRoot')
        return

    xmlLoader = getattr(memopsRoot, XML_LOADER_ATTR)  # use back linkage

    if xmlLoader.readingBlockingLevel:
        return

    # _repoName, _packageName, _guid = _getIdFromTopObject(apiTopObject)
    _id = (None, apiTopObject.packageName, apiTopObject.guid)

    if (topObj := xmlLoader.lookup(_id)) is None:
        # optionally we may have to create the TopObject instance;
        # for now consider it an error
        raise RuntimeError(f'Unable to load {apiTopObject}')

    topObj.apiTopObject = apiTopObject
    topObj.load()

# Hotfix; don't work as code is not using regular inheritance, but rather hard inserted
# Implementation.TopObject.load = _load
# Implementation.TopObject.loadFrom = _loadFrom
