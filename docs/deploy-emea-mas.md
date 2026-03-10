# Deploy CloudShift to emea-mas

Deployments target **emea-mas** so the load balancer (sow-url-map) and IAP can use the same project.

## 1. Service account in emea-mas

Create a dedicated SA for GitHub Actions (one-time):

```bash
PROJECT=emea-mas
SA_NAME=github-cloudshift-deploy
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
  --display-name="GitHub CloudShift Deploy" \
  --project=$PROJECT

# Artifact Registry + Cloud Run
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Key for GitHub Secrets
gcloud iam service-accounts keys create key-emea-mas.json \
  --iam-account=$SA_EMAIL \
  --project=$PROJECT
```

Add the **contents** of `key-emea-mas.json` as GitHub secret **GCP_SA_KEY** (overwrite the refactord key if you’re fully moving). Delete the file after: `rm key-emea-mas.json`.

## 2. Artifact Registry in emea-mas

Create the repo if it doesn’t exist:

```bash
gcloud artifacts repositories create cloudshift \
  --repository-format=docker \
  --location=us-central1 \
  --project=emea-mas
```

## 3. Workflow

The workflow is set to **emea-mas** by default. Push to `main`/`master` to build and deploy. No new secrets beyond **GCP_SA_KEY** (and optional **GEMINI_API_KEY**).
