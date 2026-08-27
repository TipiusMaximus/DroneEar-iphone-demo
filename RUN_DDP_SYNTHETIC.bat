@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements-benchmark.txt
python tools\generate_synthetic.py
python tools\build_benchmark.py --profile synthetic
python -m pytest -q
python -m ddp_experiment.run_experiment --output outputs/ddp_experiment

echo.
echo Finished. Open outputs\ddp_experiment\DDP_EXPERIMENT_REPORT.md
pausE
