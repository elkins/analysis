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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-10-15 10:35:58 +0100 (Tue, October 15, 2024) $"
__version__ = "$Revision: 3.2.9.alpha $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-05-28 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os

import numpy as np
import pandas as pd
from ccpn.util.Logging import getLogger
from ccpn.util.Path import aPath, joinPath
from ccpn.util.Colour import name2Hex
from itertools import cycle
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking, progressHandler

################################       Excel Headers Warning      ######################################################
"""The excel headers for sample, sampleComponents, substances properties are named as the appear on the wrapper.
Changing these will fail to set the attribute"""

# SHEET NAMES
SUBSTANCE = 'Substance'
SAMPLE = 'Sample'
NOTGIVEN = 'NotGiven'
SERIES = 'Series'

# """REFERENCES PAGE"""
SPECTRUM_GROUP_NAME = 'spectrumGroupName'
EXP_TYPE = 'experimentType'
SPECTRUM_PATH = 'spectrumPath'
SUBSTANCE_NAME = 'substanceName'
# added from beta6
SPECTRUM_NAME = 'spectrumName'
SPECTRUMGROUP = 'SpectrumGroup'

SPECTRUMHEXCOLOUR = 'spectrumHexColour'
SPECTRUMGROUPHEXCOLOUR = 'spectrumGroupHexColour'
POSITIVECONTOURCOLOUR = 'positiveContourColour'
NEGATIVECONTOURCOLOUR = 'negativeContourColour'
POSITIVECONTOURBASE = 'positiveContourBase'
NEGATIVECONTOURBASE = 'negativeContourBase'
INCLUDENEGATIVECONTOURS = 'includeNegativeContours'
### Substance properties: # do not change these names
comment = 'comment'
smiles = 'smiles'
synonyms = 'synonyms'
molecularMass = 'molecularMass'
empiricalFormula = 'empiricalFormula'
atomCount = 'atomCount'
hBondAcceptorCount = 'hBondAcceptorCount'
hBondDonorCount = 'hBondDonorCount'
bondCount = 'bondCount'
ringCount = 'ringCount'
polarSurfaceArea = 'polarSurfaceArea'
logPartitionCoefficient = 'logPartitionCoefficient'
userCode = 'userCode'
sequenceString = 'sequenceString'
casNumber = 'casNumber'

# """SAMPLES PAGE"""
SAMPLE_NAME = 'sampleName'
SAMPLE_NUMBER = 'sampleNumber'
### other sample properties # do not change these names
SAMPLE_COMPONENTS = 'sampleComponents'
pH = 'pH'
ionicStrength = 'ionicStrength'
amount = 'amount'
amountUnit = 'amountUnit'
isHazardous = 'isHazardous'
creationDate = 'creationDate'
batchIdentifier = 'batchIdentifier'
plateIdentifier = 'plateIdentifier'
rowNumber = 'rowNumber'
columnNumber = 'columnNumber'

# shifts
ChemicalShift = 'ChemicalShift'
ChemicalShiftLabel = 'ChemicalShiftLabel'
ChemicalShiftAnnotation = 'ChemicalShiftAnnotation'
ChemicalShiftMerit = 'ChemicalShiftMerit'
ChemicalShiftComment = 'ChemicalShiftComment'
TimeStamp = 'TimeStamp_'
Valid = 'Valid'
Salt = 'Salt'
Other = 'Other'

# Series
SERIES_VALUE = 'series'
SERIES_UNIT = 'seriesUnit'


SAMPLE_PROPERTIES = [comment, pH, ionicStrength, amount, amountUnit, isHazardous, creationDate, batchIdentifier,
                     plateIdentifier, rowNumber, columnNumber]

SUBSTANCE_PROPERTIES = [comment, smiles, synonyms, molecularMass, empiricalFormula, atomCount,
                        hBondAcceptorCount, hBondDonorCount, bondCount, ringCount, polarSurfaceArea,
                        logPartitionCoefficient, userCode, ]

SUBSTANCES_SHEET_COLUMNS = [SUBSTANCE_NAME,
                                        SPECTRUM_PATH,
                                        SPECTRUM_GROUP_NAME,
                                        SPECTRUMHEXCOLOUR,
                                        SPECTRUMGROUPHEXCOLOUR, EXP_TYPE] \
                                       + SUBSTANCE_PROPERTIES

SAMPLE_SHEET_COLUMNS = [SAMPLE_NAME,
                        SPECTRUM_GROUP_NAME,
                        SPECTRUM_PATH,
                        SPECTRUM_NAME,
                        SPECTRUMHEXCOLOUR,
                        SPECTRUMGROUPHEXCOLOUR] \
                       + SAMPLE_PROPERTIES

SERIES_SHEET_COLUMNS = [
                        SPECTRUM_GROUP_NAME,
                        SPECTRUM_PATH,
                        SPECTRUM_NAME,
                        SERIES_VALUE,
                        SERIES_UNIT,
                        SPECTRUMHEXCOLOUR,
                        SPECTRUMGROUPHEXCOLOUR]

TOP_SG_COLOURS = ['red',
                                      'blue',
                                      'purple',
                                      'green',
                                      'gold',
                                      'dimgrey',
                                      'darksalmon',
                                      'orangered'
                                      'firebrick',
                                      'tan',
                                      'beige',
                                      ]


def makeTemplate(path, fileName='lookupTemplate.xlsx', ):
    """
    :param path: path where to save the template
    :param fileName: name of template
    :return:  the file path where is saved
    """
    if path is None:
       raise ValueError("path cannot be None.")
    file = joinPath(path, fileName)
    substanceDf = getDefaultSubstancesDF()
    sampleDF = getDefaultSampleDF()
    writer = pd.ExcelWriter(file, engine='xlsxwriter')
    substanceDf.to_excel(writer, sheet_name=SUBSTANCE)
    sampleDF.to_excel(writer, sheet_name=SAMPLE)
    writer.save()
    return writer


def getDefaultSubstancesDF():
    return pd.DataFrame(columns=SUBSTANCES_SHEET_COLUMNS)


def getDefaultSampleDF():
    return pd.DataFrame(columns=SAMPLE_SHEET_COLUMNS)


def _filterBrukerExperiments(brukerFilePaths, fileType='1r', multipleExp=False, expDirName='1', procDirName='1'):
    """

    :param brukerFilePaths:
    :param fileType:
    :param multipleExp: whether or not there are subdirectories after the spectrum top dir before the  acqu files and pdata dir (even one).
                        eg.a)  SpectrumDir > pdata > 1 > 1r     ====  multipleExp=False
                        eg.b)  SpectrumDir > 1 > pdata > 1 > 1r ====  multipleExp=True

    :param expDirName: if there are: str of folder name. e.g. '1','2'... '700'
                        eg)  SpectrumDir > |1|   > pdata > 1 > 1r
                                        > |2|   > pdata > 1 > 1r
                                        > |700| > pdata > 1 > 1r
                            Default: 1
    :param procDirName: dir name straight
                         eg)  SpectrumDir > 1  > pdata > |1| > 1r
                                                      > |2| > 1r
                        default: 1
    :return: list of filtered global path
    """
    filteredPaths = []
    for path in brukerFilePaths:
        path = aPath(path)
        if path.basename == fileType:
            dirBasename = path.filepath.basename  ## directory of  1r file has to be as defaultProcsNumber
            if dirBasename == procDirName:
                if multipleExp:  # search for other expeiments and take only the one of interest.
                    expP = path.filepath
                    # pdata = expP.parents[0]
                    if expP.basename == expDirName:
                        filteredPaths.append(path)
                else:
                    filteredPaths.append(path)
    return filteredPaths


class ExcelReader(object):

    # from ccpn.util.decorators import profile
    # @profile
    def __init__(self, project, excelPath):
        """
        :param project: the ccpnmr Project object
        :param excelPath: excel file path

        This reader will process excel files containing one or more sheets.
        The file needs to contain  either the word Substances or Samples in the sheets name.

        The user can load a file only with Substances or Samples sheet or both. Or a file with enumerate sheets
        called eg Samples_Exp_1000, Samples_Exp_1001 etc.

        The project will create new Substances and/or Samples and SpectrumGroups only once for a given name.
        Therefore, dropping twice the same file, or giving two sheets with same sample/substance/spectrumGroup name
        will fail to create new objects.



        Reader Steps:

        - Parse the sheet/s and return a dataframe for each sheet containing at least the str name Substances or Samples
        - Create Substances and/or samples if not existing in the project else skip with warning
        - For each row create a dict and link to the obj eg. {Substance: {its dataframe row as dict}
        - Create SpectrumGroups if not existing in the project else add a suffix
        - Load spectra on project and dispatch to the object. (e.g. SU.referenceSpectra, SA.spectra, SG.spectra)
        - set all attributes for each object as in the wrapper


        """
        self._totalProcessesCount = 0
        self._project = project
        self.excelPath = aPath(excelPath)
        self.pandasFile = pd.ExcelFile(self.excelPath)
        self.sheets = self._getSheets(self.pandasFile)
        self.dataframes = self._getDataFrameFromSheets(self.sheets)

    def load(self):
        """Load the actual data in the the project
        """
        if SERIES in self.sheets:
            getLogger().info('Loading Series...')
            self._loadSeries()
            getLogger().info('Loading from Excel completed...')
            return
        self._addDefaultSpectrumColours = True
        self._tempSpectrumGroupsSpectra = {}  # needed to improve the loading speed
        self.substancesDicts = self._createSubstancesDataFrames(self.dataframes)
        self.samplesDicts = self._createSamplesDataDicts(self.dataframes)
        self.spectrumGroups = self._createSpectrumGroups(self.dataframes)
        self._totalProcessesCount = 5

        processCount = 1
        #### Loading Substances metadata #######
        getLogger().info('Loading Substances metadata...')
        self._dispatchAttrsToObjs(self.substancesDicts, processCount=processCount, sheetName='Substances')
        processCount += 1

        #### Loading Substances Spectra #######
        getLogger().info('Loading Substances Spectra...')
        self._loadSpectraForSheet(self.substancesDicts, processCount=processCount, sheetName='Substances')
        processCount += 1

        #### Loading Samples metadata #######
        getLogger().info('Loading Samples metadata...')
        self._dispatchAttrsToObjs(self.samplesDicts,  processCount=processCount, sheetName='Samples')
        processCount += 1

        #### Loading Substances Spectra #######
        getLogger().info('Loading Samples Spectra...')
        self._loadSpectraForSheet(self.samplesDicts, processCount=processCount, sheetName='Samples')
        processCount += 1

        #### Loading SpectrumGroups #######
        getLogger().info('Loading SpectrumGroups...')
        self._fillSpectrumGroups(processCount=processCount, sheetName='')

        getLogger().info('Loading from Excel completed...')

        # self._project.unblankNotification()

    ######################################################################################################################
    ######################                  PARSE EXCEL                     ##############################################
    ######################################################################################################################

    def _getSheets(self, pandasfile):
        """return: list of the sheet names"""
        return pandasfile.sheet_names

    def _getDataFrameFromSheet(self, sheetName):
        'Creates the dataframe for the sheet. If Values are not set, fills None with NOTGIVEN (otherwise can give errors)'
        dataFrame = self.pandasFile.parse(sheetName)
        dataFrame.fillna(NOTGIVEN, inplace=True)
        return dataFrame

    def _getDataFrameFromSheets(self, sheetNamesList):
        """Reads sheets containing the names SUBSTANCES or SAMPLES and creates a dataFrame for each"""

        dataFrames = []
        for sheetName in [name for name in sheetNamesList if SUBSTANCE in name]:
            dataFrames.append(self._getDataFrameFromSheet(sheetName))
        for sheetName in [name for name in sheetNamesList if SAMPLE in name]:
            dataFrames.append(self._getDataFrameFromSheet(sheetName))
        for sheetName in [name for name in sheetNamesList if SERIES in name]:
            dataFrames.append(self._getDataFrameFromSheet(sheetName))
        return dataFrames

    ###################################################################################################
    ######################                  CREATE SERIES               ##############################################
    ###################################################################################################

    def _loadSeries(self):
        # createSeries from SpectrumGroups
        for df in self.dataframes:
            for ix, seriesGroup in df.groupby(SPECTRUM_GROUP_NAME, sort=False):
                seriesName = seriesGroup[SPECTRUM_GROUP_NAME].unique()[0]
                spectra = []
                seriesValues = []
                seriesUnit = None
                for rix, row in seriesGroup.iterrows():
                    dct = row.to_dict()
                    spPath = row[SPECTRUM_PATH]
                    spectra.append(self._loadSpectumFromPath(spPath, dct, obj=None))
                    seriesValues.append(row.get(SERIES_VALUE))
                    seriesUnit = row.get(SERIES_UNIT)

                spGroup = self._createNewSpectrumGroup(seriesName)
                spGroup.spectra = spectra
                spGroup.series = tuple(seriesValues)
                spGroup.seriesUnits = seriesUnit

    ######################################################################################################################
    ######################                  CREATE SUBSTANCES               ##############################################
    ######################################################################################################################

    def _createSubstancesDataFrames(self, dataframesList):
        """Creates substances in the project if not already present, For each substance link a dictionary of all its values
         from the dataframe row. """
        from ccpn.core.Substance import _newSubstance

        substancesDataFrames = []
        for dataFrame in dataframesList:
            for dataFrameAsDict in dataFrame.to_dict(orient="index").values():
                if SUBSTANCE_NAME in dataFrame.columns:
                    for key, value in dataFrameAsDict.items():
                        if key == SUBSTANCE_NAME:
                            if self._project is not None:
                                if not self._project.getByPid('SU:' + str(value) + '.'):
                                    substance = _newSubstance(self._project, name=str(value))
                                    substancesDataFrames.append({substance: dataFrameAsDict})
                                else:
                                    getLogger().warning('Impossible to create substance %s. A substance with the same name already '
                                                        'exsists in the project. ' % value)

        return substancesDataFrames

    ######################################################################################################################
    ######################                  CREATE SAMPLES                  ##############################################
    ######################################################################################################################

    def _createSamplesDataDicts(self, dataframesList):
        """Creates samples in the project if not already present, For each sample link a dictionary of all its values
         from the dataframe row. """
        samplesDataFrames = []
        ## first creates samples without duplicates,
        samples = self._createSamples(dataframesList)
        if len(samples) > 0:
            ## Second creates dataframes to dispatch the properties,
            for dataFrame in dataframesList:
                for dataFrameAsDict in dataFrame.to_dict(orient="index").values():
                    if SAMPLE_NAME in dataFrame.columns:
                        for key, value in dataFrameAsDict.items():
                            if key == SAMPLE_NAME:
                                if self._project is not None:
                                    sample = self._project.getByPid('SA:' + str(value))
                                    if sample is not None:
                                        samplesDataFrames.append({sample: dataFrameAsDict})

        return samplesDataFrames

    def _createSamples(self, dataframesList):
        from ccpn.util.Common import naturalSortList
        from ccpn.core.Sample import _newSample

        samples = []
        for dataFrame in dataframesList:
            if SAMPLE_NAME in dataFrame.columns:
                saNames = list(set((dataFrame[SAMPLE_NAME])))
                saNames = naturalSortList(saNames, False)
                for name in saNames:
                    if not self._project.getByPid('SA:' + str(name)):
                        sample = _newSample(self._project, name=str(name))
                        samples.append(sample)

                    else:
                        getLogger().warning('Impossible to create sample %s. A sample with the same name already '
                                            'exsists in the project. ' % name)
        return samples

    ######################################################################################################################
    ######################            CREATE SPECTRUM GROUPS                ##############################################
    ######################################################################################################################

    def _createSpectrumGroups(self, dataframesList):
        """Creates SpectrumGroup in the project if not already present. Otherwise finds another name a creates new one.
        dropping the same file over and over will create new spectrum groups each time"""
        spectrumGroups = []
        for dataFrame in dataframesList:
            if SPECTRUM_GROUP_NAME in dataFrame.columns:
                for groupName in list(set((dataFrame[SPECTRUM_GROUP_NAME]))):
                    # name = self._checkDuplicatedSpectrumGroupName(groupName)
                    newSG = self._createNewSpectrumGroup(groupName)
                    self._tempSpectrumGroupsSpectra[groupName] = []
                    spectrumGroups.append(newSG)
        return spectrumGroups

    ##keep this code
    # def _checkDuplicatedSpectrumGroupName(self, name):
    #   'Checks in the preject if a spectrumGroup name exists already and returns a new available name '
    #   if self._project:
    #     for sg in self._project.spectrumGroups:
    #       if sg.name == name:
    #         name += '@'
    #     return name

    def _createNewSpectrumGroup(self, name):
        from ccpn.core.SpectrumGroup import _newSpectrumGroup

        if self._project:
            if not self._project.getByPid('SG:' + str(name)):
                return _newSpectrumGroup(self._project, name=str(name))
            else:
                getLogger().warning('Impossible to create the spectrumGroup %s. A spectrumGroup with the same name already '
                                    'exsists in the project. ' % name)


    ######################################################################################################################
    ######################             LOAD SPECTRA ON PROJECT              ##############################################
    ######################################################################################################################

    def _loadSpectumFromPath(self, path, dct, obj=None):

        newSpectrum = None
        excelSpectrumPath = aPath(str(path))

        if excelSpectrumPath.exists():
            ### We have the absolute (full path)
            newSpectrum = self._addSpectrum(filePath=excelSpectrumPath, dct=dct, obj=obj)
        else:
            ### We are in a relative path scenario
            self.directoryPath = self.excelPath.filepath
            globalFilePath = aPath(joinPath(self.directoryPath, excelSpectrumPath))
            if globalFilePath.exists():
                ### it is a folder, e.g Bruker type. We can handle it already.
                newSpectrum = self._addSpectrum(filePath=globalFilePath, dct=dct, obj=obj)
            else:
                ### it is a single spectrum file name or relative path for a single file,
                ### e.g.: "mySpectrum" or "mySpectrum.hdf5" or "myDir/mySpectrum.hdf5"
                globalDirFilePath = globalFilePath.filepath
                globalfilePaths = globalDirFilePath.listDirFiles()
                for _globalfilePath in globalfilePaths:
                    if _globalfilePath.basename == excelSpectrumPath.basename:
                        newSpectrum = self._addSpectrum(filePath=_globalfilePath, dct=dct, obj=obj)
        return newSpectrum

    def _loadSpectraForSheet(self, dictLists, processCount, sheetName):
        """
        Paths in an Excel sheet can be:
            - absolute (full path)
            - relative (path starts from the excel directory)
            - file name only (path is reconstructed)
        """
        _args = []
        if self._project is not None:
            process = f'Performing actions {str(processCount)}/{str(self._totalProcessesCount)}:'
            text = f'Loading Spectra for {sheetName}'
            text = f"""{process}\n{text}"""
            with progressHandler(title='Loading Data', maximum=len(dictLists), text=text,
                                 hideCancelButton=True, ) as progress:
                for i, objDict in enumerate(dictLists):
                    progress.setValue(i)
                    for obj, dct in objDict.items():
                        for key, value in dct.items():
                            if key == SPECTRUM_PATH:
                                self._loadSpectumFromPath(value, dct, obj=obj)

    def _addSpectrum(self, filePath, dct, obj):
        """
        :param filePath: spectrum full file path
        :param dct:  dict with information for the spectrum. eg EXP type
        :obj: obj to link the spectrum to. E.g. Sample or Substance,
        """
        name = dct.get(SPECTRUM_NAME)
        if not name and obj is not None:
            name = obj.name

        data = self._project.application.loadData(filePath)
        if data is not None and len(data) > 0:
            sp = data[0]
            if not sp.name == name:
                sp.rename(name)

            if obj is not None:
                self._linkSpectrumToObj(obj, sp, dct)
            if EXP_TYPE in dct:  # use exp name as it is much faster and safer to save than exp type.
                sp.experimentName = dct[EXP_TYPE]
                # getLogger().debug3(msg=(e, data[0], dct[EXP_TYPE]))

            sp.sliceColour = dct.get(SPECTRUMHEXCOLOUR, sp.sliceColour)
            sp.positiveContourColour = dct.get(POSITIVECONTOURCOLOUR,  sp.positiveContourColour)
            sp.negativeContourColour = dct.get(NEGATIVECONTOURCOLOUR,  sp.negativeContourColour)
            sp.positiveContourBase = dct.get(POSITIVECONTOURBASE, sp.positiveContourBase)
            sp.negativeContourBase = dct.get(NEGATIVECONTOURBASE, sp.negativeContourBase)
            incNeg = dct.get(INCLUDENEGATIVECONTOURS)
            includeNegativeContours =  False if incNeg in ['no', 'N', 'No','n', None, NOTGIVEN] else True
            sp.includeNegativeContours = includeNegativeContours
            self._addDefaultSpectrumColours = False
            return sp
    ######################################################################################################################
    ######################              ADD SPECTRUM TO RELATIVE OBJECTS              ####################################
    ######################################################################################################################

    def _linkSpectrumToObj(self, obj, spectrum, dct):
        from ccpn.core.Sample import Sample
        from ccpn.core.Substance import Substance

        if isinstance(obj, Substance):
            obj.referenceSpectra += (spectrum,)

        if isinstance(obj, Sample):
            obj.spectra += (spectrum,)

        for key, value in dct.items():
            if key == SPECTRUM_GROUP_NAME:
                # spectrumGroup = self._project.getByPid('SG:' + str(value))
                tempSGspectra = self._tempSpectrumGroupsSpectra.get(str(value))
                if tempSGspectra is not None:
                    tempSGspectra.append(spectrum)
                # if spectrumGroup is not None: # this strategy is very slow. do not use here.
                #     spectrumGroup.spectra += (spectrum,)
                if SERIES_VALUE in dct:  # direct insertion of series values for speed optimisation
                    spectrum._setInternalParameter(spectrum._SERIESITEMS, {'SG:' + str(value): dct[SERIES_VALUE]})

    def _fillSpectrumGroups(self,  processCount, sheetName=None):

        colourNames = cycle(TOP_SG_COLOURS)
        loopLenght = len(self._tempSpectrumGroupsSpectra.items())
        process = f'Performing actions {str(processCount)}/{str(self._totalProcessesCount)}:'
        text = f'Loading SpectrumGroups'
        text = f"""{process}\n{text}"""
        with progressHandler(title='Loading Data', maximum=loopLenght, text=text,
                             hideCancelButton=True, ) as progress:

            for i, (sgName, spectra) in enumerate(self._tempSpectrumGroupsSpectra.items()):
                progress.setValue(i)
                spectrumGroup = self._project.getByPid('SG:' + str(sgName))
                if spectrumGroup is not None:
                    spectrumGroup.spectra = spectra
                # give some default colours
                if self._addDefaultSpectrumColours:
                    hexColour = name2Hex( next(colourNames))
                    spectrumGroup.sliceColour = hexColour
                    for sp in spectra:
                        sp.sliceColour = hexColour

    ######################################################################################################################
    ######################            DISPATCH ATTRIBUTES TO RELATIVE OBJECTS         ####################################
    ######################################################################################################################

    def _dispatchAttrsToObjs(self, dataDicts, processCount, sheetName):
        from ccpn.core.Sample import Sample
        from ccpn.core.Substance import Substance
        loopLenght = len(dataDicts)
        process = f'Performing actions {str(processCount)}/{str(self._totalProcessesCount)}:'
        text = f'Loading Spectra for {sheetName}'
        text = f"""{process}\n{text}"""
        with progressHandler(title='Loading Data', maximum=loopLenght, text=text,
                             hideCancelButton=True, ) as progress:

            for i, objDict in enumerate(dataDicts):
                progress.setValue(i)
                for obj, dct in objDict.items():
                    if isinstance(obj, Substance):
                        self._setWrapperProperties(obj, SUBSTANCE_PROPERTIES, dct)
                    if isinstance(obj, Sample):
                        self._setWrapperProperties(obj, SAMPLE_PROPERTIES, dct)
                        self._createSampleComponents(obj, dct)

    def _setWrapperProperties(self, wrapperObject, properties, dataframe):
        for attr in properties:
            if attr == synonyms:
                value = self._getDFValue(attr, dataframe)
                if value is not None:
                    setattr(wrapperObject, attr, (value,))
            else:
                try:
                    currentAttrValue = getattr(wrapperObject, attr)
                    newDataValue = self._getDFValue(attr, dataframe)
                    if currentAttrValue in [None, 0]:
                        setattr(wrapperObject, attr, newDataValue)
                    else:
                        if attr == comment:
                            setattr(wrapperObject, attr, newDataValue)

                except Exception:  #wrapper needs a int
                    value = self._getDFValue(attr, dataframe)
                    if value is not None:
                        setattr(wrapperObject, attr, int(value))
                except:
                    getLogger().debug3(msg=('Value  not set for %s' % attr))

    def _getDFValue(self, header, data):
        value = [[excelHeader, value] for excelHeader, value in data.items()
                 if excelHeader == str(header) and value != NOTGIVEN]
        if len(value) > 0:
            return value[0][1]

    ######################################################################################################################
    ######################                    ADD SAMPLE COMPONENTS                   ####################################
    ######################################################################################################################

    def _createSampleComponents(self, sample, data):
        from ccpn.core.SampleComponent import _newComponent

        sampleComponentsNames = [[header, sampleComponentName] for header, sampleComponentName in data.items() if
                                 header == SAMPLE_COMPONENTS and sampleComponentName != NOTGIVEN]
        if len(sample.sampleComponents) == 0:
            if len(sampleComponentsNames) > 0:
                # check if is , or ; separated
                splitter = ','
                if ';' in sampleComponentsNames[0][1]:
                    splitter = ';'
                for name in sampleComponentsNames[0][1].split(splitter):
                    if not self._project.getByPid('SC:' + str(name)):
                        sampleComponent = _newComponent(sample, name=(str(name)))
                        sampleComponent.role = 'Compound'
