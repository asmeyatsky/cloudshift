# Auth & IAP troubleshooting (cloudshift.poc-searce.com)

## "IAP / X-Searce-ID / Bearer or valid X-API-Key required" on load

You see this when the backend is in **searce_id** mode but the first request (often the WebSocket or an API call) has no valid auth.

**Quick fix (no IAP):**

1. **Deployer:** Set an API key and redeploy:
   - GitHub repo → Settings → Secrets and variables → Actions: add **CLOUDSHIFT_API_KEY** (same value as below).
   - Redeploy (push to `main` or re-run "Build and Deploy to Cloud Run").
2. **You:** In the Web UI, enter that API key in the sidebar under "API key" and blur the field (or press Tab). The app will use it for both HTTP and WebSocket.
3. **Optional:** Before opening the app, set it in the console so the very first request is authed:  
   `window.__CLOUDSHIFT_API_KEY__ = 'your-secret';` then open or reload the app.

**If you use IAP:** Open the app via the IAP URL (e.g. **https://cloudshift.poc-searce.com**) so the load balancer injects the JWT. Do not use the raw Cloud Run URL (*.run.app).

---

## Expected behavior when IAP is working

- Opening **https://cloudshift.poc-searce.com/** in a browser should **redirect to Google sign-in** (same as other Searce apps that use IAP).
- After you sign in with your Google account, you are allowed through and the CloudShift app loads. No login form inside the app.
- The backend is in **`auth_mode=searce_id`** and accepts the **`X-Goog-IAP-JWT-Assertion`** header that the load balancer injects after IAP authentication.

## If you never see a Google sign-in prompt

Then **IAP is not in the path** (or not enabled for this backend). The backend never receives an IAP JWT, so it returns **401** for API calls and the Web UI may fail or show as “not authenticated.”

### Checklist for deployer / infra

1. **IAP enabled for the CloudShift backend**
   - GCP Console → **Security** → **Identity-Aware Proxy** (project **emea-mas**).
   - Find **Backend services** → **cloudshift-backend**.
   - Toggle **ON** for that backend.
   - See [load-balancer-poc-searce.md](load-balancer-poc-searce.md#enable-iap-on-the-backend).

2. **Traffic path**
   - Confirm **https://cloudshift.poc-searce.com** goes to the **same** load balancer / backend that has IAP enabled (e.g. **cloudshift-backend** in **emea-mas**), not to another service or project.

3. **IAP access**
   - In IAP, add principals (e.g. your email or a Google Group) with role **IAP-secured Web App User** so they get the Google prompt and are allowed through.

4. **WebSocket**
   - `/ws/progress` also needs to go through the same path so the WebSocket upgrade request gets the IAP JWT (or is allowed by the proxy). If the proxy doesn’t forward WebSockets, the console will show WebSocket errors; the rest of the app can still work via HTTP polling.

## Workaround until IAP is fixed: use API key

If IAP cannot be enabled or fixed soon, the deployer can switch to **API key** auth so both the Web UI and the VS Code extension work without IAP:

1. **Backend**
   - Set `CLOUDSHIFT_AUTH_MODE=api_key`.
   - Set `CLOUDSHIFT_API_KEY=<a-strong-secret>` (e.g. `openssl rand -hex 32`).
   - Redeploy.

2. **Web UI**
   - Users (or deployer) inject the key so the UI can call the API:
     - In the browser console on the CloudShift page:  
       `window.__CLOUDSHIFT_API_KEY__ = 'same-secret';` then reload.
   - Or the deployer serves the front end with a small script that sets `window.__CLOUDSHIFT_API_KEY__` from an env var (do not commit the key).

3. **VS Code extension**
   - In VS Code settings (JSON):  
     `"cloudshift.apiKey": "same-secret"`  
     and `"cloudshift.serverUrl": "https://cloudshift.poc-searce.com"`.

Then everyone uses the same secret; no Google prompt. Prefer switching back to IAP (or another proper SSO) when possible.
