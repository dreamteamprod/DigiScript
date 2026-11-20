/**
 * `BulkEditModal`'s emit payload, shared with both of its consumers
 * (`CollabScriptEditor.vue`, `ScriptEditor.vue`). Two optional sections, each
 * internally complete, rather than five independently-nullable fields:
 * `handleOk` only ever emits `actScene` with both of its fields set or not at
 * all, and the same for `assignee` — whose `characterId`/`characterGroupId`
 * are a union rather than two more independently-nullable fields, so
 * "neither selected" (which would silently clear a line's assignment) is not
 * representable, matching the mutual exclusivity `BulkEditModal`'s own UI
 * already enforces between its character and character-group dropdowns.
 */
export interface BulkEditPayload {
  actScene: { actId: number; sceneId: number } | null;
  assignee:
    | {
        partIndex: number;
        characterId: number;
        characterGroupId: null;
      }
    | {
        partIndex: number;
        characterId: null;
        characterGroupId: number;
      }
    | null;
}
