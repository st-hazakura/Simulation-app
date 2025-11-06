import os
def modify_boxin(config, template_path, output_path, decimals_map=None):
    with open(f"src/config/{template_path}", "r") as f:
        lines = f.readlines()

    with open(output_path, "w") as f:
        for line in lines:
            replaced = False
            for key in config:
                if line.strip().startswith("variable"):
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == key:
                        if decimals_map and key in decimals_map:
                            value_str = f"{config[key]:.{decimals_map[key]}f}"
                        else:
                            value_str = str(config[key])
                        f.write(f"variable {key} equal {value_str}\n")
                        replaced = True
                        break
            if not replaced:
                f.write(line)


    submit_template_path = "src/scripts/run_template.sh"
    with open(submit_template_path, "r") as f:
        template = f.read()

    submit_filled = template.format(
        node=config["nodes"],
        ppn=config["ppn"],
        queue=config["queue"],
        simulation_name=config["simulation_name"],
        lammps_exe=config["lammps_exe"]
    )

    submit_path = os.path.join(os.path.dirname(output_path), "run.sh")
    with open(submit_path, "w", newline="\n") as f:
        f.write(submit_filled)
