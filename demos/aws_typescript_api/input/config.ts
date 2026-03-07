// AWS configuration and environment settings

import { S3Client } from "@aws-sdk/client-s3";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { SQSClient } from "@aws-sdk/client-sqs";

const AWS_REGION = process.env.AWS_REGION || "us-east-1";

export const s3Client = new S3Client({
  region: AWS_REGION,
  maxAttempts: 3,
});

export const dynamoClient = new DynamoDBClient({
  region: AWS_REGION,
  maxAttempts: 3,
});

export const sqsClient = new SQSClient({
  region: AWS_REGION,
  maxAttempts: 3,
});

export const config = {
  region: AWS_REGION,
  s3Bucket: process.env.S3_BUCKET_NAME || "product-assets",
  dynamoTableProducts: process.env.DYNAMO_TABLE_PRODUCTS || "Products",
  dynamoTableOrders: process.env.DYNAMO_TABLE_ORDERS || "Orders",
  sqsQueueUrl: process.env.SQS_QUEUE_URL || "",
  stage: process.env.STAGE || "dev",
  corsOrigin: process.env.CORS_ORIGIN || "*",
};

export function getHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": config.corsOrigin,
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
  };
}
