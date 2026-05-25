/**
 * Show Config — Sessions tab: session tags CRUD.
 * Note: actual session start/stop is tested in 13-live-show.spec.ts.
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
  await page.goto(`${UI_BASE}/show-config/sessions`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Sessions list ─────────────────────────────────────────────────────────

test('Sessions tab renders', async () => {
  await expect(page.locator('table').first()).toBeVisible({ timeout: 10_000 });
});

// ── Tags ─────────────────────────────────────────────────────────────────

test('switches to Tags sub-tab', async () => {
  await page.click('.nav-link:has-text("Tags"), button[role="tab"]:has-text("Tags")');
  await expect(page.locator('button:has-text("New Tag")')).toBeVisible();
});

test('creates a session tag', async () => {
  await page.click('button:has-text("New Tag")');
  await waitForModal(page, 'Add Session Tag');
  await page.fill('#new-tag-name', 'Tech Run');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Tech Run")')).toBeVisible();
});

test('edits a session tag', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Tech Run")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, 'Edit Session Tag');
  await page.fill('#edit-tag-name', 'Tech Run (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Tech Run (Edited)")')).toBeVisible();
});

test('deletes a session tag', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Tech Run (Edited)")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Tech Run (Edited)")')).not.toBeVisible({
    timeout: 5_000,
  });
});
