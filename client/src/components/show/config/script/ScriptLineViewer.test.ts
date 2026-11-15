import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import ScriptLineViewer from './ScriptLineViewer.vue';
import { passthrough } from './testStubs';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

/**
 * Focused coverage for the `remoteEditors` badge (Phase 4 Step C) only — this
 * component had no test file at all before, and building out full coverage of its
 * pre-existing line-type branches is a larger, separate undertaking than this
 * feature's own scope.
 */

const stubs = {
  BRow: passthrough('div'),
  BCol: passthrough('div'),
  BButtonGroup: passthrough('div'),
  BButton: passthrough('button'),
  BBadge: passthrough('span'),
  BDropdown: passthrough('div'),
  BDropdownItem: passthrough('button'),
  BAlert: passthrough('div'),
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
    it('renders nothing when remoteEditors is omitted', () => {
      wrapper = mountViewer();
      expect(wrapper.find('.remote-editors').exists()).toBe(false);
    });

    it('renders nothing when remoteEditors is an empty array', () => {
      wrapper = mountViewer({ remoteEditors: [] });
      expect(wrapper.find('.remote-editors').exists()).toBe(false);
    });

    it('renders a badge per remote editor, with an accessible title', () => {
      wrapper = mountViewer({ remoteEditors: ['alex', 'blair'] });
      const row = wrapper.find('.remote-editors');
      expect(row.exists()).toBe(true);
      const badges = row.findAll('span');
      expect(badges).toHaveLength(2);
      expect(badges.find((b) => b.text().includes('alex'))?.attributes('title')).toBe(
        'alex is editing this line'
      );
      expect(badges.find((b) => b.text().includes('blair'))?.attributes('title')).toBe(
        'blair is editing this line'
      );
    });

    it('renders alongside every line type, not just dialogue', () => {
      wrapper = mountViewer({
        line: dialogueLine({ line_type: LINE_TYPES.CUE_LINE, line_parts: [] }),
        remoteEditors: ['alex'],
      });
      expect(wrapper.find('.remote-editors').exists()).toBe(true);
      expect(wrapper.text()).toContain('alex');
    });
  });
});
