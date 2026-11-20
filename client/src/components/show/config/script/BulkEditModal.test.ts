import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import BulkEditModal from './BulkEditModal.vue';
import type { BulkEditPayload } from '@/types/bulkEdit';

/**
 * bootstrap-vue-next components render unresolved (a harmless warning, not a
 * failure) with no global registration in this test environment — the same
 * as every other spec in this directory that mounts a component built on
 * them. These tests never assert on the rendered form controls; they drive
 * the underlying refs directly (the same `vm(w)` technique used throughout
 * CollabScriptEditor.test.ts for a `<script setup>` component's
 * non-exposed internals) and call handleOk() to exercise the actual emit
 * logic under test, rather than a hand-constructed payload.
 */
function mountModal() {
  return mount(BulkEditModal, {
    props: {
      previousLineOfStart: null,
      nextLineOfEnd: null,
      acts: [
        {
          id: 1,
          show_id: 1,
          name: 'Act 1',
          interval_after: false,
          first_scene: 1,
          previous_act: null,
          next_act: null,
        },
      ],
      scenes: [
        { id: 1, show_id: 1, act: 1, name: 'Scene 1', previous_scene: null, next_scene: null },
      ],
      characters: [
        {
          id: 1,
          show_id: 1,
          played_by: null,
          name: 'Alice',
          description: null,
          cast_member: null,
        },
      ],
      characterGroups: [{ id: 1, show_id: 1, name: 'Chorus', description: null, characters: [] }],
    },
  }) as unknown as VueWrapper & {
    vm: {
      selectedActId: number | null;
      selectedSceneId: number | null;
      selectedPartIndex: number | null;
      selectedCharacterId: number | null;
      selectedCharacterGroupId: number | null;
      combinedValue: string | null;
      handleOk: () => void;
      reset: () => void;
    };
  };
}

describe('BulkEditModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('emits actScene only when just act/scene are filled', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    w.vm.selectedSceneId = 1;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [BulkEditPayload][];
    expect(payloads).toHaveLength(1);
    expect(payloads[0]![0]).toEqual({ actScene: { actId: 1, sceneId: 1 }, assignee: null });
  });

  it('emits assignee only when just a part/character are filled', () => {
    const w = mountModal();
    w.vm.selectedPartIndex = 2;
    w.vm.selectedCharacterId = 1;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [BulkEditPayload][];
    expect(payloads).toHaveLength(1);
    expect(payloads[0]![0]).toEqual({
      actScene: null,
      assignee: { partIndex: 2, characterId: 1, characterGroupId: null },
    });
  });

  it('emits both when act/scene and character are both filled', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    w.vm.selectedSceneId = 1;
    w.vm.selectedPartIndex = 1;
    w.vm.selectedCharacterGroupId = 1;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [BulkEditPayload][];
    expect(payloads[0]![0]).toEqual({
      actScene: { actId: 1, sceneId: 1 },
      assignee: { partIndex: 1, characterId: null, characterGroupId: 1 },
    });
  });

  it('emits assignee with a character group, selected in isolation', () => {
    const w = mountModal();
    w.vm.selectedPartIndex = 3;
    w.vm.selectedCharacterGroupId = 1;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [BulkEditPayload][];
    expect(payloads[0]![0]).toEqual({
      actScene: null,
      assignee: { partIndex: 3, characterId: null, characterGroupId: 1 },
    });
  });

  it('does not emit at all when nothing is selected', () => {
    const w = mountModal();

    w.vm.handleOk();

    expect(w.emitted('apply')).toBeUndefined();
  });

  it('does not emit at all when neither section is complete', () => {
    const w = mountModal();
    w.vm.selectedActId = 1; // scene left unset — act/scene incomplete

    w.vm.handleOk();

    expect(w.emitted('apply')).toBeUndefined();
  });

  it('does not emit a half-filled section — only a part with no character selected', () => {
    const w = mountModal();
    w.vm.selectedPartIndex = 1; // no character or group selected

    w.vm.handleOk();

    expect(w.emitted('apply')).toBeUndefined();
  });

  describe('combinedValue (the combined character/group dropdown)', () => {
    it('reading it reflects whichever of character/group is currently selected', () => {
      const w = mountModal();
      expect(w.vm.combinedValue).toBeNull();

      w.vm.selectedCharacterId = 1;
      expect(w.vm.combinedValue).toBe('c:1');

      w.vm.selectedCharacterId = null;
      w.vm.selectedCharacterGroupId = 1;
      expect(w.vm.combinedValue).toBe('g:1');
    });

    it('setting it to a character clears any selected group, and vice versa', () => {
      const w = mountModal();

      w.vm.combinedValue = 'c:1';
      expect(w.vm.selectedCharacterId).toBe(1);
      expect(w.vm.selectedCharacterGroupId).toBeNull();

      w.vm.combinedValue = 'g:1';
      expect(w.vm.selectedCharacterGroupId).toBe(1);
      expect(w.vm.selectedCharacterId).toBeNull();

      w.vm.combinedValue = null;
      expect(w.vm.selectedCharacterId).toBeNull();
      expect(w.vm.selectedCharacterGroupId).toBeNull();
    });

    it('handleOk emits correctly when the assignment was made through combinedValue', () => {
      const w = mountModal();
      w.vm.selectedPartIndex = 1;
      w.vm.combinedValue = 'c:1';
      w.vm.handleOk();

      const payloads = w.emitted('apply') as [BulkEditPayload][];
      expect(payloads[0]![0]).toEqual({
        actScene: null,
        assignee: { partIndex: 1, characterId: 1, characterGroupId: null },
      });
    });
  });

  it('reset() clears every selection', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    w.vm.selectedSceneId = 1;
    w.vm.selectedPartIndex = 1;
    w.vm.selectedCharacterId = 1;

    w.vm.reset();

    expect(w.vm.selectedActId).toBeNull();
    expect(w.vm.selectedSceneId).toBeNull();
    expect(w.vm.selectedPartIndex).toBeNull();
    expect(w.vm.selectedCharacterId).toBeNull();
    expect(w.vm.selectedCharacterGroupId).toBeNull();
  });
});
