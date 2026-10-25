"""Warstwa komunikacji z urządzeniem. GUI zna tylko ten interfejs."""
import re
import threading
from typing import Protocol

import rtmidi


class DeviceError(Exception):
  """Błąd komunikacji z urządzeniem (brak połączenia, timeout itp.)."""


class RefaceDevice(Protocol):
  name: str

  def is_connected(self) -> bool: ...
  def dump_preset(self, timeout: float = 5.0) -> bytes: ...
  def send_preset(self, data: bytes) -> None: ...


# Windows dopisuje do nazwy numer portu ("reface DX 1"), który zmienia się
# zależnie od innych podłączonych urządzeń - dlatego dopasowanie wzorcem.
PORT_PATTERN = re.compile(r"^reface DX(\s+\d+)?$")


def _find_port(names: list[str]) -> int | None:
  return next((i for i, name in enumerate(names) if PORT_PATTERN.match(name)), None)


class RealDevice:
  """reface DX podłączony przez USB (python-rtmidi)."""

  name = "reface DX (USB)"

  def __init__(self):
    # sprawdzanie połączenia działa w osobnym wątku - nie może otwierać portów
    # w tym samym czasie co pobieranie/wysyłanie
    self._lock = threading.Lock()

  def is_connected(self) -> bool:
    """Gotowe do komunikacji = porty wejścia i wyjścia istnieją i dają się otworzyć."""
    with self._lock:
      midi_in = midi_out = None
      try:
        midi_in, midi_out = rtmidi.MidiIn(), rtmidi.MidiOut()
        in_idx = _find_port(midi_in.get_ports())
        out_idx = _find_port(midi_out.get_ports())
        if in_idx is None or out_idx is None:
          return False
        midi_in.open_port(in_idx)
        midi_out.open_port(out_idx)
        return True
      except rtmidi.RtMidiError:
        return False  # np. port zajęty przez inny program
      finally:
        for port in (midi_in, midi_out):
          if port is not None:
            port.close_port()

  def dump_preset(self, timeout: float = 5.0) -> bytes:
    raise NotImplementedError("Pobieranie presetu nie jest jeszcze zaimplementowane.")

  def send_preset(self, data: bytes) -> None:
    raise NotImplementedError("Wysyłanie presetu nie jest jeszcze zaimplementowane.")
