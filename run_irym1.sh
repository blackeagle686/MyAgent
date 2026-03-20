#!/bin/bash
export PYTHONPATH=$(pwd)
source .venv/bin/activate
echo "Starting IRYM1 FastAPI Server on http://127.0.0.1:8000/irym1/ ..."
python -m uvicorn apps.irym_1.irym_1:app --host 127.0.0.1 --port 8000 --reload
