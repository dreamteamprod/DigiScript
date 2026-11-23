/**
 * The payload `applyToSelection()` applies to every line in the active selection, in
 * both `ScriptEditor.vue` and `CollabScriptEditor.vue` — one call handles "Set
 * Character or Group" (`assignee` set, `actScene` null) and "Move to Scene"
 * (`actScene` set, `assignee` null) alike. Two optional sections, each internally
 * complete, rather than five independently-nullable fields: `actScene` is either
 * both fields set or absent entirely, and the same for `assignee` — whose
 * `characterId`/`characterGroupId` are a union rather than two more
 * independently-nullable fields, so "neither selected" (which would silently clear a
 * line's assignment) is not representable.
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
