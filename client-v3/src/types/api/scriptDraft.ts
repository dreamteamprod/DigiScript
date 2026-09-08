export interface RoomMember {
  user_id: number | null;
  username: string;
  role: 'editor' | 'viewer';
}

export interface RoomMembersMessage {
  members: RoomMember[];
}

export interface CollabErrorMessage {
  error: string;
}

export interface RequestEditFailureMessage {
  reason: string;
}

export interface ScriptSavedMessage {
  last_saved_at: string;
}

export interface SaveProgressMessage {
  page: number;
  total: number;
}
