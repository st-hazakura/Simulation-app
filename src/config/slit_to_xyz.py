data_path = 'dataWCA.slit'
with open(data_path, 'r') as file:
    lines = file.readlines()

# Parse the file to extract relevant information
header_end_index = lines.index("Atoms\n") + 2  # The section starts after "Atoms\n"
header = lines[:header_end_index]
atoms = lines[header_end_index:]

atoms_type_1 = []
atoms_type_2 = []

for line in atoms:
    parts = line.split()
    atom_type = parts[1]  # Atom type is the second column
    if atom_type == '1':
        atoms_type_1.append(line)
    elif atom_type == '2':
        atoms_type_2.append(line)


def convert_to_xyz(atoms, argon_radius=1.88, lj_radius=3.4):
    """Convert atom data to XYZ format with adjusted sizes."""
    num_atoms = len(atoms)
    xyz_lines = [f"{num_atoms}\n", "Converted from LAMMPS file with adjusted sizes\n"]
    for line in atoms:
        parts = line.split()
        atom_type = parts[1]  # Atom type
        x, y, z = parts[2:5]  # Coordinates
        if atom_type == '1':
            size_adjusted = argon_radius  # Argon radius in Angstroms
        elif atom_type == '2':
            size_adjusted = lj_radius  # Lennard-Jones fluid radius in Angstroms
        xyz_lines.append(f"{atom_type} {x} {y} {z} {size_adjusted:.3f}\n")
    return xyz_lines


xyz_type_1 = convert_to_xyz(atoms_type_1)
xyz_type_2 = convert_to_xyz(atoms_type_2)


output_path_xyz_type_1 = 'molekule_type_1.xyz'
output_path_xyz_type_2 = 'molekule_type_2.xyz'

with open(output_path_xyz_type_1, 'w') as file:
    file.writelines(xyz_type_1)

with open(output_path_xyz_type_2, 'w') as file:
    file.writelines(xyz_type_2)

print("Files created:")
print(f"Type 1: {output_path_xyz_type_1}")
print(f"Type 2: {output_path_xyz_type_2}")
