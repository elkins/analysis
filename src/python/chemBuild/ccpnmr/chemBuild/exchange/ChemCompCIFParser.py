"""
A basic parser for Chembuild

see all Info abaout categories and loops at
https://mmcif.wwpdb.org/dictionaries/mmcif_ma.dic/Categories/chem_comp.html

Started with  mmcif_ma.dic version 1.4.7
"""

import pandas as pd
import re

class CifVariant:
    """Class to represent a variant with its loops as DataFrames."""
    def __init__(self, name):
        self.name = name
        self.loops = {}
        self.header_data = {}

    def add_loop(self, tag, df):
        """Add a loop (DataFrame) to the variant."""
        self.loops[tag] = df

    def get_dataframe_by_tag(self, tag):
        """Retrieve a DataFrame by tag name."""
        return self.loops.get(tag)

    def get_all_tags(self):
        """Return a list of all tags in the variant."""
        return list(self.loops.keys())

    def add_header(self, tag, data):
        """Store first non-loop data in the header_data dictionary."""
        if tag not in self.header_data:
            self.header_data[tag] = []
        self.header_data[tag].append(data)

    def build_header(self):
        """Build the header DataFrame at the end."""
        # Convert header_data to a DataFrame at once
        if self.header_data:
            self.header = pd.DataFrame(self.header_data)

    def get_atom_dataframe(self):
        return self.loops['_chem_comp_atom.comp_id']

    def get_bonds_dataframe(self):
        return self.loops['_chem_comp_bond.comp_id']

class ChemCompCIFParser:
    """Generic CIF parser that handles multiple variants, both loops and header."""
    def __init__(self, file_path):
        self.file_path = file_path
        self.variants = {}

    def process_file(self):
        """Main method to parse the CIF file and extract loops and header."""
        with open(self.file_path, 'r') as file:
            lines = file.readlines()

        current_headers = []
        current_data = []
        in_loop = False
        current_variant = None

        for line in lines:
            line = line.strip()
            # Detect a new variant block
            if line.startswith("data_"):
                # A new variant starts, so save the current loop (if any) and reset for the new variant
                if in_loop and current_headers:
                    self._append_loop(current_variant, current_headers, current_data)
                in_loop = False  # Reset loop flag after handling the previous loop
                variant_name = line.split("_", 1)[1]
                if variant_name not in self.variants:
                    self.variants[variant_name] = CifVariant(variant_name)
                current_variant = self.variants[variant_name]

            elif line.startswith("loop_"):
                # If we're inside a loop, process the current data and reset for the new loop
                if in_loop and current_headers:
                    self._append_loop(current_variant, current_headers, current_data)
                # Start a new loop
                in_loop = True
                current_headers = []
                current_data = []

            elif line.startswith("_"):
                # Collect headers (only inside loops)
                if in_loop:
                    current_headers.append(line)
                else:
                    # Handle non-loop data (it's not part of a loop)
                    if current_variant:
                        tag = line.split()[0]  # Use the first word as the tag
                        data = " ".join(line.split()[1:])  # Rest is the associated data
                        current_variant.add_header(tag, data)

            elif in_loop and current_headers:
                # Collect data rows inside loops
                row = line.split()
                if len(row) == len(current_headers):
                    current_data.append(row)
                else:
                    # Handle rows with missing or extra values (either skip or fill with None)
                    if line.startswith("#"):  # Handle comment lines if needed
                        row = [None] * len(current_headers)
                        current_data.append(row)
                    else:
                        # If the row length is not correct, you could choose to skip it or handle differently
                        current_data.append([None] * len(current_headers))

        # Process the final loop if still active
        if in_loop and current_headers:
            self._append_loop(current_variant, current_headers, current_data)

        # Build the header DataFrame for each variant at the end
        for variant in self.variants.values():
            variant.build_header()

    def _append_loop(self, variant, headers, data):
        """Convert collected headers and data into a DataFrame and add it to the variant."""
        if data:
            try:
                df = pd.DataFrame(data, columns=headers)
                df = df.dropna(how='all')  # Drop rows that are all NaN
                tag = headers[0]  # Use the first header as the tag
                variant.add_loop(tag, df)
            except ValueError as e:
                print(f"Error creating DataFrame for loop with headers: {headers}")
                print(f"Data: {data}")
                raise e

    def get_variant(self, variant_name):
        """Retrieve a CifVariant object by name."""
        return self.variants.get(variant_name)

    def get_all_variant_names(self):
        """Return a list of all variant names in the CIF file."""
        return list(self.variants.keys())

    def get_atom_differences(self, base_variant_name):
        """
        Compare all variants to the base variant and return the differences.

        :param base_variant_name: Name of the base variant to compare other variants with.
        :return: A dictionary with variant names as keys and added/removed atoms as values.
        """
        base_variant = self.variants.get(base_variant_name)
        if not base_variant:
            raise ValueError(f"Base variant '{base_variant_name}' not found.")

        # Get the set of atoms in the base variant
        base_atoms = set(base_variant.get_atom_dataframe()['_chem_comp_atom.atom_id'])

        differences = {}
        allVariableAtoms = set()

        for variant_name, variant in self.variants.items():
            if variant_name == base_variant_name:
                continue  # Skip the base variant

            # Get the set of atoms in the current variant
            variant_atoms = set(variant.get_atom_dataframe()['_chem_comp_atom.atom_id'])

            # Determine added and removed atoms
            added_atoms = list(variant_atoms - base_atoms)
            removed_atoms = list(base_atoms - variant_atoms)

            differences[variant_name] = {
                'added_atoms'  : added_atoms,
                'removed_atoms': removed_atoms
                }
            changed = added_atoms + removed_atoms
            for change in changed:
                allVariableAtoms.add(change)

        return differences, list(allVariableAtoms)

    def get_base_variant_name(self):
        """
        Determine the base variant by first checking for a variant name that ends with 'FREE NEUTRAL'
        and has no extra text after it. If no such variant is found, fall back to determining the base
        by checking for a neutral charge and the most atoms.

        :return: The name of the base variant.
        """
        # First, check for the variant name that ends with "FREE NEUTRAL" without any extra text
        for variant_name in self.variants.keys():
            header = self.variants[variant_name].header
            chem_comp_name = header.get('_chem_comp.name').values[0]
            chem_comp_name = chem_comp_name.strip('"')
            if chem_comp_name.strip().upper().endswith("FREE NEUTRAL") and not re.search(r'[^\w\s\-]', chem_comp_name.strip().upper().replace("FREE NEUTRAL", "").strip()):
                return variant_name

        # If no "FREE NEUTRAL" variant is found, determine the base variant by neutral charge and atom count
        base_variant = None
        max_atoms_count = 0

        for variant_name, variant in self.variants.items():
            # Get the atom dataframe for the current variant
            atom_df = variant.get_atom_dataframe()

            # Count the number of atoms in the current variant
            atom_count = atom_df.shape[0]

            # Check if the variant has all atoms with a charge of 0 (neutral)
            neutral_atoms = atom_df[atom_df['_chem_comp_atom.charge'] == '0']

            # If the variant is neutral and has more atoms than the previous base variant, update the base
            if len(neutral_atoms) == atom_count and atom_count > max_atoms_count:
                base_variant = variant_name
                max_atoms_count = atom_count

        if not base_variant:
            raise ValueError("No base variant found with neutral charge and the most atoms.")

        return base_variant


if __name__ == '__main__':
    # Example usage
    file_path = '/Users/luca/Documents/NMR-Data/CIF/AA_variants_singles/GLY.cif'
    parser = ChemCompCIFParser(file_path)
    parser.process_file()

    # Get all variant names
    variant_names = parser.get_all_variant_names()
    print("Variants found:", variant_names)

    # Get a specific variant
    variant = parser.get_variant('ALA')
    if variant:
        print("\nCifVariant ALA loops and header:")
        for tag, df in variant.loops.items():
            print(f"\nLoop Tag: {tag}")
            print(df)
        for tag, frame in variant.header.items():
            print(f"\nFrame Tag: {tag}")
            print(frame)

    # Get a DataFrame or frame by tag for a specific variant
    if variant:
        df_atoms = variant.get_dataframe_by_tag("_chem_comp_atom.atom_id")
        if df_atoms is not None:
            print("\nDataFrame for '_chem_comp_atom.atom_id':")
            print(df_atoms)

