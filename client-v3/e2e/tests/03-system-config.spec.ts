/**
 * System config (/config): create + load show, user management, settings.
 * This spec creates and loads a show — all subsequent specs depend on that show being loaded.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  ADMIN_USERNAME,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';

test.describe.configure({ mode: 'serial' });

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Shows tab ──────────────────────────────────────────────────────────────

test('navigates to System Config', async () => {
  await page.click('a:has-text("System Config")');
  await page.waitForURL(`${UI_BASE}/config`);
  await expect(page.locator('h1, h2, h3').first()).toBeVisible();
});

test('shows the Shows tab by default', async () => {
  await expect(page.locator('button:has-text("Setup New Show")')).toBeVisible();
});

test('opens the Setup New Show modal', async () => {
  await page.click('button:has-text("Setup New Show")');
  await waitForModal(page, 'Setup New Show');
});

test('modal shows Save and Save and Load buttons', async () => {
  await expect(
    page.locator('.modal.show').getByRole('button', { name: 'Save', exact: true })
  ).toBeVisible();
  await expect(
    page.locator('.modal.show').getByRole('button', { name: 'Save and Load' })
  ).toBeVisible();
});

test('creates and loads a show via Save and Load', async () => {
  await page.fill('#show-name-input', 'E2E Test Show');
  await page.fill('#show-start-input', '2025-01-01');
  await page.fill('#show-end-input', '2025-03-31');
  // Wait for script modes to load then explicitly select to trigger v-model update
  await page
    .waitForSelector('#show-script-mode-input option:not([value=""])', { timeout: 5_000 })
    .catch(() => {});
  await page.selectOption('#show-script-mode-input', { index: 0 });
  await page.click('.modal.show button:has-text("Save and Load")');

  // Modal closes, toast appears
  await waitForModalClosed(page, 10_000);
  await waitForAppReady(page);

  // Show Config nav link appears once a show is loaded
  await expect(page.locator('a:has-text("Show Config")')).toBeVisible({ timeout: 10_000 });
});

// ── Users tab ──────────────────────────────────────────────────────────────

test('switches to the Users tab', async () => {
  await page.click(
    'button[role="tab"]:has-text("Users"), a[role="tab"]:has-text("Users"), .nav-link:has-text("Users")'
  );
  await expect(page.locator('button:has-text("New User")')).toBeVisible();
});

test('opens New User modal', async () => {
  await page.click('button:has-text("New User")');
  await waitForModal(page, 'Add New User');
  await expect(page.locator('.modal.show #username-input')).toBeVisible();
});

test('creates a non-admin user', async () => {
  await page.fill('.modal.show #username-input', 'testuser');
  await page.fill('.modal.show #password-input', 'testpassword');
  await page.fill('.modal.show #confirm-password-input', 'testpassword');
  await page.click('.modal.show button:has-text("Save")');
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("testuser")')).toBeVisible();
});

test('can configure RBAC permissions for testuser', async () => {
  const userRow = page.locator('tr', { has: page.locator('td:has-text("testuser")') });
  await userRow.locator('button:has-text("RBAC")').click();
  await waitForModal(page, 'User RBAC Config');

  const grantBtn = page.locator('.modal.show button:has-text("Grant Role")').first();
  await expect(grantBtn).toBeVisible({ timeout: 5_000 });
  await grantBtn.click();
  await expect(
    page.locator('.modal.show button:has-text("Revoke Role")').first()
  ).toBeVisible({ timeout: 5_000 });

  await page.locator('.modal.show button:has-text("Revoke Role")').first().click();
  await expect(
    page.locator('.modal.show button:has-text("Grant Role")').first()
  ).toBeVisible({ timeout: 5_000 });

  await page.locator('.modal.show .modal-header .btn-close').click();
  await waitForModalClosed(page);
});

test('resets the non-admin user password', async () => {
  // Ensure testuser row is stable before interacting
  await expect(page.locator('td:has-text("testuser")')).toBeVisible({ timeout: 5_000 });
  const userRow = page.locator('tr', { has: page.locator('td:has-text("testuser")') });
  await userRow.locator('button:has-text("Reset Password")').click();
  // Wait for the modal to appear — match visible modal content rather than title class
  await page.waitForSelector('.modal.show', { timeout: 10_000 });
  await expect(page.locator('.modal.show')).toContainText('Reset User Password');
  // Click the Reset Password button inside the modal body
  await page.locator('.modal.show button:has-text("Reset Password")').click();
  // Temporary password shown — Done button appears
  await expect(page.locator('.modal.show button:has-text("Done")')).toBeVisible({ timeout: 5_000 });
  await page.locator('.modal.show button:has-text("Done")').click();
  await waitForModalClosed(page);
});

test('deletes the non-admin user', async () => {
  const userRow = page.locator('tr', { has: page.locator('td:has-text("testuser")') });
  await userRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("testuser")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Settings tab ──────────────────────────────────────────────────────────

test('switches to the Settings tab', async () => {
  await page.click('.nav-link:has-text("Settings")');
  await expect(page.locator('button:has-text("Submit")')).toBeVisible();
});

test('Submit button is disabled until a setting is changed', async () => {
  await expect(page.locator('button:has-text("Submit")')).toBeDisabled();
});

test('changing a setting enables the Submit and Reset buttons', async () => {
  // Toggle the Debug Mode setting (a boolean switch)
  const debugSwitch = page
    .locator('label:has-text("Debug Mode")')
    .locator('..')
    .locator('input[type="checkbox"], .form-check-input')
    .first();
  if ((await debugSwitch.count()) > 0) {
    await debugSwitch.click();
    await expect(page.locator('button:has-text("Submit")')).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Reset', exact: true })).toBeEnabled();
    // Reset it back
    await page.getByRole('button', { name: 'Reset', exact: true }).click();
  }
});

// ── System tab ────────────────────────────────────────────────────────────

test('switches to the System tab', async () => {
  await page.locator('.nav-link').filter({ hasText: /^System$/ }).click();
  // Use strong selector — the modal "Connected Clients" h5 is also in the DOM (BVN teleport)
  await expect(page.locator('strong:has-text("Connected Clients")')).toBeVisible({ timeout: 10_000 });
});

test('can open the View Clients modal', async () => {
  await page.click('button:has-text("View Clients")');
  await waitForModal(page, 'Connected Clients');
  await page.click('.modal.show .btn-secondary, .modal.show button:has-text("Close")');
});

// ── Logs tab ──────────────────────────────────────────────────────────────

test('switches to the Logs tab and can change source', async () => {
  await page.click('.nav-link:has-text("Logs")');
  await expect(page.locator('text=Server').first()).toBeVisible();
  // Switch to Client logs — Bootstrap btn-check inputs have pointer-events:none; click the label
  await page.locator('.tab-pane.active label').filter({ hasText: /^Client$/ }).click();
});

// ── Backups tab ──────────────────────────────────────────────────────────

test('switches to the Backups tab', async () => {
  await page.click('.nav-link:has-text("Backups")');
  // Wait for the loading spinner to resolve to either the backups table or the empty-state alert.
  // Scope to elements unique to ConfigBackups to avoid matching the RBAC modal's table.
  await expect(
    page.locator('.alert:has-text("No backup files found")').or(
      page.locator('th:has-text("Filename")')
    )
  ).toBeVisible({ timeout: 10_000 });
});
