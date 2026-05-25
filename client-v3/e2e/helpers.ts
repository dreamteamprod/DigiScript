import type { Page } from '@playwright/test';

export const SERVER_PORT = 8888;
export const UI_BASE = `http://localhost:${SERVER_PORT}/ui-new`;
export const ADMIN_USERNAME = 'admin';
export const ADMIN_PASSWORD = 'testpassword';

/** Wait until the WebSocket is connected and the app has finished its startup sequence. */
export async function waitForAppReady(page: Page): Promise<void> {
  await page.waitForSelector('#connection-status.healthy', { timeout: 15_000 });
}

/** Navigate to the login page, fill credentials, and wait for redirect to home. */
export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto(`${UI_BASE}/login`);
  await waitForAppReady(page);
  await page.fill('#username-input', ADMIN_USERNAME);
  await page.fill('#password-input', ADMIN_PASSWORD);
  await page.click('button:has-text("Login")');
  await page.waitForURL(`${UI_BASE}/`);
  await waitForAppReady(page);
}

/** Wait for a Bootstrap modal with the given title to be visible. */
export async function waitForModal(page: Page, title: string | RegExp): Promise<void> {
  await page
    .locator('.modal.show .modal-title')
    .filter({ hasText: title })
    .waitFor({ timeout: 5_000 });
}

/** Click the OK/confirm button in the currently open Bootstrap modal. */
export async function confirmModal(page: Page): Promise<void> {
  await page.click('.modal.show .modal-footer button.btn-primary');
}

/** Click the Cancel button in the currently open Bootstrap modal. */
export async function cancelModal(page: Page): Promise<void> {
  await page.click('.modal.show .modal-footer button:has-text("Cancel")');
}

/** Wait for the currently-open Bootstrap modal to fully close. */
export async function waitForModalClosed(page: Page, timeout = 5_000): Promise<void> {
  await page.waitForSelector('.modal.show', { state: 'detached', timeout });
}

/** Click OK on a ConfirmDialog (the app-level confirm dialog, not a BModal). */
export async function confirmDialog(page: Page): Promise<void> {
  await page.waitForSelector('.modal.show', { timeout: 5_000 });
  // Confirmation buttons may be btn-primary, btn-danger, or btn-warning depending on context
  await page.locator('.modal.show .modal-footer button:not(.btn-secondary)').first().click();
  await page.waitForSelector('.modal.show', { state: 'detached', timeout: 5_000 });
}
