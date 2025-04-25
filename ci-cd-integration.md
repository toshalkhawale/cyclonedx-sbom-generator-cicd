# CI/CD Integration for SBOM Generation

This document provides examples of how to integrate SBOM generation into various CI/CD pipelines.

## GitHub Actions Example

```yaml
name: Generate SBOM

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  generate-sbom:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    
    - name: Install dependencies
      run: npm install
    
    - name: Install CycloneDX tools
      run: npm install -g @cyclonedx/cyclonedx-npm
    
    - name: Generate SBOM
      run: |
        mkdir -p sbom-output
        cyclonedx-npm --output-format json --output-file sbom-output/nodejs-sbom.json
        cyclonedx-npm --output-format xml --output-file sbom-output/nodejs-sbom.xml
    
    - name: Upload SBOM as artifact
      uses: actions/upload-artifact@v3
      with:
        name: sbom-files
        path: sbom-output/
```

## GitLab CI Example

```yaml
stages:
  - build
  - sbom
  - analyze

build:
  stage: build
  image: node:16
  script:
    - npm install
  artifacts:
    paths:
      - node_modules/

generate-sbom:
  stage: sbom
  image: node:16
  script:
    - npm install -g @cyclonedx/cyclonedx-npm
    - mkdir -p sbom-output
    - cyclonedx-npm --output-format json --output-file sbom-output/nodejs-sbom.json
    - cyclonedx-npm --output-format xml --output-file sbom-output/nodejs-sbom.xml
  artifacts:
    paths:
      - sbom-output/

analyze-vulnerabilities:
  stage: analyze
  image: anchore/grype:latest
  script:
    - grype sbom:sbom-output/nodejs-sbom.json -o json > vulnerability-report.json
  artifacts:
    paths:
      - vulnerability-report.json
```

## Jenkins Pipeline Example

```groovy
pipeline {
    agent {
        docker {
            image 'node:16'
        }
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'npm install'
            }
        }
        
        stage('Generate SBOM') {
            steps {
                sh 'npm install -g @cyclonedx/cyclonedx-npm'
                sh 'mkdir -p sbom-output'
                sh 'cyclonedx-npm --output-format json --output-file sbom-output/nodejs-sbom.json'
                sh 'cyclonedx-npm --output-format xml --output-file sbom-output/nodejs-sbom.xml'
            }
        }
        
        stage('Analyze Vulnerabilities') {
            agent {
                docker {
                    image 'anchore/grype:latest'
                    reuseNode true
                }
            }
            steps {
                sh 'grype sbom:sbom-output/nodejs-sbom.json -o json > vulnerability-report.json'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'sbom-output/*, vulnerability-report.json', fingerprint: true
        }
    }
}
```

## AWS CodeBuild Example

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 16
    commands:
      - npm install -g @cyclonedx/cyclonedx-npm
      - curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
  
  pre_build:
    commands:
      - npm install
  
  build:
    commands:
      - mkdir -p sbom-output
      - cyclonedx-npm --output-format json --output-file sbom-output/nodejs-sbom.json
      - cyclonedx-npm --output-format xml --output-file sbom-output/nodejs-sbom.xml
  
  post_build:
    commands:
      - grype sbom:sbom-output/nodejs-sbom.json -o json > vulnerability-report.json

artifacts:
  files:
    - sbom-output/**/*
    - vulnerability-report.json
```

## Best Practices for CI/CD Integration

1. **Generate SBOMs early** in the build process to catch issues sooner
2. **Store SBOMs as artifacts** for future reference and compliance
3. **Automate vulnerability scanning** as part of the pipeline
4. **Fail builds** on critical vulnerabilities or policy violations
5. **Integrate with security tools** like Dependabot, Snyk, or Anchore
6. **Version your SBOMs** alongside your application releases
7. **Include SBOM verification** in your release approval process
