#!/bin/bash

# Script to generate CycloneDX SBOM for a sample application
# This script supports multiple package ecosystems

set -e

echo "Starting SBOM generation with CycloneDX..."

# Create output directory
mkdir -p sbom-output

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Install CycloneDX CLI tools if not already installed
install_cyclonedx_tools() {
  echo "Installing CycloneDX tools..."
  
  if ! command_exists npm; then
    echo "npm is required but not installed. Please install Node.js and npm first."
    exit 1
  fi
  
  # Install CycloneDX NPM module globally if not already installed
  if ! command_exists cyclonedx-npm; then
    echo "Installing @cyclonedx/cyclonedx-npm..."
    npm install -g @cyclonedx/cyclonedx-npm
  fi
}

# Generate SBOM for Node.js project
generate_nodejs_sbom() {
  echo "Generating SBOM for Node.js project..."
  
  if [ -f "package.json" ]; then
    cyclonedx-npm --output-format json --output-file sbom-output/nodejs-sbom.json
    cyclonedx-npm --output-format xml --output-file sbom-output/nodejs-sbom.xml
    echo "Node.js SBOM generated successfully!"
  else
    echo "No package.json found. Skipping Node.js SBOM generation."
  fi
}

# Generate SBOM for Python project (if applicable)
generate_python_sbom() {
  echo "Checking for Python project..."
  
  if [ -f "requirements.txt" ]; then
    if ! command_exists cyclonedx-py; then
      echo "Installing cyclonedx-py..."
      pip install cyclonedx-bom
    fi
    
    cyclonedx-py -i requirements.txt -o sbom-output/python-sbom.json --format json
    cyclonedx-py -i requirements.txt -o sbom-output/python-sbom.xml --format xml
    echo "Python SBOM generated successfully!"
  else
    echo "No requirements.txt found. Skipping Python SBOM generation."
  fi
}

# Generate SBOM for Java project (if applicable)
generate_java_sbom() {
  echo "Checking for Java project..."
  
  if [ -f "pom.xml" ]; then
    if ! command_exists cyclonedx-maven-plugin; then
      echo "For Java projects, please run: mvn org.cyclonedx:cyclonedx-maven-plugin:makeAggregateBom"
      echo "Skipping Java SBOM generation in this script."
    fi
  else
    echo "No pom.xml found. Skipping Java SBOM generation."
  fi
}

# Validate the generated SBOM
validate_sbom() {
  echo "Validating generated SBOM..."
  
  if [ -f "sbom-output/nodejs-sbom.json" ]; then
    echo "SBOM validation would be performed here (requires additional tools)"
    # In a real scenario, you might use the CycloneDX CLI tool for validation
  fi
}

# Main execution
install_cyclonedx_tools
generate_nodejs_sbom
generate_python_sbom
generate_java_sbom
validate_sbom

echo "SBOM generation complete! Files are available in the sbom-output directory."
