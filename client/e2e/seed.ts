/**
 * REST seeding for states that are slow or fiddly to build through the UI (a populated
 * stage plan, a branched revision history, ...). Used by the documentation screenshot
 * scenarios: the UI is still what gets photographed, but the data behind it is created
 * here, and removed again afterwards so later specs see the database they expect.
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
  sceneryId: number;
  crewIds: number[];
  propTypeId: number;
  sceneryTypeId: number;
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
  const actId = await api.idByName('show/act', 'acts', 'Act 1');
  const scene1 = await api.idByName('show/scene', 'scenes', 'Scene 1');
  await api.post('show/scene', { act_id: actId, name: 'Scene 2', previous_scene_id: scene1 });
  const scene2 = await api.idByName('show/scene', 'scenes', 'Scene 2');
  await api.post('show/scene', { act_id: actId, name: 'Scene 3', previous_scene_id: scene2 });
  const scene3 = await api.idByName('show/scene', 'scenes', 'Scene 3');

  await api.post('show/stage/props/types', { name: 'Furniture' });
  const propTypeId = await api.idByName('show/stage/props/types', 'prop_types', 'Furniture');
  await api.post('show/stage/scenery/types', { name: 'Backdrop' });
  const sceneryTypeId = await api.idByName('show/stage/scenery/types', 'scenery_types', 'Backdrop');

  const propIds: number[] = [];
  for (const name of ['Chair', 'Table']) {
    await api.post('show/stage/props', { name, prop_type_id: propTypeId });
    propIds.push(await api.idByName('show/stage/props', 'props', name));
  }
  const [chair, table] = propIds;
  await api.post('show/stage/scenery', { name: 'Castle Wall', scenery_type_id: sceneryTypeId });
  const wall = await api.idByName('show/stage/scenery', 'scenery', 'Castle Wall');

  const crewIds: number[] = [];
  for (const [first, last] of [
    ['Alice', 'Brown'],
    ['Bob', 'Green'],
  ]) {
    await api.post('show/stage/crew', { firstName: first, lastName: last });
    crewIds.push(await api.idByName('show/stage/crew', 'crew', first, 'first_name'));
  }
  const [alice, bob] = crewIds;

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

  return {
    sceneIds: [scene2, scene3],
    propIds,
    sceneryId: wall,
    crewIds,
    propTypeId,
    sceneryTypeId,
  };
}

/** Remove everything `seedStagePlan` created (deleting items cascades their allocations). */
export async function removeStagePlan(api: ShowApi, plan: StagePlan): Promise<void> {
  for (const id of plan.propIds) await api.del('show/stage/props', id);
  await api.del('show/stage/scenery', plan.sceneryId);
  for (const id of plan.crewIds) await api.del('show/stage/crew', id);
  await api.del('show/stage/props/types', plan.propTypeId);
  await api.del('show/stage/scenery/types', plan.sceneryTypeId);
  for (const id of plan.sceneIds.slice().reverse()) await api.del('show/scene', id);
}
