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