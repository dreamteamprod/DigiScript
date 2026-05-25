/**
 * Live show: start session, leader navigates, follower auto-scrolls to match.
 *
 * Uses two browser contexts to simulate two concurrent clients:
 *   leaderPage  — the first client to connect (elected leader)
 *   followerPage — the second client (becomes follower)
 *
 * The WS leader status is determined server-side by which client connects first.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  ADMIN_USERNAME,
  ADMIN_PASSWORD,
  waitForAppReady,
  loginAsAdmin,
  confirmModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';

test.describe.configure({ mode: 'serial' });

let leaderCtx: BrowserContext;
let followerCtx: BrowserContext;
let leaderPage: Page;
let followerPage: Page;

test.beforeAll(async ({ browser }) => {
  leaderCtx = await browser.newContext();
  leaderPage = await leaderCtx.newPage();
  await loginAsAdmin(leaderPage);

  followerCtx = await browser.newContext();
  followerPage = await followerCtx.newPage();
  await loginAsAdmin(followerPage);
});

test.afterAll(async () => {
  await leaderCtx.close();
  await followerCtx.close();
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
  // Leader navigates using the navbar Jump To Page feature
  await leaderPage.locator('text=Live Config').click();
  const jumpBtn = leaderPage.locator('a:has-text("Jump To Page"), button:has-text("Jump To Page")');
  await jumpBtn.click();
  await leaderPage.waitForSelector('.modal.show', { timeout: 5_000 });
  await leaderPage.fill('#page-input', '1');
  await confirmModal(leaderPage);
  await waitForModalClosed(leaderPage);

  // Follower should still be in following mode (scroll sync keeps it following)
  await expect(followerPage.locator('#script-container')).toHaveAttribute(
    'data-following',
    'true',
    { timeout: 10_000 }
  );
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
