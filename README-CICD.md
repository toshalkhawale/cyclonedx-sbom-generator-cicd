# CycloneDX SBOM Generator CI/CD Pipeline

This document explains how to set up and use the CI/CD pipeline for the CycloneDX SBOM Generator project.

## Overview

The CI/CD pipeline automates the following tasks:

1. Generate SBOMs for your application
2. Upload SBOMs to S3
3. Scan SBOMs for vulnerabilities using AWS Inspector
4. Store and analyze scan results
5. Fail builds if critical vulnerabilities are found

## Deployment Options

You can deploy the CI/CD pipeline using one of the following methods:

### Option 1: AWS CloudFormation

The CloudFormation template creates all necessary AWS resources:

- S3 buckets for SBOM storage and reports
- CodeBuild project for SBOM generation and scanning
- CodePipeline for orchestration
- IAM roles with required permissions
- EventBridge rule for scheduled scans

To deploy using CloudFormation:

1. Run the deployment script:
   ```bash
   ./deploy-pipeline.sh
   ```

2. Enter your GitHub OAuth token when prompted

3. Wait for the stack creation to complete

### Option 2: GitHub Actions

The GitHub Actions workflow performs the same tasks but runs in GitHub's infrastructure:

1. Add the following secrets to your GitHub repository:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
   - `SBOM_BUCKET`: S3 bucket for storing SBOMs
   - `REPORTS_BUCKET`: S3 bucket for storing reports

2. Push the `.github/workflows/sbom-generator.yml` file to your repository

3. The workflow will run automatically on:
   - Every push to the main branch
   - Every pull request to the main branch
   - Daily at midnight UTC

## AWS CodeBuild Integration

For direct integration with AWS CodeBuild:

1. Create a CodeBuild project in the AWS Console
2. Use the provided `buildspec.yml` file
3. Set the following environment variables:
   - `S3_BUCKET`: S3 bucket for storing SBOMs
   - `REPORTS_BUCKET`: S3 bucket for storing reports

## Pipeline Workflow

The pipeline follows this workflow:

1. **Source**: Retrieves the source code from GitHub
2. **Build**: 
   - Installs dependencies
   - Generates SBOM using CycloneDX
   - Uploads SBOM to S3
3. **Scan**:
   - Creates an AWS Inspector SBOM scan
   - Waits for scan completion
   - Retrieves and analyzes results
4. **Report**:
   - Uploads scan results to S3
   - Generates a vulnerability summary
   - Fails the build if critical vulnerabilities are found

## Customization

You can customize the pipeline by modifying:

- `cloudformation/sbom-pipeline.yaml`: CloudFormation template
- `.github/workflows/sbom-generator.yml`: GitHub Actions workflow
- `buildspec.yml`: AWS CodeBuild specification

## Monitoring

Monitor your pipeline:

- AWS CodePipeline console for pipeline execution status
- AWS CodeBuild console for build logs
- S3 buckets for generated SBOMs and scan reports
- AWS Inspector console for detailed vulnerability information

## Troubleshooting

Common issues:

1. **Permission errors**: Ensure IAM roles have necessary permissions
2. **Scan failures**: Check AWS Inspector service status
3. **GitHub integration issues**: Verify OAuth token has correct permissions
4. **Build failures**: Review CodeBuild logs for detailed error messages
