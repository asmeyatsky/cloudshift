"""Utility functions for CloudWatch logging and Parameter Store access."""

import json
import time
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from config import (
    AWS_REGION,
    CLOUDWATCH_LOG_GROUP,
    CLOUDWATCH_NAMESPACE,
    SSM_PARAMETER_PREFIX,
)


cloudwatch_client = boto3.client("cloudwatch", region_name=AWS_REGION)
logs_client = boto3.client("logs", region_name=AWS_REGION)
ssm_client = boto3.client("ssm", region_name=AWS_REGION)


def put_metric(metric_name, value, unit="Count"):
    """Publish a custom metric to CloudWatch."""
    try:
        cloudwatch_client.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": datetime.utcnow(),
                }
            ],
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to put CloudWatch metric: {e}")


def log_event(log_stream, message):
    """Write a log event to CloudWatch Logs."""
    try:
        logs_client.put_log_events(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            logStreamName=log_stream,
            logEvents=[
                {
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps(message) if isinstance(message, dict) else message,
                }
            ],
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to write CloudWatch log: {e}")


def get_parameter(name, decrypt=True):
    """Retrieve a parameter from SSM Parameter Store."""
    full_name = f"{SSM_PARAMETER_PREFIX}/{name}"
    try:
        response = ssm_client.get_parameter(
            Name=full_name, WithDecryption=decrypt
        )
        return response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            return None
        raise


def put_parameter(name, value, param_type="SecureString"):
    """Store a parameter in SSM Parameter Store."""
    full_name = f"{SSM_PARAMETER_PREFIX}/{name}"
    try:
        ssm_client.put_parameter(
            Name=full_name,
            Value=value,
            Type=param_type,
            Overwrite=True,
        )
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to put SSM parameter: {e}")


def get_parameters_by_path():
    """Retrieve all parameters under the application prefix."""
    try:
        paginator = ssm_client.get_paginator("get_parameters_by_path")
        params = {}
        for page in paginator.paginate(
            Path=SSM_PARAMETER_PREFIX, Recursive=True, WithDecryption=True
        ):
            for param in page["Parameters"]:
                key = param["Name"].replace(f"{SSM_PARAMETER_PREFIX}/", "")
                params[key] = param["Value"]
        return params
    except ClientError as e:
        raise RuntimeError(f"Failed to get parameters by path: {e}")
