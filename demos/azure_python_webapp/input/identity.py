"""Azure Identity management using DefaultAzureCredential and service principals."""

from azure.identity import (
    DefaultAzureCredential,
    ClientSecretCredential,
    ManagedIdentityCredential,
)
from config import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET


def get_default_credential():
    """Get credential using DefaultAzureCredential chain."""
    credential = DefaultAzureCredential()
    return credential


def get_service_principal_credential():
    """Authenticate using an Azure AD service principal with client secret."""
    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    return credential


def get_managed_identity_credential(client_id=None):
    """Get credential using Azure Managed Identity (system or user-assigned)."""
    if client_id:
        credential = ManagedIdentityCredential(client_id=client_id)
    else:
        credential = ManagedIdentityCredential()
    return credential


def get_access_token(credential, scope="https://management.azure.com/.default"):
    """Retrieve an Azure AD access token for the given scope."""
    token = credential.get_token(scope)
    return token.token


def validate_credential(credential):
    """Validate that the credential can obtain a token from Azure AD."""
    try:
        token = credential.get_token("https://management.azure.com/.default")
        return {"valid": True, "expires_on": token.expires_on}
    except Exception as e:
        return {"valid": False, "error": str(e)}
