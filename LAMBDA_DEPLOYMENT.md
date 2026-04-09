# AWS Lambda Deployment Guide for GenPRAgent

Complete guide to deploy GenPRAgent as an AWS Lambda function with API Gateway.

---

## 📋 Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed (for building container images)
4. **AWS SAM CLI** (optional, for easier deployment)
5. **GitHub Personal Access Token**
6. **Anthropic API Key**

---

## 🎯 Deployment Options

### **Option 1: AWS SAM (Recommended)**

Easiest method with automatic API Gateway setup.

#### **Step 1: Install AWS SAM CLI**

**Mac:**
```bash
brew install aws-sam-cli
```

**Windows:**
Download from: https://aws.amazon.com/serverless/sam/

**Linux:**
```bash
pip install aws-sam-cli
```

**Verify installation:**
```bash
sam --version
```

#### **Step 2: Build the Application**

```bash
cd GenPRAgent

# Build the container image
sam build
```

#### **Step 3: Deploy to AWS**

```bash
# First deployment (interactive)
sam deploy --guided

# You'll be prompted for:
# - Stack Name: genpr-agent-stack
# - AWS Region: us-east-1 (or your preferred region)
# - GitHubToken: ghp_your_token_here
# - AnthropicApiKey: sk-ant-your_key_here
# - OpenAIApiKey: (optional, press Enter to skip)
# - DefaultModel: claude-sonnet-4-6
# - Confirm changes: Y
# - Allow SAM CLI IAM role creation: Y
# - Disable rollback: N
# - Save arguments to configuration file: Y
# - SAM configuration file: samconfig.toml
# - SAM configuration environment: default

# This will:
# 1. Create ECR repository
# 2. Build and push Docker image
# 3. Create Lambda function
# 4. Create API Gateway
# 5. Set up permissions
```

#### **Step 4: Get Your API URL**

After deployment, SAM will output:
```
Outputs
---------------------------------------------------------------
Key                 GenPRAgentApi
Description         API Gateway endpoint URL for GenPRAgent
Value               https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/
```

**Save this URL!**

#### **Step 5: Test Your Deployment**

```bash
# Health check
curl https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/health

# Create a PR
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "NullPointerException in UserService.java",
    "repo": "your-username/your-repo",
    "base_branch": "main"
  }'
```

#### **Subsequent Deployments**

```bash
# After making code changes
sam build
sam deploy  # Uses saved configuration
```

---

### **Option 2: Manual Deployment with AWS Console**

#### **Step 1: Create ECR Repository**

1. Go to AWS Console → ECR
2. Click "Create repository"
3. Repository name: `genpr-agent`
4. Click "Create repository"

#### **Step 2: Build and Push Docker Image**

```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # Change if needed

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
docker build -f Dockerfile.lambda -t genpr-agent:latest .

# Tag image
docker tag genpr-agent:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genpr-agent:latest

# Push image
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genpr-agent:latest
```

#### **Step 3: Create Lambda Function**

1. Go to AWS Console → Lambda
2. Click "Create function"
3. Select "Container image"
4. Function name: `genpr-agent`
5. Container image URI: Click "Browse images"
   - Select your ECR repository: `genpr-agent`
   - Select image tag: `latest`
6. Architecture: x86_64
7. Click "Create function"

#### **Step 4: Configure Lambda Function**

**Configuration → General configuration:**
- Memory: 2048 MB
- Timeout: 5 minutes (300 seconds)
- Ephemeral storage: 512 MB

**Configuration → Environment variables:**
Add these:
```
GITHUB_PERSONAL_ACCESS_TOKEN = ghp_your_token_here
ANTHROPIC_API_KEY = sk-ant-your_key_here
OPENAI_API_KEY = sk_your_openai_key (optional)
MODEL = claude-sonnet-4-6
HOST = 0.0.0.0
PORT = 8000
```

#### **Step 5: Create API Gateway**

1. Go to AWS Console → API Gateway
2. Click "Create API"
3. Choose "HTTP API" → Build
4. API name: `genpr-agent-api`
5. Click "Next"

**Configure routes:**
- Add integration: Lambda
- Select your Lambda function: `genpr-agent`
- Method: ANY
- Resource path: `/{proxy+}`
- Click "Next"

**Configure stages:**
- Stage name: `$default`
- Auto-deploy: Yes
- Click "Next" → "Create"

6. **Get your API URL:**
   - Format: `https://xxxxx.execute-api.us-east-1.amazonaws.com`

#### **Step 6: Test**

```bash
curl https://YOUR_API_GATEWAY_URL/health
```

---

### **Option 3: Using Deployment Script**

```bash
# Make script executable
chmod +x deploy-lambda.sh

# Configure AWS credentials
aws configure

# Run deployment
./deploy-lambda.sh
```

---

## 🔧 Configuration

### **Lambda Function Settings**

| Setting | Value | Why |
|---------|-------|-----|
| **Memory** | 2048 MB | Dependencies are large, MCP server needs memory |
| **Timeout** | 300 seconds (5 min) | PR creation with AI can take 30-60 seconds |
| **Ephemeral Storage** | 512 MB | Default is sufficient |
| **Architecture** | x86_64 | Better compatibility |

### **Environment Variables**

Required:
- `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub token
- `ANTHROPIC_API_KEY` - Anthropic API key

Optional:
- `OPENAI_API_KEY` - For GPT models
- `MODEL` - Default model (default: `claude-sonnet-4-6`)

---

## 📊 Monitoring

### **CloudWatch Logs**

View logs in AWS Console:
1. Lambda → Functions → genpr-agent
2. Monitor tab → View logs in CloudWatch

Or via CLI:
```bash
aws logs tail /aws/lambda/genpr-agent --follow
```

### **CloudWatch Metrics**

Monitor:
- **Invocations**: Number of API calls
- **Duration**: Execution time
- **Errors**: Failed invocations
- **Throttles**: Rate limit hits

### **Set Up Alarms**

Create CloudWatch alarms for:
- Error rate > 5%
- Duration > 280 seconds (near timeout)
- Throttles > 0

---

## 💰 Cost Estimation

### **Lambda Costs**

**Assumptions:**
- 1,000 requests/month
- 60 seconds average duration
- 2048 MB memory

**Costs:**
- Requests: 1,000 × $0.20/1M = $0.0002
- Duration: 1,000 × 60s × (2048/1024) × $0.0000166667 = $2.00
- **Total: ~$2-3/month**

**Free Tier (first 12 months):**
- 1M requests/month free
- 400,000 GB-seconds/month free

### **API Gateway Costs**

- $1.00 per million requests
- For 1,000 requests: ~$0.001

### **ECR Costs**

- $0.10/GB/month storage
- First 500 MB free
- Docker image (~1.5 GB): $0.15/month

### **Total Monthly Cost**

- **Light usage (1K requests)**: $2-3/month + API costs
- **Heavy usage (10K requests)**: $20-30/month + API costs

**Plus:** Anthropic/OpenAI API costs (pay-per-use)

---

## 🔒 Security Best Practices

### **1. Use AWS Secrets Manager**

Instead of environment variables:

```bash
# Store secrets
aws secretsmanager create-secret \
  --name genpr-agent/github-token \
  --secret-string "ghp_your_token_here"

aws secretsmanager create-secret \
  --name genpr-agent/anthropic-key \
  --secret-string "sk-ant-your_key_here"
```

Update Lambda to fetch from Secrets Manager (requires IAM permissions).

### **2. Restrict API Gateway**

Add API key requirement:
1. API Gateway → Authorizers
2. Create Lambda authorizer or API key

### **3. Enable CloudTrail**

Monitor all API calls to Lambda function.

### **4. Use IAM Roles**

Lambda execution role should have minimal permissions:
- CloudWatch Logs write
- Secrets Manager read (if using)
- No other AWS service access needed

---

## 🚨 Troubleshooting

### **Issue: Function timeout**

**Problem:** Lambda times out before PR is created

**Solution:**
```bash
# Increase timeout to 5 minutes
aws lambda update-function-configuration \
  --function-name genpr-agent \
  --timeout 300
```

### **Issue: Out of memory**

**Problem:** Function fails with memory error

**Solution:**
```bash
# Increase memory to 3GB
aws lambda update-function-configuration \
  --function-name genpr-agent \
  --memory-size 3008
```

### **Issue: Cold start timeout**

**Problem:** First request times out

**Solution:**
1. Enable Provisioned Concurrency (keeps 1 instance warm)
2. Or use Lambda SnapStart (if supported)
3. Or implement warming with EventBridge (ping every 5 minutes)

**Create warming rule:**
```bash
# Create EventBridge rule to ping every 5 minutes
aws events put-rule \
  --name genpr-agent-warmer \
  --schedule-expression "rate(5 minutes)"

aws events put-targets \
  --rule genpr-agent-warmer \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:genpr-agent"
```

### **Issue: MCP server fails to start**

**Problem:** "npx: command not found"

**Solution:** Verify Dockerfile.lambda includes Node.js installation

### **Issue: Environment variables not loaded**

**Problem:** API keys not found

**Solution:**
```bash
# Check environment variables
aws lambda get-function-configuration \
  --function-name genpr-agent \
  --query 'Environment'
```

### **Issue: API Gateway 502 errors**

**Problem:** Lambda returns invalid response

**Solution:**
- Check CloudWatch logs
- Verify Mangum is installed
- Test Lambda directly (bypass API Gateway)

---

## 🔄 Updates and Maintenance

### **Update Lambda Function Code**

```bash
# Option 1: Using SAM
sam build
sam deploy

# Option 2: Using script
./deploy-lambda.sh

# Option 3: Manual
docker build -f Dockerfile.lambda -t genpr-agent:latest .
# ... (push to ECR)
aws lambda update-function-code \
  --function-name genpr-agent \
  --image-uri YOUR_ECR_URI:latest
```

### **Update Environment Variables**

```bash
aws lambda update-function-configuration \
  --function-name genpr-agent \
  --environment Variables="{
    GITHUB_PERSONAL_ACCESS_TOKEN=new_token,
    ANTHROPIC_API_KEY=new_key,
    MODEL=claude-sonnet-4-6
  }"
```

### **Delete Stack**

```bash
# If deployed with SAM
sam delete --stack-name genpr-agent-stack

# Manual cleanup
aws lambda delete-function --function-name genpr-agent
aws apigateway delete-rest-api --rest-api-id YOUR_API_ID
aws ecr delete-repository --repository-name genpr-agent --force
```

---

## 📈 Performance Optimization

### **1. Reduce Cold Start Time**

- Use smaller base images
- Minimize dependencies
- Enable Lambda SnapStart (Java only, not Python yet)
- Use Provisioned Concurrency

### **2. Reduce Execution Time**

- Use faster models (e.g., `claude-haiku` or `gpt-4o-mini`)
- Optimize prompts for shorter responses
- Cache MCP connection (requires connection pooling)

### **3. Reduce Costs**

- Use ARM64 architecture (20% cheaper)
- Right-size memory allocation
- Use async endpoint (`/create-pr-async`) for background processing

---

## 🎯 Production Checklist

- [ ] Lambda function deployed
- [ ] API Gateway configured
- [ ] Environment variables set
- [ ] Timeout set to 300 seconds
- [ ] Memory set to 2048 MB
- [ ] CloudWatch logs enabled
- [ ] CloudWatch alarms configured
- [ ] API Gateway has custom domain (optional)
- [ ] SSL certificate attached (optional)
- [ ] Rate limiting configured
- [ ] Cost alerts enabled
- [ ] Secrets moved to Secrets Manager
- [ ] IAM permissions minimized
- [ ] Tested end-to-end

---

## 🔗 Useful Links

- [AWS Lambda Docs](https://docs.aws.amazon.com/lambda/)
- [AWS SAM Docs](https://docs.aws.amazon.com/serverless-application-model/)
- [API Gateway Docs](https://docs.aws.amazon.com/apigateway/)
- [Mangum (ASGI adapter)](https://mangum.io/)
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)

---

## 💡 Tips

1. **Use SAM for easy deployment** - Handles everything automatically
2. **Monitor costs** - Set up billing alerts
3. **Test locally** - Use SAM local: `sam local start-api`
4. **Version your Lambda** - Use aliases for blue/green deployments
5. **Consider Step Functions** - For workflows with multiple PR creations

---

*Last Updated: April 2026*
*GenPRAgent Lambda v1.0.0*
