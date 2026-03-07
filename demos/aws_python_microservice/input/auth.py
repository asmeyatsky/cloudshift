"""AWS IAM authentication and credential management."""

import boto3
from botocore.exceptions import ClientError

from config import (
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    ASSUME_ROLE_ARN,
)


def get_session():
    """Create a boto3 session using environment credentials."""
    return boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def get_client(service_name):
    """Get a boto3 client for the specified AWS service."""
    session = get_session()
    return session.client(service_name, region_name=AWS_REGION)


def get_resource(service_name):
    """Get a boto3 resource for the specified AWS service."""
    session = get_session()
    return session.resource(service_name, region_name=AWS_REGION)


def assume_role(role_arn=None, session_name="myapp-session"):
    """Assume an IAM role using STS and return temporary credentials."""
    arn = role_arn or ASSUME_ROLE_ARN
    sts_client = boto3.client("sts", region_name=AWS_REGION)
    try:
        response = sts_client.assume_role(
            RoleArn=arn,
            RoleSessionName=session_name,
            DurationSeconds=3600,
        )
        credentials = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=AWS_REGION,
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to assume role {arn}: {e}")


def get_caller_identity():
    """Return the current caller's AWS identity."""
    sts_client = boto3.client("sts", region_name=AWS_REGION)
    return sts_client.get_caller_identity()
