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
__dateModified__ = "$dateModified: 2025-04-16 12:49:00 +0100 (Wed, April 16, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-07-01 13:14:51 +0000 (Wed, July 01, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing
from functools import partial
from collections import OrderedDict as OD
from typing import Optional
from ccpn.core.lib import Pid
from ccpn.util import Common as commonUtil
from ccpn.util.nef import StarIo
from ccpnmodel.ccpncore.lib import Constants as coreConstants
from ccpn.core.Project import Project
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Spectrum import Spectrum
from ccpn.core.Complex import Complex
from ccpn.core.PeakList import PeakList
from ccpn.core.Substance import Substance
from ccpn.core.Sample import Sample
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.RestraintTable import RestraintTable
from ccpn.util.Logging import getLogger
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.AttrDict import AttrDict
from ccpn.framework.lib.ccpnNef.CcpnNefCommon import (nef2CcpnMap, _isALoop, _parametersFromLoopRow, _stripSpectrumName,
                                                      _stripSpectrumSerial)


CONTENTATTR = '_content'


class CcpnNefContent:
    contentFuncs = {}
    error: typing.Callable
    _parametersFromSaveFrame: typing.Callable
    _dataBlock: dict

    def storeContent(self, source, objects: dict):
        """Update the ccpnContent log with the contents of the saveFrames/loops
        """
        if getattr(source, CONTENTATTR, None) is not None:
            # SHOULD only be called once for each saveFrame
            self.error(f'Source {source.name} already exists in content', source, None)
        else:
            setattr(source, CONTENTATTR, objects)

    @staticmethod
    def updateContent(source, objects: dict):
        """Update the ccpnContent log with the contents of the saveFrames/loops
        """
        if getattr(source, CONTENTATTR, None) is not None:
            try:
                attrib = getattr(source, CONTENTATTR, None) or AttrDict()
                setattr(source, CONTENTATTR, attrib | objects)  # double up for the minute
            except Exception as es:
                raise RuntimeError(f'Error updating dict {es} ({source})')
        else:
            setattr(source, CONTENTATTR, objects)

    #-----------------------------------------------------------------------------------------

    def _contentLoops(self, project: Project, saveFrame: StarIo.NmrSaveFrame, addLoopAttribs=None,
                      excludeList=(), **kwds):
        """Iterate over the loops in a saveFrame, and add to results"""
        result = {}
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if tag not in excludeList and ccpnTag == _isALoop:
                if loop := saveFrame.get(tag):
                    if not (content := self.contentFuncs.get(tag)):
                        getLogger().debug("    unknown loop category {} {}".format(saveFrame.category, tag))
                        continue
                    if addLoopAttribs:
                        dd = []
                        for name in addLoopAttribs:
                            dd.append(saveFrame.get(name))
                        result[tag] = content(self, project, loop, saveFrame, *dd, **kwds)
                    else:
                        result[tag] = content(self, project, loop, saveFrame, **kwds)

        self.storeContent(saveFrame, result)

    def _noLoopContent(self, project: Project, loop: StarIo.NmrLoop, *arg, **kwds):
        """Get contents of the loop
        This is a loop returning no information
        """
        return None

    def content_ccpn_assignment(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # the saveframe contains nothing but three loops:
        nmrChainLoopName = 'nmr_chain'
        nmrResidueLoopName = 'nmr_residue'
        nmrAtomLoopName = 'nmr_atom'
        nmrSequenceCodeName = 'nmr_sequence_codes'
        nmrAtomCodeName = 'nmr_atom_names'

        nmrChains = OrderedSet()
        nmrResidues = OrderedSet()
        nmrAtoms = OrderedSet()
        nmrSequenceCodes = OrderedSet()
        nmrAtomCodes = OrderedSet()

        # read nmr_chain loop - add the details to nmrChain list
        mapping = nef2CcpnMap.get(nmrChainLoopName) or {}

        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrChainLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['short_name']
            nmrChains.add(chainCode)

        # read nmr_residue loop - add the details to nmrChain/nmrResidue/nmrAtom lists
        tempResidueDict = {}
        mapping = nef2CcpnMap.get(nmrResidueLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrResidueLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['chain_code']
            sequenceCode = row['sequence_code']
            residueName = row['residue_name']
            nmrResidues.add((chainCode, sequenceCode, residueName))
            tempResidueDict[(chainCode, sequenceCode)] = residueName

            # NOTE:ED - keep a record of the serial/sequence code types
            if sequenceCode[0] == '@' and sequenceCode[1:].isdigit():
                nmrSequenceCodes.add(int(sequenceCode[1:]))

        # read nmr_residue loop - add the details to nmrChain/nmrResidue/nmrAtom lists
        tempResidueDict = {}
        mapping = nef2CcpnMap.get(nmrAtomLoopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in saveFrame[nmrAtomLoopName].data:
            parameters = _parametersFromLoopRow(row, map2)
            chainCode = row['chain_code']
            sequenceCode = row['sequence_code']
            name = row['name']
            nmrAtoms.add((chainCode, sequenceCode, tempResidueDict.get((chainCode, sequenceCode)), name))

            # NOTE:ED - keep a record of the serial/sequence code types
            if name[0:2] == '?@' and name[2:].isdigit():
                nmrAtomCodes.add(int(name[2:]))

        self.storeContent(saveFrame, {nmrChainLoopName   : nmrChains,
                                      nmrResidueLoopName : nmrResidues,
                                      nmrAtomLoopName    : nmrAtoms,
                                      nmrSequenceCodeName: nmrSequenceCodes,
                                      nmrAtomCodeName    : nmrAtomCodes,
                                      })

    contentFuncs['ccpn_assignment'] = content_ccpn_assignment
    contentFuncs['nmr_chain'] = _noLoopContent
    contentFuncs['nmr_residue'] = _noLoopContent
    contentFuncs['nmr_atom'] = _noLoopContent

    def content_ccpn_complex(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_complex saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        name = framecode[len(category) + 1:]  #parameters['name']
        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_complex'] = content_ccpn_complex

    def content_ccpn_complex_chain(self, parent: Complex, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_complex_chain loop"""
        chains = OrderedSet()
        for row in loop.data:
            chains.add(row.get('complex_chain_code'))

        return chains

    contentFuncs['ccpn_complex_chain'] = content_ccpn_complex_chain

    def content_ccpn_sample(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get the contents of ccpn_sample
        # ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        # mapping = nef2CcpnMap.get(category) or {}

        name = framecode[len(category) + 1:]
        # parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        result = {category: (name,)}

        self._contentLoops(project, saveFrame, addLoopAttribs=['name'])
        self.updateContent(saveFrame, result)

    # contents['ccpn_sample'] = partial(_contentLoops, addLoopAttribs=['name'])
    contentFuncs['ccpn_sample'] = content_ccpn_sample

    def content_ccpn_sample_component(self, parent: Sample, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                      sampleName: str = None) -> Optional[OrderedSet]:
        """Get the contents for ccpn_sample_component loop"""
        components = OrderedSet()

        if sampleName is None:
            self.error('Undefined sampleName', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)

            # NOTE:ED - need to check if 'labelling' removed from pid (which is should be)
            try:
                result = (sampleName, parameters['name'], parameters.get('labelling'))
                # componentName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
                components.add(result)
            except Exception as es:
                self.error('>>> content_ccpn_sample_component {}'.format(es), loop, None)

        return components

    contentFuncs['ccpn_sample_component'] = content_ccpn_sample_component

    def content_ccpn_logging(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get the contents of ccpn_logging
        # ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        name = framecode[len(category) + 1:]
        result = {category: (name,)}

        self._contentLoops(project, saveFrame, addLoopAttribs=['date'])
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_logging'] = content_ccpn_logging

    def content_ccpn_history(self, parent, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                             date: str = None) -> Optional[OrderedSet]:
        """Get the contents for ccpn_history loop"""
        components = OrderedSet()

        if date is None:
            self.error('Undefined ccpn_history', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            try:
                result = (date,)
                components.add(result)
            except Exception as es:
                self.error('>>> content_ccpn_history {}'.format(es), loop, None)

        return components

    contentFuncs['ccpn_history'] = content_ccpn_history

    def content_ccpn_dataset(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get the contents of ccpn_dataset
        # ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        name = framecode[len(category) + 1:]
        result = {category: (name,)}

        self._contentLoops(project, saveFrame, addLoopAttribs=['id'])
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_dataset'] = content_ccpn_dataset

    def content_ccpn_calculation_step(self, parent, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                      value: str = None) -> Optional[OrderedSet]:
        """Get the contents for ccpn_calculation_step loop"""
        components = OrderedSet()

        if value is None:
            self.error('Undefined ccpn_calculation_step', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            try:
                result = (value,)
                components.add(result)
            except Exception as es:
                self.error('>>> content_ccpn_calculation_step {}'.format(es), loop, None)

        return components

    contentFuncs['ccpn_calculation_step'] = content_ccpn_calculation_step

    def content_ccpn_calculation_data(self, parent, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                      value: str = None) -> Optional[OrderedSet]:
        """Get the contents for ccpn_calculation_data loop"""
        components = OrderedSet()

        if value is None:
            self.error('Undefined ccpn_calculation_data', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            try:
                result = (value,)
                components.add(result)
            except Exception as es:
                self.error('>>> content_ccpn_calculation_data {}'.format(es), loop, None)

        return components

    contentFuncs['ccpn_calculation_data'] = content_ccpn_calculation_data

    def content_ccpn_parameter(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        from ccpn.framework.lib.ccpnNef.CcpnNefIo import DATANAME

        # Get the contents of ccpn_parameter
        # ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        _name = f"{parameters.get('dataSet')}.{parameters.get('name')}:{parameters.get('parameterName')}"
        result = {category: (_name,)}

        self._contentLoops(project, saveFrame, addLoopAttribs=[DATANAME, 'ccpn_data_id', 'ccpn_parameter_name'])
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_parameter'] = content_ccpn_parameter

    def content_ccpn_dataframe(self, parent, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                               dataSet: str, name: str, key) -> Optional[OrderedSet]:
        """Get the contents for ccpn_dataframe loop"""
        components = OrderedSet()

        if not all((dataSet, name, key)):
            self.error('Undefined ccpn_dataframe', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            try:
                result = (f'{dataSet}.{name}:{key}',)
                components.add(result)
            except Exception as es:
                self.error('>>> content_ccpn_dataframe {}'.format(es), loop, None)

        return components

    contentFuncs['ccpn_dataframe'] = content_ccpn_dataframe

    def content_ccpn_substance(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_substance saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)

        substanceId = Pid.IDSEP.join(
                ('' if x is None else str(x)) for x in (parameters['name'], parameters.get('labelling')))
        result = {category: (substanceId,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_substance'] = content_ccpn_substance

    def content_ccpn_notes(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        notes = OrderedSet()

        loopName = 'ccpn_note'
        saveFrameName = saveFrame['sf_category']

        loop = saveFrame[loopName]
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            notes.add(parameters['name'])

        result = {saveFrameName: notes}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_notes'] = content_ccpn_notes
    contentFuncs['ccpn_note'] = _noLoopContent

    def content_ccpn_integral(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                              name=None, itemLength=None):
        integrals = OrderedSet()

        # mapping = nef2CcpnMap.get(loop.name) or {}
        # map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            # parameters = _parametersFromLoopRow(row, map2)
            integralListSerial = row.get('integral_list_serial')
            integralSerial = row.get('serial')
            result = (name, integralListSerial, integralSerial)
            # listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
            integrals.add(result)

        return integrals

    contentFuncs['ccpn_integral'] = content_ccpn_integral

    def content_ccpn_multiplet(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                               name=None, itemLength=None):
        multiplets = OrderedSet()

        # mapping = nef2CcpnMap.get(loop.name) or {}
        # map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            # parameters = _parametersFromLoopRow(row, map2)
            multipletListSerial = row.get('multiplet_list_serial')
            multipletSerial = row.get('serial')
            result = (name, multipletListSerial, multipletSerial)
            # listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
            multiplets.add(result)

        return multiplets

    contentFuncs['ccpn_multiplet'] = content_ccpn_multiplet

    def content_ccpn_multiplet_peaks(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_multiplet_peaks loop"""
        multipletPeaks = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            parameters['peak_list_serial'] = row.get('peak_list_serial')
            parameters['peak_spectrum'] = row.get('peak_spectrum')

            result = tuple(parameters[col] for col in ('peak_spectrum', 'peak_list_serial', 'serial'))
            multipletPeaks.add(result)

        return multipletPeaks

    contentFuncs['ccpn_multiplet_peaks'] = _noLoopContent

    # # def content_ccpn_peak_cluster_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
    # #     """Get the contents ccpn_peak_cluster_list saveFrame"""
    # #     serialList = 'ccpn_peak_cluster_serial'
    # #     results = {serialList   : OrderedSet()}
    # #
    # #     self._contentLoops(project, saveFrame)
    # #
    # #
    # #     self.updateContent(saveFrame, results)
    #
    # contents['ccpn_peak_cluster_list'] = _contentLoops

    # contents['ccpn_peak_cluster_list'] = content_ccpn_peak_cluster_list

    # def content_ccpn_peak_cluster(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
    #                               name=None, itemLength=None):
    #     peakClusters = OrderedSet()
    #     _serialName = 'ccpn_peak_cluster_serial'
    #     # _serialErrors = parentFrame._contents[_serialName] = OrderedSet()
    #
    #     mapping = nef2CcpnMap.get(loop.name) or {}
    #     map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
    #     for row in loop.data:
    #         parameters = _parametersFromLoopRow(row, map2)
    #         result = (parameters['serial'],)
    #         listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
    #         peakClusters.add(listName)
    #         # _serialErrors.add(str(parameters['serial']))  # add the serial list name - hack for the minute
    #
    #     return peakClusters
    #
    # contents['ccpn_peak_cluster'] = content_ccpn_peak_cluster

    # def content_ccpn_peak_cluster_peaks(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame):
    #     """Get the contents of ccpn_peak_cluster_peaks loop"""
    #     clusterPeaks = OrderedSet()
    #
    #     mapping = nef2CcpnMap.get(loop.name) or {}
    #     map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
    #     for row in loop.data:
    #         parameters = _parametersFromLoopRow(row, map2)
    #         parameters['peak_list_serial'] = row.get('peak_list_serial')
    #         parameters['peak_spectrum'] = row.get('peak_spectrum')
    #
    #         result = tuple(parameters[col] for col in ('peak_spectrum', 'peak_list_serial', 'serial'))
    #         clusterPeaks.add(result)
    #
    #     return clusterPeaks
    #
    # contents['ccpn_peak_cluster_peaks'] = content_ccpn_peak_cluster_peaks

    def content_ccpn_group_spectrum(self, parent: SpectrumGroup, loop: StarIo.NmrLoop,
                                    parentFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_group_spectrum loop"""
        spectra = OrderedSet()
        for row in loop.data:
            spectra.add(row.get('nmr_spectrum_id'))

        return spectra

    contentFuncs['ccpn_group_spectrum'] = content_ccpn_group_spectrum

    def content_ccpn_integral_list(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                   name=None, itemLength=None):
        integralLists = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            result = (name, parameters['serial'])
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
            integralLists.add(listName)

        return integralLists

    contentFuncs['ccpn_integral_list'] = content_ccpn_integral_list

    def content_ccpn_multiplet_list(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                    name=None, itemLength=None):
        multipletLists = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            result = (name, parameters['serial'])
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
            multipletLists.add(listName)

        return multipletLists

    contentFuncs['ccpn_multiplet_list'] = content_ccpn_multiplet_list

    def content_ccpn_peak_list(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                               name=None, itemLength=None):
        peakLists = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            result = (name, parameters['serial'])
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in result)
            peakLists.add(listName)

        return peakLists

    contentFuncs['ccpn_peak_list'] = content_ccpn_peak_list

    def content_ccpn_spectrum_group(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_spectrum_group saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}
        parameters, loopNames = self._parametersFromSaveFrame(saveFrame, mapping)
        name = framecode[len(category) + 1:]  #parameters['name']

        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_spectrum_group'] = content_ccpn_spectrum_group

    def content_nef_chemical_shift(self, parent: ChemicalShiftList, loop: StarIo.NmrLoop,
                                   parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        """Get the contents of nef_chemical_shift loop"""
        nmrAtoms = OrderedSet()

        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)
            tt = tuple(row.get(tag) for tag in ('chain_code', 'sequence_code', 'residue_name',
                                                'atom_name'))
            nmrAtoms.add(tt)

        return nmrAtoms

    contentFuncs['nef_chemical_shift'] = content_nef_chemical_shift

    def content_nef_chemical_shift_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of nef_chemical_shift_list saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # store the name of the chemicalShiftList
        name = framecode[len(category) + 1:]
        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['nef_chemical_shift_list'] = content_nef_chemical_shift_list

    def content_ccpn_datatable(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_datatable saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # store the name of the chemicalShiftList
        name = framecode[len(category) + 1:]
        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_datatable'] = content_ccpn_datatable

    def content_nef_covalent_links(self, project: Project, loop: StarIo.NmrLoop,
                                   parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        """get the contents of nef_covalent_links loop"""
        covalentLinks = OrderedSet()

        for row in loop.data:
            id1 = Pid.createId(*(row[x] for x in ('chain_code_1', 'sequence_code_1',
                                                  'residue_name_1', 'atom_name_1',)))
            id2 = Pid.createId(*(row[x] for x in ('chain_code_2', 'sequence_code_2',
                                                  'residue_name_2', 'atom_name_2',)))
            covalentLinks.add((id1, id2))

        return covalentLinks

    contentFuncs['nef_covalent_links'] = content_nef_covalent_links

    def content_nef_molecular_system(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents nef_molecular_system saveFrame"""
        # read nmr_sequence loop
        chainCode = 'nef_sequence_chain_code'
        compoundName = 'ccpn_compound_name'
        nefSequence = 'nef_sequence'

        results = {chainCode   : OrderedSet(),
                   compoundName: OrderedSet()}

        mapping = nef2CcpnMap.get(nefSequence) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        _sequence = saveFrame.get(nefSequence)
        data = _sequence.data if _sequence and hasattr(_sequence, 'data') else []
        for row in data:
            results[chainCode].add(row['chain_code'])
            if row.get(compoundName):
                results[compoundName].add(row.get(compoundName))

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, results)

    contentFuncs['nef_molecular_system'] = content_nef_molecular_system

    def content_nef_nmr_spectrum(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        # Get ccpn-to-nef mapping for saveframe
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        mapping = nef2CcpnMap.get(category) or {}

        # Get peakList parameters and make peakList
        peakListParameters, dummy = self._parametersFromSaveFrame(saveFrame, mapping)

        # Get name from spectrum parameters, or from the framecode
        spectrumName = framecode[len(category) + 1:]
        # peakListSerial = _stripSpectrumSerial(spectrumName) or peakListParameters.get('serial') or 1
        spectrumName = _stripSpectrumName(spectrumName)

        result = {category: OrderedSet([spectrumName]), }
        # 'nef_peak_list': OrderedSet([peakListParameters['serial']])}

        # # NOTE:ED - this is a hack to get the peakLists into a list
        # if saveFrame.get('nef_peak'):
        #     content = self.contents['nef_peak']
        #     result['nef_peak'] = content(self, project, saveFrame.get('nef_peak'), saveFrame, name=spectrumName)
        #     content = self.contents['nef_peaks']
        #     result['nef_peaks'] = content(self, project, saveFrame.get('nef_peak'), saveFrame, name=spectrumName)

        self._contentLoops(project, saveFrame, name=spectrumName, itemLength=saveFrame['num_dimensions'],
                           excludeList=('nef_spectrum_dimension', 'ccpn_spectrum_dimension',  #'nef_peak',
                                        'nef_spectrum_dimension_transfer',
                                        ))
        self.updateContent(saveFrame, result)

    contentFuncs['nef_nmr_spectrum'] = content_nef_nmr_spectrum

    def content_nef_peak(self, peakList: PeakList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                         name=None, itemLength: int = None):
        """Get the contents of nef_peak loop"""
        result = OrderedSet()

        # NOTE:ED - not correct yet, need 2 lists
        # peakListSerial = parentFrame['ccpn_peaklist_serial']
        # peakListSerial = parentFrame.get('ccpn_peaklist_serial') or 1
        _parentName = parentFrame['sf_framecode']
        _parentSerial = _stripSpectrumSerial(_parentName)

        # get the list of peaks
        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            # parameters = _parametersFromLoopRow(row, map2)
            peakListSerial = _parentSerial or \
                             parentFrame.get('ccpn_peaklist_serial') or \
                             row.get('ccpn_peak_list_serial') or 1  # may not be defined in the list

            # peakListSerial = parentFrame.get('ccpn_peaklist_serial') or \
            #                  row.get('ccpn_peak_list_serial') or \
            #                  _parentSerial or 1  # may not be defined in the list
            #
            # serial = parameters['serial']
            # result.add((name, peakListSerial, serial))

            # NOTE:ED - this is actually putting the peak list name into the list NOT the peak - nef_peak
            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [name, peakListSerial])
            result.add(listName)

            if (attrib := getattr(self._dataBlock, CONTENTATTR, None)) is None:
                # create a new temporary saveFrame
                attrib = AttrDict()
                setattr(self._dataBlock, CONTENTATTR, attrib)

            if not attrib.get('loop'):
                attrib.loop = StarIo.NmrLoop(name='_ccpn_peak_list', columns=('pid',))
                attrib.loopSet = OrderedSet()
            if listName not in attrib.loopSet:
                attrib.loopSet.add(listName)
                attrib.loop.newRow((listName,))

        return result

    def content_nef_peaks(self, peakList: PeakList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                          name=None, itemLength: int = None):
        """Get the contents of nef_peak loop"""
        result = OrderedSet()

        # NOTE:ED - not correct yet, need 2 lists
        # peakListSerial = parentFrame['ccpn_peaklist_serial']
        _parentName = parentFrame['sf_framecode']
        _parentSerial = _stripSpectrumSerial(_parentName)

        # get the list of peaks
        mapping = nef2CcpnMap.get(loop.name) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        for row in loop.data:
            parameters = _parametersFromLoopRow(row, map2)

            serial = parameters['serial']
            peakListSerial = _parentSerial or \
                             parentFrame['ccpn_peaklist_serial'] or \
                             row.get('ccpn_peak_list_serial') or 1  # may not be defined in the list
            # result.add((name, peakListSerial, serial))

            listName = Pid.IDSEP.join(('' if x is None else str(x)) for x in [name, peakListSerial, serial])
            result.add(listName)

        return result

    def content_nef_peak_assignments(self, peakList: PeakList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                     name=None, itemLength: int = None):
        """Get the contents of nef_peak_assignments from nef_peak loop"""
        result = OrderedSet()

        if itemLength is None:
            self.error('Undefined peak item length', loop, None)
            return None

        # get the list of assigned nmrAtoms
        mapping = nef2CcpnMap.get(loop.name) or {}
        max = itemLength + 1
        multipleAttributes = OD((
            ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
            ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
            ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
            ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
            ))

        defaultChainCode = self.defaultChainCode
        for row in loop.data:
            ll = [list(row.get(x) for x in y) for y in multipleAttributes.values()]

            idStrings = []
            for item in zip(*ll):
                if defaultChainCode is not None and item[0] is None:
                    # ChainCode missing - replace with default chain code
                    item = (defaultChainCode,) + item[1:]

                # pid = Pid.IDSEP.join(('' if x is None else str(x)) for x in item)

                if any(x is not None for x in item):
                    # ignore peaks that are not defined
                    result.add(item)

        return result

    contentFuncs['nef_peak'] = content_nef_peak
    contentFuncs['nef_peaks'] = content_nef_peaks
    contentFuncs['nef_peak_assignments'] = content_nef_peak_assignments

    def content_ccpn_spectrum_reference_substances(self, parent: Spectrum, loop: StarIo.NmrLoop,
                                                   parentFrame: StarIo.NmrSaveFrame, **kwargs):
        """Get the contents of ccpn_group_spectrum loop"""
        substances = OrderedSet()
        for row in loop.data:
            substances.add(row.get('serial'))
        return substances

    contentFuncs['ccpn_spectrum_reference_substances'] = content_ccpn_spectrum_reference_substances

    def content_ccpn_substance_reference_spectra(self, parent: Substance, loop: StarIo.NmrLoop,
                                                 parentFrame: StarIo.NmrSaveFrame, **kwargs):
        """Get the contents of ccpn_group_spectrum loop"""
        spectra = OrderedSet()
        for row in loop.data:
            spectra.add(row.get('nmr_spectrum_id'))
        return spectra

    contentFuncs['ccpn_substance_reference_spectra'] = content_ccpn_substance_reference_spectra

    def content_nef_restraint(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop,
                              parentFrame: StarIo.NmrSaveFrame,
                              itemLength: int = None) -> Optional[OrderedSet]:
        """Get the contents for nef_distance_restraint, nef_dihedral_restraint,
        nef_rdc_restraint and ccpn_restraint loops"""
        result = OrderedSet()

        if itemLength is None:
            self.error('Undefined restraint item length', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        max = itemLength + 1
        multipleAttributes = OD((
            ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
            ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
            ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
            ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
            ))

        defaultChainCode = self.defaultChainCode
        for row in loop.data:
            serial = row.get('restraint_id')

            result.add(serial)

            # ll = [list(row.get(x) for x in y) for y in multipleAttributes.values()]
            #
            # for item in zip(*ll):
            #     if defaultChainCode is not None and item[0] is None:
            #         # ChainCode missing - replace with default chain code
            #         item = (defaultChainCode,) + item[1:]
            #
            #     result.add(item)

        return result

    contentFuncs['nef_distance_restraint'] = partial(content_nef_restraint,
                                                     itemLength=coreConstants.constraintListType2ItemLength.get(
                                                             'Distance'))
    contentFuncs['nef_dihedral_restraint'] = partial(content_nef_restraint,
                                                     itemLength=coreConstants.constraintListType2ItemLength.get(
                                                             'Dihedral'))
    contentFuncs['nef_rdc_restraint'] = partial(content_nef_restraint,
                                                itemLength=coreConstants.constraintListType2ItemLength.get('Rdc'))

    # NOTE:ED - need to check this one
    contentFuncs['ccpn_restraint'] = partial(content_nef_restraint,
                                             itemLength=coreConstants.constraintListType2ItemLength.get('Distance'))

    def content_nef_restraint_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of nef_restraint_list saveFrame"""
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]
        dataSetSerial = saveFrame.get('ccpn_dataset_serial')
        if dataSetSerial is not None:
            ss = '`%s`' % dataSetSerial
            if name.startswith(ss):
                name = name[len(ss):]

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        import re

        regex = u'\`\d*`+?'
        name = re.sub(regex, '', name)  # substitute with ''

        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['nef_distance_restraint_list'] = content_nef_restraint_list  # could be _contentLoops
    contentFuncs['nef_dihedral_restraint_list'] = content_nef_restraint_list
    contentFuncs['nef_rdc_restraint_list'] = content_nef_restraint_list
    contentFuncs['ccpn_restraint_list'] = content_nef_restraint_list

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def content_ccpn_restraint_violation(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop,
                                         parentFrame: StarIo.NmrSaveFrame,
                                         itemLength: int = None) -> Optional[OrderedSet]:
        """Get the contents for ccpn_restraint_violation loops
        """
        result = OrderedSet()

        if itemLength is None:
            self.error('Undefined restraint item length', loop, None)
            return None

        mapping = nef2CcpnMap.get(loop.name) or {}
        max = itemLength + 1
        multipleAttributes = OD((
            ('chainCodes', tuple('chain_code_%s' % ii for ii in range(1, max))),
            ('sequenceCodes', tuple('sequence_code_%s' % ii for ii in range(1, max))),
            ('residueTypes', tuple('residue_name_%s' % ii for ii in range(1, max))),
            ('atomNames', tuple('atom_name_%s' % ii for ii in range(1, max))),
            ))

        for row in loop.data:
            serial = row.get('restraint_id')

            result.add(serial)

        return result

    contentFuncs['ccpn_distance_restraint_violation'] = partial(content_ccpn_restraint_violation,
                                                                itemLength=coreConstants.constraintListType2ItemLength.get(
                                                                        'Distance'))
    contentFuncs['ccpn_dihedral_restraint_violation'] = partial(content_ccpn_restraint_violation,
                                                                itemLength=coreConstants.constraintListType2ItemLength.get(
                                                                        'Dihedral'))
    contentFuncs['ccpn_rdc_restraint_violation'] = partial(content_ccpn_restraint_violation,
                                                           itemLength=coreConstants.constraintListType2ItemLength.get(
                                                                   'Rdc'))

    def content_ccpn_restraint_violation_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        """Get the contents of ccpn_distance_restraint_violation_list saveFrame
        """
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']

        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]
        dataSetSerial = saveFrame.get('ccpn_dataset_serial')
        if dataSetSerial is not None:
            ss = '`%s`' % dataSetSerial
            if name.startswith(ss):
                name = name[len(ss):]

        # ejb - need to remove the rogue `n` at the beginning of the name if it exists
        #       as it is passed into the namespace and gets added iteratively every save
        #       next three lines remove all occurrences of `n` from name
        import re

        regex = u'\`\d*`+?'
        name = re.sub(regex, '', name)  # substitute with ''

        result = {category: (name,)}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs[
        'ccpn_distance_restraint_violation_list'] = content_ccpn_restraint_violation_list  # could be _contentLoops
    contentFuncs[
        'ccpn_dihedral_restraint_violation_list'] = content_ccpn_restraint_violation_list  # could be _contentLoops
    contentFuncs['ccpn_rdc_restraint_violation_list'] = content_ccpn_restraint_violation_list  # could be _contentLoops

    contentFuncs['ccpn_restraint_violation_list_metadata'] = _noLoopContent

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def content_nef_sequence(self, project: Project, loop: StarIo.NmrLoop,
                             parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        """get contents of the nef_sequence loop"""
        residues = OrderedSet()

        chainData = {}
        self._exists = OrderedSet()
        for row in loop.data:
            chainCode = row['chain_code']
            ll = chainData.get(chainCode)
            if ll is None:
                chainData[chainCode] = [row]
            else:
                ll.append(row)

        defaultChainCode = None
        if None in chainData:
            defaultChainCode = 'A'
            # Replace chainCode None with default chainCode
            # Selecting the first value that is not already taken.
            while defaultChainCode in chainData:
                defaultChainCode = commonUtil.incrementName(defaultChainCode)
            chainData[defaultChainCode] = chainData.pop(None)
        self.defaultChainCode = defaultChainCode

        sequence2Chain = {}
        tags = ('residue_name', 'linking', 'residue_variant')
        for chainCode, rows in sorted(chainData.items()):
            compoundName = rows[0].get('ccpn_compound_name')
            role = rows[0].get('ccpn_chain_role')
            comment = rows[0].get('ccpn_chain_comment')
            for row in rows:
                if row.get('linking') == 'dummy':
                    row['residue_name'] = 'dummy.' + row['residue_name']

                residues.add((chainCode, row.get('sequence_code'),
                              row.get('residue_name')))  #, row.get('ccpn_compound_name')))

        # for row in loop.data:
        #     chainCode = row['chain_code']
        #     sequenceCode = row['sequence_code']
        #     residue = row['residue_name']
        #     compoundName = row['ccpn_compound_name']
        #     residues.add((chainCode, sequenceCode, residue, compoundName))

        return residues

    contentFuncs['nef_sequence'] = content_nef_sequence

    def content_nef_peak_restraint_links(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        category = saveFrame['sf_category']
        framecode = saveFrame['sf_framecode']
        # Get name from framecode, add type disambiguation, and correct for ccpn dataSetSerial addition
        name = framecode[len(category) + 1:]

        result = {category: (name or 'restraintLinks',)}  # should be 'name' but can only be one

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['nef_peak_restraint_links'] = content_nef_peak_restraint_links
    contentFuncs['nef_peak_restraint_link'] = _noLoopContent

    def traverseDataBlock(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                          traverseFunc: typing.Callable,
                          *, selection: dict | None = None):
        """Traverse the saveFrames in the correct order
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def _getContents(self, project, saveFrame: StarIo.NmrSaveFrame,
                     projectIsEmpty: bool = True,
                     selection: typing.Optional[dict] = None):
        """Get the contents of the saveFrame into _contents (if in selection, or always if selection is empty)
        """
        saveFrameName = saveFrame.name
        sf_category = saveFrame['sf_category']
        if (content := self.contentFuncs.get(sf_category)) is None:
            getLogger().debug("    unknown saveframe category {} {}".format(sf_category, saveFrameName))
        else:
            return content(self, project, saveFrame)

    def contentNef(self, project: Project, dataBlock: StarIo.NmrDataBlock,
                   projectIsEmpty: bool = True,
                   selection: typing.Optional[dict] = None):
        """Verify import of selection from dataBlock into existing/empty Project
        """
        # Initialise mapping dicts
        if not hasattr(self, '_dataSet2ItemMap') or projectIsEmpty:
            self._dataSet2ItemMap = {}
        if not hasattr(self, '_nmrResidueMap') or projectIsEmpty:
            self._nmrResidueMap = {}

        self.project = project
        self.defaultChainCode = None
        dataBlock._content = AttrDict()
        return self.traverseDataBlock(project, dataBlock, traverseFunc=partial(self._getContents,
                                                                               projectIsEmpty=projectIsEmpty,
                                                                               selection=selection))

    def content_ccpn_additional_data(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        objs = OrderedSet()

        loopName = 'ccpn_internal_data'
        saveFrameName = saveFrame['sf_category']

        loop = saveFrame.get(loopName)
        if loop:
            for row in loop.data:
                pid = row.get('ccpn_object_pid')
                objs.add(pid)

        result = {saveFrameName: objs}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_additional_data'] = content_ccpn_additional_data
    contentFuncs['ccpn_internal_data'] = _noLoopContent

    def content_ccpn_collections(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        collections = OrderedSet()

        loopName = 'ccpn_collection'
        saveFrameName = saveFrame['sf_category']

        loop = saveFrame.get(loopName)
        mapping = nef2CcpnMap.get(loopName) or {}
        map2 = dict(item for item in mapping.items() if item[1] and '.' not in item[1])
        if loop:
            for row in loop.data:
                parameters = _parametersFromLoopRow(row, map2)
                collections.add(parameters['name'])

        result = {saveFrameName: collections}

        self._contentLoops(project, saveFrame)
        self.updateContent(saveFrame, result)

    contentFuncs['ccpn_collections'] = content_ccpn_collections
    contentFuncs['ccpn_collection'] = _noLoopContent

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # these are the empty ones that need methods adding as required

    contentFuncs['nef_nmr_meta_data'] = _contentLoops
    contentFuncs['nef_related_entries'] = _noLoopContent
    contentFuncs['nef_program_script'] = _noLoopContent
    contentFuncs['nef_run_history'] = _noLoopContent
    contentFuncs['nef_spectrum_dimension_transfer'] = _noLoopContent
    contentFuncs['ccpn_spectrum_dimension'] = _noLoopContent
    contentFuncs['nef_spectrum_dimension'] = _noLoopContent
    contentFuncs['ccpn_substance_synonym'] = _noLoopContent

    contentFuncs['ccpn_datatable_data'] = _noLoopContent
    contentFuncs['ccpn_datatable_metadata'] = _noLoopContent
