"""Azure Key Vault operations — secrets and certificate management."""

from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient, CertificatePolicy
from identity import get_default_credential
from config import AZURE_KEYVAULT_URL


def get_secret_client():
    """Create an Azure Key Vault SecretClient."""
    credential = get_default_credential()
    return SecretClient(vault_url=AZURE_KEYVAULT_URL, credential=credential)


def get_certificate_client():
    """Create an Azure Key Vault CertificateClient."""
    credential = get_default_credential()
    return CertificateClient(vault_url=AZURE_KEYVAULT_URL, credential=credential)


def get_secret(name):
    """Retrieve a secret value from Azure Key Vault."""
    client = get_secret_client()
    secret = client.get_secret(name)
    return secret.value


def set_secret(name, value):
    """Store a secret in Azure Key Vault."""
    client = get_secret_client()
    result = client.set_secret(name, value)
    return {"name": result.name, "version": result.properties.version}


def delete_secret(name):
    """Begin deletion of a secret from Azure Key Vault."""
    client = get_secret_client()
    poller = client.begin_delete_secret(name)
    return poller.result()


def list_secrets():
    """List all secrets in the Azure Key Vault."""
    client = get_secret_client()
    secrets = client.list_properties_of_secrets()
    return [{"name": s.name, "enabled": s.enabled, "updated": str(s.updated_on)} for s in secrets]


def create_certificate(name, subject="CN=myapp.contoso.com"):
    """Create a self-signed certificate in Azure Key Vault."""
    client = get_certificate_client()
    policy = CertificatePolicy.get_default()
    policy.subject = subject
    poller = client.begin_create_certificate(certificate_name=name, policy=policy)
    return poller.result()


def get_certificate(name):
    """Retrieve a certificate from Azure Key Vault."""
    client = get_certificate_client()
    cert = client.get_certificate(name)
    return {"name": cert.name, "thumbprint": cert.properties.x509_thumbprint.hex()}
