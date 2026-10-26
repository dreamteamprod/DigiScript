/* eslint-disable vue/one-component-per-file -- small shared test stubs */
import { defineComponent, h, type PropType } from 'vue';

/** A thin pass-through for a Bootstrap-Vue-Next component not registered in unit tests. */
export function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}

type FlatOption = { value: unknown; text: string };
type GroupedOption = { label: string; options: FlatOption[] };

function renderOption(o: FlatOption) {
  return h('option', { value: String(o.value) }, o.text);
}

/**
 * A BFormSelect stand-in that renders a plain <select> (including <optgroup>, for the
 * combined character/group dropdown's grouped options) and forwards changes as
 * numbers/null, or the raw string when it isn't purely numeric — the combined
 * dropdown's grouped values (`'c:2'`, `'g:1'`) aren't.
 */
export const SelectStub = defineComponent({
  props: {
    modelValue: { type: [Number, String] as PropType<number | string | null>, default: null },
    options: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue'],
  render() {
    const children = (this.options as (FlatOption | GroupedOption)[]).map((o) =>
      'options' in o
        ? h('optgroup', { label: o.label }, o.options.map(renderOption))
        : renderOption(o)
    );
    return h(
      'select',
      {
        'data-value': String(this.modelValue),
        onChange: (e: Event) => {
          const raw = (e.target as HTMLSelectElement).value;
          const value =
            raw === 'null' ? null : /^-?\d+$/.test(raw) ? Number.parseInt(raw, 10) : raw;
          this.$emit('update:modelValue', value);
        },
      },
      children
    );
  },
});
