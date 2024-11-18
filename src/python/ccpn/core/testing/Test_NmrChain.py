"""Test code for NmrChain

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
__dateModified__ = "$dateModified: 2024-11-18 13:19:03 +0000 (Mon, November 18, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.testing.WrapperTesting import WrapperTesting, getProperties
from ccpnmodel.ccpncore.memops.ApiError import ApiError


class NmrChainTest(WrapperTesting):
    projectPath = None

    def test_NmrChain_naming(self):
        nchain0 = self.project.getByPid('NC:@-')
        self.assertEqual(nchain0._wrappedData.serial, 1)

        ncx = self.project.getNmrChain('@-')
        self.assertIs(nchain0, ncx)
        nchain1 = self.project.newNmrChain()
        self.assertEqual(nchain1.shortName, '@2')
        nchain2 = self.project.newNmrChain(isConnected=True)
        self.assertEqual(nchain2.shortName, '#3')
        nchain3 = self.project.newNmrChain('#5')
        self.assertEqual(nchain3.shortName, '#5')
        nchain4 = self.project.newNmrChain('@4')
        self.assertEqual(nchain4.shortName, '@4')

        self.assertRaises(ValueError, nchain0.rename, 'something')
        self.assertRaises(ValueError, self.project.newNmrChain, shortName='@-')
        self.assertRaises(ValueError, self.project.newNmrChain, shortName='@2')
        self.assertRaises(ValueError, self.project.newNmrChain, shortName='#2')
        nchain4.delete()
        nchain4 = self.project.newNmrChain(shortName='#4')
        self.assertEqual(nchain4.shortName, '#4')

        nc2 = self.project.newNmrChain(isConnected=True)
        self.assertEqual(nc2.shortName, '#6')
        self.assertRaises(ValueError, nc2.rename, '@6')

        nc3 = self.project.newNmrChain()
        undo_id = nc3.pid
        self.undo.undo()
        self.assertNotEqual(undo_id, nc3.pid)
        self.undo.redo()
        self.assertEqual(nc3.shortName, '@7')
        self.assertEqual(undo_id, nc3.pid)
        self.assertRaises(ApiError, nc3.rename, '#7')

        # cannot create chain beginning with @- for safety/clarity
        self.assertRaises(ValueError, self.project.newNmrChain, shortName='@-_new')

    def test_deassignRenameError(self):
        with self.assertRaises(ValueError) as cm:
            ncx = self.project.newNmrChain(isConnected=True)
            ncx.rename('error-name')
        err = cm.exception
        self.assertEqual(str(err), 'Connected NmrChain cannot be renamed')

    def test_NmrChain_Chain(self):
        chain = self.project.createChain(sequence='AACKC', shortName='x', molType='protein')
        nmrChain = self.project.newNmrChain(shortName='x')

        # undo redo all operations
        self.undo.undo()
        self.assertIn('Deleted', nmrChain.pid)
        self.undo.redo()
        self.assertNotIn('Deleted', nmrChain.pid)
        self.assertIs(nmrChain.chain, chain)
        self.assertIs(chain.nmrChain, nmrChain)

    def test_assignSingleResidue(self):
        n_chain = self.project.fetchNmrChain('AA')
        n_residue = n_chain.fetchNmrResidue(residueType='GLN')
        self.chain = self.project.createChain(sequence='CDEFGHI', molType='protein',
                                              shortName='A')
        residues = self.chain.residues

        n_residue_pid = n_residue.pid
        n_chain.assignSingleResidue(n_residue, residues[0])
        self.assertNotEqual(n_residue_pid, n_residue.pid)

        undo_pid = n_residue.pid

        self.undo.undo()
        self.assertEqual(n_residue_pid, n_residue.pid)
        self.undo.redo()
        self.assertEqual(undo_pid, n_residue.pid)

    def test_assignSingleResidueNoObjError(self):
        nmr_chain = self.project.fetchNmrChain('AA')
        nmr_residue = nmr_chain.fetchNmrResidue(residueType='GLN')
        with self.assertRaises(ValueError) as cm:
            nmr_chain.assignSingleResidue(nmr_residue, 'ERROR')
        err = cm.exception
        self.assertEqual(str(err), 'No object found matching Pid ERROR')

    def test_assignSingleResidueAlreadyAssignError(self):
        nmr_chain = self.project.fetchNmrChain('AA')
        nmr_residue = nmr_chain.fetchNmrResidue(residueType='GLN')

        self.chain = self.project.createChain(sequence='CDEFGHI', molType='protein',
                                              shortName='A')
        residues = self.chain.residues

        nmr_chain.assignSingleResidue(nmr_residue, residues[0])
        with self.assertRaises(ValueError) as cm:
            nmr_chain.assignSingleResidue(nmr_residue, residues[0])
        err = cm.exception
        self.assertEqual(str(err), f'Cannot assign {nmr_residue.id}: Residue {residues[0].id} is already assigned')

    def test_deassign(self):
        nmr_chain = self.project.fetchNmrChain('A')
        nmr_residue = nmr_chain.fetchNmrResidue(residueType='GLN')
        self.chain = self.project.createChain(sequence='CDEFGHI', molType='protein',
                                              shortName='A')
        residues = self.chain.residues
        nmr_chain.assignSingleResidue(nmr_residue, residues[4])

        self.assertEqual([nmrres.residue.id for nmrres in nmr_chain.nmrResidues], [residues[4].id])
        nmr_chain.deassign()
        self.assertEqual([nmrres.residue for nmrres in nmr_chain.nmrResidues], [None])

    def test_deassignAPIError(self):
        ncx = self.project.getNmrChain('@-')
        self.assertRaises(ApiError, ncx.deassign)
        self.assertEqual(ncx.pid, 'NC:@-')

    def test_renumberNmrResidues(self):
        num_residues = 10
        offset = 20

        n_chain = self.project.fetchNmrChain('@-')

        for i in range(num_residues):
            n_chain.newNmrResidue(sequenceCode=i)

        def code_splitter(code):
            splits = code.split('.')
            return splits[1]

        n_res_sc = [int(code_splitter(code.pid)) for code in n_chain.nmrResidues]
        n_chain.renumberNmrResidues(offset)
        n_res_sc1 = [int(code_splitter(code.pid)) - offset for code in n_chain.nmrResidues]

        self.assertListEqual(n_res_sc, n_res_sc1)

        n_chain.renumberNmrResidues(offset)
        n_chain.renumberNmrResidues(offset)

        self.undo.undo()
        n_res_sc2 = [int(code_splitter(code.pid)) - offset * 2 for code in n_chain.nmrResidues]
        self.assertListEqual(n_res_sc, n_res_sc2)

        self.undo.undo()
        n_res_sc3 = [int(code_splitter(code.pid)) - offset for code in n_chain.nmrResidues]
        self.assertListEqual(n_res_sc, n_res_sc3)

        self.undo.redo()
        n_res_sc2 = [int(code_splitter(code.pid)) - offset * 2 for code in n_chain.nmrResidues]
        self.assertListEqual(n_res_sc, n_res_sc2)
        self.undo.redo()
        n_res_sc2 = [int(code_splitter(code.pid)) - offset * 3 for code in n_chain.nmrResidues]
        self.assertListEqual(n_res_sc, n_res_sc2)
