#!/bin/sh
set -e
alembic upgrade head
python -m app.data.benchmark_cases_seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
