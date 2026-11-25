import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import ScriptLineCueEditor from './ScriptLineCueEditor.vue';
import { passthrough } from '@/components/show/config/script/testStubs';
import { useScriptStore } from '@/stores/script';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

const characters = [
  { id: 1, name: 'Alice' },
  { id: 2, name: 'Bob' },
] as never[];

function line(
  id: number,
  type: string,
  characterId: number | null,
  text: string,
  overrides: Partial<ScriptLine> = {}
): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: type,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: id * 10,
        line_id: id,
        part_index: 0,
        character_id: characterId,
        character_group_id: null,
        line_text: text,
      },
    ],
    ...overrides,
  } as ScriptLine;
}

function mountEditor(current: ScriptLine, previous: ScriptLine | null, page: ScriptLine[]) {
  const scriptStore = useScriptStore();
  scriptStore.scriptPages = { 1: page } as never;
  return mount(ScriptLineCueEditor, {
    props: {
      line: current,
      lineIndex: page.indexOf(current),
      previousLine: previous,
      acts: [{ id: 1, name: 'Act 1' }] as never[],
      scenes: [{ id: 1, name: 'Scene 1' }] as never[],
      characters,
      characterGroups: [],
      cues: [],
      cueTypes: [],
      cuts: [],
    },
    global: {
      stubs: {
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BButton: passthrough('button'),
        BButtonGroup: passthrough('div'),
        BAlert: passthrough('div'),
        BModal: true,
        BTabs: true,
        CueGroupEditModal: true,
        CueGroupForm: true,
        IMdiPlusBox: true,
      },
    },
  });
}

describe('ScriptLineCueEditor tagged stage directions (B6)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows the character name above a tagged stage direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice exits.');
    const w = mountEditor(sd, null, [sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(true);
    expect(w.find('.tagged-sd-heading').text()).toBe('Alice');
  });

  it('shows no heading for an untagged stage direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, null, 'The lights fade.');
    const w = mountEditor(sd, null, [sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(false);
  });

  it('does not repeat the name on the same speaker line that follows a tagged direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const dialogue = line(2, LINE_TYPES.DIALOGUE, 1, 'Hello there.');
    const page = [sd, dialogue];

    const sdWrapper = mountEditor(sd, null, page);
    expect(sdWrapper.find('.tagged-sd-heading').text()).toBe('Alice');

    // The direction already named Alice, so her next line carries no name.
    const dialogueWrapper = mountEditor(dialogue, sd, page);
    expect(dialogueWrapper.find('.tagged-sd-heading').exists()).toBe(false);
    expect(dialogueWrapper.text()).not.toContain('Alice');
    expect(dialogueWrapper.text()).toContain('Hello there.');
  });

  it('shows the name again when a different speaker follows a tagged direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const dialogue = line(2, LINE_TYPES.DIALOGUE, 2, 'Evening.');
    const w = mountEditor(dialogue, sd, [sd, dialogue]);

    expect(w.text()).toContain('Bob');
  });

  it('shows no heading on a tagged direction that follows the same speaker', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello there.');
    const sd = line(2, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const w = mountEditor(sd, dialogue, [dialogue, sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(false);
  });
});
