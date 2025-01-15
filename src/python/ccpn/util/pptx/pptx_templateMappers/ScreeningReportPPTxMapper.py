import warnings
import numpy as np
from matplotlib.ticker import FuncFormatter
from ccpn.util.Path import fetchDir, joinPath
import ccpn.AnalysisScreen.lib.experimentAnalysis.matching.MatchingVariables as mv
from ccpn.util.pptx.PPTxTemplateABC import PPTxTemplateMapperABC
from ccpn.util.pptx.PPTxWriter import *


class ScreeningReportTemplateMapper(PPTxTemplateMapperABC):
    """
     slideMapping = {
                                'Title Slide':   <-- Slide master layout slide Name. Defined in the actual PPTx file
                                [
                                    {
                                        PLACEHOLDER_NAME: ' Any name',                                       <--  Slide master Placeholder Name. Defined in the actual PPTx file from the Selection Panel options
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,         <-- The Placeholder type created in the PPTx file. E.g.: Text, Image, Table
                                        PLACEHOLDER_GETTER: 'getMethod',                                 <-- The method name defined in this  .py file and needed to get the value to be filled in the Placeholder
                                    },
                                ]


    """

    templateResourcesFileName = 'Screening_report_template.pptx'
    templateName = 'Screening PPTx Report'
    scratchDirName = 'screenReport' # the directory name created inside the ccpn temporary directory. And Cleared up after the report is generated
    slideMapping = {
                                'Title Slide': [
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
                                'Report Slide': [
                                    {
                                        PLACEHOLDER_NAME: 'Title',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                        PLACEHOLDER_GETTER: 'getReportTitle',
                                    },
                                    {
                                        PLACEHOLDER_NAME: 'Subtitle',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                        PLACEHOLDER_GETTER: 'getReportSubtitle',
                                    },
                                    {
                                        PLACEHOLDER_NAME: 'MolStructure',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_IMAGE,
                                        PLACEHOLDER_GETTER: 'getMolStructure',
                                    },
                                    {
                                        PLACEHOLDER_NAME: 'Table',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TABLE,
                                        PLACEHOLDER_GETTER: 'getReportTable',
                                    },
                                    {
                                        PLACEHOLDER_NAME: 'Plots',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_IMAGE,
                                        PLACEHOLDER_GETTER: 'getReportPlots',
                                    },
                                    {
                                        PLACEHOLDER_NAME: 'Comment',
                                        PLACEHOLDER_TYPE: PLACEHOLDER_TYPE_TEXT,
                                        PLACEHOLDER_GETTER: 'getReportComment',
                                    },
                                ],
                            }

    # Table settings

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

    def setData(self, **kwargs):
        self.dataTableName = kwargs.get('dataTableName', '')
        self._hitAnalysisSourcePipeline = kwargs.get(mv._HitAnalysisSourcePipeline, {})
        self._spectrumGroupDataPaths = kwargs.get(mv.SGDataPaths, {})
        if self._hitAnalysisSourcePipeline:
            self._pipelineRunName = next(iter(self._hitAnalysisSourcePipeline), None)
            if self._pipelineRunName:
                self.pipelineSettingsDict = self._hitAnalysisSourcePipeline.get(self._pipelineRunName, {})
            else:
                self.pipelineSettingsDict = {}
        self._haModuleSettings = kwargs.get(mv.HitAnalysisSettings, {})

    # ~~~~~~ slideMapping getters ~~~~~~~~

    def getTitle(self):
        title = 'CcpNmr Screening Report'
        return title

    def getSubtitle(self):
        subtitle = f'{self.dataTableName} (Project: {self.project.name})'
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
        text = 'Data Paths:\n'
        text +=  '\n'.join(f'- {sgName}: {" ".join(sgDataPath)}'
                         for sgName, sgDataPath in self._spectrumGroupDataPaths.items())
        return text

    def getProgramInfo(self):
        text = 'CcpNmr Version: '
        if self.application is not None:
            # text += f' {self.application.applicationName}'
            text += f' {self.application.applicationVersion}'
        return text

    def getPipelineSettings(self):
        """Get the pipes as text with proper indentation."""
        from textwrap import indent
        text = 'Pipeline Settings:\n'
        for i, (pipeName, pipeSettings) in enumerate(self.pipelineSettingsDict.items()):
            line = f'• {pipeName}:\n'
            innerText = '\n'.join(f'- {key}: {value}' for key, value in pipeSettings.items())
            indentedInnerText = indent(innerText, ' ' * 4)  # Add 4 spaces of indentation
            text += line + indentedInnerText + '\n'
        return text

    def getCalculationSettings(self):
        """ Get the Hit Analysis Calculation settings """
        text = 'Hit Analysis Calculation Settings:\n'
        for i, (calcName, calcSettings) in enumerate(self._haModuleSettings.items()):
            line = f'• {calcName}: {str(calcSettings)} \n'
            text += line
        return text

    def getTitleComment(self):
        """Stub method for getTitleComment."""
        pass

    def getReportTitle(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Add the title from the Substance"""
        df = matchingTableForSubstance
        sampleName = df[mv.Sample_Name].unique()[-1]
        substanceName = df[mv.Reference_SubstanceName].unique()[-1]
        return f'{substanceName} ({sampleName})'

    def getReportSubtitle(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Stub method for getReportSubtitle."""
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

    def getReportTable(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Method to generate the report table with dynamic rounding."""
        columnMap = self.matchesTableColumnsMap
        validColumnMap = {}

        # First, build a valid column map from the matching table
        for newCol, properties in columnMap.items():
            oldCol = properties['column']
            if oldCol in matchingTableForSubstance.columns:
                validColumnMap[newCol] = oldCol
            else:
                warnings.warn(f"Column '{oldCol}' not found in the original DataFrame. Skipping.")

        # Construct the new DataFrame with valid columns
        df = pd.DataFrame({newCol: matchingTableForSubstance[oldCol] for newCol, oldCol in validColumnMap.items()})

        # Apply rounding based on the 'round' values in the columnMap
        for newCol, properties in columnMap.items():
            if properties['round'] is not None and newCol in df.columns:
                if properties['round'] == 0:
                    # Convert to int if round is 0
                    df[newCol] = df[newCol].astype('Int64')  # Using 'Int64' to support NaN values
                else:
                    # Apply rounding
                    df[newCol] = df[newCol].round(properties['round'])

        # Fill NaN values with empty strings
        df = df.fillna('')

        # Transpose the DataFrame and reset index
        df = df.T.reset_index(drop=False)

        # The first row values in the transposed DataFrame become the column headers
        df.columns = df.iloc[0]
        df.drop(0, inplace=True)

        return df

    def getReportComment(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Stub method for getReportComment."""
        pass

    def getReportPlots(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        plotter = _MatchingPeaksPlotter(self)
        tempPlotPath =  plotter._getReportPlots(substanceTableIndex, substanceTableRow, matchingTableForSubstance)
        del plotter
        return tempPlotPath

    # ~~~ helper methods ~~~~

    def _getSubstancePid(self, substanceTableRow):
        substancePid = substanceTableRow[mv.Reference_SubstancePid]
        return substancePid

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

    # Plot settings
    PLOT_SETTINGS = {
                                        "font"       : {
                                            "family": "Helvetica",
                                            "size"  : 6,
                                            },
                                        "spectrum_line"       : {
                                            "linewidth": 0.5,
                                            },
                                        "label_line": { # peak labels
                                            "linewidth": 0.5,
                                            "linestyle": "dotted",
                                            },
                                        "label"      : {
                                            "fontsize": 4,
                                            "rotation": 0,
                                            "x_offset(ppm)": 0.2,
                                            "ha"      : "left",
                                            "va"      : "bottom",
                                            },
                                        "tick_params": {
                                            "axis"     : "x",
                                            "labelsize": 4,
                                            "width"    : 0.5,
                                            },
                                        "xlabel"     : {
                                            "fontsize": 4,
                                            "ha"      : "right",
                                            "x"       : 1.0,
                                            "labelpad": -15,
                                            },
                                        "peak_symbol": {
                                            "marker": 'x',
                                            "s"      : 10, # size
                                            "alpha" : 0.8,
                                            "linewidths":0.3,
                                            },
                                        "spine_width": 0.2,
                                        "dpi"        : 300,
                                        "format"     : "png",
                                        }

    REGION_DATA_WIDTH_IN_POINTS = 100 # take this value to crop the data left-right of a peak point position and determine the plotting area
    ADD_PEAK_LABELS = True
    ADD_PEAK_SYMBOLS =True
    _regionDataCache = {}

    def __init__(self, templateMapper):
        self.templateMapper = templateMapper


    def _getReportPlots(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Generate report plots for a given substance."""
        substancePid = self.templateMapper._getSubstancePid(substanceTableRow)
        dataset = self._getDatasetSubset(matchingTableForSubstance)
        fig, axes = self._initializePlotGrid(len(dataset))

        allPeaks = self._getPeaksFromDataSet(dataset)
        self._setRegionDataCache(allPeaks, self.REGION_DATA_WIDTH_IN_POINTS)
        globalMin, globalMax = self._getGlobalYPlotLimits(allPeaks)

        for i, (ind, row) in enumerate(dataset.iterrows()):
            self._plotRowData(axes[i], row, globalMin, globalMax)

        self._hideUnusedAxes(axes, len(dataset))
        tempPlotPath = self._saveFigure(fig, substancePid)
        return tempPlotPath


    # --- helper methods for the plotting ---

    def _getDatasetSubset(self, matchingTable):
        """Limit the DataFrame to the maximum number of plots."""
        maxPlots = 4  # Max rows * max columns (2x2)
        return matchingTable.head(maxPlots)

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

        ax.plot(x, y, color=color, label=peak.id, **self.PLOT_SETTINGS["spectrum_line"])

        if self.ADD_PEAK_SYMBOLS:
            ax.scatter(float(peak.position[0]), float(peak.height), color=color, **self.PLOT_SETTINGS["peak_symbol"])

        if self.ADD_PEAK_LABELS:
            ax.legend(loc=1, fontsize=4, ncol=1, numpoints=3, frameon=False)

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
        ax.tick_params(**self.PLOT_SETTINGS["tick_params"])
        ax.set_xlabel("[ppm]", **self.PLOT_SETTINGS["xlabel"])

        for spine in ax.spines.values():
            spine.set_linewidth(self.PLOT_SETTINGS["spine_width"])

    def _hideUnusedAxes(self, axes, numPlots):
        """Hide any unused axes in the plot grid."""
        for ax in axes[numPlots:]:
            ax.set_visible(False)

    def _saveFigure(self, fig, substancePid):
        """Save the figure to a temporary path and close the figure."""
        td = fetchDir(self.templateMapper.application._temporaryDirectory.name, self.templateMapper.scratchDirName)
        tempPlotPath = joinPath(td, f'{substancePid}-plot.png')
        fig.savefig(tempPlotPath, dpi=300, bbox_inches='tight', format="png")
        plt.close(fig)
        return tempPlotPath

    @staticmethod
    def _formatPlotXTicks(value, _):
        """  Ensure plain style, no scientific notation. 2 decimal places for the ppm scale"""
        return f"{value:.2f}"

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