import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import RemoteEditorsBadge from './RemoteEditorsBadge.vue';
import { passthrough } from './testStubs';

const stubs = {
  BCol: passthrough('div'),
};

describe('RemoteEditorsBadge (Phase 4 Step C)', () => {
  it('renders nothing for an empty names array', () => {
    const wrapper = mount(RemoteEditorsBadge, { props: { names: [] }, global: { stubs } });
    expect(wrapper.find('.remote-editors').exists()).toBe(false);
  });

  it('renders one avatar per name, each with an accessible title, for the row variant', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex', 'blair'] },
      global: { stubs },
    });
    const row = wrapper.find('.remote-editors');
    expect(row.exists()).toBe(true);
    const avatars = row.findAll('.presence-avatar');
    expect(avatars).toHaveLength(2);
    expect(avatars.find((a) => a.attributes('title') === 'alex is editing this line')).toBeTruthy();
    expect(
      avatars.find((a) => a.attributes('title') === 'blair is editing this line')
    ).toBeTruthy();
  });

  it('shows just the name for a single editor in the row variant', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex'] },
      global: { stubs },
    });
    expect(wrapper.find('.remote-editors-label').text()).toBe('alex');
  });

  it('joins two names with a comma in the row variant', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex', 'blair'] },
      global: { stubs },
    });
    expect(wrapper.find('.remote-editors-label').text()).toBe('alex, blair');
  });

  it('collapses three or more names to "first +N"', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex', 'blair', 'casey'] },
      global: { stubs },
    });
    expect(wrapper.find('.remote-editors-label').text()).toBe('alex +2');
  });

  it('reads as "is also editing this line" for the editor variant with one name', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex'], variant: 'editor' },
      global: { stubs },
    });
    expect(wrapper.find('.remote-editors-label').text()).toBe('alex is also editing this line');
  });

  it('reads as "are also editing this line" for the editor variant with multiple names', () => {
    const wrapper = mount(RemoteEditorsBadge, {
      props: { names: ['alex', 'blair'], variant: 'editor' },
      global: { stubs },
    });
    expect(wrapper.find('.remote-editors-label').text()).toBe(
      'alex, blair are also editing this line'
    );
  });
});
