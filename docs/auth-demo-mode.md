# Auth: Demo mode (Searce ID) and API key

When the backend is configured with **`auth_mode=searce_id`** (demo) or **`auth_mode=api_key`**, you must send a valid credential with each request.

## API key (`auth_mode=api_key`)

- **Header**: `X-API-Key: <your-key>`
- Set the key in backend `.env`: `CLOUDSHIFT_API_KEY=your-secret-key`
- For the **web UI** (e.g. local dev), you can inject the key so the UI sends it on every request:
  - In the browser console: `window.__CLOUDSHIFT_API_KEY__ = 'your-key';` then reload.
  - Or serve the app with a small script that sets `window.__CLOUDSHIFT_API_KEY__` from an env var (never commit this key).
- **Production**: Prefer password auth (`auth_mode=password`) and user login instead of a single shared API key.

## Demo / Searce ID (`auth_mode=searce_id`)

- **Option 1 – header**: `X-Searce-ID: <token>`
- **Option 2 – Bearer**: `Authorization: Bearer <token>`
- The backend accepts either header and does not validate the token format (integration with your identity provider is left to you).
- To use from the **web UI**, set the token the same way as the API key, e.g.:
  - `window.__CLOUDSHIFT_API_KEY__ = 'your-searce-token';` (the UI sends it as `X-API-Key` today; for Bearer you’d need a separate demo-token flow or use a proxy that adds `Authorization: Bearer`).

## Getting a token for demo

- If using **Searce ID**: Obtain the token from your Searce ID / SSO integration (e.g. OAuth callback or CLI).
- If using **API key** for demo: Generate a strong secret (e.g. `openssl rand -hex 32`) and set `CLOUDSHIFT_API_KEY` and `auth_mode=api_key` in the backend; then set `window.__CLOUDSHIFT_API_KEY__` in the client as above for the UI.
