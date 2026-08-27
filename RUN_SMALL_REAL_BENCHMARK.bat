@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements-benchmark.txt
python tools\run_all.py --profile small-real
echo.
echo Finished. Open outputs\small_real\summary.md
pause
