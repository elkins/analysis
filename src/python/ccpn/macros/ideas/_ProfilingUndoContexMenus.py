"""
Version 3.0.3


"""


from ccpn.core.lib.ContextManagers import undoBlock, undoBlockWithoutSideBar, notificationEchoBlocking
import time
import random
import numpy as np
from contextlib import nullcontext
from collections import defaultdict
from scipy.integrate import trapz, simps
import time
from ccpn.core.lib.AssignmentLib import _assignNmrAtomsToPeaks
from ccpn.util.decorators import profile
from ccpn.ui.gui.lib.MenuActions import _openItemObject
import random
import math
from ccpn.ui.gui.widgets.MessageDialog import _stoppableProgressBar
from ccpn.AnalysisScreen.lib.spectralProcessing.__demoBrukerSpectrum import _lorentzian
import pandas as pd


def getShowModulesCalls():
    from ccpn.AnalysisAssign.AnalysisAssign import Assign
    from ccpn.AnalysisScreen.AnalysisScreen import Screen
    from ccpn.framework.Framework import Framework

    assignModules = [
                    Assign.showPickAndAssignModule,
                    Assign.showBackboneAssignmentModule,
                    # Assign.showSidechainAssignmentModule,
                    Assign.showPeakAssigner,
                    Assign.showAtomSelector,
                    Assign.showAssignmentInspectorModule,
                    Assign.showSequenceGraph,
                    ]
    
    screenModules = [
                    Screen.showMixtureAnalysis,
                    Screen.showScreeningPipeline,
                    # Screen.showHitAnalysisModule,
                    Screen.showDecompositionModule,
                    ]

    viewModules = [
                    Framework.showReferenceChemicalShifts,
                    Framework.showResidueInformation,
                    Framework.showChemicalShiftTable,
                    Framework.showNmrResidueTable,
                    Framework.showResidueTable,
                    Framework.showPeakTable,
                    Framework.showIntegralTable,
                    Framework.showMultipletTable,
                    Framework.showRestraintTable,
                    Framework.showStructureTable,
                    Framework.showChemicalShiftPerturbation,
                    Framework.showNotesEditor,
                    ]
    allModules = assignModules+screenModules+viewModules
    return allModules
def closeModulesExceptPythonConsole():
    for module in mainWindow.moduleArea.ccpnModules:
        if module != mainWindow.pythonConsoleModule:
            module._closeModule()

def newMockObjects(nSpectraToCreate = 1):
    t = time.time()
    sg = project.newSpectrumGroup(str(t))
    spectra = []
    nc = project.nmrChains[-1]
    sa = project.newSample()
    ch = project.createChain(sequence='YEYHGDAL', compoundName=str(t), shortName=str(t), molType='protein')

    name = t.__int__().__str__()
    for rr in _stoppableProgressBar(range(nSpectraToCreate)):  # should run in a separate thread
        sp = project.createDummySpectrum(name=str(rr) + name, axisCodes=['H'])
        su = project.newSubstance(sp.name + str(name))
        su.referenceSpectra = [sp]
        sa.newSampleComponent(su.name)
        sp.positions = np.arange(-4, 14, 0.001)
        noise = np.random.normal(size=sp.positions.shape)
        peakLines = []
        values = []
        for i in range(random.choice(np.arange(3, 10))):  # add random num of peaks at random positions and heights
            pos = random.choice(np.arange(1, 9, 0.01))
            lw = random.choice(np.arange(0, 0.1, 0.001))
            height = abs(np.max(noise) * random.choice(np.arange(10, 50, 1)))
            l = _lorentzian(sp.positions, pos, lw, intensity=height)
            integ = trapz(l)
            values.append((pos, lw, height, integ))
            peakLines.append(l)
        sp.intensities = noise + sum(peakLines)
        if not any(sp.intensities): continue
        spectra.append(sp)
        pl = sp.peakLists[-1]
        il = sp.newIntegralList()
        nr = nc.fetchNmrResidue(str(rr))
        for en, v in enumerate(values):
            pos, lw, height, integ = v
            i = il.newIntegral(value=None, limits=[[pos + lw, pos - lw], ])
            if not math.isnan(integ):
                i.value = integ
            i._baseline = np.nextafter(0, 1)
            p = pl.newPeak(ppmPositions=[pos, ], height=height)
            na = nr.fetchNmrAtom('H'+str(en))
            p.integral = i
            _assignNmrAtomsToPeaks([p], [na])
    sg.spectra = spectra
    current.peak = project.peaks[-1]
    current.nmrResidue = project.nmrResidues[-1]
    current.residue = project.residues[-1]
    current.integral = project.integrals[-1]

def changePeaks():
    print('Changing Peak properties for %s' %len(project.peaks))
    for peak in project.peaks:
        peak.comment = str(time.time())
        # peak.height = random.random()
        # randoms = np.full(shape=len(peak.ppmPositions), fill_value=random.random())
        # peak.ppmPositions = tuple(randoms)
        # peak.positionError = tuple(randoms/1000)


def timeUndos(func, createObjCount=2):
    """
    Time a function using different Undo context managers while a Gui module is open.
    :param func: a function to time
    :return: a df with execution times. Contexts names as columns, module name as indexes.
    """
    modulesCalls = getShowModulesCalls()
    contexts = [nullcontext, undoBlock, undoBlockWithoutSideBar]

    series = []

    for i in range(createObjCount):
        newMockObjects(i+1)
        allTimes = []
        modulesOpened = []
        for modulesCall in modulesCalls:
            times = []
            module = modulesCall(application)
            for context in contexts:
                it = time.time()
                with context():
                    func()
                runTime =  time.time() - it
                times.append(runTime)
            allTimes.append(times)
            modulesOpened.append(modulesCall.__name__.strip('show'))
            if module:
                module._closeModule()
        series.append(allTimes)
    # contextColumns = [context.__name__ for context in contexts]
    # df = pd.DataFrame(allTimes, columns=contextColumns, index=modulesOpened)
    # return df
    columns = [np.arange(createObjCount), ["noContext", "withSideBar", "withoutSideBar"]]
    ii = pd.MultiIndex.from_product(columns, names=["series", "context"])
    df = pd.DataFrame(series, columns=ii)
    return df

# with undoBlockWithoutSideBar():
#     newMockObjects(10)

df = timeUndos(changePeaks)
# df1 = timeUndos(changePeaks)

print('Done', df)






