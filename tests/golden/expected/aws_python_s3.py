from google.cloud import storage

client = storage.Client()


def upload_file(bucket_name, key, data):
    """Upload data to GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    blob.upload_from_string(data)


def download_file(bucket_name, key):
    """Download file from GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    return blob.download_as_bytes()


def list_files(bucket_name, prefix=""):
    """List files in GCS bucket."""
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name for blob in blobs]


def delete_file(bucket_name, key):
    """Delete file from GCS."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    blob.delete()
