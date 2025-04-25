#!/bin/bash

# Script to deploy the AWS Inspector SBOM Scanner CloudFormation stack
# This script will:
# 1. Create a unique S3 bucket name if not provided
# 2. Deploy the CloudFormation stack
# 3. Upload a sample SBOM to trigger the scanning process

set -e

echo "Starting AWS Inspector SBOM Scanner CloudFormation deployment..."

# Default values
STACK_NAME="sbom-inspector-scanner"
REGION=$(aws configure get region || echo "us-east-1")
SBOM_FILE="sbom-output/nodejs-sbom.json"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --stack-name)
      STACK_NAME="$2"
      shift
      shift
      ;;
    --region)
      REGION="$2"
      shift
      shift
      ;;
    --sbom-bucket)
      SBOM_BUCKET_NAME="$2"
      shift
      shift
      ;;
    --results-bucket)
      RESULTS_BUCKET_NAME="$2"
      shift
      shift
      ;;
    --sbom-file)
      SBOM_FILE="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Generate unique bucket names if not provided
if [ -z "$SBOM_BUCKET_NAME" ]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  TIMESTAMP=$(date +%Y%m%d%H%M%S)
  SBOM_BUCKET_NAME="sbom-storage-${ACCOUNT_ID}-${TIMESTAMP}"
  echo "Generated SBOM bucket name: $SBOM_BUCKET_NAME"
fi

if [ -z "$RESULTS_BUCKET_NAME" ]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  TIMESTAMP=$(date +%Y%m%d%H%M%S)
  RESULTS_BUCKET_NAME="sbom-results-${ACCOUNT_ID}-${TIMESTAMP}"
  echo "Generated results bucket name: $RESULTS_BUCKET_NAME"
fi

# Check if SBOM file exists
if [ ! -f "$SBOM_FILE" ]; then
  echo "SBOM file not found: $SBOM_FILE"
  echo "Generating SBOM first..."
  ./generate-sbom.sh
  
  if [ ! -f "$SBOM_FILE" ]; then
    echo "Failed to generate SBOM. Exiting."
    exit 1
  fi
fi

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack: $STACK_NAME"
aws cloudformation deploy \
  --template-file aws-inspector-cloudformation.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    SbomBucketName="$SBOM_BUCKET_NAME" \
    ResultsBucketName="$RESULTS_BUCKET_NAME" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION"

# Wait for stack to be created
echo "Waiting for stack creation to complete..."
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

# Get stack outputs
echo "Getting stack outputs..."
SBOM_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='SbomBucketName'].OutputValue" \
  --output text \
  --region "$REGION")

SBOM_PREFIX=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='SbomUploadPrefix'].OutputValue" \
  --output text \
  --region "$REGION")

RESULTS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ResultsBucketName'].OutputValue" \
  --output text \
  --region "$REGION")

# Upload SBOM to trigger scanning
echo "Uploading SBOM to S3 to trigger scanning..."
aws s3 cp "$SBOM_FILE" "s3://${SBOM_BUCKET}/${SBOM_PREFIX}$(basename "$SBOM_FILE")" \
  --region "$REGION"

echo "SBOM uploaded successfully. Scanning process has been triggered."
echo ""
echo "Stack deployment complete!"
echo "============================"
echo "SBOM Bucket: $SBOM_BUCKET"
echo "Results Bucket: $RESULTS_BUCKET"
echo ""
echo "To upload more SBOMs for scanning:"
echo "aws s3 cp your-sbom.json s3://${SBOM_BUCKET}/${SBOM_PREFIX}"
echo ""
echo "To view scan results, use the AWS Inspector dashboard or run:"
echo "./aws-inspector-dashboard.py --bucket $RESULTS_BUCKET --region $REGION"
