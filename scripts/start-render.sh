#!/bin/sh
set -eu
# Initialize the external database and image bucket before accepting traffic.
python -m flask --app run.py init-db
python -m flask --app run.py init-storage
# One process keeps the in-memory limiter consistent for this single instance.
exec gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile - run:app
