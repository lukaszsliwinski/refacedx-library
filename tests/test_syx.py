import pytest

import syx

VALID = bytes([0xF0, 0x43, 0x10, 0x7F, 0x1C, 0x00, 0x01, 0x00, 0xF7])


def test_valid_single_message():
  assert syx.validate(VALID) == [VALID]


def test_multiple_messages():
  assert len(syx.validate(VALID + VALID)) == 2


def test_empty():
  with pytest.raises(syx.SyxError):
    syx.validate(b"")


def test_missing_end_byte():
  with pytest.raises(syx.SyxError):
    syx.validate(VALID[:-1])


def test_wrong_manufacturer():
  with pytest.raises(syx.SyxError):
    syx.validate(bytes([0xF0, 0x41, 0x10, 0x7F, 0xF7]))


def test_high_bit_in_data():
  with pytest.raises(syx.SyxError):
    syx.validate(bytes([0xF0, 0x43, 0x80, 0x7F, 0xF7]))


def test_garbage_outside_message():
  with pytest.raises(syx.SyxError):
    syx.validate(b"\x01\x02" + VALID)


def test_file_roundtrip(tmp_path):
  p = tmp_path / "a.syx"
  syx.write_syx_file(p, VALID)
  assert syx.read_syx_file(p) == VALID


# --- bulk dump reface DX ---

def make_block(addr, data):
  body = [syx.MODEL_ID, *addr, *data]
  checksum = -sum(body) & 0x7F
  count = len(body)
  return bytes([0xF0, 0x43, 0x00, 0x7F, 0x1C, count >> 7, count & 0x7F, *body, checksum, 0xF7])


def make_voice(name=b"Test Voice"):
  common = name.ljust(syx.NAME_LEN, b" ") + bytes(38 - syx.NAME_LEN)
  blocks = [make_block(syx.HEADER_ADDR, [])]
  blocks.append(make_block(syx.COMMON_ADDR, common))
  blocks += [make_block((0x31, op, 0x00), bytes(28)) for op in range(4)]
  blocks.append(make_block(syx.FOOTER_ADDR, []))
  return blocks


def test_voice_has_real_size():
  assert len(b"".join(make_voice())) == 241  # tyle ma każdy preset zapisany z urządzenia


def test_assemble_any_order():
  blocks = make_voice()
  assert syx.assemble_voice(list(reversed(blocks))) == b"".join(blocks)


def test_assemble_ignores_other_messages():
  blocks = make_voice()
  identity_reply = bytes([0xF0, 0x7E, 0x7F, 0x06, 0x02, 0x43, 0x00, 0x41, 0x53, 0x06, 0, 0, 0, 0x7F, 0xF7])
  assert syx.assemble_voice([identity_reply, *blocks]) == b"".join(blocks)


def test_assemble_missing_block():
  with pytest.raises(syx.SyxError):
    syx.assemble_voice(make_voice()[:-1])


def test_bad_checksum():
  blocks = make_voice()
  bad = bytearray(blocks[1])
  bad[-2] ^= 0x01
  with pytest.raises(syx.SyxError):
    syx.assemble_voice([blocks[0], bytes(bad), *blocks[2:]])


def test_voice_name_strips_padding():
  assert syx.voice_name(b"".join(make_voice(b"80s"))) == "80s"


def test_voice_name_missing_common():
  blocks = make_voice()
  with pytest.raises(syx.SyxError):
    syx.voice_name(b"".join([blocks[0], *blocks[2:]]))