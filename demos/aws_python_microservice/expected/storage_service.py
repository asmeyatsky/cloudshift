"""Cloud Storage operations for file management."""

from datetime import timedelta

from google.cloud import storage
from google.cloud.exceptions import NotFound

from config import GCS_BUCKET_NAME, GCS_UPLOAD_PREFIX, GCS_SIGNED_URL_EXPIRY


storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)


def upload_file(file_obj, filename, content_type="application/octet-stream"):
    """Upload a file to Cloud Storage with the given key."""
    blob_name = f"{GCS_UPLOAD_PREFIX}{filename}"
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_file(file_obj, content_type=content_type)
        return f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    except Exception as e:
        raise RuntimeError(f"Cloud Storage upload failed: {e}")


def download_file(key):
    """Download a file from Cloud Storage and return its contents."""
    try:
        blob = bucket.blob(key)
        return blob.download_as_bytes()
    except NotFound:
        return None


def list_files(prefix=GCS_UPLOAD_PREFIX):
    """List all objects under a prefix in the Cloud Storage bucket."""
    try:
        blobs = storage_client.list_blobs(GCS_BUCKET_NAME, prefix=prefix)
        return [
            {"key": blob.name, "size": blob.size, "modified": blob.updated}
            for blob in blobs
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to list Cloud Storage objects: {e}")


def delete_file(key):
    """Delete an object from Cloud Storage."""
    try:
        blob = bucket.blob(key)
        blob.delete()
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to delete Cloud Storage object {key}: {e}")


def generate_presigned_url(key, expiration=GCS_SIGNED_URL_EXPIRY):
    """Generate a signed URL for temporary access to a Cloud Storage object."""
    try:
        blob = bucket.blob(key)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET",
        )
        return url
    except Exception as e:
        raise RuntimeError(f"Failed to generate signed URL: {e}")


def copy_file(source_key, dest_key):
    """Copy an object within the same Cloud Storage bucket."""
    try:
        source_blob = bucket.blob(source_key)
        bucket.copy_blob(source_blob, bucket, dest_key)
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to copy Cloud Storage object: {e}")
