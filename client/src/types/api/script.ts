export interface ScriptLinePart {
  id: number | null;
  line_id: number | null;
  part_index: number | null;
  character_id: number | null;
  character_group_id: number | null;
  line_text: string | null;
}

export interface ScriptLine {
  id: number | null;
  act_id: number | null;
  scene_id: number | null;
  page: number | null;
  line_type: number;
  stage_direction_style_id: number | null;
  line_parts: ScriptLinePart[];
}

export interface ScriptRevision {
  id: number;
  script_id: number | null;
  revision: number | null;
  created_at: string | null;
  edited_at: string | null;
  description: string | null;
  previous_revision_id: number | null;
  has_draft?: boolean;
}

export interface StageDirectionStyle {
  id: number;
  script_id: number | null;
  description: string | null;
  bold: boolean | null;
  italic: boolean | null;
  underline: boolean | null;
  text_format: string | null;
  text_colour: string | null;
  enable_background_colour: boolean | null;
  background_colour: string | null;
}

export type ScriptCut = number; // NOSONAR

export interface CompiledScript {
  revision_id: number;
  created_at: string | null;
  updated_at: string | null;
  data_path: string | null;
}

export interface PageStatus {
  added: number[];
  updated: number[];
  deleted: number[];
  inserted: number[];
}
