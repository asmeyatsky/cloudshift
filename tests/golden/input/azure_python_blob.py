from azure.storage.blob import BlobServiceClient

connection_string = "DefaultEndpointsProtocol=https;AccountName=myaccount;..."
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = "my-container"


def upload_blob(name, data):
    """Upload data to Azure Blob Storage."""
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=name
    )
    blob_client.upload_blob(data, overwrite=True)


def download_blob(name):
    """Download blob from Azure Blob Storage."""
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=name
    )
    return blob_client.download_blob().readall()


def list_blobs(prefix=""):
    """List blobs in Azure container."""
    container_client = blob_service_client.get_container_client(container_name)
    return [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]


def delete_blob(name):
    """Delete blob from Azure Blob Storage."""
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=name
    )
    blob_client.delete_blob()
