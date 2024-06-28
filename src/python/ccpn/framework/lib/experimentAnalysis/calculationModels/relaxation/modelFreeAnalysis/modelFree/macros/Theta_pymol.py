from pymol import cmd, cgo
import numpy as np
from Bio import PDB
from Bio.PDB.vectors import Vector
import warnings
# Suppress all warnings
from Bio.PDB.PDBExceptions import PDBConstructionWarning
warnings.simplefilter('ignore', PDBConstructionWarning)

def calculate_nh_vectors(pdb_file):
    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure('protein', pdb_file)

    nh_vectors = []
    residue_ids = []

    for model in structure:
        for chain in model:
            for residue in chain:
                try:
                    n_atom = residue['N']
                    h_atom = residue['H']

                    n_coord = Vector(n_atom.get_coord())
                    h_coord = Vector(h_atom.get_coord())

                    nh_vector = h_coord - n_coord
                    nh_vectors.append(nh_vector)
                    residue_ids.append((chain.id, residue.get_id()[1]))  # (chain ID, residue number)
                except KeyError:
                    continue

    return nh_vectors, residue_ids


def calculate_gyration_tensor(coordinates):
    coords = np.array(coordinates)
    center_of_mass = np.mean(coords, axis=0)
    coords -= center_of_mass

    gyration_tensor = np.dot(coords.T, coords) / len(coords)
    return gyration_tensor


def principal_axis_of_diffusion(gyration_tensor):
    eigvals, eigvecs = np.linalg.eig(gyration_tensor)
    principal_axis = eigvecs[:, np.argmax(eigvals)]
    return Vector(principal_axis)


def calculate_angle(nh_vector, principal_axis):
    nh_vector = nh_vector.normalized()
    principal_axis = principal_axis.normalized()

    cos_theta = np.dot(nh_vector, principal_axis)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)  # Ensure value is in valid range for arccos
    theta = np.arccos(cos_theta)

    return np.degrees(theta)


def visualize_diffusion_axis(pdb_file, coordinates, principal_axis):
    # Load the PDB file in PyMOL
    cmd.load(pdb_file)

    # Calculate N-H vectors and residue IDs
    nh_vectors, residue_ids = calculate_nh_vectors(pdb_file)

    # Calculate angles and draw individual axes
    for nh_vector, (chain_id, residue_num) in zip(nh_vectors, residue_ids):
        theta = calculate_angle(nh_vector, principal_axis)

        # Retrieve residue coordinates for drawing the axis
        n_atom_name = f'/{chain_id}/{residue_num}/N'
        h_atom_name = f'/{chain_id}/{residue_num}/H'
        h_atom_name = '/gb1///ASP`61/N'
        n_atom_name = '/gb1///ASP`61/H'
        n_atom_name = f'/gb1///{residue_num}/N'
        h_atom_name = f'/gb1///{residue_num}/H'
        print(n_atom_name, '=========')

        # h_atom_name = f'/{chain_id}/{residue_num}/H'
        try:
            n_coord = np.array(cmd.get_atom_coords(n_atom_name))
            h_coord =np.array(cmd.get_atom_coords(h_atom_name))
            print(n_coord, 'jhgfds')
            print(h_coord, 'jhgfds')

        except:
            print(f'Error in {residue_num} retrieving H-N atoms')
            continue

        # Draw the NH axis
        nh_vector = (h_coord - n_coord)
        nh_vector = nh_vector / np.linalg.norm(nh_vector) * 5  # Scale for visualization
        nh_axis = [
            cgo.CYLINDER, *n_coord, *(n_coord + nh_vector), 0.05, 1, 1, 1, 1, 1, 1
            ]
        cmd.load_cgo(nh_axis, f'nh_axis_{chain_id}_{residue_num}')
        print('==> ',  f'nh_axis_{chain_id}_{residue_num}')

        # Label the angle theta
        label_position = (n_coord + nh_vector).tolist()
        # cmd.pseudoatom(f'label_{chain_id}_{residue_num}', pos=label_position)
        # cmd.label(f'label_{chain_id}_{residue_num}', f'"{theta:.2f}°"')

    # Draw the principal axis longer in both directions
    center_of_mass = np.mean(coordinates, axis=0)
    principal_axis_normalized = principal_axis.normalized()
    start_point = center_of_mass - principal_axis_normalized.get_array() * 10  # Extend in both directions
    end_point = center_of_mass + principal_axis_normalized.get_array() * 10
    principal_axis_cgo = [
        cgo.CYLINDER, *start_point, *end_point, 0.2, 1, 0, 0, 1, 0, 0,
        cgo.CONE, *end_point, *(end_point + principal_axis_normalized.get_array() * 2), 0.4, 0.0, 1, 0, 0, 1, 0, 0,
        cgo.CONE, *start_point, *(start_point - principal_axis_normalized.get_array() * 2), 0.4, 0.0, 1, 0, 0, 1, 0, 0
        ]
    cmd.load_cgo(principal_axis_cgo, 'principal_axis')

# Example usage
cmd.reinitialize()
pdb_file = gb1 = '/Users/luca/Documents/NMR-Data/Relaxation/Fred_Musket/GB1/FWM_analysis_gb1_relax/gb1.pdb'
nh_vectors, residue_ids = calculate_nh_vectors(pdb_file)
parser = PDB.PDBParser()
structure = parser.get_structure("protein", pdb_file)
coordinates = np.array([atom.get_coord() for atom in structure.get_atoms()])


gyration_tensor = calculate_gyration_tensor(coordinates)
principal_axis = principal_axis_of_diffusion(gyration_tensor)

visualize_diffusion_axis(pdb_file, coordinates, principal_axis)
