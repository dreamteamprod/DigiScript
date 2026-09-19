import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import { useScriptDraft } from './useScriptDraft';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useWebSocketStore } from '@/stores/websocket';

const sendObj = vi.fn((_data: object) => true);
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj, connect: vi.fn() }),
}));

vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

const TestComponent = defineComponent({
  setup() {
    const draft = useScriptDraft();
    return { draft };
  },
  render() {
    return h('div');
  },
});

describe('useScriptDraft', () => {
  let wrappers: VueWrapper[] = [];

  beforeEach(() => {
    setActivePinia(createPinia());
    sendObj.mockClear();
    useWebSocketStore().isConnected = true;
    useWebSocketStore().authenticated = true;
    wrappers = [];
  });

  afterEach(() => {
    // Unmount anything a test forgot to, to keep the composable's module-level
    // refcount from leaking a stale count into the next test.
    wrappers.forEach((w) => {
      if (!w.vm) return;
      w.unmount();
    });
    useScriptDraftStore()._teardown();
  });

  function mountOne(): VueWrapper {
    const wrapper = mount(TestComponent);
    wrappers.push(wrapper);
    return wrapper;
  }

  it('joins the draft room on mount and leaves it on unmount', () => {
    const wrapper = mountOne();
    const store = useScriptDraftStore();

    expect(store.isDraftActive).toBe(true);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });

    wrapper.unmount();

    expect(store.isDraftActive).toBe(false);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
  });

  it('a second concurrent consumer does not rejoin, and the room stays open until the last one unmounts', () => {
    const wrapper1 = mountOne();
    sendObj.mockClear();

    const wrapper2 = mountOne();
    expect(sendObj).not.toHaveBeenCalledWith(expect.objectContaining({ OP: 'JOIN_SCRIPT_ROOM' }));

    const store = useScriptDraftStore();
    wrapper1.unmount();

    // Still active — wrapper2 is still mounted and relying on the room.
    expect(store.isDraftActive).toBe(true);
    expect(sendObj).not.toHaveBeenCalledWith(expect.objectContaining({ OP: 'LEAVE_SCRIPT_ROOM' }));

    wrapper2.unmount();

    expect(store.isDraftActive).toBe(false);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
  });

  it('three concurrent consumers only join once and only leave once the last unmounts', () => {
    const a = mountOne();
    const b = mountOne();
    const c = mountOne();
    sendObj.mockClear();

    a.unmount();
    b.unmount();
    expect(sendObj).not.toHaveBeenCalled();

    const store = useScriptDraftStore();
    expect(store.isDraftActive).toBe(true);

    c.unmount();
    expect(sendObj).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
    expect(store.isDraftActive).toBe(false);
  });

  it('a mount while disconnected does not block a later mount from joining once connected', () => {
    useWebSocketStore().isConnected = false;
    mountOne();
    const store = useScriptDraftStore();
    expect(store.isDraftActive).toBe(false);

    useWebSocketStore().isConnected = true;
    mountOne();

    expect(store.isDraftActive).toBe(true);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('a mount after the room was closed out-of-band joins again', () => {
    mountOne();
    const store = useScriptDraftStore();
    store.roomClosed();
    expect(store.isDraftActive).toBe(false);
    sendObj.mockClear();

    mountOne();

    expect(store.isDraftActive).toBe(true);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('exposes getDraftYdoc reading the live doc from the store', () => {
    const wrapper = mountOne();
    const store = useScriptDraftStore();

    expect(wrapper.vm.draft.getDraftYdoc()).toBe(store.getDraftYdoc());
    expect(wrapper.vm.draft.getDraftYdoc()).not.toBeNull();
  });

  it('exposes getPageSnapshot reading the current page snapshot from the store', () => {
    const wrapper = mountOne();

    expect(wrapper.vm.draft.getPageSnapshot('1')).toEqual([]);
  });

  it('exposes reactive state (as refs) that reflects store changes', async () => {
    const wrapper = mountOne();
    const store = useScriptDraftStore();

    // draft.isDraftSynced etc. are refs (from storeToRefs) — this composable doesn't
    // spread them into the component's top-level setup return, so template-style
    // auto-unwrapping doesn't apply when accessed this way; real consumers either
    // bind them in a <template> (auto-unwrapped there) or read `.value` in script.
    expect(wrapper.vm.draft.isDraftSynced.value).toBe(false);

    store.roomMembers({ members: [{ user_id: 1, username: 'tim', role: 'editor' }] });
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.draft.members.value).toEqual([
      { user_id: 1, username: 'tim', role: 'editor' },
    ]);
  });
});
