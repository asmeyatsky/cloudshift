// DynamoDB operations for products and orders

import {
  PutItemCommand,
  GetItemCommand,
  QueryCommand,
  ScanCommand,
  DeleteItemCommand,
  BatchWriteItemCommand,
} from "@aws-sdk/client-dynamodb";
import { dynamoClient, config } from "./config";
import { Product, Order, PaginatedResult } from "./types";

const PRODUCTS_TABLE = config.dynamoTableProducts;
const ORDERS_TABLE = config.dynamoTableOrders;

export async function putProduct(product: Product): Promise<void> {
  const command = new PutItemCommand({
    TableName: PRODUCTS_TABLE,
    Item: {
      productId: { S: product.productId },
      name: { S: product.name },
      price: { N: String(product.price) },
      category: { S: product.category },
      createdAt: { S: product.createdAt },
    },
  });
  await dynamoClient.send(command);
}

export async function getProduct(productId: string): Promise<Product | null> {
  const command = new GetItemCommand({
    TableName: PRODUCTS_TABLE,
    Key: { productId: { S: productId } },
  });
  const result = await dynamoClient.send(command);
  if (!result.Item) return null;
  return {
    productId: result.Item.productId.S!,
    name: result.Item.name.S!,
    description: result.Item.description?.S || "",
    price: Number(result.Item.price.N),
    category: result.Item.category.S!,
    createdAt: result.Item.createdAt.S!,
    updatedAt: result.Item.updatedAt?.S || "",
  };
}

export async function queryOrdersByCustomer(
  customerId: string
): Promise<PaginatedResult<Order>> {
  const command = new QueryCommand({
    TableName: ORDERS_TABLE,
    KeyConditionExpression: "customerId = :cid",
    ExpressionAttributeValues: { ":cid": { S: customerId } },
    Limit: 25,
  });
  const result = await dynamoClient.send(command);
  const items = (result.Items || []).map((item) => ({
    orderId: item.orderId.S!,
    customerId: item.customerId.S!,
    items: JSON.parse(item.items.S || "[]"),
    totalAmount: Number(item.totalAmount.N),
    status: item.status.S as Order["status"],
    createdAt: item.createdAt.S!,
  }));
  return { items, count: result.Count || 0 };
}

export async function scanProducts(): Promise<Product[]> {
  const command = new ScanCommand({ TableName: PRODUCTS_TABLE, Limit: 50 });
  const result = await dynamoClient.send(command);
  return (result.Items || []).map((item) => ({
    productId: item.productId.S!,
    name: item.name.S!,
    description: item.description?.S || "",
    price: Number(item.price.N),
    category: item.category.S!,
    createdAt: item.createdAt.S!,
    updatedAt: item.updatedAt?.S || "",
  }));
}

export async function deleteProduct(productId: string): Promise<void> {
  const command = new DeleteItemCommand({
    TableName: PRODUCTS_TABLE,
    Key: { productId: { S: productId } },
  });
  await dynamoClient.send(command);
}

export async function batchWriteProducts(products: Product[]): Promise<void> {
  const requests = products.map((p) => ({
    PutRequest: {
      Item: {
        productId: { S: p.productId },
        name: { S: p.name },
        price: { N: String(p.price) },
        category: { S: p.category },
        createdAt: { S: p.createdAt },
      },
    },
  }));
  const command = new BatchWriteItemCommand({
    RequestItems: { [PRODUCTS_TABLE]: requests },
  });
  await dynamoClient.send(command);
}
