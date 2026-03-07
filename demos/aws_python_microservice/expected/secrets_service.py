"""GCP Secret Manager operations for secret management."""

import json

from google.cloud import secretmanager
from google.api_core.exceptions import NotFound, GoogleAPICallError

from config import GCP_PROJECT_ID, SECRET_NAME


secrets_client = secretmanager.SecretManagerServiceClient()


def get_secret(secret_name=None):
    """Retrieve the latest secret version from Secret Manager."""
    name = secret_name or SECRET_NAME
    resource_name = f"projects/{GCP_PROJECT_ID}/secrets/{name}/versions/latest"
    try:
        response = secrets_client.access_secret_version(
            request={"name": resource_name}
        )
        payload = response.payload.data.decode("utf-8")
        return json.loads(payload)
    except NotFound:
        raise ValueError(f"Secret '{name}' not found")
    except GoogleAPICallError as e:
        raise RuntimeError(f"Cannot access secret '{name}': {e}")


def create_secret(name, value, description=""):
    """Create a new secret in Secret Manager."""
    parent = f"projects/{GCP_PROJECT_ID}"
    secret_value = json.dumps(value) if isinstance(value, dict) else value
    try:
        secret = secrets_client.create_secret(
            request={
                "parent": parent,
                "secret_id": name,
                "secret": {
                    "replication": {"automatic": {}},
                    "labels": {
                        "application": "myapp",
                        "managed-by": "microservice",
                    },
                },
            }
        )
        secrets_client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": secret_value.encode("utf-8")},
            }
        )
        return secret.name
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to create secret: {e}")


def update_secret(secret_name, new_value):
    """Add a new version of an existing secret."""
    secret_value = json.dumps(new_value) if isinstance(new_value, dict) else new_value
    parent = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}"
    try:
        secrets_client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": secret_value.encode("utf-8")},
            }
        )
        return True
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to update secret: {e}")


def rotate_secret(secret_name, rotation_topic):
    """Configure automatic rotation for a secret using a Pub/Sub topic."""
    secret_path = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}"
    try:
        secrets_client.update_secret(
            request={
                "secret": {
                    "name": secret_path,
                    "rotation": {
                        "rotation_period": {"seconds": 30 * 24 * 3600},
                        "next_rotation_time": None,
                    },
                    "topics": [{"name": rotation_topic}],
                },
                "update_mask": {"paths": ["rotation", "topics"]},
            }
        )
        return True
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to configure secret rotation: {e}")


def list_secrets(prefix="myapp"):
    """List all secrets matching a name prefix."""
    parent = f"projects/{GCP_PROJECT_ID}"
    try:
        secrets = []
        for secret in secrets_client.list_secrets(
            request={"parent": parent, "filter": f"name:{prefix}"}
        ):
            secrets.append({
                "name": secret.name.split("/")[-1],
                "resource_name": secret.name,
                "create_time": secret.create_time,
            })
        return secrets
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to list secrets: {e}")
