#!/usr/bin/env bash
# Single script: Cloud Run check, NEG + backend + URL map, SSL cert, IAP for cloudshift.poc-searce.com.
# Run from repo root. Requires: gcloud, Python+PyYAML or Ruby, access to emea-mas.

set -e

PROJECT="${GCP_PROJECT_ID:-emea-mas}"
REGION="${GCP_REGION:-us-central1}"
CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-cloudshift}"
URL_MAP_NAME="${URL_MAP_NAME:-sow-url-map}"
LB_HOST="${LB_HOST:-cloudshift.poc-searce.com}"
SSL_CERT_NAME="${SSL_CERT_NAME:-cloudshift-poc-searce-com}"
BACKEND_NAME="cloudshift-backend"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== 1. Check Cloud Run in $PROJECT ==="
if ! gcloud run services describe "$CLOUD_RUN_SERVICE" --region="$REGION" --project="$PROJECT" --format="value(status.url)" &>/dev/null; then
  echo "Cloud Run service '$CLOUD_RUN_SERVICE' not found in $PROJECT. Deploy it first (e.g. GCP_PROJECT_ID=$PROJECT)."
  exit 1
fi
echo "OK"
echo ""

echo "=== 2. NEG + backend + URL map ==="
GCP_PROJECT_ID="$PROJECT" GCP_REGION="$REGION" URL_MAP_NAME="$URL_MAP_NAME" LB_HOST="$LB_HOST" \
  "$SCRIPT_DIR/add-cloudshift-to-lb.sh"
echo ""

echo "=== 3. SSL cert for $LB_HOST ==="
if ! gcloud compute ssl-certificates describe "$SSL_CERT_NAME" --global --project="$PROJECT" &>/dev/null; then
  gcloud compute ssl-certificates create "$SSL_CERT_NAME" \
    --domains="$LB_HOST" \
    --global \
    --project="$PROJECT"
  echo "Created. Provisioning may take ~20 min; DNS must point to LB."
else
  echo "Cert $SSL_CERT_NAME already exists."
fi
PROXY_NAME=$(gcloud compute target-https-proxies list --global --project="$PROJECT" --filter="urlMap~$URL_MAP_NAME" --format='value(name)' --limit=1)
if [[ -n "$PROXY_NAME" ]]; then
  CURRENT=$(gcloud compute target-https-proxies describe "$PROXY_NAME" --global --project="$PROJECT" --format='value(sslCertificates)' | tr ';' ',')
  NEW_CERT="https://www.googleapis.com/compute/v1/projects/${PROJECT}/global/sslCertificates/${SSL_CERT_NAME}"
  if [[ "$CURRENT" != *"$SSL_CERT_NAME"* ]]; then
    CERT_LIST="${CURRENT:+${CURRENT},}${NEW_CERT}"
    gcloud compute target-https-proxies update "$PROXY_NAME" \
      --ssl-certificates="$CERT_LIST" \
      --global \
      --project="$PROJECT"
    echo "Attached cert to proxy $PROXY_NAME"
  else
    echo "Cert already on proxy."
  fi
else
  echo "No target-https-proxy found for $URL_MAP_NAME; attach cert $SSL_CERT_NAME to the LB frontend in Console."
fi
echo ""

echo "=== 4. IAP on $BACKEND_NAME ==="
if gcloud iap web enable --resource-type=backend-services --service="$BACKEND_NAME" --project="$PROJECT" 2>/dev/null; then
  echo "IAP enabled. Add users in Console: https://console.cloud.google.com/security/iap?project=$PROJECT"
else
  echo "IAP enable skipped or failed. Turn on in Console: Backend services > $BACKEND_NAME > Identity-Aware Proxy"
fi
echo ""
echo "Done. Allow ~20 min for SSL. Then: https://$LB_HOST/"
