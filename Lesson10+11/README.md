# Lesson 10 + 11: Flask API on ECS + MySQL on RDS

## Architecture

```
                                 Internet  (browser / curl)
                                 │  http://<PUBLIC_IP>:5000
                                 ▼
┌── AWS Region ap-southeast-1 (Singapore) ─────────────────────────────────────────────────────────┐
│ ┌─ VPC ────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │                     ┌──────────────────┐                                                     │ │
│ │                     │ Internet Gateway │                                                     │ │
│ │                     └────────┬─────────┘                                                     │ │
│ │                              ▼ :5000                                                         │ │
│ │ ┌─ Public subnet ────────────────────────┐        ┌─ Private subnets (DB subnet group) ────┐ │ │
│ │ │ route: 0.0.0.0/0 → IGW                 │        │ route: local only, no IGW              │ │ │
│ │ │                                        │        │                                        │ │ │
│ │ │ ┌─ sg-ecs-api ───────────────────────┐ │        │ ┌─ sg-rds-mysql ─────────────────────┐ │ │ │
│ │ │ │ in: TCP 5000 from 0.0.0.0/0        │ │        │ │ in: TCP 3306 from sg-ecs-api       │ │ │ │
│ │ │ │                                    │ │        │ │                                    │ │ │ │
│ │ │ │ ┌────────────────────────────────┐ │ │  3306  │ │ ┌────────────────────────────────┐ │ │ │ │
│ │ │ │ │ ECS Fargate task               │ │ │───────▶│ │ │ RDS MySQL 8.4 (db.t4g.micro)   │ │ │ │ │
│ │ │ │ │ Flask API (gunicorn :5000)     │ │ │        │ │ │ database: appdb, table: users  │ │ │ │ │
│ │ │ │ │ image: flask-mysql-api:v1      │ │ │        │ │ │ public access: No              │ │ │ │ │
│ │ │ │ │ public IP: yes                 │ │ │        │ │ │ no public IP                   │ │ │ │ │
│ │ │ │ └────────────────────────────────┘ │ │        │ │ └────────────────────────────────┘ │ │ │ │
│ │ │ └────────────────────────────────────┘ │        │ └────────────────────────────────────┘ │ │ │
│ │ └────────────────────────────────────────┘        └────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                  │
│ ECR flask-mysql-api:v1  ── pull image ──▶  ECS task (via ecsTaskExecutionRole)                   │
│ ECS task  ── container logs ──▶  CloudWatch Logs /ecs/flask-mysql-api                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

Developer Mac ── docker buildx --platform linux/amd64 --push ──▶ ECR
```

## Project files

| File | Purpose |
|---|---|
| `app/app.py` | Flask API, connects to MySQL with env vars `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |
| `app/Dockerfile` | Image runs gunicorn on port 5000 |
| `docker-compose.yml` | Local test (API + MySQL) |

Endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/` | Hello message |
| GET | `/health` | Checks the DB connection, returns MySQL version |
| GET | `/users` | List users |
| POST | `/users` | Create user `{"name": "...", "email": "..."}` |
| DELETE | `/users/<id>` | Delete user |

---

## Step 0: Test locally

```bash
docker compose up -d --build
curl localhost:8088/health
curl -X POST localhost:8088/users -H 'Content-Type: application/json' -d '{"name":"Thanh","email":"t@example.com"}'
curl localhost:8088/users
docker compose down -v
```

(Port 8088 is used locally because 5000 is taken by macOS AirPlay.)

## Step 1: Build and push the image

> **Mac M1/M2/M3 users:** you must build for `linux/amd64`, otherwise ECS fails with `exec format error`.

### Option A: Docker Hub (simplest, no AWS CLI needed)

```bash
docker login
docker buildx build --platform linux/amd64 -t <dockerhub-username>/flask-mysql-api:v1 --push ./app
```

The image URI for ECS is `docker.io/<dockerhub-username>/flask-mysql-api:v1` (the repo must be public).

### Option B: Amazon ECR

```bash
brew install awscli
aws configure            # Access key, secret key, region ap-southeast-1
aws ecr create-repository --repository-name flask-mysql-api
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-southeast-1
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker buildx build --platform linux/amd64 -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/flask-mysql-api:v1 --push ./app
```

## Step 2: Create two Security Groups

In the AWS Console, go to **EC2 → Security Groups → Create security group**, in the same VPC as your subnets:

1. **sg-ecs-api**
   - Inbound: Custom TCP, port `5000`, source `0.0.0.0/0`
2. **sg-rds-mysql**
   - Inbound: MySQL/Aurora, port `3306`, source = **sg-ecs-api** (pick the security group, not an IP)

This rule means only the ECS task can reach the DB.

## Step 3: Create the RDS MySQL database

Go to **RDS → Create database**:

- Creation method: **Standard create**
- Engine: **MySQL 8.4** (8.0 also works)
- Template: **Free tier**
- DB instance identifier: `lesson10-mysql`
- Master username: `admin`, and set a master password (write it down)
- Instance class: `db.t3.micro` or `db.t4g.micro`
- Storage: 20 GB gp2/gp3, turn off storage autoscaling
- Connectivity:
  - VPC: the same VPC as the ECS subnets
  - DB subnet group: a group with **private subnets only** (at least 2 AZs; route table has no route to the Internet Gateway). Create it first in **RDS → Subnet groups** if needed.
  - **Public access: No**
  - VPC security group: choose existing **sg-rds-mysql** (remove `default`)
- **Additional configuration → Initial database name: `appdb`** (important: if you skip this, the DB doesn't exist)
- Turn off automated backups and enhanced monitoring to save cost

Wait about 5–10 minutes until the status is **Available**. Copy the **Endpoint**, for example
`lesson10-mysql.xxxxxx.ap-southeast-1.rds.amazonaws.com`.

## Step 4: Create the ECS cluster

Go to **ECS → Clusters → Create cluster**:
- Name: `lesson10-cluster`
- Infrastructure: **AWS Fargate (serverless)**

## Step 5: Create the task definition

Go to **ECS → Task definitions → Create new task definition**:

- Family: `flask-mysql-api`
- Launch type: **AWS Fargate**
- OS/Architecture: **Linux/X86_64**
- CPU `0.25 vCPU`, Memory `0.5 GB`
- Task execution role: **Create new role** (or `ecsTaskExecutionRole`)
- Container:
  - Name: `api`
  - Image URI: the image from Step 1
  - Container port: `5000`, TCP, app protocol HTTP
  - Environment variables:

    | Key | Value |
    |---|---|
    | `DB_HOST` | RDS endpoint from Step 3 |
    | `DB_PORT` | `3306` |
    | `DB_USER` | `admin` |
    | `DB_PASSWORD` | your master password |
    | `DB_NAME` | `appdb` |

  - Log collection: keep **CloudWatch** on, so you can debug

> For a real project, put `DB_PASSWORD` in Secrets Manager or SSM Parameter Store ("ValueFrom") instead of plain text.

## Step 6: Run the service

Open the cluster `lesson10-cluster` → **Services → Create**:

- Launch type: **FARGATE**
- Task definition: `flask-mysql-api` (latest revision)
- Service name: `flask-api-svc`, Desired tasks: `1`
- Networking:
  - VPC: the same VPC, subnets: **public subnets only** (route table has `0.0.0.0/0 → Internet Gateway`)
  - Security group: **sg-ecs-api** only (remove `default`)
  - **Public IP: Turned ON** (without this the task can't pull images or be reached)
- Load balancing: None

Wait until the task is **Running**.

## Step 7: Get the public IP and test

Open the cluster → **Tasks** → the task → **Configuration** → **Public IP**.

```bash
curl http://<PUBLIC_IP>:5000/health
curl -X POST http://<PUBLIC_IP>:5000/users -H 'Content-Type: application/json' -d '{"name":"Thanh","email":"t@example.com"}'
curl http://<PUBLIC_IP>:5000/users
```

`/health` should return `"db":"connected"`, which proves ECS connects to RDS.

**To submit:** send the link `http://<PUBLIC_IP>:5000/health`, plus screenshots of the architecture above and the AWS Console (RDS Available, ECS task Running, the browser showing the result).

> The public IP changes every time the task restarts. To get a fixed URL, put an Application Load Balancer in front (outside this exercise's scope).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Task stops with `exec format error` | Image built for ARM; rebuild with `--platform linux/amd64` |
| `CannotPullContainerError` | Public IP not enabled, or the Docker Hub repo is private |
| `/health` → `Can't connect to MySQL ... timed out` | sg-rds-mysql has no inbound 3306 from sg-ecs-api, or RDS isn't in the same VPC |
| `Unknown database 'appdb'` | You skipped "Initial database name" in RDS; recreate it, or set `DB_NAME` to an existing DB |
| `Access denied for user` | Wrong `DB_USER`/`DB_PASSWORD` |
| curl to the public IP times out | sg-ecs-api has no inbound 5000 |

Logs: ECS → Task → **Logs** tab (CloudWatch).

## Cleanup (avoid charges!)

1. ECS: update the service to desired tasks 0 → delete the service → delete the cluster
2. RDS: delete `lesson10-mysql` (untick "Create final snapshot")
3. Delete the security groups, the ECR repo (if used), and the CloudWatch log group `/ecs/flask-mysql-api`
