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



def importMmCif(fileName):
    # Initialize the CIF parser and process the file
    parser = ChemCompCIFParser(fileName)
    parser.process_file()

    # Initialize the Compound and Variant
    compound = Compound(fileName)
    for variantName, varParser in parser.variants.items():
        print("Variants found:", variantName)
        var = Variant(compound)
        # if variantHeader is not None:
        #     var._id = variantHeader.get('_chem_comp.id').values[0]
        #     var._name = variantHeader.get('_chem_comp.name').values[0]
        #     var._type = variantHeader.get('_chem_comp.type').values[0]
        #     var._one_letter_code = variantHeader.get('_chem_comp.one_letter_code').values[0]
        #     var._three_letter_code = variantHeader.get('_chem_comp.three_letter_code').values[0]


        # compound.defaultVars.add(var)
        compound.variants.add(var)

        atomDict = {}
        bondDict = {}

        # Retrieve atomic coordinates and atom details from the parsed CIF DataFrame
        atom_df = varParser.loops['_chem_comp_atom.comp_id']

        if atom_df is None:
            continue
        if atom_df.empty:
            continue

        # Process the DataFrame row by row
        for _, row in atom_df.iterrows():
            atomName = row.get("_chem_comp_atom.atom_id")
            resName = row.get("_chem_comp_atom.comp_id")

            x = float(row.get("_chem_comp_atom.model_Cartn_x"))
            y = float(row.get("_chem_comp_atom.model_Cartn_y"))
            z = float(row.get("_chem_comp_atom.model_Cartn_z"))

            elem = row.get("_chem_comp_atom.type_symbol")
            charge = int(row.get("_chem_comp_atom.charge", 0))
            chirality = row.get("_chem_comp_atom.pdbx_stereo_config",)
            chirality = chirality if chirality != 'N' else None # set only if is S/R
            # Create Atom and VarAtom objects
            atomObject = Atom(compound, elem, atomName)
            varAtom = VarAtom(var, atomObject, coords=(x, y, z), chirality=chirality)

            # Set charge if available
            if charge:
                varAtom.setCharge(charge, autoVar=False)

            atomDict[atomName] = varAtom
            compound.name = resName

            # try:
        bond_df = varParser.loops['_chem_comp_bond.comp_id']

        if bond_df is not None:
            for _, bond_row in bond_df.iterrows():
                atom1_label = bond_row.get("_chem_comp_bond.atom_id_1")
                atom2_label = bond_row.get("_chem_comp_bond.atom_id_2")
                bondType = bond_row.get("_chem_comp_bond.value_order")
                bondTypeMap = {'SING':'single', 'DOUB':'double','TRIP':'triple'}
                atomA = atomDict.get(atom1_label)
                atomB = atomDict.get(atom2_label)
                bondType = bondTypeMap.get(bondType, 'single')
                Bond((atomA, atomB), bondType=bondType, autoVar=False)
            # except Exception as bondErr:
            #     print(f"Error creating Bond: {bondErr}")

        # Aromatic bonds handling
        try:
            aromatics = set()
            for key in bondDict:
                atomA = atomDict.get(key.pop())
                atomB = atomDict.get(key.pop())

                if bondDict[key] >= 4:  # Simple heuristic for aromatic bonds
                    aromatics.add(atomA)
                    aromatics.add(atomB)

            if aromatics:
                rings = var.getRings(aromatics)
                for ring in rings:
                    AtomGroup(compound, ring, AROMATIC)
        except Exception as aBondErr:
            print(f"Error creating Aromatic Bond: {aBondErr}")
        # Final adjustments and checks
        compound.center((0, 0, 0))
        var.checkBaseValences()

    return compound