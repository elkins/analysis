"""
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
__dateModified__ = "$dateModified: 2024-09-20 19:28:49 +0100 (Fri, September 20, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import datetime
from typing import Optional

from ccpnmodel.ccpncore.api.ccp.nmr.NmrConstraint import NmrConstraintStore as ApiNmrConstraintStore
from ccpnmodel.ccpncore.api.ccp.nmr.NmrConstraint import FixedResonance as ApiFixedResonance
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Project import Project
from ccpn.core.lib import Pid
from ccpn.core.lib.ContextManagers import newObject, renameObject, ccpNmrV3CoreSetter
from ccpn.util.decorators import logCommand
from ccpn.util.isotopes import name2IsotopeCode
from ccpn.util.Logging import getLogger


class StructureData(AbstractWrapperObject):
    """Data set. Used to store the input to (or output from) a calculation, including data
    selection and parameters, to group Restraints that are used together, to track
    data history and file loads. """

    #: Short class name, for PID.
    shortClassName = 'SD'
    # Attribute it necessary as subclasses must use superclass className
    className = 'StructureData'

    _parentClass = Project

    #: Name of plural link to instances of class
    _pluralLinkName = 'structureData'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiNmrConstraintStore._metaclass.qualifiedName()

    # Internal NameSpace
    _MoleculeFilePath = '_MoleculeFilePath'
    _MOLECULEFILEPATH = 'moleculeFilePath'

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _apiStructureData(self) -> ApiNmrConstraintStore:
        """ CCPN NmrConstraintStore matching StructureData"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - serial number converted to string"""
        #return str(self._wrappedData.serial)
        #return str(self.title)+'_'+str(self.serial)
        return self.name.translate(Pid.remapSeparators)  # Title should not be unique

    @property
    def serial(self) -> int:
        """serial number of StructureData, used in Pid and to identify the StructureData. """
        return self._wrappedData.serial

    @property
    def _parent(self) -> Project:
        """Parent (containing) object."""
        return self._project

    @property
    def title(self) -> str:
        """Title of StructureData.
        """
        getLogger().warning('Deprecated, please use StructureData.name')
        return self.name

    @title.setter
    def title(self, value: str):
        """Set title of the StructureData.
        """
        getLogger().warning('Deprecated, please use StructureData.name')
        self.name = value

    @property
    def name(self) -> str:
        """Name of StructureData.
        """
        # Reading V2 project resulted in name being None; create one on the fly
        if self._wrappedData.name is None:
            # needed to stop recursion of generating unique names
            name = StructureData._uniqueApiName(self.project)
            self._wrappedData.__dict__['name'] = name  # The only way to access this

        return self._wrappedData.name

    @name.setter
    def name(self, value: str):
        self.rename(value)

    @property
    def programName(self) -> str:
        """Name of program performing the calculation
        """
        return self._none2str(self._wrappedData.programName)

    @programName.setter
    def programName(self, value: str):
        self._wrappedData.programName = self._str2none(value)

    @property
    def programVersion(self) -> Optional[str]:
        """Version of program performing the calculation
        """
        return self._none2str(self._wrappedData.programVersion)

    @programVersion.setter
    def programVersion(self, value: str):
        self._wrappedData.programVersion = self._str2none(value)

    @property
    def dataPath(self) -> Optional[str]:
        """File path where structureData is stored"""
        return self._none2str(self._wrappedData.dataPath)

    @dataPath.setter
    def dataPath(self, value: str):
        self._wrappedData.dataPath = self._str2none(value)

    @property
    def creationDate(self) -> Optional[datetime.datetime]:
        """Creation timestamp for StructureData"""
        return self._wrappedData.creationDate

    @creationDate.setter
    def creationDate(self, value: datetime.datetime):
        self._wrappedData.creationDate = self._str2none(value)

    @property
    def uuid(self) -> Optional[str]:
        """Universal identifier for structureData"""
        return self._none2str(self._wrappedData.uuid)

    @uuid.setter
    def uuid(self, value: str):
        self._wrappedData.uuid = self._str2none(value)

    @property
    def moleculeFilePath(self):
        """
        :return: a filePath for corresponding molecule.
        E.g., PDB file path for displaying molecules in a molecular viewer
        """
        path = self._getInternalParameter(self._MOLECULEFILEPATH)

        return path

    @moleculeFilePath.setter
    @ccpNmrV3CoreSetter()
    def moleculeFilePath(self, filePath: str = None):
        """
        :param filePath: a filePath for corresponding molecule
        :return: None
        """
        self._setInternalParameter(self._MOLECULEFILEPATH, filePath)

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def calculationSteps(self) -> list['CalculationStep']:
        """STUB: hot-fixed later
        :return: a list of calculationSteps in the StructureData
        """
        return []

    @property
    def data(self) -> list['Data']:
        """STUB: hot-fixed later
        :return: a list of data in the StructureData
        """
        return []

    @property
    def restraintContributions(self) -> list['RestraintContribution']:
        """STUB: hot-fixed later
        :return: a list of restraintContributions in the StructureData
        """
        return []

    @property
    def restraintTables(self) -> list['RestraintTable']:
        """STUB: hot-fixed later
        :return: a list of restraintTables in the StructureData
        """
        return []

    @property
    def restraints(self) -> list['Restraint']:
        """STUB: hot-fixed later
        :return: a list of restraints in the StructureData
        """
        return []

    @property
    def violationTables(self) -> list['ViolationTable']:
        """STUB: hot-fixed later
        :return: a list of violationTables in the StructureData
        """
        return []

    #=========================================================================================
    # getter STUBS: hot-fixed later
    #=========================================================================================

    def getCalculationStep(self, relativeId: str) -> 'CalculationStep | None':
        """STUB: hot-fixed later
        :return: an instance of CalculationStep, or None
        """
        return None

    def getData(self, relativeId: str) -> 'Data | None':
        """STUB: hot-fixed later
        :return: an instance of Data, or None
        """
        return None

    def getRestraint(self, relativeId: str) -> 'Restraint | None':
        """STUB: hot-fixed later
        :return: an instance of Restraint, or None
        """
        return None

    def getRestraintContribution(self, relativeId: str) -> 'RestraintContribution | None':
        """STUB: hot-fixed later
        :return: an instance of RestraintContribution, or None
        """
        return None

    def getRestraintTable(self, relativeId: str) -> 'RestraintTable | None':
        """STUB: hot-fixed later
        :return: an instance of RestraintTable, or None
        """
        return None

    def getViolationTable(self, relativeId: str) -> 'ViolationTable | None':
        """STUB: hot-fixed later
        :return: an instance of ViolationTable, or None
        """
        return None

    #=========================================================================================
    # Core methods
    #=========================================================================================

    def _fetchFixedResonance(self, assignment: str, checkUniqueness: bool = True) -> ApiFixedResonance:
        """Fetch FixedResonance matching assignment string, creating anew if needed.

        If checkUniqueness is False the uniqueness of FixedResonance assignments will
        not be checked. NB, the odd duplicate should not be a major problem."""
        from ccpn.core.NmrAtom import UnknownIsotopeCode

        apiNmrConstraintStore = self._wrappedData

        tt = [x or None for x in Pid.splitId(assignment)]
        if len(tt) != 4:
            raise ValueError("assignment %s must have four dot-separated fields" % tt)

        dd = {
            'chainCode'   : tt[0],
            'sequenceCode': tt[1],
            'residueType' : tt[2],
            'name'        : tt[3]
            }

        if checkUniqueness:
            result = apiNmrConstraintStore.findFirstFixedResonance(**dd)
        else:
            result = None

        if result is None:
            dd['isotopeCode'] = name2IsotopeCode(tt[3]) or UnknownIsotopeCode
            result = apiNmrConstraintStore.newFixedResonance(**dd)
        #
        return result

    def _getTempItemMap(self) -> dict:
        """Get itemString:FixedResonance map, used as optional input for
        RestraintContribution.addRestraintItem(), as a faster alternative to
        calling _fetchFixedResonance (above). No other uses expected.
        Since FixedResonances are in principle mutable, this map should
        be used for a single series of creation operations (making or loading
        a set of restraint lists) and then discarded."""

        result = {}
        for fx in self._wrappedData.fixedResonances:
            ss = '.'.join(x or '' for x in (fx.chainCode, fx.sequenceCode, fx.residueType, fx.name))
            result[ss] = fx
        #
        return result

    @property
    def inputCalculationSteps(self):
        """STUB: hot-fixed later"""
        return ()

    @property
    def outputCalculationSteps(self):
        """STUB: hot-fixed later"""
        return ()

    @renameObject()
    @logCommand(get='self')
    def rename(self, value: str):
        """Rename StructureData, changing its name and Pid.
        NB, the serial remains immutable.
        """
        return self._rename(value)

    #=========================================================================================
    # Implementation methods
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Project) -> list:
        """get wrappedData for all NmrConstraintStores linked to NmrProject"""
        return parent._wrappedData.sortedNmrConstraintStores()

    def _finaliseAction(self, action: str, **actionKwds):
        """Spawn _finaliseAction notifiers for restraint/violationTables.
        """
        if not super()._finaliseAction(action, **actionKwds):
            return

        if action in {'create', 'delete'}:
            for rt in self.restraintTables:
                rt._finaliseAction(action, **actionKwds)
            for vt in self.violationTables:
                vt._finaliseAction(action, **actionKwds)

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Subclassed to allow for initialisations on restore
        """
        resList = super()._restoreObject(project, apiObj)

        # update the list of substances
        if resList._MoleculeFilePath in resList._ccpnInternalData:
            value = resList._ccpnInternalData.get(resList._MoleculeFilePath)
            if value:
                resList._setInternalParameter(resList._MOLECULEFILEPATH, value)
            del resList._ccpnInternalData[resList._MoleculeFilePath]

    # @classmethod
    # def _restoreObject(cls, project, apiObj):
    #     """Subclassed to allow for initialisations on restore
    #     """
    #     from ccpn.ui.gui.modules.RestraintAnalysisTable import Headers
    #
    #     _headers = [(['restraintpid', 'atoms', 'min', 'max', 'mean', 'std', 'count_0_3', 'count_0_5'],
    #                 Headers),
    #                ]
    #
    #     result = super()._restoreObject(project, apiObj)
    #
    #     for data in result.data:
    #         parameters = data.parameters
    #         modified = False
    #         for k, df in parameters.items():
    #             if isinstance(df, pd.DataFrame):
    #                 headers = list(df.columns)
    #                 for oldHeaders, newHeaders in _headers:
    #                     if headers == oldHeaders:
    #                         df.rename(columns={old: new for old, new in zip(oldHeaders, newHeaders)}, inplace=True)
    #                         modified = True
    #
    #         if modified:
    #             data.updateParameters(parameters)
    #
    #     return result

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    @logCommand(get='self')
    def newRestraintTable(self, restraintType, name: str = None, origin: str = None,
                          comment: str = None, unit: str = None, potentialType: str = 'unknown',
                          tensorMagnitude: float = 0.0, tensorRhombicity: float = 0.0,
                          tensorIsotropicValue: float = 0.0, tensorChainCode: str = None,
                          tensorSequenceCode: str = None, tensorResidueType: str = None,
                          restraintItemLength=None, **kwds):
        """Create new RestraintTable of type restraintType within StructureData.

        See the RestraintTable class for details.

        Optional keyword arguments can be passed in; see RestraintTable._newRestraintTable for details.

        :param restraintType:
        :param name:
        :param origin:
        :param comment:
        :param unit:
        :param potentialType:
        :param tensorMagnitude:
        :param tensorRhombicity:
        :param tensorIsotropicValue:
        :param tensorChainCode:
        :param tensorSequenceCode:
        :param tensorResidueType:
        :param restraintItemLength:
        :return: a new RestraintTable instance.
        """
        from ccpn.core.RestraintTable import _newRestraintTable

        return _newRestraintTable(self, restraintType, name=name, origin=origin,
                                  comment=comment, unit=unit, potentialType=potentialType,
                                  tensorMagnitude=tensorMagnitude, tensorRhombicity=tensorRhombicity,
                                  tensorIsotropicValue=tensorIsotropicValue, tensorChainCode=tensorChainCode,
                                  tensorSequenceCode=tensorSequenceCode, tensorResidueType=tensorResidueType,
                                  restraintItemLength=restraintItemLength, **kwds)

    @logCommand(get='self')
    def newCalculationStep(self, programName: str = None, programVersion: str = None,
                           scriptName: str = None, script: str = None,
                           inputDataUuid: str = None, outputDataUuid: str = None,
                           inputStructureData=None, outputStructureData=None, **kwds):
        """Create new CalculationStep within StructureData.

        See the CalculationStep class for details.

        Optional keyword arguments can be passed in; see CalculationStep._newCalculationStep for details.

        :param programName:
        :param programVersion:
        :param scriptName:
        :param script:
        :param inputDataUuid:
        :param outputDataUuid:
        :param inputStructureData:
        :param outputStructureData:
        :return: a new CalculationStep instance.
        """
        from ccpn.core.CalculationStep import _newCalculationStep

        return _newCalculationStep(self, programName=programName, programVersion=programVersion,
                                   scriptName=scriptName, script=script,
                                   inputDataUuid=inputDataUuid, outputDataUuid=outputDataUuid,
                                   inputStructureData=inputStructureData, outputStructureData=outputStructureData,
                                   **kwds)

    @logCommand(get='self')
    def newData(self, name: str, attachedObjectPid: str = None,
                attachedObject: AbstractWrapperObject = None, **kwds):
        """Create new Data within StructureData.

        See the Data class for details.

        Optional keyword arguments can be passed in; see Data._newData for details.

        :param name:
        :param attachedObjectPid:
        :param attachedObject:
        :return: a new Data instance.
        """
        from ccpn.core.Data import _newData

        return _newData(self, name=name, attachedObjectPid=attachedObjectPid,
                        attachedObject=attachedObject, **kwds)

    @logCommand(get='self')
    def newViolationTable(self, name: str = None, data=None, comment: str = None, **kwds):
        """Create new ViolationTable.

        See the ViolationTable class for details.

        Optional keyword arguments can be passed in; see ViolationTable._newViolationTable for details.

        :param name: new name for the ViolationTable.
        :param data: Pandas dataframe.
        :param comment: optional comment string
        :return: a new ViolationTable instance.
        """
        from ccpn.core.ViolationTable import _newViolationTable

        return _newViolationTable(self, name=name, data=data, comment=comment, **kwds)


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(StructureData)
def _newStructureData(self: Project, name: str = None, title: str = None, programName: str = None,
                      programVersion: str = None, dataPath: str = None, creationDate: datetime.datetime = None,
                      uuid: str = None, moleculeFilePath: str = None,
                      comment: str = None) -> StructureData:
    """Create new StructureData

    See the StructureData class for details.

    :param name:
    :param programName:
    :param programVersion:
    :param dataPath:
    :param creationDate:
    :param uuid:
    :param comment:
    :return: a new StructureData instance.
    """

    if title and name:
        raise TypeError(
                'Cannot create new StructureData with title and name; StructureData.title is deprecated, please use StructureData.name')
    if title:
        getLogger().warning('StructureData.title is deprecated, please use StructureData.name')
        name = title

    name = StructureData._uniqueName(parent=self, name=name)

    nmrProject = self._wrappedData

    if programName is not None and not isinstance(programName, str):
        raise TypeError("programName must be a string")
    if programVersion is not None and not isinstance(programVersion, str):
        raise TypeError("programName must be a string")

    apiNmrConstraintStore = nmrProject.root.newNmrConstraintStore(nmrProject=nmrProject,
                                                                  name=name,
                                                                  programName=programName,
                                                                  programVersion=programVersion,
                                                                  dataPath=dataPath,
                                                                  creationDate=creationDate,
                                                                  uuid=uuid,
                                                                  details=comment)
    result = self._data2Obj.get(apiNmrConstraintStore)

    if result is None:
        raise RuntimeError('Unable to generate new StructureData item')
    if moleculeFilePath:
        result.moleculeFilePath = moleculeFilePath
    return result
