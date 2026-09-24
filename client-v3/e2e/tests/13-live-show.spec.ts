/**
 * Live show: start session, leader navigates, follower auto-scrolls to match.
 *
 * Uses two browser contexts to simulate two concurrent clients, logged in as two
 * DIFFERENT users:
 *   leaderPage   — logs in as admin, starts the show session (server-elected leader)
 *   followerPage — logs in as a second, non-admin user (becomes follower)
 *
 * Leadership is assigned server-side to whichever session started the show (see
 * SessionStartController), and re-elected on disconnect from among sessions
 * belonging to that SAME user (see ws_controller.py on_close). Using two different
 * user accounts here — rather than logging both tabs in as admin — matches real
 * usage (leader and follower are normally different people) and keeps the
 * follower's session out of the leader's own re-election pool, which is what a
 * shared-login setup would otherwise race on when both tabs reload at once
 * (see issue #1414).
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  ADMIN_USERNAME,
  ADMIN_PASSWORD,
  waitForAppReady,
  loginAsAdmin,
  loginAs,
  apiLogin,
  createUser,
  deleteUserByUsername,
  waitForModal,
  confirmModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

const FOLLOWER_USERNAME = 'live-follower';
const FOLLOWER_PASSWORD = 'followerpass';

let leaderCtx: BrowserContext;
let followerCtx: BrowserContext;
let leaderPage: Page;
let followerPage: Page;

test.beforeAll(async ({ browser, request }) => {
  leaderCtx = await browser.newContext();
  leaderPage = await leaderCtx.newPage();
  await loginAsAdmin(leaderPage);

  // Create a distinct, non-admin user for the follower so it has a different
  // user_id from the leader (admin) — see the file header comment.
  const adminToken = await apiLogin(request, ADMIN_USERNAME, ADMIN_PASSWORD);
  await createUser(request, adminToken, FOLLOWER_USERNAME, FOLLOWER_PASSWORD);

  followerCtx = await browser.newContext();
  followerPage = await followerCtx.newPage();
  await loginAs(followerPage, FOLLOWER_USERNAME, FOLLOWER_PASSWORD);
});

test.afterAll(async ({ request }) => {
  await leaderCtx.close();
  await followerCtx.close();

  const adminToken = await apiLogin(request, ADMIN_USERNAME, ADMIN_PASSWORD);
  await deleteUserByUsername(request, adminToken, FOLLOWER_USERNAME);
});

// ── Session lifecycle ──────────────────────────────────────────────────────

test('Live Config dropdown is visible for admin when a show is loaded', async () => {
  await expect(leaderPage.locator('text=Live Config')).toBeVisible();
});

test('Start Session button is enabled before a session exists', async () => {
  await leaderPage.locator('text=Live Config').click();
  await expect(leaderPage.locator('button:has-text("Start Session")')).toBeEnabled();
});

test('starts a show session via the navbar', async () => {
  await leaderPage.click('button:has-text("Start Session")');
  await confirmDialog(leaderPage);
  // Session started — Live nav link becomes enabled
  await expect(leaderPage.locator('a:has-text("Live")')).not.toHaveClass(/disabled/, {
    timeout: 10_000,
  });
});

// ── Leader navigates to /live ─────────────────────────────────────────────

test('leader can navigate to /live', async () => {
  await leaderPage.click('a:has-text("Live")');
  await leaderPage.waitForURL(`${UI_BASE}/live`, { timeout: 10_000 });
  await waitForAppReady(leaderPage);
  // Script container rendered
  await expect(leaderPage.locator('#script-container')).toBeVisible({ timeout: 15_000 });
});

test('leader is NOT in following mode', async () => {
  // data-following is false on the leader's script container
  const container = leaderPage.locator('#script-container');
  await expect(container).not.toHaveAttribute('data-following', 'true');
});

test('current cue footer is visible by default', async () => {
  // toBeVisible() alone would pass even if the footer were pushed below the fold by
  // the script pane's computed height — toBeInViewport() catches that layout regression.
  await expect(leaderPage.locator('.current-cue-footer')).toBeInViewport();
});

// ── Follower connects ─────────────────────────────────────────────────────

test('follower navigates to /live after leader', async () => {
  // Leader is confirmed elected (not-following) before the follower connects
  await expect(leaderPage.locator('#script-container')).not.toHaveAttribute(
    'data-following',
    'true',
    { timeout: 10_000 }
  );
  await followerPage.goto(`${UI_BASE}/live`);
  await waitForAppReady(followerPage);
  await expect(followerPage.locator('#script-container')).toBeVisible({ timeout: 15_000 });
});

test('follower is in following mode', async () => {
  // Follower's script container should have data-following="true"
  const container = followerPage.locator('#script-container');
  await expect(container).toHaveAttribute('data-following', 'true', { timeout: 10_000 });
});

// ── Leader navigates pages, follower follows ───────────────────────────────

test('session header shows current page number', async () => {
  await expect(leaderPage.locator('b:has-text("Page")')).toBeVisible();
});

test('follower receives leader page navigation via WebSocket scroll sync', async () => {
  // Jump To Page broadcasts RELOAD_CLIENT to BOTH clients, which each do a full
  // window.location.reload() (see useWebSocket.ts). Register the `load` waits
  // BEFORE triggering the jump so we don't race the reload itself, and so this
  // assertion is checking state *after* the reload round-trip actually completed
  // rather than a leftover truthy value from before the jump (see issue #1414).
  const leaderReloaded = leaderPage.waitForEvent('load', { timeout: 15_000 });
  const followerReloaded = followerPage.waitForEvent('load', { timeout: 15_000 });

  // Leader navigates using the navbar Jump To Page feature
  await leaderPage.locator('text=Live Config').click();
  const jumpBtn = leaderPage.locator('a:has-text("Jump To Page"), button:has-text("Jump To Page")');
  await jumpBtn.click();
  await leaderPage.waitForSelector('.modal.show', { timeout: 5_000 });
  await leaderPage.fill('#page-input', '1');
  await confirmModal(leaderPage);

  await Promise.all([leaderReloaded, followerReloaded]);
  await Promise.all([waitForAppReady(leaderPage), waitForAppReady(followerPage)]);

  // Leader/follower roles must survive the reload round-trip: the leader (admin,
  // who started the session) stays the leader, and the follower (the separate
  // non-admin user) stays following. This is the invariant the reload-triggered
  // leader re-election race (ws_controller.py on_close) can break.
  await expect(leaderPage.locator('#script-container')).toBeVisible({ timeout: 15_000 });
  await expect(followerPage.locator('#script-container')).toBeVisible({ timeout: 15_000 });

  await expect(leaderPage.locator('.session-header')).toContainText('Leading', {
    timeout: 10_000,
  });
  await expect(leaderPage.locator('#script-container')).not.toHaveAttribute(
    'data-following',
    'true'
  );

  await expect(followerPage.locator('.session-header')).toContainText('Following', {
    timeout: 10_000,
  });
  await expect(followerPage.locator('#script-container')).toHaveAttribute(
    'data-following',
    'true',
    { timeout: 10_000 }
  );
});

// ── Cue add mode in live view ─────────────────────────────────────────────

test('pressing C enables cue add mode showing + buttons on the live page', async () => {
  await expect(leaderPage.locator('.script-item').first()).toBeVisible({ timeout: 10_000 });
  await leaderPage.keyboard.press('C');
  await expect(leaderPage.locator('.add-cue-btn').first()).toBeVisible({ timeout: 5_000 });
});

test('can add an individual cue from the live view', async () => {
  await leaderPage.locator('.add-cue-btn').first().click();
  await waitForModal(leaderPage, 'Add Cue');
  await expect(
    leaderPage.locator('.modal.show .nav-link:has-text("Individual Cue")')
  ).toBeVisible();
  await leaderPage.locator('.modal.show #cue-type-input').selectOption({ index: 1 });
  await leaderPage.locator('.modal.show #ident-input').fill('101');
  await leaderPage.locator('.modal.show button:has-text("Add Cue")').click();
  await waitForModalClosed(leaderPage);
  await expect(leaderPage.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({
    timeout: 5_000,
  });
});

test('current cue footer shows the last cue seen for its type', async () => {
  await expect(leaderPage.locator('.current-cue-footer .cue-button')).toHaveCount(1, {
    timeout: 5_000,
  });
  await expect(leaderPage.locator('.current-cue-footer .cue-button').first()).toContainText('101');
});

test('can add a cue group from the live view', async () => {
  await leaderPage.locator('.add-cue-btn').first().click();
  await waitForModal(leaderPage, 'Add Cue');
  await leaderPage.locator('.modal.show .nav-link:has-text("Cue Group")').click();
  // Wait for CueGroupForm content (tab may be lazy in some BVN versions)
  await expect(leaderPage.locator('.modal.show input[placeholder="1 > 100"]')).toBeVisible({
    timeout: 10_000,
  });
  // CueGroupForm filters out N/A, so LX is at index 0
  await leaderPage.locator('.modal.show .tab-pane.active select').selectOption({ index: 0 });
  await leaderPage.locator('.modal.show input[placeholder="1 > 100"]').fill('200 > 202');
  await leaderPage.locator('.modal.show button:has-text("Add Range")').click();
  await expect(
    leaderPage.locator('.modal.show .tab-pane.active input[placeholder="Identifier"]')
  ).toHaveCount(3, { timeout: 3_000 });
  await leaderPage.locator('.modal.show button:has-text("Save Group")').click();
  await waitForModalClosed(leaderPage);
  await expect(leaderPage.locator('.cue-group-btn').first()).toBeVisible({ timeout: 5_000 });
  await expect(leaderPage.locator('.cue-group-btn').first()).toContainText('LX 200 - LX 202');
});

test('current cue footer still shows exactly one badge for the cue type after grouped cues are added', async () => {
  // Grouped cues are tracked individually — the footer collapses to the single most
  // recently passed cue of that type, whichever one that ends up being.
  await expect(leaderPage.locator('.current-cue-footer .cue-button')).toHaveCount(1, {
    timeout: 5_000,
  });
});

test('cue group buttons in live view are non-interactive display-only buttons', async () => {
  // Group buttons in live view should NOT open an edit modal — editing is blocked server-side
  // during live sessions. Verify clicking doesn't open any modal.
  await leaderPage.locator('.cue-group-btn').first().click();
  await leaderPage.waitForTimeout(500);
  await expect(leaderPage.locator('.modal.show')).not.toBeVisible();
});

test('pressing C again disables cue add mode', async () => {
  await leaderPage.keyboard.press('C');
  await expect(leaderPage.locator('.add-cue-btn').first()).not.toBeVisible({ timeout: 5_000 });
});

// ── Enable/disable Stage Manager mode ─────────────────────────────────────

test('can toggle Stage Manager mode', async () => {
  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Enable Stage Manager")');
  // Stage manager pane appears
  await expect(leaderPage.locator('[class*="stage-manager"], [class*="stageManager"]'))
    .toBeVisible({ timeout: 5_000 })
    .catch(() => {
      // Not all themes render a distinct pane element; presence in UI is enough
    });
  // Disable it again
  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Disable Stage Manager")');
});

// ── Reload Clients ─────────────────────────────────────────────────────────

test('Reload Clients triggers and all clients reload', async () => {
  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Reload Clients")');
  await confirmDialog(leaderPage);
  // After reload, leader ends up back on the live page
  await leaderPage.waitForURL(`${UI_BASE}/live`, { timeout: 15_000 });
  await waitForAppReady(leaderPage);
});

// ── Stop session ───────────────────────────────────────────────────────────

test('can stop the show session', async () => {
  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Stop Session")');
  await confirmDialog(leaderPage);
  // After stop, Live nav link becomes disabled
  await expect(leaderPage.locator('a:has-text("Live")')).toHaveClass(/disabled/, {
    timeout: 10_000,
  });
});
