# Enable refactoring (Azure/AWS → GCP)

Refactoring in the **UI** and **VS Code** uses an LLM (Gemini). Without it you get "No refactoring changes" or a 503.

## One-time setup

1. **Get a Gemini API key** (free): https://aistudio.google.com/apikey  
2. **Set it on Cloud Run** (replace `YOUR_GEMINI_KEY` with your key):

```bash
gcloud run services update cloudshift --region=us-central1 --project=emea-mas \
  --update-env-vars="CLOUDSHIFT_GEMINI_API_KEY=YOUR_GEMINI_KEY"
```

The service already has `CLOUDSHIFT_DEPLOYMENT_MODE=demo`; adding the key enables refactor.

## Azure Python → GCP

Use **Refactor Selection** or **Refactor File** on Azure code; the backend will refactor to GCP (e.g. `google-cloud-*` SDKs). You can also set the project source to Azure in the UI before Plan/Apply.
