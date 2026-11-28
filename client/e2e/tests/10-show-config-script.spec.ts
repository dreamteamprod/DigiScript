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
  selectLines,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';
import { newContext, docShot } from '../docs-shots.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await newContext(browser);
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
  await docShot(page, 'config_show/script_empty');
});

test('Edit button is visible for admin', async () => {
  await expect(page.locator('button:has-text("Edit")')).toBeVisible();
});

test('requests edit mode', async () => {
  await page.click('button:has-text("Edit")');
  // After WS roundtrip, "Stop Editing" appears instead of "Edit"
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 10_000 });
});

test('reloading while editing keeps edit mode', async () => {
  // A reload closes and reopens the WebSocket; the reconnect resumes the same
  // client id (REFRESH_CLIENT) inside the server's reconnect grace window, so the
  // edit lock is kept rather than released (issue #1419).
  await page.reload();
  await waitForAppReady(page);
  await expect(page.locator('button:has-text("Stop Editing")')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: 'Edit', exact: true })).not.toBeVisible();
});

test('adds a dialogue line', async () => {
  await page.click('button:has-text("Add Dialogue")');
  // A ScriptLineEditor row appears with Done/Delete buttons
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await docShot(page, 'config_show/script_dialogue_line_editing');
  await page.locator('button:has-text("Delete Line")').first().click();
  await expect(page.locator('button:has-text("Done")')).toHaveCount(0);
});

test('adds a stage direction via the add-to-end-of-page footer', async () => {
  await page.click('button:has-text("Add Direction")');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await docShot(page, 'config_show/script_stage_direction_editing');
  await page.locator('button:has-text("Delete Line")').first().click();
  await expect(page.locator('button:has-text("Done")')).toHaveCount(0);
});

test('adds a cue line', async () => {
  await page.click('button:has-text("Add Cue")');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await docShot(page, 'config_show/script_cue_line_editing');
  await page.locator('button:has-text("Delete Line")').first().click();
  await expect(page.locator('button:has-text("Done")')).toHaveCount(0);
});

test('adds a spacing line', async () => {
  await page.click('button:has-text("Add Gap")');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await docShot(page, 'config_show/script_spacing_line_editing');
  // Left open: the next test stops editing with an unsaved change and must be asked to confirm.
});

test('stops editing without saving', async () => {
  await page.click('button:has-text("Stop Editing")');
  // Script has unsaved changes — confirm dialog appears
  await confirmDialog(page);
  // Edit button reappears — use exact match to avoid matching "Stop Editing"
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
  // First line on the page: no previous line to inherit an act/scene from, so the
  // card falls back to showing the selects directly (Design E).
  await lineEditor.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await lineEditor.locator('select').nth(1).selectOption({ label: 'Scene 1' });

  await lineEditor
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('To be or not to be');

  // Enter chains straight into a new blank dialogue line below, inheriting the
  // act/scene just set (Design E's keyboard flow) — Done alone no longer chains.
  await page.locator('input[type="text"]:visible').last().press('Enter');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });

  const lineEditor2 = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await lineEditor2
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('That is the question');

  await page.locator('button:has-text("Done")').first().click();
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

// ── Click to edit (Design E) ────────────────────────────────────────────────

test('clicking "Click to edit" on an existing saved line reopens it in place', async () => {
  // Still in edit mode from the save test, which saved two viewable dialogue lines.
  const row = page.locator('.script-line-row').filter({ hasText: 'That is the question' });
  await row.locator('.line-edit-trigger').click();

  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  // The opened line's text lives in an <input> value, not plain text content.
  await expect(page.locator('input[type="text"]:visible').last()).toHaveValue(
    'That is the question'
  );

  // Esc closes it again without changing anything (same as Done, but no save needed
  // here since nothing was edited). The input takes focus a frame after mounting, so
  // wait for that first — a page-level Esc sent earlier lands on <body> and does nothing.
  await expect(page.locator('input[type="text"]:visible').last()).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'That is the question' })
  ).toBeVisible();
});

// ── Keyboard flow (Design E) ────────────────────────────────────────────────

test('ArrowUp / ArrowDown move the open editor between lines, and Shift+Tab reaches the character select', async () => {
  const openInput = () => page.locator('.line-editor-card input[type="text"]:visible');
  const secondRow = page.locator('.script-line-row').filter({ hasText: 'That is the question' });
  await secondRow.locator('.line-edit-trigger').click();
  await expect(openInput()).toHaveValue('That is the question', { timeout: 5_000 });

  // Up closes this line and opens the one above it — one editor open at a time.
  await openInput().press('ArrowUp');
  await expect(openInput()).toHaveValue('To be or not to be', { timeout: 5_000 });
  await expect(page.locator('.line-editor-card')).toHaveCount(1);

  await openInput().press('ArrowDown');
  await expect(openInput()).toHaveValue('That is the question', { timeout: 5_000 });
  await expect(page.locator('.line-editor-card')).toHaveCount(1);

  // Shift+Tab goes back from the text field to the character select before it. Wait for
  // the freshly opened card's own deferred autofocus to land first, or it can steal focus
  // back to the text field after the keypress.
  await expect(openInput()).toBeFocused();
  await openInput().press('Shift+Tab');
  await expect(page.locator('.line-editor-card select:focus')).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page.locator('.line-editor-card')).toHaveCount(0, { timeout: 5_000 });
});

test('Esc and Enter leave an invalid line open instead of closing it', async () => {
  await page.click('button:has-text("Add Dialogue")');
  const card = page.locator('.line-editor-card');
  await expect(card).toHaveCount(1, { timeout: 5_000 });

  // A fresh dialogue line has no text or speaker yet, so it is invalid — and Done is
  // disabled while it is, which proves the premise rather than assuming it.
  await expect(card.getByRole('button', { name: 'Done' })).toBeDisabled();
  const input = card.locator('input[type="text"]:visible');

  // A bare count check right after the keypress would pass before a (buggy) close had
  // any chance to run, so let the key handler and Vue's re-render finish first.
  const settle = () =>
    page.evaluate(
      () => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())))
    );
  await input.press('Enter');
  await settle();
  await expect(card).toHaveCount(1);
  await input.press('Escape');
  await settle();
  await expect(card).toHaveCount(1);

  // Scoped to the card: an unscoped `.first()` can hit another Delete Line button.
  await card.getByRole('button', { name: 'Delete Line' }).click();
  await expect(card).toHaveCount(0, { timeout: 5_000 });
});

// ── Selection bar (Design E) ────────────────────────────────────────────────

test('ticking a line number starts a selection and shows the selection bar', async () => {
  // Still in edit mode from the save test, which saved two viewable dialogue lines.
  const firstLineRow = page.locator('.script-line-row').filter({ hasText: 'To be or not to be' });
  await firstLineRow.hover();
  await firstLineRow.getByRole('checkbox').click();

  await expect(page.locator('text=1 line selected')).toBeVisible({ timeout: 5_000 });
});

test('ticking the sole selected line again deselects it', async () => {
  // Regression: re-ticking an already-selected line's own checkbox used to
  // leave it "stuck" selected (bar still showing "1 line selected") while the
  // checkbox itself rendered unchecked — see ScriptEditor.vue's
  // onToggleSelect for why re-setting the range to the identical
  // {page, lineIndex} it already held never reconciled the checkbox's native
  // checked state back after the browser flipped it on click.
  const row = page.locator('.script-line-row').filter({ hasText: 'To be or not to be' });
  const checkbox = row.getByRole('checkbox');
  await row.hover();
  await checkbox.click();

  await expect(page.locator('text=1 line selected')).not.toBeVisible({ timeout: 5_000 });
  await expect(checkbox).not.toBeChecked();

  // Restore the selection — the next test assumes it's already active.
  await row.hover();
  await checkbox.click();
  await expect(page.locator('text=1 line selected')).toBeVisible({ timeout: 5_000 });
});

test('a second tick extends the selection to cover both lines', async () => {
  const secondLineRow = page
    .locator('.script-line-row')
    .filter({ hasText: 'That is the question' });
  await secondLineRow.hover();
  await secondLineRow.getByRole('checkbox').click();

  await expect(page.locator('text=2 lines selected')).toBeVisible({ timeout: 5_000 });
});

test('clicking the range’s own start line shrinks it, keeping the rest selected', async () => {
  // Regression: this used to collapse the whole range down to just the
  // clicked line, deselecting everything else — surprising for a UI where
  // every other checkbox behaves like a normal toggle. Ticking an endpoint
  // of a multi-line range now drops just that one line and keeps the rest
  // selected, same as nextSelectionRange's own unit tests
  // (scriptSelectionModel.test.ts) verify directly.
  const firstLineRow = page.locator('.script-line-row').filter({ hasText: 'To be or not to be' });
  const secondLineRow = page
    .locator('.script-line-row')
    .filter({ hasText: 'That is the question' });
  await selectLines(page, ['To be or not to be', 'That is the question']);

  await firstLineRow.hover();
  await firstLineRow.getByRole('checkbox').click();

  await expect(page.locator('text=1 line selected')).toBeVisible({ timeout: 5_000 });
  await expect(firstLineRow.getByRole('checkbox')).not.toBeChecked();
  await expect(secondLineRow.getByRole('checkbox')).toBeChecked();
});

test('Set Character or Group changes the selected lines’ speaker', async () => {
  const firstLineRow = page.locator('.script-line-row').filter({ hasText: 'To be or not to be' });
  await selectLines(page, ['To be or not to be', 'That is the question']);

  await page.click('button:has-text("Set Character or Group")');
  await waitForModal(page, 'Set Character or Group');
  // Alice — a different character from Hamlet (who is already assigned) so the
  // apply produces a real change that scriptChanges can detect via deep equality.
  await page.getByTestId('set-character-select').selectOption({ label: 'Alice' });
  await confirmModal(page);
  await waitForModalClosed(page);

  // The speaker actually changed. Only the first of the two previously-selected
  // lines is checked here: the second one is now consecutive with the same
  // speaker, so its own heading correctly collapses (ScriptLineViewer.vue's
  // needsHeadings) rather than repeating "Alice" — checking its rendered text
  // would be asserting the wrong thing, not verifying the apply itself.
  await expect(firstLineRow).toContainText('Alice');

  // Applying clears the selection automatically. A loose `text=line selected`
  // locator would pass this vacuously for a 2+-line selection (it doesn't
  // match "2 lines selected" either way) whether or not the selection actually
  // cleared — the toolbar's own accessible name is unambiguous.
  await expect(page.getByRole('toolbar', { name: 'Selected lines' })).toBeHidden({
    timeout: 5_000,
  });
});

test('Space on a focused line checkbox toggles the selection', async () => {
  await selectLines(page, ['To be or not to be']);
  await page.getByRole('button', { name: 'Clear Selection' }).click();

  const checkbox = page
    .locator('.script-line-row')
    .filter({ hasText: 'To be or not to be' })
    .getByRole('checkbox');
  await checkbox.focus();
  await page.keyboard.press('Space');
  await expect(page.locator('text=1 line selected')).toBeVisible({ timeout: 5_000 });
  await expect(checkbox).toBeChecked();

  await page.keyboard.press('Space');
  await expect(page.getByRole('toolbar', { name: 'Selected lines' })).toBeHidden({
    timeout: 5_000,
  });
});

test('Move to Scene applies the chosen act and scene to the selection and clears it', async () => {
  // Only Act 1 / Scene 1 exist by this point in the serial suite (spec 05 deletes the
  // others), so the move can't change a visible label — this covers the flow: the modal
  // opens, offers the act/scene, applies, closes, and the selection clears.
  await selectLines(page, ['To be or not to be', 'That is the question']);

  await page.click('button:has-text("Move to Scene")');
  await waitForModal(page, 'Move to Scene');
  await page.getByTestId('bulk-act-select').selectOption({ label: 'Act 1' });
  await page.getByTestId('bulk-scene-select').selectOption({ label: 'Scene 1' });
  await confirmModal(page);
  await waitForModalClosed(page);

  await expect(page.getByRole('toolbar', { name: 'Selected lines' })).toBeHidden({
    timeout: 5_000,
  });
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'To be or not to be' })
  ).toBeVisible();
});

test('Clear Selection removes the selection bar', async () => {
  await selectLines(page, ['To be or not to be']);
  await expect(page.locator('button:has-text("Clear Selection")')).toBeVisible({
    timeout: 5_000,
  });

  await page.click('button:has-text("Clear Selection")');
  await expect(page.locator('button:has-text("Clear Selection")')).not.toBeVisible({
    timeout: 3_000,
  });
});

// Last in the selection block: it deletes lines from the unsaved edit, and ends the
// editing session, discarding that — so later specs still find the saved script intact.
test('Delete N Lines removes the whole selection', async () => {
  await selectLines(page, ['To be or not to be', 'That is the question']);

  await page.getByRole('button', { name: 'Delete 2 Lines' }).click();

  await expect(
    page.locator('.script-line-row').filter({ hasText: 'To be or not to be' })
  ).toHaveCount(0, { timeout: 5_000 });
  await expect(
    page.locator('.script-line-row').filter({ hasText: 'That is the question' })
  ).toHaveCount(0);
  await expect(page.getByRole('toolbar', { name: 'Selected lines' })).toBeHidden();

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
  await expect(page.locator('.line-edit-trigger')).toHaveCount(0);
  await docShot(page, 'config_show/script_view_mode');
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

// ── Script Cues — add/edit/delete in place ────────────────────────────────
// Cues are placed with a card that opens under the line, not a modal.

const addCard = () => page.locator('section[aria-label="Add a cue to this line"]');
const addGroupCard = () => page.locator('section[aria-label="Add a group of cues to this line"]');
const realCues = () => page.locator('.cue-button:not(.add-cue-btn)');
const findBox = () => page.getByRole('combobox', { name: 'Find a cue' });

test('navigates to Script Cues with saved script content', async () => {
  await page.goto(`${UI_BASE}/show-config/cues`);
  await waitForAppReady(page);
  // Script Cues is the first and default tab.
  await expect(page.locator('.nav-link.active:has-text("Script Cues")')).toBeVisible();
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 10_000 });
  await expect(
    page.locator('.viewable-line').filter({ hasText: 'To be or not to be' }).first()
  ).toBeVisible({ timeout: 10_000 });
  // The script has content but no cues yet.
  await docShot(page, 'config_show/cue_configuration_empty');
});

test('"+ Cue" opens a card with the first free number suggested', async () => {
  await page.locator('.add-cue-btn').first().click();
  await expect(addCard()).toBeVisible();
  // The only cue type is the only writable one, so it is already chosen.
  await expect(addCard().getByLabel('Cue number')).toHaveValue('1');
  await expect(addCard().getByRole('button', { name: 'Add LX 1' })).toBeVisible();
  // While the card is open that line's button says so and cannot be used again.
  await expect(page.locator('.add-cue-btn').first()).toHaveText('Adding…');
  await expect(page.locator('.add-cue-btn').first()).toBeDisabled();
  await docShot(page, 'config_show/cue_add_card');
});

test('adds a cue with the keyboard alone and focus returns to "+ Cue"', async () => {
  await addCard().getByLabel('Cue number').fill('001');
  await addCard().getByLabel('Cue number').press('Enter');
  await expect(addCard()).not.toBeVisible({ timeout: 5_000 });
  await expect(realCues().first()).toHaveText('LX 001', { timeout: 5_000 });
  await expect(page.locator('.add-cue-btn').first()).toBeFocused();
});

test('edits the cue number in a card', async () => {
  await realCues().first().click();
  const card = page.locator('section[aria-label="Edit LX 001"]');
  await expect(card).toBeVisible();
  await card.getByLabel('Cue number').fill('002');
  await card.getByRole('button', { name: 'Save Cue' }).click();
  await expect(card).not.toBeVisible({ timeout: 5_000 });
  await expect(realCues().first()).toHaveText('LX 002', { timeout: 5_000 });
});

test('suggests the next number, and "Add and Stay Open" adds then offers the next', async () => {
  await page.locator('.add-cue-btn').first().click();
  await expect(addCard().getByLabel('Cue number')).toHaveValue('3');
  await addCard().getByRole('button', { name: 'Add and Stay Open' }).click();
  await expect(realCues()).toHaveCount(2, { timeout: 5_000 });
  // The card stays open with the next suggestion ready.
  await expect(addCard()).toBeVisible();
  await expect(addCard().getByLabel('Cue number')).toHaveValue('4');
  await addCard().getByRole('button', { name: 'Cancel' }).click();
  await expect(addCard()).not.toBeVisible();
});

test('warns about a duplicate number but still allows saving', async () => {
  await page.locator('.add-cue-btn').first().click();
  await addCard().getByLabel('Cue number').fill('002');
  await expect(addCard()).toContainText('LX 002 is already used on page 1. You can still save.');
  await expect(addCard().getByRole('button', { name: 'Add LX 002' })).toBeEnabled();
  await addCard().press('Escape');
  await expect(addCard()).not.toBeVisible();
});

test('edits a cue number using Enter in the card', async () => {
  await realCues().last().click();
  const card = page.locator('section[aria-label^="Edit LX"]');
  await card.getByLabel('Cue number').fill('004');
  await card.getByLabel('Cue number').press('Enter');
  await expect(card).not.toBeVisible({ timeout: 5_000 });
  await expect(realCues()).toHaveCount(2, { timeout: 5_000 });
  await expect(realCues().last()).toHaveText('LX 004');
  await docShot(page, 'config_show/cue_configuration_with_cues');
});

test('Find offers close matches when there is no exact one', async () => {
  await findBox().fill('LX 005');
  await findBox().press('Enter');
  await expect(page.getByText('No LX 005 yet. Did you mean:')).toBeVisible({ timeout: 5_000 });
  await docShot(page, 'config_show/cue_find');
  await findBox().press('Escape');
  await expect(page.getByText('No LX 005 yet. Did you mean:')).not.toBeVisible();
});

test('Find lists matches as you type, and Enter jumps to the cue and says where it went', async () => {
  await findBox().fill('LX 004');
  // After a short pause the match is listed; nothing moves until you choose it.
  await expect(page.getByRole('option', { name: /LX 004/ })).toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.v-toast__text').filter({ hasText: /Jumped to/ })).not.toBeVisible();
  await findBox().press('Enter');
  await expect(page.locator('.v-toast__text').filter({ hasText: /Jumped to LX 004/ })).toBeVisible({
    timeout: 5_000,
  });
});

test('Find says so when no cue matches', async () => {
  await findBox().fill('LX 999');
  await findBox().press('Enter');
  await expect(page.getByText('No cues found matching “LX 999”.')).toBeVisible({ timeout: 5_000 });
  await findBox().press('Escape');
  await expect(page.getByText('No cues found matching “LX 999”.')).not.toBeVisible();
});

test('Find asks which cue type a bare number is', async () => {
  await findBox().fill('2');
  await findBox().press('Enter');
  await expect(page.getByText('Which cue type is 2?')).toBeVisible({ timeout: 5_000 });
  await findBox().press('Escape');
});

test('deletes a cue after confirming', async () => {
  await realCues().last().click();
  await page
    .locator('section[aria-label^="Edit LX"]')
    .getByRole('button', { name: 'Delete Cue' })
    .click();
  await confirmDialog(page);
  await expect(realCues()).toHaveCount(1, { timeout: 10_000 });
  // Deleting your own cue is not "someone else" changing it, and focus goes back to "+ Cue".
  await expect(page.getByText('changed or removed by someone else')).not.toBeVisible();
  await expect(page.locator('.add-cue-btn').first()).toBeFocused();
});

test('deletes the last cue', async () => {
  await realCues().first().click();
  await page
    .locator('section[aria-label^="Edit LX"]')
    .getByRole('button', { name: 'Delete Cue' })
    .click();
  await confirmDialog(page);
  await expect(realCues()).not.toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('changed or removed by someone else')).not.toBeVisible();
});

// ── Cue Groups ────────────────────────────────────────────────────────────

test('the add card can switch to a group of cues', async () => {
  await page.locator('.add-cue-btn').first().click();
  await expect(addCard()).toBeVisible();
  await addCard().getByRole('button', { name: 'Group of Cues' }).click();
  await expect(addGroupCard()).toBeVisible();
  // Switching keeps the chosen type.
  await expect(addGroupCard().getByRole('radio', { name: /LX/ })).toHaveAttribute(
    'aria-checked',
    'true'
  );
});

test('adds the range 1 to 5 and shows five cues', async () => {
  await addGroupCard().getByLabel('From number').fill('1');
  await addGroupCard().getByLabel('To number').fill('5');
  await addGroupCard().getByRole('button', { name: 'Add Range' }).click();
  await expect(addGroupCard().locator('.member-input')).toHaveCount(5, { timeout: 3_000 });
  await expect(addGroupCard().getByRole('button', { name: 'Add Group of 5' })).toBeVisible();
  await docShot(page, 'config_show/cue_group_card');
});

test('saves the group and shows a dashed group button with the range label', async () => {
  await addGroupCard().getByRole('button', { name: 'Add Group of 5' }).click();
  await expect(addGroupCard()).not.toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.cue-group-btn').first()).toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.cue-group-btn').first()).toContainText('LX 1 - LX 5');
});

test('opens the group in a card with its 5 cues listed', async () => {
  await page.locator('.cue-group-btn').first().click();
  const card = page.locator('section[aria-label^="Edit group"]');
  await expect(card).toBeVisible();
  await expect(card.locator('.member-input')).toHaveCount(5);
});

test('reorders a group with the arrow buttons', async () => {
  const card = page.locator('section[aria-label^="Edit group"]');
  await card.getByRole('button', { name: 'Move cue 1 later' }).click();
  await expect(card.locator('.member-input').first()).toHaveValue('2');
  await card.getByRole('button', { name: 'Move cue 1 earlier' }).click();
  await expect(card.locator('.member-input').first()).toHaveValue('1');
});

test('adds a group name and the group button label updates on save', async () => {
  const card = page.locator('section[aria-label^="Edit group"]');
  await card.getByLabel('Group name (optional)').fill('Music Intro');
  await card.getByRole('button', { name: 'Save Group' }).click();
  await expect(card).not.toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.cue-group-btn').first()).toContainText('LX - Music Intro');
});

test('asks before discarding a changed group card', async () => {
  await page.locator('.cue-group-btn').first().click();
  const card = page.locator('section[aria-label^="Edit group"]');
  await card.getByRole('button', { name: 'Move cue 1 later' }).click();
  await card.getByRole('button', { name: 'Cancel' }).click();
  await waitForModal(page, 'Discard Changes');
  // Keep editing: the card stays.
  await page.locator('.modal.show .modal-footer button.btn-secondary').click();
  await waitForModalClosed(page);
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: 'Cancel' }).click();
  await confirmDialog(page);
  await expect(card).not.toBeVisible({ timeout: 5_000 });
});

test('deletes the cue group after confirming', async () => {
  await page.locator('.cue-group-btn').first().click();
  await page
    .locator('section[aria-label^="Edit group"]')
    .getByRole('button', { name: 'Delete Group' })
    .click();
  await confirmDialog(page);
  await expect(page.locator('.cue-group-btn')).not.toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('changed or removed by someone else')).not.toBeVisible();
});

test('a group of 100 cues scrolls inside the card instead of stretching it', async () => {
  await page.locator('.add-cue-btn').first().click();
  await addCard().getByRole('button', { name: 'Group of Cues' }).click();
  await addGroupCard().getByLabel('From number').fill('1');
  await addGroupCard().getByLabel('To number').fill('100');
  await addGroupCard().getByRole('button', { name: 'Add Range' }).click();
  await expect(addGroupCard().locator('.member-tile')).toHaveCount(100);

  const list = addGroupCard().getByRole('group', { name: 'Cues in this group' });
  const sizes = await list.evaluate((el) => ({
    scroll: el.scrollHeight,
    client: el.clientHeight,
    window: window.innerHeight,
  }));
  // Long content scrolls in a box that is a fraction of the window, not the full list height.
  expect(sizes.scroll).toBeGreaterThan(sizes.client);
  expect(sizes.client).toBeLessThanOrEqual(sizes.window * 0.5);

  // The last cue is reachable by scrolling, and the group can still be added.
  await addGroupCard().getByLabel('Cue 100 of 100').scrollIntoViewIfNeeded();
  await expect(addGroupCard().getByLabel('Cue 100 of 100')).toBeInViewport();
  await expect(addGroupCard().getByRole('button', { name: 'Add Group of 100' })).toBeEnabled();

  // Leave without adding: the changed group card asks first.
  await addGroupCard().getByRole('button', { name: 'Cancel' }).click();
  await confirmDialog(page);
  await expect(addGroupCard()).not.toBeVisible({ timeout: 5_000 });
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

  await lineEditor.locator('button:has-text("Add Speaker")').click();

  // One remove button per part
  await expect(lineEditor.locator('button.btn-outline-danger')).toHaveCount(2, { timeout: 3_000 });
  await docShot(page, 'config_show/script_multi_part_dialogue_full_mode');
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

  // This line has a previous line to inherit its act/scene from, so Design E's
  // card doesn't show the Act/Scene selects at all here (see the first-line case
  // in "saves a dialogue line to the script" above, which does).
  await lineEditor
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await lineEditor.locator('input[type="text"]').last().fill('Surviving part text');

  // Plain Done just closes the line now — no more auto-chained blank editor to
  // clean up (only Enter chains, and this flow never pressed it).
  await lineEditor.locator('button:has-text("Done")').click();
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
