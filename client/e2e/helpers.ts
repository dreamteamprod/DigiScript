import { errors, type APIRequestContext, type Locator, type Page } from '@playwright/test';

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

/**
 * Fill in the first currently-open line editor (classic or collaborative — both render
 * the same Done/Delete row) with an act, scene, optional character and text, leaving it
 * open (the caller clicks Done). Returns the editor's own locator in case the caller
 * needs it again (e.g. to add a second line before the first is done).
 *
 * Design E: the Act/Scene selects only render when this line has no previous line to
 * inherit them from (the very first line of an empty page/draft) — every later line
 * inherits them automatically, so `act`/`scene` are silently unused for those.
 */
export async function fillOpenLineEditor(
  page: Page,
  { act, scene, character, text }: { act: string; scene: string; character?: string; text?: string }
): Promise<Locator> {
  await page.waitForSelector('button:has-text("Done")', { timeout: 5_000 });
  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  // `count()` doesn't auto-wait, so checking for the act select straight away can race
  // the card's own render and silently skip act/scene. The act select and the card's
  // other controls render in the same pass, so once any control is present the act
  // select's presence is settled. A card with no controls at all (e.g. a cue line that
  // inherits its act/scene) has nothing to race, hence the swallowed timeout.
  await lineEditor
    .locator('select, input[type="text"]')
    .first()
    .waitFor({ timeout: 2_000 })
    .catch((error: unknown) => {
      if (!(error instanceof errors.TimeoutError)) throw error;
    });
  const actSelect = lineEditor.getByTestId('line-act-select');
  if ((await actSelect.count()) > 0) {
    await actSelect.selectOption({ label: act });
    await lineEditor.getByTestId('line-scene-select').selectOption({ label: scene });
  }
  if (character) {
    await lineEditor
      .locator('select')
      .filter({ hasText: character })
      .selectOption({ label: character });
  }
  if (text) {
    await page.locator('input[type="text"]:visible').last().fill(text);
  }
  return lineEditor;
}

/**
 * Clicks "Add Dialogue", fills the editor it opens, and clicks Done — which now (Design
 * E) just closes the line; only Enter chains into another blank one, and this never
 * presses it, so there is nothing left open to clean up afterwards.
 */
export async function addDialogueLine(
  page: Page,
  fields: { act: string; scene: string; character?: string; text?: string }
): Promise<void> {
  await page.click('button:has-text("Add Dialogue")');
  await fillOpenLineEditor(page, fields);
  await page.locator('button:has-text("Done")').first().click();
  await page.waitForSelector('button:has-text("Done")', { state: 'hidden', timeout: 5_000 });
}

/**
 * Selects exactly the script lines whose text matches `lineTexts`, in on-screen order
 * (top to bottom, contiguous — the selection model only supports one contiguous block),
 * by ticking each line's checkbox. Clears any selection left over from an earlier test
 * first, so each test using it is self-contained rather than inheriting selection state.
 */
export async function selectLines(page: Page, lineTexts: string[]): Promise<void> {
  const clear = page.getByRole('button', { name: 'Clear Selection' });
  if (await clear.isVisible()) {
    await clear.click();
    await clear.waitFor({ state: 'hidden', timeout: 3_000 });
  }
  for (const text of lineTexts) {
    // Sequential on purpose: the first click sets the selection anchor and later ones
    // extend the range, so running them in parallel would break the selection.
    const row = page.locator('.script-line-row').filter({ hasText: text });
    await row.hover(); // NOSONAR sequential UI interactions
    await row.getByRole('checkbox').click(); // NOSONAR sequential UI interactions
  }
  const expected = `${lineTexts.length} line${lineTexts.length === 1 ? '' : 's'} selected`;
  await page.getByRole('toolbar', { name: 'Selected lines' }).getByText(expected).waitFor({
    timeout: 5_000,
  });
}
