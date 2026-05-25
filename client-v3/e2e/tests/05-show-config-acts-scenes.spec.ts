/**
 * Show Config — Acts & Scenes tab: full CRUD for acts and scenes.
 * Creates Act 1 + Scene 1 that later specs (characters, script) depend on.
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

test.beforeAll(async (_fixtures, testInfo) => {
  if (testInfo.retry > 0 && snapshotExists()) {
    await restoreStateAndRestartServer();
  }
});

test.afterEach(async (_fixtures, testInfo) => {
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
  await page.goto(`${UI_BASE}/show-config/acts`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Acts ───────────────────────────────────────────────────────────────────

test('Acts tab is visible', async () => {
  await expect(page.locator('button:has-text("New Act")')).toBeVisible();
});

test('creates Act 1', async () => {
  await page.click('button:has-text("New Act")');
  await waitForModal(page, 'New Act');
  await page.fill('.modal.show input[type="text"]', 'Act 1');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Act 1")').first()).toBeVisible();
});

test('creates Act 2', async () => {
  await page.click('button:has-text("New Act")');
  await waitForModal(page, 'New Act');
  await page.fill('.modal.show input[type="text"]', 'Act 2');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Act 2")').first()).toBeVisible();
});

test('edits Act 2 name', async () => {
  const actRow = page.locator('tr', { has: page.locator('td:has-text("Act 2")') });
  await actRow.locator('button:has-text("Edit")').click();
  await waitForModal(page, 'Edit Act');
  await page.fill('.modal.show input[type="text"]', 'Act 2 (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Act 2 (Edited)")').first()).toBeVisible();
});

test('deletes Act 2', async () => {
  const actRow = page.locator('tr', { has: page.locator('td:has-text("Act 2 (Edited)")') });
  await actRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Act 2 (Edited)")').first()).not.toBeVisible({
    timeout: 5_000,
  });
});

// ── Scenes ────────────────────────────────────────────────────────────────

test('switches to the Scenes sub-tab', async () => {
  await page.click('.nav-link:has-text("Scenes"), button[role="tab"]:has-text("Scenes")');
  await expect(page.locator('button:has-text("New Scene")')).toBeVisible();
});

test('creates Scene 1 in Act 1', async () => {
  await page.click('button:has-text("New Scene")');
  await waitForModal(page, 'New Scene');
  await page.selectOption('#new-act-input', { index: 1 });
  await page.fill('.modal.show input[type="text"]', 'Scene 1');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Scene 1")').first()).toBeVisible();
});

test('creates Scene 2 in Act 1', async () => {
  await page.click('button:has-text("New Scene")');
  await waitForModal(page, 'New Scene');
  await page.selectOption('#new-act-input', { index: 1 });
  await page.fill('.modal.show input[type="text"]', 'Scene 2');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Scene 2")').first()).toBeVisible();
});

test('edits Scene 2 name', async () => {
  const sceneRow = page.locator('tr', { has: page.locator('td:has-text("Scene 2")') });
  await sceneRow.locator('button:has-text("Edit")').click();
  await waitForModal(page, 'Edit Scene');
  await page.fill('.modal.show input[type="text"]', 'Scene 2 (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Scene 2 (Edited)")').first()).toBeVisible();
});

test('deletes Scene 2', async () => {
  const sceneRow = page.locator('tr', { has: page.locator('td:has-text("Scene 2 (Edited)")') });
  await sceneRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Scene 2 (Edited)")').first()).not.toBeVisible({
    timeout: 5_000,
  });
});
