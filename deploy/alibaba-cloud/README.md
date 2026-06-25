// NOTICE: This file is protected under RCF-PL
# Deploying AladdinAI on Alibaba Cloud ECS

AladdinAI is deployed and running on Alibaba Cloud ECS (Elastic Compute Service) as a self-hosted AI agent platform.

## Instance Configuration

- **Provider:** Alibaba Cloud ECS
- **OS:** Ubuntu 24.04 LTS
- **Deployment method:** Docker via `npx aladdin-ai`

## Setup Steps

### 1. Create ECS Instance
- Go to Alibaba Cloud Console → Elastic Compute Service
- Create instance (recommended: 4 vCPU, 8GB RAM, Ubuntu 24.04)
- Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3000 (AladdinAI UI), 8000 (API)

### 2. Connect via SSH
```bash
ssh root@<your-ecs-ip>
```

### 3. Install dependencies
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs git
```

### 4. Deploy AladdinAI
```bash
npx aladdin-ai
```

### 5. Access the platform
Open `http://<your-ecs-ip>:3000` in your browser.

## OSS Bucket (Optional)

Mount an Alibaba Cloud OSS Bucket to `/mnt/data` for persistent file storage across instance restarts.

## Live deployment

AladdinAI agent platform is live and running on Alibaba Cloud ECS.
