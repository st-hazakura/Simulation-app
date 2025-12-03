from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPixmap
from dotenv import load_dotenv
import yaml
import requests
from bs4 import BeautifulSoup
import subprocess
import os
import shutil
import sys

from path import UI, CONFIG, SCRIPTS, ENV_FILE, in_root
from pathlib import Path

from pbs_parser import (parse_node_load_from_nodes,parse_node_load_from_jobs,)
import cluster_service
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui_path = UI / "simulace_app.ui"
        self.styles_path = UI / "style.css"
        self.param_path = CONFIG / "params.yaml"        
        self.decimal_path = CONFIG / "decimals.yaml"
        self.runall_path = SCRIPTS / "run_all.bat"
        
        load_dotenv(dotenv_path=ENV_FILE)
        self.user_name = os.getenv("CLUSTER_USERNAME")              
        self.host = os.getenv("CLUSTER_HOST")
        self.key_path = os.getenv("CLUSTER_KEY_PATH")
        self.results_dir = os.getenv("LOCAL_RESULTS_DIR")
        self.loc_sim_path = os.getenv("LOCAL_NOTEBOOK_PATH")  
        self.lmp_path = os.getenv("LAMMPS_PATH") 
        self.cluster_sim_path = os.getenv("CLUSTER_SIMULATION_DIR")
        
                      
        uic.loadUi(self.ui_path, self)
        
        with open(self.styles_path, "r") as file:
            self.setStyleSheet(file.read())  

        with open(self.param_path) as f:
            self.config = yaml.safe_load(f)


        self.node_to_queue = {
            "node01": "enp5", "node02": "enp5", "node03": "enp5",
            "node04": "enp5", "node05": "enp5", "node06": "enp5",
            "node36": "enp5", "node37": "enp5",
            "node26": "enp3", "node27": "enp3", "node28": "enp3",
            "node29": "enp3", "node30": "enp3", "node31": "enp3",
            "node32": "enp3", "node33": "enp3", "node34": "enp3"
        }
        self.queue_to_max_walltime = {"enp5": "20 dnů", "enp3": "3 dny"}

        self.nodes.addItems(self.node_to_queue.keys())
        self.nodes.currentTextChanged.connect(self.update_info)
        self.saveButton.clicked.connect(self.save_yaml)
        self.checkJobsButton.clicked.connect(self.show_job_status)
        self.update_folders.clicked.connect(self.update_simComboBox)
        self.copyAndRunButton.clicked.connect(self.copy_and_run_local_analysis)
        self.runSimButton.clicked.connect(self.run_simulation_locally)
        self.button_copy_dens_file_localy.clicked.connect(self.copy_only_dens_files)

        self.load_yaml()
        self.simulation_name.setText("WCA")
        
    def run_simulation_locally(self):
        """Сохраняем параметры симуляции, локально открываем папку для симуляций, на основе параметров генерируем входные файлы и запускаем симуляцию
        """
        self.update_yaml()
        sim_name = self.config["simulation_name"]

        Path(self.loc_sim_path).mkdir(parents=True, exist_ok=True)
        
        local_sim_path = Path(self.loc_sim_path) / sim_name
        gen_file = Path(__file__).resolve().parent / "generate_input.py"  # src/simapp/...
        
        # subprocess обычно отсылается в корень проекта то есть simulation_app 
        subprocess.run([sys.executable, str(gen_file)], check=True)   # # ex... Python из venv

        build_path = in_root(sim_name)
        shutil.move(str(build_path), str(local_sim_path))

        subprocess.Popen(
            ["cmd", "/K", "cd", "/d", str(local_sim_path), "&&", self.lmp_path, "-in", "box.in"]
        )

    
    def update_yaml(self):
        """Update yaml file with parametrs from widgets in Qt and save decimals from widgets"""
        for key in self.config:
            widget = self.findChild(QtWidgets.QWidget, key)
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                self.config[key] = widget.value()
            elif isinstance(widget, QtWidgets.QLineEdit):
                self.config[key] = widget.text()
            elif isinstance(widget, QtWidgets.QSpinBox):
                self.config[key] = widget.value()
        user_text = self.simulation_name.text()
        fluid_gap = int(self.fluid_gap.value())
        rho_fluid = str(self.rho_fluid.value())
        rho_fluid = int(rho_fluid.split('.')[1])
        self.config["simulation_name"] = f"{user_text}_H{fluid_gap}_rho0_{rho_fluid}"
        self.config["Lz"] = fluid_gap+14


        with open(self.param_path, "w") as f:
            yaml.dump(self.config, f)
            
        # Ulož mapu počtu desetinných míst
        decimals_map = self.get_decimals_map()
        with open(self.decimal_path, "w") as f:
            yaml.dump(decimals_map, f)

    def load_yaml(self):
        """Set value widgets from yaml file"""
        for key in self.config:
            widget = self.findChild(QtWidgets.QWidget, key)
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                widget.setValue(float(self.config[key]))
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(str(self.config[key]))
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.setValue(int(self.config[key]))


        node = self.config.get("nodes", "node01")
        index = self.nodes.findText(node)
        if index >= 0:
            self.nodes.setCurrentIndex(index)


    def save_yaml(self):
        """Update yaml file with parametrs from widgets and start simulation on cluster """
        answer = self.confirm_save()
        if answer == QtWidgets.QMessageBox.Yes:
            self.update_yaml()
            
            try:
                subprocess.run([self.runall_path], check=True)
            except subprocess.CalledProcessError as e:
                QtWidgets.QMessageBox.critical(self, "Chyba", f"Běh .bat selhal:\n{e}")

    
    def confirm_save(self, title="Confirm", text="Mas vse hotovo?"):
        window_confirm = QtWidgets.QMessageBox(self)
        window_confirm.setWindowTitle(title)
        window_confirm.setText(text)
  
        # pixmap = QPixmap("Icons\\thinking_cat.png")  
        # scale_pixmap = pixmap.scaled(90,90)
        # window_confirm.setIconPixmap(scale_pixmap)
        window_confirm.setStandardButtons( QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        answer = window_confirm.exec_()
        return answer

    def update_info(self):
        """Update info dropdown about cluster nodes"""
        node = self.nodes.currentText()
        queue = self.node_to_queue.get(node, "neznámá fronta")
        self.queue.setText(queue)
        self.config["nodes"] = node
        self.config["queue"] = queue

        usage = self.get_node_load(node)
        self.loadLabel.setText(usage)

        max_time = self.queue_to_max_walltime.get(queue)
        if max_time:
            self.maxTimeLabel.setText(max_time)
        else:
            self.maxTimeLabel.setText("neznámý limit")
        
    def get_node_load(self, node):
        """Zkusí zjistit zatížení nejdřív ze staré tabulky (nody v 1. sloupci), pokud ji nenajde, přepne se na nový formát tabulky jobs."""
        try:
            nodes_url = "https://pbsweb.enputron.ujep.cz/statuspbs/nodes"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
            }
            r_nodes = requests.get(nodes_url, headers=headers)
            
            text = parse_node_load_from_nodes(r_nodes.text, node)
            if text is not None:
                return text
            
            jobs_url = "https://pbsweb.enputron.ujep.cz/statuspbs/jobs"
            r_jobs = requests.get(jobs_url, headers=headers)

            text = parse_node_load_from_jobs(r_jobs.text, node)
            if text is not None:
                return text            

            return "Informace nenalezena"

        except Exception as e:
            return f"Chyba načítání: {e}"

    def show_job_status(self):
        status, error = cluster_service.get_job_status( key_path=self.key_path,
                                    user_name=self.user_name, host=self.host)

        if error is not None:
            QtWidgets.QMessageBox.critical(self, "Chyba",f"Chyba při načítání qstat:\n{error}")
            return
        
        if not status:
            QtWidgets.QMessageBox.information(self, "Stav úloh", "Žádné úlohy neběží.")
            return        
                
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Stav úloh")
        box.setInformativeText(status)
        box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        box.setStyleSheet("QLabel{min-width: 900px;}")
        box.exec_()



    def update_simComboBox(self):
        """Načte seznam složek se simulacemi z clusteru a zobrazí je v comboboxu."""
        folders, error = cluster_service.list_remote_simulations( key_path=self.key_path, 
                user_name=self.user_name, host=self.host, cluster_sim_path=self.cluster_sim_path)

        if error is not None:
            QtWidgets.QMessageBox.critical(self, "Chyba při načítání", error)
            return

        self.simComboBox.clear()
        if folders:
            self.simComboBox.addItems(folders)


    def copy_and_run_local_analysis(self):
        """Copy fold from cluster to PC"""
        sim_name = self.simComboBox.currentText()
        if not sim_name:
            QtWidgets.QMessageBox.warning( self, "Upozornění", "Nejprve vyber simulaci v seznamu.")
            return
        
        notebook_source = os.getenv("NOTEBOOK_SOURCE") 

        error = cluster_service.copy_simulation_folder( key_path=self.key_path, user_name=self.user_name,
                host=self.host, cluster_sim_path=self.cluster_sim_path, sim_name=sim_name, local_results_dir=Path(self.results_dir))
        if error is not None:
            QtWidgets.QMessageBox.critical(self, "Chyba při kopírování", error)
            return

        QtWidgets.QMessageBox.information( self, "Hotovo", f"Složka simulace '{sim_name}' byla zkopírována.")

        # # Копирование и запуск notebook ??? po zmenam kodu nevim
        # notebook_dest = os.path.join(str(self.results_dir), "hustotni_profil.ipynb")
        # shutil.copy(notebook_source, notebook_dest)
        # os.startfile(notebook_dest)

    def get_decimals_map(self):
        decimals_map = {}
        for key in self.config:
            widget = self.findChild(QtWidgets.QWidget, key)
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                decimals_map[key] = widget.decimals()
        return decimals_map


    def copy_only_dens_files(self):
        """Создать локальные папки и скопировать densF.dat из каждой симуляции с кластера."""
        error = cluster_service.copy_density_files( key_path=self.key_path, user_name=self.user_name,
                    host=self.host, cluster_sim_path=self.cluster_sim_path,
                    local_results_dir=Path(self.results_dir))

        if error is not None:
            QtWidgets.QMessageBox.critical(self,"Chyba", error)
            return

        QtWidgets.QMessageBox.information(self, "Hotovo", "Файлы densF.dat byly zkopírovány do všech složek.",)



app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec_()
