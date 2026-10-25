"""Warstwa komunikacji z urządzeniem. GUI zna tylko ten interfejs."""
import re
import threading
import time
from typing import Protocol

import rtmidi

import syx


class DeviceError(Exception):
  """Błąd komunikacji z urządzeniem (brak połączenia, timeout itp.)."""


class RefaceDevice(Protocol):
  name: str

  def is_connected(self) -> bool: ...
  def dump_preset(self) -> bytes: ...
  def send_preset(self, data: bytes) -> None: ...


# Windows dopisuje do nazwy numer portu ("reface DX 1"), który zmienia się
# zależnie od innych podłączonych urządzeń - dlatego dopasowanie wzorcem.
PORT_PATTERN = re.compile(r"^reface DX(\s+\d+)?$")


def _find_port(names: list[str]) -> int | None:
  return next((i for i, name in enumerate(names) if PORT_PATTERN.match(name)), None)


# F0 43 2n 7F 1C [model] [adres VOICE Bulk Header] F7 - prośba o aktualny głos
DUMP_REQUEST = [0xF0, 0x43, 0x20, 0x7F, 0x1C, syx.MODEL_ID, *syx.HEADER_ADDR, 0xF7]
DUMP_TIMEOUT = 2.0   # s na jedną próbę; urządzenie odpowiada w ok. 20 ms
DUMP_ATTEMPTS = 3
POLL_INTERVAL = 0.005


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

  def dump_preset(self) -> bytes:
    """Pobiera aktualny głos z urządzenia. Ponawia próbę, jeśli odpowiedź jest niepełna."""
    with self._lock:
      midi_in, midi_out = rtmidi.MidiIn(), rtmidi.MidiOut()
      try:
        in_idx = _find_port(midi_in.get_ports())
        out_idx = _find_port(midi_out.get_ports())
        if in_idx is None or out_idx is None:
          raise DeviceError("Nie znaleziono portów reface DX.")
        midi_in.ignore_types(sysex=False, timing=True, active_sense=True)  # domyślnie SysEx jest pomijany
        try:
          midi_in.open_port(in_idx)
          midi_out.open_port(out_idx)
        except rtmidi.RtMidiError as exc:
          raise DeviceError(f"Nie można otworzyć portów reface DX: {exc}") from exc

        last_error = "urządzenie nie odpowiedziało"
        for _ in range(DUMP_ATTEMPTS):
          try:
            return self._request_voice(midi_in, midi_out)
          except syx.SyxError as exc:
            last_error = str(exc)
        raise DeviceError(f"Nie udało się pobrać presetu ({DUMP_ATTEMPTS} próby): {last_error}")
      finally:
        midi_in.close_port()
        midi_out.close_port()

  @staticmethod
  def _request_voice(midi_in: rtmidi.MidiIn, midi_out: rtmidi.MidiOut) -> bytes:
    """Jedna próba: wysyła dump request i zbiera bloki, aż będzie komplet albo minie czas."""
    while midi_in.get_message():  # resztki z poprzedniej próby
      pass
    midi_out.send_message(DUMP_REQUEST)

    messages: list[bytes] = []
    deadline = time.monotonic() + DUMP_TIMEOUT
    while time.monotonic() < deadline:
      event = midi_in.get_message()
      if event is None:
        time.sleep(POLL_INTERVAL)
        continue
      messages.append(bytes(event[0]))
      try:
        return syx.assemble_voice(messages)
      except syx.SyxError:
        continue  # jeszcze nie komplet albo uszkodzony blok - czekamy dalej
    return syx.assemble_voice(messages)  # rzuci SyxError z opisem, czego brakuje

  def send_preset(self, data: bytes) -> None:
    raise NotImplementedError("Wysyłanie presetu nie jest jeszcze zaimplementowane.")
