import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises, mount } from '@vue/test-utils';
import CueCard from './CueCard.vue';
import ScriptLineCueEditor from './ScriptLineCueEditor.vue';
import { passthrough } from '@/components/show/config/script/testStubs';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { Cue } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';
import type { ActiveCueCard } from '@/types/cueCard';

const confirmMock = vi.fn();
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }));
vi.mock('@/js/toast', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const characters = [
  { id: 1, name: 'Alice' },
  { id: 2, name: 'Bob' },
] as never[];

function line(
  id: number,
  type: string,
  characterId: number | null,
  text: string,
  overrides: Partial<ScriptLine> = {}
): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: type,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: id * 10,
        line_id: id,
        part_index: 0,
        character_id: characterId,
        character_group_id: null,
        line_text: text,
      },
    ],
    ...overrides,
  } as ScriptLine;
}

function mountEditor(current: ScriptLine, previous: ScriptLine | null, page: ScriptLine[]) {
  const scriptStore = useScriptStore();
  scriptStore.scriptPages = { 1: page } as never;
  return mount(ScriptLineCueEditor, {
    props: {
      line: current,
      lineIndex: page.indexOf(current),
      previousLine: previous,
      acts: [{ id: 1, name: 'Act 1' }] as never[],
      scenes: [{ id: 1, name: 'Scene 1' }] as never[],
      characters,
      characterGroups: [],
      cues: [],
      cueTypes: [],
      cuts: [],
    },
    global: {
      stubs: {
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BButton: passthrough('button'),
        BButtonGroup: passthrough('div'),
        BAlert: passthrough('div'),
        BModal: true,
        BTabs: true,
        CueGroupEditModal: true,
        CueGroupForm: true,
        IMdiPlusBox: true,
      },
    },
  });
}

describe('ScriptLineCueEditor tagged stage directions (B6)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows the character name above a tagged stage direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice exits.');
    const w = mountEditor(sd, null, [sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(true);
    expect(w.find('.tagged-sd-heading').text()).toBe('Alice');
  });

  it('shows no heading for an untagged stage direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, null, 'The lights fade.');
    const w = mountEditor(sd, null, [sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(false);
  });

  it('does not repeat the name on the same speaker line that follows a tagged direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const dialogue = line(2, LINE_TYPES.DIALOGUE, 1, 'Hello there.');
    const page = [sd, dialogue];

    const sdWrapper = mountEditor(sd, null, page);
    expect(sdWrapper.find('.tagged-sd-heading').text()).toBe('Alice');

    // The direction already named Alice, so her next line carries no name.
    const dialogueWrapper = mountEditor(dialogue, sd, page);
    expect(dialogueWrapper.find('.tagged-sd-heading').exists()).toBe(false);
    expect(dialogueWrapper.text()).not.toContain('Alice');
    expect(dialogueWrapper.text()).toContain('Hello there.');
  });

  it('shows the name again when a different speaker follows a tagged direction', () => {
    const sd = line(1, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const dialogue = line(2, LINE_TYPES.DIALOGUE, 2, 'Evening.');
    const w = mountEditor(dialogue, sd, [sd, dialogue]);

    expect(w.text()).toContain('Bob');
  });

  it('shows no heading on a tagged direction that follows the same speaker', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello there.');
    const sd = line(2, LINE_TYPES.STAGE_DIRECTION, 1, 'Alice sits.');
    const w = mountEditor(sd, dialogue, [dialogue, sd]);

    expect(w.find('.tagged-sd-heading').exists()).toBe(false);
  });
});

// ── "+ Cue", cut and permission rules, the type filter, and opening cards ─────

const LXT = { id: 1, show_id: 1, prefix: 'LX', description: 'Lighting', colour: '#ffd23f' };
const SNDT = { id: 2, show_id: 1, prefix: 'SND', description: 'Sound', colour: '#2563c9' };

function cueOn(id: number, typeId: number, ident: string, over: Partial<Cue> = {}): Cue {
  return {
    id,
    cue_type_id: typeId,
    ident,
    group_id: null,
    sort_order: null,
    line_position: id,
    ...over,
  };
}

function mountLine(
  current: ScriptLine,
  opts: {
    admin?: boolean;
    writable?: number[];
    cuts?: number[];
    activeCard?: ActiveCueCard | null;
    filterTypeId?: number | null;
    /** Render the real cards instead of stubs. */
    realCards?: boolean;
    /** Called when the line asks for its card to be closed (as CueEditor does). */
    onCloseCard?: () => void;
  } = {}
) {
  const {
    admin = true,
    writable = [],
    cuts = [],
    activeCard = null,
    filterTypeId = null,
    realCards = false,
    onCloseCard,
  } = opts;
  useShowStore().cueTypes = [LXT, SNDT];
  useSystemStore().rbacRoles = [{ key: 'WRITE', value: 2 }];
  useUserStore().currentUser = { id: 1, is_admin: admin } as never;
  if (!admin) useUserStore().currentRbac = { cuetypes: writable.map((id) => [id, 2]) } as never;
  const scriptStore = useScriptStore();
  scriptStore.script = { '1': [current] };
  return mount(ScriptLineCueEditor, {
    props: {
      line: current,
      lineIndex: 0,
      previousLine: null,
      acts: [{ id: 1, name: 'Act 1' }] as never[],
      scenes: [{ id: 1, name: 'Scene 1' }] as never[],
      characters,
      characterGroups: [],
      cues: scriptStore.cuesForLine(current.id),
      cueTypes: [LXT, SNDT],
      cuts,
      activeCard,
      filterTypeId,
      ...(onCloseCard ? { 'onClose-card': onCloseCard } : {}),
    },
    global: {
      stubs: {
        BContainer: passthrough('div'),
        BRow: passthrough('div'),
        BCol: passthrough('div'),
        BAlert: passthrough('div'),
        ...(realCards ? {} : { CueCard: true, CueGroupCard: true }),
      },
    },
  });
}

describe('ScriptLineCueEditor "+ Cue" and cue buttons', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('gives each "+ Cue" its own accessible name from the start of the line', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Is it the good bread?');
    const w = mountLine(dialogue);

    const add = w.find('.add-cue-btn');
    expect(add.text()).toBe('+ Cue');
    expect(add.attributes('aria-label')).toBe('Add a cue: Is it the good bread?');
  });

  it('truncates a long line in the accessible name', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'word '.repeat(30));
    const w = mountLine(dialogue);

    const label = w.find('.add-cue-btn').attributes('aria-label') ?? '';
    expect(label.startsWith('Add a cue: word word')).toBe(true);
    expect(label.endsWith('…')).toBe(true);
    expect(label.length).toBeLessThan(60);
  });

  it('has no "+ Cue" on a spacing line', () => {
    const spacing = line(1, LINE_TYPES.SPACING, null, '');
    const w = mountLine(spacing);

    expect(w.find('.add-cue-btn').exists()).toBe(false);
    expect(w.text()).toContain('Spacing Line');
  });

  it('shows "+ Cue" on a cue line', () => {
    const cueLine = line(1, LINE_TYPES.CUE_LINE, null, '');
    const w = mountLine(cueLine);

    expect(w.find('.add-cue-btn').attributes('aria-label')).toBe('Add a cue: Cue Line');
  });

  it('disables "+ Cue" on a wholly cut line and says why, but existing cues still open', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Cut me');
    useScriptStore().cues = { '1': [cueOn(5, 1, '4')] };
    const w = mountLine(dialogue, { cuts: [10] });

    expect(w.find('.add-cue-btn').attributes('disabled')).toBeDefined();
    expect(w.text()).toContain('Line cut');
    const chip = w.find('.cue-button:not(.add-cue-btn)');
    expect(chip.attributes('disabled')).toBeUndefined();
    await chip.trigger('click');
    expect(w.emitted('open')?.[0][0]).toMatchObject({ kind: 'edit-cue', cueId: 5 });
  });

  it('keeps "+ Cue" enabled when only part of a line is cut', () => {
    const base = line(1, LINE_TYPES.DIALOGUE, 1, 'Mara says');
    const split = {
      ...base,
      line_parts: [
        ...base.line_parts,
        { ...base.line_parts[0], id: 11, part_index: 1, character_id: 2, line_text: 'Tobias says' },
      ],
    } as ScriptLine;
    const w = mountLine(split, { cuts: [10] });

    expect(w.find('.add-cue-btn').attributes('disabled')).toBeUndefined();
    expect(w.text()).not.toContain('Line cut');
  });

  it('has no "+ Cue" for someone who can write no cue type, but cues still open read-only', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    useScriptStore().cues = { '1': [cueOn(5, 1, '14')] };
    const w = mountLine(dialogue, { admin: false, writable: [] });

    expect(w.find('.add-cue-btn').exists()).toBe(false);
    await w.find('.cue-button').trigger('click');
    expect(w.emitted('open')?.[0][0]).toMatchObject({ kind: 'view', cueId: 5 });
  });

  it('opens a cue of an unwritable type read-only and one of a writable type for editing', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    useScriptStore().cues = { '1': [cueOn(5, 1, '14'), cueOn(6, 2, '3')] };
    const w = mountLine(dialogue, { admin: false, writable: [1] });

    const [lx, snd] = w.findAll('.cue-button:not(.add-cue-btn)');
    await lx.trigger('click');
    await snd.trigger('click');

    expect(w.emitted('open')?.[0][0]).toMatchObject({ kind: 'edit-cue', cueId: 5 });
    expect(w.emitted('open')?.[1][0]).toMatchObject({ kind: 'view', cueId: 6 });
  });

  it('passes the clicked button so focus can return to it', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const w = mountLine(dialogue);

    await w.find('.add-cue-btn').trigger('click');

    const [card, opener] = w.emitted('open')![0];
    expect(card).toEqual({ lineId: 1, kind: 'add' });
    expect(opener).toBe(w.find('.add-cue-btn').element);
  });

  it('reads "Adding…" and is disabled while its add card is open', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const w = mountLine(dialogue, { activeCard: { lineId: 1, kind: 'add' } });

    expect(w.find('.add-cue-btn').text()).toBe('Adding…');
    expect(w.find('.add-cue-btn').attributes('disabled')).toBeDefined();
  });

  it('outlines the cue being edited', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    useScriptStore().cues = { '1': [cueOn(5, 1, '14'), cueOn(6, 1, '15')] };
    const w = mountLine(dialogue, { activeCard: { lineId: 1, kind: 'edit-cue', cueId: 6 } });

    const chips = w.findAll('.cue-button:not(.add-cue-btn)');
    expect(chips[0].classes()).not.toContain('cue-selected');
    expect(chips[1].classes()).toContain('cue-selected');
  });

  it('the type filter hides other types’ cues and groups, but "+ Cue" stays', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const store = useScriptStore();
    store.cues = {
      '1': [
        cueOn(5, 1, '14'),
        cueOn(6, 2, '3'),
        cueOn(7, 2, '10', { group_id: 9, sort_order: 0 }),
        cueOn(8, 2, '11', { group_id: 9, sort_order: 1 }),
      ],
    };
    store.cueGroups = [{ id: 9, cue_type_id: 2, label_override: null }];

    const all = mountLine(dialogue);
    expect(all.findAll('.cue-button:not(.add-cue-btn)')).toHaveLength(3);

    const onlyLx = mountLine(dialogue, { filterTypeId: 1 });
    const visible = onlyLx.findAll('.cue-button:not(.add-cue-btn)');
    expect(visible).toHaveLength(1);
    expect(visible[0].text()).toBe('LX 14');
    expect(onlyLx.find('.add-cue-btn').exists()).toBe(true);

    const onlySnd = mountLine(dialogue, { filterTypeId: 2 });
    expect(onlySnd.findAll('.cue-button:not(.add-cue-btn)')).toHaveLength(2);
    expect(onlySnd.find('.cue-group-btn').exists()).toBe(true);
  });

  it('opens a group for editing, and read-only when its type cannot be written', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const store = useScriptStore();
    store.cues = {
      '1': [cueOn(7, 2, '10', { group_id: 9, sort_order: 0 })],
    };
    store.cueGroups = [{ id: 9, cue_type_id: 2, label_override: 'Storm' }];

    const editable = mountLine(dialogue);
    await editable.find('.cue-group-btn').trigger('click');
    expect(editable.emitted('open')?.[0][0]).toMatchObject({ kind: 'edit-group', groupId: 9 });

    const readOnly = mountLine(dialogue, { admin: false, writable: [1] });
    await readOnly.find('.cue-group-btn').trigger('click');
    expect(readOnly.emitted('open')?.[0][0]).toMatchObject({ kind: 'view' });
  });

  it('says so when the cue being edited disappears', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const store = useScriptStore();
    store.cues = { '1': [cueOn(5, 1, '14')] };
    const w = mountLine(dialogue, { activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 } });
    expect(w.emitted('target-gone')).toBeUndefined();

    store.cues = { '1': [] };
    await flushPromises();

    expect(w.emitted('target-gone')).toHaveLength(1);
  });

  it('renders no card for another line’s card', () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const w = mountLine(dialogue, { activeCard: { lineId: 99, kind: 'add' } });

    expect(w.findComponent({ name: 'CueCard' }).exists()).toBe(false);
    expect(w.find('.add-cue-btn').text()).toBe('+ Cue');
  });
});

describe('ScriptLineCueEditor and the card\u2019s own changes', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
    confirmMock.mockResolvedValue(true);
  });

  const lineWithCue = () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    useScriptStore().cues = { '1': [cueOn(5, 1, '14')] };
    return dialogue;
  };

  it('does not say "someone else" when the card deleted the cue itself', async () => {
    const dialogue = lineWithCue();
    const store = useScriptStore();
    // Like the real action: the cue is gone from the store by the time the request resolves.
    vi.spyOn(store, 'deleteCue').mockImplementation(async () => {
      store.cues = { '1': [] };
      await flushPromises();
      return true;
    });
    const w = mountLine(dialogue, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 },
      // CueEditor clears the open card as soon as the line asks it to close.
      onCloseCard: () => void w.setProps({ activeCard: null }),
    });
    await flushPromises();

    await w
      .findAll('button')
      .find((b) => b.text() === 'Delete Cue')!
      .trigger('click');
    await flushPromises();

    expect(w.emitted('close-card')).toHaveLength(1);
    expect(w.emitted('target-gone')).toBeUndefined();
  });

  it('does not say "someone else" when the card saved a cue that was replaced by a new one', async () => {
    const dialogue = lineWithCue();
    const store = useScriptStore();
    // Saving a cue shared with another revision gives it a new id.
    vi.spyOn(store, 'editCue').mockImplementation(async () => {
      store.cues = { '1': [cueOn(77, 1, '15')] };
      await flushPromises();
      return true;
    });
    const w = mountLine(dialogue, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 },
      // CueEditor clears the open card as soon as the line asks it to close.
      onCloseCard: () => void w.setProps({ activeCard: null }),
    });
    await flushPromises();

    await w.find('input.cue-number-input').setValue('15');
    await w
      .findAll('button')
      .find((b) => b.text() === 'Save Cue')!
      .trigger('click');
    await flushPromises();

    expect(w.emitted('close-card')).toHaveLength(1);
    expect(w.emitted('target-gone')).toBeUndefined();
  });

  it('still says so when someone else removes the cue while the card is idle', async () => {
    const dialogue = lineWithCue();
    const w = mountLine(dialogue, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 },
    });
    await flushPromises();

    useScriptStore().cues = { '1': [] };
    await flushPromises();

    expect(w.emitted('target-gone')).toHaveLength(1);
  });

  it('does not say "someone else" when the group card deleted its own group', async () => {
    const dialogue = line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
    const store = useScriptStore();
    store.cues = {
      '1': [
        cueOn(7, 1, '10', { group_id: 9, sort_order: 0 }),
        cueOn(8, 1, '11', { group_id: 9, sort_order: 1 }),
      ],
    };
    store.cueGroups = [{ id: 9, cue_type_id: 1, label_override: 'Storm' }];
    vi.spyOn(store, 'deleteCueGroup').mockImplementation(async () => {
      store.cues = { '1': [] };
      store.cueGroups = [];
      await flushPromises();
      return true;
    });
    const w = mountLine(dialogue, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-group', groupId: 9 },
      onCloseCard: () => void w.setProps({ activeCard: null }),
    });
    await flushPromises();

    await w
      .findAll('button')
      .find((b) => b.text() === 'Delete Group')!
      .trigger('click');
    await flushPromises();

    expect(w.emitted('close-card')).toHaveLength(1);
    expect(w.emitted('target-gone')).toBeUndefined();
  });

  it('a card that failed to delete stays open and does not blame someone else', async () => {
    const dialogue = lineWithCue();
    vi.spyOn(useScriptStore(), 'deleteCue').mockResolvedValue(false);
    const w = mountLine(dialogue, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 },
    });
    await flushPromises();

    await w
      .findAll('button')
      .find((b) => b.text() === 'Delete Cue')!
      .trigger('click');
    await flushPromises();

    expect(w.emitted('close-card')).toBeUndefined();
    expect(w.emitted('target-gone')).toBeUndefined();
    expect(w.find('[role="alert"]').text()).toContain('was not deleted');
  });
});

describe('ScriptLineCueEditor default cue type, view-only groups and changed cues', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
    localStorage.clear();
  });

  const dialogue = () => line(1, LINE_TYPES.DIALOGUE, 1, 'Hello');
  const addCard = { lineId: 1, kind: 'add' } as const;
  const chosenType = (w: ReturnType<typeof mountLine>) => w.findComponent(CueCard).props('typeId');

  it('starts the add card on the active filter when that type can be written', () => {
    const w = mountLine(dialogue(), { activeCard: addCard, filterTypeId: 2 });

    expect(chosenType(w)).toBe(2);
  });

  it('otherwise on the type last used', () => {
    localStorage.setItem('cueEditType', '2');
    const w = mountLine(dialogue(), { activeCard: addCard });

    expect(chosenType(w)).toBe(2);
  });

  it('prefers the filter over the type last used', () => {
    localStorage.setItem('cueEditType', '2');
    const w = mountLine(dialogue(), { activeCard: addCard, filterTypeId: 1 });

    expect(chosenType(w)).toBe(1);
  });

  it('otherwise on the only type that can be written', () => {
    const w = mountLine(dialogue(), { activeCard: addCard, admin: false, writable: [1] });

    expect(chosenType(w)).toBe(1);
  });

  it('skips a filter or a remembered type that cannot be written', () => {
    localStorage.setItem('cueEditType', '2');
    const w = mountLine(dialogue(), {
      activeCard: addCard,
      admin: false,
      writable: [1],
      filterTypeId: 2,
    });

    expect(chosenType(w)).toBe(1);
  });

  it('chooses nothing when several types could be used and nothing points at one', () => {
    const w = mountLine(dialogue(), { activeCard: addCard });

    expect(chosenType(w)).toBeNull();
  });

  it('ignores a remembered type that is not a number', () => {
    localStorage.setItem('cueEditType', 'banana');
    const w = mountLine(dialogue(), { activeCard: addCard });

    expect(chosenType(w)).toBeNull();
  });

  const groupOnLine = () => {
    const store = useScriptStore();
    store.cues = {
      '1': [
        cueOn(7, 2, '10', { group_id: 9, sort_order: 0 }),
        cueOn(8, 2, '11', { group_id: 9, sort_order: 1 }),
      ],
    };
    store.cueGroups = [{ id: 9, cue_type_id: 2, label_override: 'Storm' }];
  };

  it('opens a view-only group with its own id, so the note can name it', async () => {
    groupOnLine();
    const w = mountLine(dialogue(), { admin: false, writable: [1] });

    await w.find('.cue-group-btn').trigger('click');

    expect(w.emitted('open')?.[0][0]).toEqual({
      lineId: 1,
      kind: 'view',
      groupId: 9,
      cueId: 7,
    });
  });

  it('outlines a view-only group while its note is open, and the note names the group', async () => {
    groupOnLine();
    const w = mountLine(dialogue(), {
      realCards: true,
      admin: false,
      writable: [1],
      activeCard: { lineId: 1, kind: 'view', groupId: 9, cueId: 7 },
    });
    await flushPromises();

    expect(w.find('.cue-group-btn').classes()).toContain('cue-selected');
    expect(w.find('[role="note"]').text()).toContain('SND - Storm');
    expect(w.find('[role="note"]').text()).not.toContain('SND 10');
  });

  it('keeps the card open, with a warning on it, when a cue is changed by someone else under unsaved edits', async () => {
    const d = dialogue();
    useScriptStore().cues = { '1': [cueOn(5, 1, '14')] };
    const w = mountLine(d, {
      realCards: true,
      activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 },
    });
    await flushPromises();
    await w.find('input.cue-number-input').setValue('99');

    useScriptStore().cues = { '1': [cueOn(5, 1, '15')] };
    await flushPromises();

    expect(w.emitted('target-gone')).toBeUndefined();
    expect(w.emitted('close-card')).toBeUndefined();
    expect(w.find('output').text()).toContain('changed by someone else');
    expect((w.find('input.cue-number-input').element as HTMLInputElement).value).toBe('99');
  });

  it('a card that went away mid-request does not leave the next one thinking it is busy', async () => {
    const d = dialogue();
    useScriptStore().cues = { '1': [cueOn(5, 1, '14')] };
    const w = mountLine(d, { activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 } });
    w.findComponent(CueCard).vm.$emit('busy', true);

    await w.setProps({ activeCard: null });
    await w.setProps({ activeCard: { lineId: 1, kind: 'edit-cue', cueId: 5 } });
    useScriptStore().cues = { '1': [] };
    await flushPromises();

    expect(w.emitted('target-gone')).toHaveLength(1);
  });
});
