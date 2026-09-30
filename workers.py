"""Wykonywanie blokujących operacji (MIDI) poza wątkiem GUI."""
import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
  finished = Signal(object, object)  # (callback, wynik)
  error = Signal(str)


class Worker(QRunnable):
  def __init__(self, fn, *args, on_done):
    super().__init__()
    self.fn = fn
    self.args = args
    self.on_done = on_done
    self.signals = WorkerSignals()

  @Slot()
  def run(self):
    try:
      result = self.fn(*self.args)
    except Exception as exc:  # noqa: BLE001 - chcemy złapać wszystko
      traceback.print_exc()
      self.signals.error.emit(str(exc) or exc.__class__.__name__)
    else:
      self.signals.finished.emit(self.on_done, result)