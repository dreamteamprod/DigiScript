import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import ScriptLinePart from './ScriptLinePart.vue';
import { passthrough, SelectStub } from './testStubs';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLinePart as ScriptLinePartType } from '@/types/api/script';

const stubs = {
  BCol: passthrough('div'),
  BRow: passthrough('div'),
  BFormGroup: passthrough('div'),
  BButton: passthrough('button'),
  BFormSelect: SelectStub,
  BFormInput: passthrough('input'),
};

function part(): ScriptLinePartType {
  return {
    id: null,
    line_id: null,
    part_index: 0,
    character_id: null,
    character_group_id: null,
    line_text: 'Hello',
  };
}

describe('ScriptLinePart (classic) keyboard handling', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    setActivePinia(createPinia());
    wrapper = mount(ScriptLinePart, {
      props: {
        focusInput: false,
        characters: [],
        characterGroups: [],
        showRemoveButton: false,
        lineType: LINE_TYPES.DIALOGUE,
        lineParts: [part()],
        modelValue: part(),
      },
      global: { stubs },
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it('emits navigate-up / navigate-down on Up / Down in the text field', async () => {
    const input = wrapper!.find('input');
    await input.trigger('keydown', { key: 'ArrowUp' });
    await input.trigger('keydown', { key: 'ArrowDown' });

    expect(wrapper!.emitted('navigate-up')).toHaveLength(1);
    expect(wrapper!.emitted('navigate-down')).toHaveLength(1);
  });

  it('ignores Up / Down mid-IME-composition, so candidate selection does not close the line', async () => {
    const input = wrapper!.find('input');
    await input.trigger('keydown', { key: 'ArrowUp', isComposing: true });
    await input.trigger('keydown', { key: 'ArrowDown', isComposing: true });

    expect(wrapper!.emitted('navigate-up')).toBeUndefined();
    expect(wrapper!.emitted('navigate-down')).toBeUndefined();
  });

  it('ignores Enter mid-IME-composition', async () => {
    await wrapper!.find('input').trigger('keydown', { key: 'Enter', isComposing: true });

    expect(wrapper!.emitted('try-finish-line')).toBeUndefined();
  });
});
