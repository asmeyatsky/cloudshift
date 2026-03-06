import boto3
import json

secrets_client = boto3.client('secretsmanager', region_name='us-east-1')


def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager."""
    response = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])


def create_secret(name, value):
    """Create a new secret in AWS Secrets Manager."""
    secrets_client.create_secret(
        Name=name,
        SecretString=json.dumps(value),
    )


def update_secret(name, value):
    """Update a secret in AWS Secrets Manager."""
    secrets_client.update_secret(
        SecretId=name,
        SecretString=json.dumps(value),
    )
