# src/simapp/paths.py
from pathlib import Path

# .../Simulation-app/src/simapp/paths.py
PKG = Path(__file__).resolve().parent      # .../src/simapp
SRC = PKG.parent                           # .../src
ROOT = SRC.parent                          # .../ (корень проекта)

# use:
# from path import UI, CONFIG, ENV_FILE, SSH_KEY_PPK
# str(UI / "simulace_app.ui") 
UI      = SRC / "ui"
CONFIG  = SRC / "config"
SCRIPTS = SRC / "scripts"
CORE    = SRC / "core"

# Файлы в корне проекта, к которым нужен доступ *ssh
ENV_FILE     = ROOT / ".env"


def in_src(*parts) -> Path:
    """ Любой путь внутри src: in_src('ui','simulace_app.ui') -> .../ui/simulace_app.ui """
    return SRC.joinpath(*parts)

def in_root(*parts) -> Path:
    """Любой путь от корня проекта: in_root('README.md')"""
    return ROOT.joinpath(*parts)
