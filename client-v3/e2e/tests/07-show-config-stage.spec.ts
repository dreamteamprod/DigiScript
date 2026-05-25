/**
 * Show Config — Stage tab: prop types, props, scenery types, scenery, crew types, crew.
 * Also covers the Stage Manager scene-navigation and allocation panel.
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
  await page.goto(`${UI_BASE}/show-config/stage`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Props ──────────────────────────────────────────────────────────────────

test('Props tab is visible', async () => {
  await page.click('.nav-link:has-text("Props"), button[role="tab"]:has-text("Props")');
  await expect(
    page.locator('button:has-text("New Prop Type"), button:has-text("New Type")')
  ).toBeVisible();
});

test('creates a prop type', async () => {
  await page.click('button:has-text("New Prop Type")');
  await waitForModal(page, 'Add New Prop Type');
  await page.fill('#new-ptype-name', 'Furniture');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Furniture")')).toBeVisible();
});

test('creates a prop', async () => {
  await page.click('button:has-text("New Props Item")');
  await waitForModal(page, 'Add New Prop');
  // Select the prop type we just created
  await page.selectOption('.modal.show #new-prop-type-sel', { label: 'Furniture' });
  await page.fill('.modal.show #new-prop-name', 'Chair');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Chair")')).toBeVisible();
});

// ── Scenery ───────────────────────────────────────────────────────────────

test('switches to Scenery tab', async () => {
  await page.click('.nav-link:has-text("Scenery"), button[role="tab"]:has-text("Scenery")');
  await expect(
    page.locator('button:has-text("New Scenery Type"), button:has-text("New Type")')
  ).toBeVisible();
});

test('creates a scenery type', async () => {
  await page.click('button:has-text("New Scenery Type")');
  await waitForModal(page, 'Add New Scenery Type');
  await page.fill('#new-stype-name', 'Backdrop');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Backdrop")')).toBeVisible();
});

test('creates a scenery item', async () => {
  await page.click('button:has-text("New Scenery Item")');
  await waitForModal(page, 'Add New Scenery');
  // Select the scenery type we just created
  await page.selectOption('#new-scenery-type-sel', { label: 'Backdrop' });
  await page.fill('#new-scenery-name', 'Castle Wall');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Castle Wall")')).toBeVisible();
});

test('deletes the scenery item', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Castle Wall")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Castle Wall")')).not.toBeVisible({ timeout: 5_000 });
});

test('deletes the scenery type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Backdrop")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Backdrop")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Crew ──────────────────────────────────────────────────────────────────

test('switches to Crew tab', async () => {
  await page.click('.nav-link:has-text("Crew"), button[role="tab"]:has-text("Crew")');
  await expect(page.locator('button:has-text("New Crew Member")')).toBeVisible();
});

test('creates a crew member', async () => {
  await page.click('button:has-text("New Crew Member")');
  await waitForModal(page, 'Add Crew Member');
  await page.fill('#new-first-name', 'John');
  await page.fill('#new-last-name', 'Smith');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("John")')).toBeVisible();
});

test('deletes the crew member', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("John")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("John")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Stage Manager ─────────────────────────────────────────────────────────

test('switches to Stage Manager tab and shows scene navigation', async () => {
  await page.click(
    '.nav-link:has-text("Stage Manager"), button[role="tab"]:has-text("Stage Manager")'
  );
  // Shows Prev/Next scene buttons
  await expect(page.locator('button:has-text("Next")').first()).toBeVisible();
});

test('adds a prop allocation to the current scene', async () => {
  await page.locator('button.btn-success:has-text("Add")').click();
  await page.click('.dropdown-item:has-text("Prop")');
  await waitForModal(page, 'Add Prop to Scene');
  await page.selectOption('#add-prop-select', { label: 'Chair' });
  await confirmModal(page);
  await waitForModalClosed(page);
  // Scope to active tab — Props tab panel is also mounted in DOM and contains a Chair cell
  await expect(page.locator('.tab-pane.active td:has-text("Chair")')).toBeVisible({
    timeout: 5_000,
  });
});

test('deletes the prop allocation', async () => {
  const propRow = page.locator('.tab-pane.active tr', {
    has: page.locator('td:has-text("Chair")'),
  });
  await propRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('.tab-pane.active td:has-text("Chair")')).not.toBeVisible({
    timeout: 5_000,
  });
});

// ── Prop cleanup ──────────────────────────────────────────────────────────

test('deletes the prop', async () => {
  await page.click('.nav-link:has-text("Props"), button[role="tab"]:has-text("Props")');
  const row = page.locator('tr', { has: page.locator('td:has-text("Chair")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Chair")')).not.toBeVisible({ timeout: 5_000 });
});

test('deletes the prop type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Furniture")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Furniture")')).not.toBeVisible({ timeout: 5_000 });
});
