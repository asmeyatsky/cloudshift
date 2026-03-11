# Running the pipeline on 5k–10k lines of AWS and Azure code

This describes how to run the full CloudShift pipeline (import → scan → plan → apply → validate) on real AWS and Azure sample repositories (~5,000–10,000+ lines each).

## What runs

1. **Import (from-git)**  
   Two repos are cloned into `/tmp/cloudshift`:
   - **AWS:** [aws-samples/aws-cdk-examples](https://github.com/aws-samples/aws-cdk-examples) (CDK examples in TypeScript/Python/etc.)
   - **Azure:** [Azure/azure-quickstart-templates](https://github.com/Azure/azure-quickstart-templates) (ARM/Bicep templates)

2. **Scan**  
   Each project root is scanned with `source_provider` AWS or AZURE and `target_provider` GCP. Results are stored so Plan can use them (manifest persistence).

3. **Plan → Apply → Validate**  
   For each project, the script runs plan (using the stored manifest), then apply, then validate, and prints a short summary.

## Prerequisites

- CloudShift API server running (e.g. `uvicorn cloudshift.presentation.api.app:app --reload` from project root, or your deploy).
- Git installed (required for `POST /api/projects/from-git`).
- Python 3 (stdlib only; no extra packages).

## Run

From the project root:

```bash
# Start the API server in another terminal, then:
python scripts/run_pipeline_e2e.py
```

Optional env vars:

- `CLOUDSHIFT_BASE_URL` – default `http://localhost:8000`.
- `CLOUDSHIFT_API_KEY` – if auth is `api_key`.
- `CLOUDSHIFT_BEARER_TOKEN` – if using Bearer auth.

Example:

```bash
CLOUDSHIFT_BASE_URL=http://localhost:8000 python scripts/run_pipeline_e2e.py
```

## Output

You’ll see import paths, then for each repo (AWS and Azure) a short summary of scan (files scanned, files with findings), plan (steps, plan_id), apply (files modified, success), and validate (passed, issues). Any backend error is printed and stored in the summary.

## Manifest persistence (plan after scan)

For Plan to see the scan result, the UI (and this script) send `project_id` in the scan request. The backend then stores the scan result in the DB under that project id. Plan is called with `manifest_id = project_id`, so `get_manifest(manifest_id)` returns the stored manifest and the pipeline runs end-to-end.
