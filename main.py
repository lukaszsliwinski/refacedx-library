import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import config
from gui import MainWindow


def create_device():
  if config.USE_FAKE_DEVICE:
    from midi_io import FakeDevice
    return FakeDevice()
  from midi_io import RealDevice
  return RealDevice()


def main():
  config.PRESETS_DIR.mkdir(parents=True, exist_ok=True)
  app = QApplication(sys.argv)
  app.setWindowIcon(QIcon(str(config.resource_path("packaging/app_icon.ico"))))
  window = MainWindow(create_device(), config.PRESETS_DIR)
  window.show()
  sys.exit(app.exec())


if __name__ == "__main__":
  main()