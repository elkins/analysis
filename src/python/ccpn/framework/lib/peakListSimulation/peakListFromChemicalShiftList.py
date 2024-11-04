"""
This module defines the creation of a Simulated Spectrum from a ChemicalShift List
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
__modifiedBy__ = "$modifiedBy: Vicky Higman $"
__dateModified__ = "$dateModified: 2024-10-23 14:19:12 +0100 (Wed, October 23, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================



from ccpn.util.traits.CcpNmrTraits import Any, List, Bool, Odict, CString, CInt
from ccpn.util.Common import flattenLists
from ccpn.util.traits.TraitBase import TraitBase
from ccpn.util.traits.CcpNmrTraits import Any, List, Bool, Odict, CString
from ccpn.core.ChemicalShiftList import ChemicalShiftList, CS_ATOMNAME, CS_VALUE,\
    CS_NMRATOM, CS_NMRRESIDUE, CS_SEQUENCECODE, CS_CHAINCODE
from ccpn.framework.Application import getApplication, getProject
from ccpn.util.OrderedSet import OrderedSet
from ccpn.core.NmrResidue import NmrResidue, _getNmrResidue
import pandas as pd
from ccpn.core.lib.ContextManagers import undoStackBlocking, undoBlockWithoutSideBar, notificationEchoBlocking, PandasChainedAssignment
from ccpn.util.Logging import getLogger
from collections import OrderedDict, defaultdict




#--------------------------------------------------------------------------------------------
# ExperimentTypeSimulator class
#--------------------------------------------------------------------------------------------

class SimulatedSpectrumByExperimentTypeABC(TraitBase):

    #=========================================================================================
    # to be subclassed
    #=========================================================================================
    experimentType = None
    peakAtomNameMappers = [[],]
    isotopeCodes = []
    axisCodes = []
    spectralWidths = []
    referenceValues = []

    #=========================================================================================
    # end to be subclassed
    #=========================================================================================

    # traits
    application = Any(default_value=None, allow_none=True)

    #=========================================================================================
    # start of methods
    #=========================================================================================

    def __init__(self, chemicalShiftList, spectrumKwargs=None):
        super().__init__()
        self.chemicalShiftList = chemicalShiftList
        if not isinstance(self.chemicalShiftList, ChemicalShiftList):
            raise ValueError('Invalid chemicalShiftList "%s"' % chemicalShiftList)

        self.application = getApplication()
        self.project = getProject()
        self._spectrum = None
        self._peakListIndex = -1
        self._spectrumKwargs = self._getDefaultSpectrumKwargs()
        self._spectrumKwargs.update(spectrumKwargs if spectrumKwargs else {})
        self._initSpectrum()

    @property
    def spectrum(self):
        return self._spectrum

    def getPeakAtomNameMappers(self):
        peakAtomNameMappers = self.peakAtomNameMappers
        if peakAtomNameMappers is None:
            peakAtomNameMappers = self._createAtomNameMappers()
        return peakAtomNameMappers

    @property
    def peakList(self):
        return self._spectrum.peakLists[self._peakListIndex]

    def _initSpectrum(self):
        ''' init a new empty spectrum from the defined options
        '''

        name = self._spectrumKwargs.get('name', self.chemicalShiftList.name)
        self._spectrumKwargs.pop('name', None)

        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                self._spectrum = self.project.newEmptySpectrum(isotopeCodes=self.isotopeCodes, name=name,
                                                               **self._spectrumKwargs)
        return self._spectrum

    def simulatePeakList(self):
        """ Create new peaks from the ChemicalShiftList.
         Add ppm positions based on the CS value.
         Add peak assignment from the CS nmrAtom name.
         Use the self.peakAtomNameMappers to create group of peaks as needed for the required Experiment Type.
         Note: cannot deal yet with ccpn partial assignments, such as nmrAtomNames defined as @, @@, #
         and hardcoded offsets. Those are skipped.
         E.g.: an offset nmrResidue i-1 for sequenceCode 10 is the nmrResidue 9 and not the nmrResidue named  "10-1".
         """

        data = self.chemicalShiftList._data
        requiredAtomNames = self._getAllRequiredAtomNames()
        ## filter CSL on the atomNames of interest
        data = data[data[CS_ATOMNAME].isin(requiredAtomNames)]
        # check if the nmrAtom exists in the project. it should!. create a new column nmrResidue because we need for groupby
        with PandasChainedAssignment():
            data[CS_NMRRESIDUE] = [self.project.getByPid(na).nmrResidue if self.project.getByPid(na) else None for na in
                               data[CS_NMRATOM]]
        # Filter any Rows where No NmrResidue
        data = data[data[CS_NMRRESIDUE].notna()]
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                for ix, filteredData in data.groupby(CS_NMRRESIDUE):
                    for mappers in self.getPeakAtomNameMappers(): # mappers are list of lists
                        # make a new Peak for each mapperGroup
                        peak = self.peakList.newPeak()
                        # loop through mappers to get the required atoms names  to fill the peak assignments and CS value
                        axisCodePpmPositionsDict = {} # make a dict because a ppmPos can be None/missing (expecially when doing i-1 assignments)
                        for dim, mapper in enumerate(mappers):
                            axisCodePpmPositionsDict[mapper.axisCode] = None
                            for offset, requiredAtomName in mapper.offsetNmrAtomNames.items(): ## loop over the required atomName and residue offset
                                for rowCount, (localIndex, dataRow) in enumerate(filteredData.iterrows()): ## loop over the grouppedBy-Residue rows
                                    if requiredAtomName == dataRow[CS_ATOMNAME]: ## we found the match in the CSL
                                        # get the right nmrAtom based on the offset. Cannot deal yet @, @@, and ccpn partial assignments like the str sequenceCode "10-1"
                                        sequenceCode = dataRow[CS_SEQUENCECODE]
                                        try:
                                            sequenceCode = int(sequenceCode)
                                        except:
                                            getLogger().warn('Cannot deal yet with non-numerical nmrResidue sequenceCode. Skipping: %s' % sequenceCode)
                                            continue
                                        ## build the assignment. Get nmrChain, nmrResidue and nmrAtom from project
                                        nmrChain = self.project.getNmrChain(dataRow[CS_CHAINCODE]) # this is not necessarily as the dataRow nmrResidue.chain; that's why we get this way.
                                        if sequenceCode:
                                            sequenceCode += offset
                                        nmrResidue = _getNmrResidue(nmrChain, sequenceCode) # this is not necessarily as the dataRow nmrResidue because the offset value!
                                        if nmrResidue is not None:
                                            na = nmrResidue.getNmrAtom(dataRow[CS_ATOMNAME]) # this is not necessarily as the dataRow nmrAtom. So search again because the offset value!
                                            if na:
                                                peak.assignDimension(mapper.axisCode, [na])
                                                # find the CS value based on the offset, this is not necessarily as the dataRow CS_VALUE. that's why we search again in the whole DF
                                                cs4naValues = data[data[CS_NMRATOM] == na.pid][CS_VALUE].values
                                                if len(cs4naValues) == 1:  # should be always present!?
                                                    axisCodePpmPositionsDict[mapper.axisCode] = float(cs4naValues[0])
                                        break
                        # fill the peak.ppmPositions. Remove peak with None in PpmPosition .
                        ppmPositions = tuple(axisCodePpmPositionsDict.values())
                        if not all(ppmPositions):
                            getLogger().debug3('Simulating peak. Missing ppmPositions for %s. Deleted.' %peak.pid)
                            peak.delete()
                            continue
                        peak.ppmPositions = ppmPositions

    def _getDefaultSpectrumKwargs(self):
        """ Get the default Spectrum properties as a dict from the Class attributes"""
        _spectrumKwargs = {
                            'experimentType'    : self.experimentType,
                            'spectralWidths'    : self.spectralWidths,
                            'referenceValues'   : self.referenceValues,
                            'axisCodes'         : self.axisCodes,
                            'chemicalShiftList' : self.chemicalShiftList,
                          }
        return _spectrumKwargs

    def _setSpectrumProperties(self, **kwargs):
        """
        Set a valid spectrum property from a dict key:value. key: the property to be set, value: its value.
        See the Spectrum core class for more info.
        Usage: .setSpectrumProperties(**{'referenceValues': [12.0, 200.0, 130.0]})
        :param kwargs:
        :return:
        """
        for key, value in kwargs.items():
            try:
                setattr(self.spectrum, key, value)
            except Exception as error:
                getLogger().warning(f'Cannot set Spectrum property {key} with values {value}. {error}')

    # =========================================================================================
    # Convenient methods for error checking/logging
    # =========================================================================================

    def _isPeakWithinLimits(self, peakList):
        """check if the newly created peaks are within the expected SpectrumLimits"""
        pass

    def _isValidExperimentType(self):
        """check if valid experimentType"""
        pass

    def _isValidPeakMapper(self):
        """check if is a valid PeakMapper. e.g.: the structure is same length as the dimension count"""
        pass

    def _getAllRequiredAtomNames(self):
        values = [v._getAllAtomNames() for mm in self.getPeakAtomNameMappers() for v in mm]
        return OrderedSet(flattenLists(values))

    @staticmethod
    def _createAtomNameMappers():
        return [[],]
    # =========================================================================================

    def __str__(self):
        return f'<{self.__class__.__name__}>'

    __repr__ = __str__


#--------------------------------------------------------------------------------------------
# AtomNamesMapper class
#--------------------------------------------------------------------------------------------

class AtomNamesMapper(object):
    """
    A container to facilitate the nmrAtoms assignment mapping to a particular axisCode from a ChemicalShift
    """
    isotopeCode         = None
    axisCode            = None
    offsetNmrAtomNames  = {}


    def __init__(self, isotopeCode=None, axisCode=None, offsetNmrAtomNames=None, **kwargs):
        """
        :param isotopeCode:    str. e.g.:'1H'. Used to define the EmptySpectrum isotopeCodes list
        :param axisCode:       str. any allowed. Used to define the EmptySpectrum axisCodes list
        :param offsetNmrAtomNames:  dict, key-value.
                                -Key: offset definition, int  e.g.: 0 to define as "i"; -1 to define as "i-1".
                                -Value: string to be used for fetching nmrAtom (i) and assign using the defined axisCode
        """
        super().__init__()

        if isotopeCode:
            self.isotopeCode = isotopeCode
        if axisCode:
            self.axisCode = axisCode
        if offsetNmrAtomNames:
         self.offsetNmrAtomNames = offsetNmrAtomNames


    def _getAllAtomNames(self):
        return list(self.offsetNmrAtomNames.values())

    def __str__(self):
        nmrAtoms = [f'NmrAtom="{na}", offset={o}' for o, na in self.offsetNmrAtomNames.items()]
        return f'<{self.__class__.__name__}>: isotopeCode="{self.isotopeCode}", axisCode="{self.axisCode}", nmrAtoms={"".join(nmrAtoms)} '

    __repr__ = __str__


class HAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '1H'
    axisCode            = 'Hn'
    offsetNmrAtomNames  = {0: 'H'}

class NAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '15N'
    axisCode            = 'Nh'
    offsetNmrAtomNames  = {0: 'N'}

class ssNAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '15N'
    axisCode            = 'N'
    offsetNmrAtomNames  = {0: 'N'}

class COAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {0: 'C'}

class COM1AtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {-1: 'C'}

class CAAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {0: 'CA'}

class ssCAAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'CA'
    offsetNmrAtomNames  = {0: 'CA'}

class CAM1AtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {-1: 'CA'}

class CBAtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {0: 'CB'}

class CBM1AtomNamesMapper(AtomNamesMapper):

    isotopeCode         = '13C'
    axisCode            = 'C'
    offsetNmrAtomNames  = {-1: 'CB'}


#--------------------------------------------------------------------------------------------
# The Various ExperimentType classes
#--------------------------------------------------------------------------------------------
#
# Subclass of SimulatedSpectrumByExperimentTypeABC to allow customised behaviour/implementation
#
#--------------------------------------------------------------------------------------------
# 1D ExperimentTypes
#--------------------------------------------------------------------------------------------

class SimulatedSpectrum_1H(SimulatedSpectrumByExperimentTypeABC):

    experimentType = 'H'
    isotopeCodes = ['1H']
    axisCodes = ['H']
    spectralWidths = [12]
    referenceValues = [12]
    peakAtomNameMappers = [
        [AtomNamesMapper(isotopeCode='1H', axisCode='H', offsetNmrAtomNames={0:'H'})]
        ]



#--------------------------------------------------------------------------------------------
# 2D ExperimentTypes
#--------------------------------------------------------------------------------------------

class SimulatedSpectrum_15N_HSQC(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = '15N HSQC/HMQC'
    isotopeCodes        = ['1H', '15N']
    axisCodes           = ['Hn', 'Nh']
    spectralWidths      = [7, 40]
    referenceValues     = [12, 140]
    peakAtomNameMappers = [
                            [
                            HAtomNamesMapper(),
                            NAtomNamesMapper()
                            ],
                          ]

class SimulatedSpectrum_13C_HSQC(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = '13C HSQC/HMQC'
    isotopeCodes        = ['1H', '13C']
    axisCodes           = ['H', 'C']
    spectralWidths      = [16, 160]
    referenceValues     = [14, 160]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES_CBONDED

        peakMappers = [[],]
        for catom in NEF_ATOM_NAMES_CBONDED.keys():
            for hatom in NEF_ATOM_NAMES_CBONDED.get(catom, []):
                atomNameMappers = [AtomNamesMapper(isotopeCode='1H', axisCode='H', offsetNmrAtomNames={0:hatom}),
                                    AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:catom})]
                peakMappers.append(atomNameMappers)

        return(peakMappers)

class SimulatedSpectrum_NCA(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'NCA'
    isotopeCodes        = ['13C', '15N']
    axisCodes           = ['CA', 'N']
    spectralWidths      = [35, 50]
    referenceValues     = [75, 150]
    peakAtomNameMappers = [
                            [
                            ssCAAtomNamesMapper(),
                            ssNAtomNamesMapper()
                            ]
                           ]

class SimulatedSpectrum_NCO(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'NCO'
    isotopeCodes        = ['13C', '15N']
    axisCodes           = ['C', 'N']
    spectralWidths      = [30, 50]
    referenceValues     = [190, 150]
    peakAtomNameMappers = [
                            [
                            COM1AtomNamesMapper(),
                            ssNAtomNamesMapper()
                            ]
                           ]

class SimulatedSpectrum_CC(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'CC TOCSY; CC (relayed)'
    isotopeCodes        = ['13C', '13C']
    axisCodes           = ['C', 'C1']
    spectralWidths      = [190, 190]
    referenceValues     = [190, 190]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for c1atom in NEF_ATOM_NAMES.get('13C', []):
            for c2atom in NEF_ATOM_NAMES.get('13C', []):
                if c1atom != c2atom:
                    atomNameMappers = [AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:c1atom}),
                                        AtomNamesMapper(isotopeCode='13C', axisCode='C1', offsetNmrAtomNames={0:c2atom})]
                    peakMappers.append(atomNameMappers)

        return(peakMappers)


#--------------------------------------------------------------------------------------------
# 3D ExperimentTypes
#--------------------------------------------------------------------------------------------

class SimulatedSpectrum_HNCO(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HNCO'
    isotopeCodes        = ['1H', '13C', '15N']
    axisCodes           = ['Hn', 'C', 'Nh']
    spectralWidths      = [7, 30, 40]
    referenceValues     = [12, 190, 140]
    peakAtomNameMappers = [
                            [
                            HAtomNamesMapper(),
                            COM1AtomNamesMapper(),
                            NAtomNamesMapper()
                            ]
                        ]


class SimulatedSpectrum_HNCACO(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HNCACO'
    isotopeCodes        = ['1H', '13C', '15N']
    axisCodes           = ['Hn', 'C', 'Nh']
    spectralWidths      = [7, 30, 40]
    referenceValues     = [12, 190, 140]
    peakAtomNameMappers = [
                            ## first peak assignments
                            [
                                HAtomNamesMapper(),
                                COAtomNamesMapper(),
                                NAtomNamesMapper(),
                            ],
                            ## second peak assignments
                            [
                                HAtomNamesMapper(),
                                COM1AtomNamesMapper(),
                                NAtomNamesMapper()
                            ]
                            ## end peak assignments
                            ]

class SimulatedSpectrum_HNCA(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HNCA'
    isotopeCodes        = ['1H', '13C', '15N']
    axisCodes           = ['Hn', 'C', 'Nh']
    spectralWidths      = [7, 35, 40]
    referenceValues     = [12, 75, 140]
    peakAtomNameMappers = [
                            ## first peak assignments
                            [
                            HAtomNamesMapper(),
                            CAAtomNamesMapper(),
                            NAtomNamesMapper()
                            ],
                            ## second peak assignments
                            [
                            HAtomNamesMapper(),
                            CAM1AtomNamesMapper(),
                            NAtomNamesMapper(),
                            ]
                            ## end peak assignments
                         ]

class SimulatedSpectrum_HNCOCA(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HNCOCA'
    isotopeCodes        = ['1H', '13C', '15N']
    axisCodes           = ['Hn', 'C', 'Nh']
    spectralWidths      = [7, 35, 40]
    referenceValues     = [12, 75, 140]
    peakAtomNameMappers = [
                            ## first peak assignments
                            [
                            HAtomNamesMapper(),
                            CAM1AtomNamesMapper(),
                            NAtomNamesMapper(),
                            ]
                            ## end peak assignments
                         ]

class SimulatedSpectrum_HNCACB(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HNCA/CB'
    isotopeCodes        = ['1H', '13C', '15N']
    axisCodes           = ['Hn', 'C', 'Nh']
    spectralWidths      = [7, 80, 40]
    referenceValues     = [12, 80, 140]
    peakAtomNameMappers = [
                            ## first peak assignments: CA (i)
                            [
                            HAtomNamesMapper(),
                            CAAtomNamesMapper(),
                            NAtomNamesMapper(),
                            ],
                            ## second peak assignments CB (i)
                            [
                            HAtomNamesMapper(),
                            CBAtomNamesMapper(),
                            NAtomNamesMapper(),
                            ],
                            ## third peak assignments: CA (i-1)
                            [
                            HAtomNamesMapper(),
                            CAM1AtomNamesMapper(),
                            NAtomNamesMapper(),
                            ],
                            ## forth peak assignments CB (i-1)
                            [
                            HAtomNamesMapper(),
                            CBM1AtomNamesMapper(),
                            NAtomNamesMapper(),
                            ]
                         ]

class SimulatedSpectrum_HBHAcoNH(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'HB/HAcoNH'
    isotopeCodes        = ['1H', '1H', '15N']
    axisCodes           = ['Hn', 'Hc', 'Nh']
    spectralWidths      = [7, 14, 40]
    referenceValues     = [12, 12, 140]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for hatom in NEF_ATOM_NAMES.get('1H', []):
            if 'A' in hatom or 'B' in hatom:
                    atomNameMappers = [AtomNamesMapper(isotopeCode='1H', axisCode='Hn', offsetNmrAtomNames={0: 'H'}),
                                       AtomNamesMapper(isotopeCode='1H', axisCode='Hc', offsetNmrAtomNames={-1: hatom}),
                                       AtomNamesMapper(isotopeCode='15N', axisCode='Nh', offsetNmrAtomNames={0: 'N'})]
                    peakMappers.append(atomNameMappers)

        return(peakMappers)


class SimulatedSpectrum_CANCO(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'CANCO'
    isotopeCodes        = ['13C', '15N', '13C']
    axisCodes           = ['C', 'N', 'CA']
    spectralWidths      = [30, 50, 35]
    referenceValues     = [190, 150, 75]
    peakAtomNameMappers = [
                            [
                            COM1AtomNamesMapper(),
                            ssNAtomNamesMapper(),
                            ssCAAtomNamesMapper()
                            ]
                        ]

class SimulatedSpectrum_CANcoCX(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'CANcoCX (relayed)'
    isotopeCodes        = ['13C', '15N', '13C']
    axisCodes           = ['C', 'N', 'CA']
    spectralWidths      = [190, 30, 35]
    referenceValues     = [190, 190, 75]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for catom in NEF_ATOM_NAMES.get('13C', []):
            atomNameMappers = [AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:catom}),
                                AtomNamesMapper(isotopeCode='15N', axisCode='N', offsetNmrAtomNames={+1: 'N'}),
                                AtomNamesMapper(isotopeCode='13C', axisCode='CA', offsetNmrAtomNames={+1: 'CA'})]
            peakMappers.append(atomNameMappers)

        return(peakMappers)

class SimulatedSpectrum_NCACX(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'NCACX (relayed)'
    isotopeCodes        = ['13C', '13C', '15N']
    axisCodes           = ['C', 'CA', 'N']
    spectralWidths      = [190, 35, 50]
    referenceValues     = [190, 75, 150]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for catom in NEF_ATOM_NAMES.get('13C', []):
            atomNameMappers = [AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:catom}),
                                AtomNamesMapper(isotopeCode='13C', axisCode='CA', offsetNmrAtomNames={0: 'CA'}),
                                AtomNamesMapper(isotopeCode='15N', axisCode='N', offsetNmrAtomNames={0: 'N'})]
            peakMappers.append(atomNameMappers)

        return(peakMappers)

class SimulatedSpectrum_NCOCX(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'NCOCX (relayed)'
    isotopeCodes        = ['13C', '13C', '15N']
    axisCodes           = ['C', 'CO', 'N']
    spectralWidths      = [190, 30, 50]
    referenceValues     = [190, 190, 150]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for catom in NEF_ATOM_NAMES.get('13C', []):
            atomNameMappers = [AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:catom}),
                                AtomNamesMapper(isotopeCode='13C', axisCode='CO', offsetNmrAtomNames={0: 'C'}),
                                AtomNamesMapper(isotopeCode='15N', axisCode='N', offsetNmrAtomNames={+1: 'N'})]
            peakMappers.append(atomNameMappers)

        return(peakMappers)



#--------------------------------------------------------------------------------------------
# 4D ExperimentTypes
#--------------------------------------------------------------------------------------------

class SimulatedSpectrum_CONCACX(SimulatedSpectrumByExperimentTypeABC):

    experimentType      = 'CANCOCX (relayed)'
    isotopeCodes        = ['13C', '13C', '15N', '13C']
    axisCodes           = ['C', 'CO', 'N', 'CA']
    spectralWidths      = [190, 30, 50, 35]
    referenceValues     = [190, 190, 150, 75]
    peakAtomNameMappers = None

    @staticmethod
    def _createAtomNameMappers():
        from ccpn.core.lib.AssignmentLib import NEF_ATOM_NAMES

        peakMappers = [[],]
        for catom in NEF_ATOM_NAMES.get('13C', []):
            atomNameMappers = [AtomNamesMapper(isotopeCode='13C', axisCode='C', offsetNmrAtomNames={0:catom}),
                                AtomNamesMapper(isotopeCode='13C', axisCode='CO', offsetNmrAtomNames={0: 'C'}),
                                AtomNamesMapper(isotopeCode='15N', axisCode='N', offsetNmrAtomNames={+1: 'N'}),
                                AtomNamesMapper(isotopeCode='13C', axisCode='CA', offsetNmrAtomNames={+1: 'CA'})]
            peakMappers.append(atomNameMappers)

        return(peakMappers)



#--------------------------------------------------------------------------------------------
#  Register the Various ExperimentType classes
#--------------------------------------------------------------------------------------------

CSL2SPECTRUM_DICT = OrderedDict([
                            (SimulatedSpectrum_1H.experimentType, SimulatedSpectrum_1H),
                            (SimulatedSpectrum_15N_HSQC.experimentType, SimulatedSpectrum_15N_HSQC),
                            (SimulatedSpectrum_13C_HSQC.experimentType, SimulatedSpectrum_13C_HSQC),
                            (SimulatedSpectrum_HNCO.experimentType, SimulatedSpectrum_HNCO),
                            (SimulatedSpectrum_HNCA.experimentType, SimulatedSpectrum_HNCA),
                            (SimulatedSpectrum_HNCOCA.experimentType, SimulatedSpectrum_HNCOCA),
                            (SimulatedSpectrum_HNCACB.experimentType, SimulatedSpectrum_HNCACB),
                            (SimulatedSpectrum_HBHAcoNH.experimentType, SimulatedSpectrum_HBHAcoNH),
                            (SimulatedSpectrum_CC.experimentType, SimulatedSpectrum_CC),
                            (SimulatedSpectrum_NCA.experimentType, SimulatedSpectrum_NCA),
                            (SimulatedSpectrum_NCO.experimentType, SimulatedSpectrum_NCO),
                            (SimulatedSpectrum_CANCO.experimentType, SimulatedSpectrum_CANCO),
                            (SimulatedSpectrum_CANcoCX.experimentType, SimulatedSpectrum_CANcoCX),
                            (SimulatedSpectrum_NCACX.experimentType, SimulatedSpectrum_NCACX),
                            (SimulatedSpectrum_NCOCX.experimentType, SimulatedSpectrum_NCOCX),
                            (SimulatedSpectrum_CONCACX.experimentType, SimulatedSpectrum_CONCACX),
                            ])
