/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import CollabScriptLineEditor from './CollabScriptLineEditor.vue';
import { passthrough, SelectStub } from './testStubs';
import { act, scene } from './testFixtures';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useSystemStore } from '@/stores/system';
import type { DraftScriptLine } from '@/js/yjs/draftAdapter';

const setLineActScene = vi.fn(() => true);
const removePart = vi.fn(() => true);
const addPart = vi.fn(() => 'new-part-uid');
const setLineField = vi.fn(() => true);

vi.mock('@/composables/useDraftWriter', () => ({
  useDraftWriter: () => ({
    setLineActScene: (...args: unknown[]) => setLineActScene(...args),
    removePart: (...args: unknown[]) => removePart(...args),
    addPart: (...args: unknown[]) => addPart(...args),
    setLineField: (...args: unknown[]) => setLineField(...args),
  }),
}));
vi.mock('@/js/toast', () => ({
  toast: { warning: vi.fn(), error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { toast } from '@/js/toast';

const PartStub = defineComponent({
  props: { part: { type: Object, required: true } },
  emits: ['remove-line-part', 'try-finish-line', 'stage-direction-style-change'],
  render() {
    return h('div', { class: 'part-stub' }, (this.part as { _uid: string })._uid);
  },
});

// The badge's own render logic (per-name rendering, the accessible title) is
// covered once, directly, in RemoteEditorsBadge.test.ts — here it's stubbed, and
// only checked that the right `names` reach it.
const RemoteEditorsBadgeStub = defineComponent({
  props: { names: { type: Array, default: () => [] } },
  render() {
    return h('div', { class: 'remote-editors-stub' }, (this.names as string[]).join(','));
  },
});

const stubs = {
  BRow: passthrough('div'),
  BCol: passthrough('div'),
  BFormGroup: passthrough('div'),
  BButton: passthrough('button'),
  BButtonGroup: passthrough('div'),
  BAlert: passthrough('div'),
  BFormSelect: SelectStub,
  CollabScriptLinePart: PartStub,
  RemoteEditorsBadge: RemoteEditorsBadgeStub,
};

function line(overrides: Partial<DraftScriptLine> = {}): DraftScriptLine {
  return {
    _id: 'line1',
    _uid: 'line1',
    id: null,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [
      {
        _id: 'p1',
        _uid: 'p1',
        id: null,
        line_id: null,
        part_index: 0,
        character_id: null,
        character_group_id: null,
        line_text: '',
      },
    ],
    ...overrides,
  };
}

function mountEditor(
  overrides: Partial<InstanceType<typeof CollabScriptLineEditor>['$props']> = {}
) {
  return mount(CollabScriptLineEditor, {
    props: {
      page: 1,
      line: line(),
      lineType: LINE_TYPES.DIALOGUE,
      acts: [act(1)],
      scenes: [scene(1, 1)],
      characters: [],
      characterGroups: [],
      previousLine: null,
      nextLine: null,
      stageDirectionStyles: [],
      ...overrides,
    },
    global: { stubs },
  });
}

describe('CollabScriptLineEditor', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    setLineActScene.mockClear().mockReturnValue(true);
    removePart.mockClear().mockReturnValue(true);
    addPart.mockClear().mockReturnValue('new-part-uid');
    setLineField.mockClear().mockReturnValue(true);
    vi.mocked(toast.warning).mockClear();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it('renders a part per the live line and writes act/scene changes immediately', async () => {
    wrapper = mountEditor();
    expect(wrapper.findAll('.part-stub')).toHaveLength(1);

    await wrapper.find('select').setValue('1');
    expect(setLineActScene).toHaveBeenCalledWith(1, 'line1', 1, 1);
  });

  it('warns when an act/scene change targets a line another editor removed', async () => {
    setLineActScene.mockReturnValue(false);
    wrapper = mountEditor();
    await wrapper.find('select').setValue('1');
    expect(toast.warning).toHaveBeenCalled();
  });

  it('disables Done until act and scene are both set', async () => {
    wrapper = mountEditor({ line: line({ act_id: null }) });
    const done = wrapper.findAll('button').find((b) => b.text() === 'Done')!;
    expect(done.attributes('disabled')).toBeDefined();
  });

  it('keeps the Act/Scene selectors visible as act/scene go from null to set, instead of vanishing mid-pick', async () => {
    // Regression: this used to read props.line.act_id/scene_id live, so
    // picking an act (scene still null — selectors should stay) then a scene
    // (both now non-null) unmounted the column out from under the user,
    // jumping the layout from 10 to 12 cols with no way to fix a wrong pick.
    wrapper = mountEditor({
      previousLine: null,
      line: line({ act_id: null, scene_id: null }),
    });
    expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);

    await wrapper.setProps({ line: line({ act_id: 1, scene_id: null }) });
    expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);

    await wrapper.setProps({ line: line({ act_id: 1, scene_id: 1 }) });
    expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);
  });

  it('emits doneEditing when Done is clicked while valid', async () => {
    wrapper = mountEditor();
    const done = wrapper.findAll('button').find((b) => b.text() === 'Done')!;
    await done.trigger('click');
    expect(wrapper.emitted('doneEditing')).toBeTruthy();
  });

  it('try-finish-line from a part emits finishAndAddLine only when the line is valid', async () => {
    wrapper = mountEditor({ line: line({ act_id: null }) });
    wrapper.findComponent(PartStub).vm.$emit('try-finish-line');
    expect(wrapper.emitted('finishAndAddLine')).toBeFalsy();

    wrapper.unmount();
    wrapper = mountEditor();
    wrapper.findComponent(PartStub).vm.$emit('try-finish-line');
    // Enter (try-finish-line) chains into a new line (Design E) — doneEditing alone
    // never adds anything; see finishAndAddLine in CollabScriptEditor.vue.
    expect(wrapper.emitted('finishAndAddLine')).toBeTruthy();
  });

  it('stage-direction-style-change from a part writes the line field', () => {
    wrapper = mountEditor();
    wrapper.findComponent(PartStub).vm.$emit('stage-direction-style-change', 3);
    expect(setLineField).toHaveBeenCalledWith(1, 'line1', 'stage_direction_style_id', 3);
  });

  it('emits deleteLine when Delete Line is clicked', async () => {
    wrapper = mountEditor();
    const del = wrapper.findAll('button').find((b) => b.text() === 'Delete Line')!;
    await del.trigger('click');
    expect(wrapper.emitted('deleteLine')).toBeTruthy();
  });

  it('adds a part on mount if a dialogue line somehow has none', () => {
    wrapper = mountEditor({ line: line({ line_parts: [] }) });
    expect(addPart).toHaveBeenCalledWith(1, 'line1', { characterId: null, characterGroupId: null });
  });

  it('adds a line part seeded from the previous line at the same position', async () => {
    useSystemStore().currentShow = { script_mode: 1 } as never;
    wrapper = mountEditor({
      previousLine: line({
        _uid: 'prev',
        line_parts: [
          {
            _id: 'pp0',
            _uid: 'pp0',
            id: null,
            line_id: null,
            part_index: 0,
            character_id: null,
            character_group_id: null,
            line_text: '',
          },
          {
            _id: 'pp1',
            _uid: 'pp1',
            id: null,
            line_id: null,
            part_index: 1,
            character_id: 9,
            character_group_id: null,
            line_text: '',
          },
        ],
      }),
    });
    const addSpeaker = wrapper.findAll('button').find((b) => b.text().startsWith('Add Speaker'))!;
    await addSpeaker.trigger('click');
    expect(addPart).toHaveBeenCalledWith(1, 'line1', { characterId: 9, characterGroupId: null });
  });

  it('removes a part by uid, not by index', () => {
    wrapper = mountEditor();
    wrapper.findComponent(PartStub).vm.$emit('remove-line-part');
    expect(removePart).toHaveBeenCalledWith(1, 'line1', 'p1');
  });

  it('shows an uneditable alert for cue and spacing lines', () => {
    wrapper = mountEditor({
      lineType: LINE_TYPES.CUE_LINE,
      line: line({ line_type: LINE_TYPES.CUE_LINE }),
    });
    expect(wrapper.text()).toContain('Cue Lines have no editable content.');
    expect(wrapper.findAll('.part-stub')).toHaveLength(0);
  });

  it('focuses the row itself for a cue line, so Up/Down/Esc keep working without a text input', async () => {
    wrapper = mount(CollabScriptLineEditor, {
      attachTo: document.body,
      props: {
        page: 1,
        line: line({ line_type: LINE_TYPES.CUE_LINE, line_parts: [] }),
        acts: [act(1)],
        scenes: [scene(1, 1)],
        characters: [],
        characterGroups: [],
        previousLine: null,
        nextLine: null,
        stageDirectionStyles: [],
      },
      global: { stubs },
    });
    await flushPromises();

    const row = wrapper.find('.line-editor-card');
    expect(document.activeElement).toBe(row.element);

    await row.trigger('keydown.up');
    await row.trigger('keydown.down');
    expect(wrapper.emitted('navigateUp')).toHaveLength(1);
    expect(wrapper.emitted('navigateDown')).toHaveLength(1);
  });

  describe('remote-editors badge (Phase 4 Step C)', () => {
    it('passes an empty names array through when no one else has this line open', () => {
      wrapper = mountEditor({ remoteEditors: [] });
      expect(wrapper.findComponent(RemoteEditorsBadgeStub).props('names')).toEqual([]);
    });

    it('passes the given remoteEditors through as names', () => {
      wrapper = mountEditor({ remoteEditors: ['alex', 'blair'] });
      expect(wrapper.findComponent(RemoteEditorsBadgeStub).props('names')).toEqual([
        'alex',
        'blair',
      ]);
    });
  });
});
