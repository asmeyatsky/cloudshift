#!/usr/bin/env bash
# Add Cloud DNS A record for cloudshift.poc-searce.com pointing to the load balancer IP.
# LB is in emea-mas (sow-url-map); DNS zone is in infraappsandbox (poc-searce-com).

set -e

# LB project (where sow-url-map lives)
LB_PROJECT="${GCP_PROJECT_ID:-emea-mas}"
# DNS project and zone (from console: infraappsandbox, zone poc-searce-com)
DNS_PROJECT="${DNS_PROJECT:-infraappsandbox}"
DNS_ZONE="${DNS_ZONE:-poc-searce-com}"
RECORD_NAME="cloudshift.poc-searce.com."
URL_MAP_NAME="${URL_MAP_NAME:-sow-url-map}"
TTL="${DNS_TTL:-300}"

echo "LB project: $LB_PROJECT  DNS project: $DNS_PROJECT  Zone: $DNS_ZONE  Record: $RECORD_NAME"
echo ""

# --- Resolve LB IP (forwarding rule that uses the target proxy for sow-url-map) ---
echo "Resolving load balancer IP for URL map $URL_MAP_NAME..."
# Find target-https-proxy that uses this URL map
PROXY_NAME=$(gcloud compute target-https-proxies list --global --project="$LB_PROJECT" \
  --filter="urlMap~$URL_MAP_NAME" --format='value(name)' --limit=1 2>/dev/null || true)
if [[ -z "$PROXY_NAME" ]]; then
  # Try target-http-proxy
  PROXY_NAME=$(gcloud compute target-http-proxies list --global --project="$LB_PROJECT" \
    --filter="urlMap~$URL_MAP_NAME" --format='value(name)' --limit=1 2>/dev/null || true)
fi
if [[ -z "$PROXY_NAME" ]]; then
  echo "Could not find a target proxy for URL map $URL_MAP_NAME in $LB_PROJECT."
  echo "Get the LB IP manually: Network services > Load balancing > click the LB > copy IP."
  exit 1
fi
# Forwarding rule that uses this proxy (global, HTTPS typically port 443)
LB_IP=$(gcloud compute forwarding-rules list --global --project="$LB_PROJECT" \
  --filter="target~$PROXY_NAME" --format='value(IPAddress)' --limit=1 2>/dev/null || true)
if [[ -z "$LB_IP" ]]; then
  echo "Could not find forwarding rule IP for proxy $PROXY_NAME."
  exit 1
fi
echo "Load balancer IP: $LB_IP"
echo ""

# --- Create or update A record in Cloud DNS ---
if gcloud dns record-sets describe "$RECORD_NAME" --zone="$DNS_ZONE" --project="$DNS_PROJECT" &>/dev/null; then
  echo "Updating existing A record $RECORD_NAME -> $LB_IP..."
  gcloud dns record-sets update "$RECORD_NAME" \
    --zone="$DNS_ZONE" \
    --type=A \
    --ttl="$TTL" \
    --rrdatas="$LB_IP" \
    --project="$DNS_PROJECT"
  echo "Updated."
else
  echo "Creating A record $RECORD_NAME -> $LB_IP..."
  gcloud dns record-sets create "$RECORD_NAME" \
    --zone="$DNS_ZONE" \
    --type=A \
    --ttl="$TTL" \
    --rrdatas="$LB_IP" \
    --project="$DNS_PROJECT"
  echo "Created."
fi

echo ""
echo "Done. After DNS propagates, open https://cloudshift.poc-searce.com/"
