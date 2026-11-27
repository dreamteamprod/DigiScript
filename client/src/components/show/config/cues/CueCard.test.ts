import { afterEach, describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import CueCard from './CueCard.vue';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { Cue } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';

// Wrappers are attached to the document (for focus checks); unmount them after each test so
// ids from one test can't be matched by the next.
enableAutoUnmount(afterEach);

const confirmMock = vi.fn();
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }));
vi.mock('@/js/toast', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const LX = { id: 1, show_id: 1, prefix: 'LX', description: 'Lighting', colour: '#ffd23f' };
const SND = { id: 2, show_id: 1, prefix: 'SND', description: 'Sound', colour: '#2563c9' };
const VID = { id: 3, show_id: 1, prefix: 'VID', description: 'Video', colour: '#17744f' };

function line(id: number, page = 5): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: id * 10,
        line_id: id,
        part_index: 0,
        character_id: null,
        character_group_id: null,
        line_text: 'Hello there',
      },
    ],
  } as ScriptLine;
}

function cue(id: number, typeId: number, ident: string): Cue {
  return {
    id,
    cue_type_id: typeId,
    ident,
    group_id: null,
    sort_order: null,
    line_position: 1,
  };
}

const L1 = line(101);
const L2 = line(102); // where cues are added
const L3 = line(103);

function setup(options: { admin?: boolean; writable?: number[]; live?: boolean } = {}) {
  const { admin = true, writable = [], live = false } = options;
  const showStore = useShowStore();
  const scriptStore = useScriptStore();
  const userStore = useUserStore();

  showStore.cueTypes = [LX, SND, VID];
  showStore.currentSession = live ? ({ id: 1 } as never) : null;
  userStore.currentUser = { id: 1, is_admin: admin } as never;
  if (!admin) {
    userStore.currentRbac = { cuetypes: writable.map((id) => [id, 2]) } as never;
  }
  // useCuePermissions reads the WRITE mask from the system store's roles.
  useSystemStore().rbacRoles = [
    { key: 'READ', value: 1 },
    { key: 'WRITE', value: 2 },
  ];

  scriptStore.script = { '5': [L1, L2, L3] };
  scriptStore.cues = { '101': [cue(1, 1, '13')], '103': [cue(2, 1, '14')] };
  scriptStore.linePositions = {
    '101': { page: 5, index: 0, act_id: 1, scene_id: 1 },
    '103': { page: 5, index: 2, act_id: 1, scene_id: 1 },
  };
  return { showStore, scriptStore };
}

function mountAdd(typeId: number | null = 1) {
  return mount(CueCard, {
    props: { mode: 'add', line: L2, lineLabel: 'Hello there', typeId },
    attachTo: document.body,
  });
}

const buttonByText = (w: ReturnType<typeof mountAdd>, text: string) =>
  w.findAll('button').find((b) => b.text().trim() === text);

/** Make addNewCue behave like the real one: the cue appears on the line after the reload. */
function fakeAddNewCue(store: ReturnType<typeof useScriptStore>) {
  return vi.spyOn(store, 'addNewCue').mockImplementation(async (c) => {
    const key = String(c.lineId);
    const added = cue(900 + (store.cues[key]?.length ?? 0), c.cueType, c.ident);
    store.$patch({
      cues: { ...store.cues, [key]: [...(store.cues[key] ?? []), added] },
      linePositions: {
        ...store.linePositions,
        [key]: { page: 5, index: 1, act_id: 1, scene_id: 1 },
      },
    });
    return true;
  });
}

describe('CueCard (add)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
  });

  it('suggests a number between its neighbours and labels the nearest cues', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('13.5');
    expect(w.text()).toContain('LX 13');
    expect(w.text()).toContain('above');
    expect(w.text()).toContain('LX 14');
    expect(w.text()).toContain('below');
    expect(buttonByText(w, 'Add LX 13.5')).toBeDefined();
  });

  it('adds with the keyboard alone: Enter on the suggested number', async () => {
    const { scriptStore } = setup();
    const add = fakeAddNewCue(scriptStore);
    const w = mountAdd();
    await flushPromises();

    await w.find('input.cue-number-input').trigger('keydown', { key: 'Enter' });
    await flushPromises();

    expect(add).toHaveBeenCalledWith({ cueType: 1, ident: '13.5', lineId: 102 });
    expect(w.emitted('done')).toHaveLength(1);
  });

  it('"Add and Stay Open" adds 13.5 then offers 13.6 and keeps the card', async () => {
    const { scriptStore } = setup();
    const add = fakeAddNewCue(scriptStore);
    const w = mountAdd();
    await flushPromises();

    await buttonByText(w, 'Add and Stay Open')!.trigger('click');
    await flushPromises();

    expect(add).toHaveBeenCalledWith({ cueType: 1, ident: '13.5', lineId: 102 });
    expect(w.emitted('done')).toBeUndefined();
    expect(w.emitted('added')?.[0]).toEqual([1, true]);
    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('13.6');
  });

  it('never overwrites a number the person typed', async () => {
    const { scriptStore } = setup();
    const w = mountAdd();
    await flushPromises();

    await w.find('input.cue-number-input').setValue('99');
    scriptStore.cues = { ...scriptStore.cues, '103': [cue(2, 1, '14'), cue(3, 1, '20')] };
    await flushPromises();

    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('99');
  });

  it('keeps the card and what was typed when the add fails, and says so', async () => {
    const { scriptStore } = setup();
    vi.spyOn(scriptStore, 'addNewCue').mockResolvedValue(false);
    const w = mountAdd();
    await flushPromises();

    await w.find('input.cue-number-input').setValue('13.5');
    await buttonByText(w, 'Add LX 13.5')!.trigger('click');
    await flushPromises();

    expect(w.emitted('done')).toBeUndefined();
    expect(w.find('[role="alert"]').text()).toContain('LX 13.5 was not added');
    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('13.5');
    expect(buttonByText(w, 'Add LX 13.5')!.attributes('disabled')).toBeUndefined();
  });

  it('keeps the card when the request throws', async () => {
    const { scriptStore } = setup();
    vi.spyOn(scriptStore, 'addNewCue').mockRejectedValue(new Error('network'));
    const w = mountAdd();
    await flushPromises();

    await buttonByText(w, 'Add LX 13.5')!.trigger('click');
    await flushPromises();

    expect(w.emitted('done')).toBeUndefined();
    expect(w.find('[role="alert"]').exists()).toBe(true);
  });

  it('disables the controls while the request is in flight', async () => {
    const { scriptStore } = setup();
    let release: (value: boolean) => void = () => {};
    vi.spyOn(scriptStore, 'addNewCue').mockReturnValue(
      new Promise<boolean>((resolve) => {
        release = resolve;
      })
    );
    const w = mountAdd();
    await flushPromises();

    await buttonByText(w, 'Add LX 13.5')!.trigger('click');
    expect(buttonByText(w, 'Adding…')!.attributes('disabled')).toBeDefined();
    expect(buttonByText(w, 'Cancel')!.attributes('disabled')).toBeDefined();
    expect(w.find('input.cue-number-input').attributes('disabled')).toBeDefined();

    release(true);
    await flushPromises();
  });

  it('warns about a duplicate number with its page but still allows saving', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await w.find('input.cue-number-input').setValue('13');

    expect(w.text()).toContain('LX 13 is already used on page 5. You can still save.');
    expect(buttonByText(w, 'Add LX 13')!.attributes('disabled')).toBeUndefined();
  });

  it('asks for a type first when none is chosen, and cannot add yet', async () => {
    setup();
    const w = mountAdd(null);
    await flushPromises();

    expect(w.text()).toContain('Choose a cue type to get a suggested number.');
    expect(buttonByText(w, 'Add Cue')!.attributes('disabled')).toBeDefined();
    expect(buttonByText(w, 'Add and Stay Open')!.attributes('disabled')).toBeDefined();
  });

  it('shows a type it cannot write as view only and cannot be chosen', async () => {
    setup({ admin: false, writable: [1] });
    const w = mountAdd(1);
    await flushPromises();

    const radios = w.findAll('[role="radio"]');
    expect(radios).toHaveLength(3);
    // Writable types come first; the others are disabled and say why.
    expect(radios[0].text()).toContain('LX');
    expect(radios[1].attributes('disabled')).toBeDefined();
    expect(radios[1].text()).toContain('View only');
  });

  it('cancels with Escape', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await w.find('section').trigger('keydown', { key: 'Escape' });

    expect(w.emitted('cancel')).toHaveLength(1);
  });

  it('gives each radio a name and marks exactly the chosen one', async () => {
    setup();
    const w = mountAdd(2);
    await flushPromises();

    const checked = w
      .findAll('[role="radio"]')
      .filter((r) => r.attributes('aria-checked') === 'true');
    expect(checked).toHaveLength(1);
    expect(checked[0].text()).toContain('SND');
    expect(w.find('[role="radiogroup"]').exists()).toBe(true);
  });
});

describe('CueCard (edit)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
  });

  const target = cue(2, 1, '14');
  const mountEdit = () =>
    mount(CueCard, {
      props: { mode: 'edit', line: L3, lineLabel: 'Hello there', cue: target, typeId: null },
      attachTo: document.body,
    });

  it('saves a changed number and a changed type', async () => {
    const { scriptStore } = setup();
    const edit = vi.spyOn(scriptStore, 'editCue').mockResolvedValue(true);
    const w = mountEdit();
    await flushPromises();

    expect(buttonByText(w as never, 'Save Cue')!.attributes('disabled')).toBeDefined();
    await w.find('input.cue-number-input').setValue('15');
    await w.findAll('[role="radio"]')[1].trigger('click');
    await buttonByText(w as never, 'Save Cue')!.trigger('click');
    await flushPromises();

    expect(edit).toHaveBeenCalledWith({ cueId: 2, cueType: 2, ident: '15', lineId: 103 });
    expect(w.emitted('done')).toHaveLength(1);
  });

  it('asks before deleting, with the agreed wording, then deletes', async () => {
    const { scriptStore } = setup();
    const del = vi.spyOn(scriptStore, 'deleteCue').mockResolvedValue(true);
    confirmMock.mockResolvedValue(true);
    const w = mountEdit();
    await flushPromises();

    await buttonByText(w as never, 'Delete Cue')!.trigger('click');
    await flushPromises();

    expect(confirmMock).toHaveBeenCalledWith(
      expect.stringContaining('Delete LX 14?'),
      expect.objectContaining({ title: 'Delete Cue', okTitle: 'Delete Cue' })
    );
    expect(confirmMock.mock.calls[0][0]).toContain('Other revisions keep it.');
    expect(del).toHaveBeenCalledWith({ cueId: 2, lineId: 103 });
    expect(w.emitted('done')).toHaveLength(1);
  });

  it('does not delete when the confirmation is declined', async () => {
    const { scriptStore } = setup();
    const del = vi.spyOn(scriptStore, 'deleteCue').mockResolvedValue(true);
    confirmMock.mockResolvedValue(false);
    const w = mountEdit();
    await flushPromises();

    await buttonByText(w as never, 'Delete Cue')!.trigger('click');
    await flushPromises();

    expect(del).not.toHaveBeenCalled();
    expect(w.emitted('done')).toBeUndefined();
  });

  it('disables Save and Delete during a live session', async () => {
    setup({ live: true });
    const w = mountEdit();
    await flushPromises();

    await w.find('input.cue-number-input').setValue('15');
    expect(buttonByText(w as never, 'Save Cue')!.attributes('disabled')).toBeDefined();
    expect(buttonByText(w as never, 'Delete Cue')!.attributes('disabled')).toBeDefined();
  });

  it('updates when a session starts with the card open', async () => {
    const { showStore } = setup();
    const w = mountEdit();
    await flushPromises();
    await w.find('input.cue-number-input').setValue('15');
    expect(buttonByText(w as never, 'Delete Cue')!.attributes('disabled')).toBeUndefined();

    showStore.currentSession = { id: 7 } as never;
    await flushPromises();

    expect(buttonByText(w as never, 'Save Cue')!.attributes('disabled')).toBeDefined();
    expect(buttonByText(w as never, 'Delete Cue')!.attributes('disabled')).toBeDefined();
  });

  it('keeps the card and the typed number when saving fails', async () => {
    const { scriptStore } = setup();
    vi.spyOn(scriptStore, 'editCue').mockResolvedValue(false);
    const w = mountEdit();
    await flushPromises();

    await w.find('input.cue-number-input').setValue('15');
    await buttonByText(w as never, 'Save Cue')!.trigger('click');
    await flushPromises();

    expect(w.emitted('done')).toBeUndefined();
    expect(w.find('[role="alert"]').text()).toContain('LX 14 was not saved');
    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('15');
  });

  it('warns when the new number is used elsewhere, not counting itself', async () => {
    setup();
    const w = mountEdit();
    await flushPromises();
    expect(w.text()).not.toContain('already used');

    await w.find('input.cue-number-input').setValue('13');

    expect(w.text()).toContain('LX 13 is already used on page 5');
  });
});

describe('CueCard (view only)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows a read-only note for a type that cannot be changed', async () => {
    setup({ admin: false, writable: [1] });
    const w = mount(CueCard, {
      props: { mode: 'view', line: L3, lineLabel: 'x', cue: cue(5, 3, '1'), typeId: null },
    });
    await flushPromises();

    expect(w.find('[role="note"]').text()).toContain('VID 1 · Video');
    expect(w.text()).toContain('View only. You do not have permission to change VID cues.');
    expect(w.findAll('button')).toHaveLength(0);
  });
});
