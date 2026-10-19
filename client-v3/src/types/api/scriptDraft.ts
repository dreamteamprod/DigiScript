export interface RoomMember {
  user_id: number | null;
  username: string;
  role: 'editor' | 'viewer';
  /** Per-connection key — `user_id` alone can't tell one user's two tabs apart. */
  client_id: string | null;
}

export interface RoomMembersMessage {
  members: RoomMember[];
}

export interface CollabErrorMessage {
  error: string;
}

export interface ScriptSavedMessage {
  last_saved_at: string;
}

export interface SaveProgressMessage {
  page: number;
  total: number;
  percent: number;
}
