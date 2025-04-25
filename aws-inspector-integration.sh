#!/bin/bash

# Script to integrate SBOM generation with AWS Inspector
# This script will:
# 1. Generate a SBOM using CycloneDX
# 2. Upload the SBOM to S3
# 3. Create an AWS Inspector SBOM scan
# 4. Retrieve and analyze the scan results

set -e

echo "Starting AWS Inspector SBOM integration..."

# Configuration - modify these variables as needed
AWS_REGION="us-east-1"
S3_BUCKET_NAME="sbom-reports-$(date +%s)"  # Unique bucket name with timestamp
SBOM_FILE="sbom-output/nodejs-sbom.json"
REPORT_OUTPUT_DIR="inspector-reports"

# Create output directory
mkdir -p "$REPORT_OUTPUT_DIR"

# Function to check if AWS CLI is installed
check_aws_cli() {
  if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
  fi
}

# Function to check if SBOM exists
check_sbom_file() {
  if [ ! -f "$SBOM_FILE" ]; then
    echo "SBOM file not found: $SBOM_FILE"
    echo "Generating SBOM first..."
    ./generate-sbom.sh
    
    if [ ! -f "$SBOM_FILE" ]; then
      echo "Failed to generate SBOM. Exiting."
      exit 1
    fi
  fi
}

# Function to create S3 bucket if it doesn't exist
create_s3_bucket() {
  echo "Creating S3 bucket for SBOM storage: $S3_BUCKET_NAME"
  
  # Check if bucket exists
  if aws s3api head-bucket --bucket "$S3_BUCKET_NAME" 2>/dev/null; then
    echo "Bucket already exists: $S3_BUCKET_NAME"
  else
    # Create bucket
    if [ "$AWS_REGION" = "us-east-1" ]; then
      # For us-east-1, don't specify LocationConstraint
      aws s3api create-bucket \
        --bucket "$S3_BUCKET_NAME" \
        --region "$AWS_REGION"
    else
      # For other regions, include LocationConstraint
      aws s3api create-bucket \
        --bucket "$S3_BUCKET_NAME" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    
    # Wait for bucket to be available
    aws s3api wait bucket-exists --bucket "$S3_BUCKET_NAME"
    
    echo "S3 bucket created: $S3_BUCKET_NAME"
    
    # Add bucket policy to restrict access
    cat > /tmp/bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowInspectorAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "inspector2.amazonaws.com"
      },
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET_NAME",
        "arn:aws:s3:::$S3_BUCKET_NAME/*"
      ]
    }
  ]
}
EOF
    
    aws s3api put-bucket-policy \
      --bucket "$S3_BUCKET_NAME" \
      --policy file:///tmp/bucket-policy.json
    
    echo "Bucket policy applied to allow Inspector access"
  fi
}

# Function to upload SBOM to S3
upload_sbom_to_s3() {
  local sbom_s3_key="sboms/$(basename "$SBOM_FILE")"
  
  echo "Uploading SBOM to S3: s3://$S3_BUCKET_NAME/$sbom_s3_key"
  
  aws s3 cp "$SBOM_FILE" "s3://$S3_BUCKET_NAME/$sbom_s3_key"
  
  echo "SBOM uploaded successfully"
  
  # Return the S3 URI
  echo "s3://$S3_BUCKET_NAME/$sbom_s3_key"
}

# Function to enable AWS Inspector if not already enabled
enable_aws_inspector() {
  echo "Checking if AWS Inspector is enabled..."
  
  # Check if Inspector is already enabled for ECR (which is required for SBOM scanning)
  inspector_status=$(aws inspector2 batch-get-account-status --region "$AWS_REGION" --query 'accounts[0].resourceStatus.ecr' --output text 2>/dev/null || echo "DISABLED")
  
  if [ "$inspector_status" != "ENABLED" ]; then
    echo "Enabling AWS Inspector for ECR (required for SBOM scanning)..."
    
    aws inspector2 enable \
      --resource-types ECR \
      --region "$AWS_REGION"
    
    echo "AWS Inspector enabled for ECR"
  else
    echo "AWS Inspector is already enabled for ECR"
  fi
  
  echo "AWS Inspector is now configured for SBOM scanning"
}

# Function to create an AWS Inspector SBOM scan
create_inspector_sbom_scan() {
  local s3_uri=$1
  
  echo "Creating AWS Inspector SBOM scan for: $s3_uri"
  
  # Create a temporary JSON file for the scan request
  cat > /tmp/sbom-scan-request.json << EOF
{
  "name": "sbom-scan-$(date +%Y%m%d-%H%M%S)",
  "sbomFormat": "CYCLONEDX_1_4",
  "sbomUrl": "$s3_uri"
}
EOF
  
  # Create the SBOM scan
  scan_response=$(aws inspector2 create-sbom-scan \
    --cli-input-json file:///tmp/sbom-scan-request.json \
    --region "$AWS_REGION")
  
  # Extract the scan ID
  scan_id=$(echo "$scan_response" | grep -o '"sbomScanId": "[^"]*' | cut -d'"' -f4)
  
  echo "SBOM scan created with ID: $scan_id"
  echo "$scan_id"
}

# Function to wait for scan completion
wait_for_scan_completion() {
  local scan_id=$1
  local max_attempts=30
  local attempt=1
  local status="IN_PROGRESS"
  
  echo "Waiting for scan to complete..."
  
  while [ "$status" = "IN_PROGRESS" ] && [ $attempt -le $max_attempts ]; do
    echo "Checking scan status (attempt $attempt/$max_attempts)..."
    
    status=$(aws inspector2 get-sbom-scan \
      --sbom-scan-id "$scan_id" \
      --region "$AWS_REGION" \
      --query 'status' \
      --output text)
    
    if [ "$status" = "IN_PROGRESS" ]; then
      echo "Scan still in progress. Waiting 10 seconds..."
      sleep 10
      attempt=$((attempt + 1))
    else
      echo "Scan completed with status: $status"
    fi
  done
  
  if [ "$status" = "IN_PROGRESS" ]; then
    echo "Scan timed out. Please check the AWS Console for results."
    return 1
  elif [ "$status" = "FAILED" ]; then
    echo "Scan failed. Please check the AWS Console for details."
    return 1
  fi
  
  return 0
}

# Function to get scan results
get_scan_results() {
  local scan_id=$1
  local output_file="$REPORT_OUTPUT_DIR/inspector-scan-results.json"
  
  echo "Retrieving scan results for scan ID: $scan_id"
  
  # Get the scan results
  aws inspector2 get-sbom-scan \
    --sbom-scan-id "$scan_id" \
    --region "$AWS_REGION" > "$output_file"
  
  echo "Scan results saved to: $output_file"
  
  # Get vulnerability findings
  local findings_file="$REPORT_OUTPUT_DIR/inspector-findings.json"
  
  aws inspector2 list-findings \
    --filter-criteria '{"sbomScanArn":{"comparison":"EQUALS","value":"'"$scan_id"'"}}' \
    --region "$AWS_REGION" > "$findings_file"
  
  echo "Vulnerability findings saved to: $findings_file"
  
  # Return the findings file path
  echo "$findings_file"
}

# Function to analyze findings
analyze_findings() {
  local findings_file=$1
  local summary_file="$REPORT_OUTPUT_DIR/vulnerability-summary.txt"
  
  echo "Analyzing findings from: $findings_file"
  
  # Extract finding counts by severity
  critical_count=$(grep -o '"CRITICAL"' "$findings_file" | wc -l)
  high_count=$(grep -o '"HIGH"' "$findings_file" | wc -l)
  medium_count=$(grep -o '"MEDIUM"' "$findings_file" | wc -l)
  low_count=$(grep -o '"LOW"' "$findings_file" | wc -l)
  
  # Create a summary report
  cat > "$summary_file" << EOF
AWS Inspector SBOM Vulnerability Summary
=======================================

Scan Date: $(date)
SBOM File: $SBOM_FILE

Vulnerability Counts by Severity:
--------------------------------
CRITICAL: $critical_count
HIGH:     $high_count
MEDIUM:   $medium_count
LOW:      $low_count
TOTAL:    $(($critical_count + $high_count + $medium_count + $low_count))

EOF
  
  # Add top vulnerabilities to the summary
  echo "Top Vulnerabilities:" >> "$summary_file"
  echo "-------------------" >> "$summary_file"
  
  # Extract and format top vulnerabilities (critical and high)
  jq -r '.findings[] | select(.severity == "CRITICAL" or .severity == "HIGH") | "* " + .title + " (Severity: " + .severity + ", CVE: " + (.vulnerabilityId // "N/A") + ")"' "$findings_file" | head -10 >> "$summary_file"
  
  echo "Analysis complete. Summary saved to: $summary_file"
  
  # Display the summary
  cat "$summary_file"
}

# Main execution
check_aws_cli
check_sbom_file
create_s3_bucket
s3_uri=$(upload_sbom_to_s3)
enable_aws_inspector
scan_id=$(create_inspector_sbom_scan "$s3_uri")

if wait_for_scan_completion "$scan_id"; then
  findings_file=$(get_scan_results "$scan_id")
  analyze_findings "$findings_file"
  
  echo "AWS Inspector SBOM scan and analysis complete!"
  echo "Reports are available in the $REPORT_OUTPUT_DIR directory."
else
  echo "Failed to complete AWS Inspector scan. Please check the AWS Console."
  exit 1
fi
