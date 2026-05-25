/**
 * Show Config — Script tab: page navigation, edit mode, adding lines.
 * Also covers Stage Direction Styles sub-tab: create and delete a style.
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

test.describe.configure({ mode: 'serial' });

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Script Editor ─────────────────────────────────────────────────────────

test('script editor shows page navigation controls', async () => {
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 15_000 });
});

test('Edit button is visible for admin', async () => {
  await expect(page.locator('button:has-text("Edit")')).toBeVisible();
});

test('requests edit mode', async () => {
  await page.click('button:has-text("Edit")');
  // After WS roundtrip, "Stop Editing" appears instead of "Edit"
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });
});

test('adds a dialogue line', async () => {
  await page.click('button:has-text("Add Dialogue")');
  // A ScriptLineEditor row appears with Done/Delete buttons
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
});

test('adds a stage direction via dropdown', async () => {
  // Split dropdown: click the arrow toggle to open the menu
  await page.click('button.dropdown-toggle-split');
  await page.click('.dropdown-item:has-text("Add Stage Direction")');
  // At least two Done buttons are now visible (one per open editor)
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
});

test('stops editing without saving', async () => {
  await page.click('button:has-text("Stop Editing")');
  // Script has unsaved changes — confirm dialog appears
  await confirmDialog(page);
  // Edit button reappears — use exact match to avoid matching "Stop Editing" / "Bulk Edit"
  await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible({
    timeout: 10_000,
  });
});

test('can navigate to page via Go to Page dialog', async () => {
  await page.click('button:has-text("Go to Page")');
  await waitForModal(page, 'Go to Page');
  await page.fill('.modal.show input[type="number"]', '1');
  await confirmModal(page);
  await waitForModalClosed(page);
});

// ── Save script ────────────────────────────────────────────────────────────

test('saves a dialogue line to the script', async () => {
  await page.click('button:has-text("Edit")');
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });

  await page.click('button:has-text("Add Dialogue")');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });

  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await lineEditor.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await lineEditor.locator('select').nth(1).selectOption({ label: 'Scene 1' });

  await page.locator('select').filter({ hasText: 'Hamlet' }).selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('To be or not to be');

  await page.locator('button:has-text("Done")').first().click();
  // ScriptEditor auto-adds a blank dialogue line after Done — delete it before asserting
  await page.locator('button.btn-danger:has-text("Delete")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });

  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await waitForModal(page, 'Saving Script');
  // The "Saving Script" modal is ok-only and stays open until the user clicks OK.
  // Wait for save to finish (footer OK button appears when savingInProgress = false).
  await expect(page.locator('.modal.show').getByText('Finished saving script.')).toBeVisible({
    timeout: 15_000,
  });
  await confirmModal(page);
  await waitForModalClosed(page);

  await expect(
    page.locator('.viewable-line').filter({ hasText: 'To be or not to be' })
  ).toBeVisible({ timeout: 10_000 });
});

// ── Stage Direction Styles ────────────────────────────────────────────────

test('switches to Stage Direction Styles sub-tab', async () => {
  await page.click('.nav-link:has-text("Stage Direction Styles")');
  await expect(page.locator('button:has-text("New Style")')).toBeVisible({ timeout: 5_000 });
});

test('creates a stage direction style', async () => {
  await page.click('button:has-text("New Style")');
  await waitForModal(page, 'Add New Style');
  await page.fill('.modal.show input[type="text"]', 'Action');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Action")')).toBeVisible();
});

test('deletes the stage direction style', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Action")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Action")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Cue editor — add/edit/delete ──────────────────────────────────────────

test('navigates to cue editor with saved script content', async () => {
  await page.goto(`${UI_BASE}/show-config/cues`);
  await waitForAppReady(page);
  await page.click(
    '.nav-link:has-text("Cue Configuration"), button[role="tab"]:has-text("Cue Config")'
  );
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 10_000 });
  // .first() avoids strict-mode violation: BVN keeps the Add New Cue modal in the DOM
  // (v-show), and its preview also contains a .viewable-line with this text.
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'To be or not to be' }).first()
  ).toBeVisible({ timeout: 10_000 });
});

test('adds a cue to the script line', async () => {
  await page.locator('.add-cue-btn').first().click();
  await waitForModal(page, 'Add New Cue');
  // Scope to the visible modal's select to avoid matching the hidden "Add Cue Type" modal
  // dialog which BVN assigns id="new-cue-type" via its auto-ID scheme.
  await page.locator('.modal.show select#new-cue-type').selectOption({ index: 1 });
  await page.fill('#new-cue-ident', '001');
  await confirmModal(page);
  await waitForModalClosed(page);
  // Wait for the actual cue button (not the add-cue-btn which shares the cue-button class)
  // to confirm the WS update delivered the new cue to the store before proceeding.
  await expect(page.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({ timeout: 5_000 });
});

test('edits the cue identifier', async () => {
  // Use :not(.add-cue-btn) to target the real cue button, not the add button
  await page.locator('.cue-button:not(.add-cue-btn)').first().click();
  await waitForModal(page, 'Edit Cue');
  await page.fill('#edit-cue-ident', '002');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({ timeout: 5_000 });
});

test('deletes the cue', async () => {
  await page.locator('.cue-button:not(.add-cue-btn)').first().click();
  await waitForModal(page, 'Edit Cue');
  // Clicking Delete in Edit Cue opens a stacked ConfirmDialog (BVN modal via useConfirm),
  // not a browser dialog — scope to it by title to avoid clicking the wrong modal's button.
  await page.locator('.modal.show button:has-text("Delete")').click();
  await waitForModal(page, 'Delete Cue');
  await page
    .locator('.modal.show')
    .filter({ has: page.locator('.modal-title:has-text("Delete Cue")') })
    .locator('.modal-footer button.btn-danger')
    .click();
  // After deletion only the add-cue-btn remains; no actual cue buttons should exist
  await expect(page.locator('.cue-button:not(.add-cue-btn)')).not.toBeVisible({ timeout: 5_000 });
});
