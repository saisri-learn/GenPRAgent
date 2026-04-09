# Lambda Deployment - Quick Start Guide

## 🚀 Fastest Way to Deploy

### Prerequisites
- AWS account
- AWS CLI configured (`aws configure`)
- Docker installed
- AWS SAM CLI installed

### Deploy in 3 Commands

```bash
# 1. Build
sam build

# 2. Deploy (first time - will prompt for parameters)
sam deploy --guided

# 3. Test
curl https://YOUR_API_URL/health
```

### What You'll Be Asked

When running `sam deploy --guided`:

1. **Stack Name**: `genpr-agent-stack` (or any name)
2. **AWS Region**: `us-east-1` (or your preferred region)
3. **GitHubToken**: Your GitHub personal access token (`ghp_...`)
4. **AnthropicApiKey**: Your Anthropic API key (`sk-ant-...`)
5. **OpenAIApiKey**: (Optional - press Enter to skip)
6. **DefaultModel**: `claude-sonnet-4-6` (or change)
7. **Confirm changes**: `Y`
8. **Allow SAM CLI IAM role creation**: `Y`
9. **Disable rollback**: `N`
10. **Save arguments to config file**: `Y`

### That's It!

After deployment, SAM will show your API URL:
```
Outputs
---------------------------------------------------------------
GenPRAgentApi = https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/
```

### Test Your API

```bash
# Health check
curl https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/health

# Create PR
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "Bug in payment processing",
    "repo": "your-username/your-repo"
  }'
```

### Update After Code Changes

```bash
sam build
sam deploy
```

### Delete Everything

```bash
sam delete --stack-name genpr-agent-stack
```

---

## 📦 What Was Changed for Lambda

### New Files Added:
1. `lambda_handler.py` - Lambda entry point
2. `Dockerfile.lambda` - Lambda-specific Docker image
3. `template.yaml` - AWS SAM configuration
4. `deploy-lambda.sh` - Manual deployment script
5. `LAMBDA_DEPLOYMENT.md` - Detailed guide

### Modified Files:
1. `requirements.txt` - Added `mangum` (Lambda ASGI adapter)
2. `.gitignore` - Added AWS-specific ignores

### No Changes Needed:
- `agent.py` - Works as-is
- `main.py` - Works as-is
- Existing Docker files - Still work for EC2

---

## 🎯 Key Differences: Lambda vs EC2

| Feature | EC2 | Lambda |
|---------|-----|--------|
| Cost | $15-20/month | $2-3/month (light usage) |
| Scaling | Manual | Automatic |
| Maintenance | Update OS, packages | Just update code |
| Cold start | None | 0.5-3 seconds |
| Max timeout | Unlimited | 15 minutes |
| Setup time | 30-60 minutes | 5 minutes |

---

## 💡 Pro Tips

1. **First deployment takes 5-10 minutes** (building Docker image)
2. **Subsequent deploys take 2-3 minutes** (just code update)
3. **Set timeout to 5 minutes** (PR creation can take 30-60 seconds)
4. **Use 2GB memory** (dependencies are large)
5. **Monitor CloudWatch logs** for debugging
6. **Enable API Gateway logging** for request tracking

---

## 🆘 Common Issues

### "sam: command not found"
```bash
# Install SAM CLI
pip install aws-sam-cli
```

### "Docker daemon not running"
```bash
# Start Docker Desktop or Docker service
```

### "Unable to upload artifact"
```bash
# Check AWS credentials
aws sts get-caller-identity

# Re-configure if needed
aws configure
```

### "Timeout error"
```bash
# Increase Lambda timeout in template.yaml
Timeout: 300  # 5 minutes
```

---

## 📞 Need Help?

- Full guide: `LAMBDA_DEPLOYMENT.md`
- EC2 guide: `SETUP_GUIDE.md`
- Questions: Open GitHub issue

---

**Deployment time: ~5-10 minutes** ⏱️
