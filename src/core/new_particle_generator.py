import numpy as np
import os

def generate_particles(config):

    # как было: всегда пишем tail-колонки (ориентация/diameter/density/image)
    sim_name = config["simulation_name"]  # уже есть
    prefix = sim_name.split("_", 1)[0].strip().upper()

    # активная система, если префикс ABP (можешь расширить список при желании)
    write_abp_cols = prefix.startswith("ABP")

    # 1) Входные параметры (те же ключи)
    Lx = float(config["Lx"])
    Ly = float(config["Ly"])
    rho_wall = float(config["rho_wall"])
    rho_fluid = float(config["rho_fluid"])

    # sigma для зазора от стен к жидкости — используем sig12 (как ты хочешь)
    sigma12 = float(config["sig12"])

    # rcut: лучше брать rcut для взаимодействия wall-fluid, если он есть.
    # НО чтобы ничего не ломать, оставляем совместимость с твоим config:
    # приоритет: rcutLJ12 -> rcutLJ11 -> rcut
    if "rcutLJ12" in config:
        rcut = float(config["rcutLJ12"])
    elif "rcutLJ11" in config:
        rcut = float(config["rcutLJ11"])
    elif "rcut" in config:
        rcut = float(config["rcut"])
    else:
        # если вообще нет — лучше явно упасть, чем тихо сделать неправильно
        raise KeyError("Missing rcut key: expected rcutLJ12 or rcutLJ11 or rcut in config")

    sim_name = config["simulation_name"]
    output_dir = os.path.join(".", sim_name)
    os.makedirs(output_dir, exist_ok=True)

    data_file = os.path.join(output_dir, config["data_file"])

    # H = ширина области жидкости, по которой должна считаться плотность
    fluid_gap = float(config["fluid_gap"])

    # 2) Сначала генерируем одну стену.
    # Стена: 4 слоя по z, шаг и толщина выводятся из rho_wall для SC-решётки.
    Nz_wall = 4
    a_wall = (1.0 / rho_wall) ** (1.0 / 3.0)     # шаг решётки стены (SC)
    wall_thickness = Nz_wall * a_wall            # толщина стены = 4 слоя * шаг
    a_z = wall_thickness / Nz_wall               # == a_wall

    # Шаг по (x,y) для стены — в твоём старом коде через a_xy_approx и //.
    # Здесь a_xy_approx совпадает с a_wall (для 4 слоёв), но оставляем логику.
    a_xy_approx = np.sqrt(4.0 / (rho_wall * wall_thickness))
    Nx_wall = int(Lx // a_xy_approx)
    Ny_wall = int(Ly // a_xy_approx)

    if Nx_wall < 1 or Ny_wall < 1:
        print("Rozměry Lx, Ly vs. hustota stěn => Nx_wall nebo Ny_wall vyšlo 0! Generování zrušeno.")
        return

    # реальная разметка по X (как у тебя)
    a_xy = Lx / Nx_wall

    # 3) Проверка условия (как ты писала): wall_thickness + sigma12 должно быть > rcut
    # (rcut берём как rcut wall-fluid если он есть)
    if (sigma12 + wall_thickness) <= rcut:
        print("Podmínka sigma12 + wall_thickness > rcut NENÍ splněna. Generování se ruší.")
        return

    # 4) Теперь генерируем жидкость внутри области H (fluid_gap),
    # но с зазорами sigma12 от обеих стен.
    # То есть: [0 .. wall] [sigma12] [fluid_gap] [sigma12] [wall]
    # => вычисляем Lz (и только теперь!)
    Lz = 2.0 * wall_thickness + 2.0 * sigma12 + fluid_gap

    # обновим config, чтобы дальше box.in мог взять правильный Lz
    config["Lz"] = Lz

    # Шаг решётки жидкости из rho_fluid (как у тебя было)
    a_fluid = (1.0 / rho_fluid) ** (1.0 / 3.0)

    # Сколько слоёв реально влезет в H при шаге a_fluid (как у тебя через //)
    Nx_fluid = int(Lx // a_fluid)
    Ny_fluid = int(Ly // a_fluid)
    Nz_fluid = int(fluid_gap // a_fluid)
    print(f"Tek nz:{Nz_fluid}")

    # 5) Числа частиц и реальные плотности (те же смыслы, что у тебя)
    # Стены:
    N_wall_single = Nx_wall * Ny_wall * Nz_wall
    N_wall = 2 * N_wall_single
    V_wall = 2 * (Lx * Ly * wall_thickness)
    rho_wall_actual = N_wall / V_wall

    # Жидкость (считает по H=fluid_gap, как ты хочешь)
    N_fluid = Nx_fluid * Ny_fluid * Nz_fluid
    V_fluid = fluid_gap * Lx * Ly
    rho_fluid_actual = N_fluid / V_fluid

    # 6) Пишем .slit (формат тот же, tail тот же)
    with open(data_file, "w") as f:
        f.write("LAMMPS Description\n\n")
        # временно, как у тебя — потом поправим точным числом
        f.write(f"{N_wall + N_fluid} atoms\n")
        f.write("2 atom types\n\n")
        f.write(f"0.0 {Lx} xlo xhi\n")
        f.write(f"0.0 {Ly} ylo yhi\n")
        f.write(f"0.0 {Lz} zlo zhi\n\n")
        f.write("Masses\n\n1 1.0\n2 1.0\n\n")
        f.write("Atoms\n\n")

        atom_id = 1
        q = 0.0
        diametr = 1.0
        density = 1.0
        ix = iy = iz = 0  # image_flags

        # --- ЖИДКОСТЬ ---
        # Область жидкости по z: от (wall_thickness + sigma12) до (wall_thickness + sigma12 + fluid_gap)
        z_fluid_min = wall_thickness + sigma12
        # генерируем центры ячеек с 0.5*a_fluid, как у тебя
        z_start = z_fluid_min + 0.5 * a_fluid
        z_end = z_start + Nz_fluid * a_fluid

        # x,y как у тебя: от 0.5*a_fluid до Lx/Ly с шагом a_fluid
        x_vals = np.arange(0.5 * a_fluid, Lx, a_fluid)
        y_vals = np.arange(0.5 * a_fluid, Ly, a_fluid)

        tek_count_start = atom_id
        for z in np.arange(z_start, z_end, a_fluid):
            for y in y_vals:
                for x in x_vals:
                    v = np.random.normal(size=3)
                    norm = np.linalg.norm(v)
                    if norm == 0:
                        v_x, v_y, v_z = 1.0, 0.0, 0.0
                    else:
                        v_x, v_y, v_z = v / norm

                    if write_abp_cols:
                        tail = f"{q} {v_x} {v_y} {v_z} {diametr} {density} {ix} {iy} {iz}"
                        f.write(f"{atom_id} 1 {x:.3f} {y:.3f} {z:.3f} {tail}\n")
                    else:
                        f.write(f"{atom_id} 1 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        tek_pocet = atom_id - 1

        # --- СТЕНА НИЖНЯЯ ---
        z_bottom_start = 0.5 * a_z
        z_bottom_end = z_bottom_start + Nz_wall * a_z
        for z in np.arange(z_bottom_start, z_bottom_end, a_z):
            for y in np.arange(0.5 * a_xy, Ly, a_xy):
                for x in np.arange(0.5 * a_xy, Lx, a_xy):
                    v_x = v_y = v_z = 0.0
                    if write_abp_cols:
                        tail = f"{q} {v_x} {v_y} {v_z} {diametr} {density} {ix} {iy} {iz}"
                        f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f} {tail}\n")
                    else:
                        f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        stena_1_pocet = atom_id - 1 - tek_pocet

        # --- СТЕНА ВЕРХНЯЯ ---
        # стена начинается в z = Lz - wall_thickness
        z_top_start = (Lz - wall_thickness) + 0.5 * a_z
        z_top_end = z_top_start + Nz_wall * a_z
        for z in np.arange(z_top_start, z_top_end, a_z):
            for y in np.arange(0.5 * a_xy, Ly, a_xy):
                for x in np.arange(0.5 * a_xy, Lx, a_xy):
                    v_x = v_y = v_z = 0.0
                    if write_abp_cols:
                        tail = f"{q} {v_x} {v_y} {v_z} {diametr} {density} {ix} {iy} {iz}"
                        f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f} {tail}\n")
                    else:
                        f.write(f"{atom_id} 2 {x:.3f} {y:.3f} {z:.3f}\n")
                    atom_id += 1
        stena_2_pocet = atom_id - 1 - tek_pocet - stena_1_pocet

    # фактически записанное число жидкости (если Lx/Ly не кратны шагу)
    N_fluid_written = (tek_pocet - (tek_count_start - 1))
    N_wall_written = stena_1_pocet + stena_2_pocet

    # пересчёт плотности жидкости по H (как в твоём TODO-блоке)
    N_fluid = N_fluid_written
    V_fluid = fluid_gap * Lx * Ly
    rho_fluid_actual = N_fluid / V_fluid

    # поправим atoms в шапке (как ты делала)
    with open(data_file, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        lines[2] = f"{N_fluid + N_wall_written} atoms\n"
        f.seek(0)
        f.writelines(lines)

    print(f"N-tek: {tek_pocet}, stena_1: {stena_1_pocet}, stena_2: {stena_2_pocet}, N_wall: {N_wall_written}")
    print(f"Computed Lz: {Lz}")

    # Возвращаем те же ключи, что в старой версии
    return {
        "n_wall": N_wall_written,
        "n_fluid": N_fluid,
        "rho_wall_actual": rho_wall_actual,
        "rho_fluid_actual": rho_fluid_actual,
        "fluid_volume": V_fluid,
        "wall_volume": V_wall,
        "output_dir": output_dir
    }