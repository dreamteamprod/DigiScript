/**
 * `BulkEditModal`'s emit payload, shared with both of its consumers
 * (`CollabScriptEditor.vue`, `ScriptEditor.vue`). A discriminated union rather
 * than five independently-nullable fields: `actScene` and `assignee` are each
 * all-or-nothing (the modal's own `canApply` already enforces that a
 * half-filled section can't be submitted), so this makes that invariant part
 * of the type instead of needing it re-checked at every consumer.
 */
export interface BulkEditPayload {
  actScene: { actId: number; sceneId: number } | null;
  assignee: {
    partIndex: number;
    characterId: number | null;
    characterGroupId: number | null;
  } | null;
}
