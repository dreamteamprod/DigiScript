/**
 * Collaborative script editing (setting on): open the shared draft and browse it.
 *
 * Currently read-only: editors join and browse the draft; editing is not yet
 * implemented. Runs last on purpose — it flips the server-wide
 * `collaborative_script_editing` setting, which every earlier spec needs OFF, and puts
 * it back in afterAll. A retry's own `beforeAll` restores the DB and config from the
 * spec-start snapshot (see `registerRetryHooks`), but that does not help a *final*
 * failed attempt — `afterAll` below is what must actually put the setting back.
 *
 * The setting is hidden from the Settings page until the editor ships, so it is driven
 * through the API with the admin's own token.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  waitForModalClosed,
  confirmModal,
} from '../helpers.js';
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

const editButton = (p: Page) =>
  p.locator('.sticky-header').getByRole('button', { name: 'Edit', exact: true });
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
  // Everyone must actually stop editing before the mode can switch back — the server
  // refuses while any session is still an editor (409), regardless of which test in
  // this file failed. Closing a context does not itself send STOP_SCRIPT_EDIT, so do
  // that first; then poll, since the room closes asynchronously after the last editor
  // leaves (checkpoint, then ROOM_CLOSED).
  if (ctx2) {
    const page2 = ctx2.pages()[0];
    if (
      page2 &&
      (await stopEditing(page2)
        .isVisible()
        .catch(() => false))
    ) {
      await stopEditing(page2).click();
    }
    await ctx2.close();
  }
  if (
    await stopEditing(page)
      .isVisible()
      .catch(() => false)
  ) {
    await stopEditing(page).click();
  }

  // Stopping only releases the editor lock — Step 2 deliberately keeps the draft
  // across Stop Editing (D9), and Step 3's tests are the first in this file to
  // actually write to it, so a draft now persists to disk once the room closes with
  // no editors left. `has_unsaved_changes()` sees that persisted draft and blocks the
  // mode flip regardless of who is or isn't an editor. There is no UI for discarding
  // it yet (Step 5), so use the admin REST endpoint directly, exactly as the future
  // "Discard draft" action will.
  await page.request.delete(`${UI_BASE}/api/v1/show/script/draft`, {
    headers: { Authorization: `Bearer ${await token(page)}` },
  });

  await expect
    .poll(async () => (await patchSettings(page, { [MODE]: false })).status(), {
      timeout: 15_000,
    })
    .toBe(200);
  await ctx.close();
});

test('the mode setting rejects a non-boolean value', async () => {
  const response = await patchSettings(page, { [MODE]: 'yes' });

  expect(response.status()).toBe(400);
});

test('shows the collaborative editor, with cut mode not yet available', async () => {
  await expect(editButton(page)).toBeVisible();
  await expect(page.locator('button:has-text("Cuts")')).toBeDisabled();
});

test('Edit opens the shared draft and its lines appear', async () => {
  await editButton(page).click();

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
  // App.vue mounts its own (closed) live-view "Go to Page" modal on every route —
  // opened from the navbar's "Jump To Page" item, not by a visible button here — so
  // #page-input is not unique app-wide; scope to the modal that is actually open, as
  // spec 10 does for the classic editor's identical modal.
  await page.click('button:has-text("Go to Page")');
  await waitForModal(page, 'Go to Page');
  await page.fill('.modal.show input[type="number"]', '999');
  await confirmModal(page);
  await expect(page.locator('.modal.show').getByTestId('page-error')).toContainText('last page is');
  await page.keyboard.press('Escape');
  await waitForModalClosed(page);

  // Back to page 1 (which has content) via Go to Page rather than a single Prev Page
  // click, so this doesn't assume the fixture is exactly two pages long.
  await page.click('button:has-text("Go to Page")');
  await waitForModal(page, 'Go to Page');
  await page.fill('.modal.show input[type="number"]', '1');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('p:has-text("Current Page: 1")')).toBeVisible();
});

test('reloading while editing keeps editor status and the same draft', async () => {
  // A reload closes and reopens the WebSocket; the reconnect resumes the same client
  // id (REFRESH_CLIENT) inside the server's reconnect grace window, so the edit lock
  // is kept rather than released (issue #1419, fixed by #1427) — mirrors spec 10's
  // "reloading while editing keeps edit mode" for the classic editor. What must also
  // hold here, since the draft itself is a separate round trip from the lock: no
  // content is lost and CollabScriptEditor rejoins the *same* draft rather than a
  // fresh one, so this captures the content before reloading and compares it after —
  // a fresh/empty draft would also show a first row, so "a row is visible" alone
  // wouldn't prove that.
  const before = await firstRow(page).textContent();

  await page.reload();
  await waitForAppReady(page);

  await expect(stopEditing(page)).toBeVisible({ timeout: 15_000 });
  await expect(editButton(page)).not.toBeVisible();
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
  await expect(firstRow(page)).toHaveText(before ?? '');
});

test('a second browser can edit the same script at the same time', async ({ browser }) => {
  ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await loginAsAdmin(page2);
  await openScriptEditor(page2);

  await editButton(page2).click();

  await expect(stopEditing(page2)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page2)).toBeVisible({ timeout: 15_000 });
  // The first browser is still an editor with its draft open.
  await expect(stopEditing(page)).toBeVisible();

  // Prove the two browsers actually share the draft room, not just that each renders
  // *a* row: matching content on both, and — since a client can't create a page — the
  // same server-owned trailing page stops Next Page at the same page number for both.
  await expect(firstRow(page2)).toHaveText((await firstRow(page).textContent()) ?? '');

  async function lastPageReached(p: Page): Promise<string | null> {
    const next = p.locator('button:has-text("Next Page")');
    for (let i = 0; i < 20 && (await next.isEnabled()); i += 1) {
      await next.click();
    }
    await expect(next).toBeDisabled();
    return p.locator('p:has-text("Current Page:")').textContent();
  }
  expect(await lastPageReached(page2)).toBe(await lastPageReached(page));

  await stopEditing(page2).click();
  await expect(editButton(page2)).toBeVisible({ timeout: 10_000 });
});

test('adds a dialogue line with act, scene, character and text', async () => {
  await page.click('button:has-text("Add Dialogue")');
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });

  const lineEditor = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await lineEditor.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await lineEditor.locator('select').nth(1).selectOption({ label: 'Scene 1' });
  await lineEditor
    .locator('select')
    .filter({ hasText: 'Hamlet' })
    .selectOption({ label: 'Hamlet' });
  await page.locator('input[type="text"]:visible').last().fill('To be or not to be');

  await page.locator('button:has-text("Done")').first().click();
  // Add Dialogue chains into another blank dialogue editor after Done, for continuous
  // typing (matches the classic editor) — delete it rather than fill it in, since this
  // test only wants the one line.
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await page.locator('button.btn-danger:has-text("Delete")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.script-line-row')).toContainText('To be or not to be');
});

test('typed text survives a reload — it is written to the shared draft, not local state', async () => {
  const row = page.locator('.script-line-row').filter({ hasText: 'To be or not to be' });
  await row.locator('.script-edit-controls button:has-text("Edit")').click();
  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  await page.locator('input[type="text"]:visible').last().fill('To be, or not to be, that is it');
  await page.locator('button:has-text("Done")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });

  await page.reload();
  await waitForAppReady(page);
  await expect(stopEditing(page)).toBeVisible({ timeout: 15_000 });

  await expect(page.locator('.script-line-row')).toContainText('To be, or not to be, that is it');
});

test('inserts a line from a row menu and deletes it again', async () => {
  const row = page.locator('.script-line-row').filter({ hasText: 'To be, or not to be' });
  const rowCountBefore = await page.locator('.script-line-row').count();

  await row.locator('.script-edit-controls button.dropdown-toggle-split').click();
  await page.click('.dropdown-item:has-text("Insert Stage Direction")');

  await expect(page.locator('button:has-text("Done")').first()).toBeVisible({ timeout: 5_000 });
  const inserted = page
    .locator('div.row')
    .filter({ has: page.locator('button:has-text("Done")') })
    .first();
  await inserted.locator('select').nth(0).selectOption({ label: 'Act 1' });
  await inserted.locator('select').nth(1).selectOption({ label: 'Scene 1' });

  // Unscoped, like the classic editor's own equivalent E2E test: `div.row` nests
  // (Bootstrap grid), so the "has a Done button" filter's first match can be an
  // ancestor row that also wraps the (hidden) Stage Direction Styles tab's own Delete
  // button, making a *scoped* lookup inside it ambiguous.
  await page.locator('button.btn-danger:has-text("Delete")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.script-line-row')).toHaveCount(rowCountBefore);
});

test('Stop Editing returns to Edit', async () => {
  await stopEditing(page).click();

  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
});
