import { S3Client, PutObjectCommand, GetObjectCommand, ListObjectsV2Command, DeleteObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({ region: "us-east-1" });

export async function uploadFile(bucket: string, key: string, body: Buffer): Promise<void> {
    const command = new PutObjectCommand({ Bucket: bucket, Key: key, Body: body });
    await s3Client.send(command);
}

export async function downloadFile(bucket: string, key: string): Promise<Buffer> {
    const command = new GetObjectCommand({ Bucket: bucket, Key: key });
    const response = await s3Client.send(command);
    return Buffer.from(await response.Body!.transformToByteArray());
}

export async function listFiles(bucket: string, prefix: string = ""): Promise<string[]> {
    const command = new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix });
    const response = await s3Client.send(command);
    return (response.Contents || []).map(obj => obj.Key!);
}

export async function deleteFile(bucket: string, key: string): Promise<void> {
    const command = new DeleteObjectCommand({ Bucket: bucket, Key: key });
    await s3Client.send(command);
}
