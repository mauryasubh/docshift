# DocShift: Multi-Cloud Production Setup Guide

This guide provides step-by-step instructions for spinning up the required infrastructure for DocShift using AWS ECS (Fargate), Cloudflare R2, Neon Postgres, and Upstash Redis.

## Phase 1: Third-Party Prerequisites (The "Serverless" Layer)

Before touching AWS, you need to set up the specialized third-party services that will save you money and headaches.

### 1. Cloudflare R2 (Storage)
1. Go to the Cloudflare Dashboard -> R2.
2. Create a new bucket (e.g., `docshift-storage`).
3. Click "Manage R2 API Tokens" and create a new token with "Object Read & Write" permissions.
4. **Collect the following variables:**
   - `AWS_ACCESS_KEY_ID` (from Cloudflare token)
   - `AWS_SECRET_ACCESS_KEY` (from Cloudflare token)
   - `AWS_STORAGE_BUCKET_NAME` (e.g., `docshift-storage`)
   - `AWS_S3_ENDPOINT_URL` (looks like `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`)

### 2. Upstash Redis (Queue Broker)
1. Go to [console.upstash.com](https://console.upstash.com/).
2. Create a new Redis Database (Serverless). Select the region closest to where your AWS servers will be (e.g., `us-east-1`).
3. Scroll down to the "Connect" section.
4. **Collect the following variable:**
   - `CELERY_BROKER_URL` (Usually starts with `rediss://...`)

### 3. Neon Postgres (Database)
1. Go to [neon.tech](https://neon.tech/) and sign up.
2. Create a new project/database. Again, match the region to your AWS region (e.g., `us-east-1`).
3. On the dashboard, find the "Connection Details".
4. **Collect the following variable:**
   - `DATABASE_URL` (Starts with `postgres://...`)

---

## Phase 2: AWS Infrastructure Setup

Log into your AWS Management Console.

### 1. Set up the Container Registry (ECR)
1. Navigate to **Elastic Container Registry (ECR)** in AWS.
2. Click **Create repository**.
3. Name it `docshift-app`. Keep it "Private".
4. Click Create.
5. Click on the repository you just created and click **"View push commands"**. 
   - *You will use these commands on your local machine to build your Docker image and push it to AWS.*

### 2. Setup Security Groups
1. Navigate to **EC2** -> **Security Groups**.
2. **Create ALB Security Group**: Allow inbound HTTP (port 80) and HTTPS (port 443) from `Anywhere-IPv4` (0.0.0.0/0).
3. **Create ECS Security Group**: Allow inbound Custom TCP on port `8000` (or whatever port Gunicorn uses), but **only** allow traffic originating from the *ALB Security Group* you just created.

### 3. Create the Application Load Balancer (ALB)
1. Navigate to **EC2** -> **Load Balancers**.
2. Click **Create Load Balancer** -> Choose **Application Load Balancer**.
3. Name it `docshift-alb`. Ensure it is "Internet-facing".
4. Select at least 2 Availability Zones.
5. Attach the **ALB Security Group** created above.
6. For Listeners and Routing, create a new Target Group (Target type: **IP addresses**, port 8000, Health check path: `/health/`).

### 4. Create the ECS Fargate Cluster
1. Navigate to **Elastic Container Service (ECS)**.
2. Click **Create cluster**. Name it `docshift-cluster`.
3. Choose **AWS Fargate** as the infrastructure.

### 5. Create Task Definitions
You need to tell ECS *how* to run your Docker image.
1. Navigate to **Task Definitions** -> **Create new task definition**.
2. Name it `docshift-web-task`.
3. Select **AWS Fargate**. Choose your desired CPU/Memory (e.g., 0.5 vCPU, 1 GB RAM).
4. In the Container section:
   - Name: `web`
   - Image URI: Paste the URI from your ECR repository (e.g., `<account-id>.dkr.ecr.us-east-1.amazonaws.com/docshift-app:latest`)
   - Port mappings: `8000` (TCP)
   - Command: `gunicorn docshift.wsgi:application --bind 0.0.0.0:8000`
   - Environment Variables: Add all the keys collected in Phase 1 (`DATABASE_URL`, `CELERY_BROKER_URL`, etc.)
5. **Repeat this exact process** to create a second Task Definition named `docshift-worker-task`.
   - Use the *same Image URI*.
   - Command: `celery -A docshift worker -l info`
   - *No port mappings needed for the worker!*

### 6. Launch the Services
1. Go back to your `docshift-cluster`.
2. Click **Create Service**.
3. Select your `docshift-web-task` definition.
4. Under Networking, select your VPC and subnets, and choose the **ECS Security Group**.
5. Under Load Balancing, select the ALB and Target Group you created earlier.
6. Click Create.
7. **Repeat this process** to create a second Service for your `docshift-worker-task` (but do *not* attach a load balancer to the worker service).

---

## Phase 3: Final Wiring

1. Get the DNS name of your Load Balancer from the EC2 dashboard.
2. Go to Cloudflare DNS and create a `CNAME` record pointing your domain (e.g., `docshift.com`) to the AWS ALB DNS name. Make sure the proxy status is "Proxied" (Orange Cloud).

🎉 **You are live!**
