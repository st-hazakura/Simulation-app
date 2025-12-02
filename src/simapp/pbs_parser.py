# pbs_parser.py
from __future__ import annotations
from bs4 import BeautifulSoup


def parse_node_load_from_nodes(html: str, node: str) -> str | None:
    """
    Разбирает страницу /nodes и пытается найти загрузку CPU для заданного node.
    Возвращает строку вида 'Zatížení CPU: ...' либо None, если таблица не найдена
    или нужный узел отсутствует.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "status"})
    if table is None:
        return None

    rows = table.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        name = cols[0].get_text(strip=True)
        if name == node:
            cpu_usage = cols[2].get_text(strip=True)
            return f"Zatížení CPU: {cpu_usage}"

    return "Informace nenalezena"


def parse_node_load_from_jobs(html: str, node: str) -> str | None:
    """
    Разбирает страницу /jobs и оценивает загрузку выбранного узла:
    - сколько running-jobů на этой ноде
    - примерное количество занятых CPU
    - примерное количество занятой памяти (GB)

    Возвращает строку вида:
        'Zatížení: X jobů, Y CPU, Z GB RAM'
    либо
        'Nic neběží.'
    либо None, если таблица не найдена.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "status"})
    if table is None:
        return None

    jobs_on_node = 0
    cpus_on_node = 0.0
    mem_on_node = 0.0

    # пропускаем строку-заголовок <tr><th>...</th></tr>
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

        # CPU колонка формат "72 |72"
        cpu_text = cols[4].get_text(strip=True)
        used_cpus = None
        if cpu_text:
            first_part = cpu_text.split("|")[0].strip()
            try:
                used_cpus = int(first_part)
            except ValueError:
                used_cpus = None

        # Memory(GB): "8 |588|100"
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