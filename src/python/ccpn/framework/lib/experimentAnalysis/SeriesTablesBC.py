"""
This module defines base classes for Series Analysis
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-07 09:51:01 +0000 (Tue, November 07, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import math
import numbers
import typing
import numpy as np
import pandas as pd
from collections import OrderedDict as od
from collections import defaultdict
from ccpn.core.DataTable import TableFrame
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.util.Common import flattenLists
from ccpn.core.Peak import Peak
from ccpn.util.Sorting import isListAscending

class SeriesFrameBC(TableFrame):
    """
    A TableData used for the Series ExperimentsAnalysis, such as ChemicalShiftMapping or Relaxation I/O.
    Columns names are divided in following groups assignmentProperties, spectrumProperties, peakProperties.
    """
    SERIESFRAMENAME     = ''
    SERIESFRAMETYPE     = ''
    _rawDataHeaders     = []

    def getRowByUID(self, uid):
        self.set_index(sv._ROW_UID, inplace=True, drop=False)
        if uid in self.index:
            return self.loc[uid]

    def _buildColumnHeaders(self):
        pass

    def loadFromFile(self, filePath, *args, **kwargs):
        pass

    @staticmethod
    def _getAtomNamesFromGroupedByHeaders(groupedDf):
        """
        join the atom names from different rows in a list
        :param groupedDf: groupedBy object
        """
        nmrAtomNames = groupedDf[sv.AssignmentPropertiesHeaders].groupby(
            sv.GROUPBYAssignmentHeaders)[sv.NMRATOMNAME].unique().transform(
            lambda x: ','.join(x)).values
        return nmrAtomNames

    def _joinTwoColumnsAsStr(self, columnName1:str=None, columnName2:str=None, newColumName:str=None, separator='-'):
        """
        Create a new column by joining values from existing columns. Keep all, don't drop columns. In-place operation.
        :return: self with a new column (if successful)
        """

        self[newColumName] = self[columnName1].astype(str) + separator + self[columnName2].astype(str)
        return self

    def joinNmrResidueCodeType(self):
        """ Merge the nmrResidue SequenceCode and ResidueType columns in a new colum (NMRRESIDUECODETYPE)"""
        ## convert the sequenceCode to str. This because pandas Automatically tries to make floats.!!
        if not sv.NMRRESIDUECODE in self.columns:
            return
        self[sv.NMRRESIDUECODE] = self[sv.NMRRESIDUECODE].astype(str).apply(lambda x: x.replace('.0', ''))
        self._joinTwoColumnsAsStr(sv.NMRRESIDUECODE, sv.NMRRESIDUETYPE, newColumName=sv.NMRRESIDUECODETYPE, separator='-')


class InputSeriesFrameBC(SeriesFrameBC):
    """
    A TableData used for the Series ExperimentsAnalysis, such as ChemicalShiftMapping or Relaxation I/O.
    Columns names are divided in following groups assignmentProperties, spectrumProperties, peakProperties.

    ## --------- Columns definitions --------- ##
        - _UID                  : str,   value mandatory. Unique string used to index the DataFrame.

        - spectrumProperties group:
            - dimension         : int,   value mandatory
            - isotopeCode       : str,   value mandatory
            - seriesStep        : float, value mandatory
            - seriesUnit        : str,   value mandatory

        - peakProperties group:
            - collectionId      : int,   value mandatory
            - height            : float, value mandatory
            - ppmPosition       : float, value mandatory
            - lineWidth         : float, value optional
            - volume            : float, value optional

        - assignmentProperties group:
            - nmrChainCode      : str,   value optional
            - nmrResidueCode    : str,   value optional
            - nmrResidueType    : str,   value optional
            - nmrAtomName       : str,   value optional

        - pids group: all optional.  If available, changes to core objects may dynamically update the Data
            - spectrumPid       : str,   value optional
            - peakPid           : str,   value optional
            - nmrAtomPid        : str,   value optional
            - nmrResiduePid     : str,   value optional
            - peakCollectionPid : str,   value optional

    """

    SERIESFRAMENAME     = sv.SERIESANALYSISINPUTDATA
    SERIESFRAMETYPE     = sv.SERIESANALYSISINPUTDATA

    _spectrumPropertiesHeaders      = []
    _peakPropertiesHeaders          = []
    _assignmentPropertiesHeaders    = []
    _pidHeaders                     = []

    @property
    def assignmentHeaders(self):
        """
        the list of column Headers for the assignment values.
        Can be used to filter the Table to get a new table with only the values of interest and index.
        e.g.:  df[df.assignmentHeaders]
        :return: list of str
        """
        return self._assignmentPropertiesHeaders

    @property
    def peakPropertiesHeaders(self):
        """
        the list of column Headers for the peakProperties values.
        Can be used to filter the Table to get a new table with only the values of interest and index.
        :return: list of str
        """
        return self._peakPropertiesHeaders

    @property
    def spectrumPropertiesHeaders(self):
        """
        the list of column Headers for the spectrumProperties values.
        Can be used to filter the Table to get a new table with only the values of interest and index.
        :return: list of str
        """
        return self._spectrumPropertiesHeaders

    @property
    def pidHeaders(self):
        """
        the list of column Headers for the pid values.
        :return: list of str
        """
        return self._pidHeaders

    def _buildColumnHeaders(self):
        """
        Set the Column Headers and order of appearance in the dataframe.
        :return: None
        """
        self._spectrumPropertiesHeaders = sv.SpectrumPropertiesHeaders
        self._peakPropertiesHeaders = sv.PeakPropertiesHeaders
        self._assignmentPropertiesHeaders = sv.AssignmentPropertiesHeaders
        self._pidHeaders = sv.PidHeaders
        columns = self._spectrumPropertiesHeaders   + \
                  self._peakPropertiesHeaders       + \
                  self._assignmentPropertiesHeaders + \
                  self._pidHeaders
        self.loc[-1, columns] = None # None value, because you must give a value when creating columns after init.
        self.dropna(inplace=True)    # remove  None values that were created as a temporary spaceHolder

    @staticmethod
    def _getCollectionDict4SpectrumGroup(spectrumGroup, parentCollection=None):
        """
        Internal.
        Build a collection dict applying several filter of interest.
            - Filter collections which are subset of the parentCollection if parentCollection is given,
              else skip.
            - Filter peaks in the collection Items if their spectra are in the given spectrumGroup argument
            - Note, you cannot simply use peak.collections (which is also extremely slow)
        :param spectrumGroup:
        :param parentCollection: Collection or None, the inputCollection in the backendHandler. Top collection containing subsets of peakCollections
        :return: dict {peak:[collection,...]}
        """
        collectionDict = defaultdict(list)
        if parentCollection is not None:
            parentCollectionItems = parentCollection.items
        else:
            getLogger().warning('Parent Collection not found. Skipping... ')
            parentCollectionItems = []
        for subCollection in parentCollectionItems:
            for item in subCollection.items:
                if isinstance(item, Peak):
                    if item.spectrum in spectrumGroup.spectra:
                        collectionDict[item].append(subCollection)
        return collectionDict

    def buildFromSpectrumGroup(self, spectrumGroup, parentCollection=None, peakListIndices=None, filteredPeaks=None,
                               experimentName=None):
        """
        :param spectrumGroup: A core object containg the spectra and series information
        :param peakListIndices: list of int, same length of spectra. Define which peakList index to use.
                               If None, use -1 (last created) as default for all spectra
        :param filteredPeaks: Use only this subset of peaks. Used when a peak has changed, to avoid rebuild all.
        :return: None
        """
        self.clear()
        # build the frame
        if self.columns.empty:
            self._buildColumnHeaders()
        spectra = spectrumGroup.spectra
        if peakListIndices is None or len(peakListIndices) != len(spectra):
            peakListIndices = [-1] * len(spectra)
        collectionDict = InputSeriesFrameBC._getCollectionDict4SpectrumGroup(spectrumGroup,
                                                                             parentCollection=parentCollection)
        # isSeriesAscending = isListAscending(spectrumGroup.series)
        i = 1
        while True: ## This because we don't know how many rows we need
            for spectrum, peakListIndex in zip(spectra, peakListIndices):
                if filteredPeaks is not None:
                    peaks = [pk for pk in spectrum.peakLists[peakListIndex].peaks if pk in filteredPeaks]
                else:
                    peaks = spectrum.peakLists[peakListIndex].peaks
                for pk in peaks:
                    if not pk in collectionDict:
                        continue
                    for dimension in spectrum.dimensions:
                        try:
                            ## set the unique UID
                            self.loc[i, sv._ROW_UID] = i
                            ## build the spectrum Property Columns
                            self.loc[i, sv.DIMENSION] = dimension
                            self.loc[i, sv.ISOTOPECODE] = spectrum.getByDimensions(sv.ISOTOPECODES, [dimension])[0]
                            self.loc[i, sv.SERIES_STEP_X] = spectrum.getSeriesItem(spectrumGroup)
                            self.loc[i, sv.SERIES_STEP_Y] = pk.height  # default
                            self.loc[i, sv.SERIESUNIT] = spectrumGroup.seriesUnits
                            self.loc[i, sv.SPECTRUMPID] = spectrum.pid
                            self.loc[i, sv.EXPERIMENT] = experimentName
                            ## build the peak Property Columns
                            collections = collectionDict.get(pk, [])
                            for collection in collections:
                                self.loc[i, sv.COLLECTIONID] = collection.uniqueId
                                self.loc[i, sv.COLLECTIONPID] = collection.pid
                            for peakProperty in [sv._HEIGHT, sv._VOLUME, sv._SNR]:
                                self.loc[i, peakProperty] = getattr(pk, peakProperty, None)
                            self.loc[i, sv._PPMPOSITION] = pk.getByDimensions(sv._PPMPOSITIONS, [dimension])[0]
                            self.loc[i, sv._LINEWIDTH] = pk.getByDimensions(sv._LINEWIDTHS, [dimension])[0]
                            self.loc[i, sv.PEAKPID] = pk.pid
                            ## build the assignment Property Columns
                            assignedNmrAtoms = flattenLists(pk.getByDimensions(sv.ASSIGNEDNMRATOMS, [dimension]))
                            for nmrAtom in assignedNmrAtoms:
                                self.loc[i, sv.NMRCHAINNAME] = nmrAtom.nmrResidue.nmrChain.name
                                self.loc[i, sv.NMRRESIDUECODE] = nmrAtom.nmrResidue.sequenceCode
                                self.loc[i, sv.NMRRESIDUETYPE] = nmrAtom.nmrResidue.residueType
                                self.loc[i, sv.NMRATOMNAME] = nmrAtom.name
                                self.loc[i, sv.NMRATOMPID] = nmrAtom.pid
                                self.loc[i, sv.NMRRESIDUEPID] = nmrAtom.nmrResidue.pid
                            # for excludedFlag in sv.EXCLUDED_OBJECTS:
                            #     self.loc[i, excludedFlag] = False
                            i += 1
                        except Exception as e:
                            getLogger().warn(f'Cannot add row {i} for peak {pk.pid}. Skipping with error: {e}')
            break

        # self.loc[self.index, sv._isSeriesAscending] = isSeriesAscending


########################################################################################################################
################################           Relaxation I/O  Series Output Table                 #########################
########################################################################################################################

class RelaxationOutputFrame(SeriesFrameBC):
    SERIESFRAMETYPE = sv.RELAXATION_OUTPUT_FRAME


class HetNoeOutputFrame(SeriesFrameBC):

    """
    A TableData used for the HetNoe Series Analysis,
    Mandatory Column names are:
        ## --------- Columns definitions --------- ##
        # Group with various identifiers as the main RelaxationOutputFrame

        # Group with calculation/calculated values
        - seriesUnit        : str,
        - seriesStep        : float,
        - seriesStepValue   : float,
        - value             : float,
        - value_err         : float,

    """

    SERIESFRAMENAME = sv.HetNoe_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.HetNoe_OUTPUT_FRAME


class ETAOutputFrame(SeriesFrameBC):

    """
    A TableData used to store the Data(frame) valid for the CrossCorrelation analysis.
    Note. This is created using two inputDataTables. See the "ETACalculation" Model

    Mandatory Column names are:
        ## --------- Columns definitions --------- ##
        # Group with calculation/calculated values
        - seriesUnit        : str,
        - seriesStep        : float,
        - seriesStepValue   : float,
        - value             : float,
        - value_err         : float,

    """

    SERIESFRAMENAME = sv.CROSSCORRELRATIO_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.CROSSCORRELRATIO_OUTPUT_FRAME

class RexETAOutputFrame(SeriesFrameBC):

    """
    A TableData used to store the Data(frame) valid for the Rex via Trosy Etas analysis.
    Note. This is created using two inputDataTables. See the "ETACalculation" Model

    Mandatory Column names are:
        ## --------- Columns definitions --------- ##
        # Group with calculation/calculated values
        - seriesUnit        : str,
        - seriesStep        : float,
        - seriesStepValue   : float,
        - value             : float,
        - value_err         : float,

    """

    SERIESFRAMENAME = sv.REXVIATROSY_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.REXVIATROSY_OUTPUT_FRAME

class R2R1OutputFrame(SeriesFrameBC):

    """
    A TableData used for the R2R1 Series Analysis,

    """

    SERIESFRAMENAME = sv.R2R1_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.R2R1_OUTPUT_FRAME


class RSDMOutputFrame(SeriesFrameBC):

    """
    A TableData used for the RSDM Series Analysis,

    """

    SERIESFRAMENAME = sv.RSDM_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.RSDM_OUTPUT_FRAME

########################################################################################################################
################################   Chemical Shift Mapping  I/O Series Output Table      ################################
########################################################################################################################

class CSMOutputFrame(SeriesFrameBC):

    """
    A TableData used for the CSM Series Analysis,
    Mandatory Column names are:
        ## --------- Columns definitions --------- ##
        # Group with various identifiers etc
        - _UID              : int,
        - nmrChainName      : str,
        - nmrResidueCode    : str,
        - nmrResidueType    : str,
        - nmrAtomNames      : list,
        - collectionId      : int,
        - collectionPid     : str,
        - peakPid           : str,
        - nmrResiduePid     : str,
        # Group with calculation/calculated values
        - seriesUnit        : str,
        - seriesStep        : float,
        - seriesStepValue   : float,
        - deltaDelta        : float,
        - deltaDelta_err    : float,
        - kd                : float,
        - kd_err            : float,
        - bMax              : float,
        - bMax_err          : float,
        # Group with statistical fitting results
        - R2               : float,
        - Chi-square       : float,
        - Red-Chi-square   : float,
        - Akaike           : float,
        - Bayesian         : float,
        - Method           : str, the minimiser method used for fitting. e.g.: 'leastsq'
        - Model            : str, the minimiser model used for fitting.  e.g.: '1BindingSite'
    """

    SERIESFRAMENAME = sv.CSM_OUTPUT_FRAME
    SERIESFRAMETYPE = sv.CSM_OUTPUT_FRAME

    def _buildColumnHeaders(self):
        """
        Set the Column Headers and order of appearance in the dataframe.
        :return: None
        """
        columns = [
                    sv._ROW_UID,
                    sv.COLLECTIONID,
                    sv.COLLECTIONPID,
                    sv.NMRRESIDUEPID,
                    sv.PEAKPID,
                    sv.NMRCHAINNAME,
                    sv.NMRRESIDUECODE,
                    sv.NMRRESIDUETYPE,
                    sv.NMRATOMNAMES,
                    sv.SERIESUNIT,
                    sv.SERIES_STEP_X,
                    sv.SERIES_STEP_Y,
                    sv.DELTA_DELTA,
                    sv.KD,
                    sv.KD_ERR,
                    sv.BMAX,
                    sv.BMAX_ERR,
                  ]
        columns += sv.CONSTANT_STATS_OUTPUT_TABLE_COLUMNS
        self.loc[-1, columns] = None # None value, because you must give a value when creating columns after init.
        self.dropna(inplace=True)    # remove  None values that were created as a temporary spaceHolder

########################################################################################################################
##################################        Private Library  functions                 ###################################
########################################################################################################################


def _mergeRowsByHeaders(inputData, grouppingHeaders, dropColumnNames=[sv.NMRATOMNAME],
                        rebuildUID=True, pidShortClass='NR', keep="first", ):
    """
    Merge rows by common columns.
    grouppingHeaders:  sequence of columnNames to consider for identifying duplicate rows.

    """
    from ccpn.core.lib.Pid import createPid

    newIDs =[]
    if rebuildUID:
        for assignmentValues, grouppedDF in inputData.groupby(grouppingHeaders):        ## Group by grouppingHeaders
            newUid = grouppedDF[grouppingHeaders].values[0].astype('str')
            newIDs.append(createPid(pidShortClass, *newUid))                            ## Recreate the UID
    inputData.drop_duplicates(subset=grouppingHeaders, keep=keep, inplace=True)
    inputData.drop(columns=dropColumnNames, inplace=True)
    if rebuildUID and len(inputData.index) == len(newIDs):
        inputData[sv._ROW_UID] = newIDs
    return inputData


INPUT_SERIESFRAME_DICT = {
                    InputSeriesFrameBC.SERIESFRAMETYPE: InputSeriesFrameBC
                    }

OUTPUT_SERIESFRAMES_DICT = {
                              sv.CSM_OUTPUT_FRAME: CSMOutputFrame,
                            }



ALL_SERIES_DATA_TYPES = {
                        **INPUT_SERIESFRAME_DICT,
                        **OUTPUT_SERIESFRAMES_DICT
                         }
