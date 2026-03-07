"""Azure Blob Storage operations — upload, download, list, delete, and SAS tokens."""

from datetime import datetime, timedelta
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)
from config import AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME


def get_blob_service_client():
    """Create an Azure BlobServiceClient from the connection string."""
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


def upload_blob(blob_name, data, content_type="application/octet-stream"):
    """Upload data to Azure Blob Storage."""
    client = get_blob_service_client()
    blob_client = client.get_blob_client(AZURE_STORAGE_CONTAINER_NAME, blob_name)
    blob_client.upload_blob(data, content_type=content_type, overwrite=True)
    return blob_client.url


def download_blob(blob_name):
    """Download a blob from Azure Blob Storage and return its bytes."""
    client = get_blob_service_client()
    blob_client = client.get_blob_client(AZURE_STORAGE_CONTAINER_NAME, blob_name)
    stream = blob_client.download_blob()
    return stream.readall()


def list_blobs(prefix=None):
    """List blobs in the Azure Storage container, optionally filtered by prefix."""
    client = get_blob_service_client()
    container_client = client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
    blobs = container_client.list_blobs(name_starts_with=prefix)
    return [{"name": b.name, "size": b.size, "modified": str(b.last_modified)} for b in blobs]


def delete_blob(blob_name):
    """Delete a blob from Azure Blob Storage."""
    client = get_blob_service_client()
    blob_client = client.get_blob_client(AZURE_STORAGE_CONTAINER_NAME, blob_name)
    blob_client.delete_blob()


def generate_sas_url(blob_name, expiry_hours=1):
    """Generate a SAS URL for temporary access to an Azure blob."""
    client = get_blob_service_client()
    sas_token = generate_blob_sas(
        account_name=client.account_name,
        container_name=AZURE_STORAGE_CONTAINER_NAME,
        blob_name=blob_name,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
    )
    return f"https://{client.account_name}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_name}?{sas_token}"
