import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import LineTypeSegmented from './LineTypeSegmented.vue';
import { LINE_TYPES } from '@/constants/lineTypes';

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
const global = {
  components: { BButtonGroup: passthrough('div'), BButton: passthrough('button') },
};

describe('LineTypeSegmented', () => {
  it('emits update:modelValue with the clicked type', async () => {
    const wrapper = mount(LineTypeSegmented, {
      props: { modelValue: LINE_TYPES.DIALOGUE },
      global,
    });

    const buttons = wrapper.findAll('button');
    const directionButton = buttons.find((b) => b.text() === 'Direction')!;
    await directionButton.trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[LINE_TYPES.STAGE_DIRECTION]]);
  });

  it('marks the current type as pressed', () => {
    const wrapper = mount(LineTypeSegmented, {
      props: { modelValue: LINE_TYPES.CUE_LINE },
      global,
    });

    const buttons = wrapper.findAll('button');
    const cueButton = buttons.find((b) => b.text() === 'Cue')!;
    const dialogueButton = buttons.find((b) => b.text() === 'Dialogue')!;
    expect(cueButton.attributes('aria-pressed')).toBe('true');
    expect(dialogueButton.attributes('aria-pressed')).toBe('false');
  });

  it('disables every button when disabled is set (an already-saved line)', () => {
    const wrapper = mount(LineTypeSegmented, {
      props: { modelValue: LINE_TYPES.DIALOGUE, disabled: true },
      global,
    });

    for (const button of wrapper.findAll('button')) {
      expect(button.attributes('disabled')).toBeDefined();
    }
  });
});
