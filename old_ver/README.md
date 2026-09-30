### build command
pyinstaller --onefile --windowed --name refacedx_library_X_X_X --hidden-import=mido.backends.rtmidi main.py

### with icon
pyinstaller --onefile --windowed --name refacedx_library_X_X_X --hidden-import=mido.backends.rtmidi --icon=*.ico main.py