import type { Act, Scene } from '@/types/api/show';

type LineWithActScene = { act_id: number | null; scene_id: number | null };

/**
 * The acts a line's act select may offer: the chain starting from the previous line's
 * act (or the show's first act, if there is no previous line), stopping once the next
 * line's own act is reached. Shared by the classic and collaborative line editors —
 * this traversal has nothing to do with how the edit is written.
 */
export function computeValidActs(
  acts: Act[],
  previousLine: LineWithActScene | null,
  nextLine: LineWithActScene | null
): Act[] {
  let startAct = acts.find((a) => a.previous_act == null) ?? null;
  if (previousLine) {
    startAct = acts.find((a) => a.id === previousLine.act_id) ?? startAct;
  }
  const result: Act[] = [];
  let cur = startAct;
  while (cur) {
    result.push(cur);
    if (nextLine && nextLine.act_id === cur.id) break;
    cur = cur.next_act == null ? null : (acts.find((a) => a.id === cur!.next_act) ?? null);
  }
  return result;
}

/** The scenes a line's scene select may offer, within `actId`. Same traversal shape as {@link computeValidActs}. */
export function computeValidScenes(
  scenes: Scene[],
  actId: number | null,
  previousLine: LineWithActScene | null,
  nextLine: LineWithActScene | null
): Scene[] {
  if (actId == null) return [];
  const actScenes = scenes.filter((s) => s.act === actId);
  let startScene = actScenes.find((s) => s.previous_scene == null) ?? null;
  if (previousLine && previousLine.act_id === actId) {
    startScene = actScenes.find((s) => s.id === previousLine.scene_id) ?? startScene;
  }
  const result: Scene[] = [];
  let cur = startScene;
  while (cur) {
    result.push(cur);
    if (nextLine && nextLine.scene_id === cur.id) break;
    cur = cur.next_scene == null ? null : (actScenes.find((s) => s.id === cur!.next_scene) ?? null);
  }
  return result;
}
