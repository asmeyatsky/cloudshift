// Types and interfaces for the REST API models

export interface ApiResponse<T = unknown> {
  statusCode: number;
  body: T;
  headers?: Record<string, string>;
}

export interface Product {
  productId: string;
  name: string;
  description: string;
  price: number;
  category: string;
  imageKey?: string;
  createdAt: string;
  updatedAt: string;
}

export interface OrderItem {
  productId: string;
  quantity: number;
  unitPrice: number;
}

export interface Order {
  orderId: string;
  customerId: string;
  items: OrderItem[];
  totalAmount: number;
  status: "pending" | "processing" | "shipped" | "delivered" | "cancelled";
  createdAt: string;
}

export interface QueueMessage {
  messageId?: string;
  eventType: "ORDER_CREATED" | "ORDER_UPDATED" | "INVENTORY_LOW";
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface PaginatedResult<T> {
  items: T[];
  lastKey?: string;
  count: number;
}

export interface StorageUpload {
  key: string;
  contentType: string;
  data: Buffer | string;
}
