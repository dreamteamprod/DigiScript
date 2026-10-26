/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import CollabScriptLineEditor from './CollabScriptLineEditor.vue';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { DraftScriptLine } from '@/js/yjs/draftAdapter';
import type { Act, Scene } from '@/types/api/show';

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

function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}

const SelectStub = defineComponent({
  props: { modelValue: {}, options: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  render() {
    return h(
      'select',
      {
        class: 'act-scene-select',
        onChange: (e: Event) => {
          const raw = (e.target as HTMLSelectElement).value;
          this.$emit('update:modelValue', raw === 'null' ? null : Number.parseInt(raw, 10));
        },
      },
      (this.options as { value: unknown; text: string }[]).map((o) =>
        h('option', { value: String(o.value) }, o.text)
      )
    );
  },
});

const PartStub = defineComponent({
  props: { part: { type: Object, required: true } },
  emits: ['add-line-part', 'remove-line-part', 'try-finish-line'],
  render() {
    return h('div', { class: 'part-stub' }, (this.part as { _uid: string })._uid);
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
};

function act(id: number, overrides: Partial<Act> = {}): Act {
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
function scene(id: number, actId: number, overrides: Partial<Scene> = {}): Scene {
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

    await wrapper.find('select.act-scene-select').setValue('1');
    expect(setLineActScene).toHaveBeenCalledWith(1, 'line1', 1, 1);
  });

  it('warns when an act/scene change targets a line another editor removed', async () => {
    setLineActScene.mockReturnValue(false);
    wrapper = mountEditor();
    await wrapper.find('select.act-scene-select').setValue('1');
    expect(toast.warning).toHaveBeenCalled();
  });

  it('disables Done until act and scene are both set', async () => {
    wrapper = mountEditor({ line: line({ act_id: null }) });
    const done = wrapper.findAll('button').find((b) => b.text() === 'Done')!;
    expect(done.attributes('disabled')).toBeDefined();
  });

  it('emits doneEditing when Done is clicked while valid', async () => {
    wrapper = mountEditor();
    const done = wrapper.findAll('button').find((b) => b.text() === 'Done')!;
    await done.trigger('click');
    expect(wrapper.emitted('doneEditing')).toBeTruthy();
  });

  it('emits deleteLine when Delete is clicked', async () => {
    wrapper = mountEditor();
    const del = wrapper.findAll('button').find((b) => b.text() === 'Delete')!;
    await del.trigger('click');
    expect(wrapper.emitted('deleteLine')).toBeTruthy();
  });

  it('adds a part on mount if a dialogue line somehow has none', () => {
    wrapper = mountEditor({ line: line({ line_parts: [] }) });
    expect(addPart).toHaveBeenCalledWith(1, 'line1', { characterId: null, characterGroupId: null });
  });

  it('adds a line part seeded from the previous line at the same position', () => {
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
    wrapper.findComponent(PartStub).vm.$emit('add-line-part');
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
});
