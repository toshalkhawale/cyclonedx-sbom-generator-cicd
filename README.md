# CycloneDX SBOM Generator with AWS Inspector Integration

This project demonstrates how to generate a Software Bill of Materials (SBOM) in CycloneDX format for a sample application and integrate with AWS Inspector for vulnerability scanning.

## Project Structure

```
cyclonedx-sbom-generator/
├── index.js                              # Sample Node.js application
├── package.json                          # Node.js dependencies
├── generate-sbom.sh                      # SBOM generation script
├── docker-sbom.sh                        # Docker image SBOM generation
├── vulnerability-check.sh                # Local vulnerability scanning
├── sbom-analyzer.js                      # SBOM analysis tool
├── aws-inspector-integration.sh          # AWS Inspector integration script
├── aws-inspector-dashboard.py            # Dashboard generator for Inspector results
├── aws-inspector-cloudformation.yaml     # CloudFormation template for AWS Inspector integration
├── aws-inspector-cloudformation-deploy.sh # Script to deploy CloudFormation stack
├── aws-inspector-cloudformation-README.md # Documentation for CloudFormation deployment
├── Dockerfile                            # Container definition
├── docker-compose.yml                    # Multi-service setup
├── ci-cd-integration.md                  # CI/CD integration examples
└── sbom-output/                          # Generated SBOM files (created by the script)
```

## Prerequisites

- Node.js and npm
- Bash shell
- For Python projects: Python and pip
- For Java projects: Maven
- For AWS integration: AWS CLI configured with appropriate permissions

## Getting Started

1. Clone this repository
2. Install dependencies:
   ```
   npm install
   ```
3. Generate the SBOM:
   ```
   npm run generate-sbom
   ```
   or
   ```
   bash generate-sbom.sh
   ```

## AWS Inspector Integration

This project includes full integration with AWS Inspector for SBOM vulnerability scanning:

### Option 1: Manual Integration

Run the AWS Inspector integration script:
```
./aws-inspector-integration.sh
```

This script will:
1. Generate a SBOM if one doesn't exist
2. Create an S3 bucket for SBOM storage
3. Upload the SBOM to S3
4. Enable AWS Inspector SBOM scanning if not already enabled
5. Create an AWS Inspector SBOM scan
6. Wait for the scan to complete
7. Retrieve and analyze the scan results

### Option 2: Automated CloudFormation Deployment

Deploy the CloudFormation stack for automated scanning:
```
./aws-inspector-cloudformation-deploy.sh
```

This deploys:
- S3 buckets for SBOM storage and results
- Lambda functions for scan orchestration
- Step Function workflow for scan management
- Event-based triggers for automatic scanning
- Scheduled daily scans of all SBOMs

For more details, see [AWS Inspector CloudFormation README](aws-inspector-cloudformation-README.md).

### Dashboard Generation

Generate a visual dashboard of vulnerability findings:
```
./aws-inspector-dashboard.py --bucket [YOUR_RESULTS_BUCKET]
```

## About CycloneDX

CycloneDX is a lightweight SBOM standard designed for use in application security contexts and supply chain component analysis. It's maintained by the OWASP Foundation.

## Supported Package Ecosystems

The SBOM generator script supports:

- Node.js (npm)
- Python (requirements.txt)
- Java (Maven) - requires additional setup
- Docker images (via Syft)

## Output Formats

The script generates SBOMs in both JSON and XML formats, which are placed in the `sbom-output` directory.

## Additional Resources

- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [OWASP CycloneDX Project](https://owasp.org/www-project-cyclonedx/)
- [AWS Inspector Documentation](https://docs.aws.amazon.com/inspector/latest/user/scanning-sbom.html)
