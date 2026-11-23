import { describe, it, expect } from 'vitest';
import { mount, type VueWrapper } from '@vue/test-utils';
import BulkActSceneModal from './BulkActSceneModal.vue';

/** This component had no dedicated test before Design E retitled it "Move to
 * Scene" and gave it a new consumer (the selection bar). Same technique as the
 * other dialogs in this directory: drive the refs directly and call handleOk(). */
function mountModal() {
  return mount(BulkActSceneModal, {
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
        { id: 2, show_id: 1, act: 1, name: 'Scene 2', previous_scene: 1, next_scene: null },
      ],
    },
  }) as unknown as VueWrapper & {
    vm: {
      selectedActId: number | null;
      selectedSceneId: number | null;
      canApply: boolean;
      handleOk: () => void;
      reset: () => void;
    };
  };
}

describe('BulkActSceneModal (Move to Scene)', () => {
  it('emits the chosen act and scene', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    w.vm.selectedSceneId = 2;
    w.vm.handleOk();

    const payloads = w.emitted('apply') as [{ actId: number; sceneId: number }][];
    expect(payloads).toHaveLength(1);
    expect(payloads[0]![0]).toEqual({ actId: 1, sceneId: 2 });
  });

  it('does not emit until both act and scene are chosen', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    expect(w.vm.canApply).toBe(false);

    w.vm.handleOk();
    expect(w.emitted('apply')).toBeUndefined();
  });

  it('reset() clears both selections', () => {
    const w = mountModal();
    w.vm.selectedActId = 1;
    w.vm.selectedSceneId = 2;

    w.vm.reset();

    expect(w.vm.selectedActId).toBeNull();
    expect(w.vm.selectedSceneId).toBeNull();
  });
});
