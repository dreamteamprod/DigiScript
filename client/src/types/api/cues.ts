export interface CueType {
  id: number;
  show_id: number | null;
  prefix: string | null;
  description: string | null;
  colour: string | null;
}

export interface Cue {
  id: number;
  cue_type_id: number | null;
  ident: string | null;
}
