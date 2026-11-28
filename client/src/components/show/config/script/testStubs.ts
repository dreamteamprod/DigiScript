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

function parseSelectValue(raw: string): number | string {
  return /^-?\d+$/.test(raw) ? Number.parseInt(raw, 10) : raw;
}

/**
 * A BFormSelect stand-in that renders a plain <select> (including <optgroup>, for the
 * combined character/group dropdown's grouped options) and forwards changes as
 * numbers/null, or the raw string when it isn't purely numeric — the combined
 * dropdown's grouped values (`'c:2'`, `'g:1'`) aren't. `disabled` isn't declared as a
 * prop, so it falls through as a plain HTML attribute on the rendered <select>.
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
          const value = raw === 'null' ? null : parseSelectValue(raw);
          this.$emit('update:modelValue', value);
        },
      },
      children
    );
  },
});

/** A BAlert stand-in — renders its default slot only while modelValue is true,
 * the one piece of real show/hide behaviour worth keeping in a stub. */
export const AlertStub = defineComponent({
  props: { modelValue: { type: Boolean, default: false } },
  render() {
    return this.modelValue ? h('div', { class: 'alert-stub' }, this.$slots.default?.()) : null;
  },
});

/**
 * A BModal stand-in — content renders unconditionally (there is no real show/hide
 * here), but production code calls `.show()`/`.hide()` on its template ref, and since
 * BModal isn't exposed via `defineExpose`, the `methods` option (always part of an
 * Options API public instance) is the simplest way to give it some, as harmless no-ops.
 */
export const ModalStub = defineComponent({
  inheritAttrs: true,
  methods: {
    show() {
      // no-op: content already renders unconditionally in this stub
    },
    hide() {
      // no-op: content already renders unconditionally in this stub
    },
  },
  render() {
    return h('div', this.$slots.default?.());
  },
});
