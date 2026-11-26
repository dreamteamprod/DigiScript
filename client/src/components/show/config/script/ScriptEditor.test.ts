/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import ScriptEditor from './ScriptEditor.vue';
import { passthrough, SelectStub, AlertStub, ModalStub } from './testStubs';
import { mockCommonScriptStores } from './scriptEditorTestMocks';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useScriptStore } from '@/stores/script';
import { useSystemStore } from '@/stores/system';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj: vi.fn(), connect: vi.fn() }),
}));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), warning: vi.fn(), error: vi.fn(), success: vi.fn() },
}));
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

import { toast } from '@/js/toast';

// Same technique as CollabScriptEditor.test.ts: a bare stub that still exposes
// enough of ScriptLineViewer's real surface (selected/previewed, toggle-select,
// hover events) for the selection/hover-preview tests below to go through it.
const ViewerStub = defineComponent({
  props: {
    line: { type: Object, required: true },
    lineIndex: { type: Number, default: 0 },
    selected: { type: Boolean, default: false },
    previewed: { type: Boolean, default: false },
  },
  emits: ['edit-line', 'toggle-select', 'hover-checkbox', 'unhover-checkbox', 'cut-line-part'],
  render() {
    return h('div', { class: 'row-stub' }, String(this.lineIndex));
  },
});
const LineEditorStub = defineComponent({
  props: { modelValue: { type: Object, required: true } },
  emits: [
    'update:modelValue',
    'doneEditing',
    'finishAndAddLine',
    'deleteLine',
    'navigateUp',
    'navigateDown',
  ],
  render() {
    return h('div', { class: 'editor-stub' });
  },
});
const bootstrapStubs = {
  BContainer: passthrough('div'),
  BRow: passthrough('div'),
  BCol: passthrough('div'),
  BButton: passthrough('button'),
  BButtonGroup: passthrough('div'),
  BSpinner: passthrough('span'),
  BModal: ModalStub,
  BForm: passthrough('form'),
  BFormGroup: passthrough('div'),
  BFormInput: passthrough('span'),
  BFormSelect: SelectStub,
};

function makeLine(id: number | null, overrides: Partial<ScriptLine> = {}): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: LINE_TYPES.SPACING,
    stage_direction_style_id: null,
    line_parts: [],
    ...overrides,
  };
}

describe('ScriptEditor', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    mockCommonScriptStores();
    useScriptConfigStore().editStatus = { canRequestEdit: false, currentEditor: 'me' };
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    useSystemStore().currentShow = { id: 1, script_mode: 1 } as never;
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  /** Seeds scriptStore's own saved copy for a page — loadScriptPage is mocked to a
   * no-op above, so this is what getScriptPage (and so scriptConfigStore.addPage,
   * called from ScriptEditor's own loadPage) actually sees. */
  function seedSavedPage(page: number, lines: ScriptLine[]): void {
    useScriptStore().script[String(page)] = lines;
  }

  async function mountEditor(): Promise<VueWrapper> {
    wrapper = mount(ScriptEditor, {
      global: {
        components: bootstrapStubs,
        stubs: {
          ScriptLineViewer: ViewerStub,
          ScriptLineEditor: LineEditorStub,
          BAlert: AlertStub,
        },
      },
    });
    await flushPromises();
    return wrapper;
  }

  function vm(w: VueWrapper) {
    return w.vm as unknown as {
      editingLines: Set<string>;
      onToggleSelect: (index: number) => void;
      selectionCount: number;
      selectionRangeLabel: string;
      selectionPreviewLines: { label: string }[];
      navigateUp: (page: number, index: number) => void;
      navigateDown: (page: number, index: number) => void;
      deleteLine: (page: number, index: number) => void;
      insertLineAt: (page: number, index: number, type: number) => Promise<void>;
      beginEditingLine: (page: number, index: number) => void;
      doneEditingLine: (page: number, index: number) => void;
      onLineChange: (index: number, line: ScriptLine) => void;
      autosave: () => Promise<void>;
      firstInvalidLine: { page: string; error: string } | null;
    };
  }

  describe('selection remapping on delete/insert', () => {
    it('clears the selection when a line is deleted', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).onToggleSelect(0);
      vm(w).onToggleSelect(1);
      expect(vm(w).selectionCount).toBe(2);

      vm(w).deleteLine(1, 0);
      await flushPromises();

      expect(vm(w).selectionCount).toBe(0);
    });

    it('clears the selection when a line is inserted mid-range', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).onToggleSelect(0);
      vm(w).onToggleSelect(2);
      expect(vm(w).selectionCount).toBe(3);

      await vm(w).insertLineAt(1, 0, LINE_TYPES.SPACING);

      expect(vm(w).selectionCount).toBe(0);
    });
  });

  describe('editingLines only shifts when a line actually splices', () => {
    it('does not shift an open editor past a tombstoned (not spliced) line', async () => {
      // Regression: tombstoning a saved line doesn't move anything in the
      // array (see scriptConfig.ts's deleteLine), but editingLines used to
      // shift unconditionally — an editor open on the line after the one just
      // tombstoned would silently start pointing at the wrong index.
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).beginEditingLine(1, 2); // open an editor on the last line

      vm(w).deleteLine(1, 0); // tombstones the first (saved) line — no splice
      await flushPromises();

      expect(vm(w).editingLines.has('page_1_line_2')).toBe(true);
      expect(vm(w).editingLines.has('page_1_line_1')).toBe(false);
    });

    it('shifts an open editor down when deleting an unsaved line actually splices', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2)]);
      const w = await mountEditor();
      await vm(w).insertLineAt(1, 0, LINE_TYPES.SPACING); // unsaved line inserted at index 1
      vm(w).beginEditingLine(1, 2); // open editor on what is now index 2

      vm(w).deleteLine(1, 1); // deletes the unsaved line at index 1 — a real splice
      await flushPromises();

      expect(vm(w).editingLines.has('page_1_line_1')).toBe(true); // shifted down from 2
      expect(vm(w).editingLines.has('page_1_line_2')).toBe(false);
    });

    it('does not shift editingLines when an insert reuses a tombstoned slot', async () => {
      // Regression: insertBlankLine reuses a tombstoned slot in place (a
      // same-length replace, not a splice) when the target index is already
      // deleted — editingLines used to shift up regardless, moving an editor
      // open past that slot to the wrong index for no reason.
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).deleteLine(1, 1); // tombstones index 1
      vm(w).beginEditingLine(1, 2);

      await vm(w).insertLineAt(1, 0, LINE_TYPES.SPACING); // reuses the index-1 tombstone

      expect(vm(w).editingLines.has('page_1_line_2')).toBe(true);
    });
  });

  describe('soft-deleted lines are excluded from selection/count/navigation', () => {
    it('selectionCount does not count a tombstoned line within the range', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).deleteLine(1, 1); // tombstones the saved middle line, doesn't splice

      vm(w).onToggleSelect(0);
      vm(w).onToggleSelect(2);

      // 3-line span, but the middle one is a hidden tombstone — only 2 are real.
      expect(vm(w).selectionCount).toBe(2);
    });

    it('selectionPreviewLines skips a tombstoned line within the range', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).deleteLine(1, 1);

      vm(w).onToggleSelect(0);
      vm(w).onToggleSelect(2);

      expect(vm(w).selectionPreviewLines).toHaveLength(2);
    });

    it('navigateUp steps over a tombstoned line to the next real one', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).deleteLine(1, 1); // index 1 is now a hidden tombstone

      vm(w).navigateUp(1, 2); // Up from line index 2 should skip 1, land on 0

      expect(vm(w).editingLines.has('page_1_line_0')).toBe(true);
      expect(vm(w).editingLines.has('page_1_line_1')).toBe(false);
    });

    it('navigateDown steps over a tombstoned line to the next real one', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2), makeLine(3)]);
      const w = await mountEditor();
      vm(w).deleteLine(1, 1);

      vm(w).navigateDown(1, 0); // Down from line index 0 should skip 1, land on 2

      expect(vm(w).editingLines.has('page_1_line_2')).toBe(true);
      expect(vm(w).editingLines.has('page_1_line_1')).toBe(false);
    });
  });

  describe('autosave does not misreport success when it cannot actually save', () => {
    it('stays silent while a line is open for editing', async () => {
      // Regression: autosave always showed "Performing autosave..." then
      // "Autosave successful" around saveScript(), even once saveScript()
      // itself started silently bailing on an open editor or invalid line —
      // every tick during an editing session falsely reported success.
      seedSavedPage(1, [makeLine(1), makeLine(2)]);
      const w = await mountEditor();
      vm(w).beginEditingLine(1, 0);
      vm(w).onToggleSelect(1); // an unrelated change, so scriptChanges alone isn't the blocker
      await flushPromises();

      await vm(w).autosave();

      expect(toast.info).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    });

    it('stays silent when an invalid line would block Save, even with no editor open', async () => {
      seedSavedPage(1, []);
      const w = await mountEditor();
      await vm(w).insertLineAt(1, -1, LINE_TYPES.DIALOGUE); // appends an invalid dialogue line
      vm(w).doneEditingLine(1, 0); // close it, isolating the invalid-line gate from the open-editor one
      await flushPromises();
      expect(vm(w).editingLines.size).toBe(0); // sanity-check the isolation
      expect(vm(w).firstInvalidLine).not.toBeNull(); // sanity-check the premise

      await vm(w).autosave();

      expect(toast.info).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  describe("saveDisabledReason is shown somewhere visible, not just a disabled button's title", () => {
    // Regression: a disabled <button>'s own title attribute never shows a native
    // tooltip — Chromium (and most browsers) suppress hover events, including the
    // ones a tooltip needs, for a disabled form control entirely. Confirmed live:
    // hovering the disabled Save button for 2+ seconds showed nothing. The reason
    // must be rendered as plain visible text, not just set as an attribute.
    it('shows the open-editor reason as visible text', async () => {
      seedSavedPage(1, [makeLine(1), makeLine(2)]);
      const w = await mountEditor();
      vm(w).beginEditingLine(1, 0);
      await flushPromises();

      expect(w.find('.save-disabled-reason').text()).toBe(
        'Finish editing the open line(s) before saving'
      );
    });

    it('shows the invalid-line reason as visible text', async () => {
      seedSavedPage(1, []);
      const w = await mountEditor();
      await vm(w).insertLineAt(1, -1, LINE_TYPES.DIALOGUE);
      vm(w).doneEditingLine(1, 0);
      await flushPromises();

      expect(w.find('.save-disabled-reason').exists()).toBe(true);
      expect(w.find('.save-disabled-reason').text()).toContain('Page 1');
    });

    it('shows nothing when there is simply nothing to save yet', async () => {
      seedSavedPage(1, [makeLine(1)]);
      const w = await mountEditor();
      await flushPromises();

      expect(w.find('.save-disabled-reason').exists()).toBe(false);
    });
  });

  describe('firstInvalidLine / canSave skip soft-deleted and untouched legacy lines', () => {
    it('does not block Save on a tombstoned line that would otherwise be invalid', async () => {
      // A saved dialogue line with empty text (invalid on its own) ...
      seedSavedPage(1, [
        makeLine(1, {
          line_type: LINE_TYPES.DIALOGUE,
          line_parts: [
            {
              id: 1,
              line_id: 1,
              part_index: 0,
              character_id: 1,
              character_group_id: null,
              line_text: '',
            },
          ],
        }),
        makeLine(2),
      ]);
      const w = await mountEditor();
      // ... but it's been deleted (tombstoned), so it must not block Save.
      vm(w).deleteLine(1, 0);
      await flushPromises();

      expect(vm(w).firstInvalidLine).toBeNull();
    });

    it('does not validate a pre-existing line nothing touched this session', async () => {
      // A legacy saved line with a null act/scene (the DB allows it, this
      // validator wouldn't) that nothing in this session edits.
      const line2 = makeLine(2);
      seedSavedPage(1, [makeLine(1, { act_id: null, scene_id: null }), line2]);
      const w = await mountEditor();
      // A real, valid change to the OTHER line (onToggleSelect alone mutates
      // no draft content, so it wouldn't have exercised computePageStatus's
      // diff at all) must not cause the untouched legacy line to suddenly
      // start blocking Save.
      vm(w).onLineChange(1, { ...line2, scene_id: 2 }); // a genuinely different value
      await flushPromises();

      expect(vm(w).firstInvalidLine).toBeNull();
    });

    it('does flag a brand-new invalid line', async () => {
      seedSavedPage(1, []);
      const w = await mountEditor();
      await vm(w).insertLineAt(1, -1, LINE_TYPES.DIALOGUE); // appends to the empty page
      await flushPromises();

      expect(vm(w).firstInvalidLine).not.toBeNull();
    });

    it('does flag an invalid line inserted mid-page, not just appended', async () => {
      // Regression: computePageStatus splices an inserted line into its own
      // comparison copy at the same index before diffing, so it always diffs
      // equal to itself and lands in neither added nor updated — only in
      // status.inserted, which firstInvalidLine must also check.
      seedSavedPage(1, [makeLine(1), makeLine(2)]);
      const w = await mountEditor();
      await vm(w).insertLineAt(1, 0, LINE_TYPES.DIALOGUE); // inserts between the two saved lines
      await flushPromises();

      expect(vm(w).firstInvalidLine).not.toBeNull();
    });
  });
});
