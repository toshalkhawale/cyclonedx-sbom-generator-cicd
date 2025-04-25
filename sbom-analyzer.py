#!/usr/bin/env python3
"""
SBOM Vulnerability Analysis and Visualization Tool

This script analyzes AWS Inspector SBOM scan results and generates visualizations
to help understand vulnerability patterns and severity distributions.
"""

import argparse
import json
import os
import sys
import boto3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from tabulate import tabulate
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Set up command line arguments
parser = argparse.ArgumentParser(description='Analyze SBOM vulnerability scan results')
parser.add_argument('--input', '-i', help='Path to findings JSON file')
parser.add_argument('--s3-bucket', '-b', help='S3 bucket containing findings')
parser.add_argument('--s3-key', '-k', help='S3 key for findings file')
parser.add_argument('--scan-id', '-s', help='AWS Inspector SBOM scan ID')
parser.add_argument('--output-dir', '-o', default='./sbom-analysis', help='Output directory for reports and visualizations')
parser.add_argument('--format', '-f', choices=['html', 'pdf', 'png', 'all'], default='all', help='Output format for visualizations')
args = parser.parse_args()

# Create output directory if it doesn't exist
os.makedirs(args.output_dir, exist_ok=True)

# Function to get findings data
def get_findings_data():
    if args.input:
        # Load from local file
        with open(args.input, 'r') as f:
            return json.load(f)
    elif args.s3_bucket and args.s3_key:
        # Load from S3
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=args.s3_bucket, Key=args.s3_key)
        return json.loads(response['Body'].read().decode('utf-8'))
    elif args.scan_id:
        # Load from AWS Inspector API
        inspector = boto3.client('inspector2')
        findings = []
        paginator = inspector.get_paginator('list_findings')
        filter_criteria = {
            'sbomScanArn': {
                'comparison': 'EQUALS',
                'value': args.scan_id
            }
        }
        for page in paginator.paginate(filterCriteria=filter_criteria):
            findings.extend(page['findings'])
        return {'findings': findings}
    else:
        print("Error: You must provide either --input, --s3-bucket and --s3-key, or --scan-id")
        sys.exit(1)

# Get findings data
print("Loading findings data...")
data = get_findings_data()

# Check if findings exist
if 'findings' not in data or not data['findings']:
    print("No findings found in the provided data source.")
    sys.exit(0)

# Convert findings to pandas DataFrame for analysis
print("Processing findings data...")
findings = []
for finding in data['findings']:
    # Extract relevant information from each finding
    vulnerability = finding.get('packageVulnerabilityDetails', {})
    
    finding_data = {
        'id': finding.get('findingArn', '').split('/')[-1],
        'severity': finding.get('severity', 'UNKNOWN'),
        'package_name': vulnerability.get('vulnerablePackages', [{}])[0].get('name', 'Unknown'),
        'package_version': vulnerability.get('vulnerablePackages', [{}])[0].get('version', 'Unknown'),
        'vulnerability_id': vulnerability.get('vulnerabilityId', 'Unknown'),
        'cvss_score': vulnerability.get('cvss', [{}])[0].get('baseScore', 0) if vulnerability.get('cvss') else 0,
        'fix_available': 'Yes' if vulnerability.get('fixAvailable') == 'YES' else 'No',
        'first_observed': finding.get('firstObservedAt', ''),
        'last_observed': finding.get('lastObservedAt', ''),
        'description': vulnerability.get('vulnerabilityDetails', {}).get('description', 'No description available')
    }
    findings.append(finding_data)

df = pd.DataFrame(findings)

# Generate timestamp for report files
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

# Create summary statistics
print("Generating summary statistics...")
severity_counts = df['severity'].value_counts().to_dict()
total_vulnerabilities = len(df)
fixable_count = len(df[df['fix_available'] == 'Yes'])
fixable_percentage = (fixable_count / total_vulnerabilities) * 100 if total_vulnerabilities > 0 else 0

# Generate summary report
summary = f"""
# SBOM Vulnerability Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total vulnerabilities: {total_vulnerabilities}
- Critical: {severity_counts.get('CRITICAL', 0)}
- High: {severity_counts.get('HIGH', 0)}
- Medium: {severity_counts.get('MEDIUM', 0)}
- Low: {severity_counts.get('LOW', 0)}
- Fixable vulnerabilities: {fixable_count} ({fixable_percentage:.1f}%)

## Top Vulnerable Packages
"""

# Add top vulnerable packages to summary
top_packages = df['package_name'].value_counts().head(10)
summary += tabulate(
    [[pkg, count] for pkg, count in top_packages.items()],
    headers=['Package', 'Vulnerabilities'],
    tablefmt='pipe'
) + "\n\n"

# Save summary report
summary_path = os.path.join(args.output_dir, f'sbom_analysis_summary_{timestamp}.md')
with open(summary_path, 'w') as f:
    f.write(summary)

print(f"Summary report saved to {summary_path}")

# Set up the visualization style
plt.style.use('ggplot')
sns.set(style="whitegrid")

# Create custom color palette for severity levels
colors = {
    'CRITICAL': '#d62728',  # Red
    'HIGH': '#ff7f0e',      # Orange
    'MEDIUM': '#ffdd57',    # Yellow
    'LOW': '#2ca02c',       # Green
    'UNKNOWN': '#7f7f7f'    # Gray
}

# 1. Severity Distribution Pie Chart
print("Generating severity distribution visualization...")
plt.figure(figsize=(10, 6))
severity_series = df['severity'].value_counts()
plt.pie(
    severity_series, 
    labels=severity_series.index, 
    autopct='%1.1f%%',
    colors=[colors.get(sev, '#7f7f7f') for sev in severity_series.index],
    startangle=90,
    explode=[0.1 if sev == 'CRITICAL' else 0 for sev in severity_series.index]
)
plt.title('Vulnerability Severity Distribution', fontsize=16)
plt.tight_layout()
severity_pie_path = os.path.join(args.output_dir, f'severity_distribution_{timestamp}.png')
plt.savefig(severity_pie_path, dpi=300, bbox_inches='tight')
print(f"Severity distribution chart saved to {severity_pie_path}")

# 2. Top 10 Vulnerable Packages Bar Chart
print("Generating top vulnerable packages visualization...")
plt.figure(figsize=(12, 8))
top_packages = df['package_name'].value_counts().head(10)
bars = plt.bar(
    top_packages.index, 
    top_packages.values,
    color='#1f77b4'
)

# Add severity breakdown to each bar
package_severity = {}
for package in top_packages.index:
    package_df = df[df['package_name'] == package]
    package_severity[package] = package_df['severity'].value_counts()

bottom = np.zeros(len(top_packages))
for severity in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
    heights = [package_severity.get(pkg, pd.Series()).get(severity, 0) for pkg in top_packages.index]
    plt.bar(
        top_packages.index, 
        heights, 
        bottom=bottom, 
        color=colors.get(severity),
        label=severity
    )
    bottom += heights

plt.title('Top 10 Vulnerable Packages', fontsize=16)
plt.xlabel('Package Name', fontsize=12)
plt.ylabel('Number of Vulnerabilities', fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.legend(title='Severity')
plt.tight_layout()
top_packages_path = os.path.join(args.output_dir, f'top_vulnerable_packages_{timestamp}.png')
plt.savefig(top_packages_path, dpi=300, bbox_inches='tight')
print(f"Top vulnerable packages chart saved to {top_packages_path}")

# 3. CVSS Score Distribution
print("Generating CVSS score distribution visualization...")
plt.figure(figsize=(10, 6))
# Create custom colormap from green to red
cmap = LinearSegmentedColormap.from_list('GreenToRed', ['#2ca02c', '#ffdd57', '#ff7f0e', '#d62728'])
sns.histplot(df['cvss_score'], bins=10, kde=True, color='#1f77b4')
plt.title('CVSS Score Distribution', fontsize=16)
plt.xlabel('CVSS Score', fontsize=12)
plt.ylabel('Number of Vulnerabilities', fontsize=12)
plt.axvline(x=7.0, color='orange', linestyle='--', label='High (7.0+)')
plt.axvline(x=9.0, color='red', linestyle='--', label='Critical (9.0+)')
plt.legend()
plt.tight_layout()
cvss_dist_path = os.path.join(args.output_dir, f'cvss_distribution_{timestamp}.png')
plt.savefig(cvss_dist_path, dpi=300, bbox_inches='tight')
print(f"CVSS score distribution chart saved to {cvss_dist_path}")

# 4. Fixable vs Non-Fixable Vulnerabilities
print("Generating fixable vulnerabilities visualization...")
plt.figure(figsize=(8, 8))
fix_counts = df['fix_available'].value_counts()
plt.pie(
    fix_counts, 
    labels=fix_counts.index, 
    autopct='%1.1f%%',
    colors=['#2ca02c', '#d62728'],
    startangle=90,
    explode=[0.1, 0]
)
plt.title('Fixable vs Non-Fixable Vulnerabilities', fontsize=16)
plt.tight_layout()
fixable_pie_path = os.path.join(args.output_dir, f'fixable_vulnerabilities_{timestamp}.png')
plt.savefig(fixable_pie_path, dpi=300, bbox_inches='tight')
print(f"Fixable vulnerabilities chart saved to {fixable_pie_path}")

# 5. Generate detailed CSV report
print("Generating detailed CSV report...")
csv_path = os.path.join(args.output_dir, f'vulnerability_details_{timestamp}.csv')
df.to_csv(csv_path, index=False)
print(f"Detailed CSV report saved to {csv_path}")

# 6. Generate HTML report with embedded visualizations
print("Generating HTML report...")
html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SBOM Vulnerability Analysis Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .summary-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #4285f4;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .critical {{
            color: #d62728;
            font-weight: bold;
        }}
        .high {{
            color: #ff7f0e;
            font-weight: bold;
        }}
        .medium {{
            color: #ffbb33;
            font-weight: bold;
        }}
        .low {{
            color: #2ca02c;
            font-weight: bold;
        }}
        .visualization {{
            margin: 30px 0;
            text-align: center;
        }}
        .visualization img {{
            max-width: 100%;
            height: auto;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
    </style>
</head>
<body>
    <h1>SBOM Vulnerability Analysis Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary-box">
        <h2>Executive Summary</h2>
        <p>Total vulnerabilities: <strong>{total_vulnerabilities}</strong></p>
        <ul>
            <li>Critical: <span class="critical">{severity_counts.get('CRITICAL', 0)}</span></li>
            <li>High: <span class="high">{severity_counts.get('HIGH', 0)}</span></li>
            <li>Medium: <span class="medium">{severity_counts.get('MEDIUM', 0)}</span></li>
            <li>Low: <span class="low">{severity_counts.get('LOW', 0)}</span></li>
        </ul>
        <p>Fixable vulnerabilities: <strong>{fixable_count}</strong> ({fixable_percentage:.1f}%)</p>
    </div>
    
    <div class="dashboard">
        <div class="visualization">
            <h3>Severity Distribution</h3>
            <img src="{os.path.basename(severity_pie_path)}" alt="Severity Distribution">
        </div>
        
        <div class="visualization">
            <h3>Fixable vs Non-Fixable Vulnerabilities</h3>
            <img src="{os.path.basename(fixable_pie_path)}" alt="Fixable vs Non-Fixable">
        </div>
    </div>
    
    <div class="visualization">
        <h3>Top 10 Vulnerable Packages</h3>
        <img src="{os.path.basename(top_packages_path)}" alt="Top Vulnerable Packages">
    </div>
    
    <div class="visualization">
        <h3>CVSS Score Distribution</h3>
        <img src="{os.path.basename(cvss_dist_path)}" alt="CVSS Score Distribution">
    </div>
    
    <h2>Top 10 Critical Vulnerabilities</h2>
    <table>
        <tr>
            <th>Package</th>
            <th>Version</th>
            <th>Vulnerability ID</th>
            <th>CVSS Score</th>
            <th>Fix Available</th>
        </tr>
"""

# Add top critical vulnerabilities to HTML report
critical_vulns = df[df['severity'] == 'CRITICAL'].sort_values('cvss_score', ascending=False).head(10)
for _, vuln in critical_vulns.iterrows():
    html_report += f"""
        <tr>
            <td>{vuln['package_name']}</td>
            <td>{vuln['package_version']}</td>
            <td>{vuln['vulnerability_id']}</td>
            <td>{vuln['cvss_score']}</td>
            <td>{vuln['fix_available']}</td>
        </tr>
    """

html_report += """
    </table>
    
    <h2>Recommendations</h2>
    <ol>
        <li>Address critical vulnerabilities immediately</li>
        <li>Schedule updates for packages with available fixes</li>
        <li>Monitor packages without fixes for updates</li>
        <li>Consider alternative packages for those with multiple critical vulnerabilities</li>
    </ol>
    
    <p><a href="vulnerability_details.csv">Download full vulnerability details (CSV)</a></p>
</body>
</html>
"""

html_path = os.path.join(args.output_dir, f'sbom_analysis_report_{timestamp}.html')
with open(html_path, 'w') as f:
    f.write(html_report)
print(f"HTML report saved to {html_path}")

print("\nAnalysis complete! All reports and visualizations have been saved to the output directory.")
print(f"Open {html_path} in a web browser to view the complete report.")
