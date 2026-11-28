import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { enableAutoUnmount, mount } from '@vue/test-utils';
import CueTypePicker from './CueTypePicker.vue';
import { useUserStore } from '@/stores/user';
import { useShowStore } from '@/stores/show';
import type { CueType } from '@/types/api/cues';

enableAutoUnmount(afterEach);

const type = (id: number, prefix: string, description: string): CueType => ({
  id,
  show_id: 1,
  prefix,
  description,
  colour: '#ffd23f',
});
const LX = type(1, 'LX', 'Lighting');
const SND = type(2, 'SND', 'Sound');
const VID = type(3, 'VID', 'Video');
const FLY = type(4, 'FLY', 'Flys');

function mountPicker(modelValue: number | null, writable: number[], extra = {}) {
  useShowStore().cueTypes = [LX, SND, VID, FLY];
  useUserStore().cueColourOverrides = [];
  return mount(CueTypePicker, {
    props: {
      cueTypes: [LX, SND, VID, FLY],
      modelValue,
      writableIds: new Set(writable),
      ...extra,
    },
    attachTo: document.body,
  });
}

const radios = (w: ReturnType<typeof mountPicker>) => w.findAll('[role="radio"]');
const labels = (w: ReturnType<typeof mountPicker>) => radios(w).map((r) => r.text());

describe('CueTypePicker', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('is a labelled radio group', () => {
    const w = mountPicker(null, [1, 2], { ariaLabel: 'Cue type for the group' });

    expect(w.find('[role="radiogroup"]').attributes('aria-label')).toBe('Cue type for the group');
    expect(radios(w)).toHaveLength(4);
  });

  it('lists the types that can be written first, and marks the rest view only', () => {
    const w = mountPicker(null, [2, 4]);

    expect(labels(w)).toEqual(['SNDSound', 'FLYFlys', 'LXView only', 'VIDView only']);
    const [, , lx, vid] = radios(w);
    expect(lx.attributes('disabled')).toBeDefined();
    expect(vid.attributes('disabled')).toBeDefined();
  });

  it('marks exactly the chosen type as checked', () => {
    const w = mountPicker(2, [1, 2, 3]);

    const checked = radios(w).filter((r) => r.attributes('aria-checked') === 'true');
    expect(checked.map((r) => r.text())).toEqual(['SNDSound']);
  });

  it('chooses a type on click, but not one that is view only or while disabled', async () => {
    const w = mountPicker(null, [1]);

    await radios(w)[0].trigger('click');
    expect(w.emitted('update:modelValue')).toEqual([[1]]);

    await radios(w)[1].trigger('click');
    expect(w.emitted('update:modelValue')).toHaveLength(1);

    await w.setProps({ disabled: true });
    await radios(w)[0].trigger('click');
    expect(w.emitted('update:modelValue')).toHaveLength(1);
  });

  it('has one tab stop: the chosen type, or the first one that can be written', () => {
    const chosen = mountPicker(2, [1, 2, 4]);
    expect(radios(chosen).map((r) => r.attributes('tabindex'))).toEqual(['-1', '0', '-1', '-1']);

    const none = mountPicker(null, [2, 4]);
    expect(radios(none).map((r) => r.attributes('tabindex'))).toEqual(['0', '-1', '-1', '-1']);
  });

  it('moves between the types that can be written with the arrow keys, skipping view-only ones', async () => {
    const w = mountPicker(1, [1, 2, 4]);
    const [first] = radios(w);
    (first.element as HTMLElement).focus();

    await first.trigger('keydown', { key: 'ArrowRight' });
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([2]);
    expect(document.activeElement?.getAttribute('data-cue-type-id')).toBe('2');

    await radios(w)[1].trigger('keydown', { key: 'ArrowDown' });
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([4]);
    expect(document.activeElement?.getAttribute('data-cue-type-id')).toBe('4');
  });

  it('wraps around at both ends and goes backwards with Left and Up', async () => {
    const w = mountPicker(1, [1, 2, 4]);
    (radios(w)[0].element as HTMLElement).focus();

    await radios(w)[0].trigger('keydown', { key: 'ArrowLeft' });
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([4]);

    (radios(w)[2].element as HTMLElement).focus();
    await radios(w)[2].trigger('keydown', { key: 'ArrowRight' });
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([1]);

    (radios(w)[1].element as HTMLElement).focus();
    await radios(w)[1].trigger('keydown', { key: 'ArrowUp' });
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([1]);
  });

  it('ignores other keys, and does nothing when no type can be written', async () => {
    const w = mountPicker(null, [1, 2]);
    await radios(w)[0].trigger('keydown', { key: 'a' });
    expect(w.emitted('update:modelValue')).toBeUndefined();

    const none = mountPicker(null, []);
    await radios(none)[0].trigger('keydown', { key: 'ArrowRight' });
    expect(none.emitted('update:modelValue')).toBeUndefined();
  });

  it('can focus the chosen type, or the first one that can be written', () => {
    const chosen = mountPicker(2, [1, 2]);
    (chosen.vm as unknown as { focus: () => void }).focus();
    expect(document.activeElement?.getAttribute('data-cue-type-id')).toBe('2');

    // Types that can be written come first, in the show's own order: LX before FLY.
    const none = mountPicker(null, [4, 1]);
    (none.vm as unknown as { focus: () => void }).focus();
    expect(document.activeElement?.getAttribute('data-cue-type-id')).toBe('1');
  });
});
