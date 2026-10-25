"""Warstwa komunikacji z urządzeniem."""
import re
import threading
import time
from contextlib import contextmanager

import rtmidi

import syx


class DeviceError(Exception):
  """Błąd komunikacji z urządzeniem (brak połączenia, timeout itp.)."""


# Windows dopisuje do nazwy numer portu ("reface DX 1"), który zmienia się
# zależnie od innych podłączonych urządzeń - dlatego dopasowanie wzorcem.
PORT_PATTERN = re.compile(r"^reface DX(\s+\d+)?$")


def _find_port(names: list[str]) -> int | None:
  return next((i for i, name in enumerate(names) if PORT_PATTERN.match(name)), None)


# F0 43 2n 7F 1C [model] [adres VOICE Bulk Header] F7 - prośba o aktualny głos
DUMP_REQUEST = [0xF0, 0x43, 0x20, 0x7F, 0x1C, syx.MODEL_ID, *syx.HEADER_ADDR, 0xF7]
DUMP_TIMEOUT = 2.0   # s na jedną próbę; urządzenie odpowiada w ok. 20 ms
ATTEMPTS = 3         # liczba prób pobrania / wysłania
POLL_INTERVAL = 0.005
SEND_DELAY = 0.01    # przerwa między blokami przy wysyłaniu (zapas - działa też bez niej)


class RefaceDevice:
  """reface DX podłączony przez USB (python-rtmidi)."""

  name = "reface DX (USB)"

  def __init__(self):
    # sprawdzanie połączenia działa w osobnym wątku - nie może otwierać portów
    # w tym samym czasie co pobieranie/wysyłanie
    self._lock = threading.Lock()

  @contextmanager
  def _ports(self):
    """Otwiera porty wejścia i wyjścia reface DX na czas operacji. Rzuca DeviceError."""
    with self._lock:
      midi_in = midi_out = None
      try:
        midi_in, midi_out = rtmidi.MidiIn(), rtmidi.MidiOut()
        in_idx = _find_port(midi_in.get_ports())
        out_idx = _find_port(midi_out.get_ports())
        if in_idx is None or out_idx is None:
          raise DeviceError("Nie znaleziono portów reface DX.")
        midi_in.ignore_types(sysex=False, timing=True, active_sense=True)  # domyślnie SysEx jest pomijany
        midi_in.open_port(in_idx)
        midi_out.open_port(out_idx)
      except rtmidi.RtMidiError as exc:  # np. port zajęty przez inny program
        for port in (midi_in, midi_out):
          if port is not None:
            port.close_port()  # wejście mogło się już otworzyć
        raise DeviceError(f"Nie można otworzyć portów reface DX: {exc}") from exc
      try:
        yield midi_in, midi_out
      finally:
        midi_in.close_port()
        midi_out.close_port()

  def is_connected(self) -> bool:
    """Gotowe do komunikacji = porty wejścia i wyjścia istnieją i dają się otworzyć."""
    try:
      with self._ports():
        return True
    except DeviceError:
      return False

  def dump_preset(self) -> bytes:
    """Pobiera aktualny głos z urządzenia. Ponawia próbę, jeśli odpowiedź jest niepełna."""
    with self._ports() as (midi_in, midi_out):
      last_error = "urządzenie nie odpowiedziało"
      for _ in range(ATTEMPTS):
        try:
          return self._request_voice(midi_in, midi_out)
        except syx.SyxError as exc:
          last_error = str(exc)
      raise DeviceError(f"Nie udało się pobrać presetu ({ATTEMPTS} próby): {last_error}")

  def send_preset(self, data: bytes) -> None:
    """Wysyła głos do urządzenia i potwierdza odbiór, odczytując go z powrotem."""
    blocks = syx.voice_blocks(data)
    with self._ports() as (midi_in, midi_out):
      last_error = "urządzenie nie odpowiedziało"
      for _ in range(ATTEMPTS):
        for msg in blocks:
          midi_out.send_message(msg)
          time.sleep(SEND_DELAY)
        try:
          received = syx.split_messages(self._request_voice(midi_in, midi_out))
        except syx.SyxError as exc:
          last_error = f"brak potwierdzenia: {exc}"
          continue
        # bajt 2 (numer urządzenia) może się różnić - porównujemy resztę bloku
        by_addr = {syx.block_address(m): m[3:] for m in received}
        if all(by_addr.get(syx.block_address(m)) == m[3:] for m in blocks):
          return
        last_error = "urządzenie ma inne dane niż wysłane"
      raise DeviceError(f"Nie udało się wysłać presetu ({ATTEMPTS} próby): {last_error}")

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
