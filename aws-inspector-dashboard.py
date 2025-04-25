#!/usr/bin/env python3

"""
AWS Inspector SBOM Scan Dashboard Generator

This script:
1. Retrieves AWS Inspector SBOM scan results from S3
2. Generates an HTML dashboard with vulnerability insights
3. Provides filtering and sorting capabilities
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime
from collections import defaultdict

# HTML template for the dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Inspector SBOM Scan Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            background-color: #232f3e;
            color: white;
            padding: 1rem;
            margin-bottom: 2rem;
        }
        h1 {
            margin: 0;
        }
        .summary-cards {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 2rem;
        }
        .card {
            flex: 1;
            min-width: 200px;
            padding: 1rem;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin-top: 0;
        }
        .critical { background-color: #ff8c8c; }
        .high { background-color: #ffb38c; }
        .medium { background-color: #ffde8c; }
        .low { background-color: #d6ff8c; }
        
        .filters {
            margin-bottom: 1rem;
            padding: 1rem;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 2rem;
        }
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
            cursor: pointer;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        
        .severity-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            color: white;
            font-weight: bold;
        }
        .severity-CRITICAL { background-color: #d13212; }
        .severity-HIGH { background-color: #ff9900; }
        .severity-MEDIUM { background-color: #d9b43f; }
        .severity-LOW { background-color: #7fba00; }
        .severity-INFORMATIONAL { background-color: #999999; }
        
        .chart-container {
            display: flex;
            gap: 20px;
            margin-bottom: 2rem;
        }
        .chart {
            flex: 1;
            min-height: 300px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 1rem;
        }
        
        footer {
            margin-top: 2rem;
            text-align: center;
            color: #666;
            font-size: 0.8rem;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>AWS Inspector SBOM Scan Dashboard</h1>
            <p>Generated on: {{GENERATION_DATE}}</p>
        </header>
        
        <div class="summary-cards">
            <div class="card critical">
                <h3>Critical Vulnerabilities</h3>
                <p class="count">{{CRITICAL_COUNT}}</p>
            </div>
            <div class="card high">
                <h3>High Vulnerabilities</h3>
                <p class="count">{{HIGH_COUNT}}</p>
            </div>
            <div class="card medium">
                <h3>Medium Vulnerabilities</h3>
                <p class="count">{{MEDIUM_COUNT}}</p>
            </div>
            <div class="card low">
                <h3>Low Vulnerabilities</h3>
                <p class="count">{{LOW_COUNT}}</p>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart">
                <h3>Vulnerabilities by Severity</h3>
                <canvas id="severityChart"></canvas>
            </div>
            <div class="chart">
                <h3>Top Vulnerable Components</h3>
                <canvas id="componentsChart"></canvas>
            </div>
        </div>
        
        <div class="filters">
            <h3>Filters</h3>
            <div>
                <label for="severity-filter">Severity:</label>
                <select id="severity-filter">
                    <option value="all">All</option>
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                </select>
                
                <label for="component-filter" style="margin-left: 20px;">Component:</label>
                <select id="component-filter">
                    <option value="all">All</option>
                    {{COMPONENT_OPTIONS}}
                </select>
                
                <button id="apply-filters" style="margin-left: 20px;">Apply Filters</button>
            </div>
        </div>
        
        <h2>Vulnerability Findings</h2>
        <table id="findings-table">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Component</th>
                    <th onclick="sortTable(1)">Version</th>
                    <th onclick="sortTable(2)">Vulnerability ID</th>
                    <th onclick="sortTable(3)">Severity</th>
                    <th onclick="sortTable(4)">Description</th>
                </tr>
            </thead>
            <tbody>
                {{TABLE_ROWS}}
            </tbody>
        </table>
        
        <footer>
            <p>Generated using AWS Inspector SBOM scanning. Data from {{RESULTS_BUCKET}}</p>
        </footer>
    </div>
    
    <script>
        // Chart for vulnerabilities by severity
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        const severityChart = new Chart(severityCtx, {
            type: 'pie',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [{{CRITICAL_COUNT}}, {{HIGH_COUNT}}, {{MEDIUM_COUNT}}, {{LOW_COUNT}}],
                    backgroundColor: ['#d13212', '#ff9900', '#d9b43f', '#7fba00']
                }]
            }
        });
        
        // Chart for top vulnerable components
        const componentsCtx = document.getElementById('componentsChart').getContext('2d');
        const componentsChart = new Chart(componentsCtx, {
            type: 'bar',
            data: {
                labels: {{COMPONENT_LABELS}},
                datasets: [{
                    label: 'Vulnerabilities',
                    data: {{COMPONENT_DATA}},
                    backgroundColor: '#232f3e'
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
        
        // Table sorting function
        function sortTable(n) {
            const table = document.getElementById("findings-table");
            let switching = true;
            let dir = "asc";
            let switchcount = 0;
            
            while (switching) {
                switching = false;
                const rows = table.rows;
                
                for (let i = 1; i < (rows.length - 1); i++) {
                    let shouldSwitch = false;
                    const x = rows[i].getElementsByTagName("TD")[n];
                    const y = rows[i + 1].getElementsByTagName("TD")[n];
                    
                    if (dir == "asc") {
                        if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    } else if (dir == "desc") {
                        if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                            shouldSwitch = true;
                            break;
                        }
                    }
                }
                
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                } else {
                    if (switchcount == 0 && dir == "asc") {
                        dir = "desc";
                        switching = true;
                    }
                }
            }
        }
        
        // Filtering functionality
        document.getElementById('apply-filters').addEventListener('click', function() {
            const severityFilter = document.getElementById('severity-filter').value;
            const componentFilter = document.getElementById('component-filter').value;
            
            const rows = document.getElementById('findings-table').getElementsByTagName('tbody')[0].rows;
            
            for (let i = 0; i < rows.length; i++) {
                const component = rows[i].cells[0].textContent;
                const severity = rows[i].cells[3].textContent;
                
                let showRow = true;
                
                if (severityFilter !== 'all' && severity !== severityFilter) {
                    showRow = false;
                }
                
                if (componentFilter !== 'all' && component !== componentFilter) {
                    showRow = false;
                }
                
                rows[i].style.display = showRow ? '' : 'none';
            }
        });
    </script>
</body>
</html>
"""

def parse_args():
    parser = argparse.ArgumentParser(description='Generate AWS Inspector SBOM Scan Dashboard')
    parser.add_argument('--bucket', required=True, help='S3 bucket containing scan results')
    parser.add_argument('--output', default='inspector-dashboard.html', help='Output HTML file')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--max-scans', type=int, default=10, help='Maximum number of scans to process')
    return parser.parse_args()

def get_scan_results(bucket, region, max_scans):
    """Retrieve scan results from S3 bucket"""
    s3_client = boto3.client('s3', region_name=region)
    
    # List all scan directories
    scan_dirs = []
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix='scans/', Delimiter='/')
    
    for page in pages:
        for prefix in page.get('CommonPrefixes', []):
            scan_dirs.append(prefix.get('Prefix'))
    
    # Sort by most recent (assuming directory names contain timestamps)
    scan_dirs.sort(reverse=True)
    
    # Limit to max_scans
    scan_dirs = scan_dirs[:max_scans]
    
    all_findings = []
    
    for scan_dir in scan_dirs:
        try:
            # Get the findings file
            findings_obj = s3_client.get_object(Bucket=bucket, Key=f"{scan_dir}findings.json")
            findings_data = json.loads(findings_obj['Body'].read().decode('utf-8'))
            
            # Get the summary file
            summary_obj = s3_client.get_object(Bucket=bucket, Key=f"{scan_dir}summary.json")
            summary_data = json.loads(summary_obj['Body'].read().decode('utf-8'))
            
            # Add scan ID to each finding
            for finding in findings_data.get('findings', []):
                finding['scanId'] = summary_data.get('scanId')
                finding['scanName'] = summary_data.get('scanName')
                finding['completedAt'] = summary_data.get('completedAt')
                all_findings.append(finding)
                
        except Exception as e:
            print(f"Error processing scan {scan_dir}: {e}")
    
    return all_findings

def generate_dashboard(findings, output_file, bucket_name):
    """Generate HTML dashboard from findings"""
    # Count vulnerabilities by severity
    severity_counts = defaultdict(int)
    for finding in findings:
        severity = finding.get('severity', 'INFORMATIONAL')
        severity_counts[severity] += 1
    
    # Count vulnerabilities by component
    component_counts = defaultdict(int)
    for finding in findings:
        component = finding.get('packageVulnerabilityDetails', {}).get('vulnerablePackages', [{}])[0].get('name', 'Unknown')
        component_counts[component] += 1
    
    # Get top 10 vulnerable components
    top_components = sorted(component_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    component_labels = [f'"{c[0]}"' for c in top_components]
    component_data = [c[1] for c in top_components]
    
    # Generate component options for filter
    unique_components = sorted(set(c[0] for c in component_counts.items()))
    component_options = '\n'.join([f'<option value="{c}">{c}</option>' for c in unique_components])
    
    # Generate table rows
    table_rows = []
    for finding in findings:
        vuln_package = finding.get('packageVulnerabilityDetails', {}).get('vulnerablePackages', [{}])[0]
        component = vuln_package.get('name', 'Unknown')
        version = vuln_package.get('version', 'Unknown')
        vuln_id = finding.get('vulnerabilityId', 'Unknown')
        severity = finding.get('severity', 'INFORMATIONAL')
        description = finding.get('title', 'No description available')
        
        row = f"""
        <tr>
            <td>{component}</td>
            <td>{version}</td>
            <td>{vuln_id}</td>
            <td><span class="severity-badge severity-{severity}">{severity}</span></td>
            <td>{description}</td>
        </tr>
        """
        table_rows.append(row)
    
    # Replace placeholders in template
    html_content = HTML_TEMPLATE
    html_content = html_content.replace('{{GENERATION_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    html_content = html_content.replace('{{CRITICAL_COUNT}}', str(severity_counts.get('CRITICAL', 0)))
    html_content = html_content.replace('{{HIGH_COUNT}}', str(severity_counts.get('HIGH', 0)))
    html_content = html_content.replace('{{MEDIUM_COUNT}}', str(severity_counts.get('MEDIUM', 0)))
    html_content = html_content.replace('{{LOW_COUNT}}', str(severity_counts.get('LOW', 0)))
    html_content = html_content.replace('{{COMPONENT_OPTIONS}}', component_options)
    html_content = html_content.replace('{{TABLE_ROWS}}', '\n'.join(table_rows))
    html_content = html_content.replace('{{COMPONENT_LABELS}}', '[' + ', '.join(component_labels) + ']')
    html_content = html_content.replace('{{COMPONENT_DATA}}', '[' + ', '.join(map(str, component_data)) + ']')
    html_content = html_content.replace('{{RESULTS_BUCKET}}', bucket_name)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Dashboard generated: {output_file}")

def main():
    args = parse_args()
    
    print(f"Retrieving scan results from bucket: {args.bucket}")
    findings = get_scan_results(args.bucket, args.region, args.max_scans)
    
    if not findings:
        print("No findings retrieved. Check bucket name and permissions.")
        return 1
    
    print(f"Found {len(findings)} vulnerability findings")
    generate_dashboard(findings, args.output, args.bucket)
    return 0

if __name__ == "__main__":
    sys.exit(main())
