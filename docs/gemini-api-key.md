# Getting and securing a Gemini API key

CloudShift **demo mode** uses Google’s Gemini API for LLM-assisted migrations. You need an API key only when running with **`deployment_mode=demo`**.

---

## 1. Create a Gemini API key

1. Open **Google AI Studio**: https://aistudio.google.com/
2. Sign in with your Google account.
3. In the left sidebar, click **“Get API key”** (or go to https://aistudio.google.com/apikey).
4. Click **“Create API key”**.
5. Choose an existing Google Cloud project or create one (e.g. “CloudShift Demo”).
6. Copy the key. It looks like: `AIzaSy...` (about 39 characters).

**Free tier**: Google AI Studio offers a free tier with rate limits; suitable for demos and light use.

---

## 2. Store the key securely (never commit it)

### Recommended: GitHub Secrets

Store the Gemini key in **GitHub Secrets** so it never appears in code or logs. Use it in CI (e.g. deploy workflows) and, if you deploy from GitHub, pass it into your runtime as an env var.

1. In your repo: **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `GEMINI_API_KEY` (or `CLOUDSHIFT_GEMINI_API_KEY`).
4. Value: paste your `AIzaSy...` key and save.

**In your workflow** (e.g. deploy to Cloud Run, or any environment), set the env var from the secret:

```yaml
env:
  CLOUDSHIFT_DEPLOYMENT_MODE: demo
  CLOUDSHIFT_GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

Your app then reads `CLOUDSHIFT_GEMINI_API_KEY` from the environment. Never echo or log the secret.

**Example (Cloud Run deploy):** In `.github/workflows/deploy-cloudrun.yaml`, add the secret to the deploy step:

```yaml
--set-env-vars=CLOUDSHIFT_DEPLOYMENT_MODE=demo,CLOUDSHIFT_GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }} \
```

(Add repository secret `GEMINI_API_KEY` in GitHub **Settings → Secrets and variables → Actions**.)

### Local / dev

- Create or edit **`.env`** in the CloudShift project root (the file is in `.gitignore`).
- Add:
  ```bash
  CLOUDSHIFT_DEPLOYMENT_MODE=demo
  CLOUDSHIFT_GEMINI_API_KEY=AIzaSy...your-key...
  ```
- Do **not** commit `.env` or paste the key into docs or code.

### Alternative: Google Secret Manager (GCP)

If you deploy on GCP and prefer to keep the key there:

- Create a secret: `gcloud secrets create GEMINI_API_KEY --data-file=-` (paste key, then Ctrl+D).
- In Cloud Run (or other GCP runtime), reference it as env var `CLOUDSHIFT_GEMINI_API_KEY`.

---

## 3. Enable demo mode

In `.env` (or your environment):

```bash
# Use Gemini for LLM (demo)
CLOUDSHIFT_DEPLOYMENT_MODE=demo
CLOUDSHIFT_GEMINI_API_KEY=AIzaSy...your-key...

# Optional: use a specific model
# CLOUDSHIFT_GEMINI_MODEL=gemini-1.5-flash
```

Restart the app. The sidebar will show **“Demo (Gemini)”** when the UI calls `/api/auth/mode`.

---

## 4. If the key is leaked

1. In Google AI Studio (or Google Cloud Console → APIs & Services → Credentials), **revoke/delete** the leaked key.
2. Create a **new** API key and update it only in your secure storage (e.g. GitHub Secrets or `.env`).
3. Rotate any other secrets that might have been stored in the same place.

---

## 5. Optional: restrict the key (Google Cloud)

If you created the key in a Google Cloud project:

- Use **API key restrictions** (Console → APIs & Services → Credentials → your API key):
  - Restrict to “API restrictions” and select only “Generative Language API”.
  - Optionally add application restrictions (e.g. IP or HTTP referrer for a specific front end).

This limits what the key can call and where it can be used.
