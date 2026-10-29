/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import ScriptRevisions from './ScriptRevisions.vue';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useWebSocketStore } from '@/stores/websocket';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useConfirm } from '@/composables/useConfirm';
import { toast } from '@/js/toast';
import type { ScriptRevision } from '@/types/api/script';

const confirmMock = vi.fn().mockResolvedValue(true);
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

/** Plain-element stand-ins for Bootstrap components (not registered in unit tests). */
function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}

// A BTable stand-in that actually iterates `items` and renders the component's real
// scoped slots per row, plus the custom foot slot — enough to exercise the Load/Edit/
// Delete button logic without pulling in the real bootstrap-vue-next table.
const TableStub = defineComponent({
  props: { items: { type: Array, default: () => [] } },
  render() {
    const slots = this.$slots as unknown as Record<
      string,
      ((scope: { item: unknown }) => unknown) | undefined
    >;
    const rows = (this.items as unknown[]).map((item) =>
      h('tr', [
        h('td', slots['cell(current)']?.({ item })),
        h('td', slots['cell(previous_revision_id)']?.({ item })),
        h('td', slots['cell(btn)']?.({ item })),
      ])
    );
    const foot = slots['custom-foot']?.({});
    return h('table', [h('tbody', rows), h('tfoot', [h('tr', foot)])]);
  },
});

const ModalStub = defineComponent({
  inheritAttrs: true,
  methods: {
    show() {
      // no-op
    },
    hide() {
      // no-op
    },
  },
  render() {
    return h('div', this.$slots.default?.());
  },
});

const AlertStub = defineComponent({
  props: { modelValue: { type: Boolean, default: false } },
  render() {
    return this.modelValue ? h('div', { class: 'alert-stub' }, this.$slots.default?.()) : null;
  },
});

const bootstrapStubs = {
  BCard: passthrough('div'),
  BCollapse: passthrough('div'),
  BButton: passthrough('button'),
  BButtonGroup: passthrough('div'),
  BTable: TableStub,
  BTr: passthrough('tr'),
  BTd: passthrough('td'),
  BModal: ModalStub,
  BForm: passthrough('form'),
  BFormGroup: passthrough('div'),
  BFormInput: passthrough('span'),
  BFormInvalidFeedback: passthrough('span'),
};

function makeRevision(overrides: Partial<ScriptRevision> = {}): ScriptRevision {
  return {
    id: 1,
    script_id: 1,
    revision: 1,
    created_at: null,
    edited_at: null,
    description: 'Initial',
    previous_revision_id: null,
    has_draft: false,
    ...overrides,
  };
}

describe('ScriptRevisions', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset().mockResolvedValue(true);
    const ws = useWebSocketStore();
    ws.internalUUID = 'me';
    useSystemStore().rbacRoles = [];
    vi.spyOn(useSystemStore(), 'isScriptEditor', 'get').mockReturnValue(true);
    vi.spyOn(useScriptConfigStore(), 'getScriptConfigStatus').mockResolvedValue();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  async function mountRevisions(): Promise<VueWrapper> {
    wrapper = mount(ScriptRevisions, {
      global: {
        components: bootstrapStubs,
        stubs: {
          BAlert: AlertStub,
          RevisionGraph: true,
          RevisionDetailModal: true,
        },
      },
    });
    await flushPromises();
    return wrapper;
  }

  function button(w: VueWrapper, text: string) {
    return w.findAll('button').find((b) => b.text().trim() === text);
  }

  describe('collaborative mode', () => {
    beforeEach(() => {
      useSystemStore().settings = { collaborative_script_editing: true } as never;
    });

    it('disables Load and New Revision while the current revision has an unsaved draft', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 2;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1 }),
        makeRevision({ id: 2, revision: 2, has_draft: true }),
      ];
      const w = await mountRevisions();

      expect(button(w, 'Load')?.attributes('disabled')).toBeDefined();
      expect(button(w, 'New Revision')?.attributes('disabled')).toBeDefined();
    });

    it('leaves Load and New Revision enabled when the current revision has no draft', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 2;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1 }),
        makeRevision({ id: 2, revision: 2, has_draft: false }),
      ];
      const w = await mountRevisions();

      expect(button(w, 'Load')?.attributes('disabled')).toBeUndefined();
      expect(button(w, 'New Revision')?.attributes('disabled')).toBeUndefined();
    });

    it("disables a specific row's Edit/Delete when that row itself has a draft, even if the current revision does not", async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1, has_draft: false }),
        makeRevision({ id: 2, revision: 2, has_draft: true }),
      ];
      const w = await mountRevisions();

      // Row 2 (revision !== 1) renders its own Edit/Delete buttons.
      expect(button(w, 'Edit')?.attributes('disabled')).toBeDefined();
      expect(button(w, 'Delete')?.attributes('disabled')).toBeDefined();
    });

    it("leaves a row's Edit/Delete enabled when nothing is locked", async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1, has_draft: false }),
        makeRevision({ id: 2, revision: 2, has_draft: false }),
      ];
      const w = await mountRevisions();

      expect(button(w, 'Edit')?.attributes('disabled')).toBeUndefined();
      expect(button(w, 'Delete')?.attributes('disabled')).toBeUndefined();
    });

    it('shows the Discard Draft banner only while the current revision has a draft', async () => {
      // Two other BAlerts (inside the New Revision / branch modals, always rendered
      // by the test's unconditional BModal stub) also produce `.alert-stub` elements
      // regardless of a draft — the Discard Draft button is the unambiguous signal.
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: false })];
      const w = await mountRevisions();
      expect(button(w, 'Discard Draft')).toBeUndefined();

      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: true })];
      await flushPromises();
      expect(button(w, 'Discard Draft')).toBeDefined();
    });

    it('names other editors in the discard warning, since discard is room-wide', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: true })];
      useScriptConfigStore().editors = [{ internal_id: 'other', username: 'alex' }];
      const w = await mountRevisions();

      await button(w, 'Discard Draft')?.trigger('click');
      await flushPromises();

      expect(confirmMock).toHaveBeenCalledWith(
        expect.stringContaining('alex is also editing'),
        expect.objectContaining({ title: 'Discard Draft' })
      );
    });

    it('discards the draft over REST when confirmed', async () => {
      const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 200 })));
      vi.stubGlobal('fetch', fetchMock);
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: true })];
      const w = await mountRevisions();

      await button(w, 'Discard Draft')?.trigger('click');
      await flushPromises();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toContain('/api/v1/show/script/draft');
      expect(init.method).toBe('DELETE');
      expect(toast.success).toHaveBeenCalled();
    });

    it('does not discard when the confirmation is cancelled', async () => {
      confirmMock.mockResolvedValue(false);
      const fetchMock = vi.fn();
      vi.stubGlobal('fetch', fetchMock);
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: true })];
      const w = await mountRevisions();

      await button(w, 'Discard Draft')?.trigger('click');
      await flushPromises();

      expect(fetchMock).not.toHaveBeenCalled();
    });
  });

  describe('legacy mode (unchanged behaviour)', () => {
    beforeEach(() => {
      useSystemStore().settings = { collaborative_script_editing: false } as never;
    });

    // The Load button only renders for a row that is NOT the current revision (the
    // current one shows a checkmark instead) — a second row is needed to see it.
    it('enables Load when nobody is editing', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1 }),
        makeRevision({ id: 2, revision: 2 }),
      ];
      useScriptConfigStore().editStatus = { canRequestEdit: true, currentEditor: null };
      const w = await mountRevisions();

      expect(button(w, 'Load')?.attributes('disabled')).toBeUndefined();
    });

    it('disables Load while a different user is editing', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1 }),
        makeRevision({ id: 2, revision: 2 }),
      ];
      useScriptConfigStore().editStatus = { canRequestEdit: false, currentEditor: 'someone-else' };
      const w = await mountRevisions();

      expect(button(w, 'Load')?.attributes('disabled')).toBeDefined();
    });

    it('still allows the current editor themselves to act', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [
        makeRevision({ id: 1, revision: 1 }),
        makeRevision({ id: 2, revision: 2 }),
      ];
      useScriptConfigStore().editStatus = { canRequestEdit: false, currentEditor: 'me' };
      const w = await mountRevisions();

      expect(button(w, 'Load')?.attributes('disabled')).toBeUndefined();
    });

    it('never shows the Discard Draft banner', async () => {
      const showStore = useShowStore();
      showStore.currentRevision = 1;
      showStore.scriptRevisions = [makeRevision({ id: 1, revision: 1, has_draft: true })];
      const w = await mountRevisions();

      expect(button(w, 'Discard Draft')).toBeUndefined();
    });
  });
});
