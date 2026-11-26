import { onUnmounted } from 'vue';

/** Reads the auto-save user setting fields, shared by both editors' own
 * setupAutoSave (otherwise identical apart from which "is this an editor at
 * all" flag they AND it with) — `userSettings` is typed loosely at its two call
 * sites already (a Pinia store field typed `UserSettings | Record<string,
 * unknown>`), so this takes the same `unknown` rather than forcing a cast on
 * every caller. */
export function autoSaveSettings(userSettings: unknown): {
  enabled: boolean;
  intervalMinutes: number;
} {
  const settings = userSettings as {
    enable_script_auto_save?: boolean;
    script_auto_save_interval?: number;
  };
  return {
    enabled: !!settings.enable_script_auto_save,
    intervalMinutes: settings.script_auto_save_interval ?? 5,
  };
}

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
