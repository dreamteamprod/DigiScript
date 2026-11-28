#!/usr/bin/env node
/**
 * Keeps the user docs and the E2E suite in step.
 *
 * Fails (exit 1) when:
 *  - an image referenced from docs/ has no `docShot(page, '<name>')` call in client/e2e/tests
 *  - an image referenced from docs/ does not exist on disk (never generated / not committed)
 *  - a `docShot()` name is not referenced from docs/ (it would write an unused file)
 *  - the same name is captured by more than one `docShot()` call (the later run would overwrite)
 *  - a PNG under docs/images is neither referenced nor under IGNORED_PREFIXES (an orphan)
 *  - a `docShot()` call's name is not a plain string literal (e.g. `'x' + suffix`), so it cannot
 *    be checked statically
 *
 * The spec files are parsed with the TypeScript compiler API (from client/node_modules, so run
 * `pnpm install` in client/ first), so comments, regex literals and template strings are handled
 * properly and a commented-out `docShot()` does not count as captured.
 *
 * Otherwise pure static analysis - no browser, safe for the normal lint CI. Run from anywhere:
 *   node scripts/check-docs-screenshots.mjs
 */
import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docsDir = path.join(root, 'docs');
const imagesDir = path.join(docsDir, 'images');
const testsDir = path.join(root, 'client', 'e2e', 'tests');

let ts;
try {
  ts = createRequire(path.join(root, 'client', 'package.json'))('typescript');
} catch {
  console.error(
    'Could not load `typescript` from client/node_modules: run `pnpm install` in client/.'
  );
  process.exit(2);
}

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
const byName = (a, b) => a.localeCompare(b);

// Names referenced from the docs, e.g. ../images/config_show/cast_overview.png -> config_show/cast_overview
function referencedNames() {
  const names = new Set();
  for (const file of walk(docsDir, (f) => f.endsWith('.md'))) {
    const text = fs.readFileSync(file, 'utf8');
    for (const match of text.matchAll(/images\/([A-Za-z0-9_/.-]+)\.png/g)) {
      if (!isIgnored(match[1])) names.add(match[1]);
    }
  }
  return names;
}

/** The name of a `docShot(page, '<name>')` call, or null if it isn't a plain string literal. */
function literalName(nameArg) {
  const isLiteral =
    nameArg && (ts.isStringLiteral(nameArg) || ts.isNoSubstitutionTemplateLiteral(nameArg));
  return isLiteral ? nameArg.text : null;
}

/** Every `docShot(...)` call in a spec file, as `{ name | null, where }`. */
function docShotCalls(file) {
  const source = ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true
  );
  const calls = [];
  const visit = (node) => {
    const isDocShot =
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === 'docShot';
    if (isDocShot) {
      const { line } = source.getLineAndCharacterOfPosition(node.getStart());
      calls.push({
        name: literalName(node.arguments[1]),
        where: `${path.relative(root, file)}:${line + 1}`,
      });
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return calls;
}

const referenced = referencedNames();

const captured = new Map(); // name -> [file:line, ...]
const unreadable = []; // docShot() calls whose name isn't a string literal
for (const file of walk(testsDir, (f) => f.endsWith('.spec.ts'))) {
  for (const { name, where } of docShotCalls(file)) {
    if (name === null) unreadable.push(where);
    else captured.set(name, [...(captured.get(name) ?? []), where]);
  }
}

const onDisk = walk(imagesDir, (f) => f.endsWith('.png'))
  .map((f) =>
    path
      .relative(imagesDir, f)
      .replaceAll('\\', '/')
      .replace(/\.png$/, '')
  )
  .filter((n) => !isIgnored(n));
const onDiskSet = new Set(onDisk);

const problems = [];
const report = (title, items) => {
  if (!items.length) return;
  const lines = items.map((i) => `  - ${i}`).join('\n');
  problems.push(`${title} (${items.length}):\n${lines}`);
};

report(
  'Referenced in docs but no docShot() call in client/e2e/tests',
  [...referenced].filter((n) => !captured.has(n)).sort(byName)
);
report(
  'Referenced in docs but the PNG does not exist in docs/images',
  [...referenced].filter((n) => !onDiskSet.has(n)).sort(byName)
);
report("docShot() name is not a plain string literal, so it can't be checked", unreadable);
report(
  'docShot() name not referenced from docs',
  [...captured.keys()].filter((n) => !referenced.has(n)).sort(byName)
);
report(
  'Captured more than once',
  [...captured].filter(([, w]) => w.length > 1).map(([n, w]) => `${n}: ${w.join(', ')}`)
);
report(
  'PNG in docs/images that no doc references (orphan)',
  onDisk.filter((n) => !referenced.has(n)).sort(byName)
);

if (problems.length) {
  console.error(problems.join('\n\n'));
  process.exit(1);
}
console.log(`docs screenshots OK: ${referenced.size} referenced, ${captured.size} captured.`);
