export interface Show {
  id: number;
  name: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string | null;
  edited_at: string | null;
  first_act_id: number | null;
  current_session_id: number | null;
  script_mode: number;
}

export interface Cast {
  id: number;
  show_id: number | null;
  first_name: string | null;
  last_name: string | null;
  character_list: Character[];
}

export interface Character {
  id: number;
  show_id: number | null;
  played_by: number | null;
  name: string | null;
  description: string | null;
  cast_member: { id: number; first_name: string | null; last_name: string | null } | null;
}

export interface CharacterGroup {
  id: number;
  show_id: number | null;
  name: string | null;
  description: string | null;
  characters: number[];
}

// first_scene, next_act, and previous_act are serialized as IDs by the marshmallow schema
export interface Act {
  id: number;
  show_id: number | null;
  name: string | null;
  interval_after: boolean | null;
  first_scene: number | null;
  next_act: number | null;
  previous_act: number | null;
}

// act, next_scene, and previous_scene are serialized as IDs by the marshmallow schema
export interface Scene {
  id: number;
  show_id: number | null;
  act: number | null;
  name: string | null;
  next_scene: number | null;
  previous_scene: number | null;
}
