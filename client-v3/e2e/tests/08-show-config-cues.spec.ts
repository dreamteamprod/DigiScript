/**
 * Show Config — Cues tab: cue type CRUD, cue editor navigation, import cue types.
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

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/cues`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Cue Types ──────────────────────────────────────────────────────────────

test('Cue Types tab shows New Cue Type button', async () => {
  await expect(page.locator('button:has-text("New Cue Type")')).toBeVisible();
});

test('opens New Cue Type modal', async () => {
  await page.click('button:has-text("New Cue Type")');
  await waitForModal(page, /Cue Type/);
});

test('Save is disabled when prefix is empty', async () => {
  await expect(page.locator('.modal.show .modal-footer button.btn-primary')).toBeDisabled();
});

test('creates a cue type LX', async () => {
  await page.fill('.modal.show input[type="text"]', 'LX');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("LX")').first()).toBeVisible();
});

test('creates a cue type SQ', async () => {
  await page.click('button:has-text("New Cue Type")');
  await waitForModal(page, /Cue Type/);
  await page.fill('.modal.show input[type="text"]', 'SQ');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("SQ")').first()).toBeVisible();
});

test('edits a cue type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("SQ")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, /Edit.*Cue Type|Cue Type/);
  const prefixInput = page.locator('.modal.show input[type="text"]').first();
  await prefixInput.fill('SFX');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("SFX")').first()).toBeVisible();
});

test('deletes a cue type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("SFX")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("SFX")').first()).not.toBeVisible({ timeout: 5_000 });
});

// ── Cue Editor ────────────────────────────────────────────────────────────

test('switches to Cue Configuration sub-tab', async () => {
  await page.click(
    '.nav-link:has-text("Cue Configuration"), button[role="tab"]:has-text("Cue Config")'
  );
  // Cue editor loads the script view — shows page navigation
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 10_000 });
});

test('cue editor navigation buttons are rendered', async () => {
  // With no script content there is only one page; verify nav controls are present
  await expect(page.locator('button:has-text("Next")').first()).toBeVisible();
  await expect(
    page.locator('button:has-text("Prev"), button:has-text("Previous")').first()
  ).toBeVisible();
});

test('can open the Go to Page dialog in cue editor', async () => {
  await page.click('button:has-text("Go to Page")');
  await waitForModal(page, 'Go to Page');
  // Cancel the dialog — no script pages exist yet at this point in the test suite
  await page.click(
    '.modal.show .modal-footer button.btn-secondary, .modal.show button:has-text("Cancel")'
  );
  await waitForModalClosed(page);
});

test('Go to Page submits and navigates to the requested page', async () => {
  await page.click('button:has-text("Go to Page")');
  await waitForModal(page, 'Go to Page');
  await page.fill('.modal.show input[type="number"]', '1');
  await confirmModal(page);
  // If the fix is working, clicking OK closes the modal; previously Vuelidate prevented this
  await waitForModalClosed(page);
  await expect(page.locator('p.mb-0:has-text("Current Page: 1")')).toBeVisible();
});

// ── Cue Renumber ──────────────────────────────────────────────────────────

test('Renumber Cues button is visible in Cue Configuration tab toolbar', async () => {
  await page.click(
    '.nav-link:has-text("Cue Configuration"), button[role="tab"]:has-text("Configuration")'
  );
  await expect(page.locator('button:has-text("Renumber Cues")')).toBeVisible();
});

test('opens Renumber Cues modal at step 1', async () => {
  await page.click('button:has-text("Renumber Cues")');
  await waitForModal(page, 'Renumber Cues');
  // Step 1 shows the method selector
  await expect(page.locator('.modal.show select')).toBeVisible();
});

test('Next button is disabled until a cue type is selected', async () => {
  await expect(page.locator('.modal.show button:has-text("Next")')).toBeDisabled();
});

test('Next button enables after selecting a cue type', async () => {
  // Select the first cue type checkbox
  await page.click('.modal.show input[type="checkbox"]:first-of-type');
  await expect(page.locator('.modal.show button:has-text("Next")')).toBeEnabled();
});

test('step 2 shows empty state when no cues are placed', async () => {
  await page.click('.modal.show button:has-text("Next")');
  // No cues have been placed in the script at this point in the serial suite
  await expect(
    page.locator('.modal.show p.text-muted:has-text("No cues require renumbering")')
  ).toBeVisible();
});

test('Back button returns to step 1', async () => {
  await page.click('.modal.show button:has-text("Back")');
  // Step 1 is shown again
  await expect(page.locator('.modal.show button:has-text("Next")')).toBeVisible();
});

test('Cancel closes the Renumber Cues modal', async () => {
  await page.click('.modal.show button:has-text("Cancel")');
  await waitForModalClosed(page);
});

// ── Cue Counts ────────────────────────────────────────────────────────────

test('switches to Cue Counts sub-tab', async () => {
  await page.click('.nav-link:has-text("Cue Counts"), button[role="tab"]:has-text("Counts")');
  // Stats view loads — scope to active tab panel to avoid matching hidden panels
  await expect(
    page
      .locator('.tab-pane.active .center-spinner')
      .or(page.locator('.tab-pane.active table'))
      .or(page.locator('.tab-pane.active b'))
  ).toBeVisible({ timeout: 5_000 });
});
