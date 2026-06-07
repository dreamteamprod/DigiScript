/**
 * Show Config — Characters tab: character CRUD, character groups, cast CRUD.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  confirmModal,
  cancelModal,
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
  await page.goto(`${UI_BASE}/show-config/characters`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Characters ────────────────────────────────────────────────────────────

test('Characters tab shows New Character button', async () => {
  await expect(page.getByRole('button', { name: 'New Character', exact: true })).toBeVisible();
});

test('creates a character', async () => {
  await page.getByRole('button', { name: 'New Character', exact: true }).click();
  await waitForModal(page, 'New Character');
  await page.fill('.modal.show #character-name-input, .modal.show input[type="text"]', 'Hamlet');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Hamlet")').first()).toBeVisible();
});

test('creates a second character with description', async () => {
  await page.getByRole('button', { name: 'New Character', exact: true }).click();
  await waitForModal(page, 'New Character');
  const inputs = page.locator('.modal.show input[type="text"]');
  await inputs.first().fill('Ophelia');
  // Description may be a second text input or textarea
  const descInput = page.locator('.modal.show textarea, .modal.show input[type="text"]').nth(1);
  if ((await descInput.count()) > 0) {
    await descInput.fill("Hamlet's love interest");
  }
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Ophelia")').first()).toBeVisible();
});

test('edits a character', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Ophelia")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, 'Edit Character');
  const nameInput = page.locator('.modal.show input[type="text"]').first();
  await nameInput.fill('Ophelia (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Ophelia (Edited)")').first()).toBeVisible();
});

test('deletes a character', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Ophelia (Edited)")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Ophelia (Edited)")').first()).not.toBeVisible({
    timeout: 5_000,
  });
});

// ── Character Merge ────────────────────────────────────────────────────────

test('Merge button is visible for each character row', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Hamlet")') });
  await expect(row.locator('button:has-text("Merge")')).toBeVisible();
});

test('creates a character for merge testing', async () => {
  await page.getByRole('button', { name: 'New Character', exact: true }).click();
  await waitForModal(page, 'New Character');
  await page.fill('.modal.show input[type="text"]', 'Horatio');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Horatio")').first()).toBeVisible();
});

test('merge modal opens with correct title', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Horatio")') });
  await row.locator('button:has-text("Merge")').click();
  await waitForModal(page, /Merge Horatio/);
  await cancelModal(page);
  await waitForModalClosed(page);
});

test('merge OK button is disabled with no destination selected', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Horatio")') });
  await row.locator('button:has-text("Merge")').click();
  await waitForModal(page, /Merge Horatio/);
  const okBtn = page.locator('.modal.show .modal-footer button.btn-primary');
  await expect(okBtn).toBeDisabled();
  await cancelModal(page);
  await waitForModalClosed(page);
});

test('merges a character into another', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Horatio")') });
  await row.locator('button:has-text("Merge")').click();
  await waitForModal(page, /Merge Horatio/);
  // Open the dropdown by clicking the multiselect container, then select the option.
  await page.locator('.modal.show .multiselect').click();
  await page.locator('.modal.show .multiselect__option', { hasText: 'Hamlet' }).click();
  await confirmModal(page);
  await waitForModalClosed(page);
  // Scope to the character table to avoid matching cells in the Line Counts tab (always in DOM).
  await expect(page.locator('#character-table td:has-text("Horatio")')).not.toBeVisible({
    timeout: 5_000,
  });
  await expect(page.locator('#character-table td:has-text("Hamlet")')).toBeVisible();
});

// ── Character Groups ──────────────────────────────────────────────────────

test('switches to Character Groups sub-tab', async () => {
  await page.click('.nav-link:has-text("Character Groups"), button[role="tab"]:has-text("Groups")');
  await expect(
    page.locator('button:has-text("New Character Group"), button:has-text("New Group")')
  ).toBeVisible();
});

test('creates a character group', async () => {
  await page.click('button:has-text("New Character Group"), button:has-text("New Group")');
  await waitForModal(page, /Character Group/);
  await page.fill('.modal.show input[type="text"]', 'Royalty');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Royalty")')).toBeVisible();
});

test('deletes the character group', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Royalty")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Royalty")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Cast ─────────────────────────────────────────────────────────────────

test('navigates to Cast page', async () => {
  await page.goto(`${UI_BASE}/show-config/cast`);
  await waitForAppReady(page);
  await expect(page.locator('button:has-text("New Cast Member")')).toBeVisible();
});

test('creates a cast member', async () => {
  await page.click('button:has-text("New Cast Member")');
  await waitForModal(page, /Cast Member/);
  const textInputs = page.locator('.modal.show input[type="text"]');
  await textInputs.nth(0).fill('Jane');
  await textInputs.nth(1).fill('Doe');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Jane")').first()).toBeVisible();
});

test('edits the cast member', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Jane")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, /Cast Member/);
  const textInputs = page.locator('.modal.show input[type="text"]');
  await textInputs.nth(0).fill('Janet');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Janet")').first()).toBeVisible();
});

test('deletes the cast member', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Janet")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Janet")').first()).not.toBeVisible({ timeout: 5_000 });
});

// ── Character Timeline ─────────────────────────────────────────────────────

test('switches to Timeline sub-tab', async () => {
  await page.goto(`${UI_BASE}/show-config/characters`);
  await waitForAppReady(page);
  await page.click('.nav-link:has-text("Timeline"), button[role="tab"]:has-text("Timeline")');
  // No script lines yet — expect the empty-state message (lazy tab, needs extra timeout)
  await expect(page.locator('text=No character line data to display')).toBeVisible({
    timeout: 10_000,
  });
});
