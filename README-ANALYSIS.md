# SBOM Vulnerability Analysis and Visualization

This document explains how to use the SBOM vulnerability analysis and visualization tools included in this project.

## Overview

The SBOM vulnerability analysis tools provide:

1. Comprehensive analysis of AWS Inspector SBOM scan results
2. Visual representations of vulnerability data
3. Actionable insights for remediation
4. Exportable reports in multiple formats

## Using the Analysis Tools

### Automated Analysis in CI/CD Pipeline

The CI/CD pipeline automatically runs the analysis tools after each SBOM scan:

1. The pipeline generates an SBOM for your application
2. AWS Inspector scans the SBOM for vulnerabilities
3. The `sbom-analyzer.py` script processes the findings
4. Visualizations and reports are generated
5. All artifacts are uploaded to the S3 reports bucket

You can access the analysis results in the S3 reports bucket under the `analysis-{timestamp}` prefix.

### Manual Analysis

You can also run the analysis tools manually:

```bash
# Analyze findings from a local file
python sbom-analyzer.py --input findings.json --output-dir ./sbom-analysis

# Analyze findings from an S3 bucket
python sbom-analyzer.py --s3-bucket your-reports-bucket --s3-key findings-20250425-123456.json --output-dir ./sbom-analysis

# Analyze findings directly from AWS Inspector using a scan ID
python sbom-analyzer.py --scan-id 12345678-1234-1234-1234-123456789012 --output-dir ./sbom-analysis
```

## Visualization Types

The analysis tools generate several types of visualizations:

### 1. Severity Distribution Pie Chart

![Severity Distribution](images/severity_distribution_example.png)

This visualization shows the distribution of vulnerabilities by severity level (Critical, High, Medium, Low).

### 2. Top Vulnerable Packages Bar Chart

![Top Vulnerable Packages](images/top_packages_example.png)

This chart identifies the packages with the most vulnerabilities, with bars color-coded by severity.

### 3. CVSS Score Distribution

![CVSS Distribution](images/cvss_distribution_example.png)

This histogram shows the distribution of CVSS scores across all vulnerabilities, with markers for High (7.0+) and Critical (9.0+) thresholds.

### 4. Fixable vs Non-Fixable Vulnerabilities

![Fixable Vulnerabilities](images/fixable_vulnerabilities_example.png)

This pie chart shows the proportion of vulnerabilities that have fixes available.

## Report Formats

The analysis tools generate reports in multiple formats:

1. **HTML Report**: A comprehensive dashboard with embedded visualizations, summary statistics, and recommendations.

2. **Markdown Summary**: A concise summary of findings suitable for inclusion in documentation or GitHub issues.

3. **CSV Export**: A detailed spreadsheet of all vulnerabilities for further analysis.

## Interpreting Results

When reviewing the analysis results, focus on:

1. **Critical and High Severity Vulnerabilities**: These pose the greatest risk and should be addressed first.

2. **Packages with Multiple Vulnerabilities**: Consider updating or replacing packages that appear frequently in the "Top Vulnerable Packages" chart.

3. **Fixable Vulnerabilities**: Prioritize vulnerabilities with available fixes, as these can be remediated quickly.

4. **CVSS Score Trends**: Monitor how CVSS scores change over time to track your security posture.

## Integration with Other Tools

The analysis tools can be integrated with:

- **Slack/Teams Notifications**: Send summary reports to collaboration platforms
- **Jira/GitHub Issues**: Create tickets for vulnerability remediation
- **Security Dashboards**: Export data to security information and event management (SIEM) systems
- **Compliance Reports**: Generate evidence for security compliance requirements

## Customizing Visualizations

You can customize the visualizations by modifying the `sbom-analyzer.py` script:

- Change color schemes
- Adjust chart dimensions
- Add new visualization types
- Modify thresholds for severity classifications

## Best Practices

1. Run analysis after every significant dependency update
2. Review visualizations to identify patterns and trends
3. Prioritize remediation based on severity and fix availability
4. Archive reports for historical comparison
5. Share visualizations with development teams to build security awareness
