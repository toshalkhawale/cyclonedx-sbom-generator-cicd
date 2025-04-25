#!/usr/bin/env python3

from aws_cdk import (
    App,
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
)
from constructs import Construct

class SbomInspectorStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # S3 bucket to store SBOMs
        sbom_bucket = s3.Bucket(
            self, "SbomBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(90),
                )
            ]
        )

        # S3 bucket to store scan results
        results_bucket = s3.Bucket(
            self, "ScanResultsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(90),
                )
            ]
        )

        # IAM role for Lambda functions
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonInspector2FullAccess"),
            ]
        )

        # Add S3 permissions to Lambda role
        sbom_bucket.grant_read_write(lambda_role)
        results_bucket.grant_read_write(lambda_role)

        # Lambda function to initiate SBOM scan
        initiate_scan_lambda = lambda_.Function(
            self, "InitiateSbomScanLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import os
import json
import uuid
from datetime import datetime

def handler(event, context):
    # Get the S3 bucket and key from the event
    s3_bucket = event['bucket'] if 'bucket' in event else os.environ['SBOM_BUCKET']
    s3_key = event['key']
    sbom_format = event.get('format', 'CYCLONEDX_1_4')
    
    # Generate a unique scan name
    scan_name = f"sbom-scan-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Create S3 URL
    s3_url = f"s3://{s3_bucket}/{s3_key}"
    
    # Create Inspector SBOM scan
    inspector = boto3.client('inspector2')
    response = inspector.create_sbom_scan(
        name=scan_name,
        sbomFormat=sbom_format,
        sbomUrl=s3_url
    )
    
    print(f"Created SBOM scan: {response['sbomScanId']}")
    
    return {
        'scanId': response['sbomScanId'],
        'scanName': scan_name,
        'sbomUrl': s3_url
    }
            """),
            environment={
                "SBOM_BUCKET": sbom_bucket.bucket_name,
                "RESULTS_BUCKET": results_bucket.bucket_name,
            },
            timeout=Duration.minutes(5),
            role=lambda_role,
        )

        # Lambda function to check scan status
        check_scan_lambda = lambda_.Function(
            self, "CheckScanStatusLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import os
import json

def handler(event, context):
    scan_id = event['scanId']
    
    # Check scan status
    inspector = boto3.client('inspector2')
    response = inspector.get_sbom_scan(sbomScanId=scan_id)
    
    status = response['status']
    print(f"Scan {scan_id} status: {status}")
    
    return {
        'scanId': scan_id,
        'scanName': event['scanName'],
        'sbomUrl': event['sbomUrl'],
        'status': status,
        'isDone': status != 'IN_PROGRESS'
    }
            """),
            timeout=Duration.minutes(5),
            role=lambda_role,
        )

        # Lambda function to get scan results
        get_results_lambda = lambda_.Function(
            self, "GetScanResultsLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import os
import json
from datetime import datetime

def handler(event, context):
    scan_id = event['scanId']
    scan_name = event['scanName']
    results_bucket = os.environ['RESULTS_BUCKET']
    
    # Get scan results
    inspector = boto3.client('inspector2')
    scan_response = inspector.get_sbom_scan(sbomScanId=scan_id)
    
    # Get findings
    findings_response = inspector.list_findings(
        filterCriteria={
            'sbomScanArn': {
                'comparison': 'EQUALS',
                'value': scan_id
            }
        }
    )
    
    # Count findings by severity
    severity_counts = {
        'CRITICAL': 0,
        'HIGH': 0,
        'MEDIUM': 0,
        'LOW': 0,
        'INFORMATIONAL': 0
    }
    
    for finding in findings_response.get('findings', []):
        severity = finding.get('severity', 'INFORMATIONAL')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Create summary
    summary = {
        'scanId': scan_id,
        'scanName': scan_name,
        'status': scan_response['status'],
        'completedAt': scan_response.get('completedAt', '').isoformat() if 'completedAt' in scan_response else None,
        'findingCounts': severity_counts,
        'totalFindings': sum(severity_counts.values()),
        'sbomUrl': event['sbomUrl']
    }
    
    # Save results to S3
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    s3_client = boto3.client('s3')
    
    # Save scan details
    s3_client.put_object(
        Bucket=results_bucket,
        Key=f"scans/{scan_id}/scan-details.json",
        Body=json.dumps(scan_response, default=str),
        ContentType='application/json'
    )
    
    # Save findings
    s3_client.put_object(
        Bucket=results_bucket,
        Key=f"scans/{scan_id}/findings.json",
        Body=json.dumps(findings_response, default=str),
        ContentType='application/json'
    )
    
    # Save summary
    s3_client.put_object(
        Bucket=results_bucket,
        Key=f"scans/{scan_id}/summary.json",
        Body=json.dumps(summary, default=str),
        ContentType='application/json'
    )
    
    return summary
            """),
            environment={
                "RESULTS_BUCKET": results_bucket.bucket_name,
            },
            timeout=Duration.minutes(5),
            role=lambda_role,
        )

        # Step Function to orchestrate the SBOM scan process
        # Define the state machine
        wait_task = sfn.Wait(
            self, "WaitForScanCompletion",
            time=sfn.WaitTime.duration(Duration.seconds(30))
        )

        check_status_task = tasks.LambdaInvoke(
            self, "CheckScanStatus",
            lambda_function=check_scan_lambda,
            output_path="$.Payload"
        )

        get_results_task = tasks.LambdaInvoke(
            self, "GetScanResults",
            lambda_function=get_results_lambda,
            output_path="$.Payload"
        )

        initiate_scan_task = tasks.LambdaInvoke(
            self, "InitiateSbomScan",
            lambda_function=initiate_scan_lambda,
            output_path="$.Payload"
        )

        # Define the workflow
        definition = initiate_scan_task.next(
            check_status_task.next(
                sfn.Choice(self, "IsScanComplete")
                .when(sfn.Condition.boolean_equals("$.isDone", True), get_results_task)
                .otherwise(wait_task.next(check_status_task))
            )
        )

        # Create the state machine
        state_machine = sfn.StateMachine(
            self, "SbomScanStateMachine",
            definition=definition,
            timeout=Duration.hours(2),
            logs=sfn.LogOptions(
                destination=logs.LogGroup(self, "SbomScanLogGroup"),
                level=sfn.LogLevel.ALL
            )
        )

        # Lambda function to trigger the Step Function when a new SBOM is uploaded
        trigger_lambda = lambda_.Function(
            self, "TriggerSbomScanLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import os
import json

def handler(event, context):
    # Get the S3 event details
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Only process files in the sboms/ prefix
        if not key.startswith('sboms/'):
            print(f"Skipping non-SBOM file: {key}")
            continue
        
        # Determine SBOM format based on file extension
        sbom_format = 'CYCLONEDX_1_4'  # Default
        if key.endswith('.json'):
            sbom_format = 'CYCLONEDX_1_4'
        elif key.endswith('.xml'):
            sbom_format = 'CYCLONEDX_1_4'
        
        # Start the Step Function execution
        sfn_client = boto3.client('stepfunctions')
        response = sfn_client.start_execution(
            stateMachineArn=os.environ['STATE_MACHINE_ARN'],
            input=json.dumps({
                'bucket': bucket,
                'key': key,
                'format': sbom_format
            })
        )
        
        print(f"Started Step Function execution: {response['executionArn']}")
    
    return {
        'statusCode': 200,
        'body': 'Processing started'
    }
            """),
            environment={
                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
            },
            timeout=Duration.minutes(5),
            role=lambda_role,
        )

        # Grant permission to invoke the state machine
        state_machine.grant_start_execution(trigger_lambda)

        # Add S3 event notification to trigger the Lambda
        sbom_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3.LambdaDestination(trigger_lambda),
            s3.NotificationKeyFilter(prefix="sboms/")
        )

        # Schedule a daily scan of all SBOMs
        daily_scan_rule = events.Rule(
            self, "DailySbomScanRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="0",
                month="*",
                week_day="*",
                year="*"
            )
        )

        # Lambda function to list all SBOMs and trigger scans
        list_sboms_lambda = lambda_.Function(
            self, "ListSbomsLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import os
import json

def handler(event, context):
    s3_client = boto3.client('s3')
    sfn_client = boto3.client('stepfunctions')
    sbom_bucket = os.environ['SBOM_BUCKET']
    state_machine_arn = os.environ['STATE_MACHINE_ARN']
    
    # List all SBOMs in the bucket
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=sbom_bucket, Prefix='sboms/')
    
    scan_count = 0
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            
            # Determine SBOM format based on file extension
            sbom_format = 'CYCLONEDX_1_4'  # Default
            if key.endswith('.json'):
                sbom_format = 'CYCLONEDX_1_4'
            elif key.endswith('.xml'):
                sbom_format = 'CYCLONEDX_1_4'
            
            # Start the Step Function execution
            response = sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps({
                    'bucket': sbom_bucket,
                    'key': key,
                    'format': sbom_format
                })
            )
            
            print(f"Started Step Function execution for {key}: {response['executionArn']}")
            scan_count += 1
    
    return {
        'statusCode': 200,
        'body': f'Started {scan_count} SBOM scans'
    }
            """),
            environment={
                "SBOM_BUCKET": sbom_bucket.bucket_name,
                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
            },
            timeout=Duration.minutes(15),
            role=lambda_role,
        )

        # Grant permission to invoke the state machine
        state_machine.grant_start_execution(list_sboms_lambda)

        # Add the Lambda as a target for the daily rule
        daily_scan_rule.add_target(targets.LambdaFunction(list_sboms_lambda))

app = App()
SbomInspectorStack(app, "SbomInspectorStack")
app.synth()
