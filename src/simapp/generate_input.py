from path import in_src
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  #  Меняет пути поиска МОДУЛЕЙ .../src
from core.config_loader import load_config
from core.particle_generator import generate_particles
from core.boxin_modifier import modify_boxin
from core.density_check import check_density
import shutil
import os
import yaml

def main():
    config = load_config(in_src("config", "params.yaml")) #or str(CONFIG/"params.yaml")
    sim_name = config["simulation_name"]
    output_dir = os.path.join(".", sim_name)
    os.makedirs(output_dir, exist_ok=True) # dovoluju prepis jiz existujici slozky
    
    # 1
    positions = generate_particles(config)
    
    # 2
    check_density(config, positions, output_dir)
    
    # 3
    template = config["box_template"]
    output_boxin = os.path.join(output_dir, config["box_output"])
    # Načtení desetinných míst
    with open(in_src("config", "decimals.yaml")) as f:
        decimals_map = yaml.safe_load(f)
        
    modify_boxin(config, template, output_boxin, decimals_map)

    
    # 4
    shutil.copy(in_src("scripts", "submit_job.sh"), output_dir)
    

    # 5. Vypis nazvu slozky simulace (pro .bat soubor)
    print(sim_name)

if __name__ == "__main__":
    main()