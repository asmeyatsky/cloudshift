from google.cloud import secretmanager
import json

client = secretmanager.SecretManagerServiceClient()
PROJECT_ID = "my-project"


def get_secret(secret_name):
    """Retrieve a secret from GCP Secret Manager."""
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return json.loads(response.payload.data.decode("utf-8"))


def create_secret(name, value):
    """Create a new secret in GCP Secret Manager."""
    parent = f"projects/{PROJECT_ID}"
    secret = client.create_secret(
        request={"parent": parent, "secret_id": name, "secret": {"replication": {"automatic": {}}}}
    )
    client.add_secret_version(
        request={"parent": secret.name, "payload": {"data": json.dumps(value).encode("utf-8")}}
    )


def update_secret(name, value):
    """Update a secret in GCP Secret Manager."""
    parent = f"projects/{PROJECT_ID}/secrets/{name}"
    client.add_secret_version(
        request={"parent": parent, "payload": {"data": json.dumps(value).encode("utf-8")}}
    )
