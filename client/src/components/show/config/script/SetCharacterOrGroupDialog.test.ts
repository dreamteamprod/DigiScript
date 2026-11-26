import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import SetCharacterOrGroupDialog, {
  type SelectedLinePreview,
} from './SetCharacterOrGroupDialog.vue';

/**
 * Ported from the retired BulkEditModal.test.ts's character-assignment cases —
 * this dialog is BulkEditModal's character half, split out on its own (Move to
 * Scene, via BulkActSceneModal, replaces the act/scene half). Same technique:
 * drive the underlying refs directly and call handleOk() rather than asserting on
 * bootstrap-vue-next's unresolved form controls.
 */
function mountDialog(lines: SelectedLinePreview[] = []) {
  return mount(SetCharacterOrGroupDialog, {
    props: {
      lines,
      characters: [
        { id: 1, show_id: 1, played_by: null, name: 'Alice', description: null, cast_member: null },
      ],
      characterGroups: [{ id: 1, show_id: 1, name: 'Chorus', description: null, characters: [] }],
    },
  }) as unknown as VueWrapper & {
    vm: {
      selectedPartIndex: number;
      selectedCharacterId: number | null;
      selectedCharacterGroupId: number | null;
      combinedValue: string | null;
      changeCount: number;
      canApply: boolean;
      handleOk: () => void;
      reset: () => void;
    };
  };
}

describe('SetCharacterOrGroupDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('emits the chosen character for every line with a part at the selected index', () => {
    const w = mountDialog([
      {
        label: 'Line 1',
        lineTypeLabel: 'Dialogue',
        parts: [{ characterId: 2, characterGroupId: null }],
      },
      { label: 'Line 2', lineTypeLabel: 'Direction', parts: [] },
    ]);
    w.vm.selectedCharacterId = 1;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [
      { partIndex: number; characterId: number | null; characterGroupId: number | null },
    ][];
    expect(payloads).toHaveLength(1);
    expect(payloads[0]![0]).toEqual({ partIndex: 1, characterId: 1, characterGroupId: null });
  });

  it('a line with no part at the selected index counts as "left alone", not a change', () => {
    const w = mountDialog([
      {
        label: 'Line 1',
        lineTypeLabel: 'Dialogue',
        parts: [{ characterId: 2, characterGroupId: null }],
      },
      { label: 'Line 2', lineTypeLabel: 'Direction', parts: [] },
    ]);
    w.vm.selectedCharacterId = 1;

    expect(w.vm.changeCount).toBe(1);
  });

  it('does not emit when nothing is selected', () => {
    const w = mountDialog([
      {
        label: 'Line 1',
        lineTypeLabel: 'Dialogue',
        parts: [{ characterId: 2, characterGroupId: null }],
      },
    ]);
    w.vm.handleOk();
    expect(w.emitted('apply')).toBeUndefined();
  });

  it('does not emit when every line in range has no part at the selected index', () => {
    const w = mountDialog([{ label: 'Line 1', lineTypeLabel: 'Cue', parts: [] }]);
    w.vm.selectedCharacterId = 1;
    expect(w.vm.canApply).toBe(false);
    w.vm.handleOk();
    expect(w.emitted('apply')).toBeUndefined();
  });

  describe('combinedValue (the combined character/group dropdown)', () => {
    it('setting it to a character clears any selected group, and vice versa', () => {
      const w = mountDialog();

      w.vm.combinedValue = 'c:1';
      expect(w.vm.selectedCharacterId).toBe(1);
      expect(w.vm.selectedCharacterGroupId).toBeNull();

      w.vm.combinedValue = 'g:1';
      expect(w.vm.selectedCharacterGroupId).toBe(1);
      expect(w.vm.selectedCharacterId).toBeNull();
    });
  });

  it('reset() clears every selection', () => {
    const w = mountDialog();
    w.vm.selectedPartIndex = 2;
    w.vm.selectedCharacterId = 1;

    w.vm.reset();

    expect(w.vm.selectedPartIndex).toBe(1);
    expect(w.vm.selectedCharacterId).toBeNull();
    expect(w.vm.selectedCharacterGroupId).toBeNull();
  });
});
