import os
def check_density(config, data, output_dir):
    target_fluid = config["rho_fluid"]
    actual_fluid = data["n_fluid"] / data["fluid_volume"]

    target_wall = config["rho_wall"]
    actual_wall = data["n_wall"] / data["wall_volume"]

    with open(os.path.join(output_dir, "density_check.txt"), "w", encoding="utf-8") as f:
        f.write(f"Zadana hustota tekutiny: {target_fluid}\n")
        f.write(f"Skutecna hustota tekutiny: {actual_fluid:.4f}\n")
        f.write(f"Zadana hustota steny: {target_wall}\n")
        f.write(f"Skutecna hustota steny: {actual_wall:.4f}\n")
