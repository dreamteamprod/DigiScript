export interface User {
  id: number;
  username: string | null;
  is_admin: boolean | null;
  created_on: string | null;
  last_login: string | null;
  last_seen: string | null;
  requires_password_change: boolean;
  token_version: number;
}

export interface CueColourOverride {
  id: number;
  cue_type_id: number | null;
  colour: string | null;
}

export interface UserSettings {
  enable_script_auto_save: boolean | null;
  script_auto_save_interval: number | null;
  cue_position_right: boolean | null;
  script_text_alignment: number;
  console_log_level: string;
  character_mru_sort: boolean;
  character_combined_dropdown: boolean;
  preferred_ui: string | null;
}
