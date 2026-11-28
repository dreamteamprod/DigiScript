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
import { registerRetryHooks } from '../db-snapshot.js';
import { newContext, docShot } from '../docs-shots.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

/** Created/edited times in the revisions table are wall-clock values of this run. */
function revisionDates(page: Page) {
  return [
    {
      locator: page.locator('.tab-pane.active table tbody tr td:nth-child(3)'),
      text: '2025-01-06T09:30:12.104744',
    },
    {
      locator: page.locator('.tab-pane.active table tbody tr td:nth-child(4)'),
      text: '2025-01-06T09:41:37.416321',
    },
  ];
}

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await newContext(browser);
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
  await docShot(page, 'config_show/script_revisions', { fixText: revisionDates(page) });
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

test('a graph node opens the revision detail modal', async () => {
  // Revision 1 is current again, so revision 2 shows both Load and Create Branch actions.
  // dispatchEvent: the current revision's node pulses forever, so it is never "stable" to
  // Playwright and a real click can land on the pulse ring instead of the node.
  await page
    .locator('.revision-graph .node-group')
    .filter({ hasText: 'Rev 2' })
    .dispatchEvent('click');
  await waitForModal(page, 'Revision 2');
  await expect(page.locator('.modal.show button:has-text("Load This Revision")')).toBeVisible();
  const detailDates = page.locator('.modal.show dd');
  await docShot(page, 'config_show/script_revision_detail_modal', {
    fixText: [
      { locator: detailDates.nth(2), text: '06/01/2025, 09:41:57' },
      { locator: detailDates.nth(3), text: '06/01/2025, 09:41:57' },
      ...revisionDates(page),
    ],
  });
  await page.locator('.modal.show .modal-footer button:has-text("Close")').click();
  await waitForModalClosed(page);
  // The modal's `hidden` handler (which clears the selected revision) fires after its fade-out;
  // opening another node's modal before then can be swallowed.
  await expect(page.locator('.modal:visible')).toHaveCount(0);
});

test('creates a branch from the current revision, giving the graph two branches', async () => {
  // dispatchEvent: the current revision's node pulses forever, so it is never "stable" to
  // Playwright and a real click can land on the pulse ring instead of the node.
  await page
    .locator('.revision-graph .node-group')
    .filter({ hasText: 'Rev 1' })
    .dispatchEvent('click');
  await waitForModal(page, 'Revision 1');
  await page.locator('.modal.show button:has-text("Create Branch From Here")').click();
  await waitForModal(page, 'Create Revision Branch');
  // The modal clears its form when its `show` event fires (setupBranchForm), which on a slower
  // browser (Firefox in CI) can land after a fill made as soon as the title is visible, leaving
  // OK disabled. Refill until the description has stuck and OK is enabled.
  await expect(async () => {
    await page.fill('.modal.show #branch-description', 'Alternative ending');
    await expect(page.locator('.modal.show .modal-footer button.btn-primary')).toBeEnabled({
      timeout: 1_000,
    });
  }).toPass({ timeout: 15_000 });
  await docShot(page, 'config_show/script_create_branch_modal', {
    fixText: [
      { locator: page.locator('.modal.show dd').nth(2), text: '06/01/2025, 09:41:57' },
      { locator: page.locator('.modal.show dd').nth(3), text: '06/01/2025, 09:41:57' },
      ...revisionDates(page),
    ],
  });
  await confirmModal(page);
  await waitForModalClosed(page, 10_000);
  await expect(page.locator('td:has-text("Alternative ending")')).toBeVisible();
  // Revision 1 now has two children (2 and 3), and the new branch is the current revision.
  await expect(page.locator('.revision-graph .node-group')).toHaveCount(3);
  await docShot(page, 'config_show/script_revision_graph_branched', {
    fixText: revisionDates(page),
  });
});

test('loads revision 1 again and deletes the branch', async () => {
  const rev1Row = page
    .locator('tr')
    .filter({ has: page.locator('td:has-text("1")') })
    .first();
  await rev1Row.locator('button:has-text("Load")').click();
  await confirmDialog(page);
  const branchRow = page.locator('tr', { has: page.locator('td:has-text("Alternative ending")') });
  await expect(branchRow.locator('button:has-text("Delete")')).toBeEnabled({ timeout: 10_000 });
  await branchRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Alternative ending")')).not.toBeVisible({
    timeout: 5_000,
  });
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
