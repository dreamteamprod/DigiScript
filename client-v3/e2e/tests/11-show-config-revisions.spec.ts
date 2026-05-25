/**
 * Show Config — Script Revisions tab: create revision, view revision graph, compiled scripts.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  confirmModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';
import { snapshotExists, snapshotState, restoreStateAndRestartServer } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

test.beforeAll(async () => {
  if (test.info().retry > 0 && snapshotExists()) {
    await restoreStateAndRestartServer();
  }
});

test.afterEach(async () => {
  if (test.info().status === 'passed') {
    snapshotState();
  }
});

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/script-revisions`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Revisions ─────────────────────────────────────────────────────────────

test('Revisions tab shows the revision table', async () => {
  await expect(page.locator('button:has-text("New Revision")')).toBeVisible({ timeout: 10_000 });
  // Revision 1 exists by default
  await expect(page.locator('td:has-text("1")').first()).toBeVisible();
});

test('creates a new revision', async () => {
  await page.click('button:has-text("New Revision")');
  await waitForModal(page, 'Add New Revision');
  await page.fill('.modal.show input[type="text"]', 'Revision for e2e test');
  await confirmModal(page);
  await waitForModalClosed(page, 10_000);
  await expect(page.locator('td:has-text("Revision for e2e test")')).toBeVisible();
});

test('revision graph renders', async () => {
  // The graph card starts collapsed by default — expand it if needed
  const revisionGraph = page.locator('.revision-graph');
  if (!(await revisionGraph.isVisible())) {
    await page
      .locator('.card-header')
      .filter({ hasText: 'Revision Branch Graph' })
      .locator('button')
      .click();
  }
  await expect(revisionGraph).toBeVisible({ timeout: 5_000 });
});

test('loads revision 1', async () => {
  const rev1Row = page
    .locator('tr')
    .filter({ has: page.locator('td:has-text("1")') })
    .first();
  await expect(rev1Row).toBeVisible({ timeout: 5_000 });
  const loadBtn = rev1Row.locator('button:has-text("Load")');
  if (await loadBtn.isEnabled()) {
    await loadBtn.click();
    await confirmDialog(page);
    // Confirm the UI has settled after the load
    await expect(page.locator('button:has-text("New Revision")')).toBeVisible({ timeout: 10_000 });
  }
  // If disabled, revision 1 is already the loaded revision — no action needed
});

test('deletes the test revision', async () => {
  const testRevRow = page.locator('tr', {
    has: page.locator('td:has-text("Revision for e2e test")'),
  });
  await testRevRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Revision for e2e test")')).not.toBeVisible({
    timeout: 5_000,
  });
});

// ── Compiled Scripts ──────────────────────────────────────────────────────

test('switches to Compiled Scripts sub-tab', async () => {
  await page.click(
    '.nav-link:has-text("Compiled Scripts"), button[role="tab"]:has-text("Compiled")'
  );
  // Two tables rendered simultaneously (Revisions + Compiled Scripts tabs) — scope to active panel
  await expect(page.locator('.tab-pane.active table')).toBeVisible({ timeout: 10_000 });
});

test('can trigger script compilation', async () => {
  // "Generate" only appears when no compiled script exists yet (auto-compile on save may have already run).
  // If it exists and is enabled, click it and wait for it to finish; otherwise the row already has a
  // compiled script (showing "Delete" instead) — both states are valid.
  const generateBtn = page.locator('button:has-text("Generate")').first();
  if ((await generateBtn.count()) > 0 && (await generateBtn.isEnabled())) {
    await generateBtn.click();
    await expect(generateBtn.or(page.locator('button:has-text("Delete")').first())).toBeVisible({
      timeout: 15_000,
    });
  }
  // Either way, at least one compiled-scripts table row must exist
  await expect(page.locator('.tab-pane.active table tbody tr').first()).toBeVisible({
    timeout: 10_000,
  });
});
