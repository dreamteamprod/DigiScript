import { describe, it, expect, afterEach } from 'vitest';
import { mount, type VueWrapper } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import * as Y from 'yjs';
import { useYTextField } from './useYTextField';
import { LOCAL_EDIT_ORIGIN } from '@/js/yjs/draftWriter';
import { applyTextDiff } from '@/js/yjs/ytextDiff';

function makeIntegratedText(initial = ''): Y.Text {
  const doc = new Y.Doc();
  const text = new Y.Text(initial);
  doc.getMap('root').set('t', text);
  return text;
}

const TestField = defineComponent({
  props: {
    getText: { type: Function, required: true },
    writeText: { type: Function, required: true },
  },
  setup(props) {
    const { value, inputRef, onInput, onCaretActivity } = useYTextField(
      () => props.getText() as Y.Text | null,
      (text: string) => props.writeText(text)
    );
    return () =>
      h('input', {
        ref: inputRef,
        value: value.value,
        onInput: (e: Event) => onInput((e.target as HTMLInputElement).value),
        onKeyup: onCaretActivity,
        onClick: onCaretActivity,
        onFocus: onCaretActivity,
      });
  },
});

describe('useYTextField', () => {
  let wrapper: VueWrapper | null = null;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it('shows the Y.Text content on mount', () => {
    const ytext = makeIntegratedText('hello');
    wrapper = mount(TestField, { props: { getText: () => ytext, writeText: () => {} } });
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('hello');
  });

  it('writes a local keystroke through writeText using the minimal diff', () => {
    const ytext = makeIntegratedText('hello');
    const writeText = (text: string) => applyTextDiff(ytext, text, LOCAL_EDIT_ORIGIN);
    wrapper = mount(TestField, { props: { getText: () => ytext, writeText } });

    const input = wrapper.find('input').element as HTMLInputElement;
    input.value = 'helloo';
    input.dispatchEvent(new Event('input'));

    expect(ytext.toString()).toBe('helloo');
    expect(input.value).toBe('helloo');
  });

  it('reflects a remote edit and keeps a focused caret anchored to its character', async () => {
    const ytext = makeIntegratedText('hello world');
    const writeText = (text: string) => applyTextDiff(ytext, text, LOCAL_EDIT_ORIGIN);
    wrapper = mount(TestField, {
      props: { getText: () => ytext, writeText },
      attachTo: document.body,
    });

    const input = wrapper.find('input').element as HTMLInputElement;
    input.focus();
    // Caret sits right after "hello" (index 5), before " world".
    input.setSelectionRange(5, 5);
    input.dispatchEvent(new Event('click'));

    // A remote editor inserts text before the caret's position.
    ytext.doc!.transact(() => {
      ytext.insert(0, 'XX-');
    }, 'remote-origin');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(input.value).toBe('XX-hello world');
    // The caret followed "hello", not the raw index 5 (which would now sit inside "XX-he").
    expect(input.selectionStart).toBe(8);
    expect(input.selectionEnd).toBe(8);

    wrapper.unmount();
  });

  it('does not fight a local write with a caret restore', async () => {
    const ytext = makeIntegratedText('ab');
    const writeText = (text: string) => applyTextDiff(ytext, text, LOCAL_EDIT_ORIGIN);
    wrapper = mount(TestField, {
      props: { getText: () => ytext, writeText },
      attachTo: document.body,
    });

    const input = wrapper.find('input').element as HTMLInputElement;
    input.focus();
    input.value = 'abc';
    input.setSelectionRange(3, 3);
    input.dispatchEvent(new Event('input'));
    await wrapper.vm.$nextTick();

    expect(input.value).toBe('abc');
    expect(input.selectionStart).toBe(3);

    wrapper.unmount();
  });

  it('switches to a newly observed Y.Text when the target is recreated', () => {
    const first = makeIntegratedText('first');
    const second = makeIntegratedText('second');
    let current = first;
    wrapper = mount(TestField, { props: { getText: () => current, writeText: () => {} } });

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('first');

    current = second;
    wrapper.unmount();
    wrapper = mount(TestField, { props: { getText: () => current, writeText: () => {} } });
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('second');
  });
});
