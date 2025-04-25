FROM node:16-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package.json ./
RUN npm install

# Copy application code
COPY index.js ./

# Create directories for SBOM generation
RUN mkdir -p sbom-output vulnerability-reports

# Copy SBOM generation scripts
COPY generate-sbom.sh ./
COPY vulnerability-check.sh ./
COPY sbom-analyzer.js ./

# Make scripts executable
RUN chmod +x generate-sbom.sh vulnerability-check.sh

# Install tools for SBOM generation
RUN apk add --no-cache bash curl python3 py3-pip

# Install CycloneDX tools
RUN npm install -g @cyclonedx/cyclonedx-npm

EXPOSE 3000

# Command to run the application
CMD ["node", "index.js"]
