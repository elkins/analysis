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
__dateModified__ = "$dateModified: 2024-10-10 15:45:26 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import pandas as pd
from typing import Sequence, Optional, Union

from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import PeakList as ApiPeakList
from ccpn.core.Spectrum import Spectrum
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices, _axisCodeMapIndices
from ccpn.core.lib.ContextManagers import newObject, undoBlockWithoutSideBar, notificationEchoBlocking, undoBlock
from ccpn.core._implementation.PMIListABC import PMIListABC
from ccpn.util.decorators import logCommand
from ccpn.util import Common as commonUtil
from ccpn.util.Logging import getLogger


GAUSSIANMETHOD = 'gaussian'
LORENTZIANMETHOD = 'lorentzian'
PARABOLICMETHOD = 'parabolic'
PICKINGMETHODS = (GAUSSIANMETHOD, LORENTZIANMETHOD, PARABOLICMETHOD)


class PeakList(PMIListABC):
    """An object containing Peaks. Note: the object is not a (subtype of a) Python list.
    To access all Peak objects, use PeakList.peaks."""

    #: Short class name, for PID.
    shortClassName = 'PL'
    # Attribute it necessary as subclasses must use superclass className
    className = 'PeakList'

    _parentClass = Spectrum

    #: Name of plural link to instances of class
    _pluralLinkName = 'peakLists'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiPeakList._metaclass.qualifiedName()

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _apiPeakList(self) -> ApiPeakList:
        """API peakLists matching PeakList."""
        return self._wrappedData

    def _setPrimaryChildClass(self):
        """Set the primary classType for the child list attached to this container
        """
        from ccpn.core.Peak import Peak as klass

        if klass not in self._childClasses:
            raise TypeError(
                    f'PrimaryChildClass {klass.className} does not exist as child of {self.className}'
                    )
        self._primaryChildClass = klass

    @property
    def chemicalShiftList(self) -> 'ChemicalShiftList | None':
        """STUB: hot-fixed later
        :return: an instance of ChemicalShiftList, or None
        """
        return None

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peaks in the PeakList
        """
        return []

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def peaks(self) -> list['Peak']:
        """STUB: hot-fixed later
        :return: a list of peaks in the PeakList
        """
        return []

    #=========================================================================================
    # getter STUBS: hot-fixed later
    #=========================================================================================

    def getPeak(self, relativeId: str) -> 'Peak | None':
        """STUB: hot-fixed later
        :return: an instance of Peak, or None
        """
        return None

    #=========================================================================================
    # Core methods
    #=========================================================================================

    def pickPeaksNd(self, regionToPick: Sequence[float] = None,
                    doPos: bool = True, doNeg: bool = True,
                    fitMethod: str = GAUSSIANMETHOD, excludedRegions=None,
                    excludedDiagonalDims=None, excludedDiagonalTransform=None,
                    minDropFactor: float = 0.1):
        # DEPRECATED

        getLogger().warning('Deprecated method. Use spectrum.pickPeaks instead')
        from ccpn.core.lib.PeakListLib import _pickPeaksNd

        return _pickPeaksNd(self, regionToPick=regionToPick,
                            doPos=doPos, doNeg=doNeg,
                            fitMethod=fitMethod,
                            excludedRegions=excludedRegions,
                            excludedDiagonalDims=excludedDiagonalDims,
                            excludedDiagonalTransform=excludedDiagonalTransform,
                            minDropFactor=minDropFactor)

    @logCommand(get='self')
    def estimateVolumes(self, peaks: Union[None, list, tuple] = None, volumeIntegralLimit=2.0, noWarning=False):
        """Estimate the volumes for the peaks in this peakList.

        If peaks is specified as None then volumes are estimated for all peaks in the peakList.
        The width of the volume integral in each dimension is the lineWidth * volumeIntegralLimit,
        the default is 2.0 * FWHM of the peak.
        Set noWarning to True to ignore warnings from peaks without lineWidths, default is False.

        :param peaks: list|tuple of peaks, or None
        :param volumeIntegralLimit: integral width as a multiple of lineWidth (FWHM)
        :param noWarning: Ignore peak warnings
        """
        # otherwise circular-import error
        from ccpn.core.Peak import Peak

        # verify the parameters
        if not isinstance(peaks, (list, tuple, type(None))):
            raise TypeError(f'{self.__class__.__name__}.estimateVolumes: peaks must be list|tuple|None')
        if not peaks:
            peaks = self.peaks  # get all the peaks in the peakList
        else:
            peaks = self.project.getByPids(peaks)
            myPeaks = list(self.peaks)
            if not all(isinstance(pk, Peak) and pk in myPeaks for pk in peaks):
                raise TypeError(f'{self.__class__.__name__}.estimateVolumes: peaks contains non-Peak objects')
        if not isinstance(volumeIntegralLimit, float):
            raise TypeError(f'{self.__class__.__name__}.estimateVolumes: volumeIntegralLimit must be a float')
        if not isinstance(noWarning, bool):
            raise TypeError(f'{self.__class__.__name__}.estimateVolumes: noWarning must be True/False')

        with undoBlockWithoutSideBar():
            for pp in peaks:
                # estimate the volume for each peak
                height = pp.height
                lineWidths = pp.lineWidths
                if lineWidths and None not in lineWidths and height:
                    pp.estimateVolume(volumeIntegralLimit=volumeIntegralLimit)
                elif not noWarning:
                    getLogger().warning(f'Peak {str(pp)} contains undefined height/lineWidths')

    @logCommand(get='self')
    def copyTo(self, targetSpectrum: Spectrum, targetPeakList=None, includeAllPeakProperties=True,
               **kwargs) -> 'PeakList':
        """
        Copy the origin PeakList peaks to a targetSpectrum.
        If targetPeakList is given, peaks will be added to it, otherwise a new PeakList is created (default behaviour).
        return the target PeakList with the newly copied peaks.

        :param targetSpectrum:  object: Core.Spectrum or Str: Pid
        :param targetPeakList:  object: Core.PeakList or Str: Pid
        :param kwargs:          any extra PeakList attributes for newly created peakLists.
                                Not used if it is given a targetPeakList
        """

        singleValueTags = ['isSynthetic', 'symbolColour', 'symbolStyle', 'textColour', 'textColour',
                           'title', 'comment', 'meritThreshold', 'meritEnabled', 'meritColour']

        targetSpectrum = self.project.getByPid(targetSpectrum) if isinstance(targetSpectrum, str) else targetSpectrum
        if not targetSpectrum:
            raise TypeError('targetSpectrum not defined')
        if not isinstance(targetSpectrum, Spectrum):
            raise TypeError('targetSpectrum is not of type Spectrum')

        # checking targetSpectrum for compatibility
        # TODO enable copying across different dimensionalities
        dimensionCount = self.spectrum.dimensionCount
        if dimensionCount < targetSpectrum.dimensionCount:
            raise ValueError(
                    f"Cannot copy {dimensionCount}D {self.longPid} to {targetSpectrum.dimensionCount}D {targetSpectrum.longPid}"
                    )

        dimensionMapping = _axisCodeMapIndices(self.spectrum.axisCodes, targetSpectrum.axisCodes)
        if None in dimensionMapping:
            raise ValueError("%s axisCodes %r not compatible with targetSpectrum axisCodes %r"
                             % (self, self.spectrum.axisCodes, targetSpectrum.axisCodes))

        if targetPeakList:
            targetPeakList = self.project.getByPid(targetPeakList) if isinstance(targetPeakList,
                                                                                 str) else targetPeakList
            if not isinstance(targetPeakList, PeakList):
                raise TypeError('targetPeakList is not of type PeakList')
            if targetPeakList not in targetSpectrum.peakLists:
                raise TypeError(f'targetPeakList is not a PeakList of: {targetSpectrum.pid}')

        else:
            # make a dictionary with parameters of self to be copied to new targetPeakList (if created)
            params = {tag: getattr(self, tag) for tag in singleValueTags}
            params['comment'] = "Copy of %s\n" % self.longPid + (params['comment'] or '')
            for key, val in kwargs.items():
                if key in singleValueTags:
                    params[key] = val
                else:
                    raise ValueError(f"PeakList has no attribute {key}")

        with undoBlockWithoutSideBar():
            if not targetPeakList:
                targetPeakList = targetSpectrum.newPeakList(**params)

            for peak in self.peaks:
                peak.copyTo(targetPeakList, includeAllProperties=includeAllPeakProperties)

        return targetPeakList

    @logCommand(get='self')
    def subtractPeakLists(self, peakList: 'PeakList') -> 'PeakList':
        """
        Subtracts peaks in peakList2 from peaks in peakList1, based on position,
        and puts those in a new peakList3.  Assumes a common spectrum for now.
        """

        def _havePeakNearPosition(values, tolerances, peaks) -> Optional['Peak']:

            for peak in peaks:
                for i, position in enumerate(peak.position):
                    if abs(position - values[i]) > tolerances[i]:
                        break
                else:
                    return peak

        peakList = self.project.getByPid(peakList) if isinstance(peakList, str) else peakList
        if not peakList:
            raise TypeError('peakList not defined')
        if not isinstance(peakList, PeakList):
            raise TypeError('peakList is not of type PeakList')

        # with logCommandBlock(prefix='newPeakList=', get='self') as log:
        #     peakStr = '[' + ','.join(["'%s'" % peak.pid for peak in peakList2]) + ']'
        #     log('subtractPeakLists', peaks=peakStr)

        with undoBlockWithoutSideBar():
            spectrum = self.spectrum

            assert spectrum is peakList.spectrum, 'For now requires both peak lists to be in same spectrum'

            # dataDims = spectrum.sortedDataDims()
            tolerances = self.spectrum.assignmentTolerances

            peaks2 = peakList.peaks
            peakList3 = spectrum.newPeakList()

            for peak1 in self.peaks:
                values1 = [peak1.position[dim] for dim in range(len(peak1.position))]
                if not _havePeakNearPosition(values1, tolerances, peaks2):
                    peakList3.newPeak(height=peak1.height, volume=peak1.volume, figureOfMerit=peak1.figureOfMerit,
                                      annotation=peak1.annotation, ppmPositions=peak1.position,
                                      pointPositions=peak1.pointPositions)

        return peakList3

    # def refit(self, method: str = GAUSSIANMETHOD):
    #     fitExistingPeakList(self._apiPeakList, method)

    @logCommand(get='self')
    def restrictedPick(self, positionCodeDict, doPos, doNeg):

        codes = list(positionCodeDict.keys())
        positions = [positionCodeDict[code] for code in codes]

        # match the spectrum to the restricted codes, these are the only ones to update
        indices = getAxisCodeMatchIndices(self.spectrum.axisCodes, codes)

        # divide by 2 to get the double-width tolerance, i.e. the width of the region - CHECK WITH GEERTEN
        tolerances = tuple(tol / 2 for tol in self.spectrum.assignmentTolerances)

        limits = [sorted(lims) for lims in self.spectrum.spectrumLimits]
        selectedRegion = []
        minDropFactor = self.project.application.preferences.general.peakDropFactor

        with undoBlockWithoutSideBar():
            for ii, ind in enumerate(indices):
                if ind is not None and positions[ind] is not None:
                    selectedRegion.insert(ii, [positions[ind] - tolerances[ii], positions[ind] + tolerances[ii]])
                else:
                    selectedRegion.insert(ii, [limits[ii][0], limits[ii][1]])

            # regionToPick = selectedRegion
            # peaks = self.pickPeaksNd(regionToPick, doPos=doPos, doNeg=doNeg, minDropFactor=minDropFactor)

            # axisCodeDict = dict((code, selectedRegion[ii]) for ii, code in enumerate(self.spectrum.axisCodes))
            axisCodeDict = dict(zip(self.spectrum.axisCodes, selectedRegion))

            _spectrum = self.spectrum
            if _peakPicker := _spectrum.peakPicker:
                _peakPicker.setParameters(dropFactor=minDropFactor,
                                          setLineWidths=True,
                                          singularMode=False
                                          )
                return _spectrum.pickPeaks(
                        self,
                        _spectrum.positiveContourBase if doPos else None,
                        _spectrum.negativeContourBase if doNeg else None,
                        **axisCodeDict
                        )
        return []

    def reorderValues(self, values, newAxisCodeOrder):
        """Reorder values in spectrum dimension order to newAxisCodeOrder
        by matching newAxisCodeOrder to spectrum axis code order"""
        return commonUtil.reorder(values, self._parent.axisCodes, newAxisCodeOrder)

    # def __str__(self):
    #   """Readable string representation"""
    #   return "<%s; #peaks:%d (isSimulated=%s)>" % (self.pid, len(self.peaks), self.isSimulated)

    @logCommand(get='self')
    def pickPeaksRegion(self, regionToPick: dict = {},
                        doPos: bool = True, doNeg: bool = True,
                        minLinewidth=None, exclusionBuffer=None,
                        minDropFactor: float = 0.1, checkAllAdjacent: bool = True,
                        fitMethod: str = PARABOLICMETHOD, excludedRegions=None,
                        excludedDiagonalDims=None, excludedDiagonalTransform=None,
                        estimateLineWidths=True):

        getLogger().warning('Deprecated, please use spectrum.pickPeaks()')

        from ccpn.core.lib.PeakListLib import _pickPeaksRegion

        with undoBlockWithoutSideBar():
            peaks = _pickPeaksRegion(self, regionToPick=regionToPick,
                                     doPos=doPos, doNeg=doNeg,
                                     minLinewidth=minLinewidth, exclusionBuffer=exclusionBuffer,
                                     minDropFactor=minDropFactor, checkAllAdjacent=checkAllAdjacent,
                                     fitMethod=fitMethod, excludedRegions=excludedRegions,
                                     excludedDiagonalDims=excludedDiagonalDims,
                                     excludedDiagonalTransform=excludedDiagonalTransform,
                                     estimateLineWidths=estimateLineWidths)
        return peaks

    def fitExistingPeaks(self, peaks: Sequence['Peak'], fitMethod: str = GAUSSIANMETHOD, singularMode: bool = False,
                         halfBoxSearchWidth: int = 4, halfBoxFitWidth: int = 4):
        """Refit the current selected peaks.
        Must be called with peaks that belong to this peakList
        """
        from ccpn.core.lib.PeakListLib import _fitExistingPeaks

        # getLogger().warning('Deprecated, please use spectrum.fitExistingPeaks()') #comment-out until it is clear what is the new routine to use instead.

        return _fitExistingPeaks(self,
                                 peaks=peaks,
                                 fitMethod=fitMethod,
                                 singularMode=singularMode,
                                 halfBoxSearchWidth=halfBoxSearchWidth,
                                 halfBoxFitWidth=halfBoxFitWidth)

    @logCommand(get='self')
    def calculateClusterIds(self, tolerances=None, clustererName=None):
        """
        Calculate clusterIDs for peaks using the in Depth-First-Search (DFS) algorithm.
        """
        from ccpn.core.lib.PeakClustering import PeakClusterers, DFSPeakClusterer

        if tolerances is None:
            defaultTolerancePoints = 8
            tolerances = [defaultTolerancePoints] * self.spectrum.dimensionCount
        clusterer = PeakClusterers.get(clustererName, DFSPeakClusterer)
        peakClusterer = clusterer(self.peaks, tolerances)
        clusters = peakClusterer.findClusters()
        peakClusterer.setClusterIdToPeaks(clusters)
        return clusters

    @logCommand(get='self')
    def resetClusterIds(self):
        """
        Reset clusterIDs to a default enumeration.
        """
        with undoBlockWithoutSideBar():
            for i, peak in enumerate(self.peaks):
                peak.clusterId = i + 1

    def getPeakAliasingRanges(self):
        """Return the min/max aliasing values for the peaks in the list, if there are no peaks, return None
        """
        if not self.peaks:
            return None

        # calculate the min/max aliasing values for the spectrum
        dims = self.spectrum.dimensionCount

        aliasMin = [0] * dims
        aliasMax = [0] * dims

        for peak in self.peaks:
            alias = peak.aliasing
            aliasMax = np.maximum(aliasMax, alias)
            aliasMin = np.minimum(aliasMin, alias)

        # set min/max in spectrum here if peaks have been found
        aliasRanges = tuple((int(mn), int(mx)) for mn, mx in zip(aliasMin, aliasMax))

        return aliasRanges

    @logCommand(get='self')
    def reorderPeakListAxes(self, newAxisOrder):
        """Reorder the peak position according to the newAxisOrder
        """
        dims = self.spectrum.dimensionCount

        if not isinstance(newAxisOrder, (list, tuple)):
            raise TypeError('newAxisOrder must be a list/tuple')
        if len(newAxisOrder) != dims:
            raise ValueError('newAxisOrder is the wrong length, must match spectrum dimensions')
        if len(set(newAxisOrder)) != len(newAxisOrder):
            raise ValueError('newAxisOrder contains duplicated elements')
        if not all(isinstance(ii, int) for ii in newAxisOrder):
            raise ValueError('newAxisOrder must be ints')
        if not all(0 <= ii < dims for ii in newAxisOrder):
            raise ValueError('newAxisOrder elements must be in range 0-%i', dims - 1)

        with undoBlockWithoutSideBar():
            # reorder all peaks in the peakList
            for peak in self.peaks:
                pos = peak.position
                newPos = []
                for ii in newAxisOrder:
                    newPos.append(pos[ii])
                peak.position = newPos

    @logCommand(get='self')
    def fetchNewAssignments(self, nmrChain: 'NmrChain', keepAssignments: bool = False):
        """Fetch new assignments for each peak from the specified nmrChain.
        Optionally the original assignments can be overwritten or appended to.

        :param nmrChain: source for nmrAtoms.
        :param keepAssignments: overwrite/append assignments.
        :return:
        """
        if not self.peaks:
            return
        peak = self.peaks[0]
        axisIso = list(zip(peak.axisCodes, peak.spectrum.isotopeCodes))
        numDims = len(peak.axisCodes)
        foundMts = {}
        with undoBlock():
            for cc, peak in enumerate(self.peaks):
                # only process those that are empty OR those not empty when checkbox cleared
                dimensionNmrAtoms = peak.dimensionNmrAtoms  # for speed reasons !?
                if not keepAssignments or not any(dimensionNmrAtoms):
                    if peak.multiplets:
                        existingDims = [[] for _nd in range(numDims)]
                        for mt in peak.multiplets:
                            if mt in foundMts:
                                for i, (exst, dimNmr) in enumerate(zip(existingDims, foundMts[mt])):
                                    existingDims[i].append(dimNmr)
                            else:
                                # need to create a new residue and nmrAtoms
                                thisDims = [[] for _nd in range(numDims)]
                                nmrResidue = nmrChain.newNmrResidue()
                                for i, (axis, isotope) in enumerate(axisIso):
                                    nmrAtom = nmrResidue.fetchNmrAtom(name=str(axis[0]), isotopeCode=isotope)
                                    existingDims[i].append(nmrAtom)
                                    thisDims[i] = nmrAtom
                                foundMts[mt] = thisDims
                        # assign all the dimensions
                        peak.assignDimensions(axisCodes=peak.axisCodes, values=existingDims)
                    else:
                        # make a new nmrResidue with new nmrAtoms and assign to the peak
                        nmrResidue = nmrChain.newNmrResidue()
                        newNmrs = [[nmrResidue.fetchNmrAtom(name=str(axis[0]), isotopeCode=isotope)] for
                                   axis, isotope in axisIso]
                        peak.assignDimensions(axisCodes=peak.axisCodes, values=newNmrs)

    #=========================================================================================
    # Implementation methods
    #=========================================================================================

    def delete(self):
        """Delete peakList
        """
        # call the delete method from the parent class
        self._parent._deletePeakList(self)

    @classmethod
    def _getAllWrappedData(cls, parent: Spectrum) -> list:
        """get wrappedData (PeakLists) for all PeakList children of parent Spectrum"""
        return [x for x in parent._wrappedData.sortedPeakLists() if x.dataType == 'Peak']

    def _finaliseAction(self, action: str, **actionKwds):
        """Subclassed to notify changes to associated peakListViews
        """
        if not super()._finaliseAction(action):
            return

        # this is a can-of-worms for undelete at the minute
        try:
            if action in {'change'}:
                for plv in self.peakListViews:
                    plv._finaliseAction(action)
        except Exception as es:
            raise RuntimeError(f'Error _finalising peakListViews: {str(es)}') from es

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    @logCommand(get='self')
    def newPeak(self, ppmPositions: Sequence[float] = (), height: float = None,
                comment: str = None, **kwds):
        """Create a new Peak within a peakList.

        See the Peak class for details.

        Optional keyword arguments can be passed in; see Peak._newPeak for details.

        NB you must create the peak before you can assign it. The assignment attributes are:
        - assignments (assignedNmrAtoms) - A tuple of all (e.g.) assignment triplets for a 3D spectrum
        - assignmentsByDimensions (dimensionNmrAtoms) - A tuple of tuples of assignments, one for each dimension

        :param ppmPositions: peak position in ppm for each dimension (related attributes: positionError, pointPositions)
        :param height: height of the peak (related attributes: volume, volumeError, lineWidths)
        :param comment: optional comment string
        :return: a new Peak instance.
        """
        from ccpn.core.Peak import _newPeak  # imported here to avoid circular imports

        return _newPeak(self, ppmPositions=ppmPositions, height=height, comment=comment, **kwds)

    @logCommand(get='self')
    def newPickedPeak(self, pointPositions: Sequence[float] = None, height: float = None,
                      lineWidths: Sequence[float] = (), fitMethod: str = PARABOLICMETHOD, **kwds):
        """Create a new Peak within a peakList from a picked peak

        See the Peak class for details.

        Optional keyword arguments can be passed in; see Peak._newPickedPeak for details.

        :param height: height of the peak (related attributes: volume, volumeError, lineWidths)
        :param pointPositions: peak position in points for each dimension (related attributes: positionError, pointPositions)
        :param fitMethod: type of curve fitting
        :param lineWidths:
        :param serial: optional serial number.
        :return: a new Peak instance.
        """
        from ccpn.core.Peak import _newPickedPeak  # imported here to avoid circular imports

        return _newPickedPeak(self, pointPositions=pointPositions, height=height,
                              lineWidths=lineWidths, fitMethod=fitMethod, **kwds)

    def getAsDataFrame(self) -> pd.DataFrame:
        """ Get the peakList as a DataFrame. """
        dfs = []
        for peak in self.peaks:
            dfs.append(peak.getAsDataFrame())
        return pd.concat(dfs, axis=0)

    @logCommand(get="self")
    def fetchMultiplets(self, peaks: list['Peak'] = None) -> tuple['Multiplet']:
        """Fetches Multiplets from selected Peaks or all peaks in the PeakList

        From the peaks chosen, all associated multiplets will be returned,
        if a peak has no associated multiplet one will be created for it.

        :param peaks: List of Peaks, if blank then all peaks in
                      this peak list are used.

        """
        with undoBlock():
            with notificationEchoBlocking():
                spec = self.spectrum
                peaks = peaks if peaks is not None else self.peaks
                mps = set()
                tempML = spec.newMultipletList()
                for peak in peaks:
                    if not peak.multiplets:
                        tempML.newMultiplet(peak)
                    mps.update(peak.multiplets)
                if not tempML.multiplets:
                    tempML.delete()
        return tuple(mps)


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(PeakList)
def _newPeakList(self: Spectrum, title: str = None, comment: str = None,
                 symbolStyle: str = None, symbolColour: str = None,
                 textColour: str = None,
                 meritColour: str = None, meritEnabled: bool = False, meritThreshold: float = None,
                 lineColour: str = None,
                 arrowColour: str = None,
                 isSynthetic: bool = False,
                 isSimulated: bool = None) -> PeakList:
    """Create new empty PeakList within Spectrum

    See the PeakList class for details.

    :param title:
    :param comment:
    :param isSynthetic:
    :param symbolStyle:
    :param symbolColour:
    :param textColour:
    :return: a new PeakList instance.
    """
    if isSimulated is not None:
        getLogger().debug('Changing isSimulated value to isSynthetic')
        isSynthetic = isSimulated

    dd = {'name': title, 'details': comment, 'isSimulated': isSynthetic}
    if symbolColour:
        dd['symbolColour'] = symbolColour
    if symbolStyle:
        dd['symbolStyle'] = symbolStyle
    if textColour:
        dd['textColour'] = textColour

    apiDataSource = self._apiDataSource
    apiPeakList = apiDataSource.newPeakList(**dd)
    result = self._project._data2Obj.get(apiPeakList)
    if result is None:
        raise RuntimeError('Unable to generate new PeakList item')

    # set non-api attributes
    if meritColour is not None:
        result.meritColour = meritColour
    if meritEnabled is not None:
        result.meritEnabled = meritEnabled
    if meritThreshold is not None:
        result.meritThreshold = meritThreshold
    if lineColour is not None:
        result.lineColour = lineColour
    if arrowColour is not None:
        result.arrowColour = arrowColour

    return result

# for sp in project.spectra:
#     c = sp.positiveContourColour
#     sp.peakLists[-1].symbolColour = c
