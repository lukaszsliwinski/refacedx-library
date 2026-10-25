import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import config
from gui import MainWindow
from midi_io import RealDevice


def main():
  config.PRESETS_DIR.mkdir(parents=True, exist_ok=True)
  app = QApplication(sys.argv)
  app.setWindowIcon(QIcon(str(config.resource_path("packaging/app_icon.ico"))))
  window = MainWindow(RealDevice(), config.PRESETS_DIR)
  window.show()
  sys.exit(app.exec())


if __name__ == "__main__":
  main()