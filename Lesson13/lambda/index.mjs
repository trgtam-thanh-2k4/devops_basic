// Lambda handler for API Gateway (HTTP API, payload v2.0)
//   GET /users        -> list all users (Scan)
//   GET /users/{id}   -> one user (GetItem)
// The AWS SDK v3 is already included in the Node.js 20.x runtime, so no npm install is needed.
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, ScanCommand, GetCommand } from "@aws-sdk/lib-dynamodb";

const TABLE_NAME = process.env.TABLE_NAME;

// Created outside the handler so warm invocations reuse the connection
const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));

const json = (statusCode, body) => ({
  statusCode,
  headers: {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
  },
  body: JSON.stringify(body),
});

export const handler = async (event) => {
  console.log("request", event.requestContext?.http?.method, event.rawPath);

  if (!TABLE_NAME) {
    return json(500, { message: "TABLE_NAME env var is not set" });
  }

  try {
    const id = event.pathParameters?.id;

    if (id) {
      const { Item } = await ddb.send(new GetCommand({ TableName: TABLE_NAME, Key: { id } }));
      return Item ? json(200, Item) : json(404, { message: `User ${id} not found` });
    }

    // Scan returns max 1 MB per call, so follow LastEvaluatedKey until done
    const users = [];
    let ExclusiveStartKey;
    do {
      const page = await ddb.send(new ScanCommand({ TableName: TABLE_NAME, ExclusiveStartKey }));
      users.push(...page.Items);
      ExclusiveStartKey = page.LastEvaluatedKey;
    } while (ExclusiveStartKey);

    users.sort((a, b) => a.id.localeCompare(b.id));
    return json(200, { count: users.length, users });
  } catch (err) {
    console.error(err);
    return json(500, { message: err.name, detail: err.message });
  }
};
