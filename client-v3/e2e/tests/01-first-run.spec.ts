/**
 * First-run: covers the admin-creation flow that appears when has_admin_user is false.
 * This must be the first spec to run because it establishes the admin account used
 * by all subsequent tests.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import { UI_BASE, ADMIN_PASSWORD, waitForAppReady } from '../helpers.js';
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
});

test.afterAll(async () => {
  await ctx.close();
});

test('shows the first-run admin creation form', async () => {
  await page.goto(`${UI_BASE}/`);
  await waitForAppReady(page);
  await expect(page.locator('h2')).toHaveText('Welcome to DigiScript');
  await expect(page.locator('text=To get started, please create an admin user!')).toBeVisible();
});

test('username field is pre-filled with "admin" and disabled', async () => {
  const usernameInput = page.locator('#username-input');
  await expect(usernameInput).toHaveValue('admin');
  await expect(usernameInput).toBeDisabled();
});

test('Save button is disabled until form is valid', async () => {
  await expect(page.locator('button:has-text("Save")')).toBeDisabled();
});

test('creates the admin user and transitions to the main UI', async () => {
  await page.fill('#password-input', ADMIN_PASSWORD);
  await page.fill('#confirm-password-input', ADMIN_PASSWORD);
  await page.click('button:has-text("Save")');

  // After creation the settings update via WS and the router view replaces the form
  await page.waitForSelector('h2:has-text("Welcome to DigiScript")', {
    state: 'detached',
    timeout: 10_000,
  });
  await waitForAppReady(page);

  // The user is not yet logged in — Login link should appear in the navbar
  await expect(page.locator('a:has-text("Login")')).toBeVisible();
});

test('can log in with the newly created admin credentials', async () => {
  await page.click('a:has-text("Login")');
  await page.waitForURL(`${UI_BASE}/login`);

  await page.fill('#username-input', 'admin');
  await page.fill('#password-input', ADMIN_PASSWORD);
  await page.click('button:has-text("Login")');

  await page.waitForURL(`${UI_BASE}/`);
  await waitForAppReady(page);

  // Logged-in username appears in the navbar dropdown
  await expect(page.locator('nav').getByText('admin')).toBeVisible();
});
