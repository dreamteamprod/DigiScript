/**
 * Show Config — Show details tab: view show info, edit show name/dates/first act.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  confirmModal,
  waitForModalClosed,
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
  await page.goto(`${UI_BASE}/show-config`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

test('show config landing page displays show details table', async () => {
  await expect(page.locator('table')).toBeVisible();
  await expect(page.locator('td:has-text("E2E Test Show")')).toBeVisible();
  const detailValue = (label: string) =>
    page.locator('tr', { hasText: label }).locator('td').last();
  await docShot(page, 'config_show/config_overview', {
    fixText: [
      { locator: detailValue('Created At'), text: '2025-01-06T09:30:12.104744' },
      { locator: detailValue('Edited At'), text: '2025-01-06T09:30:12.104744' },
    ],
  });
});

test('Edit Show button is visible for admin', async () => {
  await expect(page.locator('button:has-text("Edit Show")')).toBeVisible();
});

test('opens the Edit Show modal with current values', async () => {
  await page.click('button:has-text("Edit Show")');
  await waitForModal(page, 'Edit Show');
  await expect(page.locator('#name-input')).toHaveValue('E2E Test Show');
});

test('can update the show name', async () => {
  await page.fill('#name-input', 'E2E Test Show (Updated)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("E2E Test Show (Updated)")')).toBeVisible();
});

test('restores original show name', async () => {
  await page.click('button:has-text("Edit Show")');
  await waitForModal(page, 'Edit Show');
  await page.fill('#name-input', 'E2E Test Show');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("E2E Test Show")')).toBeVisible();
});
