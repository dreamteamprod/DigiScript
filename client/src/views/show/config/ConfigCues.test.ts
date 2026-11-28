/* eslint-disable vue/one-component-per-file -- small inline stubs */
import { afterEach, describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import { defineComponent, h, type PropType } from 'vue';
import ConfigCues from './ConfigCues.vue';
import { passthrough } from '@/components/show/config/script/testStubs';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
import CueEditor from '@/components/show/config/cues/CueEditor.vue';
import type { CueType } from '@/types/api/cues';

// Renders the head/cell slots the view uses for its action buttons.
const TableStub = defineComponent({
  props: { items: { type: Array as PropType<unknown[]>, default: () => [] } },
  render() {
    return h('div', [
      h('div', { class: 'head' }, this.$slots['head(btn)']?.({})),
      ...this.items.map((item) => h('div', { class: 'row' }, this.$slots['cell(btn)']?.({ item }))),
    ]);
  },
});

const RBAC_ROLES = [
  { key: 'READ', value: 1 },
  { key: 'WRITE', value: 2 },
  { key: 'EXECUTE', value: 4 },
];

function mountView() {
  return mount(ConfigCues, {
    global: {
      directives: { bModal: {} },
      stubs: {
        CueEditor: true,
        CueCountStats: true,
        PaginationControls: true,
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BTabs: passthrough('div'),
        BTab: passthrough('div'),
        BTable: TableStub,
        BButton: passthrough('button'),
        BButtonGroup: passthrough('div'),
        BModal: true,
        BForm: true,
        BFormGroup: true,
        BFormInput: true,
        BFormInvalidFeedback: true,
        BSpinner: true,
        BCard: true,
        BCardHeader: true,
        BCollapse: true,
        IMdiChevronUp: true,
        IMdiChevronDown: true,
      },
    },
  });
}

describe('ConfigCues cue type actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useSystemStore().rbacRoles = RBAC_ROLES;
    const showStore = useShowStore();
    vi.spyOn(showStore, 'getCueTypes').mockResolvedValue(undefined as never);
    showStore.cueTypes = [
      { id: 1, prefix: 'LX', description: 'Lighting', colour: '#ff0000' } as CueType,
    ];
  });

  function setRbac(show: number | null, cuetypes: number | null) {
    const rbac: Record<string, [number, number][]> = {};
    if (show != null) rbac.shows = [[1, show]];
    if (cuetypes != null) rbac.cuetypes = [[1, cuetypes]];
    const userStore = useUserStore();
    userStore.currentUser = { id: 2, is_admin: false } as never;
    userStore.currentRbac = rbac;
  }

  // The table stub renders only the view's own action slots, so this is exactly the
  // set of buttons the view offers (modals and other tabs are stubbed out).
  const ALL_ACTIONS = ['New Cue Type', 'Import Cue Type', 'Edit', 'Delete'];

  function buttonLabels(w: ReturnType<typeof mountView>): string[] {
    return w.findAll('button').map((b) => b.text().trim());
  }

  it('shows New, Import, Edit and Delete to someone who can edit the show', () => {
    setRbac(2, 2);

    expect(buttonLabels(mountView())).toEqual(ALL_ACTIONS);
  });

  it('hides every action from a cue editor who cannot edit the show', () => {
    // Can write a cue type, but only has READ on the show: the server returns 403
    // for cue type create/update/delete, so the buttons must not be offered.
    setRbac(1, 2);
    expect(useSystemStore().isCueEditor).toBe(true);
    expect(useSystemStore().isShowEditor).toBe(false);

    expect(buttonLabels(mountView())).toEqual([]);
  });

  it('shows the actions to an admin', () => {
    setRbac(null, null);
    useUserStore().currentUser = { id: 1, is_admin: true } as never;

    expect(buttonLabels(mountView())).toEqual(ALL_ACTIONS);
  });
});

// ── The empty state on Script Cues hands off to the Cue Types tab ───────────

const TabsStub = defineComponent({
  props: { index: { type: Number, default: 0 } },
  emits: ['update:index'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});
const shown: string[] = [];
const ModalStub = defineComponent({
  props: { id: { type: String, default: '' } },
  emits: ['show', 'hide', 'ok'],
  setup(props, { expose, emit, slots }) {
    expose({
      show: () => {
        shown.push(props.id);
        emit('show');
      },
      hide: () => emit('hide'),
    });
    return () => h('div', { 'data-modal': props.id }, slots.default?.());
  },
});
const InputStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  setup(props) {
    return () => h('input', { value: props.modelValue });
  },
});

function mountForHandoff() {
  return mount(ConfigCues, {
    global: {
      directives: { bModal: {} },
      stubs: {
        CueEditor: true,
        CueCountStats: true,
        PaginationControls: true,
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BTabs: TabsStub,
        BTab: passthrough('div'),
        BTable: TableStub,
        BButton: passthrough('button'),
        BButtonGroup: passthrough('div'),
        BModal: ModalStub,
        BForm: passthrough('form'),
        BFormGroup: passthrough('div'),
        BFormInput: InputStub,
        BFormInvalidFeedback: true,
        BSpinner: true,
        BCard: true,
        BCardHeader: true,
        BCollapse: true,
        IMdiChevronUp: true,
        IMdiChevronDown: true,
      },
    },
  });
}

describe('ConfigCues hand-off from the Script Cues empty state', () => {
  enableAutoUnmount(afterEach);

  beforeEach(() => {
    setActivePinia(createPinia());
    shown.length = 0;
    useSystemStore().rbacRoles = RBAC_ROLES;
    useUserStore().currentUser = { id: 1, is_admin: true } as never;
    const showStore = useShowStore();
    vi.spyOn(showStore, 'getCueTypes').mockResolvedValue(undefined as never);
    vi.spyOn(showStore, 'getImportableCueTypes').mockResolvedValue({ cue_type_groups: [] });
    showStore.cueTypes = [];
  });

  const tabIndex = (w: ReturnType<typeof mountForHandoff>) =>
    w.findComponent(TabsStub).props('index');
  const field = (w: ReturnType<typeof mountForHandoff>, modal: string, index: number) =>
    (w.find(`[data-modal="${modal}"]`).findAll('input')[index].element as HTMLInputElement).value;

  it('starts on the Script Cues tab', () => {
    expect(tabIndex(mountForHandoff())).toBe(0);
  });

  it('a suggested type opens the Cue Types tab and the new type form, filled in', async () => {
    const w = mountForHandoff();

    w.findComponent(CueEditor).vm.$emit('new-type', {
      prefix: 'LX',
      description: 'Lighting',
      colour: '#ffd23f',
    });
    await flushPromises();

    expect(tabIndex(w)).toBe(1);
    expect(shown).toEqual(['new-cue-type']);
    expect(field(w, 'new-cue-type', 0)).toBe('LX');
    expect(field(w, 'new-cue-type', 1)).toBe('Lighting');
    expect(field(w, 'new-cue-type', 2)).toBe('#ffd23f');
  });

  it('"New Cue Type" with no suggestion opens the form empty', async () => {
    const w = mountForHandoff();

    w.findComponent(CueEditor).vm.$emit('new-type', null);
    await flushPromises();

    expect(tabIndex(w)).toBe(1);
    expect(shown).toEqual(['new-cue-type']);
    expect(field(w, 'new-cue-type', 0)).toBe('');
    expect(field(w, 'new-cue-type', 2)).toBe('#000000');
  });

  it('uses a suggestion once: the next time the form opens it is empty again', async () => {
    const w = mountForHandoff();
    w.findComponent(CueEditor).vm.$emit('new-type', {
      prefix: 'SND',
      description: 'Sound',
      colour: '#2563c9',
    });
    await flushPromises();
    expect(field(w, 'new-cue-type', 0)).toBe('SND');

    w.findComponent(CueEditor).vm.$emit('new-type', null);
    await flushPromises();

    expect(field(w, 'new-cue-type', 0)).toBe('');
  });

  it('"Import from Another Show" opens the Cue Types tab and the import dialog', async () => {
    const w = mountForHandoff();

    w.findComponent(CueEditor).vm.$emit('import');
    await flushPromises();

    expect(tabIndex(w)).toBe(1);
    expect(shown).toEqual(['import-cue-type-modal']);
    expect(useShowStore().getImportableCueTypes).toHaveBeenCalledTimes(1);
  });
});
