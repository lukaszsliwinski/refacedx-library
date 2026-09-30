import re
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
  QDir,
  QFile,
  QModelIndex,
  QPoint,
  QSortFilterProxyModel,
  QThreadPool,
  Qt,
  Slot,
)
from PySide6.QtWidgets import (
  QFileSystemModel,
  QInputDialog,
  QLabel,
  QMainWindow,
  QMenu,
  QMessageBox,
  QPushButton,
  QTreeView,
  QVBoxLayout,
  QWidget,
)

import config
import syx
from midi_io import RefaceDevice
from workers import Worker


def safe_filename(name: str) -> str:
  name = name.strip()
  if name.lower().endswith(".syx"):
    name = name[:-4]
  name = re.sub(r'[<>:"/\\|?*]', "_", name)
  return name.strip(" .")


class RootOnlyProxy(QSortFilterProxyModel):
  """Pokazuje tylko katalog 'root' i jego zawartość; ukrywa resztę katalogu nadrzędnego."""

  def __init__(self, root_dir: Path, parent=None):
    super().__init__(parent)
    self.root_dir = Path(root_dir).resolve()
    self.parent_dir = self.root_dir.parent

  def filterAcceptsRow(self, source_row, source_parent):
    model = self.sourceModel()
    index = model.index(source_row, 0, source_parent)
    path = Path(model.filePath(index)).resolve()
    if path.parent == self.parent_dir:
      return path == self.root_dir  # na poziomie nadrzędnym tylko 'presets'
    return True


class MainWindow(QMainWindow):
  def __init__(self, device: RefaceDevice, root_dir: Path):
    super().__init__()
    self.device = device
    self.root_dir = Path(root_dir)
    self._busy = False

    self.setWindowTitle(config.APP_TITLE)
    self.resize(560, 640)

    # --- model plików ---
    self.model = QFileSystemModel(self)
    self.model.setRootPath(str(self.root_dir.parent))
    self.model.setFilter(
      QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
    )
    self.model.setNameFilters(["*.syx"])
    self.model.setNameFilterDisables(False)

    self.proxy = RootOnlyProxy(self.root_dir, self)
    self.proxy.setSourceModel(self.model)

    # --- drzewo ---
    self.tree = QTreeView()
    self.tree.setModel(self.proxy)
    self.tree.setRootIndex(
      self.proxy.mapFromSource(self.model.index(str(self.root_dir.parent)))
    )
    for col in (1, 2, 3):
      self.tree.hideColumn(col)
    self.tree.setHeaderHidden(True)
    self.tree.setSortingEnabled(True)
    self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
    self.tree.doubleClicked.connect(self._on_double_click)
    self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.tree.customContextMenuRequested.connect(self._show_context_menu)
    self.tree.selectionModel().currentChanged.connect(self._update_target_label)

    # --- reszta interfejsu ---
    self.target_label = QLabel()
    self.dump_button = QPushButton("Pobierz preset z urządzenia")
    self.dump_button.clicked.connect(self._on_dump_clicked)

    layout = QVBoxLayout()
    layout.addWidget(self.target_label)
    layout.addWidget(self.tree, stretch=1)
    layout.addWidget(self.dump_button)
    central = QWidget()
    central.setLayout(layout)
    self.setCentralWidget(central)

    self.statusBar().addPermanentWidget(QLabel(f"Urządzenie: {device.name}"))
    self.statusBar().showMessage("Gotowe. Dwukrotne kliknięcie pliku .syx wysyła go do urządzenia.")

    # rozwiń i zaznacz 'presets' na starcie
    presets_index = self.proxy.mapFromSource(self.model.index(str(self.root_dir)))
    self.tree.setCurrentIndex(presets_index)
    self.tree.expand(presets_index)
    self._update_target_label()

  # ---------- pomocnicze ----------

  def current_dir(self) -> Path:
    """Katalog docelowy zapisu: zaznaczony folder, folder zaznaczonego pliku albo root."""
    index = self.tree.currentIndex()
    if not index.isValid():
      return self.root_dir
    src = self.proxy.mapToSource(index)
    path = Path(self.model.filePath(src))
    return path if self.model.isDir(src) else path.parent

  @Slot()
  def _update_target_label(self, *_):
    try:
      rel = self.current_dir().relative_to(self.root_dir)
      shown = f"\\{self.root_dir.name}" if str(rel) == "." else f"\\{self.root_dir.name}\\{rel}"
    except ValueError:
      shown = str(self.current_dir())
    self.target_label.setText(f"Katalog zapisu: {shown}")

  def _set_busy(self, busy: bool, message: str = ""):
    self._busy = busy
    self.dump_button.setEnabled(not busy)
    if busy:
      self.statusBar().showMessage(message)

  def _run_async(self, fn, *args, on_done, busy_msg: str):
    self._set_busy(True, busy_msg)
    worker = Worker(fn, *args, on_done=on_done)
    worker.signals.finished.connect(self._on_worker_finished)
    worker.signals.error.connect(self._on_worker_error)
    QThreadPool.globalInstance().start(worker)

  @Slot(object, object)
  def _on_worker_finished(self, callback, result):
    self._set_busy(False)
    callback(result)

  @Slot(str)
  def _on_worker_error(self, message: str):
    self._set_busy(False)
    self.statusBar().showMessage("Operacja nie powiodła się.", 5000)
    QMessageBox.critical(self, "Błąd urządzenia", message)

  def _check_device(self) -> bool:
    if not self.device.is_connected():
      QMessageBox.warning(self, "Brak urządzenia", "Nie wykryto reface DX.")
      return False
    return True


  # ---------- menu kontekstowe: nowy folder / zmień nazwę / usuń ----------

  @staticmethod
  def _name_taken(parent: Path, name: str, ignore: Path | None = None) -> bool:
    """Czy w folderze istnieje już element o tej nazwie (bez rozróżniania wielkości liter).
    Sprawdza też pliki ukryte przez filtr *.syx."""
    lowered = name.lower()
    for entry in parent.iterdir():
      if entry.name.lower() == lowered and entry != ignore:
        return True
    return False

  @Slot(QPoint)
  def _show_context_menu(self, pos: QPoint):
    index = self.tree.indexAt(pos)
    if not index.isValid() or self._busy:
      return  # puste miejsce albo trwa operacja na urządzeniu

    self.tree.setCurrentIndex(index)  # prawy klik zaznacza element
    src = self.proxy.mapToSource(index)
    path = Path(self.model.filePath(src))
    is_dir = self.model.isDir(src)
    is_root = path.resolve() == self.root_dir.resolve()

    menu = QMenu(self)
    act_new = act_rename = act_delete = None
    if is_dir:
      act_new = menu.addAction("Utwórz nowy folder")
    if not is_root:  # katalog główny: bez zmiany nazwy i usuwania
      act_rename = menu.addAction("Zmień nazwę")
      act_delete = menu.addAction("Usuń")

    chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
    if chosen is None:
      return
    if chosen is act_new:
      self._create_folder(path, index)
    elif chosen is act_rename:
      self._rename_item(path)
    elif chosen is act_delete:
      self._delete_item(path)

  def _create_folder(self, parent_dir: Path, parent_index: QModelIndex):
    name, ok = QInputDialog.getText(
      self, "Nowy folder", f"Nazwa nowego folderu w „{parent_dir.name}”:", text="Nowy folder"
    )
    if not ok:
      return
    name = safe_filename(name)
    if not name:
      QMessageBox.warning(self, "Nieprawidłowa nazwa", "Nazwa nie może być pusta.")
      return
    try:
      if self._name_taken(parent_dir, name):
        QMessageBox.warning(self, "Nazwa zajęta", f"W tym folderze istnieje już „{name}”.")
        return
      (parent_dir / name).mkdir()
    except OSError as exc:
      QMessageBox.critical(self, "Błąd", f"Nie udało się utworzyć folderu:\n{exc}")
      return
    self.tree.expand(parent_index)
    self.statusBar().showMessage(f"Utworzono folder: {name}", 5000)

  def _rename_item(self, path: Path):
    is_file = path.is_file()
    suffix = path.suffix if is_file else ""
    old_name = path.stem if is_file else path.name

    text, ok = QInputDialog.getText(self, "Zmień nazwę", "Nowa nazwa:", text=old_name)
    if not ok:
      return
    new_base = safe_filename(text)
    if not new_base:
      QMessageBox.warning(self, "Nieprawidłowa nazwa", "Nazwa nie może być pusta.")
      return
    new_name = new_base + suffix  # rozszerzenie pliku zostaje bez zmian
    if new_name == path.name:
      return
    try:
      # ignore=path pozwala zmienić samą wielkość liter (np. bas -> Bas)
      if self._name_taken(path.parent, new_name, ignore=path):
        QMessageBox.warning(self, "Nazwa zajęta", f"W tym folderze istnieje już „{new_name}”.")
        return
      path.rename(path.with_name(new_name))
    except OSError as exc:
      QMessageBox.critical(self, "Błąd", f"Nie udało się zmienić nazwy:\n{exc}")
      return
    self.statusBar().showMessage(f"Zmieniono nazwę: {path.name} → {new_name}", 5000)

  def _delete_item(self, path: Path):
    if path.is_dir():
      count = sum(1 for _ in path.rglob("*"))
      text = f"Usunąć folder „{path.name}” razem z zawartością ({count} elem.)?"
    else:
      text = f"Usunąć plik „{path.name}”?"

    answer = QMessageBox.question(
      self, "Potwierdź usunięcie", text,
      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
      QMessageBox.StandardButton.No,  # domyślnie "Nie"
    )
    if answer != QMessageBox.StandardButton.Yes:
      return

    # najpierw próba przeniesienia do Kosza (można odzyskać)
    result = QFile.moveToTrash(str(path))
    moved = result[0] if isinstance(result, tuple) else result
    if not moved:
      answer = QMessageBox.question(
        self, "Nie można przenieść do Kosza",
        f"Nie udało się przenieść „{path.name}” do Kosza.\nUsunąć trwale?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
      )
      if answer != QMessageBox.StandardButton.Yes:
        return
      try:
        if path.is_dir():
          shutil.rmtree(path)
        else:
          path.unlink()
      except OSError as exc:
        QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć:\n{exc}")
        return

    self._update_target_label()
    self.statusBar().showMessage(f"Usunięto: {path.name}", 5000)

  # ---------- pobieranie z urządzenia ----------

  @Slot()
  def _on_dump_clicked(self):
    if self._busy or not self._check_device():
      return
    target_dir = self.current_dir()  # zapamiętaj teraz, zaznaczenie może się zmienić
    self._run_async(
      self.device.dump_preset,
      on_done=lambda data: self._on_dump_done(data, target_dir),
      busy_msg="Pobieranie presetu z urządzenia…",
    )

  def _on_dump_done(self, data: bytes, target_dir: Path):
    try:
      syx.validate(data)
    except syx.SyxError as exc:
      QMessageBox.warning(self, "Nieprawidłowe dane", f"Urządzenie zwróciło błędne dane:\n{exc}")
      return

    default = datetime.now().strftime("preset_%Y%m%d_%H%M%S")
    name, ok = QInputDialog.getText(
      self, "Zapisz preset", f"Nazwa pliku (bez rozszerzenia)\nKatalog: {target_dir}", text=default
    )
    name = safe_filename(name) if ok else ""
    if not name:
      self.statusBar().showMessage("Zapis anulowany.", 5000)
      return

    path = target_dir / f"{name}.syx"
    if path.exists():
      answer = QMessageBox.question(
        self, "Plik istnieje", f"{path.name} już istnieje. Nadpisać?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
      )
      if answer != QMessageBox.StandardButton.Yes:
        self.statusBar().showMessage("Zapis anulowany.", 5000)
        return
    try:
      syx.write_syx_file(path, data)
    except OSError as exc:
      QMessageBox.critical(self, "Błąd zapisu", str(exc))
      return
    self.statusBar().showMessage(f"Zapisano: {path.name}", 5000)

  # ---------- wysyłanie do urządzenia ----------

  @Slot(QModelIndex)
  def _on_double_click(self, index: QModelIndex):
    src = self.proxy.mapToSource(index)
    if self._busy or self.model.isDir(src):
      return  # foldery rozwija/zwija samo drzewo
    path = Path(self.model.filePath(src))
    if path.suffix.lower() != ".syx":
      return

    try:
      data = syx.read_syx_file(path)
    except (OSError, syx.SyxError) as exc:
      QMessageBox.warning(self, "Nie można wczytać pliku", f"{path.name}:\n{exc}")
      return
    if not self._check_device():
      return

    self._run_async(
      self.device.send_preset,
      data,
      on_done=lambda _: self.statusBar().showMessage(f"Wysłano: {path.name}", 5000),
      busy_msg=f"Wysyłanie {path.name}…",
    )