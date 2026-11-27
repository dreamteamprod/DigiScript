#!/usr/bin/env node
/**
 * Keeps the user docs and the E2E suite in step.
 *
 * Fails (exit 1) when:
 *  - an image referenced from docs/ has no `docShot('<name>')` call in client/e2e/tests
 *  - a `docShot()` name is not referenced from docs/ (it would write an unused file)
 *  - the same name is captured by more than one `docShot()` call (the later run would overwrite)
 *  - a PNG under docs/images is neither referenced nor in IGNORED (an orphan)
 *
 * Pure static analysis - no browser, safe for the normal lint CI. Run from anywhere:
 *   node scripts/check-docs-screenshots.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docsDir = path.join(root, 'docs');
const imagesDir = path.join(docsDir, 'images');
const testsDir = path.join(root, 'client', 'e2e', 'tests');

/** Images that are intentionally not E2E-generated screenshots. */
const IGNORED_PREFIXES = ['brand/'];

function walk(dir, predicate) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full, predicate));
    else if (predicate(full)) out.push(full);
  }
  return out;
}

const isIgnored = (name) => IGNORED_PREFIXES.some((p) => name.startsWith(p));

// Names referenced from the docs, e.g. ../images/config_show/cast_overview.png -> config_show/cast_overview
const referenced = new Set();
for (const file of walk(docsDir, (f) => f.endsWith('.md'))) {
  for (const match of fs.readFileSync(file, 'utf8').matchAll(/images\/([A-Za-z0-9_/.-]+)\.png/g)) {
    if (!isIgnored(match[1])) referenced.add(match[1]);
  }
}

// Names captured by the E2E suite.
const captured = new Map(); // name -> [file:line, ...]
for (const file of walk(testsDir, (f) => f.endsWith('.spec.ts'))) {
  const text = fs.readFileSync(file, 'utf8');
  for (const match of text.matchAll(/docShot\(\s*[A-Za-z0-9_.]+\s*,\s*'([^']+)'/g)) {
    const line = text.slice(0, match.index).split('\n').length;
    const where = `${path.relative(root, file)}:${line}`;
    captured.set(match[1], [...(captured.get(match[1]) ?? []), where]);
  }
}

const onDisk = walk(imagesDir, (f) => f.endsWith('.png'))
  .map((f) => path.relative(imagesDir, f).replace(/\\/g, '/').replace(/\.png$/, ''))
  .filter((n) => !isIgnored(n));

const problems = [];
const report = (title, items) => {
  if (items.length) problems.push(`${title} (${items.length}):\n${items.map((i) => `  - ${i}`).join('\n')}`);
};

report(
  'Referenced in docs but no docShot() call in client/e2e/tests',
  [...referenced].filter((n) => !captured.has(n)).sort()
);
report(
  'docShot() name not referenced from docs',
  [...captured.keys()].filter((n) => !referenced.has(n)).sort()
);
report(
  'Captured more than once',
  [...captured].filter(([, w]) => w.length > 1).map(([n, w]) => `${n}: ${w.join(', ')}`)
);
report(
  'PNG in docs/images that no doc references (orphan)',
  onDisk.filter((n) => !referenced.has(n)).sort()
);

if (problems.length) {
  console.error(problems.join('\n\n'));
  process.exit(1);
}
console.log(`docs screenshots OK: ${referenced.size} referenced, ${captured.size} captured.`);
