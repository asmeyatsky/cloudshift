"""Azure-specific configuration for the web application."""

import os


# Azure Storage
AZURE_STORAGE_CONNECTION_STRING = os.environ.get(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
)
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER", "app-uploads")

# Azure Cosmos DB
AZURE_COSMOS_ENDPOINT = os.environ.get("AZURE_COSMOS_ENDPOINT", "https://myapp-cosmos.documents.azure.com:443/")
AZURE_COSMOS_KEY = os.environ.get("AZURE_COSMOS_KEY", "")
AZURE_COSMOS_DATABASE = os.environ.get("AZURE_COSMOS_DATABASE", "appdb")
AZURE_COSMOS_CONTAINER = os.environ.get("AZURE_COSMOS_CONTAINER", "items")

# Azure Service Bus
AZURE_SERVICEBUS_CONNECTION_STRING = os.environ.get(
    "AZURE_SERVICEBUS_CONNECTION_STRING",
    "Endpoint=sb://myapp-bus.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=mykey"
)
AZURE_SERVICEBUS_QUEUE_NAME = os.environ.get("AZURE_SERVICEBUS_QUEUE", "tasks")
AZURE_SERVICEBUS_TOPIC_NAME = os.environ.get("AZURE_SERVICEBUS_TOPIC", "notifications")

# Azure Key Vault
AZURE_KEYVAULT_URL = os.environ.get("AZURE_KEYVAULT_URL", "https://myapp-vault.vault.azure.net/")

# Azure AD / Identity
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")

# Application settings
APP_PORT = int(os.environ.get("APP_PORT", "8080"))
APP_DEBUG = os.environ.get("APP_DEBUG", "false").lower() == "true"
