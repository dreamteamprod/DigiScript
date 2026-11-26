import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import AddLineDivider from './AddLineDivider.vue';
import { LINE_TYPES } from '@/constants/lineTypes';

/** Plain-element stand-ins for the bootstrap-vue-next components used here (not
 * registered in unit tests) — same technique as CollabScriptEditor.test.ts. The
 * dropdown items render as plain buttons so a click can be triggered directly,
 * without needing BDropdown's own open/closed state. */
function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}
const global = {
  components: {
    BDropdown: passthrough('div'),
    BDropdownHeader: passthrough('div'),
    BDropdownItem: passthrough('button'),
  },
};

describe('AddLineDivider', () => {
  it('emits add with the dialogue line type', async () => {
    const wrapper = mount(AddLineDivider, { props: { lineNumber: 3 }, global });
    const items = wrapper.findAll('button');
    const dialogueItem = items.find((i) => i.text().includes('Dialogue'))!;
    await dialogueItem.trigger('click');

    expect(wrapper.emitted('add')).toEqual([[LINE_TYPES.DIALOGUE]]);
  });

  it('emits add with the gap (spacing) line type', async () => {
    const wrapper = mount(AddLineDivider, { props: { lineNumber: 1 }, global });
    const items = wrapper.findAll('button');
    const gapItem = items.find((i) => i.text().includes('Gap'))!;
    await gapItem.trigger('click');

    expect(wrapper.emitted('add')).toEqual([[LINE_TYPES.SPACING]]);
  });
});
