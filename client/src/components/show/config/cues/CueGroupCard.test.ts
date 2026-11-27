import { afterEach, describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import CueGroupCard from './CueGroupCard.vue';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { Cue, CueGroup } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';

// Wrappers are attached to the document (for focus checks); unmount them after each test so
// ids from one test can't be matched by the next.
enableAutoUnmount(afterEach);

const confirmMock = vi.fn();
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }));
vi.mock('@/js/toast', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const LX = { id: 1, show_id: 1, prefix: 'LX', description: 'Lighting', colour: '#ffd23f' };
const SND = { id: 2, show_id: 1, prefix: 'SND', description: 'Sound', colour: '#2563c9' };

const LINE = {
  id: 102,
  act_id: 1,
  scene_id: 1,
  page: 5,
  line_type: LINE_TYPES.DIALOGUE,
  stage_direction_style_id: null,
  line_parts: [],
} as unknown as ScriptLine;

function setup(live = false) {
  const showStore = useShowStore();
  const scriptStore = useScriptStore();
  showStore.cueTypes = [LX, SND];
  showStore.currentSession = live ? ({ id: 1 } as never) : null;
  useUserStore().currentUser = { id: 1, is_admin: true } as never;
  useSystemStore().rbacRoles = [{ key: 'WRITE', value: 2 }];
  scriptStore.script = { '5': [LINE] };
  scriptStore.cues = {};
  scriptStore.linePositions = {};
  return { showStore, scriptStore };
}

function mountAdd(typeId: number | null = 2) {
  return mount(CueGroupCard, {
    props: { mode: 'add', line: LINE, lineLabel: 'Hello there', typeId },
    attachTo: document.body,
  });
}

type Wrapper = ReturnType<typeof mountAdd>;
const button = (w: Wrapper, text: string) =>
  w.findAll('button').find((b) => b.text().trim() === text);
const inputByLabel = (w: Wrapper, label: string) =>
  w.findAll('label').find((l) => l.text() === label)!.element.control as HTMLInputElement;
const memberValues = (w: Wrapper) =>
  w.findAll('.member-input').map((i) => (i.element as HTMLInputElement).value);

async function addRange(w: Wrapper, from: string, to: string) {
  await w.find(`#${inputByLabel(w, 'From number').id}`).setValue(from);
  await w.find(`#${inputByLabel(w, 'To number').id}`).setValue(to);
  await button(w, 'Add Range')!.trigger('click');
}

describe('CueGroupCard (add)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
  });

  it('starts From at the suggested number when it is whole', async () => {
    setup();
    const w = mountAdd(2);
    await flushPromises();

    expect(inputByLabel(w, 'From number').value).toBe('1');
  });

  it('leaves From empty when the suggestion is not a whole number', async () => {
    const { scriptStore } = setup();
    scriptStore.cues = {
      '101': [
        {
          id: 1,
          cue_type_id: 1,
          ident: '13',
          group_id: null,
          sort_order: null,
          line_position: 1,
        } as Cue,
      ],
    };
    scriptStore.linePositions = { '101': { page: 5, index: 0, act_id: 1, scene_id: 1 } };
    scriptStore.script = {
      '5': [{ ...LINE, id: 101 } as ScriptLine, LINE, { ...LINE, id: 103 } as ScriptLine],
    };
    scriptStore.cues['103'] = [
      {
        id: 2,
        cue_type_id: 1,
        ident: '14',
        group_id: null,
        sort_order: null,
        line_position: 1,
      } as Cue,
    ];
    scriptStore.linePositions['103'] = { page: 5, index: 2, act_id: 1, scene_id: 1 };
    const w = mountAdd(1);
    await flushPromises();

    expect(inputByLabel(w, 'From number').value).toBe('');
  });

  it('adds a range of whole numbers and labels the button with the count', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await addRange(w, '15', '26');

    expect(memberValues(w)).toEqual(Array.from({ length: 12 }, (_, i) => String(15 + i)));
    expect(button(w, 'Add Group of 12')).toBeDefined();
    expect(w.text()).toContain('12 cues in this group, in order.');
  });

  it('runs Add Range when Enter is pressed in From or To', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await w.find(`#${inputByLabel(w, 'From number').id}`).setValue('1');
    await w.find(`#${inputByLabel(w, 'To number').id}`).setValue('3');
    await w.find(`#${inputByLabel(w, 'To number').id}`).trigger('keydown', { key: 'Enter' });

    expect(memberValues(w)).toEqual(['1', '2', '3']);
  });

  it('rejects an invalid range with the agreed message and no button', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await w.find(`#${inputByLabel(w, 'From number').id}`).setValue('26');
    await w.find(`#${inputByLabel(w, 'To number').id}`).setValue('15');

    expect(button(w, 'Add Range')!.attributes('disabled')).toBeDefined();
    expect(w.text()).toContain(
      'Use whole numbers, with From no higher than To, and no more than 10,000 cues.'
    );
  });

  it('rejects ranges over 10,000 cues', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await w.find(`#${inputByLabel(w, 'From number').id}`).setValue('1');
    await w.find(`#${inputByLabel(w, 'To number').id}`).setValue('10001');

    expect(button(w, 'Add Range')!.attributes('disabled')).toBeDefined();
  });

  it('appends, so a second range follows the first', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await addRange(w, '1', '2');
    await addRange(w, '10', '11');

    expect(memberValues(w)).toEqual(['1', '2', '10', '11']);
  });

  it('adds an empty member that makes the group invalid until it is filled', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();

    await addRange(w, '1', '2');
    await button(w, 'Add One Cue')!.trigger('click');
    expect(button(w, 'Add Group of 3')!.attributes('disabled')).toBeDefined();

    await w.findAll('.member-input')[2].setValue('3');
    expect(button(w, 'Add Group of 3')!.attributes('disabled')).toBeUndefined();
  });

  it('needs a type and at least one cue', async () => {
    setup();
    const none = mountAdd(null);
    await flushPromises();
    expect(button(none, 'Add Group')!.attributes('disabled')).toBeDefined();

    const empty = mountAdd(2);
    await flushPromises();
    expect(button(empty, 'Add Group')!.attributes('disabled')).toBeDefined();
  });

  it('reorders with the arrow buttons, labelled by cue, and focus follows the moved cue', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();
    await addRange(w, '15', '17');

    const later = w.find('[aria-label="Move cue 15 later"]');
    expect(later.exists()).toBe(true);
    expect(w.find('[aria-label="Move cue 15 earlier"]').attributes('disabled')).toBeDefined();

    await later.trigger('click');
    await flushPromises();

    expect(memberValues(w)).toEqual(['16', '15', '17']);
    expect(document.activeElement).toBe(w.find('[aria-label="Move cue 15 later"]').element);

    // Once the cue reaches the end, "later" is disabled, so focus falls back to "earlier".
    await w.find('[aria-label="Move cue 15 later"]').trigger('click');
    await flushPromises();
    expect(memberValues(w)).toEqual(['16', '17', '15']);
    expect(w.find('[aria-label="Move cue 15 later"]').attributes('disabled')).toBeDefined();
    expect(document.activeElement).toBe(w.find('[aria-label="Move cue 15 earlier"]').element);
  });

  it('removes a cue', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();
    await addRange(w, '1', '3');

    await w.find('[aria-label="Remove cue 2"]').trigger('click');

    expect(memberValues(w)).toEqual(['1', '3']);
  });

  it('previews the label from the name, or from the first and last cue', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();
    await addRange(w, '15', '26');
    expect(w.find('.cue-chip-group').text()).toBe('SND 15 - SND 26');

    await w
      .find(
        `#${(w.findAll('label').find((l) => l.text().startsWith('Group name'))!.element.control as HTMLInputElement).id}`
      )
      .setValue('Storm build');
    expect(w.find('.cue-chip-group').text()).toBe('SND - Storm build');
  });

  it('sends the whole group, in order, and closes', async () => {
    const { scriptStore } = setup();
    const add = vi.spyOn(scriptStore, 'addCueGroup').mockResolvedValue(true);
    const w = mountAdd();
    await flushPromises();
    await addRange(w, '1', '3');

    await button(w, 'Add Group of 3')!.trigger('click');
    await flushPromises();

    expect(add).toHaveBeenCalledWith({
      cueTypeId: 2,
      labelOverride: undefined,
      lineId: 102,
      cues: [
        { ident: '1', sortOrder: 0 },
        { ident: '2', sortOrder: 1 },
        { ident: '3', sortOrder: 2 },
      ],
    });
    expect(w.emitted('done')).toHaveLength(1);
  });

  it('keeps the card and every entry when adding fails', async () => {
    const { scriptStore } = setup();
    vi.spyOn(scriptStore, 'addCueGroup').mockResolvedValue(false);
    const w = mountAdd();
    await flushPromises();
    await addRange(w, '1', '3');

    await button(w, 'Add Group of 3')!.trigger('click');
    await flushPromises();

    expect(w.emitted('done')).toBeUndefined();
    expect(w.find('[role="alert"]').exists()).toBe(true);
    expect(memberValues(w)).toEqual(['1', '2', '3']);
  });

  it('reports whether it has anything that would be lost', async () => {
    setup();
    const w = mountAdd();
    await flushPromises();
    expect(w.emitted('dirty')?.at(-1)).toEqual([false]);

    await addRange(w, '1', '2');
    await flushPromises();

    expect(w.emitted('dirty')?.at(-1)).toEqual([true]);
  });
});

describe('CueGroupCard (edit)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    confirmMock.mockReset();
  });

  const group: CueGroup = { id: 7, cue_type_id: 1, label_override: 'Storm build' };
  const members = ['15', '16', '17'].map((ident, i): Cue => ({
    id: 70 + i,
    cue_type_id: 1,
    ident,
    group_id: 7,
    sort_order: i,
    line_position: 1,
  }));

  const mountEdit = () =>
    mount(CueGroupCard, {
      props: {
        mode: 'edit',
        line: LINE,
        lineLabel: 'Hello there',
        group,
        groupCues: members,
        typeId: null,
      },
      attachTo: document.body,
    });

  it('fixes the type, and only enables Save once something changed', async () => {
    setup();
    const w = mountEdit();
    await flushPromises();

    expect(w.text()).toContain('Cue type (fixed once a group exists)');
    expect(w.find('[role="radiogroup"]').exists()).toBe(false);
    expect(button(w as never, 'Save Group')!.attributes('disabled')).toBeDefined();
    expect(w.emitted('dirty')?.at(-1)).toEqual([false]);

    await w.find('[aria-label="Move cue 15 later"]').trigger('click');
    await flushPromises();

    expect(button(w as never, 'Save Group')!.attributes('disabled')).toBeUndefined();
    expect(w.emitted('dirty')?.at(-1)).toEqual([true]);
  });

  it('is clean again when the change is undone', async () => {
    setup();
    const w = mountEdit();
    await flushPromises();

    await w.find('[aria-label="Move cue 15 later"]').trigger('click');
    await w.find('[aria-label="Move cue 15 earlier"]').trigger('click');
    await flushPromises();

    expect(w.emitted('dirty')?.at(-1)).toEqual([false]);
  });

  it('keeps existing members’ ids so they are updated rather than recreated', async () => {
    const { scriptStore } = setup();
    const edit = vi.spyOn(scriptStore, 'editCueGroup').mockResolvedValue(true);
    const w = mountEdit();
    await flushPromises();
    await w.find('[aria-label="Move cue 15 later"]').trigger('click');
    await w.find('.member-input').setValue('99');

    await button(w as never, 'Save Group')!.trigger('click');
    await flushPromises();

    expect(edit).toHaveBeenCalledWith({
      groupId: 7,
      labelOverride: 'Storm build',
      lineId: 102,
      cues: [
        { id: 70 + 1, ident: '99', sortOrder: 0 },
        { id: 70, ident: '15', sortOrder: 1 },
        { id: 72, ident: '17', sortOrder: 2 },
      ],
    });
  });

  it('asks before deleting the group, naming its size, then deletes', async () => {
    const { scriptStore } = setup();
    const del = vi.spyOn(scriptStore, 'deleteCueGroup').mockResolvedValue(true);
    confirmMock.mockResolvedValue(true);
    const w = mountEdit();
    await flushPromises();

    await button(w as never, 'Delete Group')!.trigger('click');
    await flushPromises();

    const [message, options] = confirmMock.mock.calls[0];
    expect(message).toContain('Delete LX - Storm build and its 3 cues?');
    expect(message).toContain('Other revisions keep them.');
    expect(options).toMatchObject({ title: 'Delete Cue Group', okTitle: 'Delete Group' });
    expect(del).toHaveBeenCalledWith({ groupId: 7, lineId: 102 });
    expect(w.emitted('done')).toHaveLength(1);
  });

  it('disables Save and Delete during a live session', async () => {
    setup(true);
    const w = mountEdit();
    await flushPromises();
    await w.find('[aria-label="Move cue 15 later"]').trigger('click');

    expect(button(w as never, 'Save Group')!.attributes('disabled')).toBeDefined();
    expect(button(w as never, 'Delete Group')!.attributes('disabled')).toBeDefined();
  });

  it('lets a long list scroll rather than growing the card', async () => {
    setup();
    const w = mountEdit();
    await flushPromises();

    expect(w.find('.member-list').exists()).toBe(true);
  });
});
