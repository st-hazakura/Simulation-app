import numpy as np
import os
def generate_particles(config):
    # 1) Vstupní parametry z configu
    Lx = config["Lx"]
    Ly = config["Ly"]
    Lz = config["Lz"]
    rho_wall = config["rho_wall"]
    rho_fluid = config["rho_fluid"]
    sigma = config["sig12"]
    rcut = config["rcutLJ11"]   # Třeba pro interakci 1-1

    sim_name = config["simulation_name"] # nova slozka
    output_dir = os.path.join(".", sim_name)
    os.makedirs(output_dir, exist_ok=True)

    data_file = os.path.join(output_dir, config["data_file"]) # soubor s polohami .slit
    

    # Uživatel zadává fluid_gap = šířka tekutiny
    fluid_gap = config["fluid_gap"]

    # 2) Tloušťka každé stěny (dole i nahoře)
    wall_thickness = (Lz - fluid_gap - 2*sigma) / 2.0

    # Kontrola, zda stěna není příliš tenká
    if (sigma + wall_thickness) <= rcut:
        print("Podmínka sigma + wall_thickness > rcut NENÍ splněna. Generování se ruší.")
        return

    # 3) STĚNY: chceme 4 vrstvy ve směru Z
    Nz_wall = 4
    a_z = wall_thickness / Nz_wall  # krok ve směru Z
    
    # 4) Odvození kroku v (x,y) pro stěnu z hustoty (přibližný vzorec, který počítá s 4 vrstvami v ose Z)
    #    rho_wall ~ (2 * Nx * Ny * Nz_wall) / (2 * Lx * Ly * wall_thickness) =>  rho_wall ~ (Nx*Ny*4) / (Lx*Ly*wall_thickness)
    #    =>  a_xy ~ sqrt(4/(rho_wall * wall_thickness))  (bez ohledu na zaokrouhlení)            
    a_xy_approx = np.sqrt(4.0 / (rho_wall * wall_thickness))

    # 5) Zjistíme počet částic v (x,y)
    Nx_wall = int(Lx // a_xy_approx)
    Ny_wall = int(Ly // a_xy_approx)

    # Pokud by Nx_wall=0, tak to znamená, že a_xy_approx > Lx => hustota nebude splněna. Kdyby se stalo, že Nx_wall < 1, radši to "zařízneme":
    if Nx_wall < 1 or Ny_wall < 1:
        print("Rozměry Lx, Ly vs. hustota stěn => Nx_wall nebo Ny_wall vyšlo 0! Generování zrušeno.")
        return

    # 6) Skutečná rozteč v (x,y) (použijeme celou šířku / Nx_wall)
    a_xy = Lx / Nx_wall
    # Pro Ly můžeme udělat totéž, anebo akceptovat lehce odlišný krok. Zde pro zjednodušení budeme předpokládat Lx=Ly ~ 100 => a_xy ok.
    # Kdybychom chtěli "čtvercovou" buňku i pro Ly, můžeme: a_y = Ly / Ny_wall
    # a tady by se mohlo lišit. Zde budeme generovat s a_xy i v ose Y, jen to nebude dokonale vyplněné.

    # 7) TEKUTINA  Krok z hustoty: a_fluid
    a_fluid = (1.0 / rho_fluid) ** (1.0/3.0)
    Nx_fluid = int(Lx // a_fluid)
    Ny_fluid = int(Ly // a_fluid)
    Nz_fluid = int(fluid_gap // a_fluid)
    print(f"Tek nz:{Nz_fluid}")

    # 8) Spočítej skutečné počty částic a objemy
    N_wall_single = Nx_wall * Ny_wall * Nz_wall
    N_wall = 2 * N_wall_single  # 2 stěny
    V_wall = 2 * (Lx * Ly * wall_thickness)
    rho_wall_actual = N_wall / V_wall

    N_fluid = Nx_fluid * Ny_fluid * Nz_fluid
    V_fluid = fluid_gap * Lx * Ly
    rho_fluid_actual = N_fluid / V_fluid

    # # 9) Zkontroluj odchylku hustoty (třeba ±1%)
    # wall_diff = abs(rho_wall_actual - rho_wall)/rho_wall
    # fluid_diff = abs(rho_fluid_actual - rho_fluid)/rho_fluid
    # if wall_diff > 0.01:
    #     print(f"UPOZORNĚNÍ: Hustota stěny se liší o více než ±1%: {rho_wall_actual:.4f} vs {rho_wall}")
    # if fluid_diff > 0.01:
    #     print(f"UPOZORNĚNÍ: Hustota tekutiny se liší o více než ±1%: {rho_fluid_actual:.4f} vs {rho_fluid}")


    with open(data_file, "w") as f:
        f.write("LAMMPS Description\n\n")
        f.write(f"{N_wall + N_fluid} atoms\n")
        f.write("2 atom types\n\n")
        f.write(f"0.0 {Lx} xlo xhi\n")
        f.write(f"0.0 {Ly} ylo yhi\n")
        f.write(f"0.0 {Lz} zlo zhi\n\n")
        f.write("Masses\n\n1 1.0\n2 1.0\n\n")
        f.write("Atoms\n\n")

        atom_id = 1

        # Generování TEKUTINY. Z-rozsah: wall_thickness až (wall_thickness + fluid_gap), s offsetem 0.5*a_fluid
        # z_fluid_start = wall_thickness + 0.5 * a_fluid
        # z_fluid_end   = z_fluid_start + Nz_fluid * a_fluid
        # for z in np.arange(z_fluid_start, z_fluid_end, a_fluid):
        #     for y in np.arange(0.5*a_fluid, Ly, a_fluid):
        #         for x in np.arange(0.5*a_fluid, Lx, a_fluid):
        #             f.write(f"{atom_id} 1 {x:.3f} {y:.3f} {z:.3f}\n")
        #             atom_id += 1
        z_fluid_start = Lz/2 - fluid_gap/2 + 0.5 * a_fluid
        z_fluid_end   = z_fluid_start + Nz_fluid * a_fluid
        Nz_fluid_new = 0
        for z in np.arange(z_fluid_start, z_fluid_end, a_fluid):
            Nz_fluid_new += 1
            for y in np.arange(0.5*a_fluid, Ly, a_fluid):
                for x in np.arange(0.5*a_fluid, Lx, a_fluid):
                    f.write(f"{atom_id} 1 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        tek_pocet = atom_id-1
        
        
        # Generování STĚNY (dole): z in [0, wall_thickness] 4 vrstvy => krok a_z, offset 0.5*a_z
        z_bottom_start = 0.5 * a_z
        z_bottom_end   = z_bottom_start + Nz_wall * a_z
        for z in np.arange(z_bottom_start, z_bottom_end, a_z):
            for y in np.arange(0.5*a_xy, Ly, a_xy):
                for x in np.arange(0.5*a_xy, Lx, a_xy):
                    f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        stena_1_pocet = atom_id-1 - tek_pocet
        
        
        # Generování STĚNY (nahoře): z in [Lz - wall_thickness, Lz]
        z_top_start = (Lz - wall_thickness) - 0.5 * a_z
        z_top_end   = z_top_start + Nz_wall * a_z
        # for z in np.arange(z_top_start, z_top_end, a_z):
        for k in range(Nz_wall):
            z = z_top_start + (k + 0.5) * a_z
            for y in np.arange(0.5*a_xy, Ly, a_xy):
                for x in np.arange(0.5*a_xy, Lx, a_xy):
                    f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        stena_2_pocet = atom_id-1 - tek_pocet - stena_1_pocet
    print(f"N-tek: {tek_pocet}, stena_1: {stena_1_pocet}, stena_2: {stena_2_pocet}, N_wall: {N_wall}")
        


    # TODO 
    N_fluid = Nx_fluid * Ny_fluid * Nz_fluid_new
    V_fluid = fluid_gap * Lx * Ly
    rho_fluid_actual = N_fluid / V_fluid
    
    with open(data_file, "r+") as f:
        lines = f.readlines()
        lines[2] = f"{N_fluid + N_wall} atoms\n"
        f.seek(0)
        f.writelines(lines)
        
    # Vrátíme dictionary s užitečnými daty
    return {
        "n_wall": N_wall,
        "n_fluid": N_fluid,
        "rho_wall_actual": rho_wall_actual,
        "rho_fluid_actual": rho_fluid_actual,
        "fluid_volume": V_fluid,
        "wall_volume": V_wall,
        "output_dir": output_dir
    }

