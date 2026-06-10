#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DOCS_DIR = path.join(__dirname, '../../docs');
const OUTPUT_DIR = path.join(__dirname, '../public/docs');
const MANIFEST_PATH = path.join(OUTPUT_DIR, 'manifest.json');

interface ManifestEntry {
  title: string;
  slug: string;
  path: string;
  category: string;
  order: number;
}

function generateSlug(filepath: string): string {
  // pages/getting_started.md → getting-started
  // pages/show_config/acts_and_scenes.md → show-config/acts-and-scenes
  const withoutExt = filepath.replace(/\.md$/, '');
  const withoutPages = withoutExt.replace(/^pages\//, '');
  return withoutPages.replace(/_/g, '-');
}

function extractTitle(content: string, filepath: string): string {
  const parts = filepath.split('/');

  if (parts.length > 2) {
    const h3Match = content.match(/^###\s+(.+)$/m);
    if (h3Match) return h3Match[1];
  }

  const match = content.match(/^##?\s+(.+)$/m);
  if (match) return match[1];

  const filename = parts[parts.length - 1].replace(/\.md$/, '');
  return filename.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractCategory(relativePath: string): string {
  const parts = relativePath.split('/');
  return parts.length > 2 ? parts[1] : 'root';
}

function extractMarkdownLinks(content: string): string[] {
  // Extract all markdown links: [text](./path.md) or [text](path.md)
  return [...content.matchAll(/\[([^\]]+)\]\(([^)]+\.md)\)/g)].map((m) => m[2]);
}

function normalizeLink(currentFile: string, link: string): string {
  const currentDir = path.dirname(currentFile);
  return path.normalize(path.join(currentDir, link)).replace(/\\/g, '/');
}

function buildOrderFromLinks(docsDir: string): string[] {
  const visited = new Set<string>();
  const order: string[] = [];

  function traverse(relativePath: string): void {
    if (visited.has(relativePath)) return;

    const fullPath = path.join(docsDir, relativePath);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) return;

    visited.add(relativePath);
    order.push(relativePath);

    const content = fs.readFileSync(fullPath, 'utf8');
    for (const link of extractMarkdownLinks(content)) {
      traverse(normalizeLink(relativePath, link));
    }
  }

  traverse('index.md');
  return order;
}

function walkDocs(dir: string, basePath = ''): Omit<ManifestEntry, 'order'>[] {
  const manifest: Omit<ManifestEntry, 'order'>[] = [];

  if (!fs.existsSync(dir)) {
    console.warn(`Warning: Directory ${dir} does not exist`);
    return manifest;
  }

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.join(basePath, entry.name);

    if (entry.isDirectory() && entry.name !== 'images') {
      manifest.push(...walkDocs(fullPath, relativePath));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      const content = fs.readFileSync(fullPath, 'utf8');
      manifest.push({
        title: extractTitle(content, relativePath),
        slug: generateSlug(relativePath),
        path: relativePath.replace(/\\/g, '/'),
        category: extractCategory(relativePath),
      });
    }
  }

  return manifest;
}

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

console.log('Generating documentation manifest...');

const linkOrder = buildOrderFromLinks(DOCS_DIR);
console.log(`📊 Discovered ${linkOrder.length} documents via link traversal`);

const orderMap = new Map<string, number>(linkOrder.map((filePath, i) => [filePath, i]));

const manifest: ManifestEntry[] = walkDocs(DOCS_DIR).map((entry) => ({
  ...entry,
  order: orderMap.get(entry.path) ?? 999,
}));

const filteredManifest = manifest
  .filter((entry) => entry.path !== 'index.md')
  .sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order;
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    return a.title.localeCompare(b.title);
  });

fs.writeFileSync(MANIFEST_PATH, JSON.stringify(filteredManifest, null, 2));
console.log(`✅ Generated manifest with ${filteredManifest.length} documents (excluded index.md)`);
console.log(`📄 Manifest saved to: ${MANIFEST_PATH}`);
