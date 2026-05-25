/**
 * Show Config — Mics tab: microphone CRUD, allocations view, timeline view.
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

test.beforeAll(async () => {
  if (test.info().retry > 0 && snapshotExists()) {
    await restoreStateAndRestartServer();
  }
});

test.afterEach(async () => {
  if (test.info().status === 'passed') {
    snapshotState();
  }
});

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/mics`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Mics ──────────────────────────────────────────────────────────────────

test('Mics tab shows New Microphone button', async () => {
  await expect(page.locator('button:has-text("New Microphone")')).toBeVisible();
});

test('creates a microphone', async () => {
  await page.click('button:has-text("New Microphone")');
  await waitForModal(page, /Microphone/);
  await page.fill('.modal.show input[type="text"]', 'Mic 1');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 1")')).toBeVisible();
});

test('creates a second microphone', async () => {
  await page.click('button:has-text("New Microphone")');
  await waitForModal(page, /Microphone/);
  await page.fill('.modal.show input[type="text"]', 'Mic 2');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 2")')).toBeVisible();
});

test('edits a microphone', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Mic 2")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, /Edit.*Mic|Microphone/);
  const input = page.locator('.modal.show input[type="text"]').first();
  await input.fill('Mic 2 (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 2 (Edited)")')).toBeVisible();
});

test('deletes a microphone', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Mic 2 (Edited)")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Mic 2 (Edited)")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Allocations ───────────────────────────────────────────────────────────

test('switches to Allocations sub-tab', async () => {
  await page.click('.nav-link:has-text("Allocations"), button[role="tab"]:has-text("Allocations")');
  // Allocations table container is always visible on this sub-tab
  await expect(page.locator('#allocations-table')).toBeVisible({ timeout: 10_000 });
});

test('switches to edit mode and back', async () => {
  // Component may initialise in edit mode — ensure we start in view mode.
  // Use :visible to avoid strict-mode violation from Cancel buttons inside hidden BVN modals.
  if ((await page.locator('button:has-text("View"):visible').count()) > 0) {
    await page.locator('button:has-text("View"):visible').click();
  }
  // Scope to active panel — the Mics tab (not active) also has row-level Edit buttons in the DOM
  const editBtn = page.locator('.tab-pane.active button:has-text("Edit")');
  await expect(editBtn).toBeVisible({ timeout: 5_000 });
  await editBtn.click();
  await expect(page.locator('.tab-pane.active button:has-text("Save")')).toBeVisible();
  await page
    .locator('.tab-pane.active')
    .locator('button:has-text("View"), button:has-text("Cancel")')
    .click();
});

test('saves a mic allocation', async () => {
  // Re-navigate so MicAllocations re-mounts with Mic 1 already in the store.
  // internalState is initialised in onMounted; the first navigation (beforeAll) ran before any
  // mics existed, so the component would have set up an empty internalState and toggleAllocation
  // would silently no-op. A fresh navigation after mic creation fixes this.
  await page.goto(`${UI_BASE}/show-config/mics`);
  await waitForAppReady(page);
  await page.click('.nav-link:has-text("Allocations"), button[role="tab"]:has-text("Allocations")');
  await expect(page.locator('#allocations-table')).toBeVisible({ timeout: 10_000 });

  // MicAllocations starts with editMode = true; #mic-input is immediately visible
  await expect(page.locator('#mic-input')).toBeVisible({ timeout: 5_000 });
  await page.selectOption('#mic-input', { label: 'Mic 1' });

  await page
    .locator('#allocations-table tbody tr')
    .first()
    .locator('td')
    .nth(1)
    .locator('button')
    .click();
  await page.locator('.tab-pane.active button:has-text("Save")').click();

  await page
    .locator('.tab-pane.active')
    .locator('button:has-text("View"), button:has-text("Cancel")')
    .click();
  await expect(page.locator('.tab-pane.active button:has-text("Edit")')).toBeVisible({
    timeout: 5_000,
  });

  await expect(page.locator('#allocations-table .allocation-cell').first()).toBeVisible({
    timeout: 5_000,
  });
});

// ── Timeline ─────────────────────────────────────────────────────────────

test('switches to Timeline sub-tab', async () => {
  await page.click('.nav-link:has-text("Timeline"), button[role="tab"]:has-text("Timeline")');
  await expect(page.locator('button:has-text("By Microphone")')).toBeVisible({ timeout: 10_000 });
});

// ── Density ──────────────────────────────────────────────────────────────

test('switches to Density sub-tab', async () => {
  await page.click('.nav-link:has-text("Density"), button[role="tab"]:has-text("Density")');
  await expect(page.locator('h5:has-text("Scene Microphone Density")')).toBeVisible({
    timeout: 10_000,
  });
});

// ── Availability ──────────────────────────────────────────────────────────

test('switches to Availability sub-tab', async () => {
  await page.click(
    '.nav-link:has-text("Availability"), button[role="tab"]:has-text("Availability")'
  );
  await expect(page.locator('h5:has-text("Microphone Resource Availability")')).toBeVisible({
    timeout: 10_000,
  });
});
