# reface DX Librarian

Simple preset librarian for the Yamaha reface DX synthesizer (Windows 11, USB-MIDI, `.syx` files).

- browse the `presets` folder as a tree (subfolders supported)
- download a preset from the device and save it in the selected folder
- double-click a `.syx` file (or press Enter) to send it to the device
- keyboard: Enter expands/collapses a folder, Delete removes the selected file or folder (with confirmation)
- right-click menu: create folder, rename, delete (the root `presets` folder can only get new subfolders)

## Requirements

- Python 3.12 (newer versions have no official `python-rtmidi` wheels): https://www.python.org/downloads/release/python-31210/
- Windows 11

## Setup

```
python -m venv rdxvenv
rdxvenv\Scripts\activate
pip install -r requirements.txt
```

## Run

```
python main.py
```

## Tests

```
pytest
```

## Build

Set your venv name in `build.bat`, then:

```
.\build.bat
```

Output: `dist\RefaceLibrarian\RefaceLibrarian.exe`.