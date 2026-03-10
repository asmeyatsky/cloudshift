# CloudShift Demo and Production Image

**One Docker image** is used for both demo and production. Long-term, CloudShift is deployed on client site (on-prem or air-gapped) as this same image. For demos, run the same image locally with Docker or on any Kubernetes cluster.

---

## Building the image

From the repo root:

```bash
docker build -t cloudshift:0.1.0 -f docker/Dockerfile .
```

Tag and push to your registry when needed:

```bash
docker tag cloudshift:0.1.0 <your-registry>/cloudshift:0.1.0
docker push <your-registry>/cloudshift:0.1.0
```

---

## Demo: run with Docker

Same image, no Kubernetes required:

```bash
docker run -d --name cloudshift \
  -p 8000:8000 \
  -v cloudshift-data:/app/data \
  -e CLOUDSHIFT_LLM_ENABLED=false \
  -e CLOUDSHIFT_DATA_DIR=/app/data \
  cloudshift:0.1.0
```

- **Web UI & API:** http://localhost:8000  
- Data is stored in the named volume `cloudshift-data` (persists across container restarts).

To use an image from your registry, replace `cloudshift:0.1.0` with `<your-registry>/cloudshift:0.1.0`.

---

## Demo: deploy to Cloud Run

The same image runs on **Google Cloud Run**. The container listens on the port given by the `PORT` environment variable (Cloud Run sets this, e.g. 8080); if unset, it defaults to 8000.

1. Build and push the image to **Artifact Registry** (e.g. `us-central1-docker.pkg.dev/PROJECT/cloudshift:0.1.0`).
2. Create a Cloud Run service from that image. Set env vars as needed (e.g. `CLOUDSHIFT_LLM_ENABLED=false`). No need to set `PORT` — Cloud Run injects it.
3. **Note:** Cloud Run’s filesystem is ephemeral. Data in `/app/data` (SQLite, uploaded projects) is lost when the instance scales to zero or is replaced. Fine for short demos; for persistent state you’d need a different backend or keep the service always allocated.

```bash
# Example: deploy to Cloud Run (after pushing image to Artifact Registry)
gcloud run deploy cloudshift-demo \
  --image us-central1-docker.pkg.dev/PROJECT/cloudshift:0.1.0 \
  --region us-central1 \
  --platform managed \
  --set-env-vars CLOUDSHIFT_LLM_ENABLED=false \
  --allow-unauthenticated
```

---

## Demo: run on any Kubernetes

Use the minimal Kubernetes manifest for a quick demo on **any** cluster (GKE, EKS, AKS, on-prem, etc.):

1. **Build and push** the image to a registry your cluster can pull from (e.g. Artifact Registry, ECR, ACR, or an in-cluster registry).

2. **Deploy** using the standalone manifest (no Helm):

   ```bash
   # If your image is not cloudshift:0.1.0, edit the Deployment image in
   # deploy/kubernetes-demo.yaml, then:
   kubectl apply -f deploy/kubernetes-demo.yaml
   ```

3. **Access** the app (no Ingress by default):

   ```bash
   kubectl port-forward svc/cloudshift-demo 8000:80
   ```

   Open http://localhost:8000

The demo manifest uses an **emptyDir** for `/app/data` (state does not persist across pod restarts). For persistent state, replace the `emptyDir` volume with a PVC or use the full Helm chart.

---

## Production / client-site deployment

- **Same image.** Ship the image to the client (e.g. via `docker save`/`docker load` for air-gapped) or push to their registry.
- **Deploy on their Kubernetes** using the **Helm chart** for full control (replicas, ingress, storage class, optional Ollama, TLS, etc.):

  ```bash
  helm install cloudshift ./deploy/helm/cloudshift \
    --set global.imageRegistry=<client-registry> \
    -f deploy/helm/values-gcp.yaml   # or values-aws.yaml, values-azure.yaml
  ```

- The chart is **Kubernetes-flavour agnostic**; cloud-specific behaviour is configured via the values files (ingress class, storage class, workload identity).

See [Deployment](../README.md#deployment) in the main README and [On-Premises / Air-Gapped](../README.md#on-premises--air-gapped) for image transfer and air-gapped Helm install.
