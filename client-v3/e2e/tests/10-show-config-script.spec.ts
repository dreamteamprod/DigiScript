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
import { registerRetryHooks } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

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

  await lineEditor
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('To be or not to be');

  await page.locator('button:has-text("Done")').first().click();
  // ScriptEditor auto-adds a blank dialogue editor after Done — fill it in as a second line so
  // the bulk edit tests below can use a two-line range without needing the split dropdown.
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });

  const lineEditor2 = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await lineEditor2.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await lineEditor2.locator('select').nth(1).selectOption({ label: 'Scene 1' });
  await lineEditor2
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('That is the question');

  await page.locator('button:has-text("Done")').first().click();
  // Delete the third auto-added blank editor
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
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'That is the question' })
  ).toBeVisible({ timeout: 10_000 });
});

// ── Bulk edit ─────────────────────────────────────────────────────────────

test('bulk edit mode is accessible and shows Start/End buttons', async () => {
  // Still in edit mode from the save test, which saved two viewable dialogue lines.
  await page.click('button:has-text("Bulk Edit")');
  // Two ScriptLineViewer rows → two Start/End button pairs
  await expect(page.getByRole('button', { name: 'Start', exact: true }).first()).toBeVisible({
    timeout: 5_000,
  });
  await expect(page.getByRole('button', { name: 'End', exact: true }).first()).toBeVisible({
    timeout: 5_000,
  });
});

test('bulk edit opens the Bulk Edit modal when start and end span two different lines', async () => {
  // Start on the first line, End on the last line (different indices → valid range)
  await page.getByRole('button', { name: 'Start', exact: true }).first().click();
  await page.getByRole('button', { name: 'End', exact: true }).last().click();
  await waitForModal(page, 'Bulk Edit');
});

test('bulk edit can assign a character to part 1', async () => {
  await page.locator('.modal.show #bulk-part-input').selectOption({ label: 'Part 1' });
  // Select Alice — a different character from Hamlet (who is already assigned) so the apply
  // produces a real change that scriptChanges can detect via deep equality.
  await page.locator('.modal.show #bulk-char-input').selectOption({ label: 'Alice' });
  await confirmModal(page);
  await waitForModalClosed(page);
  // After apply, bulk edit mode exits automatically
  await expect(page.getByRole('button', { name: 'Bulk Edit', exact: true })).toBeVisible({
    timeout: 5_000,
  });
});

test('bulk edit stops when Exit Bulk Edit is clicked', async () => {
  await page.click('button:has-text("Bulk Edit")');
  await expect(page.getByRole('button', { name: 'Start', exact: true }).first()).toBeVisible({
    timeout: 5_000,
  });
  await page.click('button:has-text("Exit Bulk Edit")');
  await expect(page.getByRole('button', { name: 'Start', exact: true })).not.toBeVisible({
    timeout: 3_000,
  });
  await page.click('button:has-text("Stop Editing")');
  await confirmDialog(page);
  await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible({
    timeout: 10_000,
  });
});

// ── Cut mode ──────────────────────────────────────────────────────────────

test('enters cut mode', async () => {
  await page.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(page);
  await page.click('button:has-text("Cuts")');
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });
});

test('dialogue line becomes clickable in cut mode', async () => {
  await expect(
    page.locator('a.viewable-line-cut').filter({ hasText: 'To be or not to be' })
  ).toBeVisible({ timeout: 5_000 });
});

test('clicking a line toggles cut styling', async () => {
  await page.locator('a.viewable-line-cut').filter({ hasText: 'To be or not to be' }).click();
  await expect(
    page.locator('.cut-line-part').filter({ hasText: 'To be or not to be' })
  ).toBeVisible({ timeout: 3_000 });
});

test('saves cuts', async () => {
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.locator('.v-toast__text').filter({ hasText: /saved/i })).toBeVisible({
    timeout: 5_000,
  });
});

test('stops cut mode without blank-page flash', async () => {
  // In cut mode the line is an anchor (.viewable-line-cut); verify it exists before stopping
  await expect(
    page.locator('.viewable-line-cut').filter({ hasText: 'To be or not to be' })
  ).toBeVisible();

  await page.click('button:has-text("Stop Editing")');

  // Edit button reappears
  await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible({
    timeout: 10_000,
  });
  // The saved line is still visible (no reload / blank flash)
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'To be or not to be' })
  ).toBeVisible();
  // No edit controls are shown after stopping
  await expect(page.locator('.script-edit-controls')).not.toBeVisible();
});

test('cut styling persists after re-entering cut mode', async () => {
  await page.click('button:has-text("Cuts")');
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });
  await expect(
    page.locator('.cut-line-part').filter({ hasText: 'To be or not to be' })
  ).toBeVisible({ timeout: 5_000 });
  // Clean up: un-cut the line so later tests start from a known state
  await page.locator('a.viewable-line-cut').filter({ hasText: 'To be or not to be' }).click();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.locator('.v-toast__text').filter({ hasText: /saved/i })).toBeVisible({
    timeout: 5_000,
  });
  await page.click('button:has-text("Stop Editing")');
  await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible({
    timeout: 10_000,
  });
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
  await waitForModal(page, 'Add Cue');
  // Individual Cue tab is active by default — no extra click needed
  // Scope to the visible modal's select to avoid matching the hidden "Add Cue Type" modal
  // dialog which BVN assigns id="new-cue-type" via its auto-ID scheme.
  await page.locator('.modal.show select#new-cue-type').selectOption({ index: 1 });
  await page.locator('.modal.show #new-cue-ident').fill('001');
  await confirmModal(page);
  await waitForModalClosed(page);
  // Wait for the actual cue button (not the add-cue-btn which shares the cue-button class)
  // to confirm the WS update delivered the new cue to the store before proceeding.
  await expect(page.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({
    timeout: 5_000,
  });
});

test('edits the cue identifier', async () => {
  // Use :not(.add-cue-btn) to target the real cue button, not the add button
  await page.locator('.cue-button:not(.add-cue-btn)').first().click();
  await waitForModal(page, 'Edit Cue');
  await page.locator('.modal.show #edit-cue-ident').fill('002');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({
    timeout: 5_000,
  });
});

test('can add a cue using Enter key in Add New Cue modal', async () => {
  await page.locator('.add-cue-btn').first().click();
  await waitForModal(page, 'Add Cue');
  // Individual Cue tab is active by default — no extra click needed
  await page.locator('.modal.show select#new-cue-type').selectOption({ index: 1 });
  await page.locator('.modal.show #new-cue-ident').fill('003');
  // Enter key submits the form (fix: BForm @submit bound to onSubmitNew)
  // Scope to .modal.show to avoid strict-mode violation from other Add New Cue modal instances
  // in the DOM (one per viewable script line — BVN v-show keeps them all present).
  await page.locator('.modal.show #new-cue-ident').press('Enter');
  await waitForModalClosed(page);
  await expect(page.locator('.cue-button:not(.add-cue-btn)')).toHaveCount(2, { timeout: 5_000 });
});

test('can edit a cue identifier using Enter key in Edit Cue modal', async () => {
  // Click the second cue button (003)
  await page.locator('.cue-button:not(.add-cue-btn)').last().click();
  await waitForModal(page, 'Edit Cue');
  await page.locator('.modal.show #edit-cue-ident').fill('004');
  // Enter key submits the form (fix: BForm @submit bound to onSubmitEdit)
  await page.locator('.modal.show #edit-cue-ident').press('Enter');
  await waitForModalClosed(page);
  await expect(page.locator('.cue-button:not(.add-cue-btn)')).toHaveCount(2, { timeout: 5_000 });
});

test('Jump to Cue navigates and auto-closes the modal', async () => {
  await page.click('button:has-text("Go to Cue")');
  await waitForModal(page, 'Jump to Cue');
  await page.locator('.modal.show select').selectOption({ index: 1 }); // LX type
  await page.locator('.modal.show input').fill('004');
  await confirmModal(page); // Click Search
  // Single exact match → navigateToMatch() now calls modal.hide() (fix)
  await waitForModalClosed(page);
  await expect(page.locator('.v-toast__text').filter({ hasText: /Jumped to/ })).toBeVisible({
    timeout: 5_000,
  });
});

test('deletes the Enter-key-added cue', async () => {
  // Removes the LX 004 cue created in the Enter key test, leaving only LX 002
  await page.locator('.cue-button:not(.add-cue-btn)').last().click();
  await waitForModal(page, 'Edit Cue');
  await page.locator('.modal.show button:has-text("Delete")').click();
  await waitForModal(page, 'Delete Cue');
  await page
    .locator('.modal.show')
    .filter({ has: page.locator('.modal-title:has-text("Delete Cue")') })
    .locator('.modal-footer button.btn-danger')
    .click();
  await expect(page.locator('.cue-button:not(.add-cue-btn)')).toHaveCount(1, { timeout: 5_000 });
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

// ── Cue Groups ────────────────────────────────────────────────────────────

test('opens Add Cue modal with Individual Cue and Cue Group tabs', async () => {
  // After individual cue tests all cues have been deleted. Still on the cue config page.
  await page.locator('.add-cue-btn').first().click();
  await waitForModal(page, 'Add Cue');
  await expect(page.locator('.modal.show .nav-link:has-text("Individual Cue")')).toBeVisible();
  await expect(page.locator('.modal.show .nav-link:has-text("Cue Group")')).toBeVisible();
  // Dismiss modal
  await page.keyboard.press('Escape');
  await waitForModalClosed(page);
});

test('switches to Cue Group tab to show group form', async () => {
  await page.locator('.add-cue-btn').first().click();
  await waitForModal(page, 'Add Cue');
  await page.locator('.modal.show .nav-link:has-text("Cue Group")').click();
  // Wait for tab content to be visible (BTabs lazy may delay mount)
  await expect(page.locator('.modal.show input[placeholder="1 > 100"]')).toBeVisible({
    timeout: 10_000,
  });
});

test('selects cue type and adds range 1 > 5', async () => {
  // Select the LX cue type (first real option after N/A placeholder)
  await page.locator('.modal.show select').selectOption({ index: 1 });
  await page.locator('.modal.show input[placeholder="1 > 100"]').fill('1 > 5');
  await page.locator('.modal.show button:has-text("Add Range")').click();
  // 5 cue ident inputs should appear
  await expect(page.locator('.modal.show input[placeholder="Identifier"]')).toHaveCount(5, {
    timeout: 3_000,
  });
});

test('saves the cue group and shows a dashed group button with range label', async () => {
  await page.locator('.modal.show button:has-text("Save Group")').click();
  await waitForModalClosed(page);
  await expect(page.locator('.cue-group-btn').first()).toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.cue-group-btn').first()).toContainText('LX 1 - LX 5');
});

test('clicks group button to open Edit Cue Group modal with 5 cues listed', async () => {
  await page.locator('.cue-group-btn').first().click();
  await waitForModal(page, 'Edit Cue Group');
  await expect(page.locator('.modal.show input[placeholder="Identifier"]')).toHaveCount(5, {
    timeout: 5_000,
  });
});

test('adds label override and group button label updates on save', async () => {
  await page.locator('.modal.show input[placeholder="e.g. Music Intro"]').fill('Music Intro');
  await page.locator('.modal.show button:has-text("Save Group")').click();
  await waitForModalClosed(page);
  await expect(page.locator('.cue-group-btn').first()).toContainText('LX - Music Intro');
});

test('deletes the cue group and column returns to empty', async () => {
  await page.locator('.cue-group-btn').first().click();
  await waitForModal(page, 'Edit Cue Group');
  await page.locator('.modal.show button:has-text("Delete Group")').click();
  // useConfirm opens a stacked BVN modal — scope to its title to avoid intercepting the
  // Edit Cue Group modal footer behind it.
  await waitForModal(page, 'Delete Cue Group');
  await page
    .locator('.modal.show')
    .filter({ has: page.locator('.modal-title:has-text("Delete Cue Group")') })
    .locator('.modal-footer button.btn-danger')
    .click();
  await expect(page.locator('.cue-group-btn')).not.toBeVisible({ timeout: 5_000 });
});

// ── Line part removal ──────────────────────────────────────────────────────

test('remove button is absent on a single-part dialogue line', async () => {
  await page.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(page);
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });

  await page.click('button:has-text("Add Dialogue")');
  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await expect(lineEditor.locator('button:has-text("Done")')).toBeVisible({ timeout: 5_000 });

  // With only 1 part no remove button should be present
  await expect(lineEditor.locator('button.btn-outline-danger')).not.toBeVisible();
});

test('remove button appears when a second part is added', async () => {
  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();

  // btn-secondary is the add-line-part (+) button — only btn-secondary in the editor row
  await lineEditor.locator('button.btn-secondary').click();

  // One remove button per part
  await expect(lineEditor.locator('button.btn-outline-danger')).toHaveCount(2, { timeout: 3_000 });
});

test('clicking remove reduces to single part and hides the remove button', async () => {
  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();

  await lineEditor.locator('button.btn-outline-danger').first().click();

  // Back to 1 part — remove button gone
  await expect(lineEditor.locator('button.btn-outline-danger')).not.toBeVisible({ timeout: 3_000 });
});

test('dialogue line with removed part saves correctly', async () => {
  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();

  await lineEditor.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await lineEditor.locator('select').nth(1).selectOption({ label: 'Scene 1' });
  await lineEditor
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await lineEditor.locator('input[type="text"]').last().fill('Surviving part text');

  await lineEditor.locator('button:has-text("Done")').click();
  // Delete the auto-added blank editor that appears after Done
  await page.locator('button.btn-danger:has-text("Delete")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });

  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await waitForModal(page, 'Saving Script');
  await expect(page.locator('.modal.show').getByText('Finished saving script.')).toBeVisible({
    timeout: 15_000,
  });
  await confirmModal(page);
  await waitForModalClosed(page);

  await expect(
    page.locator('.viewable-line').filter({ hasText: 'Surviving part text' })
  ).toBeVisible({ timeout: 10_000 });
});
