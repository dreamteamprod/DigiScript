/**
 * "Set Character or Group" for one part position: exactly one of `characterId` /
 * `characterGroupId` is set, so "neither selected" (which would silently clear a
 * line's assignment) is not representable. `partIndex` is 1-based, as shown in the
 * dialog.
 */
export type CharacterAssignee =
  | {
      partIndex: number;
      characterId: number;
      characterGroupId: null;
    }
  | {
      partIndex: number;
      characterId: null;
      characterGroupId: number;
    };

/**
 * The payload `applyToSelection()` applies to every line in the active selection, in
 * both `ScriptEditor.vue` and `CollabScriptEditor.vue`. A discriminated union on
 * `kind`: "Move to Scene" (`actScene`) and "Set Character or Group" (`assignee`) are
 * mutually exclusive, so the nonsensical "both" and "neither" payloads cannot be
 * constructed.
 */
export type BulkEditPayload =
  { kind: 'actScene'; actId: number; sceneId: number } | ({ kind: 'assignee' } & CharacterAssignee);
