import { Storage } from "@google-cloud/storage";

const storage = new Storage();

export async function uploadFile(bucket: string, key: string, body: Buffer): Promise<void> {
    const file = storage.bucket(bucket).file(key);
    await file.save(body);
}

export async function downloadFile(bucket: string, key: string): Promise<Buffer> {
    const file = storage.bucket(bucket).file(key);
    const [contents] = await file.download();
    return contents;
}

export async function listFiles(bucket: string, prefix: string = ""): Promise<string[]> {
    const [files] = await storage.bucket(bucket).getFiles({ prefix });
    return files.map(file => file.name);
}

export async function deleteFile(bucket: string, key: string): Promise<void> {
    const file = storage.bucket(bucket).file(key);
    await file.delete();
}
