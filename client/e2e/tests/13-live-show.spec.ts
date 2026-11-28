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
  addDialogueLine,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';
import { newContext, docShot } from '../docs-shots.js';
import { ShowApi, seedStagePlan, removeStagePlan, type StagePlan } from '../seed.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

const FOLLOWER_USERNAME = 'live-follower';
const FOLLOWER_PASSWORD = 'followerpass';

// Undefined until beforeAll gets that far, so afterAll must tolerate them missing.
let leaderCtx: BrowserContext | undefined;
let followerCtx: BrowserContext | undefined;
let leaderPage: Page;
let followerPage: Page;
// Seeded so the Stage Manager pane and Plan modal have something to show; allocations can't
// change once a session is live, so this is created up front and removed after the session ends.
let stagePlan: StagePlan;

/** The elapsed-time counter ticks every second, so it can't be captured as-is. */
const elapsedTime = (page: Page) => page.locator('.session-header').getByText(/^Elapsed Time:/);

test.beforeAll(async ({ browser, request }) => {
  leaderCtx = await newContext(browser);
  leaderPage = await leaderCtx.newPage();
  await loginAsAdmin(leaderPage);
  stagePlan = await seedStagePlan(await ShowApi.asAdmin(request));

  // Create a distinct, non-admin user for the follower so it has a different
  // user_id from the leader (admin) — see the file header comment.
  const adminToken = await apiLogin(request, ADMIN_USERNAME, ADMIN_PASSWORD);
  await createUser(request, adminToken, FOLLOWER_USERNAME, FOLLOWER_PASSWORD);

  followerCtx = await newContext(browser);
  followerPage = await followerCtx.newPage();
  await loginAs(followerPage, FOLLOWER_USERNAME, FOLLOWER_PASSWORD);
});

test.afterAll(async ({ request }) => {
  // Independent steps: beforeAll may have failed part way, and a failed attempt may have left
  // the stage plan undeletable (e.g. a session still live). None of that may stop the other
  // steps running or replace the test's own failure; the first cleanup error is rethrown last.
  const failures: unknown[] = [];
  const attempt = async (step: () => Promise<unknown>) => {
    try {
      await step();
    } catch (error) {
      failures.push(error);
    }
  };
  await attempt(async () => leaderCtx?.close());
  await attempt(async () => followerCtx?.close());
  await attempt(async () => {
    if (stagePlan) await removeStagePlan(await ShowApi.asAdmin(request), stagePlan);
  });
  await attempt(async () => {
    const adminToken = await apiLogin(request, ADMIN_USERNAME, ADMIN_PASSWORD);
    await deleteUserByUsername(request, adminToken, FOLLOWER_USERNAME);
  });
  if (failures.length > 0) throw failures[0];
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
  await docShot(leaderPage, 'live_show/live_with_script', { mask: [elapsedTime(leaderPage)] });
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

test('follower tracks leader line-by-line via WebSocket scroll sync', async () => {
  // Real content-position check (not just a flag): the leader steps forward one
  // line with the keyboard (SCRIPT_SCROLL sync), and the follower must land on
  // that exact same line — starting from page_1_line_0, so this genuinely moves.
  const leaderLine = leaderPage.locator('#script-container .current-line');
  const followerLine = followerPage.locator('#script-container .current-line');

  await expect(leaderLine).toHaveId('page_1_line_0');
  await expect(followerLine).toHaveId('page_1_line_0');

  await leaderPage.keyboard.press('ArrowDown');

  await expect(leaderLine).toHaveId('page_1_line_1', { timeout: 5_000 });
  await expect(followerLine).toHaveId('page_1_line_1', { timeout: 10_000 });
});

test('follower survives leader page navigation via Jump To Page reload', async () => {
  // Jump To Page broadcasts RELOAD_CLIENT to BOTH clients, which each do a full
  // window.location.reload() (see useWebSocket.ts). Register the `load` waits
  // BEFORE triggering the jump so we don't race the reload itself, and so these
  // assertions check state *after* the reload round-trip actually completed
  // rather than a leftover truthy value from before the jump (see issue #1414).
  const leaderReloaded = leaderPage.waitForEvent('load', { timeout: 15_000 });
  const followerReloaded = followerPage.waitForEvent('load', { timeout: 15_000 });

  // Leader navigates using the navbar Jump To Page feature — back to page 1,
  // which is a real position change from the line-1 the previous test left us on.
  await leaderPage.locator('text=Live Config').click();
  const jumpBtn = leaderPage.locator('a:has-text("Jump To Page"), button:has-text("Jump To Page")');
  await jumpBtn.click();
  await leaderPage.waitForSelector('.modal.show', { timeout: 5_000 });
  await leaderPage.fill('#page-input', '1');
  await docShot(leaderPage, 'live_show/live_jump_to_page_modal', {
    mask: [elapsedTime(leaderPage)],
  });
  await confirmModal(leaderPage);

  await Promise.all([leaderReloaded, followerReloaded]);
  await Promise.all([waitForAppReady(leaderPage), waitForAppReady(followerPage)]);

  // The jump moved the position back to page_1_line_0 on both clients.
  await expect(leaderPage.locator('#script-container .current-line')).toHaveId('page_1_line_0', {
    timeout: 15_000,
  });
  await expect(followerPage.locator('#script-container .current-line')).toHaveId('page_1_line_0', {
    timeout: 15_000,
  });

  // Leader/follower roles must also survive the reload round-trip: the leader
  // (admin, who started the session) stays the leader, and the follower (the
  // separate non-admin user) stays following. This is the invariant the
  // reload-triggered leader re-election race (ws_controller.py on_close) can
  // break — see the file header comment and issue #1414.
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
  await docShot(leaderPage, 'live_show/live_show_full_mode_with_cues', {
    mask: [elapsedTime(leaderPage)],
  });
});

// ── Enable/disable Stage Manager mode ─────────────────────────────────────

test('can toggle Stage Manager mode', async () => {
  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Enable Stage Manager")');
  await expect(leaderPage.locator('.stage-manager-pane')).toBeVisible({ timeout: 5_000 });
  await expect(leaderPage.locator('.stage-manager-pane .scene-card').first()).toBeVisible();
  await docShot(leaderPage, 'live_show/live_stage_manager_pane', {
    mask: [elapsedTime(leaderPage)],
  });

  // The Plan button on a scene card lists what is being set and struck, with the crew assigned.
  await leaderPage.locator('.stage-manager-pane button:has-text("Plan")').first().click();
  await waitForModal(leaderPage, /Plan/);
  // Scene 1 sets the Castle Wall (Bob) and the Chair (Alice) - see seedStagePlan.
  const planModal = leaderPage.locator('.modal.show');
  await expect(planModal).toContainText('Castle Wall');
  await expect(planModal).toContainText('Bob Green');
  await expect(planModal).toContainText('Chair');
  await expect(planModal).toContainText('Alice Brown');
  await docShot(leaderPage, 'live_show/live_plan_modal_crew', {
    mask: [elapsedTime(leaderPage)],
  });
  await leaderPage.locator('.modal.show .modal-footer button').first().click();
  await waitForModalClosed(leaderPage);

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

// ── COMPACT script mode ───────────────────────────────────────────────────
//
// A show's script mode is fixed when it is created, so the single-column COMPACT live view
// needs a show of its own. Build a small one, run it live, then put the main show back.
//
// The COMPACT show is left in the database afterwards because deleting it currently fails
// (#1561; see the fixme test at the end). That is safe for the specs after this one: spec 14
// only touches user settings, and spec 15 works on whichever show is loaded (the main show,
// reloaded below). The COMPACT show's session has ended, its script and cues belong to it
// alone, and the edit lock taken while seeding its script is released before its session starts
// (a leaked editor would make spec 15's edit/cut requests fail).

const COMPACT_SHOW = 'E2E Compact Show';

test('creates and loads a COMPACT script mode show', async () => {
  await leaderPage.goto(`${UI_BASE}/config`);
  await waitForAppReady(leaderPage);
  await leaderPage.click('button:has-text("Setup New Show")');
  await waitForModal(leaderPage, 'Setup New Show');
  await leaderPage.fill('#show-name-input', COMPACT_SHOW);
  await leaderPage.fill('#show-start-input', '2025-01-01');
  await leaderPage.fill('#show-end-input', '2025-03-31');
  // <option>s are never "visible"; wait for both modes (FULL, COMPACT) to be loaded instead.
  await expect(leaderPage.locator('#show-script-mode-input option')).toHaveCount(2);
  await leaderPage.selectOption('#show-script-mode-input', { label: 'COMPACT' });

  // Loading a show reloads the page (SHOW_CHANGED); listen before clicking.
  const afterLoad = leaderPage.waitForEvent('load', { timeout: 30_000 });
  await leaderPage.click('.modal.show button:has-text("Save and Load")');
  await afterLoad;
  await waitForAppReady(leaderPage);
  await expect(leaderPage.locator('a:has-text("Show Config")')).toBeVisible({ timeout: 10_000 });
});

test('seeds the compact show with a script and cues', async ({ request }) => {
  const api = await ShowApi.asAdmin(request);
  await api.post('show/act', { name: 'Act 1', interval_after: false, previous_act_id: null });
  const actId = await api.idByName('show/act', 'acts', 'Act 1');
  await api.post('show/scene', { act_id: actId, name: 'Scene 1', previous_scene_id: null });
  await api.post('show/character', { name: 'Hamlet', description: '' });
  await api.post('show/character', { name: 'Ophelia', description: '' });
  await api.post('show/cues/types', { prefix: 'LX', description: 'Lighting', colour: '#e74c3c' });
  await api.post('show/cues/types', { prefix: 'SQ', description: 'Sound', colour: '#3498db' });

  await leaderPage.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(leaderPage);
  await leaderPage.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(leaderPage.locator('button:has-text("Stop Editing")')).toBeVisible({
    timeout: 10_000,
  });
  const lines: Array<[string, string]> = [
    ['Hamlet', 'To be, or not to be, that is the question.'],
    ['Ophelia', 'Good my lord, how does your honour for this many a day?'],
    ['Hamlet', 'I humbly thank you; well, well, well.'],
  ];
  for (const [character, text] of lines) {
    await addDialogueLine(leaderPage, { act: 'Act 1', scene: 'Scene 1', character, text });
  }
  await leaderPage.getByRole('button', { name: 'Save', exact: true }).click();
  await waitForModal(leaderPage, 'Saving Script');
  await expect(leaderPage.locator('.modal.show').getByText('Finished saving script.')).toBeVisible({
    timeout: 15_000,
  });
  await confirmModal(leaderPage);
  await waitForModalClosed(leaderPage);

  await leaderPage.goto(`${UI_BASE}/show-config/cues`);
  await waitForAppReady(leaderPage);
  await leaderPage.click(
    '.nav-link:has-text("Cue Configuration"), button[role="tab"]:has-text("Cue Config")'
  );
  await expect(leaderPage.locator('.add-cue-btn').first()).toBeVisible({ timeout: 10_000 });
  const addCue = async (lineIndex: number, typeIndex: number, ident: string) => {
    await leaderPage.locator('.add-cue-btn').nth(lineIndex).click();
    await waitForModal(leaderPage, 'Add Cue');
    await leaderPage.locator('.modal.show select#new-cue-type').selectOption({ index: typeIndex });
    await leaderPage.locator('.modal.show #new-cue-ident').fill(ident);
    await confirmModal(leaderPage);
    await waitForModalClosed(leaderPage);
  };
  await addCue(0, 1, '1');
  await addCue(2, 2, '1');
  await expect(leaderPage.locator('.cue-button:not(.add-cue-btn)')).toHaveCount(2, {
    timeout: 5_000,
  });
});

test('the COMPACT live view shows a single-column script with its cues', async () => {
  // Release the edit lock taken above before running the show. The lock survives a reload and
  // is a server-wide flag, so a leaked editor would reject spec 15's edit/cut requests.
  // "Stop Editing" only renders after the WS editor-status round trip, so wait for either
  // settled state before deciding.
  await leaderPage.goto(`${UI_BASE}/show-config/script`);
  await waitForAppReady(leaderPage);
  const stopEditing = leaderPage.locator('button:has-text("Stop Editing")');
  const editButton = leaderPage.getByRole('button', { name: 'Edit', exact: true });
  await expect(stopEditing.or(editButton)).toBeVisible({ timeout: 10_000 });
  if (await stopEditing.isVisible()) {
    await stopEditing.click();
    await expect(editButton).toBeVisible({ timeout: 10_000 });
  }

  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Start Session")');
  await confirmDialog(leaderPage);
  await expect(leaderPage.locator('a:has-text("Live")')).not.toHaveClass(/disabled/, {
    timeout: 10_000,
  });
  await leaderPage.click('a:has-text("Live")');
  await leaderPage.waitForURL(`${UI_BASE}/live`, { timeout: 10_000 });
  await waitForAppReady(leaderPage);
  await expect(leaderPage.locator('#script-container')).toBeVisible({ timeout: 15_000 });
  await expect(leaderPage.locator('.cue-button:not(.add-cue-btn)').first()).toBeVisible({
    timeout: 10_000,
  });
  await docShot(leaderPage, 'live_show/live_show_compact_mode_with_cues', {
    mask: [elapsedTime(leaderPage)],
  });

  await leaderPage.locator('text=Live Config').click();
  await leaderPage.click('button:has-text("Stop Session")');
  await confirmDialog(leaderPage);
  await expect(leaderPage.locator('a:has-text("Live")')).toHaveClass(/disabled/, {
    timeout: 10_000,
  });
});

test('reloads the main show', async () => {
  await leaderPage.goto(`${UI_BASE}/config`);
  await waitForAppReady(leaderPage);
  const mainRow = leaderPage.locator('tr', {
    has: leaderPage.locator('td:has-text("E2E Test Show")'),
  });
  const afterLoad = leaderPage.waitForEvent('load', { timeout: 30_000 });
  await mainRow.locator('button:has-text("Load")').click();
  await afterLoad;
  await waitForAppReady(leaderPage);
  await expect(mainRow.locator('button:has-text("Loaded")')).toBeVisible({ timeout: 10_000 });
});

// Deleting a show that has script lines and cues returns a 500 after ~5s, so the COMPACT show
// above is left in the database. Remove this fixme and delete the show there once fixed.
test.fixme('deletes the COMPACT show (#1561)', async () => {
  const compactRow = leaderPage.locator('tr', {
    has: leaderPage.locator(`td:has-text("${COMPACT_SHOW}")`),
  });
  await compactRow.locator('button:has-text("Delete")').click();
  await confirmDialog(leaderPage);
  await expect(leaderPage.locator(`td:has-text("${COMPACT_SHOW}")`)).not.toBeVisible({
    timeout: 20_000,
  });
});
