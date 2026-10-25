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
  return messages


# --- bulk dump głosu reface DX (dokumentacja: reface Data List, s. 6-9) ---

MODEL_ID = 0x05
HEADER_ADDR = (0x0E, 0x0F, 0x00)
COMMON_ADDR = (0x30, 0x00, 0x00)
FOOTER_ADDR = (0x0F, 0x0F, 0x00)
# kolejność bloków w pliku: header, common, operatory 1-4, footer
VOICE_BLOCKS = [HEADER_ADDR, COMMON_ADDR] + [(0x31, op, 0x00) for op in range(4)] + [FOOTER_ADDR]
NAME_LEN = 10

# F0 43 0n 7F 1C [count H] [count L] [model] [adres x3] dane... [suma] F7
_PREFIX_LEN = 7


def is_bulk_dump(msg: bytes) -> bool:
  """Czy wiadomość to blok bulk dump reface DX."""
  return (
    len(msg) >= 13
    and msg[0] == SYSEX_START
    and msg[1] == YAMAHA_ID
    and msg[2] & 0xF0 == 0x00
    and msg[3] == 0x7F
    and msg[4] == 0x1C
    and msg[7] == MODEL_ID
  )


def block_address(msg: bytes) -> tuple[int, int, int]:
  return msg[8], msg[9], msg[10]


def check_bulk_block(msg: bytes) -> None:
  """Sprawdza liczbę bajtów i sumę kontrolną bloku. Rzuca SyxError."""
  byte_count = (msg[5] << 7) | msg[6]
  # byte count obejmuje bajty od Model ID do danych włącznie (bez sumy i F7)
  if byte_count != len(msg) - _PREFIX_LEN - 2:
    raise SyxError(f"Blok {bytes(block_address(msg)).hex(' ')}: nieprawidłowa długość.")
  # suma od Model ID do sumy kontrolnej włącznie musi mieć 7 dolnych bitów = 0
  if sum(msg[_PREFIX_LEN:-1]) & 0x7F:
    raise SyxError(f"Blok {bytes(block_address(msg)).hex(' ')}: błędna suma kontrolna.")


def assemble_voice(messages: list[bytes]) -> bytes:
  """Składa kompletny głos z bloków (w dowolnej kolejności). Rzuca SyxError."""
  blocks: dict[tuple[int, int, int], bytes] = {}
  for msg in messages:
    if is_bulk_dump(msg):
      check_bulk_block(msg)
      blocks[block_address(msg)] = msg
  missing = [addr for addr in VOICE_BLOCKS if addr not in blocks]
  if missing:
    raise SyxError(f"Niekompletny preset - brak {len(missing)} z {len(VOICE_BLOCKS)} bloków.")
  return b"".join(blocks[addr] for addr in VOICE_BLOCKS)


def voice_blocks(data: bytes) -> list[bytes]:
  """Bloki głosu reface DX do wysłania. Rzuca SyxError, jeśli plik zawiera coś innego.

  Urządzenie przyjmuje bloki w dowolnej kolejności i niekompletny zestaw,
  ale odrzuca całość, jeśli trafi się blok spoza głosu (dokumentacja, s. 8)."""
  messages = validate(data)
  for i, msg in enumerate(messages, start=1):
    if not is_bulk_dump(msg) or block_address(msg) not in VOICE_BLOCKS:
      raise SyxError(f"Wiadomość {i} nie jest blokiem presetu reface DX.")
    check_bulk_block(msg)
  if not any(block_address(m) not in (HEADER_ADDR, FOOTER_ADDR) for m in messages):
    raise SyxError("Plik nie zawiera danych presetu.")
  return messages


def voice_name(data: bytes) -> str:
  """Nazwa głosu z bloku common (bez spacji z końca)."""
  for msg in split_messages(data):
    if is_bulk_dump(msg) and block_address(msg) == COMMON_ADDR:
      start = _PREFIX_LEN + 4  # za Model ID i adresem
      return bytes(msg[start:start + NAME_LEN]).decode("ascii", errors="replace").rstrip()
  raise SyxError("Brak bloku z nazwą presetu.")


def read_syx_file(path: Path) -> bytes:
  data = Path(path).read_bytes()
  voice_blocks(data)
  return data


def write_syx_file(path: Path, data: bytes) -> None:
  voice_blocks(data)
  Path(path).write_bytes(data)