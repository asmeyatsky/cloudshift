import { Firestore } from "@google-cloud/firestore";

const db = new Firestore();
const COLLECTION_NAME = "users";

export async function putUser(id: string, name: string, email: string): Promise<void> {
    await db.collection(COLLECTION_NAME).doc(id).set({ name, email });
}

export async function getUser(id: string): Promise<Record<string, any> | null> {
    const doc = await db.collection(COLLECTION_NAME).doc(id).get();
    return doc.exists ? doc.data()! : null;
}

export async function queryByEmail(email: string): Promise<Record<string, any>[]> {
    const snapshot = await db.collection(COLLECTION_NAME)
        .where("email", "==", email)
        .get();
    return snapshot.docs.map(doc => doc.data());
}

export async function deleteUser(id: string): Promise<void> {
    await db.collection(COLLECTION_NAME).doc(id).delete();
}
