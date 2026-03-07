// Pub/Sub messaging operations for order events

import { pubsubClient, config } from "./config";
import { QueueMessage } from "./types";

const TOPIC_NAME = config.pubsubTopic;

export async function publishMessage(message: QueueMessage): Promise<string> {
  const topic = pubsubClient.topic(TOPIC_NAME);
  const data = Buffer.from(JSON.stringify(message));
  const messageId = await topic.publishMessage({
    data,
    attributes: {
      eventType: message.eventType,
    },
  });
  return messageId;
}

export async function pollMessages(maxCount: number = 10): Promise<QueueMessage[]> {
  const subscription = pubsubClient.subscription(`${TOPIC_NAME}-sub`);
  const [messages] = await subscription.pull({
    maxMessages: Math.min(maxCount, 10),
  });
  return messages.map((msg) => ({
    messageId: msg.message.messageId,
    ...JSON.parse(msg.message.data?.toString() || "{}"),
  }));
}

export async function acknowledgeMessage(ackId: string): Promise<void> {
  const subscription = pubsubClient.subscription(`${TOPIC_NAME}-sub`);
  await subscription.acknowledge([ackId]);
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
