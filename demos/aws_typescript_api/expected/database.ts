// Firestore operations for products and orders

import { firestoreClient, config } from "./config";
import { Product, Order, PaginatedResult } from "./types";

const PRODUCTS_COLLECTION = config.firestoreCollectionProducts;
const ORDERS_COLLECTION = config.firestoreCollectionOrders;

export async function putProduct(product: Product): Promise<void> {
  const docRef = firestoreClient.collection(PRODUCTS_COLLECTION).doc(product.productId);
  await docRef.set({
    name: product.name,
    price: product.price,
    category: product.category,
    createdAt: product.createdAt,
  });
}

export async function getProduct(productId: string): Promise<Product | null> {
  const docRef = firestoreClient.collection(PRODUCTS_COLLECTION).doc(productId);
  const snapshot = await docRef.get();
  if (!snapshot.exists) return null;
  const data = snapshot.data()!;
  return {
    productId: snapshot.id,
    name: data.name,
    description: data.description || "",
    price: Number(data.price),
    category: data.category,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt || "",
  };
}

export async function queryOrdersByCustomer(
  customerId: string
): Promise<PaginatedResult<Order>> {
  const snapshot = await firestoreClient
    .collection(ORDERS_COLLECTION)
    .where("customerId", "==", customerId)
    .limit(25)
    .get();
  const items = snapshot.docs.map((doc) => {
    const data = doc.data();
    return {
      orderId: doc.id,
      customerId: data.customerId,
      items: data.items || [],
      totalAmount: Number(data.totalAmount),
      status: data.status as Order["status"],
      createdAt: data.createdAt,
    };
  });
  return { items, count: items.length };
}

export async function scanProducts(): Promise<Product[]> {
  const snapshot = await firestoreClient
    .collection(PRODUCTS_COLLECTION)
    .limit(50)
    .get();
  return snapshot.docs.map((doc) => {
    const data = doc.data();
    return {
      productId: doc.id,
      name: data.name,
      description: data.description || "",
      price: Number(data.price),
      category: data.category,
      createdAt: data.createdAt,
      updatedAt: data.updatedAt || "",
    };
  });
}

export async function deleteProduct(productId: string): Promise<void> {
  await firestoreClient.collection(PRODUCTS_COLLECTION).doc(productId).delete();
}

export async function batchWriteProducts(products: Product[]): Promise<void> {
  const batch = firestoreClient.batch();
  for (const p of products) {
    const docRef = firestoreClient.collection(PRODUCTS_COLLECTION).doc(p.productId);
    batch.set(docRef, {
      name: p.name,
      price: p.price,
      category: p.category,
      createdAt: p.createdAt,
    });
  }
  await batch.commit();
}
