import { onUnmounted } from 'vue';

/**
 * The timer-scheduling half of autosave, shared by the classic and collaborative
 * script editors — only the scheduling is identical; what a tick actually *does*
 * (`onTick`) differs between them (the classic editor always shows the blocking save
 * modal, the collaborative one is deliberately lighter-touch), so that stays with each
 * caller rather than living here.
 */
export function useAutoSave(onTick: () => void | Promise<void>) {
  let timer: ReturnType<typeof setInterval> | null = null;

  function stop(): void {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  }

  /**
   * (Re)start the timer at `intervalMinutes` (clamped to a 1-minute floor), or stop it
   * if `enabled` is false. Always clears any previous timer first, so it's safe to call
   * on every relevant change (editor status, settings) rather than tracking what
   * changed.
   */
  function restart(enabled: boolean, intervalMinutes: number): void {
    stop();
    if (!enabled) return;
    const ms = Math.max(intervalMinutes, 1) * 60_000;
    timer = setInterval(() => void onTick(), ms);
  }

  onUnmounted(stop);

  return { restart, stop };
}
