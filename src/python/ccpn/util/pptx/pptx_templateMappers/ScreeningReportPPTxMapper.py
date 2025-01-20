import warnings
import inspect
import numpy as np
from matplotlib.ticker import FuncFormatter
from ccpn.util.Path import fetchDir, joinPath
from ccpn.util.pptx.PPTxTemplateABC import PPTxTemplateMapperABC
from ccpn.util.pptx.PPTxWriter import * # they are just the various module variable like LAYOUT_GETTER, etc
from ccpn.util.Logging import getLogger
import ccpn.AnalysisScreen.lib.experimentAnalysis.matching.MatchingVariables as mv


class ScreeningReportTemplateMapper(PPTxTemplateMapperABC):
    """
     See ABC for documentation
    """

    templateResourcesFileName = 'Screening_report_template.pptx'
    templateSettingsFileName = 'Screening_report_template_settings.json'
    templateMapperName = 'Screening PPTx Report'
    scratchDirName = 'screenReport' # the directory name created inside the ccpn temporary directory. And Cleared up after the report is generated
    slideMapping = {
                                'Title Slide': {
                                    LAYOUT_GETTER: 'buildTitleSlide',
                                    PLACEHOLDER_DEFS: [
                                                                            {
                                                                                PLACEHOLDER_NAME  : 'Title',
                                                                                PLACEHOLDER_TYPE  : PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getTitle',
                                                                                },
                                                                            {
                                                                                PLACEHOLDER_NAME  : 'Subtitle',
                                                                                PLACEHOLDER_TYPE  : PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getSubtitle',
                                                                                },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Operator',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getOperator',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Date-Time',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getDateTime',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Data Paths',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getDataPaths',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Program Info',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getProgramInfo',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Pipeline Settings',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getPipelineSettings',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Calculation Settings',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getCalculationSettings',
                                                                            },
                                                                            {
                                                                                PLACEHOLDER_NAME: 'Comment',
                                                                                PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                                PLACEHOLDER_GETTER: 'getTitleComment',
                                                                            },
                                    ],
                                },

                            'Substances Summary': {
                                LAYOUT_GETTER: 'buildSubstancesSummarySlides',
                                PLACEHOLDER_DEFS: [
                                                                        {
                                                                            PLACEHOLDER_NAME: 'Title',
                                                                            PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                            PLACEHOLDER_GETTER: 'getSummaryTitle',
                                                                            },
                                                                        {
                                                                            PLACEHOLDER_NAME: 'Subtitle',
                                                                            PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                            PLACEHOLDER_GETTER: 'getSummarySubtitle',
                                                                            },

                                                                        {
                                                                            PLACEHOLDER_NAME: 'SummaryTable',
                                                                            PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TABLE,
                                                                            PLACEHOLDER_GETTER: 'getSummaryTable',
                                                                            },

                                ],
                            },

                            'Substance Slide': {
                                LAYOUT_GETTER: 'buildSubstanceSlides',
                                PLACEHOLDER_DEFS: [
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Title',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                        PLACEHOLDER_GETTER: 'getSubstanceTitle',
                                                                    },
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Subtitle',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                        PLACEHOLDER_GETTER: 'getSubstanceSubtitle',
                                                                    },
                                                                    {
                                                                        PLACEHOLDER_NAME: 'MolStructure',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_IMAGE,
                                                                        PLACEHOLDER_GETTER: 'getMolStructure',
                                                                    },
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Table',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TABLE,
                                                                        PLACEHOLDER_GETTER: 'getSubstanceTable',
                                                                    },
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Plots',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_IMAGE,
                                                                        PLACEHOLDER_GETTER: 'getSubstancePlots',
                                                                    },
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Comment',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                        PLACEHOLDER_GETTER: 'getSubstanceComment',
                                                                    },
                                                                    # Footer - pptx footer is not supported as it is in PPTx, therefore is a normal placeholder masked as footer
                                                                    {
                                                                        PLACEHOLDER_NAME: 'Slide Number',
                                                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                                                        PLACEHOLDER_GETTER: 'getSlideNumber',
                                                                        },
                                ],
                            }
                            }

    # Table settings. Add Remove from here. Definitions in the mv module (AnalysisScreen/lib/experimentAnalysis/matching/MatchingVariables.py)

    matchesTableColumnsMap = {
        'Reference Peak Pid'      : {'column': mv.Reference_PeakPid, 'round': None},
        'Binding Score'                : {'column': mv.SpectrumHit_PeakScore, 'round': 2},
        'Matching Score'             : {'column': mv.Reference_PeakMatchScore, 'round': 0},
        'Displacement Score'      : {'column': mv.SpectrumHit_PeakDisplacementScore, 'round': 2},
        'Control S/N'                   : {'column': mv.Control_PeakSNR, 'round': 2},
        'Reference Position (ppm)': {'column': mv.Reference_PeakPosition, 'round': 3},
        'Label'                              : {'column': mv.Reference_Flag_Label, 'round': None},
        'Comment'                       : {'column': mv.Reference_Comment, 'round': None},
        }

    substancesTableColumnsMap = {
        'Index'                              : {'column': mv.Serial, 'round': None},
        'Sample Name'                : {'column': mv.Sample_Name, 'round': None},
        'Substance Name'           : {'column': mv.Reference_SubstanceName, 'round': None},
        'Binding Score'                : {'column': mv.Reference_Score, 'round': 2},
        'Displacement Score'      : {'column': mv.Reference_DisplacementScore, 'round': 2},
        'Matching Score'             : {'column': mv.Reference_MatchScore, 'round': 0},
        'Control S/N'                   :  {'column': mv.Control_Relative_SNR, 'round': 2},
        'Flag'                               : {'column': mv.Reference_Flag_Label, 'round': None},
        }


    # ~~~~~~ Layout Title Slide getter  ~~~~~~~~

    def buildTitleSlide(self, writer, slideLayoutName):
        """
        Build the first Page with title and project summary
        """
        writer._buildPlaceholdersForLayout(slideLayoutName)

    # ~~~~~~ Placeholders Title Slide getters  ~~~~~~~

    def getTitle(self):
        title = 'CcpNmr Screening Report'
        return title

    def getSubtitle(self):
        dataTableName = self.dataHandler.getData('dataTableName', '')
        subtitle = f'{dataTableName} (Project: {self.project.name})'
        return subtitle

    def getOperator(self):
        """ Get the logger user. Not sure if this property is available in the API"""
        text = 'Operator: '
        if self.application is not None:
            regDetails = self.application.getRegistrationDetails()
            name = regDetails.get('name')
            text += name
        return text

    def getDateTime(self):
        from datetime import datetime
        text = 'Date/Time: '
        text += datetime.now().strftime("%d/%m/%y %H-%M-%S")
        return text

    def getDataPaths(self):
        """Get the spectrumGroups data paths"""
        spectrumGroupDataPaths = self.dataHandler.getData(mv.SGDataPaths, {})
        text = 'Data Paths:\n'
        text +=  '\n'.join(f'- {sgName}: {" ".join(sgDataPath)}'
                         for sgName, sgDataPath in spectrumGroupDataPaths.items())
        return text

    def getProgramInfo(self):
        text = 'CcpNmr Version: '
        if self.application is not None:
            text += f' {self.application.applicationVersion}'
        return text

    def getPipelineSettings(self):
        """Get the pipes as text with proper indentation."""
        from textwrap import indent
        text = 'Pipeline Settings:\n'
        pipelineSettingsDict = self.dataHandler.getData(mv._HitAnalysisSourcePipeline, {})
        for pipelineName in pipelineSettingsDict:
            pipelineDict = pipelineSettingsDict[pipelineName]
            for i, (pipeName, pipeSettings) in enumerate(pipelineDict.items()):
                line = f'• {pipeName}:\n'
                innerText = '\n'.join(f'- {key}: {value}' for key, value in pipeSettings.items())
                indentedInnerText = indent(innerText, ' ' * 4)  # Add 4 spaces of indentation
                text += line + indentedInnerText + '\n'
            break # use only the first (if multiple than one, which is unlikely)
        return text

    def getCalculationSettings(self):
        """ Get the Hit Analysis Calculation settings """
        haModuleSettings = self.dataHandler.getData(mv.HitAnalysisSettings, {})
        text = 'Hit Analysis Calculation Settings:\n'
        for i, (calcName, calcSettings) in enumerate(haModuleSettings.items()):
            line = f'• {calcName}: {str(calcSettings)} \n'
            text += line
        return text

    def getTitleComment(self):
        """Stub method for getTitleComment."""
        pass

    # ~~~~~~ Layout Summary Substance Slide getter  ~~~~~~~~

    def buildSubstancesSummarySlides(self, writer, slideLayoutName):
        """
        Build the Substances Summary Slide(s). This will create a slides containing a summary table. Table will be split in multiple pages to ensure readability and fit the slide margins.
        """
        import ccpn.AnalysisScreen.lib.experimentAnalysis.matching.MatchingVariables as mv

        substanceTable = self.dataHandler.getData('substanceTable')
        if substanceTable is None:
            return
        substanceTable[mv.Serial] = range(1, len(substanceTable) + 1)
        # split the data in chunks
        maxRowsKey = 'substances_summary_max_rows_per_table'
        chunkSize = self.settingsHandler.getValue(maxRowsKey, 20)
        chunks = [substanceTable.iloc[i:i + chunkSize] for i in range(0, len(substanceTable), chunkSize)]
        for idx, chunk in enumerate(chunks, 1):
            writer._buildPlaceholdersForLayout(slideLayoutName, slideIndex=idx, totalSummarySlides=len(chunks), substancesTableData=chunk)

    # ~~~~~~ Placeholders Substance Summary Slide getters  ~~~~~~~

    def getSummaryTitle(self, slideIndex, totalSummarySlides, substancesTableData):
        title = 'Substances  Summary'
        return title

    def getSummarySubtitle(self, slideIndex, totalSummarySlides, substancesTableData):
        subtitle = ''
        if totalSummarySlides > 1:
            subtitle = f'Part {slideIndex} of {totalSummarySlides}'
        return subtitle

    def getSummaryTable(self, slideIndex, totalSummarySlides, substancesTableData):

        df = self._formatDataFrameForTable(substancesTableData,  self.substancesTableColumnsMap)
        return df

    # ~~~~~~ Layout Substance Slide getter  ~~~~~~~~

    def buildSubstanceSlides(self, writer, slideLayoutName):
        """
        Build all dedicated Substances Pages in order
        """
        import ccpn.AnalysisScreen.lib.experimentAnalysis.matching.MatchingVariables as mv

        substanceTable = self.dataHandler.getData('substanceTable')
        matchingTable = self.dataHandler.getData('matchingTable')
        if substanceTable is None:
            return

        for i, (tableIndex, substanceTableRow) in enumerate(substanceTable.iterrows()):
            substancePid = substanceTableRow[mv.Reference_SubstancePid]
            matchingTableForSubstance = matchingTable[matchingTable[mv.Reference_SubstancePid] == substancePid]
            writer._buildPlaceholdersForLayout(slideLayoutName, substanceTableIndex=i + 1,
                                        substanceTableRow=substanceTableRow,
                                        matchingTableForSubstance=matchingTableForSubstance)

    # ~~~~~~ Placeholders Substance Slide getters  ~~~~~~~

    def getSubstanceTitle(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Add the title from the Substance"""
        df = matchingTableForSubstance
        sampleName = df[mv.Sample_Name].unique()[-1]
        substanceName = df[mv.Reference_SubstanceName].unique()[-1]
        return f'{substanceName} ({sampleName})'

    def getSubstanceSubtitle(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        substanceBindScore = substanceTableRow[mv.Reference_Score]
        substanceDisplScore = substanceTableRow[mv.Reference_DisplacementScore]
        substanceMatchScore = substanceTableRow[mv.Reference_MatchScore]
        text = f'{substanceTableIndex}) '
        text += f'{mv.Binding} {mv.Score}: {round(substanceBindScore, 2)} -- '
        if substanceDisplScore not in [np.nan, None, np.inf]:
            text += f'{mv.Displacement} {mv.Score}: {round(substanceDisplScore, 2)} -- '
        try:
            text += f'{mv.Matching} {mv.Score}: {int(substanceMatchScore)}'
        except Exception as r:
            text += f'{mv.Matching} {mv.Score}: {substanceMatchScore}'
        return text

    def getMolStructure(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Stub method for getMolStructure."""
        substancePid = self._getSubstancePid(substanceTableRow)
        project = self.project
        su = project.getByPid(substancePid)
        if su is None:
            return
        name = su.name
        smiles = su.smiles
        if not smiles:
            return
        td = fetchDir(self.application._temporaryDirectory.name, self.scratchDirName)
        tempSmilesPath = joinPath(td, f'{name}.png')
        try:
            self._smilesToImage(smiles, tempSmilesPath)
            return tempSmilesPath
        except Exception as err:
            print(f'Error creating Mol from Smiles. {substancePid} - {smiles}. Exit with error: {err}')
        return None

    def getSubstanceTable(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Method to generate the report table with dynamic rounding."""

        df = self._formatDataFrameForTable(matchingTableForSubstance,  self.matchesTableColumnsMap)
        df = df.astype(object) # we need to convert to object to fill nans with ''
        df = df.fillna('')
        # Transpose the DataFrame and reset index
        df = df.T.reset_index(drop=False)
        # The first row values in the transposed DataFrame become the column headers
        df.columns = df.iloc[0]
        df.drop(0, inplace=True)
        return df

    def getSubstanceComment(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Stub method for getReportComment."""
        pass

    def getSubstancePlots(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        plotter = _MatchingPeaksPlotter(self)
        tempPlotPath =  plotter._getSubstancePlots(substanceTableIndex, substanceTableRow, matchingTableForSubstance)
        del plotter
        return tempPlotPath

    # ~~~~~ Footer ~~~~~~~~

    def getSlideNumber(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        include_page_number = self.settingsHandler.getValue('substance_slide_include_page_number', True)
        if include_page_number:
            return f'{substanceTableIndex}'
        return ''

    # ~~~ helper methods ~~~~

    def _getSubstancePid(self, substanceTableRow):
        substancePid = substanceTableRow[mv.Reference_SubstancePid]
        return substancePid

    @staticmethod
    def _formatDataFrameForTable(dataframe, columnMap):
        validColumnMap = {}

        # First, build a valid column map from the matching table
        for newCol, properties in columnMap.items():
            oldCol = properties['column']
            if oldCol in dataframe.columns:
                validColumnMap[newCol] = oldCol
            else:
                warnings.warn(f"Column '{oldCol}' not found in the original DataFrame. Skipping.")

        # Construct the new DataFrame with valid columns
        df = pd.DataFrame({newCol: dataframe[oldCol] for newCol, oldCol in validColumnMap.items()})

        # Apply rounding based on the 'round' values in the columnMap
        for newCol, properties in columnMap.items():
            if properties['round'] is not None and newCol in df.columns:
                if properties['round'] == 0:
                    # Convert to int if round is 0
                    df[newCol] = df[newCol].astype('Int64')  # Using 'Int64' to support NaN values
                else:
                    # Apply rounding
                    df[newCol] = df[newCol].round(properties['round'])

        return df

    @staticmethod
    def _smilesToImage(smiles, path):
        """
        Converts a SMILES string to a PNG image and saves it to disk.
        :param smiles: SMILES string of the molecule.
        :param path: Path to save the PNG file.
        """
        from rdkit import Chem
        from rdkit.Chem import Draw
        molecule = Chem.MolFromSmiles(smiles, sanitize=False)
        if molecule is None:
            return False
        Draw.MolToFile(molecule, path, format='PNG')
        return True



class _MatchingPeaksPlotter():
    """A class that handles the 1D matching peaks region data and plots to a matplotlib plt instance.
     Private and specialised class to the PPTX screening reporter only. """
    _regionDataCache = {}

    def __init__(self, templateMapper):
        self.templateMapper = templateMapper
        self.settingsHandler = self.templateMapper.settingsHandler
        self._regionDataPointsWidth = self.settingsHandler.getValue('region_data_points_width', 100)
        self._maxAxesPerSlide = self.settingsHandler.getValue('max_axes_per_slide', 4)
        self._plotSettings = self.settingsHandler.getValue('plot_settings', {})
        self._showPeakLabels =  self.settingsHandler.getValue(['plot_settings', 'show_peak_labels'], True)
        self._showPeakSymbols =  self.settingsHandler.getValue(['plot_settings', 'show_peak_symbols'], True)
        self._maxAxesPerSlide = self.settingsHandler.getValue('max_axes_per_slide', 4)
        self._loggedDiscarded = set() #j store this info just in case some settings where discarded, so that we log this only once and not for every axis/spectrum etc...


    def _getSubstancePlots(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Generate report plots for a given substance."""
        substancePid = self.templateMapper._getSubstancePid(substanceTableRow)
        dataset = self._getDatasetSubset(matchingTableForSubstance)
        fig, axes = self._initializePlotGrid(len(dataset))

        allPeaks = self._getPeaksFromDataSet(dataset)
        self._setRegionDataCache(allPeaks, self._regionDataPointsWidth)
        globalMin, globalMax = self._getGlobalYPlotLimits(allPeaks)

        for i, (ind, row) in enumerate(dataset.iterrows()):
            self._plotRowData(axes[i], row, globalMin, globalMax)

        self._hideUnusedAxes(axes, len(dataset))
        tempPlotPath = self._saveFigure(fig, substancePid)
        return tempPlotPath


    # --- helper methods for the plotting ---

    def _getDatasetSubset(self, matchingTable):
        """Limit the DataFrame to the maximum number of plots. In otherwords, if there are multiple matches to be plotted, limit the amount to show to a fix number"""
        return matchingTable.head(self._maxAxesPerSlide)

    def _initializePlotGrid(self, numPlots):
        """Create and configure the figure and subplot grid."""
        maxCols = 2
        numCols = min(maxCols, numPlots)
        numRows = (numPlots + numCols - 1) // numCols
        fig, axes = plt.subplots(numRows, numCols, figsize=(3 * numCols, 2 * numRows))

        if numPlots == 1:
            axes = [axes]  # If only one plot, make axes a list
        else:
            axes = axes.flatten()  # Flatten the axes for consistency

        return fig, axes

    def _plotRowData(self, ax, row, globalMin, globalMax):
        """Plot the data for a single row on the given axis."""
        peakPids = row[[mv.Reference_PeakPid, mv.Control_PeakPid, mv.Target_PeakPid, mv.Displacer_PeakPid]].values
        peaks = self.templateMapper.project.getByPids(peakPids)

        for peak in peaks:
            self._plotPeak(ax, peak)

        self._adjustAxisLimits(ax, row, globalMin, globalMax)
        self._customizeAxis(ax)

    def _plotPeak(self, ax, peak):
        """Plot each single 1D peak on the given axis."""
        spectrum = peak.spectrum
        color = spectrum.sliceColour
        x, y = self._regionDataCache.get(peak.pid, ([], []))
        plotSettings = self._plotSettings.get('spectrum_line')
        try: # try just in case some options from the settings file  are not allowed/wrong
            ax.plot(x, y, color=color, label=peak.id, **plotSettings)
        except Exception as err:
            getLogger().debug(f'PPTx report. Plotting error: {err}')


        if self._showPeakSymbols:
            ax.scatter(float(peak.position[0]), float(peak.height), color=color, **self._plotSettings.get('peak_symbol', {}))

        if self._showPeakLabels:
            peakLegendSettings =  self._plotSettings.get('peak_legend_settings', {})
            ax.legend(**peakLegendSettings)

    def _adjustAxisLimits(self, ax, row, globalMin, globalMax):
        """Adjust the Y-axis limits for the plot."""
        if globalMax and globalMin:
            yMinLim, yMaxLim = globalMin * 1.5, globalMax * 1.5

            if row[mv.Control_PeakSNR] is not None and len(ax.figure.axes) == 1:
                controlPeakSN = row[mv.Control_PeakSNR]
                scaling_factor = max(1.0, 1 / controlPeakSN)
                yMinLim *= scaling_factor
                yMaxLim *= scaling_factor

            ax.set_ylim(yMinLim, yMaxLim)

    def _customizeAxis(self, ax):
        """Customize the axis appearance."""
        ax.xaxis.set_major_formatter(FuncFormatter(self._formatPlotXTicks))
        ax.set_yticks([])
        ax.set_yticklabels([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.invert_xaxis()
        ax.tick_params(**self._plotSettings.get('tick_params', {}))
        ax.set_xlabel(**self._plotSettings.get('xlabel', {}))

        for spine in ax.spines.values():
            spine.set_linewidth(self._plotSettings.get('spine_width', 0.2))

    def _hideUnusedAxes(self, axes, numPlots):
        """Hide any unused axes in the plot grid."""
        for ax in axes[numPlots:]:
            ax.set_visible(False)

    def _saveFigure(self, fig, substancePid):
        """Save the figure to a temporary path and close the figure."""
        td = fetchDir(self.templateMapper.application._temporaryDirectory.name, self.templateMapper.scratchDirName)
        tempPlotPath = joinPath(td, f'{substancePid}-plot.png')
        fig.savefig(tempPlotPath, dpi=300, bbox_inches='tight', format='png')
        plt.close(fig)
        return tempPlotPath

    @staticmethod
    def _formatPlotXTicks(value, _):
        """  Ensure plain style, no scientific notation. 2 decimal places for the ppm scale"""
        return f'{value:.2f}'

    ## ---- Region Data helpers ---- ##

    def _setRegionDataCache(self, peaks, extraPointLimit=25):
        peaksRegionData = self._getRegionDatafFor1DPeaks(peaks, extraPointLimit)
        self._regionDataCache.update(peaksRegionData)

    def _getRegionDatafFor1DPeaks(self, peaks, extraPointLimit=25):
        peaksRegionData = {}
        for peak in peaks:
            spectrum = peak.spectrum
            axisCode = spectrum.axisCodes[-1]  #we assume we are working with 1D only for screening
            peakPointPosition = int(peak.pointPositions[-1])
            pointLimits = peakPointPosition - extraPointLimit, peakPointPosition + extraPointLimit
            pointsRange = abs(pointLimits[1] - pointLimits[0]) + 1
            ppmLimits = [spectrum.point2ppm(pointLimit, axisCode) for pointLimit in pointLimits]
            regionData = spectrum.getRegion(**{axisCode: ppmLimits})
            regionData *= spectrum.scale
            ppmRange = np.linspace(*ppmLimits, pointsRange)
            peaksRegionData[peak.pid] = (ppmRange, regionData)
        return peaksRegionData

    def _getPeaksFromDataSet(self, dataset):
        allPeaks = []
        for i, (ind, row) in enumerate(dataset.iterrows()):
            peakPids = row[[mv.Reference_PeakPid, mv.Control_PeakPid, mv.Target_PeakPid, mv.Displacer_PeakPid]].values
            peaks = self.templateMapper.project.getByPids(peakPids)
            allPeaks.extend([pk for pk in peaks if pk is not None])
        return allPeaks

    def _getGlobalYPlotLimits(self, peaks):
        """Get the lowest and highest point in the region data, needed for scaling the Y limits in the plot, so that a only-noise region is not over-represented as a real signal.  """
        arrays = [self._regionDataCache.get(peak.pid, ([], []))[1] for peak in peaks]
        flattened = np.concatenate(arrays)
        if len(flattened) > 0:
            globalMin = flattened.min()
            globalMax = flattened.max()
            return globalMin, globalMax
        return -np.inf, np.inf
