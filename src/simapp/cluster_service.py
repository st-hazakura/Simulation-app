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
