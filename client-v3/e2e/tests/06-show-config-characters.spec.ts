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
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';
import { snapshotExists, snapshotState, restoreStateAndRestartServer } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({}, testInfo) => {
  if (testInfo.retry > 0 && snapshotExists()) {
    await restoreStateAndRestartServer();
  }
});

test.afterEach(async ({}, testInfo) => {
  if (testInfo.status === 'passed') {
    snapshotState();
  }
});

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
