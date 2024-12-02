@echo off
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
python "%SCRIPT_DIR%printegrate.py" %1
call "%SCRIPT_DIR%venv\Scripts\deactivate.bat"