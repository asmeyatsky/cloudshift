// GCP configuration and environment settings

import { Storage } from "@google-cloud/storage";
import { Firestore } from "@google-cloud/firestore";
import { PubSub } from "@google-cloud/pubsub";

const GCP_PROJECT_ID = process.env.GCP_PROJECT_ID || "my-project";

export const storageClient = new Storage({
  projectId: GCP_PROJECT_ID,
  retryOptions: { maxRetries: 3 },
});

export const firestoreClient = new Firestore({
  projectId: GCP_PROJECT_ID,
});

export const pubsubClient = new PubSub({
  projectId: GCP_PROJECT_ID,
});

export const config = {
  projectId: GCP_PROJECT_ID,
  storageBucket: process.env.GCS_BUCKET_NAME || "product-assets",
  firestoreCollectionProducts: process.env.FIRESTORE_COLLECTION_PRODUCTS || "Products",
  firestoreCollectionOrders: process.env.FIRESTORE_COLLECTION_ORDERS || "Orders",
  pubsubTopic: process.env.PUBSUB_TOPIC || "",
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
