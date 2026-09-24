import type { APIRequestContext, Page } from '@playwright/test';

import { BASE_URL } from './env.js';

export const UI_BASE = BASE_URL;
export const ADMIN_USERNAME = 'admin';
export const ADMIN_PASSWORD = 'testpassword';

/** Wait until the WebSocket is connected and the app has finished its startup sequence. */
export async function waitForAppReady(page: Page): Promise<void> {
  await page.waitForSelector('#connection-status.healthy', { timeout: 15_000 });
}

/** Navigate to the login page, fill the given credentials, and wait for redirect to home. */
export async function loginAs(page: Page, username: string, password: string): Promise<void> {
  await page.goto(`${UI_BASE}/login`);
  await waitForAppReady(page);
  await page.fill('#username-input', username);
  await page.fill('#password-input', password);
  await page.click('button:has-text("Login")');
  await page.waitForURL(`${UI_BASE}/`);
  await waitForAppReady(page);
}

/** Navigate to the login page, fill credentials, and wait for redirect to home. */
export async function loginAsAdmin(page: Page): Promise<void> {
  await loginAs(page, ADMIN_USERNAME, ADMIN_PASSWORD);
}

/**
 * Log in via the REST API (no browser page involved) and return the JWT access token.
 * Useful for setup/teardown API calls, e.g. creating a second test user as admin.
 */
export async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<string> {
  const response = await request.post(`${UI_BASE}/api/v1/auth/login`, {
    data: { username, password },
  });
  if (!response.ok()) {
    throw new Error(
      `apiLogin failed for ${username}: ${response.status()} ${await response.text()}`
    );
  }
  const body = await response.json();
  return body.access_token as string;
}

/** Create a user via the admin-only auth/create endpoint. Requires an admin bearer token. */
export async function createUser(
  request: APIRequestContext,
  adminToken: string,
  username: string,
  password: string,
  isAdmin = false
): Promise<void> {
  const response = await request.post(`${UI_BASE}/api/v1/auth/create`, {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { username, password, is_admin: isAdmin },
  });
  if (!response.ok()) {
    throw new Error(
      `createUser failed for ${username}: ${response.status()} ${await response.text()}`
    );
  }
}

/** Delete a user by username via the admin-only auth/delete endpoint (looked up via auth/users). */
export async function deleteUserByUsername(
  request: APIRequestContext,
  adminToken: string,
  username: string
): Promise<void> {
  const listResponse = await request.get(`${UI_BASE}/api/v1/auth/users`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  if (!listResponse.ok()) return;
  const { users } = (await listResponse.json()) as { users: { id: number; username: string }[] };
  const match = users.find((u) => u.username === username);
  if (!match) return;
  await request.post(`${UI_BASE}/api/v1/auth/delete`, {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { id: match.id },
  });
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
