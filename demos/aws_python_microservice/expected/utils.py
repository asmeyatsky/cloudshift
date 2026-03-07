"""Utility functions for Cloud Logging, Monitoring, and Runtime Config."""

import json
from datetime import datetime

from google.cloud import logging as cloud_logging
from google.cloud import monitoring_v3
from google.cloud import secretmanager

from config import GCP_PROJECT_ID, LOG_NAME, MONITORING_NAMESPACE, PARAMETER_PREFIX


logging_client = cloud_logging.Client()
monitoring_client = monitoring_v3.MetricServiceClient()
secrets_client = secretmanager.SecretManagerServiceClient()

cloud_logger = logging_client.logger(LOG_NAME)


def put_metric(metric_name, value, unit="1"):
    """Write a custom metric to Cloud Monitoring."""
    project_name = f"projects/{GCP_PROJECT_ID}"
    series = monitoring_v3.TimeSeries()
    series.metric.type = f"{MONITORING_NAMESPACE}/{metric_name}"
    series.resource.type = "global"
    now = datetime.utcnow()
    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": int(now.timestamp())}}
    )
    point = monitoring_v3.Point(
        {"interval": interval, "value": {"double_value": float(value)}}
    )
    series.points = [point]
    try:
        monitoring_client.create_time_series(
            request={"name": project_name, "time_series": [series]}
        )
    except Exception as e:
        raise RuntimeError(f"Failed to write Cloud Monitoring metric: {e}")


def log_event(log_stream, message):
    """Write a structured log entry to Cloud Logging."""
    try:
        struct = message if isinstance(message, dict) else {"message": message}
        struct["stream"] = log_stream
        cloud_logger.log_struct(struct)
    except Exception as e:
        raise RuntimeError(f"Failed to write Cloud Logging entry: {e}")


def get_parameter(name, decrypt=True):
    """Retrieve a parameter stored as a secret version in Secret Manager."""
    secret_name = f"{PARAMETER_PREFIX}-{name}"
    resource = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
    try:
        response = secrets_client.access_secret_version(
            request={"name": resource}
        )
        return response.payload.data.decode("utf-8")
    except Exception:
        return None


def put_parameter(name, value, param_type="string"):
    """Store a parameter as a secret version in Secret Manager."""
    secret_name = f"{PARAMETER_PREFIX}-{name}"
    parent = f"projects/{GCP_PROJECT_ID}"
    secret_path = f"{parent}/secrets/{secret_name}"
    try:
        try:
            secrets_client.get_secret(request={"name": secret_path})
        except Exception:
            secrets_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        secrets_client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": value.encode("utf-8")},
            }
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to store parameter: {e}")


def get_parameters_by_path():
    """Retrieve all parameters (secrets) under the application prefix."""
    parent = f"projects/{GCP_PROJECT_ID}"
    try:
        params = {}
        for secret in secrets_client.list_secrets(
            request={"parent": parent, "filter": f"name:{PARAMETER_PREFIX}"}
        ):
            short_name = secret.name.split("/")[-1].replace(
                f"{PARAMETER_PREFIX}-", ""
            )
            version_name = f"{secret.name}/versions/latest"
            try:
                version = secrets_client.access_secret_version(
                    request={"name": version_name}
                )
                params[short_name] = version.payload.data.decode("utf-8")
            except Exception:
                continue
        return params
    except Exception as e:
        raise RuntimeError(f"Failed to list parameters: {e}")
