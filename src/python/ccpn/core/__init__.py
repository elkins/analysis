"""CCPN core package. High level interface for normal data access

Projects are saved by myProject.save(path, ...)

Within the CcpNmr suite there is always a project open, assigned to the variable 'project'.

Module Organisation
-------------------

Class Hierarchy
^^^^^^^^^^^^^^^

Classes are organised in a hierarchy, with all data objects ultimately contained within the Project:
The diagram shows the hierarchy, with child objects displaced to the right of the containing parent
object. E.g. Spectrum, SpectrumGroup, and StructureData are all children of Project; PeakList and
IntegralList are both children of Spectrum; and Peak is a child of PeakList.

::

  Project
  \-------Spectrum
          \-------SpectrumReference
          \-------PeakList
                  \-------Peak
          \-------IntegralList
                  \-------Integral
          \-------PseudoDimension
          \-------SpectrumHit
  \-------SpectrumGroup
  \-------Sample
          \-------SampleComponent
  \-------Substance
  \-------Chain
          \-------Residue
                  \-------Atom
  \-------Complex
  \-------NmrChain
          \-------NmrResidue
                  \-------NmrAtom
  \-------ChemicalShiftList
          \-------ChemicalShift
  \-------StructureData
          \-------RestraintTable
                  \-------Restraint
                          \-------RestraintContribution
          \-------CalculationStep
          \-------Data
  \-------StructureEnsemble
          \-------Model
  \-------Note
  \-------Collection
  \-------DataTable

The **Project** object serves as container for all other data objects and the starting
point for navigation.

A **Spectrum** object contains all the stored properties of a spectrum, as well as the path to the
stored NMR data file.

A **SpectrumReference** holds detailed information about axes and referencing needed for
e.g. multple-quantum, projection, and reduced-dimensionality experiments.

A **PeakList** serves as a container for **Peak** objects,
which contain Peak position, intensity and assignment information.

An **IntegralList** serves as a container for **Integral**
objects, which contain Integral intervals and values.

A **PseudoDimension** object is used to describe
sampled-value axes, such as the time delay axis for T1 experiments.

A **SpectrumHis** object is used in screening and metabolomics implementations to describe
that a Substance has been found to be present (metabolomics) or active (screening) in a given
spectrum.

A **SpectrumGroup** combines multiple Spectrum objects, so they can be treated as a single object.

A **Sample** corresponds to an NMR sample. It is made up of **SampleComponents**, which indicate
which individual chemical entities make up that Sample, (e.g. protein, buffer, salt), and
their concentrations.

A **Substance** object represents a defined chemical entity, e.g. Lysozyme, ATP, NaCl, or (less
commonly) a composite material like fetal calf serum or standard lysis buffer.

A **Chain** object corresponds to a molecular chain. It is made up of **Residue** objects,
which in turn are made up of **Atom** objects.

A **Complex** is a group of chain objects, combined so that they can be treated as a single
object.

Assignment is done through a hierarchy of **NmrChain**, **NmrResidue**, and **NmrAtom**
objects. that parallels the hierarchy of molecular chains. An NmrChain (NmrResidue, Atom) is
considered assigned to the Chain (Residue, Atom) with the same ID.
NmrAtom objects serve as a way of connecting a named nucleus to an observed chemical shift, and
peaks are assigned to NmrAtoms.

A **ChemicalShiftList** object is a container for **ChemicalShift** objects, which represent
observed chemical shifts.

**StructureData** objects serve to group RestraintTables/ViolationTables and other input and output from a
calculation.

A **RestraintTable** contains **Restraint** Objects of a specific type (distance, dihedral, etc.).
**RestraintContribution** objects hold the detailed information; they are needed for
complex restraints, like coupled phi and psi dihedral restraints.

The **CalculationStep** object is used to track the calculation history of StructureData, storing
input and output StructureData IDs, and the names of the programs used.

**Data** object storing links to the data structures (PeakLists, Spectra, StructureEnsembles
etc.) connected to a given StructureData, and their associated calculation parameters.

A **StructureEnsemble** object is a container for ensembles of coordinate structures, with each
coordinate structure defined by a **Model** object.

**Note** objects contain free-text information to be stored in a project.

A **Collection** is a container, a list of core objects. It can also contain nested collections.

A **DataTable** is a container for a pandas dataFrame object.


Common Class elements
^^^^^^^^^^^^^^^^^^^^^

All classes in this module are subclasses of the core._implementation.AbstractWrapperObject,
and inherit the following elements:

**project** - *ccpn.core.Project*

The Project (root) containing the object.

**pid** - *ccpn.util.Pid.Pid*

Identifier for the object, unique within the project.
Set automatically from the short class name and object.id
E.g. 'NA:A.102.ALA.CA'

**longPid** - *ccpn.util.Pid.Pid*

Identifier for the object, unique within the project.
Set automatically from the full class name and object.id
E.g. 'NmrAtom:A.102.ALA.CA'

**id** - *str*

Identifier for the object, used to generate the pid and longPid.
Generated by combining the id of the containing object, with the
value of one or more key attributes that uniquely identify the
object in context.
E.g. the id for an Atom, 'A.55.VAL.HA' is generated from:

    - 'A' *Chain.shortName*

    - '55' *Residue.sequenceCode*

    - 'VAL' *Residue.residueType*

    - 'HA' *Atom.name*

**delete()**

Delete object, with all contained objects and underlying data.

**getByPid(pidString)**

Get an arbitrary data object from either its pid (e.g. 'SP:HSQC2') or its longPid
(e.g. 'Spectrum:HSQC2'

Returns None for invalid or unrecognised input strings.

**rename(newName)**

Change the object name or other key attribute(s), changing the object id, pid,
and all internal references to maintain consistency.
A number of Objects (Chain, Residue, Atom, Peak, cannot be renamed

Data access
^^^^^^^^^^^

The data of objects are accessed with the normal Python syntax (x = object.value; object.value = x.
There are no public getter and setter functions. For collections you will get an unmodifiable copy
of the internal collection, to prevent accidental modification of the data
(e.g. myPeakList.peaks will return a tuple, not a list)

Each object has a link to the containing (parent) object (e.g. myPeakList.spectrum)

Each class has a link to contained objects,
and a function to get a contained object by relative id.
E.g. myProject.peaks, mySpectrum.peaks, and myPeakList.peaks will each get
all peaks contained within the relevant object. The lists will be in creation order
(where applicable) otherwise sorted by name or underlying key.
Similarly, a given peak can be found by either myProject.getPeak('HSQC2.1.593'),
mySpectrum.getPeak('1.593'), or myPeakList.getPeak('593')

Most objects can be created using a *newXyzObject* method on the parent.
E.g. you can create a new Restraint object with the myRestraintTable.newRestraint(...) function.
'new' functions create a single objects, using the passed-in parameters.
There is no 'newSpectrum' function; spectra are created with 'loadSpectrum' as a complete spectrum
object requires an external file with the data.

More complex object creation is done with 'create...()' functions, that may create multiple
objects, and use heuristics to fill in missing parameters.
E.g. the myRestraintTable.createRestraint(....) function creates a Restraint with the
contained RestraintContributions and restraintItems.

Functions whose names start with 'get' (e.g. getNmrAtom(...)) mostly take some kind of identifier
as an argument and returns the identified object if it exists, None otherwise.

Functions whose names start with 'fetch' (e.g. fetchNmrAtom(...)) also take some kind of identifier
as an argument.
These will return the identified object if it exists, but will create a new object otherwise.

Other common prefixes for function names include 'add' and 'remove' (which add and remove
pre-existing objects to collections), 'copy', 'clear', 'load', 'process' and 'toggle',
all of which should be self-explanatory.

Objects sort by type (in import order) then by parent, then by local key.
Sorting the objects will give a sensible and reproducible ordering for all classes.
A number of classes are returned sorted by creation order (e.g. NmrAtoms), but are
sorted by a more significant key (for NmrAtoms alphabetically by name).
ChemicalShift objects sort as the NmrAtom they belong to.
NmrResidue objects behave in there different ways:

  - If they are assigned to a Residue they sort like the Residue, in sequential order
  - If they belong to a connected NmrChain, they sort by the order they appear in the NmrChain.
  - In other 4cases they sort by creation order.
  - Offset NmrResidues in all cases sort alongside their main NmrResidue, by offset.

"""

# Previous documentation with links to top level functions. Kept here to serve as example


# All data are organised in Projects. The standard ways of starting a project are:
#
# - myProject = :ref:`ccpn-loadProject-ref` (*path*, ...)
# - myProject = :ref:`ccpn-newProject-ref` (*projectName*, ...)


# .. currentmodule:: ccpn
#
# Module level functions :
# ------------------------
#
# .. _ccpn-loadProject-ref:
#
# ccpn.loadProject
# ^^^^^^^^^^^^^^^^
#
# .. autofunction:: ccpn.loadProject
#
# .. _ccpn-newProject-ref:
#
# ccpn.newProject
# ^^^^^^^^^^^^^^^
#
# .. autofunction:: ccpn.newProject

#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (http://www.ccpn.ac.uk) 2014 - 2017"
__credits__ = ("Wayne Boucher, Ed Brooksbank, Rasmus H Fogh, Luca Mureddu, Timothy J Ragan & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               "or ccpnmodel.ccpncore.memops.Credits.CcpnLicense for licence text")
__reference__ = ("For publications, please use reference from http://www.ccpn.ac.uk/v3-software/downloads/license",
                 "or ccpnmodel.ccpncore.memops.Credits.CcpNmrReference")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: CCPN $"
__dateModified__ = "$dateModified: 2017-07-07 16:32:44 +0100 (Fri, July 07, 2017) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

# Import classes and set to this module
# All classes must be imported in correct order for subsequent code
# to work

_PRINT_HOTFIXES = False
_coreImportOrder = (
    'Project',
    'Spectrum',
    'SpectrumReference',
    'PseudoDimension',
    'PeakList',
    'Peak',
    'IntegralList',
    'Integral',
    'MultipletList',
    'Multiplet',
    'SpectrumHit',
    'SpectrumGroup',
    'Sample',
    'SampleComponent',
    'Substance',
    'Chain',
    'Residue',
    'Atom',
    'Complex',
    'NmrChain',
    'NmrResidue',
    'NmrAtom',
    'ChemicalShiftList',
    '_OldChemicalShift',
    'ChemicalShift',
    'StructureData',
    'RestraintTable',
    'Restraint',
    'RestraintContribution',
    'ViolationTable',
    'CalculationStep',
    'Data',
    'StructureEnsemble',
    'Model',
    'DataTable',
    'Collection',
    'Note',
    '_PeakCluster',
    )

# Register the classes
"""  Note very important! do not import here a module like:
        >>>  from ccpn.core.Project import Project  
     
     because It directly binds Project to the class within the ccpn.core.Project namespace. If you later use somewhere:
       >>>  import ccpn.core.Project
        
    It will unexpectedly point to the Project class rather than the module, effectively “shadowing” the module itself, creating a very nasty bug.
    
   In other words:
   Here in __init__.py
   DO NOT DO
   from ccpn.core.Project import Project. Will make a mess on namespaces!
   do instead from ccpn.core.Project import Project as _Project 
    In any other files is ok importing the class Project that way.     
    for macro users: if you need the Project class, use instead
    from ccpn.api import Project
    

"""
from ccpn.core.Project import Project as _Project
_Project._registerCoreClass()

from ccpn.core.Spectrum import Spectrum as _Spectrum
_Spectrum._registerCoreClass()

from ccpn.core.SpectrumReference import SpectrumReference as _SpectrumReference
_SpectrumReference._registerCoreClass()

from ccpn.core.PseudoDimension import PseudoDimension as _PseudoDimension
_PseudoDimension._registerCoreClass()

from ccpn.core.PeakList import PeakList as _PeakList
_PeakList._registerCoreClass()

from ccpn.core.Peak import Peak as _Peak
_Peak._registerCoreClass()

from ccpn.core.IntegralList import IntegralList as _IntegralList
_IntegralList._registerCoreClass()

from ccpn.core.Integral import Integral as _Integral
_Integral._registerCoreClass()

from ccpn.core.MultipletList import MultipletList as _MultipletList
_MultipletList._registerCoreClass()

from ccpn.core.Multiplet import Multiplet as _Multiplet
_Multiplet._registerCoreClass()

from ccpn.core.SpectrumHit import SpectrumHit as _SpectrumHit
_SpectrumHit._registerCoreClass()

from ccpn.core.SpectrumGroup import SpectrumGroup as _SpectrumGroup
_SpectrumGroup._registerCoreClass()

from ccpn.core.Sample import Sample as _Sample
_Sample._registerCoreClass()

from ccpn.core.SampleComponent import SampleComponent as _SampleComponent
_SampleComponent._registerCoreClass()

from ccpn.core.Substance import Substance as _Substance
_Substance._registerCoreClass()

from ccpn.core.Chain import Chain as _Chain
_Chain._registerCoreClass()

from ccpn.core.Residue import Residue as _Residue
_Residue._registerCoreClass()

from ccpn.core.Atom import Atom as _Atom
_Atom._registerCoreClass()

from ccpn.core.Bond import Bond as _Bond
_Bond._registerCoreClass()

from ccpn.core.Complex import Complex as _Complex
_Complex._registerCoreClass()

from ccpn.core.NmrChain import NmrChain as _NmrChain
_NmrChain._registerCoreClass()

from ccpn.core.NmrResidue import NmrResidue as _NmrResidue
_NmrResidue._registerCoreClass()

from ccpn.core.NmrAtom import NmrAtom as _NmrAtom
_NmrAtom._registerCoreClass()

from ccpn.core.ChemicalShiftList import ChemicalShiftList as _ChemicalShiftList
_ChemicalShiftList._registerCoreClass()

from ccpn.core._implementation._OldChemicalShift import _OldChemicalShift as _ocs
_ocs._registerCoreClass()

from ccpn.core.ChemicalShift import ChemicalShift as _ChemicalShift
_ChemicalShift._registerCoreClass()

from ccpn.core.StructureData import StructureData as _StructureData
_StructureData._registerCoreClass()

from ccpn.core.RestraintTable import RestraintTable as _RestraintTable
_RestraintTable._registerCoreClass()

from ccpn.core.Restraint import Restraint as _Restraint
_Restraint._registerCoreClass()

from ccpn.core.RestraintContribution import RestraintContribution as _RestraintContribution
_RestraintContribution._registerCoreClass()

from ccpn.core.ViolationTable import ViolationTable as _ViolationTable
_ViolationTable._registerCoreClass()

from ccpn.core.CalculationStep import CalculationStep as _CalculationStep
_CalculationStep._registerCoreClass()

from ccpn.core.Data import Data as _Data
_Data._registerCoreClass()

from ccpn.core.DataTable import DataTable as _DataTable
_DataTable._registerCoreClass()

from ccpn.core.StructureEnsemble import StructureEnsemble as _StructureEnsemble
_StructureEnsemble._registerCoreClass()

from ccpn.core.Model import Model as _Model
_Model._registerCoreClass()

from ccpn.core.Collection import Collection as _Collection
_Collection._registerCoreClass()

from ccpn.core.Note import Note as _Note
_Note._registerCoreClass()

# GUI classes
_uiImportOrder = (
    'Window',
    'SpectrumDisplay',
    'Strip',
    'Axis',
    'SpectrumView',
    'PeakListView',
    'PeakView',
    'MultipletListView',
    'MultipletView',
    'IntegralListView'
    'IntegralView',
    'Mark',
    )

from ccpn.ui.gui.MainWindow import MainWindow as _MainWindow
_MainWindow._registerCoreClass()

from ccpn.ui._implementation.Mark import Mark as _Mark
_Mark._registerCoreClass()

from ccpn.ui.gui.modules.SpectrumDisplay import SpectrumDisplay as _SpectrumDisplay
_SpectrumDisplay._registerCoreClass()

from ccpn.ui.gui.lib.Strip import Strip as _Strip
_Strip._registerCoreClass()

from ccpn.ui._implementation.Axis import Axis as _Axis
_Axis._registerCoreClass()

from ccpn.ui.gui.lib.SpectrumView import SpectrumView as _SpectrumView
_SpectrumView._registerCoreClass()

from ccpn.ui.gui.lib.PeakListView import PeakListView as _PeakListView
_PeakListView._registerCoreClass()

from ccpn.ui._implementation.PeakView import PeakView as _PeakView
_PeakView._registerCoreClass()

from ccpn.ui.gui.lib.MultipletListView import MultipletListView as _MultipletListView
_MultipletListView._registerCoreClass()

from ccpn.ui._implementation.MultipletView import MultipletView as _MultipletView
_MultipletView._registerCoreClass()

from ccpn.ui.gui.lib.IntegralListView import IntegralListView as _IntegralListView
_IntegralListView._registerCoreClass()

from ccpn.ui._implementation.IntegralView import IntegralView as _IntegralView
_IntegralView._registerCoreClass()

from ccpn.core._implementation._PeakCluster import _PeakCluster
_PeakCluster._registerCoreClass()

_allGetters = {}
_Project._linkWrapperClasses(_allGetters=_allGetters)

if _PRINT_HOTFIXES:
    # print the hotfixes to save to change-log/edit into core classes
    for grp, stubs in sorted(_allGetters.items(), key=lambda val: val[0]):
        print(f'\n\n\n#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n# --> {grp}')

        header = True
        for num, stub in sorted(stubs):
            if not stub.startswith('get'):
                if header:
                    header = False
                    # header for property section
                    print(f'#=========================================================================================')
                    print(f'# property STUBS: hot-fixed later')
                    print(f'#=========================================================================================\n')

                if stub == 'spectra':
                    lbl = 'Spectrum'
                elif stub == 'axes':
                    lbl = 'Axis'
                elif stub == 'complexes':
                    lbl = 'Complex'
                else:
                    lbl = stub[0].upper() + (stub[1:-1] if stub.endswith('s') else stub[1:])
                # print code-stub for property
                print(f'''@property
    def {stub}(self) -> list['{lbl}']:
        """STUB: hot-fixed later
        :return: a list of {stub} in the {grp}
        """
        return []
    '''
                      )

        header = True
        for num, stub in sorted(stubs):
            if stub.startswith('get'):
                if header:
                    header = False
                    # header for getter section
                    print(f'#=========================================================================================')
                    print(f'# getter STUBS: hot-fixed later')
                    print(f'#=========================================================================================\n')

                # print code-stub for getter
                print(f'''def {stub}(self, relativeId: str) -> '{stub[3:]} | None':
        """STUB: hot-fixed later
        :return: an instance of {stub[3:]}, or None
        """
        return None
    '''
                      )
        # header for the next block
        print(f'#=========================================================================================')
        print(f'# Core methods')
        print(f'#=========================================================================================\n')

#=========================================================================================
# current list of getters for core objects - inserted by _linkWrapperClasses
#     Chain.atoms
#     Chain.getAtom
#     Chain.getResidue
#     Chain.residues
#     ChemicalShiftList._oldChemicalShifts
#     ChemicalShiftList.get_OldChemicalShift
#     IntegralList.getIntegral
#     IntegralList.integrals
#     MultipletList.getMultiplet
#     MultipletList.multiplets
#     NmrChain.getNmrAtom
#     NmrChain.getNmrResidue
#     NmrChain.nmrAtoms
#     NmrChain.nmrResidues
#     NmrResidue.getNmrAtom
#     NmrResidue.nmrAtoms
#     PeakList.getPeak
#     PeakList.peaks
#     Project._oldChemicalShifts
#     Project._peakClusters
#     Project.atoms
#     Project.axes
#     Project.calculationSteps
#     Project.chains
#     Project.chemicalShiftLists
#     Project.complexes
#     Project.data
#     Project.dataTables
#     Project.getAtom
#     Project.getAxis
#     Project.getCalculationStep
#     Project.getChain
#     Project.getChemicalShiftList
#     Project.getComplex
#     Project.getData
#     Project.getDataTable
#     Project.getIntegral
#     Project.getIntegralList
#     Project.getIntegralListView
#     Project.getMark
#     Project.getModel
#     Project.getMultiplet
#     Project.getMultipletList
#     Project.getMultipletListView
#     Project.getNmrAtom
#     Project.getNmrChain
#     Project.getNmrResidue
#     Project.getNote
#     Project.getPeak
#     Project.getPeakList
#     Project.getPeakListView
#     Project.getPseudoDimension
#     Project.getResidue
#     Project.getRestraint
#     Project.getRestraintContribution
#     Project.getRestraintTable
#     Project.getSample
#     Project.getSampleComponent
#     Project.getSpectrum
#     Project.getSpectrumDisplay
#     Project.getSpectrumGroup
#     Project.getSpectrumHit
#     Project.getSpectrumReference
#     Project.getSpectrumView
#     Project.getStrip
#     Project.getStructureData
#     Project.getStructureEnsemble
#     Project.getSubstance
#     Project.getViolationTable
#     Project.getWindow
#     Project.get_OldChemicalShift
#     Project.get_PeakCluster
#     Project.integralListViews
#     Project.integralLists
#     Project.integrals
#     Project.marks
#     Project.models
#     Project.multipletListViews
#     Project.multipletLists
#     Project.multiplets
#     Project.nmrAtoms
#     Project.nmrChains
#     Project.nmrResidues
#     Project.notes
#     Project.peakListViews
#     Project.peakLists
#     Project.peaks
#     Project.pseudoDimensions
#     Project.residues
#     Project.restraintContributions
#     Project.restraintTables
#     Project.restraints
#     Project.sampleComponents
#     Project.samples
#     Project.spectra
#     Project.spectrumDisplays
#     Project.spectrumGroups
#     Project.spectrumHits
#     Project.spectrumReferences
#     Project.spectrumViews
#     Project.strips
#     Project.structureData
#     Project.structureEnsembles
#     Project.substances
#     Project.violationTables
#     Project.windows
#     Residue.atoms
#     Residue.getAtom
#     Restraint.getRestraintContribution
#     Restraint.restraintContributions
#     RestraintTable.getRestraint
#     RestraintTable.getRestraintContribution
#     RestraintTable.restraintContributions
#     RestraintTable.restraints
#     Sample.getSampleComponent
#     Sample.sampleComponents
#     Spectrum.getIntegral
#     Spectrum.getIntegralList
#     Spectrum.getMultiplet
#     Spectrum.getMultipletList
#     Spectrum.getPeak
#     Spectrum.getPeakList
#     Spectrum.getPseudoDimension
#     Spectrum.getSpectrumHit
#     Spectrum.getSpectrumReference
#     Spectrum.integralLists
#     Spectrum.integrals
#     Spectrum.multipletLists
#     Spectrum.multiplets
#     Spectrum.peakLists
#     Spectrum.peaks
#     Spectrum.pseudoDimensions
#     Spectrum.spectrumHits
#     Spectrum.spectrumReferences
#     SpectrumDisplay.axes
#     SpectrumDisplay.getAxis
#     SpectrumDisplay.getIntegralListView
#     SpectrumDisplay.getMultipletListView
#     SpectrumDisplay.getPeakListView
#     SpectrumDisplay.getSpectrumView
#     SpectrumDisplay.getStrip
#     SpectrumDisplay.integralListViews
#     SpectrumDisplay.multipletListViews
#     SpectrumDisplay.peakListViews
#     SpectrumDisplay.spectrumViews
#     SpectrumDisplay.strips
#     SpectrumView.getIntegralListView
#     SpectrumView.getMultipletListView
#     SpectrumView.getPeakListView
#     SpectrumView.integralListViews
#     SpectrumView.multipletListViews
#     SpectrumView.peakListViews
#     Strip.axes
#     Strip.getAxis
#     Strip.getIntegralListView
#     Strip.getMultipletListView
#     Strip.getPeakListView
#     Strip.getSpectrumView
#     Strip.integralListViews
#     Strip.multipletListViews
#     Strip.peakListViews
#     Strip.spectrumViews
#     StructureData.calculationSteps
#     StructureData.data
#     StructureData.getCalculationStep
#     StructureData.getData
#     StructureData.getRestraint
#     StructureData.getRestraintContribution
#     StructureData.getRestraintTable
#     StructureData.getViolationTable
#     StructureData.restraintContributions
#     StructureData.restraintTables
#     StructureData.restraints
#     StructureData.violationTables
#     StructureEnsemble.getModel
#     StructureEnsemble.models
#=========================================================================================
