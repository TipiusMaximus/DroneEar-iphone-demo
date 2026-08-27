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
python tools\build_benchmark.py --profile small-real
python -m pytest -q
python -m ddp_experiment.run_experiment_v02 --output outputs/ddp_v02_real_only --exclude-synthetic
python -m ddp_experiment.run_experiment_v02 --output outputs/ddp_v02_real_only_raw --exclude-synthetic --no-normalize
echo.
echo Finished.
echo Normalized: outputs\ddp_v02_real_only\DDP_V02_EXPERIMENT_REPORT.md
echo Raw-scale:  outputs\ddp_v02_real_only_raw\DDP_V02_EXPERIMENT_REPORT.md
pause
