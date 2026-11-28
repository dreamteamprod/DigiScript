import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import ScriptLineEditor from './ScriptLineEditor.vue';
import { passthrough, SelectStub } from './testStubs';
import { act, scene } from './testFixtures';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

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

    it('stays visible as the user picks an act then a scene, instead of vanishing mid-pick', async () => {
      // Regression: this used to read state.act_id/scene_id live, so picking
      // an act (still null scene — selectors should stay) then a scene (both
      // now non-null) unmounted the column out from under the user, jumping
      // the layout from 10 to 12 cols with no way to fix a wrong pick.
      wrapper = mountEditor({
        previousLine: makeLine({ act_id: null, scene_id: null }),
        modelValue: makeLine({ act_id: null, scene_id: null }),
      });
      const vm = wrapper.vm as unknown as { state: ScriptLine };

      vm.state.act_id = 1;
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);

      vm.state.scene_id = 1;
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-testid="line-act-select"]').exists()).toBe(true);
    });
  });

  describe('modelValue re-sync (reused row after an insert/bulk-apply)', () => {
    it('does not reset local edits when modelValue echoes back its own update', async () => {
      // Goes through a real onStateChange (the act select's own update:model-value),
      // which is what actually records lastEmittedSnapshot — directly mutating
      // vm.state, as this test used to, never calls onStateChange at all, so
      // lastEmittedSnapshot stays null and the echo guard is never exercised;
      // the old assertion passed whether or not that guard did anything.
      wrapper = mountEditor({
        previousLine: null,
        modelValue: makeLine({ id: 1, act_id: null, scene_id: null }),
      });
      await wrapper.find('[data-testid="line-act-select"]').setValue('1');
      const emittedSnapshot = wrapper.emitted('update:modelValue')!.at(-1)![0] as ScriptLine;

      const vm = wrapper.vm as unknown as {
        state: ScriptLine;
        v$: { $dirty: boolean };
      };
      // A further local change this component hasn't emitted yet (e.g. a
      // keystroke not modelled in full here) — the echo guard must tell this
      // apart from a real external change by comparing the incoming value
      // against what was LAST emitted, not against the current live state.
      vm.state.scene_id = 1;

      // The parent echoing back this component's own earlier update.
      await wrapper.setProps({ modelValue: emittedSnapshot });

      expect(vm.state.scene_id).toBe(1); // untouched by the echo
      expect(vm.v$.$dirty).toBe(true); // only a genuine re-sync calls $reset()
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
