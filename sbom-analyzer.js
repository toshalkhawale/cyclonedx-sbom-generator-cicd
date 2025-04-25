/**
 * SBOM Analyzer - A simple tool to analyze CycloneDX SBOMs
 * 
 * This script reads a CycloneDX JSON SBOM and provides basic analysis:
 * - Component count
 * - Dependency tree
 * - License information
 */

const fs = require('fs');
const path = require('path');

// Check if file path is provided
if (process.argv.length < 3) {
  console.error('Please provide the path to a CycloneDX JSON SBOM file');
  console.error('Usage: node sbom-analyzer.js <path-to-sbom.json>');
  process.exit(1);
}

const sbomPath = process.argv[2];

// Read and parse the SBOM file
try {
  const sbomData = JSON.parse(fs.readFileSync(sbomPath, 'utf8'));
  analyzeSbom(sbomData);
} catch (error) {
  console.error(`Error reading or parsing SBOM file: ${error.message}`);
  process.exit(1);
}

/**
 * Analyze the SBOM data and print results
 */
function analyzeSbom(sbom) {
  console.log('='.repeat(50));
  console.log('SBOM ANALYSIS REPORT');
  console.log('='.repeat(50));
  
  // Basic metadata
  console.log('\n📋 SBOM METADATA:');
  console.log(`  Format: ${sbom.bomFormat || 'Unknown'}`);
  console.log(`  Specification Version: ${sbom.specVersion || 'Unknown'}`);
  console.log(`  Serial Number: ${sbom.serialNumber || 'Not specified'}`);
  console.log(`  Version: ${sbom.version || '1'}`);
  
  // Component analysis
  if (sbom.components && Array.isArray(sbom.components)) {
    analyzeComponents(sbom.components);
  } else {
    console.log('\n⚠️  No components found in SBOM');
  }
  
  // Dependencies analysis
  if (sbom.dependencies && Array.isArray(sbom.dependencies)) {
    analyzeDependencies(sbom.dependencies, sbom.components);
  } else {
    console.log('\n⚠️  No dependency information found in SBOM');
  }
  
  console.log('\n='.repeat(50));
}

/**
 * Analyze component information
 */
function analyzeComponents(components) {
  console.log(`\n📦 COMPONENTS (${components.length} total):`);
  
  // Count by type
  const typeCount = {};
  components.forEach(comp => {
    const type = comp.type || 'unknown';
    typeCount[type] = (typeCount[type] || 0) + 1;
  });
  
  console.log('\n  Component types:');
  Object.entries(typeCount).forEach(([type, count]) => {
    console.log(`    - ${type}: ${count}`);
  });
  
  // License analysis
  const licenses = new Set();
  const componentsWithoutLicense = [];
  
  components.forEach(comp => {
    if (comp.licenses && Array.isArray(comp.licenses)) {
      comp.licenses.forEach(license => {
        if (license.license) {
          if (license.license.id) {
            licenses.add(license.license.id);
          } else if (license.license.name) {
            licenses.add(license.license.name);
          }
        }
      });
    } else {
      componentsWithoutLicense.push(comp.name);
    }
  });
  
  console.log('\n  License information:');
  console.log(`    - Unique licenses: ${licenses.size}`);
  console.log(`    - Components without license: ${componentsWithoutLicense.length}`);
  
  if (licenses.size > 0) {
    console.log('    - License types:');
    Array.from(licenses).sort().forEach(license => {
      console.log(`      * ${license}`);
    });
  }
}

/**
 * Analyze dependency relationships
 */
function analyzeDependencies(dependencies, components) {
  console.log('\n🔄 DEPENDENCY ANALYSIS:');
  
  // Create a map of component refs to names for easier lookup
  const componentMap = {};
  if (components && Array.isArray(components)) {
    components.forEach(comp => {
      if (comp.bom && comp.bom.ref) {
        componentMap[comp.bom.ref] = `${comp.name}@${comp.version || 'unknown'}`;
      }
    });
  }
  
  // Find root dependencies (those that are not dependencies of others)
  const allDependencies = new Set();
  const dependencyOf = new Set();
  
  dependencies.forEach(dep => {
    if (dep.ref) {
      allDependencies.add(dep.ref);
    }
    if (dep.dependsOn && Array.isArray(dep.dependsOn)) {
      dep.dependsOn.forEach(childRef => {
        dependencyOf.add(childRef);
      });
    }
  });
  
  const rootDeps = Array.from(allDependencies).filter(ref => !dependencyOf.has(ref));
  
  console.log(`  Root dependencies: ${rootDeps.length}`);
  console.log(`  Total dependency relationships: ${dependencyOf.size}`);
  
  // Print the first few levels of the dependency tree for the first root
  if (rootDeps.length > 0) {
    console.log('\n  Sample dependency tree (first root):');
    const visited = new Set();
    printDependencyTree(rootDeps[0], dependencies, componentMap, '    ', visited, 0, 3);
  }
}

/**
 * Print a dependency tree with limited depth
 */
function printDependencyTree(ref, dependencies, componentMap, indent, visited, currentDepth, maxDepth) {
  if (visited.has(ref) || currentDepth > maxDepth) {
    return;
  }
  
  visited.add(ref);
  console.log(`${indent}- ${componentMap[ref] || ref}`);
  
  const dep = dependencies.find(d => d.ref === ref);
  if (dep && dep.dependsOn && Array.isArray(dep.dependsOn)) {
    dep.dependsOn.forEach(childRef => {
      printDependencyTree(childRef, dependencies, componentMap, indent + '  ', visited, currentDepth + 1, maxDepth);
    });
  }
}
