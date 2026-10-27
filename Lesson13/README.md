# Lesson 13: Node.js Lambda + DynamoDB + API Gateway

**Requirement:** Deploy a Node.js (or Python) project that connects to DynamoDB, with Lambda memory set to **1 GB**.
- Write a `GET users` API
- Submit the API Gateway link
- Screenshots: Lambda env vars, code editor (VS Code in Lambda), handler, Lambda permissions

## Architecture

```
 Browser / curl ── HTTPS ──▶ API Gateway (HTTP API)  lesson13-users-api
                               GET /users        ┐
                               GET /users/{id}   ┘ Lambda proxy integration (payload v2.0)
                                  │  resource-based policy: apigateway → lambda:InvokeFunction
                                  ▼
                             Lambda  lesson13-get-users   (Node.js 20.x, 1024 MB, handler index.handler)
                               env TABLE_NAME=lesson13-users
                                  │  execution role: dynamodb:Scan, dynamodb:GetItem
                                  ▼
                             DynamoDB table  lesson13-users   (partition key: id, String, on-demand)
```

Two kinds of permissions are involved, and both show up in the **Permissions** tab:
- **Execution role** (what Lambda is allowed to call): read access to the DynamoDB table.
- **Resource-based policy** (who is allowed to call Lambda): API Gateway. The console adds it when you attach the trigger.

## Project files

| File | Purpose |
|---|---|
| `lambda/index.mjs` | Lambda handler: `GET /users` (Scan) and `GET /users/{id}` (GetItem) |
| `lambda/package.json` | Only for local testing. The Node.js 20.x runtime already ships AWS SDK v3 |
| `lambda/test-local.mjs` | Optional: call the handler from your Mac |
| `dynamodb/users.json` | Sample users (readable form) |
| `dynamodb/seed-batch.json` | Same users in `batch-write-item` format for CloudShell |
| `iam/dynamodb-read-policy.json` | Least-privilege inline policy for the execution role |

Region: `ap-southeast-1` (same as earlier lessons).

---

## Step 1: Create the DynamoDB table

AWS Console → **DynamoDB** → **Tables** → **Create table**
- Table name: `lesson13-users`
- Partition key: `id` · type **String**
- Sort key: none
- Table settings: **Customize settings** → Capacity mode **On-demand** (pay per request, nearly free for this lab)
- → **Create table**, wait for status **Active**

📸 Evidence: `evidence/01-dynamodb-table.png`

## Step 2: Add sample users

**Option A: CloudShell (fast).** Open **CloudShell** (the `>_` icon in the top bar) → **Actions** → **Upload file** → choose `dynamodb/seed-batch.json`, then:

```bash
aws dynamodb batch-write-item --request-items file://seed-batch.json
aws dynamodb scan --table-name lesson13-users --select COUNT    # "Count": 5
```

**Option B: Console.** Table → **Explore table items** → **Create item** → **JSON view**, turn **off** "View DynamoDB JSON", paste one object from `dynamodb/users.json` → **Create item**. Repeat a few times.

📸 Evidence: `evidence/02-dynamodb-items.png`

## Step 3: Create the Lambda function

Lambda → **Functions** → **Create function**
- **Author from scratch**
- Function name: `lesson13-get-users`
- Runtime: **Node.js 24.x** (or 20.x/22.x, all include AWS SDK v3)
- Permissions: nothing to choose. By default Lambda creates a new execution role with CloudWatch Logs access only. DynamoDB access is added in Step 6.
- **Additional settings**: leave every toggle OFF (ARM64, Custom execution role, Function URL, VPC…). API Gateway is used instead of a Function URL.
- → **Create function** (newer consoles label it **Create Event Function**)

## Step 4: Paste the code (VS Code in Lambda)

Function → tab **Code**. The editor is the VS Code based Code OSS editor.
- Open `index.mjs` in the Explorer on the left, delete the sample code, paste the content of `lambda/index.mjs`
- Click **Deploy** (or `Cmd+Shift+U`). Wait for "Successfully updated the function".

📸 Evidence: `evidence/03-lambda-code-editor.png` (show the editor with the code and the Deploy success message)

## Step 5: Configuration: memory 1 GB, env, handler

**Memory 1 GB:** Tab **Configuration** → **General configuration** → **Edit**
- Memory: **1024 MB**
- Timeout: `10 sec` (default 3 sec is tight for a cold start + Scan)
- → **Save**

📸 Evidence: `evidence/04-lambda-memory-1gb.png`

**Environment variables:** **Configuration** → **Environment variables** → **Edit** → **Add environment variable**
- Key `TABLE_NAME` · Value `lesson13-users` → **Save**

You don't need `AWS_REGION`. Lambda sets it automatically and the SDK reads it.

📸 Evidence: `evidence/05-lambda-env.png`

**Handler:** Tab **Code** → scroll down to **Runtime settings** → it must show **Handler `index.handler`** (file `index.mjs`, exported function `handler`). If you renamed the file, click **Edit** and change it to match.

📸 Evidence: `evidence/06-lambda-handler.png`

## Step 6: Give Lambda access to DynamoDB (execution role)

**Configuration** → **Permissions** → under *Execution role* click the role name (`lesson13-get-users-role-xxxx`). This opens IAM.
- **Add permissions** → **Create inline policy** → tab **JSON**
- Paste `iam/dynamodb-read-policy.json` and replace `<ACCOUNT_ID>` with your 12-digit account ID (top-right menu in the console)
- **Next** → Policy name `lesson13-dynamodb-read` → **Create policy**

Least privilege: only `Scan` and `GetItem`, and only on this one table. Using `AmazonDynamoDBReadOnlyAccess` also works but grants read on every table.

## Step 7: Test inside Lambda

Tab **Test** → **Create new event**
- Event name: `get-users` · Template: **API Gateway HTTP API** (or paste the JSON below)

```json
{
  "rawPath": "/users",
  "requestContext": { "http": { "method": "GET" } }
}
```

→ **Test**. Expected: `statusCode: 200` and the body contains `"count": 5`. In the log output, check **Max memory used** and **Memory size: 1024 MB**.

If you see `AccessDeniedException ... dynamodb:Scan`, Step 6 isn't done or the table ARN in the policy is wrong.

📸 Evidence: `evidence/07-lambda-test.png`

## Step 8: Create the API Gateway

API Gateway → **Create API** → **HTTP API** → **Build**
1. **Create and configure integrations**: **Add integration** → **Lambda** → region `ap-southeast-1` → function `lesson13-get-users` · Version **2.0** · API name `lesson13-users-api`
2. **Configure routes**:
   - Method `GET` · Resource path `/users` · Integration target `lesson13-get-users`
   - **Add route**: Method `GET` · Resource path `/users/{id}` · same target
3. **Define stages**: keep `$default` with **Auto-deploy** ON
4. **Review and create** → **Create**

Copy the **Invoke URL** (for example `https://abc123xyz.execute-api.ap-southeast-1.amazonaws.com`). This is the link to submit:

```
https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/users
```

📸 Evidence: `evidence/08-api-gateway-routes.png`

## Step 9: Lambda permissions (resource-based policy)

Back in Lambda → **Configuration** → **Permissions** → scroll to **Resource-based policy statements**. You should see a statement that allows principal `apigateway.amazonaws.com` to call `lambda:InvokeFunction`, with a source ARN like `arn:aws:execute-api:ap-southeast-1:<account>:<api-id>/*/*/users`.

The function **Diagram** at the top of the page should also show **API Gateway** as a trigger.

📸 Evidence: `evidence/09-lambda-permissions-role.png` (execution role + its policies), `evidence/10-lambda-resource-policy.png` (API Gateway statement)

## Step 10: Verify

```bash
API=https://<api-id>.execute-api.ap-southeast-1.amazonaws.com
curl -s $API/users | python3 -m json.tool        # 200, count 5
curl -s $API/users/u002 | python3 -m json.tool   # 200, Tran Thi Binh
curl -i $API/users/nope                          # 404
curl -i $API/                                    # 404 {"message":"Not Found"} from API Gateway (no route)
```

Open `$API/users` in the browser too.

📸 Evidence: `evidence/11-browser-users.png`, `evidence/12-curl.png`, optional `evidence/13-cloudwatch-logs.png` (Monitor → View CloudWatch logs)

## Optional: run the handler locally

Needs the AWS CLI configured on your Mac (`aws configure`).

```bash
cd Lesson13/lambda
npm install
TABLE_NAME=lesson13-users AWS_REGION=ap-southeast-1 node test-local.mjs
TABLE_NAME=lesson13-users AWS_REGION=ap-southeast-1 node test-local.mjs u001
```

## Submission checklist

- [ ] API link: `https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/users`
- [ ] Lambda env (`TABLE_NAME`)
- [ ] VS Code editor in Lambda with the code
- [ ] Handler `index.handler`
- [ ] Lambda permissions: execution role + resource-based policy
- [ ] Memory 1024 MB

## Clean up (after the grade)

1. API Gateway → `lesson13-users-api` → **Delete**
2. Lambda → `lesson13-get-users` → **Actions** → **Delete**
3. IAM → Roles → `lesson13-get-users-role-xxxx` → **Delete**
4. CloudWatch → Log groups → `/aws/lambda/lesson13-get-users` → **Delete**
5. DynamoDB → `lesson13-users` → **Delete**

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `{"message":"Internal Server Error"}` from API | Lambda crashed or timed out. Check CloudWatch logs |
| `AccessDeniedException ... not authorized to perform: dynamodb:Scan` | Inline policy missing, or wrong account ID / region / table name in the ARN |
| `ResourceNotFoundException` | `TABLE_NAME` typo, or table is in another region than the Lambda |
| `{"message":"TABLE_NAME env var is not set"}` | Step 5 env var not saved |
| `Runtime.ImportModuleError` / `handler is undefined` | Handler isn't `index.handler`, or file was saved as `index.js` instead of `index.mjs` |
| `{"message":"Not Found"}` | Route missing. Call `/users`, not the bare invoke URL |
| Code changes don't apply | You didn't click **Deploy** in the editor |
| `Task timed out after 3.00 seconds` | Raise timeout to 10 sec (Step 5) |
