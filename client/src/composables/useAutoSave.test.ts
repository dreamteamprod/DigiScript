import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { defineComponent } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { useAutoSave } from './useAutoSave';

describe('useAutoSave', () => {
  let wrapper: VueWrapper | null = null;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    vi.useRealTimers();
  });

  function mountWith(onTick: () => void) {
    const Comp = defineComponent({
      setup() {
        return { autoSave: useAutoSave(onTick) };
      },
      render: () => null,
    });
    wrapper = mount(Comp);
    return (wrapper.vm as unknown as { autoSave: ReturnType<typeof useAutoSave> }).autoSave;
  }

  it('does not schedule a tick when disabled', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);

    autoSave.restart(false, 5);
    vi.advanceTimersByTime(10 * 60_000);

    expect(onTick).not.toHaveBeenCalled();
  });

  it('ticks on the requested interval when enabled', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);

    autoSave.restart(true, 5);
    vi.advanceTimersByTime(5 * 60_000 - 1);
    expect(onTick).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(onTick).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(5 * 60_000);
    expect(onTick).toHaveBeenCalledTimes(2);
  });

  it('clamps an interval below 1 minute up to 1 minute', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);

    autoSave.restart(true, 0);
    vi.advanceTimersByTime(60_000 - 1);
    expect(onTick).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onTick).toHaveBeenCalledTimes(1);
  });

  it('restarting replaces the previous timer rather than stacking a second one', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);

    autoSave.restart(true, 5);
    vi.advanceTimersByTime(2 * 60_000);
    autoSave.restart(true, 5); // re-armed from now, not from the first call

    vi.advanceTimersByTime(4 * 60_000);
    expect(onTick).not.toHaveBeenCalled();
    vi.advanceTimersByTime(60_000);
    expect(onTick).toHaveBeenCalledTimes(1);
  });

  it('stop() cancels a pending tick', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);

    autoSave.restart(true, 5);
    autoSave.stop();
    vi.advanceTimersByTime(10 * 60_000);

    expect(onTick).not.toHaveBeenCalled();
  });

  it('stops the timer when the component unmounts', () => {
    const onTick = vi.fn();
    const autoSave = mountWith(onTick);
    autoSave.restart(true, 5);

    wrapper!.unmount();
    wrapper = null;
    vi.advanceTimersByTime(10 * 60_000);

    expect(onTick).not.toHaveBeenCalled();
  });
});
