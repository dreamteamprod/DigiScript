import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import CueEditor from './CueEditor.vue';
import CueEmptyState from './CueEmptyState.vue';
import CueToolbar from './CueToolbar.vue';
import ScriptLineCueEditor from './ScriptLineCueEditor.vue';
import { passthrough } from '@/components/show/config/script/testStubs';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import type { FindMatch } from '@/js/cueFind';
import type { ScriptLine } from '@/types/api/script';

enableAutoUnmount(afterEach);

const confirmMock = vi.fn();
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }));
const toastSuccess = vi.fn();
vi.mock('@/js/toast', () => ({
  toast: { success: (m: string) => toastSuccess(m), error: vi.fn() },
}));

const LX = { id: 1, show_id: 1, prefix: 'LX', description: 'Lighting', colour: '#ffd23f' };
const SND = { id: 2, show_id: 1, prefix: 'SND', description: 'Sound', colour: '#2563c9' };

function line(id: number, page: number): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [],
  } as unknown as ScriptLine;
}

function setup(options: { cueTypes?: unknown[]; admin?: boolean; live?: boolean } = {}) {
  const { cueTypes = [LX, SND], admin = true, live = false } = options;
  const showStore = useShowStore();
  const scriptStore = useScriptStore();
  const userStore = useUserStore();
  const systemStore = useSystemStore();

  // The page loads a lot on mount; none of that is under test here.
  const quiet = (store: object, names: string[]) =>
    names.forEach((n) =>
      vi.spyOn(store as never, n as never).mockResolvedValue(undefined as never)
    );
  quiet(userStore, ['getCurrentUser', 'getStageDirectionStyleOverrides', 'getCueColourOverrides']);
  quiet(showStore, [
    'getActList',
    'getSceneList',
    'getCharacterList',
    'getCharacterGroupList',
    'getCueTypes',
    'getShowSessionData',
  ]);
  quiet(scriptStore, ['loadCues', 'getCuts', 'getStageDirectionStyles']);
  vi.spyOn(scriptStore, 'getMaxPage').mockImplementation(async () => {
    scriptStore.maxPage = 3;
    return true;
  });
  const loadPage = vi.spyOn(scriptStore, 'loadScriptPage').mockResolvedValue(undefined);

  showStore.cueTypes = cueTypes as never;
  showStore.currentSession = live ? ({ id: 1 } as never) : null;
  userStore.currentUser = { id: 1, is_admin: admin } as never;
  if (!admin) userStore.currentRbac = { cuetypes: [] } as never;
  systemStore.rbacRoles = [{ key: 'WRITE', value: 2 }];
  scriptStore.script = { '1': [line(1, 1), line(2, 1)], '2': [line(3, 2)] };
  scriptStore.cues = {};
  return { showStore, scriptStore, loadPage };
}

async function mountEditor() {
  const w = mount(CueEditor, {
    global: {
      stubs: {
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BSpinner: true,
        BModal: true,
        BForm: true,
        BFormGroup: true,
        BFormInput: true,
        CueToolbar: true,
        ScriptLineCueEditor: true,
      },
    },
  });
  await flushPromises();
  return w;
}

const toolbar = (w: Awaited<ReturnType<typeof mountEditor>>) => w.findComponent(CueToolbar);
const firstLine = (w: Awaited<ReturnType<typeof mountEditor>>) =>
  w.findAllComponents(ScriptLineCueEditor)[0];

describe('CueEditor', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
    toastSuccess.mockReset();
    localStorage.clear();
  });

  it('shows an empty state, not the script, when there are no cue types', async () => {
    setup({ cueTypes: [] });
    const w = await mountEditor();

    expect(w.findComponent(CueEmptyState).exists()).toBe(true);
    expect(toolbar(w).exists()).toBe(false);
  });

  it('passes the empty state’s choices on to the page', async () => {
    setup({ cueTypes: [] });
    const w = await mountEditor();
    const empty = w.findComponent(CueEmptyState);

    empty.vm.$emit('new-type', { prefix: 'LX', description: 'Lighting', colour: '#ffd23f' });
    empty.vm.$emit('import');

    expect(w.emitted('new-type')?.[0]).toEqual([
      { prefix: 'LX', description: 'Lighting', colour: '#ffd23f' },
    ]);
    expect(w.emitted('import')).toHaveLength(1);
  });

  it('offers editing the cue types to someone who can edit the show, and not to others', async () => {
    setup({ cueTypes: [] });
    const admin = await mountEditor();
    expect(admin.findComponent(CueEmptyState).props('canEditShow')).toBe(true);

    setActivePinia(createPinia());
    setup({ cueTypes: [], admin: false });
    const other = await mountEditor();
    expect(other.findComponent(CueEmptyState).props('canEditShow')).toBe(false);
  });

  it('shows the live-session banner, and the view-only banner when nothing can be written', async () => {
    setup({ live: true, admin: false });
    const w = await mountEditor();

    expect(w.text()).toContain('A show is running. You can add cues');
    expect(w.text()).toContain('View only. You can look at cues but you do not have permission');
  });

  it('shows neither banner for an admin with no live session', async () => {
    setup();
    const w = await mountEditor();

    expect(w.text()).not.toContain('A show is running');
    expect(w.text()).not.toContain('View only');
  });

  it('remembers the filter, and ignores a remembered type that no longer exists', async () => {
    localStorage.setItem('cueEditFilter', '2');
    setup();
    const w = await mountEditor();
    expect(toolbar(w).props('filterTypeId')).toBe(2);

    toolbar(w).vm.$emit('update:filterTypeId', 1);
    await flushPromises();
    expect(localStorage.getItem('cueEditFilter')).toBe('1');
    expect(firstLine(w).props('filterTypeId')).toBe(1);

    setActivePinia(createPinia());
    localStorage.setItem('cueEditFilter', '99');
    setup();
    const stale = await mountEditor();
    expect(toolbar(stale).props('filterTypeId')).toBeNull();
  });

  it('returns the filter to All when a cue of a hidden type is added', async () => {
    setup();
    localStorage.setItem('cueEditFilter', '1');
    const w = await mountEditor();
    expect(toolbar(w).props('filterTypeId')).toBe(1);

    firstLine(w).vm.$emit('added', 2, false);
    await flushPromises();

    expect(toolbar(w).props('filterTypeId')).toBeNull();
  });

  it('keeps the filter when the added cue is of the filtered type', async () => {
    setup();
    localStorage.setItem('cueEditFilter', '1');
    const w = await mountEditor();

    firstLine(w).vm.$emit('added', 1, true);
    await flushPromises();

    expect(toolbar(w).props('filterTypeId')).toBe(1);
  });

  it('opens one card at a time, and a card is only passed to its own line', async () => {
    setup();
    const w = await mountEditor();
    const lines = w.findAllComponents(ScriptLineCueEditor);

    lines[0].vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();
    expect(lines[0].props('activeCard')).toEqual({ lineId: 1, kind: 'add' });

    lines[1].vm.$emit('open', { lineId: 2, kind: 'add' }, null);
    await flushPromises();
    // The first card closed without asking, as nothing in it was a changed group.
    expect(confirmMock).not.toHaveBeenCalled();
    expect(lines[0].props('activeCard')).toEqual({ lineId: 2, kind: 'add' });
  });

  it('asks before leaving a changed group card for another page, and stays if declined', async () => {
    const { loadPage } = setup();
    const w = await mountEditor();
    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();
    firstLine(w).vm.$emit('dirty', true);
    await flushPromises();
    loadPage.mockClear();
    confirmMock.mockResolvedValue(false);

    toolbar(w).vm.$emit('next');
    await flushPromises();

    expect(confirmMock).toHaveBeenCalledWith(
      expect.stringContaining('Discard'),
      expect.objectContaining({ okTitle: 'Discard Changes' })
    );
    expect(toolbar(w).props('currentPage')).toBe(1);
    expect(firstLine(w).props('activeCard')).toEqual({ lineId: 1, kind: 'add' });
    expect(loadPage).not.toHaveBeenCalled();
  });

  it('changes page and closes the changed group card when the discard is confirmed', async () => {
    setup();
    const w = await mountEditor();
    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();
    firstLine(w).vm.$emit('dirty', true);
    await flushPromises();
    confirmMock.mockResolvedValue(true);

    toolbar(w).vm.$emit('next');
    await flushPromises();

    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(toolbar(w).props('currentPage')).toBe(2);
    expect(firstLine(w).props('activeCard')).toBeNull();
  });

  it('changes page without asking when nothing in the card would be lost', async () => {
    setup();
    const w = await mountEditor();
    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();

    toolbar(w).vm.$emit('next');
    await flushPromises();

    expect(confirmMock).not.toHaveBeenCalled();
    expect(toolbar(w).props('currentPage')).toBe(2);
    expect(firstLine(w).props('activeCard')).toBeNull();
  });

  it('asks before opening another card over a changed group card, and keeps it if declined', async () => {
    setup();
    const w = await mountEditor();
    const lines = w.findAllComponents(ScriptLineCueEditor);
    lines[0].vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();
    lines[0].vm.$emit('dirty', true);
    await flushPromises();
    confirmMock.mockResolvedValue(false);

    lines[1].vm.$emit('open', { lineId: 2, kind: 'add' }, null);
    await flushPromises();

    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(lines[0].props('activeCard')).toEqual({ lineId: 1, kind: 'add' });
  });

  it('asks before cancelling a changed group card, but not an unchanged one', async () => {
    setup();
    const w = await mountEditor();
    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();

    firstLine(w).vm.$emit('cancel-card');
    await flushPromises();
    expect(confirmMock).not.toHaveBeenCalled();
    expect(firstLine(w).props('activeCard')).toBeNull();

    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'add' }, null);
    await flushPromises();
    firstLine(w).vm.$emit('dirty', true);
    await flushPromises();
    confirmMock.mockResolvedValue(true);
    firstLine(w).vm.$emit('cancel-card');
    await flushPromises();
    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(firstLine(w).props('activeCard')).toBeNull();
  });

  it('closes the card and says so when the cue being edited was removed elsewhere', async () => {
    const { scriptStore } = setup();
    scriptStore.cues = {
      '1': [
        { id: 5, cue_type_id: 1, ident: '14', group_id: null, sort_order: null, line_position: 1 },
      ],
    };
    const w = await mountEditor();
    firstLine(w).vm.$emit('open', { lineId: 1, kind: 'edit-cue', cueId: 5 }, null);
    await flushPromises();

    firstLine(w).vm.$emit('target-gone');
    await flushPromises();

    expect(firstLine(w).props('activeCard')).toBeNull();
    expect(w.text()).toContain(
      'LX 14 was changed or removed by someone else, so the card was closed.'
    );
  });

  it('opens a found cue’s page, marks its line and says where it went', async () => {
    const { loadPage } = setup();
    localStorage.setItem('cueEditFilter', '2');
    const w = await mountEditor();
    loadPage.mockClear();
    const match: FindMatch = {
      cue: { id: 5, ident: '14', cue_type_id: 1 },
      cue_type: LX,
      location: { page: 2, line_id: 3, act_id: 1, scene_id: 1 },
    };

    toolbar(w).vm.$emit('jump', match);
    await flushPromises();

    expect(toolbar(w).props('currentPage')).toBe(2);
    expect(loadPage).toHaveBeenCalledWith(2);
    // The filter would have hidden the cue we jumped to.
    expect(toolbar(w).props('filterTypeId')).toBeNull();
    expect(firstLine(w).props('highlightLineId')).toBe(3);
    expect(toastSuccess).toHaveBeenCalledWith('Jumped to LX 14 on page 2');
  });

  it('remembers the page', async () => {
    setup();
    const w = await mountEditor();

    toolbar(w).vm.$emit('next');
    await flushPromises();

    expect(localStorage.getItem('cueEditPage')).toBe('2');
  });

  it('does not go past the last page or before the first', async () => {
    setup();
    const w = await mountEditor();

    toolbar(w).vm.$emit('prev');
    await flushPromises();
    expect(toolbar(w).props('currentPage')).toBe(1);

    toolbar(w).vm.$emit('next');
    toolbar(w).vm.$emit('next');
    await flushPromises();
    toolbar(w).vm.$emit('next');
    await flushPromises();
    expect(toolbar(w).props('currentPage')).toBe(3);
  });
});
