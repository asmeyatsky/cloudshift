# CI: Deploy to Cloud Run on Push

The GitHub Action [../.github/workflows/deploy-cloudrun.yaml](../.github/workflows/deploy-cloudrun.yaml) builds the CloudShift image and deploys it to Google Cloud Run on every push to `main` or `master`.

## One-time setup

CI uses the existing **Cloud Refactor Agent** service account. Ensure it has the required roles, then create a key and store it in GitHub.

### 1. Grant roles to Cloud Refactor Agent (if not already present)

Use the service account email for "Cloud Refactor Agent" (e.g. `cloud-refactor-agent@refactord-479213.iam.gserviceaccount.com` — confirm in **IAM & Admin → Service Accounts**). Then:

```bash
# Replace with your Cloud Refactor Agent SA email if different
export SA="cloud-refactor-agent@refactord-479213.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding refactord-479213 \
  --member="serviceAccount:${SA}" \
  --role="roles/cloudbuild.builds.builder"

gcloud projects add-iam-policy-binding refactord-479213 \
  --member="serviceAccount:${SA}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding refactord-479213 \
  --member="serviceAccount:${SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding refactord-479213 \
  --member="serviceAccount:${SA}" \
  --role="roles/iam.serviceAccountUser"
```

### 2. Create a JSON key and add it to GitHub Secrets

```bash
# Use the Cloud Refactor Agent SA email (adjust if your SA id differs)
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=cloud-refactor-agent@refactord-479213.iam.gserviceaccount.com \
  --project=refactord-479213
```

1. In your GitHub repo: **Settings → Secrets and variables → Actions**.
2. **New repository secret**
3. Name: `GCP_SA_KEY`
4. Value: paste the entire contents of `github-actions-key.json`
5. Delete the local file: `rm github-actions-key.json`

### 3. Push to trigger

Push to the `main` (or `master`) branch. The workflow will:

1. Build the image on Cloud Build (tag: `sha-<short-sha>`)
2. Push to Artifact Registry
3. Deploy the new image to Cloud Run

## Optional: Use a different project or branch

Edit the `env` and `on` sections in [../.github/workflows/deploy-cloudrun.yaml](../.github/workflows/deploy-cloudrun.yaml):

- `GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_RUN_SERVICE` for your project/region/service name.
- `on.push.branches` to run on other branches (e.g. `release`).

## Security note

For production, prefer [Workload Identity Federation](https://github.com/google-github-actions/auth#setting-up-workload-identity-federation) so you don’t store a long-lived key in GitHub. The workflow can be updated to use `workload_identity_provider` and `service_account` instead of `credentials_json`.
