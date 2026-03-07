"""Google Cloud Secret Manager operations — secrets management."""

from google.cloud import secretmanager
from config import GCP_SECRET_PROJECT


def get_secret_client():
    """Create a Google Cloud Secret Manager client."""
    return secretmanager.SecretManagerServiceClient()


def get_secret(name):
    """Retrieve the latest version of a secret from Secret Manager."""
    client = get_secret_client()
    secret_path = f"projects/{GCP_SECRET_PROJECT}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("utf-8")


def set_secret(name, value):
    """Create or add a version of a secret in Secret Manager."""
    client = get_secret_client()
    parent = f"projects/{GCP_SECRET_PROJECT}"
    try:
        client.create_secret(
            request={"parent": parent, "secret_id": name, "secret": {"replication": {"automatic": {}}}}
        )
    except Exception:
        pass  # Secret already exists
    secret_path = f"projects/{GCP_SECRET_PROJECT}/secrets/{name}"
    response = client.add_secret_version(
        request={"parent": secret_path, "payload": {"data": value.encode("utf-8")}}
    )
    version = response.name.split("/")[-1]
    return {"name": name, "version": version}


def delete_secret(name):
    """Delete a secret from Secret Manager."""
    client = get_secret_client()
    secret_path = f"projects/{GCP_SECRET_PROJECT}/secrets/{name}"
    client.delete_secret(request={"name": secret_path})


def list_secrets():
    """List all secrets in the GCP project."""
    client = get_secret_client()
    parent = f"projects/{GCP_SECRET_PROJECT}"
    secrets = client.list_secrets(request={"parent": parent})
    results = []
    for secret in secrets:
        results.append({
            "name": secret.name.split("/")[-1],
            "enabled": True,
            "updated": str(secret.create_time),
        })
    return results


def get_secret_version(name, version="latest"):
    """Retrieve a specific version of a secret."""
    client = get_secret_client()
    secret_path = f"projects/{GCP_SECRET_PROJECT}/secrets/{name}/versions/{version}"
    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("utf-8")
