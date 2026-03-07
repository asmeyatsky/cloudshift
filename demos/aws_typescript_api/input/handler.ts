// Lambda handler entry point for API Gateway events

import { getHeaders, config } from "./config";
import { getProduct, putProduct, scanProducts, deleteProduct } from "./database";
import { uploadFile, getFile, listFiles } from "./storage";
import { sendOrderEvent } from "./messaging";
import { ApiResponse, Product } from "./types";

interface APIGatewayEvent {
  httpMethod: string;
  path: string;
  pathParameters?: Record<string, string>;
  queryStringParameters?: Record<string, string>;
  body?: string;
}

function respond<T>(statusCode: number, body: T): ApiResponse<string> {
  return {
    statusCode,
    body: JSON.stringify(body),
    headers: getHeaders(),
  };
}

export async function handler(event: APIGatewayEvent): Promise<ApiResponse<string>> {
  const { httpMethod, path } = event;

  try {
    if (path.startsWith("/products")) {
      return handleProducts(event);
    }
    if (path.startsWith("/assets")) {
      return handleAssets(event);
    }
    return respond(404, { error: "Route not found" });
  } catch (err: any) {
    console.error(`[${config.stage}] Error:`, err.message);
    return respond(500, { error: "Internal server error" });
  }
}

async function handleProducts(event: APIGatewayEvent): Promise<ApiResponse<string>> {
  const productId = event.pathParameters?.id;

  if (event.httpMethod === "GET" && productId) {
    const product = await getProduct(productId);
    if (!product) return respond(404, { error: "Product not found" });
    return respond(200, product);
  }
  if (event.httpMethod === "GET") {
    const products = await scanProducts();
    return respond(200, { items: products });
  }
  if (event.httpMethod === "POST") {
    const product: Product = JSON.parse(event.body || "{}");
    await putProduct(product);
    await sendOrderEvent("ORDER_CREATED", product.productId, { name: product.name });
    return respond(201, { message: "Product created" });
  }
  if (event.httpMethod === "DELETE" && productId) {
    await deleteProduct(productId);
    return respond(200, { message: "Product deleted" });
  }
  return respond(405, { error: "Method not allowed" });
}

async function handleAssets(event: APIGatewayEvent): Promise<ApiResponse<string>> {
  if (event.httpMethod === "GET") {
    const prefix = event.queryStringParameters?.prefix || "";
    const keys = await listFiles(prefix);
    return respond(200, { keys });
  }
  if (event.httpMethod === "POST") {
    const { key, contentType, data } = JSON.parse(event.body || "{}");
    const uri = await uploadFile({ key, contentType, data });
    return respond(201, { uri });
  }
  return respond(405, { error: "Method not allowed" });
}
