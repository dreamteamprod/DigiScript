import type { Act, Scene } from '@/types/api/show';

/** Shared `Act`/`Scene` builders — used identically by `ScriptLineEditor.test.ts`
 * and `CollabScriptLineEditor.test.ts` (and any other script-editor test that
 * needs a plausible `actOptions`/`sceneOptions` source). */
export function act(id: number, overrides: Partial<Act> = {}): Act {
  return {
    id,
    show_id: 1,
    name: `Act ${id}`,
    interval_after: false,
    first_scene: null,
    next_act: null,
    previous_act: null,
    ...overrides,
  };
}

export function scene(id: number, actId: number, overrides: Partial<Scene> = {}): Scene {
  return {
    id,
    show_id: 1,
    act: actId,
    name: `Scene ${id}`,
    next_scene: null,
    previous_scene: null,
    ...overrides,
  };
}
