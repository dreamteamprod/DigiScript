/**
 * Collaborative script editing (setting on): open the shared draft and browse it.
 *
 * Step 2 is read-only. Runs last on purpose — it flips the server-wide
 * `collaborative_script_editing` setting, which every earlier spec needs OFF, and puts
 * it back in afterAll. (The retry hooks also restore config, covering a failed run.)
 *
 * The setting is hidden from the Settings page until the editor ships, so it is driven
 * through the API with the admin's own token.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import { UI_BASE, loginAsAdmin, waitForAppReady, confirmModal } from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

const MODE = 'collaborative_script_editing';
const SCRIPT_URL = `${UI_BASE}/show-config/script`;

let ctx: BrowserContext;
let page: Page;
let ctx2: BrowserContext | null = null;

async function token(p: Page): Promise<string> {
  const t = await p.evaluate(() => localStorage.getItem('digiscript_auth_token'));
  if (!t) throw new Error('no auth token in localStorage');
  return t;
}

async function patchSettings(p: Page, body: Record<string, unknown>) {
  return p.request.patch(`${UI_BASE}/api/v1/settings`, {
    headers: { Authorization: `Bearer ${await token(p)}` },
    data: body,
  });
}

/** Wait until the collaborative editor (not the classic one) is what is on screen. */
async function openScriptEditor(p: Page): Promise<void> {
  await p.goto(SCRIPT_URL);
  await waitForAppReady(p);
  await expect(p.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 15_000 });
}

const stopEditing = (p: Page) => p.locator('button:has-text("Stop Editing")');
const firstRow = (p: Page) => p.locator('.script-line-row').first();

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  const response = await patchSettings(page, { [MODE]: true });
  expect(response.status()).toBe(200);
  await openScriptEditor(page);
});

test.afterAll(async () => {
  // Nobody is editing any more, so the server allows the switch back. The room closes
  // asynchronously after the last editor leaves, so allow it a moment.
  await expect
    .poll(async () => (await patchSettings(page, { [MODE]: false })).status(), {
      timeout: 15_000,
    })
    .toBe(200);
  await ctx2?.close();
  await ctx.close();
});

test('the mode setting rejects a non-boolean value', async () => {
  const response = await patchSettings(page, { [MODE]: 'yes' });

  expect(response.status()).toBe(400);
});

test('shows the collaborative editor, with cut mode not yet available', async () => {
  await expect(page.locator('button:has-text("Edit")')).toBeVisible();
  await expect(page.locator('button:has-text("Cuts")')).toBeDisabled();
});

test('Edit opens the shared draft and its lines appear', async () => {
  await page.click('button:has-text("Edit")');

  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
});

test('the mode cannot be changed while someone is editing', async () => {
  const response = await patchSettings(page, { [MODE]: false });

  expect(response.status()).toBe(409);
});

test('Next Page stops at the last page that exists', async () => {
  const next = page.locator('button:has-text("Next Page")');
  for (let i = 0; i < 20 && (await next.isEnabled()); i += 1) {
    await next.click();
  }

  await expect(next).toBeDisabled();
  // Go to Page past the end is refused with a message rather than creating a page.
  await page.click('button:has-text("Go to Page")');
  await page.fill('#page-input', '999');
  await confirmModal(page);
  await expect(page.getByTestId('page-error')).toContainText('last page is');
  await page.keyboard.press('Escape');
});

test('reloading during a draft rejoins it', async () => {
  await page.reload();
  await waitForAppReady(page);

  await expect(stopEditing(page)).toBeVisible({ timeout: 15_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
});

test('a second browser can edit the same script at the same time', async ({ browser }) => {
  ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await loginAsAdmin(page2);
  await openScriptEditor(page2);

  await page2.click('button:has-text("Edit")');

  await expect(stopEditing(page2)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page2)).toBeVisible({ timeout: 15_000 });
  // The first browser is still an editor with its draft open.
  await expect(stopEditing(page)).toBeVisible();

  await stopEditing(page2).click();
  await expect(page2.locator('button:has-text("Edit")')).toBeVisible({ timeout: 10_000 });
});

test('Stop Editing returns to Edit', async () => {
  await stopEditing(page).click();

  await expect(page.locator('button:has-text("Edit")')).toBeVisible({ timeout: 10_000 });
});
