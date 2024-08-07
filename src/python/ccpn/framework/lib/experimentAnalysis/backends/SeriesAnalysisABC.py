"""
This module defines base classes for Series Analysis
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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-07 09:20:36 +0100 (Wed, August 07, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from scipy import stats
import pandas as pd
from abc import ABC
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Logging import getLogger
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.DataTable import DataTable
from ccpn.util.traits.TraitBase import TraitBase
from ccpn.util.traits.CcpNmrTraits import List
from ccpn.framework.Application import getApplication, getCurrent, getProject
from ccpn.framework.lib.experimentAnalysis.SeriesTables import SeriesFrameBC, InputSeriesFrameBC
import ccpn.framework.lib.experimentAnalysis.calculationModels._libraryFunctions as lf
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.PathsAndUrls import ccpnExperimentAnalysisPath
from ccpn.util.Path import aPath, scandirs
from ccpn.util.Common import fetchPythonModules


class SeriesAnalysisABC(ABC):
    """
    The top level class for SeriesAnalysis modules.
    """
    seriesAnalysisName = ''
    _allowedPeakProperties = [sv._HEIGHT, sv._VOLUME, sv._PPMPOSITION, sv._LINEWIDTH]
    _minimisedProperty = None  # the property currently used to perform the fitting routines. Default height, but can be anything.
    _modelsAreLoaded = False

    @property
    def inputDataTables(self) -> list:
        """
        Get the attached input DataTables
        Lists of DataTables.
        """
        self._ensureDataType()
        return list(self._inputDataTables)

    @inputDataTables.setter
    def inputDataTables(self, values):
        self._inputDataTables = OrderedSet(values)
        self._ensureDataType()

    def addInputDataTable(self, dataTable):
        """
        Add a DataTable as inputData
        """
        self._inputDataTables.add(dataTable)

    def removeInputDataTable(self, dataTable):
        """
        Remove a DataTable as inputData
        """
        self._inputDataTables.discard(dataTable)

    def clearInputDataTables(self):
        """
        Remove all  DataTable as inputData
        """
        self._inputDataTables = OrderedSet()

    @property
    def outputDataTableName(self):
        """The name for the outputDataTable created after a fitData routine """
        return self._outputDataTableName

    @outputDataTableName.setter
    def outputDataTableName(self, name):
        self._outputDataTableName = name

    @property
    def resultDataTable(self):
        """ The dataTable  which will be displayed on tables"""
        return self._resultDataTable

    @resultDataTable.setter
    def resultDataTable(self, dataTable):
        self._resultDataTable = dataTable


    @property
    def _resultDataFrameWithExclusions(self):
        """ The dataFrame  which contains filtered out values based on user's exclusions.
         This method is necessary to do not override the data on the output ResultData table"""
        _resultDataTable = self._resultDataTable
        df = _resultDataTable.data.copy()
        if sv.NMRRESIDUEPID not in df:
            return df

        blankColumns = []
        if sv.MODEL_NAME in df:
            modelName = df.modelName.values[-1]
            fittingModelClass = self.getFittingModelByName(modelName)
            if fittingModelClass:
                model = fittingModelClass()
                blankColumns += model.modelStatsNames
                blankColumns += model.modelArgumentNames
                blankColumns += model.modelArgumentErrorNames

        if sv.CALCULATION_MODEL in df:
            calculationName = df.calculationModel.values[-1]
            calculationModelClass = self.getCalculationModelByName(calculationName)
            if calculationModelClass:
                model = calculationModelClass()
                blankColumns += model.modelArgumentNames

        excludedNmrResiduesPids = self.exclusionHandler._getExcludedNmrResiduePids(dataTable=_resultDataTable)
        excludedNmrResiduesDf = df[df[sv.NMRRESIDUEPID].isin(excludedNmrResiduesPids)]
        excludedIndexes = excludedNmrResiduesDf.index
        df.loc[excludedIndexes, blankColumns] = np.nan

        return df

    def _fetchOutputDataTable(self, name=None):
        """
        Interanl. Called after 'fit()' to get a valid Datatable to attach the fitting output SeriesFrame
        :param seriesFrameType: str,  A filtering serieFrameType.
        :return: DataTable
        """
        dataTable = self.project.getDataTable(name)
        if dataTable:
            # restore the type in case is from a reopened project.
            dataTable.data.__class__ = SeriesFrameBC

        if not dataTable:
            dataTable = self.project.newDataTable(name)
        ## update the DATATABLETYPE
        dataTable.setMetadata(sv.DATATABLETYPE, sv.SERIESANALYSISOUTPUTDATA)
        dataTable.setMetadata(sv.SERIESFRAMETYPE,  sv.SERIESANALYSISOUTPUTDATA)
        return dataTable

    def getResultDataFrame(self, useFiltered=True) -> pd.DataFrame:
        """
        Get the SelectedOutputDataTable and merge rows by the collection pid
        """

        dataTable = self.resultDataTable
        if dataTable is None:
            return pd.DataFrame()
        if useFiltered:
            dataFrame = self._resultDataFrameWithExclusions
        else:
            dataFrame = dataTable.data
        if len(dataFrame)==0:
            return pd.DataFrame()
        if not sv.COLLECTIONPID in dataFrame:
            return dataFrame
        ## group by id and keep only first row as all duplicated except the series steps, which are not needed here.
        ## reset index otherwise you lose the column collectionId
        outDataFrame = dataFrame.groupby(sv.COLLECTIONPID).first().reset_index()
        outDataFrame.set_index(sv.COLLECTIONPID, drop=False, inplace=True)

        # add the rawData as new columns (Transposed from column to row)
        lastSeenSeriesStep = None
        for ix, ys in dataFrame.groupby(sv.COLLECTIONPID)[[sv.SERIES_STEP_X, sv.SERIES_STEP_Y]]:
            for seriesStep, seriesValue in zip(ys[sv.SERIES_STEP_X].astype(str).values, ys[sv.SERIES_STEP_Y].values):
                if seriesStep == lastSeenSeriesStep:
                    seriesStep += sv.SEP # this is the case when two series Steps are the same! Cannot create two identical columns or 1 will disappear
                outDataFrame.loc[ix, seriesStep] = seriesValue
                lastSeenSeriesStep = seriesStep
        # additional Series values to be added here?

        # drop columns that should not be on the Gui. To remove: peak properties (dim, height, ppm etc)
        toDrop = sv.PeakPropertiesHeaders + [sv._SNR, sv.DIMENSION, sv.ISOTOPECODE, sv.NMRATOMNAME, sv.NMRATOMPID]
        # toDrop += sv.ALL_EXCLUDED
        toDrop += ['None',  'None_'] #not sure yet where they come from
        outDataFrame.drop(toDrop, axis=1, errors='ignore', inplace=True)

        outDataFrame[sv.COLLECTIONID] = outDataFrame[sv.COLLECTIONID]
        ## sort by NmrResidueCode if available otherwise by COLLECTIONID
        if outDataFrame[sv.NMRRESIDUECODE].astype(str).str.isnumeric().all():
            outDataFrame.sort_values(by=sv.NMRRESIDUECODE, key=lambda x: x.astype(int), inplace =True)
        else:
            outDataFrame.sort_values(by=sv.COLLECTIONID, inplace=True)
        ## apply an ascending ASHTAG. This is needed for tables and BarPlotting
        outDataFrame[sv.INDEX] = np.arange(1, len(outDataFrame) + 1)
        ## put ASHTAG as first header
        outDataFrame.insert(0, sv.INDEX, outDataFrame.pop(sv.INDEX))
        return outDataFrame

    @property
    def inputCollection(self):
        """The parent collection containing all subPeakCollections """
        return self._inputCollection

    @inputCollection.setter
    def inputCollection(self, collection):
        """The parent collection containing all subPeakCollections """
        self._inputCollection = collection

    @property
    def inputSpectrumGroups(self):
        return list(self._inputSpectrumGroups)

    def addInputSpectrumGroup(self, spectrumGroup):
        """Add a spectrumGroup to the inputList. Used to create InputDataTables"""
        self._inputSpectrumGroups.add(spectrumGroup)

    def removeInputSpectrumGroup(self, spectrumGroup):
        """Remove a spectrumGroup to the inputList. Used to create InputDataTables"""
        self._inputSpectrumGroups.discard(spectrumGroup)

    def clearInputSpectrumGroups(self):
        """Remove  spectrumGroups to the inputList. Used to create InputDataTables"""
        self._inputSpectrumGroups.clear()

    @property
    def exclusionHandler(self):
        """Get an object containing all excluded pids"""
        exclusionHandler = self._exclusionHandler
        dataTable = self.project.getDataTable(self.outputDataTableName)
        if dataTable is not None:
            exclusionHandler._dataTable = dataTable
        return exclusionHandler

    @property
    def untraceableValue(self) -> float:
        return self._untraceableValue

    @untraceableValue.setter
    def untraceableValue(self, value):
        if isinstance(value, (float, int)):
            self._untraceableValue = value
        else:
            getLogger().warning(f'Impossible to set untraceableValue to {value}. Use type int or float.')

    def fitInputData(self) -> DataTable:
        """
        Perform calculations using the currentFittingModel and currentCalculationModel to the inputDataTables
        and save outputs to a single newDataTable.
        1) Perform the CalculationModel routines (which do not do any fitting (e.g.: exponential decay)  but only a plain calculation)
        2) Use the result frame from the Calculation model as input for the FittingModel.
        We must follow this order.

        Sometime only a calculation model is necessary, in that case set calculationModel._disableFittingModels to True.

        Resulting dataTables are available in the outputDataTables.
        :return: output dataTable . Creates a new output dataTable in outputDataTables
        """
        getLogger().warning(sv.UNDER_DEVELOPMENT_WARNING)

        if len(self.inputDataTables) == 0:
            raise RuntimeError('Cannot run any fitting models. Add a valid inputData first')

        outputFrame = self.currentCalculationModel.calculateValues(self.inputDataTables)
        self._minimisedProperty =  self.currentCalculationModel._minimisedProperty
        if not self.currentCalculationModel._disableFittingModels:
            outputFrame = self.currentFittingModel.fitSeries(outputFrame)

        outputFrame.joinNmrResidueCodeType()
        outputDataTable = self._fetchOutputDataTable(name=self._outputDataTableName)
        outputDataTable.data = outputFrame
        self._setMinimisedPropertyFromModels()
        return outputDataTable

    def refitCollection(self, collectionPid,
                        fittingModel=None,
                        minimiserMethod=None,
                        resetInitialParams=False,
                        customMinimiserParamsDict=None):
        """
        Given a CollectionPid, refit the series using the options defined in the module.
        :param collectionPid: str: Ccpn collection pid for a collection which is contained in the inputDataTables and outputData.
        :param resetInitialParams: bool. True   to re-guess the initial params. False to start the refit using the parameters from the last best fit.
        :param customMinimiserParamsDict. A dict of dict containing the new parameters to be considered for the fitting. Use with caution, see the Minimiser "make_params" for proper usage.
                    e.g.: usage for a OnePhaseDecayPlateauModel:
                            minimiserParamsDict = {'amplitude': 10, 'rate': 3, 'plateau': 0}
                            or to setup ranges:
                            minimiserParamsDict = {'amplitude': dict(value=2.4),
                                                                 'rate': dict(value=1.5),
                                                                  'plateau': dict(value=0.5, min=0, max=None)}

        :return: a pandas dataFrame with the latest fitted data.
        """
        resultDataTable = self.resultDataTable
        resultData = resultDataTable.data
        fittingModel = fittingModel or self.currentFittingModel
        dfForCollection = resultData[resultData[sv.COLLECTIONPID] == collectionPid].copy()
        dfForCollection.sort_values([fittingModel.xSeriesStepHeader], inplace=True)
        seriesSteps = Xs = dfForCollection[fittingModel.xSeriesStepHeader].values
        seriesValues = Ys = dfForCollection[fittingModel.ySeriesStepHeader].values
        minimiser = fittingModel.Minimiser()

        ## Get the initial fitting Params from the ResultData
        resultDataForCollection = resultData[resultData[sv.COLLECTIONPID] == collectionPid].copy()
        if resetInitialParams:
            params = minimiser.guess(Ys, Xs)
        else:
            if customMinimiserParamsDict is None:
                modelNames = fittingModel.modelArgumentNames
                modelValues = resultDataForCollection[modelNames].values[0]
                existingModelParamsDict = dict(zip(modelNames, modelValues))
                params = minimiser.make_params(**existingModelParamsDict)
            else:
                try:
                    params = minimiser.make_params(**customMinimiserParamsDict)
                except Exception as err:
                    getLogger().warn(f'Could not make parameters for the current fitting. Ensure the format is correct. {customMinimiserParamsDict}. {err}. Fallback enabled.')
                    params = minimiser.guess(Ys, Xs)
        if minimiserMethod is not None:
            minimiser.setMethod(minimiserMethod)
        print(f'FITTING WITH: {Ys} ===PARAMS: {params}  == Xs:{Xs}')
        result = minimiser.fit(Ys, params, x=Xs, method=minimiserMethod)
        print(f'====='*5)

        ## write to the output data (overriding the previously results)
        for ix, row in resultDataForCollection.iterrows():
            for resultName, resulValue in result.getAllResultsAsDict().items():
                resultData.loc[ix, resultName] = resulValue
            resultData.loc[ix, sv.MODEL_NAME] = fittingModel.modelName
            resultData.loc[ix, sv.MINIMISER_METHOD] = minimiser.method

    def _setMinimisedPropertyFromModels(self):
        """ Set the _minimisedProperty from the current models.
         Calculation model has priority, otherwise use the fitting model unless disabled."""

        self._minimisedProperty =  self.currentCalculationModel._minimisedProperty
        if self._minimisedProperty is None and not self.currentCalculationModel._disableFittingModels:
            self._minimisedProperty = self.currentFittingModel._minimisedProperty

    def _rebuildInputData(self):
        """Rebuild all the inputData tables from the defined SpectrumGroups."""
        inputCollection = self.inputCollection
        for spGroup in self.inputSpectrumGroups:
            for inputData in self.inputDataTables:
                inputData.data.buildFromSpectrumGroup(spGroup, parentCollection=inputCollection)

    @property
    def currentFittingModel(self):
        """ The working fittingModel in the module.
         E.g.: the initiated ExponentialDecayModel. See models for docs. """
        if self._currentFittingModel is None:
            model = self._getFirstModel(self.fittingModels)
            return model()
        return self._currentFittingModel

    @currentFittingModel.setter
    def currentFittingModel(self, model):
        self._currentFittingModel = model

    @property
    def currentCalculationModel(self):
        """ The working CalculationModel in the module.
        E.g.: the initiated EuclidianModel for ChemicalshiftMapping. See models for docs. """
        if self._currentCalculationModel is None:
            model = self._getFirstModel(self.calculationModels)
            return model()
        return self._currentCalculationModel

    @currentCalculationModel.setter
    def currentCalculationModel(self, model):
        self._currentCalculationModel = model

    def _loadModelsFromDisk(self):
        """ Inspect the directory and search for importable modules """
        import inspect as _inspect
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC
        from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel

        print('LOADING  self._loadedModels===:',  self._loadedModels)
        if self._modelsAreLoaded:
            print('LOADING  self._loadedModels===:', self._loadedModels)
            return
        fittingModelsPath = aPath(ccpnExperimentAnalysisPath) / 'fittingModels'
        calculationModelsPath = aPath(ccpnExperimentAnalysisPath) / 'calculationModels'
        # userModels = ''to be done'
        fittingModelsSubDirPaths = scandirs(fittingModelsPath)
        calculationModelsSubDirPaths = scandirs(calculationModelsPath)

        allModelsFilePaths = fittingModelsSubDirPaths + calculationModelsSubDirPaths
        print('allModelsFilePaths:::: ', allModelsFilePaths)
        pythonModules = fetchPythonModules(allModelsFilePaths) # this does the physical loading of the files to Python-Modules
        for pythonModule in pythonModules:
            try:
                for i, obj in _inspect.getmembers(pythonModule): # this scans for the right classes within the Python-Module
                    if _inspect.isclass(obj):
                        if issubclass(obj,  (FittingModelABC, CalculationModel)):
                            if self.seriesAnalysisName not in obj.targetSeriesAnalyses:
                                continue # skip
                            if not obj._autoRegisterModel:
                                continue
                            if not obj.modelName:
                                continue
                            print('LOADING ===:', obj)
                            self._loadedModels.add(obj)

            except Exception as loadingError: # Not encountered any so far. but just in case
                getLogger().warn(f'Error in registering the class from {pythonModule}. Skipping with: {loadingError} ')
        self._modelsAreLoaded = True
        print('end self._loadedModels===:',  self._loadedModels)


    def _registerModels(self):
        """ Register all the available models"""
        from ccpn.framework.lib.experimentAnalysis.fittingModels.BlankFittingModel import BlankFittingModel
        from ccpn.framework.lib.experimentAnalysis.calculationModels.BlankCalculationModel import BlankCalculationModel
        self.registerModel(BlankFittingModel)
        self.registerModel(BlankCalculationModel)
        for model in self._loadedModels:
            self.registerModel(model)

    def registerModel(self, model):
        """
        A method to register a Model object, either FittingModel or CalculationModel.
        See the FittingModelABC for more information
        """
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC
        from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel

        if issubclass(model, CalculationModel):
            self.calculationModels.update({model.modelName: model})
            return
        elif issubclass(model, FittingModelABC):
            self.fittingModels.update({model.modelName: model})
        else:
            getLogger().warn(f'The given model type could not be identified. Skipping: {model} ')
        return

    def deRegisterModel(self, model):
        """
        A method to de-register a  Model
        """
        self.calculationModels.pop(model.modelName, None)
        self.fittingModels.pop(model.modelName, None)

    def getFittingModelByName(self, modelName):
        """
        Convenient method to get a registered FittingModel Object  by its name
        :param modelName: str
        :return:
        """
        return self.fittingModels.get(modelName, None)

    def getCalculationModelByName(self, modelName):
        """
        Convenient method to get a registered Calculation Object  by its name
        :param modelName: str
        :return:
        """
        return self.calculationModels.get(modelName, None)

    def _getFirstModel(self, models):
        """
        Get the first Model in the dict
        :param models: dict of FittingModels or CalculationModels
        :return:
        """
        first = next(iter(models), iter({}))
        model = models.get(first)
        return model

    def newInputDataTableFromSpectrumGroup(self, spectrumGroup:SpectrumGroup,
                                           peakListIndices=None, dataTableName:str=None,
                                           experimentName:str=None):
        """
        :param spectrumGroup: object of type SpectrumGroup
        :param dataTableName: str, name for a newData table object. Autogenerated if none
        :param peakListIndices: list of int, same length of spectra. Define which peakList index to use.
                               If None, use -1 (last created) as default for all spectra
        :return:
        """
        if not isinstance(spectrumGroup, SpectrumGroup):
            raise TypeError(f'spectrumGroup argument must be a SpectrumGroup Type. Given: {type(spectrumGroup)}')
        project = spectrumGroup.project
        inputCollection = self.inputCollection
        seriesFrame = InputSeriesFrameBC()
        seriesFrame.buildFromSpectrumGroup(spectrumGroup,
                                           parentCollection=inputCollection,
                                           peakListIndices=peakListIndices,
                                           experimentName = experimentName
                                           )
        dataTable = project.newDataTable(name=dataTableName, data=seriesFrame)
        dataTable.setMetadata(sv.DATATABLETYPE, sv.SERIESANALYSISINPUTDATA)
        self._setRestoringMetadata(dataTable, seriesFrame, spectrumGroup)
        return dataTable

    def newCollectionsFromSpectrumGroup(self, spectrumGroup:SpectrumGroup, peakListIndices=None):
        """
        :param spectrumGroup: object of type SpectrumGroup
        :param dataTableName: str, name for a newData table object. Autogenerated if none
        :param peakListIndices: list of int, same length of spectra. Define which peakList index to use.
                             If None, use -1 (last created) as default for all spectra
        :return: a list of collections
        """
        from ccpn.core.lib.PeakCollectionLib import createCollectionsFromSpectrumGroup
        if not isinstance(spectrumGroup, SpectrumGroup):
            raise TypeError(f'spectrumGroup argument must be a SpectrumGroup Type. Given: {type(spectrumGroup)}')
        collections = createCollectionsFromSpectrumGroup(spectrumGroup, peakListIndices)
        return collections

    def getThresholdValueForData(self, data, columnName, calculationMode=sv.MAD, sdFactor=1.):
        """ Get the Threshold value for the ColumnName values.
        :param data: pd.dataFrame
        :param columnName: str. a column name presents in the data(frame)
        :param calculationMode: str, one of ['MAD', 'AAD', 'Mean', 'Median', 'STD']
        :param factor: float. Multiplication factor.
        :return float.

        MAD: Median absolute deviation, (https://en.wikipedia.org/wiki/Median_absolute_deviation)
        AAD: Average absolute deviation, (https://en.wikipedia.org/wiki/Average_absolute_deviation).
        Note, MAD and AAD are often abbreviated the same way, in fact, in scipy MAD is Median absolute deviation,
        whereas in Pandas MAD is Mean absolute deviation!
        """
        if columnName not in data:
            return
        value = None
        if data is not None:
            if len(data[columnName])>0:
                values = data[columnName].values
                values = values[~np.isnan(values)]  # skip nans
                mean = np.mean(values)
                if calculationMode == sv.MEAN:
                    value = mean

                if calculationMode == sv.MEDIAN:
                    value = np.median(values)

                sdFactor = sdFactor if sdFactor is not None else 1

                if calculationMode == sv.MAD:
                    value = mean + stats.median_abs_deviation(values)

                if calculationMode == sv.AAD:
                    value = mean + lf.aad(values)

                if calculationMode == sv.STD:
                    value = mean + (np.std(values) * sdFactor)

                if calculationMode == sv.VARIANCE:
                    value = mean + np.var(values)

        return value

    @staticmethod
    def _setRestoringMetadata(dataTable, seriesFrame, spectrumGroup):
        """ set the metadata needed for restoring the object"""
        dataTable.setMetadata(spectrumGroup.className, spectrumGroup.pid)
        dataTable.setMetadata(sv.SERIESFRAMETYPE, seriesFrame.SERIESFRAMETYPE)

    def _ensureDataType(self):
        """
        Reset variables and Obj type after restoring a project from its metadata.
        :return: dataTable
        """
        for dataTable in self._inputDataTables:
            if not isinstance(dataTable.data.__class__ , InputSeriesFrameBC):
                dataTable.data.__class__ = InputSeriesFrameBC

    def _isPidInDataTables(self, header, pid):
        """Check if a pid is in the inputDataTables.
         :param header: str, dataTable header e.g.: sv.PeakPid
         :param pid: str, the pid to search in the column
         :return bool. True if pid in data"""
        if len(self.inputDataTables) > 0:
            for inputDataTable in self.inputDataTables:
                data = inputDataTable.data
                filteredData = data.getByHeader(header, [pid])
                if not filteredData.empty:
                    return True
        return False

    def _getChainsFromDataFrame(self, df):
        nmrChainCodesFromDf = df[sv.NMRCHAINNAME].unique()
        nmrChains = [self.project.getNmrChain(c) for c in nmrChainCodesFromDf]
        chains = [nmrChain.chain for nmrChain in nmrChains]
        return chains

    @classmethod
    def exportToFile(cls, path, fileType, *args, **kwargs):
        """
        A method to export to an external File
        """
        pass

    def _getSeriesStepValues(self):
        """ Get the series values from the first input SpectrumGroups"""

        for spectrumGroup in self.inputSpectrumGroups:
            if spectrumGroup.series and  len(spectrumGroup.series)>0:
                return list(spectrumGroup.series) # not yet implemented with multiple SG.
        return []

    def plotResults(self, *args, **kwargs):
        pass

    def _getFittedCurvesData(self, fittedCurvePoinCount=1000):
        """ Get the fitted curves coordinates as dataframe.
        Curves are recreated from the current fitting model and output resultDataTable.
        """
        outputData = self.resultDataTable
        model = self.currentFittingModel
        df = outputData.data
        pids = df[sv.COLLECTIONPID].unique()
        xs = df[model.xSeriesStepHeader].values
        initialPoint = min(xs)
        finalPoint = max(xs)
        xf = np.linspace(initialPoint, finalPoint, fittedCurvePoinCount)
        resultDf = pd.DataFrame()
        resultDf.index = xf
        for ix, pid in enumerate(pids):
            filteredDf = df[df[sv.COLLECTIONPID] == pid]
            resCode = filteredDf[sv.NMRRESIDUECODE].values[-1]
            func = model.getFittingFunc(model)
            funcArgs = model.modelArgumentNames
            argsFit = filteredDf.iloc[0][funcArgs]
            fittingArgs = argsFit.astype(float).to_dict()
            yf = func(xf, **fittingArgs)
            resultDf[pid] = yf
        return resultDf

    def __init__(self):
        self.project = getProject()
        self.application = getApplication()
        self.current = getCurrent()
        self. _loadedModels = set()
        self._inputDataTables = OrderedSet()
        self._inputSpectrumGroups = OrderedSet()
        self._inputCollection = None
        self._outputDataTableName = sv.SERIESANALYSISOUTPUTDATA
        self._resultDataTable = None
        self._untraceableValue = 1.0   # default value for replacing NaN values in untraceableValues.
        self.fittingModels = dict()
        self.calculationModels = dict()
        self._currentFittingModel = None     ## e.g.: ExponentialDecay for relaxation
        self._currentCalculationModel = None ## e.g.: HetNoe for Relaxation
        self._needsRefitting = False
        self._needsRebuildingInputDataTables = False
        self._exclusionHandler = ExclusionHandler()

        self._loadModelsFromDisk()
        self._registerModels()

    def close(self):
        self.clearInputDataTables()
        self._currentCalculationModel = None
        self._currentFittingModel = None

    def __str__(self):
        return f'<{self.__class__.__name__}: {self.seriesAnalysisName}>'

    __repr__ = __str__


class ExclusionHandler(TraitBase):
    """ A class that holds pids of objects to be excluded from calculations. E.g.: peaks from fitting etc.
    Available Objects: (traitName are taken from the object's _pluralLinkName property):
        - peaks
        - collections
        - nmrResidues
        - nmrAtoms
        - spectra
    Use save/restore to save/restore traits as metadata into/from a datatable
    """

    _traitNames = [f'{tag}s' for tag in sv.EXCLUDED_OBJECTS]

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.project = getProject()
        for name in self._traitNames:
            self.add_traits(**{name:List()})
            self.update({name:[]}) ## ensures all starts correctly and a list works as a list!

    def getExcludedNmrResidues(self, dataTable):
        """
        Get the excluded NmrResidues from specified dataTables or globally for the backend  if  dataTables are not given.
        :param dataTable:
        :return:
        """
        excludedNmrResiduePids = self._getExcludedNmrResiduePids(dataTable)
        nmrResidues = [self.project.getByPid(nr) for nr in excludedNmrResiduePids]
        return nmrResidues

    def _getExcludedNmrResiduePids(self, dataTable):
        excludedNmrResiduePids = []
        df = dataTable.data
        if sv.NMRRESIDUEPID in df and sv.EXCLUDED_NMRRESIDUEPID in df:
            excluded = df[df[sv.EXCLUDED_NMRRESIDUEPID] == True]
            excludedNmrResiduePids = excluded[sv.NMRRESIDUEPID].unique()
        return list(excludedNmrResiduePids)

    def setExcludedNmrResidues(self, nmrResidues, dataTable):
        """Add an exclusion tag to the dataTables containing the specified residues """
        nmrResiduesPids = [nr.pid for nr in nmrResidues]
        # amend table in place. Don't need to resave to dataTable
        df = dataTable.data
        if sv.NMRRESIDUEPID in df:
            excludedNmrResiduesDf = df[df[sv.NMRRESIDUEPID].isin(nmrResiduesPids)]
            excludedIndexes = excludedNmrResiduesDf.index
            includedIndexes = [ix for ix in df.index if ix not in excludedIndexes]
            df.loc[excludedIndexes, sv.EXCLUDED_NMRRESIDUEPID] = True
            df.loc[includedIndexes, sv.EXCLUDED_NMRRESIDUEPID] = False




####
## Below objects are not implemeted yet and will be done with NTDB definitions

class GroupingNmrAtomABC(ABC):
    """
    Class for defining grouping nmrAtoms in a seriesAnalysis
    """

    groupType = None
    groupInfo = None
    nmrAtomNames = None
    excludeResidueTypes = None
    includedResidueTypes = None

    def __init__(self):
        pass

    def _getResidueFullName(self):
        pass

    def __str__(self):
        return f'<{self.__class__.__name__}: {self.groupType}>'

    __repr__ = __str__


class GroupingBackboneNmrAtoms(GroupingNmrAtomABC):

    groupType = 'Backbone'
    groupInfo = 'Follow the backbone atoms in a series Analysis'
    nmrAtomNames = ['H', 'N', 'CA', 'C ', 'HA',]
    excludeResidueTypes = ['Proline']
    includedResidueTypes = None

class GroupingSideChainNmrAtoms(GroupingNmrAtomABC):

    groupType = 'SideChain'
    groupInfo = 'Follow the SideChain atoms in a series Analysis'
    nmrAtomNames = []
    excludeResidueTypes = ['Glycine']
    includedResidueTypes = None

class GroupingBBandSSNmrAtoms(GroupingNmrAtomABC):

    groupType = 'Backbone+SideChain'
    groupInfo = 'Follow the Backbone and SideChain atoms in a series Analysis'
    nmrAtomNames = GroupingBackboneNmrAtoms.nmrAtomNames+GroupingSideChainNmrAtoms.nmrAtomNames
    excludeResidueTypes = GroupingBackboneNmrAtoms.excludeResidueTypes+GroupingSideChainNmrAtoms.excludeResidueTypes
    includedResidueTypes = None

class GroupingMethylNmrAtoms(GroupingNmrAtomABC):

    groupType = 'Methyl'
    groupInfo = 'Follow the Methyl atoms in a series Analysis'
    nmrAtomNames = []
    excludeResidueTypes = None
    includedResidueTypes = ['Alanine', 'Leucine', 'Valine', 'Isoleucine', 'Threonine', 'Methionine']

class GroupingCustomNmrAtoms(GroupingNmrAtomABC):

    groupType = 'Custom'
    groupInfo = 'Follow custom atoms in a series Analysis'
    nmrAtomNames = []
    excludeResidueTypes = None
    includedResidueTypes = None

ALL_GROUPINGNMRATOMS = {
                        GroupingBackboneNmrAtoms.groupType:GroupingBackboneNmrAtoms,
                        GroupingSideChainNmrAtoms.groupType:GroupingSideChainNmrAtoms,
                        GroupingBBandSSNmrAtoms.groupType:GroupingBBandSSNmrAtoms,
                        GroupingMethylNmrAtoms.groupType:GroupingMethylNmrAtoms,
                        GroupingCustomNmrAtoms.groupType:GroupingCustomNmrAtoms
                        }
