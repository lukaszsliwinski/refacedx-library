@echo off
setlocal

cd /d "%~dp0"
call rdxvenv\Scripts\activate || goto :error

set OUT=dist\RefaceLibrarian

echo === Testy ===
pytest -q || goto :error

echo === Zamykanie uruchomionej aplikacji ===
taskkill /F /IM RefaceLibrarian.exe >nul 2>&1

echo === Budowanie ===
if not exist packaging mkdir packaging
pyinstaller --noconfirm --clean --windowed --specpath packaging --icon "%~dp0packaging\app_icon.ico" --add-data "%~dp0packaging\app_icon.ico;packaging" --name RefaceLibrarian main.py
if errorlevel 1 goto :error

echo === Tworzenie pustego katalogu presets ===
if exist "%OUT%\presets" rmdir /S /Q "%OUT%\presets"
mkdir "%OUT%\presets" || goto :error

echo.
echo Gotowe: %OUT%\RefaceLibrarian.exe
if /I "%~1"=="run" start "" "%OUT%\RefaceLibrarian.exe"
exit /b 0

:error
echo.
echo BLAD: build nie powiodl sie.
exit /b 1