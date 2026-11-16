import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import RemoteEditorsBadge from './RemoteEditorsBadge.vue';
import { passthrough } from './testStubs';

const stubs = {
  BCol: passthrough('div'),
  BBadge: passthrough('span'),
};

describe('RemoteEditorsBadge (Phase 4 Step C)', () => {
  it('renders nothing for an empty names array', () => {
    const wrapper = mount(RemoteEditorsBadge, { props: { names: [] }, global: { stubs } });
    expect(wrapper.find('.remote-editors').exists()).toBe(false);
  });

  it('renders one badge per name, each with an accessible title', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex', 'blair'] },
      global: { stubs },
    });
    const row = wrapper.find('.remote-editors');
    expect(row.exists()).toBe(true);
    const badges = row.findAll('span');
    expect(badges).toHaveLength(2);
    expect(badges.find((b) => b.text().includes('alex'))?.attributes('title')).toBe(
      'alex is editing this line'
    );
    expect(badges.find((b) => b.text().includes('blair'))?.attributes('title')).toBe(
      'blair is editing this line'
    );
  });
});
