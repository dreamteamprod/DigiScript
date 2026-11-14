/**
 * Collaborative script editing (setting on): join the shared draft, edit it, save/
 * stop/discard it, bulk edit, and cut mode (Phase 3, Steps 1-5). Runs last on purpose —
 * it flips the server-wide `collaborative_script_editing` setting, which every earlier
 * spec needs OFF, and puts it back in afterAll. A retry's own `beforeAll` restores the
 * DB and config from the spec-start snapshot (see `registerRetryHooks`), but that does
 * not help a *final* failed attempt — `afterAll` below is what must actually put the
 * setting back.
 *
 * The setting is turned on through the real Settings page UI in `beforeAll` (proving
 * the admin toggle control itself, now that Step 5 has un-hidden it) rather than the
 * API directly; it is turned back off through the API in `afterAll` since that is
 * cleanup, not a thing under test. The two direct-API tests below (rejecting a
 * non-boolean value, refusing a change mid-edit) exercise the REST contract itself,
 * which does not need the UI.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  waitForModalClosed,
  confirmModal,
  confirmDialog,
  fillOpenLineEditor,
  addDialogueLine,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

const MODE = 'collaborative_script_editing';
const SCRIPT_URL = `${UI_BASE}/show-config/script`;

let ctx: BrowserContext;
let page: Page;
let ctx2: BrowserContext | null = null;
let ctx4: BrowserContext | null = null;

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

/** Bring ctx2's idle page back in as an editor, for a test that reuses it. */
async function reenterCtx2AsEditor(ctx: BrowserContext | null): Promise<Page> {
  if (!ctx) throw new Error('ctx2 from the earlier two-editor test is not open');
  const page2 = ctx.pages()[0]!;
  await editButton(page2).click();
  await expect(stopEditing(page2)).toBeVisible({ timeout: 10_000 });
  return page2;
}

/** Turn the setting on via the real Settings page UI (System Config > Settings). */
async function enableCollabEditingViaUI(p: Page): Promise<void> {
  await p.goto(UI_BASE);
  await waitForAppReady(p);
  await p.click('a:has-text("System Config")');
  await p.click('.nav-link:has-text("Settings")');
  await expect(p.locator('button:has-text("Submit")')).toBeVisible({ timeout: 10_000 });

  const toggle = p
    .locator('label:has-text("Collaborative Script Editing")')
    .locator('..')
    .locator('input[type="checkbox"], .form-check-input')
    .first();
  await expect(toggle).toBeVisible({ timeout: 5_000 });
  // Don't assume it's currently off — only click if it needs to change, so a retry
  // (or any other state the DB snapshot left it in) can't double-toggle it back off.
  if (!(await toggle.isChecked())) await toggle.click();
  await p.click('button:has-text("Submit")');
  await expect(p.locator('.v-toast__item:has-text("Saved settings")')).toBeVisible({
    timeout: 10_000,
  });
}

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await enableCollabEditingViaUI(page);
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
  if (ctx4) {
    await ctx4.close();
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
  // mode flip regardless of who is or isn't an editor. The Step 4 tests below already
  // exercise Discard through the UI; this REST call is a belt-and-braces cleanup for
  // whatever state a *failed* attempt at any test in this file leaves behind, same as
  // the admin's own Discard would do.
  const discardResponse = await page.request.delete(`${UI_BASE}/api/v1/show/script/draft`, {
    headers: { Authorization: `Bearer ${await token(page)}` },
  });
  expect(
    discardResponse.ok(),
    `discarding the script draft failed: ${discardResponse.status()} ${await discardResponse.text()}`
  ).toBe(true);

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

test('shows the collaborative editor, with Cuts available', async () => {
  await expect(editButton(page)).toBeVisible();
  await expect(page.locator('button:has-text("Cuts")')).toBeEnabled();
});

test('the mode can be changed while only a viewer (no editor) is present', async () => {
  // `page` has already auto-joined the room as a plain viewer by now (Phase 4
  // Step A — joining happens on mount, regardless of role) and is not yet an
  // editor, proving the mode-switch guard's fix: a lone viewer must not block
  // the toggle, unlike an actual editor (checked below once `page` becomes
  // one). Flip off and immediately back on, so every later test in this file
  // still runs with the mode on — and wait for CollabScriptEditor to actually
  // remount before moving on, since toggling the setting switches components.
  const off = await patchSettings(page, { [MODE]: false });
  expect(off.status()).toBe(200);

  const on = await patchSettings(page, { [MODE]: true });
  expect(on.status()).toBe(200);
  await expect(page.locator('button:has-text("Go to Page")')).toBeVisible({ timeout: 10_000 });
});

test('cut mode: toggling a line part requires Save Cuts, exclusive with editing', async () => {
  await page.click('button:has-text("Cuts")');

  await expect(page.locator('button:has-text("Stop Cutting")')).toBeVisible({ timeout: 10_000 });
  const saveCutsButton = page.getByRole('button', { name: 'Save Cuts', exact: true });
  await expect(saveCutsButton).toBeDisabled();
  // D11: cutting and editing are mutually exclusive — Edit is not offered while cutting.
  await expect(editButton(page)).not.toBeVisible();

  const cutLinePart = firstRow(page).locator('.viewable-line-cut').first();
  await cutLinePart.click();
  await expect(saveCutsButton).toBeEnabled();
  await saveCutsButton.click();
  await expect(page.locator('.v-toast__item:has-text("Saved script cuts")').first()).toBeVisible({
    timeout: 10_000,
  });
  // The authoritative "this save has actually landed" signal, not just "a toast with
  // this text is somewhere in the DOM" — Save Cuts only disables once linePartCuts
  // matches the server's cuts. Needed before un-cutting below: a second toast
  // assertion could otherwise match the first (still-visible) toast's own element
  // rather than proving the second save round-tripped.
  await expect(saveCutsButton).toBeDisabled({ timeout: 10_000 });

  // Un-cut it again before leaving — this test's job is to prove the save round trip
  // works, not to leave a cut line part behind for later tests/specs to work around.
  // Stop Cutting below would otherwise confirm() first (cutsChanged still true if this
  // save hadn't actually settled yet), hanging forever with nothing to answer it.
  await cutLinePart.click();
  await expect(saveCutsButton).toBeEnabled();
  await saveCutsButton.click();
  await expect(saveCutsButton).toBeDisabled({ timeout: 10_000 });

  await page.click('button:has-text("Stop Cutting")');
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('button:has-text("Cuts")')).toBeVisible();
});

test('Edit opens the shared draft and its lines appear', async () => {
  await editButton(page).click();

  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
});

test('a non-editing viewer sees the live draft, not stale saved content (Phase 4 Step A)', async ({
  browser,
}) => {
  ctx4 = await browser.newContext();
  const page4 = await ctx4.newPage();
  await loginAsAdmin(page4);
  await openScriptEditor(page4);

  // Never requests edit — stays a plain viewer throughout this and the next test.
  await expect(editButton(page4)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page4)).toBeVisible({ timeout: 15_000 });
  // Matches the editor's own (live, synced) content, not a stale REST render —
  // a fresh/empty join would also show *a* row, so this compares actual text.
  // page's row is can-edit=true and renders its edit-controls menu inline as
  // text too (Edit/Insert.../Delete); page4 is a plain viewer and never does.
  // Diff a clone (not the live row, which later tests still click into) with
  // that subtree stripped out before comparing.
  const editorText = await firstRow(page).evaluate((el) => {
    const clone = el.cloneNode(true) as HTMLElement;
    clone.querySelector('.script-edit-controls')?.remove();
    return clone.textContent;
  });
  await expect(firstRow(page4)).toHaveText(editorText ?? '');
});

test('Cuts is proactively disabled, with a reason, while someone is editing', async ({
  browser,
}) => {
  // A disposable third context — unlike ctx2, nothing later in this file depends on it.
  // The button is disabled client-side before any request is sent (cutsDisabledReason),
  // so this cannot be proven by clicking past it and catching a server rejection.
  const ctx3 = await browser.newContext();
  const page3 = await ctx3.newPage();
  await loginAsAdmin(page3);
  await openScriptEditor(page3);

  const cutsButton = page3.locator('button:has-text("Cuts")');
  await expect(cutsButton).toBeDisabled({ timeout: 10_000 });
  await expect(cutsButton).toHaveAttribute('title', 'Script editing is in progress');

  await ctx3.close();
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
  await addDialogueLine(page, {
    act: 'Act 1',
    scene: 'Scene 1',
    character: 'Hamlet',
    text: 'To be or not to be',
  });

  await expect(page.locator('.script-line-row')).toContainText('To be or not to be');
});

test('the non-editing viewer sees the new line live, without a reload', async () => {
  if (!ctx4) throw new Error('ctx4 from the earlier live-viewing test is not open');
  const page4 = ctx4.pages()[0]!;

  await expect(
    page4.locator('.script-line-row').filter({ hasText: 'To be or not to be' })
  ).toBeVisible({ timeout: 10_000 });

  await ctx4.close();
  ctx4 = null;
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

  await fillOpenLineEditor(page, { act: 'Act 1', scene: 'Scene 1' });

  // Unscoped, like the classic editor's own equivalent E2E test: `div.row` nests
  // (Bootstrap grid), so the "has a Done button" filter's first match can be an
  // ancestor row that also wraps the (hidden) Stage Direction Styles tab's own Delete
  // button, making a *scoped* lookup inside it ambiguous.
  await page.locator('button.btn-danger:has-text("Delete")').first().click();
  await expect(page.locator('button:has-text("Done")')).not.toBeVisible({ timeout: 5_000 });
  await expect(page.locator('.script-line-row')).toHaveCount(rowCountBefore);
});

test('Save commits the draft to the DB, not just the shared draft', async () => {
  const saveButton = page.getByRole('button', { name: 'Save', exact: true });
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  // The SaveProgressModal (shared with the classic editor) is ok-only and stays open
  // until dismissed — its backdrop would otherwise block every click after this one.
  await waitForModal(page, 'Saving Script');
  await expect(page.locator('.modal.show').getByText('Finished saving script.')).toBeVisible({
    timeout: 15_000,
  });
  await confirmModal(page);
  await waitForModalClosed(page);

  // The unsaved-draft indicator (Step 4) clears once the server confirms the save.
  await expect(page.locator('.sticky-header').getByText('Unsaved draft')).not.toBeVisible({
    timeout: 10_000,
  });

  // Stop Editing now goes straight back to Edit (nothing unsaved) — and the viewer,
  // which reads over REST rather than the shared draft, already shows the saved
  // content, proving Save reached the DB and not just the draft.
  await stopEditing(page).click();
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('.script-line-row')).toContainText('To be, or not to be, that is it');

  await editButton(page).click();
  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
});

test('typing again after a save makes Stop Editing offer Keep Draft / Discard', async () => {
  // Only "A line to keep" should remain unsaved — addDialogueLine() already drops the
  // auto-chained blank editor Done leaves behind.
  await addDialogueLine(page, {
    act: 'Act 1',
    scene: 'Scene 1',
    character: 'Alice',
    text: 'A line to keep',
  });

  await stopEditing(page).click();
  await waitForModal(page, 'Stop Editing');
  await page.click('.modal.show button:has-text("Keep Draft")');
  await waitForModalClosed(page);

  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
});

test('the Revisions page blocks New Revision and offers Discard while the draft is unsaved', async () => {
  await page.goto(`${UI_BASE}/show-config/script-revisions`);
  await waitForAppReady(page);

  await expect(page.locator('button:has-text("New Revision")')).toBeDisabled({ timeout: 10_000 });
  await expect(page.getByRole('button', { name: 'Discard Draft', exact: true })).toBeVisible({
    timeout: 10_000,
  });

  // Don't actually discard here — the next test needs this kept draft to still exist.
  await openScriptEditor(page);
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
});

test('re-entering resumes the kept draft, with Save already enabled (D8)', async () => {
  await editButton(page).click();
  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.script-line-row').filter({ hasText: 'A line to keep' })).toBeVisible({
    timeout: 10_000,
  });

  // D8: resuming a kept draft must not require a fresh local edit before Save
  // re-enables — the rejoin's own sync step used to clear isDraftDirty unconditionally,
  // leaving Save stuck disabled until something was typed again.
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeEnabled({
    timeout: 10_000,
  });
});

test('bulk edit applies a character across a range of lines', async () => {
  await page.click('button:has-text("Bulk Edit")');
  await expect(page.getByRole('button', { name: 'Start', exact: true }).first()).toBeVisible({
    timeout: 5_000,
  });

  await page.getByRole('button', { name: 'Start', exact: true }).first().click();
  await page.getByRole('button', { name: 'End', exact: true }).last().click();
  await waitForModal(page, 'Bulk Edit');

  await page.locator('.modal.show #bulk-part-input').selectOption({ label: 'Part 1' });
  await page.locator('.modal.show #bulk-char-input').selectOption({ label: 'Alice' });
  await confirmModal(page);
  await waitForModalClosed(page);

  // After apply, bulk edit mode exits automatically.
  await expect(page.getByRole('button', { name: 'Bulk Edit', exact: true })).toBeVisible({
    timeout: 5_000,
  });
  await expect(
    page.locator('.script-line-row').filter({ hasText: 'To be, or not to be, that is it' })
  ).toContainText('Alice');
});

test('Discard, triggered from the Revisions page, reverts the draft and closes the room for every editor in it', async ({
  browser,
}) => {
  // ctx2/page2 is still open (idle, Edit button visible) from the earlier two-editor
  // test — bring it back in as a second editor with its own real unsaved edit, so
  // Discard's effect on *another* client's actual work (not just the one who clicked
  // it) is actually exercised — proving the "will lose their work too" warning true,
  // not just testing its label text.
  const page2 = await reenterCtx2AsEditor(ctx2);
  await addDialogueLine(page2, {
    act: 'Act 1',
    scene: 'Scene 1',
    character: 'Hamlet',
    text: "page2's own unsaved line",
  });
  // The shared draft — confirms both clients see it before the discard below.
  await expect(
    page.locator('.script-line-row').filter({ hasText: "page2's own unsaved line" })
  ).toBeVisible({ timeout: 10_000 });

  // Discard it from the Revisions page's own button, via a third session that was
  // never an editor — a disposable context, same pattern as the earlier cut/edit
  // exclusivity test. `page`/`page2` deliberately stay joined editors throughout
  // (rather than navigating one of them away first) so the server's demote-every-
  // client-still-in-the-room logic has both of them to clear, exactly like the
  // earlier (never-exercised) in-editor Discard path did.
  const ctx3 = await browser.newContext();
  const page3 = await ctx3.newPage();
  await loginAsAdmin(page3);
  await page3.goto(`${UI_BASE}/show-config/script-revisions`);
  await waitForAppReady(page3);
  const discardDraftButton = page3.getByRole('button', { name: 'Discard Draft', exact: true });
  await expect(discardDraftButton).toBeVisible({ timeout: 10_000 });
  await discardDraftButton.click();
  await confirmDialog(page3);
  // The revision unlocks for everyone once the discard completes server-side.
  await expect(page3.locator('button:has-text("New Revision")')).toBeEnabled({ timeout: 10_000 });
  await ctx3.close();

  // Both editors are torn down server-side and notified — ROOM_CLOSED (or the
  // isEditor watcher, once GET_SCRIPT_CONFIG_STATUS drops them from `editors`) flips
  // each one back to the Edit button, with no action from either of them.
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
  await expect(editButton(page2)).toBeVisible({ timeout: 10_000 });

  // Reverted to the last save — both the kept-not-saved line from the earlier test
  // and page2's own freshly-typed, never-saved line are gone, for both clients.
  await editButton(page).click();
  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
  await expect(firstRow(page)).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.script-line-row').filter({ hasText: 'A line to keep' })).toHaveCount(
    0
  );
  await expect(
    page.locator('.script-line-row').filter({ hasText: "page2's own unsaved line" })
  ).toHaveCount(0);
});

test('Stop Editing downgrades to viewer and keeps watching live, rather than reverting to stale content (Phase 4 Step A, Tim’s decision)', async () => {
  // ctx2/page2 is idle (Edit button visible) since the earlier Discard test
  // tore its editor status down too. Bring it back in as the one still editing.
  const page2 = await reenterCtx2AsEditor(ctx2);

  // `page` stops editing — per Tim's decision this downgrades to viewer and
  // keeps watching live, rather than leaving the room and falling back to a
  // stale REST render.
  await stopEditing(page).click();
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });

  await addDialogueLine(page2, {
    act: 'Act 1',
    scene: 'Scene 1',
    character: 'Hamlet',
    text: "page2's live-only line",
  });

  // `page`, now a mere viewer that never reloaded, sees it with no action of
  // its own — proving it kept watching live rather than needing a refresh.
  await expect(
    page.locator('.script-line-row').filter({ hasText: "page2's live-only line" })
  ).toBeVisible({ timeout: 10_000 });

  // Clean up page2's own unsaved line so the draft is clean again before the
  // final test below, which expects Stop Editing to go straight back to Edit
  // with nothing unsaved (no Keep/Discard modal).
  await stopEditing(page2).click();
  await waitForModal(page2, 'Stop Editing');
  await page2.click('.modal.show button:has-text("Discard")');
  await waitForModalClosed(page2);
  await expect(editButton(page2)).toBeVisible({ timeout: 10_000 });

  // Discarding tears the room down for every connected client, including a
  // mere viewer — `page` falls back to the Edit button too and re-enters,
  // clean, for the final test below.
  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
  await editButton(page).click();
  await expect(stopEditing(page)).toBeVisible({ timeout: 10_000 });
});

test('Stop Editing returns to Edit', async () => {
  await stopEditing(page).click();

  await expect(editButton(page)).toBeVisible({ timeout: 10_000 });
});
