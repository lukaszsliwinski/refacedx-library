"""Walidacja i obsługa plików .syx (SysEx)."""
from pathlib import Path

SYSEX_START = 0xF0
SYSEX_END = 0xF7
YAMAHA_ID = 0x43
MAX_FILE_SIZE = 1024 * 1024  # 1 MB - zabezpieczenie przed wysłaniem dużego pliku


class SyxError(Exception):
  """Plik/dane nie są poprawnym SysEx-em."""


def split_messages(data: bytes) -> list[bytes]:
  """Dzieli strumień bajtów na osobne wiadomości F0 ... F7."""
  messages: list[bytes] = []
  current = bytearray()
  inside = False

  for pos, b in enumerate(data):
    if b == SYSEX_START:
      if inside:
        raise SyxError(f"Bajt F0 w środku wiadomości (pozycja {pos}).")
      inside = True
      current = bytearray([b])
    elif b == SYSEX_END:
      if not inside:
        raise SyxError(f"Bajt F7 bez wcześniejszego F0 (pozycja {pos}).")
      current.append(b)
      messages.append(bytes(current))
      inside = False
    elif inside:
      if b > 0x7F:
        raise SyxError(f"Niedozwolony bajt 0x{b:02X} w danych (pozycja {pos}).")
      current.append(b)
    else:
      raise SyxError(f"Dane poza wiadomością SysEx (pozycja {pos}).")

  if inside:
    raise SyxError("Brak bajtu końcowego F7 - dane ucięte.")
  return messages


def validate(data: bytes) -> list[bytes]:
  """Sprawdza dane i zwraca listę wiadomości. Rzuca SyxError przy problemie."""
  if not data:
    raise SyxError("Pusty plik.")
  if len(data) > MAX_FILE_SIZE:
    raise SyxError("Plik jest za duży jak na preset.")

  messages = split_messages(data)
  if not messages:
    raise SyxError("Brak wiadomości SysEx.")

  for i, msg in enumerate(messages, start=1):
    if len(msg) < 4:
      raise SyxError(f"Wiadomość {i} jest zbyt krótka.")
    if msg[1] != YAMAHA_ID:
      raise SyxError(
        f"Wiadomość {i}: to nie Yamaha (ID producenta 0x{msg[1]:02X}, oczekiwano 0x43)."
      )
    # TODO: tu dodaj sprawdzanie nagłówka modelu reface DX, oczekiwanej
    # długości i sumy kontrolnej - według dokumentacji MIDI.
  return messages


def read_syx_file(path: Path) -> bytes:
  data = Path(path).read_bytes()
  validate(data)
  return data


def write_syx_file(path: Path, data: bytes) -> None:
  validate(data)
  Path(path).write_bytes(data)