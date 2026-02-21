@echo off
setlocal

set PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe
if not exist "%PYTHON_EXE%" (
  echo No se encontro Python en "%PYTHON_EXE%".
  pause
  exit /b 1
)

echo Instalando PyInstaller...
"%PYTHON_EXE%" -m pip install pyinstaller
if errorlevel 1 (
  echo Error instalando PyInstaller.
  pause
  exit /b 1
)

echo Generando EXE...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --onefile --windowed --name EditorCancionero editor_cancionero.py
if errorlevel 1 (
  echo Error generando el EXE.
  pause
  exit /b 1
)

echo Listo. EXE generado en: dist\EditorCancionero.exe
pause
