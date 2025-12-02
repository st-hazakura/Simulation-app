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

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui_path = UI / "simulace_app.ui"
        self.styles_path = UI / "style.css"
        self.param_path = CONFIG / "params.yaml"        
        self.decimal_path = CONFIG / "decimals.yaml"
        self.runall_path = SCRIPTS / "run_all.bat"
        
        load_dotenv(dotenv_path=ENV_FILE)
        self.user_name = os.getenv("CLUSTER_USERNAME")              # str | None
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

        self.queue_to_max_walltime = {
            "enp5": "20 dnů",
            "enp3": "3 dny",
        }

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
            url = "https://pbsweb.enputron.ujep.cz/statuspbs/nodes"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, 'html.parser')

            table = soup.find("table", {"class": "status"})
            if table is None:
                return self._get_load_from_jobs_table(node)

            rows = table.find_all("tr")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue
                name = cols[0].text.strip()
                if name == node:
                    cpu_usage = cols[2].text.strip()
                    return f"Zatížení CPU: {cpu_usage}"

            return "Informace nenalezena"
        except Exception as e:
            return f"Chyba načítání: {e}"


    def _get_load_from_jobs_table(self, node):
        """
        Парсим страницу /jobs и оцениваем загрузку выбранного узла:
        - сколько running-job'ов на этой ноде
        - примерное количество занятых CPU
        - примерное количество занятой памяти (GB)
        """
        try:
            url = "https://pbsweb.enputron.ujep.cz/statuspbs/jobs" 
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", {"class": "status"})
            if table is None:
                return "Tabulka jobů nenalezena"

            jobs_on_node = 0
            cpus_on_node = 0.0
            mem_on_node = 0.0 

            # пропускаем строку с <th> (заголовок)
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 14:
                    continue

                job_state = cols[12].get_text(strip=True)
                if job_state.lower() != "running":
                    continue

                exec_hosts = cols[13].get_text(strip=True)
                if node not in exec_hosts:
                    continue

                jobs_on_node += 1

                # CPU: колонка формат "72 |72"
                cpu_text = cols[4].get_text(strip=True)
                used_cpus = None
                if cpu_text:
                    # берём первое число до первой вертикальной черты
                    first_part = cpu_text.split("|")[0].strip()
                    try:
                        used_cpus = int(first_part)
                    except ValueError:
                        used_cpus = None

                #  Memory(GB): "8 |588|100" 
                mem_text = cols[6].get_text(strip=True)
                used_mem = 0.0
                if mem_text:
                    mem_parts = [p.strip() for p in mem_text.split("|") if p.strip()]
                    if mem_parts:
                        try:
                            used_mem = float(mem_parts[0])
                        except ValueError:
                            used_mem = 0.0

                # Exec Hosts: "node10[0] node10[1]" – делим ресурсы поровну между всеми хостами
                hosts = [h for h in exec_hosts.split() if h.strip()]
                n_hosts = max(len(hosts), 1)

                if used_cpus is not None:
                    cpus_on_node += used_cpus / n_hosts
                mem_on_node += used_mem / n_hosts

            if jobs_on_node == 0:
                return "Nic neběží."

            cpus_on_node_int = int(round(cpus_on_node))
            mem_on_node_rounded = round(mem_on_node, 1)

            return (
                f"Zatížení: {jobs_on_node} jobů, "
                f"{cpus_on_node_int} CPU, {mem_on_node_rounded} GB RAM"
            )

        except Exception as e:
            return f"Chyba načítání: {e}"

    def show_job_status(self):
        status = self.check_job_status()
        if status:
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("Stav úloh")
            box.setInformativeText(status)
            box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            box.setStyleSheet("QLabel{min-width: 900px;}")
            box.exec_()

    def check_job_status(self):
        try:
            result = subprocess.run(
                ["plink", "-batch", "-i", self.key_path, f"{self.user_name}@{self.host}", f"qstat -u {self.user_name}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                print("Aktuální úlohy:\n" + result.stdout)
                return result.stdout
            else:
                print("Chyba při načítání qstat:\n" + result.stderr)
                return None
        except Exception as e:
            print(f"Výjimka: {e}")
            return None

    def update_simComboBox(self):
        result = subprocess.run([
            "plink", "-batch", "-i", self.key_path, f"{self.user_name}@{self.host}",
            f"ls {self.cluster_sim_path}"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            folders = result.stdout.strip().splitlines()
            self.simComboBox.clear()
            self.simComboBox.addItems(folders)
        else:
            QtWidgets.QMessageBox.critical(self, "Chyba při načítání", result.stderr)


    def copy_and_run_local_analysis(self):
        """Copy fold from cluster to PC"""
        sim_name = self.simComboBox.currentText()
        notebook_source = os.getenv("NOTEBOOK_SOURCE") 

        dest_sim_folder = os.path.join(str(self.results_dir), sim_name)
        os.makedirs(dest_sim_folder, exist_ok=True)

        remote_path = f"{self.user_name}@{self.host}:{self.cluster_sim_path}/{sim_name}/*"
        result = subprocess.run([
            "pscp", "-i", self.key_path, "-r", remote_path, dest_sim_folder
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            QtWidgets.QMessageBox.critical(self, "Chyba při kopírování", result.stderr)
            return

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
        """Создать локальные папки и скопировать densF.dat из каждой симуляции с кластера"""

        # Получаем список всех папок в ~/simulations
        result = subprocess.run([
            "plink", "-batch", "-i", self.key_path, f"{self.user_name}@{self.host}",
            f"ls {self.cluster_sim_path}"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            QtWidgets.QMessageBox.critical(self, "Chyba", result.stderr)
            return

        all_folders = result.stdout.strip().splitlines()

        for folder in all_folders:
            local_path = os.path.join(self.results_dir, folder)
            os.makedirs(local_path, exist_ok=True)

            remote_file = f"{self.user_name}@{self.host}:{self.cluster_sim_path}/{folder}/densF.dat"
            local_file_path = os.path.join(local_path, "densF.dat")

            # Копируем только densF.dat
            subprocess.run([
                "pscp", "-i", self.key_path, remote_file, local_file_path
            ])

        QtWidgets.QMessageBox.information(self, "Hotovo", "Файлы densF.dat скопированы во все папки.")



app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec_()
