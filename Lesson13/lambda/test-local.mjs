// Optional: run the handler on your Mac against the real table.
// Needs AWS credentials in your shell and `npm install` in this folder.
//   TABLE_NAME=lesson13-users AWS_REGION=ap-southeast-1 node test-local.mjs [id]
import { handler } from "./index.mjs";

const id = process.argv[2];
const event = {
  rawPath: id ? `/users/${id}` : "/users",
  requestContext: { http: { method: "GET" } },
  pathParameters: id ? { id } : undefined,
};

const res = await handler(event);
console.log(res.statusCode, JSON.stringify(JSON.parse(res.body), null, 2));
