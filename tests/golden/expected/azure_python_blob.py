from google.cloud import storage

client = storage.Client()
bucket_name = "my-container"


def upload_blob(name, data):
    """Upload data to GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(name)
    blob.upload_from_string(data)


def download_blob(name):
    """Download blob from GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(name)
    return blob.download_as_bytes()


def list_blobs(prefix=""):
    """List blobs in GCS bucket."""
    bucket = client.bucket(bucket_name)
    return [blob.name for blob in bucket.list_blobs(prefix=prefix)]


def delete_blob(name):
    """Delete blob from GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(name)
    blob.delete()
