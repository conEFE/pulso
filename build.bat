@echo off
rem Compila PULSO:
rem   dist\PulsoDigital.exe            portable (un solo archivo)
rem   dist\PulsoDigital\               versión en carpeta (abre más rápido)
rem   dist\PULSO_Setup_<versión>.exe   instalador con asistente (si Inno Setup 6 está instalado)
setlocal
cd /d "%~dp0"

if not exist venv (
    python -m venv venv || goto :error
)
call venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt || goto :error

if not exist data\modelo_ia.joblib (
    python descargar_datos.py || goto :error
    python prep_data.py || goto :error
)

set COMUNES=--noconfirm --windowed --name PulsoDigital --icon icono.ico --add-data "data;data" --add-data "icono.ico;." --collect-data customtkinter
pyinstaller %COMUNES% --onefile --workpath build\onefile app.py || goto :error
pyinstaller %COMUNES% --onedir --workpath build\onedir app.py || goto :error

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
for /f "tokens=2 delims==" %%v in ('findstr /b /c:"VERSION = " app.py') do set VERSION=%%~v
set VERSION=%VERSION: =%
set VERSION=%VERSION:"=%
if defined ISCC (
    %ISCC% /DMyAppVersion=%VERSION% installer\pulso.iss || goto :error
) else (
    echo Inno Setup 6 no esta instalado: se omite el instalador.
)

echo.
echo Listo. Archivos en la carpeta dist\
exit /b 0

:error
echo.
echo Fallo la compilacion.
exit /b 1
