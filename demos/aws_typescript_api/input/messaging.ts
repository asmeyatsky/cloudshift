// SQS messaging operations for order events

import {
  SendMessageCommand,
  ReceiveMessageCommand,
  DeleteMessageCommand,
} from "@aws-sdk/client-sqs";
import { sqsClient, config } from "./config";
import { QueueMessage } from "./types";

const QUEUE_URL = config.sqsQueueUrl;

export async function publishMessage(message: QueueMessage): Promise<string> {
  const command = new SendMessageCommand({
    QueueUrl: QUEUE_URL,
    MessageBody: JSON.stringify(message),
    MessageAttributes: {
      eventType: {
        DataType: "String",
        StringValue: message.eventType,
      },
    },
    DelaySeconds: 0,
  });
  const result = await sqsClient.send(command);
  return result.MessageId || "";
}

export async function pollMessages(maxCount: number = 10): Promise<QueueMessage[]> {
  const command = new ReceiveMessageCommand({
    QueueUrl: QUEUE_URL,
    MaxNumberOfMessages: Math.min(maxCount, 10),
    WaitTimeSeconds: 5,
    MessageAttributeNames: ["All"],
  });
  const result = await sqsClient.send(command);
  if (!result.Messages) return [];
  return result.Messages.map((msg) => ({
    messageId: msg.MessageId,
    ...JSON.parse(msg.Body || "{}"),
  }));
}

export async function acknowledgeMessage(receiptHandle: string): Promise<void> {
  const command = new DeleteMessageCommand({
    QueueUrl: QUEUE_URL,
    ReceiptHandle: receiptHandle,
  });
  await sqsClient.send(command);
}

export async function sendOrderEvent(
  eventType: QueueMessage["eventType"],
  orderId: string,
  details: Record<string, unknown>
): Promise<string> {
  const message: QueueMessage = {
    eventType,
    payload: { orderId, ...details },
    timestamp: new Date().toISOString(),
  };
  return publishMessage(message);
}
