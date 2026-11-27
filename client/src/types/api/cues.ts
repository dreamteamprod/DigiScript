export interface CueType {
  id: number;
  show_id: number | null;
  prefix: string | null;
  description: string | null;
  colour: string | null;
}

export interface CueGroup {
  id: number;
  cue_type_id: number;
  label_override: string | null;
}

export interface Cue {
  id: number;
  cue_type_id: number | null;
  ident: string | null;
  group_id: number | null;
  sort_order: number | null;
  line_position: number | null;
}

/**
 * Where a line that has cues sits in the current revision's script, from
 * `GET show/cues`. `index` is zero-based within the page, in script order. Lines
 * without an entry have an unknown position (never treat that as "first").
 */
export interface LinePosition {
  page: number | null;
  index: number;
  act_id: number | null;
  scene_id: number | null;
}
