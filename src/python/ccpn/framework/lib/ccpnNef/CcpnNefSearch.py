"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2025-04-11 13:04:32 +0100 (Fri, April 11, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-12-08 15:44:37 +0000 (Thu, December 8, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import re
import typing
from collections import OrderedDict
from functools import partial

from ccpn.framework.lib.ccpnNef.CcpnNefCommon import nef2CcpnMap, _isALoop, _getSaveFramesInOrder
from ccpn.util.nef import StarIo
from ccpn.util.Logging import getLogger


#=========================================================================================
# SearchABC
#=========================================================================================

class SearchABC():
    """BaseClass for searching nef-saveFrames
    """
    debugFound = False
    debugNotFound = False

    def __init__(self, project, dataBlock, replace=False, validFramesOnly=False):
        """Initialise the class
        """
        self._project = project
        self._dataBlock = dataBlock
        self._saveFrameName = None
        self._replace = replace
        self._validFramesOnly = validFramesOnly

    #-----------------------------------------------------------------------------------------
    # Traverse all saveFrames in dataBlock
    #-----------------------------------------------------------------------------------------

    def _traverse(self, selection: typing.Optional[dict] = None,
                  traverseFunc=None):
        """Traverse the saveFrames in the correct order
        """
        dataBlock = self._dataBlock

        result = OrderedDict()
        saveframeOrderedDict = _getSaveFramesInOrder(dataBlock)

        if metaDataFrame := dataBlock['nef_nmr_meta_data']:
            self._saveFrameName = 'nef_nmr_meta_data'
            result[self._saveFrameName] = traverseFunc(metaDataFrame)
            del saveframeOrderedDict['nef_nmr_meta_data']

        if saveFrame := dataBlock.get('nef_molecular_system'):
            self._saveFrameName = 'nef_molecular_system'
            result[self._saveFrameName] = traverseFunc(saveFrame)
            del saveframeOrderedDict['nef_molecular_system']

        if saveFrame := dataBlock.get('ccpn_assignment'):
            self._saveFrameName = 'ccpn_assignment'
            result[self._saveFrameName] = traverseFunc(saveFrame)
            del saveframeOrderedDict['ccpn_assignment']

        for sf_category, saveFrames in saveframeOrderedDict.items():
            for saveFrame in saveFrames:
                saveFrameName = self._saveFrameName = saveFrame.name

                if selection and saveFrameName not in selection:
                    getLogger().debug2(f'>>>   -- skip saveframe {saveFrameName}')
                    continue
                getLogger().debug2(f'>>> _traverse saveframe {saveFrameName}')

                if val := traverseFunc(saveFrame):
                    result[self._saveFrameName] = val

        return result

    def _traverseDataBlock(self, selection: typing.Optional[dict] = None,
                           traverseFunc=None):
        """Traverse the saveFrames in the correct order
        """
        return self._traverse(selection, traverseFunc)

    #-----------------------------------------------------------------------------------------
    # Main loop-traverse
    #-----------------------------------------------------------------------------------------

    def processLoopItem(self, loop, rowNum, row, k, val, searchValues, replaceValues):
        """Process the values in the loop
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def processFrame(self, saveFrame, k, val, searchValues, replaceValues):
        """Process the values in the saveFrame
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    #-----------------------------------------------------------------------------------------
    # Main loop-traverse
    #-----------------------------------------------------------------------------------------

    def _replaceLoop(self, loop: StarIo.NmrLoop,
                     searchValues=None, replaceValues=None,
                     rowSearchList=None):
        """Search the loop for occurrences of searchFrameCode and replace if required
        """
        if not loop:
            return

        for row in loop.data:
            for rowNum, (k, val) in enumerate(row.items()):
                if rowSearchList and k not in rowSearchList:
                    continue

                # check the item in the loop
                self.processLoopItem(loop, rowNum, row, k, val, searchValues, replaceValues)

    def _replaceFrame(self, saveFrame: StarIo.NmrSaveFrame,
                      searchValues=None, replaceValues=None,
                      frameSearchList=None, attributeSearchList=None,
                      loopSearchList=None, rowSearchList=None):
        """Search the saveFrame for occurrences of searchFrameCode and replace if required
        """
        if not saveFrame:
            return

        framecode = saveFrame['sf_framecode']

        if not frameSearchList or framecode in frameSearchList:
            for k, val in saveFrame.items():
                if attributeSearchList and k not in attributeSearchList:
                    continue

                self.processFrame(saveFrame, k, val, searchValues, replaceValues)

        elif self._validFramesOnly:
            return

        # search loops as well - will still search for all loops even in ignored saveFrames
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and not (loopSearchList and loop.name not in loopSearchList):
                    self._replaceLoop(loop, searchValues=searchValues, replaceValues=replaceValues,
                                      rowSearchList=rowSearchList)

    def replace(self, searchValues=None, replaceValues=None,
                frameSearchList=None, attributeSearchList=None,
                loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        if searchValues:
            return self._traverseDataBlock(selection=None,
                                           traverseFunc=partial(self._replaceFrame,
                                                                searchValues=searchValues,
                                                                replaceValues=replaceValues,
                                                                frameSearchList=frameSearchList,
                                                                attributeSearchList=attributeSearchList,
                                                                loopSearchList=loopSearchList,
                                                                rowSearchList=rowSearchList))


#=========================================================================================
# Basic Search
#=========================================================================================

class SearchBasic(SearchABC):
    debugFound = True

    #-----------------------------------------------------------------------------------------
    # replace methods
    #-----------------------------------------------------------------------------------------

    def processLoopItem(self, loop, rowNum, row, k, val, searchValues, replaceValues):
        """Process the row of a loop
        """
        # search for any matching value - regex would be nicer :|
        if val == searchValues or val.startswith(f'{searchValues}.'):
            if self.debugFound:
                getLogger().debug(f'{self.__class__.__name__}.processLoopItem: found {rowNum} {k} --> {val}')

            if self._replace:
                row[k] = replaceValues + val[len(searchValues):]

        elif self.debugNotFound:
            getLogger().debug(f'{self.__class__.__name__}.processLoopItem: not found {rowNum} {k}')

    def processFrame(self, saveFrame, k, val, searchValues, replaceValues):
        """Process the saveFrame
        """
        if val == searchValues:
            if self.debugFound:
                getLogger().debug(f'{self.__class__.__name__}.processFrame: found {saveFrame} {k} --> {val}')

            if self._replace:
                saveFrame[k] = replaceValues

        elif self.debugNotFound:
            getLogger().debug(f'{self.__class__.__name__}.processFrame: not found {saveFrame} {k}')

    #-----------------------------------------------------------------------------------------
    # replace entry-point
    #-----------------------------------------------------------------------------------------

    def replace(self, searchValues=None, replaceValues=None,
                frameSearchList=None, attributeSearchList=None,
                loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        # search/replace values must be str
        if not isinstance(searchValues, str):
            raise TypeError(f'{self.__class__.__name__}.processFrame: searchValues must be a str')
        if not isinstance(replaceValues, str):
            raise TypeError(f'{self.__class__.__name__}.processFrame: replaceValues must be a str')

        super().replace(searchValues=searchValues, replaceValues=replaceValues,
                        frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                        loopSearchList=loopSearchList, rowSearchList=rowSearchList)


#=========================================================================================
# Search for deeper elements
#=========================================================================================

class SearchDeep(SearchABC):
    debugFound = True

    #-----------------------------------------------------------------------------------------
    # replace methods
    #-----------------------------------------------------------------------------------------

    def processLoopItem(self, loop, rowNum, row, k, val, searchValues, replaceValues):
        """Process the row of a loop
        """
        # regex for different wrapping quotes
        subs = (f'(\")({searchValues})(\"|[.]\d+\")',
                f"(\')({searchValues})(\'|[.]\d+\')")

        if isinstance(val, str):
            for sub in subs:
                if (result := re.sub(sub, f'\g<1>{replaceValues}\g<3>', val)) != val:
                    # search for any matching value
                    if self.debugFound:
                        getLogger().debug(f'{self.__class__.__name__}.processLoopItem: found {rowNum} {k} --> {val}')

                    if self._replace:
                        # replace as required
                        row[k] = val = result

                elif self.debugNotFound:
                    getLogger().debug(f'{self.__class__.__name__}.processLoopItem: not found {rowNum} {k}')

    def processFrame(self, saveFrame, k, val, searchValues, replaceValues):
        """Process the saveFrame
        """
        if val == searchValues:
            if self.debugFound:
                getLogger().debug(f'{self.__class__.__name__}.processFrame: found {saveFrame} {k} --> {val}')

            if self._replace:
                saveFrame[k] = replaceValues

        elif self.debugNotFound:
            getLogger().debug(f'{self.__class__.__name__}.processFrame: not found {saveFrame} {k}')

    #-----------------------------------------------------------------------------------------
    # replace entry-point
    #-----------------------------------------------------------------------------------------

    def replace(self, searchValues=None, replaceValues=None,
                frameSearchList=None, attributeSearchList=None,
                loopSearchList=None, rowSearchList=None):
        """Search the saveframes for references to findFrameCode
        If replace is True, will replace all attributes of saveFrame (if in selection, or all if selection is empty)
        and row items
        """
        # search/replace values must be str
        if not isinstance(searchValues, str):
            raise TypeError(f'{self.__class__.__name__}.processFrame: searchValues must be a str')
        if not isinstance(replaceValues, str):
            raise TypeError(f'{self.__class__.__name__}.processFrame: replaceValues must be a str')

        super().replace(searchValues=searchValues, replaceValues=replaceValues,
                        frameSearchList=frameSearchList, attributeSearchList=attributeSearchList,
                        loopSearchList=loopSearchList, rowSearchList=rowSearchList)
