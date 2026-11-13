@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo          PromptBox 1.0.0 - Build
echo ========================================

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller no esta instalado. Instalando con el Python activo...
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 goto error
)

python -m PyInstaller --clean --noconfirm --onefile --windowed ^
  --name PromptBox ^
  --icon "promptbox.ico" ^
  --add-data "promptbox.ico;." ^
  --add-data "promptbox_icon.png;." ^
  --add-data "promptbox_logo.png;." ^
  app.py
if errorlevel 1 goto error

echo.
echo Compilacion terminada: dist\PromptBox.exe
echo Los datos se conservan en %USERPROFILE%\AppData\Local\PromptBox.
exit /b 0

:error
echo.
echo Error durante la compilacion. Revisa Python, PyInstaller y los recursos del proyecto.
exit /b 1
