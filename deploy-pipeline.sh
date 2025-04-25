#!/bin/bash

# Script to deploy the SBOM Generator CI/CD pipeline using CloudFormation

set -e

echo "Deploying SBOM Generator CI/CD Pipeline..."

# Configuration - modify these variables as needed
AWS_REGION="us-east-1"
STACK_NAME="sbom-generator-pipeline"
GITHUB_OWNER="your-github-username"
GITHUB_REPO="cyclonedx-sbom-generator"
GITHUB_BRANCH="main"
S3_BUCKET_NAME="sbom-storage-$(date +%s)"  # Unique bucket name with timestamp

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "AWS CLI is not installed. Please install it first."
  echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
  exit 1
fi

# Prompt for GitHub token
read -sp "Enter your GitHub OAuth token: " GITHUB_TOKEN
echo

# Create CloudFormation directory if it doesn't exist
mkdir -p cloudformation

# Deploy the CloudFormation stack
echo "Deploying CloudFormation stack: $STACK_NAME"

aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://cloudformation/sbom-pipeline.yaml \
  --parameters \
    ParameterKey=GitHubOwner,ParameterValue="$GITHUB_OWNER" \
    ParameterKey=GitHubRepo,ParameterValue="$GITHUB_REPO" \
    ParameterKey=GitHubBranch,ParameterValue="$GITHUB_BRANCH" \
    ParameterKey=GitHubToken,ParameterValue="$GITHUB_TOKEN" \
    ParameterKey=SBOMBucketName,ParameterValue="$S3_BUCKET_NAME" \
  --capabilities CAPABILITY_IAM \
  --region "$AWS_REGION"

echo "Waiting for stack creation to complete..."
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION"

# Get stack outputs
echo "Stack creation complete. Retrieving outputs..."

SBOM_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='SBOMStorageBucket'].OutputValue" \
  --output text \
  --region "$AWS_REGION")

REPORTS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='SBOMReportsBucket'].OutputValue" \
  --output text \
  --region "$AWS_REGION")

PIPELINE_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CodePipeline'].OutputValue" \
  --output text \
  --region "$AWS_REGION")

echo "Deployment complete!"
echo "SBOM Storage Bucket: $SBOM_BUCKET"
echo "SBOM Reports Bucket: $REPORTS_BUCKET"
echo "CodePipeline: $PIPELINE_NAME"
echo
echo "Your CI/CD pipeline is now set up and will automatically generate SBOMs and scan for vulnerabilities."
echo "The pipeline will run automatically when you push to your GitHub repository."
echo "It will also run daily at midnight UTC."
