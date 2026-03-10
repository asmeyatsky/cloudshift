# Add CloudShift to existing *.poc-searce.com load balancer

One script creates the Cloud Run backend and adds **cloudshift.poc-searce.com** to the existing load balancer. The only manual step is **DNS**.

**Load balancer:** [sow-url-map](https://console.cloud.google.com/net-services/loadbalancing/details/http/sow-url-map?project=emea-mas) in project **emea-mas**.

## Prerequisites

- **gcloud** authenticated with project **emea-mas** (or set `GCP_PROJECT_ID=emea-mas`).
- **Python with PyYAML** (`pip install pyyaml`) or **Ruby** (YAML in stdlib) — needed to patch the URL map.
- Cloud Run service **cloudshift** deployed in **emea-mas**. If you deploy via [deploy-cloudrun](.github/workflows/deploy-cloudrun.yaml) to another project, deploy CloudShift to emea-mas first (e.g. set `GCP_PROJECT_ID=emea-mas` in the workflow or run deploy manually to emea-mas).
- **SSL certificate** on the load balancer that includes **cloudshift.poc-searce.com** (see [SSL certificate](#ssl-certificate) below). If you see `certificate verify failed: Hostname mismatch`, the cert does not yet cover this host.

## Where to run the script

Run it on any machine where **gcloud** is installed and authenticated with access to project **emea-mas** (e.g. your laptop or [Google Cloud Shell](https://shell.cloud.google.com)). Cloud Shell already has gcloud; you may need `pip install pyyaml` if the script uses Python to patch the URL map.

## Run the script (does everything)

From the **repo root** (directory that contains `deploy/`):

```bash
chmod +x deploy/gcp/add-cloudshift-to-lb.sh
./deploy/gcp/add-cloudshift-to-lb.sh
```

Defaults: project **emea-mas**, URL map **sow-url-map**, host **cloudshift.poc-searce.com**. Override if needed:

```bash
GCP_PROJECT_ID=emea-mas URL_MAP_NAME=sow-url-map LB_HOST=cloudshift.poc-searce.com ./deploy/gcp/add-cloudshift-to-lb.sh
```

The script will:

1. Create serverless NEG **cloudshift-neg** for the Cloud Run service (region `us-central1`).
2. Create global backend service **cloudshift-backend** and attach the NEG.
3. Export **sow-url-map**, add a host rule for **cloudshift.poc-searce.com** → **cloudshift-backend**, and re-import the URL map.

If the host is already in the URL map, the script skips the patch. Re-running is safe (idempotent).

## SSL certificate

The load balancer’s **HTTPS front-end** must use an SSL certificate that is valid for **cloudshift.poc-searce.com**. If the cert only lists other hosts (e.g. auto-sow.poc-searce.com), browsers and the propagation checker will report **Hostname mismatch** or **certificate verify failed**.

**Add cloudshift.poc-searce.com to the certificate:**

1. Open the load balancer in **emea-mas**: [sow-url-map](https://console.cloud.google.com/net-services/loadbalancing/details/http/sow-url-map?project=emea-mas).
2. Click **Edit** → **Frontend configuration**.
3. Open the HTTPS frontend (port 443) and check which **Certificate** is attached.
4. **Google-managed certificate:**  
   - In [Certificates](https://console.cloud.google.com/net-services/loadbalancing/advanced/ssl-certificates/list?project=emea-mas), open the cert (or create a new one).  
   - Add **cloudshift.poc-searce.com** to the domain list (or use a cert that already has `*.poc-searce.com`).  
   - Google will provision/renew the cert (often **~20 minutes**); ensure DNS for cloudshift.poc-searce.com points to the LB IP so validation can succeed.
5. **Self-managed certificate:**  
   - Obtain a new cert that includes **cloudshift.poc-searce.com** (or a wildcard `*.poc-searce.com`), then upload it in **Certificates** and attach it to the HTTPS frontend (or add it as an extra cert and select it for the frontend).

After the cert includes cloudshift.poc-searce.com and is attached to the LB frontend, HTTPS to **https://cloudshift.poc-searce.com/** will validate correctly.

## Enable IAP on the backend

To require Google sign-in for **https://cloudshift.poc-searce.com/** (same idea as auto-sow):

### 1. Turn on IAP for the backend service

**Console (recommended):**

1. Open **Security** → **Identity-Aware Proxy**:  
   [IAP – emea-mas](https://console.cloud.google.com/security/iap?project=emea-mas)
2. In the list, find the row for **Backend services** / **cloudshift-backend** (resource type “Backend service”, name “cloudshift-backend”).
3. Turn **ON** the toggle for that row.  
   If you don’t see **cloudshift-backend**, use the filter or open **Backend services** in the left menu and select **cloudshift-backend**, then look for the IAP toggle.
4. When prompted, confirm **Enable** for the backend service.

**gcloud:**

```bash
gcloud iap web enable \
  --resource-type=backend-services \
  --service=cloudshift-backend \
  --project=emea-mas
```

### 2. Restrict who can access the app

1. On the same [IAP page](https://console.cloud.google.com/security/iap?project=emea-mas), click **cloudshift-backend** (or the **Backend services** group).
2. Click **Add principal** (or **Manage access**).
3. Add the users or groups that should be allowed (e.g. `your@email.com` or a Google Group). Role: **IAP-secured Web App User**.
4. Save. Only those principals will get past the Google sign-in; others will see “Access denied”.

After this, opening **https://cloudshift.poc-searce.com/** in a browser will redirect to Google sign-in, then show the app if the user is allowed.

## After running the script: DNS

DNS for **poc-searce.com** is in Google Cloud: zone **poc-searce-com**, project **infraappsandbox** ([Console](https://console.cloud.google.com/net-services/dns/zones/poc-searce-com/details?project=infraappsandbox)).

Run the DNS script to add an A record for **cloudshift.poc-searce.com** pointing to the load balancer’s IP (it discovers the LB IP from **emea-mas** and creates/updates the record in **infraappsandbox**):

```bash
chmod +x deploy/gcp/add-cloudshift-dns.sh
./deploy/gcp/add-cloudshift-dns.sh
```

Defaults: LB project **emea-mas**, DNS project **infraappsandbox**, zone **poc-searce-com**. Override if needed:

```bash
GCP_PROJECT_ID=emea-mas DNS_PROJECT=infraappsandbox DNS_ZONE=poc-searce-com ./deploy/gcp/add-cloudshift-dns.sh
```

You need **gcloud** authenticated with access to both **emea-mas** (to read the LB IP) and **infraappsandbox** (to edit the zone).

### Check when DNS propagation works

Use the propagation checker to verify that **cloudshift.poc-searce.com** resolves and (optionally) that the app URL returns 2xx:

```bash
# One-off check (from repo root)
python3 deploy/gcp/check_dns_propagated.py --host cloudshift.poc-searce.com --url https://cloudshift.poc-searce.com/

# Optional: require DNS to match the LB IP (paste the IP from add-cloudshift-dns.sh output)
python3 deploy/gcp/check_dns_propagated.py --host cloudshift.poc-searce.com --expected-ip 34.120.x.x --url https://cloudshift.poc-searce.com/

# Poll until propagation succeeds (default 20 min timeout; DNS/cert can take that long)
python3 deploy/gcp/check_dns_propagated.py --host cloudshift.poc-searce.com --url https://cloudshift.poc-searce.com/ --wait

# If the LB cert doesn't yet include cloudshift.poc-searce.com (hostname mismatch), use --insecure to only check that the app responds (skip SSL verify)
python3 deploy/gcp/check_dns_propagated.py --host cloudshift.poc-searce.com --url https://cloudshift.poc-searce.com/ --insecure
```

Run tests for the checker: `pytest tests/deploy/test_check_dns_propagated.py -v`.

DNS and SSL cert updates often take **around 20 minutes** to propagate. The checker’s `--wait` mode defaults to a 20-minute timeout. After propagation, open **https://cloudshift.poc-searce.com/**.

## Optional: Restrict Cloud Run ingress

To ensure traffic only reaches CloudShift via the load balancer (and not the default `*.run.app` URL), set the Cloud Run service to accept **Internal and Cloud Load Balancing** only:

```bash
gcloud run services update cloudshift \
  --region=us-central1 \
  --ingress=internal-and-cloud-load-balancing \
  --project=emea-mas
```

Then only the LB (and internal traffic) can reach the service; the public `https://cloudshift-….run.app` URL will stop working.
