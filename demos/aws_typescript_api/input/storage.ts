// S3 storage operations for product assets

import {
  PutObjectCommand,
  GetObjectCommand,
  ListObjectsV2Command,
  DeleteObjectCommand,
  CreateBucketCommand,
} from "@aws-sdk/client-s3";
import { s3Client, config } from "./config";
import { StorageUpload } from "./types";

const BUCKET = config.s3Bucket;

export async function uploadFile(upload: StorageUpload): Promise<string> {
  const command = new PutObjectCommand({
    Bucket: BUCKET,
    Key: upload.key,
    Body: upload.data,
    ContentType: upload.contentType,
  });
  await s3Client.send(command);
  return `s3://${BUCKET}/${upload.key}`;
}

export async function getFile(key: string): Promise<Buffer> {
  const command = new GetObjectCommand({ Bucket: BUCKET, Key: key });
  const response = await s3Client.send(command);
  const stream = response.Body as NodeJS.ReadableStream;
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

export async function listFiles(prefix: string): Promise<string[]> {
  const command = new ListObjectsV2Command({
    Bucket: BUCKET,
    Prefix: prefix,
    MaxKeys: 100,
  });
  const response = await s3Client.send(command);
  return (response.Contents || []).map((obj) => obj.Key!);
}

export async function deleteFile(key: string): Promise<void> {
  const command = new DeleteObjectCommand({ Bucket: BUCKET, Key: key });
  await s3Client.send(command);
}

export async function ensureBucket(): Promise<void> {
  try {
    const command = new CreateBucketCommand({ Bucket: BUCKET });
    await s3Client.send(command);
  } catch (err: any) {
    if (err.name !== "BucketAlreadyOwnedByYou") throw err;
  }
}
