/* eslint-disable vue/one-component-per-file -- small shared test stubs */
import { defineComponent, h } from 'vue';

/** A thin pass-through for a Bootstrap-Vue-Next component not registered in unit tests. */
export function passthrough(tag: string) {
  return defineComponent({
    inheritAttrs: true,
    render() {
      return h(tag, this.$slots.default?.());
    },
  });
}

/** A BFormSelect stand-in that renders a plain <select> and forwards changes as numbers/null. */
export const SelectStub = defineComponent({
  props: { modelValue: {}, options: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  render() {
    return h(
      'select',
      {
        'data-value': String(this.modelValue),
        onChange: (e: Event) => {
          const raw = (e.target as HTMLSelectElement).value;
          this.$emit('update:modelValue', raw === 'null' ? null : Number.parseInt(raw, 10));
        },
      },
      (this.options as { value: unknown; text: string }[]).map((o) =>
        h('option', { value: String(o.value) }, o.text)
      )
    );
  },
});
