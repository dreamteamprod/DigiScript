import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import ScriptLineEditor from './ScriptLineEditor.vue';
import { passthrough, SelectStub } from './testStubs';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';
import type { Act, Scene } from '@/types/api/show';

const PartStub = defineComponent({
  props: { modelValue: { type: Object, required: true } },
  emits: [
    'update:modelValue',
    'remove-line-part',
    'try-finish-line',
    'stage-direction-style-change',
  ],
  render() {
    return h(
      'div',
      { class: 'part-stub' },
      String((this.modelValue as { part_index: number }).part_index)
    );
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
  ScriptLinePart: PartStub,
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

function makeLine(overrides: Partial<ScriptLine> = {}): ScriptLine {
  return {
    id: null,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: LINE_TYPES.SPACING,
    stage_direction_style_id: null,
    line_parts: [],
    ...overrides,
  };
}

function mountEditor(
  overrides: Partial<InstanceType<typeof ScriptLineEditor>['$props']> = {}
): VueWrapper {
  return mount(ScriptLineEditor, {
    props: {
      lineIndex: 0,
      currentEditPage: 1,
      acts: [act(1)],
      scenes: [scene(1, 1)],
      characters: [],
      characterGroups: [],
      previousLine: null,
      nextLine: null,
      stageDirectionStyles: [],
      modelValue: makeLine(),
      ...overrides,
    },
    global: { stubs },
  });
}

describe('ScriptLineEditor', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  describe('Act/Scene selectors', () => {
    it('shows them when there is no previous line', () => {
      wrapper = mountEditor({ previousLine: null });
      expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);
    });

    it('hides them when the previous line has a real act and scene', () => {
      wrapper = mountEditor({
        previousLine: makeLine({ act_id: 1, scene_id: 1 }),
        modelValue: makeLine({ act_id: 1, scene_id: 1 }),
      });
      expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(false);
    });

    it('shows them when there is a previous line but its act/scene inherited as null', () => {
      // Regression: a line can inherit a null act/scene from a previous line
      // that itself had none set — hiding the selectors then left no way to
      // fix it, and Done/Esc/Enter stayed blocked by lineValid forever.
      wrapper = mountEditor({
        previousLine: makeLine({ act_id: null, scene_id: null }),
        modelValue: makeLine({ act_id: null, scene_id: null }),
      });
      expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);
    });
  });

  describe('modelValue re-sync (reused row after an insert/bulk-apply)', () => {
    it('does not reset local edits when modelValue echoes back its own update', async () => {
      wrapper = mountEditor({ modelValue: makeLine({ id: 1 }) });
      const vm = wrapper.vm as unknown as { state: ScriptLine };

      vm.state.act_id = 2;
      await wrapper.setProps({ modelValue: { ...makeLine({ id: 1 }), act_id: 2 } });

      expect(vm.state.act_id).toBe(2);
    });

    it('re-syncs from modelValue when it changes to a genuinely different line', async () => {
      // Same row key, different identity underneath — e.g. an insert/delete
      // shifted a different line into this slot, or a bulk apply changed the
      // currently-open line's own content.
      wrapper = mountEditor({ modelValue: makeLine({ id: 1, act_id: 1 }) });
      const vm = wrapper.vm as unknown as { state: ScriptLine };

      await wrapper.setProps({ modelValue: makeLine({ id: 2, act_id: 2 }) });

      expect(vm.state.id).toBe(2);
      expect(vm.state.act_id).toBe(2);
    });
  });
});
