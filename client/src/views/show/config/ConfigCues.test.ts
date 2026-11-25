import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { defineComponent, h, type PropType } from 'vue';
import ConfigCues from './ConfigCues.vue';
import { passthrough } from '@/components/show/config/script/testStubs';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
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

  it('shows New, Import, Edit and Delete to someone who can edit the show', () => {
    setRbac(2, 2);
    const w = mountView();

    expect(w.text()).toContain('New Cue Type');
    expect(w.text()).toContain('Import Cue Type');
    expect(w.text()).toContain('Edit');
    expect(w.text()).toContain('Delete');
  });

  it('hides every action from a cue editor who cannot edit the show', () => {
    // Can write a cue type, but only has READ on the show: the server returns 403
    // for cue type create/update/delete, so the buttons must not be offered.
    setRbac(1, 2);
    expect(useSystemStore().isCueEditor).toBe(true);
    expect(useSystemStore().isShowEditor).toBe(false);
    const w = mountView();

    expect(w.text()).not.toContain('New Cue Type');
    expect(w.text()).not.toContain('Import Cue Type');
    expect(w.text()).not.toContain('Edit');
    expect(w.text()).not.toContain('Delete');
  });

  it('shows the actions to an admin', () => {
    setRbac(null, null);
    useUserStore().currentUser = { id: 1, is_admin: true } as never;
    const w = mountView();

    expect(w.text()).toContain('New Cue Type');
    expect(w.text()).toContain('Delete');
  });
});
