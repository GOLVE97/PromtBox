@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo          PromptBox 0.5 - Build
echo ========================================
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto error

pyinstaller --clean --noconfirm --onefile --windowed ^
  --name PromptBox ^
  --icon "promptbox.ico" ^
  --add-data "promptbox.ico;." ^
  --add-data "promptbox_icon.png;." ^
  --add-data "promptbox_logo.png;." ^
  app.py
if errorlevel 1 goto error

echo.
echo Compilacion terminada: dist\PromptBox.exe
echo Los datos existentes se mantienen en AppData\Local\PromptBox.
pause
exit /b 0

:error
echo.
echo Error durante la compilacion. Revisa Python y vuelve a intentarlo.
pause
exit /b 1
