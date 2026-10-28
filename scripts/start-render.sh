#!/bin/sh
set -eu
# The persistent disk is mounted at runtime, not during Render builds.
python -m flask --app run.py init-db
# One process keeps the in-memory limiter consistent for this single instance.
exec gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile - run:app
