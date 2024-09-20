
"""
Alpha version of a popup for setting up a structure calculation using Xplor-NIH calculations.
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$Author: Luca Mureddu $"
__dateModified__ = "$Date: 2021-04-27 16:04:57 +0100 (Tue, April 27, 2021) $"
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2021-04-27 16:04:57 +0100 (Tue, April 27, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown, ChemicalShiftListPulldown, ChainPulldown
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ListWidget import ListWidgetPair
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets import CheckBox
import os
import shutil

from datetime import datetime
from distutils.dir_util import copy_tree
from ccpn.ui.gui.widgets.FileDialog import OtherFileDialog
from ccpn.framework.Application import getApplication
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.framework.Version import applicationVersion
#!/usr/bin/env python3
import argparse
import string

# import pandas as pd
#from tabulate import tabulate
import sys
import pathlib
import re

from pynmrstar import Entry, Saveframe, Loop

with undoBlockWithoutSideBar():
    with notificationEchoBlocking():


        if '3.1' in applicationVersion:
            ccpnVersion310 = True
        else:
            ccpnVersion310 = False

        #
        # if (application.preferences.externalPrograms.get('xplor') is None) or (len(application.preferences.externalPrograms.get('xplor')) <2):
        #     showWarning('XPLOR PATH NOT SET UP', 'Please make sure you have set the path in preferences.')
        #     sys.exit()
        #
        # application = getApplication()
        #
        #
        # if application:
        #
        #     # This is an example folder from Xplor NIH distribution with scripts necessary for running calculations
        #     pathToXplorBinary = application.preferences.externalPrograms.get('xplor')
        #     xplorRootDirectory = os.path.dirname(os.path.dirname(pathToXplorBinary))
        #     pathToens2pdb = os.path.join(xplorRootDirectory, 'bin','ens2pdb')
        #
        #
        # def removeSpaces(txt):
        #     return ','.join(txt.split())
        #
        #
        # #This function is purely for removing lines from Xplor NIH peaks info, the original out.nef remains untouched.
        # def removeCommentsFromOutNef(xplorOutputDirectory):
        #     os.chdir(xplorOutputDirectory)
        #     dirWithXplorOutNef = os.path.basename(xplorOutputDirectory)
        #     if os.path.isfile(os.path.join(xplorOutputDirectory, 'out.nef')):
        #         if os.path.isfile(os.path.join(dirWithXplorOutNef+'_out.nef')) == False:
        #             outNefWithNoComments = open(dirWithXplorOutNef+'_out.nef', "a")
        #
        #             with open(os.path.join(xplorOutputDirectory, 'out.nef'), 'r') as nefFile:
        #                 for line in nefFile.readlines():
        #                     if line.startswith('#') == False:
        #                         outNefWithNoComments.write(line)
        #             nefFile.close()
        #             outNefWithNoComments.close()
        #     else: print('out.nef found')
        #     return dirWithXplorOutNef+'_out.nef'
        #
        #
        # def cleanupXplor(xplorOutputDirectory):
        #     os.chdir(xplorOutputDirectory)
        #
        #     pass1Path = os.path.join(xplorOutputDirectory,'pass1')
        #     pass2Path = os.path.join(xplorOutputDirectory,'pass2')
        #     pass3Path = os.path.join(xplorOutputDirectory,'pass3')
        #     logPath = os.path.join(xplorOutputDirectory,'xplor_log')
        #     fold = os.path.join(xplorOutputDirectory,'fold')
        #     spectra_pass_files = os.path.join(xplorOutputDirectory,'spectra_pass_files')
        #     talos= os.path.join(xplorOutputDirectory,'talos_files')
        #     xplorScripts = os.path.join(xplorOutputDirectory,'xplor_scripts')
        #
        #     directories = [#pass1Path,
        #                    pass2Path,
        #                    pass3Path,
        #                    logPath,
        #                    talos,fold,
        #                    xplorScripts,
        #                    spectra_pass_files]
        #
        #     for dir in directories:
        #         print(dir, os.path.isdir(dir))
        #         if os.path.isdir(dir) == False:
        #             os.mkdir(dir)
        #
        #     for file in os.listdir():
        #         currentPath = os.path.join(xplorOutputDirectory,file)
        #         print(currentPath)
        #
        #         if file.startswith('pass1_'):
        #             os.rename(currentPath, os.path.join(pass1Path,file))
        #         if file.startswith('pass2_'):
        #             os.rename(currentPath, os.path.join(pass2Path,file))
        #         if file.startswith('pass3_'):
        #             os.rename(currentPath, os.path.join(pass3Path,file))
        #         if file.startswith('xplor.log'):
        #             os.rename(currentPath, os.path.join(logPath,file))
        #         if file.startswith('fold_'):
        #             #print(os.path.isfile(currentPath))
        #             os.rename(currentPath, os.path.join(fold,file))
        #         if file.endswith('.py') or file.endswith('.sh') :
        #             os.rename(currentPath, os.path.join(xplorScripts,file))
        #         if file.endswith('.peaks') or file.endswith('Assignments') or file.endswith('exceptions'):
        #             os.rename(currentPath, os.path.join(spectra_pass_files, file))
        #         if file.endswith('.tab'):
        #             os.rename(currentPath, os.path.join(talos, file))
        #
        #     cleanedNef = os.path.join(xplorOutputDirectory,removeCommentsFromOutNef(xplorOutputDirectory))
        #     return cleanedNef
        #
        # def makeEnsemble(path):
        #     statsFileDir = os.path.join(path,'fold')
        #     statsFile = os.path.join(statsFileDir, 'fold_##.sa.stats')
        #
        #     f = open(statsFile)
        #
        #     start = False
        #
        #     filenames = []
        #     fitRMSD = []
        #     comparisonRMSD = []
        #
        #     for line in f.readlines():
        #         if "energy       RMSD       RMSD" in line:
        #             start = True
        #             continue
        #         if start == True:
        #             lineToRecord = removeSpaces(line).split(',')
        #             if len(lineToRecord) == 1:
        #                 start = False
        #                 continue
        #
        #             filenames.append(lineToRecord[0])
        #             fitRMSD.append(lineToRecord[1])
        #             comparisonRMSD.append(lineToRecord[2])
        #     f.close()
        #
        #     pdbFilesNames = ' '.join([str(elem) for elem in filenames])
        #     os.chdir(statsFileDir)
        #     print(os.getcwd())
        #
        #     command = pathToens2pdb + ' ' + pdbFilesNames + ' > ensemble.pdb'
        #     print(command)
        #
        #     os.system(command)
        #
        #     if os.path.isdir(os.path.join(statsFileDir, 'highestEnergy')):
        #         print('Directory Exists')
        #     else:
        #         os.mkdir(os.path.join(statsFileDir, 'highestEnergy'))
        #
        #     if os.path.isdir(os.path.join(statsFileDir, 'lowestEnergy')):
        #         print('Directory Exists')
        #     else:
        #         os.mkdir(os.path.join(statsFileDir, 'lowestEnergy'))
        #
        #     firstCif = True
        #     for filename in filenames:
        #
        #         for ending in ['', '.cif','.viols']:
        #             if (ending == '.cif') and (firstCif == True):
        #                 firstCif = False
        #
        #                 try:
        #                     os.chdir(statsFileDir)
        #                     shutil.copy(os.path.join(statsFileDir, filename+ending),
        #                               os.path.join(statsFileDir, 'lowestEnergyStructure.cif'))
        #
        #                     print(statsFileDir, filename+ending, '.... created lowestEnergyStructure.cif')
        #                 except:
        #                     stringText = '.... failed to create lowestEnergyStructure.cif (does the file exist?)'
        #                     MessageDialog.showWarning('', stringText)
        #                     print(stringText)
        #
        #             try:
        #                 os.chdir(statsFileDir)
        #                 os.rename(os.path.join(statsFileDir, filename+ending),
        #                           os.path.join(statsFileDir, 'lowestEnergy', filename+ending))
        #
        #                 print(statsFileDir, filename+ending, '.... moved')
        #             except:
        #                 stringText = filename +ending+ '.... move failed (does the file exist?)'
        #                 MessageDialog.showWarning('', stringText)
        #                 print(filename, '.... move failed (does the file exist?)')
        #
        #     os.chdir(statsFileDir)
        #     # List remining files in directory statsFileDir
        #     items = os.listdir(".")
        #     for fileName in items:
        #         #print(fileName + ' ****')
        #         if fileName == 'lowestEnergyStructure.cif':
        #             print(fileName)
        #             continue
        #         if fileName.endswith(".cif") or fileName.endswith(".sa") or fileName.endswith(
        #                 ".viols") and not fileName.endswith("pdb.viols"):
        #             os.rename(os.path.join(statsFileDir, fileName), os.path.join(statsFileDir, 'highestEnergy', fileName))
        #
        #     return
        #
        #
        # EXIT_ERROR = 1
        # UNUSED ='.'
        # filename_matcher=re.compile('fold_([0-9]+).sa.viols')
        # parser = None
        # range_split = re.compile('\.\.').split
        #
        # def exit_error(msg):
        #
        #         print(f'ERROR: {msg}')
        #         print(' exiting...')
        #         sys.exit(EXIT_ERROR)
        #
        # def read_args():
        #     global parser
        #     parser = argparse.ArgumentParser(description='convert xplor nOe violations to NEF')
        #
        #     parser.add_argument(metavar='<XPLOR>.viols', action='extend', nargs='+', dest='files')
        #
        #     parser.add_argument('-o', '--output-file', dest='output_file', default=None)
        #
        #     return parser.parse_args()
        #
        #
        #
        #
        # def collapse_name(names, depth=2):
        #
        #     digit_by_depth = {}
        #
        #
        #     for target in names:
        #
        #         for i in range(1, depth+1):
        #
        #             if target[-i].isdigit():
        #                 digit_by_depth.setdefault(-i,set()).add(target[-i])
        #
        #             else:
        #                 break
        #
        #     name_list = list(list(names)[0])
        #     for depth, unique_digits in digit_by_depth.items():
        #         if len(unique_digits) > 1:
        #             name_list[depth] = '%'
        #     result = ''.join(name_list)
        #
        #     result = collapse_right_repeated_string(result)
        #     if 'HN' in result: result = 'H'
        #     return result
        #
        #
        # def collapse_right_repeated_string(target, repeating='%'):
        #
        #     orig_length = len(target)
        #
        #     result = target.rstrip(repeating)
        #
        #     if len(result) < orig_length:
        #         result = result + repeating
        #
        #     return result
        #
        #
        # def viol_to_nef(file_handle, model, file_path): #, args):
        #     in_data = False
        #     results = {}
        #
        #     for line in file_handle:
        #
        #         if 'NOE restraints in potential term' in line:
        #             restraint_number = None
        #             sub_restraint_id = 0
        #             pair_number = 0
        #             current_selections = None
        #             current_fields = None
        #             index = 0
        #
        #             frame_name = line.split(':')[1].split('(')[0].strip()
        #             in_data = True
        #             lines = {}
        #             results[frame_name] = lines
        #
        #             while not line.startswith('-----'):
        #                 line = next(file_handle)
        #             line = next(file_handle)
        #
        #         if in_data and line.startswith('number of restraints'):
        #             in_data = False
        #             restraint_number = None
        #             pair_number = None
        #             index = 0
        #
        #         if in_data and len(line.strip()) == 0:
        #             continue
        #
        #         if in_data and '-- OR --' in line:
        #             sub_restraint_id += 1
        #             pair_number = 0
        #             continue
        #
        #         if in_data:
        #             line = line.strip()
        #
        #             line = _remove_violated_mark_if_present(line)
        #
        #             new_restraint_number = _get_id(line, restraint_number)
        #
        #             pair_number = 0 if new_restraint_number != restraint_number else pair_number
        #             current_pair_number = pair_number
        #             pair_number = pair_number+1
        #
        #             sub_restraint_id = 0 if new_restraint_number != restraint_number else sub_restraint_id
        #             restraint_number = new_restraint_number
        #             line = _remove_id(line)
        #
        #             selections = _get_selections(line, 2, current_selections)
        #             current_selections = selections
        #             line = _remove_selections(line, 2)
        #
        #             line = ' '.join(line.split('!'))
        #             fields = line.split()
        #             if not fields:
        #                 fields = current_fields
        #             current_fields = fields
        #
        #             calculated = float(fields[0])
        #             min_bound = float(range_split(fields[1])[0])
        #             max_bound = float(range_split(fields[1])[1])
        #
        #             violation = 0.0
        #             if calculated < min_bound:
        #                 violation = calculated - min_bound
        #             elif calculated > max_bound:
        #                 violation = calculated - max_bound
        #
        #
        #             key = (index, model, new_restraint_number, sub_restraint_id, current_pair_number)
        #             comment = fields[3]
        #             restraint_list = comment.rstrip(string.digits)
        #             restraint_identifier = comment[len(restraint_list):]
        #             result = {'selection-1': selections[0],
        #                       'selection-2': selections[1],
        #                       'probability': '.',
        #                       'calc': calculated,
        #                       'min': min_bound,
        #                       'max': max_bound,
        #                       'dist': calculated,
        #                       'viol': violation,
        #                       'restraint-list': restraint_list,
        #                       'restraint-number': restraint_identifier,
        #                       'comment': fields[3],
        #                       'violation-file': file_path.parts[-1],
        #                       'structure-file': f'{file_path.stem}.cif'
        #
        #             }
        #
        #             lines[key] = result
        #             index += 1
        #
        #
        #             # print(line.strip().split([')','(']))
        #             # while((fields:=line.strip().partition(')'))[2:] !=('','')):
        #             #     line=fields[-1]
        #             #     print(fields)
        #             # return
        #     #args.next_index = index
        #     return results
        #
        # def _get_id(line, current_id):
        #     putative_id = line.split()[0].strip()
        #
        #     result = current_id
        #     if not putative_id.startswith('('):
        #         result = int(putative_id)
        #
        #     return result
        #
        #
        # def _remove_violated_mark_if_present(line):
        #
        #     result = line.strip().lstrip('*').strip()
        #     return result
        #
        #
        # def _remove_id(line):
        #     return line.lstrip('0123456789').strip()
        #
        #
        # def _line_active(line):
        #     fields = line.split()
        #     return fields[0] != '*'
        #
        #
        # def _get_selections(line, count, current_selections):
        #
        #     results = []
        #     line = line.strip()
        #     for i in range(count):
        #         value, _, line = line.partition(')')
        #         results.append(value)
        #         line = line.strip()
        #
        #     results = [selection.lstrip('(') for selection in results]
        #     selections = []
        #     for i, result in enumerate(results):
        #         selection = []
        #
        #         if len(result.strip()):
        #             selections.append(selection)
        #             segid = result[:4]
        #             selection.append(segid)
        #             result = result[4:]
        #             selection.extend(result.split())
        #         else:
        #             selections.append(current_selections[i])
        #
        #     return selections
        #
        #
        # def _remove_selections(line,count):
        #
        #     line = line.strip()
        #     for i in range(count):
        #         value, _, line = line.partition(')')
        #         line = line.strip()
        #
        #     return line
        #
        #
        # def tabulate_data(data):
        #     for restraint_table in data:
        #         print(restraint_table)
        #         print('-' * len(restraint_table))
        #         print()
        #
        #
        #
        #         table = []
        #         non_index_headings = ['probability', 'calc', 'min',
        #                     'max', 'dist', 'viol', 'restraint-list', 'restraint-number', 'comment']
        #         selections = ['selection-1', 'selection-2' ]
        #
        #         for indices, datum in data[restraint_table].items():
        #
        #             line = []
        #             table.append(line)
        #
        #             have_path_ids = len(indices) == 5
        #             if have_path_ids:
        #                 (index, model, id, sub_id,path_id) = indices
        #             else:
        #                 (index, model, id, sub_id) = indices
        #
        #             line.append(index+1)
        #             line.append(model)
        #             line.append(int(id)+1)
        #             line.append(sub_id+1)
        #             if have_path_ids:
        #                 line.append(path_id + 1)
        #             line.append('.'.join(datum['selection-1']))
        #             line.append('.'.join(datum['selection-2']))
        #
        #             for elem in non_index_headings:
        #                 line.append(datum[elem])
        #
        #         if have_path_ids:
        #             headings = ['index', 'model', 'id', 'sub id', 'path_id', *selections, *non_index_headings]
        #         else:
        #             headings = ['index', 'model', 'id', 'sub id', *selections, *non_index_headings]
        #
        #         print(tabulate(table, headers=headings))
        #         # tableDF = pd.DataFrame(table, columns=headings)
        #         # print(tableDF.to_string(index=False))
        #         print()
        #
        #
        # def _collapse_pairs(nef_entries):
        #
        #     result = {}
        #     for entry_name, data in nef_entries.items():
        #
        #         pair_selections = {}
        #         unique_entry_data = {}
        #
        #         for i,(key, entry) in enumerate(data.items()):
        #
        #             new_key = key[1:-1]
        #
        #             pair_selections.setdefault(new_key, []).append((entry['selection-1'],entry['selection-2']))
        #             unique_entry_data[new_key] = entry
        #
        #         new_entry = {}
        #         for i, (new_key, selection_data) in enumerate(pair_selections.items()):
        #
        #             atoms_1 = set()
        #             atoms_2 = set()
        #             for selection_1, selection_2 in selection_data:
        #                 atoms_1.add(selection_1[-1])
        #                 atoms_2.add(selection_2[-1])
        #
        #             selection_1 = selection_data[0][0]
        #             selection_2 = selection_data[0][1]
        #
        #             nef_atom_name_1 = collapse_name(atoms_1)
        #             nef_atom_name_2 = collapse_name(atoms_2)
        #
        #             selection_1[-1] = nef_atom_name_1
        #             selection_2[-1] = nef_atom_name_2
        #
        #             unique_entry_data[new_key]['selection-1'] = selection_1
        #             unique_entry_data[new_key]['selection-2'] = selection_2
        #
        #
        #
        #             new_entry[new_key] = unique_entry_data[new_key]
        #
        #         result[entry_name] = new_entry
        #
        #
        #     # ic(result)
        #     return result
        #
        #
        # def data_as_nef(overall_result):
        #
        #     entry = Entry.from_scratch('default')
        #
        #     for table_name, table_data in overall_result.items():
        #         table_name = table_name.replace('noe-', '', 1)
        #         category = "ccpn_distance_restraint_violation_list"
        #         frame_code = f'{category}_{table_name}'
        #         frame = Saveframe.from_scratch(frame_code, category)
        #         entry.add_saveframe(frame)
        #
        #         frame.add_tag("sf_category", "ccpn_distance_restraint_violation_list")
        #         frame.add_tag("sf_framecode", frame_code)
        #         frame.add_tag("nef_spectrum", f"nef_nmr_spectrum_{list(table_data.values())[0]['restraint-list']}")
        #         frame.add_tag("nef_restraint_list", f"{list(table_data.values())[0]['restraint-list']}")
        #         frame.add_tag("program", 'Xplor-NIH')
        #         frame.add_tag("program_version", UNUSED)
        #         frame.add_tag("protocol", 'marvin/pasd,refine')
        #         frame.add_tag("protocol_version", UNUSED)
        #         frame.add_tag("protocol_parameters", UNUSED)
        #
        #
        #
        #         lp = Loop.from_scratch()
        #
        #         tags = ('index', 'model_id', 'restraint_id', 'restraint_sub_id',
        #                 'chain_code_1','sequence_code_1', 'residue_name_1', 'atom_name_1',
        #                 'chain_code_2', 'sequence_code_2', 'residue_name_2', 'atom_name_2',
        #                 'weight', 'probability', 'lower_limit', 'upper_limit', 'distance', 'violation',
        #                 'violation_file', 'structure_file', 'structure_index','nef_peak_id', 'comment'
        #                 )
        #
        #         lp.set_category('_ccpn_distance_restraint_violation') # category)
        #         lp.add_tag(tags)
        #
        #         for index, (indices, line_data) in enumerate(table_data.items()):
        #
        #
        #             indices = list(indices)
        #             indices = [index,*indices]
        #
        #             indices[0] += 1
        #             indices[2] += 1
        #             indices[3] += 1
        #
        #             #TODO: conversion of SEGID to chain ID maybe too crude
        #             selection_1 = line_data['selection-1']
        #             selection_1[0] = selection_1[0].strip()
        #             selection_2 = line_data['selection-2']
        #             selection_2[0] = selection_2[0].strip()
        #
        #             data = [*indices, *selection_1, *selection_2,
        #                     1.0, line_data['probability'], line_data['min'], line_data['max'],
        #                     # GST: this removes trailing rounding errors without loss of accuracy
        #                     round(line_data['dist'], 10),
        #                     round(line_data['viol'],10),
        #                     line_data['violation-file'],line_data['structure-file'], 1,
        #                     line_data['restraint-number'], line_data['comment']
        #                     ]
        #
        #             lp.add_data(data)
        #
        #         frame.add_loop(lp)
        #
        #     return str(entry)
        #
        #
        # def writeViolationsNEF(dirPath, fileList):
        #     overall_result = {}
        #     fileDir = os.path.join(dirPath, 'fold', 'lowestEnergy')
        #
        #     for name in fileList:
        #         path = pathlib.Path(os.path.join(fileDir,name))
        #
        #         try:
        #             model_number = int(filename_matcher.match(path.parts[-1]).group(1))
        #         except:
        #             exit_error(f"Couldn't find a model number in {path.parts[-1]} using matcher {filename_matcher.pattern}")
        #
        #         if not path.is_file():
        #             exit_error(f'I need an input file, path was {path}')
        #
        #         with open(path) as fh:
        #             entries = viol_to_nef(fh, model_number, path)#, args)
        #
        #             entries = _collapse_pairs(entries)
        #
        #             for entry_name, entry in entries.items():
        #                 overall_result.setdefault(entry_name, {}).update(entry)
        #
        #
        #     #tabulate_data(overall_result)
        #
        #     result = data_as_nef(overall_result)
        #
        #     dateTimeStr = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        #
        #     with open(os.path.join(dirPath,'violations.nef'),'w') as fh:
        #
        #         metaData = """data_default
        #
        #         save_nef_nmr_meta_data
        #         _nef_nmr_meta_data.sf_category     nef_nmr_meta_data
        #         _nef_nmr_meta_data.sf_framecode    nef_nmr_meta_data
        #         _nef_nmr_meta_data.format_name     nmr_exchange_format
        #         _nef_nmr_meta_data.format_version  1.1
        #         _nef_nmr_meta_data.program_name    CCPNprocessXplorNIHCalculation
        #         _nef_nmr_meta_data.program_version 3.2
        #         _nef_nmr_meta_data.creation_date   {0}
        #         _nef_nmr_meta_data.uuid            CCPNprocessXplorNIHCalculation_{1}
        #         save_
        #         """.format(dateTimeStr, dateTimeStr)
        #
        #         fh.write(result.replace('data_default', metaData).replace('                ',''))
        #
        #     return


        class ProcessXplorCalculationFolderPopup(CcpnDialogMainWidget):
            """

            """
            FIXEDWIDTH = True
            FIXEDHEIGHT = False

            title = 'Process Xplor-NIH Structure Calculation (Alpha)'
            def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
                super().__init__(parent, setLayout=True, windowTitle=title,
                                 size=(500, 10), minimumSize=None, **kwds)

                if mainWindow:
                    self.mainWindow = mainWindow
                    self.application = mainWindow.application
                    self.current = self.application.current
                    self.project = mainWindow.project

                else:
                    self.mainWindow = None
                    self.application = None
                    self.current = None
                    self.project = None

                self._createWidgets()

                # enable the buttons
                self.tipText = ''
                self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Clean up', enabled=True)
                self.setCloseButton(callback=self.reject, tipText='Close')
                self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

            def _createWidgets(self):

                row = 0
                self.pathLabel = Label(self.mainWidget, text="Xplor NIH Run Directory", grid=(row, 0))
                self.pathData = PathEdit(self.mainWidget, grid=(row, 1), vAlign='t', )
                self.pathDataButton = Button(self.mainWidget, grid=(row, 2), callback=self._getPathFromDialog,
                                                   icon='icons/directory', hPolicy='fixed')
                if ccpnVersion310:
                    row =1
                    self.checkLabel = Label(self.mainWidget, text="Generate Violations.nef?", grid=(row, 0))

                    self.checkBox = CheckBox.CheckBox(self.mainWidget,grid=(row,1))

            def _getPathFromDialog(self):
                dialog = OtherFileDialog(parent=self.mainWindow, _useDirectoryOnly=True,)
                dialog._show()
                path = dialog.getExistingDirectory() # dialog.selectedFile()

                if path:
                    self.pathData.setText(str(path))

            def _okCallback(self):
                """Clicked ok: process the calculation files
                """
                from ccpn.AnalysisStructure.lib.runManagers.XplorNihRunManager import XplorNihRunManager

                if self.project:
                    pathRun = self.pathData.get()

                    if not pathRun:
                        MessageDialog.showWarning('', 'Include path to Xplor run data directory')
                        return

                    # run the calculation
                    project = self.project
                    myRun = XplorNihRunManager(project=project,
                                               runName='run', runId=1
                                               )
                    myRun.restoreState(runPath=self.pathData.get())
                    # run the cleanup
                    myRun.processCalculation()

                    if ccpnVersion310:
                        if self.checkBox.isChecked():
                            myRun._runViolationAnalysisScript()

                self.accept()

        if __name__ == '__main__':
            from ccpn.ui.gui.widgets.Application import TestApplication
            # app = TestApplication()
            popup = ProcessXplorCalculationFolderPopup(mainWindow=mainWindow)
            popup.show()
            popup.raise_()
            # app.start()

