import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import ScriptLineViewer from './ScriptLineViewer.vue';
import { passthrough } from './testStubs';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

/**
 * Focused coverage for the `remoteEditors` badge (Phase 4 Step C) only — this
 * component had no test file at all before, and building out full coverage of its
 * pre-existing line-type branches is a larger, separate undertaking than this
 * feature's own scope. The badge's own render logic (per-name rendering, the
 * accessible title) is covered once, directly, in RemoteEditorsBadge.test.ts —
 * here it's stubbed, and only checked that the right `names` reach it.
 */

const RemoteEditorsBadgeStub = defineComponent({
  props: { names: { type: Array, default: () => [] } },
  render() {
    return h('div', { class: 'remote-editors-stub' }, (this.names as string[]).join(','));
  },
});

const stubs = {
  BRow: passthrough('div'),
  BCol: passthrough('div'),
  BButtonGroup: passthrough('div'),
  BButton: passthrough('button'),
  BDropdown: passthrough('div'),
  BDropdownItem: passthrough('button'),
  BAlert: passthrough('div'),
  RemoteEditorsBadge: RemoteEditorsBadgeStub,
};

function dialogueLine(overrides: Partial<ScriptLine> = {}): ScriptLine {
  return {
    id: 1,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: 1,
        line_id: 1,
        part_index: 0,
        character_id: null,
        character_group_id: null,
        line_text: 'Hello',
      },
    ],
    ...overrides,
  };
}

function mountViewer(overrides: Partial<InstanceType<typeof ScriptLineViewer>['$props']> = {}) {
  return mount(ScriptLineViewer, {
    props: {
      line: dialogueLine(),
      lineIndex: 0,
      page: [dialogueLine()],
      previousLine: null,
      acts: [],
      scenes: [],
      characters: [],
      characterGroups: [],
      canEdit: false,
      linePartCuts: [],
      stageDirectionStyles: [],
      stageDirectionStyleOverrides: [],
      ...overrides,
    },
    global: { stubs },
  });
}

describe('ScriptLineViewer', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  describe('remote-editors badge (Phase 4 Step C)', () => {
    it('passes an empty names array through when remoteEditors is omitted', () => {
      wrapper = mountViewer();
      expect(wrapper.findComponent(RemoteEditorsBadgeStub).props('names')).toEqual([]);
    });

    it('passes the given remoteEditors through as names', () => {
      wrapper = mountViewer({ remoteEditors: ['alex', 'blair'] });
      expect(wrapper.findComponent(RemoteEditorsBadgeStub).props('names')).toEqual([
        'alex',
        'blair',
      ]);
    });

    it('renders alongside every line type, not just dialogue', () => {
      wrapper = mountViewer({
        line: dialogueLine({ line_type: LINE_TYPES.CUE_LINE, line_parts: [] }),
        remoteEditors: ['alex'],
      });
      expect(wrapper.findComponent(RemoteEditorsBadgeStub).props('names')).toEqual(['alex']);
    });
  });
});
