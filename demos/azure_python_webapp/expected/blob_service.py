"""Google Cloud Storage operations — upload, download, list, delete, and signed URLs."""

from datetime import timedelta
from google.cloud import storage
from config import GCS_BUCKET_NAME


def get_storage_client():
    """Create a Google Cloud Storage client."""
    return storage.Client()


def upload_blob(blob_name, data, content_type="application/octet-stream"):
    """Upload data to Google Cloud Storage."""
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    return blob.public_url


def download_blob(blob_name):
    """Download a blob from Google Cloud Storage and return its bytes."""
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def list_blobs(prefix=None):
    """List blobs in the GCS bucket, optionally filtered by prefix."""
    client = get_storage_client()
    blobs = client.list_blobs(GCS_BUCKET_NAME, prefix=prefix)
    return [{"name": b.name, "size": b.size, "modified": str(b.updated)} for b in blobs]


def delete_blob(blob_name):
    """Delete a blob from Google Cloud Storage."""
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.delete()


def generate_signed_url(blob_name, expiry_hours=1):
    """Generate a signed URL for temporary access to a GCS blob."""
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=expiry_hours),
        method="GET",
    )
    return url
