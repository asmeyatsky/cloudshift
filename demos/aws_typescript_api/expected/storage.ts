// Cloud Storage operations for product assets

import { storageClient, config } from "./config";
import { StorageUpload } from "./types";

const BUCKET_NAME = config.storageBucket;

export async function uploadFile(upload: StorageUpload): Promise<string> {
  const bucket = storageClient.bucket(BUCKET_NAME);
  const file = bucket.file(upload.key);
  await file.save(Buffer.from(upload.data), {
    contentType: upload.contentType,
  });
  return `gs://${BUCKET_NAME}/${upload.key}`;
}

export async function getFile(key: string): Promise<Buffer> {
  const bucket = storageClient.bucket(BUCKET_NAME);
  const file = bucket.file(key);
  const [contents] = await file.download();
  return contents;
}

export async function listFiles(prefix: string): Promise<string[]> {
  const bucket = storageClient.bucket(BUCKET_NAME);
  const [files] = await bucket.getFiles({
    prefix,
    maxResults: 100,
  });
  return files.map((file) => file.name);
}

export async function deleteFile(key: string): Promise<void> {
  const bucket = storageClient.bucket(BUCKET_NAME);
  const file = bucket.file(key);
  await file.delete();
}

export async function ensureBucket(): Promise<void> {
  try {
    await storageClient.createBucket(BUCKET_NAME);
  } catch (err: any) {
    if (err.code !== 409) throw err;
  }
}
