#!/bin/sh
set -eu

echo "Starting Plattenradar API on 0.0.0.0:8000"
python -c "import music_review.api.app as api_module; print('Loaded API app:', api_module.app.title)"

exec python -m uvicorn music_review.api.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
