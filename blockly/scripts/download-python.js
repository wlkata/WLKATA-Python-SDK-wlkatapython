#!/usr/bin/env node
/**
 * Download Standalone Python for Embedding
 *
 * Downloads a standalone, relocatable Python distribution suitable for
 * bundling with the Electron app.
 *
 * For Windows: Uses the official python.org embeddable package (already provided).
 * For macOS:   Downloads from python-build-standalone (indygreg) project.
 *
 * Usage:
 *   node scripts/download-python.js                  # auto-detect platform
 *   node scripts/download-python.js --platform mac   # macOS only
 *   node scripts/download-python.js --platform win   # Windows only
 *   node scripts/download-python.js --platform all   # both platforms
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const PYTHON_VERSION = '3.14.3';

// python-build-standalone release info
// Using cpython-3.13 as 3.14 may not be available yet in standalone builds
// Update this URL when a 3.14 standalone build becomes available
const STANDALONE_VERSION = '20250317';
const STANDALONE_PYTHON = '3.13.2';

const DOWNLOADS = {
  'macos-arm64': {
    url: `https://github.com/indygreg/python-build-standalone/releases/download/${STANDALONE_VERSION}/cpython-${STANDALONE_PYTHON}+${STANDALONE_VERSION}-aarch64-apple-darwin-install_only_stripped.tar.gz`,
    extractDir: 'python',
    targetDir: `python-3.14.3-macos-arm64`,
    type: 'tar.gz',
  },
  'macos-x64': {
    url: `https://github.com/indygreg/python-build-standalone/releases/download/${STANDALONE_VERSION}/cpython-${STANDALONE_PYTHON}+${STANDALONE_VERSION}-x86_64-apple-darwin-install_only_stripped.tar.gz`,
    extractDir: 'python',
    targetDir: `python-3.14.3-macos-x64`,
    type: 'tar.gz',
  },
};

const DIST_DIR = path.join(__dirname, '..', '..', 'dist');

/**
 * Follow redirects and download a file.
 */
function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    console.log(`  Downloading: ${url}`);
    console.log(`  Destination: ${destPath}`);

    const file = fs.createWriteStream(destPath);
    let totalBytes = 0;
    let downloadedBytes = 0;

    const makeRequest = (reqUrl) => {
      const protocol = reqUrl.startsWith('https') ? https : http;
      protocol.get(reqUrl, { headers: { 'User-Agent': 'blockly-python-downloader' } }, (response) => {
        // Handle redirects
        if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
          console.log(`  Redirecting to: ${response.headers.location}`);
          makeRequest(response.headers.location);
          return;
        }

        if (response.statusCode !== 200) {
          file.close();
          fs.unlinkSync(destPath);
          reject(new Error(`Download failed with status ${response.statusCode}`));
          return;
        }

        totalBytes = parseInt(response.headers['content-length'] || '0', 10);

        response.on('data', (chunk) => {
          downloadedBytes += chunk.length;
          if (totalBytes > 0) {
            const pct = ((downloadedBytes / totalBytes) * 100).toFixed(1);
            process.stdout.write(`\r  Progress: ${pct}% (${(downloadedBytes / 1024 / 1024).toFixed(1)} MB)`);
          }
        });

        response.pipe(file);

        file.on('finish', () => {
          file.close();
          console.log(`\n  Download complete: ${(downloadedBytes / 1024 / 1024).toFixed(1)} MB`);
          resolve();
        });
      }).on('error', (err) => {
        file.close();
        if (fs.existsSync(destPath)) fs.unlinkSync(destPath);
        reject(err);
      });
    };

    makeRequest(url);
  });
}

/**
 * Extract a tar.gz archive.
 */
function extractTarGz(archivePath, destDir) {
  console.log(`  Extracting: ${archivePath}`);
  console.log(`  To: ${destDir}`);

  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  execSync(`tar -xzf "${archivePath}" -C "${destDir}"`, { stdio: 'inherit' });
  console.log('  Extraction complete.');
}

/**
 * Download and set up Python for a specific platform.
 */
async function setupPlatform(platformKey) {
  const config = DOWNLOADS[platformKey];
  if (!config) {
    console.log(`  No download configuration for: ${platformKey}`);
    return;
  }

  const targetPath = path.join(DIST_DIR, config.targetDir);

  // Check if already exists
  if (fs.existsSync(targetPath)) {
    console.log(`  ✓ ${config.targetDir} already exists, skipping download.`);
    return;
  }

  console.log(`\n--- Setting up Python for ${platformKey} ---`);

  // Ensure dist directory exists
  if (!fs.existsSync(DIST_DIR)) {
    fs.mkdirSync(DIST_DIR, { recursive: true });
  }

  // Download
  const archiveExt = config.type === 'tar.gz' ? '.tar.gz' : '.zip';
  const archivePath = path.join(DIST_DIR, `${config.targetDir}${archiveExt}`);

  if (!fs.existsSync(archivePath)) {
    await downloadFile(config.url, archivePath);
  } else {
    console.log(`  Archive already downloaded: ${archivePath}`);
  }

  // Extract
  const tempExtractDir = path.join(DIST_DIR, `_temp_${platformKey}`);
  if (fs.existsSync(tempExtractDir)) {
    fs.rmSync(tempExtractDir, { recursive: true });
  }

  if (config.type === 'tar.gz') {
    extractTarGz(archivePath, tempExtractDir);
  }

  // Move the extracted directory to the target name
  const extractedDir = path.join(tempExtractDir, config.extractDir);
  if (fs.existsSync(extractedDir)) {
    fs.renameSync(extractedDir, targetPath);
  } else {
    // If the archive extracts directly without a subdirectory
    fs.renameSync(tempExtractDir, targetPath);
  }

  // Cleanup temp directory
  if (fs.existsSync(tempExtractDir)) {
    fs.rmSync(tempExtractDir, { recursive: true });
  }

  // Make Python executable (macOS/Linux)
  if (process.platform !== 'win32') {
    const binDir = path.join(targetPath, 'bin');
    if (fs.existsSync(binDir)) {
      const files = fs.readdirSync(binDir);
      for (const f of files) {
        if (f.startsWith('python')) {
          fs.chmodSync(path.join(binDir, f), 0o755);
        }
      }
    }
  }

  console.log(`  ✓ ${config.targetDir} is ready.`);
}

async function main() {
  const args = process.argv.slice(2);
  let platform = 'auto';

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--platform' && args[i + 1]) {
      platform = args[i + 1];
      i++;
    }
  }

  console.log('=== Blockly Desktop App - Python Environment Setup ===\n');

  if (platform === 'auto') {
    // Auto-detect current platform
    if (process.platform === 'darwin') {
      const arch = process.arch === 'arm64' ? 'arm64' : 'x64';
      await setupPlatform(`macos-${arch}`);
    } else if (process.platform === 'win32') {
      console.log('  Windows embedded Python should already be in dist/');
      console.log('  Download from: https://www.python.org/downloads/');
    } else {
      console.log(`  Platform ${process.platform} not supported for embedded Python.`);
    }
  } else if (platform === 'mac' || platform === 'macos') {
    await setupPlatform('macos-arm64');
    await setupPlatform('macos-x64');
  } else if (platform === 'win' || platform === 'windows') {
    console.log('  Windows embedded Python should already be in dist/');
    console.log('  Download from: https://www.python.org/downloads/');
  } else if (platform === 'all') {
    await setupPlatform('macos-arm64');
    await setupPlatform('macos-x64');
    console.log('\n  Windows embedded Python should already be in dist/');
  } else {
    console.error(`  Unknown platform: ${platform}`);
    process.exit(1);
  }

  console.log('\n=== Setup complete ===');
}

main().catch((err) => {
  console.error('Setup failed:', err);
  process.exit(1);
});
