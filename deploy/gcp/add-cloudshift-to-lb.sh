#!/usr/bin/env bash
# One-shot: create Cloud Run backend (NEG + backend service) and add
# cloudshift.poc-searce.com to the existing sow-url-map load balancer.
# Requires: gcloud, and Python (with PyYAML) or Ruby for editing the URL map YAML.

set -e

# Load balancer sow-url-map lives in emea-mas
PROJECT="${GCP_PROJECT_ID:-emea-mas}"
REGION="${GCP_REGION:-us-central1}"
CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-cloudshift}"
URL_MAP_NAME="${URL_MAP_NAME:-sow-url-map}"
LB_HOST="${LB_HOST:-cloudshift.poc-searce.com}"

NEG_NAME="cloudshift-neg"
BACKEND_NAME="cloudshift-backend"
PATH_MATCHER_NAME="cloudshift"

BACKEND_SERVICE_URL="https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/backendServices/${BACKEND_NAME}"

echo "Project: $PROJECT  Region: $REGION  URL map: $URL_MAP_NAME  Host: $LB_HOST"
echo ""

# --- 1. Serverless NEG for Cloud Run ---
if gcloud compute network-endpoint-groups describe "$NEG_NAME" --region="$REGION" --project="$PROJECT" &>/dev/null; then
  echo "[1/4] NEG $NEG_NAME already exists."
else
  echo "[1/4] Creating NEG $NEG_NAME..."
  gcloud compute network-endpoint-groups create "$NEG_NAME" \
    --region="$REGION" \
    --network-endpoint-type=serverless \
    --cloud-run-service="$CLOUD_RUN_SERVICE" \
    --project="$PROJECT"
  echo "      Created NEG: $NEG_NAME"
fi

# --- 2. Global backend service ---
if gcloud compute backend-services describe "$BACKEND_NAME" --global --project="$PROJECT" &>/dev/null; then
  echo "[2/4] Backend service $BACKEND_NAME already exists."
else
  echo "[2/4] Creating backend service $BACKEND_NAME..."
  gcloud compute backend-services create "$BACKEND_NAME" \
    --load-balancing-scheme=EXTERNAL \
    --global \
    --project="$PROJECT"
  echo "      Created backend service: $BACKEND_NAME"
fi

# --- 3. Attach NEG to backend ---
if gcloud compute backend-services describe "$BACKEND_NAME" --global --project="$PROJECT" --format='value(backends[].group)' 2>/dev/null | grep -q "$NEG_NAME"; then
  echo "[3/4] NEG already attached to $BACKEND_NAME."
else
  echo "[3/4] Attaching NEG to backend service..."
  gcloud compute backend-services add-backend "$BACKEND_NAME" \
    --global \
    --network-endpoint-group="$NEG_NAME" \
    --network-endpoint-group-region="$REGION" \
    --project="$PROJECT"
  echo "      Attached NEG to $BACKEND_NAME."
fi

# --- 4. Add host rule to URL map ---
echo "[4/4] Updating URL map $URL_MAP_NAME for host $LB_HOST..."

EXPORT_FILE=$(mktemp)
trap 'rm -f "$EXPORT_FILE"' EXIT

gcloud compute url-maps export "$URL_MAP_NAME" \
  --destination="$EXPORT_FILE" \
  --global \
  --project="$PROJECT"

# Skip if host rule already present
if grep -qF "$LB_HOST" "$EXPORT_FILE" 2>/dev/null; then
  echo "      Host $LB_HOST already in URL map; skipping patch."
  exit 0
fi

if python3 -c "import yaml" 2>/dev/null; then
  python3 - "$EXPORT_FILE" "$BACKEND_SERVICE_URL" "$LB_HOST" "$PATH_MATCHER_NAME" << 'PY'
import sys, yaml
path, backend_url, host, path_matcher = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f:
    d = yaml.safe_load(f)
d.setdefault("hostRules", []).append({"hosts": [host], "pathMatcher": path_matcher})
d.setdefault("pathMatchers", []).append({"name": path_matcher, "defaultService": backend_url})
with open(path, "w") as f:
    yaml.dump(d, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
PY
elif command -v ruby &>/dev/null; then
  ruby -r yaml -e "
    d = YAML.load_file('$EXPORT_FILE')
    d['hostRules'] ||= []
    d['hostRules'] << {'hosts' => ['$LB_HOST'], 'pathMatcher' => '$PATH_MATCHER_NAME'}
    d['pathMatchers'] ||= []
    d['pathMatchers'] << {'name' => '$PATH_MATCHER_NAME', 'defaultService' => '$BACKEND_SERVICE_URL'}
    File.write('$EXPORT_FILE', d.to_yaml)
  "
else
  echo "      Error: need Python (with PyYAML) or Ruby to patch the URL map. Install with: pip install pyyaml"
  echo "      Export saved at: $EXPORT_FILE"
  echo "      Add manually: host $LB_HOST -> pathMatcher $PATH_MATCHER_NAME, pathMatchers entry with defaultService $BACKEND_SERVICE_URL"
  exit 1
fi

gcloud compute url-maps import "$URL_MAP_NAME" \
  --source="$EXPORT_FILE" \
  --global \
  --project="$PROJECT"

echo "      URL map updated: $LB_HOST -> $BACKEND_NAME"
echo ""
echo "Done. Next: add DNS so $LB_HOST points to this load balancer's IP (the same LB that serves auto-sow; host routing sends traffic to the CloudShift backend)."
echo "Then open https://$LB_HOST/"
