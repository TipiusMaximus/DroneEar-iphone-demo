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
python tools\build_distance_benchmark.py
python -m pytest -q
python -m ddp_experiment.run_experiment_v02 --manifest data/distance_benchmark/manifest.csv --output outputs/ddp_v02_distance
python -m ddp_experiment.run_experiment_v02 --manifest data/distance_benchmark/manifest.csv --output outputs/ddp_v02_distance_raw --no-normalize
echo.
echo Finished.
echo Normalized: outputs\ddp_v02_distance\DDP_V02_EXPERIMENT_REPORT.md
echo Raw-scale:  outputs\ddp_v02_distance_raw\DDP_V02_EXPERIMENT_REPORT.md
pause
