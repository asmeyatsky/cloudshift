"""AWS Secrets Manager operations for secret management."""

import json

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, SECRET_NAME


secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)


def get_secret(secret_name=None):
    """Retrieve a secret value from AWS Secrets Manager."""
    name = secret_name or SECRET_NAME
    try:
        response = secrets_client.get_secret_value(SecretId=name)
        secret_string = response.get("SecretString")
        if secret_string:
            return json.loads(secret_string)
        return response.get("SecretBinary")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ResourceNotFoundException":
            raise ValueError(f"Secret '{name}' not found")
        elif code == "DecryptionFailureException":
            raise RuntimeError(f"Cannot decrypt secret '{name}'")
        raise


def create_secret(name, value, description=""):
    """Create a new secret in AWS Secrets Manager."""
    secret_value = json.dumps(value) if isinstance(value, dict) else value
    try:
        response = secrets_client.create_secret(
            Name=name,
            Description=description,
            SecretString=secret_value,
            Tags=[
                {"Key": "Application", "Value": "myapp"},
                {"Key": "ManagedBy", "Value": "microservice"},
            ],
        )
        return response["ARN"]
    except ClientError as e:
        raise RuntimeError(f"Failed to create secret: {e}")


def update_secret(secret_name, new_value):
    """Update an existing secret's value."""
    secret_value = json.dumps(new_value) if isinstance(new_value, dict) else new_value
    try:
        secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=secret_value,
        )
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to update secret: {e}")


def rotate_secret(secret_name, rotation_lambda_arn):
    """Enable automatic rotation for a secret using a Lambda function."""
    try:
        secrets_client.rotate_secret(
            SecretId=secret_name,
            RotationLambdaARN=rotation_lambda_arn,
            RotationRules={"AutomaticallyAfterDays": 30},
        )
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to rotate secret: {e}")


def list_secrets(prefix="myapp/"):
    """List all secrets matching a name prefix."""
    try:
        paginator = secrets_client.get_paginator("list_secrets")
        secrets = []
        for page in paginator.paginate(
            Filters=[{"Key": "name", "Values": [prefix]}]
        ):
            for secret in page["SecretList"]:
                secrets.append({
                    "name": secret["Name"],
                    "arn": secret["ARN"],
                    "last_changed": secret.get("LastChangedDate"),
                })
        return secrets
    except ClientError as e:
        raise RuntimeError(f"Failed to list secrets: {e}")
