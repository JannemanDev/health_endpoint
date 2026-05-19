@echo off
setlocal
cd /d "%~dp0"

set "VENV_DIR=.venv"

where python >nul 2>&1
if errorlevel 1 (
	echo ERROR: python not found in PATH
	exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
	if exist "%VENV_DIR%" (
		echo Removing incomplete virtual environment at %VENV_DIR%
		rmdir /s /q "%VENV_DIR%"
	)
	echo Creating virtual environment in %VENV_DIR%
	python -m venv "%VENV_DIR%"
)

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt

echo.
echo Dependencies installed.
echo Activate the venv in CMD with:  call activate_venv.bat
echo Activate the venv in PowerShell with:  .\.venv\Scripts\Activate.ps1
