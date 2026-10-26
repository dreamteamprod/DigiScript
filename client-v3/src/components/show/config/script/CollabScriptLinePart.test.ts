import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import * as Y from 'yjs';
import CollabScriptLinePart from './CollabScriptLinePart.vue';
import { passthrough, SelectStub } from './testStubs';
import { useUserStore } from '@/stores/user';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { applyTextDiff } from '@/js/yjs/ytextDiff';
import { LOCAL_EDIT_ORIGIN } from '@/js/yjs/draftWriter';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { DraftScriptLinePart } from '@/js/yjs/draftAdapter';
import type { Character, CharacterGroup } from '@/types/api/show';

const setPartText = vi.fn();
const setPartCharacter = vi.fn(() => true);
let liveText = new Y.Text('');

vi.mock('@/composables/useDraftWriter', () => ({
  useDraftWriter: () => ({
    getPartText: () => liveText,
    setPartText: (...args: unknown[]) => setPartText(...args),
    setPartCharacter: (...args: unknown[]) => setPartCharacter(...args),
  }),
}));
vi.mock('@/js/toast', () => ({
  toast: { warning: vi.fn(), error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { toast } from '@/js/toast';

const stubs = {
  BCol: passthrough('div'),
  BRow: passthrough('div'),
  BFormGroup: passthrough('div'),
  BButton: passthrough('button'),
  BFormSelect: SelectStub,
};

function part(overrides: Partial<DraftScriptLinePart> = {}): DraftScriptLinePart {
  return {
    _id: 'p1',
    _uid: 'p1',
    id: null,
    line_id: null,
    part_index: 0,
    character_id: null,
    character_group_id: null,
    line_text: '',
    ...overrides,
  };
}

const characters: Character[] = [
  { id: 1, show_id: 1, played_by: null, name: 'Alice', description: null, cast_member: null },
  { id: 2, show_id: 1, played_by: null, name: 'Bob', description: null, cast_member: null },
];
const characterGroups: CharacterGroup[] = [
  { id: 1, show_id: 1, name: 'Chorus', description: null, characters: [] },
];

function mountPart(props: Partial<InstanceType<typeof CollabScriptLinePart>['$props']> = {}) {
  return mount(CollabScriptLinePart, {
    props: {
      page: 1,
      lineUid: 'line1',
      part: part(),
      focusInput: false,
      characters,
      characterGroups,
      showAddButton: false,
      enableAddButton: true,
      showRemoveButton: false,
      lineType: LINE_TYPES.DIALOGUE,
      lineParts: [part()],
      ...props,
    },
    global: { stubs },
    attachTo: document.body,
  });
}

describe('CollabScriptLinePart', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    liveText = new Y.Text('');
    new Y.Doc().getMap('root').set('t', liveText); // integrate so relative positions resolve
    setPartText.mockReset();
    setPartText.mockReturnValue('changed');
    setPartCharacter.mockClear();
    setPartCharacter.mockReturnValue(true);
    vi.mocked(toast.warning).mockClear();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it('shows the live text of the part', () => {
    liveText.insert(0, 'hello there');
    wrapper = mountPart();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('hello there');
  });

  it('writes a keystroke via setPartText using the minimal diff', () => {
    liveText.insert(0, 'hi');
    setPartText.mockImplementation(
      (_page: number, _lineUid: string, _partUid: string, text: string) =>
        applyTextDiff(liveText, text, LOCAL_EDIT_ORIGIN) ? 'changed' : 'unchanged'
    );
    wrapper = mountPart({ part: part({ line_text: 'hi' }) });

    const input = wrapper.find('input').element as HTMLInputElement;
    input.value = 'hiya';
    input.dispatchEvent(new Event('input'));

    expect(setPartText).toHaveBeenCalledWith(1, 'line1', 'p1', 'hiya');
    expect(liveText.toString()).toBe('hiya');
  });

  it('warns when a keystroke targets a part another editor already removed', () => {
    setPartText.mockReturnValue('gone');
    wrapper = mountPart();

    const input = wrapper.find('input').element as HTMLInputElement;
    input.value = 'x';
    input.dispatchEvent(new Event('input'));

    expect(toast.warning).toHaveBeenCalled();
  });

  it('sets a character and clears the group through setPartCharacter', async () => {
    wrapper = mountPart({ part: part({ character_group_id: 1 }) });
    const select = wrapper.find('select');
    await select.setValue('2');

    expect(setPartCharacter).toHaveBeenCalledWith(1, 'line1', 'p1', 2, null);
  });

  it('warns when the character change targets a vanished part', async () => {
    setPartCharacter.mockReturnValue(false);
    wrapper = mountPart();
    const select = wrapper.find('select');
    await select.setValue('1');

    expect(toast.warning).toHaveBeenCalled();
  });

  it('emits add-line-part / remove-line-part / try-finish-line', async () => {
    wrapper = mountPart({ showAddButton: true, showRemoveButton: true });
    const buttons = wrapper.findAll('button');
    await buttons[0]?.trigger('click'); // remove is rendered before add in the template
    await wrapper.find('input').trigger('keydown.enter');

    expect(wrapper.emitted('try-finish-line')).toBeTruthy();
  });

  it('sorts character options by most-recently-used when the user setting is on', () => {
    useUserStore().userSettings = { character_mru_sort: true };
    useScriptDraftStore().pageSnapshots = {
      '1': [
        {
          _id: 'a',
          _uid: 'a',
          id: null,
          act_id: null,
          scene_id: null,
          line_type: LINE_TYPES.DIALOGUE,
          stage_direction_style_id: null,
          parts: [
            {
              _id: 'ap',
              _uid: 'ap',
              id: null,
              part_index: 0,
              character_id: 2,
              character_group_id: null,
              line_text: 'Bob speaks a lot',
            },
          ],
        },
      ],
    };
    wrapper = mountPart();

    const options = wrapper.find('select').findAll('option');
    // Bob (id 2) was used, so comes before Alice despite Alice being listed first in props.
    const texts = options.map((o) => o.text());
    expect(texts.indexOf('Bob')).toBeLessThan(texts.indexOf('Alice'));
  });
});
