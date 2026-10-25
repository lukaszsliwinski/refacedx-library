import pytest

from gui import safe_filename


@pytest.mark.parametrize("name, expected", [
  ("E.Piano 1", "E.Piano 1"),
  ("Bass/Lead", "Bass_Lead"),
  ('A:B*C?"<>|', "A_B_C_____"),
  ("Pad.", "Pad"),
  ("  Strings  ", "Strings"),
  ("con", "con_"),
  ("LPT1", "LPT1_"),
  ("...", ""),
])
def test_safe_filename(name, expected):
  assert safe_filename(name) == expected
