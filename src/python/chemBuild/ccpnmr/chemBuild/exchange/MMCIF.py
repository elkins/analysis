"""
Reader for the Chemical Component as CIF format
see info at
https://www.wwpdb.org/data/ccd


Search engines:
https://www.ebi.ac.uk/pdbe-srv/pdbechem/

"""

from ccpnmr.chemBuild.exchange.ChemCompCIFParser import ChemCompCIFParser
from ccpnmr.chemBuild.general.Constants import LINK, AROMATIC
from ccpnmr.chemBuild.model.Compound import Compound
from ccpnmr.chemBuild.model.Variant import Variant
from ccpnmr.chemBuild.model.VarAtom import VarAtom
from ccpnmr.chemBuild.model.Atom import Atom
from ccpnmr.chemBuild.model.AtomGroup import AtomGroup
from ccpnmr.chemBuild.model.Bond import Bond


PeptideLinking = 'Peptide-Linking'
DNALinking = 'DNA-Linking'
RNALinking = 'RNA-Linking'
Carbohydrate = 'Carbohydrate'
NonPolymer = 'Non-Polymer'
Unclassified = 'Unclassified'
PROTEIN = 'protein'
DNA = 'DNA'
RNA = 'RNA'

MOLTYPEMAP = { #cif:chembuild
                        PeptideLinking:PROTEIN,
                        DNALinking:DNA,
                        RNALinking:RNA,
                        Carbohydrate:Carbohydrate.lower(),
                        }


def _setBaseCompoundInfo(compound, baseVariant):

    header = baseVariant.header
    if header is None:
        return

    _id = header.get('_chem_comp.id').values[0]
    compound.name = header.get('_chem_comp.name').values[0]
    molType = header.get('_chem_comp.type').values[0]
    one_letter_code = header.get('_chem_comp.one_letter_code').values[0]
    three_letter_code = header.get('_chem_comp.three_letter_code').values[0]
    compound.ccpCode = _id
    compound.one_letter_code = one_letter_code
    compound.three_letter_code = three_letter_code
    for cifMolType, ccpnMolType in MOLTYPEMAP.items():
        if cifMolType in molType:
            compound.ccpMolType = ccpnMolType
    # we could add extra info from the parser

def _setVarianInfo(variant, cifVariant):

    header = cifVariant.header
    if header is None:
        return

    _id = header.get('_chem_comp.id').values[0]
    _name = header.get('_chem_comp.name').values[0]
    molType = header.get('_chem_comp.type').values[0]
    one_letter_code = header.get('_chem_comp.one_letter_code').values[0]
    three_letter_code = header.get('_chem_comp.three_letter_code').values[0]
    variant._name = _name.strip('"')
    variant._id = _id
    variant._one_letter_code = one_letter_code
    variant._three_letter_code = three_letter_code
    variant._type = molType

def _addAtomsToCompound(compound, variant, cifVariant, atomMap):
    atom_df = cifVariant.get_atom_dataframe()
    if atom_df is None:
        return
    if atom_df.empty:
        return
    # Process the DataFrame row by row
    varAtomDict = {}
    for _, row in atom_df.iterrows():
        atomName = row.get("_chem_comp_atom.atom_id")
        elem = row.get("_chem_comp_atom.type_symbol")
        x = float(row.get("_chem_comp_atom.model_Cartn_x"))
        y = float(row.get("_chem_comp_atom.model_Cartn_y"))
        z = float(row.get("_chem_comp_atom.model_Cartn_z"))
        charge = int(row.get("_chem_comp_atom.charge", 0))
        chirality = row.get("_chem_comp_atom.pdbx_stereo_config", )
        chirality = chirality if chirality != 'N' else None  # set only if is S/R

        # Create Atom and VarAtom objects
        atomObject = atomMap.get(atomName)
        if not atomObject:
            atomObject = Atom(compound, elem, atomName)
        varAtom = VarAtom(variant, atomObject, coords=(x, y, z), chirality=chirality)
        if charge:
            varAtom.setCharge(charge, autoVar=False)

        varAtomDict[atomName] = varAtom

    return varAtomDict

def _addBondsToCompound(cifVariant, atomDict):

    bond_df = cifVariant.get_bonds_dataframe()
    if bond_df is not None:
        for _, bond_row in bond_df.iterrows():
            atom1_label = bond_row.get("_chem_comp_bond.atom_id_1")
            atom2_label = bond_row.get("_chem_comp_bond.atom_id_2")
            bondType = bond_row.get("_chem_comp_bond.value_order")
            bondTypeMap = {'SING': 'single', 'DOUB': 'double', 'TRIP': 'triple'}
            atomA = atomDict.get(atom1_label)
            atomB = atomDict.get(atom2_label)
            bondType = bondTypeMap.get(bondType, 'single')
            Bond((atomA, atomB), bondType=bondType, autoVar=False)


def importMmCif(fileName):

    cifParser = ChemCompCIFParser(fileName)
    cifParser.process_file()
    # Initialize the Compound and Variant
    compound = Compound(fileName)
    cifMainVariantName = cifParser.get_base_variant_name()
    cifMainVariant = cifParser.variants.get(cifMainVariantName)
    if not cifMainVariant:
        return
    _, variableAtoms = cifParser.get_atom_differences(cifMainVariantName)
    _setBaseCompoundInfo(compound, cifMainVariant)

    # add main Atoms definitions but not the VarAtoms
    atom_df = cifMainVariant.get_atom_dataframe()
    atomMap = {}
    for _, row in atom_df.iterrows():
        atomName = row.get("_chem_comp_atom.atom_id")
        elem = row.get("_chem_comp_atom.type_symbol")
        atomObject = Atom(compound, elem, atomName)
        if atomName in variableAtoms:
            atomObject.isVariable = True
        atomMap[atomName] = atomObject
    for cifVariantName, cifVariantParser in cifParser.variants.items():
        variant = Variant(compound)
        _setVarianInfo(variant, cifVariantParser)
        compound.variants.add(variant)
        atomDict = _addAtomsToCompound(compound, variant, cifVariantParser, atomMap)
        _addBondsToCompound(cifVariantParser, atomDict)
        if cifVariantName == cifMainVariantName:
            compound.defaultVars.add(variant)
    return compound

