"""GCP IAM authentication and credential management."""

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from config import GCP_PROJECT_ID, IMPERSONATE_SERVICE_ACCOUNT


def get_credentials():
    """Get default application credentials."""
    credentials, project = google.auth.default()
    return credentials, project


def get_impersonated_credentials(
    target_service_account=None, target_scopes=None
):
    """Impersonate a service account and return temporary credentials."""
    target = target_service_account or IMPERSONATE_SERVICE_ACCOUNT
    scopes = target_scopes or ["https://www.googleapis.com/auth/cloud-platform"]
    source_credentials, _ = google.auth.default()
    try:
        target_credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target,
            target_scopes=scopes,
            lifetime=3600,
        )
        return target_credentials
    except Exception as e:
        raise RuntimeError(
            f"Failed to impersonate service account {target}: {e}"
        )


def get_caller_identity():
    """Return the current caller's GCP identity."""
    credentials, project = google.auth.default()
    credentials.refresh(Request())
    return {
        "project": project,
        "service_account_email": getattr(
            credentials, "service_account_email", "unknown"
        ),
    }
