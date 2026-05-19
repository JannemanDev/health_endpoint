@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
	echo Virtual environment not found. Run install_deps.bat first.
	exit /b 1
)

call ".venv\Scripts\activate.bat"
