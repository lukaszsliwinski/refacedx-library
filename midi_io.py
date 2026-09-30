"""Warstwa komunikacji z urządzeniem. GUI zna tylko ten interfejs."""
import time
from typing import Protocol


class DeviceError(Exception):
  """Błąd komunikacji z urządzeniem (brak połączenia, timeout itp.)."""


class RefaceDevice(Protocol):
  name: str

  def is_connected(self) -> bool: ...
  def dump_preset(self, timeout: float = 5.0) -> bytes: ...
  def send_preset(self, data: bytes) -> None: ...


class FakeDevice:
  """Atrapa do pracy bez sprzętu."""

  name = "Atrapa (tryb testowy)"

  def __init__(self, simulate_errors: bool = False):
    self.simulate_errors = simulate_errors

  def is_connected(self) -> bool:
    return True

  def dump_preset(self, timeout: float = 5.0) -> bytes:
    time.sleep(1.0)  # symulacja opóźnienia
    if self.simulate_errors:
      raise DeviceError("Symulowany timeout: urządzenie nie odpowiedziało.")
    # Dane zastępcze - NIE są prawdziwym presetem reface DX.
    return bytes([0xF0, 0x43, 0x7D, 0x00, 0xF7])

  def send_preset(self, data: bytes) -> None:
    time.sleep(0.5)
    if self.simulate_errors:
      raise DeviceError("Symulowany błąd wysyłania.")
    print(f"[FAKE] wysłano {len(data)} bajtów: {data.hex(' ')}")


class RealDevice:
  """Docelowa implementacja na python-rtmidi - do napisania po zdobyciu sprzętu."""

  name = "reface DX (USB)"

  def __init__(self):
    raise NotImplementedError("RealDevice nie jest jeszcze zaimplementowane.")