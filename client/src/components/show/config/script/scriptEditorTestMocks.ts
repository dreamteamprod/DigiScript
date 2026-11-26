import { vi } from 'vitest';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useWebSocketStore } from '@/stores/websocket';

/**
 * The store setup shared by `ScriptEditor.test.ts` and `CollabScriptEditor.test.ts`'s
 * own `beforeEach` — the act/scene/character list loads, the stage-direction-styles/
 * cuts/script-config-status/load-script-page fetches, and this session's own
 * websocket identity. Each test file still sets its own editor-status/show-settings
 * fields on top (the two editors disagree on what "can edit" even means), so this is
 * only the genuinely identical part.
 */
export function mockCommonScriptStores(): void {
  useWebSocketStore().internalUUID = 'me';
  for (const m of [
    'getActList',
    'getSceneList',
    'getCharacterList',
    'getCharacterGroupList',
  ] as const) {
    vi.spyOn(useShowStore(), m).mockResolvedValue();
  }
  vi.spyOn(useScriptStore(), 'getStageDirectionStyles').mockResolvedValue();
  vi.spyOn(useScriptStore(), 'getCuts').mockResolvedValue();
  vi.spyOn(useScriptStore(), 'loadScriptPage').mockResolvedValue();
  vi.spyOn(useScriptConfigStore(), 'getScriptConfigStatus').mockResolvedValue();
}
