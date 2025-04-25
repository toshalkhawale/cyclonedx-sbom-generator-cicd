# AWS Inspector SBOM Scanner - CloudFormation

This CloudFormation template deploys an automated infrastructure for scanning SBOMs with AWS Inspector.

## Architecture

The solution includes:

1. **S3 Buckets**:
   - SBOM storage bucket
   - Scan results storage bucket

2. **Lambda Functions**:
   - Trigger function (responds to S3 events)
   - Initiate scan function
   - Check scan status function
   - Get scan results function
   - List SBOMs function (for scheduled scans)

3. **Step Function**:
   - Orchestrates the SBOM scanning workflow

4. **EventBridge Rule**:
   - Schedules daily scans of all SBOMs

## Workflow

1. Upload a SBOM to the S3 bucket in the `sboms/` prefix
2. This triggers the Lambda function, which starts the Step Function
3. The Step Function:
   - Initiates an AWS Inspector SBOM scan
   - Periodically checks the scan status
   - Once complete, retrieves and stores the results
4. Results are stored in the results bucket

## Prerequisites

- AWS CLI configured with appropriate permissions
- A CycloneDX SBOM file to scan

## Deployment

### Option 1: Using the deployment script

```bash
./aws-inspector-cloudformation-deploy.sh
```

This script will:
1. Generate unique bucket names
2. Deploy the CloudFormation stack
3. Upload a sample SBOM to trigger the scanning process

You can customize the deployment with these options:
```bash
./aws-inspector-cloudformation-deploy.sh \
  --stack-name my-sbom-scanner \
  --region us-west-2 \
  --sbom-bucket my-sbom-bucket \
  --results-bucket my-results-bucket \
  --sbom-file path/to/my-sbom.json
```

### Option 2: Manual deployment

1. Deploy the CloudFormation stack:
   ```bash
   aws cloudformation deploy \
     --template-file aws-inspector-cloudformation.yaml \
     --stack-name sbom-inspector-scanner \
     --parameter-overrides \
       SbomBucketName=my-sbom-bucket \
       ResultsBucketName=my-results-bucket \
     --capabilities CAPABILITY_IAM
   ```

2. Upload a SBOM to trigger scanning:
   ```bash
   aws s3 cp sbom-output/nodejs-sbom.json s3://my-sbom-bucket/sboms/
   ```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| SbomBucketName | Name for the S3 bucket to store SBOMs | sbom-storage-bucket |
| ResultsBucketName | Name for the S3 bucket to store scan results | sbom-results-bucket |
| SbomPrefix | Prefix for SBOM files in the S3 bucket | sboms/ |
| DailyScheduleEnabled | Enable daily scheduled scans of all SBOMs | true |

## Outputs

| Output | Description |
|--------|-------------|
| SbomBucketName | Name of the S3 bucket for storing SBOMs |
| ResultsBucketName | Name of the S3 bucket for storing scan results |
| SbomUploadPrefix | Prefix for uploading SBOMs |
| UploadCommand | Command to upload a SBOM for scanning |
| StateMachineArn | ARN of the Step Function state machine |

## Viewing Results

1. Use the AWS Inspector console to view scan results
2. Generate a dashboard with the provided script:
   ```bash
   ./aws-inspector-dashboard.py --bucket my-results-bucket
   ```

## Cleanup

To remove all resources:

```bash
aws cloudformation delete-stack --stack-name sbom-inspector-scanner
```

**Note**: This will not delete the S3 buckets by default. To delete them:
```bash
aws s3 rm s3://my-sbom-bucket --recursive
aws s3 rb s3://my-sbom-bucket
aws s3 rm s3://my-results-bucket --recursive
aws s3 rb s3://my-results-bucket
```
