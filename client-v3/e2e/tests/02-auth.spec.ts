/**
 * Authentication: login, wrong credentials error, logout, force-password-change guard.
 * Assumes the admin account was created in 01-first-run.spec.ts.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  ADMIN_USERNAME,
  ADMIN_PASSWORD,
  waitForAppReady,
  loginAsAdmin,
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
});

test.afterAll(async () => {
  await ctx.close();
});

test('login page renders correctly', async () => {
  await page.goto(`${UI_BASE}/login`);
  await waitForAppReady(page);
  await expect(page.locator('h3')).toHaveText('Login to DigiScript');
  await expect(page.locator('#username-input')).toBeVisible();
  await expect(page.locator('#password-input')).toBeVisible();
  await expect(page.locator('button:has-text("Login")')).toBeDisabled();
});

test('Login button is enabled once both fields are filled', async () => {
  await page.fill('#username-input', ADMIN_USERNAME);
  await page.fill('#password-input', ADMIN_PASSWORD);
  await expect(page.locator('button:has-text("Login")')).toBeEnabled();
});

test('shows error message on wrong credentials', async () => {
  await page.fill('#password-input', 'wrongpassword');
  await page.click('button:has-text("Login")');
  await expect(page.locator('b:has-text("Login unsuccessful.")')).toBeVisible();
});

test('successful login redirects to home page', async () => {
  await page.fill('#password-input', ADMIN_PASSWORD);
  await page.click('button:has-text("Login")');
  await page.waitForURL(`${UI_BASE}/`);
  await waitForAppReady(page);
  await expect(page.locator('nav').getByText(ADMIN_USERNAME)).toBeVisible();
});

test('redirects to login when already logged in trying to visit /login', async () => {
  await page.goto(`${UI_BASE}/login`);
  // Router guard redirects authenticated users away from /login
  await page.waitForURL(`${UI_BASE}/`);
});

test('can sign out via the navbar dropdown', async () => {
  // Open the username dropdown
  await page.locator('nav').getByText(ADMIN_USERNAME).click();
  await page.click('button:has-text("Sign Out")');
  // After logout, Login link reappears
  await expect(page.locator('a:has-text("Login")')).toBeVisible({ timeout: 5_000 });
});

test('protected routes redirect to login when not authenticated', async () => {
  await page.goto(`${UI_BASE}/config`);
  await page.waitForURL(`${UI_BASE}/login`);
});

test('can log back in after logout', async () => {
  await loginAsAdmin(page);
  // Allow extra time for user data to populate the nav after WS reconnect
  await expect(page.locator('nav').getByText(ADMIN_USERNAME)).toBeVisible({ timeout: 15_000 });
});
