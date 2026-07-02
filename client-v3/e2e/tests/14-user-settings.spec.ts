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
  waitForModal,
  confirmModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

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
  await expect(page.locator('button[role="tab"]:has-text("About")')).toBeVisible();
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

test('creates a stage direction style for override testing', async () => {
  // spec-10 cleaned up after itself, so we need a fresh style here
  await page.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(page);
  await page.click('.nav-link:has-text("Stage Direction Styles")');
  await expect(page.locator('button:has-text("New Style")')).toBeVisible({ timeout: 5_000 });
  await page.click('button:has-text("New Style")');
  await waitForModal(page, 'Add New Style');
  await page.fill('.modal.show input[type="text"]', 'Action');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Action")')).toBeVisible();
  await page.goto(`${UI_BASE}/me`);
  await waitForAppReady(page);
});

test('switches to Stage Direction Styles tab', async () => {
  await page.click('.nav-link:has-text("Stage Direction")');
  // Use the component-specific table ID to avoid matching hidden tab-panel elements
  await expect(page.locator('#stage-directions-table')).toBeVisible({ timeout: 5_000 });
});

test('"New Override" button is enabled when stage direction styles exist', async () => {
  // Scope to thead to avoid matching the "New Override" button in the Cue Colour Preferences tab
  // (BVN BTabs without lazy mounts all tab panels, so inactive tab content stays in the DOM)
  await expect(
    page.locator('#stage-directions-table thead button:has-text("New Override")')
  ).toBeEnabled();
});

test('clicking "New Override" opens the style selection modal', async () => {
  await page.click('#stage-directions-table thead button:has-text("New Override")');
  await waitForModal(page, 'Add New Override');
  // OK is disabled until a style is selected
  await expect(page.locator('.modal.show .modal-footer button.btn-primary')).toBeDisabled();
});

test('selecting a style and clicking OK opens the configuration modal', async () => {
  await page.locator('.modal.show select').selectOption({ index: 1 });
  await confirmModal(page);
  // The config modal is identified by an input unique to it (both modals share the same title)
  await expect(page.locator('#new-text-colour-input')).toBeVisible({ timeout: 5_000 });
});

test('submitting the configuration creates the override', async () => {
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('#stage-directions-table td:has-text("Action")')).toBeVisible({
    timeout: 5_000,
  });
});

test('deletes the stage direction override', async () => {
  const row = page.locator('#stage-directions-table tr', {
    has: page.locator('td:has-text("Action")'),
  });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('#stage-directions-table td:has-text("Action")')).not.toBeVisible({
    timeout: 5_000,
  });
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
