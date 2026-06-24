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
}
