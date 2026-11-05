/* eslint-disable vue/one-component-per-file -- small in-file stubs */
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import SaveProgressModal from './SaveProgressModal.vue';

// bootstrap-vue-next components are not registered in unit tests. BModal's content
// renders unconditionally here (there is no real show/hide), with no-op show()/hide()
// exposed since defineExpose() in the real component calls through to them.
const ModalStub = defineComponent({
  inheritAttrs: true,
  methods: {
    show() {
      // no-op
    },
    hide() {
      // no-op
    },
  },
  render() {
    return h('div', this.$slots.default?.());
  },
});
// A thin stand-in that keeps `variant` (and the other props SaveProgressModal sets)
// readable as attributes, so a test can assert on them without a real BProgress.
const ProgressStub = defineComponent({
  inheritAttrs: true,
  render() {
    return h('div', { class: 'progress-stub' });
  },
});

function mountModal(props: {
  inProgress: boolean;
  currentPage: number;
  totalPages: number;
  error: string | null;
}) {
  return mount(SaveProgressModal, {
    props,
    global: { components: { BModal: ModalStub, BProgress: ProgressStub } },
  });
}

describe('SaveProgressModal', () => {
  it('shows the current page while in progress', () => {
    const w = mountModal({ inProgress: true, currentPage: 2, totalPages: 5, error: null });

    expect(w.text()).toContain('Saving page 2 of 5');
    expect(w.find('.progress-stub').attributes('variant')).toBe('primary');
  });

  it('shows a success message once finished with no error', () => {
    const w = mountModal({ inProgress: false, currentPage: 5, totalPages: 5, error: null });

    expect(w.text()).toContain('Finished saving script.');
    expect(w.text()).not.toContain('Saving page');
    expect(w.find('.progress-stub').attributes('variant')).toBe('success');
  });

  it('shows the failure reason instead of the success message once finished with an error', () => {
    const w = mountModal({
      inProgress: false,
      currentPage: 2,
      totalPages: 5,
      error: 'disk full',
    });

    expect(w.text()).toContain('disk full');
    expect(w.text()).not.toContain('Finished saving script.');
    expect(w.find('.progress-stub').attributes('variant')).toBe('danger');
  });

  it('exposes show/hide that call through to the inner modal', () => {
    const w = mountModal({ inProgress: false, currentPage: 0, totalPages: 0, error: null });
    const exposed = w.vm as unknown as { show: () => void; hide: () => void };

    // The inner BModal is a stub with no-op show()/hide() — this just proves
    // SaveProgressModal's own exposed methods reach it rather than throwing.
    expect(() => exposed.show()).not.toThrow();
    expect(() => exposed.hide()).not.toThrow();
  });
});
