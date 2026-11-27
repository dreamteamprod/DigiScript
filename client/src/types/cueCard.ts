/** The one cue card open on the Script Cues page, if any. */
export interface ActiveCueCard {
  lineId: number;
  /**
   * `add` places a new cue or group; `edit-cue` / `edit-group` change an existing one;
   * `view` is the read-only note for a cue type the person cannot change.
   */
  kind: 'add' | 'edit-cue' | 'edit-group' | 'view';
  cueId?: number;
  groupId?: number;
}
