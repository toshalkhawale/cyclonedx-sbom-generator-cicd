# AWS Inspector SBOM Scanner CDK Project

This CDK project deploys an automated infrastructure for scanning SBOMs with AWS Inspector.

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

- AWS CDK installed
- Python 3.9 or later
- AWS CLI configured with appropriate permissions

## Deployment

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Bootstrap your AWS environment (if not already done):
   ```
   cdk bootstrap
   ```

3. Deploy the stack:
   ```
   cdk deploy
   ```

## Usage

### Upload a SBOM

```bash
aws s3 cp sbom-output/nodejs-sbom.json s3://[SBOM_BUCKET_NAME]/sboms/
```

### View Scan Results

Results are stored in the results bucket with the following structure:
```
s3://[RESULTS_BUCKET_NAME]/scans/[SCAN_ID]/
  ├── scan-details.json
  ├── findings.json
  └── summary.json
```

### Trigger a Manual Scan of All SBOMs

```bash
aws lambda invoke --function-name [LIST_SBOMS_LAMBDA_NAME] output.json
```

## Cleanup

To remove all resources:

```bash
cdk destroy
```
