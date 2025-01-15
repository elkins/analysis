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

    templateRelativePath = 'Screening_report_template.pptx'
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

    # ---------- The following methods are called from the PPTxWriter -------

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

    def _getSubstancePid(self, substanceTableRow):
        substancePid = substanceTableRow[mv.Reference_SubstancePid]
        return substancePid

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

    @staticmethod
    def _setRegionDataCache(peaks, extraPointLimit=25):
        peaksRegionData = ScreeningReportTemplateMapper.getRegionDatafForPeaks(peaks, extraPointLimit)
        ScreeningReportTemplateMapper._regionDataCache.update(peaksRegionData)

    @staticmethod
    def getRegionDatafForPeaks(peaks, extraPointLimit=25):
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
            peaks = [self.project.getByPid(pid) for pid in peakPids]
            allPeaks.extend([pk for pk in peaks if pk is not None])
        return allPeaks

    def _getGlobalYPlotLimits(self, peaks):
        """Get the lowest and highest point in the region data, needed for scaling the Y limits in the plot, so that a only-noise region is not over-represented as a real signal.  """
        arrays = [self._regionDataCache.get(peak.pid, ([], [])) [1] for peak in peaks]
        flattened = np.concatenate(arrays)
        if len(flattened)>0:
            globalMin = flattened.min()
            globalMax = flattened.max()
            return globalMin, globalMax
        return -np.inf, np.inf

    def getReportPlots(self, substanceTableIndex, substanceTableRow, matchingTableForSubstance):
        """Stub method for getReportPlots."""
        substancePid = self._getSubstancePid(substanceTableRow)
        imageAspectRatio = (3, 2) # 3:2
        # Define the maximum rows and columns
        maxRows = 2
        maxCols = 2
        maxPlots = maxRows * maxCols

        # Limit the DataFrame to the first 'maxPlots' rows
        dataset = matchingTableForSubstance.head(maxPlots)

        # Calculate the number of rows and columns dynamically
        numPlots = len(dataset)
        if numPlots <= maxCols:
            numRows, numCols = 1, numPlots  # Single row if plots fit in one row
        else:
            numCols = min(maxCols, numPlots)  # Cap columns at maxCols
            numRows = (numPlots + numCols - 1) // numCols  # Calculate rows needed

        plt.close('all')
        # Create the figure and subplots
        fig, axes = plt.subplots(numRows, numCols, figsize=(imageAspectRatio[0] * numCols, imageAspectRatio[1] * numRows))

        # Flatten axes for consistent handling, even if there's only one subplot
        if numPlots == 1:
            axes = [axes]  # Single axis as a list
        else:
            axes = axes.flatten()

        allPeaks = self._getPeaksFromDataSet(dataset)
        self._setRegionDataCache(allPeaks, self.REGION_DATA_WIDTH_IN_POINTS)
        globalMin, globalMax = self._getGlobalYPlotLimits(allPeaks)
        for i, (ind, row) in enumerate(dataset.iterrows()):
            ax = axes[i]
            peakPids = row[[mv.Reference_PeakPid, mv.Control_PeakPid, mv.Target_PeakPid, mv.Displacer_PeakPid]].values
            peaks = [self.project.getByPid(pid) for pid in peakPids]
            peaks = [pk for pk in peaks if pk is not None]

            # Loop through sorted peaks and plot
            for ii, peak in enumerate(peaks):
                spectrum = peak.spectrum
                color = spectrum.sliceColour
                x, y = self._regionDataCache.get(peak.pid, ([], []))

                # Plot the peak data
                ax.plot(x, y,
                        color=color,
                        label=peak.id,
                        **self.PLOT_SETTINGS["spectrum_line"])

                if self.ADD_PEAK_SYMBOLS:
                    # add peak symbol
                    ax.scatter(float(peak.position[0]), float(peak.height),
                            color=color,
                            **self.PLOT_SETTINGS["peak_symbol"])
                if self.ADD_PEAK_LABELS:
                    ax.legend(loc=1, fontsize=4, ncol=1, numpoints=3, frameon=False)

            # Force x-axis to use full tick values
            # Apply the custom formatter to the x-axis # Ensure plain style, no scientific notation
            ax.xaxis.set_major_formatter(FuncFormatter(self._formatPlotXTicks))
            if globalMax and globalMin:
                snr_threshold = 1
                yMinLim = globalMin*1.5
                yMaxLim = globalMax * 1.5
                # scale by control S/N but only if there is one axis in one slide.
                if len(axes)==1: #apply additional scaling based on the S/N Otherwise if is only noise region will look over-represented compared to other slides,
                    controlPeakSN = row[mv.Control_PeakSNR]
                    if controlPeakSN is not None:
                        scaling_factor = max(1.0, snr_threshold / controlPeakSN)  # Ensure it's at least 1.0
                        yMinLim *= scaling_factor
                        yMaxLim *= scaling_factor
                ax.set_ylim(yMinLim, yMaxLim)  # Set the same Y-limits for all curves

            # Remove the y-axis
            ax.set_yticks([])  # Removes the ticks from the y-axis
            ax.set_yticklabels([])  # Removes the labels from the y-axis
            # Remove the top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)

            # Invert the x-axis
            ax.invert_xaxis()
            ax.tick_params(**self.PLOT_SETTINGS["tick_params"])
            ax.set_xlabel("[ppm]", **self.PLOT_SETTINGS["xlabel"])
            for spine in ax.spines.values():
                spine.set_linewidth(self.PLOT_SETTINGS["spine_width"])

        # Hide unused axes
        for j in range(len(dataset), len(axes)):
            axes[j].set_visible(False)

        td = fetchDir(self.application._temporaryDirectory.name, self.scratchDirName)
        tempPlotPath = joinPath(td, f'{substancePid}-plot.png')

        fig.savefig(tempPlotPath, dpi=300, bbox_inches='tight', format="png")
        plt.close(fig)
        return tempPlotPath

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

    @staticmethod
    def _formatPlotXTicks(value, _):
        """  Ensure plain style, no scientific notation. 2 decimal places for the ppm scale"""
        return f"{value:.2f}"
