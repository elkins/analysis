"""
Alpha version of a popup for generating percentage assignment tables
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
__dateModified__ = "$dateModified: 2024-09-16 10:12:11 +0100 (Mon, September 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: eliza $"
__date__ = "$Date: 2021-04-27 16:04:57 +0100 (Tue, April 27, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as et

from PyQt5 import QtCore, QtGui, QtWidgets

from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown, ChemicalShiftListPulldown, ChainPulldown
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ListWidget import ListWidgetPair
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets import CheckBox, LineEdit
from ccpn.ui.gui.widgets.FileDialog import OtherFileDialog
from ccpn.ui.gui.widgets.HLine import LabeledHLine
from ccpn.ui.gui.widgets.PulldownListsForObjects import StructureDataPulldown

from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.core.DataTable import TableFrame

from ccpn.framework.Application import getApplication
from ccpn.framework.Version import applicationVersion

from ccpn.util.Path import aPath
# from sandbox.Geerten.NTdb.NTdbLib import getNefName
from ccpn.framework.lib.NTdb.NTdbDefs import getNTdbDefs
from ccpn.core.lib.AssignmentLib import PROTEIN_NEF_ATOM_NAMES


_ntDefs = getNTdbDefs()

if applicationVersion == '3.1.0':
    ccpnVersion310 = True
else:
    ccpnVersion310 = False


class aminoAcid():
    # A class that stores the other possible atom names
    def __init__(self):
        self.name = ""
        self.c = [['C']]
        self.n = [['N']]
        self.ca = [['CA']]
        self.cb = [['CB']]
        self.cg = [[]]
        self.cd = [[]]
        self.ce = [[]]
        self.cz = [[]]
        self.ch = [[]]
        self.nd = [[]]
        self.ne = [[]]
        self.nz = [[]]
        self.nh = [[]]
        self.h = [['H']]
        self.ha = [['HA']]
        self.hb = [[]]
        self.hg = [[]]
        self.hd = [[]]
        self.he = [[]]
        self.hz = [[]]
        self.hh = [[]]
        self.backbone = [['C', 'HA', 'H', 'N', 'CA']]
        self.methyl = [[]]
        self.aromatic = [[]]


# specify the groups of atoms

ALA = aminoAcid()
ALA.name = "ALA"
ALA.hb = [['HB1', 'HB2', 'HB3'], ['HB%'], ['QB']]
ALA.methyl = [['HB1', 'HB2', 'HB3'], ['HB%'], ['QB']]

ARG = aminoAcid()
ARG.name = "ARG"
ARG.cg = [['CG']]
ARG.cd = [['CD']]
ARG.cz = [['CZ']]
ARG.ne = [['NE']]
ARG.nh = [['NH1', 'NH2'], ['NHx', 'NHy'], ['NH%']]
ARG.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
ARG.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]
ARG.hd = [['HD2', 'HD3'], ['HDx', 'HDy'], ['HD%']]
ARG.he = [['HE']]
ARG.hh = [['HH11', 'HH12', 'HH21', 'HH22'], ['HHx%', 'HHy%'], ['HH1%', 'HH2%'], ['HH%']]

ASN = aminoAcid()
ASN.name = "ASN"
#ASN.cg = [['CG']]
ASN.nd = [['ND2']]
ASN.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
ASN.hd = [['HD21', 'HD22'], ['HD2x', 'HD2y'], ['HD2%']]

ASP = aminoAcid()
ASP.name = "ASP"
#ASP.cg = [['CG']]
ASP.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]

CYS = aminoAcid()
CYS.name = "CYS"
CYS.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
#CYS.hg = [['HG']] #  'HG' not included in statistics

GLN = aminoAcid()
GLN.name = "GLN"
GLN.cg = [['CG']]
#GLN.cd = [['CD']]
GLN.ne = [['NE2']]
GLN.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
GLN.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]
GLN.he = [['HE21', 'HE22'], ['HE2x', 'HE2y'], ['HE2%']]

GLU = aminoAcid()
GLU.name = "GLU"
GLU.cg = [['CG']]
#GLU.cd = [['CD']]
GLU.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
GLU.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]

GLY = aminoAcid()
GLY.name = "GLY"
GLY.ha = [['HAx', 'HAy'], ['HA%'], ['HA2', 'HA3']]
GLY.cb = [[]]

HIS = aminoAcid()
HIS.name = "HIS"
#HIS.cg = [['CG']]
HIS.cd = [['CD2']]
HIS.nd = [['ND1']]
HIS.ce = [['CE1']]
HIS.ne = [['NE2']]
HIS.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
HIS.hd = [['HD2']]
HIS.he = [['HE1']]
HIS.aromatic = [['HD2', 'HE1']]  # Nitrogen attached protons HE2 and Hd1 are not included in the aromatic count

ILE = aminoAcid()
ILE.name = "ILE"
ILE.cg = [['CG1', 'CG2']]
ILE.cd = [['CD1']]
ILE.hb = [['HB']]
ILE.hg = [['HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
          ['HG1x', 'HG1y'],
          ['HG1%'], ['HG2%']
          ]
ILE.hd = [['HD11', 'HD12', 'HD13'], ['HD1%']]
ILE.methyl = [['HD11', 'HD12', 'HD13', 'HG21', 'HG22', 'HG23'], ['HD1%', 'HG2%']]

LEU = aminoAcid()
LEU.name = "LEU"
LEU.cg = [['CG']]
LEU.cd = [['CD1', 'CD2'], ['CDx', 'CDy'], ['CD%']]
LEU.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
LEU.hg = [['HG']]
LEU.hd = [['HD11', 'HD12', 'HD13', 'HD21', 'HD22', 'HD23'],
          ['HD1%', 'HD2%'], ['HDx%', 'HDy%'], ['HD%']]
LEU.methyl = LEU.hd

LYS = aminoAcid()
LYS.name = "LYS"
LYS.cg = [['CG']]
LYS.cd = [['CD']]
LYS.ce = [['CE']]
LYS.nz = [['NZ']]
LYS.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
LYS.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]
LYS.hd = [['HD2', 'HD3'], ['HDx', 'HDy'], ['HD%']]
LYS.he = [['HE2', 'HE3'], ['HEx', 'HEy'], ['HE%']]
LYS.hz = [['HZ1', 'HZ2', 'HZ3'], ['HZ%']]

MET = aminoAcid()
MET.name = "MET"
MET.cg = [['CG']]
MET.ce = [['CE']]
MET.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
MET.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]
MET.he = [['HE1', 'HE2', 'HE3'], ['HE%']]
MET.methyl = MET.he

PHE = aminoAcid()
PHE.name = "PHE"
#PHE.cg = [['CG']]
PHE.cd = [['CD1', 'CD2'], ['CDx', 'CDy'], ['CD%']]
PHE.ce = [['CE1', 'CE2'], ['CEx', 'CEy'], ['CE%']]
PHE.cz = [['CZ']]
PHE.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
PHE.hd = [['HD1', 'HD2'], ['HDx', 'HDy'], ['HD%']]
PHE.he = [['HE1', 'HE2'], ['HEx', 'HEy'], ['HE%']]
PHE.hz = [['HZ']]
PHE.aromatic = [['HD1', 'HD2', 'HE1', 'HE2'],
                ['HDx', 'HDy', 'HEx', 'HEy'],
                ['HD%', 'HE%', 'HZ']]
PRO = aminoAcid()
PRO.name = "PRO"
PRO.h = [[]]
PRO.cg = [['CG']]
PRO.cd = [['CD']]
PRO.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
PRO.hg = [['HG2', 'HG3'], ['HGx', 'HGy'], ['HG%']]
PRO.hd = [['HD2', 'HD3'], ['HDx', 'HDy'], ['HD%']]
PRO.backbone = [['C', 'N', 'CA']]

SER = aminoAcid()
SER.name = "SER"
SER.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
# SER.hg = [['HG']] #  'HG' not included in statistics

THR = aminoAcid()
THR.name = "THR"
THR.cg = [['CG2']]
THR.hb = [['HB']]
THR.hg = [['HG21', 'HG22', 'HG23'], ['HG2%']]  #  'HG1' not included in statistics
THR.methyl = [['HG21', 'HG22', 'HG23'], ['HG2%']]

TRP = aminoAcid()
TRP.name = "TRP"
#TRP.cg = [['CG']]
TRP.cd = [['CD1', 'CD2']]
TRP.ce = [['CE2', 'CE3']]
TRP.cz = [['CZ2'], ['CZ3']]
TRP.ch = [['CH2']]
TRP.ne = [['NE1']]
TRP.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
TRP.hd = [['HD1']]
TRP.he = [['HE1'], ['HE3']]
TRP.hz = [['HZ2'], ['HZ3']]
TRP.hh = [['HH2']]
TRP.aromatic = [['HD1', 'HE1', 'HE3', 'HZ2', 'HZ3', 'HH2']]

TYR = aminoAcid()
TYR.name = "TYR"
#TYR.cg = [['CG']]
TYR.cd = [['CD1', 'CD2'], ['CDx', 'CDy'], ['CD%']]
TYR.ce = [['CE1', 'CE2'], ['CEx', 'CEy'], ['CE%']]
TYR.cz = [['CZ']]
TYR.hb = [['HB2', 'HB3'], ['HBx', 'HBy'], ['HB%']]
TYR.hd = [['HD1', 'HD2'], ['HDx', 'HDy'], ['HD%']]
TYR.he = [['HE1', 'HE2'], ['HEx', 'HEy'], ['HE%']]
TYR.hh = [['HH']]
TYR.aromatic = [['HD1', 'HD2', 'HE1', 'HE2'],
                ['HDx', 'HDy', 'HEx', 'HEy'],
                ['HD%', 'HE%']]

VAL = aminoAcid()
VAL.name = "VAL"
VAL.cg = [['CG1', 'CG2'], ['CGx', 'CGy'], ['CG%']]
VAL.hb = [['HB']]
VAL.hg = [['HG11', 'HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
          ['HG1%', 'HG2%'], ['HGx%', 'HGy%'], ['HG%']]
VAL.methyl = VAL.hg

# Create a dictionary to help identify the relevant aminoacid
aaDict = {'ALA': ALA,
          'ARG': ARG,
          'ASN': ASN,
          'ASP': ASP,
          'CYS': CYS,
          'GLU': GLU,
          'GLN': GLN,
          'GLY': GLY,
          'HIS': HIS,
          'ILE': ILE,
          'LEU': LEU,
          'LYS': LYS,
          'MET': MET,
          'PHE': PHE,
          'PRO': PRO,
          'SER': SER,
          'THR': THR,
          'TRP': TRP,
          'TYR': TYR,
          'VAL': VAL}


class calculateAssignments():
    def __init__(self, project=None, cslPID=None, chnPID=None, excludeList=[], ignoreN=False):
        self.project = project
        self.csl = project.getByPid(cslPID)
        self.chain = project.getByPid(chnPID)
        self.excludeList = excludeList
        self.ignoreN = ignoreN
        self.AtomTypeList = ['C', 'CA', 'CB', 'CG', 'CD', 'CE', 'CZ', 'CH', 'H', 'HA', 'HB', 'HG', 'HD',
                             'HE', 'HZ', 'HH', 'N']

        # For future when we can list additional groups:
        # self.AtomTypeList = ['C','CA','CB','CG','CD','CE','CZ','CH', 'H','HA','HB','HG','HD',
        #                      'HE','HZ','HH','N','backboneCHN','methylH', 'aromaticH']

        self.AssignedResidueTable = self.getAssignedResidueTable()
        self.proteinDetailsArray, self.allProteinDetails = self.buildProteinDetailsArray()
        self.summaryTable = self.buildSummaryTable()
        self.problemArray = self.buildPossibleproblemsArray()

    def getAssignedResidueTable(self):
        # Function that takes a chain of nmrResidues and an index for the chemicalShiftList

        # Build a list of all possible atoms in protein as defined by the NMR chain - this can be problematic if user
        # manually filters this list
        atomList = []
        for resi in self.chain.residues:
            for atom in resi.atoms:
                if atom.name not in atomList:
                    atomList.append(atom.name)

        for key, residue in aaDict.items():
            for atomGroup in [residue.c, residue.ca, residue.cb, residue.cg,
                              residue.cd, residue.ce, residue.cz, residue.ch,
                              residue.h, residue.ha, residue.hb, residue.hg,
                              residue.hd, residue.he, residue.hz, residue.hh, residue.n]:

                # residue.backbone, residue.methyl, residue.aromatic]:
                for atomSet in atomGroup:
                    for atomName in atomSet:
                        if atomName not in atomList:
                            atomList.append(atomName)

        # Add in any missing atom names from PROTEIN_NEF_ATOM_NAMES dictionary
        for atom_list in PROTEIN_NEF_ATOM_NAMES.values():
            for atomName in atom_list:
                atomList.append(atomName)

        # get unique atomNames
        atomList = sorted(list(set(atomList)))  # Optionally sort the list

        # go through the nmrResidues and see if atom has a chemical shift value
        # (ie is assigned) in a specified chemicalshiftlist
        proteinArray = []
        for resi in self.chain.residues:
            atomCheckList = [pd.NA for i in range(len(atomList))]

            # 2 approaches here - because nmratoms doesnt have to match chain atoms we go through both lists
            # most of the time this will be redundant

            for atomName in atomList:

                naPID = "NA:{chain}.{resiNum}.{resiCode}.{atom}".format(chain=resi.chain.name,
                                                                        resiNum=resi.sequenceCode,
                                                                        resiCode=resi.residueType,
                                                                        atom=atomName)

                #if int(resi.sequenceCode )==5:
                #   print(naPID, project.getByPid(naPID))
                try:
                    nmrAtom = project.getByPid(naPID)

                    for i, cs in enumerate(nmrAtom.chemicalShifts):
                        # Only get chemical shift value if chemicalShiftList is the desired one
                        if cs.chemicalShiftList.pid == self.csl.pid:
                            atomCheckList[atomList.index(atomName)] = nmrAtom.chemicalShifts[i].value

                except:
                    # nmr atom doesnt exist
                    next

            for atom in resi.atoms:

                if atom.name not in atomList:
                    continue

                if atom.nmrAtom is None:
                    continue
                    #atomCheckList[atomList.index(atom.name)] = 0  #99999
                elif len(atom.nmrAtom.chemicalShifts) == 0:
                    continue
                    #atomCheckList[atomList.index(atom.name)] = 0  #99999
                else:
                    for i, cs in enumerate(atom.nmrAtom.chemicalShifts):
                        #if int(resi.sequenceCode) ==79:
                        #    print(resi.pid, resi.residueType, resi.sequenceCode, atom.name, atom.nmrAtom.chemicalShifts[i].value)
                        # Only get chemical shift value if chemicalShiftList is the desired one
                        if cs.chemicalShiftList.pid == self.csl.pid:
                            atomCheckList[atomList.index(atom.name)] = atom.nmrAtom.chemicalShifts[i].value
                            break

            if int(resi.sequenceCode) not in self.excludeList:
                proteinArray.append([resi.pid, resi.residueType, resi.sequenceCode] + atomCheckList)

        #return a dataframe containing the assignments.
        df = pd.DataFrame(proteinArray, columns=['pid', 'residueType', 'sequenceCode'] + atomList)

        return df

    def checkMaxLen(self, residue, maxLen, i):
        # i is the atomset index as specified in the list in line 332
        if residue.name == "ALA" and i == 10:
            maxLen = 1

        if residue.name == "ILE" and i == 11:
            maxLen = 3

        if residue.name == "VAL" and i == 11:
            maxLen = 2

        if residue.name == "LEU" and i == 12:
            maxLen = 2

        if residue.name == "THR" and i == 11:
            maxLen = 1

        if residue.name == "TYR" and i == 4:
            maxLen = 1

        if residue.name == "PHE" and i == 4:
            maxLen = 1

        if residue.name == "TYR" and i == 5:
            maxLen = 1

        if residue.name == "PHE" and i == 5:
            maxLen = 1

        if i == 18:  # methyls
            if residue.name == "VAL":
                maxLen = 2
            if residue.name == "THR":
                maxLen = 1
            if residue.name == "ALA":
                maxLen = 1
            if residue.name == "ILE":
                maxLen = 2
            if residue.name == "LEU":
                maxLen = 2

        return maxLen

    def getResiDetails_AllPossible(self, resiRow, residue):
        # function to work out if an atom in a residue is potentially assignable
        # by going through each atomSet in the residue.
        # We use this information later to calculate the percentages of assigned resonances.

        resiDetailsArray = []

        for i, atomGroup in enumerate(
                [residue.c, residue.ca, residue.cb, residue.cg, residue.cd, residue.ce, residue.cz, residue.ch,
                 residue.h, residue.ha, residue.hb, residue.hg, residue.hd, residue.he, residue.hz, residue.hh,
                 residue.n]):
            # residue.backbone, residue.methyl, residue.aromatic]):

            # the number of resonances can be calculated for most Resi/Atom types automatically
            # from the length of the (atomSet) but some residues need some manual tweaking
            # mostly this is about methyl groups.

            # atom group example [[HB2,HB3], [HB%]]
            maxLen = 0

            for atomSet in atomGroup:
                if len(atomSet) > maxLen: maxLen = len(atomSet)

            if maxLen == 0:
                resiDetailsArray.append(pd.NA)
                continue

            maxLen = self.checkMaxLen(residue, maxLen, i)

            resiDetailsArray.append(maxLen)

        return resiDetailsArray

    def getResiDetails(self, resiRow, residue):
        # function to work out if an atom in a residue is assigned by going through each atomSet in the
        # residue.
        resiDetailsArray = []

        for i, atomGroup in enumerate([residue.c, residue.ca, residue.cb, residue.cg,
                                       residue.cd, residue.ce, residue.cz, residue.ch,
                                       residue.h, residue.ha, residue.hb, residue.hg,
                                       residue.hd, residue.he, residue.hz, residue.hh, residue.n]):
            # residue.backbone, residue.methyl, residue.aromatic]):

            # the number of resonances can be calculated for most Resi/Atom types automatically
            # from the length of the (atomSet) but some residues need some manual tweaking
            # mostly this is about methyl groups.

            # atom group example [[HB2,HB3], [HB%]]
            maxLen = 0

            for atomSet in atomGroup:
                if len(atomSet) > maxLen: maxLen = len(atomSet)

            if maxLen == 0:
                resiDetailsArray.append(pd.NA)
                continue

            maxLen = self.checkMaxLen(residue, maxLen, i)

            percent = 0
            for atomSet in atomGroup:
                if len(atomSet) == 0: continue
                # ILE.hg = [['HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
                #           ['HG1x', 'HG1y'],
                #           ['HG1%'], ['HG2%']
                #           ]
                if residue.name == "ILE" and atomSet == ILE.hg[0]:
                    # ILE Hg
                    temp = 0
                    # the atoms in this atomset are CH2 and therefore can possibly give 2 signals
                    indexes = list(set(resiRow.index) & set(atomSet[0:2]))
                    temp = resiRow.where(resiRow[indexes] > 0).count()
                    percent += temp

                    # the atoms in this atomset are a methyl and therefore are expected to only give 1 signal
                    indexes = list(set(resiRow.index) & set(atomSet[2:]))
                    temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                    percent += temp

                elif residue.name == "ILE" and atomSet == ILE.hg[1]:
                    # ILE Hg
                    temp = 0
                    indexes = list(set(resiRow.index) & set(atomSet))
                    temp = resiRow.where(resiRow[indexes] > 0).count() * 1
                    percent += temp

                elif residue.name == "ILE" and atomSet == ILE.hg[2]:
                    # ILE Hg1%
                    temp = 0
                    indexes = list(set(resiRow.index) & set(atomSet))
                    temp = resiRow.where(resiRow[indexes] > 0).count() * 2
                    percent += temp

                elif residue.name == "ILE" and atomSet == ILE.hg[3]:
                    # ILE Hg
                    temp = 0
                    indexes = list(set(resiRow.index) & set(atomSet))
                    temp = resiRow.where(resiRow[indexes] > 0).count() * 1
                    percent += temp

                # elif residue.name == "VAL" and atomSet == VAL.hg[0]:
                #     #VAL.hg = [['HG11', 'HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
                #     #          ['HG1%', 'HG2%'], ['HGx%', 'HGy%'], ['HG%']]
                #     indexes = list(set(resiRow.index) & set(atomSet[0:3]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                #     percent = percent + temp
                #
                #     indexes = list(set(resiRow.index) & set(atomSet[3:]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                #     percent = percent + temp
                #
                # elif residue.name == "VAL" and atomSet == VAL.hg[1]:
                #     #VAL.hg = [['HG11', 'HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
                #     #          ['HG1%', 'HG2%'], ['HGx%', 'HGy%'], ['HG%']]
                #     indexes = list(set(resiRow.index) & set(atomSet))
                #     temp = resiRow.where(resiRow[indexes] > 0).count()
                #     percent = percent + temp
                #
                # elif residue.name == "VAL" and atomSet == VAL.hg[2]:
                #     #VAL.hg = [['HG11', 'HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
                #     #          ['HG1%', 'HG2%'], ['HGx%', 'HGy%'], ['HG%']]
                #     indexes = list(set(resiRow.index) & set(atomSet))
                #     temp = resiRow.where(resiRow[indexes] > 0).count()
                #     percent = percent + temp
                #
                # elif residue.name == "VAL" and atomSet == VAL.hg[3]:
                #     #VAL.hg = [['HG11', 'HG12', 'HG13', 'HG21', 'HG22', 'HG23'],
                #     #          ['HG1%', 'HG2%'], ['HGx%', 'HGy%'], ['HG%']]
                #     indexes = list(set(resiRow.index) & set(atomSet))
                #     temp = resiRow.where(resiRow[indexes] > 0).count()
                #     percent = percent + temp

                # elif residue.name == "LEU" and atomSet == LEU.hd[0]:
                #     # LEU.hd = [['HD11', 'HD12', 'HD13', 'HD21', 'HD22', 'HD23'],
                #     #           ['HD1%', 'HD2%'], ['HDx%', 'HDy%'], ['HD%']]
                #     indexes = list(set(resiRow.index) & set(atomSet[0:3]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                #     percent = percent + temp
                #
                #     indexes = list(set(resiRow.index) and set(atomSet[3:]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                #     percent = percent + temp

                # elif residue.name == "THR" and atomSet == THR.hg[0]:
                #     #THR.hg = [['HG21', 'HG22', 'HG23'], ['HG2%']]
                #     indexes = list(set(resiRow.index) & set(atomSet[0]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count()
                #     percent = percent + temp
                #
                #     indexes = list(set(resiRow.index) and set(atomSet[1:]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count() * (1 / 3)
                #     percent = percent + temp
                #
                # elif residue.name == "THR" and atomSet == THR.hg[1]:
                #     indexes = list(set(resiRow.index) and set(atomSet[1:]))
                #     temp = resiRow.where(resiRow[indexes] > 0).count()
                #     percent = percent + temp

                else:
                    # Which atom names appear in both the resiRow and atomSet
                    indexes = list(set(resiRow.index) & set(atomSet))

                    # given the atom group [['HB%],[HBx, HBy]] - then the maxLen would be 2 - this tells us HB% should also account
                    # for 2 resonances. the len([HB%]) = 1 so dividing maxLen/len([HB%]) gives us the multiplier we need for that atom name
                    # if the atomset is [HBx, HBy] then maxLen/len(atomset) is 1 and therefore it is simply the count of the
                    # chemical shifts.
                    filtered_resiRow = resiRow.loc[indexes].dropna()

                    temp = filtered_resiRow.count() * maxLen / len(atomSet)
                    percent = percent + temp

            resiDetailsArray.append(percent)

        return resiDetailsArray

    def buildProteinDetailsArray(self):
        # Build a pandas dataframe that contains all the chemical shift info
        # for each residue in the protein - get the residue atom information from our aminoacid dictionary
        proteinDetailsArray = pd.DataFrame(columns=['pid', 'residueType', 'sequenceCode'] + self.AtomTypeList)
        allResidueDetailsArray = pd.DataFrame(columns=['pid', 'residueType', 'sequenceCode'] + self.AtomTypeList)

        for i, resi in self.AssignedResidueTable.iterrows():
            _r = aaDict[resi['residueType']]
            # is the atom assigned or does it not exist?
            assignmentArray = self.getResiDetails(resi, _r)

            tempDF = pd.DataFrame([[resi['pid'], resi['residueType'], resi['sequenceCode']] + assignmentArray],
                                  columns=['pid', 'residueType', 'sequenceCode'] + self.AtomTypeList)

            # proteinDetailsArray = proteinDetailsArray.append(tempDF)
            proteinDetailsArray = pd.concat([proteinDetailsArray, tempDF])
            assignmentArray = self.getResiDetails_AllPossible(resi, _r)
            tempDF = pd.DataFrame([[resi['pid'], resi['residueType'], resi['sequenceCode']] + assignmentArray],
                                  columns=['pid', 'residueType', 'sequenceCode'] + self.AtomTypeList)

            # allResidueDetailsArray = allResidueDetailsArray.append(tempDF)
            allResidueDetailsArray = pd.concat([allResidueDetailsArray, tempDF])

        return proteinDetailsArray, allResidueDetailsArray

    def buildPossibleproblemsArray(self):
        # Build a pandas dataframe that contains all the chemical shift info
        # for each residue in the protein - get the residue atom information from our aminoacid dictionaty

        # Define the list of columns to exclude from the check
        excluded_cols = ['pid', 'residueType', 'sequenceCode']  #,'backboneCHN', 'methylH', 'aromaticH']
        # Apply the filter to the DataFrame
        filtered_df = self.proteinDetailsArray[
            (self.proteinDetailsArray.drop(columns=excluded_cols)
             .fillna(value=-999)  # replace NaN values with -999, just so we can run a function (=applymap)
             .applymap(lambda x: x not in [0, 1, 1.0, -999])  # compare values
             .any(axis=1))  # check if any value in each row is True
        ]

        # exclude columns from both dataframes
        exclude_cols = ['pid', 'residueType', 'sequenceCode']  #,'backboneCHN', 'methylH', 'aromaticH']
        df1 = self.proteinDetailsArray.drop(columns=exclude_cols)
        df2 = self.allProteinDetails.drop(columns=exclude_cols)

        result = df1 / df2
        # apply the mask to filtered_df
        filtered_df = pd.concat([self.proteinDetailsArray[exclude_cols], result], axis=1)

        return filtered_df[(filtered_df.drop(columns=excluded_cols)
                            .fillna(
                value=-999)  # replace NaN values with -999, just so we can run a function (=applymap)
                            .applymap(lambda x: x not in [0, 1, 1.0, -999])  # compare values
                            .any(axis=1))  # check if any value in each row is True
        ]

    def buildSummaryTable(self):
        summaryDict = []
        # Go through each atom and determine the percentage assigned.
        # Note pd.NA is found if atom doesnt exist in residue so this is ignored

        for atom in self.AtomTypeList:

            # most publications ignore the assignment of the N
            # terminal Nitrogen as its normally not observed
            # we are just subtracting 1 from the possible
            # assignments

            ignoreNcorrection = 0
            if self.ignoreN and atom == "N":
                ignoreNcorrection = 1

            assigned = (self.proteinDetailsArray[atom]).sum(skipna=True)
            possible = self.allProteinDetails[atom][self.allProteinDetails[atom] >= 1].sum()
            notAssigned = possible - assigned - ignoreNcorrection

            if assigned + notAssigned != 0:
                summaryDict.append([atom, assigned, notAssigned, round((100 * assigned) / (assigned + notAssigned), 2)])
            else:
                summaryDict.append([atom, assigned, notAssigned, pd.NA])

        return pd.DataFrame(summaryDict, columns=['atomType', 'assigned', 'notAssigned', 'percentage'])


class CalculateAssignmentDataPopup(CcpnDialogMainWidget):
    """

    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    _GREY = '#888888'

    title = 'Calculate Assigned Percentages (ALPHA version)'

    def __init__(self, parent=None, mainWindow=None, title=title, **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(100, 10), minimumSize=None, **kwds)

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
        # self.tipText = ''
        # self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Import data', enabled=True)
        self.setUserButton(text='Calculate!',
                           tipText='Calculate Assignment Percentages for selected Chemical Shift List',
                           callback=self._importData)

        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        _height = 30
        _col1 = 0
        _col2 = 2

        row = -1

        row += 1

        topFrame = Frame(self.mainWidget, grid=(row, 0), gridSpan=(1, 3), setLayout=True)
        Label(topFrame,
              text='This is an experimental version.\nIf you find any issues please report to support@ccpn.ac.uk\n',
              grid=(0, 0), gridSpan=(1, 3))

        row += 1

        Label(self.mainWidget, text="Chain", grid=(row, 0), hAlign='right')
        self.chainListWidget = ChainPulldown(parent=self.mainWidget,
                                             mainWindow=self.mainWindow,
                                             grid=(row, 1),
                                             showSelectName=True,
                                             callback=None,
                                             labelText=''  # effectively not showing the label
                                             )

        row += 1

        Label(self.mainWidget, text="ChemicalShiftList", grid=(row, 0), hAlign='right')
        self.chemicalShiftListWidget = ChemicalShiftListPulldown(parent=self.mainWidget,
                                                                 mainWindow=self.mainWindow,
                                                                 grid=(row, 1),
                                                                 showSelectName=True,
                                                                 callback=None,
                                                                 labelText=''  # effectively not showing the label
                                                                 )
        row += 1

        namesFrame = Frame(self.mainWidget, grid=(row, 0), gridSpan=(1, 3), setLayout=True)

        LabeledHLine(namesFrame, text='Project Destinations', grid=(0, 0), gridSpan=(1, 3),
                     style='SolidLine', colour=self._GREY, sides='both')

        self.checkLabel = Label(namesFrame, text="Full Table", grid=(1, 0), hAlign='right')
        self.checkBox = CheckBox.CheckBox(namesFrame, grid=(1, 1), checked=True,
                                          callback=self._updateCallback)

        # row += 1
        # Label(self.mainWidget, grid=(2,0), hAlign='right')
        self.fullTableName = LineEdit.LineEdit(namesFrame, text='AssignmentCompleteness', grid=(1, 2),
                                               textAlignment='left')
        # Label(self.mainWidget, text="---> Assignment Table", grid=(row, _col2), hAlign='right')
        # self.fullTableName = LineEdit.LineEdit(self.mainWidget, text='AssignmentCompleteness', grid=(row, _col2 + 1),
        #                                        textAlignment='left')
        self.fullTableName.setMinimumWidth(200)

        self.checkLabel1 = Label(namesFrame, text="Summary Table", grid=(2, 0), hAlign='right')
        self.checkBox1 = CheckBox.CheckBox(namesFrame, grid=(2, 1), checked=True,
                                           callback=self._updateCallback)
        self.summaryTableName = LineEdit.LineEdit(namesFrame, text='SummaryAssignment', grid=(2, 2),
                                                  textAlignment='left')
        self.summaryTableName.setMinimumWidth(200)

        self.checkLabel2 = Label(namesFrame, text="Assigned CS Table", grid=(3, 0), hAlign='right')
        self.checkBox2 = CheckBox.CheckBox(namesFrame, grid=(3, 1), checked=True,
                                           callback=self._updateCallback)

        self.CSsummaryTableName = LineEdit.LineEdit(namesFrame, text='AssignedChemicalShifts', grid=(3, 2),
                                                    textAlignment='left')
        self.CSsummaryTableName.setMinimumWidth(200)

        self.checkLabel3 = Label(namesFrame, text="Possible problems", grid=(4, 0), hAlign='right')
        self.checkBox3 = CheckBox.CheckBox(namesFrame, grid=(4, 1), checked=True,
                                           callback=self._updateCallback)

        self.ProblemTableName = LineEdit.LineEdit(namesFrame, text='PossibleProblems', grid=(4, 2),
                                                  textAlignment='left')
        self.ProblemTableName.setMinimumWidth(200)

        # temporally hashed - until work out how to do list, eg 1-12, -> hashed lines 749
        # row += 1
        # self.checkLabel4 = Label(self.mainWidget, text="Exclude Residue", grid=(row, 0), hAlign='right')
        # self.checkBox4 = CheckBox.CheckBox(self.mainWidget, grid=(row, 1), checked=False,
        #                                    callback=self._updateCallback)
        #
        # Label(self.mainWidget, text="---> Residue List (comma seperated)", grid=(row, _col2), hAlign='right')
        # self.exludeResidueList = LineEdit.LineEdit(self.mainWidget, text='1,2,3', grid=(row, _col2 + 1),
        #                                           textAlignment='left')
        # self.exludeResidueList.setMinimumWidth(100)

        self.checkLabelIgnoreN = Label(namesFrame, text="Ignore N-terminus N", grid=(5, 0), hAlign='right')
        self.checkBoxignoreN = CheckBox.CheckBox(namesFrame, grid=(5, 1), checked=True,
                                                 callback=self._updateCallback)
        self.checkLabelDateTime = Label(namesFrame, text="Add timestamps", grid=(6, 0), hAlign='right')
        self.checkBoxDateTime = CheckBox.CheckBox(namesFrame, grid=(6, 1), checked=False,
                                                  callback=self._updateCallback)

        self._updateCallback()

    def _getPathFromDialog(self):

        _currentPath = self.pathData.get()

    def _updateCallback(self):
        """Update the entry boxes"""
        self.summaryTableName.setEnabled(self.checkBox1.get())
        self.summaryTableName.setEnabled(self.checkBox1.get())
        self.fullTableName.setEnabled(self.checkBox.get())
        self.chemicalShiftListWidget.selectFirstItem()
        self.chainListWidget.selectFirstItem()

    def _importData(self):

        if self.project:
            if (chn := self.chainListWidget.getSelectedObject()) is None:
                MessageDialog.showWarning('', 'Select a Chain first')
                return

            if (csl := self.chemicalShiftListWidget.getSelectedObject()) is None:
                MessageDialog.showWarning('', 'Select a Chemical Shift List first')
                return

            csl = self.chemicalShiftListWidget.getSelectedObject()
            #for cs in csl.chemicalShifts:
            #    print(cs, cs.nmrAtom, cs.nmrAtom.atom)

            #    if cs.nmrAtom.atom is None:
            #        MessageDialog.showWarning(cs, 'there is a problem with this shift')
            #        return

            # run the calculation
            with undoBlockWithoutSideBar():
                with notificationEchoBlocking():

                    excludeList = []
                    # if self.checkBox4.isChecked():
                    #     excludeList = self.exludeResidueList.text().split(',')
                    #     excludeList = [int(i) for i in excludeList]

                    data = calculateAssignments(self.project,
                                                csl.pid,
                                                chn.pid,
                                                excludeList,
                                                self.checkBoxignoreN.isChecked())

                    if self.checkBoxDateTime.isChecked():
                        current_time = datetime.now()
                        date_string = current_time.strftime("_%Y-%m-%d_%H:%M:%S")
                    else:
                        date_string = ""

                    # values in tables are stored as strings with empty values denoted with a space,
                    # This is to prevent the tables from printing NA values for empty cells and cluttering view
                    # The result is that you cannot for instance search by chemical shifts >X
                    # It also means empty values can be filtered by excluding space (' ')

                    if self.checkBox2.isChecked():
                        # report Summary Table
                        _data2 = data.AssignedResidueTable.dropna(axis=1, how='all').fillna(' ').applymap(
                                lambda x: '-' if x == 0 else x)
                        self.project.newDataTable(name=self.CSsummaryTableName.text() + date_string, data=_data2,
                                                  comment='List of all shifts (including incorrect) for known atoms')

                    if self.checkBox.isChecked():
                        # Report Full DataTable
                        _data = data.proteinDetailsArray.round(2).dropna(axis=1, how='all').fillna(' ').astype(str)
                        self.project.newDataTable(name=self.fullTableName.text() + date_string, data=_data,
                                                  comment='Table with expected shifts')

                        _data = data.allProteinDetails.dropna(axis=1, how='all').fillna(' ')
                        #self.project.newDataTable(name=self.fullTableName.text()+date_string+'_all', data=_data,
                        #                          comment='All residue details')

                    if self.checkBox1.isChecked():
                        # report Summary Table
                        _data1 = data.summaryTable.dropna(axis=1, how='all').fillna(' ').astype(str)
                        self.project.newDataTable(name=self.summaryTableName.text() + date_string, data=_data1,
                                                  comment='Percentage of assigned atoms')

                    if self.checkBox3.isChecked():
                        # report Summary Table
                        #print(data.problemArray.apply(pd.to_numeric, errors='ignore').dtypes)
                        _data2 = data.problemArray.apply(pd.to_numeric, errors='ignore').round(2).dropna(axis=1,
                                                                                                         how='all').fillna(
                                ' ').astype(str)
                        self.project.newDataTable(name=self.ProblemTableName.text() + date_string, data=_data2,
                                                  comment='Problematic Chemical Shift')

            self.accept()

    def _cleanupDialog(self):
        self.chainListWidget.unRegister()
        self.chemicalShiftListWidget.unRegister()


def main():
    popup = CalculateAssignmentDataPopup(mainWindow=mainWindow)
    popup.exec_()


if __name__ == '__main__':
    main()
