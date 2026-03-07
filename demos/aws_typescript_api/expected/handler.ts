// Cloud Function handler entry point for HTTP events

import { getHeaders, config } from "./config";
import { getProduct, putProduct, scanProducts, deleteProduct } from "./database";
import { uploadFile, getFile, listFiles } from "./storage";
import { sendOrderEvent } from "./messaging";
import { ApiResponse, Product } from "./types";

interface HttpRequest {
  method: string;
  path: string;
  params?: Record<string, string>;
  query?: Record<string, string>;
  body?: string;
}

function respond<T>(statusCode: number, body: T): ApiResponse<string> {
  return {
    statusCode,
    body: JSON.stringify(body),
    headers: getHeaders(),
  };
}

export async function handler(req: HttpRequest): Promise<ApiResponse<string>> {
  const { method, path } = req;

  try {
    if (path.startsWith("/products")) {
      return handleProducts(req);
    }
    if (path.startsWith("/assets")) {
      return handleAssets(req);
    }
    return respond(404, { error: "Route not found" });
  } catch (err: any) {
    console.error(`[${config.stage}] Error:`, err.message);
    return respond(500, { error: "Internal server error" });
  }
}

async function handleProducts(req: HttpRequest): Promise<ApiResponse<string>> {
  const productId = req.params?.id;

  if (req.method === "GET" && productId) {
    const product = await getProduct(productId);
    if (!product) return respond(404, { error: "Product not found" });
    return respond(200, product);
  }
  if (req.method === "GET") {
    const products = await scanProducts();
    return respond(200, { items: products });
  }
  if (req.method === "POST") {
    const product: Product = JSON.parse(req.body || "{}");
    await putProduct(product);
    await sendOrderEvent("ORDER_CREATED", product.productId, { name: product.name });
    return respond(201, { message: "Product created" });
  }
  if (req.method === "DELETE" && productId) {
    await deleteProduct(productId);
    return respond(200, { message: "Product deleted" });
  }
  return respond(405, { error: "Method not allowed" });
}

async function handleAssets(req: HttpRequest): Promise<ApiResponse<string>> {
  if (req.method === "GET") {
    const prefix = req.query?.prefix || "";
    const keys = await listFiles(prefix);
    return respond(200, { keys });
  }
  if (req.method === "POST") {
    const { key, contentType, data } = JSON.parse(req.body || "{}");
    const uri = await uploadFile({ key, contentType, data });
    return respond(201, { uri });
  }
  return respond(405, { error: "Method not allowed" });
}
