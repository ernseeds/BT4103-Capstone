# Windows PowerShell
$env:GCP_SA_JSON = gcloud secrets versions access latest --secret=GCP_SA_JSON
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000