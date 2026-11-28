import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, mount } from '@vue/test-utils';
import { defineComponent, h, nextTick } from 'vue';
import CueToolbar from './CueToolbar.vue';
import { useUserStore } from '@/stores/user';
import { useShowStore } from '@/stores/show';
import type { CueType } from '@/types/api/cues';

enableAutoUnmount(afterEach);

const LX: CueType = { id: 1, show_id: 1, prefix: 'LX', description: null, colour: '#ffd23f' };
const SND: CueType = { id: 2, show_id: 1, prefix: 'SND', description: null, colour: '#2563c9' };

const FindStub = defineComponent({
  emits: ['jump'],
  setup(_, { expose }) {
    expose({ focus: () => undefined });
    return () => h('div', { 'data-test': 'find' });
  },
});

function mountToolbar(props: Partial<InstanceType<typeof CueToolbar>['$props']> = {}) {
  useShowStore().cueTypes = [LX, SND];
  useUserStore().cueColourOverrides = [];
  return mount(CueToolbar, {
    props: {
      currentPage: 3,
      maxPage: 5,
      busy: false,
      cueTypes: [LX, SND],
      filterTypeId: null,
      ...props,
    },
    global: { stubs: { CueFindBox: FindStub } },
  });
}

const button = (w: ReturnType<typeof mountToolbar>, name: string) =>
  w.findAll('button').find((b) => b.text().replace(/\s+/g, ' ').trim() === name)!;

describe('CueToolbar', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows the current page and asks to go to a page, the previous page and the next page', async () => {
    const w = mountToolbar();

    expect(w.text()).toContain('Current Page: 3');
    await button(w, 'Go to Page').trigger('click');
    await button(w, 'Prev Page').trigger('click');
    await button(w, 'Next Page').trigger('click');

    expect(w.emitted('go-to-page')).toHaveLength(1);
    expect(w.emitted('prev')).toHaveLength(1);
    expect(w.emitted('next')).toHaveLength(1);
  });

  it('cannot go before the first page or past the last', () => {
    const first = mountToolbar({ currentPage: 1 });
    expect(button(first, 'Prev Page').attributes('disabled')).toBeDefined();
    expect(button(first, 'Next Page').attributes('disabled')).toBeUndefined();

    const last = mountToolbar({ currentPage: 5 });
    expect(button(last, 'Next Page').attributes('disabled')).toBeDefined();
    expect(button(last, 'Prev Page').attributes('disabled')).toBeUndefined();
  });

  it('disables both page buttons while a page is loading', () => {
    const w = mountToolbar({ busy: true });

    expect(button(w, 'Prev Page').attributes('disabled')).toBeDefined();
    expect(button(w, 'Next Page').attributes('disabled')).toBeDefined();
  });

  it('offers All and each cue type, with the chosen one pressed', () => {
    const w = mountToolbar({ filterTypeId: 2 });
    const group = w.find('fieldset[aria-label="Show cue types"]');
    const buttons = group.findAll('button');

    expect(buttons.map((b) => b.text())).toEqual(['All', 'LX', 'SND']);
    expect(buttons.map((b) => b.attributes('aria-pressed'))).toEqual(['false', 'false', 'true']);
  });

  it('shows All as pressed when no type is chosen', () => {
    const w = mountToolbar({ filterTypeId: null });

    expect(button(w, 'All').attributes('aria-pressed')).toBe('true');
  });

  it('changes the filter to a type, and back to all', async () => {
    const w = mountToolbar({ filterTypeId: null });

    await button(w, 'LX').trigger('click');
    await button(w, 'All').trigger('click');

    expect(w.emitted('update:filterTypeId')).toEqual([[1], [null]]);
  });

  it('passes a find result on', () => {
    const w = mountToolbar();
    const match = { cue: { id: 1 } };

    w.findComponent(FindStub).vm.$emit('jump', match);

    expect(w.emitted('jump')?.[0]).toEqual([match]);
  });

  it('says that changes save straight away', () => {
    expect(mountToolbar().text()).toContain('Cue changes save straight away');
  });

  it('sits just under the app navbar when there is one, and at a default height otherwise', async () => {
    const without = mountToolbar();
    expect(without.find('.cue-toolbar').attributes('style')).toContain('top: 56px');

    const navbar = document.createElement('nav');
    navbar.className = 'navbar';
    Object.defineProperty(navbar, 'offsetHeight', { value: 72 });
    document.body.appendChild(navbar);
    try {
      const withNavbar = mountToolbar();
      await nextTick();
      expect(withNavbar.find('.cue-toolbar').attributes('style')).toContain('top: 72px');
    } finally {
      navbar.remove();
    }
  });
});
