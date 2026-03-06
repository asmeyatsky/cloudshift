import { DynamoDBClient, PutItemCommand, GetItemCommand, QueryCommand, DeleteItemCommand } from "@aws-sdk/client-dynamodb";
import { marshall, unmarshall } from "@aws-sdk/util-dynamodb";

const client = new DynamoDBClient({ region: "us-east-1" });
const TABLE_NAME = "users";

export async function putUser(id: string, name: string, email: string): Promise<void> {
    await client.send(new PutItemCommand({
        TableName: TABLE_NAME,
        Item: marshall({ id, name, email }),
    }));
}

export async function getUser(id: string): Promise<Record<string, any> | null> {
    const response = await client.send(new GetItemCommand({
        TableName: TABLE_NAME,
        Key: marshall({ id }),
    }));
    return response.Item ? unmarshall(response.Item) : null;
}

export async function queryByEmail(email: string): Promise<Record<string, any>[]> {
    const response = await client.send(new QueryCommand({
        TableName: TABLE_NAME,
        IndexName: "email-index",
        KeyConditionExpression: "email = :email",
        ExpressionAttributeValues: marshall({ ":email": email }),
    }));
    return (response.Items || []).map(item => unmarshall(item));
}

export async function deleteUser(id: string): Promise<void> {
    await client.send(new DeleteItemCommand({
        TableName: TABLE_NAME,
        Key: marshall({ id }),
    }));
}
