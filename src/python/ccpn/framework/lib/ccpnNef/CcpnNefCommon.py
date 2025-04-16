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
__date__ = "$Date: 2020-07-01 13:38:47 +0000 (Wed, July 01, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import typing
from collections import OrderedDict
from ccpn.util.Logging import getLogger
from ccpn.core.Project import Project
from ccpn.util.nef import StarIo


def _getSaveFramesInOrder(dataBlock: StarIo.NmrDataBlock) -> OrderedDict:
    """Get saveframes in fixed reading order as Ordereddict(category:[saveframe,])"""
    result = OrderedDict(((x, []) for x in saveFrameReadingOrder))
    result['other'] = otherFrames = []
    for saveFrameName, saveFrame in dataBlock.items():
        sf_category = saveFrame.get('sf_category')
        ll = result.get(sf_category)
        if ll is None:
            ll = otherFrames
        ll.append(saveFrame)
    #
    for k, sfList in result.items():
        # sort the contents of each group
        sfList[:] = sorted(sfList, key=lambda sf: sf.name)
    return result


def _traverse(cls, project: Project, dataBlock: StarIo.NmrDataBlock,
              traverseFunc: typing.Callable,
              *, selection: dict | None = None,
              ):
    """Traverse the saveFrames in the correct order
    """
    result = OrderedDict()
    saveframeOrderedDict = _getSaveFramesInOrder(dataBlock)

    if metaDataFrame := dataBlock['nef_nmr_meta_data']:
        cls._saveFrameName = 'nef_nmr_meta_data'
        result[cls._saveFrameName] = traverseFunc(project, metaDataFrame)
        del saveframeOrderedDict['nef_nmr_meta_data']

    saveFrame = dataBlock.get('nef_molecular_system')
    if saveFrame:
        cls._saveFrameName = 'nef_molecular_system'
        result[cls._saveFrameName] = traverseFunc(project, saveFrame)
        del saveframeOrderedDict['nef_molecular_system']

    # Load assignments, or preload from shift-lists
    # to make sure '@' and '#' identifiers match the right serials
    saveFrame = dataBlock.get('ccpn_assignment')
    if saveFrame:
        cls._saveFrameName = 'ccpn_assignment'
        result[cls._saveFrameName] = traverseFunc(project, saveFrame)
        del saveframeOrderedDict['ccpn_assignment']

    for sf_category, saveFrames in saveframeOrderedDict.items():
        for saveFrame in saveFrames:
            saveFrameName = cls._saveFrameName = saveFrame.name

            if selection and saveFrameName not in selection:
                getLogger().debug2(f'>>>   -- skip saveframe {saveFrameName}')
                continue
            getLogger().debug2(f'>>> _traverse saveframe {saveFrameName}')

            if (val := traverseFunc(project, saveFrame)):
                # only set if there is a result?
                result[cls._saveFrameName] = val

    return result


def _parametersFromLoopRow(row, mapping):
    parameters = {}
    for tag, ccpnTag in mapping.items():
        val = row.get(tag)
        if val is not None:
            parameters[ccpnTag] = val
    #
    return parameters


#  - saveframe category names in reading order
# The order is significant, because setting of crosslinks relies on the order frames are read
# Frames are read in correct order regardless of how they are in the file
saveFrameReadingOrder = [
    'nef_nmr_meta_data',
    'nef_molecular_system',
    'ccpn_sample',
    'ccpn_substance',
    'ccpn_assignment',
    'nef_chemical_shift_list',
    'ccpn_dataset',
    'nef_distance_restraint_list',
    'nef_dihedral_restraint_list',
    'nef_rdc_restraint_list',
    'nef_nmr_spectrum',
    'nef_peak_restraint_links',
    'ccpn_complex',
    'ccpn_spectrum_group',
    'ccpn_restraint_list',
    # 'ccpn_peak_cluster_list',
    'ccpn_notes',
    'ccpn_distance_restraint_violation_list',
    'ccpn_dihedral_restraint_violation_list',
    'ccpn_rdc_restraint_violation_list',
    'ccpn_datatable',
    'ccpn_collections',
    'ccpn_additional_data',
    'ccpn_parameter',
    'ccpn_logging'
    ]

# Saveframe writing order - must start with official 'nef_' frames
saveFrameWritingOrder = ([x for x in saveFrameReadingOrder if x.startswith('nef_')] +
                         [x for x in saveFrameReadingOrder if not x.startswith('nef_')])

# NEf to CCPN tag mapping (and tag order)
#
# Contents are:
# Nef2CcpnMap = {saveframe_or_loop_category:contents}
# contents = {tag:ccpn_tag_or_None}
# loopMap = {tag:ccpn_tag}
#
# Loops are entered as saveFrame contents with their category as tag and 'ccpn_tag' None
# and at the top level under their category name
# This relies on loop categories being unique, both at the top level, and among the item
# names within a saveframe

# Sentinel value - MUST evaluate as False
_isALoop = ()

# This dictionary is used directly to control what is read from and written to
# NEF. The top level keys are the tags for saveframes and loops, which must
# either have their own entries in the Reader 'imprters' dictionary, of (if loops)
# be read directly by the parent samveframe).
# The next level down describes saveframe attributes or loop elements.
#
# Each saveframe or loop row matches a wrapper object, and the nef2CcpnMap map
# is used to read and write starting at that object.
# There are several variants. Using nef_sequence as an example:
#
# ('residue_name','residueType') means that the NEF value is read AND written
#  to residue.residueType.
#
# ('chain_code','chain.shortName') means that the NEF value is set (for writing) automatically,
# but the code for reading from NEF and passing it into the project must be done by hand
#
# ('cis_peptide',None), means that the tag exists, but that both on reading and writing it
# must be handled  explicitly.
#
# values _isALoop have an obvious meaning
#
# Note the _parametersFromSaveFrame and _parametersFromLoopRow functions
# that make a parameters dictionary (for use in object creation), using these mappings

nef2CcpnMap = {
    'nef_nmr_meta_data'                     : OrderedDict((
        ('format_name', None),
        ('format_version', None),
        ('program_name', None),
        ('program_version', None),
        ('creation_date', None),
        ('uuid', None),
        ('coordinate_file_name', None),
        ('nef_related_entries', _isALoop),
        ('nef_program_script', _isALoop),
        ('nef_run_history', _isALoop),
        )),

    'nef_related_entries'                   : OrderedDict((
        ('database_name', None),
        ('database_accession_code', None),
        )),

    'nef_program_script'                    : OrderedDict((
        ('program_name', None),
        ('script_name', None),
        ('script', None),
        )),

    'nef_run_history'                       : OrderedDict((
        ('run_number', 'serial'),
        ('program_name', 'programName'),
        ('program_version', 'programVersion'),
        ('script_name', 'scriptName'),
        ('script', 'script'),
        ('ccpn_input_uuid', 'inputDataUuid'),
        ('ccpn_output_uuid', 'outputDataUuid'),
        # ('ccpn_date', 'date'),
        # ('ccpn_stream_id', 'date'),
        # ('ccpn_saveframe', 'saveframe'),
        # ('ccpn_comment', 'comment'),
        )),

    # new saveframes to handle ccpn specific logging
    'ccpn_logging'                          : OrderedDict((
        ('ccpn_history', _isALoop),
        )),

    'ccpn_history'                          : OrderedDict((
        ('date', 'date'),
        ('username', 'username'),
        ('program_name', 'program_name'),
        ('program_version', 'program_version'),
        ('script_name', 'script_name'),
        ('input_uuid', 'input_uuid'),
        ('saveframe', 'saveframe'),
        ('comment', 'comment'),
        )),

    'nef_molecular_system'                  : OrderedDict((
        ('nef_sequence', _isALoop),
        ('nef_covalent_links', _isALoop),
        )),

    'nef_sequence'                          : OrderedDict((
        ('index', None),
        ('chain_code', 'chain.shortName'),
        ('sequence_code', 'sequenceCode'),
        ('residue_name', 'residueType'),
        ('linking', 'linking'),
        ('residue_variant', 'residueVariant'),
        ('cis_peptide', None),
        ('ccpn_comment', 'comment'),
        ('ccpn_chain_role', 'chain.role'),
        ('ccpn_compound_name', 'chain.compoundName'),
        ('ccpn_chain_comment', 'chain.comment'),
        )),

    'nef_covalent_links'                    : OrderedDict((
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        )),

    'nef_chemical_shift_list'               : OrderedDict((
        ('ccpn_serial', 'serial'),
        ('ccpn_auto_update', 'autoUpdate'),
        ('ccpn_is_simulated', 'isSimulated'),
        ('ccpn_comment', 'comment'),
        ('nef_chemical_shift', _isALoop),
        )),

    'nef_chemical_shift'                    : OrderedDict((
        ('chain_code', None),
        ('sequence_code', None),
        ('residue_name', None),
        ('atom_name', None),
        ('value', 'value'),
        ('value_uncertainty', 'valueError'),
        ('element', None),
        ('isotope_number', None),
        ('ccpn_figure_of_merit', 'figureOfMerit'),
        ('ccpn_static', None),
        ('ccpn_comment', 'comment')
        )),

    'nef_distance_restraint_list'           : OrderedDict((
        ('potential_type', 'potentialType'),
        ('restraint_origin', 'origin'),
        ('ccpn_tensor_chain_code', 'tensorChainCode'),
        ('ccpn_tensor_sequence_code', 'tensorSequenceCode'),
        ('ccpn_tensor_residue_name', 'tensorResidueType'),
        ('ccpn_tensor_magnitude', 'tensorMagnitude'),
        ('ccpn_tensor_rhombicity', 'tensorRhombicity'),
        ('ccpn_tensor_isotropic_value', 'tensorIsotropicValue'),
        ('ccpn_serial', 'serial'),
        # ('ccpn_dataset_id', 'structureData.id'),
        # ('ccpn_dataset_serial', 'structureData.serial'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('ccpn_unit', 'unit'),
        ('ccpn_comment', 'comment'),
        ('nef_distance_restraint', _isALoop),
        )),

    'nef_distance_restraint'                : OrderedDict((
        ('index', None),
        ('restraint_id', 'restraint.serial'),
        ('restraint_combination_id', 'combinationId'),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('weight', 'weight'),
        ('target_value', 'targetValue'),
        ('target_value_uncertainty', 'error'),
        ('lower_linear_limit', 'additionalLowerLimit'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('upper_linear_limit', 'additionalUpperLimit'),
        ('ccpn_figure_of_merit', 'restraint.figureOfMerit'),
        ('ccpn_comment', 'restraint.comment'),
        )),

    'nef_dihedral_restraint_list'           : OrderedDict((
        ('potential_type', 'potentialType'),
        ('restraint_origin', 'origin'),
        ('ccpn_tensor_chain_code', 'tensorChainCode'),
        ('ccpn_tensor_sequence_code', 'tensorSequenceCode'),
        ('ccpn_tensor_residue_name', 'tensorResidueType'),
        ('ccpn_tensor_magnitude', 'tensorMagnitude'),
        ('ccpn_tensor_rhombicity', 'tensorRhombicity'),
        ('ccpn_tensor_isotropic_value', 'tensorIsotropicValue'),
        ('ccpn_serial', 'serial'),
        # ('ccpn_dataset_id', 'structureData.id'),
        # ('ccpn_dataset_serial', 'structureData.serial'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('ccpn_unit', 'unit'),
        ('ccpn_comment', 'comment'),
        ('nef_dihedral_restraint', _isALoop),
        )),

    'nef_dihedral_restraint'                : OrderedDict((
        ('index', None),
        ('restraint_id', 'restraint.serial'),
        ('restraint_combination_id', 'combinationId'),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('chain_code_3', None),
        ('sequence_code_3', None),
        ('residue_name_3', None),
        ('atom_name_3', None),
        ('chain_code_4', None),
        ('sequence_code_4', None),
        ('residue_name_4', None),
        ('atom_name_4', None),
        ('weight', 'weight'),
        ('target_value', 'targetValue'),
        ('target_value_uncertainty', 'error'),
        ('lower_linear_limit', 'additionalLowerLimit'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('upper_linear_limit', 'additionalUpperLimit'),
        ('name', None),
        ('ccpn_figure_of_merit', 'restraint.figureOfMerit'),
        ('ccpn_comment', 'restraint.comment'),
        )),

    'nef_rdc_restraint_list'                : OrderedDict((
        ('potential_type', 'potentialType'),
        ('restraint_origin', 'origin'),
        ('tensor_magnitude', 'tensorMagnitude'),
        ('tensor_rhombicity', 'tensorRhombicity'),
        ('tensor_chain_code', 'tensorChainCode'),
        ('tensor_sequence_code', 'tensorSequenceCode'),
        ('tensor_residue_name', 'tensorResidueType'),
        ('ccpn_tensor_isotropic_value', 'tensorIsotropicValue'),
        ('ccpn_serial', 'serial'),
        # ('ccpn_dataset_id', 'structureData.id'),
        # ('ccpn_dataset_serial', 'structureData.serial'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('ccpn_unit', 'unit'),
        ('ccpn_comment', 'comment'),
        ('nef_rdc_restraint', _isALoop),
        )),

    'nef_rdc_restraint'                     : OrderedDict((
        ('index', None),
        ('restraint_id', 'restraint.serial'),
        ('restraint_combination_id', 'combinationId'),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('weight', 'weight'),
        ('target_value', 'targetValue'),
        ('target_value_uncertainty', 'error'),
        ('lower_linear_limit', 'additionalLowerLimit'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('upper_linear_limit', 'additionalUpperLimit'),
        ('scale', 'scale'),
        ('distance_dependent', 'isDistanceDependent'),
        ('ccpn_vector_length', 'restraint.vectorLength'),
        ('ccpn_figure_of_merit', 'restraint.figureOfMerit'),
        ('ccpn_comment', 'restraint.comment'),
        )),

    'nef_nmr_spectrum'                      : OrderedDict((
        ('num_dimensions', 'dimensionCount'),
        ('chemical_shift_list', None),
        ('experiment_classification', 'experimentType'),
        ('experiment_type', 'experimentName'),
        ('ccpn_reference_experiment_dimensions', 'referenceExperimentDimensions'),
        ('ccpn_positive_contour_count', 'positiveContourCount'),
        ('ccpn_positive_contour_base', 'positiveContourBase'),
        ('ccpn_positive_contour_factor', 'positiveContourFactor'),
        ('ccpn_positive_contour_colour', 'positiveContourColour'),
        ('ccpn_negative_contour_count', 'negativeContourCount'),
        ('ccpn_negative_contour_base', 'negativeContourBase'),
        ('ccpn_negative_contour_factor', 'negativeContourFactor'),
        ('ccpn_negative_contour_colour', 'negativeContourColour'),
        ('ccpn_slice_colour', 'sliceColour'),
        ('ccpn_spectrum_scale', 'scale'),
        ('ccpn_spinning_rate', 'spinningRate'),
        ('ccpn_spectrum_comment', 'comment'),
        ('ccpn_spectrum_file_path', 'filePath'),
        ('ccpn_file_type', 'dataFormat'),
        ('ccpn_file_scale_factor', 'scale'),
        ('ccpn_sample', None),

        # NOTE:ED - testing again
        # ('ccpn_peaklist_serial', 'serial'),
        # ('ccpn_peaklist_comment', 'comment'),
        # ('ccpn_peaklist_name', 'title'),
        # ('ccpn_peaklist_is_simulated', 'isSimulated'),
        # ('ccpn_peaklist_symbol_colour', 'symbolColour'),
        # ('ccpn_peaklist_symbol_style', 'symbolStyle'),
        # ('ccpn_peaklist_text_colour', 'textColour'),

        ('nef_spectrum_dimension', _isALoop),
        ('ccpn_spectrum_dimension', _isALoop),
        ('nef_spectrum_dimension_transfer', _isALoop),
        # ('ccpn_peak_list', _isALoop),
        ('nef_peak', _isALoop),
        ('ccpn_integral_list', _isALoop),
        ('ccpn_integral', _isALoop),
        ('ccpn_multiplet_list', _isALoop),
        ('ccpn_multiplet', _isALoop),
        ('ccpn_multiplet_peaks', _isALoop),
        ('ccpn_spectrum_hit', _isALoop),
        ('ccpn_spectrum_reference_substances', _isALoop),
        )),

    'nef_ccpn_spectrum_datastore'           : OrderedDict((
        # ('ccpn_spectrum_file_path', 'filePath'),
        ('ccpn_file_header_size', 'headerSize'),
        ('ccpn_file_number_type', 'isFloatData'),
        ('ccpn_file_complex_stored_by', 'complexStoredBy'),
        # ('ccpn_file_scale_factor', 'dataScale'),
        ('ccpn_file_is_big_endian', 'isBigEndian'),
        ('ccpn_file_byte_number', 'wordSize'),  # nByte
        ('ccpn_file_has_block_padding', 'hasBlockPadding'),
        ('ccpn_file_block_header_size', 'blockHeaderSize'),
        # ('ccpn_file_type', 'fileType'),
        )),

    'ccpn_spectrum_reference_substances'    : OrderedDict((
        ('serial', None),
        ('name', 'name'),
        ('labelling', 'labelling'),
        )),

    'nef_spectrum_dimension'                : OrderedDict((
        ('dimension_id', None),
        ('axis_unit', 'axisUnits'),
        ('axis_code', 'isotopeCodes'),
        ('spectrometer_frequency', 'spectrometerFrequencies'),
        ('spectral_width', 'spectralWidths'),
        ('value_first_point', 'referenceValues'),
        ('folding', None),
        ('absolute_peak_positions', None),
        ('is_acquisition', None),
        ('ccpn_axis_code', 'axisCodes'),
        )),

    # NB PseudoDimensions are not yet supported
    'ccpn_spectrum_dimension'               : OrderedDict((
        ('dimension_id', None),
        ('point_count', 'pointCounts'),
        ('reference_point', None),
        ('total_point_count', None),
        ('assignment_tolerance', 'assignmentTolerances'),
        ('lower_aliasing_limit', None),
        ('higher_aliasing_limit', None),
        ('measurement_type', 'measurementTypes'),
        ('phase_0', 'phases0'),
        ('phase_1', 'phases1'),
        ('window_function', 'windowFunctions'),
        ('lorentzian_broadening', 'lorentzianBroadenings'),
        ('gaussian_broadening', 'gaussianBroadenings'),
        ('sine_window_shift', 'sineWindowShifts'),
        )),

    'nef_spectrum_dimension_transfer'       : OrderedDict((
        ('dimension_1', None),
        ('dimension_2', None),
        ('transfer_type', None),
        ('is_indirect', None),
        )),

    # NOTE:ED - testing peakList per spectrum
    'ccpn_peak_list'                        : OrderedDict((
        ('peak_list_serial', 'serial'),
        ('comment', 'comment'),
        ('name', 'title'),
        ('is_simulated', 'isSimulated'),
        ('symbol_colour', 'symbolColour'),
        ('symbol_style', 'symbolStyle'),
        ('text_colour', 'textColour'),
        )),
    # NOTE:ED - added for older nef when no peakList information in the spectrum saveFrame
    'ccpn_no_peak_list'                     : OrderedDict((
        ('ccpn_peaklist_serial', 'serial'),
        ('ccpn_peaklist_comment', 'comment'),
        ('ccpn_peaklist_name', 'title'),
        ('ccpn_peaklist_is_simulated', 'isSimulated'),
        ('ccpn_peaklist_symbol_colour', 'symbolColour'),
        ('ccpn_peaklist_symbol_style', 'symbolStyle'),
        ('ccpn_peaklist_text_colour', 'textColour'),
        )),

    # NBNB: boxWidths and lineWidths are NOT included.
    'nef_peak'                              : OrderedDict((
        ('index', None),
        ('peak_id', 'serial'),
        ('volume', 'volume'),
        ('volume_uncertainty', 'volumeError'),
        ('height', 'height'),
        ('height_uncertainty', 'heightError'),
        ('position_1', None),
        ('position_uncertainty_1', None),
        ('position_2', None),
        ('position_uncertainty_2', None),
        ('position_3', None),
        ('position_uncertainty_3', None),
        ('position_4', None),
        ('position_uncertainty_4', None),
        ('position_5', None),
        ('position_uncertainty_5', None),
        ('position_6', None),
        ('position_uncertainty_6', None),
        ('position_7', None),
        ('position_uncertainty_7', None),
        ('position_8', None),
        ('position_uncertainty_8', None),
        ('position_9', None),
        ('position_uncertainty_9', None),
        ('position_10', None),
        ('position_uncertainty_10', None),
        ('position_11', None),
        ('position_uncertainty_11', None),
        ('position_12', None),
        ('position_uncertainty_12', None),
        ('position_13', None),
        ('position_uncertainty_13', None),
        ('position_14', None),
        ('position_uncertainty_14', None),
        ('position_15', None),
        ('position_uncertainty_15', None),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('chain_code_3', None),
        ('sequence_code_3', None),
        ('residue_name_3', None),
        ('atom_name_3', None),
        ('chain_code_4', None),
        ('sequence_code_4', None),
        ('residue_name_4', None),
        ('atom_name_4', None),
        ('chain_code_5', None),
        ('sequence_code_5', None),
        ('residue_name_5', None),
        ('atom_name_5', None),
        ('chain_code_6', None),
        ('sequence_code_6', None),
        ('residue_name_6', None),
        ('atom_name_6', None),
        ('chain_code_7', None),
        ('sequence_code_7', None),
        ('residue_name_7', None),
        ('atom_name_7', None),
        ('chain_code_8', None),
        ('sequence_code_8', None),
        ('residue_name_8', None),
        ('atom_name_8', None),
        ('chain_code_9', None),
        ('sequence_code_9', None),
        ('residue_name_9', None),
        ('atom_name_9', None),
        ('chain_code_10', None),
        ('sequence_code_10', None),
        ('residue_name_10', None),
        ('atom_name_10', None),
        ('chain_code_11', None),
        ('sequence_code_11', None),
        ('residue_name_11', None),
        ('atom_name_11', None),
        ('chain_code_12', None),
        ('sequence_code_12', None),
        ('residue_name_12', None),
        ('atom_name_12', None),
        ('chain_code_13', None),
        ('sequence_code_13', None),
        ('residue_name_13', None),
        ('atom_name_13', None),
        ('chain_code_14', None),
        ('sequence_code_14', None),
        ('residue_name_14', None),
        ('atom_name_14', None),
        ('chain_code_15', None),
        ('sequence_code_15', None),
        ('residue_name_15', None),
        ('atom_name_15', None),
        ('ccpn_figure_of_merit', 'figureOfMerit'),
        ('ccpn_linked_integral', None),
        ('ccpn_annotation', 'annotation'),
        ('ccpn_comment', 'comment'),
        # NOTE:ED - testing multiple peakLists per spectrum
        ('ccpn_peak_list_serial', 'peakList.serial'),
        )),

    # NB SpectrumHit crosslink to sample and sampleComponent are derived
    # And need not be stored here.
    'ccpn_spectrum_hit'                     : OrderedDict((
        ('ccpn_substance_name', 'substanceName'),
        ('ccpn_pseudo_dimension_number', 'pseudoDimensionNumber'),
        ('ccpn_point_number', 'pointNumber'),
        ('ccpn_figure_of_merit', 'figureOfMerit'),
        ('ccpn_merit_code', 'meritCode'),
        ('ccpn_normalised_change', 'normalisedChange'),
        ('ccpn_is_confirmed_', 'isConfirmed'),
        ('ccpn_concentration', 'concentration'),
        ('ccpn_', 'concentrationError'),
        ('ccpn_concentration_uncertainty', 'concentrationUnit'),
        ('ccpn_comment', 'comment'),
        )),

    'nef_peak_restraint_links'              : OrderedDict((
        ('nef_peak_restraint_link', _isALoop),
        )),

    'nef_peak_restraint_link'               : OrderedDict((
        ('nmr_spectrum_id', None),
        ('peak_id', None),
        ('restraint_list_id', None),
        ('restraint_id', None),
        )),

    'ccpn_complex'                          : OrderedDict((
        ('name', 'name'),
        ('ccpn_complex_chain', _isALoop),
        )),

    'ccpn_complex_chain'                    : OrderedDict((
        ('complex_chain_code', None),
        )),

    'ccpn_spectrum_group'                   : OrderedDict((
        ('name', 'name'),
        ('ccpn_group_spectrum', _isALoop),
        )),

    'ccpn_group_spectrum'                   : OrderedDict((
        ('nmr_spectrum_id', None),
        )),

    'ccpn_integral_list'                    : OrderedDict((
        ('serial', 'serial'),
        ('name', 'title'),
        ('symbol_colour', 'symbolColour'),
        ('text_colour', 'textColour'),
        ('comment', 'comment'),
        )),

    'ccpn_integral'                         : OrderedDict((
        ('integral_list_serial', 'integralList.serial'),
        ('integral_serial', 'serial'),
        ('value', 'value'),
        ('value_uncertainty', 'valueError'),
        # ('volume', 'volume'),
        # ('volume_uncertainty', 'volumeError'),
        # ('height', 'height'),
        # ('height_uncertainty', 'heightError'),
        ('offset', 'offset'),
        ('figure_of_merit', 'figureOfMerit'),
        ('constraint_weight', 'constraintWeight'),
        # ('position', 'position'),
        # ('position_uncertainty', 'positionError'),
        ('slopes', 'slopes'),
        ('limits', 'limits'),
        ('point_limits', 'pointLimits'),
        ('ccpn_linked_peak', None),
        ('annotation', 'annotation'),
        ('comment', 'comment'),
        )),

    'ccpn_multiplet_list'                   : OrderedDict((
        ('serial', 'serial'),
        ('name', 'title'),
        ('symbol_colour', 'symbolColour'),
        ('text_colour', 'textColour'),
        ('comment', 'comment'),
        )),

    'ccpn_multiplet'                        : OrderedDict((
        ('multiplet_list_serial', 'multipletList.serial'),
        ('multiplet_serial', 'serial'),
        ('height', 'height'),
        ('height_uncertainty', 'heightError'),
        ('volume', 'volume'),
        ('volume_uncertainty', 'volumeError'),
        ('offset', 'offset'),
        ('figure_of_merit', 'figureOfMerit'),
        ('constraint_weight', 'constraintWeight'),
        ('position', 'position'),
        ('position_uncertainty', 'positionError'),
        ('slopes', 'slopes'),
        ('limits', 'limits'),
        ('point_limits', 'pointLimits'),
        ('annotation', 'annotation'),
        ('comment', 'comment'),
        )),

    'ccpn_multiplet_peaks'                  : OrderedDict((
        ('multiplet_list_serial', None),  #'multiplet.multipletList.serial'),
        ('multiplet_serial', None),  #, 'multiplet.serial'),
        ('peak_spectrum', 'peakList.spectrum.name'),
        ('peak_list_serial', 'peakList.serial'),
        ('peak_serial', 'serial'),
        # ('peak_pid', 'pid'),
        )),

    # 'ccpn_peak_cluster_list'                : OrderedDict((
    #     ('ccpn_peak_cluster', _isALoop),
    #     ('ccpn_peak_cluster_peaks', _isALoop),
    #     )),
    #
    # 'ccpn_peak_cluster'                     : OrderedDict((
    #     ('serial', 'serial'),
    #     ('annotation', 'annotation'),
    #     )),
    #
    # 'ccpn_peak_cluster_peaks'               : OrderedDict((
    #     ('peak_cluster_serial', None),
    #     ('peak_spectrum', 'peakList.spectrum.name'),
    #     ('peak_list_serial', 'peakList.serial'),
    #     ('peak_serial', 'serial'),
    #     # ('peak_pid', 'pid'),
    #     )),

    # NB Sample crosslink to spectrum is handled on the spectrum side
    'ccpn_sample'                           : OrderedDict((
        ('name', 'name'),
        ('pH', 'ph'),
        ('ionic_strength', 'ionicStrength'),
        ('amount', 'amount'),
        ('amount_unit', 'amountUnit'),
        ('is_hazardous', 'isHazardous'),
        ('is_virtual', 'isVirtual'),
        ('creation_date', 'creationDate'),
        ('batch_identifier', 'batchIdentifier'),
        ('plate_identifier', 'plateIdentifier'),
        ('row_number', 'rowNumber'),
        ('column_number', 'columnNumber'),
        ('comment', 'comment'),
        ('ccpn_sample_component', _isALoop),
        )),

    'ccpn_sample_component'                 : OrderedDict((
        ('name', 'name'),
        ('labelling', 'labelling'),
        ('role', 'role'),
        ('concentration', 'concentration'),
        ('concentration_error', 'concentrationError'),
        ('concentration_unit', 'concentrationUnit'),
        ('purity', 'purity'),
        ('comment', 'comment'),
        )),

    'ccpn_substance'                        : OrderedDict((
        ('name', 'name'),
        ('labelling', 'labelling'),
        ('substance_type', None),
        ('user_code', 'userCode'),
        ('smiles', 'smiles'),
        ('inchi', 'inChi'),
        ('cas_number', 'casNumber'),
        ('empirical_formula', 'empiricalFormula'),
        ('sequence_string', None),
        ('mol_type', None),
        ('start_number', None),
        ('is_cyclic', None),
        ('molecular_mass', 'molecularMass'),
        ('atom_count', 'atomCount'),
        ('bond_count', 'bondCount'),
        ('ring_count', 'ringCount'),
        ('h_bond_donor_count', 'hBondDonorCount'),
        ('h_bond_acceptor_count', 'hBondAcceptorCount'),
        ('polar_surface_area', 'polarSurfaceArea'),
        ('log_partition_coefficient', 'logPartitionCoefficient'),
        ('comment', 'comment'),
        ('ccpn_substance_synonym', _isALoop),
        ('ccpn_substance_reference_spectra', _isALoop)
        )),

    'ccpn_substance_reference_spectra'      : OrderedDict((
        ('nmr_spectrum_id', None),
        )),

    'ccpn_substance_synonym'                : OrderedDict((
        ('synonym', None),
        )),

    'ccpn_assignment'                       : OrderedDict((
        ('nmr_chain', _isALoop),
        ('nmr_residue', _isALoop),
        ('nmr_atom', _isALoop),
        )),

    'nmr_chain'                             : OrderedDict((
        ('short_name', 'shortName'),
        ('serial', None),
        ('label', 'label'),
        ('is_connected', 'isConnected'),
        ('comment', 'comment'),
        )),

    'nmr_residue'                           : OrderedDict((
        ('chain_code', 'nmrChain.shortName'),
        ('sequence_code', 'sequenceCode'),
        # ('residue_name',None),
        ('residue_name', 'residueType'),
        ('serial', None),
        ('comment', 'comment'),
        )),

    'nmr_atom'                              : OrderedDict((
        ('chain_code', 'nmrResidue.nmrChain.shortName'),
        ('sequence_code', 'nmrResidue.sequenceCode'),
        ('serial', None),
        ('name', 'name'),
        ('isotope_code', 'isotopeCode'),
        ('comment', 'comment'),
        )),

    'ccpn_dataset'                          : OrderedDict((
        ('serial', 'serial'),
        ('name', 'name'),
        ('program_name', 'programName'),
        ('program_version', 'programVersion'),
        ('data_path', 'dataPath'),
        ('creation_date', None),
        ('uuid', 'uuid'),
        ('comment', 'comment'),
        ('ccpn_calculation_step', _isALoop),
        ('ccpn_calculation_data', _isALoop),
        )),

    'ccpn_calculation_step'                 : OrderedDict((
        ('serial', None),
        ('program_name', 'programName'),
        ('program_version', 'programVersion'),
        ('script_name', 'scriptName'),
        ('script', 'script'),
        ('input_data_uuid', 'inputDataUuid'),
        ('output_data_uuid', 'outputDataUuid'),
        )),

    'ccpn_calculation_data'                 : OrderedDict((
        ('data_name', 'name'),
        ('attached_object_pid', 'attachedObjectPid'),
        )),

    # saveframe to handle dataSet.data storage
    'ccpn_parameter'                        : OrderedDict((
        # ('ccpn_dataset_id', 'structureData'),
        # ('ccpn_dataset_serial', 'serial'),
        # ('ccpn_dataset_id', 'structureData.id'),
        # ('ccpn_dataset_serial', 'structureData.serial'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('ccpn_data_id', 'name'),
        ('ccpn_parameter_name', 'parameterName'),
        ('ccpn_value', 'value'),
        ('ccpn_dataframe', _isALoop),
        )),

    # saveframe to handle dataSet.data storage
    # holds a pandas dataframe - structure is loaded from loop.data, columns not explicitly required
    'ccpn_dataframe'                        : OrderedDict((
    )),

    'ccpn_restraint_list'                   : OrderedDict((
        ('potential_type', 'potentialType'),
        ('restraint_origin', 'origin'),
        ('tensor_chain_code', 'tensorChainCode'),
        ('tensor_sequence_code', 'tensorSequenceCode'),
        ('tensor_residue_name', 'tensorResidueType'),
        ('tensor_magnitude', 'tensorMagnitude'),
        ('tensor_rhombicity', 'tensorRhombicity'),
        ('tensor_isotropic_value', 'tensorIsotropicValue'),
        ('name', 'name'),
        ('restraint_type', 'restraintType'),
        ('restraint_item_length', 'restraintItemLength'),
        ('unit', 'unit'),
        ('measurement_type', 'measurementType'),
        ('comment', 'comment'),
        ('ccpn_serial', 'serial'),
        # ('ccpn_dataset_id', 'structureData.id'),
        # ('ccpn_dataset_serial', 'structureData.serial'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('ccpn_restraint', _isALoop),
        )),

    'ccpn_restraint'                        : OrderedDict((
        ('index', None),
        ('restraint_id', 'restraint.serial'),
        ('restraint_combination_id', 'combinationId'),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('chain_code_3', None),
        ('sequence_code_3', None),
        ('residue_name_3', None),
        ('atom_name_3', None),
        ('chain_code_4', None),
        ('sequence_code_4', None),
        ('residue_name_4', None),
        ('atom_name_4', None),
        ('weight', 'weight'),
        ('target_value', 'targetValue'),
        ('target_value_uncertainty', 'error'),
        ('lower_linear_limit', 'additionalLowerLimit'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('upper_linear_limit', 'additionalUpperLimit'),
        ('scale', 'scale'),
        ('distance_dependent', 'isDistanceDependent'),
        ('name', None),
        ('vector_length', 'restraint.vectorLength'),
        ('figure_of_merit', 'restraint.figureOfMerit'),
        # NB This tag has 'ccpn' prefix to match corresponding nef restraint lists
        ('ccpn_comment', 'restraint.comment'),
        )),

    'ccpn_notes'                            : OrderedDict((
        ('ccpn_note', _isALoop),
        )),

    'ccpn_note'                             : OrderedDict((
        ('serial', None),
        ('name', 'name'),
        ('created', None),
        ('last_modified', None),
        ('text', 'text'),
        )),

    'ccpn_additional_data'                  : OrderedDict((
        ('ccpn_internal_data', _isALoop),
        )),

    'ccpn_internal_data'                    : OrderedDict((
        ('ccpn_object_pid', None),
        ('internal_data_string', None)
        )),

    'ccpn_datatable'                        : OrderedDict((
        ('ccpn_datatable_columns', None),
        ('ccpn_datatable_metadata', _isALoop),
        ('ccpn_datatable_data', _isALoop),
        )),

    'ccpn_datatable_metadata'               : OrderedDict((
        ('name', None),
        ('parameter', None)
        )),

    'ccpn_datatable_data'                   : OrderedDict((
    )),

    'ccpn_collections'                      : OrderedDict((
        ('ccpn_collection', _isALoop),
        )),

    'ccpn_collection'                       : OrderedDict((
        ('uniqueId', 'uniqueId'),
        ('name', 'name'),
        ('items', None),
        ('comment', 'comment'),
        )),

    'ccpn_distance_restraint_violation_list': OrderedDict((
        ('serial', 'serial'),
        ('name', 'name'),
        ('nef_spectrum', None),
        ('nef_restraint_list', 'restraintTable.id'),
        ('run_id', 'runId'),
        ('program', None),
        ('program_version', None),
        ('protocol', None),
        ('protocol_version', None),
        ('protocol_parameters', None),
        # ('ccpn_dataset_id', 'structureData.id'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('comment', 'comment'),
        ('ccpn_restraint_violation_list_columns', None),
        ('ccpn_restraint_violation_list_metadata', _isALoop),
        ('ccpn_distance_restraint_violation', _isALoop),
        )),

    'ccpn_dihedral_restraint_violation_list': OrderedDict((
        ('serial', 'serial'),
        ('name', 'name'),
        ('nef_spectrum', None),
        ('nef_restraint_list', 'restraintTable.id'),
        ('run_id', 'runId'),
        ('program', None),
        ('program_version', None),
        ('protocol', None),
        ('protocol_version', None),
        ('protocol_parameters', None),
        # ('ccpn_dataset_id', 'structureData.id'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('comment', 'comment'),
        ('ccpn_restraint_violation_list_columns', None),
        ('ccpn_restraint_violation_list_metadata', _isALoop),
        ('ccpn_dihedral_restraint_violation', _isALoop),
        )),

    'ccpn_rdc_restraint_violation_list'     : OrderedDict((
        ('serial', 'serial'),
        ('name', 'name'),
        ('nef_spectrum', None),
        ('nef_restraint_list', 'restraintTable.id'),
        ('run_id', 'runId'),
        ('program', None),
        ('program_version', None),
        ('protocol', None),
        ('protocol_version', None),
        ('protocol_parameters', None),
        # ('ccpn_dataset_id', 'structureData.id'),
        ('ccpn_structuredata_name', 'structureData.id'),
        ('comment', 'comment'),
        ('ccpn_restraint_violation_list_columns', None),
        ('ccpn_restraint_violation_list_metadata', _isALoop),
        ('ccpn_rdc_restraint_violation', _isALoop),
        )),

    'ccpn_restraint_violation_list_metadata': OrderedDict((
        ('name', None),
        ('parameter', None)
        )),

    'ccpn_distance_restraint_violation'     : OrderedDict((
        ('index', None),
        ('model_id', None),
        ('restraint_id', None),
        ('restraint_sub_id', None),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('weight', 'weight'),
        ('probability', 'probability'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('distance', 'distance'),
        ('violation', 'violation'),
        ('violation_file', None),
        ('structure_file', None),
        ('structure_index', None),
        ('nef_peak_id', 'peakID'),
        ('comment', None),
        )),

    'ccpn_dihedral_restraint_violation'     : OrderedDict((
        ('index', None),
        ('model_id', None),
        ('restraint_id', None),
        ('restraint_sub_id', None),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('chain_code_3', None),
        ('sequence_code_3', None),
        ('residue_name_3', None),
        ('atom_name_3', None),
        ('chain_code_4', None),
        ('sequence_code_4', None),
        ('residue_name_4', None),
        ('atom_name_4', None),
        ('weight', 'weight'),
        ('probability', 'probability'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('distance', 'distance'),
        ('violation', 'violation'),
        ('violation_file', None),
        ('structure_file', None),
        ('structure_index', None),
        ('nef_peak_id', 'peakID'),
        ('comment', None),
        )),

    'ccpn_rdc_restraint_violation'          : OrderedDict((
        ('index', None),
        ('model_id', None),
        ('restraint_id', None),
        ('restraint_sub_id', None),
        ('chain_code_1', None),
        ('sequence_code_1', None),
        ('residue_name_1', None),
        ('atom_name_1', None),
        ('chain_code_2', None),
        ('sequence_code_2', None),
        ('residue_name_2', None),
        ('atom_name_2', None),
        ('weight', 'weight'),
        ('probability', 'probability'),
        ('lower_limit', 'lowerLimit'),
        ('upper_limit', 'upperLimit'),
        ('distance', 'distance'),
        ('violation', 'violation'),
        ('violation_file', None),
        ('structure_file', None),
        ('structure_index', None),
        ('nef_peak_id', 'peakID'),
        ('comment', None),
        )),

    }


def _stripSpectrumName(value):
    if isinstance(value, str):
        ll = value.rsplit('`', 2)
        return ll[0]


def _stripSpectrumSerial(value):
    if isinstance(value, str):
        ll = value.rsplit('`', 2)
        if len(ll) == 3:
            # name is of form abc`xyz`
            try:
                return int(ll[1])
            except ValueError:
                pass


nef2CcpnClassNames = {
    'nef_nmr_meta_data'                     : None,
    'nef_sequence_chain_code'               : 'MC',
    'nef_sequence'                          : 'MC',
    'ccpn_sample'                           : 'SA',
    'ccpn_substance'                        : 'SU',
    'nmr_chain'                             : 'NC',
    'nef_chemical_shift_list'               : 'CL',
    'ccpn_dataset'                          : 'SD',
    'nef_distance_restraint_list'           : 'RT',
    'nef_dihedral_restraint_list'           : 'RT',
    'nef_rdc_restraint_list'                : 'RT',
    'nef_nmr_spectrum'                      : 'SP',
    'nef_peak_restraint_links'              : None,
    'ccpn_complex'                          : 'MX',
    'ccpn_spectrum_group'                   : 'SG',
    'ccpn_restraint_list'                   : 'RT',
    # 'ccpn_peak_cluster_list'                : '_PC',
    'ccpn_notes'                            : 'NO',
    'ccpn_note'                             : 'NO',
    'ccpn_distance_restraint_violation_list': 'VT',
    'ccpn_dihedral_restraint_violation_list': 'VT',
    'ccpn_rdc_restraint_violation_list'     : 'VT',
    'ccpn_datatable'                        : 'DT',
    'ccpn_collections'                      : 'CO',
    'ccpn_collection'                       : 'CO',
    'ccpn_additional_data'                  : None,
    'ccpn_parameter'                        : None,
    'ccpn_logging'                          : None,
    'nef_peak'                              : 'PL',
    'ccpn_peak_list'                        : 'PL',
    'ccpn_integral_list'                    : 'IL',
    'ccpn_multiplet_list'                   : 'ML',
    'ccpn_internal_data'                    : None,
    }
