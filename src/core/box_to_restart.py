import re

def make_restart_in_from_box(box_text: str, rstfile: str, nrun_cont: int) -> str:
    txt = box_text

    # 1) вставка переменных перед "# General"
    insert = (
        "\n# --- Continuation from restart ---\n"
        f"variable nrun_cont   equal   {nrun_cont}\n"
        f"variable rstfile     string  {rstfile}\n\n"
    )
    txt = txt.replace("\n# General\n", insert + "# General\n", 1)

    # 2) read_data -> read_restart
    txt = re.sub(r"^\s*read_data\s+.*$",
                 "read_restart     ${rstfile}",
                 txt, flags=re.MULTILINE)

    # 3) убрать блоки #0 и #1 до reset_timestep 0 (включительно)
    txt = re.sub(r"#0 Rescaling NVT.*?^\s*reset_timestep\s+0\s*$\n?",
                 "", txt, flags=re.DOTALL | re.MULTILINE)

    # 4) убрать velocity scale перед production
    txt = re.sub(r"^\s*velocity\s+fluid\s+scale\s+.*\n",
                 "", txt, flags=re.MULTILINE)

    # 5) run ${nrun} -> run ${nrun_cont}
    txt = re.sub(r"^\s*run\s+\$\{nrun\}\s*$",
                 "run              ${nrun_cont}",
                 txt, flags=re.MULTILINE)

    return txt
