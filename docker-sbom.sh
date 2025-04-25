#!/bin/bash

# Script to generate CycloneDX SBOM for Docker images
# This demonstrates how to create SBOMs for container images

set -e

echo "Starting Docker image SBOM generation with CycloneDX..."

# Create output directory
mkdir -p sbom-output

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Install Syft if not already installed
install_syft() {
  if ! command_exists syft; then
    echo "Installing Syft..."
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
  fi
}

# Generate SBOM for a Docker image
generate_docker_sbom() {
  local image_name=$1
  local output_file=$2
  
  echo "Generating SBOM for Docker image: $image_name"
  
  # Use Syft to generate CycloneDX SBOM
  syft "$image_name" -o cyclonedx-json > "$output_file"
  
  echo "Docker image SBOM generated: $output_file"
}

# Main execution
install_syft

# Example Docker images to analyze
# You can replace these with your own images
generate_docker_sbom "node:16-alpine" "sbom-output/node-alpine-sbom.json"
generate_docker_sbom "python:3.9-slim" "sbom-output/python-slim-sbom.json"

echo "Docker SBOM generation complete! Files are available in the sbom-output directory."
