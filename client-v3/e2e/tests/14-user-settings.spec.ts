/**
 * User Settings (/me): personal settings, stage direction style overrides,
 * password change, API token management.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  ADMIN_PASSWORD,
  loginAsAdmin,
  waitForAppReady,
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

const NEW_PASSWORD = 'newpassword123';

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/me`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── About ─────────────────────────────────────────────────────────────────

test('Settings page renders the About tab', async () => {
  await expect(
    page.locator('.nav-link:has-text("About"), button[role="tab"]:has-text("About")')
  ).toBeVisible();
});

// ── Settings ──────────────────────────────────────────────────────────────

test('switches to Settings tab', async () => {
  await page.click('.nav-link:has-text("Settings"), button[role="tab"]:has-text("Settings")');
  await expect(page.locator('button:has-text("Submit")')).toBeVisible({ timeout: 5_000 });
});

test('Submit button is disabled until a setting is changed', async () => {
  await expect(page.locator('button:has-text("Submit")')).toBeDisabled();
});

test('changing a toggle enables the Submit button', async () => {
  const toggle = page.locator('input[type="checkbox"]').first();
  if ((await toggle.count()) > 0) {
    await toggle.click();
    await expect(page.locator('button:has-text("Submit")')).toBeEnabled();
    // Reset back
    await page.click('button:has-text("Reset")');
  }
});

// ── Stage Direction Styles ────────────────────────────────────────────────

test('switches to Stage Direction Styles tab', async () => {
  await page.click('.nav-link:has-text("Stage Direction")');
  // Use the component-specific table ID to avoid matching hidden tab-panel elements
  await expect(page.locator('#stage-directions-table')).toBeVisible({ timeout: 5_000 });
});

// ── Change Password ───────────────────────────────────────────────────────

test('switches to Change Password tab', async () => {
  await page.click(
    '.nav-link:has-text("Change Password"), button[role="tab"]:has-text("Password")'
  );
  // Use the form input as the visibility anchor (avoids matching the nav tab button)
  await expect(page.locator('#current-password-input')).toBeVisible();
});

test('Change Password button is disabled when fields are empty', async () => {
  await expect(page.locator('button[type="submit"]:has-text("Change Password")')).toBeDisabled();
});

test('changes the admin password', async () => {
  await page.fill('#current-password-input', ADMIN_PASSWORD);
  await page.fill('#new-password-input', NEW_PASSWORD);
  await page.fill('#confirm-password-input', NEW_PASSWORD);
  await page.click('button[type="submit"]:has-text("Change Password")');
  // Form resets on success (current-password-input cleared) — toBeDisabled alone catches loading=true
  await expect(page.locator('#current-password-input')).toHaveValue('', { timeout: 10_000 });
});

test('can log in with the new password', async () => {
  // Logout first
  await page.locator('nav').getByText('admin').click();
  await page.click('button:has-text("Sign Out")');
  await expect(page.locator('a:has-text("Login")')).toBeVisible({ timeout: 5_000 });

  // Login with new password
  await page.goto(`${UI_BASE}/login`);
  await page.fill('#username-input', 'admin');
  await page.fill('#password-input', NEW_PASSWORD);
  await page.click('button:has-text("Login")');
  await page.waitForURL(`${UI_BASE}/`);
  await waitForAppReady(page);
});

test('restores the original admin password', async () => {
  await page.goto(`${UI_BASE}/me`);
  await waitForAppReady(page);
  await page.click(
    '.nav-link:has-text("Change Password"), button[role="tab"]:has-text("Password")'
  );
  await page.fill('#current-password-input', NEW_PASSWORD);
  await page.fill('#new-password-input', ADMIN_PASSWORD);
  await page.fill('#confirm-password-input', ADMIN_PASSWORD);
  await page.click('button[type="submit"]:has-text("Change Password")');
  await expect(page.locator('#current-password-input')).toHaveValue('', { timeout: 10_000 });
});

// ── API Token ─────────────────────────────────────────────────────────────

test('switches to API Token tab', async () => {
  await page.click('.nav-link:has-text("API Token"), button[role="tab"]:has-text("API")');
  await expect(page.locator('h3:has-text("API Token Management")')).toBeVisible({ timeout: 5_000 });
});

test('generates an API token', async () => {
  const generateBtn = page.locator('button:has-text("Generate API Token")');
  await expect(generateBtn).toBeVisible({ timeout: 5_000 });
  await generateBtn.click();
  // Scope to card to avoid matching the hidden modal footer "Revoke Token" button
  await expect(page.locator('.card button:has-text("Revoke Token")')).toBeVisible({
    timeout: 10_000,
  });
});

test('revokes the API token', async () => {
  // Scope to card button (distinct from modal footer "Revoke Token" ok button)
  const revokeBtn = page.locator('.card button:has-text("Revoke Token")');
  await expect(revokeBtn).toBeVisible({ timeout: 5_000 });
  await revokeBtn.click();
  await confirmDialog(page);
  await expect(page.locator('button:has-text("Generate API Token")')).toBeVisible({
    timeout: 10_000,
  });
});
