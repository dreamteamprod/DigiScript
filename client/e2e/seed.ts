/**
 * REST seeding for states that are slow or fiddly to build through the UI (currently a
 * populated stage plan; the mic-allocation scenario seeds inline in its spec using `ShowApi`).
 * The UI is still what gets exercised and photographed, but the data behind it is created
 * here, and removed again afterwards so later specs see the database they expect.
 *
 * `idByName` matches the first item with that name, so seed only into a database where the
 * names it uses (Chair, Table, Castle Wall, Alice, Bob, ...) don't already exist.
 */
import type { APIRequestContext } from '@playwright/test';

import { UI_BASE, ADMIN_PASSWORD, ADMIN_USERNAME, apiLogin } from './helpers.js';

export class ShowApi {
  private constructor(
    private readonly request: APIRequestContext,
    private readonly token: string
  ) {}

  /** Log in as the E2E admin (using whichever password the calling spec currently expects). */
  static async asAdmin(
    request: APIRequestContext,
    password: string = ADMIN_PASSWORD
  ): Promise<ShowApi> {
    return new ShowApi(request, await apiLogin(request, ADMIN_USERNAME, password));
  }

  private get headers() {
    return { Authorization: `Bearer ${this.token}` };
  }

  async get<T>(path: string): Promise<T> {
    const res = await this.request.get(`${UI_BASE}/api/v1/${path}`, { headers: this.headers });
    if (!res.ok()) throw new Error(`GET ${path} failed: ${res.status()} ${await res.text()}`);
    return (await res.json()) as T;
  }

  async post(path: string, data: Record<string, unknown>): Promise<void> {
    const res = await this.request.post(`${UI_BASE}/api/v1/${path}`, {
      headers: this.headers,
      data,
    });
    if (!res.ok()) throw new Error(`POST ${path} failed: ${res.status()} ${await res.text()}`);
  }

  async patch(path: string, data: Record<string, unknown>): Promise<void> {
    const res = await this.request.patch(`${UI_BASE}/api/v1/${path}`, {
      headers: this.headers,
      data,
    });
    if (!res.ok()) throw new Error(`PATCH ${path} failed: ${res.status()} ${await res.text()}`);
  }

  /** Delete by id, which the API takes as a query argument. */
  async del(path: string, id: number): Promise<void> {
    const res = await this.request.delete(`${UI_BASE}/api/v1/${path}?id=${id}`, {
      headers: this.headers,
    });
    if (!res.ok()) throw new Error(`DELETE ${path} failed: ${res.status()} ${await res.text()}`);
  }

  /** Look up an item's id by name in a list endpoint's response (`{ [key]: [{ id, name }] }`). */
  async idByName(path: string, key: string, name: string, field = 'name'): Promise<number> {
    const body =
      await this.get<Record<string, Array<Record<string, unknown> & { id: number }>>>(path);
    const match = body[key].find((item) => item[field] === name);
    if (!match) throw new Error(`${name} not found in ${path}`);
    return match.id;
  }
}

export interface StagePlan {
  sceneIds: number[];
  propIds: number[];
  sceneryId?: number;
  crewIds: number[];
  propTypeId?: number;
  sceneryTypeId?: number;
}

/**
 * A small, fully-assigned stage plan on top of the show's existing Act 1 / Scene 1:
 *
 *            Scene 1   Scene 2   Scene 3
 *   Chair      SET       .        STRIKE      Alice SET, Bob STRIKE
 *   Castle     SET     STRIKE                 Bob SET, Alice STRIKE
 *   Table               SET      STRIKE       Bob SET, STRIKE unassigned
 *
 * Allocations are blocked while a live session is running, so seed before starting one.
 */
export async function seedStagePlan(api: ShowApi): Promise<StagePlan> {
  const plan: StagePlan = { sceneIds: [], propIds: [], crewIds: [] };
  try {
    await buildStagePlan(api, plan);
  } catch (error) {
    // Don't strand a half-built plan in the database for later specs. If the rollback fails
    // too, report both errors: the build failure is the one that explains what went wrong.
    try {
      await removeStagePlan(api, plan);
    } catch (cleanupError) {
      throw new AggregateError(
        [error, cleanupError],
        'seedStagePlan failed, and so did rolling it back (the first error is the build failure)',
        { cause: cleanupError }
      );
    }
    throw error;
  }
  return plan as StagePlan;
}

async function buildStagePlan(api: ShowApi, plan: StagePlan): Promise<void> {
  const actId = await api.idByName('show/act', 'acts', 'Act 1');
  const scene1 = await api.idByName('show/scene', 'scenes', 'Scene 1');
  await api.post('show/scene', { act_id: actId, name: 'Scene 2', previous_scene_id: scene1 });
  const scene2 = await api.idByName('show/scene', 'scenes', 'Scene 2');
  plan.sceneIds.push(scene2);
  await api.post('show/scene', { act_id: actId, name: 'Scene 3', previous_scene_id: scene2 });
  const scene3 = await api.idByName('show/scene', 'scenes', 'Scene 3');
  plan.sceneIds.push(scene3);

  await api.post('show/stage/props/types', { name: 'Furniture' });
  const propTypeId = await api.idByName('show/stage/props/types', 'prop_types', 'Furniture');
  Object.assign(plan, { propTypeId });
  await api.post('show/stage/scenery/types', { name: 'Backdrop' });
  const sceneryTypeId = await api.idByName('show/stage/scenery/types', 'scenery_types', 'Backdrop');
  Object.assign(plan, { sceneryTypeId });

  for (const name of ['Chair', 'Table']) {
    await api.post('show/stage/props', { name, prop_type_id: propTypeId });
    plan.propIds.push(await api.idByName('show/stage/props', 'props', name));
  }
  const [chair, table] = plan.propIds;
  await api.post('show/stage/scenery', { name: 'Castle Wall', scenery_type_id: sceneryTypeId });
  const wall = await api.idByName('show/stage/scenery', 'scenery', 'Castle Wall');
  Object.assign(plan, { sceneryId: wall });

  for (const [first, last] of [
    ['Alice', 'Brown'],
    ['Bob', 'Green'],
  ]) {
    await api.post('show/stage/crew', { firstName: first, lastName: last });
    plan.crewIds.push(await api.idByName('show/stage/crew', 'crew', first, 'first_name'));
  }
  const [alice, bob] = plan.crewIds;

  for (const scene of [scene1, scene2, scene3]) {
    await api.post('show/stage/props/allocations', { props_id: chair, scene_id: scene });
  }
  for (const scene of [scene2, scene3]) {
    await api.post('show/stage/props/allocations', { props_id: table, scene_id: scene });
  }
  for (const scene of [scene1, scene2]) {
    await api.post('show/stage/scenery/allocations', { scenery_id: wall, scene_id: scene });
  }

  const assign = (crew_id: number, scene_id: number, assignment_type: string, item: object) =>
    api.post('show/stage/crew/assignments', { crew_id, scene_id, assignment_type, ...item });
  await assign(alice, scene1, 'set', { prop_id: chair });
  await assign(bob, scene3, 'strike', { prop_id: chair });
  await assign(bob, scene1, 'set', { scenery_id: wall });
  await assign(alice, scene2, 'strike', { scenery_id: wall });
  await assign(bob, scene2, 'set', { prop_id: table });
}

/**
 * Remove everything `seedStagePlan` created (deleting items cascades their allocations).
 * Each delete is attempted independently, so one that fails (or whose item was never created)
 * doesn't strand the rest; the first failure is rethrown at the end.
 */
export async function removeStagePlan(api: ShowApi, plan: StagePlan): Promise<void> {
  const steps: Array<() => Promise<void>> = [
    ...plan.propIds.map((id) => () => api.del('show/stage/props', id)),
    ...(plan.sceneryId === undefined ? [] : [() => api.del('show/stage/scenery', plan.sceneryId!)]),
    ...plan.crewIds.map((id) => () => api.del('show/stage/crew', id)),
    ...(plan.propTypeId === undefined
      ? []
      : [() => api.del('show/stage/props/types', plan.propTypeId!)]),
    ...(plan.sceneryTypeId === undefined
      ? []
      : [() => api.del('show/stage/scenery/types', plan.sceneryTypeId!)]),
    ...plan.sceneIds
      .slice()
      .reverse()
      .map((id) => () => api.del('show/scene', id)),
  ];
  let firstError: unknown;
  for (const step of steps) {
    try {
      await step();
    } catch (error) {
      firstError ??= error;
    }
  }
  if (firstError) throw firstError;
}
