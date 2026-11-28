/**
 * Show Config — Mics tab: microphone CRUD, allocations view, timeline view.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  UI_BASE,
  loginAsAdmin,
  waitForAppReady,
  waitForModal,
  confirmModal,
  waitForModalClosed,
  confirmDialog,
} from '../helpers.js';
import { registerRetryHooks } from '../db-snapshot.js';
import { newContext, docShot } from '../docs-shots.js';
import { ShowApi } from '../seed.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await newContext(browser);
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/mics`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Mics ──────────────────────────────────────────────────────────────────

test('Mics tab shows New Microphone button', async () => {
  await expect(page.locator('button:has-text("New Microphone")')).toBeVisible();
  await docShot(page, 'config_show/mics_empty');
});

test('creates a microphone', async () => {
  await page.click('button:has-text("New Microphone")');
  await waitForModal(page, /Microphone/);
  await page.fill('.modal.show input[type="text"]', 'Mic 1');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 1")')).toBeVisible();
});

test('creates a second microphone', async () => {
  await page.click('button:has-text("New Microphone")');
  await waitForModal(page, /Microphone/);
  await page.fill('.modal.show input[type="text"]', 'Mic 2');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 2")')).toBeVisible();
  await docShot(page, 'config_show/mics_with_data');
});

test('edits a microphone', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Mic 2")') });
  await row.locator('button:has-text("Edit")').click();
  await waitForModal(page, /Edit.*Mic|Microphone/);
  const input = page.locator('.modal.show input[type="text"]').first();
  await input.fill('Mic 2 (Edited)');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Mic 2 (Edited)")')).toBeVisible();
});

test('deletes a microphone', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Mic 2 (Edited)")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Mic 2 (Edited)")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Allocations ───────────────────────────────────────────────────────────

test('switches to Allocations sub-tab', async () => {
  await page.click('.nav-link:has-text("Allocations"), button[role="tab"]:has-text("Allocations")');
  // Allocations table container is always visible on this sub-tab
  await expect(page.locator('#allocations-table')).toBeVisible({ timeout: 10_000 });
  await docShot(page, 'config_show/mics_allocations');
});

test('switches to edit mode and back', async () => {
  // Component may initialise in edit mode — ensure we start in view mode.
  // Use :visible to avoid strict-mode violation from Cancel buttons inside hidden BVN modals.
  if ((await page.locator('button:has-text("View"):visible').count()) > 0) {
    await page.locator('button:has-text("View"):visible').click();
  }
  // Scope to active panel — the Mics tab (not active) also has row-level Edit buttons in the DOM
  const editBtn = page.locator('.tab-pane.active button:has-text("Edit")');
  await expect(editBtn).toBeVisible({ timeout: 5_000 });
  await editBtn.click();
  await expect(page.locator('.tab-pane.active button:has-text("Save")')).toBeVisible();
  await page
    .locator('.tab-pane.active')
    .locator('button:has-text("View"), button:has-text("Cancel")')
    .click();
});

test('saves a mic allocation', async () => {
  // Re-navigate so MicAllocations re-mounts with Mic 1 already in the store.
  // internalState is initialised in onMounted; the first navigation (beforeAll) ran before any
  // mics existed, so the component would have set up an empty internalState and toggleAllocation
  // would silently no-op. A fresh navigation after mic creation fixes this.
  await page.goto(`${UI_BASE}/show-config/mics`);
  await waitForAppReady(page);
  await page.click('.nav-link:has-text("Allocations"), button[role="tab"]:has-text("Allocations")');
  await expect(page.locator('#allocations-table')).toBeVisible({ timeout: 10_000 });

  // MicAllocations starts with editMode = true; #mic-input is immediately visible
  await expect(page.locator('#mic-input')).toBeVisible({ timeout: 5_000 });
  await page.selectOption('#mic-input', { label: 'Mic 1' });
  await docShot(page, 'config_show/mics_allocations_with_mic_selected');

  await page
    .locator('#allocations-table tbody tr')
    .first()
    .locator('td')
    .nth(1)
    .locator('button')
    .click();
  await docShot(page, 'config_show/mics_allocations_editing');
  await page.locator('.tab-pane.active button:has-text("Save")').click();

  await page
    .locator('.tab-pane.active')
    .locator('button:has-text("View"), button:has-text("Cancel")')
    .click();
  await expect(page.locator('.tab-pane.active button:has-text("Edit")')).toBeVisible({
    timeout: 5_000,
  });

  await expect(page.locator('#allocations-table .allocation-cell').first()).toBeVisible({
    timeout: 5_000,
  });
  await docShot(page, 'config_show/mics_allocations_saved');
});

// ── Populated allocations (also the source of the timeline/density/availability screenshots) ──
//
// Seeded over the API, removed again at the end of the spec. Mic 1 already has a saved
// allocation from the test above; this adds scenes 2 (same act) and 3 (next act) so that
// Mic 1 changes character at both an in-act and an across-interval boundary (the orange and
// blue conflict highlights), and gives Mic 2 a run of its own.

const micPlan: {
  actId?: number;
  sceneIds: number[];
  micId?: number;
} = { sceneIds: [] };

test('seeds allocations across three scenes with changeover conflicts', async ({ request }) => {
  const api = await ShowApi.asAdmin(request);

  const act1 = await api.idByName('show/act', 'acts', 'Act 1');
  const scene1 = await api.idByName('show/scene', 'scenes', 'Scene 1');
  await api.post('show/scene', { act_id: act1, name: 'Scene 2', previous_scene_id: scene1 });
  const scene2 = await api.idByName('show/scene', 'scenes', 'Scene 2');
  micPlan.sceneIds.push(scene2);
  await api.post('show/act', { name: 'Act 2', interval_after: false, previous_act_id: act1 });
  const act2 = await api.idByName('show/act', 'acts', 'Act 2');
  micPlan.actId = act2;
  await api.post('show/scene', { act_id: act2, name: 'Scene 3', previous_scene_id: null });
  const scene3 = await api.idByName('show/scene', 'scenes', 'Scene 3');
  micPlan.sceneIds.push(scene3);

  await api.post('show/microphones', { name: 'Mic 2', description: '' });
  const mic1 = await api.idByName('show/microphones', 'microphones', 'Mic 1');
  const mic2 = await api.idByName('show/microphones', 'microphones', 'Mic 2');
  micPlan.micId = mic2;

  const { characters } = await api.get<{ characters: Array<{ id: number }> }>('show/character');
  expect(characters.length).toBeGreaterThanOrEqual(2);
  const [charA, charB] = characters.map((c) => c.id);
  await api.patch('show/microphones/allocations', {
    [mic1]: { [scene1]: charA, [scene2]: charB, [scene3]: charA },
    [mic2]: { [scene1]: charB, [scene2]: charA, [scene3]: charB },
  });

  await page.goto(`${UI_BASE}/show-config/mics`);
  await waitForAppReady(page);
  await page.click('.nav-link:has-text("Allocations"), button[role="tab"]:has-text("Allocations")');
  // The tab opens in edit mode; the conflict highlights are part of the read-only view.
  await page.locator('.tab-pane.active button:has-text("View"):visible').click();
  await expect(page.locator('#allocations-table .allocation-cell').first()).toBeVisible({
    timeout: 10_000,
  });
});

test('conflicting changeovers are highlighted in the allocations view', async () => {
  await expect(page.locator('#allocations-table [class*="conflict"]').first()).toBeVisible({
    timeout: 5_000,
  });
  await docShot(page, 'config_show/mics_conflict_highlighting');
});

// ── Timeline ─────────────────────────────────────────────────────────────

test('switches to Timeline sub-tab', async () => {
  await page.click('.nav-link:has-text("Timeline"), button[role="tab"]:has-text("Timeline")');
  await expect(page.locator('button:has-text("By Microphone")')).toBeVisible({ timeout: 10_000 });
  await docShot(page, 'config_show/mics_timeline');
});

// ── Density ──────────────────────────────────────────────────────────────

test('switches to Density sub-tab', async () => {
  await page.click('.nav-link:has-text("Density"), button[role="tab"]:has-text("Density")');
  await expect(page.locator('h5:has-text("Scene Microphone Density")')).toBeVisible({
    timeout: 10_000,
  });
  await docShot(page, 'config_show/mics_density_heatmap');
});

// ── Availability ──────────────────────────────────────────────────────────

test('switches to Availability sub-tab', async () => {
  await page.click(
    '.nav-link:has-text("Availability"), button[role="tab"]:has-text("Availability")'
  );
  await expect(page.locator('h5:has-text("Microphone Resource Availability")')).toBeVisible({
    timeout: 10_000,
  });
  await docShot(page, 'config_show/mics_availability');
});

test('removes the seeded scenes and microphone', async ({ request }) => {
  const api = await ShowApi.asAdmin(request);
  // Independent attempts so one failure doesn't strand the rest; the first error is rethrown.
  const results = await Promise.allSettled([
    ...(micPlan.micId === undefined ? [] : [api.del('show/microphones', micPlan.micId)]),
    ...micPlan.sceneIds.map((id) => api.del('show/scene', id)),
  ]);
  if (micPlan.actId !== undefined) {
    results.push(...(await Promise.allSettled([api.del('show/act', micPlan.actId)])));
  }
  const failed = results.find((r): r is PromiseRejectedResult => r.status === 'rejected');
  if (failed) throw failed.reason;
  const { microphones } = await api.get<{ microphones: Array<{ name: string }> }>(
    'show/microphones'
  );
  expect(microphones.map((m) => m.name)).not.toContain('Mic 2');
});
