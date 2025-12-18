#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.join(__dirname, '../../docs');
const OUTPUT_DIR = path.join(__dirname, '../public/docs');
const MANIFEST_PATH = path.join(OUTPUT_DIR, 'manifest.json');

function generateSlug(filepath) {
  // pages/getting_started.md → getting-started
  // pages/show_config/acts_and_scenes.md → show-config/acts-and-scenes
  const withoutExt = filepath.replace(/\.md$/, '');
  // Remove 'pages/' prefix if present
  const withoutPages = withoutExt.replace(/^pages\//, '');
  return withoutPages.replace(/_/g, '-');
}

function extractTitle(content, filepath) {
  // For nested docs (e.g., show_config/*), extract H3 title
  // For root docs, extract H1/H2 title
  const parts = filepath.split('/');

  if (parts.length > 2) {
    // Nested document - try to extract H3 first
    const h3Match = content.match(/^###\s+(.+)$/m);
    if (h3Match) {
      return h3Match[1];
    }
  }

  // Fall back to H1/H2
  const match = content.match(/^##?\s+(.+)$/m);
  if (match) {
    return match[1];
  }

  // Last resort: generate from filename
  const filename = parts[parts.length - 1].replace(/\.md$/, '');
  return filename
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractCategory(relativePath) {
  // pages/getting_started.md → root
  // pages/show_config/acts_and_scenes.md → show_config
  const parts = relativePath.split('/');
  if (parts.length > 2) {
    return parts[1]; // Return subdirectory name
  }
  return 'root';
}

function extractMarkdownLinks(content) {
  // Extract all markdown links: [text](./path.md) or [text](path.md)
  const linkRegex = /\[([^\]]+)\]\(([^)]+\.md)\)/g;
  const links = [];
  let match;

  while ((match = linkRegex.exec(content)) !== null) {
    links.push(match[2]); // The URL part
  }

  return links;
}

function normalizeLink(currentFile, link) {
  // Convert relative link to absolute path within docs
  // currentFile: 'index.md' or 'pages/getting_started.md'
  // link: './pages/getting_started.md' or '../pages/show_config.md'

  const currentDir = path.dirname(currentFile);
  const absolutePath = path.join(currentDir, link);

  // Normalize path (resolve .. and .)
  const normalized = path.normalize(absolutePath);

  // Convert backslashes to forward slashes for consistency
  return normalized.replace(/\\/g, '/');
}

function buildOrderFromLinks(docsDir) {
  const visited = new Set();
  const order = [];

  function traverse(relativePath) {
    // Skip if already visited
    if (visited.has(relativePath)) {
      return;
    }

    // Check if file exists
    const fullPath = path.join(docsDir, relativePath);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) {
      return;
    }

    visited.add(relativePath);
    order.push(relativePath);

    // Read file and extract links
    const content = fs.readFileSync(fullPath, 'utf8');
    const links = extractMarkdownLinks(content);

    // Recursively traverse each link
    for (const link of links) {
      const normalizedLink = normalizeLink(relativePath, link);
      traverse(normalizedLink);
    }
  }

  // Start traversal from index.md
  traverse('index.md');

  return order;
}

function walkDocs(dir, basePath = '') {
  const manifest = [];

  // Check if directory exists
  if (!fs.existsSync(dir)) {
    console.warn(`Warning: Directory ${dir} does not exist`);
    return manifest;
  }

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.join(basePath, entry.name);

    if (entry.isDirectory() && entry.name !== 'images') {
      // Recursively walk subdirectories
      manifest.push(...walkDocs(fullPath, relativePath));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      const content = fs.readFileSync(fullPath, 'utf8');
      const title = extractTitle(content, relativePath);
      const slug = generateSlug(relativePath);
      const category = extractCategory(relativePath);

      manifest.push({
        title,
        slug,
        path: relativePath.replace(/\\/g, '/'),
        category,
      });
    }
  }

  return manifest;
}

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

console.log('Generating documentation manifest...');

// Build link order by traversing from index.md
const linkOrder = buildOrderFromLinks(DOCS_DIR);
console.log(`📊 Discovered ${linkOrder.length} documents via link traversal`);

// Walk all docs to get complete manifest
const manifest = walkDocs(DOCS_DIR);

// Create order map from link traversal
const orderMap = new Map();
linkOrder.forEach((path, index) => {
  orderMap.set(path, index);
});

// Add order to each manifest entry
manifest.forEach((entry) => {
  const order = orderMap.get(entry.path);
  entry.order = order !== undefined ? order : 999;
});

// Filter out index.md since we have a navigation sidebar instead
const filteredManifest = manifest.filter((entry) => entry.path !== 'index.md');

// Sort manifest by order, then by category and title
filteredManifest.sort((a, b) => {
  // First, sort by link order
  if (a.order !== b.order) {
    return a.order - b.order;
  }
  // Then by category
  if (a.category !== b.category) {
    return a.category.localeCompare(b.category);
  }
  // Finally by title
  return a.title.localeCompare(b.title);
});

fs.writeFileSync(MANIFEST_PATH, JSON.stringify(filteredManifest, null, 2));
console.log(`✅ Generated manifest with ${filteredManifest.length} documents (excluded index.md)`);
console.log(`📄 Manifest saved to: ${MANIFEST_PATH}`);
