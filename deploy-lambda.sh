#!/bin/bash
# AWS Lambda Deployment Script for GenPRAgent

set -e  # Exit on error

# Configuration
AWS_REGION="us-east-1"
FUNCTION_NAME="genpr-agent"
ECR_REPO_NAME="genpr-agent"
IMAGE_TAG="latest"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting GenPRAgent Lambda Deployment${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Full ECR repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

# Step 1: Create ECR repository if it doesn't exist
echo -e "${YELLOW}📦 Checking ECR repository...${NC}"
if ! aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo -e "${YELLOW}Creating ECR repository: ${ECR_REPO_NAME}${NC}"
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}
    echo -e "${GREEN}✅ ECR repository created${NC}"
else
    echo -e "${GREEN}✅ ECR repository exists${NC}"
fi

# Step 2: Login to ECR
echo -e "${YELLOW}🔐 Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
echo -e "${GREEN}✅ Logged in to ECR${NC}"

# Step 3: Build Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker build -f Dockerfile.lambda -t ${ECR_REPO_NAME}:${IMAGE_TAG} .
echo -e "${GREEN}✅ Docker image built${NC}"

# Step 4: Tag image for ECR
echo -e "${YELLOW}🏷️  Tagging image...${NC}"
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
echo -e "${GREEN}✅ Image tagged${NC}"

# Step 5: Push image to ECR
echo -e "${YELLOW}📤 Pushing image to ECR...${NC}"
docker push ${ECR_URI}:${IMAGE_TAG}
echo -e "${GREEN}✅ Image pushed to ECR${NC}"

# Step 6: Check if Lambda function exists
echo -e "${YELLOW}🔍 Checking if Lambda function exists...${NC}"
if aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} &> /dev/null; then
    # Update existing function
    echo -e "${YELLOW}♻️  Updating Lambda function...${NC}"
    aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --image-uri ${ECR_URI}:${IMAGE_TAG} \
        --region ${AWS_REGION}
    echo -e "${GREEN}✅ Lambda function updated${NC}"
else
    echo -e "${RED}❌ Lambda function does not exist. Please create it first using AWS Console or SAM.${NC}"
    echo -e "${YELLOW}💡 Tip: Use 'sam deploy' or create manually in AWS Console${NC}"
    exit 1
fi

# Step 7: Wait for update to complete
echo -e "${YELLOW}⏳ Waiting for function update to complete...${NC}"
aws lambda wait function-updated --function-name ${FUNCTION_NAME} --region ${AWS_REGION}

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🎉 GenPRAgent is now running on AWS Lambda${NC}"

# Get function URL if it exists
FUNCTION_URL=$(aws lambda get-function-url-config --function-name ${FUNCTION_NAME} --region ${AWS_REGION} 2>/dev/null | jq -r '.FunctionUrl' || echo "")

if [ ! -z "$FUNCTION_URL" ]; then
    echo -e "${GREEN}🔗 Function URL: ${FUNCTION_URL}${NC}"
else
    # Get API Gateway URL
    API_ID=$(aws apigateway get-rest-apis --region ${AWS_REGION} --query "items[?name=='${FUNCTION_NAME}'].id" --output text)
    if [ ! -z "$API_ID" ]; then
        echo -e "${GREEN}🔗 API Gateway URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/Prod/${NC}"
    fi
fi
