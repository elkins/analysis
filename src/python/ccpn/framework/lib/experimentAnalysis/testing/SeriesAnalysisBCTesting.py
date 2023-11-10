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
__dateModified__ = "$dateModified: 2023-11-10 16:12:24 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.framework.lib.experimentAnalysis.testing.ExperimentAnalysisTesting import ExperimentAnalysisTestingBC



class SeriesAnalysisABC_Test(ExperimentAnalysisTestingBC):

    # =========================================================================================
    # setUp       initialise a new project
    # =========================================================================================

    def setUp(self):
        """
        Test the SeriesAnalysisABC class contains the right methods.
        """
        from ccpn.framework.lib.experimentAnalysis.backends.SeriesAnalysisABC import SeriesAnalysisABC
        with self.initialSetup():
            self.seriesAnalysisABC = SeriesAnalysisABC()

    def test_classVariableType_fittingModels(self):
        """Test the class Variable fittingModels is of the correct type."""
        from ccpn.util.OrderedSet import OrderedSet
        message = "fittingModels class-variable is not of instance OrderedSet."
        self.assertIsInstance(self.seriesAnalysisABC.fittingModels, OrderedSet, message)

    def test_registerFittingModel_badModelType(self):
        """Test if a bad FittingModel Type fails to register. Pass if a valueError is raised """
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC

        message = f'The given fittingModel is not of instance {FittingModelABC}.'
        badModelExample = 'A_wrong_model_type'
        with self.assertRaises(ValueError):
            self.seriesAnalysisABC.registerModel(badModelExample)
            self.assertTrue(message)

    def test_registerFittingModel_goodModelType(self):
        """Test if a correct FittingModel Type is registered correctly. Fail if an error is raised """
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import T1FittingModel
        message = f'An unexpected error was raising registering a correct Type FittingModel.'
        goodModelExample = T1FittingModel()
        try:
            self.seriesAnalysisABC.registerModel(goodModelExample)
        except ValueError:
            self.fail(message)

    def test_deregisterFittingModel(self):
        """Test if a correct FittingModel Type is deregistered correctly. Fail if an error is raised """
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import T1FittingModel
        message = f'An unexpected error was raising registering a correct Type FittingModel.'
        fittingModel = T1FittingModel()
        self.seriesAnalysisABC.registerModel(fittingModel)
        try:
            self.seriesAnalysisABC.deRegisterModel(fittingModel)
        except ValueError:
            self.fail(message)

    def test_getFittingModelByName(self):
        """Test if a FittingModel is retrieved correctly by name."""
        from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import T1FittingModel
        queryName = T1FittingModel.modelName
        fittingModel = T1FittingModel()
        self.seriesAnalysisABC.registerModel(fittingModel)
        message = "getFittingModelByName retrieved the wrong Object"
        foundFittingModel =  self.seriesAnalysisABC.getFittingModelByName(queryName)
        self.assertEqual(fittingModel, foundFittingModel, message)
