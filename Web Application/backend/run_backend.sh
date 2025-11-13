#!/usr/bin/env bash
set -euo pipefail
export GCP_SA_JSON="$(gcloud secrets versions access latest --secret=GCP_SA_JSON)"
uvicorn app:app --reload --host 0.0.0.0 --port 8000