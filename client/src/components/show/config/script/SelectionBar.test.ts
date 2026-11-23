import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import SelectionBar from './SelectionBar.vue';

/** Plain-element stand-ins for the bootstrap-vue-next components used here (not
 * registered in unit tests) — same technique as CollabScriptEditor.test.ts. */
function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}
const global = { components: { BButton: passthrough('button') } };

describe('SelectionBar', () => {
  it('shows the count and range label', () => {
    const wrapper = mount(SelectionBar, {
      props: { count: 3, rangeLabel: 'Lines 3 to 5' },
      global,
    });
    expect(wrapper.text()).toContain('3 lines selected');
    expect(wrapper.text()).toContain('Lines 3 to 5');
  });

  it('uses singular wording for a single-line selection', () => {
    const wrapper = mount(SelectionBar, { props: { count: 1, rangeLabel: 'Line 3' }, global });
    expect(wrapper.text()).toContain('1 line selected');
    expect(wrapper.text()).toContain('Delete 1 Line');
    expect(wrapper.text()).not.toContain('Delete 1 Lines');
  });

  it('emits each action from its own button', async () => {
    const wrapper = mount(SelectionBar, {
      props: { count: 2, rangeLabel: 'Lines 1 to 2' },
      global,
    });

    await wrapper.find('button:nth-of-type(1)').trigger('click'); // Set Character or Group
    await wrapper.find('button:nth-of-type(2)').trigger('click'); // Move to Scene
    await wrapper.find('button:nth-of-type(3)').trigger('click'); // Delete 2 Lines
    await wrapper.find('button:nth-of-type(4)').trigger('click'); // Clear Selection

    expect(wrapper.emitted('set-character')).toHaveLength(1);
    expect(wrapper.emitted('move-to-scene')).toHaveLength(1);
    expect(wrapper.emitted('delete')).toHaveLength(1);
    expect(wrapper.emitted('clear')).toHaveLength(1);
  });
});
