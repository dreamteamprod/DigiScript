/**
 * Show Config — Cues: first-visit empty state, cue type CRUD, Script Cues navigation, counts.
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

// ── Script Cues: first visit, before any cue types exist ───────────────────

test('tabs are Script Cues, Cue Types and Cue Counts, with Script Cues first and active', async () => {
  const tabs = page.locator('.nav-tabs .nav-link');
  await expect(tabs).toHaveText(['Script Cues', 'Cue Types', 'Cue Counts']);
  await expect(page.locator('.nav-tabs .nav-link.active')).toHaveText('Script Cues');
});

test('with no cue types, Script Cues asks for some first', async () => {
  await expect(page.locator('.tab-pane.active')).toContainText('Add your cue types first');
  await expect(
    page.locator('.tab-pane.active button:has-text("Import from Another Show")')
  ).toBeVisible();
});

test('a suggested cue type opens the new type form, pre-filled, on the Cue Types tab', async () => {
  await page.locator('.tab-pane.active .suggestion-chip:has-text("LX")').click();
  await waitForModal(page, /Cue Type/);
  await expect(page.locator('.nav-tabs .nav-link.active')).toHaveText('Cue Types');
  await expect(page.locator('.modal.show #new-prefix-input')).toHaveValue('LX');
  await expect(page.locator('.modal.show #new-description-input')).toHaveValue('Lighting');
});

test('creates the suggested cue type LX', async () => {
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("LX")').first()).toBeVisible();
});

// ── Cue Types ──────────────────────────────────────────────────────────────

test('Cue Types tab shows New Cue Type button', async () => {
  await expect(page.locator('.tab-pane.active button:has-text("New Cue Type")')).toBeVisible();
});

test('opens New Cue Type modal', async () => {
  await page.click('.tab-pane.active button:has-text("New Cue Type")');
  await waitForModal(page, /Cue Type/);
});

test('Save is disabled when prefix is empty', async () => {
  await expect(page.locator('.modal.show .modal-footer button.btn-primary')).toBeDisabled();
});

test('creates a cue type SQ', async () => {
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

// ── Script Cues ───────────────────────────────────────────────────────────

test('switches to the Script Cues tab', async () => {
  await page.click('.nav-link:has-text("Script Cues")');
  // The editor loads the script view — shows page navigation
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 10_000 });
});

test('the toolbar has page navigation, a find box and a cue type filter', async () => {
  await expect(page.locator('button:has-text("Next Page")')).toBeVisible();
  await expect(page.locator('button:has-text("Prev Page")')).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Find a cue' })).toBeVisible();
  const filter = page.getByRole('group', { name: 'Show cue types' });
  await expect(filter.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true');
  await expect(filter.getByRole('button', { name: 'LX' })).toHaveAttribute('aria-pressed', 'false');
});

test('can open the Go to Page dialog in the cue editor', async () => {
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
  await expect(page.getByText('Current Page: 1')).toBeVisible();
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
