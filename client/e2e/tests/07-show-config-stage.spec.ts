/**
 * Show Config — Stage tab: prop types, props, scenery types, scenery, crew types, crew.
 * Also covers the Stage Manager scene-navigation and allocation panel.
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
import { ShowApi, seedStagePlan, removeStagePlan, type StagePlan } from '../seed.js';

test.describe.configure({ mode: 'serial' });

registerRetryHooks();

let ctx: BrowserContext;
let page: Page;

test.beforeAll(async ({ browser }) => {
  ctx = await newContext(browser);
  page = await ctx.newPage();
  await loginAsAdmin(page);
  await page.goto(`${UI_BASE}/show-config/stage`);
  await waitForAppReady(page);
});

test.afterAll(async () => {
  await ctx.close();
});

// ── Props ──────────────────────────────────────────────────────────────────

test('Props tab is visible', async () => {
  await page.click('.nav-link:has-text("Props"), button[role="tab"]:has-text("Props")');
  await expect(
    page.locator('button:has-text("New Prop Type"), button:has-text("New Type")')
  ).toBeVisible();
  await docShot(page, 'config_show/stage_props_empty');
});

test('creates a prop type', async () => {
  await page.click('button:has-text("New Prop Type")');
  await waitForModal(page, 'Add New Prop Type');
  await page.fill('#new-ptype-name', 'Furniture');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Furniture")')).toBeVisible();
});

test('creates a prop', async () => {
  await page.click('button:has-text("New Props Item")');
  await waitForModal(page, 'Add New Prop');
  // Select the prop type we just created
  await page.selectOption('.modal.show #new-prop-type-sel', { label: 'Furniture' });
  await page.fill('.modal.show #new-prop-name', 'Chair');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Chair")')).toBeVisible();
});

// ── Scenery ───────────────────────────────────────────────────────────────

test('switches to Scenery tab', async () => {
  await page.click('.nav-link:has-text("Scenery"), button[role="tab"]:has-text("Scenery")');
  await expect(
    page.locator('button:has-text("New Scenery Type"), button:has-text("New Type")')
  ).toBeVisible();
  await docShot(page, 'config_show/stage_scenery_empty');
});

test('creates a scenery type', async () => {
  await page.click('button:has-text("New Scenery Type")');
  await waitForModal(page, 'Add New Scenery Type');
  await page.fill('#new-stype-name', 'Backdrop');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Backdrop")')).toBeVisible();
});

test('creates a scenery item', async () => {
  await page.click('button:has-text("New Scenery Item")');
  await waitForModal(page, 'Add New Scenery');
  // Select the scenery type we just created
  await page.selectOption('#new-scenery-type-sel', { label: 'Backdrop' });
  await page.fill('#new-scenery-name', 'Castle Wall');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("Castle Wall")')).toBeVisible();
});

test('deletes the scenery item', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Castle Wall")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Castle Wall")')).not.toBeVisible({ timeout: 5_000 });
});

test('deletes the scenery type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Backdrop")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Backdrop")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Crew ──────────────────────────────────────────────────────────────────

test('switches to Crew tab', async () => {
  await page.click('.nav-link:has-text("Crew"), button[role="tab"]:has-text("Crew")');
  await expect(page.locator('button:has-text("New Crew Member")')).toBeVisible();
  await docShot(page, 'config_show/stage_crew_empty');
});

test('creates a crew member', async () => {
  await page.click('button:has-text("New Crew Member")');
  await waitForModal(page, 'Add Crew Member');
  await page.fill('#new-first-name', 'John');
  await page.fill('#new-last-name', 'Smith');
  await confirmModal(page);
  await waitForModalClosed(page);
  await expect(page.locator('td:has-text("John")')).toBeVisible();
});

test('deletes the crew member', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("John")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("John")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Stage Manager ─────────────────────────────────────────────────────────

test('switches to Stage Manager tab and shows scene navigation', async () => {
  await page.click(
    '.nav-link:has-text("Stage Manager"), button[role="tab"]:has-text("Stage Manager")'
  );
  // Shows Prev/Next scene buttons
  await expect(page.locator('button:has-text("Next")').first()).toBeVisible();
  await docShot(page, 'config_show/stage_manager_empty');
});

test('adds a prop allocation to the current scene', async () => {
  await page.locator('button.btn-success:has-text("Add")').click();
  await page.click('.dropdown-item:has-text("Prop")');
  await waitForModal(page, 'Add Prop to Scene');
  await page.selectOption('#add-prop-select', { label: 'Chair' });
  await confirmModal(page);
  await waitForModalClosed(page);
  // Scope to active tab — Props tab panel is also mounted in DOM and contains a Chair cell
  await expect(page.locator('.tab-pane.active td:has-text("Chair")')).toBeVisible({
    timeout: 5_000,
  });
});

test('deletes the prop allocation', async () => {
  const propRow = page.locator('.tab-pane.active tr', {
    has: page.locator('td:has-text("Chair")'),
  });
  await propRow.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('.tab-pane.active td:has-text("Chair")')).not.toBeVisible({
    timeout: 5_000,
  });
});

// ── Prop cleanup ──────────────────────────────────────────────────────────

test('deletes the prop', async () => {
  await page.click('.nav-link:has-text("Props"), button[role="tab"]:has-text("Props")');
  const row = page.locator('tr', { has: page.locator('td:has-text("Chair")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Chair")')).not.toBeVisible({ timeout: 5_000 });
});

test('deletes the prop type', async () => {
  const row = page.locator('tr', { has: page.locator('td:has-text("Furniture")') });
  await row.locator('button:has-text("Delete")').click();
  await confirmDialog(page);
  await expect(page.locator('td:has-text("Furniture")')).not.toBeVisible({ timeout: 5_000 });
});

// ── Populated stage plan (also the source of the stage documentation screenshots) ──────────
//
// Seeded over the API (building this through the UI would repeat everything above; see
// seedStagePlan for the layout), then exercised and photographed through the UI, and removed
// again so later specs are unaffected.

let stagePlan: StagePlan;

test('seeds a populated stage plan', async ({ request }) => {
  stagePlan = await seedStagePlan(await ShowApi.asAdmin(request));
  expect(stagePlan.propIds).toHaveLength(2);
  expect(stagePlan.crewIds).toHaveLength(2);
  expect(stagePlan.sceneIds).toHaveLength(2);
  await page.goto(`${UI_BASE}/show-config/stage`);
  await waitForAppReady(page);
});

test('Crew, Scenery and Props lists show the seeded data', async () => {
  await expect(page.locator('.tab-pane.active td:has-text("Alice")')).toBeVisible();
  await docShot(page, 'config_show/stage_crew_with_data');

  await page.click('.nav-link:has-text("Scenery"), button[role="tab"]:has-text("Scenery")');
  await expect(page.locator('.tab-pane.active td:has-text("Castle Wall")')).toBeVisible();
  await docShot(page, 'config_show/stage_scenery_with_data');

  await page.click('.nav-link:has-text("Props"), button[role="tab"]:has-text("Props")');
  await expect(page.locator('.tab-pane.active td:has-text("Chair")')).toBeVisible();
  await docShot(page, 'config_show/stage_props_with_data');
});

test('Stage Manager shows the scene allocations and SET crew assignments', async () => {
  await page.click(
    '.nav-link:has-text("Stage Manager"), button[role="tab"]:has-text("Stage Manager")'
  );
  const active = page.locator('.tab-pane.active');
  await expect(active.locator('td:has-text("Chair")').first()).toBeVisible();
  await expect(active.locator('td:has-text("Castle Wall")').first()).toBeVisible();
  await docShot(page, 'config_show/stage_manager_with_allocations');

  // Both blocks start in Scene 1, so the SET card lists Chair (Alice) and Castle Wall (Bob).
  await active.locator('.section-card-header:has-text("SET")').click();
  await expect(active.locator('.crew-badge').first()).toBeVisible();
  await docShot(page, 'config_show/stage_manager_crew_assignments');
});

test('removing a boundary allocation warns about the crew assignments it would drop', async () => {
  const chairRow = page
    .locator('.tab-pane.active .section-card:has-text("Allocations") tr')
    .filter({ has: page.locator('td:has-text("Chair")') });
  await chairRow.locator('button:has-text("Delete")').click();
  await waitForModal(page, 'Crew assignments will be removed');
  await docShot(page, 'config_show/stage_allocation_warning');
  await page.locator('.modal.show .modal-footer button.btn-secondary').click();
  await waitForModalClosed(page);
  await expect(chairRow).toBeVisible();
});

test('Timeline shows the allocations, and a bar opens the crew side panel', async () => {
  await page.click('.nav-link:has-text("Timeline"), button[role="tab"]:has-text("Timeline")');
  const bar = page.locator('.tab-pane.active .allocation-bar').first();
  await expect(bar).toBeVisible({ timeout: 10_000 });
  await docShot(page, 'config_show/stage_timeline');

  await bar.click();
  await expect(page.locator('.side-panel.open')).toBeVisible();
  await docShot(page, 'config_show/stage_timeline_side_panel');
});

test('Crew timeline lists each crew member with their SET and STRIKE assignments', async () => {
  await page
    .locator('.tab-pane.active .nav-link')
    .filter({ hasText: /^Crew$/ })
    .click();
  await expect(page.locator('.tab-pane.active .assignment-bar').first()).toBeVisible({
    timeout: 10_000,
  });
  await docShot(page, 'config_show/stage_crew_timeline');
});

test('removes the seeded stage plan', async ({ request }) => {
  const api = await ShowApi.asAdmin(request);
  await removeStagePlan(api, stagePlan);
  const { crew } = await api.get<{ crew: Array<{ first_name: string }> }>('show/stage/crew');
  expect(crew.map((c) => c.first_name)).not.toContain('Alice');
  const { props } = await api.get<{ props: Array<{ name: string }> }>('show/stage/props');
  expect(props.map((p) => p.name)).not.toContain('Chair');
});
