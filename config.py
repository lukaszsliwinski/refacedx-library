import sys
from pathlib import Path


def app_dir() -> Path:
  """Katalog projektu (python main.py) lub katalog z .exe (po spakowaniu)."""
  if getattr(sys, "frozen", False):
    return Path(sys.executable).resolve().parent
  return Path(__file__).resolve().parent

def resource_path(relative: str) -> Path:
    """Plik dołączony do aplikacji (python main.py lub po spakowaniu)."""
    base = Path(getattr(sys, "_MEIPASS", app_dir()))
    return base / relative

PRESETS_DIR = app_dir() / "presets"

USE_FAKE_DEVICE = True
APP_TITLE = "reface DX Librarian"