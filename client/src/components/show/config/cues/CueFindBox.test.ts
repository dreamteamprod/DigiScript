import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import CueFindBox from './CueFindBox.vue';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
import type { FindMatch, FindResponse } from '@/js/cueFind';

enableAutoUnmount(afterEach);

const LX = { id: 1, show_id: 1, prefix: 'LX', description: 'Lighting', colour: '#ffd23f' };
const SND = { id: 2, show_id: 1, prefix: 'SND', description: 'Sound', colour: '#2563c9' };

function match(id: number, ident: string, page: number, type = LX, score?: number): FindMatch {
  return {
    cue: { id, ident, cue_type_id: type.id },
    cue_type: type,
    location: { page, line_id: id * 10, act_id: 1, scene_id: 2 },
    similarity_score: score,
  };
}

function setup(respond: (arg: { identifier: string; cueTypeId: number }) => FindResponse | Error) {
  const showStore = useShowStore();
  const scriptStore = useScriptStore();
  showStore.cueTypes = [LX, SND];
  showStore.actList = [{ id: 1, name: 'Act 1' }] as never;
  showStore.sceneList = [{ id: 2, name: 'Scene 2' }] as never;
  useUserStore().cueColourOverrides = [];
  scriptStore.script = {
    '4': [
      {
        id: 10,
        line_parts: [{ line_text: 'Dawn. MARA sits on an upturned crate, mending a net.' }],
      } as never,
    ],
  };
  vi.spyOn(scriptStore, 'loadScriptPage').mockResolvedValue(undefined);
  const search = vi.spyOn(scriptStore, 'searchCues').mockImplementation(async (arg) => {
    const result = respond(arg);
    if (result instanceof Error) throw result;
    return result as never;
  });
  return { search };
}

const empty: FindResponse = { exact_matches: [], suggestions: [] };

async function find(w: ReturnType<typeof mount>, text: string, how: 'enter' | 'button' = 'enter') {
  const input = w.find('input');
  await input.setValue(text);
  if (how === 'enter') await input.trigger('keydown', { key: 'Enter' });
  else await w.find('button').trigger('click');
  await flushPromises();
}

describe('CueFindBox', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('does not search while typing, only on Enter or Find', async () => {
    const { search } = setup(() => empty);
    const w = mount(CueFindBox);

    await w.find('input').setValue('LX 1');
    await w.find('input').setValue('LX 14');
    expect(search).not.toHaveBeenCalled();

    await w.find('button').trigger('click');
    await flushPromises();
    expect(search).toHaveBeenCalledTimes(1);
    expect(search).toHaveBeenCalledWith({ identifier: '14', cueTypeId: 1 });
  });

  it('jumps straight to a single exact match, with no list', async () => {
    setup(() => ({ exact_matches: [match(1, '14', 4)], suggestions: [] }));
    const w = mount(CueFindBox);

    await find(w, 'LX 14');

    expect(w.emitted('jump')?.[0][0]).toMatchObject({ cue: { ident: '14' } });
    expect(w.find('[role="listbox"]').exists()).toBe(false);
    expect(w.find('input').attributes('aria-expanded')).toBe('false');
  });

  it('searches case-insensitively by prefix', async () => {
    const { search } = setup(() => empty);
    const w = mount(CueFindBox);

    await find(w, 'snd7');

    expect(search).toHaveBeenCalledWith({ identifier: '7', cueTypeId: 2 });
  });

  it('lists several exact matches with page, act, scene and the start of the line', async () => {
    setup(() => ({
      exact_matches: [match(1, '13', 4), match(2, '13', 31)],
      suggestions: [],
    }));
    const w = mount(CueFindBox);

    await find(w, 'LX 13');

    expect(w.text()).toContain('2 cues are numbered LX 13');
    const rows = w.findAll('[role="option"]');
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain('Page 4 · Act 1 Scene 2');
    expect(rows[0].text()).toContain('Dawn. MARA sits on an upturned crate');
    expect(rows[1].text()).toContain('Page 31');
    expect(w.emitted('jump')).toBeUndefined();
  });

  it('chooses with the arrow keys and opens with Enter, and closes with Esc', async () => {
    setup(() => ({ exact_matches: [match(1, '13', 4), match(2, '13', 31)], suggestions: [] }));
    const w = mount(CueFindBox);
    await find(w, 'LX 13');
    const input = w.find('input');

    expect(input.attributes('role')).toBe('combobox');
    expect(input.attributes('aria-expanded')).toBe('true');
    expect(input.attributes('aria-activedescendant')).toBe(
      w.findAll('[role="option"]')[0].attributes('id')
    );

    await input.trigger('keydown', { key: 'ArrowDown' });
    expect(input.attributes('aria-activedescendant')).toBe(
      w.findAll('[role="option"]')[1].attributes('id')
    );
    expect(w.findAll('[role="option"]')[1].attributes('aria-selected')).toBe('true');

    await input.trigger('keydown', { key: 'Enter' });
    expect(w.emitted('jump')?.[0][0]).toMatchObject({ cue: { id: 2 } });
    expect(w.find('[role="listbox"]').exists()).toBe(false);
  });

  it('closes the list with Escape without jumping', async () => {
    setup(() => ({ exact_matches: [match(1, '13', 4), match(2, '13', 31)], suggestions: [] }));
    const w = mount(CueFindBox);
    await find(w, 'LX 13');

    await w.find('input').trigger('keydown', { key: 'Escape' });

    expect(w.find('[role="listbox"]').exists()).toBe(false);
    expect(w.emitted('jump')).toBeUndefined();
  });

  it('offers close matches when there is no exact one', async () => {
    setup(() => ({
      exact_matches: [],
      suggestions: [match(1, '13', 4, LX, 0.8), match(2, '3', 1, LX, 0.5)],
    }));
    const w = mount(CueFindBox);

    await find(w, 'LX 13.5');

    expect(w.text()).toContain('No LX 13.5 yet. Did you mean:');
    expect(w.findAll('[role="option"]')).toHaveLength(2);
  });

  it('says so when nothing is found or close', async () => {
    setup(() => empty);
    const w = mount(CueFindBox);

    await find(w, 'LX 999');

    expect(w.text()).toContain('No cues found matching “LX 999”.');
  });

  it('asks which type a bare number is, and searches once one is chosen', async () => {
    const { search } = setup(() => ({ exact_matches: [match(1, '13', 4)], suggestions: [] }));
    const w = mount(CueFindBox);

    await find(w, '13');
    expect(w.text()).toContain('Which cue type is 13?');
    expect(search).not.toHaveBeenCalled();

    await w.findAll('.find-type-chip')[1].trigger('click');
    await flushPromises();

    expect(search).toHaveBeenCalledWith({ identifier: '13', cueTypeId: 2 });
    expect(w.emitted('jump')).toHaveLength(1);
  });

  it('asks for a number when only a prefix is typed', async () => {
    const { search } = setup(() => empty);
    const w = mount(CueFindBox);

    await find(w, 'LX');

    expect(w.text()).toContain('Add the number you are looking for');
    expect(search).not.toHaveBeenCalled();
  });

  it('reports a failed search, and Try Again searches again', async () => {
    let fail = true;
    const { search } = setup(() =>
      fail ? new Error('boom') : { exact_matches: [match(1, '14', 4)], suggestions: [] }
    );
    const w = mount(CueFindBox);

    await find(w, 'LX 14');
    expect(w.find('[role="alert"]').text()).toBe('Search failed. Please try again.');
    expect(w.emitted('jump')).toBeUndefined();

    fail = false;
    const retry = w.findAll('button').find((b) => b.text() === 'Try Again')!;
    await retry.trigger('click');
    await flushPromises();

    expect(search).toHaveBeenCalledTimes(2);
    expect(w.emitted('jump')).toHaveLength(1);
  });

  it('searches every type that shares the prefix, and merges the answers', async () => {
    const twin = { ...LX, id: 3 };
    const showStore = useShowStore();
    const { search } = setup(({ cueTypeId }) =>
      cueTypeId === 1
        ? { exact_matches: [match(1, '13', 4)], suggestions: [] }
        : { exact_matches: [match(2, '13', 31, twin)], suggestions: [] }
    );
    showStore.cueTypes = [LX, twin];
    const w = mount(CueFindBox);

    await find(w, 'LX 13');

    expect(search).toHaveBeenCalledTimes(2);
    expect(w.findAll('[role="option"]')).toHaveLength(2);
  });

  it('labels its input for screen readers and lets the Find button be used by mouse', async () => {
    setup(() => ({ exact_matches: [match(1, '14', 4)], suggestions: [] }));
    const w = mount(CueFindBox);

    expect(w.find('label').text()).toBe('Find a cue');
    await find(w, 'LX 14', 'button');
    expect(w.emitted('jump')).toHaveLength(1);
  });
});
