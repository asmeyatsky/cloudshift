"""GCP Identity management using Application Default Credentials and service accounts."""

import google.auth
from google.auth import credentials as ga_credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from config import GOOGLE_APPLICATION_CREDENTIALS, GCP_SERVICE_ACCOUNT_EMAIL


def get_default_credential():
    """Get credential using Application Default Credentials."""
    credentials, project = google.auth.default()
    return credentials


def get_service_account_credential(scopes=None):
    """Authenticate using a GCP service account key file."""
    scopes = scopes or ["https://www.googleapis.com/auth/cloud-platform"]
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=scopes,
    )
    return credentials


def get_impersonated_credential(target_email=None):
    """Get credential by impersonating a service account."""
    from google.auth import impersonated_credentials
    source_credentials, _ = google.auth.default()
    target = target_email or GCP_SERVICE_ACCOUNT_EMAIL
    credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return credentials


def get_access_token(credentials):
    """Retrieve a GCP access token from the credentials."""
    credentials.refresh(Request())
    return credentials.token


def validate_credential(credentials):
    """Validate that the credential can obtain a token from GCP."""
    try:
        credentials.refresh(Request())
        return {"valid": True, "expiry": str(credentials.expiry)}
    except Exception as e:
        return {"valid": False, "error": str(e)}
