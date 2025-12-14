from __future__ import annotations
from typing import List, Tuple, Optional
import subprocess
from pathlib import Path


def _run_plink(key_path: str, user_name: str, host: str, command: str) -> subprocess.CompletedProcess:
    """Внутренний helper для plink."""
    return subprocess.run(
        ["plink", "-batch", "-i", key_path, f"{user_name}@{host}", command,],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_pscp( key_path: str, source: str, dest: str, recursive: bool = False) -> subprocess.CompletedProcess:
    """Внутренний helper для pscp."""
    cmd = ["pscp", "-i", key_path]
    if recursive:
        cmd.append("-r")
    cmd.extend([source, dest])

    return subprocess.run( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def get_job_status(key_path: str, user_name: str, host: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Запускает `qstat -u user_name` на кластере.
    Возвращает (output, error):
      - если всё ок: (stdout, None)
      - если ошибка: (None, text_error)
    """
    try:
        result = _run_plink( key_path=key_path, user_name=user_name, host=host, 
                            command=f"qstat -u {user_name}")
        if result.returncode == 0:
            return result.stdout, None
        else:
            return None, result.stderr or "Neznámá chyba qstat"
    except Exception as e:
        return None, str(e)


def list_remote_simulations(key_path: str, user_name: str, host: str, cluster_sim_path: str,
                            ) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Возвращает список папок в каталоге с симуляциями на кластере.
    (folders, error)
    """
    try:
        result = _run_plink(key_path=key_path, user_name=user_name, host=host,
                            command=f"ls {cluster_sim_path}")
        if result.returncode != 0:
            return None, result.stderr or "Chyba při načítání seznamu simulací"

        folders = result.stdout.strip().splitlines()
        return folders, None
    except Exception as e:
        return None, str(e)


def copy_simulation_folder( key_path: str, user_name: str, host: str, cluster_sim_path: str,
                           sim_name: str, local_results_dir: Path) -> Optional[str]:
    """
    Копирует папку конкретной симуляции с кластера в локальный каталог.
    Возвращает:
      - None, если всё ок
      - текст ошибки, если что-то пошло не так
    """
    try:
        dest_sim_folder = local_results_dir / sim_name
        dest_sim_folder.mkdir(parents=True, exist_ok=True)

        remote_path = f"{user_name}@{host}:{cluster_sim_path}/{sim_name}/*"
        result = _run_pscp( key_path=key_path, source=remote_path, 
                           dest=str(dest_sim_folder), recursive=True)
        if result.returncode != 0:
            return result.stderr or "Chyba při kopírování simulace"

        return None
    except Exception as e:
        return str(e)


def copy_density_files( key_path: str, user_name: str, host: str, cluster_sim_path: str,
                       local_results_dir: Path) -> Optional[str]:
    """
    Создаёт локальные папки и копирует densF.dat из каждой симуляции с кластера.
    Возвращает:
      - None, если всё ок
      - текст ошибки, если что-то пошло не так (первая серьёзная ошибка)
    """
    # 1. Получаем список папок на кластере
    folders, err = list_remote_simulations(key_path=key_path, user_name=user_name, host=host,
                                           cluster_sim_path=cluster_sim_path)
    if err is not None:
        return err
    if not folders:
        return "Na clustru nebyly nalezeny žádné složky se simulacemi."

    # 2. Копируем densF.dat из каждой
    for folder in folders:
        local_path = local_results_dir / folder
        local_path.mkdir(parents=True, exist_ok=True)

        remote_file = (f"{user_name}@{host}:{cluster_sim_path}/{folder}/densF.dat")
        local_file_path = local_path / "densF.dat"

        result = _run_pscp( key_path=key_path, source=remote_file, dest=str(local_file_path),
                           recursive=False)
        # если очень хочется, можно проверять returncode и копить ошибки в список
        # но для простоты: если сломалось — возвращаем первую ошибку
        if result.returncode != 0:
            return result.stderr or f"Chyba při kopírování densF.dat ze složky {folder}"

    return None


def completeness_check(key_path: str, user_name: str, host: str, cluster_sim_path: str
                                        ) -> Tuple[List[Tuple[str, int | None, int]], Optional[str], List[str]]:
    """
    Для всех симуляций на кластере:
      - читает nrun из box.in,
      - ищет файлы run.restart.* и определяет последний шаг,
      - если последний шаг >= nrun -> добавляет путь папки в isfinished
      - иначе добавляет запись в список unfinished_list незавершённых симуляций.

    Возвращает:
      (unfinished_list, error, isfinished),
      где unfinished_list: [(folder, last_restart_step | None, expected_nrun), ...]
    """
    # 1. Получаем список папок
    folders, err = list_remote_simulations( key_path=key_path, user_name=user_name, host=host, cluster_sim_path=cluster_sim_path)
    if err is not None:
        return [], err
    if not folders:
        return [], "Na clustru nebyly nalezeny žádné složky se simulacemi."
    
    unfinished: List[Tuple[str, int | None, int]] = []
    isfinished: List[str] = []
    

    for folder in folders:
        # --- читаем nrun из box.in ---
        cmd_nrun = (
            f"cd {cluster_sim_path}/{folder} && "
            "grep 'variable nrun' box.in | awk '{print $4}'")
        
        result_nrun = _run_plink( key_path=key_path, user_name=user_name, host=host, command=cmd_nrun,)
        if result_nrun.returncode != 0 or not result_nrun.stdout.strip():
            return [], result_nrun.stderr or f"Nelze zjistit nrun v simulaci {folder}"
        try:
            nrun = int(result_nrun.stdout.strip().split()[0])
        except ValueError:
            return [], f"Neplatná hodnota nrun v simulaci {folder}: {result_nrun.stdout!r}"

        # --- ищем restart файлы, в случае ошибки программа возвращает 0 ---
        cmd_ls_restart = (
            f"cd {cluster_sim_path}/{folder} && ls run.restart.* 2>/dev/null || true")
        
        
        result_restart = _run_plink( key_path=key_path, user_name=user_name, host=host, command=cmd_ls_restart)
        if result_restart.returncode != 0:
            # тут treat как ошибку, это уже странно
            return [], result_restart.stderr or f"Chyba při listování restart souborů v {folder}"
        
        # список всех рестарт файлов + требуемый последний рестарт
        lines = [ln for ln in result_restart.stdout.strip().splitlines() if ln]
        steps: List[int] = []
        for name in lines:
            # ожидаем имена вида run.restart.500000б оставляем то что после точки
            parts = name.rsplit(".", 1)
            if len(parts) != 2:
                continue
            try:
                steps.append(int(parts[1]))
            except ValueError:
                continue
        #тайпхинт переменной
        last_step: int | None = max(steps) if steps else None

        # решение: докопалась ли симуляция до конца
        finished = last_step is not None and last_step >= nrun

        if finished:
            isfinished.append(str(folder))
        else:
            unfinished.append((folder, last_step, nrun))

    return unfinished, None, isfinished



def copy_densF_for_finish_sim(key_path: str, user_name: str, host: str, cluster_sim_path: str,
                              isfinished: List[str], local_results_dir: Path):
    folders, err = list_remote_simulations( key_path=key_path, user_name=user_name, host=host, cluster_sim_path=cluster_sim_path)
    
    for folder in folders:
        if folder in isfinished:
            # копируем densF.dat, как в copy_density_files
            local_path = local_results_dir / folder
            local_path.mkdir(parents=True, exist_ok=True)

            remote_file = f"{user_name}@{host}:{cluster_sim_path}/{folder}/densF.dat"
            local_file_path = local_path / "densF.dat"

            copy_result = _run_pscp(
                key_path=key_path,
                source=remote_file,
                dest=str(local_file_path),
                recursive=False,
            )
            if copy_result.returncode != 0:
                return copy_result.stderr or f"Chyba při kopírování densF.dat ze složky {folder}"
    return None




def restart_simulation_on_cluster(key_path: str, user_name: str, host: str, cluster_sim_path: str,
                                  sim_name: str, node: str, queue: str, ppn: int, mem_gb: int,
                                  last_step: int | None, expected_nrun: int | None):
    """
      - проверяем входные данные;
      - переписываем ресурсы в run.sh (nodes, queue, mem);
      - запускаем qsub run.sh через plink.
      
          Возвращает:
      None       - если всё ок;
      строку str - с текстом ошибки, если что-то пошло не так
    """
    
    if not sim_name:
        return "Nebyl předán název simulace."
    if not node:
        return "Nebyl vybrán žádný node."
    if not queue:
        return "Pro vybraný node nebyla nalezena fronta (queue)."    
    
    remote_sim_dir = Path(cluster_sim_path) / sim_name
    remote_sim_dir_str = str(remote_sim_dir)
    
    mem_str = f"{int(mem_gb)}gb"


    # Команда, которая выполняется на кластере
    remote_cmd_parts = [
        f'cd "{remote_sim_dir_str}"',
        'if [ ! -f run.sh ]; then echo "run.sh nenalezen"; exit 1; fi',
        # обновляем узел + ppn
        f"sed -i 's/^#PBS -l nodes=.*/#PBS -l nodes={node}:ppn={ppn}/' run.sh",
        # очередь
        f"sed -i 's/^#PBS -q .*/#PBS -q {queue}/' run.sh",
        # память
        f"sed -i 's/^#PBS -l mem=.*/#PBS -l mem={mem_str}/' run.sh",
        # запуск задания
        "qsub run.sh",
    ]
    
    remote_cmd = " && ".join(remote_cmd_parts)
    
    result = _run_plink(
        key_path=key_path,
        user_name=user_name,
        host=host,
        command=remote_cmd,
    )        
    
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "neznámá chyba"
        return f"Chyba při spouštění restartu na clustru:\n{msg}"
    
    return None
