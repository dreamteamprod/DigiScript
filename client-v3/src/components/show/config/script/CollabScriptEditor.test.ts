/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import CollabScriptEditor from './CollabScriptEditor.vue';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useWebSocketStore } from '@/stores/websocket';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';
import type { ScriptLine } from '@/types/api/script';

const sendObj = vi.fn((_data: object) => true);
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj, connect: vi.fn() }),
}));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

// The viewer is stubbed to a bare row so a row's DOM identity can be tracked.
const ViewerStub = defineComponent({
  props: { line: { type: Object, required: true }, lineIndex: { type: Number, default: 0 } },
  render() {
    return h('div', { class: 'row-stub' }, (this.line as { _uid?: string })._uid ?? 'rest');
  },
});
// bootstrap-vue-next components are not registered in unit tests; only the alert needs
// real show/hide behaviour, the rest can render as plain elements.
const AlertStub = defineComponent({
  props: { modelValue: { type: Boolean, default: false } },
  render() {
    return this.modelValue ? h('div', { class: 'alert-stub' }, this.$slots.default?.()) : null;
  },
});

/** Plain-element stand-ins for the Bootstrap components (not registered in unit tests). */
function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}
const bootstrapStubs = {
  BContainer: passthrough('div'),
  BRow: passthrough('div'),
  BCol: passthrough('div'),
  BButton: passthrough('button'),
  BButtonGroup: passthrough('div'),
  BSpinner: passthrough('span'),
  BModal: passthrough('div'),
  BForm: passthrough('form'),
  BFormGroup: passthrough('div'),
  BFormInput: passthrough('span'),
};

function snap(uid: string, id: number | null = null): SnapshotLine {
  return {
    _id: id === null ? uid : String(id),
    _uid: uid,
    id,
    act_id: 1,
    scene_id: 1,
    line_type: 1,
    stage_direction_style_id: null,
    parts: [],
  };
}

function restLine(id: number): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: 1,
    stage_direction_style_id: null,
    line_parts: [],
  };
}

const sentOps = (): string[] => sendObj.mock.calls.map((c) => (c[0] as { OP: string }).OP);
const buttons = (w: VueWrapper) => w.findAll('button');
const button = (w: VueWrapper, text: string) =>
  buttons(w).find((b) => b.text().trim() === text || b.text().includes(text));

describe('CollabScriptEditor', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    const ws = useWebSocketStore();
    ws.isConnected = true;
    ws.authenticated = true;
    ws.internalUUID = 'me';
    useSystemStore().settings = { collaborative_script_editing: true } as never;
    useSystemStore().rbacRoles = [];
    for (const m of [
      'getActList',
      'getSceneList',
      'getCharacterList',
      'getCharacterGroupList',
    ] as const) {
      vi.spyOn(useShowStore(), m).mockResolvedValue();
    }
    vi.spyOn(useScriptStore(), 'getStageDirectionStyles').mockResolvedValue();
    vi.spyOn(useScriptStore(), 'loadScriptPage').mockResolvedValue();
    vi.spyOn(useScriptConfigStore(), 'getScriptConfigStatus').mockResolvedValue();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    useScriptDraftStore()._teardown();
  });

  async function mountEditor(): Promise<VueWrapper> {
    wrapper = mount(CollabScriptEditor, {
      global: {
        components: bootstrapStubs,
        stubs: { ScriptLineViewer: ViewerStub, BAlert: AlertStub },
      },
    });
    await flushPromises();
    return wrapper;
  }

  function becomeEditor(): void {
    useScriptConfigStore().editors = [{ internal_id: 'me', username: 'admin' }];
  }

  function syncDraft(pages: Record<string, SnapshotLine[]>): void {
    const draft = useScriptDraftStore();
    draft.status = 'synced';
    draft.pageSnapshots = pages;
  }

  it('reads saved pages over REST when not an editor and holds no room', async () => {
    useScriptStore().script = { '1': [restLine(1), restLine(2)] };
    useSystemStore().rbacRoles = [];
    const w = await mountEditor();

    expect(w.findAll('.row-stub')).toHaveLength(2);
    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('sends the collab flag when Edit is pressed', async () => {
    const system = useSystemStore();
    vi.spyOn(system, 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();

    await button(w, 'Edit')!.trigger('click');

    expect(sendObj).toHaveBeenCalledWith({ OP: 'REQUEST_SCRIPT_EDIT', DATA: { collab: true } });
  });

  it('joins the draft on mount when already an editor (a reload), showing a spinner until synced', async () => {
    becomeEditor();
    const w = await mountEditor();

    expect(sentOps()).toContain('JOIN_SCRIPT_ROOM');
    expect(useScriptDraftStore().status).toBe('joining');
    expect(w.find('.row-stub').exists()).toBe(false);
    expect(w.find('.alert-stub').exists()).toBe(false);
  });

  it('joins when the server adds us to the editors after mount, and leaves when removed', async () => {
    const w = await mountEditor();
    expect(useScriptDraftStore().isDraftActive).toBe(false);

    becomeEditor();
    await flushPromises();
    expect(useScriptDraftStore().status).toBe('joining');

    useScriptConfigStore().editors = [];
    await flushPromises();
    expect(useScriptDraftStore().isDraftActive).toBe(false);
    expect(w.exists()).toBe(true);
  });

  it('renders the synced draft from snapshots, keyed by _uid', async () => {
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a'), snap('b')], '2': [] });
    await flushPromises();

    expect(w.findAll('.row-stub').map((r) => r.text())).toEqual(['a', 'b']);
  });

  it('keeps a row mounted when a save rewrites its _id (identity is _uid)', async () => {
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a'), snap('b')], '2': [] });
    await flushPromises();
    const rowFor = (uid: string) => w.findAll('.row-stub').find((r) => r.text() === uid)!.element;
    const before = rowFor('a');

    // A save's id patch (same _uid, new DB id) while another editor inserted a line
    // above it: an index key would hand row `a` to the new line.
    useScriptDraftStore().pageSnapshots = {
      '1': [snap('new'), snap('a', 501), snap('b', 502)],
      '2': [],
    };
    await flushPromises();

    expect(rowFor('a')).toBe(before);
    expect(w.findAll('.row-stub').map((r) => r.text())).toEqual(['new', 'a', 'b']);
  });

  it('stops Next Page at the last page that exists (the server-made trailing page)', async () => {
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();

    const next = button(w, 'Next Page')!;
    expect(next.attributes('disabled')).toBeUndefined();
    await next.trigger('click');
    await flushPromises();
    expect(w.text()).toContain('Current Page: 2');
    expect(button(w, 'Next Page')!.attributes('disabled')).toBeDefined();

    // ...and grows with the doc when the server adds a page.
    useScriptDraftStore().pageSnapshots['3'] = [];
    await flushPromises();
    expect(button(w, 'Next Page')!.attributes('disabled')).toBeUndefined();
  });

  it('refuses Go to Page past the last page with a message, and does not navigate', async () => {
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();
    const vm = w.vm as unknown as { pageInputNo: number; goToPage: () => Promise<void> };

    vm.pageInputNo = 9;
    await vm.goToPage();
    await flushPromises();

    expect(w.find('[data-testid="page-error"]').text()).toContain('last page is 2');
    expect(w.text()).toContain('Current Page: 1');
  });

  it('clamps a remembered page that is past the end of the draft', async () => {
    localStorage.setItem('scriptEditPage', '40');
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();

    expect(w.text()).toContain('Current Page: 2');
  });

  it('offers Retry when an editor has no room, and Retry rejoins', async () => {
    becomeEditor();
    const w = await mountEditor();
    // A rejected join tears the room down: still an editor, but no room.
    useScriptDraftStore()._teardown();
    await flushPromises();

    expect(w.find('.alert-stub').exists()).toBe(true);
    sendObj.mockClear();
    await w.find('.alert-stub button').trigger('click');

    expect(sentOps()).toContain('JOIN_SCRIPT_ROOM');
    expect(useScriptDraftStore().status).toBe('joining');
  });

  it('a rejected join (COLLAB_ERROR while joining) shows the real server reason in the Retry alert', async () => {
    becomeEditor();
    const w = await mountEditor();
    expect(useScriptDraftStore().status).toBe('joining');

    useScriptDraftStore().collabError({ error: 'No show loaded' });
    await flushPromises();

    expect(w.find('.alert-stub').text()).toContain('No show loaded');
    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('a failed initial sync unwinds to the Retry alert instead of hanging on the spinner', async () => {
    becomeEditor();
    const w = await mountEditor();
    expect(useScriptDraftStore().status).toBe('joining');

    useScriptDraftStore().yjsSync({ step: 0, payload: 'not-valid-base64!!' });
    await flushPromises();

    expect(w.find('.alert-stub').exists()).toBe(true);
    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('ROOM_CLOSED after a successful sync also lands on Retry, not a stuck view', async () => {
    becomeEditor();
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();

    useScriptDraftStore().roomClosed();
    await flushPromises();

    expect(w.find('.alert-stub').exists()).toBe(true);
  });

  it('Stop Editing sends STOP only — never LEAVE first, which would make the server skip checkpoint/close', async () => {
    becomeEditor();
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();
    sendObj.mockClear();

    await button(w, 'Stop Editing')!.trigger('click');

    // LEAVE_SCRIPT_ROOM first would remove us from room.clients before STOP_SCRIPT_EDIT
    // arrives, so the server's get_room_for_client(self) would return None and skip
    // checkpoint/close entirely — the local draft must not be torn down client-side
    // either, until the server actually says so (ROOM_CLOSED, or editors no longer
    // listing us).
    expect(sentOps()).toEqual(['STOP_SCRIPT_EDIT']);
    expect(useScriptDraftStore().isDraftActive).toBe(true);
  });

  it('Stop Editing as the last editor: ROOM_CLOSED (from the server) tears the draft down', async () => {
    becomeEditor();
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();

    await button(w, 'Stop Editing')!.trigger('click');
    useScriptDraftStore().roomClosed();
    await flushPromises();

    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('Stop Editing with another editor still present: losing editor status tears the draft down', async () => {
    becomeEditor();
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();

    await button(w, 'Stop Editing')!.trigger('click');
    // The server's GET_SCRIPT_CONFIG_STATUS reply no longer lists us.
    useScriptConfigStore().editors = [];
    await flushPromises();

    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('requestEdit tells the user when the frame could not be sent', async () => {
    sendObj.mockReturnValueOnce(false);
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();

    await button(w, 'Edit')!.trigger('click');

    const { toast } = await import('@/js/toast');
    expect(toast.error).toHaveBeenCalledWith('Cannot edit script: not connected to the server');
  });

  it('stopEditing tells the user when the frame could not be sent', async () => {
    becomeEditor();
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    const w = await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    await flushPromises();
    sendObj.mockReturnValueOnce(false);

    await button(w, 'Stop Editing')!.trigger('click');

    const { toast } = await import('@/js/toast');
    expect(toast.error).toHaveBeenCalledWith('Cannot stop editing: not connected to the server');
  });

  it('leaves the room when the component unmounts', async () => {
    becomeEditor();
    await mountEditor();
    syncDraft({ '1': [snap('a')], '2': [] });
    sendObj.mockClear();

    wrapper!.unmount();
    wrapper = null;

    expect(sentOps()).toContain('LEAVE_SCRIPT_ROOM');
    expect(useScriptDraftStore().isDraftActive).toBe(false);
  });

  it('is chosen by the server setting', () => {
    const system = useSystemStore();
    expect(system.isCollabScriptEditing).toBe(true);
    system.settings = {} as never;
    expect(system.isCollabScriptEditing).toBe(false);
    system.settings = { collaborative_script_editing: false } as never;
    expect(system.isCollabScriptEditing).toBe(false);
  });
});
