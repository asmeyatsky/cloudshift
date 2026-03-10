# Load balancer + IAP (single script)

From repo root:

```bash
chmod +x deploy/gcp/setup-lb-and-iap.sh
./deploy/gcp/setup-lb-and-iap.sh
```

**Requires:** Cloud Run **cloudshift** already deployed in **emea-mas** (deploy there first if you only use refactord-479213). Allow ~20 min for SSL cert provisioning. Add IAP users in Console if the script enables IAP.
