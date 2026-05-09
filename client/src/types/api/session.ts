export interface ShowSession {
  id: number;
  show_id: number;
  script_revision_id: number;
  start_date_time: string | null;
  end_date_time: string | null;
  user_id: number | null;
  client_internal_id: string | null;
  latest_line_ref: string | null;
  current_interval_id: number | null;
  tags: SessionTag[];
}

export interface Interval {
  id: number;
  session_id: number | null;
  act_id: number | null;
  start_datetime: string | null;
  end_datetime: string | null;
  initial_length: number | null;
}

export interface SessionTag {
  id: number;
  show_id: number | null;
  tag: string;
  colour: string;
}
