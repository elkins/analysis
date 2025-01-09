import pandas as pd
import re

class Variant:
    """Class to represent a variant with its loops as DataFrames."""
    def __init__(self, name):
        self.name = name
        self.loops = {}

    def add_loop(self, tag, df):
        """Add a loop (DataFrame) to the variant."""
        self.loops[tag] = df

    def get_dataframe_by_tag(self, tag):
        """Retrieve a DataFrame by tag name."""
        return self.loops.get(tag)

    def get_all_tags(self):
        """Return a list of all tags in the variant."""
        return list(self.loops.keys())

class ChemCompCIFParser:
    """Generic CIF parser that handles multiple variants."""
    def __init__(self, file_path):
        self.file_path = file_path
        self.variants = {}

    def process_file(self):
        """Main method to parse the CIF file and extract loops into DataFrames."""
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
                variant_name = line.split("_", 1)[1]
                if variant_name not in self.variants:
                    self.variants[variant_name] = Variant(variant_name)
                current_variant = self.variants[variant_name]

            elif line.startswith("loop_"):
                # Process the previous loop
                if in_loop and current_headers:
                    self._append_loop(current_variant, current_headers, current_data)
                # Reset for a new loop
                in_loop = True
                current_headers = []
                current_data = []

            elif line.startswith("_"):
                # Collect headers
                current_headers.append(line)

            elif in_loop and current_headers:
                # Collect data rows
                row = line.split()
                if len(row) == len(current_headers):
                    current_data.append(row)
                else:
                    # Handle rows with missing or extra values
                    if line.startswith("#"):
                        row = [None]*len(current_headers)
                        current_data.append(row)
        # Process the final loop
        if in_loop and current_headers:
            self._append_loop(current_variant, current_headers, current_data)

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
        """Retrieve a Variant object by name."""
        return self.variants.get(variant_name)

    def get_all_variant_names(self):
        """Return a list of all variant names in the CIF file."""
        return list(self.variants.keys())

if __name__ == '__main__':
    # Example usage
    file_path = '/Users/luca/Documents/NMR-Data/CIF/AA_variants_singles/ALA.cif'
    parser = ChemCompCIFParser(file_path)
    parser.process_file()

    # Get all variant names
    variant_names = parser.get_all_variant_names()
    print("Variants found:", variant_names)

    # Get a specific variant
    variant = parser.get_variant('ALA')
    if variant:
        print("\nVariant ALA loops:")
        for tag, df in variant.loops.items():
            print(f"\nTag: {tag}")
            print(df)

    # Get a DataFrame by tag for a specific variant
    if variant:
        df_atoms = variant.get_dataframe_by_tag("_chem_comp_atom.atom_id")
        if df_atoms is not None:
            print("\nDataFrame for '_chem_comp_atom.atom_id':")
            print(df_atoms)